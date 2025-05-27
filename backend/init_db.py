# app/init_db.py
from pymongo import MongoClient, ASCENDING
import os
from pymongo.errors import ServerSelectionTimeoutError
import time

def init_mongo():
    uri = f"mongodb://{os.environ['MONGO_INIT_USER']}:{os.environ['MONGO_INIT_PASS']}@mongo:27017/"
    max_retries = 20
    delay = 3
    
    for attempt in range(1, max_retries + 1):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            db = client["game_tracker"]
            db.command("ping")  # test connection
            
            existing = db.list_collection_names()
            if "users" not in existing:
                db.create_collection("users")
                db["users"].create_index("email", unique=True)
            
            db["users"].insert_one(
                {
                    "username": "test_user",
                    "password": "test_password",
                    "email": "test@example.com",
                    "platforms": {
                        "steam": "steam_id",
                        "psn": "psn_id",
                        "xbox": "xbox_id",
                    },
                    "api_keys": {
                        "steam": "steam_api_key",
                        "psn": "psn_api_key",
                        "xbox": "xbox_api_key",
                    },
                }
            )

            if "games" not in existing:
                db.create_collection("games")
                db["games"].create_index("game_ID", unique=True)
                
            db["games"].insert_one(
                {
                    "game_ID": "test_game_ID",
                    "name": "Test Game",
                    "platforms": ["steam", "psn", "xbox"],
                    "genres": ["Action", "Adventure"],
                    "release_date": "2023-01-01",
                }
            )

            if "games_user" not in existing:
                db.create_collection("games_user")
                db["games_user"].create_index([("game_ID", ASCENDING), ("user_id", ASCENDING)], unique=True)

            db["games_user"].insert_one(
                {
                    "game_ID": "test_game_ID",
                    "user_ID": "Test Game",
                    "platforms": ["steam", "psn", "xbox"],
                    "num_trophies_psn": "3",
                    "num_achievements_steam": "5",
                    "num_achievements_xbox": "0",
                }
            )

            if "metadata" not in existing:
                db.create_collection("metadata")
                db["metadata"].create_index("gameDB_ID", unique=True)
                
            db["metadata"].insert_one(
                {
                    "gameDB_ID": "test_gameDB_ID",
                    "name": "Test GameDB",
                    "platforms": ["steam", "psn", "xbox"],
                    "genres": ["Action", "Adventure"],
                    "release_date": "2023-01-01",
                    "game_ID": "test_game_ID",
                }
            )

            if "schedules" not in existing:
                db.create_collection("schedules")

            # your init logic here...
            print("MongoDB connected and initialized.")
            return
        except ServerSelectionTimeoutError:
            print(f"Mongo not ready, retrying ({attempt + 1}/10)...")
            time.sleep(delay)
    raise Exception("Failed to connect to MongoDB after several attempts")