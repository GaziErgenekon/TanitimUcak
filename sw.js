// GAZİ Kampüs Uçuş Simülatörü — çevrimdışı service worker.
// Güncelleme yayınlarken SURUM'u artırın: eski önbellek silinir, yeni dosyalar
// ilk yenilemede devreye girer. (index.html ve sw.js sunucuda "no-cache"
// başlığıyla sunulmalı; bkz. README > Yayın.)
const SURUM = 'gazi-ucus-v1';
const DOSYALAR = [
  './',
  './index.html',
  './binalar.js',
  './cevre.js',
  './bolgeler.js',
  './manifest.webmanifest',
  './ikon-192.png',
  './ikon-512.png',
  './ikon-512-maskable.png',
  './vendor/three/three.module.js',
  './vendor/three/addons/utils/BufferGeometryUtils.js',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(SURUM)
      .then((c) => c.addAll(DOSYALAR))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((adlar) => Promise.all(
        adlar.filter((a) => a !== SURUM).map((a) => caches.delete(a))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const istek = e.request;
  if (istek.method !== 'GET') return;
  const url = new URL(istek.url);
  if (url.origin !== location.origin) return;   // dış istek yok, güvenli kal

  if (istek.mode === 'navigate') {              // sayfa açılışı: önbellekten
    e.respondWith(
      caches.match('./index.html').then((c) => c || fetch(istek))
    );
    return;
  }

  e.respondWith(
    caches.match(istek, { ignoreSearch: true }).then((c) => {
      if (c) return c;
      return fetch(istek).then((yanit) => {
        if (yanit && yanit.ok) {
          const kopya = yanit.clone();
          caches.open(SURUM).then((ca) => ca.put(istek, kopya));
        }
        return yanit;
      });
    })
  );
});
