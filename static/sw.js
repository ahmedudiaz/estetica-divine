// Service Worker para PWA Estética Divine
const CACHE_NAME = "estetica-divine-cache-v4";
const ASSETS = [
  "/",
  "/static/css/style.css?v=4.0",
  "/static/js/app.js?v=4.0",
  "/static/manifest.json"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) return caches.delete(k);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  // Solo cacheamos peticiones GET que no sean de la API
  if (e.request.method === "GET" && !e.request.url.includes("/api/")) {
    e.respondWith(
      fetch(e.request).catch(() => caches.match(e.request))
    );
  }
});
