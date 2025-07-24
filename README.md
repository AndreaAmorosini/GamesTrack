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

#### 4. Sincronizzazione
1. Creare un utente
2. Procedere alla sezione di update del profilo
3. Compilare le credenziali per steam e psn
    - **Steam**: Inserire le credenziali Steam
        - Vai su [Steam API Key](https://steamcommunity.com/dev/apikey)
        - Genera una nuova chiave
        - Inserisci la chiave generata ed il proprio SteamID
   - **PSN**: Inserire credenziali PlayStation
     - Username PSN
     - NPSSO
       - Per recuperare il proprio NPSSO:
         1. Login nel tuo account [My PlayStation](https://my.playstation.com).
         2. In un'altra scheda, vai su [https://ca.account.sony.com/api/v1/ssocookie](https://ca.account.sony.com/api/v1/ssocookie).
         3. Se sei loggato, vedrai un testo simile a questo:
            ```json
            {"npsso":"<64 character npsso code>"}
            ```
4. Avviare la sincronizzazione dalla dashboard

## Tecnologie

- **Frontend**: React, Tailwind CSS
- **Backend**: FastAPI, Python
- **Database**: MongoDB, Redis
- **Infrastructure**: Docker,