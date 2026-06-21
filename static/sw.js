const CACHE = "quant-atlas-v1";
const STATIC_RESOURCES = [
  "/static/manifest.json",
  "/static/favicon.svg",
  "/static/favicon.ico",
  "/static/css/vendor/bootstrap-4.6.2.min.css",
  "/static/css/design-tokens.css",
  "/static/js/vendor/jquery-3.7.1.min.js",
  "/static/js/vendor/bootstrap-4.6.2.bundle.min.js",
  "/static/js/vendor/lightweight-charts.standalone.production.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => {
      return cache.addAll(STATIC_RESOURCES).catch((err) => {
        console.warn("[SW] pre-cache partial failure", err);
      });
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Only cache same-origin GET requests to known static paths
  if (
    event.request.method !== "GET" ||
    url.origin !== self.location.origin
  ) {
    return;
  }

  const path = url.pathname;

  // API calls and dynamic pages: network-first
  if (path.startsWith("/api/") || path.startsWith("/system/health")) {
    return;
  }

  // HTML pages: network-first with cache fallback
  if (path === "/" || path.endsWith(".html") || !path.includes(".")) {
    event.respondWith(
      fetch(event.request)
        .then((resp) => {
          const clone = resp.clone();
          caches.open(CACHE).then((cache) => cache.put(event.request, clone));
          return resp;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Static assets: cache-first
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});