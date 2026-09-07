#!/usr/bin/env python3
"""
Gazi Üniversitesi kampüs çevre verisini OpenStreetMap'ten çekip binalar.js üretir.

Kullanım:
    python3 araçlar/kampus_verisi.py          # OSM'den yeniden çek, binalar.js yaz

Çıktı: proje kökünde binalar.js
- ONEMLI_BINALAR   : isimli önemli binalar   (elle düzenlenebilir)
- ARKA_PLAN_BINALAR: isimsiz binalar         (kompakt)
- PARKLAR          : park/bahçe/çim alanları (elle düzenlenebilir)
- YOLLAR           : yollar (yaya/service/konut/ana) (elle düzenlenebilir)
- FISKIYELER       : fıskiye/havuz noktaları (elle düzenlenebilir)
- SPOR_ALANLARI    : futbol/tenis sahası, koşu pisti (elle düzenlenebilir)

Ham OSM verisi araçlar/osm_onbellek.json'a kaydedilir; ağ hatasında önbellekten
devam edilir. Koordinat sistemi: kampüs merkezi (0,0); x=doğu(+), z=güney(+), metre.
"""

import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

# --- Ayarlar -----------------------------------------------------------------
MERKEZ_LAT = 39.9435
MERKEZ_LON = 32.8205
YARICAP_M = 900
ONEMLI_BINA_LIMITI = 40
ONBELLEK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "osm_onbellek.json")

# Kullanıcının OSM linkinden doğrulanmış Rektörlük konumu (OSM'de isimli değil):
REKTORLUK_LAT, REKTORLUK_LON = 39.939483, 32.822092
# SABİT REKTÖRLÜK: OSM way 418594116 poligonu, merkezi kullanıcının işaretine
# (136,447) taşınmış hali. Otomatik seçim KAPALI — bu poligon korunur.
# Değiştirmek için bu listeyi düzenle.
SABIT_REKTORLUK_TABAN = [[154.2, 452.3], [157.1, 450.2], [160.1, 454.3], [151.5, 460.6], [153.4, 463.2], [162.0, 456.9], [165.6, 461.8], [152.6, 471.3], [147.1, 463.8], [144.5, 465.7], [150.1, 473.3], [136.3, 483.3], [127.7, 471.6], [139.6, 462.9], [132.6, 453.3], [125.3, 458.6], [121.6, 453.6], [128.9, 448.3], [121.9, 438.7], [110.0, 447.4], [101.4, 435.7], [115.2, 425.6], [120.8, 433.2], [123.4, 431.3], [117.8, 423.7], [130.8, 414.2], [134.4, 419.1], [125.8, 425.4], [127.7, 428.1], [136.4, 421.8], [139.4, 425.9], [136.4, 428.1]]
SABIT_REKTORLUK_YUKSEKLIK = 24  # 4 kat × 3 m × 2 ölçek
SABIT_REKTORLUK_KAT = 4

ENDPOINTLER = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

PALET = [0xd8c9a8, 0xcfc4b0, 0xb8a98c, 0xc9bdbd, 0xb5c2c9,
         0xd0b49a, 0xc2b6a3, 0xadb8c4, 0xcabfb2, 0xb0a896]

# Bölge tanımı çevresinden çekilecek katman sorguları
SORGULAR = {
    "binalar":  f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["building"];',
    "yollar":   f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["highway"~"^(footway|path|pedestrian|service|residential|secondary|trunk|trunk_link|primary)$"];',
    "spor":     f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["leisure"~"^(pitch|track|stadium)$"];',
    "parklar":  f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["leisure"~"^(park|garden)$"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["landuse"~"^(grass|meadow|recreation_ground)$"];',
    "fiskiyeler": f'node(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["man_made"="fountain"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["man_made"="fountain"];',
}

# --- Overpass istemcisi (dayanıklı) -------------------------------------------
def overpass_calistir(alt_sorgular):
    sorgu = "[out:json][timeout:45];(" + "".join(alt_sorgular) + ");out body;>;out skel qt;"
    son_hata = None
    for endpoint in ENDPOINTLER:
        for yontem in ("GET", "POST"):
            try:
                if yontem == "GET":
                    url = endpoint + "?data=" + urllib.parse.quote(sorgu)
                    istek = urllib.request.Request(
                        url, headers={"User-Agent": "TanitimUcak/1.0",
                                      "Accept": "application/json"})
                else:
                    veri = urllib.parse.urlencode({"data": sorgu}).encode()
                    istek = urllib.request.Request(
                        endpoint, data=veri, method="POST",
                        headers={"User-Agent": "TanitimUcak/1.0",
                                 "Accept": "application/json"})
                with urllib.request.urlopen(istek, timeout=180) as yanit:
                    return json.loads(yanit.read().decode("utf-8"))
            except Exception as e:
                son_hata = e
                print(f"  {endpoint} ({yontem}) başarısız: {e}")
                time.sleep(2)
    raise RuntimeError(f"Tüm Overpass uçları başarısız: {son_hata}")

def osm_verisi_edin():
    try:
        veri = overpass_calistir(SORGULAR.values())
        with open(ONBELLEK, "w", encoding="utf-8") as f:
            json.dump(veri, f)
        print(f"  {len(veri.get('elements', []))} OSM elemanı (önbelleğe yazıldı)")
        return veri
    except RuntimeError as e:
        print(f"  UYARI: {e}")
        if os.path.exists(ONBELLEK):
            print("  Önbellekten devam ediliyor:", ONBELLEK)
            with open(ONBELLEK, "r", encoding="utf-8") as f:
                return json.load(f)
        sys.exit("Önbellek de yok; internet varken tekrar deneyin.")

# --- Koordinat dönüşümü --------------------------------------------------------
class Donusturucu:
    def __init__(self, lat0, lon0):
        self.lat0, self.lon0 = lat0, lon0
        self.coslat = math.cos(math.radians(lat0))

    def xy(self, lat, lon):
        x = (lon - self.lon0) * 111320.0 * self.coslat
        z = -(lat - self.lat0) * 111320.0
        return (round(x, 1), round(z, 1))

# --- Ramer-Douglas-Peucker sadeleştirme ----------------------------------------
def rdp(noktalar, tolerans):
    if len(noktalar) < 3:
        return noktalar

    def _en_uzak(ib, is_):
        (x1, y1), (x2, y2) = noktalar[ib], noktalar[is_]
        en_d, en_i = 0.0, ib
        for i in range(ib + 1, is_):
            x0, y0 = noktalar[i]
            dx = x2 - x1
            dy = y2 - y1
            L2 = dx * dx + dy * dy
            d = math.hypot(x0 - x1, y0 - y1) if L2 == 0 else math.hypot(
                x0 - (x1 + max(0.0, min(1.0, ((x0 - x1) * dx + (y0 - y1) * dy) / L2)) * dx),
                y0 - (y1 + max(0.0, min(1.0, ((x0 - x1) * dx + (y0 - y1) * dy) / L2)) * dy))
            if d > en_d:
                en_d, en_i = d, i
        return en_d, en_i

    tut = set()
    yigin = [(0, len(noktalar) - 1)]
    while yigin:
        bas, son = yigin.pop()
        d, i = _en_uzak(bas, son)
        if d > tolerans and i not in (bas, son):
            tut.add(i)
            yigin.append((bas, i))
            yigin.append((i, son))
    return [noktalar[i] for i in sorted(tut | {0, len(noktalar) - 1})]

def poligon_alani(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1]
                   for i in range(len(p)))) / 2.0

def merkez(p):
    return (sum(x for x, _ in p) / len(p), sum(z for _, z in p) / len(p))

def yukseklik_tahmin(p):
    # Kullanıcı kararı: kat aralığı daraltıldı (2-3), görsel ölçek ×2 (kat*3m*2).
    # Rektörlük (4 kat) artık cüce kalmaz, kampüs silüeti heybetli durur.
    kat = max(2, min(3, round(math.sqrt(poligon_alani(p)) / 6.0)))
    return kat * 6, kat

# --- Ana işlem ------------------------------------------------------------------
def main():
    veri = osm_verisi_edin()
    d2 = Donusturucu(MERKEZ_LAT, MERKEZ_LON)
    dugumler = {e["id"]: (e["lat"], e["lon"]) for e in veri["elements"] if e["type"] == "node"}

    # Yol tipine göre şerit genişliği (m) ve render tipi
    YOL_GENISLIK = {"footway": 1.4, "path": 1.4, "pedestrian": 2.5, "service": 3.5,
                    "residential": 4.5, "secondary": 6.0, "trunk": 8.0,
                    "trunk_link": 5.0, "primary": 8.0}
    YOL_TIP = {"footway": "footway", "path": "path", "pedestrian": "pedestrian",
               "service": "service", "residential": "service",
               "secondary": "ana", "trunk": "ana", "trunk_link": "ana", "primary": "ana"}

    onemli, arka_plan, parklar, yollar, fiskiyeler, spor = [], [], [], [], [], []
    gorulen = set()

    for e in veri["elements"]:
        if e["type"] == "node":
            t = e.get("tags", {})
            if t.get("man_made") == "fountain":
                x, z = d2.xy(e["lat"], e["lon"])
                fiskiyeler.append({"isim": t.get("name", "Fıskiye"),
                                   "merkez": [x, z], "yaricap": 2})
            continue
        if e["type"] != "way":
            continue
        coords = [d2.xy(*dugumler[n]) for n in e.get("nodes", []) if n in dugumler]
        if len(coords) < 2:
            continue
        kapali = len(coords) >= 4 and coords[0] == coords[-1]
        if kapali:
            coords = coords[:-1]
        tags = e.get("tags", {})
        isim = tags.get("name")

        if "building" in tags:
            if e.get("id") == 418594116:
                continue  # hayalet: eski konumdaki Rektörlük kopyası
            if not kapali or len(coords) < 3:
                continue
            uni_mi = tags["building"] == "university" or tags.get("amenity") in ("library", "university")
            pol = rdp(coords, 0.5 if (isim and uni_mi) else 1.0)
            if len(pol) < 3:
                continue
            yuk, kat = yukseklik_tahmin(pol)
            if isim and isim not in gorulen and (uni_mi or tags["building"] not in ("residential",)):
                gorulen.add(isim)
                onemli.append({"isim": isim, "taban": pol, "yukseklik": yuk, "kat": kat})
            else:
                duz = []
                for x, z in pol:
                    duz.extend([x, z])
                arka_plan.append([duz, yuk, e.get("id")])

        elif tags.get("highway") in YOL_GENISLIK:
            pol = rdp(coords, 0.8)
            if len(pol) >= 2:
                duz = []
                for x, z in pol:
                    duz.extend([x, z])
                hw = tags.get("highway")
                yollar.append([duz, YOL_GENISLIK[hw], YOL_TIP[hw]])

        elif tags.get("leisure") in ("pitch", "track", "stadium"):
            if not kapali or len(coords) < 3:
                continue
            pol = rdp(coords, 1.0)
            if len(pol) < 3:
                continue
            spor.append({"isim": isim or {"pitch": "Saha", "track": "Koşu Pisti",
                                          "stadium": "Stadyum"}[tags.get("leisure")],
                         "spor": tags.get("sport", tags.get("leisure")),
                         "taban": pol})

        elif tags.get("leisure") in ("park", "garden") or \
                tags.get("landuse") in ("grass", "meadow", "recreation_ground"):
            if not kapali or len(coords) < 3:
                continue
            pol = rdp(coords, 1.0)
            if len(pol) < 3:
                continue
            tip = tags.get("leisure") or tags.get("landuse")
            parklar.append({"isim": isim, "taban": pol, "tip": tip})

        elif tags.get("man_made") == "fountain":
            if len(coords) >= 3:
                cx, cz = merkez(coords)
                xs = [c[0] for c in coords]
                zs = [c[1] for c in coords]
                r = max(1.5, min(6.0, (max(xs) - min(xs) + max(zs) - min(zs)) / 4))
                fiskiyeler.append({"isim": isim or "Fıskiye",
                                   "merkez": [round(cx, 1), round(cz, 1)],
                                   "yaricap": round(r, 1)})

    # --- Rektörlük: SABİT poligon (otomatik seçim kapalı, kullanıcı onaylı) ---
    def _nokta_icinde(x, z, pol):
        icinde = False
        n = len(pol)
        for i in range(n):
            x1, z1 = pol[i]
            x2, z2 = pol[(i + 1) % n]
            if ((z1 > z) != (z2 > z)) and (x < (x2 - x1) * (z - z1) / (z2 - z1) + x1):
                icinde = not icinde
        return icinde

    if not any("Rektörlük" in b["isim"] for b in onemli):
        # Sabit poligonla çakışan arka plan binalarını çıkar (çift çizim olmasın)
        once = len(arka_plan)
        sabit = [[float(v) for v in p] for p in SABIT_REKTORLUK_TABAN]
        tutulan = []
        for a in arka_plan:
            pol = [[a[0][i], a[0][i + 1]] for i in range(0, len(a[0]), 2)]
            cx = sum(p[0] for p in pol) / len(pol)
            cz = sum(p[1] for p in pol) / len(pol)
            if not _nokta_icinde(cx, cz, sabit):
                tutulan.append(a)
        arka_plan = tutulan
        onemli.insert(0, {"isim": "Rektörlük", "taban": SABIT_REKTORLUK_TABAN,
                          "yukseklik": SABIT_REKTORLUK_YUKSEKLIK,
                          "kat": SABIT_REKTORLUK_KAT})
        print(f"  Rektörlük: sabit poligon yerleştirildi "
              f"({len(SABIT_REKTORLUK_TABAN)} nokta, {once - len(arka_plan)} çakışan bina çıkarıldı)")

    onemli = sorted(onemli, key=lambda b: -poligon_alani(b["taban"]))[:ONEMLI_BINA_LIMITI]

    # --- binalar.js yaz ---
    s = []
    s.append("// ** BU DOSYA araclar/kampus_verisi.py ILE OTOMATIK URETILMISTIR **")
    s.append("// Listeleri ELLE DUZENLEMEK icin serbestsiniz; tarayicida F5 yeterli.")
    s.append("// Koordinat: kampus merkezi (0,0); x = dogu (+), z = guney (+), birim: metre.")
    s.append("")
    s.append("// ===== ONEMLI BINALAR (isimli, elle duzenle) =====")
    s.append("const ONEMLI_BINALAR = [")
    for i, b in enumerate(onemli):
        renk = PALET[i % len(PALET)]
        taban_js = json.dumps([[x, z] for x, z in b["taban"]])
        s.append("  {")
        s.append(f"    isim: {json.dumps(b['isim'], ensure_ascii=False)},")
        s.append(f"    taban: {taban_js},")
        s.append(f"    yukseklik: {b['yukseklik']},")
        s.append(f"    renk: 0x{renk:06x},")
        s.append("    catRengi: 0x6e6e6e,")
        s.append(f"    detay: {{ katsayisi: {b['kat']} }}")
        s.append("  },")
    s.append("];")
    s.append("")
    s.append("// ===== PARKLAR / YESIL ALANLAR (duz poligonlar, elle duzenle) =====")
    s.append("const PARKLAR = [")
    for p in sorted(parklar, key=lambda p: -poligon_alani(p["taban"])):
        taban_js = json.dumps([[x, z] for x, z in p["taban"]])
        s.append(f"  {{ isim: {json.dumps(p['isim'] or ('Park' if p['tip'] in ('park','garden') else 'Yesil alan'), ensure_ascii=False)}, "
                 f"tip: {json.dumps(p['tip'], ensure_ascii=False)}, taban: {taban_js} }},")
    # OSM kaçırdıysa görselden elle eklenenler (2 ve 3 numaralı işaretler)
    s.append('  // Elle: Rektörlük önü parkı (2. işaret) —')
    s.append('  { isim: "Rektörlük Parkı", tip: "park", taban: [[163,351],[273,401],[208,451],[93,401],[163,351]] },')
    s.append('  // Elle: Teknoloji Fakültesi parkı (3. işaret) —')
    s.append('  { isim: "Teknoloji Parkı", tip: "garden", taban: [[-147,518],[-7,468],[33,588],[-87,668],[-147,518]] },')
    s.append("];")
    s.append("")
    s.append("// ===== YAYA YOLLARI (poligon degil cizgi; [duzluk, genislik(m), tip]) =====")
    s.append("const YOLLAR = [")
    for duz, genislik, tip in sorted(yollar, key=lambda y: -len(y[0])):
        s.append(f"  [{json.dumps(duz)}, {genislik}, {json.dumps(tip)}],")
    s.append("];")
    s.append("")
    s.append("// ===== FISKIYELER / NOKTA YAPILAR (merkez + yaricap) =====")
    s.append("const FISKIYELER = [")
    seen = set()
    for f in fiskiyeler:
        anahtar = tuple(f["merkez"])
        if anahtar in seen:
            continue
        seen.add(anahtar)
        s.append(f"  {{ isim: {json.dumps(f['isim'], ensure_ascii=False)}, "
                 f"merkez: [{f['merkez'][0]}, {f['merkez'][1]}], yaricap: {f['yaricap']} }},")
    # OSM'de çıkmazsa kullanıcının görselinden elle eklenen rektörlük önü fıskiyesi
    s.append('  // Elle: Rektörlük önündeki KARE fıskiye (kullanıcı OSM linki 39.940102, 32.822988;')
    s.append('  // kenar 18 m ≈ en yakın yürüme yoluna (9.5 m) kadar uzanır) —')
    s.append('  { isim: "Rektörlük Fıskiyesi", merkez: [212, 378], yaricap: 3, sekil: "kare", boyut: 18 },')
    s.append("];")
    s.append("")
    s.append("// ===== SPOR ALANLARI (futbol/tenis pisti vb., elle duzenle) =====")
    s.append("const SPOR_ALANLARI = [")
    for a in sorted(spor, key=lambda a: -poligon_alani(a["taban"])):
        taban_js = json.dumps([[x, z] for x, z in a["taban"]])
        s.append(f"  {{ isim: {json.dumps(a['isim'], ensure_ascii=False)}, "
                 f"spor: {json.dumps(a['spor'], ensure_ascii=False)}, taban: {taban_js} }},")
    s.append("];")
    s.append("")
    s.append("// ===== ARKA PLAN BINALARI (kompakt: [duzpoligon, yukseklik]) =====")
    s.append("const ARKA_PLAN_BINALAR = [")
    for duz, yuk, _ in arka_plan:
        s.append(f"  [{json.dumps(duz)}, {yuk}],")
    s.append("];")
    s.append("")

    with open("binalar.js", "w", encoding="utf-8") as f:
        f.write("\n".join(s))

    boyut = os.path.getsize("binalar.js")
    print(f"binalar.js yazildi: {len(onemli)} onemli bina, {len(arka_plan)} arka plan, "
          f"{len(parklar)} park, {len(yollar)} yol, {len(seen)} fiskiye, "
          f"{len(spor)} spor — {boyut/1024:.0f} KB")

if __name__ == "__main__":
    main()
