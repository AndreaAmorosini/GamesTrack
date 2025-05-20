from steam import Steam
from decouple import config
import json
import numpy as np
import pandas as pd
from tqdm import tqdm

KEY = config("STEAM_API_KEY")
steam = Steam(KEY)

user = steam.users.get_user_details("76561198074617013")
#print(user)
#print(user["player"])
#print("PLAYER DETAILS")
#for i in user["player"]:
    #print(str(i) + " : " + str(user["player"][i]))

print("STEAMID: " + str(user["player"]["steamid"]) + " NAME : " + str(user["player"]["personaname"]))


#friends = steam.users.get_user_friends_list("76561198074617013")
#print(friends)

steamId = str(user["player"]["steamid"]) # 76561198074617013

listOfList = []


#GAMES
games = steam.users.get_owned_games(steamId)
print("Game Count : " + str(games.get("game_count")))
print("Recupero Dati : ")
for i in tqdm(games.get("games")):
    listGame = [i.get("appid"), i.get("name"), i.get("playtime_forever")]
    #print("appId: " + str(i.get("appid")) + " / Name: " + str(i.get("name")) + " / Playtime: " + str(i.get("playtime_forever")))
    try:
        if i.get("playtime_forever") > 0:
            gameS = steam.apps.get_user_stats(steamId, i.get("appid"))
            g = steam.apps.get_app_details(i.get("appid"))
            totAchievement = int(g.split("achievements")[1].split("total")[1].split(",")[0].split(" ")[1])
            earnedAchievement = len(gameS.get("playerstats").get("achievements"))
            #print("Tot Achievement : " + str(totAchievement))
            listGame.append(str(totAchievement))
            #print("Earned Achievement : " + str(earnedAchievement))
            listGame.append(str(earnedAchievement))
            if totAchievement > 0:
                percAchievement = (earnedAchievement / totAchievement) * 100
                #print("Achievement % : " + str(round(percAchievement, 2)) + "%")
                listGame.append(str(round(percAchievement, 2)) + "%")
            else:
                #print("Achievement % : 0 %")
                listGame.append(str(0) + "%")
        else :
            #print("No Achievement Data")
            listGame.append(str(0))
            listGame.append(str(0))
            listGame.append(str(0) + "%")
    except:
        #print("No Achievement Data")
        listGame.append(str(0))
        listGame.append(str(0))
        listGame.append(str(0) + "%")
    listOfList.append(listGame)

#TODO : organizzare dati in dataFrame

arr = np.array(listOfList)
df = pd.DataFrame(arr, columns=["appId", "Name", "Playtime", "TotAchievement", "EarnedAchievement", "Achievement%"])
print(df)




searchGame = steam.apps.search_games("Dota 2")
#print(searchGame)

gameAchievement = steam.apps.get_user_achievements("76561198074617013", 220)
#print(gameAchievement)

gameStats = steam.apps.get_user_stats("76561198074617013", 220)
#print(gameStats)

gameDetail = steam.apps.get_app_details(220)
#print(gameDetail)
