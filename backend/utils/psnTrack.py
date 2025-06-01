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
    # print("account_Id : " + client.account_id + ", online_id : " + client.online_id)
    # print(
    #     "totTrophies : "
    #     + str(
    #         client.trophy_summary().earned_trophies.bronze
    #         + client.trophy_summary().earned_trophies.silver
    #         + client.trophy_summary().earned_trophies.gold
    #         + client.trophy_summary().earned_trophies.platinum
    #     )
    # )

    listOfListGames = []
    listOfListTrophy = []


    gameCount = 0
    totPlayTimeCount = 0
    for t in client.title_stats():
        # print("name : " + t.name + " , title_id : " + str(t.title_id) + " , play_count : " + str(t.play_count) + " ,total_items_count : " + str(t.total_items_count))
        listGame = [
            t.title_id,
            t.name,
            t.image_url,
            t.category,
            t.play_count,
            t.first_played_date_time,
            t.last_played_date_time,
            t.play_duration,
        ]
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
        ],
    )
    # In caso fare join tra le due tabelle per ottenere la lista completa di giochi e dove non c'e la category PS5 o PS4 mettere Ps3

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
        "gameCount": gameCount,
        "earnedTrophyCount": earnedTrophyCount,
        "totTrophyCount": totTrophyCount,
        "completeTrophyCount": completeTrophyCount,
        "totPlayTimeCount": totPlayTimeCount,
    }

    # df_games_psn
