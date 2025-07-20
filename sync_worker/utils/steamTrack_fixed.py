# FIX LUIGI
import requests
import json
import numpy as np
import pandas as pd
from tqdm import tqdm
import os
import logging
import sys
import time
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

def sync_steam(steam_api_key, steam_id, logger=None):
    """Sincronizzazione Steam con gestione errori SSL migliorata"""
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
        
        listOfList = []
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
            
            listGame = [appid, name, playtime]
            totPlayTimeCount += playtime
            
            # Ottieni achievement solo se il gioco è stato giocato
            if playtime > 0:
                try:
                    # Ottieni achievement totali
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
                    
                    listGame.append(str(tot_achievements))
                    listGame.append(str(earned_achievements))
                    
                    if tot_achievements > 0:
                        perc_achievement = (earned_achievements / tot_achievements) * 100
                        listGame.append(f"{perc_achievement:.2f}%")
                    else:
                        listGame.append("0%")
                        
                except Exception as e:
                    if "403" in str(e):
                        logger.warning(f"Profile may be private or API key insufficient for achievements in {name}. Error: {e}")
                        print(f"Request failed: {e}", flush=True)
                    else:
                        logger.warning(f"Error getting achievements for {name}: {e}")
                    listGame.extend(["0", "0", "0%"])
            else:
                listGame.extend(["0", "0", "0%"])
            
            listOfList.append(listGame)
            time.sleep(0.5)  # Rate limiting
        
        # 4. Crea DataFrame e restituisci risultati
        arr = np.array(listOfList)
        df_games_steam = pd.DataFrame(
            arr,
            columns=[
                "title_id",
                "name", 
                "play_count",
                "totTrophy",
                "earnedTrophy",
                "percTrophy",
            ],
        )
        
        logger.info(f"Sync completed: {game_count} games, {totEarnedAchievement} achievements earned")
        print(f"Sync completed: {game_count} games, {totEarnedAchievement} achievements earned", flush=True)
        
        return {
            "fullGames": df_games_steam.to_dict(orient="records"),
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