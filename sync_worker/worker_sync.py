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

from pymongo import MongoClient, UpdateOne, errors
from .utils.psnTrack import sync_psn                # FIX LUIGI
from .utils.steamTrack import sync_steam            # FIX LUIGI
from .utils.retroTrack import sync_retroachievements
from .utils.gogTrack import sync_gog
from .utils.notify import send_notification
from .utils.priceTrack import collect_prices_for_game, create_robust_session as create_price_session
from utils.igdb_api import IGDBAutoAuthClient
from utils.crypto import decrypt_value as decrypt_credential
from arq.connections import RedisSettings
from arq.cron import cron
from bson import ObjectId


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logging.getLogger().setLevel(logging.INFO)

os.makedirs("logs", exist_ok=True)


class MongoLogHandler(logging.Handler):
    """Salva i record di log del job nella collection sync_logs su MongoDB,
    per la visualizzazione dalla web UI (SyncJobs -> Visualizza log)."""
    def __init__(self, db, job_string_id):
        super().__init__()
        self.db = db
        self.job_string_id = job_string_id

    def emit(self, record):
        try:
            self.db["sync_logs"].insert_one({
                "job_string_id": self.job_string_id,
                "level": record.levelname,
                "message": self.format(record),
                "timestamp": datetime.now(),
            })
        except Exception:
            pass  # un errore di logging non deve mai far crashare il job

    def trim(self, max_records=1000):
        """Mantiene solo gli ultimi max_records log per il job"""
        try:
            count = self.db["sync_logs"].count_documents({"job_string_id": self.job_string_id})
            if count > max_records:
                excess = count - max_records
                oldest = list(
                    self.db["sync_logs"]
                    .find({"job_string_id": self.job_string_id}, {"_id": 1})
                    .sort("timestamp", 1)
                    .limit(excess)
                )
                if oldest:
                    self.db["sync_logs"].delete_many(
                        {"_id": {"$in": [o["_id"] for o in oldest]}}
                    )
        except Exception:
            pass


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


def normalize_name(name):
    if not name:
        return ""
    name = name.translate(str.maketrans("", "", string.punctuation))
    return " ".join(name.lower().split())


def clean_game_name(game_name):
    if not game_name:
        return ""
    game_name = game_name.replace("™", "").replace("®", "").strip()
    pattern = re.compile(r"tro(f|ph)[a-z]*", re.IGNORECASE)
    match = pattern.search(game_name)
    if match:
        game_name = game_name[: match.start()].strip()
    return game_name


async def sync_job(ctx, user_id, platform, string_job_id):
    try:
        db = ctx["db"]
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
        # Handler su MongoDB per la visualizzazione dei log dalla web UI
        mongo_handler = MongoLogHandler(db, log_id)
        mongo_handler.setLevel(logging.INFO)
        mongo_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(mongo_handler)

        logger.info(f"Starting sync for user {user_id} on platform {platform}")
        job_file_handler.flush()

        def mark_job(status, error=None, extra=None):
            update = {"status": status, "updated_at": datetime.now()}
            if error is not None:
                update["error"] = error
            if extra:
                update.update(extra)
            db["schedules"].update_one(
                {"job_string_id": string_job_id}, {"$set": update}
            )

        try:
            try:
                db["schedules"].update_one(
                    {"job_string_id": string_job_id, "status": "queued"},
                    {"$set": {"status": "in_progress", "updated_at": datetime.now()}},
                )
            except errors.PyMongoError as e:
                logger.error(f"Error updating schedule for user {user_id} on {platform}: {e}", flush=True)
                job_file_handler.flush()
                return

            # Check platform
            if platform not in ["psn", "steam", "retroachievements", "gog"]:
                mark_job("fail", error="Invalid platform")
                return

            # Check user
            try:
                user = db.users.find_one({"_id": ObjectId(user_id)})
            except errors.PyMongoError as e:
                logger.info(f"Error finding user {user_id}: {e}")
                mark_job("fail", error="Database error")
                return
            if not user:
                mark_job("fail", error="User not found")
                return

            # Check platform linkage
            try:
                link = db["platforms-users"].find_one(
                    {"user_id": str(user_id), "platform": platform}
                )
            except errors.PyMongoError as e:
                logger.info(f"Error finding platform link for user {user_id} on {platform}: {e}")
                mark_job("fail", error="Database error")
                return
            if not link:
                logger.info(f"No platform linkage found for user {user_id} on {platform}", flush=True)
                mark_job("fail", error="No linkage for platform")
                return

            # Le credenziali sono cifrate a riposo: si decifrano prima dell'uso
            api_key = decrypt_credential(link.get("api_key"))
            if platform == "steam":
                # FIX LUIGI
                # Per Steam, usa platform_id invece di steam_id
                steam_id = link.get("platform_id")
                logger.info(f"Raw Steam ID from DB (platform_id): {steam_id} (type: {type(steam_id)})")
                if not steam_id:
                    logger.error(f"No Steam ID found for user {user_id} in platform_id field")
                    mark_job("fail", error="No Steam ID configured in platform_id")
                    return
                # Assicurati che steam_id sia una stringa
                steam_id = str(steam_id)
                # END FIX LUIGI

            if api_key is None:
                mark_job("fail", error="No API key")
                return

            logger.info(f"Platform: {platform}")
            logger.info(f"API Key: {api_key[:10]}..." if api_key else "None")
            if platform == "steam":
                logger.info(f"Steam ID (from platform_id): {steam_id}")
            elif platform == "psn":
                psn_id = link.get("platform_id")
                logger.info(f"PSN ID (from platform_id): {psn_id}")

            # Call sync function
            logger.info("Calling Platform API...")
            job_file_handler.flush()
            if platform == "psn":
                stats = sync_psn(api_key, logger=logger)
            elif platform == "retroachievements":
                # api_key = Web API Key RA, platform_id = username RetroAchievements
                stats = sync_retroachievements(api_key, link.get("platform_id"), logger=logger)
            elif platform == "gog":
                # platform_id = username/email GOG, api_key = password GOG
                stats = sync_gog(link.get("platform_id"), api_key, logger=logger)
            else:
                stats = sync_steam(api_key, steam_id, logger=logger, db=db)

            if "internalError" in stats:
                logger.error(f"Error in platform API call: {stats['internalError']}")
                mark_job("fail", error=stats["internalError"])
                send_notification(
                    db,
                    "GamesTrack — sync fallita",
                    f"Sincronizzazione {platform} non riuscita: {stats['internalError']}",
                    tags=["x"],
                    logger=logger,
                    only_if_flag="notify_on_sync",
                )
                return

            full_games_dict = stats["fullGames"]

            # --- Pre-caricamento delle lookup in memoria (elimina le query N+1) ---
            # Mappa chiave -> documento gioco esistente.
            # Chiavi: ("name", nome.lower()), ("original", original_name.lower()),
            #         ("norm", normalized_name), ("ext", external_id in formato stringa)
            games_map = {}
            existing_igdb_ids = set()
            existing_name_ext = set()
            for g in db["games"].find(
                {},
                {
                    "name": 1,
                    "original_name": 1,
                    "normalized_name": 1,
                    "psn_game_id": 1,
                    "steam_game_id": 1,
                    "ra_game_id": 1,
                    "gog_game_id": 1,
                    "igdb_id": 1,
                },
            ):
                doc_ref = {
                    "_id": g["_id"],
                    "name": g.get("name"),
                    "original_name": g.get("original_name"),
                    "normalized_name": g.get("normalized_name"),
                    "psn_game_id": g.get("psn_game_id"),
                    "steam_game_id": g.get("steam_game_id"),
                    "ra_game_id": g.get("ra_game_id"),
                    "gog_game_id": g.get("gog_game_id"),
                    "igdb_id": g.get("igdb_id"),
                }
                if g.get("name"):
                    games_map.setdefault(("name", g["name"].lower()), doc_ref)
                if g.get("original_name"):
                    games_map.setdefault(("original", g["original_name"].lower()), doc_ref)
                if g.get("normalized_name"):
                    games_map.setdefault(("norm", g["normalized_name"]), doc_ref)
                if g.get("psn_game_id") is not None:
                    games_map.setdefault(("ext", str(g["psn_game_id"])), doc_ref)
                if g.get("steam_game_id") is not None:
                    games_map.setdefault(("ext", str(g["steam_game_id"])), doc_ref)
                if g.get("ra_game_id") is not None:
                    games_map.setdefault(("ext", str(g["ra_game_id"])), doc_ref)
                if g.get("gog_game_id") is not None:
                    games_map.setdefault(("ext", str(g["gog_game_id"])), doc_ref)
                if g.get("igdb_id") is not None:
                    existing_igdb_ids.add(g["igdb_id"])
                if g.get("name"):
                    existing_name_ext.add(
                        (
                            g["name"].lower(),
                            g.get("psn_game_id")
                            or g.get("steam_game_id")
                            or g.get("ra_game_id")
                            or g.get("gog_game_id"),
                        )
                    )

            # Mappa game_id -> collegamento game_user esistente per questo utente/piattaforma
            # (num_trophies serve per capire se i trofei sono cambiati e ricaricare la lista)
            game_user_map = {}
            for gu in db["game_user"].find(
                {"user_id": str(user_id), "platform": platform},
                {"game_id": 1, "user_id": 1, "platform": 1, "num_trophies": 1},
            ):
                if gu.get("game_id") is not None:
                    game_user_map[gu["game_id"]] = gu

            def find_existing_game(game_name, external_id):
                candidates = []
                if external_id is not None:
                    candidates.append(("ext", str(external_id)))
                candidates.append(("name", game_name.lower()))
                candidates.append(("original", game_name.lower()))
                candidates.append(("norm", normalize_name(game_name)))
                for key in candidates:
                    doc = games_map.get(key)
                    if doc is not None:
                        return doc
                return None

            def register_pending_doc(game_doc, external_id):
                # Registra un documento ancora da inserire: le occorrenze successive
                # nello stesso batch trovano subito la corrispondenza senza richiamare IGDB
                if game_doc.get("name"):
                    games_map.setdefault(("name", game_doc["name"].lower()), game_doc)
                if game_doc.get("original_name"):
                    games_map.setdefault(("original", game_doc["original_name"].lower()), game_doc)
                if game_doc.get("normalized_name"):
                    games_map.setdefault(("norm", game_doc["normalized_name"]), game_doc)
                if external_id is not None:
                    games_map.setdefault(("ext", str(external_id)), game_doc)

            # --- Fase 1: classificazione dei giochi della piattaforma (nessuna chiamata esterna) ---
            new_entries = []  # coppie (game_name, external_id, platform_data)
            games_to_update = []
            game_user_to_insert, game_user_to_update = [], []
            # Job per la sync delle liste complete di trofei/achievement:
            # solo giochi nuovi o con conteggio trofei cambiato (risparmia rate limit)
            trophy_jobs = []

            def queue_trophy_list_job(game_id, platform_data, old_count):
                # None = gioco nuovo: la lista va recuperata comunque
                new_count = int(platform_data.get("earnedTrophy", 0) or 0)
                if old_count is not None and old_count == new_count:
                    return
                if new_count <= 0 and platform not in ("steam", "retroachievements"):
                    return
                trophy_jobs.append({
                    "game_id": game_id,
                    "external_id": platform_data.get("product_id")
                    if platform == "psn"
                    else platform_data.get("title_id"),
                    "np_communication_id": platform_data.get("np_communication_id")
                    if platform == "psn"
                    else None,
                    "new_count": new_count,
                })

            for game in full_games_dict:
                raw_name = game.get("name") if game.get("name") is not None else game.get("title_name")
                if not raw_name:
                    logger.warning(f"Skipping game entry without name: {game}")
                    continue
                game_name = clean_game_name(raw_name)
                external_id = None
                if platform == "steam":
                    external_id = int(game["title_id"]) if game.get("title_id") is not None else None
                elif platform == "psn":
                    # I product ID PSN sono alfanumerici (es. "PPSA12345_00"): vanno mantenuti come stringa
                    external_id = str(game["product_id"]) if game.get("product_id") is not None else None
                elif platform == "retroachievements":
                    external_id = int(game["title_id"]) if game.get("title_id") is not None else None
                elif platform == "gog":
                    external_id = int(game["title_id"]) if game.get("title_id") is not None else None

                existing_game = find_existing_game(game_name, external_id)

                if existing_game is not None and "_id" not in existing_game:
                    # Duplicato di un gioco già accodato per l'inserimento in questo batch:
                    # le statistiche vengono collegate tramite la prima occorrenza
                    continue

                if existing_game is None:
                    if "demo" in game_name.lower() or "beta" in game_name.lower():
                        logger.info(f"Skipping demo/beta game: {game_name}")
                        job_file_handler.flush()
                        continue
                    new_entries.append((game_name, external_id, game))
                else:
                    logger.info(f"Game already exists in the database: {game_name}")
                    job_file_handler.flush()

                    game_id = existing_game["_id"]
                    gu_entry = game_user_map.get(game_id)
                    queue_trophy_list_job(
                        game_id,
                        game,
                        int(gu_entry.get("num_trophies") or 0) if gu_entry else None,
                    )

                    if platform == "steam" and existing_game.get("steam_game_id") is None:
                        games_to_update.append(
                            UpdateOne(
                                {"_id": game_id},
                                {"$set": {"steam_game_id": external_id}},
                            )
                        )
                    elif platform == "psn" and existing_game.get("psn_game_id") is None:
                        games_to_update.append(
                            UpdateOne(
                                {"_id": game_id},
                                {"$set": {"psn_game_id": external_id}},
                            )
                        )
                    elif platform == "retroachievements" and existing_game.get("ra_game_id") is None:
                        games_to_update.append(
                            UpdateOne(
                                {"_id": game_id},
                                {"$set": {"ra_game_id": external_id}},
                            )
                        )
                    elif platform == "gog" and existing_game.get("gog_game_id") is None:
                        games_to_update.append(
                            UpdateOne(
                                {"_id": game_id},
                                {"$set": {"gog_game_id": external_id}},
                            )
                        )

                    game_user_entry = game_user_map.get(game_id)
                    stats_data = {
                        "num_trophies": int(game.get("earnedTrophy", 0) or 0),
                        "play_count": int(game.get("play_count", 0) or 0),
                    }
                    source_data = {}
                    # Il flag sorgente arriva dal record della piattaforma
                    # (psnTrack lo ricava dalle entitlement ufficiali PSN)
                    if game.get("source"):
                        source_data["source"] = game["source"]
                    if game_user_entry is None:
                        game_user_to_insert.append(
                            {
                                "game_id": game_id,
                                "user_id": str(user_id),
                                "platform": platform,
                                **stats_data,
                                **source_data,
                                "console": 6 if platform in ("steam", "gog") else game.get("console", 9999),
                            },
                        )
                        # Placeholder per evitare inserimenti duplicati nello stesso batch
                        game_user_map[game_id] = {"game_id": game_id}
                    else:
                        game_user_to_update.append(
                            {
                                "game_id": game_id,
                                "user_id": str(user_id),
                                "platform": platform,
                                **stats_data,
                                **source_data,
                            },
                        )

            # --- Fase 2: metadati IGDB in batch (poche richieste aggregate) ---
            metadata_map = {}
            if new_entries:
                # Deduplica le richieste: coppie (nome, external_id) identiche condividono il risultato
                seen_requests = set()
                batch_requests = []
                for name, ext, _ in new_entries:
                    key = (name.lower(), ext)
                    if key not in seen_requests:
                        seen_requests.add(key)
                        batch_requests.append((name, ext))

                logger.info(
                    f"Retrieving IGDB metadata for {len(batch_requests)} new games in batch mode"
                )
                job_file_handler.flush()
                try:
                    metadata_map = igdb_client = None  # placeholder sostituito sotto
                except Exception:
                    pass
                igdb_client = IGDBAutoAuthClient(
                    client_id=os.getenv("IGDB_CLIENT_ID"),
                    client_secret=os.getenv("IGDB_CLIENT_SECRET"),
                )
                try:
                    metadata_map = igdb_client.get_games_metadata_batch(batch_requests)
                except Exception as e:
                    logger.warning(
                        f"Batch metadata retrieval failed, falling back to per-game calls: {e}"
                    )
                    metadata_map = {}

            # --- Fase 3: costruzione dei documenti e scrittura su MongoDB ---
            games_to_insert = []  # coppie (game_doc, platform_data)

            for game_name, external_id, platform_data in new_entries:
                metadata = metadata_map.get((game_name.lower(), external_id))

                if metadata is None:
                    # Fallback: chiamata singola, come prima dell'introduzione del batch
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
                    else:
                        time.sleep(1.0)  # rate limit IGDB

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
                    "ra_game_id": external_id if platform == "retroachievements" else None,
                    "gog_game_id": external_id if platform == "gog" else None,
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
                games_to_insert.append((game_doc, platform_data))
                register_pending_doc(game_doc, external_id)

            if games_to_insert:
                # Deduplica dentro il batch e contro i giochi già presenti
                unique_entries = []
                for game_doc, platform_data in games_to_insert:
                    key = (
                        game_doc["name"].lower(),
                        game_doc.get("psn_game_id")
                        or game_doc.get("steam_game_id")
                        or game_doc.get("ra_game_id")
                        or game_doc.get("gog_game_id"),
                    )
                    if game_doc.get("igdb_id") is not None and game_doc["igdb_id"] in existing_igdb_ids:
                        continue
                    if game_doc.get("igdb_id") is None and key in existing_name_ext:
                        continue
                    if game_doc.get("igdb_id") is not None:
                        existing_igdb_ids.add(game_doc["igdb_id"])
                    existing_name_ext.add(key)
                    unique_entries.append((game_doc, platform_data))

                games_to_insert = unique_entries

                if games_to_insert:
                    result = db["games"].insert_many(
                        [game_doc for game_doc, _ in games_to_insert]
                    )
                    logger.info(
                        f"Inserted {len(result.inserted_ids)} new games into the database."
                    )
                    job_file_handler.flush()

                    # Collega le statistiche utente usando gli _id restituiti dall'insert,
                    # senza dover ri-consultare il database per ogni gioco
                    for (platform_data,), game_id in zip(
                        [(pd,) for _, pd in games_to_insert], result.inserted_ids
                    ):
                        queue_trophy_list_job(game_id, platform_data, None)
                        game_user_to_insert.append(
                            {
                                "game_id": game_id,
                                "user_id": str(user_id),
                                "platform": platform,
                                "num_trophies": int(platform_data.get("earnedTrophy", 0) or 0),
                                "play_count": int(platform_data.get("play_count", 0) or 0),
                                **(
                                    {"source": platform_data["source"]}
                                    if platform == "psn" and platform_data.get("source")
                                    else {}
                                ),
                                "console": 6 if platform in ("steam", "gog") else platform_data.get("console", 9999),
                            },
                        )

            if games_to_update:
                try:
                    db["games"].bulk_write(games_to_update)
                    logger.info(f"Updated {len(games_to_update)} games in the database.")
                    job_file_handler.flush()
                except errors.BulkWriteError as bwe:
                    logger.error(f"Bulk write error: {bwe.details}")
                    mark_job("fail", error="Bulk Write Error on Games")
                    return

            # Filtra e deduplica
            game_user_to_insert = [
                g
                for g in game_user_to_insert
                if g.get("num_trophies") is not None
                and g.get("play_count") is not None
                and g.get("game_id") is not None
                and g.get("user_id") is not None
                and g.get("platform") is not None
            ]
            seen_game_user = set()
            unique_game_user_to_insert = []
            for g in game_user_to_insert:
                key = (g["game_id"], g["user_id"], g["platform"])
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
                    job_file_handler.flush()
            except errors.BulkWriteError as bwe:
                logger.error(f"Bulk write error: {bwe.details}")
                job_file_handler.flush()
                mark_job("fail", error="Bulk Write Error on Games")
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
                                    "num_trophies": int(g["num_trophies"] or 0),
                                    "play_count": int(g["play_count"] or 0),
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
                    logger.error(f"Error updating game-user linkages: {e}")
                    job_file_handler.flush()
                    mark_job("fail", error="Bulk write of game_user failed")
                    return

            # --- Storico achievement: uno snapshot per sync, per la pagina
            # Statistiche (progressione trofei/ore nel tempo) ---
            try:
                now = datetime.now()
                snapshots = [
                    {
                        "user_id": str(user_id),
                        "platform": platform,
                        "game_id": g["game_id"],
                        "num_trophies": int(g["num_trophies"] or 0),
                        "play_count": int(g["play_count"] or 0),
                        "timestamp": now,
                    }
                    for g in game_user_to_insert + game_user_to_update
                    if g.get("game_id") is not None
                ]
                if snapshots:
                    db["trophy_history"].insert_many(snapshots)
                    logger.info(f"Recorded {len(snapshots)} trophy history snapshots")
            except errors.PyMongoError as e:
                logger.warning(f"Trophy history write failed (non bloccante): {e}")

            # --- Liste complete di trofei/achievement (per la pagina di dettaglio):
            # solo i giochi nuovi o con conteggio cambiato (vedi trophy_jobs) ---
            if trophy_jobs and platform in ("psn", "steam", "retroachievements"):
                logger.info(
                    f"Syncing full trophy lists for {len(trophy_jobs)} games ({platform})"
                )
                job_file_handler.flush()
                try:
                    if platform == "psn":
                        from utils.psnTrack import create_client, fetch_trophy_list

                        psn_client = create_client(api_key)
                    elif platform == "steam":
                        from utils.steamTrack import (
                            create_robust_session,
                            fetch_achievement_list,
                        )

                        steam_session = create_robust_session()
                    else:
                        from utils.retroTrack import (
                            create_robust_session,
                            fetch_achievement_list,
                        )

                        ra_session = create_robust_session()

                    fetched_count = 0
                    for job in trophy_jobs:
                        try:
                            if platform == "psn":
                                data = fetch_trophy_list(
                                    psn_client,
                                    job.get("np_communication_id"),
                                )
                                time.sleep(1.0)  # rate limit PSN
                            elif platform == "steam":
                                data = fetch_achievement_list(
                                    api_key,
                                    steam_id,
                                    job.get("external_id"),
                                    session=steam_session,
                                )
                                time.sleep(0.3)
                            else:
                                data = fetch_achievement_list(
                                    api_key,
                                    link.get("platform_id"),
                                    job.get("external_id"),
                                    session=ra_session,
                                )
                                time.sleep(0.5)
                            if data is None:
                                continue
                            db["trophy_lists"].update_one(
                                {
                                    "user_id": str(user_id),
                                    "platform": platform,
                                    "game_id": job["game_id"],
                                },
                                {
                                    "$set": {
                                        "user_id": str(user_id),
                                        "platform": platform,
                                        "game_id": job["game_id"],
                                        "trophies": data,
                                        "earned_count": job["new_count"],
                                        "source": "sync",
                                        "fetched_at": datetime.now(),
                                    }
                                },
                                upsert=True,
                            )
                            fetched_count += 1
                        except Exception as e:
                            logger.warning(
                                f"Trophy list fetch failed for game_id {job.get('game_id')}: {e}"
                            )
                            continue
                    logger.info(f"Stored {fetched_count} full trophy lists")
                except Exception as e:
                    logger.warning(f"Trophy list sync failed (non bloccante): {e}")
                job_file_handler.flush()

            # Aggiorna summary
            try:
                db["platforms-users"].update_one(
                    {"user_id": str(user_id), "platform": platform},
                    {
                        "$set": {
                            # "game_count": stats.get("gameCount", 0),
                            # "earned_achievements": stats.get("earnedTrophyCount", 0),
                            # "play_count": stats.get("totPlayTimeCount", 0),
                            "full_trophies_count": stats.get("completeTrophyCount", 0),
                        }
                    },
                )
                logger.info(f"Updated platform summary for {platform} for user {user_id}")
                job_file_handler.flush()
            except errors.PyMongoError as e:
                logger.error(f"Error updating platform summary for {platform}: {e}")
                job_file_handler.flush()
                mark_job("fail", error="Failed updating platform summary")
                return

            mark_job(
                "success",
                extra={
                    "game_inserted": len(games_to_insert),
                    "game_updated": len(games_to_update),
                    "game_user_inserted": len(game_user_to_insert),
                    "game_user_updated": len(game_user_to_update),
                },
            )
            logger.info(f"Sync for user {user_id} on {platform} completed successfully.")
            job_file_handler.flush()

        except Exception as e:
            mark_job("fail", error=str(e))
            logger.error(f"Sync failed for user {user_id} on {platform}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            send_notification(
                db,
                "GamesTrack — sync fallita",
                f"Sincronizzazione {platform} fallita per l'utente: {e}",
                tags=["x"],
                logger=logger,
                only_if_flag="notify_on_sync",
            )
            return
        finally:
            logger.removeHandler(job_file_handler)
            job_file_handler.close()
            mongo_handler.trim()
            logger.removeHandler(mongo_handler)
    except Exception as e:
        logging.error(f"Error in sync_job: {e}")
        if "job_file_handler" in locals():
            job_file_handler.close()
        raise e


async def platform_sync_tick(ctx):
    """Cron ogni minuto: se è il giorno/ora configurati in app_settings
    (modificabili dalla web UI, default: lunedì ore 8), esegue la
    sincronizzazione di tutte le piattaforme collegate da tutti gli utenti."""
    db = ctx["db"]
    settings = db["app_settings"].find_one({"key": "platform_sync"}) or {}
    if not settings.get("enabled"):
        return

    now = datetime.now()
    try:
        weekday = int(settings.get("weekday", 0))   # 0 = lunedì
        hour = int(settings.get("hour", 8))
    except (TypeError, ValueError):
        return
    if now.weekday() != weekday or now.hour != hour:
        return

    # Evita doppie esecuzioni nella stessa finestra (stesso giorno)
    last_run = settings.get("last_run")
    if last_run is not None and (now - last_run).total_seconds() < 20 * 3600:
        return

    db["app_settings"].update_one(
        {"key": "platform_sync"}, {"$set": {"last_run": now}}, upsert=True
    )

    links = list(db["platforms-users"].find({}))
    logger = logging.getLogger("platform_sync_tick")
    logger.info(f"Sincronizzazione automatica: {len(links)} collegamenti piattaforma da processare")
    for link in links:
        user_id = link.get("user_id")
        platform = link.get("platform")
        if not user_id or platform not in ["psn", "steam", "retroachievements", "gog"]:
            continue
        job_string_id = f"{user_id}_{platform}_auto_{now.strftime('%Y%m%d_%H%M%S')}"
        try:
            await sync_job(ctx, user_id, platform, job_string_id)
        except Exception as e:
            logger.error(f"Auto sync failed for {user_id}/{platform}: {e}")
    logger.info("Sincronizzazione automatica completata")


async def price_track_job(ctx, job_string_id=None):
    """Job: raccoglie i prezzi per gli item in wishlist e li registra nella
    collection price_history. Stato e log sono tracciati per la web UI."""
    db = ctx["db"]
    if job_string_id is None:
        job_string_id = f"price_track_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_id = job_string_id

    logger = logging.getLogger(f"price_track_{log_id}")
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    mongo_handler = MongoLogHandler(db, log_id)
    mongo_handler.setLevel(logging.INFO)
    mongo_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(mongo_handler)

    db["schedules"].insert_one(
        {
            "job_string_id": log_id,
            "platform": "price_track",
            "user_id": None,
            "status": "in_progress",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    )
    logger.info("Price tracking avviato")

    items = list(db["game_user_wishlist"].find({}))
    logger.info(f"{len(items)} wishlist items da processare")

    session = create_price_session()
    snapshots_written = 0
    price_alerts = []  # item scattati in questo ciclo, per la notifica ntfy
    # Lista globale negozi Trovaprezzi (impostazioni web UI): usata come filtro
    # per gli item che non hanno una lista propria
    global_settings = db["app_settings"].find_one({"key": "price_track"}) or {}
    global_stores = global_settings.get("trovaprezzi_stores") or []
    try:
        for item in items:
            game_id = item.get("game_id")
            if not game_id:
                continue
            game = db["games"].find_one({"_id": ObjectId(game_id)})
            if not game:
                logger.warning(f"Wishlist item {item.get('_id')}: game {game_id} non trovato, skip")
                continue

            try:
                effective_tracking = dict(item.get("price_tracking") or {})
                if not effective_tracking.get("stores") and global_stores:
                    effective_tracking["stores"] = global_stores
                prices = collect_prices_for_game(
                    session, game, price_tracking=effective_tracking, logger=logger
                )
            except Exception as e:
                logger.warning(f"Price collection failed for game {game_id}: {e}")
                continue
            if not prices:
                logger.info(f"Nessun prezzo trovato per {game.get('name')}")
                continue

            now = datetime.now()
            for p in prices:
                p["game_id"] = game_id
                p["user_id"] = item.get("user_id")
                p["timestamp"] = now
            try:
                db["price_history"].insert_many(prices)
                snapshots_written += len(prices)
            except errors.BulkWriteError as e:
                logger.error(f"Bulk write error su price_history: {e.details}")

            # Riepilogo sul wishlist item: prezzo minimo tra i negozi disponibili
            available = [p["price"] for p in prices if p.get("price") is not None]
            update = {"latest_price_checked_at": now}
            if available:
                best = min(prices, key=lambda p: p["price"])
                update["latest_price"] = best["price"]
                update["latest_price_store"] = best["store"]
            tracking = item.get("price_tracking") or {}
            alert_below = tracking.get("alert_below")
            if alert_below is not None and available and min(available) <= alert_below:
                if not item.get("alert_triggered"):
                    # Alert appena scattato (non già attivo): notifica
                    price_alerts.append(
                        {
                            "name": game.get("name", game_id),
                            "price": min(available),
                            "store": update.get("latest_price_store", ""),
                            "threshold": alert_below,
                        }
                    )
                update["alert_triggered"] = True
            db["game_user_wishlist"].update_one({"_id": item["_id"]}, {"$set": update})

        db["schedules"].update_one(
            {"job_string_id": log_id},
            {"$set": {"status": "success", "updated_at": datetime.now(), "price_snapshots": snapshots_written}},
        )
        logger.info(f"Price tracking completato: {snapshots_written} snapshot scritti")

        # Notifica ntfy con gli alert prezzo scattati in questo ciclo
        if price_alerts:
            lines = [
                f"· {a['name']}: {a['price']:.2f} € su {a['store']} (soglia {a['threshold']} €)"
                for a in price_alerts
            ]
            send_notification(
                db,
                "GamesTrack — alert prezzi!",
                "Prezzi scesi sotto la soglia:\n" + "\n".join(lines),
                tags=["money"],
                logger=logger,
                only_if_flag="notify_on_price",
            )
    except Exception as e:
        db["schedules"].update_one(
            {"job_string_id": log_id},
            {"$set": {"status": "fail", "error": str(e), "updated_at": datetime.now()}},
        )
        logger.error(f"Price tracking fallito: {e}")
    finally:
        mongo_handler.trim()
        logger.removeHandler(mongo_handler)


async def price_track_tick(ctx):
    """Cron ogni minuto: legge le impostazioni del tracking prezzi da
    app_settings (modificabili dalla web UI) ed esegue price_track_job
    quando l'intervallo configurato è trascorso."""
    db = ctx["db"]
    settings = db["app_settings"].find_one({"key": "price_track"})
    if not settings or not settings.get("enabled", True):
        return
    interval_minutes = int(settings.get("interval_minutes", 1440))
    last_run = settings.get("last_run")
    now = datetime.now()
    if last_run is not None and (now - last_run).total_seconds() < interval_minutes * 60:
        return
    # Aggiorna last_run prima dell'esecuzione per evitare doppie esecuzioni
    db["app_settings"].update_one(
        {"key": "price_track"}, {"$set": {"last_run": now}}, upsert=True
    )
    await price_track_job(ctx)


class WorkerSettings:
    functions = [sync_job, price_track_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn("redis://redis:6379")
    max_jobs = 1
    poll_delay = 0.5
    # Le sincronizzazioni di librerie grandi richiedono molto più di 5 minuti
    # (chiamate API Steam/PSN + IGDB con rate limiting): timeout portato a 1 ora
    job_timeout = 3600
    max_tries = 2
    # Tick ogni minuto: controllano le impostazioni (modificabili dalla web UI)
    # e avviano i job solo quando è il momento configurato
    cron_jobs = [
        cron(price_track_tick, second=0, run_at_startup=False),
        cron(platform_sync_tick, second=0, run_at_startup=False),
    ]
