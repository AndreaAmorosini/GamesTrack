from typing import Union

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from init_db import init_mongo
import os
from pymongo import MongoClient, errors
from utils.security import hash_password
from datetime import datetime
from bson import ObjectId
from utils.psnTrack import sync_psn
from utils.steamTrack import sync_steam


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
    xbox: str | None = None
    xbox_api_key: str | None = None


class Request(BaseModel):
    user_id: str | None = None
    game_id: str | None = None
    game_search_term: str | None = None

app = FastAPI()

test_env = os.getenv("MONGO_INIT_USER"), os.getenv("MONGO_INIT_PASS")
mongo_uri = f"mongodb://{os.getenv('MONGO_INIT_USER')}:{os.getenv('MONGO_INIT_PASS')}@mongo:27017/"
client = MongoClient(mongo_uri)
db = client["game_tracker"]


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
        "is_active": doc.get("is_active", False),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }

#TODO: Login
#TODO: Register
@app.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: User):
    """Register a new user with email, password, and optional platform IDs."""
    user_doc = {
        "username": user.username,
        "email": user.email,
        "password": hash_password(user.password),
    }
    try:
        result = db.users.insert_one(user_doc)
        return {"id": str(result.inserted_id), "email": user.email}
    except errors.DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
#TODO: update user
#Update the user data by ObjectID by adding the platform IDs and API keys ready to retrieve data by external job
@app.patch("/users/{user_id}", response_model=dict)
def update_user(user_id: str, update: User):
    """Update an existing user's data by ObjectId."""
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID"
        )
    update_fields = {}
    if update.email:
        update_fields["email"] = update.email
    if update.password:
        update_fields["password"] = hash_password(update.password)
        
    platforms = {}
    if update.steam is not None:
        platforms["steam"] = update.steam
        db["platforms-users"].insert_one(
            {
                "platform": "steam",
                "user_id": user_id,
                "platform_ID": update.steam,
                "api_key": update.steam_api_key,  # Placeholder for future API key
                "game_count": 0,
                "earned_achievements": 0,
                "play_count": 0,
                "full_trophies_count": 0,
            }
        )
    if update.psn is not None:
        platforms["psn"] = update.psn
        db["platforms-users"].insert_one(
            {
                "platform": "psn",
                "user_id": user_id,
                "platform_ID": update.psn,
                "api_key": update.psn_api_key,  # Placeholder for future API key
                "game_count": 0,
                "earned_achievements": 0,
                "play_count": 0,
                "full_trophies_count": 0,
            }
        )
    if update.xbox is not None:
        platforms["xbox"] = update.xbox
    
    
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
#TODO: sync metadata
#TODO: retrieve all games
#TODO: retrieve game by ID
#TODO: retrieve games by platform
#TODO: retrieve games by search term