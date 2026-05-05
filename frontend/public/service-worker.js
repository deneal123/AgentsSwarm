const CACHE_NAME = 'gpthub-v2';
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/favicon-gpthub.svg',
  '/gpthub-logo.svg',
  // Add other critical assets if necessary
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
          return Promise.resolve();
        })
      )
    )
  );
  self.clients.claim();
});

// Простая стратегия: cache-first для статичных ресурсов, network-first для /api/
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignore cross-origin requests
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith('/api/')) {
    // Network-first for API (only cache GET requests)
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Only cache GET requests - POST/PUT/DELETE are not supported by Cache API
          if (response && response.status === 200 && request.method === 'GET') {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => {
          // Only try to return cached response for GET requests
          if (request.method === 'GET') {
            return caches.match(request);
          }
          return new Response(JSON.stringify({ error: 'Offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  // For navigation and static assets - cache first
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        // Don't cache opaque responses (from cross-origin)
        if (response && response.status === 200 && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      }).catch(() => {
        // If navigation and offline, return cached index.html
        if (request.mode === 'navigate') {
          return caches.match('/index.html');
        }
        return new Response(null, { status: 503, statusText: 'Offline' });
      });
    })
  );
});
