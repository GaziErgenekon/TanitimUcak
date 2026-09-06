#!/usr/bin/env python3
"""
ESP32 seri port -> WebSocket köprüsü (Firefox/Safari desteği için).

Kurulum (bir kez, iki yöntem):
    a) python3 -m venv .venv && .venv/bin/pip install pyserial websockets
    b) (venv yoksa) python3 -m pip install --target=libs pyserial websockets

Çalıştırma:
    .venv/bin/python seri_kopru.py                 # yöntem a
    PYTHONPATH=libs python3 seri_kopru.py          # yöntem b
    (varsayılan port /dev/ttyUSB0, başka port: ".../python seri_kopru.py /dev/ttyUSB1")

Tarayıcıda "WebSocket ile Bağlan" düğmesi ws://localhost:8765'e bağlanır.
Seri satırlar (pitch,roll,butonState) olduğu gibi iletilir.
"""

import asyncio
import sys

import serial
import websockets

SERI_PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
BAUD = 115200
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

async def seri_dongusu():
    döngü = asyncio.get_running_loop()

    def oku():
        """Bloklayan seri okuma; executor thread'inde çalışır."""
        with serial.Serial(SERI_PORT, BAUD, timeout=1) as ser:
            print(f"Seri port açık: {SERI_PORT} @ {BAUD}")
            while True:
                satir = ser.readline().decode("utf-8", errors="ignore").strip()
                if satir:
                    yield_satir = satir + "\n"
                    asyncio.run_coroutine_threadsafe(yayla(yield_satir), döngü)

    await döngü.run_in_executor(None, oku)

async def yayla(mesaj):
    if baglilar:
        await asyncio.gather(*(ws.send(mesaj) for ws in baglilar),
                             return_exceptions=True)

async def main():
    print(f"WebSocket sunucusu: ws://{WS_ADRES}:{WS_PORT}")
    async with websockets.serve(ws_kayit, WS_ADRES, WS_PORT):
        await seri_dongusu()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except serial.SerialException as e:
        print(f"Seri port hatası: {e}")
        print("İpucu: 'ls /dev/ttyUSB* /dev/ttyACM*' ile doğru portu bulun, "
              "gerekirse 'sudo usermod -aG dialout $USER' ve yeniden giriş.")
