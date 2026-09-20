#!/usr/bin/env python3
"""
ESP32 seri port -> WebSocket köprüsü (Firefox/Safari ve Windows desteği için).

Kurulum (bir kez, iki yöntem):
    a) python3 -m venv .venv && .venv/bin/pip install -r kopruler/requirements.txt
       Windows: py -3 -m venv .venv && .venv\\Scripts\\pip install -r kopruler\\requirements.txt
    b) (venv yoksa) python3 -m pip install --target=libs pyserial websockets

Çalıştırma (kolay yol: depo kökündeki baslat.sh / baslat.bat "seri" seçeneği):
    .venv/bin/python kopruler/seri_kopru.py            # port otomatik bulunur
    PYTHONPATH=libs python3 kopruler/seri_kopru.py     # yöntem b
    .../python kopruler/seri_kopru.py /dev/ttyUSB1     # Linux'ta özel port
    ...\\python kopruler\\seri_kopru.py COM3             # Windows'ta özel port

Port otomatik bulma:
    Linux : /dev/ttyUSB* veya /dev/ttyACM* (ilk bulunan)
    Windows: COM* (açıklamasında USB geçen ilk port tercih edilir)
    macOS : /dev/cu.usbserial*, /dev/cu.usbmodem* … (tty.* yerine cu.* tercih)
Cihaz çıkarılırsa köprü 3 sn arayla yeniden bağlanmayı dener; tarayıcı
"WebSocket ile Bağlan" düğmesiyle ws://localhost:8765'e bağlanır.
"""

import asyncio
import glob
import sys

import serial
import serial.tools.list_ports
import websockets

BAUD = 115200
WS_ADRES = "localhost"
WS_PORT = 8765

# macOS'ta "cu.*" (callout) aygıtları tercih edilir: tty.* açılışta DCD sinyali
# bekleyip kilitlenebilir. Sıra önemlidir (ilk bulunan kullanılır).
MAC_PORT_DESENLERI = (
    "/dev/cu.usbserial*",
    "/dev/cu.usbmodem*",
    "/dev/cu.SLAB_USBtoUART*",
    "/dev/cu.wchusbserial*",
    "/dev/tty.usbserial*",
    "/dev/tty.usbmodem*",
)
LINUX_PORT_DESENLERI = ("/dev/ttyUSB*", "/dev/ttyACM*")

baglilar = set()


def port_bul():
    """Uygun seri portu bul (Linux/macOS /dev/*, Windows COM*); yoksa None."""
    if sys.platform.startswith("win"):
        adaylar = list(serial.tools.list_ports.comports())
        if not adaylar:
            return None
        # Açıklamasında USB geçenleri öne al (dahili COM1'i atlamak için)
        adaylar.sort(key=lambda p: "usb" not in (p.description or "").lower())
        return adaylar[0].device
    desenler = MAC_PORT_DESENLERI if sys.platform == "darwin" else LINUX_PORT_DESENLERI
    for desen in desenler:
        bulunanlar = sorted(glob.glob(desen))
        if bulunanlar:
            return bulunanlar[0]
    return None


SERI_PORT = sys.argv[1] if len(sys.argv) > 1 else None


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


async def seri_dongusu():
    """Portu aç, oku; kopunca kapatıp yeniden bağlanmayı dene."""
    döngü = asyncio.get_running_loop()
    while True:
        port = SERI_PORT or port_bul()
        if port is None:
            print("Seri port bulunamadı; 3 sn sonra yeniden bakılacak… "
                  "(ESP32 USB ile bağlı mı? Linux'ta 'dialout' grubu, "
                  "Windows/macOS'ta CP210x/CH340 sürücüsü gerekli olabilir.)")
            await asyncio.sleep(3)
            continue
        try:
            await döngü.run_in_executor(None, seri_oku, port, döngü)
        except serial.SerialException as e:
            print(f"Seri port hatası: {e}")
        except Exception as e:                      # sürpriz hatalarda da ayakta kal
            print(f"Seri okuma hatası: {e}")
        print("Seri port kapandı; 3 sn sonra yeniden denenecek…")
        await asyncio.sleep(3)


def seri_oku(port, döngü):
    """Bloklayan seri okuma; executor thread'inde çalışır. Port koparsa döner."""
    with serial.Serial(port, BAUD, timeout=1) as ser:
        print(f"Seri port açık: {port} @ {BAUD}")
        while True:
            try:
                satir = ser.readline().decode("utf-8", errors="ignore").strip()
            except (serial.SerialException, OSError):
                return                                   # üst döngü yeniden bağlanır
            if satir:
                asyncio.run_coroutine_threadsafe(yayla(satir + "\n"), döngü)


async def main():
    print(f"WebSocket sunucusu: ws://{WS_ADRES}:{WS_PORT}")
    print("Tarayıcıda 'WebSocket ile Bağlan' düğmesine basın.")
    async with websockets.serve(ws_kayit, WS_ADRES, WS_PORT):
        await seri_dongusu()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nKöprü kapatıldı.")
