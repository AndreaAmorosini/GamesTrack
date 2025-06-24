from typing import Union, Annotated
import sys
from fastapi import FastAPI, HTTPException, status, Depends
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
import math


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
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8)
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
                {"user_id": str(current_user.id), "platform": "steam"},
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

#TODO: sync data (PSN, Xbox, Steam)
#Forse fare che i metadata del gioco vengono recuperati man mano quando si apre la pagina di dettaglio del gioco
@app.post("/sync/{platform}")
def sync_user_platform(platform: str, current_user: Annotated[User, Depends(get_current_active_user)], db=Depends(get_db)):
    """Synchronize data for a user on a specified platform."""
    
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
    existing_game_user_to_insert = []
    game_user_to_update = []
    name_to_gameuser_indexes = {}
    
    for game in full_games_dict:
        game_name = game["name"] if game["name"] is not None else game["title_name"]
        external_id = None
        if platform == "steam":
            external_id = game.get("title_id", None)
        elif platform == "psn":
            external_id = game.get("product_id", None)
            
        if game_name.lower() not in existing_game_names and (external_id is not None and external_id not in existing_external_ids):
            #Retrieve metadata for the game
            metadata = igdb_client.get_game_metadata(game_name, external_id=external_id)
            #Skip if no metadata found
            if metadata is None:
                logging.warning(f"No metadata found for game: {game_name} with external ID: {external_id}")
                continue
            #TODO: recuperare dai metadata gli id per generi, developer, publishers, platforms e game_modes e prendere l'id da MongoDB
            games_to_insert.append(
                {
                    "name": metadata.get("name", game_name),
                    "igbd_id": metadata.get("igdb_id"),
                    "psn_game_ID": external_id if platform == "psn" else None,
                    "steam_game_ID": external_id if platform == "steam" else None,
                    "platforms": metadata.get("platforms", []),
                    "genres": metadata.get("genres", []),
                    "game_modes": metadata.get("game_modes", []),
                    "release_date": metadata.get("release_date"),
                    "publisher": metadata.get("publisher"),
                    "developer": metadata.get("developer"),
                    "description": metadata.get("description"),
                    "cover_image": metadata.get("cover_image"),
                    "screenshots": metadata.get("screenshots", []),
                    "total_rating": metadata.get("total_rating", 0.0),
                    "total_rating_count": metadata.get("total_rating_count", 0),
                }
            )
            game_id = None
            existing_game_names.add(game_name.lower())  # Add to existing names to avoid duplicates
        else:
            existing_game = db["games"].find_one(
                {
                    "$or": [
                        {"name": game_name},
                        {"psn_game_ID": external_id},
                        {"steam_game_ID": external_id},
                    ]
                }
            )
            game_id = existing_game["_id"] if existing_game else None
        
        if game_id is not None:
            exist = db["game_users"].find_one(
                {
                    "game_ID": game_id,
                    "user_id": str(current_user.id),
                    "platform": platform,
                }
            )
            if not exist:
                existing_game_user_to_insert.append(
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
        else:
            game_user_to_insert.append(
                {
                    "game_ID": game_id,
                    "user_id": str(current_user.id),
                    "platform": platform,
                    "num_trophies": game.get("earnedTrophy"),
                    "play_count": game.get("play_count", 0),
                }
            )
            name_to_gameuser_indexes[(game_name.lower(), external_id)] = len(game_user_to_insert)

        
        time.sleep(0.5)  # To avoid hitting API rate limits too quickly
        
    if games_to_insert:
        unique_games = []
        seen_igdb_ids = set(g["igbd_id"] for g in db["games"].find({}, {"igbd_id": 1}) if g.get("igbd_id") is not None)
        seen_name_extid = set((g["name"].lower(), g.get("psn_game_ID") or g.get("steam_game_ID")) for g in db["games"].find({}, {"name": 1, "psn_game_ID": 1, "steam_game_ID": 1}))
        
        for game in games_to_insert:
            key = (game["name"].lower(), game.get("psn_game_ID") or game.get("steam_game_ID"))
            if (game.get("igbd_id") is not None and game["igbd_id"] not in seen_igdb_ids) or (game.get("igdb_id") is None and key not in seen_name_extid):
                unique_games.append(game)
                if game.get("igbd_id") is not None:
                    seen_igdb_ids.add(game["igbd_id"])
                seen_name_extid.add(key)
        games_to_insert = unique_games
        
        if games_to_insert != []:
            result = db["games"].insert_many(games_to_insert)
            logging.info(f"Inserted {len(result.inserted_ids)} new games into the database.")
            inserted_ids = result.inserted_ids
            logging.info(f"name_to_gameuser_indexes: {name_to_gameuser_indexes}")
            logging.info(f"games_to_insert: {game_user_to_insert}")
            for game_doc, game_id in zip(games_to_insert, inserted_ids):
                key = (game_doc["name"].lower(), game_doc.get("psn_game_ID") or game_doc.get("steam_game_ID"))
                idx = name_to_gameuser_indexes[key]
                game_user_to_insert[idx]["game_ID"] = game_id
            
        db["game_users"].insert_many(game_user_to_insert)
        logging.info(f"Inserted {len(game_user_to_insert)} games-user linkages into the database.")
        
    if existing_game_user_to_insert:
        db["game_users"].insert_many(existing_game_user_to_insert)
        logging.info(f"Inserted {len(existing_game_user_to_insert)} existing games-user linkages into the database.")
        
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
                            "play_count": game.get("play_count", 0),
                        }
                    },
                )
            )
        db["game_users"].bulk_write(bulk_updates)
        logging.info(f"Updated {len(game_user_to_update)} games-user linkages in the database.")
        
        

    # Optionally update linkage summary fields
    db["platform-users"].update_one(
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
    
    return {"detail": f"${platform} data synchronized"}

#TODO: sync metadata
#TODO: retrieve all games
#TODO: retrieve game by ID
#TODO: retrieve games by platform
#TODO: retrieve games by search term