import os
import sys
import logging
import string
import time
from datetime import datetime
import re
import traceback

# Aggiungi la directory corrente al Python path per permettere l'importazione dei moduli utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from arq.worker import run_worker
from pymongo import MongoClient, UpdateOne, errors
from utils.psnTrack import sync_psn
from utils.steamTrack import sync_steam
from utils.igdb_api import IGDBAutoAuthClient
from arq.connections import RedisSettings
from bson import ObjectId


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger().setLevel(logging.INFO)

os.makedirs("logs", exist_ok=True)

async def startup(ctx):
    logging.info("Worker starting up...")
    mongo_uri = f"mongodb://{os.environ['MONGO_INIT_USER']}:{os.environ['MONGO_INIT_PASS']}@mongo:27017/"
    ctx["db_client"] = MongoClient(mongo_uri)
    ctx["db"] = ctx["db_client"]["game_tracker"]
    logging.info("MongoDB client initialized.")
    
async def shutdown(ctx):
    logging.info("Worker shutting down...")
    if "db_client" in ctx:
        ctx["db_client"].close()
        logging.info("MongoDB client closed.")
    else:
        logging.warning("No MongoDB client to close.")
    logging.info("Worker shutdown complete.")

#TODO: In caso aggiungere che il logging vada su file e che possa essere letto dal frontend associandolo poi con gli id del job
# TODO: creare una query separata su igdb per i giochi della tre per restringere il margine di errore (forse mettere il filtro per tutte?)
async def sync_job(ctx, user_id, platform, string_job_id):
    print(f"[DEBUG] 1. Function started: {user_id}, {platform}", flush=True)

    try:
        db = ctx["db"]
        job = ctx.get("job")
        job_id = getattr(job, 'job_id', None)
        log_id = string_job_id
        # Crea un file handler specifico per questo job
        logger = logging.getLogger(f"sync_job_{log_id}")
        logger.setLevel(logging.INFO)
        if logger.hasHandlers():
            logger.handlers.clear()  # Clear existing handlers to avoid duplicates
        log_filename = f"logs/worker_sync_{log_id}.log"
        job_file_handler = logging.FileHandler(log_filename)
        job_file_handler.setLevel(logging.INFO)
        job_file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(job_file_handler)
        
        
        logger.info(f"Starting sync for user {user_id} on platform {platform}")
        job_file_handler.flush()

        def normalize_name(name):
            if not name:
                return ""
            name = name.translate(str.maketrans("", "", string.punctuation))
            return " ".join(name.lower().split())

        try:
            try:
                result = db["schedules"].update_one(
                    {"job_string_id": string_job_id, "status": "queued"},
                    {"$set": {"status": "in_progress", "updated_at": datetime.now()}},
                )

            except errors.PyMongoError as e:
                logger.error(f"Error updating schedule for user {user_id} on {platform}: {e}", flush=True)
                job_file_handler.flush()
                return
            
            # Check platform
            if platform not in ["psn", "steam"]:
                db["schedules"].update_one(
                    {"job_string_id": string_job_id},
                    {"$set": {"status": "fail", "error": "Invalid platform", "updated_at": datetime.now()}},
                )
                return

            # Check user
            try:
                user = db.users.find_one({"_id": ObjectId(user_id)})
            except errors as e:
                logger.info(f"Error finding user {user_id}: {e}")
                db["schedules"].update_one(
                    {"job_string_id": string_job_id},
                    {"$set": {"status": "fail", "error": "Database error", "updated_at": datetime.now()}},
                )
                return
            if not user:
                db["schedules"].update_one(
                    {"job_string_id": string_job_id},
                    {"$set": {"status": "fail", "error": "User not found", "updated_at": datetime.now()}},
                )
                return

            # Check platform linkage
            try:
                link = db["platforms-users"].find_one(
                    {"user_id": str(user_id), "platform": platform}
                )
            except errors as e:
                logger.info(f"Error finding platform link for user {user_id} on {platform}: {e}")
                db["schedules"].update_one(
                    {"job_string_id": string_job_id},
                    {"$set": {"status": "fail", "error": "Database error", "updated_at": datetime.now()}},
                )
                return
            if not link:
                logger.info(f"No platform linkage found for user {user_id} on {platform}", flush=True)
                db["schedules"].update_one(
                    {"job_string_id": string_job_id},
                    {"$set": {"status": "fail", "error": "No linkage for platform", "updated_at": datetime.now()}},
                )
                return

            api_key = link.get("api_key")
            if api_key is None:
                db["schedules"].update_one(
                    {"job_string_id": string_job_id},
                    {"$set": {"status": "fail", "error": "No API key", "updated_at": datetime.now()}},
                )
                return

            # Call sync function
            logger.info("Calling Platform API...")
            job_file_handler.flush()
            stats = sync_psn(api_key, logger=logger) if platform == "psn" else sync_steam(api_key, logger=logger)
            
            full_games_dict = stats["fullGames"]
            print(f"[DEBUG] 28. Full games dict: {full_games_dict}", flush=True)

            existing_game_names = set(
                g["name"].lower() for g in db["games"].find({}, {"name": 1})
            )
            existing_external_ids = set()
            if platform == "steam":
                existing_external_ids = set(
                    g["steam_game_id"]
                    for g in db["games"].find({}, {"steam_game_id": 1})
                    if g.get("steam_game_id") is not None
                )
            elif platform == "psn":
                existing_external_ids = set(
                    g["psn_game_id"]
                    for g in db["games"].find({}, {"psn_game_id": 1})
                    if g.get("psn_game_id") is not None
                )

            games_to_insert, games_to_update = [], []
            game_user_to_insert, game_user_to_update = [], []

            igdb_client = IGDBAutoAuthClient(
                client_id=os.getenv("IGDB_CLIENT_ID"),
                client_secret=os.getenv("IGDB_CLIENT_SECRET"),
            )

            for game in full_games_dict:
                game_name = game["name"] if game["name"] is not None else game["title_name"]
                if "™" in game_name or "®" in game_name:
                    game_name = game_name.replace("™", "").replace("®", "").strip()
                pattern = re.compile(r"tro(f|ph)[a-z]*", re.IGNORECASE)
                match = pattern.search(game_name)
                if match:
                    game_name = game_name[: match.start()].strip()
                external_id = None
                if platform == "steam":
                    external_id = int(game["title_id"]) if game.get("title_id") is not None else None
                elif platform == "psn":
                    external_id = int(game["product_id"]) if game.get("product_id") is not None else None
                    
                if game_name.lower() not in existing_game_names and (
                    (external_id is not None and external_id not in existing_external_ids)
                    or external_id is None
                ):
                    if "demo" in game_name.lower() or "beta" in game_name.lower():
                        logger.info(f"Skipping demo/beta game: {game_name}")
                        job_file_handler.flush()
                        continue
                    logger.info(
                        f"Retrieving metadata for game: {game_name} with external ID: {external_id}"
                    )
                    job_file_handler.flush()
                    try:
                        metadata = igdb_client.get_game_metadata(
                            game_name, external_id=external_id
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error retrieving metadata for game: {game_name} with external ID: {external_id}: {e}"
                        )
                        job_file_handler.flush()
                        metadata = None
                        time.sleep(5.0)
                        
                    if metadata is None:
                        logger.warning(
                            f"No metadata found for game: {game_name} with external ID: {external_id}"
                        )
                        job_file_handler.flush()

                    normalized_game_name = normalize_name(game_name)
                    normalized_metadata_name = (
                        normalize_name(metadata.get("name", ""))
                        if metadata is not None
                        else ""
                    )

                    game_doc = {
                        "name": metadata.get("name", game_name)
                        if metadata is not None
                        else game_name,
                        "psn_game_id": external_id if platform == "psn" else None,
                        "steam_game_id": external_id if platform == "steam" else None,
                        "platforms": metadata.get("platforms", [])
                        if metadata is not None
                        else [],
                        "genres": metadata.get("genres", [])
                        if metadata is not None
                        else [],
                        "game_modes": metadata.get("game_modes", [])
                        if metadata is not None
                        else [],
                        "release_date": metadata.get("release_date")
                        if metadata is not None
                        else None,
                        "publisher": metadata.get("publisher")
                        if metadata is not None
                        else None,
                        "developer": metadata.get("developer")
                        if metadata is not None
                        else None,
                        "description": metadata.get("description")
                        if metadata is not None
                        else None,
                        "cover_image": metadata.get("cover_image")
                        if metadata is not None
                        else None,
                        "screenshots": metadata.get("screenshots", [])
                        if metadata is not None
                        else [],
                        "total_rating": metadata.get("total_rating", 0.0)
                        if metadata is not None
                        else 0.0,
                        "total_rating_count": metadata.get("total_rating_count", 0)
                        if metadata is not None
                        else 0,
                        "original_name": game_name,
                        "normalized_name": normalized_metadata_name
                        if normalized_metadata_name != ""
                        else normalized_game_name,
                        "toVerify": True
                        if (
                            external_id is None
                            or (normalized_metadata_name != normalized_game_name)
                        )
                        else False,
                    }
                    igdb_id = metadata.get("igdb_id") if metadata is not None else None
                    if igdb_id is not None:
                        game_doc["igdb_id"] = igdb_id
                    games_to_insert.append(game_doc)
                    game_id = None
                    existing_game_names.add(game_name.lower())
                else:
                    existing_game = db["games"].find_one(
                        {
                            "$or": [
                                {"name": game_name},
                                {"original_name": game_name},
                                {"normalized_name": normalize_name(game_name)},
                                {"psn_game_id": external_id},
                                {"steam_game_id": external_id},
                            ]
                        }
                    )
                    
                    if existing_game:
                        logger.info(f"Game already exists in the database: {game_name}")
                        job_file_handler.flush()

                        if (platform == "steam" and existing_game.get("steam_game_id") is None):
                            existing_game["steam_game_id"] = external_id
                            games_to_update.append(existing_game)
                        elif platform == "psn" and existing_game.get("psn_game_id") is None:
                            existing_game["psn_game_id"] = external_id
                            games_to_update.append(existing_game)
                            
                    game_id = existing_game["_id"] if existing_game else None
                    exist = db["game_user"].find_one(
                        {
                            "game_id": game_id,
                            "user_id": str(user_id),
                            "platform": platform,
                        }
                    )
                    if not exist:
                        print("[DEBUG] 29. Game not found in game_user collection, inserting new entry", flush=True)
                        game_user_to_insert.append(
                            {
                                "game_id": game_id,
                                "user_id": str(user_id),
                                "platform": platform,
                                "num_trophies": game.get("earnedTrophy", 0),
                                "play_count": game.get("play_count", 0),
                            },
                        )
                    else:
                        print("[DEBUG] 29. Game found in game_user collection, updating existing entry", flush=True)
                        game_user_to_update.append(
                            {
                                "game_id": exist["game_id"],
                                "user_id": exist["user_id"],
                                "platform": exist["platform"],
                                "num_trophies": game.get("earnedTrophy", 0),
                                "play_count": game.get("play_count", 0),
                            },
                        )
                time.sleep(1.0)  # API rate limit

            if games_to_insert:
                unique_games = []
                seen_igdb_ids = set(
                    g.get("igdb_id")
                    for g in db["games"].find({}, {"igdb_id": 1})
                    if g.get("igdb_id") is not None
                )
                seen_name_extid = set(
                    (g["name"].lower(), g.get("psn_game_id") or g.get("steam_game_id"))
                    for g in db["games"].find(
                        {}, {"name": 1, "psn_game_id": 1, "steam_game_id": 1}
                    )
                )
                for game in games_to_insert:
                    key = (
                        game["name"].lower(),
                        game.get("psn_game_id") or game.get("steam_game_id"),
                    )
                    if (game.get("igdb_id") is not None and game["igdb_id"] not in seen_igdb_ids) or (game.get("igdb_id") is None and key not in seen_name_extid):
                        unique_games.append(game)
                        if game.get("igdb_id") is not None:
                            seen_igdb_ids.add(game["igdb_id"])
                        seen_name_extid.add(key)
                games_to_insert = unique_games

                if games_to_insert:
                    result = db["games"].insert_many(games_to_insert)
                    logger.info(
                        f"Inserted {len(result.inserted_ids)} new games into the database."
                    )
                    job_file_handler.flush()

                if games_to_update:
                    bulk_updates = []
                    for game in games_to_update:
                        if platform == "steam":
                            bulk_updates.append(
                                UpdateOne(
                                    {"_id": game["_id"]},
                                    {"$set": {"steam_game_id": game["steam_game_id"]}},
                                )
                            )
                        elif platform == "psn":
                            bulk_updates.append(
                                UpdateOne(
                                    {"_id": game["_id"]},
                                    {"$set": {"psn_game_id": game["psn_game_id"]}},
                                )
                            )
                    try:
                        db["games"].bulk_write(bulk_updates)
                        logger.info(f"Updated {len(bulk_updates)} games in the database.")
                        job_file_handler.flush()
                    except errors.BulkWriteError as bwe:
                        print(f"[DEBUG] 29. Bulk write error: {bwe.details}", flush=True)
                        logger.error(f"Bulk write error: {bwe.details}")

                for game_doc in games_to_insert:
                    game_id = db["games"].find_one(
                        {"normalized_name": game_doc["normalized_name"]}
                    )["_id"]
                    print(f"[DEBUG] 29. Game ID: {game_id}, {game_doc['original_name']}, {game_doc['normalized_name']}", flush=True)
                    platform_data = next(
                        (game for game in full_games_dict 
                        if game["name"] == game_doc["original_name"] or 
                        (platform == "psn" and game.get("title_name") == game_doc["original_name"])), 
                        {}
                    )
    
                    if platform_data == {}:
                        # Se non troviamo una corrispondenza diretta, prova con nomi normalizzati
                        platform_data = next(
                            (game for game in full_games_dict 
                            if normalize_name(game.get("name", "")) == game_doc["normalized_name"] or 
                            normalize_name(game.get("title_name", "")) == game_doc["normalized_name"]), 
                            {}
                        )

                    if platform_data == {}:
                        logger.warning(f"No platform data found for game: {game_doc['original_name']}")
                        print(f"[DEBUG] 29. No platform data found for game: {game_doc['original_name']}", flush=True)
                        continue
                        
                    print(f"[DEBUG] 29. Platform data: {platform_data}", flush=True)
                        
                    game_name = (
                        platform_data.get("name")
                        if platform_data.get("name") is not None
                        else platform_data.get("title_name")
                    )
                    if "™" in game_name or "®" in game_name:
                        game_name = game_name.replace("™", "").replace("®", "").strip()
                    pattern = re.compile(r"tro(f|ph)[a-z]*", re.IGNORECASE)
                    match = pattern.search(game_name)
                    if match:
                        game_name = game_name[: match.start()].strip()

                    exist = db["game_user"].find_one(
                        {
                            "game_id": game_id,
                            "user_id": str(user_id),
                            "platform": platform,
                        }
                    )
                    if not exist:
                        game_user_to_insert.append(
                            {
                                "game_id": game_id,
                                "user_id": str(user_id),
                                "platform": platform,
                                "num_trophies": platform_data.get("earnedTrophy", 0),
                                "play_count": platform_data.get("play_count", 0),
                            },
                        )
                    else:
                        game_user_to_update.append(
                            {
                                "game_id": exist["game_id"],
                                "user_id": exist["user_id"],
                                "platform": exist["platform"],
                                "num_trophies": platform_data.get("earnedTrophy", 0),
                                "play_count": platform_data.get("play_count", 0),
                            },
                        )

            # Filtra e deduplica
            print(f"[DEBUG] 29. Game user to insert: {len(game_user_to_insert)}", flush=True)
            game_user_to_insert = [
                g
                for g in game_user_to_insert
                if g.get("num_trophies") is not None
                and g.get("play_count") is not None
                and g.get("game_id") is not None
                and g.get("user_id") is not None
                and g.get("platform") is not None
            ]
            print(f"[DEBUG] 29. Filtered game user to insert: {len(game_user_to_insert)}", flush=True)
            seen_game_user = set()
            unique_game_user_to_insert = []
            for g in game_user_to_insert:
                key = (g["game_id"], g["user_id"], g["platform"])
                if key not in seen_game_user:
                    unique_game_user_to_insert.append(g)
                    seen_game_user.add(key)
            game_user_to_insert = unique_game_user_to_insert
            print(f"[DEBUG] 29. Unique game user to insert: {len(game_user_to_insert)}", flush=True)

            try:
                if game_user_to_insert:
                    db["game_user"].insert_many(game_user_to_insert)
                    logger.info(
                        f"Inserted {len(game_user_to_insert)} games-user linkages into the database."
                    )
                    job_file_handler.flush()
            except errors.BulkWriteError as bwe:
                print(f"[DEBUG] 29. Bulk write error: {bwe.details}", flush=True)
                logger.error(f"Bulk write error: {bwe.details}")
                job_file_handler.flush()

                db["schedules"].update_one(
                    {"job_string_id": string_job_id},
                    {"$set": {"status": "fail", "error": "Bulk Write Error on Games", "updated_at": datetime.now()}},
                )
                return


            if game_user_to_update:
                bulk_updates = []
                for g in game_user_to_update:
                    bulk_updates.append(
                        UpdateOne(
                            {
                                "game_id": g["game_id"],
                                "user_id": g["user_id"],
                                "platform": g["platform"],
                            },
                            {
                                "$set": {
                                    "num_trophies": g["num_trophies"],
                                    "play_count": g["play_count"],
                                }
                            },
                        )
                    )
                try:
                    db["game_user"].bulk_write(bulk_updates)
                    logger.info(
                        f"Updated {len(game_user_to_update)} games-user linkages in the database."
                    )
                    job_file_handler.flush()

                except errors.BulkWriteError as e:
                    print(f"[DEBUG] 29. Error updating game-user linkages: {e}", flush=True)
                    logger.error(f"Error updating game-user linkages: {e}")
                    job_file_handler.flush()

                    db["schedules"].update_one(
                        {"job_string_id": string_job_id},
                        {"$set": {"status": "fail", "error": "Bulk write of game_user failed", "updated_at": datetime.now()}},
                    )
                    return


            # Aggiorna summary
            try:
                db["platforms-users"].update_one(
                    {"user_id": str(user_id), "platform": platform},
                    {
                        "$set": {
                            "game_count": stats.get("gameCount", 0),
                            "earned_achievements": stats.get("earnedTrophyCount", 0),
                            "play_count": stats.get("totPlayTimeCount", 0),
                            "full_trophies_count": stats.get("completeTrophyCount", 0),
                        }
                    },
                )
                logger.info(f"Updated platform summary for {platform} for user {user_id}")
                job_file_handler.flush()
            except errors.PyMongoError as e:
                logger.error(f"Error updating platform summary for {platform}: {e}")
                job_file_handler.flush()

                db["schedules"].update_one(
                    {"job_string_id": string_job_id},
                    {"$set": {"status": "fail", "error": "Failed updating platform summary", "updated_at": datetime.now()}},
                )
                return


            db["schedules"].update_one(
                {"job_string_id": string_job_id}, {"$set": {"status": "success"}}
            )
            logger.info(f"Sync for user {user_id} on {platform} completed successfully.")
            job_file_handler.flush()


        except Exception as e:
            db["schedules"].update_one(
                {"job_string_id": string_job_id},
                {"$set": {"status": "fail", "error": str(e), "updated_at": datetime.now()}},
            )
            logger.error(f"Sync failed for user {user_id} on {platform}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"[DEBUG] 29. Error during sync: {e}", flush=True)
            print(f"[DEBUG] 29. Traceback: {traceback.format_exc()}", flush=True)
            return
        finally:
            logger.removeHandler(job_file_handler)
            job_file_handler.close()
    except Exception as e:
        print(f"[DEBUG] 2. Error in sync_job: {e}", flush=True)
        logging.error(f"Error in sync_job: {e}")
        if "job_file_handler" in locals():
            job_file_handler.close()
        raise e


class WorkerSettings:
    functions = [sync_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn("redis://redis:6379")
    max_jobs = 1
    poll_delay = 0.5
    job_timeout = 300
    max_tries = 2
