// index.html içindeki işaretli blokları ve veri dosyalarını okur (test yardımcısı).
// Blok işaretleri: --AD-BASLA-- ... --AD-BIT--   (index.html'de; imzayı bozma)
import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';

export const KOK = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));
export const html = fs.readFileSync(path.join(KOK, 'index.html'), 'utf8');

export function blok(ad) {
  const bas = `// --${ad}-BASLA--`;
  const bit = `// --${ad}-BIT--`;
  const i = html.indexOf(bas);
  const j = html.indexOf(bit);
  if (i < 0 || j < 0 || j <= i) throw new Error(`Blok bulunamadı: ${ad}`);
  // Başlangıç işaretinin satır sonundan, bitiş işaretinin satır başına kadar al
  const basSon = html.indexOf('\n', i + bas.length);
  const bitBas = html.lastIndexOf('\n', j);
  if (basSon < 0 || bitBas <= basSon) throw new Error(`Blok satırları bozuk: ${ad}`);
  return html.slice(basSon + 1, bitBas + 1);
}

export function veriDosyasi(ad) {
  return fs.readFileSync(path.join(KOK, ad), 'utf8');
}

// binalar.js / cevre.js global listelerini güvenli şekilde yükler
import vm from 'node:vm';
const VERI_ADLARI = ['ONEMLI_BINALAR', 'ARKA_PLAN_BINALAR', 'PARKLAR', 'YOLLAR',
  'FISKIYELER', 'SPOR_ALANLARI', 'AGACLAR', 'ISLETMELER', 'OTOPARKLAR',
  'DURAKLAR', 'RAYLAR', 'GIRISLER', 'BAYRAKLAR'];

export function veriYukle() {
  const kaynak = veriDosyasi('binalar.js') + '\n' + veriDosyasi('cevre.js') +
    `\n;globalThis.__veri = { ${VERI_ADLARI.join(', ')} };\n`;
  const ctx = { console };
  vm.createContext(ctx);
  vm.runInContext(kaynak, ctx);
  return ctx.__veri;
}

// three varsa modülü döndürür; yoksa null (geometri testleri atlanır)
export async function threeYukle() {
  const adaylar = ['three', '/tmp/opencode/geo/node_modules/three/build/three.module.js'];
  for (const aday of adaylar) {
    try { return await import(aday); } catch {}
  }
  return null;
}
