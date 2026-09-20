#!/usr/bin/env python3
"""
Yayın paketi üretici — campus.gazisiber.org gibi statik sunucular için.

Simülatörün çalışması için gereken dosyaları tek klasörde toplar:
    python3 araçlar/yayin_paketi.py            # yayin/ klasörü
    python3 araçlar/yayin_paketi.py --zip      # yayin/ + yayin.zip
    python3 araçlar/yayin_paketi.py --hedef /tmp/campus --zip /tmp/campus.zip

Paket içeriği: index.html, veri dosyaları, vendor/three, PWA dosyaları
(manifest + sw.js + ikonlar). Python/köprü/ESP32/test dosyaları PAKETE GİRMEZ
(sunucuda çalışmaz; köprü her ziyaretçinin kendi bilgisayarında çalışır).
Sunucu tarafı başlık/MIME örnekleri için README > Yayın bölümüne bakın.
"""

import argparse
import os
import shutil
import sys
import zipfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOSYALAR = [
    "index.html",
    "binalar.js",
    "cevre.js",
    "bolgeler.js",
    "manifest.webmanifest",
    "sw.js",
    "ikon-192.png",
    "ikon-512.png",
    "ikon-512-maskable.png",
]
KLASORLER = ["vendor"]


def boyut_yolu(yol):
    """İnsan okur boyut (KB)."""
    toplam = 0
    if os.path.isfile(yol):
        return os.path.getsize(yol)
    for kok, _, dosyalar in os.walk(yol):
        for d in dosyalar:
            toplam += os.path.getsize(os.path.join(kok, d))
    return toplam


def main():
    ap = argparse.ArgumentParser(description="Statik yayın paketi üret")
    ap.add_argument("--hedef", default=os.path.join(KOK, "yayin"),
                    help="paket klasörü (varsayılan: yayin/)")
    ap.add_argument("--zip", nargs="?", const=os.path.join(KOK, "yayin.zip"),
                    default=None, metavar="DOSYA",
                    help="ayrıca zip üret (varsayılan ad: yayin.zip)")
    args = ap.parse_args()

    eksik = [d for d in DOSYALAR if not os.path.isfile(os.path.join(KOK, d))]
    eksik += [k for k in KLASORLER if not os.path.isdir(os.path.join(KOK, k))]
    if eksik:
        sys.exit("HATA: eksik dosya/klasör: " + ", ".join(eksik) +
                 "\nDepo eksik indirilmiş olabilir.")

    if os.path.exists(args.hedef):
        shutil.rmtree(args.hedef)
    os.makedirs(args.hedef)
    for dosya in DOSYALAR:
        shutil.copy2(os.path.join(KOK, dosya), os.path.join(args.hedef, dosya))
    for klasor in KLASORLER:
        shutil.copytree(os.path.join(KOK, klasor),
                        os.path.join(args.hedef, klasor))

    print(f"Yayın paketi hazır: {args.hedef}")
    for dosya in DOSYALAR:
        print(f"  {dosya:28s} {boyut_yolu(os.path.join(args.hedef, dosya)) / 1024:8.1f} KB")
    for klasor in KLASORLER:
        print(f"  {klasor + '/':28s} "
              f"{boyut_yolu(os.path.join(args.hedef, klasor)) / 1024:8.1f} KB")

    if args.zip:
        with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as z:
            for kok, _, dosyalar in os.walk(args.hedef):
                for d in sorted(dosyalar):
                    tam = os.path.join(kok, d)
                    z.write(tam, os.path.relpath(tam, args.hedef))
        print(f"Zip: {args.zip} ({os.path.getsize(args.zip) / 1024:.1f} KB)")

    print("\nSunucuya bu klasörün içeriğini kopyalayın; "
          "başlık/MIME örnekleri README > Yayın.")


if __name__ == "__main__":
    main()
