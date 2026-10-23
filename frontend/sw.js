const CACHE = "justice-auto-robuste-v3";

const PRECACHE = [
    "./manifest.json",
    "./icon-192.png",
    "./icon-512.png"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE).then(cache => {
            return Promise.allSettled(
                PRECACHE.map(path => cache.add(path))
            );
        })
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

    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const copy = response.clone();

                    caches.open(CACHE).then(cache => cache.put("./index.html", copy));

                    return response;
                })
                .catch(() => caches.match("./index.html"))
        );

        return;
    }

    event.respondWith(
        caches.match(event.request).then(cached => {
            if (cached) {
                return cached;
            }

            return fetch(event.request).then(response => {
                if (response.ok && url.origin === location.origin) {
                    const copy = response.clone();

                    caches.open(CACHE).then(cache => cache.put(event.request, copy));
                }

                return response;
            });
        })
    );
});
