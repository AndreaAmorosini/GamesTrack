# Sincronizzazione RetroAchievements tramite la Web API pubblica
# (https://api-docs.retroachievements.org/): autenticazione con header
# X-API-Key (Web API Key dell'account) + username utente.

import requests
import logging
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RA_API_BASE = "https://api.retroachievements.org"

# Mappatura parziale ConsoleID RetroAchievements -> ID piattaforma IGDB.
# Le console non mappate usano il fallback 9999 (stessa convenzione di PSN).
RA_CONSOLE_TO_IGDB = {
    1: 29,    # Sega Genesis / Mega Drive
    2: 4,     # Nintendo 64
    3: 19,    # SNES
    4: 33,    # Game Boy
    7: 18,    # NES
    11: 64,   # Sega Master System
    12: 7,    # PlayStation
    15: 35,   # Sega Game Gear
    17: 59,   # Atari 2600
    18: 66,   # Atari 7800
    20: 62,   # Atari Jaguar
    24: 23,   # Sega Dreamcast
    39: 37,   # Nintendo 3DS
    41: 20,   # Nintendo DS
    43: 38,   # PSP
    44: 46,   # PS Vita
}

RECENTLY_PLAYED_LIMIT = 100


def create_robust_session():
    """Crea una sessione requests con configurazioni robuste"""
    session = requests.Session()

    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def ra_api_request(session, web_api_key, endpoint, params=None, timeout=30):
    """Esegue una richiesta alla Web API di RetroAchievements"""
    url = f"{RA_API_BASE}/API/{endpoint}"
    try:
        response = session.get(
            url,
            params=params,
            headers={"X-API-Key": web_api_key},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request failed ({endpoint}): {e}", flush=True)
        raise


def load_user_progress_counts(session, web_api_key, username, console_ids, logger):
    """Recupera i conteggi achievement per-console (API_GetUserProgress).

    Ritorna: dict GameID -> {"earned": n, "total": n, "earned_hardcore": n}
    Il parsing è difensivo: la struttura della risposta varia tra versioni dell'API.
    """
    progress_by_game = {}
    if not console_ids:
        return progress_by_game
    try:
        data = ra_api_request(
            session,
            web_api_key,
            "API_GetUserProgress.php",
            params={"u": username, "c": ",".join(str(c) for c in console_ids)},
        )
        # La risposta è strutturata per console: {consoleID: {gameID: {...}}}
        for console_data in (data or {}).values():
            if not isinstance(console_data, dict):
                continue
            for game_id, prog in console_data.items():
                if not isinstance(prog, dict) or "NumPossibleAchievements" not in prog:
                    continue
                try:
                    progress_by_game[int(game_id)] = {
                        "earned": int(prog.get("NumAchieved", 0) or 0),
                        "total": int(prog.get("NumPossibleAchievements", 0) or 0),
                        "earned_hardcore": int(prog.get("NumAchievedHardcore", 0) or 0),
                    }
                except (TypeError, ValueError):
                    continue
    except Exception as e:
        logger.warning(f"Error retrieving user progress counts: {e}")
    return progress_by_game


def sync_retroachievements(web_api_key, ra_username, logger=None):
    """Sincronizzazione RetroAchievements.

    web_api_key: Web API Key generata dal controllo panel dell'account RA
    ra_username: username RetroAchievements
    """
    if logger is None:
        logger = logging.getLogger()

    logger.info("Starting RetroAchievements synchronization...")
    print("Starting RetroAchievements synchronization...", flush=True)

    session = create_robust_session()

    try:
        # 1. Premiazioni utente: giochi completati/masterizzati (libreria storica)
        logger.info(f"Getting user awards for RetroAchievements user: {ra_username}")
        awards_data = ra_api_request(
            session, web_api_key, "API_GetUserAwards.php", params={"u": ra_username}
        )
        awards = (awards_data or {}).get("Awards", [])

        award_games = {}  # GameID -> info gioco
        for award in awards:
            # AwardType 1 = premi "gioco" (mastery/completion); gli altri sono
            # premi di sito/evento senza un gioco associato utile alla libreria
            if award.get("AwardType") != 1:
                continue
            game_id = award.get("AwardData")
            if game_id is None:
                continue
            entry = award_games.setdefault(
                int(game_id),
                {
                    "title_id": int(game_id),
                    "name": award.get("Title"),
                    "console": RA_CONSOLE_TO_IGDB.get(award.get("ConsoleID"), 9999),
                    "image_url": (
                        f"https://media.retroachievements.org/Badge/{award.get('BadgeName')}.png"
                        if award.get("BadgeName")
                        else None
                    ),
                    "mastered_hardcore": award.get("AwardDataExtra") == 1,
                },
            )
            entry["mastered_hardcore"] = entry["mastered_hardcore"] or award.get("AwardDataExtra") == 1

        logger.info(f"Found {len(award_games)} games with awards")

        # 2. Giochi giocati di recente (con conteggi achievement)
        logger.info("Getting recently played games...")
        recently_played = (
            ra_api_request(
                session,
                web_api_key,
                "API_GetUserRecentlyPlayedGames.php",
                params={"u": ra_username, "c": RECENTLY_PLAYED_LIMIT},
            )
            or []
        )

        played_games = {}
        for g in recently_played:
            game_id = g.get("GameID")
            if game_id is None:
                continue
            game_id = int(game_id)
            played_games[game_id] = {
                "title_id": game_id,
                "name": g.get("Title"),
                "console": RA_CONSOLE_TO_IGDB.get(g.get("ConsoleID"), 9999),
                "image_url": (
                    f"https://media.retroachievements.org{g.get('ImageIcon')}"
                    if g.get("ImageIcon")
                    else None
                ),
                "last_played": g.get("LastPlayed"),
                "mastered_hardcore": False,
            }
            # i ConsoleID del recent-played sono RA, non IGDB: ricava quelli RA originali
        # RA ConsoleID originali per la chiamata GetUserProgress
        ra_console_ids = {
            a.get("ConsoleID") for a in awards if a.get("AwardType") == 1 and a.get("ConsoleID") is not None
        } | {
            g.get("ConsoleID") for g in recently_played if g.get("ConsoleID") is not None
        }

        progress_by_game = load_user_progress_counts(
            session, web_api_key, ra_username, ra_console_ids, logger
        )
        logger.info(f"Loaded achievement progress for {len(progress_by_game)} games")

        # 3. Unione: premi (storico) + giochi giocati di recente
        merged = dict(played_games)
        for game_id, entry in award_games.items():
            if game_id not in merged:
                merged[game_id] = entry

        game_records = []
        earnedTrophyCount = 0
        totTrophyCount = 0
        completeTrophyCount = 0

        for game_id, game in merged.items():
            progress = progress_by_game.get(game_id, {})
            earned = progress.get("earned", 0) or 0
            total = progress.get("total", 0) or 0
            if game_id in played_games or game["mastered_hardcore"]:
                completeTrophyCount += 1
            earnedTrophyCount += earned
            totTrophyCount += total

            game_records.append({
                "title_id": game_id,
                "name": game.get("name"),
                "image_url": game.get("image_url"),
                "console": game.get("console", 9999),
                "earnedTrophy": earned,
                "totTrophy": total,
                "percTrophy": f"{(earned / total * 100):.2f}%" if total > 0 else "0%",
                "play_count": 0,  # RA non traccia il tempo di gioco
                "last_played": game.get("last_played"),
            })

        logger.info(
            f"RetroAchievements sync completed: {len(game_records)} games, "
            f"{earnedTrophyCount} achievements earned"
        )
        print(
            f"RetroAchievements sync completed: {len(game_records)} games, "
            f"{earnedTrophyCount} achievements earned",
            flush=True,
        )

        if not game_records:
            logger.warning(
                "No games found. This might be a private profile, an invalid username, "
                "or the user has no achievements yet."
            )

        return {
            "fullGames": game_records,
            "gameCount": len(game_records),
            "earnedTrophyCount": earnedTrophyCount,
            "totTrophyCount": totTrophyCount,
            "completeTrophyCount": completeTrophyCount,
            "totPlayTimeCount": 0,
        }

    except Exception as e:
        logger.error(f"RetroAchievements sync failed: {e}")
        print(f"RetroAchievements sync failed: {e}", flush=True)
        return {
            "fullGames": [],
            "gameCount": 0,
            "earnedTrophyCount": 0,
            "totTrophyCount": 0,
            "completeTrophyCount": 0,
            "totPlayTimeCount": 0,
            "internalError": str(e)
        }


def fetch_achievement_list(web_api_key, ra_username, ra_game_id, session=None):
    """Lista completa achievement RetroAchievements per un gioco (con stato utente).

    Ritorna una lista di dict serializzabili, o None in caso di fallimento.
    """
    if not (web_api_key and ra_username and ra_game_id):
        return None
    if session is None:
        session = create_robust_session()

    try:
        data = ra_api_request(
            session,
            web_api_key,
            "API_GetGameInfoAndUserProgress.php",
            params={"g": int(ra_game_id), "u": ra_username},
        )
        raw = (data or {}).get("Achievements") or {}
        achievements = []
        for ach in raw.values():
            badge_url = ach.get("BadgeURL") or ""
            if badge_url and not badge_url.startswith("http"):
                badge_url = f"https://media.retroachievements.org{badge_url}"
            achievements.append({
                "ra_id": ach.get("ID"),
                "name": ach.get("Title", ""),
                "description": ach.get("Description", ""),
                "badge_url": badge_url,
                "points": ach.get("Points", 0),
                "earned": bool(ach.get("DateEarned")),
                "earned_hardcore": bool(ach.get("DateEarnedHardcore")),
                "earned_date": ach.get("DateEarned"),
                "display_order": ach.get("DisplayOrder", 0),
                "type": ach.get("type"),
            })
        achievements.sort(key=lambda a: (a["display_order"] or 0))
        return achievements if achievements else None
    except Exception:
        return None
