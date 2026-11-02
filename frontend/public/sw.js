/* Service worker per GamesTrack.
 *
 * Sostituisce il precache di CRA (workbox): con quello, index.html restava
 * servito dalla cache anche dopo un nuovo deploy, e il vecchio index
 * richiedeva chunk oramai inesistenti su nginx (flickering e richieste 404).
 *
 * Strategia:
 * - navigazioni (index.html): network-first, fallback alla cache se offline
 * - /static/ (file con hash nel nome): cache-first, sono immutabili
 * - altro (manifest, icone): network con fallback cache
 * - skipWaiting + clients.claim: gli aggiornamenti del SW si applicano subito
 */

const CACHE = 'gamestrack-v2';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Navigazioni (apertura dell'app): network-first, fallback cache
  if (req.mode === 'navigate') {
    event.respondWith(
      (async () => {
        try {
          return await fetch(req);
        } catch (err) {
          const cache = await caches.open(CACHE);
          return (await cache.match('/index.html')) || Response.error();
        }
      })()
    );
    return;
  }

  // Asset statici con hash nel nome: cache-first (immutabili)
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      (async () => {
        const cache = await caches.open(CACHE);
        const hit = await cache.match(req);
        if (hit) return hit;
        const resp = await fetch(req);
        if (resp.ok) cache.put(req, resp.clone());
        return resp;
      })()
    );
  }
});
