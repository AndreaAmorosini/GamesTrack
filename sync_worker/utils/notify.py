"""Notifiche push via ntfy (https://ntfy.sh o server self-hosted).

Configurazione letta da app_settings (key: "ntfy"), modificabile dalla
web UI nella pagina Impostazioni:
    {enabled, server_url, topic, token, notify_on_sync, notify_on_price}

Uso dall'utente:
1. Installare l'app ntfy (iOS/Android) o usare il sito
2. Scegliere un nome topic non indovinabile (es. "gametrack-pippo-8341ab")
   e iscriversi alla topic nell'app
3. Inserire topic (e opzionalmente server self-hosted e token) nella
   pagina Impostazioni di GamesTrack
"""

import logging

import requests


def send_notification(db, title, message, tags=None, logger=None, only_if_flag=None):
    """Invia una notifica ntfy secondo la configurazione in app_settings.

    only_if_flag: nome opzionale del flag di configurazione da rispettare
    (es. "notify_on_sync", "notify_on_price").
    Ritorna True se inviata, False altrimenti (mai eccezioni: la notifica
    non deve mai far fallire il job chiamante).
    """
    if logger is None:
        logger = logging.getLogger()
    try:
        settings = db["app_settings"].find_one({"key": "ntfy"}) or {}
        if not settings.get("enabled"):
            return False
        if only_if_flag and not settings.get(only_if_flag, True):
            return False
        topic = settings.get("topic")
        if not topic:
            logger.info("Notifica ntfy saltata: topic non configurato")
            return False
        server = (settings.get("server_url") or "https://ntfy.sh").rstrip("/")

        headers = {"Title": title}
        if tags:
            headers["Tags"] = ",".join(tags)
        token = settings.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.post(
            f"{server}/{topic}",
            data=message.encode("utf-8"),
            headers=headers,
            timeout=10,
        )
        if response.status_code >= 400:
            logger.warning(f"ntfy notification failed: HTTP {response.status_code}")
            return False
        logger.info(f"Notifica ntfy inviata: {title}")
        return True
    except Exception as e:
        logger.warning(f"ntfy notification failed: {e}")
        return False


def send_test_notification(db, logger=None):
    """Invia una notifica di prova; ritorna (ok, messaggio errore)."""
    if logger is None:
        logger = logging.getLogger()
    settings = db["app_settings"].find_one({"key": "ntfy"}) or {}
    if not settings.get("topic"):
        return False, "Topic non configurato: inserisci prima il nome della topic"
    ok = send_notification(
        db,
        "GamesTrack — notifica di prova",
        "Se leggi questo messaggio, le notifiche sono configurate correttamente! 🎮",
        tags=["white_check_mark"],
        logger=logger,
    )
    return (True, "Notifica inviata: controlla l'app ntfy") if ok else (False, "Invio fallito: controlla server e topic")
