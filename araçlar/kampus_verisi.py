#!/usr/bin/env python3
"""
Gazi Üniversitesi kampüs çevre verisini OpenStreetMap'ten çekip binalar.js üretir.

Kullanım:
    python3 araçlar/kampus_verisi.py            # OSM'den yeniden çek, binalar.js yaz
    python3 araçlar/kampus_verisi.py --onbellek # ağa çıkmadan son önbellekten üret

Çıktı: proje kökünde binalar.js
- ONEMLI_BINALAR   : isimli önemli binalar   (elle düzenlenebilir)
- ARKA_PLAN_BINALAR: isimsiz binalar         (kompakt)
- PARKLAR          : park/bahçe/çim alanları (elle düzenlenebilir)
- YOLLAR           : yollar (yaya/service/konut/ana) (elle düzenlenebilir)
- FISKIYELER       : fıskiye/havuz noktaları (elle düzenlenebilir)
- SPOR_ALANLARI    : futbol/tenis sahası, koşu pisti (elle düzenlenebilir)

ELLE DÜZENLEMELER: araçlar/elle_veri.json okunur (sabit binalar, silinecek OSM
way id'leri, renk/pencere sabitlemeleri, sıralama, elle park/fıskiye). Bu dosya
sayesinde binalar.js yeniden üretilse bile elle kayıtlar korunur.

Ham OSM verisi araçlar/osm_onbellek.json'a kaydedilir; ağ hatasında önbellekten
devam edilir. Koordinat sistemi: kampüs merkezi (0,0); x=doğu(+), z=güney(+), metre.
"""

import json
import math
import os
import random
import sys
import time
import urllib.parse
import urllib.request

# --- Ayarlar -----------------------------------------------------------------
MERKEZ_LAT = 39.9435
MERKEZ_LON = 32.8205
YARICAP_M = 900
ONEMLI_BINA_LIMITI = 40
ARACLAR = os.path.dirname(os.path.abspath(__file__))
ONBELLEK = os.path.join(ARACLAR, "osm_onbellek.json")
ELLE_VERI = os.path.join(ARACLAR, "elle_veri.json")

ENDPOINTLER = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

PALET = [0xd8c9a8, 0xcfc4b0, 0xb8a98c, 0xc9bdbd, 0xb5c2c9,
         0xd0b49a, 0xc2b6a3, 0xadb8c4, 0xcabfb2, 0xb0a896]

# Bölge tanımı çevresinden çekilecek katman sorguları
SORGULAR = {
    "binalar":  f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["building"];',
    "yollar":   f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["highway"~"^(footway|path|pedestrian|service|residential|secondary|trunk|trunk_link|primary|tertiary|tertiary_link|unclassified|living_street|primary_link|motorway|motorway_link|steps|cycleway|track)$"];',
    "spor":     f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["leisure"~"^(pitch|track|stadium)$"];',
    "parklar":  f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["leisure"~"^(park|garden)$"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["landuse"~"^(grass|meadow|recreation_ground)$"];',
    "fiskiyeler": f'node(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["man_made"="fountain"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["man_made"="fountain"];',
    "agaclar":  f'node(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["natural"="tree"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["natural"="tree_row"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["natural"="wood"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["landuse"~"^(forest|orchard)$"];',
    "isletmeler": f'node(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["shop"];'
                f'node(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["amenity"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["shop"];'
                f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["amenity"];',
    "duraklar": f'node(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["highway"="bus_stop"];'
                f'node(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["railway"~"^(station|halt|tram_stop)$"];'
                f'node(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["public_transport"="platform"];',
    "otoparklar": f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["amenity"="parking"];',
    "raylar":   f'way(around:{YARICAP_M},{MERKEZ_LAT},{MERKEZ_LON})["railway"~"^(rail|light_rail|tram|subway)$"];',
}

# İşletme/POI olarak gösterilecek etiket değerleri (hacmi sınırlı tutar)
POI_TIPLERI = {
    "supermarket", "convenience", "bakery", "greengrocer", "butcher", "kiosk",
    "mall", "department_store", "cafe", "restaurant", "fast_food", "food_court",
    "ice_cream", "pub", "bar", "bank", "atm", "pharmacy", "dentist",
    "veterinary", "fuel", "marketplace", "theatre", "cinema",
    "community_centre", "post_office", "bus_station", "car_rental",
    "bicycle_rental", "driving_school",
}

# Ağaç üretim sınırları (performans: instancing ile çizilir)
AGAC_BUDGET = 9000       # toplam üst sınır
AGAC_KAPSAM = 1400.0     # uçuş sınırı (+pay) dışındaki ağaçlar eklenmez (m)
AGAC_PARK_ADIM = 14.0    # park içi prosedürel aralık (m)
AGAC_CIM_ADIM = 20.0     # kampüs çim/yeşil alan içi prosedürel aralık (m)
AGAC_ORMAN_ADIM = 18.0   # orman/akhile içi prosedürel aralık (m)
AGAC_YOL_ADIM = 8.0      # tree_row boyunca aralık (m)
AGAC_YOL_ARALIK = 11.0   # kampüste yol kenarı ağaç sırası aralığı (m)
AGAC_YOL_YAN = 3.8       # yol kenarı ağacının yol merkezinden uzaklığı (m)
# Gazi ana yerleşkesi (x1, x2, z1, z2): çim dolgusu ve yol kenarı sıraları
# yalnızca bu alanda üretilir (şehir geneline yayılmasın).
KAMPUS_BBOX = (-520.0, 390.0, 150.0, 860.0)
BINA_PAY = 1.2           # prosedürel ağacın binaya minimum uzaklığı (m, dıştan)

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

def osm_verisi_edin(sadece_onbellek=False):
    if sadece_onbellek:
        if os.path.exists(ONBELLEK):
            print("  Önbellek kullanılıyor (--onbellek):", ONBELLEK)
            with open(ONBELLEK, "r", encoding="utf-8") as f:
                return json.load(f)
        sys.exit("--onbellek verildi ama osm_onbellek.json yok; önce ağlı çalıştırın.")
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

def nokta_icinde(x, z, pol):
    """Işın atma testi: nokta poligon içinde mi (dışbükey olmayan poligonlar için)."""
    icinde = False
    n = len(pol)
    for i in range(n):
        x1, z1 = pol[i]
        x2, z2 = pol[(i + 1) % n]
        if ((z1 > z) != (z2 > z)) and (x < (x2 - x1) * (z - z1) / (z2 - z1) + x1):
            icinde = not icinde
    return icinde

def agac_doldur(pol, adim, tohum, tip, engel=None):
    """Poligon içine deterministik ızgara + jitter ile prosedürel ağaç noktaları.
    engel(x, z) True dönerse o nokta atlanır (örn. bina içi)."""
    xs = [p[0] for p in pol]
    zs = [p[1] for p in pol]
    rnd = random.Random(tohum)
    cikti = []
    z = min(zs) + adim / 2
    while z < max(zs):
        x = min(xs) + adim / 2
        while x < max(xs):
            jx = x + (rnd.random() - 0.5) * adim * 0.5
            jz = z + (rnd.random() - 0.5) * adim * 0.5
            if nokta_icinde(jx, jz, pol) and not (engel and engel(jx, jz)):
                cikti.append((round(jx, 1), round(jz, 1), tip))
            x += adim
        z += adim
    return cikti

def cizgi_agac(pts, adim, tohum, tip=0):
    """Polyline (tree_row) boyunca adım aralığıyla ağaç noktaları."""
    rnd = random.Random(tohum)
    cikti = []
    tasinan = 0.0
    for i in range(len(pts) - 1):
        x1, z1 = pts[i]
        x2, z2 = pts[i + 1]
        L = math.hypot(x2 - x1, z2 - z1)
        if L < 1e-6:
            continue
        t = tasinan
        while t < L:
            f = t / L
            cikti.append((round(x1 + (x2 - x1) * f, 1),
                          round(z1 + (z2 - z1) * f, 1), tip))
            t += adim
        tasinan = t - L
    return cikti

def yol_agac(pts, tohum, icinde, tip=0):
    """Kampüs yolu boyunca iki yana dönüşümlü ağaç sırası.
    icinde(x, z) False dönerse nokta atlanır (bbox/bina filtresi)."""
    rnd = random.Random(tohum)
    cikti = []
    tasinan = 0.0
    taraf = 1
    for i in range(len(pts) - 1):
        x1, z1 = pts[i]
        x2, z2 = pts[i + 1]
        dx, dz = x2 - x1, z2 - z1
        L = math.hypot(dx, dz)
        if L < 1e-6:
            continue
        ux, uz = dx / L, dz / L
        nx, nz = -uz, ux
        # Hafif doğal sapma: sabit ızgara yerine ±%15 jitter
        qx0 = (rnd.random() - 0.5) * AGAC_YOL_ARALIK * 0.3
        t = tasinan + qx0
        while t < L:
            f = t / L
            px, pz = x1 + dx * f, z1 + dz * f
            off = AGAC_YOL_YAN * taraf
            qx, qz = px + nx * off, pz + nz * off
            if icinde(qx, qz):
                cikti.append((round(qx, 1), round(qz, 1), tip))
            taraf = -taraf
            t += AGAC_YOL_ARALIK
        tasinan = t - L
    return cikti

def bina_kutusu(pol, pay=BINA_PAY):
    """(bbox, poligon) — hızlı bina içi testi için."""
    xs = [p[0] for p in pol]
    zs = [p[1] for p in pol]
    return ((min(xs) - pay, max(xs) + pay, min(zs) - pay, max(zs) + pay), pol)

def bina_engel(kutular, x, z):
    """Nokta herhangi bir binanın (paylı) sınırları içinde mi."""
    for (x1, x2, z1, z2), pol in kutular:
        if x1 <= x <= x2 and z1 <= z <= z2 and nokta_icinde(x, z, pol):
            return True
    return False

def yukseklik_tahmin(p):
    # Kullanıcı kararı: kat aralığı daraltıldı (2-3), görsel ölçek ×2 (kat*3m*2).
    # Rektörlük (4 kat) artık cüce kalmaz, kampüs silüeti heybetli durur.
    kat = max(2, min(3, round(math.sqrt(poligon_alani(p)) / 6.0)))
    return kat * 6, kat

def yukseklik_belirle(p, tags):
    """OSM building:levels/height etiketlerini güvenli sınırlarla kullan;
    etiket yoksa/geçersizse alan tahminine düş. Görsel ölçek: gerçek m ×2."""
    def _sayi(metin):
        try:
            return float(str(metin).replace(",", ".").split(";")[0].split()[0])
        except (ValueError, IndexError):
            return None

    h_m = _sayi(tags.get("height")) if tags.get("height") else None
    if h_m is not None and 3 <= h_m <= 60:
        return max(6, round(h_m * 2)), max(1, min(15, round(h_m / 3)))
    k = _sayi(tags.get("building:levels")) if tags.get("building:levels") else None
    if k is not None:
        k = int(round(k))
        if 1 <= k <= 15:
            return k * 6, k
    return yukseklik_tahmin(p)

# --- Elle veri (araçlar/elle_veri.json) -----------------------------------------
def elle_veriyi_yukle():
    """Elle düzenlemelerin tek kaynağı; üretim bunları korur. Eksik dosya hata değil."""
    bos = {"binalar": [], "sil": [], "sira": [], "renkler": {}, "pencereler": {},
           "parklar": [], "fiskiyeler": [], "yollar": [], "poiler": [], "agaclar": [],
           "girisler": [], "bayraklar": []}
    if not os.path.exists(ELLE_VERI):
        print(f"  UYARI: {ELLE_VERI} yok; elle düzenlemeler uygulanmayacak.")
        return bos
    try:
        with open(ELLE_VERI, "r", encoding="utf-8") as f:
            v = json.load(f)
    except Exception as e:
        print(f"  UYARI: elle_veri.json okunamadı ({e}); yok sayılıyor.")
        return bos
    for k, d in bos.items():
        v.setdefault(k, d)
    return v

def renk_coz(deger):
    """0xRRGGBB metni veya sayıyı int'e çevirir; geçersizse None."""
    if deger is None:
        return None
    if isinstance(deger, int):
        return deger
    s = str(deger).strip()
    try:
        return int(s, 16) if s.lower().startswith("0x") else int(s)
    except ValueError:
        return None

# --- Ana işlem ------------------------------------------------------------------
def main():
    veri = osm_verisi_edin("--onbellek" in sys.argv[1:])
    elle = elle_veriyi_yukle()
    sil = {int(x) for x in elle["sil"]}
    # Elle binada osmWay verilmişse OSM kopyası çizilmesin (elle sürüm geçerlidir)
    for b in elle["binalar"]:
        if b.get("osmWay"):
            sil.add(int(b["osmWay"]))
    d2 = Donusturucu(MERKEZ_LAT, MERKEZ_LON)
    dugumler = {e["id"]: (e["lat"], e["lon"]) for e in veri["elements"] if e["type"] == "node"}

    # Yol tipine göre şerit genişliği (m) ve render tipi
    YOL_GENISLIK = {"footway": 1.4, "path": 1.4, "pedestrian": 2.5, "service": 3.5,
                    "residential": 4.5, "secondary": 6.0, "trunk": 8.0,
                    "trunk_link": 5.0, "primary": 8.0, "tertiary": 6.0,
                    "tertiary_link": 4.0, "unclassified": 4.5, "living_street": 4.0,
                    "primary_link": 6.0, "motorway": 10.0, "motorway_link": 6.0,
                    "steps": 1.5, "cycleway": 2.0, "track": 3.0}
    YOL_TIP = {"footway": "footway", "path": "path", "pedestrian": "pedestrian",
               "service": "service", "residential": "service",
               "secondary": "ana", "trunk": "ana", "trunk_link": "ana", "primary": "ana",
               "tertiary": "tertiary", "tertiary_link": "tertiary",
               "unclassified": "unclassified", "living_street": "living",
               "primary_link": "primary", "motorway": "motorway",
               "motorway_link": "motorway", "steps": "steps",
               "cycleway": "cycleway", "track": "track"}

    onemli, arka_plan, parklar, yollar, fiskiyeler, spor = [], [], [], [], [], []
    gorulen = set()
    # Opsiyonel çevre katmanları
    agac_osm, agac_park, agac_cim, agac_yol, agac_orman = [], [], [], [], []
    isletmeler, otoparklar, duraklar, raylar = [], [], [], []
    poi_anahtar = set()
    bina_kutulari = []   # prosedürel ağaçlarda bina kaçınması için (bbox, poligon)

    def agac_ekle(liste, x, z, tip):
        liste.append((round(x, 1), round(z, 1), tip))

    def poi_ekle(x, z, tip, ad):
        anahtar = (round(x, 1), round(z, 1), tip)
        if anahtar in poi_anahtar:
            return
        poi_anahtar.add(anahtar)
        isletmeler.append((anahtar[0], anahtar[1], tip, ad or ""))

    def agac_tipi(t):
        lt = t.get("leaf_type")
        if lt == "needleleaved":
            return 1
        return 0

    for e in veri["elements"]:
        if e["type"] == "node":
            t = e.get("tags", {})
            if t.get("man_made") == "fountain":
                x, z = d2.xy(e["lat"], e["lon"])
                fiskiyeler.append({"isim": t.get("name", "Fıskiye"),
                                   "merkez": [x, z], "yaricap": 2})
                continue
            if t.get("natural") == "tree":
                x, z = d2.xy(e["lat"], e["lon"])
                agac_ekle(agac_osm, x, z, agac_tipi(t))
                continue
            poi = t.get("shop") or t.get("amenity")
            if poi in POI_TIPLERI:
                x, z = d2.xy(e["lat"], e["lon"])
                poi_ekle(x, z, poi, t.get("name"))
                continue
            if t.get("highway") == "bus_stop":
                x, z = d2.xy(e["lat"], e["lon"])
                duraklar.append((x, z, "bus", t.get("name", "")))
                continue
            if t.get("railway") in ("station", "halt", "tram_stop"):
                x, z = d2.xy(e["lat"], e["lon"])
                tip = "tram" if t.get("railway") == "tram_stop" else "rail"
                duraklar.append((x, z, tip, t.get("name", "")))
                continue
            if t.get("public_transport") == "platform":
                x, z = d2.xy(e["lat"], e["lon"])
                duraklar.append((x, z, "bus", t.get("name", "")))
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

        # İşletme/POI: bina olsa bile ikon olarak eklenir
        poi = tags.get("shop") or tags.get("amenity")
        if poi in POI_TIPLERI:
            cx, cz = merkez(coords)
            poi_ekle(cx, cz, poi, isim)

        if "building" in tags:
            if e.get("id") in sil:
                continue  # elle_veri.json: hayalet/çakışan bina
            if not kapali or len(coords) < 3:
                continue
            uni_mi = tags["building"] == "university" or tags.get("amenity") in ("library", "university")
            pol = rdp(coords, 0.5 if (isim and uni_mi) else 1.0)
            if len(pol) < 3:
                continue
            yuk, kat = yukseklik_belirle(pol, tags)
            if isim and isim not in gorulen and (uni_mi or tags["building"] not in ("residential",)):
                gorulen.add(isim)
                onemli.append({"isim": isim, "taban": pol, "yukseklik": yuk,
                               "kat": kat, "_uni": uni_mi, "osmWay": e.get("id")})
            else:
                duz = []
                for x, z in pol:
                    duz.extend([x, z])
                arka_plan.append([duz, yuk, e.get("id")])
            bina_kutulari.append(bina_kutusu(pol))

        elif tags.get("highway") in YOL_GENISLIK:
            pol = rdp(coords, 0.8)
            if len(pol) >= 2:
                duz = []
                for x, z in pol:
                    duz.extend([x, z])
                hw = tags.get("highway")
                yollar.append([duz, YOL_GENISLIK[hw], YOL_TIP[hw]])
                # Kampüs içi yaya/service yollarına iki yana ağaç sırası
                if hw in ("footway", "path", "pedestrian", "service", "living_street"):
                    mx = sum(p[0] for p in pol) / len(pol)
                    mz = sum(p[1] for p in pol) / len(pol)
                    x1, x2, z1, z2 = KAMPUS_BBOX
                    if x1 <= mx <= x2 and z1 <= mz <= z2:
                        def _uygun(qx, qz, _kutular=bina_kutulari):
                            x1, x2, z1, z2 = KAMPUS_BBOX
                            return (x1 <= qx <= x2 and z1 <= qz <= z2 and
                                    not bina_engel(_kutular, qx, qz))
                        agac_yol.extend(yol_agac(pol, e.get("id", 0), _uygun, 0))

        elif tags.get("natural") == "tree_row":
            pol = rdp(coords, 0.8)
            agac_osm.extend(cizgi_agac(pol, AGAC_YOL_ADIM, e.get("id", 0), agac_tipi(tags)))

        elif tags.get("natural") == "wood" or tags.get("landuse") in ("forest", "orchard"):
            if kapali and len(coords) >= 3:
                pol = rdp(coords, 1.0)
                if len(pol) >= 3:
                    agac_orman.extend(agac_doldur(pol, AGAC_ORMAN_ADIM,
                                                  e.get("id", 0), agac_tipi(tags)))

        elif tags.get("amenity") == "parking":
            if kapali and len(coords) >= 3:
                pol = rdp(coords, 1.0)
                if len(pol) >= 3:
                    duz = []
                    for x, z in pol:
                        duz.extend([x, z])
                    otoparklar.append(duz)

        elif tags.get("railway") in ("rail", "light_rail", "tram", "subway"):
            pol = rdp(coords, 1.0)
            if len(pol) >= 2:
                duz = []
                for x, z in pol:
                    duz.extend([x, z])
                raylar.append((duz, tags.get("railway")))

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
            # Park/bahçe içine prosedürel ağaç (OSM ağacı yoksa görsel yoğunluk);
            # bina içine düşen noktalar elenir.
            def _bina_var(qx, qz, _kutular=bina_kutulari):
                return bina_engel(_kutular, qx, qz)
            if tip in ("park", "garden"):
                agac_park.extend(agac_doldur(pol, AGAC_PARK_ADIM, e.get("id", 0), 0,
                                             _bina_var))
            elif tip in ("grass", "meadow", "recreation_ground"):
                # Kampüs içindeki çim/yeşil alanlara seyrek ağaç (üniversite yoğunluğu)
                x1, x2, z1, z2 = KAMPUS_BBOX
                if any(x1 <= p[0] <= x2 and z1 <= p[1] <= z2 for p in pol):
                    agac_cim.extend(agac_doldur(pol, AGAC_CIM_ADIM, e.get("id", 0), 0,
                                                _bina_var))

        elif tags.get("man_made") == "fountain":
            if len(coords) >= 3:
                cx, cz = merkez(coords)
                xs = [c[0] for c in coords]
                zs = [c[1] for c in coords]
                r = max(1.5, min(6.0, (max(xs) - min(xs) + max(zs) - min(zs)) / 4))
                fiskiyeler.append({"isim": isim or "Fıskiye",
                                   "merkez": [round(cx, 1), round(cz, 1)],
                                   "yaricap": round(r, 1)})

    # --- Ağaç havuzlarını birleştir (OSM önce, prosedürel sonra) + bütçe ---
    agaclar, agac_gorulen = [], set()
    elle_agac = [(float(a[0]), float(a[1]), int(a[2])) for a in elle["agaclar"]]
    for liste in (elle_agac, agac_osm, agac_park, agac_cim, agac_yol, agac_orman):
        otomatik = liste is not elle_agac
        for x, z, tip in liste:
            if len(agaclar) >= AGAC_BUDGET:
                break
            if math.hypot(x, z) > AGAC_KAPSAM:
                continue
            # Bina içine düşen otomatik ağaçları ele (elle eklenenlere dokunma)
            if otomatik and bina_engel(bina_kutulari, x, z):
                continue
            anahtar = (round(x, 1), round(z, 1))
            if anahtar in agac_gorulen:
                continue
            agac_gorulen.add(anahtar)
            agaclar.append((anahtar[0], anahtar[1], tip))
        if len(agaclar) >= AGAC_BUDGET:
            print(f"  NOT: ağaç bütçesi ({AGAC_BUDGET}) doldu; kalanlar eklenmedi.")
            break

    # --- Elle POI / yol eklemeleri (elle_veri.json) ---
    for p in elle["poiler"]:
        if p.get("merkez"):
            poi_ekle(float(p["merkez"][0]), float(p["merkez"][1]),
                     p.get("tip", "market"), p.get("isim", ""))
    for y in elle["yollar"]:
        if y and len(y) >= 3:
            yollar.append(y)

    # --- Elle binalar: elle_veri.json'daki sabit poligonlar (kullanıcı onaylı) ---
    elle_binalar = []
    for kayit in elle["binalar"]:
        isim = kayit.get("isim")
        if not isim or not kayit.get("taban"):
            print(f"  UYARI: elle bina kaydı eksik, atlandı: {kayit!r}")
            continue
        if any(isim in b["isim"] for b in onemli):
            continue  # OSM'den zaten isimli geldi
        taban = [[float(v) for v in p] for p in kayit["taban"]]
        yukseklik = int(kayit.get("yukseklik", 12))
        kat = int(kayit.get("kat", max(2, yukseklik // 6)))
        # Elle poligonla çakışan arka plan binalarını çıkar (çift çizim olmasın)
        once = len(arka_plan)
        tutulan = []
        for a in arka_plan:
            pol = [[a[0][i], a[0][i + 1]] for i in range(0, len(a[0]), 2)]
            cx = sum(p[0] for p in pol) / len(pol)
            cz = sum(p[1] for p in pol) / len(pol)
            if not nokta_icinde(cx, cz, taban):
                tutulan.append(a)
        arka_plan = tutulan
        elle_binalar.append({"isim": isim, "taban": taban, "yukseklik": yukseklik,
                             "kat": kat, "renk": kayit.get("renk"),
                             "pencere": kayit.get("pencere"),
                             "osmWay": kayit.get("osmWay")})
        print(f"  {isim}: elle poligon yerleştirildi "
              f"({len(taban)} nokta, {once - len(arka_plan)} çakışan bina çıkarıldı)")

    # Sıralama: elle_veri.json 'sira' başa, kalanlar alana göre azalan.
    # ONEMLI_BINA_LIMITI yalnızca OSM kaynaklılara uygulanır (elle binalar limitten muaf).
    # Limit dolduğunda üniversite binaları önceliklidir (öncelik yoksa alan sırası korunur).
    if len(onemli) > ONEMLI_BINA_LIMITI:
        onemli = sorted(onemli, key=lambda b: (0 if b.get("_uni") else 1,
                                               -poligon_alani(b["taban"])))[:ONEMLI_BINA_LIMITI]
    else:
        onemli = sorted(onemli, key=lambda b: -poligon_alani(b["taban"]))
    sira = list(elle["sira"])
    one = [b for ad in sira for b in elle_binalar if b["isim"] == ad]
    geri = [b for b in elle_binalar if b["isim"] not in sira] + onemli
    geri.sort(key=lambda b: -poligon_alani(b["taban"]))
    onemli = one + geri

    # --- binalar.js yaz ---
    s = []
    s.append("// ** BU DOSYA araclar/kampus_verisi.py ILE OTOMATIK URETILMISTIR **")
    s.append("// Listeleri ELLE DUZENLEMEK icin serbestsiniz; tarayicida F5 yeterli.")
    s.append("// Kalici duzenleme: araclar/elle_veri.json (yeniden uretimde korunur).")
    s.append("// Koordinat: kampus merkezi (0,0); x = dogu (+), z = guney (+), birim: metre.")
    s.append("// Pencereler (sadece ONEMLI_BINALAR'da, opsiyonel):")
    s.append("//   pencere: false                  \u2192 bu binada pencere yok")
    s.append("//   pencere: { yogunluk: 0.8 }      \u2192 pencerelerin %80'i cizilir (0-1)")
    s.append("//   pencere: { renk: 0x7fb6cc }      \u2192 cam rengi (varsayilan acik mavi)")
    s.append("//   pencere: { isikOran: 0.4 }       \u2192 yanan (sari) cam orani (varsayilan 0.25)")
    s.append("//   (hic yazilmazsa varsayilan: yogunluk 0.75, acik mavi cam, %25 yanik)")
    s.append("")
    s.append("// ===== ONEMLI BINALAR (isimli, elle duzenle) =====")
    s.append("const ONEMLI_BINALAR = [")
    for i, b in enumerate(onemli):
        renk = renk_coz(b.get("renk"))
        if renk is None:
            renk = renk_coz(elle["renkler"].get(b["isim"]))
        if renk is None:
            renk = PALET[i % len(PALET)]
        taban_js = json.dumps([[x, z] for x, z in b["taban"]])
        pencere = b.get("pencere") or elle["pencereler"].get(b["isim"])
        s.append("  {")
        s.append(f"    isim: {json.dumps(b['isim'], ensure_ascii=False)},")
        s.append(f"    taban: {taban_js},")
        s.append(f"    yukseklik: {b['yukseklik']},")
        if b.get("osmWay"):
            s.append(f"    osmWay: {b['osmWay']},")
        s.append(f"    renk: 0x{renk:06x},")
        s.append("    catRengi: 0x6e6e6e,")
        if pencere:
            s.append(f"    pencere: {json.dumps(pencere, ensure_ascii=False)},")
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
    # OSM kaçırdıysa elle eklenenler (araçlar/elle_veri.json)
    gorulen_isim = {p["isim"] for p in parklar if p.get("isim")}
    for p in elle["parklar"]:
        if not p.get("taban") or p.get("isim") in gorulen_isim:
            continue
        taban_js = json.dumps([[float(x), float(z)] for x, z in p["taban"]])
        s.append(f"  // Elle (elle_veri.json): {json.dumps(p.get('isim', 'Park'), ensure_ascii=False)}")
        s.append(f"  {{ isim: {json.dumps(p.get('isim', 'Park'), ensure_ascii=False)}, "
                 f"tip: {json.dumps(p.get('tip', 'park'), ensure_ascii=False)}, taban: {taban_js} }},")
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
    # OSM'de çıkmazsa elle eklenenler (araçlar/elle_veri.json)
    for f in elle["fiskiyeler"]:
        anahtar = (float(f["merkez"][0]), float(f["merkez"][1]))
        if anahtar in seen:
            continue
        seen.add(anahtar)
        ek = ""
        if f.get("sekil"):
            ek += f", sekil: {json.dumps(f['sekil'], ensure_ascii=False)}"
        if f.get("boyut"):
            ek += f", boyut: {f['boyut']}"
        s.append(f"  // Elle (elle_veri.json): {json.dumps(f.get('isim', 'Fıskiye'), ensure_ascii=False)}")
        s.append(f"  {{ isim: {json.dumps(f.get('isim', 'Fıskiye'), ensure_ascii=False)}, "
                 f"merkez: [{anahtar[0]}, {anahtar[1]}], yaricap: {f.get('yaricap', 2)}{ek} }},")
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
    s.append("// ===== ARKA PLAN BINALARI (kompakt: [duzpoligon, yukseklik, osmWay]) =====")
    s.append("const ARKA_PLAN_BINALAR = [")
    for duz, yuk, oid in arka_plan:
        s.append(f"  [{json.dumps(duz)}, {yuk}, {oid}],")
    s.append("];")
    s.append("")

    with open("binalar.js", "w", encoding="utf-8") as f:
        f.write("\n".join(s))

    boyut = os.path.getsize("binalar.js")
    print(f"binalar.js yazildi: {len(onemli)} onemli bina, {len(arka_plan)} arka plan, "
          f"{len(parklar)} park, {len(yollar)} yol, {len(seen)} fiskiye, "
          f"{len(spor)} spor — {boyut/1024:.0f} KB")

    # --- cevre.js: opsiyonel detay katmanlari (agac, POI, otopark, durak, ray) ---
    # binalar.js'ten ayri tutulur; tarayici dosyayi bulamazsa uygulama cokmez.
    c = []
    c.append("// ** BU DOSYA araclar/kampus_verisi.py ILE OTOMATIK URETILMISTIR **")
    c.append("// Opsiyonel cevre katmanlari. Ana listeler binalar.js'tedir.")
    c.append("// Koordinat: x = dogu (+), z = guney (+), birim: metre.")
    c.append("")
    c.append("// [x, z, tip] — tip: 0 yaprakli, 1 iğne yaprakli, 2 cali (prosedurel)")
    c.append("const AGACLAR = [")
    for x, z, tip in agaclar:
        c.append(f"  [{x}, {z}, {tip}],")
    c.append("];")
    c.append("")
    c.append("// [x, z, tip, isim] — tip: supermarket, cafe, bank, atm, pharmacy, ...")
    c.append("const ISLETMELER = [")
    for x, z, tip, ad in isletmeler:
        c.append(f"  [{x}, {z}, {json.dumps(tip, ensure_ascii=False)}, "
                 f"{json.dumps(ad, ensure_ascii=False)}],")
    c.append("];")
    c.append("")
    c.append("// [duzpoligon] — otopark alanlari")
    c.append("const OTOPARKLAR = [")
    for duz in otoparklar:
        c.append(f"  {json.dumps(duz)},")
    c.append("];")
    c.append("")
    c.append("// [x, z, tip, isim] — tip: bus, tram, rail")
    c.append("const DURAKLAR = [")
    for x, z, tip, ad in duraklar:
        c.append(f"  [{x}, {z}, {json.dumps(tip, ensure_ascii=False)}, "
                 f"{json.dumps(ad, ensure_ascii=False)}],")
    c.append("];")
    c.append("")
    c.append("// [duzpoligon, tip] — tip: rail, tram, subway, light_rail")
    c.append("const RAYLAR = [")
    for duz, tip in raylar:
        c.append(f"  [{json.dumps(duz)}, {json.dumps(tip, ensure_ascii=False)}],")
    c.append("];")
    c.append("")
    c.append("// Kampüs giriş kapıları: { isim, merkez:[x,z], aci (derece), pano }")
    c.append("const GIRISLER = [")
    for g in elle["girisler"]:
        if not g.get("merkez"):
            continue
        kayit = {k: v for k, v in g.items() if not k.startswith("_")}
        c.append("  " + json.dumps(kayit, ensure_ascii=False) + ",")
    c.append("];")
    c.append("")
    c.append("// Bayraklar: { isim, merkez:[x,z], tip, yukseklik }")
    c.append("const BAYRAKLAR = [")
    for b in elle["bayraklar"]:
        if not b.get("merkez"):
            continue
        kayit = {k: v for k, v in b.items() if not k.startswith("_")}
        c.append("  " + json.dumps(kayit, ensure_ascii=False) + ",")
    c.append("];")
    c.append("")

    with open("cevre.js", "w", encoding="utf-8") as f:
        f.write("\n".join(c))

    cboyut = os.path.getsize("cevre.js")
    print(f"cevre.js yazildi: {len(agaclar)} agac, {len(isletmeler)} isletme, "
          f"{len(otoparklar)} otopark, {len(duraklar)} durak, {len(raylar)} ray, "
          f"{len(elle['girisler'])} giris, {len(elle['bayraklar'])} bayrak "
          f"— {cboyut/1024:.0f} KB")

if __name__ == "__main__":
    main()
