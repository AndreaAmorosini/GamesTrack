# GamesTrack — Frontend

React single-page application (Create React App) built on the [Windmill Dashboard](https://windmillui.com/react-ui) template with Tailwind CSS, Chart.js and full PWA support.

## Features

- **Responsive by design**: mobile-first layout with off-canvas sidebar on small screens, scrollable tables, touch-friendly controls and iOS-specific fixes (no auto-zoom on inputs, safe-area support for notch and home indicator).
- **Installable PWA**: installable on iPhone/iPad ("Add to Home Screen"), Android and desktop ("Install app"). Runs fullscreen in standalone mode with offline precaching via service worker. Requires HTTPS (or localhost).
- **Pages**:
  - **Dashboard** — per-platform statistics, distribution charts and totals
  - **La mia libreria** — user library with filters, sorting, pagination and per-platform sync buttons
  - **Cerca Giochi / Esplora Giochi** — IGDB-backed search and catalog browsing
  - **Wishlist** — multi-console wishlist with per-store price badges, price alerts and per-item price tracking configuration (Trovaprezzi feed + store filter + threshold)
  - **Storico Sincronizzazioni** — start any sync pipeline (Steam, PSN, RetroAchievements, GOG), watch live progress via status polling, and open real-time job logs
  - **Servizi** — per-platform credential setup with step-by-step instructions, and editable price tracking schedule (enable/disable, interval, manual run)
- **Auth**: JWT (OAuth2 password flow) with protected routes; sessions expire gracefully to the login page.
- **Theming**: dark mode initialized from the system preference and switchable by the user (Windmill theme context).

## Development

```bash
npm install

# Generate the Tailwind CSS (required before the first start/build)
npm run tailwind:dev

# Start the dev server (expects the API on http://localhost:8000)
npm start

# Production build (emits the PWA service worker and manifest)
npm run build
```

Notes:
- The API base URL is set via `REACT_APP_API_URL` (default `http://localhost:8000`).
- Tailwind CSS output (`src/assets/css/tailwind.output.css`) is generated: `prestart` and `prebuild` scripts regenerate it automatically. It is gitignored.
- On Node >= 17 the production build needs `NODE_OPTIONS=--openssl-legacy-provider` (CRA 3.4 / webpack 4). The official Docker image (node:16) does not.
- Adding new custom CSS (mobile/PWA utilities, safe areas): edit `src/assets/css/tailwind.css` and regenerate with `npm run tailwind:dev`.

## Production

The Docker build (`Dockerfile`) compiles the app and serves it with Nginx:

- SPA fallback: all routes serve `index.html`
- `service-worker.js`, `index.html` and `manifest.json` are served with `no-cache` so installed apps pick up updates immediately
- `/static/` assets are served with a 1-year immutable cache
- `/api/` is proxied to the FastAPI backend

## PWA details

- `public/manifest.json`: standalone display, maskable icons (192/512), theme color `#7e3af2`, Italian locale.
- `public/index.html`: iOS (`apple-mobile-web-app-*`) and Android/desktop (`mobile-web-app-capable`) meta tags, `viewport-fit=cover` for notch handling.
- `src/serviceWorker.js`: CRA service worker registration, enabled in `src/index.js`.
- Custom mobile/PWA styles live in `src/assets/css/tailwind.css` (safe areas, tap highlight, scroll behavior).
