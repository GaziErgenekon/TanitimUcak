#!/usr/bin/env python3
"""
Gazi Üniversitesi kampüs bina verisini OpenStreetMap'ten çekip binalar.js üretir.

Kullanım:
    python3 araçlar/kampus_verisi.py

Çıktı: proje kökünde binalar.js
- ONEMLI_BINALAR : isimli üniversite binaları (elle düzenlenebilir liste)
- ARKA_PLAN_BINALAR : isimsiz/apartmanlar (kompakt format)

Koordinat sistemi: kampüs merkezi (0,0). x = doğu (+), z = güney (+), birim metre.
"""

import json
import math
import sys
import urllib.request
import urllib.parse

# --- Ayarlar -----------------------------------------------------------------
MERKEZ_LAT = 39.9435
MERKEZ_LON = 32.8205
YARICAP_M = 900                     # kampüs merkezi etrafında tarama yarıçapı
ONEMLI_BINA_LIMITI = 40             # en fazla bu kadar isimli bina "önemli" olur
OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

# Varsayılan cephe renkleri (önemli binalara sırayla atanır; elle değiştirilebilir)
PALET = [0xd8c9a8, 0xcfc4b0, 0xb8a98c, 0xc9bdbd, 0xb5c2c9,
         0xd0b49a, 0xc2b6a3, 0xadb8c4, 0xcabfb2, 0xb0a896]

# --- Overpass'tan ham veri çekme ---------------------------------------------
def osm_cek():
    sorgu = (
        "[out:json][timeout:60];"
        f"(way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})[\"building\"];);"
        "out body;>;out skel qt;"
    )
    url = OVERPASS_URL + "?data=" + urllib.parse.quote(sorgu)
    print("Overpass sorgusu gönderiliyor...")
    with urllib.request.urlopen(url, timeout=180) as yanit:
        veri = json.loads(yanit.read().decode("utf-8"))
    print(f"  {len(veri.get('elements', []))} OSM elemanı alındı")
    return veri

# --- Koordinat dönüşümü (lat/lon -> yerel metre) ------------------------------
class Donusturucu:
    def __init__(self, lat0, lon0):
        self.lat0 = lat0
        self.lon0 = lon0
        self.coslat = math.cos(math.radians(lat0))

    def xy(self, lat, lon):
        x = (lon - self.lon0) * 111320.0 * self.coslat
        z = -(lat - self.lat0) * 111320.0     # güney pozitif
        return (round(x, 1), round(z, 1))

# --- Ramer-Douglas-Peucker poligon sadeleştirme --------------------------------
def rdp(noktalar, tolerans):
    if len(noktalar) < 3:
        return noktalar

    def _en_uzak(idx_bas, idx_son):
        (x1, y1), (x2, y2) = noktalar[idx_bas], noktalar[idx_son]
        en_uzak_mesafe, en_uzak_idx = 0.0, idx_bas
        for i in range(idx_bas + 1, idx_son):
            x0, y0 = noktalar[i]
            dx, dy = x2 - x1, y2 - y1
            uzunluk2 = dx * dx + dy * dy
            if uzunluk2 == 0:
                d = math.hypot(x0 - x1, y0 - y1)
            else:
                t = ((x0 - x1) * dx + (y0 - y1) * dy) / uzunluk2
                t = max(0.0, min(1.0, t))
                d = math.hypot(x0 - (x1 + t * dx), y0 - (y1 + t * dy))
            if d > en_uzak_mesafe:
                en_uzak_mesafe, en_uzak_idx = d, i
        return en_uzak_mesafe, en_uzak_idx

    tut = set()
    # Kapalı poligon gibi davran: başlangıç = bitiş köşesi olarak ilk noktayı kullan
    yigin = [(0, len(noktalar) - 1)]
    while yigin:
        bas, son = yigin.pop()
        mesafe, idx = _en_uzak(bas, son)
        if mesafe > tolerans and idx not in (bas, son):
            tut.add(idx)
            yigin.append((bas, idx))
            yigin.append((idx, son))
    return [noktalar[i] for i in sorted(tut | {0, len(noktalar) - 1})]

def poligon_alani(poligon):
    alan = 0.0
    n = len(poligon)
    for i in range(n):
        x1, y1 = poligon[i]
        x2, y2 = poligon[(i + 1) % n]
        alan += x1 * y2 - x2 * y1
    return abs(alan) / 2.0

def yukseklik_tahmin(poligon):
    """Taban alanından 2-8 kat (6-24 m) deterministik yükseklik tahmini."""
    alan = poligon_alani(poligon)
    kat = max(2, min(8, round(math.sqrt(alan) / 6.0)))
    return kat * 3, kat

# --- Ana işlem -----------------------------------------------------------------
def main():
    veri = osm_cek()
    donustur = Donusturucu(MERKEZ_LAT, MERKEZ_LON)

    dugumler = {e["id"]: (e["lat"], e["lon"]) for e in veri["elements"] if e["type"] == "node"}
    yollar = [e for e in veri["elements"] if e["type"] == "way"]

    onemli, arka_plan = [], []
    gorulen_isimler = set()

    for yol in yollar:
        coords = []
        for nid in yol.get("nodes", []):
            if nid in dugumler:
                coords.append(donustur.xy(*dugumler[nid]))
        if len(coords) < 4:
            continue
        # kapanan son noktayı at (OSM kapalı poligon)
        if coords[0] == coords[-1]:
            coords = coords[:-1]
        if len(coords) < 3:
            continue

        tags = yol.get("tags", {})
        isim = tags.get("name")
        bina_tipi = tags.get("building", "yes")
        universite_mi = bina_tipi == "university" or tags.get("amenity") in (
            "library", "university")

        tolerans = 0.5 if (isim and universite_mi) else 1.0
        poligon = rdp(coords, tolerans)
        if len(poligon) < 3:
            continue
        yukseklik, kat = yukseklik_tahmin(poligon)

        if isim and universite_mi and isim not in gorulen_isimler:
            gorulen_isimler.add(isim)
            onemli.append({"isim": isim, "taban": poligon,
                           "yukseklik": yukseklik, "kat": kat})
        elif isim and isim not in gorulen_isimler and bina_tipi not in ("residential",):
            # İsimli ama üniversite olmayan (cami, istasyon vb.) da önemli olabilir
            gorulen_isimler.add(isim)
            onemli.append({"isim": isim, "taban": poligon,
                           "yukseklik": yukseklik, "kat": kat})
        else:
            duz = []
            for (x, z) in poligon:
                duz.extend([x, z])
            arka_plan.append([duz, yukseklik])

    # Önemli binaları alan büyüklüğüne göre sıralayıp limitle
    onemli.sort(key=lambda b: -poligon_alani(b["taban"]))
    onemli = onemli[:ONEMLI_BINA_LIMITI]

    # Rektörlük OSM'de yoksa elle düzenlenecek yer tutucu ekle
    if not any("Rektörlük" in b["isim"] for b in onemli):
        onemli.insert(0, {
            "isim": "Rektörlük (YER TUTUCU - düzenleme moduyla konumu bul)",
            "taban": [[-20, -12], [20, -12], [20, 12], [-20, 12]],
            "yukseklik": 21, "kat": 7})

    satirlar = []
    satirlar.append("// ** BU DOSYA araçlar/kampus_verisi.py ILE OTOMATIK URETILMISTIR **")
    satirlar.append("// ONEMLI_BINALAR listesini ELLE DUZENLEMEK icin serbestsiniz:")
    satirlar.append("// taban noktalarini, yukseklik ve renk degerlerini degistirip tarayicida F5 yapin.")
    satirlar.append("// Koordinat sistemi: kampus merkezi (0,0). x = dogu (+), z = guney (+), birim: metre.")
    satirlar.append("")
    satirlar.append("// ===== ONEMLI BINALAR (elle duzenle) =====")
    satirlar.append("const ONEMLI_BINALAR = [")
    for i, b in enumerate(onemli):
        renk = PALET[i % len(PALET)]
        taban_js = json.dumps([[x, z] for (x, z) in b["taban"]])
        satirlar.append("  {")
        satirlar.append(f"    isim: {json.dumps(b['isim'], ensure_ascii=False)},")
        satirlar.append(f"    taban: {taban_js},")
        satirlar.append(f"    yukseklik: {b['yukseklik']},")
        satirlar.append(f"    renk: 0x{renk:06x},")
        satirlar.append("    catRengi: 0x6e6e6e,")
        satirlar.append(f"    detay: {{ katsayisi: {b['kat']} }}")
        satirlar.append("  },")
    satirlar.append("];")
    satirlar.append("")
    satirlar.append("// ===== ARKA PLAN BINALARI (otomatik, kompakt format: [poligon, yukseklik]) =====")
    satirlar.append("const ARKA_PLAN_BINALAR = [")
    for duz, yukseklik in arka_plan:
        satirlar.append(f"  [{json.dumps(duz)}, {yukseklik}],")
    satirlar.append("];")
    satirlar.append("")

    with open("binalar.js", "w", encoding="utf-8") as dosya:
        dosya.write("\n".join(satirlar))

    import os
    boyut = os.path.getsize("binalar.js")
    print(f"binalar.js yazildi: {len(onemli)} onemli, {len(arka_plan)} arka plan binasi, "
          f"{boyut/1024:.0f} KB")

if __name__ == "__main__":
    main()
