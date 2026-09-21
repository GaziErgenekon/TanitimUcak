# STAND KARTI — GAZİ Kampüs Uçuş Simülatörü

> Bir sayfa; yazdırıp standın yanına koyun. Ayrıntı: `README.md`

## Açılış (3 adım)

1. **Yayınlanmış sayfa:** tarayıcıda `https://kampus.gazisiber.org` aç
   **veya yerel kopya:** Linux `./baslat.sh` · macOS `baslat.command` ·
   Windows `baslat.bat`
2. Tarayıcı penceresini **tam ekran** yap (`F11`)
3. Kumandayı USB'ye tak → **"Seri Porttan Bağlan"** (Chrome/Edge)

> Firefox kullanıyorsan köprü gerekir: `./baslat.sh seri`
> (Windows: `baslat.bat seri`, macOS: `baslat.command seri`)
> → sonra tarayıcıda **"WebSocket ile Bağlan"**.
> Yayınlanmış sayfada yalnız köprü için `kopru-seri` yeterlidir.
> İlk çalıştırma bağımlılık indirir; **standdan önce bir kez yapın.**

## Bağlantı seçimi

| Tarayıcı | Kumanda | Yapılacak |
|---|---|---|
| Chrome / Edge | USB | "Seri Porttan Bağlan" |
| Chrome / Edge | Bluetooth | "Bluetooth ile Bağlan" |
| Firefox 151+ | USB | Site eklentisini kur + "Seri Porttan Bağlan" |
| Firefox / Safari | USB | `baslat.sh seri` + "WebSocket ile Bağlan" |
| Firefox / Safari | Bluetooth | `baslat.sh bt` + "WebSocket ile Bağlan" |

**Mac:** Chrome/Edge kur → Bluetooth ile bağlan (sürücü gerekmez) veya USB
için CP210x sürücüsünü kur. Safari doğrudan bağlanamaz.

**Chrome/Edge "yerel ağa erişim" izni sorarsa: İzin ver.**
(Reddedildiyse: adres çubuğu > site izinleri > Yerel ağ = İzin ver.)

## Uçuş

- Kartı **öne eğ** → tırman, **sağa yat** → sağa dön.
- **Buton** → kamera değiştir (takip ↔ kokpit).
- **C** → sıfırla (kart düzken bas).
- Sağ üst **Ayarlar (H)**: araç seçimi, hız, konum ışınlanma, katmanlar.

## Sensör çalışmazsa (30 saniyede çözüm)

1. `H` ile Ayarlar'ı aç.
2. **Klavye simülasyonu**'nu işaretle.
3. **Ok tuşlarıyla** uç. Sorun düzelince kapat.

Diğer denemeler: USB kabloyu başka porta tak → "Seri Porttan Bağlan"a
yeniden bas. Hiç olmazsa: sayfayı yenile (`F5`) ve tekrar bağlan.

## Sık karşılaşılanlar

| Durum | Ne yap |
|---|---|
| Sayfa boş / açılmadı | Başlatıcı penceresindeki adresi tarayıcıya yaz (ör. `http://localhost:8001`) |
| "WebSocket bağlantısı kurulamadı" | Köprü penceresi açık mı? Değilse `baslat.sh seri` / `baslat.bat seri` |
| "8765 portu kullanımda" | Eski köprü açık; penceresinde **Ctrl+C**, sonra tekrar başlat |
| Kumanda tepki vermiyor | Kabloyu kontrol et; ESP32'yi USB'den çıkar-tak; `C` ile sıfırla |
| USB portu yok (Mac) | CP210x sürücüsünü kur veya Bluetooth ile bağlan |
| Bilgisayar ısındı / kastı | Ayarlar > Katmanlar: arka plan, ağaç, uzak bölgeleri kapat |
| Her şey karıştı | Sayfayı yenile (`F5`); köprüyü Ctrl+C ile kapatıp yeniden başlat |

## Kapatma

- Köprü/sunucu penceresinde **Ctrl+C** (Windows'ta pencereyi kapat).
- Kumandayı kullanmayacaksan butona **1.5 sn** bas: BLE kapanır (pil tasarrufu).

## Acil iletişim

Ad: ____________________  Tel: ____________________
