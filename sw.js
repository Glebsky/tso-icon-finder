// TSO Icon Finder - Progressive Web App Service Worker
const CACHE_NAME = 'tso-icons-v1';

const CORE_ASSETS = [
  './',
  'index.html',
  'manifest.webmanifest',
  'favicon.ico',
  'favicon.svg',
  'favicon-16x16.png',
  'favicon-32x32.png',
  'apple-touch-icon.png',
  'icon-192.png',
  'icon-512.png',
  'icon-maskable-192.png',
  'icon-maskable-512.png',
  'og-image.png'
];

// Install: Cache core application shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(CORE_ASSETS).catch((err) => {
        console.warn('[SW] Pre-caching non-fatal warning:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Activate: Clean up previous cache generations
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('tso-icons-') && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: Caching strategies
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Only handle GET requests and same-origin / relative assets
  if (request.method !== 'GET') return;

  // 1. Icon PNG assets (/icons/*.png): Cache-First strategy
  if (url.pathname.includes('/icons/')) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return networkResponse;
        }).catch(() => {
          // Offline fallback
          return caches.match('favicon-32x32.png');
        });
      })
    );
    return;
  }

  // 2. Icon catalog data (icons_data.js): Stale-While-Revalidate
  if (url.pathname.endsWith('icons_data.js')) {
    event.respondWith(
      caches.match(request).then((cachedResponse) => {
        const fetchPromise = fetch(request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseClone);
            });
          }
          return networkResponse;
        }).catch((err) => {
          console.warn('[SW] icons_data.js offline fetch error:', err);
          return cachedResponse;
        });

        return cachedResponse || fetchPromise;
      })
    );
    return;
  }

  // 3. Navigation / HTML pages: Network-First with Cache fallback
  if (request.mode === 'navigate' || request.destination === 'document') {
    event.respondWith(
      fetch(request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return networkResponse;
      }).catch(() => {
        return caches.match('./') || caches.match('index.html');
      })
    );
    return;
  }

  // 4. Default: Cache with Network Fallback
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      return cachedResponse || fetch(request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && url.origin === self.location.origin) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return networkResponse;
      });
    })
  );
});
