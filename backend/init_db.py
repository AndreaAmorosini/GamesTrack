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
                db["users"].create_index("username", unique=True)
            
            db["users"].insert_one(
                {
                    "username": "test_user",
                    "password": "test_password",
                    "email": "test@example.com",
                    "metadata_api_key": "test_api_key",  # API key for metadata service
                }
            )
            
            if "platforms-users" not in existing:
                db.create_collection("platforms-users")
                db["platforms-users"].create_index([("platform", ASCENDING), ("user_id", ASCENDING)], unique=True)
                
            db["platforms-users"].insert_one(
                {
                    "platform": "steam", #steam, psn, xbox
                    "user_id": "test_user",
                    "platform_ID": "steam_id",
                    "api_key": "steam_api_key",
                    "game_count": 0, # total games played on this platform
                    "earned_achievements": 5, # total achievements earned
                    "play_count": 10, # total play count
                    "full_trophies_count": 1, # total full trophies count
                }
            )

            if "games" not in existing:
                db.create_collection("games")
                db["games"].create_index("game_ID", unique=True)
                
            db["games"].insert_one(
                {
                    "game_ID": "test_game_ID",
                    "gameDB_ID": "test_gameDB_ID",
                    "psn_game_ID": "test_psn_game_ID",
                    "xbox_game_ID": "test_xbox_game_ID",
                    "steam_game_ID": "test_steam_game_ID",
                    "name": "Test Game",
                    "platforms": ["steam", "psn", "xbox"],
                    "genres": ["Action", "Adventure"],
                    "game_modes": ["Single-player", "Multiplayer"],
                    "release_date": "2023-01-01",
                    "publisher": "Test Publisher",
                    "developer": "Test Developer",
                    "description": "This is a test game description.",
                    "cover_image": "https://example.com/test_game_cover.jpg",
                    "screenshots": [
                        "https://example.com/test_game_screenshot1.jpg",
                        "https://example.com/test_game_screenshot2.jpg"
                    ],
                    "total_rating" : 90.8,
                    "total_rating_count" : 1000,
                }
            )

            if "games_user" not in existing:
                db.create_collection("games_user")
                db["games_user"].create_index([("game_ID", ASCENDING), ("user_id", ASCENDING)], unique=True)

            db["games_user"].insert_one(
                {
                    "game_ID": "test_game_ID",
                    "user_ID": "Test Game",
                    "platform": "steam",
                    "num_trophies": 3,
                    "play_count" : 10,
                }
            )


            if "schedules" not in existing:
                db.create_collection("schedules")

            # your init logic here...
            print("MongoDB connected and initialized.")
            client.close()
            return
        except ServerSelectionTimeoutError:
            print(f"Mongo not ready, retrying ({attempt + 1}/10)...")
            time.sleep(delay)
    raise Exception("Failed to connect to MongoDB after several attempts")