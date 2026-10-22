// Arma con la lógica de app.js todas las horas de un tramo de fechas y las
// vuelca en JSON: lo que la app enseñaría, sección por sección.
//   node arma.js <raiz del proyecto> <desde> <hasta> <salida.json>
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const [raiz, desde, hasta, salida] = process.argv.slice(2);
const app = path.join(raiz, 'app');
const lee = (n) => JSON.parse(fs.readFileSync(path.join(app, 'datos', n), 'utf8'));

// un objeto que lo traga todo: el DOM no hace falta para armar una hora
const nada = new Proxy(function () {}, {
  get: (t, k) => k === Symbol.toPrimitive ? () => '' : (k === 'length' ? 0 : nada),
  apply: () => nada, construct: () => nada, set: () => true
});
const almacen = () => { const m = {}; return {
  getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); },
  removeItem: (k) => { delete m[k]; } }; };
const ctx = {
  console, document: nada, window: nada, navigator: {}, screen: {}, location: nada,
  localStorage: almacen(), sessionStorage: almacen(), matchMedia: () => ({ matches: false, addEventListener() {} }),
  setTimeout: () => 0, clearTimeout() {}, requestAnimationFrame: () => 0, fetch: () => Promise.reject(new Error('sin red')),
  Intl, Date, Math, JSON, Promise, Map, Set, Object, Array, String, Number, RegExp, Error,
  CSS: { supports: () => false }, history: nada, performance: { now: () => 0 }
};
ctx.globalThis = ctx;
vm.createContext(ctx);
let src = fs.readFileSync(path.join(app, 'app.js'), 'utf8');
src = src.replace(/\narranca\(\);\s*$/, '\n');
vm.runInContext(src + `
;globalThis.__api = { E, armaHora, celebracionesHoras, ordenDe };`, ctx, { filename: 'app.js' });
const { E, armaHora } = ctx.__api;
E.cal = lee('calendario.json');
E.horas = lee('horas.json');
E.horasDias = lee('horas_dias.json');
E.horas.comun_de['smv'] = ['santisima virgen maria'];
E.elecciones = {};
const HORAS = ['oficio', 'laudes', 'tercia', 'sexta', 'nona', 'visperas', 'completas'];
// cada texto se guarda una vez, y las secciones lo citan por su número
const textos = [], numDe = new Map();
const guarda = (c) => {
  if (!c) return -1;
  const j = JSON.stringify({ r: c.r || '', l: c.l || [], f: c.f || '' });
  if (!numDe.has(j)) { numDe.set(j, textos.length); textos.push(JSON.parse(j)); }
  return numDe.get(j);
};
const alts = (s) => s.alts.map((a) => [a.id, a.rot || '', guarda(a.c)]);
const out = {};
for (let t = new Date(desde + 'T12:00:00Z'); t <= new Date(hasta + 'T12:00:00Z'); t.setUTCDate(t.getUTCDate() + 1)) {
  const iso = t.toISOString().slice(0, 10);
  const dia = out[iso] = { d: E.horasDias.dias[iso] || null, horas: {} };
  for (const h of HORAS) {
    const base = armaHora(iso, h);
    if (!base) continue;
    dia.horas[h] = base.cels.ops.map((op) => {
      const o = op.id === base.op.id ? base : armaHora(iso, h, op.id);
      return {
        op: op.id, t: op.t, g: op.g, modo: op.modo, def: op.id === base.cels.def,
        secs: o.secciones.map((s) => {
          const x = { cl: s.cl, i: s.i, alts: alts(s) };
          if (s.formas) {
            x.modo = s.modo;
            x.formas = Object.fromEntries(Object.entries(s.formas)
              .map(([k, f]) => [k, { i: f.i, alts: alts(f) }]));
          }
          return x;
        })
      };
    });
  }
}
fs.writeFileSync(salida, JSON.stringify({ dias: out, textos }));
console.log('fechas', Object.keys(out).length);
