# GAZİ Kampüs Uçuş Simülatörü — Proje Belleği

## Proje Nedir?
ESP32 (Lolin32 Lite) + MPU-6050 IMU ile fiziksel eğim kontrollü, tarayıcıda çalışan
3D uçuş simülatörü. Gazi Üniversitesi (Beşevler/Yenimahalle, Ankara) kampüsünün
gerçek OpenStreetMap geometrileri üzerinde uçulur. Arayüz Türkçe.
Uzak repo: https://github.com/GaziErgenekon/TanitimUcak

## Dosya Yapısı
- `index.html` — Tek dosya uygulama: Three.js sahnesi, ejderha modeli, uçuş dinamiği,
  kameralar (takip/kokpit/gezin), HUD, veri kaynakları, **Düzenleme Modu 2.0**.
  `binalar.js` + `cevre.js` globallerini okur (ikisi de yoksa çökmez).
  Başlangıç: Teknoloji Fakültesi üstü (15, 40, 639), kuzeye bakış.
- `binalar.js` — ÜRETİLİR (`araçlar/kampus_verisi.py`):
  - `ONEMLI_BINALAR`: isimli binalar. Alanlar: isim, taban, yukseklik, `osmWay`,
    renk, catRengi, `pencere` (ops.), `detay.katsayisi` (kat sayısı).
  - `ARKA_PLAN_BINALAR`: `[duzpoligon, yukseklik, osmWay]`.
  - `PARKLAR`, `YOLLAR` ([duz, genislik, tip]), `FISKIYELER`, `SPOR_ALANLARI`.
  - Yol tipleri: ana/service/footway/path/pedestrian + tertiary/unclassified/
    living/primary/motorway/steps/cycleway/track.
- `cevre.js` — ÜRETİLİR, opsiyonel katmanlar:
  - `AGACLAR` [x,z,tip], `ISLETMELER` [x,z,tip,isim], `OTOPARKLAR` [duzpoligon],
    `DURAKLAR` [x,z,tip,isim], `RAYLAR` [duzpoligon,tip].
- `araçlar/elle_veri.json` — **ELLE DÜZENLEMELERİN TEK KAYNAĞI** (commitlenir):
  binalar (sabit poligonlar; `osmWay` verirsen OSM kopyası otomatik silinir),
  `sil` (yoksayılacak way id), `sira` (baştaki binalar), `renkler`, `pencereler`,
  `parklar`, `fiskiyeler`, `yollar`, `poiler`, `agaclar`.
- `araçlar/kampus_verisi.py` — binalar.js + cevre.js üretici (stdlib only;
  3 Overpass ucu × GET/POST; `araçlar/osm_onbellek.json` önbelleği;
  `--onbellek` ile ağsız üretim; `building:levels`/`height` (3-15 kat / 3-60 m
  sınırıyla) yoksa alan tahmini; bina çakışması elle poligonlara göre ayıklanır).
- `esp32_ucak_kumandasi/esp32_ucak_kumandasi.ino` — Lolin32 Lite firmware:
  MPU-6050 complementary filtre (50 Hz) + buton + **BLE (Nordic UART)** + batarya.
  USB seri ve BLE **aynı anda** basar. Butona >1.5 sn basmak BLE'yi aç/kapatır.
- `seri_kopru.py` — Firefox/Safari için USB seri → WebSocket köprüsü
  (`ws://localhost:8765`, port otomatik: ttyUSB*/ttyACM*).
- `bt_kopru.py` — BLE → WebSocket köprüsü (bleak; Firefox/Safari için).
- `test/` — `node --test test/test.mjs` (three opsiyonel: /tmp/opencode/geo).

## Protokol / Donanım
- CSV (50 Hz): `pitch,roll,butonState,pil_mV` — eski 3 alanlı firmware ile uyumlu;
  `pil_mV=-1` → batarya ölçümü kapalı (HUD `—`).
- Pinler: SDA=25, SCL=26, buton=4 (GND, pull-up). Batarya (ops.): BAT+ → 100k/100k
  → GPIO35 + 100nF; firmware'de `PIL_AKTIF 1` yapınca okunur (Lolin32 Lite'ta
  dahili bölücü yok varsayımı; önce multimetreyle doğrula).
- BLE NUS UUID'leri: servis 6E400001-…, TX(notify) 6E400003-…, RX 6E400002-…;
  cihaz adı `GAZI-UCAK`. Web Bluetooth Chrome/Edge + localhost/HTTPS ister.
- Eksen kuralı: X ileri, Z yukarı → pitch burun-yukarı +, roll sağa-yatış +.
  (pitch gyroY'nin NEGATİFİ, roll gyroX'in POZİTİFİ — fizik gereği.)

## Mimari Kararlar
- **Koordinat:** kampüs merkezi (39.9435 N, 32.8205 E) = (0,0). x=doğu(+), z=güney(+),
  metre. Three.js'te -Z = kuzey/ileri.
- **Rektörlük/Dekanlık/Taşkent:** kullanıcı onaylı sabit poligonlar artık
  `elle_veri.json > binalar` içinde (üretici kodunda değil). Yeniden üretim
  bunları KORUR; çakışan arka plan binası üreticide ayıklanır.
- **Bina geometrisi:** `THREE.Shape((x,-z))` → Extrude → `rotateX(-π/2)`.
  **ExtrudeGeometry grup 0 = kapak (çatı), grup 1 = yan duvar** (three.js sırası;
  eski kod ters varsayıyordu!). Materyal dizisi `[catMat, yanMat]` olmalı.
  Yan duvar UV'leri `(x, 1-depth)` gelir → `duvarUVGuncelle()` duvar grubunu
  yeniden yazar: u = baskın yatay eksen (m), v = dünya yüksekliği (m).
  Böylece doku repeat'i metre cinsinden çalışır, kat hizası tutar.
- **Pencereler:** `pencereAyar()` parametrik: kolonAralik (varsayılan 1.6 m),
  katAralik (varsayılan `yukseklik/detay.katsayisi` veya 3 m), genislik, yukseklik,
  zeminBos, yogunluk, renk, isikOran. `pencereDokusu()` önemli binalarda tam
  yükseklik dokusu (her kat ayrı çizilir, zemin hizası birebir); arka planda
  **tek kat karosu** + 4 varyant kovası (duvar = 4 merge mesh, çatı 1 mesh).
  `pencere:false` → penceresiz. `--PENCERE-AYAR/DOKU--` blok imzalarını bozma.
- **Arka plan:** `mergeGeometries` grupları düşürür; malzeme dizili tek mesh
  ÇİZİLMEZ → duvar/çatı ayrı mesh. `arkaKur(haric)` yeniden kurar; her mesh'te
  `userData.araliklar` face→bina eşlemesi (düzenleme seçimi için).
- **Ağaçlar:** instanced (1 gövde + 3 yaprak = 4 çizim); OSM `natural=tree/tree_row`
  + park/orman içine prosedürel (bütçe 6000, kapsam 1400 m). POI'ler mesafeyle
  sönen billboard sprite.
- **Düzenleme Modu 2.0 (E):** tıkla-seç (önemli + arka plan), köşe sürükle,
  köşe ekle/sil, isim/yükseklik/kat/renk/pencere canlı önizleme, "JSON Kopyala"
  (`elle_veri.json > binalar` kaydı üretir). Arka plan binası seçilince kovadan
  çıkarılıp bireysel düzenlenebilir binaya dönüşür.
- **Veri kaynakları:** Web Serial / Web Bluetooth / WebSocket. Ortak `satirIsle()`;
  BLE bildirimi satır bölebilir → tampon. Buton 1→0 kenar sönümlemesi: 3 ardışık
  aynı örnek + 500 ms refractory (`butonKenarIsle`).
- **İşleme:** EMA α=0.15 + ±2° deadband + C kalibrasyon. `YURUT_*` işaret sabitleri.
- **Uçuş:** 25 m/s; roll→yaw, pitch→irtifa; min 0.8 m; ±1300 m sınır.
- **Kameralar:** takip ↔ kokpit (buton/Enter) + gezin (G: WASD, oklar, Q/Z, +/-).
- **Katman paneli:** Önemli/Etiket/Arka plan/Yol/Park/Spor/Fıskiye/Ağaç/
  İşletme-Durak/Otopark/Raylı.

## Çalıştırma
```bash
python3 -m http.server 8000
# Veri: python3 araçlar/kampus_verisi.py [--onbellek]
# Chrome/Edge: "Seri Porttan Bağlan" veya "Bluetooth ile Bağlan" (Web Bluetooth)
# Firefox: PYTHONPATH=libs python3 seri_kopru.py  (veya bt_kopru.py) + "WebSocket ile Bağlan"
# Arduino IDE: esp32_ucak_kumandasi.ino'yu Lolin32 Lite'a yükle (115200 baud izle)
```

## Kısıtlar / Notlar
- Web Bluetooth yalnız Chromium + güvenli bağlam (localhost/HTTPS); Firefox/Safari
  için `bt_kopru.py` (pip: bleak websockets). Web Serial da yalnız Chromium.
- ESP32'de 3D render imkânsız (PC/Pi gerekir).
- OSM'de `height` yok → `building:levels` (varsa) ×3 m×2 görsel ölçek; C Blok'un
  hatalı 66 kat/220 m verisi sınırlarla reddedilir. Overpass sık 504 verir →
  üretici önbelleğe düşer; `osm_onbellek.json` commitlenmez.
- Elle düzenlemeler artık kalıcı: önce `elle_veri.json`'a yaz (Edit 2.0 JSON'unu
  yapıştır), sonra üret. Doğrudan binalar.js düzenlemek yeniden üretimde kaybolur.

## Testler
- `node --check` (index.html modülü çıkartılarak, binalar.js, cevre.js).
- `node --test test/test.mjs`: pencere parametreleri/UV, buton sönümleme, CSV 3/4
  alan, pil yüzdesi, veri geçerliliği (isim tekilliği, ±1400 m, way id), geometri
  (extrude yönü, grup 0=kapak/1=duvar, dilimle, merge) — three varsa
  (`npm --prefix /tmp/opencode/geo i three@0.160.0`; yoksa geometri atlanır).
- `python3 -m py_compile seri_kopru.py bt_kopru.py araçlar/kampus_verisi.py`.
- Firefox headless duman testi: `python3 -m http.server` + `firefox --headless
  --screenshot` (WebGL yazılım render ile sahne görünür).
- arduino-cli bu makinede yok; .ino derleme doğrulaması kullanıcıda (API kullanımı
  standart Arduino-ESP32 BLE API'si; filtre matematiği simülasyonla doğrulanmıştı).
- Köprü e2e: pty → seri_kopru.py → ws istemcisi (PYTHONPATH=/tmp/opencode/libs).
