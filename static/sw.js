// Service Worker for VTS Report Tool PWA
const CACHE_NAME = 'vts-report-tool-v1.0.0';
const STATIC_CACHE = 'vts-static-v1.0.0';
const DYNAMIC_CACHE = 'vts-dynamic-v1.0.0';

// Files to cache immediately
const STATIC_FILES = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  'Kenhalogo.png',
  'pwa_manifest.json'
];

// Install event - cache static files
self.addEventListener('install', event => {
  console.log('[SW] Installing service worker');
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[SW] Caching static files');
        return cache.addAll(STATIC_FILES);
      })
      .catch(err => console.log('[SW] Error caching static files:', err))
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[SW] Activating service worker');
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
  );
  self.clients.claim();
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // Skip external requests (API calls, etc.)
  if (!url.origin.includes(self.location.origin) &&
      !url.href.includes('fonts.googleapis.com') &&
      !url.href.includes('fonts.gstatic.com')) {
    return;
  }

  // Handle API requests differently
  if (url.pathname.startsWith('/api/') ||
      url.pathname.includes('streamlit') ||
      url.pathname.includes('folium')) {
    // Network first for API calls
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Cache successful responses
          if (response.status === 200) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE)
              .then(cache => cache.put(event.request, responseClone));
          }
          return response;
        })
        .catch(() => {
          // Fallback to cache if network fails
          return caches.match(event.request);
        })
    );
  } else {
    // Cache first for static assets
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          if (response) {
            return response;
          }

          return fetch(event.request)
            .then(response => {
              // Don't cache if not successful
              if (!response || response.status !== 200 || response.type !== 'basic') {
                return response;
              }

              const responseClone = response.clone();
              caches.open(DYNAMIC_CACHE)
                .then(cache => cache.put(event.request, responseClone));

              return response;
            })
            .catch(err => {
              console.log('[SW] Fetch failed:', err);
              // Return offline fallback
              if (event.request.destination === 'document') {
                return caches.match('/');
              }
            });
        })
    );
  }
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'background-sync-reports') {
    event.waitUntil(syncPendingReports());
  }
});

// Function to sync pending reports when back online
async function syncPendingReports() {
  try {
    // Get pending reports from IndexedDB or local storage
    const pendingReports = await getPendingReports();

    for (const report of pendingReports) {
      try {
        const response = await fetch('/api/incident-reports', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(report)
        });

        if (response.ok) {
          // Remove from pending
          await removePendingReport(report.id);
          console.log('[SW] Synced report:', report.id);
        }
      } catch (error) {
        console.log('[SW] Failed to sync report:', report.id, error);
      }
    }
  } catch (error) {
    console.log('[SW] Background sync error:', error);
  }
}

// Placeholder functions for IndexedDB operations
async function getPendingReports() {
  // In a real implementation, this would query IndexedDB
  return [];
}

async function removePendingReport(id) {
  // In a real implementation, this would remove from IndexedDB
  return true;
}

// Push notification handling
self.addEventListener('push', event => {
  console.log('[SW] Push received:', event);

  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body,
      icon: 'Kenhalogo.png',
      badge: 'Kenhalogo.png',
      vibrate: [100, 50, 100],
      data: {
        dateOfArrival: Date.now(),
        primaryKey: data.primaryKey
      }
    };

    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// Notification click handling
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification click:', event);
  event.notification.close();

  event.waitUntil(
    clients.openWindow('/')
  );
});