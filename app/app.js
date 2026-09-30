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
  memorias: 'santo', inicio: 'menu', hLibre: 'santo', hComun: 'comun'
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
  vista: 'hoy'
};

const $ = (s) => document.querySelector(s);
const vista = $('#vista');

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

function fechaLarga(iso) {
  const d = new Date(iso + 'T12:00:00');
  const s = d.toLocaleDateString('es', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  });
  return s.charAt(0).toUpperCase() + s.slice(1);
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
  document.body.dataset.tema = E.cfg.tema;
  document.documentElement.style.setProperty(
    '--cuerpo', (E.cfg.tam / 100 * 1.0625).toFixed(3) + 'rem');
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
function celebracionesDe(val) {
  const cs = [];
  val.c.forEach(([slug, bloque, m], i) => {
    const d = E.diaDe.get(slug);
    if (d) cs.push({ slug: slug, bloque: bloque, dia: d, m: m, orden: i });
  });
  if (E.cfg.memorias === 'feria' && cs.length > 1
      && cs[0].m.k === 's' && cs[0].m.r >= 10) {
    const i = cs.findIndex((c) => c.m.f && !c.m.z);
    if (i > 0) cs.unshift(cs.splice(i, 1)[0]);
  }
  return cs;
}

/** Nombre corto para el chip: lo que va antes de la primera coma. */
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
  document.body.dataset.color = E.colorDe.get(slug) || 'neutro';
  $('#titulo-dia').textContent = d.t;
  const cel = (cels || []).find((o) => o.slug === slug);
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
  vista.scrollTop = 0;
  window.scrollTo(0, 0);
}

/* ------------------------------------------------------------ las vistas */
function verDia(iso, slug, bloque) {
  E.vista = 'hoy';
  marcaBarra('hoy');
  $('#cabecera').classList.remove('compacta', 'portada');
  $('#rotulo-fecha').textContent = fechaLarga(iso);
  $('#selector-fecha').value = iso;
  E.fecha = iso;
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
  const cels = celebracionesDe(val);
  if (!cels.length) { vista.innerHTML = '<p class="aviso">Nada que mostrar.</p>'; return; }
  let s = slug, b = bloque;
  const cel = cels.find((o) => o.slug === s);
  if (!cel) { s = cels[0].slug; b = cels[0].bloque; }
  else if (b === undefined) b = cel.bloque;
  pintaFormulario(s, b, iso, cels, val);
}

function modoPanel(titulo) {
  $('#cabecera').classList.add('compacta');
  $('#cabecera').classList.remove('portada');
  $('#titulo-dia').textContent = titulo;
  $('#subtitulo-dia').textContent = '';
  $('#celebraciones').innerHTML = '';
  $('#formularios').innerHTML = '';
  $('#nota-dia').style.display = 'none';
  document.body.dataset.color = 'neutro';
}

function verIndice() {
  E.vista = 'indice';
  marcaBarra('indice');
  modoPanel('Índice del año');
  const h = [];
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
  window.scrollTo(0, 0);
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
  marcaBarra('buscar');
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

function verAjustes() {
  E.vista = 'ajustes';
  marcaBarra('ajustes');
  modoPanel('Ajustes');
  const sel = (id, etiqueta, pista, ops) =>
    '<div class="ajuste"><label for="' + id + '">' + etiqueta
    + (pista ? '<span class="pista">' + pista + '</span>' : '')
    + '</label><select id="' + id + '">' + ops.map(([v, t]) =>
      '<option value="' + v + '"' + (E.cfg[id] === v ? ' selected' : '')
      + '>' + t + '</option>').join('') + '</select></div>';
  vista.innerHTML = [
    '<h2 class="seccion">Texto</h2>',
    sel('fuente', 'Versión latina',
      'La Nova Vulgata es el latín de los libros litúrgicos vigentes; la '
      + 'Clementina, la Vulgata de siempre.',
      [['clementina', 'Vulgata Clementina'], ['nova', 'Nova Vulgata']]),
    sel('acentos', 'Acentuación litúrgica',
      'El acento tónico marcado, como en los libros de coro.',
      [[true, 'Sí'], [false, 'No']]),
    sel('numeros', 'Números de versículo', '', [[true, 'Sí'], [false, 'No']]),
    '<div class="ajuste"><label for="tam">Tamaño de letra</label>'
    + '<input type="range" id="tam" min="80" max="170" step="5" value="'
    + E.cfg.tam + '"></div>',
    sel('tema', 'Aspecto', '',
      [['auto', 'Según el teléfono'], ['claro', 'Claro'],
        ['sepia', 'Sepia'], ['oscuro', 'Oscuro']]),
    sel('inicio', 'Al abrir la app',
      'La app lleva dentro dos libros. Si siempre vas al mismo, dilo aquí y '
      + 'no se te vuelve a preguntar.',
      [['menu', 'Preguntar'], ['misa', 'Las lecturas de la misa'],
        ['horas', 'La liturgia de las horas']]),
    '<h2 class="seccion">Calendario</h2>',
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
    '<h2 class="seccion">Liturgia de las Horas</h2>',
    sel('hLibre', 'En las memorias libres, rezar',
      'Una memoria libre se puede celebrar o dejar. Las dos opciones salen '
      + 'siempre arriba: esto sólo decide cuál viene marcada.',
      [['santo', 'El oficio del santo'], ['feria', 'El de la feria']]),
    sel('hComun', 'En las memorias, lo que no es propio',
      'Las rúbricas dejan tomarlo del común o del día, y cada sección lleva '
      + 'su selector: esto sólo decide cuál viene marcado.',
      [['comun', 'Del común'], ['dia', 'Del día']]),
    '<p class="pie">' + esc(E.lecturas.cabecera) + '<br><br>'
    + 'Calendario general romano y latinoamericano, con el propio y el común '
    + 'de los santos (leccionario V), las misas por diversas necesidades y '
    + 'votivas (VI) y las rituales y de difuntos (VIII). La concurrencia de '
    + 'celebraciones se resuelve con la Tabla de los días litúrgicos. '
    + 'El leccionario IX (misas con niños) no está incluido. '
    + 'Calendario de ' + E.cal.rango[0] + ' a ' + E.cal.rango[1] + '.'
    + '</p>'
  ].join('');

  window.scrollTo(0, 0);
}

/** Un solo oyente para todos los ajustes: la vista se repinta a menudo y
 *  colgar oyentes en cada repintado los iría acumulando. */
async function alCambiarAjuste(ev) {
  if (E.vista !== 'ajustes') return;
  const id = ev.target.id;
  if (!(id in E.cfg)) return;
  let v = ev.target.value;
  if (v === 'true' || v === 'false') v = (v === 'true');
  E.cfg[id] = id === 'tam' ? +v : v;
  guardaCfg();
  aplicaCfg();
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
  const hoy = cels.length ? (E.diaDe.get(cels[0].slug) || {}).t : null;
  const anio = anioDe(iso);
  const hora = HORAS.find((x) => x[0] === horaSugerida());

  vista.innerHTML = [
    '<p class="portada-fecha">' + esc(fechaLarga(iso)) + '</p>',
    hoy ? '<p class="portada-dia">' + esc(hoy) + '</p>' : '',
    '<div class="portada-elige">',
    '<a class="tarjeta" href="#/d/' + iso + '">',
    '<span class="tarjeta-icono">☩</span>',
    '<span class="tarjeta-t">Lecturas de la Misa</span>',
    '<span class="tarjeta-p">El leccionario romano en latín'
    + (anio ? ' · Ciclo ' + anio.ciclo + ' · Año ' + anio.ferial : '')
    + '</span>',
    '</a>',
    '<a class="tarjeta" href="#/h/' + iso + '">',
    '<span class="tarjeta-icono">☾</span>',
    '<span class="tarjeta-t">Liturgia de las Horas</span>',
    '<span class="tarjeta-p">El oficio divino en castellano · ahora, '
    + esc(hora[1]) + '</span>',
    '</a>',
    '</div>',
    '<nav class="portada-menudo">',
    '<a href="#/indice">Índice del año</a>',
    '<a href="#/buscar">Buscar</a>',
    '<a href="#/ajustes">Ajustes</a>',
    '</nav>'
  ].join('');
  window.scrollTo(0, 0);
}

/* ----------------------------------------------- la liturgia de las horas */
/* Las horas van en ficheros aparte y no se cargan hasta que se piden: son
 * 25 MB, y quien sólo venga a las lecturas no tiene por qué esperarlos. */
const HORAS = [
  ['oficio', 'Oficio de Lectura', 'Lectura'],
  ['laudes', 'Laudes', 'Laudes'],
  ['tercia', 'Tercia', 'Tercia'],
  ['sexta', 'Sexta', 'Sexta'],
  ['nona', 'Nona', 'Nona'],
  ['visperas', 'Vísperas', 'Vísperas'],
  ['completas', 'Completas', 'Completas']
];

async function cargaHoras() {
  if (E.horas) return;
  const [libro, dias] = await Promise.all(
    [json('horas.json'), json('horas_dias.json')]);
  E.horas = libro;
  E.horasDias = dias;
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
//   dia    del Propio del tiempo aunque la fuente traiga otra cosa: la
//          lectura bíblica del Oficio sólo es propia en las fiestas
//   (lo demás) del salterio, «excepto cuando tienen propios esos
//          elementos»: la salmodia
const EN_MEMORIA = {
  invitatorio: 'elige', himno: 'elige', lectura_breve: 'elige',
  responsorio_breve: 'elige', cantico_evangelico: 'elige', preces: 'elige',
  lectura2: 'santo', responsorio2: 'santo', oracion: 'santo',
  lectura1: 'dia', responsorio: 'dia'
};
// «En la Hora intermedia nunca se hace mención de las memorias de los
// santos», y Completas se toman siempre del salterio.
const SIN_MEMORIAS = ['tercia', 'sexta', 'nona', 'completas'];

function bonito(g) { return g ? g.charAt(0) + g.slice(1).toLowerCase() : ''; }

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
  // memorias libres: cualquiera de ellas, o la feria
  return {
    ops: cs.concat([feria]),
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

/** Lo del día: el propio del tiempo, el salterio y el ordinario. */
function delDia(d, hora, cl) {
  const L = E.horas;
  return pieza(L.tiempo, d.k + '/', hora, cl)
    || (cl === 'salmodia' && d.p
      && L.salterio[d.t + '/' + d.p + '/' + d.d + '/' + hora])
    || L.ordinario[d.t + '/' + hora + '/' + cl]
    || L.ordinario['@/' + hora + '/' + cl] || null;
}

function delSanto(op, hora, cl) {
  return pieza(E.horas.santoral, op.cel[1] + '/' + op.cel[0] + '/', hora, cl);
}

function deSusComunes(op, hora, cl) {
  const L = E.horas;
  return (L.comun_de[op.id] || []).map((k) => {
    const c = pieza(L.comunes, k + '/', hora, cl);
    return c && { id: 'c:' + k, rot: L.rotulo_comun[k] || 'Común', c: c };
  }).filter(Boolean);
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

/** Las opciones de una sección, cada una con su rótulo para el selector.
 *  Una sola, casi siempre; dos o tres, donde las rúbricas dejan elegir. */
function opcionesSeccion(d, op, hora, cl) {
  const dia = delDia(d, hora, cl);
  const soloDia = dia ? [{ id: 'dia', rot: 'Del día', c: dia }] : [];
  // el sábado, las vísperas son las primeras del domingo (lo dice `v`)
  const cedeVisperas = d.v && (hora === 'visperas' || hora === 'completas');
  let regla = 'dia';
  if (op.modo === 'entero' && !cedeVisperas) regla = 'entero';
  if (op.modo === 'memoria' && !cedeVisperas && !SIN_MEMORIAS.includes(hora)) {
    regla = EN_MEMORIA[cl] || 'salterio';
  }
  if (regla === 'dia') return soloDia;
  const propio = delSanto(op, hora, cl);
  if (propio) return [{ id: 'propio', rot: 'Propio', c: propio }];
  if (regla === 'salterio') return soloDia;
  const comunes = deSusComunes(op, hora, cl);
  if (regla === 'elige') return distintas(soloDia.concat(comunes));
  // solemnidades, fiestas y lo que en las memorias es del santo: del
  // propio o del común, y del día sólo si no hay otra cosa
  return comunes.length ? distintas(comunes) : soloDia;
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
function eleccionDe(iso, idCel, hora, cl, alts) {
  const guardada = E.elecciones[claveEleccion(iso, idCel, hora, cl)];
  let i = alts.findIndex((o) => o.id === guardada);
  if (i < 0) {
    i = alts.findIndex((o) =>
      E.cfg.hComun === 'dia' ? o.id === 'dia' : o.id !== 'dia');
  }
  return Math.max(0, i);
}

/** El orden de las secciones. La invocación inicial va delante (el orden
 *  recuperado del volcado la dejaba al final de Laudes), y el preámbulo
 *  del Oficio es el invitatorio con otra forma, que ya ocupa su sitio. */
function ordenDe(hora) {
  let o = (E.horas.orden[hora] || []).slice();
  if (hora === 'oficio') o = o.filter((cl) => cl !== 'preambulo');
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
  const d = E.horasDias.dias[iso];
  if (!d) return null;
  const cels = celebracionesHoras(d);
  const op = cels.ops.find((o) => o.id === idCel)
    || cels.ops.find((o) => o.id === cels.def);
  let secciones = [];
  for (const cl of ordenDe(hora)) {
    const alts = opcionesSeccion(d, op, hora, cl);
    if (alts.length) {
      secciones.push({ cl: cl, alts: alts,
        i: eleccionDe(iso, op.id, hora, cl, alts) });
    }
  }
  // Laudes empiezan con el invitatorio, que ya trae «Señor, abre mis
  // labios»; la invocación sola, sólo cuando no lo hay
  if (secciones.some((s) => s.cl === 'invitatorio')) {
    secciones = secciones.filter((s) => s.cl !== 'invocacion');
  }
  if (op.modo === 'conmemoracion') conmemora(secciones, op, hora);
  return { iso: iso, hora: hora, dia: d, cels: cels, op: op,
    secciones: secciones };
}

/* El texto va tal cual: la acentuación que se puede apagar en Ajustes es la
 * del latín, y quitarle las tildes al castellano sería estropearlo. */
function pintaSeccionHora(s) {
  const o = s.alts[s.i];
  const h = [];
  const selector = s.alts.length < 2 ? ''
    : '<div class="alterna" role="group" aria-label="De dónde se toma">'
      + s.alts.map((a, j) => '<button type="button" aria-pressed="'
        + (j === s.i) + '" data-op="' + esc(a.id) + '">' + esc(a.rot)
        + '</button>').join('') + '</div>';
  if (o.c.r || selector) {
    h.push('<div class="sec-cab"><h2 class="rotulo">' + esc(o.c.r || '')
      + '</h2>' + selector + '</div>');
  }
  let parrafo = [];
  const cierra = () => {
    if (parrafo.length) h.push('<p class="verso">' + parrafo.join('<br>') + '</p>');
    parrafo = [];
  };
  for (const ln of o.c.l) {
    const t = ln.map((tr) => tr[0]
      ? '<b class="rub">' + esc(tr[1]) + '</b>' : esc(tr[1])).join('');
    if (t.trim()) parrafo.push(t); else cierra();
  }
  cierra();
  return '<section class="hora-sec' + (/^conm/.test(s.cl) ? ' conm' : '')
    + '" data-cl="' + esc(s.cl) + '">' + h.join('') + '</section>';
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
  const t = document.createElement('template');
  t.innerHTML = pintaSeccionHora(s);
  const nueva = t.content.firstElementChild;
  nueva.classList.add('cambia');
  sec.replaceWith(nueva);
  nueva.querySelector('[aria-pressed="true"]').focus({ preventScroll: true });
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
function colorHoras(iso, titulo) {
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
  const p = $('#nota-dia');
  p.textContent = n.join(' ');
  p.style.display = n.length ? '' : 'none';
}

function pintaChipsHoras(iso, hora) {
  $('#formularios').innerHTML = HORAS.map(([cl, , corto]) =>
    '<button data-hora="' + cl + '"' + (cl === hora ? ' class="sel"' : '')
    + '>' + esc(corto) + '</button>').join('');
}

async function verHoras(iso, hora, idCel) {
  E.vista = 'horas';
  marcaBarra('horas');
  E.fecha = iso;
  E.hora = hora = hora || horaSugerida();
  $('#cabecera').classList.remove('compacta', 'portada');
  $('#rotulo-fecha').textContent = fechaLarga(iso);
  $('#selector-fecha').value = iso;
  $('#celebraciones').innerHTML = '';
  $('#nota-dia').style.display = 'none';
  vista.innerHTML = '<p class="aviso">Abriendo el oficio…</p>';
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
  document.body.dataset.color = colorHoras(iso, conm ? d.tt : o.op.t);
  $('#titulo-dia').textContent = HORAS.find((x) => x[0] === hora)[1];
  const partes = [conm ? d.tt : o.op.t];
  if (o.op.g && !conm) partes.push(bonito(o.op.g));
  if (d.p) partes.push('Salterio ' + ['', 'I', 'II', 'III', 'IV'][d.p]);
  $('#subtitulo-dia').textContent = partes.join(' · ');
  vista.innerHTML = o.secciones.length
    ? o.secciones.map(pintaSeccionHora).join('')
    : '<p class="aviso">No tengo los textos de esta hora para este día.</p>';
  vista.scrollTop = 0;
  window.scrollTo(0, 0);
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
  const h = location.hash.slice(2);
  const p = h.split('/').map(decodeURIComponent);
  if (p[0] === 'indice') return verIndice();
  if (p[0] === 'buscar') return verBusqueda(p[1] || '');
  if (p[0] === 'ajustes') return verAjustes();
  if (p[0] === 'f' && p[1]) {
    E.vista = 'hoy';
    marcaBarra('hoy');
    $('#cabecera').classList.remove('compacta', 'portada');
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
  vista.addEventListener('input', (ev) => {
    if (ev.target.id === 'tam') alCambiarAjuste(ev);
  });
  document.querySelectorAll('#barra button').forEach((b) =>
    b.addEventListener('click', () => {
      const ir = b.dataset.ir;
      const destino = ir === 'portada' ? '#/menu'
        : ir === 'hoy' ? '#/d/' + (E.fecha || hoyISO())
        : ir === 'horas' ? '#/h/' + (E.fecha || hoyISO())
        : '#/' + ir;
      if (location.hash === destino) enruta(); else location.hash = destino;
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
