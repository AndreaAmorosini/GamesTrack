from typing import Union, Annotated
import sys
from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from init_db import init_mongo
import os
from pymongo import MongoClient, errors
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
    metadata_api_key = user.get("metadata_api_key")
    if not metadata_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metadata API key is required for synchronization",
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
    for game in full_games_dict:
        # Check if game already exists in the database
        external_id = None
        if platform == "steam":
            existing_game = db["games"].find_one({"name": game["name"]})
            external_id = game.get("title_id", None)
        elif platform == "psn":
            existing_game = db["games"].find_one({"name": game["name"] if game["name"] is not None else game["title_name"]})
            external_id = game.get("product_id", None)
        if not existing_game:
            #Retrieve metadata for the game
            if platform == "steam":
                metadata = igdb_client.get_game_metadata(game["name"], external_id=external_id)
            elif platform == "psn":
                metadata = igdb_client.get_game_metadata(game["name"] if game["name"] is not None else game["title_name"], external_id=external_id)
            #TODO: Da rivedere assegnazione dei campi
            result = db["games"].insert_one(
                {
                    "game_ID": game["titleId"],
                    "name": metadata.get("name", game["name"] if game["name"] is not None else game["title_name"]),
                    "gameDB_ID": metadata.get("id"),
                    "psn_game_ID": metadata.get("psn_id"),
                    "steam_game_ID": metadata.get("steam_id"),
                    "platforms": metadata.get("platforms", []),
                    "genres": metadata.get("genres", []),
                    "game_modes": metadata.get("game_modes", []),
                    "release_date": metadata.get("release_date"),
                    "publisher": metadata.get("publishers"),
                    "developer": metadata.get("developers"),
                    "description": metadata.get("description"),
                    "cover_image": metadata.get("cover_image"),
                    "screenshots": metadata.get("screenshots", []),
                    "total_rating": metadata.get("total_rating", 0.0),
                    "total_rating_count": metadata.get("total_rating_count", 0),
                }
            )
            game_id = result.inserted_id
        else:
            game_id = existing_game["_id"]
        
        db["games_user"].insert_one(
            {
                "game_ID": game_id,
                "user_id": str(current_user.id),
                "platform": platform,
                "num_trophies": game.get("earnedTrophy"),
                "play_count": game.get("play_duration"),
            },
        )

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