/* DishGennie Service Worker */

const STATIC_CACHE = 'dishgennie-static-v1';
const PAGE_CACHE   = 'dishgennie-pages-v1';

// Pre-cached on install — must all return 200 or install aborts
const PRECACHE_URLS = [
  '/offline.html',
  '/static/css/base.css',
  '/static/css/components.css',
  '/static/css/dishgennie-theme.css',
  '/static/js/app.js',
];

// ── Install: pre-cache core assets ──────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: delete stale caches ───────────────────────────────────────────
self.addEventListener('activate', event => {
  const keep = [STATIC_CACHE, PAGE_CACHE];
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => !keep.includes(k)).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// ── Fetch ────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin GET requests
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // API calls — network only, never cache
  if (url.pathname.startsWith('/api/')) return;

  // Static assets — cache first, network fallback, update cache in background
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.open(STATIC_CACHE).then(cache =>
        cache.match(request).then(cached => {
          const networkFetch = fetch(request).then(response => {
            cache.put(request, response.clone());
            return response;
          });
          return cached || networkFetch;
        })
      )
    );
    return;
  }

  // Navigation — network first, page-cache fallback, offline page last resort
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          const clone = response.clone();
          caches.open(PAGE_CACHE).then(cache => cache.put(request, clone));
          return response;
        })
        .catch(() =>
          caches.match(request, { cacheName: PAGE_CACHE })
            .then(cached => cached || caches.match('/offline.html', { cacheName: STATIC_CACHE }))
        )
    );
    return;
  }
});
