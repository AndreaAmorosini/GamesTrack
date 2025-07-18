# FIX LUIGI

from psnawp_api import PSNAWP
from tqdm import tqdm
import pandas as pd
import numpy as np
import os
from psnawp_api.models import SearchDomain
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import time
import logging
import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
    
    return session

def sync_psn(npsso, logger=None):
    """Sincronizzazione PSN con gestione errori migliorata"""
    if logger is None:
        logger = logging.getLogger()
    
    logger.info("Starting PSN synchronization with improved error handling...")
    print("Starting PSN synchronization with improved error handling...", flush=True)
    
    try:
        # Crea oggetto PSNAWP con gestione errori
        psn = PSNAWP(npsso)
        
        # Profile di npsso owner
        client = psn.me()
        
        def get_np_communication_id(title_id):
            try:
                game_title = psn.game_title(title_id=title_id, account_id="me")
                product_id = game_title.get_details()[0].get("id", None)
                return {
                    "np_communication_id": game_title.np_communication_id,
                    "product_id": product_id,
                }
            except Exception as e:
                logger.warning(f"Error retrieving np_communication_id for title_id {title_id}: {e}")
                return {"np_communication_id": None, "product_id": None}

        def get_np_communication_id_with_timeout(title_id, timeout=10):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(get_np_communication_id, title_id)
                try:
                    return future.result(timeout=timeout)
                except TimeoutError:
                    logger.warning(f"Timeout getting np_communication_id for title_id {title_id}")
                    return {"np_communication_id": None, "product_id": None}

        listOfListGames = []
        listOfListTrophy = []

        gameCount = 0
        totPlayTimeCount = 0
        logger.info("Recupero Dati Giochi: ")
        print("Recupero Dati Giochi: ", flush=True)
        
        # Ottieni statistiche dei giochi
        try:
            title_stats = list(client.title_stats())
            logger.info(f"Found {len(title_stats)} games in title stats")
            
            for t in title_stats:
                logger.info("GAME: Title ID: " + str(t.title_id) + " / Name: " + str(t.name))
                print("GAME: Title ID: " + str(t.title_id) + " / Name: " + str(t.name), flush=True)
                
                ids = get_np_communication_id_with_timeout(t.title_id)
                np_communication_id = ids["np_communication_id"]
                product_id = ids["product_id"]
                
                console = t.category.name
                if console == "PS5":
                    console = 167
                elif console == "PS4":
                    console = 48
                else:
                    console = 9999
                
                listGame = [
                    t.title_id,
                    t.name,
                    t.image_url,
                    console,
                    t.play_count,
                    t.first_played_date_time,
                    t.last_played_date_time,
                    t.play_duration,
                    np_communication_id,
                    product_id
                ]
                
                if np_communication_id is not None:
                    listOfListGames.append(listGame)
                    gameCount += 1
                    totPlayTimeCount += int(t.play_duration.total_seconds())
                    time.sleep(1.5)  # Rate limiting
                    
        except Exception as e:
            logger.error(f"Error getting title stats: {e}")
            print(f"Error getting title stats: {e}", flush=True)

        np_communication_id_list = [
            game[8] for game in listOfListGames if game[8] is not None
        ]

        earnedTrophyCount = 0
        totTrophyCount = 0
        completeTrophyCount = 0
        logger.info("Recupero Dati da Trofei: ")
        
        # Ottieni trofei
        try:
            trophy_titles = list(client.trophy_titles())
            logger.info(f"Found {len(trophy_titles)} trophy titles")
            
            for tr in trophy_titles:
                product_id = next((game[9] for game in listOfListGames if game[8] == tr.np_communication_id), None)
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
                
                listGame = [
                    tr.np_communication_id,
                    tr.title_name,
                    (
                        tr.defined_trophies.bronze
                        + tr.defined_trophies.silver
                        + tr.defined_trophies.gold
                        + tr.defined_trophies.platinum
                    ),
                    (
                        tr.earned_trophies.bronze
                        + tr.earned_trophies.silver
                        + tr.earned_trophies.gold
                        + tr.earned_trophies.platinum
                    ),
                    (str(tr.progress) + "%"),
                ]
                listOfListTrophy.append(listGame)
                earnedTrophyCount += (
                    tr.earned_trophies.bronze
                    + tr.earned_trophies.silver
                    + tr.earned_trophies.gold
                    + tr.earned_trophies.platinum
                )
                totTrophyCount += (
                    tr.defined_trophies.bronze
                    + tr.defined_trophies.silver
                    + tr.defined_trophies.gold
                    + tr.defined_trophies.platinum
                )
                if tr.earned_trophies.platinum > 0:
                    completeTrophyCount += 1
                    
        except Exception as e:
            logger.error(f"Error getting trophy titles: {e}")
            print(f"Error getting trophy titles: {e}", flush=True)

        # Crea DataFrame con gestione casi vuoti
        if listOfListTrophy:
            df_trophy_psn = pd.DataFrame(
                np.array(listOfListTrophy),
                columns=[
                    "np_communication_id",
                    "title_name",
                    "totTrophy",
                    "earnedTrophy",
                    "percTrophy",
                ],
            )
        else:
            # DataFrame vuoto con le colonne corrette
            df_trophy_psn = pd.DataFrame(columns=[
                "np_communication_id",
                "title_name",
                "totTrophy",
                "earnedTrophy",
                "percTrophy",
            ])
            
        if listOfListGames:
            df_games_psn = pd.DataFrame(
                np.array(listOfListGames),
                columns=[
                    "title_id",
                    "name",
                    "image_url",
                    "console",
                    "play_count",
                    "first_played_date_time",
                    "last_played_date_time",
                    "play_duration",
                    "np_communication_id",
                    "product_id",
                ],
            )
        else:
            # DataFrame vuoto con le colonne corrette
            df_games_psn = pd.DataFrame(columns=[
                "title_id",
                "name",
                "image_url",
                "console",
                "play_count",
                "first_played_date_time",
                "last_played_date_time",
                "play_duration",
                "np_communication_id",
                "product_id",
            ])
        
        # Merge delle tabelle solo se ci sono dati
        if not df_games_psn.empty and not df_trophy_psn.empty:
            df_merged = pd.merge(df_games_psn, df_trophy_psn, on="np_communication_id", how="right")
            df_merged = df_merged.where(pd.notnull(df_merged), None)
        else:
            # Se uno dei due DataFrame è vuoto, usa l'altro o crea un DataFrame vuoto
            if not df_games_psn.empty:
                df_merged = df_games_psn
            elif not df_trophy_psn.empty:
                df_merged = df_trophy_psn
            else:
                # Entrambi vuoti, crea un DataFrame vuoto con tutte le colonne
                df_merged = pd.DataFrame(columns=[
                    "title_id", "name", "image_url", "console", "play_count",
                    "first_played_date_time", "last_played_date_time", "play_duration",
                    "np_communication_id", "product_id", "title_name", "totTrophy",
                    "earnedTrophy", "percTrophy"
                ])

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
            "fullGames": df_merged.to_dict(orient="records"),
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
# END FIX LUIGI