# GAZİ Kampüs Uçuş Simülatörü — Proje Belleği

## Proje Nedir?
ESP32 (Lolin32 Lite) + MPU-6050 IMU ile fiziksel eğim kontrollü, tarayıcıda çalışan
3D uçuş simülatörü. Gazi Üniversitesi (Beşevler/Yenimahalle, Ankara) kampüsünün
gerçek OpenStreetMap bina geometrileri üzerinde uçulur. Arayüz Türkçe.

## Dosya Yapısı
- `index.html` — Tek dosya uygulama: Three.js sahnesi, uçak modeli, uçuş dinamiği,
  kameralar, HUD, veri kaynakları. Üzerinde `binalar.js` global const'larını okur.
- `binalar.js` — Kampüs bina verisi (ELLE DÜZENLENEBİLİR):
  - `ONEMLI_BINALAR`: isimli önemli bina listesi (taban poligonu [x,z] metre,
    yükseklik, renk, catRengi, detay). Kullanıcı bu listeyi düzenler.
  - `ARKA_PLAN_BINALAR`: kompakt [duzpoligon, yukseklik] listeleri (OSM'den otomatik).
  - Üreten: `araçlar/kampus_verisi.py` (Overpass API → bu dosyayı yeniden yazar).
- `seri_kopru.py` — Firefox/Safari desteği için seri→WebSocket köprüsü.
- `araçlar/kampus_verisi.py` — binalar.js üretici (stdlib only, Overpass GET).

## Mimari Kararlar
- **Koordinat sistemi:** kampüs merkezi (39.9435 N, 32.8205 E) = (0,0).
  x = doğu (+), z = güney (+), birim metre. Three.js'te -Z = kuzey/ileri yön.
- **Bina geometrisi:** `THREE.Shape((x, -z))` → `ExtrudeGeometry` → `rotateX(-π/2)`.
  Yan cephe + çatı için 2 materyal grubu (yan=0, çatı=1). Arka plan tek
  `mergeGeometries` birleşik mesh (performans).
- **Veri kaynakları (çift mod):** Web Serial API (Chromium) veya WebSocket
  (`ws://localhost:8765`, seri_kopru.py). Ortak `satirIsle()` CSV parse:
  `pitch,roll,butonState` (115200 baud, `\n` sonlu; buton 1=dolu, 0=basılı,
  1→0 düşen kenarda kamera değişir).
- **Sensör işleme:** EMA (α=0.15) + ±2° deadband + kalibrasyon offset'i
  ("Sıfırla" butonu / C tuşu). İşaret düzeltmeleri `YURUT_PITCH/YURUT_ROLL` sabitleri.
- **Uçuş:** sabit 25 m/s; roll → yaw dönüşü, pitch → irtifa; min irtifa 0.8 m;
  ±1300 m uçuş sınırı.
- **Kameralar:** takip (3. şahıs, lerp-arka takip) ↔ kokpit (1. şahıs).
- **Düzenleme modu:** E tuşu/butonu → en yakın önemli bina bilgisi ya da yeni bina
  şablonu (uçak konumundan) panel/konsola döker; kullanıcı binalar.js'e yapıştırır.
- **Klavye simülasyonu:** checkbox; ok tuşları pitch/roll, Enter = kamera toggle.
  Donanımsız test için.

## Çalıştırma
```bash
python3 -m http.server 8000        # Web Serial localhost güvenli bağlam ister
# Chrome/Edge: "Seri Porttan Bağlan"
# Firefox: terminale "PYTHONPATH=libs python3 seri_kopru.py" sonra "WebSocket ile Bağlan"
```

## Önemli Kısıtlar
- Web Serial API yalnızca Chromium tabanlı tarayıcılarda var; Firefox için köprü.
- ESP32'yi doğrudan ekrana (TFT) bağlayıp 3D render etmek pratik olarak imkânsız —
  PC/Raspberry Pi gerekir (520 KB RAM, GPU yok).
- Kampüs bina yükseklikleri tahmini (OSM'de height etiketi yok; 2-8 kat = 6-24 m,
  taban alanından deterministik). Kullanıcı önemli binaların yüksekliğini elle verir.

## Süreç Kararları (kullanıcı tercihleri)
- Kampüs ortamı (basit şehir değil), gerçek uçuş dinamiği (sadece görsel tilt değil).
- Önemli binalar kullanıcı tarafından binalar.js içinde elle düzenlenecek.
- Rektörlük OSM'de isimli değildi: yer tutucu olarak eklendi, düzenleme moduyla konum
  bulunabilir.
- Yeni OSM verisi gerekince `python3 araçlar/kampus_verisi.py` binalar.js'i
  YENİDEN ÜRETİR — elle düzenlemeler ONEMLI_BINALAR'da korunmak isteniyorsa
  üretim öncesi kopyala.

## Testler
- `node --check`, geometri doğrulama testi /tmp/opencode/geo/test.mjs (three@0.160).
- Köprü e2e: /tmp/opencode/ws_kopru_testi.py (pty → seri_kopru.py → ws istemcisi).
- CDN (jsdelivr three@0.160.0) erişilebilir.
