import os
import sys

parent_dir = os.path.dirname(os.getcwd())
wrapper_path = os.path.join(os.path.dirname(os.getcwd()), "RAWG_API_wrapper")
sys.path.append(wrapper_path)
from rawg_client import RAWGClient
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("RAWG_API_KEY")


client = RAWGClient(api_key=KEY)  # API Key from https://rawg.io/apidocs

results = client.search_games("Super Mario Odyssey")
game_id = results[0]["id"]
metadata = client.get_game_metadata(game_id)

print("TITOLO:", metadata["name"])
print("DATA USCITA:", metadata["released"])
print("PIATTAFORME:", metadata["platforms"])
print("GENERI:", metadata["genres"])
print("SVILUPPATORI:", metadata["developers"])
print("PUBLISHER:", metadata["publishers"])
print("IMMAGINE:", metadata["cover_image"])
print("DESCRIZIONE:", metadata["description"][:500])
