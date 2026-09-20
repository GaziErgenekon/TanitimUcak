#!/usr/bin/env python3
"""
GAZİ Kampüs Uçuş Simülatörü — tek tık başlatıcı.

Kullanım:
    python3 baslat.py                      # menülü (çift tık / terminal)
    python3 baslat.py sunucu               # yalnız web sunucusu + tarayıcı
    python3 baslat.py seri [PORT]          # sunucu + seri köprü (Firefox/Safari)
    python3 baslat.py bt [AD]              # sunucu + Bluetooth köprü
    python3 baslat.py kopru-seri [PORT]    # YALNIZ seri köprü (hosted sayfa için)
    python3 baslat.py kopru-bt [AD]        # YALNIZ Bluetooth köprü (hosted için)

Ne yapar?
- Sunucu modlarında boş bir portta (8000'den başlayarak) yerel web sunucusu
  açar; varsayılan tarayıcıyı http://localhost:<port> ile açar. İnternet gerekmez.
- `kopru-*` modları yalnız köprüyü çalıştırır: sayfa campus.gazisiber.org gibi
  bir HTTPS adresten açılırken kullanılır (sunucu/tarayıcı açılmaz).
- Köprü modlarında .venv yoksa oluşturur ve kopruler/requirements.txt
  bağımlılıklarını kurar (yalnız ilk kurulumda internet gerekir).
- Köprüyü .venv içindeki Python ile çalıştırır; Ctrl+C ile her şey kapanır.

Kolay yol: depo kökündeki baslat.sh (Linux) / baslat.command (macOS) /
baslat.bat (Windows).
"""

import argparse
import functools
import hashlib
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import venv
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

KOK = os.path.dirname(os.path.abspath(__file__))
KOPRU_DIZIN = os.path.join(KOK, "kopruler")
GEREKSINIM = os.path.join(KOPRU_DIZIN, "requirements.txt")
LIBS_DIZIN = os.path.join(KOK, "libs")
PORT_ARALIK = range(8000, 8011)

KOPRULER = {
    "seri": ("seri_kopru.py", "seri_kopru.py [PORT]",
             "Seri köprü (USB) — Firefox/Safari ve Windows/macOS portları için"),
    "bt": ("bt_kopru.py", "bt_kopru.py [CIHAZ_ADI]",
           "Bluetooth köprü (BLE) — Firefox/Safari için"),
}
# Sunucusuz (hosted sayfa) karşılıkları: python3 baslat.py kopru-seri
YALNIZ_KOPRU = {"kopru-seri": "seri", "kopru-bt": "bt"}


class SessizHandler(SimpleHTTPRequestHandler):
    """Dosya sunucusu; her isteği loglamayız (stand çıktısı temiz kalsın)."""

    def log_message(self, *args):
        pass


def sunucu_baslat():
    """Boş portta yerel web sunucusu başlat (daemon thread). Portu döndürür."""
    handler = functools.partial(SessizHandler, directory=KOK)
    for port in PORT_ARALIK:
        if port_dolu(port):
            continue
        try:                       # gerçek bind denemesi (TIME_WAIT engel değil)
            httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
        except OSError:
            continue
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        return port
    return None


def tarayici_ac(port):
    time.sleep(0.4)                      # sunucu istekleri karşılamaya başlasın
    webbrowser.open(f"http://localhost:{port}")


def venv_python():
    """Sağlam .venv içindeki Python'u döndür (pip yoksa yarım venv sayılır)."""
    adaylar = [
        (os.path.join(KOK, ".venv", "Scripts", "python.exe"),  # Windows
         os.path.join(KOK, ".venv", "Scripts", "pip.exe")),
        (os.path.join(KOK, ".venv", "bin", "python"),          # Linux/macOS
         os.path.join(KOK, ".venv", "bin", "pip")),
    ]
    for python, pip in adaylar:
        if os.path.exists(python) and os.path.exists(pip):
            return python
    return None


def gereksinim_ozeti():
    """requirements.txt içeriğinin kısa özeti (kurulum damgası için)."""
    with open(GEREKSINIM, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def pip_kur(python, hedef=None):
    """Bağımlılıkları kur (gerekmiyorsa hiç internete çıkmadan döner)."""
    marker = os.path.join(hedef or os.path.join(KOK, ".venv"), ".gazi-bagimlilik")
    ozet = gereksinim_ozeti()
    try:                                   # daha önce kurulduysa ağ gerekmez
        with open(marker, encoding="ascii") as f:
            if f.read().strip() == ozet:
                return True
    except OSError:
        pass
    print("Bağımlılıklar kuruluyor… (bu adım internet gerektirir)")
    komut = [python, "-m", "pip", "install", "-q", "--upgrade"]
    if hedef:
        komut += ["--target", hedef]
    komut += ["-r", GEREKSINIM]
    if subprocess.run(komut).returncode != 0:
        return False
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="ascii") as f:
            f.write(ozet)
    except OSError:
        pass
    return True


def venv_hazirla():
    """Gerekirse .venv (olamazsa libs/) kur. (python_yolu, ortam) döndürür."""
    if not os.path.exists(GEREKSINIM):
        sys.exit(f"HATA: {GEREKSINIM} bulunamadı; depo eksik indirilmiş olabilir.")

    python = venv_python()
    if python is None:
        print("Sanal ortam (.venv) oluşturuluyor… (ilk kurulum, bir kez)")
        try:
            venv.EnvBuilder(with_pip=True).create(os.path.join(KOK, ".venv"))
            python = venv_python()
        except (Exception, SystemExit) as e:
            print(f".venv oluşturulamadı ({e}).")
            print("Linux'ta kalıcı çözüm: sudo apt install python3-venv")
            print("Şimdilik 'libs/' klasörüne kurulacak (alternatif yöntem).")
            shutil.rmtree(os.path.join(KOK, ".venv"), ignore_errors=True)
            python = None
        if python is None:
            if not pip_kur(sys.executable, hedef=LIBS_DIZIN):
                sys.exit("HATA: Bağımlılıklar kurulamadı. İnternet bağlantısını kontrol edin.")
            ortam = os.environ.copy()
            ortam["PYTHONPATH"] = LIBS_DIZIN + os.pathsep + ortam.get("PYTHONPATH", "")
            return sys.executable, ortam

    if not pip_kur(python):
        sys.exit("HATA: Bağımlılıklar kurulamadı. İnternet bağlantısını kontrol edin.")
    return python, os.environ.copy()


def port_dolu(port):
    """Portta dinleyen biri var mı? (TIME_WAIT'i dolu saymaz)"""
    for adres, aile in (("127.0.0.1", socket.AF_INET), ("::1", socket.AF_INET6)):
        with socket.socket(aile) as s:
            s.settimeout(0.3)
            try:
                s.connect((adres, port))
                return True
            except OSError:
                continue
    return False


def kopru_calistir(mod, ek_args, sunucu_var=True):
    dosya, kullanim, aciklama = KOPRULER[mod]
    if port_dolu(8765):
        sys.exit("HATA: 8765 portu kullanımda. Başka bir köprü çalışıyor olabilir;\n"
                 "önce onu kapatın (köprü penceresinde Ctrl+C) ve tekrar deneyin.")
    python, ortam = venv_hazirla()
    print(f"\n{aciklama}")
    print(f"Köprü başlıyor: {kullanim}  (durdurmak için Ctrl+C)")
    if not sunucu_var:
        print("Tarayıcıda campus.gazisiber.org adresini açın ve "
              "\"WebSocket ile Bağlan\" düğmesine basın.\n")
    else:
        print()
    cocuk = subprocess.Popen([python, "-u", os.path.join(KOPRU_DIZIN, dosya), *ek_args],
                             env=ortam)
    onceki = signal.getsignal(signal.SIGTERM)
    # Köprü, launcher'a gelen kapatma sinyalini de alsın (yetim kalmasın)
    signal.signal(signal.SIGTERM, lambda *_: cocuk.terminate())
    try:
        cocuk.wait()
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGTERM, onceki)
        if cocuk.poll() is None:
            cocuk.terminate()
            try:
                cocuk.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cocuk.kill()


def menu():
    print("=" * 60)
    print("  GAZİ Kampüs Uçuş Simülatörü — başlatıcı")
    print("=" * 60)
    print("  Yerel kopya (bu bilgisayardaki dosyalarla):")
    print("    1) Sunucu + tarayıcı        (Chrome/Edge, USB — önerilen)")
    print("    2) Sunucu + seri köprü      (Firefox/Safari, USB)")
    print("    3) Sunucu + Bluetooth köprü (Firefox/Safari, BLE)")
    print("  Hosted sayfa (campus.gazisiber.org) için yalnız köprü:")
    print("    4) Seri köprü               (USB)")
    print("    5) Bluetooth köprü          (BLE)")
    print("    0) Çıkış")
    secim = input("Seçim [1]: ").strip() or "1"
    return {"1": "sunucu", "2": "seri", "3": "bt",
            "4": "kopru-seri", "5": "kopru-bt", "0": None}.get(secim)


def main():
    ap = argparse.ArgumentParser(description="GAZİ Kampüs Uçuş Simülatörü başlatıcı")
    ap.add_argument("mod", nargs="?",
                    choices=["sunucu", "seri", "bt", "kopru-seri", "kopru-bt"],
                    help="çalışma modu (verilmezse menü)")
    ap.add_argument("ek", nargs=argparse.REMAINDER,
                    help="köprüye iletilecek ek argümanlar (ör. COM3)")
    args = ap.parse_args()

    mod = args.mod
    if mod is None:
        if sys.stdin.isatty():
            mod = menu()
            if mod is None:
                return
        else:
            mod = "sunucu"                  # çift tık / boru hattı: güvenli varsayılan

    if mod in YALNIZ_KOPRU:                  # hosted sayfa: sunucu/tarayıcı yok
        kopru_calistir(YALNIZ_KOPRU[mod], args.ek, sunucu_var=False)
        return

    port = sunucu_baslat()
    if port is None:
        sys.exit("HATA: 8000-8010 portlarının tümü dolu. Diğer kopyaları kapatın.")
    print(f"Web sunucusu: http://localhost:{port}")
    threading.Thread(target=tarayici_ac, args=(port,), daemon=True).start()

    if mod in KOPRULER:
        kopru_calistir(mod, args.ek)
    else:
        print("Tarayıcıda 'Seri Porttan Bağlan' düğmesini kullanın. "
              "(Firefox için: ./baslat.sh seri)")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    print("\nSunucu kapatıldı.")


if __name__ == "__main__":
    for akis in (sys.stdout, sys.stderr):        # çıktı yönlendirilse de görünsün
        try:
            akis.reconfigure(line_buffering=True)
        except Exception:
            pass
    try:
        main()
    except KeyboardInterrupt:
        print("\nKapatıldı.")
