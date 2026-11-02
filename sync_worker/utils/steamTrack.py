# FIX LUIGI
import requests
import json
import os
import logging
import sys
import time
from datetime import datetime
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disabilita gli avvisi SSL per debug
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_robust_session():
    """Crea una sessione requests con configurazioni robuste per SSL"""
    session = requests.Session()

    # Configura retry con backoff esponenziale
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    # Adapter con retry e timeout
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Headers per evitare problemi di user-agent
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    return session

def steam_api_request(session, url, params=None, timeout=30):
    """Esegue una richiesta all'API Steam con gestione errori robusta"""
    try:
        # Primo tentativo con SSL normale
        response = session.get(url, params=params, timeout=timeout, verify=True)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.SSLError as e:
        print(f"SSL Error, trying without verification: {e}")
        try:
            # Secondo tentativo senza verifica SSL
            response = session.get(url, params=params, timeout=timeout, verify=False)
            response.raise_for_status()
            return response.json()
        except Exception as e2:
            print(f"SSL fallback also failed: {e2}")
            raise
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        raise

def load_schema_cache(db, played_appids, logger):
    """Carica dalla cache MongoDB i totali achievement degli schemi già noti"""
    schema_cache = {}
    if db is None or not played_appids:
        return schema_cache
    try:
        for doc in db["steam_schema_cache"].find(
            {"steam_app_id": {"$in": played_appids}},
            {"steam_app_id": 1, "total_achievements": 1},
        ):
            schema_cache[doc["steam_app_id"]] = doc["total_achievements"]
        if schema_cache:
            logger.info(
                f"Achievement schema cache hits: {len(schema_cache)}/{len(played_appids)}"
            )
    except Exception as e:
        logger.warning(f"Could not load achievement schema cache: {e}")
        schema_cache = {}
    return schema_cache

def store_schema_cache(db, appid, total_achievements, logger):
    """Salva in cache il totale achievement di uno schema appena scaricato"""
    if db is None:
        return
    try:
        db["steam_schema_cache"].update_one(
            {"steam_app_id": appid},
            {
                "$set": {
                    "steam_app_id": appid,
                    "total_achievements": total_achievements,
                    "updated_at": datetime.now(),
                }
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"Could not store achievement schema for appid {appid}: {e}")

def sync_steam(steam_api_key, steam_id, logger=None, db=None):
    """Sincronizzazione Steam con gestione errori SSL migliorata.

    db: client MongoDB opzionale, usato per la cache degli schemi achievement
    (GetSchemaForGame cambia raramente: il totale viene salvato e riusato nei sync successivi)
    """
    if logger is None:
        logger = logging.getLogger()

    logger.info("Starting Steam synchronization with improved SSL handling...")
    print("Starting Steam synchronization with improved SSL handling...", flush=True)

    # Crea sessione robusta
    session = create_robust_session()

    try:
        # 1. Ottieni dettagli utente
        logger.info(f"Getting user details for Steam ID: {steam_id}")
        user_url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
        user_params = {
            'key': steam_api_key,
            'steamids': steam_id
        }

        user_data = steam_api_request(session, user_url, user_params)

        if not user_data.get('response', {}).get('players'):
            logger.error(f"User with Steam ID {steam_id} not found on Steam.")
            return {
                "fullGames": [],
                "gameCount": 0,
                "earnedTrophyCount": 0,
                "totTrophyCount": 0,
                "totPlayTimeCount": 0,
                "internalError": "User not found"
            }

        user = user_data['response']['players'][0]
        logger.info(f"STEAMID: {user['steamid']} NAME: {user['personaname']}")
        print(f"STEAMID: {user['steamid']} NAME: {user['personaname']}", flush=True)

        # 2. Ottieni giochi posseduti
        logger.info("Getting owned games...")
        games_url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        games_params = {
            'key': steam_api_key,
            'steamid': steam_id,
            'include_appinfo': 1,
            'include_played_free_games': 1
        }

        games_data = steam_api_request(session, games_url, games_params)
        games_response = games_data.get('response', {})
        games = games_response.get('games', [])
        game_count = games_response.get('game_count', 0)

        logger.info(f"Game Count: {game_count}")
        print(f"Game Count: {game_count}", flush=True)

        # Cache degli schemi achievement: solo per i giochi effettivamente giocati
        played_appids = [
            g.get('appid') for g in games if g.get('playtime_forever', 0) > 0
        ]
        schema_cache = load_schema_cache(db, played_appids, logger)

        game_records = []
        totEarnedAchievement = 0
        totAchievement = 0
        totPlayTimeCount = 0

        # 3. Processa ogni gioco
        for i, game in enumerate(games):
            appid = game.get('appid')
            name = game.get('name', 'Unknown')
            playtime = game.get('playtime_forever', 0)

            logger.info(f"Processing game {i+1}/{len(games)}: {name} (ID: {appid})")
            print(f"Processing game {i+1}/{len(games)}: {name} (ID: {appid})", flush=True)

            record = {
                "title_id": appid,
                "name": name,
                "play_count": playtime,
            }
            totPlayTimeCount += playtime

            # Ottieni achievement solo se il gioco è stato giocato
            if playtime > 0:
                try:
                    # Totale achievement: dalla cache se noto, altrimenti da GetSchemaForGame
                    if appid in schema_cache:
                        tot_achievements = schema_cache[appid]
                    else:
                        achievements_url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
                        achievements_params = {
                            'key': steam_api_key,
                            'appid': appid
                        }

                        achievements_data = steam_api_request(session, achievements_url, achievements_params)
                        game_schema = achievements_data.get('game', {})
                        available_stats = game_schema.get('availableGameStats', {})
                        achievements = available_stats.get('achievements', [])
                        tot_achievements = len(achievements)

                        schema_cache[appid] = tot_achievements
                        store_schema_cache(db, appid, tot_achievements, logger)

                    # Ottieni achievement ottenuti
                    user_achievements_url = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/"
                    user_achievements_params = {
                        'key': steam_api_key,
                        'steamid': steam_id,
                        'appid': appid
                    }

                    user_achievements_data = steam_api_request(session, user_achievements_url, user_achievements_params)
                    player_stats = user_achievements_data.get('playerstats', {})
                    earned_achievements = len([a for a in player_stats.get('achievements', []) if a.get('achieved', 0) == 1])

                    totEarnedAchievement += earned_achievements
                    totAchievement += tot_achievements

                    record["totTrophy"] = tot_achievements
                    record["earnedTrophy"] = earned_achievements

                    if tot_achievements > 0:
                        perc_achievement = (earned_achievements / tot_achievements) * 100
                        record["percTrophy"] = f"{perc_achievement:.2f}%"
                    else:
                        record["percTrophy"] = "0%"

                except Exception as e:
                    if "403" in str(e):
                        logger.warning(f"Profile may be private or API key insufficient for achievements in {name}. Error: {e}")
                        print(f"Request failed: {e}", flush=True)
                    else:
                        logger.warning(f"Error getting achievements for {name}: {e}")
                    record.update({"totTrophy": 0, "earnedTrophy": 0, "percTrophy": "0%"})
            else:
                record.update({"totTrophy": 0, "earnedTrophy": 0, "percTrophy": "0%"})

            game_records.append(record)
            time.sleep(0.5)  # Rate limiting

        logger.info(f"Sync completed: {game_count} games, {totEarnedAchievement} achievements earned")
        print(f"Sync completed: {game_count} games, {totEarnedAchievement} achievements earned", flush=True)

        return {
            "fullGames": game_records,
            "gameCount": game_count,
            "earnedTrophyCount": totEarnedAchievement,
            "totTrophyCount": totAchievement,
            "totPlayTimeCount": totPlayTimeCount,
        }

    except Exception as e:
        logger.error(f"Steam sync failed: {e}")
        print(f"Steam sync failed: {e}", flush=True)
        return {
            "fullGames": [],
            "gameCount": 0,
            "earnedTrophyCount": 0,
            "totTrophyCount": 0,
            "totPlayTimeCount": 0,
            "internalError": str(e)
        }
# END FIX LUIGI


def fetch_achievement_list(steam_api_key, steam_id, appid, session=None):
    """Lista completa achievement Steam con stato utente (schema + progresso).

    Ritorna una lista di dict serializzabili, o None in caso di fallimento.
    """
    if not (steam_api_key and steam_id and appid):
        return None
    if session is None:
        session = create_robust_session()

    try:
        schema_data = steam_api_request(
            session,
            "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/",
            {"key": steam_api_key, "appid": int(appid)},
        )
        schema = (schema_data.get("availableGameStats", {}) or {}).get("achievements", []) or []

        user_data = steam_api_request(
            session,
            "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/",
            {"key": steam_api_key, "steamid": str(steam_id), "appid": int(appid)},
        )
        player_stats = user_data.get("playerstats", {}) or {}
        achieved_map = {
            a.get("name"): a for a in (player_stats.get("achievements", []) or [])
        }

        achievements = []
        for entry in schema:
            api_name = entry.get("name")
            progress = achieved_map.get(api_name, {})
            unlock_time = progress.get("unlocktime")
            achievements.append({
                "name": entry.get("displayName") or api_name,
                "description": entry.get("description") or "",
                "icon": entry.get("icon") or "",
                "icon_gray": entry.get("icongray") or "",
                "achieved": bool(progress.get("achieved")),
                "unlock_time": (
                    datetime.fromtimestamp(unlock_time).strftime("%Y-%m-%d")
                    if unlock_time else None
                ),
            })
        return achievements if achievements else None
    except Exception as e:
        logging.getLogger().warning(f"Trophy list fetch failed for appid {appid}: {e}")
        return None
