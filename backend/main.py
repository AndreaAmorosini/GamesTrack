from typing import Union, Annotated
import sys
from fastapi import FastAPI, HTTPException, status, Depends, Query
from fastapi.middleware.cors import CORSMiddleware  # Luigi   (per il frontend)
from pydantic import BaseModel, EmailStr, Field
from init_db import init_mongo
import os
from pymongo import MongoClient, errors, UpdateOne
from utils.security import hash_password
from datetime import datetime
from bson import ObjectId
from utils.psnTrack import sync_psn
from utils.steamTrack import sync_steam
from utils.gameDB import get_metadata
from utils.igdb_api import IGDBAutoAuthClient
from utils.db import get_db
from utils.user_utils import router as user_utils_router
from utils.user_utils import get_password_hash, verify_password, get_current_active_user
import logging
import time
from fastapi.responses import JSONResponse
import re
import string


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
os.environ["PYTHONUNBUFFERED"] = "1"  # Disable output buffering for real-time logs
sys.stdout = sys.__stdout__
class CustomHTTPException(HTTPException):
    def __init__(self, status_code: int, detail: str, error_code: int):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class Response(BaseModel):
    message: str | None = None
    
# Pydantic model for registration input
class User(BaseModel):
    email: EmailStr
    username: str = Field(None, min_length=3, max_length=50)    # Luigi   (per il frontend)
    password: str = Field(None, min_length=8)                   # Luigi   (per il frontend)  
    steam: str | None = None
    steam_api_key: str | None = None
    psn: str | None = None
    psn_api_key: str | None = None
    metadata_api_key: str | None = None  # Placeholder for future API key


class Request(BaseModel):
    user_id: str | None = None
    game_id: str | None = None
    game_search_term: str | None = None

app = FastAPI()

# Luigi   (per il frontend)
# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_utils_router, prefix="/users", tags=["users"])

test_env = os.getenv("MONGO_INIT_USER"), os.getenv("MONGO_INIT_PASS")
mongo_uri = f"mongodb://{os.getenv('MONGO_INIT_USER')}:{os.getenv('MONGO_INIT_PASS')}@mongo:27017/"
client = MongoClient(mongo_uri)
db = client["game_tracker"]

igdb_client = IGDBAutoAuthClient(
    client_id=os.getenv("IGDB_CLIENT_ID"),
    client_secret=os.getenv("IGDB_CLIENT_SECRET")
)


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.on_event("startup")
def startup_event():
    init_mongo()

def user_response(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "platforms": doc.get("platforms", {}),
    }

#TODO: Login
#TODO: Register
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: User, db=Depends(get_db)):
    """Register a new user with email, password, and optional platform IDs."""
    user_doc = {
        "username": user.username,
        "email": user.email,
        "password": get_password_hash(user.password),
    }
    #Vedere di codificare le api key in modo che non siano visibili
    if user.metadata_api_key is not None:
        user_doc["metadata_api_key"] = user.metadata_api_key
    try:
        result = db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)
        if user.steam_api_key is not None:
            #Search platform by name
            platform_user_doc = {
                "platform": "steam",
                "user_id": user_id,
                "platform_ID": user.steam,
                "api_key": user.steam_api_key,
                "game_count": 0,
                "earned_achievements": 0,
                "play_count": 0,
                "full_trophies_count": 0,
            }
            try:
                db["platforms-users"].insert_one(platform_user_doc)
            except errors.DuplicateKeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Steam platform already linked",
                )
        
        if user.psn_api_key is not None:
            platform_user_doc = {
                "platform": "psn",
                "user_id": user_id,
                "platform_ID": user.psn,
                "api_key": user.psn_api_key,
                "game_count": 0,
                "earned_achievements": 0,
                "play_count": 0,
                "full_trophies_count": 0,
            }
            try:
                db["platforms-users"].insert_one(platform_user_doc)
            except errors.DuplicateKeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PSN platform already linked",
                )
                
        return {"id": str(result.inserted_id), "email": user.email}
    except errors.DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
#TODO: update user
#Update the user data by ObjectID by adding the platform IDs and API keys ready to retrieve data by external job
@app.patch("/users/update", response_model=dict)
def update_user(
    update: User,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db=Depends(get_db)
):
    """Update an existing user's data by ObjectId."""
    try:
        oid = ObjectId(str(current_user.id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        )
    update_fields = {}
    if update.email:
        update_fields["email"] = update.email
    if update.password:
        update_fields["password"] = get_password_hash(update.password)
    if update.metadata_api_key:
        update_fields["metadata_api_key"] = update.metadata_api_key
        
    if update.steam is not None:
        link = db["platforms-users"].find_one({"user_id": str(current_user.id), "platform": "steam"})
        if link:
            db["platforms-users"].update_one(
                {"user_id": str(current_user.id), "platform": "steam"},
                {
                    "$set": {
                        "platform_ID": update.steam
                        if update.steam
                        else link.get("platform_ID"),
                        "api_key": update.steam_api_key
                        if update.steam_api_key
                        else link.get("api_key"),
                    }
                },
            )
        else:
            db["platforms-users"].insert_one(
                {
                    "platform": "steam",
                    "user_id": str(current_user.id),
                    "platform_ID": update.steam,
                    "api_key": update.steam_api_key,  # Placeholder for future API key
                    "game_count": 0,
                    "earned_achievements": 0,
                    "play_count": 0,
                    "full_trophies_count": 0,
                }
            )
    if update.psn is not None or update.psn_api_key is not None:
        link = db["platforms-users"].find_one({"user_id": str(current_user.id), "platform": "psn"})
        if link:
            db["platforms-users"].update_one(
                {"user_id": str(current_user.id), "platform": "psn"},
                {
                    "$set": {
                        "platform_ID": update.psn
                        if update.psn
                        else link.get("platform_ID"),
                        "api_key": update.psn_api_key
                        if update.psn_api_key
                        else link.get("api_key"),
                    }
                },
            )
        else:
            db["platforms-users"].insert_one(
                {
                    "platform": "psn",
                    "user_id": str(current_user.id),
                    "platform_ID": update.psn,
                    "api_key": update.psn_api_key,  # Placeholder for future API key
                    "game_count": 0,
                    "earned_achievements": 0,
                    "play_count": 0,
                    "full_trophies_count": 0,
                }
            )    
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update"
        )
        
    updated = db.users.find_one_and_update(
        {"_id": oid}, {"$set": update_fields}, return_document=True
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user_response(updated)

#TODO: sync data (PSN, Xbox, Steam) da fare asincrono come job in background
#Forse fare che i metadata del gioco vengono recuperati man mano quando si apre la pagina di dettaglio del gioco
@app.post("/sync/{platform}", response_model=dict)
def sync_user_platform(platform: str, current_user: Annotated[User, Depends(get_current_active_user)], db=Depends(get_db)):
    """Synchronize data for a user on a specified platform."""
    
    def normalize_name(name):
        if not name:
            return ""
        # Remove punctuation
        name = name.translate(str.maketrans("", "", string.punctuation))
        # Remove extra spaces and lowercase
        return " ".join(name.lower().split())

    
    if platform not in ["psn", "steam", "xbox"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid platform specified. Supported platforms: psn, steam, xbox.",
        )
    
    # Validate user ID
    try:
        oid = ObjectId(str(current_user.id))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        )
    # Check if user exists
    user = db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    
    # Check platform linkage
    link = db["platforms-users"].find_one({"user_id": str(current_user.id), "platform": platform})
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No linkage for platform {platform}",
        )
    # Retrieve API credentials
    api_key = link.get("api_key")
    
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No API key found for platform {platform}",
        )
    
    # Call corresponding sync function
    stats = sync_psn(api_key) if platform == "psn" else sync_steam(api_key)
    full_games_dict = stats["fullGames"]
    #Insert all the games in database and update from metadata
    #TODO: da rivedere e forse meglio fare il check sugli external id piuttosto che sul nome
    existing_game_names = set(g["name"].lower() for g in db["games"].find({}, {"name": 1}))
    existing_external_ids = []
    if platform == "steam":
        existing_external_ids = set(g["steam_game_ID"] for g in db["games"].find({}, {"steam_game_ID": 1}) if g.get("steam_game_ID") is not None)
    elif platform == "psn":
        existing_external_ids = set(g["psn_game_ID"] for g in db["games"].find({}, {"psn_game_ID": 1}) if g.get("psn_game_ID") is not None)
    
    games_to_insert = []
    game_user_to_insert = []
    game_user_to_update = []
    
    for game in full_games_dict:
        game_name = game["name"] if game["name"] is not None else game["title_name"]
        #Check if game name contains special characters like the trademark symbol
        if "™" in game_name or "®" in game_name:
            game_name = game_name.replace("™", "").replace("®", "").strip()
        pattern = re.compile(r"tro(f|ph)[a-z]*", re.IGNORECASE)
        match = pattern.search(game_name)
        if match:
            game_name = game_name[:match.start()].strip()
        external_id = None
        if platform == "steam":
            external_id = game.get("title_id", None)
        elif platform == "psn":
            external_id = game.get("product_id", None)
            
        if game_name.lower() not in existing_game_names and ((external_id is not None and external_id not in existing_external_ids) or external_id is None):
            #Retrieve metadata for the game
            metadata = igdb_client.get_game_metadata(game_name, external_id=external_id)
            #Skip if no metadata found
            if metadata is None:
                logging.warning(f"No metadata found for game: {game_name} with external ID: {external_id}")
            #TODO: recuperare dai metadata gli id per generi, developer, publishers, platforms e game_modes e prendere l'id da MongoDB
            # Normalize names for comparison: remove punctuation, extra spaces, and lowercase
            normalized_game_name = normalize_name(game_name)
            normalized_metadata_name = normalize_name(metadata.get("name", "")) if metadata is not None else ""

            game_doc = {
                "name": metadata.get("name", game_name) if metadata is not None else game_name,
                "psn_game_ID": external_id if platform == "psn" else None,
                "steam_game_ID": external_id if platform == "steam" else None,
                "platforms": metadata.get("platforms", []) if metadata is not None else [],
                "genres": metadata.get("genres", []) if metadata is not None else [],
                "game_modes": metadata.get("game_modes", []) if metadata is not None else [],
                "release_date": metadata.get("release_date") if metadata is not None else None,
                "publisher": metadata.get("publisher") if metadata is not None else None,
                "developer": metadata.get("developer") if metadata is not None else None,
                "description": metadata.get("description") if metadata is not None else None,
                "cover_image": metadata.get("cover_image") if metadata is not None else None,
                "screenshots": metadata.get("screenshots", []) if metadata is not None else [],
                "total_rating": metadata.get("total_rating", 0.0) if metadata is not None else 0.0,
                "total_rating_count": metadata.get("total_rating_count", 0) if metadata is not None else 0,
                "original_name": game_name,
                "normalized_name": normalized_metadata_name if normalized_metadata_name != "" else normalized_game_name,
                "toVerify": True if (external_id is None or (normalized_metadata_name != normalized_game_name)) else False,
            }
            
            igdb_id = metadata.get("igdb_id") if metadata is not None else None
            if igdb_id is not None:
                game_doc["igdb_id"] = igdb_id
            
            games_to_insert.append(game_doc)
            game_id = None
            existing_game_names.add(game_name.lower())  # Add to existing names to avoid duplicates
        else:
            existing_game = db["games"].find_one(
                {
                    "$or": [
                        {"name": game_name},
                        {"original_name": game_name},
                        {"normalized_name": normalize_name(game_name)},
                        {"psn_game_ID": external_id},
                        {"steam_game_ID": external_id},
                    ]
                }
            )
            game_id = existing_game["_id"] if existing_game else None
            exist = db["game_users"].find_one(
                {
                    "game_ID": game_id,
                    "user_id": str(current_user.id),
                    "platform": platform,
                }
            )
            if not exist:
                game_user_to_insert.append(
                    {
                        "game_ID": game_id,
                        "user_id": str(current_user.id),
                        "platform": platform,
                        "num_trophies": game.get("earnedTrophy"),
                        "play_count": game.get("play_count", 0),
                    },
                )
            else:
                game_user_to_update.append(
                    {
                        "game_ID": exist["game_ID"],
                        "user_id": exist["user_id"],
                        "platform": exist["platform"],
                        "num_trophies": game.get("earnedTrophy"),
                        "play_count": game.get("play_count", 0),
                    },
                )
        
        time.sleep(0.5)  # To avoid hitting API rate limits too quickly
        
    if games_to_insert:
        unique_games = []
        seen_igdb_ids = set(g["igdb_id"] for g in db["games"].find({}, {"igdb_id": 1}) if g.get("igdb_id") is not None)
        seen_name_extid = set((g["name"].lower(), g.get("psn_game_ID") or g.get("steam_game_ID")) for g in db["games"].find({}, {"name": 1, "psn_game_ID": 1, "steam_game_ID": 1}))
        
        for game in games_to_insert:
            key = (game["name"].lower(), game.get("psn_game_ID") or game.get("steam_game_ID"))
            if (game.get("igdb_id") is not None and game["igdb_id"] not in seen_igdb_ids) or (game.get("igdb_id") is None and key not in seen_name_extid):
                unique_games.append(game)
                if game.get("igdb_id") is not None:
                    seen_igdb_ids.add(game["igdb_id"])
                seen_name_extid.add(key)
        games_to_insert = unique_games
        
        if games_to_insert != []:
            result = db["games"].insert_many(games_to_insert)
            logging.info(f"Inserted {len(result.inserted_ids)} new games into the database.")

            
        for game_doc in games_to_insert:            
            game_id = db["games"].find_one({"normalized_name": game_doc["normalized_name"]})["_id"]
            exist = db["game_users"].find_one(
                {
                    "game_ID": game_id,
                    "user_id": str(current_user.id),
                    "platform": platform,
                }
            )
            if not exist:
                game_user_to_insert.append(
                    {
                        "game_ID": game_id,
                        "user_id": str(current_user.id),
                        "platform": platform,
                        "num_trophies": game_doc.get("earnedTrophy"),
                        "play_count": game_doc.get("play_count", 0),
                    },
                )
            else:
                game_user_to_update.append(
                    {
                        "game_ID": exist["game_ID"],
                        "user_id": exist["user_id"],
                        "platform": exist["platform"],
                        "num_trophies": game_doc.get("earnedTrophy"),
                        "play_count": game_doc.get("play_count", 0),
                    },
                )

        
        db["game_users"].insert_many(game_user_to_insert)
        logging.info(f"Inserted {len(game_user_to_insert)} games-user linkages into the database.")
        
    # if existing_game_user_to_insert:
    #     db["game_users"].insert_many(existing_game_user_to_insert)
    #     logging.info(f"Inserted {len(existing_game_user_to_insert)} existing games-user linkages into the database.")
        
    if  game_user_to_update != [] and len(game_user_to_update) > 0:
        bulk_updates = []
        for game_user in game_user_to_update:
            bulk_updates.append(
                UpdateOne(
                    {
                        "game_ID": game_user["game_ID"],
                        "user_id": game_user["user_id"],
                        "platform": game_user["platform"],
                    },
                    {
                        "$set": {
                            "num_trophies": game_user["num_trophies"],
                            "play_count": game_user["play_count"],
                        }
                    },
                )
            )
        try:
            db["game_users"].bulk_write(bulk_updates)
            logging.info(f"Updated {len(game_user_to_update)} games-user linkages in the database.")
        except errors as e:
            logging.error(f"Error updating game-user linkages: {e}")
        
    # Optionally update linkage summary fields
    try:
        db["platforms-users"].update_one(
            {"user_id": str(current_user.id), "platform": platform},
            {
                "$set": {
                    "game_count": stats.get("gameCount", 0),
                    "earned_achievements": stats.get("earnedTrophyCount", 0),
                    "play_count": stats.get("totPlayTimeCount", 0),
                    "full_trophies_count": stats.get("completeTrophyCount", 0),
                }
            },
        )
        logging.info(f"Updated platform summary for {platform} for user {current_user.id}")
    except errors.PyMongoError as e:
        logging.error(f"Error updating platform summary for {platform}: {e}")
        
    # return Response(message=f"${platform} data synchronized")
    return {"message": f"{platform} data synchronized"}

#Per alcuni di questi filtri sarebbe l'ideale avere dei dropdown con i valori possibili e con la possibilita' di selezionarne piu' di uno e con la possibilita' di cercarne nel dropdown
@app.get("/games", response_model=list[dict])
def get_all_games(
    db=Depends(get_db),
    name: str = Query(None, description="Filter games by name (case-insensitive)"),
    genres: list[int] = Query(None, description="Filter games by genres (comma-separated)"),
    platforms: list[int] = Query(None, description="Filter games by console (comma-separated)"),
    developer: list[int] = Query(None, description="Filter games by developer"),
    publisher: int = Query(None, description="Filter games by publisher"),
    game_mode: list[int] = Query(None, description="Filter games by game mode (e.g., Single-player, Multiplayer)"),
):
    query = {}
    
    if name:
        query["$or"] = [
            {"name": {"$regex": name, "$options": "i"}},  # Case-insensitive search
            {"original_name": {"$regex": name, "$options": "i"}},  # Search in original game name
        ]

    if genres:
        query["genres"] = {"$in": genres}

    if platforms:
        query["platforms"] = {"$in": platforms}

    if developer:
        query["developer"] = {"$in": developer} if isinstance(developer, list) else developer

    if publisher:
        query["publisher"] = {"$in": publisher} if isinstance(publisher, list) else publisher

    if game_mode:
        query["game_modes"] = {"$in": game_mode}
        
    logging.info(f"Querying games with filters: {query}")
        
    games = list(db["games"].find(query))
    for game in games:
        game["_id"] = str(game["_id"])
        
    return games

@app.get("/companies", response_model=list[dict])
def get_all_companies(
    db=Depends(get_db),
    name: str = Query(None, description="Filter companies by name (case-insensitive)"),
    country: str = Query(None, description="Filter companies by country (e.g., USA, Japan)"),
):
    query = {}
    
    if name:
        query["company_name"] = {"$regex": name, "$options": "i"}
    if country:
        query["country"] = {"$regex": country, "$options": "i"}
        
    companies = list(db["companies"].find(query))
    for company in companies:
        company["_id"] = str(company["_id"])
    return companies

@app.get("/genres", response_model=list[dict])
def get_all_genres(
    db=Depends(get_db),
    name: str = Query(None, description="Filter genres by name (case-insensitive)"),
):
    query = {}

    if name:
        query["genre_name"] = {"$regex": name, "$options": "i"}

    genres = list(db["genres"].find(query))
    for genre in genres:
        genre["_id"] = str(genre["_id"])
    return genres

@app.get("/game_modes", response_model=list[dict])
def get_all_game_modes(
    db=Depends(get_db),
    name: str = Query(None, description="Filter game_modes by name (case-insensitive)"),
):
    query = {}

    if name:
        query["game_mode_name"] = {"$regex": name, "$options": "i"}

    game_modes = list(db["game_modes"].find(query))
    for game_mode in game_modes:
        game_mode["_id"] = str(game_mode["_id"])
    return game_modes


@app.get("/consoles", response_model=list[dict])
def get_all_consoles(
    db=Depends(get_db),
    name: str = Query(None, description="Filter consoles by name (case-insensitive)"),
    generation: int = Query(None, description="Filter consoles by generation (e.g., 8, 16, 32, 64, 128)"),
):
    query = {}

    if name:
        query["$or"] = [
            {"platform_name": {"$regex": name, "$options": "i"}},  # Case-insensitive search
            {
                "abbreviation": {"$regex": name, "$options": "i"}
            },  # Search in original game name
        ]
        
    if generation:
        query["generation"] = generation

    consoles = list(db["console_platforms"].find(query))
    for console in consoles:
        console["_id"] = str(console["_id"])
    return consoles


#TODO: sync metadata
#TODO: retrieve game by ID
#TODO: retrieve games by search term and filters (genere, platform, console,. developer, publisher, game mode)
#TODO: search game metadata by name
#TODO: add to wishlist
#TODO: remove from wishlist
#TODO: force update game metadata
