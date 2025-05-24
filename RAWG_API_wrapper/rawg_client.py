# rawg_client.py

import requests


class RAWGClient:
    BASE_URL = "https://api.rawg.io/api"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _get(self, endpoint: str, params=None):
        if params is None:
            params = {}
        params["key"] = self.api_key
        response = requests.get(f"{self.BASE_URL}/{endpoint}", params=params)
        response.raise_for_status()
        return response.json()

    def search_games(self, query: str, page: int = 1, page_size: int = 10):
        params = {"search": query, "page": page, "page_size": page_size}
        data = self._get("games", params)
        return data["results"]

    def get_game(self, game_id: int):
        return self._get(f"games/{game_id}")

    def get_game_screenshots(self, game_id: int):
        data = self._get(f"games/{game_id}/screenshots")
        return data["results"]
    
    def get_game_metadata(self, game_id: int):
        data = self.get_game(game_id)
        return {
            "id": data["id"],
            "name": data["name"],
            "released": data.get("released", ""),
            "platforms": [p["platform"]["name"] for p in data.get("platforms", [])],
            "description": data.get("description_raw", ""),
            "developers": [d["name"] for d in data.get("developers", [])],
            "publishers": [p["name"] for p in data.get("publishers", [])],
            "genres": [g["name"] for g in data.get("genres", [])],
            "cover_image": data.get("background_image", ""),
        }
