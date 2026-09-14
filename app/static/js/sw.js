/* CVStand service worker — offline shell.

   Deferred since 2026-08-30 for a good reason: while the app was local-only,
   an offline shell could not do anything, because the résumé, the preview and
   both exports all lived on the server. Two things changed that. The app is
   being deployed, and the résumé moved into the browser — so with the shell
   cached, a person on a bad connection can still open the builder and edit
   their CV. Only the preview render and the two exports need the network.

   WHAT IS DELIBERATELY NOT CACHED
   - /api/* and /export/* — every one is a live render, and a stale answer here
     is worse than an error. `export` is a POST anyway, which a cache cannot
     serve.
   - /preview — same: it renders a document, and which document depends on the
     request.

   THE LANGUAGE HAZARD, and why navigations are network-first.
   The app shell is bilingual and its language comes from the `ui_lang` COOKIE,
   so one URL has two different correct responses. A cache keyed by URL alone
   cannot tell them apart, and a naive cache-first worker would happily serve a
   visitor the other language's page — the same shape of bug as the gallery
   thumbnails that rendered the wrong résumé. So:

     navigations  network-first. Online, the server decides the language, every
                  time. The cache is only ever a fallback for being offline,
                  where "the last version of this page you actually loaded" is
                  the honest answer and the only one available.
     static       cache-first. CSS, JS, fonts and icons carry no language.

   That leaves one accepted limitation, stated rather than hidden: switch
   interface language, go offline, and a cached page may come back in the
   previous language until you are online again. The alternative — no offline
   shell at all — is worse.

   CACHE VERSIONING is manual. Flask serves /static with no content hash, so
   there is nothing in a URL to tell a new build from an old one. Bump VERSION
   whenever app.css, builder.js or autofit.js changes; `activate` deletes every
   cache that is not the current one, so a bump is a full, clean refresh.
*/
const VERSION = "v2";
const SHELL_CACHE = `cvstand-shell-${VERSION}`;
const ASSET_CACHE = `cvstand-assets-${VERSION}`;
const CURRENT = new Set([SHELL_CACHE, ASSET_CACHE]);
/* The cache prefix was renamed resumecraft- -> cvstand- on 2026-09-14.
   The cleanup below has to sweep the OLD prefix too: it only ever deletes
   keys it recognises, so a rename alone would strand every cache a
   browser had already stored under the previous name, permanently. */

/* The shell only. Fonts are NOT precached: there are 34 .woff2 files across
   Latin and Arabic, and forcing every visitor to download all of them on first
   load to serve an offline case most will never hit is a bad trade. They come
   into the asset cache as they are actually used. */
const PRECACHE = [
  "/static/css/app.css",
  "/static/js/builder.js",
  "/static/js/autofit.js",
  "/static/icons/icon-192.png",
];

const isStatic = (url) => url.pathname.startsWith("/static/");
const isLive = (url) =>
  url.pathname.startsWith("/api/") ||
  url.pathname.startsWith("/export/") ||
  url.pathname === "/preview";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(ASSET_CACHE)
      /* Individually, not addAll: addAll is atomic, so one 404 in the list
         throws away the whole precache and the worker never installs. A
         missing icon must not cost the offline shell. */
      .then((cache) => Promise.all(
        PRECACHE.map((url) => cache.add(url).catch(() => null))
      ))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => (k.startsWith("cvstand-") || k.startsWith("resumecraft-")) && !CURRENT.has(k))
            .map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  /* Only GET is cacheable, and only our own origin is ours to cache. */
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (isLive(url)) return;

  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(SHELL_CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || caches.match("/builder")))
    );
    return;
  }

  if (isStatic(url)) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(ASSET_CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }))
    );
  }
});
