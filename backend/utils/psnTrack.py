from psnawp_api import PSNAWP
from tqdm import tqdm
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv


def sync_psn(npsso):
    # Create a PSNAWP object
    psn = PSNAWP(npsso)

    # Profile of npsso owner
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
            # print(f"Error retrieving np_communication_id for title_id {title_id}: {e}")
            return {"np_communication_id": None, "product_id": None}

    listOfListGames = []
    listOfListTrophy = []


    gameCount = 0
    totPlayTimeCount = 0
    for t in client.title_stats():
        ids = get_np_communication_id(t.title_id)
        np_communication_id = ids["np_communication_id"]
        product_id = ids["product_id"]
        listGame = [
            t.title_id,
            t.name,
            t.image_url,
            t.category,
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
            totPlayTimeCount += t.play_duration

    earnedTrophyCount = 0
    totTrophyCount = 0
    completeTrophyCount = 0
    for tr in tqdm(client.trophy_titles()):
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
            tr.np_title_id,
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

    df_trophy_psn = pd.DataFrame(
        np.array(listOfListTrophy),
        columns=[
            "np_communication_id",
            "title_name",
            "totTrophy",
            "earnedTrophy",
            "percTrophy",
            "np_title_id",
        ],
    )
    df_games_psn = pd.DataFrame(
        np.array(listOfListGames),
        columns=[
            "title_id",
            "name",
            "image_url",
            "category",
            "play_count",
            "first_played_date_time",
            "last_played_date_time",
            "play_duration",
            "np_communication_id",
            "product_id",
        ],
    )
    # In caso fare join tra le due tabelle per ottenere la lista completa di giochi e dove non c'e la category PS5 o PS4 mettere Ps3
    #Join tra lke due tabelle
    # Si fa il merge in maniera right per includere anche i giochi PS3 da riempirne i dati poi tramite metadata

    df_merged = pd.merge(df_games_psn, df_trophy_psn, on="np_communication_id", how="right")
    df_merged


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
    
    return {
        "fullGames": df_merged.to_dict(orient="records"),
        "gameCount": gameCount,
        "earnedTrophyCount": earnedTrophyCount,
        "totTrophyCount": totTrophyCount,
        "completeTrophyCount": completeTrophyCount,
        "totPlayTimeCount": totPlayTimeCount,
    }