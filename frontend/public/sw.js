// Service Worker for performance optimization
const CACHE_NAME = 'Forge-v1';
const STATIC_ASSETS = [
  '/',
  // Add static assets you want precached here. Removed missing logo/manifest entries that caused 404s during dev.
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => cacheName !== CACHE_NAME)
          .map((cacheName) => caches.delete(cacheName))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache when possible
self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // If we have a cached response, return it.
        if (response) return response;

        // For non-HTTP(S) schemes (e.g. chrome-extension://) do not attempt
        // to fetch-and-cache them — the Cache API does not support those.
        let requestUrl;
        try {
          requestUrl = new URL(event.request.url);
        } catch (e) {
          // If URL parsing fails, fall back to network fetch without caching.
          return fetch(event.request);
        }

        if (requestUrl.protocol !== 'http:' && requestUrl.protocol !== 'https:') {
          return fetch(event.request);
        }

        return fetch(event.request).then((fetchResponse) => {
          // Don't cache API calls or non-successful responses
          if (
            !fetchResponse ||
            fetchResponse.status !== 200 ||
            event.request.url.includes('/api/') ||
            event.request.url.includes('/ws/')
          ) {
            return fetchResponse;
          }

          // Cache successful responses (best-effort; ignore cache errors)
          const responseToCache = fetchResponse.clone();
          caches
            .open(CACHE_NAME)
            .then((cache) => {
              try {
                cache.put(event.request, responseToCache);
              } catch (err) {
                // Some requests (like extension schemes) may throw; ignore to avoid breaking fetch.
                // eslint-disable-next-line no-console
                console.debug('sw: cache.put failed, skipping cache for', event.request.url, err);
              }
            })
            .catch(() => {
              // ignore cache open errors
            });

          return fetchResponse;
        });
      })
  );
});