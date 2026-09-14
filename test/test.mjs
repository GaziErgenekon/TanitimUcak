// GAZİ Kampüs Uçuş Simülatörü testleri — bağımlılık yok (three opsiyonel).
// Çalıştırma: node --test test/
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { blok, veriYukle, threeYukle } from './ayikla.mjs';

// --- pencereAyar / pencere sınırları -----------------------------------------
function pencereSandbox() {
  const ctx = { Number, Math, console, isNaN, parseFloat, parseInt };
  vm.createContext(ctx);
  vm.runInContext(blok('PENCERE-AYAR') +
    '\n;globalThis.__p = { pencereAyar, pencereSinirla };\n', ctx);
  return ctx.__p;
}

test('pencereAyar varsayılanları: sık kolon + kat hizası', () => {
  const { pencereAyar } = pencereSandbox();
  const a = pencereAyar(null);
  assert.equal(a.katAralik, 3);
  assert.equal(a.kolonAralik, 1.6);
  assert.ok(a.genislik > 0 && a.genislik <= a.kolonAralik - 0.15, 'pencere kolondan dar');
  assert.ok(a.yukseklik > 0 && a.yukseklik <= a.katAralik - 0.6);
  assert.equal(a.zeminBos, 0);
  assert.equal(a.yogunluk, 0.85);
  assert.equal(a.isikOran, 0.25);
});

test('pencereAyar false / acik:false penceresiz bina', () => {
  const { pencereAyar } = pencereSandbox();
  assert.equal(pencereAyar({ pencere: false }), null);
  assert.equal(pencereAyar({ pencere: { acik: false } }), null);
});

test('pencereAyar kat yüksekliğini yükseklik/katsayisi ile hizalar', () => {
  const { pencereAyar } = pencereSandbox();
  assert.equal(pencereAyar({ yukseklik: 24, detay: { katsayisi: 4 } }).katAralik, 6);
  assert.equal(pencereAyar({ yukseklik: 18, detay: { katsayisi: 3 } }).katAralik, 6);
  assert.equal(pencereAyar({ yukseklik: 18, pencere: { katAralik: 3 } }).katAralik, 3);
});

test('pencereAyar kullanıcı değerlerini sınırlar', () => {
  const { pencereAyar } = pencereSandbox();
  const a = pencereAyar({ pencere: { kolonAralik: 0.1, katAralik: 100, genislik: 99, yogunluk: 5 } });
  assert.equal(a.kolonAralik, 0.8);
  assert.equal(a.katAralik, 8);
  assert.ok(a.genislik <= a.kolonAralik - 0.15);
  assert.equal(a.yogunluk, 1);
});

// --- buton sönümleme ----------------------------------------------------------
function butonSandbox() {
  const ctx = {};
  vm.createContext(ctx);
  vm.runInContext(blok('BUTON-KENAR') +
    '\n;globalThis.__b = { butonKenarIsle, durum: () => ({ butonKararli, butonArdarda, sonToggleMs }) };\n', ctx);
  return ctx.__b;
}

test('buton: 3 ardışık aynı örnek + 500ms refractory', () => {
  const b = butonSandbox();
  assert.equal(b.butonKenarIsle(1, 0), false);      // değişim yok
  assert.equal(b.butonKenarIsle(0, 100), false);    // 1/3
  assert.equal(b.butonKenarIsle(0, 120), false);    // 2/3
  assert.equal(b.butonKenarIsle(0, 140), true);     // 3/3 → geçerli basış
  assert.equal(b.butonKenarIsle(1, 200), false);
  assert.equal(b.butonKenarIsle(1, 220), false);
  assert.equal(b.butonKenarIsle(1, 240), false);    // buton bırakıldı (toggle yok)
  assert.equal(b.butonKenarIsle(0, 300), false);
  assert.equal(b.butonKenarIsle(0, 320), false);
  assert.equal(b.butonKenarIsle(0, 340), false);    // 340-140=200ms < 500 → refractory
  assert.equal(b.butonKenarIsle(1, 400), false);
  assert.equal(b.butonKenarIsle(1, 420), false);
  assert.equal(b.butonKenarIsle(1, 440), false);
  assert.equal(b.butonKenarIsle(0, 1000), false);
  assert.equal(b.butonKenarIsle(0, 1020), false);
  assert.equal(b.butonKenarIsle(0, 1040), true);    // refractory doldu
});

// --- CSV satır işleme + pil alanı --------------------------------------------
function satirSandbox() {
  const ctx = {
    console, isNaN, parseFloat, parseInt, Math,
    YURUT_PITCH: 1, YURUT_ROLL: 1,
    ham: { pitch: 0, roll: 0, buton: 1 },
    performance: { now: () => 0 },
    veriKaydet: () => {},
    kameraTogglesi: () => { ctx.__kamera++; },
    __kamera: 0,
    butonKenarIsle: () => false,
  };
  vm.createContext(ctx);
  // Pil tanımı ve satır işleme aynı kapsamda çalışır (index.html'deki sıra gibi)
  vm.runInContext(blok('PIL') + blok('SATIR-ISLE') +
    '\n;globalThis.__s = { satirIsle, pil };\n', ctx);
  return ctx.__s;
}

test('CSV 3 alan (eski firmware) geriye uyumlu', () => {
  const s = satirSandbox();
  s.satirIsle('12.50,-4.20,1');
  assert.equal(s.pil.mv, -1);
});

test('CSV 4 alan pil_mV okunur', () => {
  const s = satirSandbox();
  s.satirIsle('12.50,-4.20,1,3980');
  assert.equal(s.pil.mv, 3980);
  s.satirIsle('12.50,-4.20,1,-1');
  assert.equal(s.pil.mv, -1);
});

test('CSV bozuk/eksik satır yok sayılır', () => {
  const s = satirSandbox();
  s.satirIsle('abc,def,ghi');
  s.satirIsle('1,2');
  assert.equal(s.pil.mv, -1);
});

// --- pil yüzdesi --------------------------------------------------------------
function pilSandbox() {
  const ctx = { Math };
  vm.createContext(ctx);
  vm.runInContext(blok('PIL') + '\n;globalThis.__p = { pilYuzde, pilMetni, pil };\n', ctx);
  return ctx.__p;
}

test('pil yüzdesi eşikleri', () => {
  const p = pilSandbox();
  assert.equal(p.pilYuzde(4.2), 100);
  assert.equal(p.pilYuzde(3.2), 0);
  assert.equal(p.pilYuzde(3.9), 75);
  assert.equal(p.pilYuzde(3.7), 40);
  assert.equal(p.pilYuzde(4.0), 85);
});

test('pil metni ölçüm yok/açık', () => {
  const p = pilSandbox();
  assert.equal(p.pilMetni(), '—');
  p.pil.mv = 3980;
  assert.equal(p.pilMetni(), '%83 (3.98V)');
});

// --- veri dosyaları geçerliliği ----------------------------------------------
test('binalar.js ve cevre.js verileri geçerli', () => {
  const v = veriYukle();
  assert.ok(v.ONEMLI_BINALAR.length >= 30, 'önemli bina sayısı');
  assert.ok(v.ARKA_PLAN_BINALAR.length > 500, 'arka plan bina sayısı');
  assert.ok(v.PARKLAR.length > 5 && v.YOLLAR.length > 100 && v.SPOR_ALANLARI.length > 5);

  const adlar = new Set();
  for (const b of v.ONEMLI_BINALAR) {
    assert.ok(b.isim && b.taban.length >= 3, `geçersiz bina: ${b.isim}`);
    assert.ok(!adlar.has(b.isim), `çift isim: ${b.isim}`);
    adlar.add(b.isim);
    assert.ok(b.yukseklik >= 3 && b.yukseklik <= 200, `yükseklik: ${b.isim}`);
    for (const [x, z] of b.taban) {
      assert.ok(Math.abs(x) < 1400 && Math.abs(z) < 1400, `sınır dışı: ${b.isim}`);
    }
  }
  assert.ok(v.ONEMLI_BINALAR.some(b => b.osmWay), 'OSM way id taşınmalı');
  assert.ok(v.ARKA_PLAN_BINALAR.every(k => k.length === 3 && k[2] > 0), 'arka plan [duz,yuk,way]');

  for (const a of v.AGACLAR) {
    assert.equal(a.length, 3);
    assert.ok(Math.hypot(a[0], a[1]) <= 1401, 'ağaç sınır dışı');
    assert.ok(a[2] >= 0 && a[2] <= 2);
  }
  for (const i of v.ISLETMELER) {
    assert.equal(i.length, 4);
    assert.ok(typeof i[2] === 'string');
  }
  assert.ok(v.OTOPARKLAR.every(o => o.length >= 6));
  assert.ok(v.DURAKLAR.every(d => ['bus', 'tram', 'rail'].includes(d[2])));
  assert.ok(v.RAYLAR.every(r => r.length === 2));

  // Kapılar ve bayraklar
  assert.ok(v.GIRISLER.length >= 2, 'en az A ve C kapısı olmalı');
  const kapıAdları = v.GIRISLER.map(g => g.isim);
  assert.ok(kapıAdları.some(a => a.includes('A Kapısı')));
  assert.ok(kapıAdları.some(a => a.includes('C Kapısı')));
  for (const g of v.GIRISLER) {
    assert.equal(g.merkez.length, 2);
    assert.ok(Math.abs(g.merkez[0]) < 1400 && Math.abs(g.merkez[1]) < 1400);
    assert.ok(Number.isFinite(g.aci), 'kapı açısı sayı olmalı');
    assert.ok(typeof g.pano === 'string' && g.pano.length > 0, 'pano yazısı');
  }
  assert.ok(v.BAYRAKLAR.length >= 1);
  for (const b of v.BAYRAKLAR) {
    assert.equal(b.merkez.length, 2);
    assert.ok(b.yukseklik >= 5 && b.yukseklik <= 30);
  }
});

// --- geometri (three varsa) ---------------------------------------------------
const THREE = await threeYukle();

test('binaGeometrisi: extrude yere dik, yükseklik doğru', { skip: !THREE }, () => {
  const ctx = { THREE, Math, console };
  vm.createContext(ctx);
  vm.runInContext(blok('GEO') +
    '\n;globalThis.__g = { binaGeometrisi, merkezHesapla, duvarUVGuncelle };\n', ctx);
  const { binaGeometrisi, merkezHesapla, duvarUVGuncelle } = ctx.__g;
  const taban = [[0, 0], [10, 0], [10, 10], [0, 10]];
  const g = binaGeometrisi(taban, 12);
  g.computeBoundingBox();
  assert.ok(Math.abs(g.boundingBox.min.y) < 0.01, 'taban y=0');
  assert.ok(Math.abs(g.boundingBox.max.y - 12) < 0.01, 'yükseklik 12');
  const [cx, cz] = merkezHesapla(taban);
  assert.equal(cx, 5);
  assert.equal(cz, 5);
  const gruplar = g.groups.map(x => x.materialIndex).sort();
  assert.deepEqual(gruplar, [0, 1], 'kapak + duvar grubu');

  // three.js: grup 0 = kapak (dikey normal), grup 1 = yan duvar (yatay normal)
  const nor = g.attributes.normal;
  for (const gr of g.groups) {
    let yToplam = 0;
    for (let i = gr.start; i < gr.start + gr.count; i++) yToplam += Math.abs(nor.getY(i));
    yToplam /= gr.count;
    if (gr.materialIndex === 0) assert.ok(yToplam > 0.99, 'grup 0 kapak olmalı');
    else assert.ok(yToplam < 0.01, 'grup 1 yan duvar olmalı');
  }

  // duvarUVGuncelle: v = dünya yüksekliği (m), u metre (baskın eksen)
  duvarUVGuncelle(g);
  const uv = g.attributes.uv, pos = g.attributes.position;
  const duvar = g.groups.find(x => x.materialIndex === 1);
  for (let i = duvar.start; i < duvar.start + duvar.count; i++) {
    assert.ok(Math.abs(uv.getY(i) - pos.getY(i)) < 1e-6, 'UV v = yükseklik (m)');
    assert.ok(Math.abs(uv.getX(i) - pos.getX(i)) < 1e-6 ||
              Math.abs(uv.getX(i) - pos.getZ(i)) < 1e-6, 'UV u metre');
  }
});

test('dilimle: duvar/çatı ayrık ve birleştirilebilir', { skip: !THREE }, async () => {
  let mergeGeometries = null;
  for (const aday of ['three/addons/utils/BufferGeometryUtils.js',
    '/tmp/opencode/geo/node_modules/three/examples/jsm/utils/BufferGeometryUtils.js']) {
    try { ({ mergeGeometries } = await import(aday)); break; } catch {}
  }
  assert.ok(mergeGeometries, 'BufferGeometryUtils bulunamadı');
  const ctx = { THREE, Math, console };
  vm.createContext(ctx);
  vm.runInContext(blok('GEO') + '\n;globalThis.__g = { binaGeometrisi };\n', ctx);
  vm.runInContext(blok('DILIMLE') + '\n;globalThis.__d = { dilimle };\n', ctx);
  const g = ctx.__g.binaGeometrisi([[0, 0], [8, 0], [8, 8], [0, 8]], 9);
  const duvar = ctx.__d.dilimle(g, 0);
  const cati = ctx.__d.dilimle(g, 1);
  assert.ok(duvar.attributes.position.count > 0);
  assert.ok(cati.attributes.position.count > 0);
  assert.equal(duvar.attributes.position.count + cati.attributes.position.count,
               g.attributes.position.count, 'tüm üçgenler kapsanmalı');
  const birlestir = mergeGeometries([duvar, duvar], false);
  assert.ok(birlestir && birlestir.attributes.position.count === duvar.attributes.position.count * 2);
});

test('pencereDokusu: tam bina ve karo tekrarı doğru', { skip: !THREE }, () => {
  const tuvalSahte = () => ({
    width: 0, height: 0,
    getContext: () => ({
      fillStyle: '', font: '',
      fillRect() {},
      measureText: () => ({ width: 10 }),
    }),
  });
  const ctx = { THREE, Math, console, Number, isNaN,
    document: { createElement: () => tuvalSahte() } };
  vm.createContext(ctx);
  vm.runInContext(blok('PENCERE-AYAR') + blok('PENCERE-DOKU') +
    '\n;globalThis.__pd = { pencereAyar, pencereDokusu, mulberry32 };\n', ctx);
  const { pencereAyar, pencereDokusu } = ctx.__pd;
  const a = pencereAyar(null);
  const tam = pencereDokusu(a, 7, 24, false);
  assert.ok(Math.abs(tam.repeat.x - 1 / a.kolonAralik) < 1e-9);
  assert.ok(Math.abs(tam.repeat.y - 1 / 24) < 1e-9);
  assert.ok(tam.image.height > 0 && tam.image.width > 0);
  const karo = pencereDokusu(a, 7, a.katAralik, true);
  assert.ok(Math.abs(karo.repeat.y - 1 / a.katAralik) < 1e-9, 'karo kat hizası');
  assert.ok(karo.image.height < tam.image.height, 'karo tek kat olmalı');
});
