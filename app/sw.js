// 앱 화면은 캐시(오프라인에서도 열림), 데이터는 항상 최신 우선
const C = "jarvis-v23";
const SHELL = ["./", "index.html", "style.css", "app.js", "icon.svg", "icon-192.png", "manifest.webmanifest"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(C).then((c) => c.addAll(SHELL))); self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== C).map((k) => caches.delete(k))))); self.clients.claim(); });
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.hostname === "api.github.com" || u.pathname.includes("/previews/")) return;  // 영상은 캐시 안 함(부분 요청)
  const isShell = u.origin === location.origin && u.pathname.includes("/app/");
  e.respondWith(isShell
    ? fetch(e.request).then((r) => { const cp = r.clone(); caches.open(C).then((c) => c.put(e.request, cp)); return r; }).catch(() => caches.match(e.request))
    : fetch(e.request).catch(() => caches.match(e.request)));
});
