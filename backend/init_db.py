# app/init_db.py
from pymongo import MongoClient, ASCENDING
import os
from pymongo.errors import ServerSelectionTimeoutError
import time
from utils.igdb_api import IGDBAutoAuthClient
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def init_mongo():
    uri = f"mongodb://{os.environ['MONGO_INIT_USER']}:{os.environ['MONGO_INIT_PASS']}@mongo:27017/"
    max_retries = 20
    delay = 3
    
    logging.info(f"Initializing IGDB client with client ID {os.environ['IGDB_CLIENT_ID']} and client secret {os.environ['IGDB_CLIENT_SECRET']}")
    igdb_client = IGDBAutoAuthClient(
        client_id=os.environ["IGDB_CLIENT_ID"],
        client_secret=os.environ["IGDB_CLIENT_SECRET"]
    )
    
    
    for attempt in range(1, max_retries + 1):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            db = client["game_tracker"]
            db.command("ping")  # test connection
            logging.info("Creating Users collection")
            existing = db.list_collection_names()
            logging.info(f"Existing collections: {existing}")
            if "users" not in existing:
                db.create_collection("users")
                db["users"].create_index("email", unique=True)
                db["users"].create_index("username", unique=True)
            
                result = db["users"].insert_one(
                    {
                        "username": "test_user",
                        "password": "test_password",
                        "email": "test@example.com",
                    }
                )
            
                user_id = str(result.inserted_id)
            
            #Check which info on genres, platforms, publishers and developers can be retrieved from igdb
            logging.info("Creating Platforms")
            if "platforms" not in existing:
                db.create_collection("platforms")
                db["platforms"].create_index("platform_name", unique=True)
                
                resultPlat = db.platforms.insert_many(
                    [
                        {
                            "platform_name": "steam",
                            "logo_image": "https://www.citypng.com/public/uploads/preview/steam-round-logo-icon-download-png-701751694966032dl6elakl5o.png",
                        },
                        {
                            "platform_name": "psn",
                            "logo_image": "https://icon2.cleanpng.com/lnd/20241222/is/174b213741c74c8d4a12a73ff2169c.webp",
                        },
                        {
                            "platform_name": "xbox",
                            "logo_image": "https://img.favpng.com/7/6/15/xbox-360-controller-logo-png-favpng-Y7Ebihg6jcr1YmCD6fYByX048.jpg",
                        },
                    ]
                )
            
                platIdTest = resultPlat.inserted_ids  # Store the inserted IDs if needed
            
            
            if "console_platforms" not in existing:
                db.create_collection("console_platforms")
                db["console_platforms"].create_index("igdb_id", unique=True)
                
                console_platforms_remote = igdb_client.get_all_game_platforms()
                logging.info(f"Found {len(console_platforms_remote)} console platforms from IGDB")
                resultConsole = db.console_platforms.insert_many(console_platforms_remote)
                consolePlatIdTest = resultConsole.inserted_ids  # Store the inserted IDs if needed
            
            
            if "genres" not in existing:
                db.create_collection("genres")
                db["genres"].create_index("igdb_id", unique=True)
                
                genres_remote = igdb_client.get_all_game_genres()
                logging.info(f"Found {len(genres_remote)} genres from IGDB")
                resultGenres = db.genres.insert_many(genres_remote)
                genresIdTest = resultGenres.inserted_ids  # Store the inserted IDs if needed
                
                
            if "companies" not in existing:
                db.create_collection("companies")
                db["companies"].create_index("igdb_id", unique=True)
                
                companies_remote = igdb_client.get_all_game_companies()
                logging.info(f"Found {len(companies_remote)} companies from IGDB")
                resultPub = db.companies.insert_many(companies_remote)
                compIdTest = resultPub.inserted_ids  # Store the inserted IDs if needed       
            
            
            if "game_modes" not in existing:
                db.create_collection("game_modes")
                db["game_modes"].create_index("igdb_id", unique=True)
                
                game_modes_remote = igdb_client.get_all_game_modes()
                logging.info(f"Found {len(game_modes_remote)} game modes from IGDB")
                resultModes = db.game_modes.insert_many(game_modes_remote)
                gameModesId = resultModes.inserted_ids  # Store the inserted IDs if needed    
            
              
            
            if "platforms-users" not in existing:
                db.create_collection("platforms-users")
                db["platforms-users"].create_index([("platform", ASCENDING), ("user_id", ASCENDING)], unique=True)
                
                db["platforms-users"].insert_one(
                    {
                        "platform": platIdTest[0], #steam, psn, xbox
                        "user_id": user_id,
                        "platform_ID": "steam_id",
                        "api_key": "steam_api_key",
                        "game_count": 10, # total games played on this platform
                        "earned_achievements": 5, # total achievements earned
                        "play_count": 10, # total play count
                        "full_trophies_count": 0, # total full trophies count
                    }
                )
                
                db["platforms-users"].insert_one(
                    {
                        "platform": platIdTest[1], #steam, psn, xbox
                        "user_id": user_id,
                        "platform_ID": "psn_id",
                        "api_key": "psn_api_key",
                        "game_count": 20, # total games played on this platform
                        "earned_achievements": 55, # total achievements earned
                        "play_count": 10, # total play count
                        "full_trophies_count": 1, # total full trophies count
                    }
                )


            if "games" not in existing:
                db.create_collection("games")
                db["games"].create_index("igbd_id", unique=True)
                
                db["games"].insert_one(
                    {
                        "igdb_id": "test_gameDB_ID",
                        "psn_game_ID": "test_psn_game_ID",
                        "xbox_game_ID": "test_xbox_game_ID",
                        "steam_game_ID": "test_steam_game_ID",
                        "name": "Test Game",
                        "platforms": [platIdTest[0], platIdTest[1]],  # List of platform IDs
                        "genres": [genresIdTest[0], genresIdTest[1]],  # List of genre IDs
                        "game_modes": [gameModesId[0], gameModesId[1]],  # List of game mode IDs
                        "release_date": "2023-01-01",
                        "publisher": compIdTest[0],  # Test Publisher
                        "developer": compIdTest[1],  # Test Developer
                        "description": "This is a test game description.",
                        "cover_image": "https://example.com/test_game_cover.jpg",
                        "screenshots": [
                            "https://example.com/test_game_screenshot1.jpg",
                            "https://example.com/test_game_screenshot2.jpg",
                        ],
                        "total_rating": 90.8,
                        "total_rating_count": 1000,
                    }
                )

            if "games_user" not in existing:
                db.create_collection("games_user")
                db["games_user"].create_index([("game_ID", ASCENDING), ("user_id", ASCENDING)], unique=True)

                db["games_user"].insert_one(
                    {
                        "game_ID": "test_game_ID",
                        "user_ID": user_id,
                        "platform": platIdTest[0],  # steam
                        "num_trophies": 3,
                        "play_count" : 10,
                    }
                )

            if "schedules" not in existing:
                db.create_collection("schedules")

            # your init logic here...
            logging.info("MongoDB connected and initialized.")
            client.close()
            return
        except ServerSelectionTimeoutError:
            logging.error(f"Mongo not ready, retrying ({attempt + 1}/10)...")
            time.sleep(delay)
    raise Exception("Failed to connect to MongoDB after several attempts")