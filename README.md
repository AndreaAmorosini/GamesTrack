# GamesTrack 🎮

Un sistema di gestione della libreria videoludica personale con sincronizzazione automatica da Steam e PSN, wishlist e ricerca giochi tramite database IGDB.

## Caratteristiche

- Sincronizzazione automatica della libreria da Steam e PlayStation Network
- Gestione wishlist con supporto multi-piattaforma
- Ricerca e esplorazione di giochi tramite database IGDB
- Dashboard con statistiche dettagliate per utente
- Aggiornamento metadati giochi in tempo reale

## Installazione e Avvio

### Prerequisiti

- Docker e Docker Compose
- Account IGDB per API key

### 1. Configura le credenziali IGDB

Crea un file `.env` nella root del progetto:

```bash
# .env
IGDB_CLIENT_ID="your_igdb_client_id_here"
IGDB_CLIENT_SECRET="your_igdb_client_secret_here"
```

Per ottenere le credenziali:
1. Vai su [IGDB API](https://api.igdb.com/)
2. Registrati con account Twitch
3. Crea nuova applicazione
4. Copia Client ID e Client Secret

### 2. Avvia l'applicazione

```bash
# Avvia tutti i servizi
docker-compose up -d

# Ferma tutti i servizi
docker-compose down
```

### 3. Accedi all'applicazione

- **Frontend**: http://localhost:3000
- **Documentazione API**: http://localhost:8000/docs

## Tecnologie

- **Frontend**: React, Tailwind CSS
- **Backend**: FastAPI, Python
- **Database**: MongoDB, Redis
- **Infrastructure**: Docker,