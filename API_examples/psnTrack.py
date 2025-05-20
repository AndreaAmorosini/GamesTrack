from psnawp_api import PSNAWP
from tqdm import tqdm
import pandas as pd
import numpy as np

# Get your npsso from https://psnprofiles.com/psnawp
npsso = ""
# Create a PSNAWP object
psn = PSNAWP(npsso)

# Profile of npsso owner
client = psn.me()
print("account_Id : " + client.account_id + ", online_id : " + client.online_id)
print("totTrophies : " + str(client.trophy_summary().earned_trophies.bronze + client.trophy_summary().earned_trophies.silver + client.trophy_summary().earned_trophies.gold + client.trophy_summary().earned_trophies.platinum))

listOfList = []



#gameCount = 0
# for t in client.title_stats():
#    print("name : " + t.name + " , title_id : " + str(t.title_id) + " , play_count : " + str(t.play_count) + " ,total_items_count : " + str(t.total_items_count))
#    gameCount += 1

trophyCount = 0
for tr in tqdm(client.trophy_titles()):
    listGame = [tr.np_communication_id, tr.title_name,
                (tr.defined_trophies.bronze + tr.defined_trophies.silver + tr.defined_trophies.gold + tr.defined_trophies.platinum),
                (tr.earned_trophies.bronze + tr.earned_trophies.silver + tr.earned_trophies.gold + tr.earned_trophies.platinum),
                (str(tr.progress) + "%")]
    listOfList.append(listGame)
    trophyCount += 1

arr = np.array(listOfList)
df = pd.DataFrame(arr, columns=["np_communication_id", "title_name", "totTrophy", "earnedTrophy", "percTrophy"])
#print("Game Count : " + str(gameCount))
print("Game Count : " + str(trophyCount))
print(df)

