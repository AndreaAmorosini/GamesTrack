import os
import logging
import string
import time
from datetime import datetime
import re
from arq.worker import run_worker
from pymongo import MongoClient, UpdateOne, errors
from utils.psnTrack import sync_psn
from utils.steamTrack import sync_steam
from utils.igdb_api import IGDBAutoAuthClient
from arq.connections import RedisSettings
import logging
from bson import ObjectId


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger().setLevel(logging.INFO)

os.makedirs("logs", exist_ok=True)

#TODO: In caso aggiungere che il logging vada su file e che possa essere letto dal frontend associandolo poi con gli id del job
async def sync_job(ctx, user_id, platform):
    job = ctx.get("job")
    job_id = getattr(job, 'job_id', None)
    log_id = job_id if job_id else f"{user_id}_{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
    print(f"[DEBUG] Starting job: {user_id}, {platform}", flush=True)
    mongo_uri = f"mongodb://{os.environ['MONGO_INIT_USER']}:{os.environ['MONGO_INIT_PASS']}@mongo:27017/"
    client = MongoClient(mongo_uri)
    db = client["game_tracker"]

    def normalize_name(name):
        if not name:
            return ""
        name = name.translate(str.maketrans("", "", string.punctuation))
        return " ".join(name.lower().split())

    try:
        # Check platform
        if platform not in ["psn", "steam"]:
            db["schedules"].update_one(
                {"user_ID": user_id, "platform": platform},
                {"$set": {"status": "fail", "error": "Invalid platform"}},
            )
            return

        # Check user
        try:
            user = db.users.find_one({"_id": ObjectId(user_id)})
        except errors as e:
            logger.info(f"Error finding user {user_id}: {e}")
            db["schedules"].update_one(
                {"user_ID": user_id, "platform": platform},
                {"$set": {"status": "fail", "error": "Database error"}},
            )
            return
        if not user:
            db["schedules"].update_one(
                {"user_ID": user_id, "platform": platform},
                {"$set": {"status": "fail", "error": "User not found"}},
            )
            return

        # Check platform linkage
        try:
            link = db["platforms-users"].find_one(
                {"user_ID": str(user_id), "platform": platform}
            )
        except errors as e:
            logger.info(f"Error finding platform link for user {user_id} on {platform}: {e}")
            db["schedules"].update_one(
                {"user_ID": user_id, "platform": platform},
                {"$set": {"status": "fail", "error": "Database error"}},
            )
            return
        if not link:
            db["schedules"].update_one(
                {"user_ID": user_id, "platform": platform},
                {"$set": {"status": "fail", "error": "No linkage for platform"}},
            )
            return

        api_key = link.get("api_key")
        if api_key is None:
            db["schedules"].update_one(
                {"user_ID": user_id, "platform": platform},
                {"$set": {"status": "fail", "error": "No API key"}},
            )
            return

        # Call sync function
        logger.info("Calling Steam API...")
        stats = sync_psn(api_key, logger=logger) if platform == "psn" else sync_steam(api_key, logger=logger)
        full_games_dict = stats["fullGames"]

        existing_game_names = set(
            g["name"].lower() for g in db["games"].find({}, {"name": 1})
        )
        existing_external_ids = set()
        if platform == "steam":
            existing_external_ids = set(
                g["steam_game_ID"]
                for g in db["games"].find({}, {"steam_game_ID": 1})
                if g.get("steam_game_ID") is not None
            )
        elif platform == "psn":
            existing_external_ids = set(
                g["psn_game_ID"]
                for g in db["games"].find({}, {"psn_game_ID": 1})
                if g.get("psn_game_ID") is not None
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
                external_id = game.get("title_id", None)
            elif platform == "psn":
                external_id = game.get("product_id", None)

            if game_name.lower() not in existing_game_names and (
                (external_id is not None and external_id not in existing_external_ids)
                or external_id is None
            ):
                if "demo" in game_name.lower() or "beta" in game_name.lower():
                    logger.info(f"Skipping demo/beta game: {game_name}")
                    continue
                logger.info(
                    f"Retrieving metadata for game: {game_name} with external ID: {external_id}"
                )
                metadata = igdb_client.get_game_metadata(
                    game_name, external_id=external_id
                )
                if metadata is None:
                    logger.warning(
                        f"No metadata found for game: {game_name} with external ID: {external_id}"
                    )
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
                    "psn_game_ID": external_id if platform == "psn" else None,
                    "steam_game_ID": external_id if platform == "steam" else None,
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
                            {"psn_game_ID": external_id},
                            {"steam_game_ID": external_id},
                        ]
                    }
                )
                
                if existing_game:
                    logger.info(f"Game already exists in the database: {game_name}")
                    if (platform == "steam" and existing_game.get("steam_game_ID") is None):
                        existing_game["steam_game_ID"] = external_id
                        games_to_update.append(existing_game)
                    elif platform == "psn" and existing_game.get("psn_game_ID") is None:
                        existing_game["psn_game_ID"] = external_id
                        games_to_update.append(existing_game)
                        
                game_id = existing_game["_id"] if existing_game else None
                exist = db["game_user"].find_one(
                    {
                        "game_ID": game_id,
                        "user_ID": str(user_id),
                        "platform": platform,
                    }
                )
                if not exist:
                    game_user_to_insert.append(
                        {
                            "game_ID": game_id,
                            "user_ID": str(user_id),
                            "platform": platform,
                            "num_trophies": game.get("earnedTrophy", 0),
                            "play_count": game.get("play_count", 0),
                        },
                    )
                else:
                    game_user_to_update.append(
                        {
                            "game_ID": exist["game_ID"],
                            "user_ID": exist["user_ID"],
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
                (g["name"].lower(), g.get("psn_game_ID") or g.get("steam_game_ID"))
                for g in db["games"].find(
                    {}, {"name": 1, "psn_game_ID": 1, "steam_game_ID": 1}
                )
            )
            for game in games_to_insert:
                key = (
                    game["name"].lower(),
                    game.get("psn_game_ID") or game.get("steam_game_ID"),
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

            if games_to_update:
                bulk_updates = []
                for game in games_to_update:
                    if platform == "steam":
                        bulk_updates.append(
                            UpdateOne(
                                {"_id": game["_id"]},
                                {"$set": {"steam_game_ID": game["steam_game_ID"]}},
                            )
                        )
                    elif platform == "psn":
                        bulk_updates.append(
                            UpdateOne(
                                {"_id": game["_id"]},
                                {"$set": {"psn_game_ID": game["psn_game_ID"]}},
                            )
                        )
                try:
                    db["games"].bulk_write(bulk_updates)
                    logger.info(f"Updated {len(bulk_updates)} games in the database.")
                except errors.BulkWriteError as bwe:
                    logger.error(f"Bulk write error: {bwe.details}")

            for game_doc in games_to_insert:
                game_id = db["games"].find_one(
                    {"normalized_name": game_doc["normalized_name"]}
                )["_id"]
                exist = db["game_user"].find_one(
                    {
                        "game_ID": game_id,
                        "user_ID": str(user_id),
                        "platform": platform,
                    }
                )
                if not exist:
                    game_user_to_insert.append(
                        {
                            "game_ID": game_id,
                            "user_ID": str(user_id),
                            "platform": platform,
                            "num_trophies": game_doc.get("earnedTrophy", 0),
                            "play_count": game_doc.get("play_count", 0),
                        },
                    )
                else:
                    game_user_to_update.append(
                        {
                            "game_ID": exist["game_ID"],
                            "user_ID": exist["user_id"],
                            "platform": exist["platform"],
                            "num_trophies": game_doc.get("earnedTrophy", 0),
                            "play_count": game_doc.get("play_count", 0),
                        },
                    )

            # Filtra e deduplica
            game_user_to_insert = [
                g
                for g in game_user_to_insert
                if g.get("num_trophies") is not None
                and g.get("play_count") is not None
                and g.get("game_ID") is not None
                and g.get("user_ID") is not None
                and g.get("platform") is not None
            ]
            seen_game_user = set()
            unique_game_user_to_insert = []
            for g in game_user_to_insert:
                key = (g["game_ID"], g["user_ID"], g["platform"])
                if key not in seen_game_user:
                    unique_game_user_to_insert.append(g)
                    seen_game_user.add(key)
            game_user_to_insert = unique_game_user_to_insert

            try:
                if game_user_to_insert:
                    db["game_user"].insert_many(game_user_to_insert)
                    logger.info(
                        f"Inserted {len(game_user_to_insert)} games-user linkages into the database."
                    )
            except errors.BulkWriteError as bwe:
                logger.error(f"Bulk write error: {bwe.details}")

        if game_user_to_update:
            bulk_updates = []
            for g in game_user_to_update:
                bulk_updates.append(
                    UpdateOne(
                        {
                            "game_ID": g["game_ID"],
                            "user_ID": g["user_ID"],
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
            except errors.BulkWriteError as e:
                logger.error(f"Error updating game-user linkages: {e}")

        # Aggiorna summary
        try:
            db["platforms-users"].update_one(
                {"user_ID": str(user_id), "platform": platform},
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

        db["schedules"].update_one(
            {"user_ID": user_id, "platform": platform}, {"$set": {"status": "success"}}
        )
        logger.info(f"Sync for user {user_id} on {platform} completed successfully.")

    except Exception as e:
        db["schedules"].update_one(
            {"user_ID": user_id, "platform": platform},
            {"$set": {"status": "fail", "error": str(e)}},
        )
        logger.error(f"Sync failed for user {user_id} on {platform}: {e}")
    finally:
        logger.removeHandler(job_file_handler)
        job_file_handler.close()


class WorkerSettings:
    functions = [sync_job]
    redis_settings = RedisSettings.from_dsn("redis://redis:6379")
    # max_jobs = 1
    # poll_delay = 0.5
    # job_timeout = 4800
    # max_tries = 2


if __name__ == "__main__":
    logging.info("Starting worker...")
    run_worker(WorkerSettings)
