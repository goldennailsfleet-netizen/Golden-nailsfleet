const CACHE = 'ai-super-app-v1';
const ASSETS = [
  '/Golden-nailsfleet/',
  '/Golden-nailsfleet/index.html',
  '/Golden-nailsfleet/manifest.json',
  '/Golden-nailsfleet/icon.svg',
];

// Install — cache the app shell
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

// Activate — remove old caches
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch — network first for API calls, cache first for app shell
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // Always go to network for AI APIs
  const isApi = url.hostname.includes('pollinations.ai') ||
                url.hostname.includes('allorigins.win') ||
                url.hostname.includes('corsproxy.io') ||
                url.hostname.includes('codetabs.com') ||
                url.hostname.includes('fonts.googleapis.com');

  if (isApi) {
    e.respondWith(fetch(e.request).catch(() => new Response('', { status: 503 })));
    return;
  }

  // Cache first for app shell
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return response;
      }).catch(() => caches.match('/Golden-nailsfleet/'));
    })
  );
});
