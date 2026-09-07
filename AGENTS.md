# GAZİ Kampüs Uçuş Simülatörü — Proje Belleği

## Proje Nedir?
ESP32 (Lolin32 Lite) + MPU-6050 IMU ile fiziksel eğim kontrollü, tarayıcıda çalışan
3D uçuş simülatörü. Gazi Üniversitesi (Beşevler/Yenimahalle, Ankara) kampüsünün
gerçek OpenStreetMap bina geometrileri üzerinde uçulur. Arayüz Türkçe.
Uzak repo: https://github.com/GaziErgenekon/TanitimUcak

## Dosya Yapısı
- `index.html` — Tek dosya uygulama: Three.js sahnesi, ejderha modeli (kanat çırpma
  + sallanma animasyonlu), uçuş dinamiği, kameralar (takip/kokpit/gezin), HUD,
  veri kaynakları. `binalar.js` globallerini okur. Başlangıç: Teknoloji Fakültesi
  üstü (15, 40, 639), kuzeye bakış.
- `binalar.js` — Kampüs çevre verisi (ELLE DÜZENLENEBİLİR):
  - `ONEMLI_BINALAR`: isimli binalar (taban [x,z], yükseklik, renk, catRengi,
    pencere:{yogunluk,renk,isikOran}/false, detay).
  - `ARKA_PLAN_BINALAR`: kompakt [duzpoligon, yukseklik] (OSM otomatik).
  - `PARKLAR`: {isim, tip, taban} düz yeşil poligonlar.
  - `YOLLAR`: [duzluk, genislik(m), tip] — tip: ana/service/footway/path/pedestrian
    (residential→service, secondary/trunk→ana olarak normalize edilir).
  - `FISKIYELER`: {isim, merkez, yaricap}.
  - `SPOR_ALANLARI`: {isim, spor, taban} — futbol/tenis/basket sahaları, koşu pisti.
  - Üreten: `araçlar/kampus_verisi.py` (Overpass → önbellek → bu dosya).
- `esp32_ucak_kumandasi/esp32_ucak_kumandasi.ino` — Lolin32 Lite firmware:
  MPU-6050 complementary filtre (pitch/roll, 50 Hz) + buton, CSV `pitch,roll,buton`.
  Pinler: SDA=25, SCL=26, buton=4 (GND'ye, pull-up). Kütüphane: Adafruit MPU6050.
  Eksen kuralı: X ileri, Z yukarı → pitch burun-yukarı +, roll sağa-yatış +.
  (pitch gyroY'nin NEGATİFİnden, roll gyroX'in POZİTİFİnden gelir — fizik gereği.)
- `seri_kopru.py` — Firefox/Safari için seri→WebSocket köprüsü (`ws://localhost:8765`).
- `araçlar/kampus_verisi.py` — binalar.js üretici (stdlib only; dayanıklı istemci:
  3 endpoint × GET/POST denemesi, `araçlar/osm_onbellek.json` önbelleği).
- `.gitignore` — `__pycache__`, `libs/`, `.venv/`, `node_modules/`, `osm_onbellek.json`
  repo DIŞINDA tutulur. (`osm_onbellek.json` yeniden üretilebilir ara veridir.)

## Mimari Kararlar
- **Koordinat:** kampüs merkezi (39.9435 N, 32.8205 E) = (0,0). x=doğu(+), z=güney(+),
  metre. Three.js'te -Z = kuzey/ileri.
- **Rektörlük:** OSM'de isimli değil. Kullanıcı onaylı kural: fıskiye (213,401)
  bitişiğindeki blok. Üretici, işaret noktasına (39.939483, 32.822092) en yakın
  ≥400 m² binayı seçer (şu an OSM way 418594116 değil, **way 418645330**:
  45×31 m, merkez ~177,530 — parkın güney bitişiği). Şüpheliyse binalar.js'ten elle
  düzelt (düzenleme modu + E tuşu ile konum bulunur).
- **Dekanlık:** OSM'de kaydı yok. Kullanıcı linkiyle (39.938969, 32.820167) OSM
  way 418133405 poligonu sabitlendi (`SABIT_DEKANLIK_*`, 16 nokta, 18 m).
  Üretici sabit poligonları (`sabitler` listesi) her üretimde başa ekler ve
  çakışan arka plan binasını çıkarır.
- **Taşkent:** OSM'de kaydı yok. Link çevresindeki bitişik 3 blok (OSM way
  418129562/418129558/418133414) "Taşkent Binası 1/2/3" olarak sabitlendi
  (`SABIT_TASKENT_*`, 18 m).
- **Bina geometrisi:** `THREE.Shape((x,-z))` → Extrude → `rotateX(-π/2)`. Yan+çatı için
  2 materyal grubu (0/1). Duvarlarda prosedürel pencere dokusu (3×6m karo, 2×2 küçük
  pencere, tekrarlı UV;
  arka plan tek doku, önemlilerde bina başına + `pencere` alanından ayarlanır).
  Arka plan duvar/çatı AYRI iki merge mesh (tek malzemeli). NOT: mergeGeometries
  grupları düşürür; malzeme dizili tek mesh HİÇ ÇİZİLMEZ — `dilimle()` ile ayır.
  Yollar: genişlikli şerit (ribbon)
  tek mesh + vertex rengi (ana=asfalt, service=gri, yaya=açık). Parklar: ShapeGeometry
  (y=0.05). Fıskiye: mavi daire + silindir sütun. Spor: futbol yeşil, pist kırmızı,
  tenis mavi (y=0.06). Veri listeleri `typeof` korumasıyla okunur (eski binalar.js
  ile çökmez).
- **Veri kaynakları:** Web Serial (Chromium) veya WebSocket köprüsü. Ortak `satirIsle()`
  CSV parse; buton 1→0 düşen kenarında kamera değişir — web tarafında sönümleme var:
  3 ardışık aynı örnek (~60ms) + 500ms refractory (`butonKenarIsle`, test.mjs'te
  senaryolarla doğrulanır). Tek-seferlik klavye tuşlarında `e.repeat` yoksayılır.
- **İşleme:** EMA α=0.15 + ±2° deadband + "Sıfırla"/C kalibrasyonu. `YURUT_*` işaret sabitleri.
- **Uçuş:** 25 m/s sabit; roll→yaw (banklı dönüş), pitch→irtifa; min 0.8 m; ±1300 m sınır.
- **Kameralar:** takip ↔ kokpit (buton/Enter) + **gezin modu** (G): WASD hareket,
  ok tuşları bakış, Q/Z irtifa, +/- hız; uçaktan bağımsız, uçak uçmaya devam eder.
- **Klavye simülasyonu:** ok tuşları (Sol=negatif roll → sola dönüş; sağ=pozitif).
- **Düzenleme modu (E):** en yakın önemli bina bilgisi veya uçak konumundan yeni bina
  şablonu panel/konsola döker → binalar.js'e yapıştır.

## Çalıştırma
```bash
python3 -m http.server 8000
# Chrome/Edge: "Seri Porttan Bağlan" | Firefox: "PYTHONPATH=libs python3 seri_kopru.py" + "WebSocket ile Bağlan"
# Arduino IDE: esp32_ucak_kumandasi.ino'yu Lolin32 Lite'a yükle (115200 baud izle)
```

## Kısıtlar / Notlar
- Web Serial yalnızca Chromium; ESP32'de 3D render imkânsız (PC/Pi gerekir).
- OSM'de bina `height` yok → 2-8 kat (6-24 m) taban-alan tahmini.
- Overpass sık 504 verir → üretici önbelleğe düşer; `osm_onbellek.json` commitlenmez.
- binalar.js'i yeniden üretmek elle ONEMLI düzenlemelerini EZER — önce yedekle.
- arduino-cli bu makinede yok; .ino derleme doğrulaması yapılamadı (API kullanımı standart,
  filtre matematiği Python simülasyonuyla doğrulandı).

## Testler
- `node --check` (index.html modülü + binalar.js).
- Geometri testi /tmp/opencode/geo/test.mjs (three@0.160, npm --prefix ile kurulur):
  extrude yönü, materyal grupları, merge, 32 önemli bina, Rektörlük konumu
  (fıskiye bitişiği), PARKLAR/YOLLAR/FISKIYELER/SPOR_ALANLARI geçerliliği,
  futbol+koşu pisti varlığı, ±1300 m kapsam.
- Köprü e2e: pty → seri_kopru.py → ws istemcisi (PYTHONPATH=/tmp/opencode/libs).
- CDN jsdelivr three@0.160.0 erişilebilir.
