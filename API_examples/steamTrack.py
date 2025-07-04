from steam_web_api import Steam
import json
import numpy as np
import pandas as pd
from tqdm import tqdm
import os
from dotenv import load_dotenv

load_dotenv()

def sync_steam(steam_api_key):
    steam = Steam(steam_api_key)

    user = steam.users.get_user_details("76561198074617013")

    print(
        "STEAMID: "
        + str(user["player"]["steamid"])
        + " NAME : "
        + str(user["player"]["personaname"])
    )

    steamId = str(user["player"]["steamid"])  # 76561198074617013

    listOfList = []
    
    totEarnedAchievement = 0
    totAchievement = 0


    # GAMES
    games = steam.users.get_owned_games(steamId)
    print("Game Count : " + str(games.get("game_count")))
    print("Recupero Dati : ")
    for i in tqdm(games.get("games")):
        listGame = [i.get("appid"), i.get("name"), i.get("playtime_forever")]
        # print("appId: " + str(i.get("appid")) + " / Name: " + str(i.get("name")) + " / Playtime: " + str(i.get("playtime_forever")))
        try:
            if i.get("playtime_forever") > 0:
                gameS = steam.apps.get_user_stats(steamId, i.get("appid"))
                achievements = steam.apps.get_user_achievements(steamId, i.get("appid"))
                g = steam.apps.get_app_details(i.get("appid"))
                totAchievement = int(
                    len(achievements.get("playerstats").get("achievements"))
                )
                earnedAchievement = len(gameS.get("playerstats").get("achievements"))
                totEarnedAchievement += earnedAchievement
                totAchievement += totAchievement
                # print("Tot Achievement : " + str(totAchievement))
                listGame.append(str(totAchievement))
                # print("Earned Achievement : " + str(earnedAchievement))
                listGame.append(str(earnedAchievement))
                if totAchievement > 0:
                    percAchievement = (earnedAchievement / totAchievement) * 100
                    # print("Achievement % : " + str(round(percAchievement, 2)) + "%")
                    listGame.append(str(round(percAchievement, 2)) + "%")
                else:
                    # print("Achievement % : 0 %")
                    listGame.append(str(0) + "%")
            else:
                # print("No Achievement Data")
                listGame.append(str(0))
                listGame.append(str(0))
                listGame.append(str(0) + "%")
        except:
            # print("No Achievement Data")
            listGame.append(str(0))
            listGame.append(str(0))
            listGame.append(str(0) + "%")
        listOfList.append(listGame)

    # TODO : organizzare dati in dataFrame

    arr = np.array(listOfList)
    df_games_steam = pd.DataFrame(
        arr,
        columns=[
            "appId",
            "Name",
            "Playtime",
            "TotAchievement",
            "EarnedAchievement",
            "Achievement%",
        ],
    )

    
    return {
        "fullGames": df_games_steam.to_dict(orient="records"),
        "gameCount": games.get("game_count"),
        "earnedTrophyCount": totEarnedAchievement,
        "totTrophyCount": totAchievement,
        "totPlayTimeCount": df_games_steam["Playtime"].sum(),
    }
