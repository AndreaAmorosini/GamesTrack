import time
import requests
from igdb.wrapper import IGDBWrapper
import json


class IGDBAutoAuthClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = 0  # Unix timestamp
        self.wrapper = None

    def _fetch_access_token(self):
        response = requests.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        self.token_expiry = int(time.time()) + expires_in - 60  # buffer before expiry
        self.wrapper = IGDBWrapper(self.client_id, self.access_token)

    def _ensure_token_valid(self):
        if not self.access_token or time.time() >= self.token_expiry:
            self._fetch_access_token()

    def query(self, endpoint: str, query: str):
        self._ensure_token_valid()
        return self.wrapper.api_request(endpoint, query)
    
    def query_games(self, query: str):
        self._ensure_token_valid()
        return self.query("games", query)
    
    def get_game_metadata(self, game_name: str):
        query = f'''
        fields 
        name,
        summary,
        storyline,
        genres.name,
        themes.name,
        keywords.name,
        platforms.name,
        release_dates.date,
        release_dates.human,
        release_dates.platform.name,
        first_release_date,
        involved_companies.company.name,
        involved_companies.developer,
        involved_companies.publisher,
        involved_companies.porting,
        involved_companies.supporting,
        cover.url,
        artworks.url,
        screenshots.url,
        videos.video_id,
        websites.url,
        websites.category,
        game_modes.name,
        player_perspectives.name,
        category,
        status,
        total_rating,
        total_rating_count,
        aggregated_rating,
        aggregated_rating_count,
        collection.name,
        franchise.name,
        similar_games.name;
        where name ~ *"{game_name}"* & category = 0;
        limit 1;
        '''
        result = self.query_games(query)
        result = json.loads(result)
        
        if "artworks" in result[0]:
            result[0]["artworks"] = [artwork["url"] for artwork in result[0]["artworks"]]
            
        if "game_modes" in result[0]:
            result[0]["game_modes"] = [mode["name"] for mode in result[0]["game_modes"]]
            
        if "genres" in result[0]:
            result[0]["genres"] = [genre["name"] for genre in result[0]["genres"]]
        
        if "involved_companies" in result[0]:
            result[0]["developer"] = next(
                (company["company"]["name"] for company in result[0]["involved_companies"] if company.get("developer")), "")
            result[0]["publisher"] = next(
                (company["company"]["name"] for company in result[0]["involved_companies"] if company.get("publisher")), "")
            
        if "platforms" in result[0]:
            result[0]["platforms"] = [platform["name"] for platform in result[0]["platforms"]]
            
        if "screenshots" in result[0]:
            result[0]["screenshots"] = [screenshot["url"] for screenshot in result[0]["screenshots"]]

        
        game_metadata = {
            "igdb_id": result[0].get("id"),
            "name": result[0].get("name"),
            "platforms": result[0].get("platforms", []),
            "genres": result[0].get("genres", []),
            "game_modes": result[0].get("game_modes", []),
            "release_date": result[0].get("release_dates", [])[0].get("human", "N/A"),
            "publisher": result[0].get("publisher", ""),
            "developer": result[0].get("developer", ""),
            "description": result[0].get("summary", ""),
            "cover_image": result[0].get("cover", {}).get("url", ""),
            "screenshots": result[0].get("screenshots", []),
            "artworks": result[0].get("artworks", []),
            "total_rating": result[0].get("total_rating", 0.0),
            "total_rating_count": result[0].get("total_rating_count", 0),
        }
        
        return game_metadata
