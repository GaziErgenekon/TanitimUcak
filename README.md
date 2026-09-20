# GAZİ Kampüs Uçuş Simülatörü

Gazi Üniversitesi (Beşevler/Yenimahalle, Ankara) kampüsünün gerçek
OpenStreetMap geometrileri üzerinde, **ESP32 + MPU-6050** eğim sensörüyle
fiziksel olarak kontrol edilen, tarayıcıda çalışan 3D uçuş simülatörü.
Arayüz Türkçe; **internet bağlantısı gerektirmez** (Three.js depo içindedir)
ve yayınlandığında **PWA** olarak kurulup çevrimdışı da açılabilir.

- Kampüs binaları, yollar, parklar, ağaçlar, kapılar/bayraklar ve uzak
  bölgeler (Maltepe Mühendislik, Ankara Garı) gerçek konumlarıyla.
- Üç araç: **Ejderha (Dişsiz)**, **Uçak**, **Kurt** (Ayarlar > Görünüm).
- Takip/kokpit kamerası, serbest gezinme, çarpışma, Düzenleme Modu 2.0.
- Kumanda: USB seri veya Bluetooth LE; kurulum gerektirmeden klavye ile de
  uçulabilir.

**İki çalıştırma yolu vardır:**
1. **Yayınlanmış sayfa** (önerilen, Chrome/Edge): `campus.gazisiber.org`
   adresini aç → USB kumandayı tak → "Seri Porttan Bağlan". Python gerekmez.
2. **Yerel kopya** (çevrimdışı/garanti): depoyu indir, `./baslat.sh`
   (Windows: `baslat.bat`, macOS: `baslat.command`) çalıştır.

---

## Hızlı Başlangıç (stand görevlisi)

### Gereksinimler

| Ne | Zorunlu mu? | Not |
|---|---|---|
| Chrome/Edge **veya** Firefox 151+ | Evet | Chrome/Edge'de Python gerekmez |
| Python 3.9+ | Yalnız köprü (Firefox/Safari) için | `baslat` scripti kurar |
| ESP32 kumanda (USB veya BLE) | Hayır | Sensör yoksa klavye modu var |

### 1) Simülatörü aç

**Yayınlanmış sayfa (en kolay):** tarayıcıda `https://campus.gazisiber.org`
adresini açın. USB kumanda için Python gerekmez (Chrome/Edge).

**Yerel kopya:** Linux `./baslat.sh` · macOS `baslat.command` (çift tık) ·
Windows `baslat.bat`. Başlatıcı boş bir portta (8000'den başlayarak) yerel
sunucuyu açar ve tarayıcıyı otomatik açar. İnternet gerekmez.

### 2) Kumandayı bağla

Kumandayı USB ile takın (veya BLE için açık bırakın) ve tarayıcıda:

| Tarayıcı | USB seri | Bluetooth (BLE) |
|---|---|---|
| **Chrome / Edge** | **"Seri Porttan Bağlan"** (önerilen) | "Bluetooth ile Bağlan" |
| **Firefox 151+** | Siteye özel "seri port" eklentisi kurulur + "Seri Porttan Bağlan" | Köprü: `baslat.sh bt` + "WebSocket ile Bağlan" |
| **Safari** | Doğrudan desteklenmez → Chrome/Edge veya köprü | Desteklenmez → Chrome/Edge veya köprü |

- **Chrome/Edge + USB** en kolay yoldur: Python bile gerekmez.
- **Firefox/Safari + köprü**: `./baslat.sh seri` (macOS: `baslat.command seri`;
  Windows: `baslat.bat seri`) + tarayıcıda "WebSocket ile Bağlan".
  Yayınlanmış sayfa kullanıyorsanız yalnız köprü modu yeter:
  `./baslat.sh kopru-seri` / `baslat.bat kopru-seri`.
- Köprü modunda başlatıcı ilk çalıştırmada `.venv` (olmazsa `libs/`)
  oluşturup bağımlılıkları indirir; **yalnız bu ilk kurulumda internet
  gerekir**. Kurulumu standdan önce bir kez yapın; sonraki açılışlar
  internetsiz çalışır.
- Yerel sayfa açılışta WebSocket köprüsüne kendiliğinden bağlanır. Yayınlanmış
  sayfada otomatik deneme yapılmaz; bağlanma her zaman düğmeyle olur.
- Köprü 8765 numaralı yerel portu kullanır; aynı anda tek köprü çalıştırın.
- **Chrome/Edge 147+ notu (yayınlanmış sayfa + köprü):** Tarayıcı ilk bağlanmada
  "yerel ağa erişim" izni sorar → **İzin ver**'i seçin. İzin, site başına
  hatırlanır; reddedildiyse adres çubuğundaki site izinlerinden açılabilir.
  Kurumsal makinelerde yönetici `LocalNetworkAccessAllowedForUrls` politikasıyla
  izni önceden verebilir (bkz. Yayın bölümü).

### 3) Uç

- Kartı öne doğru eğin → tırmanış, sağa yatırın → sağa dönüş.
- Kumandadaki buton: **kamera değiştir** (takip ↔ kokpit).
- Butona 1.5 sn basılı tutmak ESP32'de **BLE'yi aç/kapatır** (uzun süre
  kullanılmayacaksa kapatın).
- `C` tuşu: uçuş sıfırlama (kartı düz tutup basın) — sapmaları düzeltir.
- HUD her şeyi gösterir: kaynak, pitch/roll, irtifa, hız, pil, veri akışı.

### 4) Kapat

Köprü/sunucu penceresinde **Ctrl+C**, Windows'ta pencereyi kapatın.

---

## Sensörsüz Deneme (klavye)

Kumanda yoksa veya arıza yaparsa simülatör klavyeyle uçulur:

1. Sağ üstten **Ayarlar (H)** panelini açın.
2. **Klavye simülasyonu** kutusunu işaretleyin.
3. Ok tuşları: yukarı/aşağı pitch, sol/sağ roll. `C` ile sıfırlayın.

## Kısayollar

| Tuş | İşlev |
|---|---|
| `Enter` / kumanda butonu | Kamera: takip ↔ kokpit |
| `H` / `Esc` | Ayarlar panelini aç / kapat |
| `C` | Uçuş sıfırlama / kalibrasyon |
| `G` | Gezin modu (serbest kamera): WASD, ok tuşları, Q/Z, +/- |
| `E` | Düzenleme Modu 2.0 (bina seç, köşe sürükle, JSON üret) |
| Ok tuşları | Klavye simülasyonunda pitch/roll |

## Ayarlar Paneli (H)

- **Görünüm**: ejderha / uçak / kurt.
- **Uçuş hızı**: 10–120 m/s.
- **Konumlar**: kampüs, Maltepe Mühendislik, Ankara Garı ve kapılar
  arasında hızlı ışınlanma.
- **Çarpışma**: bina ve ağaç çarpışmasını kapatma (standda serbest uçuş
  isterseniz kapatın).
- **Katmanlar**: önemli binalar, arka plan, yollar, ağaçlar, uzak bölgeler
  vb. — bilgisayar yavaşsa gereksiz katmanları kapatın.

---

## macOS Notları

Mac'lerde en kolay yol **Chrome/Edge**'dir (Chrome 89+ macOS'ta Web Serial ve
Web Bluetooth'u destekler):

- **Bluetooth (BLE) ile bağlanın** → hiçbir sürücü gerekmez: kumandayı açın,
  "Bluetooth ile Bağlan" düğmesine basın.
- **USB ile bağlanacaksanız** Lolin32 Lite'ın CP2102 çipi için Silicon Labs
  CP210x VCP sürücüsü (6.0.2+) gerekir. Kurulumdan sonra **Sistem Ayarları >
  Gizlilik ve Güvenlik**'te "Silicon Laboratories" sistem uzantısına izin verip
  Mac'i yeniden başlatın. Apple Silicon (M1–M4) sürücü tarafından desteklenir.
- **Safari** Web Serial/Web Bluetooth'u hiç desteklemez; Safari'de köprü
  (aşağıdaki Python yolu) veya yerel kopya kullanılmalıdır.
- **Firefox 151+** Web Serial'i destekler ama site başına Mozilla "seri port"
  eklentisi kurulumu ister; köprü daha pratik olabilir.
- **Python** (köprü için): [python.org](https://www.python.org/downloads/macos/)
  kurulumu veya `brew install python` yeterlidir.
- Depoyu zip olarak indirdiyseniz Gatekeeper scriptleri engelleyebilir:
  Terminal'de `xattr -dr com.apple.quarantine .` çalıştırın (git ile indirdiyseniz
  gerekmez). Başlatıcıya Finder'dan çift tıklamak için `baslat.command` kullanın.
- Köprü USB portunu macOS'ta otomatik bulur (`/dev/cu.usbserial-*`,
  `/dev/cu.usbmodem*`). Özel port: `./baslat.sh seri /dev/cu.usbserial-0001`.

---

## Donanım: ESP32 Kumanda

### Bağlantı şeması

| MPU-6050 | Lolin32 Lite |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO25 |
| SCL | GPIO26 |

Buton: bir ucu **GPIO4**, diğer ucu **GND** (dahili pull-up, direnç yok).
Opsiyonel batarya ölçümü için firmware başındaki açıklamaya bakın.

**Önemli**: MPU-6050'nin X ekseni uçağın ileri yönüne, Z ekseni yukarı
bakmalı. Ters monte edildiyse firmware'de `TERS_PITCH` / `TERS_ROLL`
değerlerini `-1` yapın.

### Firmware yükleme

1. Arduino IDE'ye **esp32** kart paketini ve **Adafruit MPU6050**
   kütüphanesini kurun (Kütüphane Yöneticisi).
2. `esp32_ucak_kumandasi/esp32_ucak_kumandasi.ino` dosyasını açın.
3. Kart: **WEMOS LOLIN32 Lite**, port: ESP32'nin bağlı olduğu port.
4. Yükleyin; seri monitörde (115200) `pitch,roll,buton,pil_mV` satırlarını
   görürsünüz. Açılışta kartı 2 sn hareket ettirmeyin (gyro kalibrasyonu).

### Veri protokolü

`pitch,roll,butonState,pil_mV` (50 Hz). 3 alanlı eski firmware de çalışır;
`pil_mV=-1` ise HUD'da pil `—` görünür.

---

## Sorun Giderme

| Belirti | Çözüm |
|---|---|
| Sayfa açılmıyor / boş | Başlatıcı penceresindeki adresi kullanın (ör. `http://localhost:8001`). 8000 doluysa başlatıcı otomatik başka port seçer |
| "Seri port bulunamadı" (Linux) | `sudo usermod -aG dialout $USER` + oturumu kapatıp açın; kabloyu takın |
| Windows'ta COM portu yok | ESP32 kartındaki CP210x/CH340 USB çipi için sürücü kurun (Silicon Labs CP210x VCP) |
| Tarayıcı "Web Serial desteklemiyor" diyor | Chrome/Edge kullanın; Firefox 151+ site eklentisi ister; Safari desteklemez (köprü kullanın) |
| "WebSocket bağlantısı kurulamadı" | Köprü çalışıyor mu? `baslat.sh seri` / `baslat.bat seri` ile yeniden başlatın |
| "8765 portu kullanımda" | Başka bir köprü açık; onu kapatın (Ctrl+C) |
| BLE cihazı görünmüyor | ESP32'de butona 1.5 sn basıp BLE'yi açın; tarayıcı izinlerini kontrol edin. Linux'ta `sudo usermod -aG bluetooth $USER` |
| Sensör ters çalışıyor | Firmware'de `TERS_PITCH` / `TERS_ROLL` işaretini çevirin |
| Uçak sürekli yana kaçıyor | Kartı düz tutup `C` (sıfırla); ESP32'yi hareket ettirmeden yeniden başlatın |
| Sahne ağır/ısınıyor | Ayarlar > Katmanlar'dan arka plan/ağaç/uzak bölgeyi kapatın; pencereyi küçültün |
| Köprü ilk kurulumda hata | İnternet gerekir. Linux'ta `sudo apt install python3-venv` önerilir; başlatıcı aksi halde `libs/` klasörüne kurar |
| Yayınlanmış sayfada köprü bağlanmıyor (Chrome) | Tarayıcı "yerel ağa erişim" iznini reddetmiş olabilir: adres çubuğu > site izinleri > Yerel ağ = İzin ver, sayfayı yenileyin |
| macOS'ta USB portu yok | CP210x VCP sürücüsünü kurup izin verin; ya da Bluetooth ile bağlanın (sürücüsüz) |
| Firefox'ta "Seri Porttan Bağlan" hata veriyor | Firefox 151+ siteye özel seri port eklentisini ister; kurmak istemezseniz `kopru-seri` kullanın |
| PWA eski sürümü gösteriyor | Sunucuda `sw.js` ve `index.html` "no-cache" sunulmalı; yeni sürümde `sw.js` içindeki `SURUM` artırılır (bkz. Yayın) |

---

## Yayın (campus.gazisiber.org)

Simülatör **tamamen statik**tir; sunucuda Python/Node çalışmaz. Köprü, her
ziyaretçinin kendi bilgisayarında çalışır.

```bash
python3 araçlar/yayin_paketi.py --zip     # yayin/ klasörü + yayin.zip
```

Paketteki dosyaları sunucudaki site köküne kopyalayın (alt dizine de
koyabilirsiniz; tüm yollar görelidir). Gerekenler: `index.html`, üç veri
dosyası, `vendor/`, `manifest.webmanifest`, `sw.js`, `ikon-*.png`.

**Örnek Caddy yapılandırması:**

```caddy
campus.gazisiber.org {
    root * /srv/campus
    file_server
    encode gzip zstd

    # İçerik güncellenince hemen görünsün (PWA önbelleği sw.js ile yönetilir)
    header /index.html Cache-Control "no-cache"
    header /sw.js Cache-Control "no-cache"
    header /manifest.webmanifest Cache-Control "no-cache"
    # Değişmeyen varlıklar uzun süre önbelleklenebilir
    header /vendor/* Cache-Control "public, max-age=31536000, immutable"
}
```

Notlar:

- **HTTPS zorunludur**: Web Serial (USB) ve service worker yalnız güvenli
  bağlamda çalışır. HTTP'de USB sessizce çalışmaz.
- **Top-level yayınlayın** (iframe içine gömmeyin). Gömmek zorundaysanız
  iframe'e `allow="serial; bluetooth; local-network; loopback-network"`
  eklenmelidir.
- **PWA**: Chrome/Edge adres çubuğundaki "Yükle" simgesiyle uygulama olarak
  kurulur; ilk açılıştan sonra çevrimdışı da açılır. Güncelleme yayınlarken
  `sw.js` içindeki `SURUM` değerini artırın.
- **Köprü izni (Chrome/Edge 147+)**: Yayınlanmış sayfa `ws://localhost:8765`
  köprüsüne bağlanırken tarayıcı "yerel ağa erişim" izni sorar. Kurumsal
  makinelerde yönetici, izni önceden verebilir:
  `LocalNetworkAccessAllowedForUrls` politikasına site adresini ekleyin
  (Edge'de aynı isimli politika).
- **Firefox/Safari** kullanıcıları köprüyü `./baslat.sh kopru-seri`
  (`baslat.bat kopru-seri`) ile çalıştırır; sayfa tarafında ek ayar gerekmez.

---

## Proje Yapısı

```
index.html                     Tek dosya uygulama (sahne, uçuş, HUD, editör)
binalar.js / cevre.js / bolgeler.js   Üretilmiş kampüs verisi
manifest.webmanifest / sw.js / ikon-*.png   PWA (kurulabilir + çevrimdışı)
baslat.sh / baslat.command / baslat.bat / baslat.py
                               Tek tık başlatıcı (sunucu/köprü + otomatik venv)
kopruler/
  seri_kopru.py                USB seri → WebSocket köprüsü (Firefox/Safari;
                               Linux/macOS/Windows port otomatik bulma)
  bt_kopru.py                  Bluetooth LE → WebSocket köprüsü
  requirements.txt             pyserial, websockets, bleak
vendor/three/                  Three.js (MIT) — internet gerekmez
esp32_ucak_kumandasi/          Lolin32 Lite firmware'i
araçlar/
  kampus_verisi.py             OSM → JS veri üreticisi
  yayin_paketi.py              Statik yayın paketi üretici (yayin/ + zip)
  elle_veri.json               Elle düzenlemelerin tek kaynağı
test/                          Node testleri (veri + geometri + PWA)
belgeler/STAND-KARTI.md        Yazdırılabilir görevli kartı
```

## Geliştiriciler için

```bash
# Yerel sunucu (veri üretmeden):
python3 -m http.server 8000

# Kampüs verisini üret (Overpass; ağ yoksa --onbellek):
python3 araçlar/kampus_verisi.py --onbellek

# Statik yayın paketi (campus.gazisiber.org için):
python3 araçlar/yayin_paketi.py --zip

# Testler:
node --test test/test.mjs
python3 -m py_compile baslat.py kopruler/seri_kopru.py kopruler/bt_kopru.py \
    araçlar/kampus_verisi.py araçlar/yayin_paketi.py
```

- **Elle düzenlemeler kalıcıdır**: önce `araçlar/elle_veri.json`'a yazın
  (Düzenleme Modu 2.0'ın "JSON Kopyala" çıktısını yapıştırın), sonra veriyi
  üretin. Doğrudan `binalar.js` düzenlemek yeniden üretimde kaybolur.
- Three.js'i güncellemek için `vendor/three/` içeriğini yeni sürümle
  değiştirin (lisans dosyasını koruyun).
- Yayın güncellemesinde `sw.js` içindeki `SURUM` değerini artırın, sonra
  `python3 araçlar/yayin_paketi.py --zip` ile paketi yenileyin.
- Ayrıntılı mimari notlar: `AGENTS.md`.

## Lisans ve Teşekkür

- Kampüs verisi: © OpenStreetMap katkıcıları (ODbL).
- Three.js: MIT (`vendor/three/LICENSE`).
