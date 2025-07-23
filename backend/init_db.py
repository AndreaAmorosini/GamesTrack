# app/init_db.py
from pymongo import MongoClient, ASCENDING
import os
from pymongo.errors import ServerSelectionTimeoutError
import time
from utils.igdb_api import IGDBAutoAuthClient
import logging
import datetime


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
            else:
                users_remote = db["users"]
                user_id = users_remote.find_one({"username": "test_user"})["_id"]
            
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
            else:
                platforms_remote = db["platforms"]
                platIdTest = platforms_remote.find_one()["_id"]
            
            
            if "console_platforms" not in existing:
                db.create_collection("console_platforms")
                db["console_platforms"].create_index("igdb_id", unique=True)
                
                console_platforms_remote = igdb_client.get_all_game_platforms()
                logging.info(f"Found {len(console_platforms_remote)} console platforms from IGDB")
                resultConsole = db.console_platforms.insert_many(console_platforms_remote)
                consolePlatIdTest = resultConsole.inserted_ids  # Store the inserted IDs if needed
            else:
                console_plat_remote = db["console_platforms"]
                if console_plat_remote.count_documents({}) == 0:
                    console_platforms_remote = igdb_client.get_all_game_platforms()
                    logging.info(f"Found {len(console_platforms_remote)} console platforms from IGDB")
                    resultConsole = db.console_platforms.insert_many(console_platforms_remote)
                    consolePlatIdTest = resultConsole.inserted_ids
            
            
            if "genres" not in existing:
                db.create_collection("genres")
                db["genres"].create_index("igdb_id", unique=True)
                
                genres_remote = igdb_client.get_all_game_genres()
                logging.info(f"Found {len(genres_remote)} genres from IGDB")
                resultGenres = db.genres.insert_many(genres_remote)
                genresIdTest = resultGenres.inserted_ids  # Store the inserted IDs if needed
            else:
                genres_remote = db["genres"]
                if genres_remote.count_documents({}) == 0:
                    genres_remote = igdb_client.get_all_game_genres()
                    logging.info(f"Found {len(genres_remote)} genres from IGDB")
                    resultGenres = db.genres.insert_many(genres_remote)
                    genresIdTest = resultGenres.inserted_ids
                
                
            if "companies" not in existing:
                db.create_collection("companies")
                db["companies"].create_index("igdb_id", unique=True)
                
                companies_remote = igdb_client.get_all_game_companies()
                logging.info(f"Found {len(companies_remote)} companies from IGDB")
                resultPub = db.companies.insert_many(companies_remote)
                compIdTest = resultPub.inserted_ids  # Store the inserted IDs if needed
            else:
                companies_remote = db["companies"]
                if companies_remote.count_documents({}) == 0:
                    companies_remote = igdb_client.get_all_game_companies()
                    logging.info(f"Found {len(companies_remote)} companies from IGDB")
                    resultPub = db.companies.insert_many(companies_remote)
                    compIdTest = resultPub.inserted_ids       
            
            
            if "game_modes" not in existing:
                db.create_collection("game_modes")
                db["game_modes"].create_index("igdb_id", unique=True)
                
                game_modes_remote = igdb_client.get_all_game_modes()
                logging.info(f"Found {len(game_modes_remote)} game modes from IGDB")
                resultModes = db.game_modes.insert_many(game_modes_remote)
                gameModesId = resultModes.inserted_ids  # Store the inserted IDs if needed
            else:
                game_modes_remote = db["game_modes"]
                if game_modes_remote.count_documents({}) == 0:
                    game_modes_remote = igdb_client.get_all_game_modes()
                    logging.info(f"Found {len(game_modes_remote)} game modes from IGDB")
                    resultModes = db.game_modes.insert_many(game_modes_remote)
                    gameModesId = resultModes.inserted_ids    
            
              
            
            if "platforms-users" not in existing:
                db.create_collection("platforms-users")
                db["platforms-users"].create_index([("platform", ASCENDING), ("user_id", ASCENDING)], unique=True)
                
                db["platforms-users"].insert_one(
                    {
                        "platform": "steam", #steam, psn, xbox
                        "user_id": user_id,
                        "platform_id": "steam_id",
                        "api_key": "steam_api_key",
                        # "game_count": 10, # total games played on this platform
                        # "earned_achievements": 5, # total achievements earned
                        # "play_count": 10, # total play count
                        "full_trophies_count": 0, # total full trophies count
                    }
                )
                
                db["platforms-users"].insert_one(
                    {
                        "platform": "psn", #steam, psn, xbox
                        "user_id": user_id,
                        "platform_id": "psn_id",
                        "api_key": "psn_api_key",
                        # "game_count": 20, # total games played on this platform
                        # "earned_achievements": 55, # total achievements earned
                        # "play_count": 10, # total play count
                        "full_trophies_count": 1, # total full trophies count
                    }
                )


            if "games" not in existing:
                db.create_collection("games")
                db["games"].create_index(
                    [("igdb_id", 1)],
                    unique=True,
                    partialFilterExpression={"igdb_id": {"$exists": True}},
                )
                
                db["games"].insert_one(
                    {
                        "igdb_id": 305152,
                        "psn_game_id": 10008503,
                        "steam_game_id": None,
                        "name": "Clair Obscur: Expedition 33",
                        "platforms": [169, 6],  # List of platform IDs
                        "genres": [12, 16],  # List of genre IDs
                        "game_modes": [1, 2],  # List of game mode IDs
                        "release_date": 1745452800,
                        "publisher": 37893,  # Test Publisher
                        "developer": 55283,  # Test Developer
                        "description": "Lead the members of Expedition 33 on their quest to destroy the Paintress so that she can never paint death again. Explore a world of wonders inspired by Belle Époque France and battle unique enemies in this turn-based RPG with real-time mechanics.",
                        "cover_image": "//images.igdb.com/igdb/image/upload/t_thumb/co9gam.jpg",
                        "screenshots": [
                            "//images.igdb.com/igdb/image/upload/t_thumb/scsodz.jpg",
                            "//images.igdb.com/igdb/image/upload/t_thumb/scsoe8.jpg",
                        ],
                        "total_rating": 90.33744655818265,
                        "total_rating_count": 243,
                        "original_name": "Clair Obscur: Expedition 33",
                        "toVerify": False,  # Indicates if the game needs verification
                    }
                )

            if "game_user" not in existing:
                db.create_collection("game_user")
                db["game_user"].create_index(
                    [("game_id", ASCENDING), ("user_id", ASCENDING), ("platform", ASCENDING)], unique=True
                )

                db["game_user"].insert_one(
                    {
                        "game_id": "test_game_id",
                        "user_id": user_id,
                        "platform": "steam",  # steam
                        "num_trophies": 3,
                        "play_count": 10,
                    }
                )
            
            if "game_user_wishlist" not in existing:
                db.create_collection("game_user_wishlist")
                db["game_user_wishlist"].create_index(
                    [("game_id", ASCENDING), ("user_id", ASCENDING), ("platform", ASCENDING)], unique=True
                )

                db["game_user_wishlist"].insert_one(
                    {
                        "game_id": "test_game_id",
                        "user_id": user_id,
                        "platform": "steam",
                    }
                )

            if "schedules" not in existing:
                db.create_collection("schedules")
                db["schedules"].create_index(
                    [("user_id", ASCENDING), ("platform", ASCENDING)],
                )
                
                db["schedules"].insert_one(
                    {
                        "job_id": "test_job_id",
                        "job_string_id": "test_job_string_id",
                        "user_id": user_id,
                        "platform": "steam",
                        "status": "success",  # pending, running, completed, failed
                        "created_at": datetime.datetime(2025, 7, 4, 16, 19, 57, 898000),
                        "updated_at": datetime.datetime(2025, 7, 4, 16, 19, 57, 898000),
                        "error": None,
                        "game_inserted": 10,  # Number of games inserted
                        "game_updated": 5,  # Number of games updated
                        "game_user_inserted": 3,  # Number of games associated
                        "game_user_updated": 2,  # Number of game-user associations updated
                    }
                )

            # your init logic here...
            logging.info("MongoDB connected and initialized.")
            client.close()
            return
        except ServerSelectionTimeoutError:
            logging.error(f"Mongo not ready, retrying ({attempt + 1}/10)...")
            time.sleep(delay)
    raise Exception("Failed to connect to MongoDB after several attempts")