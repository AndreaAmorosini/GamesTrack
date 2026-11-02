import time
import string
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


def normalize_name(name):
    if not name:
        return ""
    name = name.translate(str.maketrans("", "", string.punctuation))
    return " ".join(name.lower().split())


class IGDBAutoAuthClient:
    # Campi richiesti a IGDB per i metadati completi di un gioco
    GAME_FIELDS = '''
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
        game_type,
        status,
        total_rating,
        total_rating_count,
        aggregated_rating,
        aggregated_rating_count,
        collection.name,
        franchise.name,
        similar_games.name;
        '''

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

    @staticmethod
    def _chunks(seq, size):
        for i in range(0, len(seq), size):
            yield seq[i:i + size]

    def _process_game_result(self, r):
        """Normalizza un risultato 'games' di IGDB nel formato dei metadati interni"""
        try:
            if "artworks" in r:
                r["artworks"] = [artwork["url"] for artwork in r["artworks"]]

            if "game_modes" in r:
                r["game_modes"] = [mode["id"] for mode in r["game_modes"]]

            if "genres" in r:
                r["genres"] = [genre["id"] for genre in r["genres"]]

            if "involved_companies" in r:
                r["developer"] = next(
                    (company["company"]["id"] for company in r["involved_companies"] if company.get("developer")), "")
                r["publisher"] = next(
                    (company["company"]["id"] for company in r["involved_companies"] if company.get("publisher")), "")

            if "platforms" in r:
                r["platforms"] = [platform["id"] for platform in r["platforms"]]

            if "screenshots" in r:
                r["screenshots"] = [screenshot["url"] for screenshot in r["screenshots"]]
        except (IndexError, KeyError, TypeError) as e:
            logger.error(f"Error processing game result: {e} - Result: {r}")
            return None

        return {
            "igdb_id": r.get("id"),
            "name": r.get("name"),
            "platforms": r.get("platforms", []),
            "genres": r.get("genres", []),
            "game_modes": r.get("game_modes", []),
            "release_date": r.get("first_release_date", ""),
            "publisher": r.get("publisher", ""),
            "developer": r.get("developer", ""),
            "description": r.get("summary", ""),
            "cover_image": r.get("cover", {}).get("url", ""),
            "screenshots": r.get("screenshots", []),
            "artworks": r.get("artworks", []),
            "total_rating": r.get("total_rating", 0.0),
            "total_rating_count": r.get("total_rating_count", 0),
        }

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

        if game_id:
            query = f'fields {self.GAME_FIELDS} where id = {game_id};'
        else:
            query = f'fields {self.GAME_FIELDS} where name ~ *"{game_name}"* & game_type = 0; limit 1;'

        result = self.query_games(query)
        if result is None or result == "[]":
            logger.info(f"No game found for name: {game_name} with external ID: {external_id}")
            return None
        result = json.loads(result)
        if not result:
            logger.info(f"No game found for name: {game_name} with external ID: {external_id}")
            return None

        return self._process_game_result(result[0])

    def get_games_metadata_batch(self, game_requests, chunk_size=50, name_chunk_size=20):
        """
        Recupera i metadati per un batch di giochi con poche richieste IGDB aggregate
        invece di una chiamata per gioco (il rate limit IGDB e' di 4 richieste/secondo).

        game_requests: lista di tuple (game_name, external_id)
        Ritorna: dict con chiave (game_name.lower(), external_id) -> metadata dict o None
        """
        results = {}

        if not game_requests:
            return results

        # 1) Lookup per external_id: una sola query external_games per chunk di ID
        with_ext = [(name, ext) for name, ext in game_requests if ext is not None]
        ext_to_game_id = {}
        for chunk in self._chunks(with_ext, chunk_size):
            uids = ", ".join(f'"{ext}"' for _, ext in chunk)
            query = f'''
            fields id, game, uid, category;
            where category = (1, 4, 5, 8, 9, 11, 10, 36) & uid = ({uids});
            limit 500;
            '''
            try:
                raw = self.query("external_games", query)
                rows = json.loads(raw) if raw and raw != "[]" else []
            except Exception as e:
                logger.warning(f"Batch external_games lookup failed: {e}")
                rows = []
            for row in rows:
                if row.get("uid") is not None and row.get("game") is not None:
                    ext_to_game_id.setdefault(str(row["uid"]), row["game"])
            time.sleep(0.4)  # rate limit IGDB: max 4 richieste/secondo

        # chiave -> game_id IGDB risolto finora (chiavi sempre (name.lower(), external_id))
        key_to_game_id = {}
        pending_by_name = []
        for name, ext in with_ext:
            game_id = ext_to_game_id.get(str(ext))
            if game_id is not None:
                key_to_game_id[(name.lower(), ext)] = game_id
            else:
                pending_by_name.append((name.lower(), ext))
        for name, ext in game_requests:
            if ext is None:
                pending_by_name.append((name.lower(), ext))

        # 2) Lookup per nome in batch: fuzzy match, poi assegnazione per nome normalizzato
        name_index = {}
        for name, ext in pending_by_name:
            name_index.setdefault(normalize_name(name), (name, ext))

        for chunk in self._chunks(list(name_index.keys()), name_chunk_size):
            conditions = " | ".join(
                f'name ~ *"{name}"*' for name in chunk
            )
            query = f'''
            fields id, name;
            where game_type = 0 & ({conditions});
            limit 500;
            '''
            try:
                raw = self.query_games(query)
                rows = json.loads(raw) if raw and raw != "[]" else []
            except Exception as e:
                logger.warning(f"Batch name lookup failed: {e}")
                rows = []
            for row in rows:
                key = name_index.get(normalize_name(row.get("name", "")))
                if key is not None and key not in key_to_game_id:
                    key_to_game_id[key] = row["id"]
            time.sleep(0.4)  # rate limit IGDB: max 4 richieste/secondo

        # 3) Metadati completi in batch per tutti gli id risolti
        id_to_keys = {}
        for key, game_id in key_to_game_id.items():
            id_to_keys.setdefault(game_id, []).append(key)

        for game_ids in self._chunks(list(id_to_keys.keys()), chunk_size):
            ids = ", ".join(str(gid) for gid in game_ids)
            query = f'fields {self.GAME_FIELDS} where id = ({ids}); limit {len(game_ids)};'
            try:
                raw = self.query_games(query)
                rows = json.loads(raw) if raw and raw != "[]" else []
            except Exception as e:
                logger.warning(f"Batch games metadata lookup failed: {e}")
                rows = []
            for row in rows:
                metadata = self._process_game_result(row)
                for key in id_to_keys.get(row.get("id"), []):
                    results[key] = metadata
            time.sleep(0.4)  # rate limit IGDB: max 4 richieste/secondo

        # Chiavi non risolte: None, il chiamante puo' usare il fallback per-gioco
        for name, ext in game_requests:
            results.setdefault((name.lower(), ext), None)

        return results

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
