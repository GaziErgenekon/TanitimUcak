# GAZİ Kampüs Uçuş Simülatörü — Proje Belleği

## Proje Nedir?
ESP32 (Lolin32 Lite) + MPU-6050 IMU ile fiziksel eğim kontrollü, tarayıcıda çalışan
3D uçuş simülatörü. Gazi Üniversitesi (Beşevler/Yenimahalle, Ankara) kampüsünün
gerçek OpenStreetMap geometrileri üzerinde uçulur. Arayüz Türkçe.
Uzak repo: https://github.com/GaziErgenekon/TanitimUcak

## Dosya Yapısı
- `index.html` — Tek dosya uygulama: Three.js sahnesi, **3 skin** (ejderha/uçak/kurt),
  uçuş dinamiği, kameralar (takip/kokpit/gezin), HUD, **çarpışma**, veri kaynakları,
  **Ayarlar drawer'ı**, **Düzenleme Modu 2.0**. `binalar.js` + `cevre.js` +
  `bolgeler.js` globallerini okur (üçü de yoksa çökmez).
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
    `DURAKLAR` [x,z,tip,isim], `RAYLAR` [duzpoligon,tip],
    `GIRISLER` {isim,merkez,aci,pano}, `BAYRAKLAR` {isim,merkez,tip,yukseklik}.
- `bolgeler.js` — ÜRETİLİR, uzak bölgeler (opsiyonel katman):
  `UZAK_BINALAR` [duz,yuk,way], `UZAK_YOLLAR` [duz,genislik,tip],
  `UZAK_AGACLAR` [x,z,tip], `BOLGELER` {isim,merkez,bakis,irtifa} (ışınlanma).
  Maltepe (Mühendislik) r=600 + Ankara Garı r=500 tam detay; ana kampüsten
  Celal Bayar Bulvarı koridoru (around:170 bina / 120 yol) ile bağlanır.
- `araçlar/elle_veri.json` — **ELLE DÜZENLEMELERİN TEK KAYNAĞI** (commitlenir):
  binalar (sabit poligonlar; `osmWay` verirsen OSM kopyası otomatik silinir),
  `sil` (yoksayılacak way id), `sira` (baştaki binalar), `renkler`, `pencereler`,
  `parklar`, `fiskiyeler`, `yollar`, `poiler`, `agaclar`, `girisler`, `bayraklar`,
  `carpismaYok` (çarpışması kapatılacak way id'leri).
  Bina kaydında `carpisma:false` o binada çarpışmayı kapatır.
- `araçlar/kampus_verisi.py` — binalar.js + cevre.js + bolgeler.js üretici
  (stdlib only; 3 Overpass ucu × GET/POST; `araçlar/osm_onbellek.json` önbelleği
  `{merkez, uzak}`; `--onbellek` ile ağsız üretim; `building:levels`/`height`
  (3-15 kat / 3-60 m sınırıyla) yoksa alan tahmini; bina çakışması elle
  poligonlara göre ayıklanır; uzak sorgu merkez way id'lerini atlar).
- `esp32_ucak_kumandasi/esp32_ucak_kumandasi.ino` — Lolin32 Lite firmware:
  MPU-6050 complementary filtre (50 Hz) + buton + **BLE (Nordic UART)** + batarya.
  USB seri ve BLE **aynı anda** basar. Butona >1.5 sn basmak BLE'yi aç/kapatır.
- `kopruler/seri_kopru.py` — Firefox/Safari için USB seri → WebSocket köprüsü
  (`ws://localhost:8765`; port otomatik: Linux ttyUSB*/ttyACM*, macOS
  cu.usbserial*/cu.usbmodem* (cu önce) + tty.* yedeği, Windows
  `serial.tools.list_ports` COM*; kopmada 3 sn'de yeniden bağlanır).
- `kopruler/bt_kopru.py` — BLE → WebSocket köprüsü (bleak; Firefox/Safari için).
- `kopruler/requirements.txt` — pyserial, websockets, bleak (venv/libs kurulumu).
- `baslat.py` + `baslat.sh` / `baslat.command` / `baslat.bat` — tek tık
  başlatıcı: boş portta (8000-8010) yerel HTTP sunucusu + tarayıcı;
  `sunucu|seri|bt` modları; `kopru-seri|kopru-bt` yalnız köprü çalıştırır
  (campus.gazisiber.org gibi hosted sayfa için; sunucu/tarayıcı açılmaz).
  Köprü modunda `.venv` kurar, olmazsa (python3-venv yoksa) `--target libs/`
  yedeğine düşer; SIGTERM'i köprüye devreder. `requirements.txt` özetini
  `.gazi-bagimlilik` damgasına yazar → sonraki açılışlar internetsiz.
  Menü yalnız TTY varsa. `baslat.command` macOS Finder çift tık sarmalayıcısı.
- `vendor/three/` — Three.js 0.160.0 yerel kopyası (MIT, `LICENSE` ve Node
  self-reference için `package.json`). index.html importmap'i buraya bakar;
  **CDN bağımlılığı yok, internet gerekmez.**
- `manifest.webmanifest` + `sw.js` + `ikon-192.png` / `ikon-512.png` /
  `ikon-512-maskable.png` — PWA: sürümlü (SURUM) cache-first service worker;
  index.html ve sw.js sunucuda `no-cache` sunulmalı. Yayın güncellemesinde
  SURUM artırılır.
- `araçlar/yayin_paketi.py` — statik yayın paketi üretici (stdlib; `yayin/`
  klasörü ve `--zip`). Pakete Python/ESP32/test dosyaları GİRMEZ.
- `README.md` — stand görevlisi kurulum/kullanım/sorun giderme kılavuzu
  (Yayın/Caddy, macOS notları dahil).
- `belgeler/STAND-KARTI.md` — yazdırılabilir tek sayfa görevli kartı.
- `test/` — `node --test test/test.mjs` (three `vendor/three`'den;
  `/tmp/opencode/geo` yalnız yedek; PWA/yayın dosya testi dahil).

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
  + park/orman içine prosedürel (merkez bütçe 9000, kapsam 1400 m) + uzak bölge
  yol kenarı sıraları (bolgeler.js, 40 m aralık). POI ve etiketler mesafeyle söner
  (etiket 900 m, POI 260 m).
- **Düzenleme Modu 2.0 (E):** tıkla-seç (önemli + arka plan), köşe sürükle,
  köşe ekle/sil, isim/yükseklik/kat/renk/pencere/**çarpışma** canlı önizleme,
  "JSON Kopyala" (`elle_veri.json > binalar` kaydı üretir). Arka plan binası
  seçilince kovadan çıkarılıp bireysel düzenlenebilir binaya dönüşür.
- **Kapı/bayrak:** `GIRISLER` (A/C kapıları: sütun+pano+bariyer+kulübe; `aci` yola
  dik) ve `BAYRAKLAR` (12 m direk + CPU'da dalgalanan kumaş). A Kapısı konumu
  kullanıcı OSM linkinden: (141.2, 581.5); C Kapısı (376, 213).
- **Çarpışma:** 32 m spatial grid; önemli + arka plan + uzak bina poligonları ve
  ağaç silindirleri. Kaydırmalı ilerleme (tam adım → x/z ayrı); bina yüksekliği
  üstü serbest ama alçalışta `carpismaInisY` çatıya kondurur (yukarıdan içine
  girilmez). Bina başına `carpisma:false` / `CARPISMA_YOK`; Ayarlar'dan global
  ve ağaç anahtarları. `--CARPISMA--` blok imzasını bozma.
- **Modeller/skinler:** `MODEL_FABRIKASI` ejderha (Dişsiz esintili: siyah gövde,
  yeşil göz, kırmızı kuyruk yüzgeci), uçak (dönen pervane, iniş takımı) ve kurt
  (dört bacak koşu + kuyruk). Sözleşme: `{grup, yaricap, kamera, animasyon}`;
  seçim localStorage (`gazi_skin`).
- **Ayarlar drawer'ı (H/Esc):** sağ üstte; görünüm(skin), uçuş hızı (10-120 m/s,
  `gazi_hiz`), konumlar (ışınlanma), çarpışma, kamera, klavye, katmanlar.
  Sol üstte yalnız bağlantı butonları; HUD tek satır.
- **Veri kaynakları:** Web Serial / Web Bluetooth / WebSocket. Ortak `satirIsle()`;
  BLE bildirimi satır bölebilir → tampon. Buton 1→0 kenar sönümlemesi: 3 ardışık
  aynı örnek + 500 ms refractory (`butonKenarIsle`).
- **İşleme:** EMA α=0.15 + ±2° deadband + C kalibrasyon. `YURUT_*` işaret sabitleri.
- **Uçuş:** 25 m/s (ayarlanır); roll→yaw, pitch→irtifa; min 0.8 m; ±3200 m sınır.
- **Kameralar:** takip ↔ kokpit (buton/Enter) + gezin (G: WASD, oklar, Q/Z, +/-).
- **Katman paneli:** Önemli/Etiket/Arka plan/Yol/Park/Spor/Fıskiye/Ağaç/
  İşletme-Durak/Otopark/Raylı/Giriş-Bayrak/Uzak bölgeler.

## Çalıştırma
```bash
./baslat.sh [sunucu|seri|bt|kopru-seri|kopru-bt]   # Linux; macOS .command, Win .bat
python3 -m http.server 8000         # eşdeğeri (köprüsüz hızlı test)
# Yayın: python3 araçlar/yayin_paketi.py --zip
# Veri: python3 araçlar/kampus_verisi.py [--onbellek]
# Chrome/Edge: "Seri Porttan Bağlan" veya "Bluetooth ile Bağlan" (Web Bluetooth)
# Firefox: ./baslat.sh seri  (veya bt) + tarayıcıda "WebSocket ile Bağlan"
# Hosted sayfa (campus.gazisiber.org): ./baslat.sh kopru-seri  (+ "WebSocket ile Bağlan")
# Arduino IDE: esp32_ucak_kumandasi.ino'yu Lolin32 Lite'a yükle (115200 baud izle)
```

## Kısıtlar / Notlar
- Web Bluetooth yalnız Chromium + güvenli bağlam (localhost/HTTPS); Firefox/Safari
  için `kopruler/bt_kopru.py` (pip: bleak websockets). Web Serial Chrome/Edge
  masaüstünde (89+) ve **Firefox 151+**'ta var (Firefox site başına Mozilla
  "seri port" eklentisi ister); Safari hiç desteklemez.
- Stand hedefi: Chrome/Edge + USB seri en kolay yol (Python gerekmez); Firefox
  için `baslat.sh seri`/`baslat.bat seri`. Oynanış çevrimdışı çalışır
  (`vendor/three`), köprülerin ilk kurulumu internet ister.
- Windows'ta bat dosyası CRLF (`.gitattributes`); venv yolu Scripts/, Linux bin/;
  macOS'ta `baslat.command` çift tık (LF + çalıştırma biti git'te).
- **Hosted (campus.gazisiber.org)**: HTTPS zorunlu (Web Serial + SW). Chrome/Edge
  147+ yayınlanmış sayfadan `ws://localhost:8765`'e LNA izni sorar (site başına,
  `LocalNetworkAccessAllowedForUrls` ile ön verilebilir). Bu yüzden otomatik WS
  denemesi yalnız yerel sayfada (`YEREL_SAYFA`); hosted'da düğmeyle bağlanılır.
  PWA cache-first: index.html/sw.js `no-cache`, vendor uzun önbellek; sürüm
  artırımı `sw.js > SURUM`.
- Yayın paketi: `python3 araçlar/yayin_paketi.py --zip` → `yayin/` + zip
  (gitignore'lu). iframe'e gömülürse `allow="serial; bluetooth; loopback-network"`.
- ESP32'de 3D render imkânsız (PC/Pi gerekir).
- OSM'de `height` yok → `building:levels` (varsa) ×3 m×2 görsel ölçek; C Blok'un
  hatalı 66 kat/220 m verisi sınırlarla reddedilir. Overpass sık 504 verir →
  üretici önbelleğe düşer; `osm_onbellek.json` commitlenmez.
- Elle düzenlemeler artık kalıcı: önce `elle_veri.json`'a yaz (Edit 2.0 JSON'unu
  yapıştır), sonra üret. Doğrudan binalar.js düzenlemek yeniden üretimde kaybolur.

## Testler
- `node --check` (index.html modülü çıkartılarak, binalar.js, cevre.js, bolgeler.js).
- `node --test test/test.mjs`: offline three yerelleştirme, PWA dosyaları
  (manifest/sw/ikon listesi tutarlılığı), pencere parametreleri/UV, buton
  sönümleme, CSV 3/4 alan, pil yüzdesi, çarpışma matematiği (poligon
  içi/mesafe, yükseklik, ağaç, çatı kotu/iniş), kapı/bayrak ve bolgeler.js
  verisi (isim tekilliği, ±3200 m, way id), geometri (extrude yönü, grup
  0=kapak/1=duvar, dilimle, merge). three `vendor/three`'den gelir
  (Node self-reference); `/tmp/opencode/geo` yalnız yedek.
- Üretim determinist: `python3 araçlar/kampus_verisi.py --onbellek` iki kez
  çalıştırıldığında dosyalar bit bit aynı olmalı.
- `python3 -m py_compile baslat.py kopruler/seri_kopru.py kopruler/bt_kopru.py
  araçlar/kampus_verisi.py araçlar/yayin_paketi.py`.
- Firefox headless duman testi: `python3 -m http.server` + `firefox --headless
  --screenshot` (WebGL yazılım render ile sahne görünür).
- arduino-cli bu makinede yok; .ino derleme doğrulaması kullanıcıda (API kullanımı
  standart Arduino-ESP32 BLE API'si; filtre matematiği simülasyonla doğrulanmıştı).
- Köprü e2e: pty → `baslat.py kopru-seri` → ws istemcisi
  (PYTHONPATH=/tmp/opencode/libs); sunucu açılmadığı, kopma/yeniden bağlanma
  çalıştığı doğrulanır (`/tmp/opencode/test_seri_kopru.py`).
- PWA çevrimdışı: `yayin/` sunulur, Firefox profiline SW kurulur, sunucu
  kapatılıp yeniden yüklenir → uygulama kabuğu açılmalı (headless screenshot).
