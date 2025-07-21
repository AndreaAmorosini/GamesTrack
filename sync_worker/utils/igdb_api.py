import time
import requests
from igdb.wrapper import IGDBWrapper
import json
import pycountry
import logging

logger = logging.getLogger(__name__)

def country_name_from_numeric_code(numeric_code):
    # Convert to zero-padded 3-digit string, as per ISO 3166-1 standard
    code_str = str(numeric_code).zfill(3)
    country = pycountry.countries.get(numeric=code_str)
    return country.name if country else None


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
    
    def get_game_metadata(self, game_name: str, external_id: str = None):
        if external_id is not None:
            external_game_query = f'''
            fields
            id,
            game,
            name,
            uid,
            category;
            where uid="{external_id}" & category = (1, 4, 8, 9, 11, 10, 36);
            '''       
            external_game_result = self.query("external_games", external_game_query)
            external_game_result = json.loads(external_game_result)
            
            logger.info(f"External Game Result: {external_game_result}")
            
            game_id = external_game_result[0].get("game", None) if external_game_result else None
        else:
            game_id = None
        
        query = '''
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
        '''

        if game_id:
            query += f'where id = {game_id};'
        else:
            query += f'''
            where name ~ *"{game_name}"* & category = 0;
            limit 1;
            '''
        result = self.query_games(query)
        if result is None or result == "[]":
            logger.info(f"No game found for name: {game_name} with external ID: {external_id}")
            return None
        result = json.loads(result)
        
        try:
            if "artworks" in result[0]:
                result[0]["artworks"] = [artwork["url"] for artwork in result[0]["artworks"]]
                
            if "game_modes" in result[0]:
                result[0]["game_modes"] = [mode["id"] for mode in result[0]["game_modes"]]
                
            if "genres" in result[0]:
                result[0]["genres"] = [genre["id"] for genre in result[0]["genres"]]
            
            if "involved_companies" in result[0]:
                result[0]["developer"] = next(
                    (company["company"]["id"] for company in result[0]["involved_companies"] if company.get("developer")), "")
                result[0]["publisher"] = next(
                    (company["company"]["id"] for company in result[0]["involved_companies"] if company.get("publisher")), "")
                
            if "platforms" in result[0]:
                result[0]["platforms"] = [platform["id"] for platform in result[0]["platforms"]]
                
            if "screenshots" in result[0]:
                result[0]["screenshots"] = [screenshot["url"] for screenshot in result[0]["screenshots"]]
                
        except IndexError as e:
            logger.error(f"IndexError: {e} - Result: {result}")
            return None
          
        
        game_metadata = {
            "igdb_id": result[0].get("id"),
            "name": result[0].get("name"),
            "platforms": result[0].get("platforms", []),
            "genres": result[0].get("genres", []),
            "game_modes": result[0].get("game_modes", []),
            "release_date": result[0].get("first_release_date", ""),
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
    
    def get_all_game_genres(self):
        offset = 0
        genres = []
        while True:
            query = f'''
            fields id, name;
            limit 500;
            offset {offset};
            '''
            result = self.query("genres", query)
            result = json.loads(result)
            if not result:
                break
            for genre in result:
                gen = {
                    "igdb_id": genre["id"],
                    "genre_name": genre["name"]
                }
                genres.append(gen)
            offset += 500
        return genres
    
    def get_all_game_platforms(self):
        offset = 0
        platforms = []
        while True:
            query = f'''
            fields id, name, abbreviation, generation;
            limit 500;
            offset {offset};
            '''
            result = self.query("platforms", query)
            result = json.loads(result)
            if not result:
                break
            for platform in result:
                plat = {
                    "igdb_id": platform["id"],
                    "platform_name": platform["name"],
                    "abbreviation": platform.get("abbreviation", ""),
                    "generation": platform.get("generation", 0)
                }
                platforms.append(plat)
            offset += 500
        return platforms

    def get_all_game_modes(self):
        offset = 0
        modes = []
        while True:
            query = f'''
            fields id, name;
            limit 500;
            offset {offset};
            '''
            result = self.query("game_modes", query)
            result = json.loads(result)
            if not result:
                break
            for mode in result:
                mod = {
                    "igdb_id": mode["id"],
                    "game_mode_name": mode["name"]
                }
                modes.append(mod)
            offset += 500
        return modes
    
    def get_all_game_companies(self):
        offset = 0
        companies = []
        while True:
            query = f'''
            fields id, name, country;
            limit 500;
            offset {offset};
            '''
            result = self.query("companies", query)
            result = json.loads(result)
            if not result:
                break
            for company in result:
                if "duplicate" in company["name"].lower():
                    logger.warning(f"Skipping duplicate company: {company['name']}")
                    continue 
                country_name = country_name_from_numeric_code(company.get("country", 0))
                comp = {
                    "igdb_id": company["id"],
                    "company_name": company["name"],
                    "country": country_name
                }
                companies.append(comp)
            offset += 500
        return companies
