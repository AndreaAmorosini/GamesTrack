# GamesTrack 🎮

A personal video game library management system with automatic synchronization from Steam and PSN, wishlist and game search through IGDB database.

## Features

- Automatic library synchronization from Steam and PlayStation Network
- Wishlist management with multi-platform support
- Game search and exploration through IGDB database
- Dashboard with detailed user statistics
- Real-time game metadata updates

## Installation and Setup

### Prerequisites

- Docker and Docker Compose
- IGDB account for API key

### 1. Configure IGDB credentials

Create a `.env` file in the project root:

```bash
# .env
IGDB_CLIENT_ID="your_igdb_client_id_here"
IGDB_CLIENT_SECRET="your_igdb_client_secret_here"
```

To obtain the credentials:
1. Go to [IGDB API](https://api.igdb.com/)
2. Register with Twitch account
3. Create new application
4. Copy Client ID and Client Secret

### 2. Start the application

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down
```

### 3. Access the application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

#### 4. Synchronization
1. Create a user
2. Go to the profile update section
3. Fill in credentials for Steam and PSN
    - **Steam**: Enter Steam credentials
        - Go to [Steam API Key](https://steamcommunity.com/dev/apikey)
        - Generate a new key
        - Insert the generated key and your SteamID
   - **PSN**: Enter PlayStation credentials
     - PSN Username
     - NPSSO
       - To retrieve your NPSSO:
         1. Login to your [My PlayStation](https://my.playstation.com) account.
         2. In another tab, go to [https://ca.account.sony.com/api/v1/ssocookie](https://ca.account.sony.com/api/v1/ssocookie).
         3. If you are logged in, you will see text similar to this:
            ```json
            {"npsso":"<64 character npsso code>"}
            ```
4. Start synchronization from the dashboard

## Technologies

- **Frontend**: React, Tailwind CSS
- **Backend**: FastAPI, Python
- **Database**: MongoDB, Redis
- **Infrastructure**: Docker