# Sincronizzazione PSN tramite psnawp (versione 3.x).
#
# Novità 3.1.0 usate qui:
# - client.title_stats() / client.trophy_titles(): iteratori paginati nativi
# - psn.game_title(title_id, platform, account_id): np_communication_id senza wrapper
# - client.game_entitlements(): entitlements ufficiali (con isSubscription) che
#   sostituiscono la GraphQL custom per il flag "source" (digital/psplus)

from psnawp_api import PSNAWP
from psnawp_api.models.trophies import PlatformType
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import time
import logging
import sys

# Timeout per la risoluzione del np_communication_id di un singolo titolo
TITLE_LOOKUP_TIMEOUT = 10
# Rate limiting: pausa tra le chiamate pesanti (Sony non pubblica i limiti)
TITLE_STATS_PAUSE = 1.0

# Executor condiviso: un solo pool per l'intero sync (invece di uno per titolo)
_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def sync_psn(npsso, logger=None):
    """Sincronizzazione PSN: giochi, trofei, entitlement e flag sorgente.

    npsso: token SSO dell'account (64 caratteri).
    """
    if logger is None:
        logger = logging.getLogger()

    logger.info("Starting PSN synchronization (psnawp 3.x)...")
    print("Starting PSN synchronization (psnawp 3.x)...", flush=True)

    try:
        psn = PSNAWP(npsso)
        client = psn.me()
        account_id = client.account_id
        logger.info(f"Authenticated PSN account: {client.online_id}")

        def lookup_title_ids(t):
            """Risolve np_communication_id e product_id di un titolo (con timeout)"""
            def _lookup():
                platform = (
                    PlatformType.PS5
                    if t.category is not None and t.category.name == "PS5"
                    else PlatformType.PS4
                )
                try:
                    game_title = psn.game_title(
                        title_id=t.title_id,
                        platform=platform,
                        account_id=account_id,
                    )
                    product_id = None
                    try:
                        details = game_title.get_details()
                        product_id = details[0].get("id") if details else None
                    except Exception as e:
                        logger.warning(f"Details not available for {t.title_id}: {e}")
                    return {
                        "np_communication_id": game_title.np_communication_id,
                        "product_id": product_id,
                    }
                except Exception as e:
                    logger.warning(f"Error retrieving np_communication_id for title_id {t.title_id}: {e}")
                    return {"np_communication_id": None, "product_id": None}

            future = _EXECUTOR.submit(_lookup)
            try:
                return future.result(timeout=TITLE_LOOKUP_TIMEOUT)
            except FutureTimeoutError:
                logger.warning(f"Timeout getting np_communication_id for title_id {t.title_id}")
                future.cancel()
                return {"np_communication_id": None, "product_id": None}

        games_records = []
        trophy_records = []

        gameCount = 0
        totPlayTimeCount = 0
        logger.info("Recupero Dati Giochi: ")
        print("Recupero Dati Giochi: ", flush=True)

        # Ottieni statistiche dei giochi
        try:
            title_stats = list(client.title_stats(page_size=200))
            logger.info(f"Found {len(title_stats)} games in title stats")

            for t in title_stats:
                logger.info("GAME: Title ID: " + str(t.title_id) + " / Name: " + str(t.name))
                print("GAME: Title ID: " + str(t.title_id) + " / Name: " + str(t.name), flush=True)

                ids = lookup_title_ids(t)
                np_communication_id = ids["np_communication_id"]
                product_id = ids["product_id"]

                console = t.category.name if t.category is not None else "UNKNOWN"
                if console == "PS5":
                    console = 167
                elif console == "PS4":
                    console = 48
                else:
                    console = 9999

                if np_communication_id is not None:
                    games_records.append({
                        "title_id": t.title_id,
                        "name": t.name,
                        "image_url": t.image_url,
                        "console": console,
                        "play_count": t.play_count,
                        "first_played_date_time": t.first_played_date_time,
                        "last_played_date_time": t.last_played_date_time,
                        "play_duration": t.play_duration,
                        "np_communication_id": np_communication_id,
                        "product_id": product_id,
                    })
                    gameCount += 1
                    if t.play_duration is not None:
                        totPlayTimeCount += int(t.play_duration.total_seconds())

                time.sleep(TITLE_STATS_PAUSE)  # Rate limiting

        except Exception as e:
            logger.error(f"Error getting title stats: {e}")
            print(f"Error getting title stats: {e}", flush=True)

        earnedTrophyCount = 0
        totTrophyCount = 0
        completeTrophyCount = 0
        logger.info("Recupero Dati da Trofei: ")

        # Ottieni trofei
        try:
            trophy_titles = list(client.trophy_titles(page_size=50))
            logger.info(f"Found {len(trophy_titles)} trophy titles")

            for tr in trophy_titles:
                logger.info(
                    "TROPHY: Title ID: "
                    + str(tr.np_communication_id)
                    + " / Name: "
                    + str(tr.title_name)
                )
                print(
                    "TROPHY: Title ID: "
                    + str(tr.np_communication_id)
                    + " / Name: "
                    + str(tr.title_name),
                    flush=True,
                )

                defined_trophies = (
                    tr.defined_trophies.bronze
                    + tr.defined_trophies.silver
                    + tr.defined_trophies.gold
                    + tr.defined_trophies.platinum
                )
                earned_trophies = (
                    tr.earned_trophies.bronze
                    + tr.earned_trophies.silver
                    + tr.earned_trophies.gold
                    + tr.earned_trophies.platinum
                )

                trophy_records.append({
                    "np_communication_id": tr.np_communication_id,
                    "title_name": tr.title_name,
                    "totTrophy": defined_trophies,
                    "earnedTrophy": earned_trophies,
                    "percTrophy": str(tr.progress) + "%",
                })
                earnedTrophyCount += earned_trophies
                totTrophyCount += defined_trophies
                if tr.earned_trophies.platinum > 0:
                    completeTrophyCount += 1

        except Exception as e:
            logger.error(f"Error getting trophy titles: {e}")
            print(f"Error getting trophy titles: {e}", flush=True)

        # Merge dei record: un gioco senza trofei non ha corrispondenza nei trofei e
        # viene scartato (come il merge how="right" della versione pandas); un trofeo
        # senza record di gioco mantiene i campi di gioco a None
        games_by_npcid = {
            g["np_communication_id"]: g for g in games_records
        }
        merged_records = []
        for tr in trophy_records:
            game = games_by_npcid.get(tr["np_communication_id"])
            row = {field: game.get(field) if game else None for field in (
                "title_id", "name", "image_url", "console", "play_count",
                "first_played_date_time", "last_played_date_time", "play_duration",
                "np_communication_id", "product_id",
            )}
            row.update(tr)
            merged_records.append(row)

        # Flag sorgente dalle entitlement ufficiali (sostituisce la GraphQL custom):
        # isSubscription=True -> licenza da abbonamento (psplus), altrimenti acquistata
        source_by_product = {}
        try:
            entitlements = list(client.game_entitlements(page_size=200))
            logger.info(f"Found {len(entitlements)} game entitlements")
            for ent in entitlements:
                pid = ent.get("productId")
                if pid is not None and pid not in source_by_product:
                    source_by_product[pid] = "psplus" if ent.get("isSubscription") else "digital"
        except Exception as e:
            logger.warning(f"Error getting game entitlements (source flag will be 'unknown'): {e}")

        for row in merged_records:
            row["source"] = source_by_product.get(row.get("product_id"), "unknown")

        print(
            "Game Count : "
            + str(gameCount)
            + ", Earned Trophy Count : "
            + str(earnedTrophyCount)
            + ", Total Trophy Count : "
            + str(totTrophyCount)
            + ", Complete Trophy Count : "
            + str(completeTrophyCount)
        )

        logger.info(f"PSN sync completed: {gameCount} games, {earnedTrophyCount} trophies earned")
        print(f"PSN sync completed: {gameCount} games, {earnedTrophyCount} trophies earned", flush=True)

        # Se non ci sono giochi, potrebbe essere un profilo privato
        if gameCount == 0 and earnedTrophyCount == 0:
            logger.warning("No games or trophies found. This might be a private profile or the user has no games.")
            print("No games or trophies found. This might be a private profile or the user has no games.", flush=True)

        return {
            "fullGames": merged_records,
            "gameCount": gameCount,
            "earnedTrophyCount": earnedTrophyCount,
            "totTrophyCount": totTrophyCount,
            "completeTrophyCount": completeTrophyCount,
            "totPlayTimeCount": totPlayTimeCount,
        }

    except Exception as e:
        logger.error(f"PSN sync failed: {e}")
        print(f"PSN sync failed: {e}", flush=True)
        return {
            "fullGames": [],
            "gameCount": 0,
            "earnedTrophyCount": 0,
            "totTrophyCount": 0,
            "completeTrophyCount": 0,
            "totPlayTimeCount": 0,
            "internalError": str(e)
        }


# --- Lista completa trofei per gioco (per la collection trophy_lists) ---

def create_client(npsso):
    """Crea il client psnawp (una sola autenticazione per tutta la sync)"""
    return PSNAWP(npsso)


def fetch_trophy_list(client, np_communication_id, platform_keys=None):
    """Recupera la lista completa dei trofei di un titolo con lo stato utente.

    Ritorna una lista di dict serializzabili, o None in caso di fallimento.
    Prova le piattaforme indicate (es. ["PS4", "PS5"]) poi PS5/PS4 come fallback.
    """
    if not np_communication_id:
        return None

    candidates = []
    for key in platform_keys or ["PS4", "PS5", "PS3", "PSVITA"]:
        try:
            candidates.append(PlatformType(key))
        except ValueError:
            continue
    for fallback in (PlatformType.PS5, PlatformType.PS4):
        if fallback not in candidates:
            candidates.append(fallback)

    for platform in candidates:
        try:
            iterator = client.trophies(
                np_communication_id,
                platform,
                include_progress=True,
                trophy_group_id="all",
                limit=None,
            )
            trophies = []
            for t in iterator:
                earned_dt = getattr(t, "earned_date_time", None)
                trophies.append({
                    "trophy_id": getattr(t, "trophy_id", None),
                    "name": getattr(t, "name", ""),
                    "detail": getattr(t, "detail", ""),
                    "type": getattr(t, "type", None),
                    "icon_url": getattr(t, "icon_url", ""),
                    "earned": bool(getattr(t, "earned", False)),
                    "earned_date": earned_dt.isoformat() if earned_dt else None,
                    "progress_value": getattr(t, "progress_value", None),
                    "rarity": getattr(t, "rarity", None),
                })
            return trophies
        except Exception:
            continue
    return None
