import os
from dotenv import load_dotenv
import sys

# sys.path.append("RAWG_API_wrapper")
from .RAWG_API_wrapper.rawg_client import RAWGClient

def get_metadata(search_term: str, api_key: str) -> dict:
    
    client = RAWGClient(
        api_key=api_key
    )  # API Key from https://rawg.io/apidocs

    results = client.search_games(search_term)
    game_id = results[0]["id"]
    metadata = client.get_game_metadata(game_id)

    return {
        "id": results[0]["id"],
        "name": metadata["name"],
        "release_date": metadata["released"],
        "platforms": metadata["platforms"],
        "genres": metadata["genres"],
        "developers": metadata["developers"],
        "publishers": metadata["publishers"],
        "cover_image": metadata["cover_image"],
        "description": metadata["description"],
    }
    
# if __name__ == "__main__":
#     dict = get_metadata("The Witcher 3", "a3f6c2755cdf49b49911ec4576c3e6f7")
#     print(dict)