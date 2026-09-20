#!/usr/bin/env python3
"""
ESP32 Bluetooth LE (Nordic UART) -> WebSocket köprüsü.

Firefox/Safari Web Bluetooth desteklemediği için bu köprü BLE verisini
mevcut WebSocket kanalına basar; tarayıcıda "WebSocket ile Bağlan" yeterlidir.

Kurulum (bir kez, iki yöntem):
    a) python3 -m venv .venv && .venv/bin/pip install -r kopruler/requirements.txt
       Windows: py -3 -m venv .venv && .venv\\Scripts\\pip install -r kopruler\\requirements.txt
    b) (venv yoksa) python3 -m pip install --target=libs bleak websockets

Çalıştırma (kolay yol: depo kökündeki baslat.sh / baslat.bat "bt" seçeneği):
    .venv/bin/python kopruler/bt_kopru.py                     # cihaz adı: GAZI-UCAK
    PYTHONPATH=libs python3 kopruler/bt_kopru.py              # yöntem b
    PYTHONPATH=libs python3 kopruler/bt_kopru.py GAZI-UCAK    # ad değiştirilebilir

Notlar:
- Cihaz kapanıp açılırsa köprü otomatik yeniden bağlanır.
- Linux'ta BLE izni için: 'sudo usermod -aG bluetooth $USER' + yeniden giriş.
- Windows 10/11'de Bluetooth açık olmalı; ek sürücü gerekmez.
- Aynı anda hem USB seri hem BLE kullanılabilir; bu köprü yalnız BLE içindir.
"""

import asyncio
import sys

from bleak import BleakScanner
from bleak import BleakClient
import websockets

NUS_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # notify (cihazdan veri)
CIHAZ_ADI = sys.argv[1] if len(sys.argv) > 1 else "GAZI-UCAK"
WS_ADRES = "localhost"
WS_PORT = 8765

baglilar = set()


async def ws_kayit(ws):
    baglilar.add(ws)
    print(f"Tarayıcı bağlandı ({len(baglilar)} istemci)")
    try:
        await ws.wait_closed()
    finally:
        baglilar.discard(ws)
        print("Tarayıcı ayrıldı")


async def yayla(mesaj):
    if baglilar:
        await asyncio.gather(*(ws.send(mesaj) for ws in baglilar),
                             return_exceptions=True)


async def cihaz_bul():
    print(f"BLE cihazı aranıyor: {CIHAZ_ADI} ...")
    try:
        cihaz = await BleakScanner.find_device_by_name(CIHAZ_ADI, timeout=15)
    except AttributeError:   # eski bleak sürümleri
        cihazlar = await BleakScanner.discover(timeout=15)
        cihaz = next((c for c in cihazlar if (c.name or "") == CIHAZ_ADI), None)
    if cihaz is None:
        sys.exit("Cihaz bulunamadı. ESP32 açık mı? (Uzun basış BLE'yi kapatmış olabilir.)")
    return cihaz


async def main():
    cihaz = await cihaz_bul()
    dongu = asyncio.get_running_loop()

    def veri_geldi(_, veri):
        metin = veri.decode("utf-8", errors="ignore")
        dongu.create_task(yayla(metin))

    print(f"WebSocket sunucusu: ws://{WS_ADRES}:{WS_PORT}")
    async with websockets.serve(ws_kayit, WS_ADRES, WS_PORT):
        while True:
            try:
                async with BleakClient(cihaz) as istemci:
                    await istemci.start_notify(NUS_TX_UUID, veri_geldi)
                    print(f"BLE bağlandı: {cihaz.name or cihaz.address}")
                    while istemci.is_connected:
                        await asyncio.sleep(1)
                    print("BLE bağlantısı koptu; yeniden deneniyor…")
            except Exception as e:
                print(f"BLE hatası: {e} — 3 sn sonra yeniden denenecek")
            await asyncio.sleep(3)
            try:
                cihaz = await cihaz_bul()
            except SystemExit:
                print("Cihaz hâlâ bulunamıyor; 5 sn sonra tekrar…")
                await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
