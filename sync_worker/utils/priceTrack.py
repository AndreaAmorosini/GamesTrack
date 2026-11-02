"""Tracking dei prezzi per la wishlist.

Fase 1 - Store digitali:
- Steam: API pubblica ufficiale (appdetails, filters=price_overview), nessuna chiave
- GOG: api.gog.com/v2/games/{id}/prices (community-documented)
- PSN Store: GraphQL della web store, best-effort
  (richiede PSN_STORE_GRAPHQL_HASH in env, altrimenti saltato)

Fase 2 - Negozi fisici:
- Trovaprezzi.it: feed RSS per prodotto. L'URL del feed è configurato
  dall'utente sul singolo item della wishlist (campo price_tracking),
  perché non esiste un'API di ricerca pubblica per associare un gioco
  generico a una scheda prodotto. I risultati possono essere filtrati per
  una lista di negozi di interesse (es. Unieuro, GameLife, Amazon).
"""

import logging
import os
import re
import time
import xml.etree.ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"
GOG_PRICES_URL = "https://api.gog.com/v2/games/{game_id}/prices"
PSN_GRAPHQL_URL = "https://web.np.playstation.com/api/graphql/v1/op"
PSN_CATALOG_URL = "https://store.playstation.com/it-it/concept/{concept_id}"

DEFAULT_COUNTRY = "it"


def create_robust_session():
    """Crea una sessione requests con configurazioni robuste"""
    session = requests.Session()

    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({"User-Agent": "GamesTrack/1.0 (wishlist price tracker)"})
    return session


def _price_record(store, price=None, formatted=None, currency=None, url=None):
    return {
        "store": store,
        "price": price,
        "formatted_price": formatted,
        "currency": currency,
        "url": url,
        "available": price is not None,
    }


# --------------------------------------------------------------------------
# Store digitali
# --------------------------------------------------------------------------

def fetch_steam_price(session, app_id, logger=None, cc=DEFAULT_COUNTRY):
    """Prezzo Steam tramite l'API pubblica appdetails.

    Ritorna un price record; se il gioco non è venduto o non ha prezzo
    (F2P), "available" è False.
    """
    if logger is None:
        logger = logging.getLogger()
    try:
        response = session.get(
            STEAM_APPDETAILS_URL,
            params={"appids": app_id, "cc": cc, "filters": "price_overview"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json() or {}
        app_data = (data.get(str(app_id)) or {}).get("data") or {}
        overview = app_data.get("price_overview")
        if not overview:
            # Free-to-play o gioco senza prezzo in questa regione
            logger.info(f"Steam: no price_overview for appid {app_id}")
            return _price_record("steam", url=f"https://store.steampowered.com/app/{app_id}")
        return _price_record(
            "steam",
            price=overview.get("final", 0) / 100.0,
            formatted=overview.get("final_formatted"),
            currency=overview.get("currency"),
            url=f"https://store.steampowered.com/app/{app_id}",
        )
    except Exception as e:
        logger.warning(f"Steam price fetch failed for appid {app_id}: {e}")
        return None


def fetch_gog_price(session, game_id, logger=None, country_code="IT"):
    """Prezzo GOG tramite l'endpoint prezzi della Galaxy API.

    Ritorna un price record; se non disponibili ritorna un record con
    available False o None su errore.
    """
    if logger is None:
        logger = logging.getLogger()
    try:
        response = session.get(
            GOG_PRICES_URL.format(game_id=game_id),
            params={"countryCode": country_code},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json() or {}
        # Parsing difensivo: {"_embedded": {"prices": [{"baseAmount": "59.99", "finalAmount": ...}]}}
        prices = ((payload.get("_embedded") or {}).get("prices")) or []
        if not prices:
            logger.info(f"GOG: no prices for game {game_id}")
            return _price_record("gog")
        first = prices[0]
        final = first.get("finalAmount", first.get("baseAmount"))
        price = float(final) if final is not None else None
        return _price_record(
            "gog",
            price=price,
            formatted=f"{price:.2f} €" if price is not None else None,
            currency="EUR",
            url=f"https://www.gog.com/it/game/{game_id}",
        )
    except Exception as e:
        logger.warning(f"GOG price fetch failed for game {game_id}: {e}")
        return None


def fetch_psn_price(session, title_name, logger=None, persisted_query_hash=None):
    """Prezzo PSN Store via GraphQL della web store (best-effort).

    Come per psn_library.py: richiede l'hash della persisted query in env
    (PSN_STORE_GRAPHQL_HASH); senza, viene saltato. La ricerca è per nome
    (il catalogo PSN non è mappabile con i product_id dei trofei).
    """
    if logger is None:
        logger = logging.getLogger()

    query_hash = persisted_query_hash
    if query_hash is None:
        query_hash = os.getenv("PSN_STORE_GRAPHQL_HASH")
    if query_hash is None:
        return None

    try:
        response = session.get(
            PSN_GRAPHQL_URL,
            params={
                "operationName": "categoryGridRetrieve",
                "variables": (
                    '{"id": "' + title_name.replace('"', "") + '", '
                    '"pageParam": "searchStoreTerm", "sortBy": null, '
                    '"pageSize": 10, "start": 0}'
                ),
                "extensions": (
                    '{"persistedQuery": {"version": 1, "sha256Hash": "' + query_hash + '"}}'
                ),
            },
            timeout=30,
        )
        response.raise_for_status()
        # Il parsing dipende dalla struttura della risposta: il price tracking
        # PSN va verificato contro l'API reale prima di fidarsi del risultato.
        data = response.json()
        concepts = (((data.get("data") or {}).get("categoryGridRetrieve") or {}).get("concepts")) or []
        if not concepts:
            return None
        first = concepts[0]
        price_info = ((first.get("price") or {}).get("basePrice") or {})
        return _price_record(
            "psn",
            price=price_info.get("value", 0) / 100.0 if price_info.get("value") else None,
            formatted=price_info.get("formattedValue"),
            currency="EUR",
            url=first.get("ref") or PSN_CATALOG_URL.format(concept_id=first.get("id", "")),
        )
    except Exception as e:
        logger.warning(f"PSN price fetch failed for '{title_name}': {e}")
        return None


DIGITAL_STORE_FETCHERS = {
    "steam": lambda session, game, logger: (
        fetch_steam_price(session, game["steam_game_id"], logger)
        if game.get("steam_game_id") is not None
        else None
    ),
    "gog": lambda session, game, logger: (
        fetch_gog_price(session, game["gog_game_id"], logger)
        if game.get("gog_game_id") is not None
        else None
    ),
}


# --------------------------------------------------------------------------
# Negozi fisici via Trovaprezzi (feed RSS)
# --------------------------------------------------------------------------

# Prezzi del tipo "1.234,56" o "59,99" o "59.99" preceduti da € o EUR
_PRICE_EU_RE = re.compile(
    r"(?:€|EUR)\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{1,2})?|[0-9]+(?:[.,][0-9]{1,2})?)"
)


def _parse_eur_price(text):
    """Estrae il primo prezzo in euro da un testo libero"""
    match = _PRICE_EU_RE.search(text or "")
    if not match:
        return None
    raw = match.group(1)
    # Formato italiano "1.234,56" -> 1234.56
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def fetch_trovaprezzi_offers(session, feed_url, stores=None, logger=None):
    """Recupera le offerte dal feed RSS Trovaprezzi di un prodotto.

    feed_url: URL del feed RSS della scheda prodotto (es.
              https://www.trovaprezzi.it/rss/prezzo.aspx?id=NNNNN)
    stores: lista opzionale di nomi negozi di interesse (es. ["Unieuro",
            "GameLife"]); None o lista vuota = tutti i negozi del feed.
            Il filtro è per sottostringa, case-insensitive.

    Ritorna: lista di dict {store, price, url, name}, ordinata per prezzo.
    Il formato RSS è HTML libero: il parsing è difensivo e va verificato
    contro i feed reali.
    """
    if logger is None:
        logger = logging.getLogger()
    try:
        response = session.get(feed_url, timeout=30)
        response.raise_for_status()
        # Alcuni feed non dichiarano correttamente l'encoding: forza UTF-8 tollerante
        root = ET.fromstring(response.content)
        offers = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            description = item.findtext("description") or ""
            # Il nome del negozio è nel tag <source> o nel testo della descrizione
            store_name = (item.findtext("source") or "").strip()
            if not store_name:
                bold = re.search(r"<b>([^<]+)</b>", description)
                store_name = bold.group(1).strip() if bold else ""
            price = _parse_eur_price(description) or _parse_eur_price(title)
            offers.append({
                "store": store_name,
                "price": price,
                "url": link,
                "name": title,
            })

        if stores:
            wanted = [s.lower() for s in stores]
            offers = [
                o for o in offers
                if any(w in (o["store"] or "").lower() for w in wanted)
            ]

        offers.sort(key=lambda o: (o["price"] is None, o["price"] if o["price"] is not None else 0))
        return offers
    except Exception as e:
        logger.warning(f"Trovaprezzi feed fetch failed for {feed_url}: {e}")
        return []


# --------------------------------------------------------------------------
# Raccolta aggregata per un gioco della wishlist
# --------------------------------------------------------------------------

def collect_prices_for_game(session, game_doc, price_tracking=None, logger=None):
    """Raccoglie tutti i prezzi disponibili per un gioco (documento di 'games').

    - Store digitali: in base agli external id presenti sul documento
    - Negozi fisici: se l'item wishlist ha configurato un feed Trovaprezzi
      (price_tracking.trovaprezzi_url) con eventuale filtro negozi

    Ritorna: lista di price record
    """
    if logger is None:
        logger = logging.getLogger()

    prices = []
    for store, fetcher in DIGITAL_STORE_FETCHERS.items():
        record = fetcher(session, game_doc, logger)
        if record is not None:
            prices.append(record)
        time.sleep(0.3)  # limite di cortesia tra richieste

    if price_tracking and price_tracking.get("trovaprezzi_url"):
        offers = fetch_trovaprezzi_offers(
            session,
            price_tracking["trovaprezzi_url"],
            stores=price_tracking.get("stores"),
            logger=logger,
        )
        for offer in offers:
            prices.append(_price_record("trovaprezzi", **offer))

    return prices
