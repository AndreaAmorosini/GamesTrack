# GamesTrack 🎮

A self-hosted, personal video game library management system. GamesTrack automatically synchronizes your game libraries from **Steam**, **PlayStation Network**, **RetroAchievements** and **GOG**, enriches game metadata through the **IGDB** database, and lets you manage a wishlist with **price tracking** across digital stores and physical retailers.

## Features

### Library synchronization
- **Steam**: full library sync with playtime and achievement counts. Achievement schemas are cached in MongoDB (`steam_schema_cache`), halving Steam API calls on subsequent syncs.
- **PlayStation Network**: games, trophies and play statistics via NPSSO authentication, powered by **psnawp 3.1**. Each library entry carries a **source flag** (`digital` / `psplus` / `unknown`) read from the official PlayStation entitlements API: digital/purchased copies and PS Plus (Extra/Essential) catalogue titles are told apart automatically — no reverse-engineered GraphQL hashes involved.
- **Trophy history**: every PSN sync stores a timestamped snapshot of each game's trophy count, powering the progression charts on the Statistics page.
- **RetroAchievements**: mastered/completed games (full history) plus recently played titles with achievement counts, via the public RA Web API.
- **GOG**: owned titles list via the Galaxy API (accounts with 2FA are not supported).
- **IGDB metadata enrichment**: game metadata (cover, description, genres, platforms, ratings, screenshots) is fetched in **batched queries** (~50 games per request) instead of one call per game, respecting the IGDB rate limit. Unmatched games are marked `toVerify` for manual review.
- **Smart IGDB dedup**: unmatched games are collected in a dedicated **"To Verify"** page, where you can search IGDB by name and link the correct entry in one click — the game is then re-enriched with the full metadata.
- **Scheduled syncs**: a weekly automatic sync of all configured platforms, fully editable from the web UI (enable/disable, day of week, hour). A built-in guard prevents overlapping or duplicated runs.
- **Notifications (ntfy)**: optional push notifications through a self-hosted or public [ntfy](https://ntfy.sh) instance — sync results (success/failure) and price-alert triggers, each individually toggleable. Setup and a send-test button live in the Settings page.
- **Robust pipelines**: every sync job validates user/platform linkage, writes progress to a `schedules` collection, streams its logs to MongoDB (viewable from the web UI), and never exceeds a 1-hour timeout.

### Wishlist and price tracking
- Multi-console wishlist with IGDB-backed game data.
- **Digital store prices**: Steam (public Store API) and GOG (Galaxy price API) are polled automatically; PSN Store prices can be enabled with an extra configuration.
- **Physical retailers**: per-game Trovaprezzi.it RSS feeds with a configurable **store filter** (e.g. Unieuro, GameLife, MediaWorld) — one parser covers the Italian retail landscape.
- **Price history**: every poll writes a snapshot to `price_history`, so each wishlist item has a per-store price history and a `latest_price` summary.
- **Price alerts**: set a threshold per item; when the lowest available price drops below it, the item is flagged in the UI.
- **Editable schedule**: the price tracking cron is configured from the web UI (enable/disable, interval from 5 minutes to 7 days) and applies within a minute — no restart needed. Manual runs are also available.

### Web application
- **Dashboard** with per-platform statistics, distribution charts and totals.
- **Statistics page**: trophy progression over time (from the history snapshots), most-played games, per-platform breakdowns of trophies and library size.
- **Library, Wishlist, Game Explorer, Game Search** pages with filtering, sorting and pagination.
- **To Verify page**: review and resolve games that could not be matched to IGDB automatically.
- **Services page**: per-platform credential setup with step-by-step instructions on where each token comes from, plus price tracking settings and the weekly sync schedule.
- **Settings page**: ntfy notification setup (server, topic, token, event toggles) with step-by-step instructions and a test button.
- **Sync Jobs page**: start any sync pipeline, watch its live progress (3s polling), and open a **real-time log viewer** (auto-refreshing) for any job, including price tracking jobs.
- **Installable PWA**: fullscreen app-like experience on iPhone, iPad, Android and desktop, with safe-area support (notch / home indicator), offline precache via service worker, and mobile-first layout (scrollable tables, touch-friendly controls, no iOS auto-zoom on inputs).

## Architecture

```
├── backend/          FastAPI REST API: auth (JWT), library, wishlist,
│   ├── main.py       prices, settings, job management
│   ├── init_db.py    Database bootstrap and IGDB catalog seeding
│   └── utils/        Auth utilities, IGDB client (with batch queries)
├── sync_worker/      ARQ worker (Redis queue): all sync pipelines
│   ├── worker_sync.py    Platform sync + price tracking + scheduled/weekly jobs
│   └── utils/
│       ├── steamTrack.py      Steam API (with achievement schema cache)
│       ├── psnTrack.py        PSN API via psnawp 3.1 (incl. native entitlements)
│       ├── retroTrack.py      RetroAchievements Web API
│       ├── gogTrack.py        GOG Galaxy API (2-step login)
│       ├── priceTrack.py      Price adapters (Steam/GOG/PSN/Trovaprezzi RSS)
│       └── notify.py          ntfy push notifications
├── frontend/         React (CRA) + Tailwind + Windmill UI, served by Nginx
├── docs/             Project documentation and diagrams
└── docker-compose.yaml
```

| Component | Technology |
|---|---|
| Frontend | React 16, Tailwind CSS, Windmill React UI, Chart.js, Nginx, PWA (service worker + manifest) |
| Backend | FastAPI, PyMongo, ARQ (job queue), JWT auth |
| Worker | ARQ worker: Steam/PSN/RetroAchievements/GOG sync, price tracking cron |
| Data | MongoDB (games, libraries, wishlist, price history, jobs, logs, settings), Redis (queue) |

### MongoDB collections

| Collection | Purpose |
|---|---|
| `users` | Accounts (bcrypt-hashed passwords) |
| `platforms-users` | Per-user platform credentials and linkages |
| `games` | Game catalog with IGDB metadata and external IDs (`steam_game_id`, `psn_game_id`, `ra_game_id`, `gog_game_id`) |
| `game_user` | Library entries: user, game, platform, trophies, playtime, console, PSN source flag |
| `trophy_history` | Timestamped trophy-count snapshots per game (PSN), powering progression charts |
| `trophy_lists` | Full trophy/achievement lists per game and platform (PSN/Steam/RetroAchievements), synced by the worker |
| `game_user_wishlist` | Wishlist entries + price tracking config (`price_tracking`) |
| `price_history` | Price snapshots (store, price, url, timestamp) |
| `schedules` | Sync job records (status, counts, errors) |
| `sync_logs` | Job logs streamed by the worker (capped at 1000 lines/job) |
| `app_settings` | Editable settings (price tracking cron, weekly sync schedule, ntfy config) |
| `steam_schema_cache` | Cached Steam achievement schemas |

## Installation and Setup

### Prerequisites
- Docker and Docker Compose
- An IGDB account (free, via Twitch)

### 1. Configure environment

Create a `.env` file in the project root:

```bash
# .env
IGDB_CLIENT_ID="your_igdb_client_id_here"
IGDB_CLIENT_SECRET="your_igdb_client_secret_here"

# Optional — see the "Optional features" section below
# PSN_STORE_GRAPHQL_HASH="..."
# GOG_CLIENT_ID="..."
# GOG_CLIENT_SECRET="..."
```

To obtain the IGDB credentials:
1. Go to [IGDB API](https://api.igdb.com/)
2. Register with your Twitch account
3. Create a new application
4. Copy the Client ID and Client Secret

### 2. Start the application

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down
```

### 3. Access the application

- **Frontend**: http://localhost:3000
- **API Documentation** (Swagger): http://localhost:8000/docs
- **Mongo Express** (DB admin): http://localhost:8081

### 4. Link your platforms

1. Create a user
2. Go to **Servizi** (Services) in the sidebar
3. Enter credentials for the platforms you use — each card includes instructions:

**Steam**
- Steam ID: the 17-digit identifier of your account (find it on your profile details or via [steamid.io](https://steamid.io))
- Web API Key: generate a free key at [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey)

**PlayStation Network**
- PSN Online ID: your PlayStation username
- NPSSO:
  1. Log in to your [My PlayStation](https://my.playstation.com) account
  2. In another tab, open [https://ca.account.sony.com/api/v1/ssocookie](https://ca.account.sony.com/api/v1/ssocookie)
  3. If logged in, you will see: `{"npsso":"<64 character npsso code>"}`

**RetroAchievements**
- Username: your [retroachievements.org](https://retroachievements.org) username
- Web API Key: from your [account settings](https://retroachievements.org/settings)

**GOG**
- Email/username and password
- Note: accounts with two-factor authentication are not supported

### 5. Synchronize

- Start any platform sync from the **Storico Sincronizzazioni** (Sync Jobs) page and follow the live progress
- Every job's full log is viewable from the same page, in real time while the job runs
- Optionally enable the **weekly automatic sync** from the **Servizi** page: pick the day and hour, and all your linked platforms are synced automatically once a week

### 6. Notifications (ntfy)

1. Install the [ntfy app](https://ntfy.sh/docs/subscription/) on your phone, or use any ntfy-compatible client
2. Choose a **hard-to-guess topic name** (anyone who knows it can send you notifications) and subscribe to it in the app
3. In GamesTrack, open **Impostazioni** (Settings), enable notifications and enter the server URL (`https://ntfy.sh` for the public instance) and the topic; an access token is optional and only needed for protected topics
4. Choose which events trigger a notification (sync results, price alerts) and press **Send test notification** to verify the setup

### 7. Wishlist price tracking

1. Add games to your wishlist
2. On each wishlist card, click **Prezzi** to configure tracking:
   - **Trovaprezzi RSS feed URL** (for physical retailers): open the game's page on [trovaprezzi.it](https://www.trovaprezzi.it), click the RSS icon, and copy the feed URL (format: `https://www.trovaprezzi.it/rss/prezzo.aspx?id=NNNNN`)
   - **Stores filter** (optional): comma-separated list of stores of interest (e.g. `Unieuro, GameLife, Mediaworld`)
   - **Alert threshold** (optional): a price in €; the item is flagged when any tracked store drops below it
3. Digital store prices (Steam/GOG) are collected automatically for every wishlist item
4. Configure the polling schedule from the **Servizi** page

## Optional features via environment variables

| Variable | Effect |
|---|---|
| `JWT_SECRET_KEY` | Secret used to sign auth tokens (`openssl rand -hex 32`). If unset, a random one is generated at each backend start and all sessions are invalidated on restart. **Set it in production.** |
| `CREDENTIAL_ENCRYPTION_KEY` | Enables **encryption at rest** for platform credentials stored in MongoDB (Fernet). Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Existing plaintext values keep working (transparent migration); without it, credentials are stored in plaintext. Must be set for both `fastapi` and `sync-worker`. |
| `CORS_ORIGINS` | Comma-separated list of allowed origins (default `*`: the app uses Bearer tokens, no cookies — suitable for Tailscale/direct LAN access). |
| `MONGO_USER` / `MONGO_PASS` | MongoDB credentials (default `root`/`root` — change them if the instance is reachable by others). |
| `PSN_STORE_GRAPHQL_HASH` | Enables **PSN Store price tracking** (community-documented GraphQL persisted query; same caveats as below). |
| `GOG_CLIENT_ID` / `GOG_CLIENT_SECRET` | Override the built-in GOG Galaxy client credentials. |

All the optional features degrade gracefully: if the key/hash is missing or the API changes, the affected data is simply marked as unavailable and syncs never fail because of it.

### Networking note

The frontend calls the API at `http://<host-you-are-browsing>:8000` automatically (same hostname as the page, port 8000), so it works unchanged on `localhost`, a Tailscale IP/hostname or any LAN access — no reverse proxy needed. Both ports (`3000` for the UI, `8000` for the API) must be reachable from the client.

## Technologies

- **Frontend**: React, Tailwind CSS, Windmill React UI, Chart.js, PWA
- **Backend**: FastAPI, Python
- **Database**: MongoDB, Redis
- **Infrastructure**: Docker, Docker Compose

## Installable Web App (PWA)

The frontend is an installable Progressive Web App: on **iPhone/iPad** use "Add to Home Screen" from the Safari share menu, on **Android/Chrome/Edge** use the "Install app" prompt (or the browser menu). Once installed it runs fullscreen, outside the browser chrome, with support for safe areas (notch/home indicator) and offline precaching. The frontend must be served over **HTTPS** (or localhost) for the service worker and installation to work.

## Known limitations

- **GOG**: no play statistics (GOG does not expose them via API) and no 2FA support.
- **PSN source flag**: digital/purchased copies and PS Plus catalogue titles are distinguished via the official entitlements API, but the individual PS Plus tier (Essential vs Extra vs Premium) is not exposed; games on physical disc appear as `unknown` because discs create no entitlement.
- **PSN store prices**: rely on the same GraphQL persisted queries used by the official web store (community-documented, no official contract); the hash may need updating after Sony changes its web store. The library sync and source flag, by contrast, use psnawp's official endpoints.
- **Trovaprezzi RSS**: feeds are HTML-based and parsed defensively; a change in the feed layout may require a parser update.
- **Amazon Games**: not supported (no API, ToS prohibits scraping). Amazon prices are still visible through Trovaprezzi feeds.
- **Epic Games Store**: not implemented; feasible via `legendary-gl` (see project notes) but without play statistics.
