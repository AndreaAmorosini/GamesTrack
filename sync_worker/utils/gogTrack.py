"""Sincronizzazione GOG tramite la Galaxy API non ufficiale.

Flow di autenticazione (documentato dalla community, gogapidocs.readthedocs.io):
1. GET auth.gog.com/auth -> pagina di login con token CSRF
2. POST login.gog.com/login_check con username/password + CSRF
3. Codice di autorizzazione dal redirect -> token OAuth da auth.gog.com/token
4. userData.json per l'user id -> api.gog.com/v2/users/{uid}/games per la libreria

Limiti noti:
- Account protetti da 2FA non supportati (il secondo fattore non è previsto
  nello schema credenziali dell'app): la sync fallisce con errore esplicito.
- GOG non espone statistiche di gioco (tempo/achievement): i record hanno
  play_count ed earnedTrophy a 0.
- Le credenziali (username in platform_id, password in api_key) sono salvate
  in chiaro nel DB, come già avviene per l'NPSSO PSN.
"""

import logging
import re
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Credenziali client pubbliche del client GOG Galaxy (stesse usate da
# galaxy-integrations e gogdl); sovrascrivibili via variabili d'ambiente
import os

GOG_CLIENT_ID = os.getenv("GOG_CLIENT_ID", "46899977096215655")
GOG_CLIENT_SECRET = os.getenv("GOG_CLIENT_SECRET", "9d85c43b148649baa8e57c1e0f4f8a4b")
GOG_AUTH_URL = "https://auth.gog.com"
GOG_LOGIN_URL = "https://login.gog.com"
GOG_EMBED_URL = "https://embed.gog.com"
GOG_API_URL = "https://api.gog.com"
GOG_REDIRECT_URI = "https://embed.gog.com/on_login_success?origin=client"

IGDB_PLATFORM_PC = 6  # PC (Windows): i giochi GOG sono titoli PC


def create_robust_session():
    """Crea una sessione requests con configurazioni robuste"""
    session = requests.Session()

    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def _extract_csrf_token(html):
    """Estrae il token CSRF login[_token] dalla pagina di login"""
    match = re.search(
        r'name="login\[_token\]"\s+value="([^"]+)"', html
    )
    if match:
        return match.group(1)
    match = re.search(
        r'value="([^"]+)"\s+name="login\[_token\]"', html
    )
    return match.group(1) if match else None


def _extract_authorization_code(location):
    """Estrae il code di autorizzazione dall'URL di redirect"""
    if not location:
        return None
    match = re.search(r"[?&]code=([^&]+)", location)
    return match.group(1) if match else None


def gog_login(session, username, password, logger=None):
    """Esegue il login GOG e ritorna un access token OAuth.

    Solleva RuntimeError con messaggio esplicito in caso di credenziali
    errate, 2FA richiesto o cambio del flow di login.
    """
    if logger is None:
        logger = logging.getLogger()

    # 1. Pagina di login (ottiene cookie di sessione e CSRF)
    auth_page = session.get(
        f"{GOG_AUTH_URL}/auth",
        params={
            "client_id": GOG_CLIENT_ID,
            "redirect_uri": GOG_REDIRECT_URI,
            "response_type": "code",
            "layout": "client2",
        },
        timeout=30,
    )
    auth_page.raise_for_status()
    csrf_token = _extract_csrf_token(auth_page.text)
    if not csrf_token:
        raise RuntimeError("GOG login page changed: CSRF token not found")

    # 2. POST credenziali
    login_response = session.post(
        f"{GOG_LOGIN_URL}/login_check",
        data={
            "login[username]": username,
            "login[password]": password,
            "login[_token]": csrf_token,
        },
        timeout=30,
        allow_redirects=False,
    )

    # Alcuni flow rispondono con redirect intermedio su login.gog.com
    location = login_response.headers.get("Location", "")
    if login_response.status_code == 200:
        # Se la risposta contiene il form del secondo fattore, la 2FA è attiva
        if "second_step_authentication" in login_response.text:
            raise RuntimeError(
                "GOG account has two-factor authentication enabled, which is "
                "not supported: use an account without 2FA or create an app password"
            )
        raise RuntimeError("GOG login failed: check username and password")

    auth_code = _extract_authorization_code(location)
    if not auth_code and location:
        # Segui il redirect intermedio finché non troviamo il code
        for _ in range(5):
            follow = session.get(location, timeout=30, allow_redirects=False)
            location = follow.headers.get("Location", "")
            auth_code = _extract_authorization_code(location)
            if auth_code:
                break
            if not location:
                break
    if not auth_code:
        raise RuntimeError("GOG login failed: authorization code not found")

    # 3. Scambio del code con il token OAuth
    token_response = session.get(
        f"{GOG_AUTH_URL}/token",
        params={
            "client_id": GOG_CLIENT_ID,
            "client_secret": GOG_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": GOG_REDIRECT_URI,
        },
        timeout=30,
    )
    token_response.raise_for_status()
    token_data = token_response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError("GOG login failed: no access token in token exchange response")
    return access_token


def fetch_owned_games(session, access_token, logger=None):
    """Recupera i giochi posseduti dall'utente GOG.

    Ritorna: lista di dict {title_id (int), name (str)}
    """
    if logger is None:
        logger = logging.getLogger()

    headers = {"Authorization": f"Bearer {access_token}"}

    user_response = session.get(
        f"{GOG_EMBED_URL}/userData.json", headers=headers, timeout=30
    )
    user_response.raise_for_status()
    user_data = user_response.json()
    user_id = user_data.get("userId")
    if not user_id:
        raise RuntimeError("GOG userData.json did not return a userId")
    logger.info(f"GOG user id: {user_id}")

    games_response = session.get(
        f"{GOG_API_URL}/v2/users/{user_id}/games",
        params={"locale": "en-US"},
        headers=headers,
        timeout=30,
    )
    games_response.raise_for_status()
    payload = games_response.json()

    # Parsing difensivo: la risposta attesa è {"games": [{"id": ..., "title": ...}]}
    games = payload.get("games") if isinstance(payload, dict) else payload
    owned = []
    for game in games or []:
        game_id = game.get("id")
        name = game.get("title") or game.get("name")
        if game_id is None or not name:
            continue
        owned.append({"title_id": int(game_id), "name": name})
    return owned


def sync_gog(username, password, logger=None):
    """Sincronizzazione GOG: libreria dei giochi posseduti.

    username: email o username dell'account GOG (salvato in platform_id)
    password: password dell'account GOG (salvata in api_key)
    """
    if logger is None:
        logger = logging.getLogger()

    logger.info("Starting GOG synchronization...")
    print("Starting GOG synchronization...", flush=True)

    try:
        session = create_robust_session()
        access_token = gog_login(session, username, password, logger=logger)
        logger.info("GOG login successful, fetching owned games")
        owned_games = fetch_owned_games(session, access_token, logger=logger)

        game_records = [
            {
                "title_id": game["title_id"],
                "name": game["name"],
                "console": IGDB_PLATFORM_PC,
                "play_count": 0,      # GOG non espone statistiche di gioco
                "earnedTrophy": 0,
                "totTrophy": 0,
                "percTrophy": "0%",
            }
            for game in owned_games
        ]

        logger.info(f"GOG sync completed: {len(game_records)} games owned")
        print(f"GOG sync completed: {len(game_records)} games owned", flush=True)

        if not game_records:
            logger.warning("No games found in the GOG library.")

        return {
            "fullGames": game_records,
            "gameCount": len(game_records),
            "earnedTrophyCount": 0,
            "totTrophyCount": 0,
            "completeTrophyCount": 0,
            "totPlayTimeCount": 0,
        }

    except Exception as e:
        logger.error(f"GOG sync failed: {e}")
        print(f"GOG sync failed: {e}", flush=True)
        return {
            "fullGames": [],
            "gameCount": 0,
            "earnedTrophyCount": 0,
            "totTrophyCount": 0,
            "completeTrophyCount": 0,
            "totPlayTimeCount": 0,
            "internalError": str(e)
        }
