const CACHE = "justice-auto-robuste-v2";

const STATIC_ASSETS = [
    "./",
    "./index.html",
    "./manifest.json",
    "./icon-192.png",
    "./icon-512.png"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE).then(cache => cache.addAll(STATIC_ASSETS))
    );

    self.skipWaiting();
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(key => key !== CACHE).map(key => caches.delete(key))
            )
        )
    );

    self.clients.claim();
});

self.addEventListener("fetch", event => {
    const url = new URL(event.request.url);

    if (event.request.method !== "GET") {
        return;
    }

    if (url.pathname.includes("/api/")) {
        return;
    }

    event.respondWith(
        caches.match(event.request).then(cached => {
            if (cached) {
                return cached;
            }

            return fetch(event.request).then(response => {
                const copy = response.clone();

                caches.open(CACHE).then(cache => cache.put(event.request, copy));

                return response;
            }).catch(() => caches.match("./index.html"));
        })
    );
});
