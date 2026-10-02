/// <reference lib="webworker" />
// The service worker: the shell and its assets cached by hash, the reading routes of the app cached
// for a known page to open without a connection, and push messages shown as notifications. It is
// built by vite-plugin-pwa (injectManifest), which fills in the precache list.
import { clientsClaim } from "workbox-core";
import { ExpirationPlugin } from "workbox-expiration";
import {
  cleanupOutdatedCaches,
  createHandlerBoundToURL,
  precacheAndRoute,
  type PrecacheEntry,
} from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";
import { CacheFirst, NetworkFirst } from "workbox-strategies";

interface WorkerGlobal extends ServiceWorkerGlobalScope {
  __WB_MANIFEST: (string | PrecacheEntry)[];
}
declare const self: WorkerGlobal;

interface PushPayload {
  title?: string;
  body?: string;
  url?: string;
}

clientsClaim();
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

registerRoute(
  new NavigationRoute(createHandlerBoundToURL("/index.html"), { denylist: [/^\/api\//, /^\/healthz$/] }),
);
// Small renditions, immutable by hash: kept for offline viewing, a bounded number of them.
registerRoute(
  ({ url }) => /^\/api\/images\/[^/]+\/(thumb|preview)$/.test(url.pathname),
  new CacheFirst({
    cacheName: "photos",
    plugins: [new ExpirationPlugin({ maxEntries: 400, maxAgeSeconds: 30 * 24 * 3600 })],
  }),
);
// Everything else the app reads, so a known page opens without a connection. Never the originals,
// the full renditions or downloads.
registerRoute(
  ({ url }) =>
    url.pathname.startsWith("/api/") &&
    !/\/(original|full)$/.test(url.pathname) &&
    !url.pathname.includes("/download") &&
    !url.pathname.startsWith("/api/reference-card"),
  new NetworkFirst({
    cacheName: "api",
    networkTimeoutSeconds: 4,
    plugins: [new ExpirationPlugin({ maxEntries: 500 })],
  }),
);

// The page decides when a new version takes over (registerType "prompt").
self.addEventListener("message", (event) => {
  if ((event.data as { type?: string } | undefined)?.type === "SKIP_WAITING") void self.skipWaiting();
});

// A push message is JSON the browser has already decrypted: a title, a line or two, where to open.
self.addEventListener("push", (event) => {
  let payload: PushPayload | undefined;
  try {
    payload = event.data?.json() as PushPayload | undefined;
  } catch {
    payload = undefined;
  }
  if (!payload?.title) return;
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body ?? "",
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      tag: "nevus-due",
      data: { url: payload.url ?? "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data as { url?: string } | undefined)?.url ?? "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (windows) => {
      const open = windows[0];
      if (open) {
        await open.focus();
        await open.navigate(url);
        return;
      }
      await self.clients.openWindow(url);
    }),
  );
});
