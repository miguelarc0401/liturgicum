/* Leccionario latino — la app entera, en un fichero y sin dependencias.
 *
 * No calcula nada del leccionario: todo viene resuelto y auditado desde el
 * proyecto (datos/lecturas_*.json, datos/indice.json, datos/calendario.json).
 * Aquí sólo se elige qué mostrar y se maqueta.
 *
 * Una nota sobre los acentos: el texto se empaqueta acentuado, porque quitar
 * un agudo es trivial y ponerlo costó toda una fase del proyecto. Apagar la
 * acentuación es descomponer en NFD y borrar el U+0301, lo que respeta la
 * diéresis (Israël) y la ligadura (æ), que no son acento.
 */
'use strict';

const RUTA_DATOS = 'datos/';
const POR_OMISION = {
  fuente: 'clementina', acentos: true, numeros: true, tam: 100, tema: 'auto',
  epifania: 'domingo', ascension: 'domingo', corpus: 'domingo',
  memorias: 'santo', inicio: 'menu', hLibre: 'santo', hComun: 'comun',
  hAntFinal: '', calAbre: 'misa',
  // el formato del texto (Ajustes, «Formato del texto»)
  letra: 'serif', interlinea: 'normal', medida: 'normal', justifica: 'si',
  particion: 'si', cruces: 'si', despierto: false,
  // al rezar (Ajustes, «Liturgia de las Horas»)
  carril: 'si', gestos: 'si', rezadas: 'si'
};

const E = {              // todo el estado de la app
  cfg: Object.assign({}, POR_OMISION),
  indice: null, cal: null, lecturas: null,
  horas: null, horasDias: null, hora: null,
  oficio: null,          // la hora que se está rezando, con sus opciones
  horasCel: null,        // la celebración elegida, cuando hay donde elegir
  elecciones: {},        // lo elegido en cada sección, mientras dura la sesión
  diaDe: new Map(),      // slug -> día del índice
  diaDeClave: new Map(), // clave de formulario -> día
  colorDe: new Map(),    // slug -> color litúrgico
  busqueda: null,
  rezadas: null,        // las horas que ya se han rezado hoy
  entraDesde: null,     // por qué lado entra la vista nueva, al deslizar
  vista: 'hoy',
  pos: {},               // vista -> {k, y}: dónde se dejó cada una
  claveVista: null,      // qué se está leyendo, para saber si es lo mismo
  ultimaMisa: null,      // la ruta de la misa que se leía
  calQ: ''               // lo que se busca en el calendario
};

const $ = (s) => document.querySelector(s);
const vista = $('#vista');

/* Los iconos, de trazo, del mismo juego que los de la barra (index.html):
 * un glifo de texto cambia de un teléfono a otro, un trazo no. */
const svg = (d) => '<svg viewBox="0 0 24 24" aria-hidden="true">' + d + '</svg>';
const ICONO = {
  buscar: svg('<circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/>'),
  cerrar: svg('<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>'),
  izq: svg('<path d="M14.5 5.5 8 12l6.5 6.5"/>'),
  der: svg('<path d="M9.5 5.5 16 12l-6.5 6.5"/>'),
  // la cruz del altar y el breviario abierto con su cinta
  misa: svg('<path d="M12 3v18M6.5 8.2h11"/>'),
  horas: svg('<path d="M12 7.3C10.2 5.9 7.4 5.5 4 5.9v12.4c3.4-.4 6.2.1 8 '
    + '1.5 1.8-1.4 4.6-1.9 8-1.5V5.9c-3.4-.4-6.2 0-8 1.4Z"/>'
    + '<path d="M12 7.3v12.5"/><path d="M15.2 5.6v5l1.6-1.3 1.6 1.3v-5"/>')
};

/* ------------------------------------------------------------ utilidades */
function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

/** Quita el acento agudo y deja intactas diéresis y ligaduras. */
function sinAcento(t) {
  return t.normalize('NFD').replace(/́/g, '').normalize('NFC');
}

/** Clave de búsqueda: sin ningún diacrítico, con æ/œ desatadas. */
function plano(t) {
  return t.normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/æ/g, 'ae').replace(/Æ/g, 'AE')
    .replace(/œ/g, 'oe').replace(/Œ/g, 'OE').toLowerCase();
}

/** Como plano(), pero guardando de qué letra del original sale cada letra.
 *  Hace falta para resaltar: «quaesumus» tiene una letra más que «quǽsumus»,
 *  así que la posición en el texto llano no sirve en el texto acentuado. */
function planoConMapa(t) {
  let p = '';
  const pos = [];
  for (let i = 0; i < t.length; i++) {
    const c = plano(t[i]);
    for (let k = 0; k < c.length; k++) pos.push(i);
    p += c;
  }
  pos.push(t.length);
  return [p, pos];
}

function tx(t) { return E.cfg.acentos ? t : sinAcento(t); }

function hoyISO() {
  const d = new Date();
  return [d.getFullYear(), d.getMonth() + 1, d.getDate()]
    .map((n, i) => i ? String(n).padStart(2, '0') : n).join('-');
}

function suma(iso, n) {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + n);
  return [d.getFullYear(), d.getMonth() + 1, d.getDate()]
    .map((v, i) => i ? String(v).padStart(2, '0') : v).join('-');
}

function fechaLarga(iso, semana) {
  const d = new Date(iso + 'T12:00:00');
  const s = d.toLocaleDateString('es', {
    weekday: semana || 'long', day: 'numeric', month: 'long', year: 'numeric'
  });
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** La fecha abreviada —«jue, 1 oct»— para la cabecera resumida, que la
 *  lleva en un solo renglón con la hora y la celebración. */
function fechaCorta(iso) {
  const d = new Date(iso + 'T12:00:00');
  const o = { weekday: 'short', day: 'numeric', month: 'short' };
  if (iso.slice(0, 4) !== hoyISO().slice(0, 4)) o.year = 'numeric';
  return d.toLocaleDateString('es', o).replace(/\.(?=,|$| )/g, '');
}

/** La fecha de la cabecera, entera: el botón «Hoy» ya no le quita sitio
 *  —flota sobre el texto—, así que no hay que abreviarla nunca. */
function rotuloFecha(iso) { return fechaLarga(iso); }

/** El rótulo de la fecha, con su forma corta a cuestas (la usa la cabecera
 *  resumida, que la saca con `content: attr(data-corta)`). */
function ponFecha(iso) {
  const r = $('#rotulo-fecha');
  r.textContent = rotuloFecha(iso);
  r.dataset.corta = fechaCorta(iso);
  $('#selector-fecha').value = iso;
}

/* --------------------------------------------- volver donde se estaba
 * Quien sale de Laudes al calendario y vuelve, vuelve al mismo renglón. Se
 * recuerda una posición por vista, con la clave de lo que se leía en ella:
 * otro día, otra hora u otra celebración la cambian, y entonces se empieza
 * arriba. Vive en memoria, así que cerrar la app la olvida. */
function claveVista() {
  if (E.vista === 'horas') {
    return [E.fecha, E.hora, E.oficio ? E.oficio.op.id : ''].join('|');
  }
  return location.hash;
}

/** Antes de cambiar de vista: lo que se deja, dónde se deja. */
function guardaPosicion() {
  if (E.vista && E.claveVista) {
    E.pos[E.vista] = { k: E.claveVista, y: window.scrollY };
  }
  E.donde = dondeIba();
}

/* Pasar de Laudes a Vísperas, o del oficio del santo al de la feria, no es
 * empezar de nuevo: es seguir rezando. Así que no se vuelve al principio,
 * se vuelve al mismo sitio —a la misma sección y a la misma altura dentro
 * de ella—, que es donde estaba el ojo. */
function dondeIba() {
  if (E.vista !== 'horas') return null;
  const corte = $('#cabecera').getBoundingClientRect().bottom;
  let cual = null;
  document.querySelectorAll('#vista .hora-sec').forEach((x) => {
    if (x.getBoundingClientRect().top <= corte + 4) cual = x;
  });
  if (!cual) return null;
  return { fecha: E.fecha, cl: cual.dataset.cl,
    dentro: corte - cual.getBoundingClientRect().top };
}

function vuelveADonde(d) {
  if (!d || d.fecha !== E.fecha) return false;
  const s = document.querySelector('#vista .hora-sec[data-cl="' + d.cl + '"]');
  if (!s) return false;
  const corte = $('#cabecera').getBoundingClientRect().bottom;
  window.scrollTo(0, Math.max(0, window.scrollY
    + s.getBoundingClientRect().top - corte + d.dentro));
  return true;
}

/** La vista nueva entra subiendo un pelo. Se reinicia el animación a mano
 *  —quitar la clase, forzar el reflujo, volver a ponerla— porque el elemento
 *  es siempre el mismo y el navegador, si no, no vuelve a arrancarla. */
function entraVista() {
  const dir = E.entraDesde;
  E.entraDesde = null;
  vista.classList.remove('entra', 'entra-izq', 'entra-der');
  void vista.offsetWidth;
  vista.classList.add(dir ? 'entra-' + dir : 'entra');
}

/** Después de pintar una vista: si es la misma que se dejó, al mismo sitio;
 *  si no, arriba (o donde diga `siNo`, que devuelve false si no hizo nada). */
function colocaPosicion(siNo) {
  entraVista();
  E.claveVista = claveVista();
  const p = E.pos[E.vista];
  if (p && p.k === E.claveVista) {
    window.scrollTo(0, p.y);
    return;
  }
  if (!siNo || siNo() === false) window.scrollTo(0, 0);
}

/* -------------------------------------------------------------- ajustes */
function cargaCfg() {
  try {
    Object.assign(E.cfg, JSON.parse(localStorage.getItem('cfg') || '{}'));
  } catch (_) { /* almacenamiento bloqueado: se usan los valores de fábrica */ }
}
function guardaCfg() {
  try { localStorage.setItem('cfg', JSON.stringify(E.cfg)); } catch (_) {}
}
function aplicaCfg() {
  const b = document.body.dataset;
  b.tema = E.cfg.tema;
  b.letra = E.cfg.letra;
  b.interlinea = E.cfg.interlinea;
  b.medida = E.cfg.medida;
  b.justifica = E.cfg.justifica;
  b.particion = E.cfg.particion;
  b.cruces = E.cfg.cruces;
  document.documentElement.style.setProperty(
    '--cuerpo', (E.cfg.tam / 100 * 1.0625).toFixed(3) + 'rem');
  velaPantalla();
}

/* La pantalla, despierta mientras se reza: un oficio son diez o quince
 * minutos de lectura sin tocar nada, y el teléfono se apaga a la mitad. El
 * permiso lo da el sistema y se pierde al pasar la app a segundo plano, así
 * que se vuelve a pedir al volver. Donde no exista, el ajuste no se ofrece. */
let _vela = null;
async function velaPantalla() {
  if (!('wakeLock' in navigator)) return;
  if (E.cfg.despierto && !_vela && !document.hidden) {
    try {
      _vela = await navigator.wakeLock.request('screen');
      _vela.addEventListener('release', () => { _vela = null; });
    } catch (_) { _vela = null; }
  } else if (!E.cfg.despierto && _vela) {
    try { await _vela.release(); } catch (_) { /* ya estaba suelto */ }
    _vela = null;
  }
}

/* --------------------------------------------------------------- datos */
async function json(nombre) {
  const r = await fetch(RUTA_DATOS + nombre, { cache: 'no-cache' });
  if (!r.ok) throw new Error(nombre + ': ' + r.status);
  return r.json();
}

async function cargaLecturas(fuente) {
  if (E.lecturas && E.lecturas.fuente === fuente) return;
  E.lecturas = await json('lecturas_' + fuente + '.json');
  E.busqueda = null;
}

function indexaIndice() {
  for (const sec of E.indice.secciones) {
    for (const g of sec.g) {
      for (const d of g.d) {
        d._sec = sec.t; d._grp = g.t;
        E.diaDe.set(d.s, d);
        // el santoral trae su propio color (rojo los mártires, los apóstoles
        // y la Santa Cruz); el tiempo, el de su sección
        E.colorDe.set(d.s, d.c || sec.c);
        for (const b of d.b) if (!E.diaDeClave.has(b.k)) E.diaDeClave.set(b.k, d);
      }
    }
  }
}

/* ------------------------------------------------- el calendario del año */
/** Celebraciones de una fecha, con los parches regionales ya aplicados.
 *  {c: [[slug, bloque, meta], …], o: [{t, g}, …]}  — 'o', lo que se omite. */
function entradasDe(iso) {
  let e = E.cal.fechas[iso];
  for (const p of Object.values(E.cal.parches)) {
    if (E.cfg[p.opcion] === p.valor && Object.prototype.hasOwnProperty
      .call(p.fechas, iso)) e = p.fechas[iso];
  }
  return (e && e.c && e.c.length) ? e : null;
}

let _anios = null;
function anioDe(iso) {
  if (!_anios) {
    _anios = Object.entries(E.cal.anios)
      .map(([a, m]) => Object.assign({ anio: +a }, m))
      .sort((x, y) => x.inicio < y.inicio ? -1 : 1);
  }
  let hallado = null;
  for (const a of _anios) { if (a.inicio <= iso) hallado = a; else break; }
  return hallado;
}

/* ------------------------------------------------- maquetar un formulario */
function versos(tramos, sep, castellano) {
  return tramos.map((tr) => {
    // los apéndices traen algún texto sin número de versículo (las antífonas
    // «O», las aclamaciones) y alguno en castellano (las respuestas
    // salmódicas, que el leccionario da sin cita y no hay de dónde traducir)
    const t = tr.map(([n, s]) => ((E.cfg.numeros && n)
      ? '<sup>' + esc(n) + '</sup>' : '')
      + esc(castellano ? s : tx(s))).join(' ');
    return '<p class="' + (sep ? 'estrofa' : 'texto') + '">' + t + '</p>';
  }).join(sep || '<p class="omision">[…]</p>');
}

function pintaLectura(l) {
  const h = ['<section class="lect">'];
  if (l.t) h.push('<h3 class="rubrica">' + esc(l.es ? l.t : tx(l.t)) + '</h3>');
  if (l.f) {
    h.push('<p class="formula">' + esc(tx(l.f))
      + '<span class="cita">' + esc(l.c) + '</span></p>');
  } else if (l.c) {
    h.push('<p class="formula"><span class="cita">' + esc(l.c)
      + '</span></p>');
  }
  if (l.k === 'salmo') {
    if (l.r) h.push('<p class="antifona">℟. ' + esc(tx(l.r)) + '</p>');
    else if (l.rr) h.push('<p class="antifona">℟. (' + esc(l.rr) + ')</p>');
    h.push(versos(l.g, '<p class="resp">℟.</p>', l.es));
    h.push('<p class="resp">℟.</p>');
  } else {
    h.push(versos(l.g, null, l.es));
    if (l.k === 'lectura') {
      h.push('<p class="cierre">' + esc(tx(E.lecturas.cierre)) + '</p>');
    }
  }
  return h.join('') + '</section>';
}

/** Las celebraciones de una fecha, ya ordenadas por preferencia.
 *
 *  El orden viene hecho de casa: lo calcula src/18_santoral.py con la Tabla de
 *  los días litúrgicos, que es la que resuelve la concurrencia. Aquí sólo se
 *  aplica la única preferencia que es del lector y no del libro: si en las
 *  memorias quiere la lectura continua de la feria (que es lo que prescribe el
 *  Ordo lectionum Missae, n. 82, salvo lecturas propias) o la del santo.
 */
function celebracionesDe(val, iso) {
  const cs = [];
  val.c.forEach(([slug, bloque, m], i) => {
    const d = E.diaDe.get(slug);
    if (d) cs.push({ slug: slug, bloque: bloque, dia: d, m: m, orden: i });
  });
  if (cabeSantaMariaMisa(iso, cs)) {
    const d = E.diaDe.get(COMUN_SMV);
    if (d) {
      cs.push({ slug: COMUN_SMV, bloque: 0, dia: d, orden: 99,
        m: { t: SMV.t, g: 'Memoria libre', k: 's', smv: 1,
          n: 'los sábados del tiempo ordinario en que no hay memoria '
            + 'obligatoria puede celebrarse la memoria de Santa María '
            + 'Virgen, con las lecturas del Común de la Virgen' } });
    }
  }
  if (E.cfg.memorias === 'feria' && cs.length > 1
      && cs[0].m.k === 's' && cs[0].m.r >= 10) {
    const i = cs.findIndex((c) => c.m.f && !c.m.z);
    if (i > 0) cs.unshift(cs.splice(i, 1)[0]);
  }
  return cs;
}

/* El sábado de Santa María, también en la misa: el Misal la pone los
 * sábados del tiempo ordinario libres de memoria obligatoria, y sus
 * lecturas son las del Común de la Virgen, que es a donde lleva. */
const COMUN_SMV = 'lv_5224comsvi';

function cabeSantaMariaMisa(iso, cs) {
  if (!iso || !cs.length || new Date(iso + 'T12:00:00').getDay() !== 6) {
    return false;
  }
  if (cs[0].m.k !== 't' || cs[0].dia._sec !== 'TIEMPO ORDINARIO') return false;
  return !cs.some((c) => c.m.k === 's' && /^memoria$/i.test(c.m.g || ''));
}

/** Nombre corto para el chip: lo que va antes de la primera coma. */
/* El color de las fiestas de la Virgen. El libro dice blanco, pero la
 * costumbre —y en México la de Guadalupe sobre todas— lo quiere azul, y la
 * Santa Sede lo concede a España y a sus antiguos reinos. Se reconoce por
 * el nombre, con una lista cerrada: «santa María Magdalena» empieza igual
 * que «santa María Virgen» y no es de la Virgen. */
const DE_LA_VIRGEN = new RegExp([
  'santisima virgen maria', 'nuestra senora', 'santa maria virgen',
  'santa maria madre', 'inmaculada concepcion', 'inmaculado corazon',
  'la asuncion de la', 'la natividad de la santisima',
  'la visitacion de la santisima', 'la presentacion de la santisima',
  'maria madre de la iglesia', 'la virgen maria', 'santa maria en sabado'
].join('|'));

function esDeLaVirgen(titulo) {
  return DE_LA_VIRGEN.test(plano(titulo || ''));
}

function corto(t) {
  const s = t.split(/,| · /)[0];
  return s.length > 34 ? s.slice(0, 33) + '…' : s;
}

function pintaChipsCelebraciones(cels, slug) {
  const c = $('#celebraciones');
  if (cels.length < 2) { c.innerHTML = ''; return; }
  c.innerHTML = cels.map((o) =>
    '<button aria-pressed="' + (o.slug === slug) + '"'
    + (o.m.z ? ' class="apagado"' : '')
    + ' data-slug="' + esc(o.slug) + '" data-bloque="' + o.bloque + '">'
    + esc(corto(o.m.t))
    + (o.m.g ? '<small>' + esc(o.m.g) + '</small>' : '')
    + (o.m.z ? '<small>no se celebra</small>' : '')
    + '</button>').join('');
}

function pintaChipsFormularios(d, bloque) {
  const c = $('#formularios');
  c.className = 'chips finos';
  if (!d || d.b.length < 2) { c.innerHTML = ''; return; }
  c.innerHTML = d.b.map((b, i) =>
    '<button aria-pressed="' + (i === bloque) + '" data-slug="' + esc(d.s)
    + '" data-bloque="' + i + '">' + esc(b.e || ('Formulario ' + (i + 1)))
    + '</button>').join('');
}

function pintaNota(cel, val) {
  const n = [];
  if (cel && cel.m) {
    if (cel.m.x) n.push('Trasladada del ' + fechaLarga(cel.m.x).toLowerCase()
      + ', impedida por una celebración de mayor precedencia.');
    if (cel.m.n) n.push(cel.m.n.charAt(0).toUpperCase() + cel.m.n.slice(1)
      + '.');
    if (cel.m.z) n.push('Este año no se celebra: lo impide '
      + 'una celebración de mayor precedencia. Sus lecturas se muestran '
      + 'porque son las del ciclo.');
  }
  if (val && val.o && val.o.length) {
    n.push('Se omite este año: ' + val.o.map((x) =>
      x.t + (x.g ? ' (' + x.g.toLowerCase() + ')' : '')).join('; ') + '.');
  }
  const p = $('#nota-dia');
  p.innerHTML = n.map(esc).join(' ');
  p.style.display = n.length ? '' : 'none';
}

function pintaFormulario(slug, bloque, iso, cels, val) {
  const d = E.diaDe.get(slug);
  if (!d) { vista.innerHTML = '<p class="aviso">No encuentro ese día.</p>'; return; }
  if (bloque >= d.b.length || bloque < 0) bloque = 0;
  const b = d.b[bloque];
  const lects = b && E.lecturas.bloques[b.k];
  const cel = (cels || []).find((o) => o.slug === slug);
  document.body.dataset.color = (cel && cel.m.smv) || esDeLaVirgen(d.t)
    ? 'azul' : E.colorDe.get(slug) || 'neutro';
  // el común se titula a sí mismo «Leccionario V…»: cuando se abre como la
  // misa de Santa María en sábado, el título es el de la celebración
  $('#titulo-dia').textContent = (cel && cel.m.smv) ? cel.m.t : d.t;
  const sec = d._sec.toLowerCase();
  const partes = [];
  if (d.g) partes.push(d.g);
  partes.push(sec.charAt(0).toUpperCase() + sec.slice(1));
  if (iso) {
    const a = anioDe(iso);
    if (a) partes.push('Ciclo ' + a.ciclo + ' · Año ' + a.ferial);
  }
  if (d.b.length === 1 && d.b[0].e && d.b[0].e !== 'Propio') {
    partes.push(d.b[0].e);
  }
  $('#subtitulo-dia').textContent = partes.join(' · ');
  pintaChipsCelebraciones(cels || [], slug);
  pintaChipsFormularios(d, bloque);
  pintaNota(cel, val);
  if (!lects) {
    vista.innerHTML = '<p class="aviso">Este formulario no está en '
      + esc(E.lecturas.fuente) + '.</p>';
    return;
  }
  vista.innerHTML = lects.map(pintaLectura).join('');
  if (iso) { E.ultimaMisa = location.hash; cabeceraFija(true); }
  colocaPosicion();
}

/** El botón «Hoy» sale sólo cuando se está en otro día. */
function marcaHoy(iso) {
  $('#ir-hoy').hidden = !iso || iso === hoyISO();
}

/* ------------------------------------------------------------ las vistas */
function verDia(iso, slug, bloque) {
  E.vista = 'hoy';
  marcaBarra('hoy');
  $('#cabecera').classList.remove('compacta', 'portada');
  limpiaCabExtra();
  ponFecha(iso);
  E.fecha = iso;
  marcaHoy(iso);
  const val = entradasDe(iso);
  if (!val) {
    document.body.dataset.color = 'neutro';
    $('#titulo-dia').textContent = 'Sin formulario';
    $('#subtitulo-dia').textContent = '';
    $('#celebraciones').innerHTML = '';
    $('#formularios').innerHTML = '';
    $('#nota-dia').style.display = 'none';
    vista.innerHTML = '<p class="aviso">Esta fecha cae fuera del calendario '
      + 'que trae la app (' + E.cal.rango[0] + '–' + E.cal.rango[1] + ').</p>';
    return;
  }
  const cels = celebracionesDe(val, iso);
  if (!cels.length) { vista.innerHTML = '<p class="aviso">Nada que mostrar.</p>'; return; }
  let s = slug, b = bloque;
  const cel = cels.find((o) => o.slug === s);
  if (!cel) { s = cels[0].slug; b = cels[0].bloque; }
  else if (b === undefined) b = cel.bloque;
  pintaFormulario(s, b, iso, cels, val);
}

/** Lo que una vista deja en la cabecera —la barra resumida del calendario,
 *  el renglón resumido de las horas— no es de las demás: se quita al
 *  entrar en cualquiera. */
function limpiaCabExtra() {
  $('#cab-extra').innerHTML = '';
  $('#cabecera').classList.remove('cal-pegada');
  cabeceraFija(false);
  limpiaCarril();
}

/* --------------------------------------------- la cabecera, al bajar
 * La cabecera se pliega siguiendo el dedo. `--pliegue` va de 0 a 1 según lo
 * que se lleve bajado, y con esa variable la hoja de estilo calcula todo lo
 * que la cabecera mide: no hay dos estados y un salto entre ellos, sino un
 * movimiento, y al subir vuelve por donde vino.
 *
 * Mientras eso puede pasar, la cabecera va `fixed` y su sitio lo guarda un
 * relleno del <body> del alto de la cabecera entera. Así cambiar de alto no
 * cambia el flujo, y el texto que se está leyendo no da un salto a media
 * oración (que es lo que haría con la cabecera pegada: al encogerse, todo
 * lo de debajo subiría de golpe). */
const PLIEGUE = 130;        // píxeles de dedo que la pliegan del todo
let _altoCab = 0, _ultimoY = 0, _plegado = 0, _midiendoCab = false;

function ponPliegue(p) {
  _plegado = p;
  $('#cabecera').style.setProperty('--pliegue', p.toFixed(3));
}

/** Los dos altos de la cabecera, entera y plegada: el primero guarda su
 *  sitio en el <body>, el segundo le dice al carril dónde dejar la sección
 *  a la que salta. Se mide sin transiciones, para que medir no se vea. */
function mideCabecera() {
  const cab = $('#cabecera');
  const est = document.documentElement.style;
  const antes = _plegado;
  cab.classList.add('midiendo');
  ponPliegue(0);
  _altoCab = cab.offsetHeight;
  ponPliegue(1);
  const altoMin = cab.offsetHeight;
  ponPliegue(antes);
  cab.classList.remove('midiendo');
  est.setProperty('--alto-cab', _altoCab + 'px');
  est.setProperty('--alto-cab-min', altoMin + 'px');
}

/** Enciende o apaga el pliegue. Se llama con la cabecera ya pintada: su
 *  alto entero es el que guarda el sitio. */
function cabeceraFija(si) {
  const cab = $('#cabecera');
  if (!si) {
    document.body.classList.remove('cab-fija');
    cab.style.removeProperty('--pliegue');
    document.documentElement.style.removeProperty('--alto-cab');
    document.documentElement.style.removeProperty('--alto-cab-min');
    _altoCab = 0; _plegado = 0;
    return;
  }
  document.body.classList.add('cab-fija');
  ponPliegue(0);
  mideCabecera();
  _ultimoY = Math.max(0, window.scrollY);
  alDesplazarCabecera();
}

/** Al bajar se pliega, al subir se despliega, y en la misma proporción en
 *  que se mueve el dedo. Nunca más plegada de lo que da lo bajado, para que
 *  al principio de la página no se abra un hueco entre ella y el texto. */
function alDesplazarCabecera() {
  if (!document.body.classList.contains('cab-fija') || _midiendoCab) return;
  _midiendoCab = true;
  requestAnimationFrame(() => {
    _midiendoCab = false;
    if (!document.body.classList.contains('cab-fija')) return;
    const y = Math.max(0, window.scrollY);
    const d = y - _ultimoY;
    _ultimoY = y;
    if (Date.now() < _saltoHasta) return;
    const p = Math.max(0, Math.min(1, _plegado + d / PLIEGUE, y / PLIEGUE));
    if (Math.abs(p - _plegado) > 0.002) ponPliegue(p);
  });
}

function modoPanel(titulo) {
  $('#cabecera').classList.add('compacta');
  $('#cabecera').classList.remove('portada');
  limpiaCabExtra();
  marcaHoy(null);
  $('#titulo-dia').textContent = titulo;
  $('#subtitulo-dia').textContent = '';
  $('#celebraciones').innerHTML = '';
  $('#formularios').innerHTML = '';
  $('#nota-dia').style.display = 'none';
  document.body.dataset.color = 'neutro';
}

function verIndice() {
  E.vista = 'indice';
  // el índice se abre desde el calendario, y es allí donde se vuelve
  marcaBarra('calendario');
  modoPanel('Índice del leccionario');
  // el buscador del latín salió de la barra de abajo: es cosa del
  // leccionario, y aquí está a mano de quien lo hojea
  const h = ['<a class="enlace-buscar" href="#/buscar">' + ICONO.buscar
    + 'Buscar en el latín del leccionario</a>'];
  E.indice.secciones.forEach((sec, i) => {
    h.push('<details class="sec"' + (i === 0 ? ' open' : '')
      + '><summary>' + esc(sec.t) + '</summary>');
    for (const g of sec.g) {
      h.push('<div class="grupo">');
      if (g.t) h.push('<h3>' + esc(g.t) + '</h3>');
      h.push('<div class="dias">' + g.d.map((d) =>
        '<a href="#/f/' + encodeURIComponent(d.s) + '">' + esc(d.i)
        + '</a>').join('') + '</div></div>');
    }
    h.push('</details>');
  });
  vista.innerHTML = h.join('');
  colocaPosicion();
}

/* ------------------------------------------------- el calendario del año
 * Lo que se celebra cada día del año civil, con su grado, del mismo
 * calendario que siguen la misa y las horas (precedencia ya resuelta en
 * src/18_santoral.py, parches regionales de Ajustes aplicados). Un toque en
 * un día lo abre en la misa o en las horas, lo que se haya elegido arriba. */
const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
  'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
const DSEM = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];

/** El grado de una celebración. Los santos lo traen; el de los días del
 *  tiempo se deduce de su lugar en la Tabla de los días litúrgicos. */
function gradoCal(m) {
  if (m.g) return m.g;
  const r = m.r || 99, t = m.t || '';
  if (r === 1) return 'Triduo pascual';
  if ((r === 2 || r === 6) && /^(Domingo|Segundo domingo)/i.test(t)) return 'Domingo';
  if (r <= 4) {
    if (/Ceniza/i.test(t)) return 'Feria privilegiada';
    if (/octava de Pascua/i.test(t)) return 'Octava de Pascua';
    if (/Santo\b|Semana Santa/i.test(t)) return 'Semana Santa';
    return 'Solemnidad';
  }
  if (r <= 8) return 'Fiesta';
  if (r === 9) {
    if (/octava/i.test(t)) return 'Octava de Navidad';
    if (/diciembre/i.test(t)) return 'Feria mayor de Adviento';
    return 'Feria de Cuaresma';
  }
  if (/Adviento/i.test(t)) return 'Feria de Adviento';
  if (/Pascua/i.test(t)) return 'Feria de Pascua';
  if (/enero|Epifan|Navidad/i.test(t)) return 'Feria de Navidad';
  return 'Feria';
}

/** La clase del grado, para el color de su rótulo. */
function claseGrado(g) {
  if (/^(Solemnidad|Triduo|Octava de Pascua|Conmemoración)/.test(g)) return 's';
  if (/^Fiesta/.test(g)) return 'f';
  if (/^Domingo/.test(g)) return 'd';
  if (g === 'Memoria') return 'm';
  if (g === 'Memoria libre') return 'ml';
  if (/privilegiada|mayor|Cuaresma|Semana Santa|Octava/.test(g)) return 'fp';
  return 'fe';
}

/** El nombre del día para el calendario: el de la celebración, salvo cuando
 *  el leccionario lo nombra por la misa («Misa del día»). */
function tituloCal(slug, m) {
  const d = E.diaDe.get(slug);
  if (/^Vigilia pascual/.test(m.t)) return 'Sábado santo · Vigilia pascual';
  if (/^Misa\b/.test(m.t)) {
    if (/Pascua/.test(m.t)) return 'Domingo de Pascua de la Resurrección del Señor';
    if (d && d._grp) return d._grp;
  }
  // «7 de enero — Lunes después de Epifanía»: lo que dice qué día es va
  // detrás; «Jueves Santo — Misa Crismal»: va delante
  const p = m.t.split(/\s+—\s+/);
  return p.length > 1 && /^\d+ de \w+$/.test(p[0]) ? p[1] : p[0];
}

function filaCal(iso, hoy) {
  const val = entradasDe(iso);
  const d = new Date(iso + 'T12:00:00');
  const ds = d.getDay();
  const abre = E.cfg.calAbre === 'horas' ? '#/h/' : '#/d/';
  const num = '<span class="cal-num">' + d.getDate() + '<small>'
    + DSEM[ds] + '</small></span>';
  if (!val) {
    return '<div class="cal-dia vacio">' + num + '<span class="cal-txt">'
      + '<span class="cal-t">—</span></span></div>';
  }
  // las que se celebran, sin repetir el día (Navidad trae tres misas)
  const vistas = new Set();
  const cs = [];
  let vigilia = null;
  for (const [slug, , m] of val.c) {
    if (m.z) continue;
    // la misa vespertina de la vigilia (Nochebuena) no es el día: el 24 es
    // feria de Adviento, y la Natividad empieza por la tarde
    if (/^Misa de la vigilia/.test(m.t) && val.c.length > 1) {
      const d = E.diaDe.get(slug);
      vigilia = d && d._grp ? d._grp : m.t;
      continue;
    }
    const t = tituloCal(slug, m);
    if (vistas.has(t)) continue;
    vistas.add(t);
    cs.push({ slug: slug, m: m, t: t, g: gradoCal(m) });
  }
  if (!cs.length) return '';
  const p = cs[0];
  const color = E.colorDe.get(p.slug) || 'neutro';
  // lo que encuentra el buscador: todo lo que se celebra o se puede
  // celebrar ese día, y lo que se omite, sin acentos
  const q = plano(cs.map((o) => o.t + ' ' + o.g).concat(
    (val.o || []).map((x) => x.t), vigilia ? [vigilia] : []).join(' · '));
  const h = ['<a class="cal-dia' + (ds === 0 ? ' domingo' : '')
    + (iso === hoy ? ' hoy' : '') + '"' + (iso === hoy ? ' id="cal-hoy"' : '')
    + ' href="' + abre + iso + '" data-color="' + color + '" data-q="'
    + esc(q) + '">', num,
    '<span class="cal-txt"><span class="cal-t">' + esc(p.t) + '</span>',
    '<span class="cal-g g-' + claseGrado(p.g) + '">'
    + esc(p.g) + '</span>'];
  // Lo que se puede elegir en vez de lo primero: en una memoria libre, las
  // otras memorias libres o la feria; en una feria privilegiada, la memoria
  // sólo como conmemoración. Una memoria obligatoria no deja elegir.
  if (p.g === 'Memoria libre') {
    const otras = cs.slice(1, 4).map((o) => o.t + ' · ' + o.g.toLowerCase());
    if (otras.length) {
      h.push('<span class="cal-o">o ' + otras.map(esc).join('; o ') + '</span>');
    }
  } else if (p.m.k === 't' && p.m.r === 9) {
    const cm = cs.slice(1).filter((o) => o.m.k === 's');
    if (cm.length) {
      h.push('<span class="cal-o">Conmemoración: ' + cm.map((o) =>
        esc(o.t)).join('; ') + '</span>');
    }
  }
  if (vigilia) {
    h.push('<span class="cal-o">Por la tarde, misa de la vigilia: '
      + esc(vigilia) + '</span>');
  }
  if (val.o && val.o.length) {
    h.push('<span class="cal-o omite">Se omite: ' + val.o.map((x) => esc(x.t)
      + (x.g ? ' (' + esc(x.g.toLowerCase()) + ')' : '')).join('; ') + '</span>');
  }
  h.push('</span></a>');
  return h.join('');
}

function verCalendario(anio) {
  E.vista = 'calendario';
  marcaBarra('calendario');
  const hoy = hoyISO();
  const [min, max] = E.cal.rango;
  anio = Math.min(max, Math.max(min, +anio || +hoy.slice(0, 4)));
  modoPanel('Calendario litúrgico');
  // el ciclo dominical y el año ferial cambian el primer domingo de Adviento
  const ciclos = [];
  for (const iso of [anio + '-01-01', anio + '-12-31']) {
    const a = anioDe(iso);
    if (a && !ciclos.some((c) => c.inicio === a.inicio)) ciclos.push(a);
  }
  const diaYMes = (iso) => {
    const d = new Date(iso + 'T12:00:00');
    return d.getDate() + ' de ' + MESES[d.getMonth()].toLowerCase();
  };
  const ciclo = ciclos.map((a, i) => (i ? 'desde el ' + diaYMes(a.inicio)
    + ': ' : (ciclos.length > 1 ? 'hasta el ' + diaYMes(suma(ciclos[1].inicio, -1)) + ': ' : ''))
    + 'ciclo ' + a.ciclo + ', año ' + a.ferial).join(' · ');
  const h = [
    '<div class="cal-cab">',
    '<div class="cal-anio">',
    anio > min ? '<button type="button" data-anio="' + (anio - 1)
      + '" aria-label="Año anterior">‹</button>' : '<span></span>',
    '<h2>' + anio + '</h2>',
    anio < max ? '<button type="button" data-anio="' + (anio + 1)
      + '" aria-label="Año siguiente">›</button>' : '<span></span>',
    '</div>',
    '<p class="cal-ciclo">' + esc(ciclo.charAt(0).toUpperCase() + ciclo.slice(1))
      + '</p>',
    '<label class="cal-busca">' + ICONO.buscar
      + '<input type="search" id="cal-q" autocomplete="off" '
      + 'enterkeyhint="search" spellcheck="false" '
      + 'placeholder="Buscar un santo o una fiesta" '
      + 'aria-label="Buscar una celebración en el calendario" value="'
      + esc(E.calQ) + '">'
      + '<button type="button" class="cal-borra" data-borra="1" '
      + 'aria-label="Borrar la búsqueda">' + ICONO.cerrar + '</button></label>',
    '<p class="cal-res" id="cal-res" aria-live="polite"></p>',
    '<div class="cal-ctl"><span class="cal-et">Al tocar un día, abrir</span>'
      + '<div class="alterna" role="group" aria-label="Al tocar un día, abrir">'
      + [['misa', 'Misa'], ['horas', 'Horas']].map(([v, t]) =>
        '<button type="button" data-abre="' + v + '" aria-pressed="'
        + (E.cfg.calAbre === v) + '">' + t + '</button>').join('')
      + '</div></div>',
    '<nav class="cal-meses" aria-label="Meses">' + MESES.map((m, i) =>
      '<button type="button" data-mes="' + i + '">' + m.slice(0, 3)
      + '</button>').join('') + '</nav>',
    '</div>'
  ];
  for (let mes = 0; mes < 12; mes++) {
    h.push('<section class="cal-mes" id="cal-mes-' + mes + '"><h3>'
      + MESES[mes] + ' <small>' + anio + '</small></h3>');
    const dias = new Date(anio, mes + 1, 0).getDate();
    for (let dia = 1; dia <= dias; dia++) {
      h.push(filaCal(anio + '-' + String(mes + 1).padStart(2, '0') + '-'
        + String(dia).padStart(2, '0'), hoy));
    }
    h.push('</section>');
  }
  h.push('<p class="aviso cal-nada" id="cal-nada" hidden></p>');
  h.push('<p class="pie cal-pie">Calendario general romano y latinoamericano, '
    + 'con la concurrencia resuelta por la Tabla de los días litúrgicos. '
    + '<a href="#/indice">Índice del leccionario</a> (formularios, apéndices, '
    + 'misas votivas y rituales).</p>');
  vista.innerHTML = h.join('');
  pintaBarraCal(anio, min, max);
  // los rótulos de mes se quedan pegados bajo la cabecera, que también lo está
  document.documentElement.style.setProperty('--alto-cabecera',
    $('#cabecera').offsetHeight + 'px');
  if (E.calQ) filtraCalendario(E.calQ);
  colocaPosicion(() => {
    const marcado = !E.calQ && document.getElementById('cal-hoy');
    if (!marcado) return false;
    marcado.scrollIntoView({ block: 'center' });
  });
  alDesplazarCalendario();
}

/* La cabecera del calendario se queda arriba al bajar por el año, pero
 * resumida: el año con sus flechas, los meses en una tira y la lupa. Ocupa
 * el sitio del título, que a esa altura ya no dice nada, de modo que la
 * cabecera no cambia de alto y la página no salta. */
function pintaBarraCal(anio, min, max) {
  const flecha = (a, dir) => (a < min || a > max)
    ? '<span class="mini-hueco"></span>'
    : '<button type="button" data-anio="' + a + '" aria-label="Año '
      + (dir < 0 ? 'anterior' : 'siguiente') + '">'
      + (dir < 0 ? ICONO.izq : ICONO.der) + '</button>';
  $('#cab-extra').innerHTML = '<div class="mini-cal" aria-label="Calendario '
    + anio + '">'
    + '<div class="mini-anio">' + flecha(anio - 1, -1) + '<span>' + anio
    + '</span>' + flecha(anio + 1, 1) + '</div>'
    + '<div class="mini-meses">' + MESES.map((m, i) => '<button type="button" '
      + 'data-mes="' + i + '" aria-label="' + m + '">' + m.slice(0, 3)
      + '</button>').join('') + '</div>'
    + '<button type="button" class="mini-lupa" data-lupa="1" '
    + 'aria-label="Buscar en el calendario">' + ICONO.buscar + '</button>'
    + '</div>';
}

/** Al bajar: se pega la barra resumida cuando la cabecera grande ya no se
 *  ve, y se marca en ella el mes que se está leyendo. */
let _desplazando = false;
function alDesplazarCalendario() {
  if (E.vista !== 'calendario' || _desplazando) return;
  _desplazando = true;
  requestAnimationFrame(() => {
    _desplazando = false;
    if (E.vista !== 'calendario') return;
    const cab = document.querySelector('.cal-cab');
    const alto = $('#cabecera').offsetHeight;
    if (!cab) return;
    $('#cabecera').classList.toggle('cal-pegada',
      cab.getBoundingClientRect().bottom < alto);
    let mes = -1;
    document.querySelectorAll('.cal-mes').forEach((s, i) => {
      if (!s.hidden && s.getBoundingClientRect().top <= alto + 48) mes = i;
    });
    const tira = document.querySelector('.mini-meses');
    if (!tira) return;
    tira.querySelectorAll('button').forEach((b) => {
      const es = +b.dataset.mes === mes;
      if (es && !b.classList.contains('actual')) {
        // la tira se corre sola para que el mes se vea, sin mover la página
        const x = b.getBoundingClientRect().left - tira.getBoundingClientRect().left;
        tira.scrollLeft += x - (tira.clientWidth - b.offsetWidth) / 2;
      }
      b.classList.toggle('actual', es);
      if (es) b.setAttribute('aria-current', 'true');
      else b.removeAttribute('aria-current');
    });
  });
}

/* El buscador del calendario: filtra el año que se ve, que es donde están
 * las fechas que importan. Ignora acentos y mayúsculas, y basta con que
 * estén todas las palabras («teresa jesus» encuentra las dos Teresas). */
let _temporizadorCal = null;
function filtraCalendario(q) {
  E.calQ = q;
  const palabras = plano(q.trim()).split(/\s+/).filter(Boolean);
  const activo = palabras.length > 0;
  let n = 0;
  document.querySelectorAll('.cal-mes').forEach((s) => {
    let visibles = 0;
    s.querySelectorAll('.cal-dia').forEach((a) => {
      const ok = !activo || (a.dataset.q
        && palabras.every((p) => a.dataset.q.includes(p)));
      a.hidden = !ok;
      if (ok && activo && a.dataset.q) visibles++;
    });
    s.hidden = activo && !visibles;
    n += visibles;
  });
  vista.classList.toggle('filtrando', activo);
  const res = $('#cal-res'), nada = $('#cal-nada');
  const anio = location.hash.split('/')[2] || hoyISO().slice(0, 4);
  if (res) {
    res.textContent = !activo ? '' : n === 1 ? 'Un día en ' + anio
      : n ? n + ' días en ' + anio : '';
  }
  if (nada) {
    nada.hidden = !activo || n > 0;
    nada.textContent = 'Nada con «' + q.trim() + '» en ' + anio + '. Prueba '
      + 'con una sola palabra del nombre, sin «san» ni «santa» («Francisco», '
      + '«Guadalupe», «Ángeles»).';
  }
}

function alEscribirCalendario(ev) {
  if (E.vista !== 'calendario' || ev.target.id !== 'cal-q') return;
  clearTimeout(_temporizadorCal);
  const v = ev.target.value;
  _temporizadorCal = setTimeout(() => {
    filtraCalendario(v);
    // los resultados empiezan bajo el buscador
    const cab = document.querySelector('.cal-cab');
    if (cab && window.scrollY > cab.offsetTop + cab.offsetHeight) {
      window.scrollTo(0, 0);
    }
    alDesplazarCalendario();
  }, 140);
}

function alTocarCalendario(ev) {
  if (E.vista !== 'calendario') return;
  const b = ev.target.closest('button');
  if (!b) return;
  if (b.dataset.anio) {
    location.hash = '#/calendario/' + b.dataset.anio;
  } else if (b.dataset.abre) {
    E.cfg.calAbre = b.dataset.abre;
    guardaCfg();
    const y = window.scrollY;
    verCalendario(location.hash.split('/')[2]);
    window.scrollTo(0, y);
  } else if (b.dataset.mes) {
    if (E.calQ) {                      // un mes entero: fuera el filtro
      const q = $('#cal-q');
      if (q) q.value = '';
      filtraCalendario('');
    }
    const s = document.getElementById('cal-mes-' + b.dataset.mes);
    if (s) s.scrollIntoView({ block: 'start', behavior: suave() });
  } else if (b.dataset.lupa) {
    window.scrollTo({ top: 0, behavior: suave() });
    const q = $('#cal-q');
    if (q) q.focus({ preventScroll: true });
  } else if (b.dataset.borra) {
    const q = $('#cal-q');
    q.value = '';
    filtraCalendario('');
    q.focus();
  }
}

/** Movimiento suave, salvo para quien ha pedido menos movimiento. */
function suave() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ? 'auto' : 'smooth';
}

function construyeBusqueda() {
  if (E.busqueda) return E.busqueda;
  const filas = [];
  for (const [clave, lects] of Object.entries(E.lecturas.bloques)) {
    const dia = E.diaDeClave.get(clave);
    if (!dia) continue;
    const bloque = Math.max(0, dia.b.findIndex((b) => b.k === clave));
    for (const l of lects) {
      const t = l.g.map((tr) => tr.map((v) => v[1]).join(' ')).join(' ');
      filas.push({ dia: dia, bloque: bloque, cita: l.c, texto: t,
        plano: plano(t), planoCita: plano(l.c + ' ' + (l.q || '')) });
    }
  }
  E.busqueda = filas;
  return filas;
}

function verBusqueda(q) {
  E.vista = 'buscar';
  // se llega desde el índice, que cuelga del calendario
  marcaBarra('calendario');
  modoPanel('Buscar en el latín');
  vista.innerHTML = '<input class="campo" id="q" type="search" '
    + 'placeholder="Palabra latina o cita (Is 2,1)" value="' + esc(q || '')
    + '" autocomplete="off"><div id="res"></div>';
  const campo = $('#q');
  let temporizador = null;
  campo.addEventListener('input', () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => {
      const v = campo.value.trim();
      // se guarda en la URL para poder volver, pero sin repintar la vista:
      // repintarla arrancaría el foco del campo en cada tecla
      const destino = '#/buscar/' + encodeURIComponent(v);
      if (location.hash !== destino) {
        E.ignoraHash = true;
        location.replace(destino);
      }
      pintaResultados(v);
    }, 220);
  });
  pintaResultados(q || '');
  if (!q) campo.focus();
}

function pintaResultados(q) {
  const caja = $('#res');
  if (!caja) return;
  if (q.length < 2) {
    caja.innerHTML = '<p class="aviso">Escribe al menos dos letras. La '
      + 'búsqueda ignora acentos y desata æ/œ, así que «quaesumus» encuentra '
      + '«quǽsumus».</p>';
    return;
  }
  const p = plano(q);
  // «Salmo 121» no es subcadena de «Sal 121»: cuando la frase entera no
  // aparece, basta con que todas sus palabras estén en la cita, que es un
  // campo corto y por tanto no se dispara de falsos positivos.
  const palabras = p.split(/\s+/).filter(Boolean);
  const porPalabras = palabras.length > 1;
  const filas = construyeBusqueda();
  const hallados = [];
  const porCita = [];
  for (const f of filas) {
    const k = f.plano.indexOf(p);
    if (k >= 0) hallados.push([f, k]);
    else if (f.planoCita.indexOf(p) >= 0) porCita.push([f, -1]);
    else if (porPalabras && palabras.every((t) => f.planoCita.includes(t))) {
      porCita.push([f, -1]);
    }
    if (hallados.length + porCita.length >= 300) break;
  }
  hallados.push(...porCita);
  if (!hallados.length) {
    caja.innerHTML = '<p class="aviso">Nada con «' + esc(q) + '».</p>';
    return;
  }
  caja.innerHTML = '<p class="aviso">' + hallados.length
    + (hallados.length === 300 ? '+' : '') + ' lecturas.</p>'
    + hallados.map(([f, k]) => {
      let frag;
      if (k < 0) {                       // el hallazgo está en la cita
        frag = esc(tx(f.texto.slice(0, 130))) + '…';
      } else {
        // del texto llano al acentuado: la posición no se traslada sola
        const [, pos] = planoConMapa(f.texto);
        const a = pos[k], b = pos[k + p.length];
        const desde = Math.max(0, a - 45);
        frag = (desde ? '…' : '')
          + esc(tx(f.texto.slice(desde, a)))
          + '<mark>' + esc(tx(f.texto.slice(a, b))) + '</mark>'
          + esc(tx(f.texto.slice(b, b + 90))) + '…';
      }
      return '<a class="resultado" href="#/f/'
        + encodeURIComponent(f.dia.s) + '/' + f.bloque + '">'
        + '<span class="donde">' + esc(f.dia.t) + ' · ' + esc(f.cita)
        + '</span><span class="frag">' + frag + '</span></a>';
    }).join('');
}

/* La muestra de Ajustes: un trozo de salmo y otro de lectura, con las
 * mismas clases que el oficio de verdad —`en-verso` con sangría francesa,
 * `prosa` justificada y partida— de modo que lo que se ve es exactamente lo
 * que se verá rezando, y no una imitación que podría mentir. La lectura es
 * de las más largas que hay en una lectura breve, para que el justificado
 * tenga renglones de sobra donde lucirse. */
function muestraFormato() {
  const ln = (t, cl) => '<span class="ln' + (cl ? ' ' + cl : '') + '">'
    + t + '</span>';
  const rub = (t) => '<b class="rub">' + esc(t) + '</b>';
  return '<div class="muestra" aria-hidden="true">'
    + '<section class="hora-sec en-verso">'
    + '<p class="estrofa-h">'
    + ln(rub('Ant.') + ' ' + esc('El Señor es mi pastor') + ' ' + CRUZ, 'sigla')
    + '</p><p class="estrofa-h">'
    + ln(rub('SALMO 22') + esc('   El buen pastor'), 'tit')
    + ln(esc('El Señor es mi pastor, nada me falta:'))
    + ln(CRUZ + ' ' + esc('en verdes praderas me hace recostar;'))
    + ln(esc('me conduce hacia fuentes tranquilas'))
    + ln(esc('y repara mis fuerzas.'))
    + '</p></section>'
    + '<section class="hora-sec prosa">'
    + '<div class="sec-cab"><h2 class="rotulo">Lectura breve</h2></div>'
    + '<p class="estrofa-h">'
    + ln(esc('Hermanos: Estad siempre alegres en el Señor; os lo repito, '
      + 'estad alegres. Que vuestra mesura la conozcan todos los hombres. '
      + 'El Señor está cerca. Nada os preocupe; sino que, en toda ocasión, '
      + 'en la oración y en la súplica, con acción de gracias, vuestras '
      + 'peticiones sean presentadas a Dios.'))
    + '</p></section></div>';
}

function verAjustes() {
  E.vista = 'ajustes';
  marcaBarra('ajustes');
  modoPanel('Ajustes');
  const sel = (id, etiqueta, pista, ops) =>
    '<div class="ajuste"><label for="aj-' + id + '">' + etiqueta
    + (pista ? '<span class="pista">' + pista + '</span>' : '')
    + '</label><select id="aj-' + id + '">' + ops.map(([v, t]) =>
      '<option value="' + v + '"' + (E.cfg[id] === v ? ' selected' : '')
      + '>' + t + '</option>').join('') + '</select></div>';
  // Cada sección, una pestaña que se abre: la lista entera de un tirón son
  // cuatro pantallas de deslizar para cambiar una cosa. Viene abierta la
  // del formato, que es a lo que más se vuelve.
  let n = 0;
  const ajuste = (titulo) => '</div></details>'
    + '<details class="ajustes-sec"' + (n++ === 1 ? ' open' : '')
    + '><summary>' + titulo + '</summary><div class="ajustes-cuerpo">';
  vista.innerHTML = [
    ajuste('El latín del leccionario'),
    sel('fuente', 'Versión latina',
      'La Nova Vulgata es el latín de los libros litúrgicos vigentes; la '
      + 'Clementina, la Vulgata de siempre.',
      [['clementina', 'Vulgata Clementina'], ['nova', 'Nova Vulgata']]),
    sel('acentos', 'Acentuación litúrgica',
      'El acento tónico marcado, como en los libros de coro.',
      [[true, 'Sí'], [false, 'No']]),
    sel('numeros', 'Números de versículo', '', [[true, 'Sí'], [false, 'No']]),
    ajuste('Formato del texto'),
    muestraFormato(),
    '<div class="ajuste ancho"><label for="aj-tam">Tamaño de letra'
    + '<span class="pista">Lo de arriba es el texto de verdad, con las '
    + 'mismas reglas: lo que se vea ahí es lo que se verá rezando.</span>'
    + '</label>'
    + '<input type="range" id="aj-tam" min="80" max="200" step="5" value="'
    + E.cfg.tam + '">'
    + '<span class="marcas"><span>Menor</span><span id="aj-tam-pct">'
    + E.cfg.tam + '%</span><span>Mayor</span></span></div>',
    sel('interlinea', 'Interlineado', '',
      [['compacto', 'Compacto'], ['normal', 'Normal'], ['holgado', 'Holgado']]),
    sel('letra', 'Tipo de letra',
      'La de libro es la de los libros de coro, con remates; la de pantalla '
      + 'es de palo seco, y se lee mejor con la letra muy pequeña o muy '
      + 'grande.',
      [['serif', 'De libro'], ['sans', 'De pantalla']]),
    sel('justifica', 'Lecturas justificadas',
      'Las lecturas, los responsorios, las preces y la oración, a caja, '
      + 'como en el libro. Los himnos, los salmos y los cánticos van '
      + 'siempre por renglones, con sangría francesa.',
      [['si', 'Sí'], ['no', 'No: a la izquierda']]),
    sel('particion', 'Partir las palabras',
      'Con guiones al final del renglón. Sin partirlas, el justificado abre '
      + 'más espacio entre palabras.',
      [['si', 'Sí'], ['no', 'No']]),
    sel('cruces', 'La cruz del salmo',
      'Donde el salmo empieza repitiendo su antífona, una cruz dice dónde '
      + 'seguir: «El Señor es mi pastor †».',
      [['si', 'Sí'], ['no', 'No']]),
    sel('medida', 'Ancho de la columna',
      'En una tableta o en el ordenador, un renglón corto se lee mejor que '
      + 'uno que cruza la pantalla.',
      [['normal', 'Estrecha, como un libro'], ['ancha', 'Toda la pantalla']]),
    ajuste('Aspecto'),
    sel('tema', 'Color del papel', '',
      [['auto', 'Según el teléfono'], ['claro', 'Claro'],
        ['sepia', 'Sepia'], ['oscuro', 'Oscuro'], ['noche', 'De noche']]),
    'wakeLock' in navigator
      ? sel('despierto', 'No apagar la pantalla',
        'Un oficio son diez o quince minutos de lectura sin tocar nada, y '
        + 'el teléfono se apaga a la mitad. Mientras la app esté delante, '
        + 'la pantalla se queda encendida.',
        [[false, 'No'], [true, 'Sí']])
      : '',
    ajuste('Al abrir la app'),
    sel('inicio', 'Al abrir la app',
      'La app lleva dentro dos libros. Si siempre vas al mismo, dilo aquí y '
      + 'no se te vuelve a preguntar.',
      [['menu', 'Preguntar'], ['misa', 'Las lecturas de la misa'],
        ['horas', 'La liturgia de las horas']]),
    ajuste('Calendario'),
    sel('epifania', 'Epifanía',
      'En España se celebra el 6 de enero; en gran parte de América, el '
      + 'domingo entre el 2 y el 8.',
      [['domingo', 'Domingo entre el 2 y el 8'], ['6enero', 'Siempre el 6 de enero']]),
    sel('ascension', 'Ascensión', '',
      [['domingo', 'Trasladada al domingo'], ['jueves', 'Jueves, 40 días']]),
    sel('corpus', 'Corpus Christi', '',
      [['domingo', 'Trasladado al domingo'], ['jueves', 'Jueves']]),
    sel('memorias', 'En las memorias, leer',
      'El Ordo lectionum Missae (n. 82) manda seguir la lectura continua de '
      + 'la feria salvo que el santo tenga lecturas propias; la Tabla de los '
      + 'días litúrgicos, en cambio, pone la memoria por encima de la feria. '
      + 'Las dos opciones se ofrecen siempre: esto sólo decide cuál sale '
      + 'primero.',
      [['santo', 'Las del santo (Tabla de los días litúrgicos)'],
        ['feria', 'La lectura continua de la feria (OLM 82)']]),
    ajuste('Liturgia de las Horas'),
    sel('hLibre', 'En las memorias libres, rezar',
      'Una memoria libre se puede celebrar o dejar. Las dos opciones salen '
      + 'siempre arriba: esto sólo decide cuál viene marcada.',
      [['santo', 'El oficio del santo'], ['feria', 'El de la feria']]),
    sel('hComun', 'En las memorias, lo que no es propio',
      'Las rúbricas dejan tomarlo del común o del día, y cada sección lleva '
      + 'su selector: esto sólo decide cuál viene marcado.',
      [['comun', 'Del común'], ['dia', 'Del día']]),
    sel('carril', 'Índice de la hora',
      'Las cintas del breviario: una raya por sección al borde de la caja, '
      + 'más larga la de donde vas. Tocar una lleva a su sección.',
      [['si', 'Sí'], ['no', 'No']]),
    sel('gestos', 'Deslizar para cambiar de hora',
      'Arrastrar sobre el texto pasa a la hora siguiente o a la anterior, y '
      + 'de Completas al Oficio de lectura del día siguiente.',
      [['si', 'Sí'], ['no', 'No']]),
    sel('rezadas', 'Marcar lo ya rezado hoy',
      'Una rayita bajo las horas de hoy que ya has rezado. No hay que decir '
      + 'nada: queda marcada aquella cuyo final has llegado a leer.',
      [['si', 'Sí'], ['no', 'No']]),
    '<p class="pie">' + esc(E.lecturas.cabecera) + '<br><br>'
    + 'Calendario general romano y latinoamericano, con el propio y el común '
    + 'de los santos (leccionario V), las misas por diversas necesidades y '
    + 'votivas (VI) y las rituales y de difuntos (VIII). La concurrencia de '
    + 'celebraciones se resuelve con la Tabla de los días litúrgicos. '
    + 'El leccionario IX (misas con niños) no está incluido. '
    + 'Calendario de ' + E.cal.rango[0] + ' a ' + E.cal.rango[1] + '.'
    + '</p>'
  // el primer `ajuste()` no tiene nada que cerrar, y el último se queda sin
  // cerrar: se le quita a uno y se le pone al otro
  ].join('').replace('</div></details>', '') + '</div></details>';

  colocaPosicion();
}

/** Un solo oyente para todos los ajustes: la vista se repinta a menudo y
 *  colgar oyentes en cada repintado los iría acumulando. Los controles van
 *  con el prefijo `aj-` para no chocar con los `id` de la página. */
async function alCambiarAjuste(ev) {
  if (E.vista !== 'ajustes') return;
  const id = (ev.target.id || '').replace(/^aj-/, '');
  if (!(id in E.cfg)) return;
  let v = ev.target.value;
  if (v === 'true' || v === 'false') v = (v === 'true');
  E.cfg[id] = id === 'tam' ? +v : v;
  guardaCfg();
  aplicaCfg();
  if (id === 'tam') {
    const pct = $('#aj-tam-pct');
    if (pct) pct.textContent = E.cfg.tam + '%';
  }
  if (id === 'fuente') {
    vista.innerHTML = '<p class="aviso">Cambiando de versión…</p>';
    await cargaLecturas(v);
    verAjustes();
  }
}

function marcaBarra(cual) {
  document.querySelectorAll('#barra button').forEach((b) =>
    b.classList.toggle('activo', b.dataset.ir === cual));
}

/* ---------------------------------------------------------------- portada
 * La app lleva dentro dos libros distintos —el leccionario de la misa y el
 * oficio divino— y el que se quiere a cada hora no lo sabe nadie más que
 * quien abre. Así que se pregunta, en vez de suponer; y quien siempre va al
 * mismo sitio lo dice una vez en Ajustes y no se le vuelve a preguntar. */
/** La hora por la que abre la portada: la que toca por el reloj y, si ésa
 *  ya se rezó hoy, la primera de las siguientes que no se haya rezado. */
function horaDeLaPortada() {
  const hoy = hoyISO();
  const ya = (cl) => !!(E.cfg.rezadas !== 'no' && E.rezadas
    && E.rezadas.d === hoy && E.rezadas.h[cl]);
  const i = Math.max(0, HORAS.findIndex((x) => x[0] === horaSugerida()));
  if (!ya(HORAS[i][0])) return { i: i, rotulo: 'Ahora', ya: ya };
  for (let j = i + 1; j < HORAS.length; j++) {
    if (!ya(HORAS[j][0])) return { i: j, rotulo: 'Sigue', ya: ya };
  }
  return { i: i, rotulo: 'Ahora', ya: ya, todas: true };
}

function verPortada() {
  E.vista = 'portada';
  marcaBarra('portada');
  const iso = hoyISO();
  E.fecha = iso;
  modoPanel('');
  $('#cabecera').classList.add('portada');
  $('#titulo-dia').textContent = 'Liturgicum';

  const val = entradasDe(iso);
  const cels = val ? celebracionesDe(val) : [];
  const dia = cels.length ? E.diaDe.get(cels[0].slug) : null;
  const anio = anioDe(iso);
  const h = horaDeLaPortada();
  // la portada toma el color del día, como las dos vistas a las que lleva
  if (cels.length) {
    document.body.dataset.color = esDeLaVirgen(dia && dia.t) ? 'azul'
      : E.colorDe.get(cels[0].slug) || 'neutro';
  }

  const tira = HORAS.map(([cl, , nombre, breve], i) => {
    const marcas = (i === h.i ? ' ahora' : '') + (h.ya(cl) ? ' rezada' : '');
    return '<a href="#/h/' + iso + '/' + cl + '"' + (marcas ? ' class="'
      + marcas.trim() + '"' : '') + ' aria-label="' + esc(nombre)
      + (h.ya(cl) ? ', rezada' : '') + '">' + esc(breve) + '</a>';
  }).join('');

  vista.innerHTML = [
    '<p class="portada-fecha">' + esc(fechaLarga(iso)) + '</p>',
    dia ? '<p class="portada-dia">' + esc(dia.t)
      + (cels[0].m && cels[0].m.g ? '<small>' + esc(cels[0].m.g) + '</small>'
        : '') + '</p>' : '',
    '<div class="portada-elige">',
    '<a class="tarjeta" href="#/d/' + iso + '">',
    '<span class="tarjeta-icono">' + ICONO.misa + '</span>',
    '<span class="tarjeta-t">Lecturas de la Misa</span>',
    '<span class="tarjeta-p">El leccionario romano en latín'
    + (anio ? ' · Ciclo ' + anio.ciclo + ' · Año ' + anio.ferial : '')
    + '</span>',
    '</a>',
    // la de las horas lleva pegadas las siete, con la que toca marcada y
    // una rayita bajo las que ya se han rezado hoy: la pregunta de quien
    // abre la app a media tarde es por dónde iba, no cuál de los dos libros
    '<a class="tarjeta con-tira" href="#/h/' + iso + '/' + HORAS[h.i][0] + '">',
    '<span class="tarjeta-icono">' + ICONO.horas + '</span>',
    '<span class="tarjeta-t">Liturgia de las Horas</span>',
    '<span class="tarjeta-p">' + (h.todas
      ? 'Hoy las has rezado todas · ' + esc(HORAS[h.i][1])
      : h.rotulo + ', ' + esc(HORAS[h.i][1])) + '</span>',
    '</a>',
    '<nav class="portada-horas" aria-label="Las horas de hoy">' + tira + '</nav>',
    '</div>',
    '<nav class="portada-menudo">',
    '<a href="#/calendario">Calendario</a>',
    '<a href="#/indice">Índice del leccionario</a>',
    '<a href="#/ajustes">Ajustes</a>',
    '</nav>'
  ].join('');
  colocaPosicion();
}

/* ----------------------------------------------- la liturgia de las horas
 * Las horas van en ficheros aparte y no se cargan hasta que se piden: son
 * 25 MB, y quien sólo venga a las lecturas no tiene por qué esperarlos.
 *
 * [clave, título de la cabecera, nombre en la tira, abreviatura]: en la
 * tira de las horas sólo la elegida lleva su nombre, y las demás tres
 * letras, para que las siete se vean de golpe y no haya que deslizarla. */
const HORAS = [
  ['oficio', 'Oficio de Lectura', 'Oficio', 'Ofi'],
  ['laudes', 'Laudes', 'Laudes', 'Lau'],
  ['tercia', 'Tercia', 'Tercia', 'Ter'],
  ['sexta', 'Sexta', 'Sexta', 'Sex'],
  ['nona', 'Nona', 'Nona', 'Non'],
  ['visperas', 'Vísperas', 'Vísperas', 'Vís'],
  ['completas', 'Completas', 'Completas', 'Com']
];

async function cargaHoras() {
  if (E.horas) return;
  const [libro, dias] = await Promise.all(
    [json('horas.json'), json('horas_dias.json')]);
  E.horas = libro;
  E.horasDias = dias;
  // Santa María en sábado no es un santo del calendario —no tiene día— y su
  // oficio sale entero del Común de la Virgen: se le da ese común como si
  // lo fuera, y la cascada de siempre hace el resto
  libro.comun_de[SMV.id] = [COMUN_VIRGEN];
}

/* --------------------------------------------------- lo que se puede elegir
 * El oficio de un día no siempre es uno solo. Las rúbricas del Ordinario de
 * la Liturgia de las Horas dejan elegir en dos niveles, y la app ofrece los
 * dos sin decidir por nadie:
 *
 *  · la celebración: una memoria libre se puede celebrar o dejar, y en las
 *    ferias privilegiadas una memoria sólo puede hacerse como conmemoración.
 *    Se elige arriba, con los chips de la cabecera.
 *  · cada sección: en las memorias, lo que el santo no tiene propio «puede
 *    elegirse del Común o de la feria». Se elige en la sección misma, con un
 *    selector discreto junto a su rótulo.
 *
 * Qué se celebra cada día, y con qué grado, viene resuelto de casa
 * (horas_dias.json, con la precedencia del calendario); aquí sólo se
 * aplican las rúbricas de cada sección. */

// En las memorias, sección por sección:
//   elige  «si no tiene propio, puede elegirse el del Común o el de la
//          feria»: el invitatorio, el himno, y en Laudes y Vísperas de la
//          lectura breve a las preces
//   santo  del Propio o del Común, nunca de la feria: la lectura
//          hagiográfica del Oficio y la oración
//   biblica  «la primera lectura, con su responsorio, se toma del Oficio
//          corriente, es decir, del tiempo», salvo que el santo tenga la
//          suya. Catorce memorias la tienen —san Atanasio, san Policarpo,
//          san Ireneo, santa Catalina de Siena…—, y se sabe cuáles porque
//          se mide: lo que el santoral guarda como propio es casi siempre
//          la lectura corrida del otro año del ciclo, que la fuente
//          publicó aquel día y la fase 2 no supo distinguir
//   (lo demás) del salterio, «excepto cuando tienen propios esos
//          elementos»: la salmodia
const EN_MEMORIA = {
  invitatorio: 'elige', himno: 'elige', lectura_breve: 'elige',
  responsorio_breve: 'elige', cantico_evangelico: 'elige', preces: 'elige',
  lectura2: 'santo', responsorio2: 'santo', oracion: 'santo',
  lectura1: 'biblica', responsorio: 'biblica'
};

/* Lo que va en pareja se elige una vez: la lectura breve manda sobre su
 * responsorio breve, y la lectura bíblica del Oficio sobre el suyo. Tomar
 * la del santo y responderle con la de la feria no tiene sentido. */
const LIGADAS = { responsorio: 'lectura1',
  responsorio_breve: 'lectura_breve' };
// «En la Hora intermedia nunca se hace mención de las memorias de los
// santos», y Completas se toman siempre del salterio.
const SIN_MEMORIAS = ['tercia', 'sexta', 'nona', 'completas'];

function bonito(g) { return g ? g.charAt(0) + g.slice(1).toLowerCase() : ''; }

/* «Los sábados del tiempo ordinario en que no ocurra una memoria
 * obligatoria, puede hacerse la memoria libre de Santa María Virgen»
 * (Normas universales sobre el año litúrgico, n. 15). Todo su oficio se
 * toma del Común de la Virgen, y de Vísperas no tiene: las del sábado son
 * siempre las primeras del domingo. */
const COMUN_VIRGEN = 'santisima virgen maria';
const SMV = {
  id: 'smv', t: 'Santa María Virgen en sábado', g: 'MEMORIA LIBRE',
  modo: 'memoria', smv: 1
};

function cabeSantaMaria(d) {
  return d.d === 6 && d.t === 'Ordinario' && !d.cm
    && !(d.c || []).some((c) => !/LIBRE/.test(c[3] || ''));
}

/** Qué oficios puede rezar quien abre el día, y cuál sale primero. */
function celebracionesHoras(d) {
  const feria = { id: 'feria', t: d.tt, g: '', modo: 'feria' };
  const cs = (d.c || []).map((c) => ({
    id: c[0], t: c[2], g: c[3], cel: c,
    modo: d.cm ? 'conmemoracion'
      : /^MEMORIA/.test(c[3]) ? 'memoria' : 'entero'
  }));
  if (d.cm) return { ops: [feria].concat(cs), def: 'feria' };
  if (cs.length && d.w && cs[0].g !== 'MEMORIA LIBRE') {
    return { ops: [cs[0]], def: cs[0].id };
  }
  // memorias libres: cualquiera de ellas, la de la Virgen si es sábado del
  // tiempo ordinario, o la feria
  const libres = cabeSantaMaria(d) ? cs.concat([SMV]) : cs;
  return {
    ops: libres.concat([feria]),
    def: cs.length && E.cfg.hLibre !== 'feria' ? cs[0].id : 'feria'
  };
}

/* En el Oficio, algunos días la fuente da el invitatorio con otra forma
 * («Si el Oficio de lectura es la primera oración del día…») y lo llama de
 * otra manera: es la misma pieza, y va en el mismo sitio. */
function pieza(tabla, prefijo, hora, cl) {
  return tabla[prefijo + hora + '/' + cl]
    || (hora === 'oficio' && cl === 'invitatorio'
      && tabla[prefijo + hora + '/preambulo']) || null;
}

/** Lo del día: el propio del tiempo, el salterio y el ordinario.
 *
 *  La lectura bíblica del Oficio sigue el ciclo de dos años: el libro
 *  guarda la de un año en `tiempo` y la del otro en `tiempo_anio`, y el año
 *  ferial (I los impares, II los pares) lo dice el calendario. */
function delDia(d, hora, cl) {
  const L = E.horas;
  const otroAnio = (L.tiempo_anio || {})[d.k + '/' + hora + '/' + cl];
  if (otroAnio && otroAnio[d.a]) return otroAnio[d.a];
  return pieza(L.tiempo, d.k + '/', hora, cl)
    || (cl === 'salmodia' && d.p
      && L.salterio[d.t + '/' + d.p + '/' + d.d + '/' + hora])
    || L.ordinario[d.t + '/' + hora + '/' + cl]
    || L.ordinario['@/' + hora + '/' + cl] || null;
}

function delSanto(op, hora, cl) {
  if (!op.cel) return null;          // la de la Virgen en sábado no tiene día
  return pieza(E.horas.santoral, op.cel[1] + '/' + op.cel[0] + '/', hora, cl);
}

function deSusComunes(op, hora, cl) {
  const L = E.horas;
  const ops = [];
  for (const k of L.comun_de[op.id] || []) {
    const c = pieza(L.comunes, k + '/', hora, cl);
    if (!c) continue;
    const rot = L.rotulo_comun[k] || 'Común';
    ops.push({ id: 'c:' + k, rot: rot, c: c });
    // Un común ofrece más de una lectura patrística, y se escoge: van
    // detrás de la suya, numeradas (el Común de la Virgen trae dos).
    ((L.otras_lecturas || {})[k + '/' + hora + '/' + cl] || []).forEach(
      (otra, j) => ops.push({ id: 'c:' + k + ':' + (j + 2),
        rot: rot + ' ' + ROMANOS[j + 1], tit: incipit(otra), c: otra }));
  }
  return ops;
}

/** Sin repetir: dos comunes que dan el mismo texto son una sola opción. */
function distintas(ops) {
  const textos = new Set(), rotulos = new Set();
  return ops.filter((o) => {
    const k = JSON.stringify(o.c.l);
    if (textos.has(k) || rotulos.has(o.rot)) return false;
    textos.add(k); rotulos.add(o.rot);
    return true;
  });
}

const ROMANOS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X'];

/** Las primeras palabras de un texto: el nombre con que se conoce un himno
 *  o una antífona, para el título del botón que lo elige. */
function incipit(c) {
  for (const ln of (c && c.l) || []) {
    const t = ln.filter((tr) => !tr[0]).map((tr) => tr[1]).join('').trim();
    if (t) return t.length > 48 ? t.slice(0, 47) + '…' : t;
  }
  return '';
}
function claveIncipit(c) {
  return incipit(c).toLowerCase().normalize('NFD').replace(/[^a-z ]/g, '')
    .split(/\s+/).slice(0, 5).join(' ');
}

/* «En el Oficio dominical y ferial, se dice el himno que se indica en el
 * Salterio […]. Pueden usarse también otros cantos oportunos» (Ordinario).
 * Del himno del día se ofrecen los otros que el libro da para ese mismo día;
 * en Completas, los del tiempo, que se turnan. Van numerados, como en el
 * libro, y el primero es siempre el del día. */
/** El grupo de himnos al que pertenece un día: su tiempo, y en el ordinario
 *  la mitad que le toca —hasta la semana XVII o desde la XVIII, que es el
 *  corte de los tomos III y IV—. Las dos solemnidades del Señor sin semana
 *  numerada (la Trinidad y el Corpus) caen en la primera. */
function grupoHimnos(d) {
  if (d.t !== 'Ordinario') return d.t;
  return 'Ordinario/' + (+d.k.split('/')[1] > 17 ? 2 : 1);
}

function otrosHimnos(d, hora, base) {
  const L = E.horas;
  let pool = [];
  if (INTERMEDIAS.includes(hora)) {
    // la Hora intermedia: los del tiempo, y en el ordinario los de su
    // mitad; el Triduo y Pentecostés traen el suyo, y entonces sólo ése
    const H = L.himnos_intermedia || {};
    pool = H[d.k + '/' + hora] || H[grupoHimnos(d) + '/' + hora] || [];
  } else if (hora === 'completas') {
    // Completas: los del tiempo, y en el ordinario los de su mitad. Cada
    // tiempo tiene los suyos —medido, dos por grupo, que se turnan—, así
    // que no se le añaden los de ningún otro.
    pool = (L.himnos_completas || {})[grupoHimnos(d)] || [];
  } else {
    pool = (L.otros_himnos || {})[d.k + '/' + hora + '/himno'] || [];
  }
  const vistos = new Set([claveIncipit(base)]);
  return pool.filter((c) => {
    const k = claveIncipit(c);
    if (!k || vistos.has(k)) return false;
    vistos.add(k);
    return true;
  });
}

/* La antífona final de la Virgen: «se dice una de las siguientes», y en
 * Pascua, «Reina del cielo». Las cuatro van en el orden del Ordinario. */
function antifonasFinales(d) {
  const A = E.horas.antifonas_finales || {};
  return (A[d.t] || A.Ordinario || []).map((c, j) => ({
    id: 'af' + j, rot: ROMANOS[j], tit: incipit(c), c: c
  }));
}

/** Las opciones de una sección, cada una con su rótulo para el selector.
 *  Una sola, casi siempre; dos o tres, donde las rúbricas dejan elegir. */
function opcionesSeccion(d, op, hora, cl) {
  if (cl === 'antifona_final') {
    const af = antifonasFinales(d);
    if (af.length) return af;
  }
  const alts = opcionesSeccionBase(d, op, hora, cl);
  const i = alts.findIndex((o) => o.id === 'dia');
  if (cl === 'salmodia' && i >= 0 && alts.length === 1) {
    const propias = antifonasPropias(d, op, hora, alts[i].c);
    if (propias) return propias;
    const sal = salmodiaIntermedia(d, hora, alts[i].c);
    if (sal) return sal;
  }
  // los himnos que se pueden escoger se cuelgan del «del día»
  if (cl === 'himno' && i >= 0) {
    const otros = otrosHimnos(d, hora, alts[i].c);
    if (otros.length) {
      const solo = alts.length === 1;
      alts[i].rot = solo ? 'I' : alts[i].rot;
      alts[i].tit = incipit(alts[i].c);
      alts.splice(i + 1, 0, ...otros.map((c, j) => ({
        id: 'dia' + (j + 2), rot: ROMANOS[j + 1], tit: incipit(c), c: c
      })));
    }
  }
  return alts;
}

function opcionesSeccionBase(d, op, hora, cl) {
  const dia = delDia(d, hora, cl);
  const soloDia = dia ? [{ id: 'dia', rot: 'Del día', c: dia }] : [];
  // el sábado, las vísperas son las primeras del domingo (lo dice `v`); y de
  // la memoria de la Virgen en sábado, que es de sábado, nunca son
  const cedeVisperas = (d.v || op.smv)
    && (hora === 'visperas' || hora === 'completas');
  let regla = 'dia';
  if (op.modo === 'entero' && !cedeVisperas) regla = 'entero';
  if (op.modo === 'memoria' && !cedeVisperas && !SIN_MEMORIAS.includes(hora)) {
    regla = EN_MEMORIA[cl] || 'salterio';
  }
  if (regla === 'dia') return soloDia;
  // La antífona del Benedictus y del Magníficat: en las memorias y las
  // fiestas de los santos se ofrece también la del día, detrás de la del
  // santo (propia o del común), que es la que sale marcada.
  const yDelDia = (ops) => (cl === 'cantico_evangelico'
    && /^(MEMORIA|FIESTA)/.test(op.g || '')) ? distintas(ops.concat(soloDia))
    : ops;
  const propio = delSanto(op, hora, cl);
  if (regla === 'biblica') {
    return propio ? distintas(
      [{ id: 'propio', rot: 'Propio', c: propio }].concat(soloDia)) : soloDia;
  }
  if (propio) return yDelDia([{ id: 'propio', rot: 'Propio', c: propio }]);
  if (regla === 'salterio') return soloDia;
  const comunes = deSusComunes(op, hora, cl);
  // lo propio del santo —aquí, lo de su común— va siempre delante, y lo
  // del día detrás: el orden de los botones es el mismo en toda la hora
  if (regla === 'elige') return distintas(comunes.concat(soloDia));
  // solemnidades, fiestas y lo que en las memorias es del santo: del
  // propio o del común, y del día sólo si no hay otra cosa
  return comunes.length ? yDelDia(distintas(comunes)) : soloDia;
}

/* ---------------------------------------------------- la Hora intermedia
 * «Quien reza una sola hora intermedia toma la salmodia del día; quien reza
 * más de una, en las otras toma la complementaria» (Ordinario): los salmos
 * graduales, 119-121 en Tercia, 122-124 en Sexta y 125-127 en Nona. Aquí la
 * del día va por omisión en Sexta y la complementaria en Tercia y Nona, y
 * las tres dejan cambiar.
 *
 * La fuente reza las tres y pone la del día donde le parece, así que la
 * otra se rehace: los salmos de una con las antífonas de la otra. En el
 * tiempo ordinario cada salmo lleva la suya, que va con él; en Adviento,
 * Navidad, Cuaresma y Pascua cada hora tiene una sola para toda la
 * salmodia, y ésa se queda aunque cambien los salmos. */
const INTERMEDIAS = ['tercia', 'sexta', 'nona'];

const esAntifona = (ln) => ln.length > 0 && ln[0][0] && /^\s*Ant/.test(ln[0][1]);
// el título del salmo viene a veces en mayúsculas y a veces no
const esTituloSalmo = (ln) => ln.length > 0 && ln[0][0]
  && /^\s*(salmo|c[áa]ntico)/i.test(ln[0][1]);
const negro = (ln) => ln.filter((tr) => !tr[0]).map((tr) => tr[1]).join('').trim();

/** Una salmodia en sus piezas: las antífonas, sin la repetición del final,
 *  y cada salmo, del título a la gloria. */
function despieza(lineas) {
  const ants = [], salmos = [];
  let salmo = null;
  for (const ln of lineas) {
    if (esAntifona(ln)) {
      salmo = null;
      // «Ant 1.», «Ant 2.»… abren; «Ant.» a secas repite la de antes
      if (/^\s*Ant\.?\s*\d/.test(ln[0][1])) ants.push(negro(ln));
    } else if (esTituloSalmo(ln)) {
      salmos.push(salmo = [ln]);
    } else if (salmo) {
      salmo.push(ln);
    }
  }
  for (const s of salmos) while (s.length && !s[s.length - 1].length) s.pop();
  return { ants: ants, salmos: salmos };
}

/** Y al revés: una antífona por salmo, o una sola para todos. */
function compone(ants, salmos) {
  const l = [[]];
  const ant = (n, t) => l.push([[1, n ? 'Ant ' + n + '. ' : 'Ant. '], [0, t]], []);
  if (ants.length > 1 && ants.length === salmos.length) {
    salmos.forEach((s, i) => { ant(i + 1, ants[i]); l.push(...s, []); ant(0, ants[i]); });
  } else {
    ant(1, ants[0]);
    salmos.forEach((s) => l.push(...s, []));
    ant(0, ants[0]);
  }
  return l;
}

/* Lo que una celebración tiene propio en la salmodia son sus antífonas: los
 * salmos son los del salterio que toque ese día, y por eso la misma fiesta
 * sale con unos salmos u otros según el año. Se componen las dos cosas —las
 * antífonas del santo sobre los salmos del día— y se ofrece también la
 * salmodia tal cual, por si quien reza prefiere las del salterio.
 *
 * Medido sobre ocho años: 46 casillas las tienen (san Mateo, san Andrés,
 * los Arcángeles, los Ángeles Custodios, la Inmaculada…). */
const DIAS_SEM = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves',
  'viernes', 'sábado'];

function antifonasPropias(d, op, hora, dia) {
  const e = op.cel
    && (E.horas.antifonas || {})[op.cel[1] + '/' + op.cel[0] + '/' + hora];
  if (!e || !e.a || !e.a.length) return null;
  // «Se toma la salmodia del domingo I»: una rúbrica que el libro escribe y
  // la fuente no, porque la aplica. Cuando la celebración tiene señalada su
  // casilla del salterio, los salmos salen de allí; si no, son los del día.
  let fuente = dia, rotulo = 'Con los salmos del día';
  if (e.s) {
    const [sem, ds] = e.s.split('/');
    const otra = E.horas.salterio[d.t + '/' + e.s + '/' + hora]
      || E.horas.salterio['Ordinario/' + e.s + '/' + hora];
    if (otra) {
      fuente = otra;
      rotulo = 'Salmos del ' + DIAS_SEM[+ds] + ' ' + ROMANOS[+sem - 1];
    }
  }
  const piezas = despieza(fuente.l);
  if (!piezas.salmos.length) return null;
  return [
    { id: 'propio', rot: 'Propio', tit: 'Antífonas propias · ' + rotulo,
      c: { r: dia.r || 'SALMODIA', l: compone(e.a, piezas.salmos) } },
    { id: 'dia', rot: 'Del día', tit: 'La salmodia del día', c: dia }
  ];
}

function salmodiaIntermedia(d, hora, dia) {
  const L = E.horas, I = L.intermedia;
  if (!I || !d.p || !INTERMEDIAS.includes(hora)) return null;
  const base = d.t + '/' + d.p + '/' + d.d;
  // sólo la del salterio: la propia de una fiesta no se toca
  if (dia !== L.salterio[base + '/' + hora]) return null;
  let delDiaC = I.dia[base];
  if (typeof delDiaC === 'string') delDiaC = L.salterio[base + '/' + delDiaC];
  const compC = I.comp[hora];
  if (!delDiaC || !compC) return null;
  const aqui = despieza(dia.l);
  if (!aqui.ants.length || !aqui.salmos.length) return null;
  const nums = aqui.salmos.map((s) => +((s[0][0][1].match(/\d+/) || [])[0]));
  const esComp = nums.join() === I.salmos[hora].join();
  // una antífona para toda la salmodia: la de esta hora, con cualquier salmo
  const unica = aqui.ants.length === 1 && aqui.salmos.length > 1;
  const rehecha = (c) => unica ? compone(aqui.ants, despieza(c.l).salmos) : c.l;
  return [
    { id: 'sal-dia', rot: 'Del día', tit: 'Salmodia del día',
      c: { r: 'SALMODIA', l: esComp ? rehecha(delDiaC) : dia.l } },
    { id: 'sal-comp', rot: 'Complementaria', tit: 'Salmodia complementaria',
      c: { r: 'SALMODIA COMPLEMENTARIA', l: esComp ? dia.l : rehecha(compC) } }
  ];
}

/* Lo que se elige en cada sección se recuerda mientras dura la sesión,
 * para que pasar de Laudes a Vísperas y volver no lo deshaga. */
function claveEleccion(iso, idCel, hora, cl) {
  return [iso, idCel, hora, cl].join('|');
}
function cargaElecciones() {
  try {
    E.elecciones = JSON.parse(sessionStorage.getItem('elecciones') || '{}');
  } catch (_) { E.elecciones = {}; }
}
function guardaElecciones() {
  try {
    sessionStorage.setItem('elecciones', JSON.stringify(E.elecciones));
  } catch (_) { /* sin almacenamiento: vale para esta vista */ }
}
function eleccionDe(iso, idCel, hora, cl, alts, d) {
  const guardada = E.elecciones[claveEleccion(iso, idCel, hora, cl)];
  let i = alts.findIndex((o) => o.id === guardada);
  if (i < 0 && cl === 'antifona_final') {
    // la que se eligió la última noche; si no, la que trae el día
    i = alts.findIndex((o) => claveIncipit(o.c) === E.cfg.hAntFinal);
    if (i < 0) {
      const delDiaK = claveIncipit(delDia(d, hora, cl));
      i = alts.findIndex((o) => claveIncipit(o.c) === delDiaK);
    }
  }
  // la salmodia del día, en Sexta; la complementaria, en Tercia y Nona
  if (i < 0 && cl === 'salmodia' && alts.some((o) => o.id === 'sal-dia')) {
    i = alts.findIndex((o) => o.id === (hora === 'sexta' ? 'sal-dia' : 'sal-comp'));
  }
  // lo propio del santo, si lo tiene, va siempre delante de lo del día
  if (i < 0) i = alts.findIndex((o) => o.id === 'propio');
  if (i < 0) {
    i = alts.findIndex((o) => E.cfg.hComun === 'dia'
      ? o.id === 'dia' : !o.id.startsWith('dia'));
  }
  return Math.max(0, i);
}

/** El orden de las secciones. La invocación inicial va delante (el orden
 *  recuperado del volcado la dejaba al final de Laudes), y el preámbulo
 *  del Oficio es el invitatorio con otra forma, que ya ocupa su sitio. */
function ordenDe(hora) {
  let o = (E.horas.orden[hora] || []).slice();
  if (hora === 'oficio') o = o.filter((cl) => cl !== 'preambulo');
  // El Te Deum: la fuente lo rotula «Himno: Señor, Dios eterno» y el libro
  // lo guarda como un segundo himno, que el orden recuperado dejaba detrás
  // de la conclusión. Va después del segundo responsorio (Ordinario).
  if (hora === 'oficio' && o.includes('himno2')) {
    o = o.filter((cl) => cl !== 'himno2');
    const r = o.indexOf('responsorio2');
    o.splice(r < 0 ? o.length : r + 1, 0, 'himno2');
  }
  if (o.includes('invocacion')) {
    o = ['invocacion'].concat(o.filter((cl) => cl !== 'invocacion'));
  }
  return o;
}

/** Una sección que no se elige: la que añade la conmemoración. */
function fija(cl, rotulo, lineas) {
  return { cl: cl, alts: [{ id: 'propio', rot: '', c: { r: rotulo, l: lineas } }], i: 0 };
}

/** La conmemoración (Principios y normas generales, nn. 238-239): el oficio
 *  es entero de la feria, y del santo se añade, en el Oficio de lectura, la
 *  lectura hagiográfica con su responsorio y la oración; en Laudes y
 *  Vísperas, después de la oración, la antífona y la oración del santo. */
function conmemora(secs, op, hora) {
  const L = E.horas;
  const delSantoOComun = (cl) => delSanto(op, hora, cl)
    || (L.comun_de[op.id] || []).map((k) => L.comunes[k + '/' + hora + '/' + cl])
      .find(Boolean) || null;
  const rub = (t) => [[1, t]];
  const tras = (cl) => {
    const i = secs.findIndex((s) => s.cl === cl);
    return i < 0 ? secs.length : i + 1;
  };
  const orac = delSantoOComun('oracion');
  if (hora === 'oficio') {
    const lec = delSantoOComun('lectura2');
    if (!lec) return;
    const resp = delSantoOComun('responsorio2');
    const extra = [fija('conm', 'Conmemoración: ' + op.t,
      [rub('Después de la lectura patrística se añade la del santo, con su '
        + 'responsorio, y se concluye con su oración.')]),
    fija('conm_lectura', lec.r, lec.l)];
    if (resp) extra.push(fija('conm_resp', resp.r, resp.l));
    secs.splice(tras(secs.some((s) => s.cl === 'responsorio2')
      ? 'responsorio2' : 'lectura2'), 0, ...extra);
    const o = secs.find((s) => s.cl === 'oracion');
    if (o && orac) o.alts = [{ id: 'propio', rot: '', c: orac }];
  } else if ((hora === 'laudes' || hora === 'visperas') && orac) {
    const cant = delSantoOComun('cantico_evangelico');
    const ant = cant ? cant.l.filter((ln) => ln.length && ln[0][0]
      && /^Ant/.test(ln[0][1])).slice(0, 1) : [];
    secs.splice(tras('oracion'), 0, fija('conm', 'Conmemoración: ' + op.t,
      [rub('Se omite la conclusión de la oración del día, y se añade:'), []]
        .concat(ant, [[]], orac.l)));
  }
}

/** Las secciones de una hora, con sus opciones. La cascada es la del libro
 *  —lo propio del santo; si no lo tiene, lo de su común; si no, lo del
 *  tiempo; la salmodia, del salterio; lo que no cambia, del ordinario—,
 *  pero ahora cada sección sabe además si se puede tomar de otro sitio. */
function armaHora(iso, hora, idCel) {
  if (!E.horasDias.dias[iso]) return null;
  // el año ferial (I o II), para la lectura bíblica del Oficio
  const d = Object.assign({ a: (anioDe(iso) || {}).ferial },
    E.horasDias.dias[iso]);
  const cels = celebracionesHoras(d);
  const op = cels.ops.find((o) => o.id === idCel)
    || cels.ops.find((o) => o.id === cels.def);
  let secciones = [];
  for (const cl of ordenDe(hora)) {
    const alts = opcionesSeccion(d, op, hora, cl);
    if (alts.length) {
      secciones.push({ cl: cl, alts: alts,
        i: eleccionDe(iso, op.id, hora, cl, alts, d) });
    }
  }
  // La reseña del santo o de la fiesta, al comienzo del Oficio de lectura,
  // como la trae el libro antes del oficio de cada celebración
  if (hora === 'oficio' && op.cel) {
    const r = delSanto(op, 'oficio', 'resena');
    if (r) secciones.unshift(fija('resena', null, r.l));
    if (r && r.f) secciones[0].alts[0].c.f = r.f;
  }
  // Laudes empiezan con el invitatorio, que ya trae «Señor, abre mis
  // labios»; la invocación sola, sólo cuando no lo hay
  if (secciones.some((s) => s.cl === 'invitatorio')) {
    secciones = secciones.filter((s) => s.cl !== 'invocacion');
  }
  if (op.modo === 'conmemoracion') conmemora(secciones, op, hora);
  for (const [resp, lect] of Object.entries(LIGADAS)) {
    const l = secciones.find((x) => x.cl === lect);
    const r = secciones.find((x) => x.cl === resp);
    if (l && r && r.alts.length > 1) {
      r.ligada = lect;
      sigueALaLectura(l, r);
    }
  }
  return { iso: iso, hora: hora, dia: d, cels: cels, op: op,
    secciones: secciones };
}

/* El texto va tal cual: la acentuación que se puede apagar en Ajustes es la
 * del latín, y quitarle las tildes al castellano sería estropearlo. */
function pintaSeccionHora(s, zoom) {
  const o = s.alts[s.i];
  const h = [];
  // lo que no está en la fuente y se tomó de los tomos impresos (la
  // traducción española) lo dice, en pequeño, junto al rótulo
  const ed = o.c.f === 'pdf'
    ? '<span class="ed-pdf" title="No está en la fuente de la app: se toma '
      + 'de la Liturgia de las Horas de la Conferencia Episcopal Española">'
      + 'ed. española</span>' : '';
  if (s.cl === 'resena') {
    return '<section class="hora-sec resena prosa" data-cl="resena">'
      + o.c.l.filter((ln) => ln.length).map((ln) => '<p>'
        + esc(ln.map((tr) => tr[1]).join('')) + '</p>').join('')
      + ed + '</section>';
  }
  // el responsorio breve no lleva selector: va con el de su lectura breve
  const selector = s.alts.length < 2 || s.ligada ? ''
    : '<div class="alterna" role="group" aria-label="'
      + (s.cl === 'himno' || s.cl === 'antifona_final'
        ? 'Elegir otro texto' : 'De dónde se toma') + '">'
      + s.alts.map((a, j) => '<button type="button" aria-pressed="'
        + (j === s.i) + '" data-op="' + esc(a.id) + '"'
        + (a.tit ? ' title="' + esc(a.tit) + '" aria-label="' + esc(a.rot
          + ': ' + a.tit) + '"' : '')
        + '>' + esc(a.rot) + '</button>').join('') + '</div>';
  if (o.c.r || selector || ed || zoom) {
    h.push('<div class="sec-cab"><h2 class="rotulo">' + esc(o.c.r || '')
      + ed + '</h2>' + selector + (zoom || '') + '</div>');
  }
  h.push(pintaLineas(o.c.l, PROSA.test(s.cl), s.cl));
  return '<section class="hora-sec' + (/^conm/.test(s.cl) ? ' conm' : '')
    + (PROSA.test(s.cl) ? ' prosa' : ' en-verso')
    + '" data-cl="' + esc(s.cl) + '">' + h.join('') + '</section>';
}

/* Lo que se lee —las lecturas, los responsorios, las preces, la oración—
 * va justificado, como en el libro. Lo que se canta o se recita en versos
 * —himnos, salmos, cánticos— va por renglones, con sangría francesa: si la
 * letra crece y un renglón se parte, la continuación entra y se sigue
 * viendo dónde empieza el siguiente. */
const PROSA = /^(lectura|responsorio|oracion|preces|examen|conm)/;

/** Palabras sin acentos ni signos, para comparar antífona y salmo. */
function palabrasDe(t) {
  return t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .match(/[a-z0-9]+/g) || [];
}

/* Cuando el salmo empieza con las mismas palabras que su antífona (con o sin
 * el «aleluya» del final), una cruz al final de la antífona y otra al
 * comienzo del renglón que sigue a lo repetido: dicha la antífona, se sigue
 * desde ahí. Medido en el libro, la antífona acaba siempre en fin de
 * renglón; si alguna acabara a media línea, no se marca. */
function cruces(lineas) {
  const fin = new Set(), ini = new Set();
  const salta = (n) => {            // renglones vacíos y rúbricas (títulos)
    while (n < lineas.length && (!lineas[n].length || lineas[n][0][0])) {
      if (esAntifona(lineas[n])) return -1;
      n++;
    }
    return n < lineas.length ? n : -1;
  };
  lineas.forEach((ln, i) => {
    if (!esAntifona(ln)) return;
    let j = i + 1;
    while (j < lineas.length && !lineas[j].length) j++;
    if (j >= lineas.length || !esTituloSalmo(lineas[j])) return;
    const a = palabrasDe(negro(ln));
    while (a.length && a[a.length - 1] === 'aleluya') a.pop();
    if (a.length < 2) return;
    let k = 0;
    for (let n = salta(j + 1); n >= 0; n = salta(n + 1)) {
      for (const w of palabrasDe(negro(lineas[n]))) {
        if (k >= a.length || w !== a[k]) return;   // otra cosa, o a media línea
        k++;
      }
      if (k === a.length) {
        const sigue = salta(n + 1);
        if (sigue >= 0) { fin.add(i); ini.add(sigue); }
        return;
      }
    }
  });
  return { fin: fin, ini: ini };
}

/* Cada prez son dos partes: la petición de quien preside y la respuesta de
 * todos. La fuente las separa con un renglón en blanco —dos líneas por
 * bloque— y los tomos impresos abren la respuesta con una raya; las dos
 * formas se reconocen, y la respuesta se marca para pegarla a su petición y
 * sangrarla entera. */
function respuestas(lineas) {
  const r = new Set();
  let n = 0;
  const cierra = (fin) => {
    if (n === 2) r.add(fin - 1);       // petición y respuesta: la segunda
    n = 0;
  };
  lineas.forEach((ln, i) => {
    if (!ln.length || !ln.some((tr) => tr[1].trim())) { cierra(i); return; }
    n++;
    if (/^\s*[—–-]\s/.test(ln.map((tr) => tr[1]).join(''))) r.add(i);
  });
  cierra(lineas.length);
  return r;
}

const CRUZ = '<span class="cruz" aria-hidden="true">†</span>';

function pintaLineas(lineas, prosa, seccion) {
  const marcas = cruces(lineas);
  const resp = seccion === 'preces' ? respuestas(lineas) : null;
  const bloques = [];
  let actual = [];
  const cierra = () => {
    if (actual.length) bloques.push(actual);
    actual = [];
  };
  lineas.forEach((ln, i) => {
    const t = ln.map((tr) => tr[0]
      ? '<b class="rub">' + esc(tr[1]) + '</b>' : esc(tr[1])).join('');
    if (!t.trim()) { cierra(); return; }
    let cl = 'ln';
    if (esTituloSalmo(ln)) cl += ' tit';
    else if (ln.every((tr) => tr[0] || !tr[1].trim())) cl += ' solo-rub';
    // los «V.» y los «R.» cuelgan de su sigla; la antífona no, que es un
    // texto seguido y la sangría le partía el renglón sin falta
    else if (ln[0][0] && /^\s*Ant/.test(ln[0][1])) cl += ' ant';
    else if (ln[0][0] && /^\s*(V\.|R\.)/.test(ln[0][1])) cl += ' sigla';
    if (resp && resp.has(i)) cl += ' prez-r';
    actual.push({ sigla: cl.includes(' sigla'),
      h: '<span class="' + cl + '">'
        + (marcas.ini.has(i) ? CRUZ + ' ' : '') + t
        + (marcas.fin.has(i) ? ' ' + CRUZ : '') + '</span>' });
  });
  cierra();
  return bloques.map((b) => {
    // El examen de conciencia es lo único de la prosa que trae una oración
    // escrita en renglones de sentido —el «Yo confieso»—, y ésa no se
    // justifica: partida en trozos cortos, el justificado la llena de ríos
    // de blanco. Va como los versos, a la izquierda y con sangría francesa.
    // Su primer párrafo, que sí es prosa seguida, es bloque de un renglón.
    const sentido = seccion === 'examen' && b.length > 1 && !b[0].sigla;
    return '<p class="estrofa-h' + (sentido ? ' sentido' : '') + '">'
      + b.map((x) => x.h).join('') + '</p>';
  }).join('');
}

/** El responsorio breve, de donde salga la lectura breve: la misma opción
 *  si la tiene, y si no, la primera. */
function sigueALaLectura(lectura, resp) {
  const i = resp.alts.findIndex((o) => o.id === lectura.alts[lectura.i].id);
  resp.i = i >= 0 ? i : 0;
}

/** Al tocar una opción se repinta sólo esa sección: repintar la hora
 *  entera devolvería la página arriba, a media oración. */
function alElegirOpcion(ev) {
  const b = ev.target.closest('.alterna button');
  if (!b || E.vista !== 'horas' || !E.oficio) return;
  const sec = b.closest('.hora-sec');
  const s = E.oficio.secciones.find((x) => x.cl === sec.dataset.cl);
  const i = s ? s.alts.findIndex((a) => a.id === b.dataset.op) : -1;
  if (i < 0 || i === s.i) return;
  s.i = i;
  const o = E.oficio;
  E.elecciones[claveEleccion(o.iso, o.op.id, o.hora, s.cl)] = s.alts[i].id;
  guardaElecciones();
  // la antífona de la Virgen que se elige una noche sale marcada la siguiente
  if (s.cl === 'antifona_final') {
    E.cfg.hAntFinal = claveIncipit(s.alts[i].c);
    guardaCfg();
  }
  repintaSeccion(sec, s).querySelector('[aria-pressed="true"]')
    .focus({ preventScroll: true });
  // y con la lectura se mueve su responsorio
  const rb = E.oficio.secciones.find((x) => x.ligada === s.cl);
  const caja = rb && document.querySelector('.hora-sec[data-cl="'
    + rb.cl + '"]');
  if (caja) { sigueALaLectura(s, rb); repintaSeccion(caja, rb); }
}

/** Cambia una sección por su versión nueva, sin tocar el resto de la hora. */
function repintaSeccion(caja, s) {
  const t = document.createElement('template');
  t.innerHTML = pintaSeccionHora(s);
  const nueva = t.content.firstElementChild;
  nueva.classList.add('cambia');
  caja.replaceWith(nueva);
  return nueva;
}

function pintaChipsCelebracionesHoras(o) {
  const c = $('#celebraciones');
  if (o.cels.ops.length < 2) { c.innerHTML = ''; return; }
  c.innerHTML = o.cels.ops.map((x) =>
    '<button aria-pressed="' + (x.id === o.op.id) + '" data-cel="'
    + esc(x.id) + '">' + esc(corto(x.t)) + '<small>'
    + esc(x.modo === 'feria' ? 'feria'
      : x.modo === 'conmemoracion' ? 'conmemoración' : bonito(x.g))
    + '</small></button>').join('');
}

/** El color del día, del calendario de la misa: el del santo si se reza
 *  su oficio, el del tiempo si no. */
function colorHoras(iso, titulo, op) {
  if (op && op.smv) return 'azul';
  if (esDeLaVirgen(titulo)) return 'azul';
  const val = entradasDe(iso);
  if (!val) return 'neutro';
  const e = val.c.find((x) => x[2] && x[2].t === titulo)
    || val.c.find((x) => x[2] && x[2].k === 't') || val.c[0];
  return E.colorDe.get(e[0]) || 'neutro';
}

function notaHoras(o) {
  const n = [], d = o.dia;
  if (d.x) {
    const g = bonito(d.x[1]).toLowerCase();
    n.push(d.x[0] + (d.x[0].toLowerCase().includes(g) ? '' : ' (' + g + ')')
      + ': no tengo sus textos, y el oficio sale de la feria.');
  }
  if (o.op.modo === 'conmemoracion') {
    n.push('En este tiempo la memoria sólo puede hacerse como '
      + 'conmemoración: en el Oficio de lectura se añade su lectura, y en '
      + 'Laudes y Vísperas, su antífona y su oración.');
  } else if (o.op.modo === 'memoria'
      && ['tercia', 'sexta', 'nona'].includes(o.hora)) {
    n.push('En la Hora intermedia no se hace mención de la memoria.');
  }
  if (o.op.cel && d.v && o.hora === 'visperas') {
    n.push('Las vísperas de hoy son las primeras del domingo.');
  }
  if (o.op.smv) {
    n.push('Memoria libre de Santa María Virgen en sábado: su oficio se '
      + 'toma del Común de la Virgen.');
    if (o.hora === 'visperas' || o.hora === 'completas') {
      n.push('No tiene vísperas: las del sábado son las primeras del '
        + 'domingo.');
    }
  }
  const p = $('#nota-dia');
  p.textContent = n.join(' ');
  p.style.display = n.length ? '' : 'none';
}

function pintaChipsHoras(iso, hora) {
  const hoy = iso === hoyISO() && E.cfg.rezadas !== 'no' && E.rezadas;
  // la tira de las horas ocupa el renglón entero, repartido; la de los
  // formularios de la misa, no: allí los rótulos son largos y se desliza
  $('#formularios').className = 'chips finos horas';
  $('#formularios').innerHTML = HORAS.map(([cl, , nombre, breve]) => {
    const es = cl === hora;
    const ya = hoy && E.rezadas.h[cl];
    const clases = (es ? 'sel' : '') + (ya ? ' rezada' : '');
    return '<button data-hora="' + cl + '"'
      + (clases.trim() ? ' class="' + clases.trim() + '"' : '')
      + ' aria-label="' + esc(nombre) + (ya ? ', rezada' : '') + '"'
      + '>' + esc(es ? nombre : breve) + '</button>';
  }).join('');
}

async function verHoras(iso, hora, idCel) {
  E.vista = 'horas';
  marcaBarra('horas');
  E.fecha = iso;
  E.hora = hora = hora || horaSugerida();
  $('#cabecera').classList.remove('compacta', 'portada');
  limpiaCabExtra();
  marcaHoy(iso);
  ponFecha(iso);
  $('#celebraciones').innerHTML = '';
  $('#nota-dia').style.display = 'none';
  vista.innerHTML = '<p class="aviso cargando">Abriendo el oficio…</p>';
  try {
    await cargaHoras();
  } catch (err) {
    vista.innerHTML = '<p class="aviso">No he podido cargar las horas ('
      + esc(err.message) + ').</p>';
    return;
  }
  const o = E.oficio = armaHora(iso, hora, idCel);
  pintaChipsHoras(iso, hora);
  if (!o) {
    E.horasCel = null;
    document.body.dataset.color = 'neutro';
    $('#titulo-dia').textContent = 'Sin oficio';
    $('#subtitulo-dia').textContent = '';
    vista.innerHTML = '<p class="aviso">Esta fecha cae fuera del calendario '
      + 'que trae la app (' + E.horasDias.rango[0] + '–'
      + E.horasDias.rango[1] + ').</p>';
    return;
  }
  // la celebración elegida viaja con la hora: pasar de Laudes a Vísperas
  // no debe devolver a quien reza al oficio que no escogió
  E.horasCel = o.cels.ops.length > 1 ? o.op.id : null;
  pintaChipsCelebracionesHoras(o);
  notaHoras(o);
  const d = o.dia;
  // la conmemoración no cambia el oficio, que sigue siendo de la feria: ni
  // su título ni su color
  const conm = o.op.modo === 'conmemoracion';
  document.body.dataset.color = colorHoras(iso, conm ? d.tt : o.op.t, o.op);
  $('#titulo-dia').textContent = HORAS.find((x) => x[0] === hora)[1];
  const partes = [conm ? d.tt : o.op.t];
  if (o.op.g && !conm) partes.push(bonito(o.op.g));
  if (d.p) partes.push('Salterio ' + ['', 'I', 'II', 'III', 'IV'][d.p]);
  $('#subtitulo-dia').textContent = partes.join(' · ');
  // el tamaño de la letra va en la fila del primer rótulo de la hora, a la
  // derecha; si lo primero es la reseña del santo, en el de la sección que
  // la sigue, que es donde empieza de verdad el oficio
  const iz = o.secciones.findIndex((x) => x.cl !== 'resena');
  vista.innerHTML = o.secciones.length
    ? o.secciones.map((x, i) => pintaSeccionHora(x, i === iz ? controlZoom() : ''))
      .join('')
    : '<p class="aviso">No tengo los textos de esta hora para este día.</p>';
  cabeceraFija(true);
  pintaCarril(o);
  colocaPosicion(() => vuelveADonde(E.donde));
}

/* ---------------------------------------------- el tamaño, a la mano
 * Que la letra se ve chica se nota al empezar a rezar, no en Ajustes: dos
 * aes al comienzo de la hora, discretas y a la derecha, y se sigue. Es el
 * mismo ajuste de siempre, así que queda puesto para todo. */
function controlZoom() {
  // sin el tanto por ciento: comparte renglón con el rótulo de la sección y
  // con su selector, y no cabe un número más. Lo que se cambia se ve solo.
  return '<div class="zoom" role="group" aria-label="Tamaño de la letra">'
    + '<button type="button" data-zoom="-5" aria-label="Letra más pequeña">'
    + 'A</button>'
    + '<button type="button" data-zoom="5" aria-label="Letra más grande">'
    + 'A</button></div>';
}

function alTocarZoom(ev) {
  const b = ev.target.closest('[data-zoom]');
  if (!b) return;
  const v = Math.min(200, Math.max(80, E.cfg.tam + Number(b.dataset.zoom)));
  if (v === E.cfg.tam) return;
  E.cfg.tam = v;
  guardaCfg();
  aplicaCfg();
  if (document.body.classList.contains('cab-fija')) mideCabecera();
}

/* ------------------------------------------------- el carril de la hora
 * Un breviario lleva cintas, y quien reza las usa: para volver a la
 * salmodia, para adelantar a la lectura. Aquí son una tira de rayas al
 * borde de la caja, una por sección; la de donde se va leyendo es más
 * larga y del color del día, y tocar cualquiera lleva a la suya. */
const NOMBRE_SEC = {
  resena: 'Reseña', invocacion: 'Invocación', invitatorio: 'Invitatorio',
  examen: 'Examen de conciencia', himno: 'Himno', himno2: 'Te Deum',
  salmodia: 'Salmodia', salmodia2: 'Salmodia', lectura1: 'Primera lectura',
  responsorio: 'Responsorio', lectura2: 'Segunda lectura',
  responsorio2: 'Responsorio', lectura12: 'Lectura',
  lectura_breve: 'Lectura breve', responsorio_breve: 'Responsorio breve',
  cantico_evangelico: 'Cántico evangélico', preces: 'Preces',
  oracion: 'Oración', oracion2: 'Oración', oracion3: 'Oración',
  conclusion: 'Conclusión', bendicion: 'Bendición',
  antifona_final: 'Antífona final', conm: 'Conmemoración',
  conm_lectura: 'Lectura del santo', conm_resp: 'Responsorio del santo'
};

function nombreSeccion(s) {
  if (NOMBRE_SEC[s.cl]) return NOMBRE_SEC[s.cl];
  const r = (s.alts[s.i].c.r || '').split(':')[0].trim();
  return r ? r.charAt(0) + r.slice(1).toLowerCase() : 'Sección';
}

function pintaCarril(o) {
  // con tres secciones la hora cabe de un vistazo y la cinta sobra
  if (E.cfg.carril === 'no' || !o || o.secciones.length < 4) {
    limpiaCarril();
    return;
  }
  const c = $('#carril');
  c.innerHTML = o.secciones.map((s) => {
    const n = esc(nombreSeccion(s));
    return '<button type="button" data-nombre="' + n + '" aria-label="Ir a '
      + n + '"></button>';
  }).join('');
  c.hidden = false;
  document.body.classList.add('con-carril');
  actualizaCarril();
}

function limpiaCarril() {
  const c = $('#carril');
  if (!c.hidden) { c.hidden = true; c.innerHTML = ''; }
  document.body.classList.remove('con-carril');
}

/** La raya de la sección que se está leyendo: la última que ha pasado por
 *  debajo de la cabecera; y al final del todo, la última de la hora. */
function actualizaCarril() {
  const c = $('#carril');
  if (c.hidden) return;
  const corte = $('#cabecera').getBoundingClientRect().bottom + 24;
  const secs = document.querySelectorAll('#vista .hora-sec');
  let n = 0;
  secs.forEach((s, i) => { if (s.getBoundingClientRect().top <= corte) n = i; });
  if (window.scrollY + window.innerHeight
      >= document.documentElement.scrollHeight - 4) n = secs.length - 1;
  c.querySelectorAll('button').forEach((b, i) => {
    if (i === n) b.setAttribute('aria-current', 'true');
    else b.removeAttribute('aria-current');
  });
}

/* Mientras dura el salto no se toca la cabecera: subir a una sección
 * anterior la haría crecer, y la sección quedaría debajo de ella. */
let _saltoHasta = 0;

function alTocarCarril(ev) {
  const b = ev.target.closest('button');
  if (!b || E.vista !== 'horas') return;
  const i = Array.prototype.indexOf.call($('#carril').children, b);
  const sec = document.querySelectorAll('#vista .hora-sec')[i];
  if (!sec) return;
  // se salta a un sitio lejano del texto: la cabecera se queda plegada,
  // que es como está al bajar, y el renglón cae justo debajo de ella
  ponPliegue(1);
  _saltoHasta = Date.now() + 800;
  sec.scrollIntoView({ block: 'start', behavior: suave() });
  setTimeout(() => { _saltoHasta = 0; alDesplazarCabecera(); }, 820);
}

/* --------------------------------------------------- deslizar de hora
 * Las siete horas son una cadena, y la cadena no se corta al acabar el
 * día: de Completas se pasa al Oficio de lectura del día siguiente, y al
 * revés. El gesto no se recoge donde ya hay algo que se desliza a dedo
 * —las tiras de la cabecera, los selectores, el carril—. */
let _dedo = null;

function alEmpezarGesto(ev) {
  _dedo = null;
  if (E.cfg.gestos === 'no' || E.vista !== 'horas'
      || ev.touches.length !== 1) return;
  if (ev.target.closest('.chips, .alterna, .carril, #cabecera, #barra, '
    + 'input, select, a')) return;
  const t = ev.touches[0];
  _dedo = { x: t.clientX, y: t.clientY, t: Date.now() };
}

function alAcabarGesto(ev) {
  const d = _dedo;
  _dedo = null;
  if (!d || E.vista !== 'horas' || !E.oficio) return;
  const t = ev.changedTouches[0];
  const dx = t.clientX - d.x;
  const dy = t.clientY - d.y;
  // ancho de sobra, más ancho que alto, y de una vez: un arrastre lento
  // es alguien buscando dónde poner el dedo, no un gesto
  if (Math.abs(dx) < 65 || Math.abs(dx) < Math.abs(dy) * 1.8) return;
  if (Date.now() - d.t > 700) return;
  otraHora(dx < 0 ? 1 : -1);
}

function otraHora(n) {
  const i = HORAS.findIndex((x) => x[0] === E.hora) + n;
  const iso = E.fecha || hoyISO();
  E.entraDesde = n > 0 ? 'izq' : 'der';
  // al cambiar de día no viaja la celebración elegida: es de aquel día
  if (i < 0) location.hash = '#/h/' + suma(iso, -1) + '/completas';
  else if (i >= HORAS.length) location.hash = '#/h/' + suma(iso, 1) + '/oficio';
  else {
    location.hash = '#/h/' + iso + '/' + HORAS[i][0]
      + (E.horasCel ? '/' + encodeURIComponent(E.horasCel) : '');
  }
}

/* --------------------------------------------------- lo ya rezado hoy
 * Un punto discreto en las horas que ya se han rezado hoy. No hay que
 * decírselo a la app: cuenta como rezada aquella cuyo final se ha llegado
 * a leer. Se guarda sólo el día de hoy, y cambiar de día lo olvida. */
function cargaRezadas() {
  E.rezadas = { d: hoyISO(), h: {} };
  try {
    const r = JSON.parse(localStorage.getItem('rezadas') || '{}');
    if (r && r.d === hoyISO() && r.h) E.rezadas = r;
  } catch (_) { /* sin almacenamiento: se marcan sólo en esta sesión */ }
}

function marcaRezada(hora) {
  if (E.cfg.rezadas === 'no' || !hora || E.fecha !== hoyISO()) return;
  if (E.rezadas.d !== hoyISO()) E.rezadas = { d: hoyISO(), h: {} };
  if (E.rezadas.h[hora]) return;
  E.rezadas.h[hora] = 1;
  try {
    localStorage.setItem('rezadas', JSON.stringify(E.rezadas));
  } catch (_) {}
  pintaChipsHoras(E.fecha, E.hora);
}

/* El carril y la marca de lo rezado miran dónde va la página, y mirarlo
 * cuesta un reflujo: se hace una vez por cuadro y no una por cada aviso de
 * desplazamiento, que en un dedo largo son decenas. */
let _enDesplazamiento = false;
function alDesplazarHoras() {
  if (E.vista !== 'horas' || _enDesplazamiento) return;
  _enDesplazamiento = true;
  requestAnimationFrame(() => {
    _enDesplazamiento = false;
    actualizaCarril();
    miraSiSeAcabo();
  });
}

/** Al llegar al final de la hora, queda rezada. */
function miraSiSeAcabo() {
  if (E.vista !== 'horas' || E.cfg.rezadas === 'no') return;
  if (window.scrollY + window.innerHeight
      >= document.documentElement.scrollHeight - 120) marcaRezada(E.hora);
}

/** A qué hora del día corresponde la hora del reloj. */
function horaSugerida() {
  const h = new Date().getHours();
  if (h < 6) return 'oficio';
  if (h < 9) return 'laudes';
  if (h < 12) return 'tercia';
  if (h < 15) return 'sexta';
  if (h < 17) return 'nona';
  if (h < 21) return 'visperas';
  return 'completas';
}

/* ------------------------------------------------------------------ rutas */
function enruta() {
  guardaPosicion();
  E.claveVista = null;        // la pone la vista nueva cuando acaba de pintarse
  const h = location.hash.slice(2);
  const p = h.split('/').map(decodeURIComponent);
  if (p[0] === 'indice') return verIndice();
  if (p[0] === 'calendario') return verCalendario(p[1]);
  if (p[0] === 'buscar') return verBusqueda(p[1] || '');
  if (p[0] === 'ajustes') return verAjustes();
  if (p[0] === 'f' && p[1]) {
    E.vista = 'hoy';
    marcaBarra('hoy');
    $('#cabecera').classList.remove('compacta', 'portada');
    limpiaCabExtra();
    marcaHoy(null);
    $('#nota-dia').style.display = 'none';
    return pintaFormulario(p[1], +(p[2] || 0), null, null, null);
  }
  if (p[0] === 'menu') return verPortada();
  if (p[0] === 'misa') return verDia(hoyISO());
  if (p[0] === 'h') return verHoras(p[1] || hoyISO(), p[2], p[3]);
  if (p[0] === 'd' && p[1]) return verDia(p[1], p[2], p[3] ? +p[3] : undefined);
  if (E.cfg.inicio === 'misa') return verDia(hoyISO());
  if (E.cfg.inicio === 'horas') return verHoras(hoyISO());
  return verPortada();
}

/* ------------------------------------------------------------- arranque */
async function arranca() {
  cargaCfg();
  cargaElecciones();
  cargaRezadas();
  aplicaCfg();
  try {
    const [ind, cal] = await Promise.all([json('indice.json'),
      json('calendario.json')]);
    E.indice = ind; E.cal = cal;
    indexaIndice();
    await cargaLecturas(E.cfg.fuente);
  } catch (err) {
    vista.innerHTML = '<p class="aviso">No he podido cargar los textos ('
      + esc(err.message) + '). Si has abierto el fichero con doble clic, '
      + 'el navegador no deja leer los datos: hay que servir la carpeta '
      + '(ver LEEME.md).</p>';
    return;
  }

  window.addEventListener('hashchange', () => {
    if (E.ignoraHash) { E.ignoraHash = false; return; }
    enruta();
  });
  vista.addEventListener('change', alCambiarAjuste);
  vista.addEventListener('click', alElegirOpcion);
  vista.addEventListener('click', alTocarZoom);
  vista.addEventListener('click', alTocarCalendario);
  vista.addEventListener('input', (ev) => {
    if (ev.target.id === 'aj-tam') alCambiarAjuste(ev);
  });
  document.querySelectorAll('#barra button').forEach((b) =>
    b.addEventListener('click', () => {
      const ir = b.dataset.ir;
      const fecha = E.fecha || hoyISO();
      // Misa y Horas vuelven a lo que se estaba leyendo: la misma misa, la
      // misma hora con la misma celebración (y, si es el mismo día, al
      // mismo renglón)
      const misa = E.ultimaMisa && E.ultimaMisa.startsWith('#/d/' + fecha)
        ? E.ultimaMisa : '#/d/' + fecha;
      const horas = '#/h/' + fecha + (E.hora ? '/' + E.hora
        + (E.horasCel ? '/' + encodeURIComponent(E.horasCel) : '') : '');
      const destino = ir === 'portada' ? '#/menu'
        : ir === 'hoy' ? misa
        : ir === 'horas' ? horas
        : '#/' + ir;
      // tocar la sección en la que ya se está la sube al principio
      if (location.hash === destino) {
        window.scrollTo({ top: 0, behavior: suave() });
      } else {
        location.hash = destino;
      }
    }));
  const otroDia = (n) => {
    const iso = suma(E.fecha || hoyISO(), n);
    location.hash = E.vista === 'horas'
      ? '#/h/' + iso + '/' + (E.hora || '') : '#/d/' + iso;
  };
  $('#anterior').addEventListener('click', () => otroDia(-1));
  $('#siguiente').addEventListener('click', () => otroDia(1));
  const selector = $('#selector-fecha');
  selector.addEventListener('change', () => {
    if (!selector.value) return;
    location.hash = E.vista === 'horas'
      ? '#/h/' + selector.value + '/' + (E.hora || '')
      : '#/d/' + selector.value;
  });
  const alPulsarChip = (ev) => {
    const b = ev.target.closest('button');
    if (!b) return;
    if (b.dataset.hora) {
      location.hash = '#/h/' + (E.fecha || hoyISO()) + '/' + b.dataset.hora
        + (E.horasCel ? '/' + encodeURIComponent(E.horasCel) : '');
      return;
    }
    if (b.dataset.cel) {
      location.hash = '#/h/' + (E.fecha || hoyISO()) + '/' + E.hora + '/'
        + encodeURIComponent(b.dataset.cel);
      return;
    }
    const iso = E.vista === 'hoy' ? E.fecha : null;
    location.hash = iso
      ? '#/d/' + iso + '/' + encodeURIComponent(b.dataset.slug) + '/' + b.dataset.bloque
      : '#/f/' + encodeURIComponent(b.dataset.slug) + '/' + b.dataset.bloque;
  };
  $('#celebraciones').addEventListener('click', alPulsarChip);
  $('#formularios').addEventListener('click', alPulsarChip);
  $('#ir-hoy').addEventListener('click', () => {
    const hoy = hoyISO();
    location.hash = E.vista === 'horas'
      ? '#/h/' + hoy + '/' + (E.hora || '') : '#/d/' + hoy;
  });
  // el calendario: su barra resumida vive en la cabecera
  $('#cab-extra').addEventListener('click', alTocarCalendario);
  vista.addEventListener('input', alEscribirCalendario);
  window.addEventListener('scroll', () => {
    alDesplazarCalendario();
    alDesplazarCabecera();
    alDesplazarHoras();
  }, { passive: true });
  $('#carril').addEventListener('click', alTocarCarril);
  document.addEventListener('touchstart', alEmpezarGesto, { passive: true });
  document.addEventListener('touchend', alAcabarGesto, { passive: true });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) velaPantalla();
  });
  window.addEventListener('resize', () => {
    if (document.body.classList.contains('cab-fija')) mideCabecera();
    if (E.vista !== 'calendario') return;
    document.documentElement.style.setProperty('--alto-cabecera',
      $('#cabecera').offsetHeight + 'px');
    alDesplazarCalendario();
  });

  // La app instalada se quedó clavada en vertical porque el manifiesto lo
  // decía, y el manifiesto se lee al instalarla: cambiarlo no basta para la
  // que ya está puesta. Esto suelta el cierre desde dentro.
  if (screen.orientation && screen.orientation.unlock) {
    try { screen.orientation.unlock(); } catch (_) { /* no deja: paciencia */ }
  }

  enruta();

  vigilaActualizaciones();
}

/* --------------------------------------------------------- actualizarse
 * La app instalada en el teléfono no se actualiza sola por arte de magia: el
 * service worker guarda todo en caché precisamente para abrir sin conexión.
 * Lo que hace que se entere de un cambio es preguntar —al arrancar y al
 * volver a primer plano— si hay una versión nueva. Cuando la hay, el worker
 * nuevo toma el control (skipWaiting) y aquí se recarga la página una sola
 * vez, para que los datos viejos que ya estaban en memoria no sobrevivan.
 */
function vigilaActualizaciones() {
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('sw.js').then((reg) => {
    const mira = () => { reg.update().catch(() => {}); };
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) mira();
    });
    window.addEventListener('online', mira);
    setTimeout(mira, 3000);
  }).catch(() => {});

  let recargando = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    // sólo cuando ya había uno: la primera instalación no necesita recargar
    if (recargando || !E.controlada) return;
    recargando = true;
    location.reload();
  });
  E.controlada = !!navigator.serviceWorker.controller;
}

arranca();
