/* -------------------------------------------- pruebas del devocionario
 * PROVISIONAL. Cuatro maneras de enseñar el mismo devocionario, para elegir
 * una. No toca los datos ni lo que hay en app.js: se monta encima,
 * sustituyendo las funciones que pintan la portada, el capítulo, la sección
 * y la fila, y una tira abajo cambia de prueba sin salir de donde se está.
 * «Antes» es lo de siempre, sin tocar. Cuando se elija una, lo elegido pasa
 * a app.js y este fichero y devo-pruebas.css se borran.
 *
 *   A · Índice sereno   el mismo árbol, con mucha menos tinta: los capítulos
 *                       en cuatro bandas, cada banda en su caja, migas de
 *                       pan arriba y las secciones grandes agrupadas.
 *   B · Mosaico         teselas con icono y un color por banda; dentro del
 *                       capítulo, pestañas en vez de un nivel más.
 *   C · Árbol plegable  todo en una página: el capítulo se abre en su sitio,
 *                       y su rótulo se queda pegado arriba mientras se baja.
 *   D · Para hoy        la portada empieza por lo de este momento —la hora
 *                       del día, el día de la semana, el tiempo o el mes— y
 *                       debajo, las de siempre a mano y el índice entero.
 */

const PD = [
  ['actual', 'Antes', 'Lo de ahora'],
  ['a', 'A', 'Índice sereno'],
  ['b', 'B', 'Mosaico'],
  ['c', 'C', 'Árbol plegable'],
  ['d', 'D', 'Para hoy']
];

function pdCual() {
  let v = null;
  try { v = localStorage.getItem('devoPrueba'); } catch (_) {}
  return PD.some((x) => x[0] === v) ? v : 'a';
}
function pdPon(v) {
  try { localStorage.setItem('devoPrueba', v); } catch (_) {}
}

/* Los once capítulos, en cuatro bandas: lo que se reza en la vida de cada
 * día, lo que va con el tiempo, a quién se reza y lo que se aprende. */
const PD_BANDAS = [
  ['La vida de cada día', ['comunes', 'dia', 'misa', 'confesion', 'necesidad'],
    '--lit-verde'],
  ['El tiempo', ['anio', 'horas'], '--lit-morado'],
  ['A quién se reza', ['dios', 'santos'], '--lit-azul'],
  ['Para aprender', ['escritura', 'doctrina'], '--lit-blanco']
];

function pdBandas() {
  const vistos = new Set();
  const bandas = PD_BANDAS.map(([t, claves, tono]) => ({
    t: t, tono: tono,
    caps: claves.map((k) => { vistos.add(k); return E.devoCap.get(k); })
      .filter(Boolean)
  }));
  // lo que el devocionario traiga de nuevo y aquí no esté, a la última
  const resto = E.devo.caps.filter((c) => !vistos.has(c.c));
  if (resto.length) bandas.push({ t: 'Otras', tono: '--acento', caps: resto });
  return bandas;
}

function pdTonoDe(clave) {
  const b = PD_BANDAS.find((x) => x[1].indexOf(clave) >= 0);
  return b ? b[2] : '--acento';
}

/* Los capítulos grandes, partidos por dentro: veinte secciones seguidas no
 * se leen; cuatro grupos de cinco, sí. */
const PD_SUB = {
  dios: [
    ['La Trinidad', ['La Santísima Trinidad', 'Dios Padre', 'El Espíritu Santo']],
    ['Jesucristo', ['Nuestro Señor Jesucristo', 'El Sagrado Corazón',
      'El santo Nombre', 'La santa Cruz', 'La Pasión',
      'La Preciosísima Sangre', 'La Divina Misericordia',
      'El Santísimo Sacramento']]
  ],
  santos: [
    ['La Virgen María', ['La Santísima Virgen', 'La Inmaculada', 'Los Dolores',
      'La Virgen del Carmen', 'Las antífonas finales']],
    ['San José y la Sagrada Familia', ['San José', 'La Sagrada Familia']],
    ['Los ángeles', ['El ángel de la guarda', 'San Miguel', 'San Gabriel',
      'San Rafael', 'Los ángeles']],
    ['Los santos', ['Todos los santos', 'San Agustín', 'San Antonio de Padua',
      'San Benito', 'San Francisco de Asís', 'San Patricio', 'Santa Ana',
      'Santa Escolástica']]
  ],
  anio: [
    ['Navidad', ['Adviento', 'Navidad', 'Epifanía']],
    ['Pascua', ['Cuaresma', 'Triduo', 'Pascua', 'Pentecostés']],
    ['Las fiestas', ['Corpus Christi', 'Todos los Santos']]
  ]
};

function pdGrupos(c) {
  const def = PD_SUB[c.c];
  if (!def) return null;
  const usadas = new Set();
  const grupos = def.map(([t, nombres]) => ({
    t: t,
    secs: nombres.map((n) => c.secs.find((s) => s.s === n)).filter((s) => {
      if (s) usadas.add(s.s);
      return !!s;
    })
  })).filter((g) => g.secs.length);
  const resto = c.secs.filter((s) => !usadas.has(s.s));
  if (resto.length) grupos.push({ t: 'Otras', secs: resto });
  return grupos;
}

/* Un icono por capítulo, del mismo trazo que los de la barra. */
const PD_ICONO = {
  comunes: svg('<path d="M5 6.5h14M5 10.5h14M5 14.5h8"/><path d="M17 13v7.5M14.5 15.5h5"/>'),
  dia: svg('<path d="M7 16.5a5 5 0 0 1 10 0"/><path d="M3 16.5h18M6 20h12M12 6.5v3M5.6 10l1.8 1.6M18.4 10l-1.8 1.6"/>'),
  misa: svg('<path d="M7 3.5h10c0 5.2-2.2 8.2-5 8.2S7 8.7 7 3.5Z"/><path d="M12 11.7v6.3M8 20.5h8"/>'),
  confesion: svg('<circle cx="8" cy="12" r="3.6"/><path d="M11.6 12H20.5M17.3 12v3M20.3 12v2.5"/>'),
  anio: svg('<path d="M8 20.5V11M12 20.5V9M16 20.5V11"/><path d="M8 8.4c-.8-.8-.8-1.8 0-2.8.8 1 .8 2 0 2.8ZM12 6.4c-.8-.8-.8-1.8 0-2.8.8 1 .8 2 0 2.8ZM16 8.4c-.8-.8-.8-1.8 0-2.8.8 1 .8 2 0 2.8Z"/><path d="M5 20.5h14"/>'),
  horas: svg('<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3.4 2.1"/>'),
  dios: svg('<path d="M12 4.5 20 18.5H4Z"/><circle cx="12" cy="13.5" r="1.6"/>'),
  santos: svg('<ellipse cx="12" cy="4.6" rx="4.6" ry="1.6"/><circle cx="12" cy="11" r="3.4"/><path d="M5.2 20.5c.8-3.5 3.5-5.4 6.8-5.4s6 1.9 6.8 5.4"/>'),
  necesidad: svg('<path d="M12 19.5s-7-4.3-7-9.7A3.9 3.9 0 0 1 12 7.4a3.9 3.9 0 0 1 7 2.4c0 5.4-7 9.7-7 9.7Z"/>'),
  escritura: svg('<path d="M5 4.5h10.5a3 3 0 0 1 3 3v12H8a3 3 0 0 1-3-3Z"/><path d="M5 16.5a3 3 0 0 1 3-3h10.5M9 8h6M9 10.5h4"/>'),
  doctrina: svg('<path d="M4.5 20V8.5a3.5 3.5 0 0 1 7 0V20ZM12.5 20V8.5a3.5 3.5 0 0 1 7 0V20Z"/><path d="M6.5 11h3M6.5 14h3M14.5 11h3M14.5 14h3"/>'),
  compendio: ICONO.devocionario,
  estrella: ICONO.estrella
};

/* -------------------------------------------------- piezas comunes */

/** Las migas de pan: de dónde cuelga lo que se está viendo. */
function pdMigas(pasos) {
  return '<nav class="pd-migas" aria-label="Dónde estás">' + pasos.map(
    ([href, t]) => '<a href="' + href + '">' + esc(t) + '</a>')
    .join(ICONO.der) + '</nav>';
}

function pdEnlaceSec(clave, sec) {
  return '#/oraciones/s/' + encodeURIComponent(clave) + '/'
    + encodeURIComponent(sec);
}
function pdEnlaceCap(clave) {
  return '#/oraciones/c/' + encodeURIComponent(clave);
}

/** Un capítulo de más de cuarenta oraciones tiene una página por sección;
 *  uno corto las enseña todas en la suya. */
function pdSeccionConPagina(c) { return c.n > 40 && c.secs.length > 3; }

function pdPasosDe(p) {
  const c = E.devoCap.get(p.c);
  const pasos = [['#/oraciones', 'Devocionario']];
  if (!c) return pasos;
  pasos.push([pdEnlaceCap(p.c), c.t]);
  if (p.s && pdSeccionConPagina(c)) pasos.push([pdEnlaceSec(p.c, p.s), p.s]);
  return pasos;
}

/** La fila. Lo que se dice sin abrir la oración, y nada más: el título
 *  latino; el castellano debajo, cuando lo hay —y eso mismo dice que lo
 *  hay—; y qué es, sólo si no es una oración, que es lo que son casi todas. */
function pdFila(p, ctx, num, sinEstrella) {
  const meta = [];
  if (p.f !== 'oración' && p.f !== pdCalla) meta.push(esc(p.f));
  if (p.hora) meta.push(esc(devoHora(p)));
  if (p.comp && !num) meta.push('Compendio');
  return '<a class="pd-fila" href="#/oraciones/o/' + esc(p.id) + '">'
    + (num ? '<span class="pd-num">' + num + '</span>' : '')
    + '<span class="pd-fila-c">'
    + (ctx ? '<span class="pd-ctx">' + esc(ctx) + '</span>' : '')
    + '<span class="pd-la" lang="la">' + esc(tx(p.tla))
    + (p.dist ? ' <span class="pd-dist">' + esc(p.dist) + '</span>' : '')
    + (!sinEstrella && esFavorita(p.id) ? '<span class="pd-estrella" '
      + 'title="Favorita">' + ICONO.estrella + '</span>' : '')
    + '</span>'
    + (p.tes ? '<span class="pd-es">' + esc(p.tes) + '</span>' : '')
    + (meta.length ? '<span class="pd-meta">' + meta.join(' · ') + '</span>'
      : '')
    + '</span></a>';
}

function pdFilaCol(partes) {
  const p = partes[0];
  const meta = [partes.length + ' ' + (p.colq || 'partes')];
  if (devoPlural(p.f) !== p.colq) meta.push(devoPlural(p.f));
  return '<a class="pd-fila pd-fila-col" href="#/oraciones/k/'
    + encodeURIComponent(p.col) + '"><span class="pd-fila-c">'
    + '<span class="pd-la">' + esc(p.colt) + '</span>'
    + '<span class="pd-meta">' + esc(meta.join(' · ')) + '</span>'
    + '</span></a>';
}

/* La forma que se calla en la fila porque la lista entera es de ella: en
 * el himnario, «himno» en cada renglón no dice nada. */
let pdCalla = null;

function pdLista(piezas, rot, opc) {
  return '<div class="pd-lista"' + (rot ? ' data-rot="' + esc(rot) + '"' : '')
    + '>' + devoLista(piezas, opc) + '</div>';
}

function pdBanda(t, n) {
  return '<h2 class="pd-banda">' + esc(t)
    + (n ? ' <span class="pd-n">' + n + '</span>' : '') + '</h2>';
}

function pdY(nombres) {
  return nombres.length < 2 ? nombres.join('')
    : nombres.slice(0, -1).join(', ') + ' y ' + nombres[nombres.length - 1];
}

/** Las oraciones de un capítulo con sus secciones dentro. Una sección de
 *  tres o más lleva su rótulo y su caja; las menudas seguidas —Prima,
 *  Tercia, Sexta y Nona, de una cada una— van juntas en una caja, y cada
 *  fila dice la suya. Y si casi todas son menudas, como en «En cada
 *  necesidad», una sola lista. */
function pdListaConSecciones(c, piezas, ids, secs) {
  secs = secs || c.secs;
  const de = (s) => piezas.filter((p) => p.s === s.s);
  const h = [];
  const sueltas = piezas.filter((p) => !p.s);
  if (sueltas.length) h.push(pdLista(sueltas, c.t, { ids: ids }));
  if (!secs.length) return h.join('');
  const n = secs.reduce((a, s) => a + s.n, 0);
  if (n / secs.length < 2.5) {
    h.push(pdLista(secs.flatMap(de), c.t, { ids: ids, ctx: (p) => p.s }));
    return h.join('');
  }
  let menudas = [];
  const vacia = () => {
    if (!menudas.length) return;
    const nombres = menudas.map((s) => s.s);
    if (menudas.length === 1) {
      h.push(pdBanda(nombres[0], menudas[0].n)
        + pdLista(de(menudas[0]), nombres[0], { ids: ids }));
    } else {
      h.push((menudas.length <= 4 ? pdBanda(pdY(nombres)) : '')
        + pdLista(menudas.flatMap(de), pdY(nombres),
          { ids: ids, ctx: (p) => p.s }));
    }
    menudas = [];
  };
  for (const s of secs) {
    if (s.n >= 3) {
      vacia();
      h.push(pdBanda(s.s, s.n) + pdLista(de(s), s.s, { ids: ids }));
    } else menudas.push(s);
  }
  vacia();
  return h.join('');
}

/** La fila de una sección en el índice de un capítulo grande. La que tiene
 *  una sola oración lleva derecho a ella: una lista de una no es un sitio. */
function pdFilaSec(c, s) {
  const piezas = E.devo.piezas.filter((p) => p.c === c.c && p.s === s.s);
  let href = pdEnlaceSec(c.c, s.s);
  if (piezas.length === 1) href = '#/oraciones/o/' + piezas[0].id;
  else if (piezas.length && piezas.every((p) => p.col && p.col === piezas[0].col)) {
    href = '#/oraciones/k/' + encodeURIComponent(piezas[0].col);
  }
  return '<a class="pd-sec" href="' + href + '"><span class="pd-sec-t">'
    + esc(s.s) + '</span><span class="pd-n">' + s.n + '</span></a>';
}

function pdIndiceSecciones(c) {
  const grupos = pdGrupos(c) || [{ t: null, secs: c.secs }];
  return grupos.map((g) => (g.t ? pdBanda(g.t,
    g.secs.reduce((a, s) => a + s.n, 0)) : '')
    + '<div class="pd-lista">' + g.secs.map((s) => pdFilaSec(c, s)).join('')
    + '</div>').join('');
}

function pdFilaCap(c, conPista) {
  return '<a class="pd-cap-fila" href="' + pdEnlaceCap(c.c) + '">'
    + '<span class="pd-cap-c"><span class="pd-cap-t">' + esc(c.t) + '</span>'
    + (conPista ? '<span class="pd-cap-p">' + esc(c.p) + '</span>' : '')
    + '</span><span class="pd-n">' + c.n + '</span></a>';
}

function pdNumEs() { return E.devo.piezas.filter((p) => p.es).length; }

/** Las otras dos entradas, que no son capítulos: por lo que es cada pieza
 *  y las que ya tienen castellano. */
function pdOtrasEntradas() {
  return pdBanda('Otras maneras de buscar') + '<div class="pd-lista">'
    + '<a class="pd-cap-fila" href="#/oraciones/f"><span class="pd-cap-c">'
    + '<span class="pd-cap-t">Por tipo de oración</span>'
    + '<span class="pd-cap-p">Himnos, letanías, novenas, salmos…</span>'
    + '</span><span class="pd-n">' + E.devo.formas.length + '</span></a>'
    + '<a class="pd-cap-fila" href="' + devoEnlaceFiltro(null, 'es') + '">'
    + '<span class="pd-cap-c"><span class="pd-cap-t">Con su castellano</span>'
    + '<span class="pd-cap-p">Las que ya tienen la traducción verificada</span>'
    + '</span><span class="pd-n">' + pdNumEs() + '</span></a></div>';
}

function pdFavoritasArriba(ids, conBanda) {
  const favs = devoFavoritas();
  if (!favs.length) return '';
  for (const p of favs) ids.push(p.id);
  return (conBanda ? pdBanda('Favoritas') : '')
    + pdLista(favs.slice(0, 5), 'Favoritas', { sinPlegar: true,
      sinEstrella: true, ctx: (p) => devoDondeVive(p) })
    + (favs.length > 5 ? '<a class="pd-mas" href="#/oraciones/m">Todas las '
      + 'favoritas (' + favs.length + ')' + ICONO.der + '</a>' : '');
}

/** El buscador, con lo que haya debajo cuando no se busca nada. `pinta`
 *  es una función, porque el árbol plegable cambia mientras se usa y al
 *  borrar la búsqueda tiene que volver como se dejó. */
function pdBuscador(pinta, vuelta, alPintar) {
  vista.innerHTML = '<div class="devo-busca pd-busca">' + ICONO.buscar
    + '<input class="campo" id="devo-q" type="search" '
    + 'placeholder="Buscar una oración, en latín o en castellano" '
    + 'aria-label="Buscar una oración" autocomplete="off"></div>'
    + '<div id="devo-res">' + pinta() + '</div>';
  const campo = $('#devo-q');
  const caja = $('#devo-res');
  if (alPintar) alPintar(caja);
  const busca = () => {
    E.devoQ = campo.value;
    const q = plano(campo.value.trim());
    if (q.length < 2) {
      caja.innerHTML = pinta();
      E.devoVuelta = vuelta;
      return;
    }
    const hay = E.devo.piezas.filter((p) => p.k.includes(q)).slice(0, 60);
    const ids = [];
    caja.innerHTML = hay.length
      ? '<p class="pd-intro">' + (hay.length === 60 ? 'Las 60 primeras'
        : devoCuenta(hay)) + '</p>'
        + pdLista(hay, null, { sinPlegar: true,
          ctx: (p) => devoDondeVive(p), ids: ids })
      : '<p class="aviso">Ninguna oración se llama así. La búsqueda ignora '
      + 'acentos y desata æ/œ, y entiende lo que la pieza es: «letanía», '
      + '«himno», «novena».</p>';
    E.devoVuelta = { ids: ids, href: '#/oraciones', rot: 'La búsqueda' };
  };
  E.devoVuelta = vuelta;
  campo.addEventListener('input', busca);
  if (E.devoQ) { campo.value = E.devoQ; busca(); }
}

/** En las pruebas donde una página tiene varias listas (el árbol, las
 *  tarjetas de hoy), «anterior» y «siguiente» recorren la lista donde se
 *  tocó, no la página entera. */
function pdVueltaAlTocar(caja) {
  caja.addEventListener('click', (ev) => {
    const a = ev.target.closest('a.pd-fila[href^="#/oraciones/o/"]');
    const l = a && a.closest('.pd-lista[data-rot]');
    if (!l) return;
    const ids = [...l.querySelectorAll('a.pd-fila[href^="#/oraciones/o/"]')]
      .map((x) => x.getAttribute('href').split('/').pop());
    E.devoVuelta = { ids: ids, rot: l.dataset.rot, href: location.hash };
  });
}

function pdAltoCab() { return $('#cabecera').offsetHeight; }

/* Dónde se dejó cada lista. La app guarda una posición por vista, y la
 * oración y la lista de la que se viene son la misma vista: al volver de una
 * oración, la lista empezaba arriba. Aquí se guarda por dirección. */
const pdPos = {};
function pdColoca(siNo) {
  colocaPosicion(() => {
    const y = pdPos[location.hash];
    if (y != null) { window.scrollTo(0, y); return; }
    return siNo ? siNo() : false;
  });
}

/* ----------------------------------------------- A · índice sereno */

function pdPuertaCompendio() {
  const n = E.devo.piezas.filter((p) => p.comp).length;
  if (!n) return '';
  return '<a class="pd-puerta" href="#/oraciones/p">'
    + '<span class="pd-cap-c"><span class="pd-puerta-ojo">Para empezar</span>'
    + '<span class="pd-cap-t">Las oraciones del Compendio</span></span>'
    + '<span class="pd-n">' + n + '</span></a>';
}

function pdPortadaA() {
  modoPanel('Devocionario');
  $('#subtitulo-dia').textContent = E.devo.piezas.length + ' oraciones';
  const idsFav = [];
  const fav = pdFavoritasArriba(idsFav, true);
  const html = fav + pdPuertaCompendio()
    + pdBandas().map((b) => pdBanda(b.t) + '<div class="pd-lista">'
      + b.caps.map((c) => pdFilaCap(c, true)).join('') + '</div>').join('')
    + pdOtrasEntradas();
  pdBuscador(() => html, { ids: idsFav, href: '#/oraciones', rot: 'Favoritas' });
  pdColoca();
}

function pdCapituloA(clave) {
  const c = E.devoCap.get(clave);
  if (!c) return pdPortada();
  modoPanel(c.t);
  const piezas = E.devo.piezas.filter((p) => p.c === clave);
  const ids = [];
  const h = [pdMigas([['#/oraciones', 'Devocionario']]),
    '<p class="pd-intro">' + esc(c.p) + '. ' + devoCuenta(piezas) + '.</p>'];
  if (pdSeccionConPagina(c)) h.push(pdIndiceSecciones(c));
  else h.push(pdListaConSecciones(c, piezas, ids));
  vista.innerHTML = h.join('');
  E.devoVuelta = { ids: ids, rot: c.t, href: pdEnlaceCap(clave) };
  pdColoca();
}

function pdSeccionA(clave, sec) {
  const c = E.devoCap.get(clave);
  if (!c) return pdPortada();
  const piezas = E.devo.piezas.filter((p) => p.c === clave && p.s === sec);
  if (!piezas.length) return pdCapituloA(clave);
  modoPanel(sec);
  const ids = [];
  vista.innerHTML = pdMigas([['#/oraciones', 'Devocionario'],
    [pdEnlaceCap(clave), c.t]])
    + '<p class="pd-intro">' + devoCuenta(piezas) + '.</p>'
    + pdLista(piezas, sec, { ids: ids });
  E.devoVuelta = { ids: ids, rot: sec, href: pdEnlaceSec(clave, sec) };
  pdColoca();
}

/* ------------------------------------------------------- B · mosaico */

function pdTesela(href, icono, t, n, ancha) {
  return '<a class="pd-tesela' + (ancha ? ' pd-tesela-ancha' : '') + '" href="'
    + href + '"><span class="pd-tesela-i">' + icono + '</span>'
    + '<span class="pd-tesela-c"><span class="pd-tesela-t">' + esc(t)
    + '</span><span class="pd-tesela-n">' + n + '</span></span></a>';
}

function pdPortadaB() {
  modoPanel('Devocionario');
  $('#subtitulo-dia').textContent = E.devo.piezas.length + ' oraciones';
  const favs = devoFavoritas();
  const comp = E.devo.piezas.filter((p) => p.comp).length;
  const arriba = [];
  if (comp) {
    arriba.push(pdTesela('#/oraciones/p', PD_ICONO.compendio,
      'Las oraciones del Compendio', comp + ' · para empezar', true));
  }
  if (favs.length) {
    arriba.push(pdTesela('#/oraciones/m', PD_ICONO.estrella, 'Favoritas',
      favs.length + (favs.length === 1 ? ' marcada' : ' marcadas'), true));
  }
  const formas = E.devo.formas.slice(0, 10).map((x) => '<a class="devo-chip" '
    + 'href="' + devoEnlaceFiltro(x.f) + '">' + esc(devoPlural(x.f))
    + ' <span>' + x.n + '</span></a>').join('');
  const html = '<div class="pd-teselas pd-arriba">' + arriba.join('') + '</div>'
    + pdBandas().map((b) => pdBanda(b.t) + '<div class="pd-teselas" '
      + 'style="--pd-tono: var(' + b.tono + ')">' + b.caps.map((c) => pdTesela(
        pdEnlaceCap(c.c), PD_ICONO[c.c] || PD_ICONO.compendio, c.t, c.n))
        .join('') + '</div>').join('')
    + pdBanda('Por tipo de oración')
    + '<div class="devo-chips pd-tira">' + formas
    + '<a class="devo-chip devo-chip-mas" href="#/oraciones/f">todas…</a></div>'
    + '<div class="devo-chips pd-tira"><a class="devo-chip" href="'
    + devoEnlaceFiltro(null, 'es') + '">con castellano <span>' + pdNumEs()
    + '</span></a></div>';
  pdBuscador(() => html, { ids: [], href: '#/oraciones', rot: 'Devocionario' });
  pdColoca();
}

/** Las pestañas de un capítulo: sus grupos si los tiene, y si no sus
 *  secciones, con «Todas» delante. Un capítulo de secciones menudas no lleva
 *  pestañas: se ve entero. */
function pdPestanas(c) {
  const grupos = pdGrupos(c);
  let p = null;
  if (grupos) p = grupos;
  else if (c.secs.length >= 2 && c.secs.length <= 9
    && c.n / c.secs.length >= 2.5) {
    p = c.secs.map((s) => ({ t: s.s, secs: [s] }));
  }
  if (!p) return null;
  return [{ t: 'Todas', secs: c.secs, todas: true }].concat(p);
}

function pdCapituloB(clave, secPedida) {
  const c = E.devoCap.get(clave);
  if (!c) return pdPortada();
  modoPanel(c.t);
  const piezas = E.devo.piezas.filter((p) => p.c === clave);
  const pest = pdPestanas(c);
  E.pdPest = E.pdPest || {};
  let cual = E.pdPest[clave];
  if (pest && secPedida) {
    const i = pest.findIndex((t, k) => k > 0 && t.secs.some((s) => s.s === secPedida));
    if (i > 0) cual = i;
  }
  if (pest && (cual == null || cual >= pest.length)) cual = c.n > 40 ? 1 : 0;
  const h = [pdMigas([['#/oraciones', 'Devocionario']]),
    '<header class="pd-cab-b" style="--pd-tono: var(' + pdTonoDe(clave) + ')">'
    + '<span class="pd-tesela-i">' + (PD_ICONO[clave] || PD_ICONO.compendio)
    + '</span><span><span class="pd-cab-b-p">' + esc(c.p) + '</span>'
    + '<span class="pd-cab-b-n">' + devoCuenta(piezas) + '</span></span></header>'];
  if (pest) {
    h.push('<nav class="pd-pestanas" role="tablist" aria-label="Secciones">'
      + pest.map((t, i) => '<button type="button" role="tab" data-pest="' + i
        + '" aria-selected="' + (i === cual) + '">' + esc(t.t) + (t.todas ? ''
          : ' <span>' + t.secs.reduce((a, s) => a + s.n, 0) + '</span>')
        + '</button>').join('') + '</nav><div id="pd-pest"></div>');
  } else {
    const ids = [];
    h.push(pdListaConSecciones(c, piezas, ids));
    E.devoVuelta = { ids: ids, rot: c.t, href: pdEnlaceCap(clave) };
  }
  vista.innerHTML = h.join('');
  if (pest) {
    const pinta = (i) => {
      cual = i;
      E.pdPest[clave] = i;
      const t = pest[i];
      const ids = [];
      const suyas = piezas.filter((p) => t.todas || t.secs.some((s) => s.s === p.s));
      $('#pd-pest').innerHTML = t.secs.length === 1
        ? pdLista(suyas, t.t, { ids: ids })
        : pdListaConSecciones(c, suyas, ids, t.secs);
      E.devoVuelta = { ids: ids, rot: t.todas ? c.t : t.t,
        href: pdEnlaceCap(clave) };
      vista.querySelectorAll('[data-pest]').forEach((b) =>
        b.setAttribute('aria-selected', String(+b.dataset.pest === i)));
      // la pestaña puesta, siempre a la vista en la tira
      const act = tira.querySelector('[aria-selected="true"]');
      if (act) tira.scrollLeft = Math.max(0, act.offsetLeft - 48);
    };
    const tira = vista.querySelector('.pd-pestanas');
    pinta(cual);
    tira.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-pest]');
      if (!b) return;
      // si la tira ya va pegada arriba, la lista nueva empieza bajo ella
      const arriba = tira.getBoundingClientRect().top <= pdAltoCab() + 1;
      pinta(+b.dataset.pest);
      if (arriba) {
        window.scrollTo(0, window.scrollY + $('#pd-pest').getBoundingClientRect().top
          - pdAltoCab() - tira.offsetHeight);
      }
    });
  }
  pdColoca();
}

/* ----------------------------------------------- C · árbol plegable */

function pdDentroC(c, st) {
  const piezas = E.devo.piezas.filter((p) => p.c === c.c);
  if (!pdSeccionConPagina(c)) return pdListaConSecciones(c, piezas, []);
  const grupos = pdGrupos(c) || [{ t: null, secs: c.secs }];
  return grupos.map((g) => (g.t ? pdBanda(g.t) : '') + g.secs.map((s) => {
    const suyas = piezas.filter((p) => p.s === s.s);
    if (suyas.length === 1) {
      return pdLista(suyas, s.s, { ctx: () => s.s });
    }
    return '<details class="pd-rama" data-s="' + esc(s.s) + '"'
      + (st.s === s.s ? ' open' : '') + '><summary><span class="pd-rama-t">'
      + esc(s.s) + '</span><span class="pd-n">' + s.n + '</span></summary>'
      + pdLista(suyas, s.s, {}) + '</details>';
  }).join('')).join('');
}

function pdArbolHtml() {
  const st = E.pdArbol;
  const idsFav = [];
  const favs = devoFavoritas();
  const h = [pdPuertaCompendio()];
  if (favs.length) {
    h.push('<details class="pd-cap" data-c="*fav"'
      + (st.c === '*fav' ? ' open' : '') + '><summary><span class="pd-cap-t">'
      + 'Favoritas</span><span class="pd-n">' + favs.length + '</span></summary>'
      + '<div class="pd-cap-dentro">' + pdLista(favs, 'Favoritas', {
        sinPlegar: true, sinEstrella: true, ctx: (p) => devoDondeVive(p),
        ids: idsFav }) + '</div></details>');
  }
  for (const b of pdBandas()) {
    h.push(pdBanda(b.t));
    for (const c of b.caps) {
      h.push('<details class="pd-cap" data-c="' + esc(c.c) + '"'
        + (st.c === c.c ? ' open' : '') + '><summary><span class="pd-cap-c">'
        + '<span class="pd-cap-t">' + esc(c.t) + '</span>'
        + '<span class="pd-cap-p">' + esc(c.p) + '</span></span>'
        + '<span class="pd-n">' + c.n + '</span></summary>'
        + '<div class="pd-cap-dentro">' + pdDentroC(c, st) + '</div></details>');
    }
  }
  // lo que la pieza es, también como rama: el mismo gesto para todo
  h.push(pdBanda('Por tipo de oración'));
  h.push('<details class="pd-cap" data-c="*formas"'
    + (st.c === '*formas' ? ' open' : '') + '><summary><span class="pd-cap-c">'
    + '<span class="pd-cap-t">Himnos, letanías, novenas…</span>'
    + '<span class="pd-cap-p">Lo que es cada oración, de todo el libro</span>'
    + '</span><span class="pd-n">' + E.devo.formas.length + '</span></summary>'
    + '<div class="pd-cap-dentro"><div class="pd-lista">'
    + E.devo.formas.map((x) => '<a class="pd-sec" href="'
      + devoEnlaceFiltro(x.f) + '"><span class="pd-sec-t">'
      + esc(mayuscula(devoPlural(x.f))) + '</span><span class="pd-n">' + x.n
      + '</span></a>').join('')
    + '<a class="pd-sec" href="' + devoEnlaceFiltro(null, 'es') + '">'
    + '<span class="pd-sec-t">Con su castellano</span><span class="pd-n">'
    + pdNumEs() + '</span></a></div></div></details>');
  return h.join('');
}

function pdArbolEventos(caja) {
  pdVueltaAlTocar(caja);
  // `toggle` no sube: se coge al bajar
  caja.addEventListener('toggle', (ev) => {
    const d = ev.target;
    if (!(d instanceof HTMLDetailsElement)) return;
    const st = E.pdArbol;
    if (d.classList.contains('pd-cap')) {
      if (d.open) {
        st.c = d.dataset.c;
        st.s = null;
        // un capítulo abierto cada vez: así la página no crece sin fin
        caja.querySelectorAll('details.pd-cap[open]').forEach((x) => {
          if (x !== d) x.open = false;
        });
        requestAnimationFrame(() => {
          if (d.getBoundingClientRect().top < pdAltoCab()) {
            d.scrollIntoView({ block: 'start' });
          }
        });
      } else if (st.c === d.dataset.c) { st.c = null; st.s = null; }
    } else if (d.classList.contains('pd-rama')) {
      if (d.open) {
        st.s = d.dataset.s;
        d.parentElement.querySelectorAll('details.pd-rama[open]').forEach((x) => {
          if (x !== d) x.open = false;
        });
        requestAnimationFrame(() => {
          const s = d.querySelector('summary');
          if (s.getBoundingClientRect().top < pdAltoCab() + 52) {
            d.scrollIntoView({ block: 'start' });
          }
        });
      } else if (st.s === d.dataset.s) st.s = null;
    }
  }, true);
}

function pdPortadaC(clave, sec) {
  modoPanel('Devocionario');
  $('#subtitulo-dia').textContent = E.devo.piezas.length + ' oraciones';
  E.pdArbol = E.pdArbol || { c: null, s: null };
  if (clave) { E.pdArbol.c = clave; E.pdArbol.s = sec || null; }
  pdBuscador(pdArbolHtml, { ids: [], href: '#/oraciones', rot: 'Devocionario' },
    pdArbolEventos);
  pdColoca(() => {
    if (!clave) return false;
    const d = vista.querySelector('details.pd-cap[open]');
    const r = sec && d && d.querySelector('details.pd-rama[open]');
    if (!d) return false;
    (r || d).scrollIntoView({ block: 'start' });
  });
}

/* --------------------------------------------------- D · para hoy */

/* Lo que la piedad reza cada día de la semana y cada mes del año: no lo
 * manda nadie, pero es la costumbre que llena los devocionarios. */
const PD_SEMANA = [
  ['Los domingos', 'a la Santísima Trinidad', [['dios', 'La Santísima Trinidad']]],
  ['Los lunes', 'al Espíritu Santo y por las ánimas',
    [['dios', 'El Espíritu Santo'], ['necesidad', 'Por los difuntos']]],
  ['Los martes', 'a los ángeles',
    [['santos', 'El ángel de la guarda'], ['santos', 'Los ángeles']]],
  ['Los miércoles', 'a san José', [['santos', 'San José']]],
  ['Los jueves', 'al Santísimo Sacramento', [['dios', 'El Santísimo Sacramento']]],
  ['Los viernes', 'a la Pasión del Señor', [['dios', 'La Pasión'],
    ['dios', 'La santa Cruz'], ['dios', 'El Sagrado Corazón']]],
  ['Los sábados', 'a la Virgen', [['santos', 'La Santísima Virgen']]]
];

const PD_MES = [
  ['Enero', 'mes del santo Nombre', [['dios', 'El santo Nombre']]],
  ['Febrero', 'mes de la Sagrada Familia', [['santos', 'La Sagrada Familia']]],
  ['Marzo', 'mes de san José', [['santos', 'San José']]],
  ['Abril', 'mes del Santísimo Sacramento', [['dios', 'El Santísimo Sacramento']]],
  ['Mayo', 'mes de la Virgen', [['santos', 'La Santísima Virgen']]],
  ['Junio', 'mes del Sagrado Corazón', [['dios', 'El Sagrado Corazón']]],
  ['Julio', 'mes de la Preciosísima Sangre', [['dios', 'La Preciosísima Sangre']]],
  ['Agosto', 'mes del Inmaculado Corazón', [['santos', 'La Inmaculada']]],
  ['Septiembre', 'mes de los Dolores', [['santos', 'Los Dolores']]],
  ['Octubre', 'mes del Rosario', [['*forma', 'rosario'], ['santos', 'Los ángeles']]],
  ['Noviembre', 'mes de los difuntos', [['necesidad', 'Por los difuntos'],
    ['necesidad', 'Por la buena muerte'], ['necesidad', 'Por los agonizantes']]],
  ['Diciembre', 'mes de la Inmaculada', [['santos', 'La Inmaculada']]]
];

function pdDe(fuentes) {
  const vistas = new Set();
  const r = [];
  for (const [c, s] of fuentes) {
    const suyas = c === '*forma' ? E.devo.piezas.filter((p) => p.f === s)
      : E.devo.piezas.filter((p) => p.c === c && p.s === s);
    for (const p of suyas) if (!vistas.has(p.id)) { vistas.add(p.id); r.push(p); }
  }
  return r;
}

/** Del primer domingo de Adviento al fin de año: el año litúrgico de la
 *  fecha empezó este mismo año civil. */
function pdEnAdviento(iso) {
  const a = anioDe(iso);
  return !!a && a.inicio.slice(0, 4) === iso.slice(0, 4) && iso >= a.inicio;
}

/** El tiempo litúrgico de una fecha, por la Pascua y el Adviento del año
 *  del calendario: lo justo para escoger la sección del año litúrgico. */
function pdTiempo(iso) {
  const a = anioDe(iso);
  if (!a) return null;
  const dia = (x) => Date.parse(x + 'T12:00:00Z') / 864e5;
  const k = Math.round(dia(iso) - dia(a.pascua));
  const md = iso.slice(5);
  if (pdEnAdviento(iso) && md < '12-25') return ['Adviento', 'Adviento'];
  if (md >= '12-25' || md <= '01-12') {
    return md === '01-06' ? ['Epifanía', 'Epifanía'] : ['Navidad', 'Navidad'];
  }
  if (k >= -46 && k <= -4) return ['Cuaresma', 'Cuaresma'];
  if (k >= -3 && k <= -1) return ['Triduo pascual', 'Triduo'];
  if (k >= 0 && k <= 48) return ['Tiempo de Pascua', 'Pascua'];
  if (k === 49) return ['Pentecostés', 'Pentecostés'];
  if (k >= 60 && k <= 63) return ['Corpus Christi', 'Corpus Christi'];
  if (md === '11-01' || md === '11-02') return ['Todos los Santos', 'Todos los Santos'];
  return null;
}

function pdMomento(hora) {
  if (hora >= 5 && hora < 12) return ['Esta mañana', 'al empezar el día', [['dia', 'La mañana']]];
  if (hora >= 12 && hora < 16) return ['Al mediodía', 'el Ángelus y la mesa', [['dia', 'La mesa']]];
  if (hora >= 16 && hora < 20) return ['Esta tarde', 'los himnos de Vísperas', [['horas', 'Vísperas']]];
  return ['Esta noche', 'antes de dormir', [['dia', 'La noche'], ['horas', 'Completas'],
    ['santos', 'Las antífonas finales']]];
}

/** De lo que tiene tiempo o día, sólo lo de hoy: la antífona final de la
 *  Virgen va por su tiempo —Alma Redemptóris del Adviento a la Candelaria,
 *  Ave Regína cælórum hasta la Semana Santa, Regína cæli en Pascua y Salve
 *  Regína el resto del año—, y el himno de Vísperas, por su día. */
const PD_DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves',
  'viernes', 'sábado'];
function pdDeHoy(piezas, iso) {
  const a = anioDe(iso);
  const dia = (x) => Date.parse(x + 'T12:00:00Z') / 864e5;
  const k = a ? Math.round(dia(iso) - dia(a.pascua)) : 999;
  const md = iso.slice(5);
  const antifona = pdEnAdviento(iso) || md >= '12-25' || md < '02-02'
    ? 'Adviento' : k < 0 ? 'Cuaresma' : k <= 49 ? 'Pascua' : 'Tiempo ordinario';
  const tpo = (pdTiempo(iso) || [])[1];
  const hoy = PD_DIAS[new Date(iso + 'T12:00:00').getDay()];
  return piezas.filter((p) => {
    if (p.dia && p.dia !== hoy) return false;
    if (!p.tpo) return true;
    if (p.f === 'antífona') return p.tpo === antifona;
    return p.tpo === tpo || (p.tpo === 'Pasión' && tpo === 'Cuaresma');
  });
}

function pdPrimeras(piezas, n) {
  const r = [];
  const cols = new Set();
  for (const p of piezas) {
    if (p.col) { if (cols.has(p.col)) continue; cols.add(p.col); }
    r.push(p);
    if (r.length >= n) break;
  }
  return r;
}

function pdParaHoy(iso, ahora) {
  const t = [];
  const m = pdMomento(ahora.getHours());
  let piezas = pdDe(m[2]);
  // al mediodía va delante el Ángelus, o el Regína cæli si es Pascua
  if (m[0] === 'Al mediodía') {
    const pascua = (pdTiempo(iso) || [])[1] === 'Pascua';
    const a = E.devo.piezas.find((p) => p.comp === (pascua ? 8 : 7));
    if (a) piezas = [a].concat(piezas.filter((p) => p !== a));
  }
  t.push({ ojo: m[0], t: mayuscula(m[1]), piezas: piezas });
  const dow = new Date(iso + 'T12:00:00').getDay();
  const s = PD_SEMANA[dow];
  t.push({ ojo: s[0], t: mayuscula(s[1]), piezas: pdDe(s[2]) });
  const tpo = pdTiempo(iso);
  if (tpo) {
    t.push({ ojo: 'El tiempo', t: tpo[0], piezas: pdDe([['anio', tpo[1]]]) });
  } else {
    const mes = PD_MES[+iso.slice(5, 7) - 1];
    // la del Compendio delante: en octubre, el Rosario antes que la coronilla
    const suyas = pdDe(mes[2]);
    t.push({ ojo: mes[0], t: mayuscula(mes[1]),
      piezas: suyas.filter((p) => p.comp).concat(suyas.filter((p) => !p.comp)) });
  }
  for (const x of t) x.piezas = pdDeHoy(x.piezas, iso);
  return t.filter((x) => x.piezas.length);
}

function pdPortadaD() {
  modoPanel('Devocionario');
  $('#subtitulo-dia').textContent = E.devo.piezas.length + ' oraciones';
  const iso = hoyISO();
  const val = entradasDe(iso);
  const cels = val ? celebracionesDe(val) : [];
  const dia = cels.length ? E.diaDe.get(cels[0].slug) : null;
  const tarjetas = pdParaHoy(iso, new Date());
  // a mano: las favoritas primero, y luego las que se rezan cada día
  const pascua = (pdTiempo(iso) || [])[1] === 'Pascua';
  const comunes = [1, 3, 4, 2, pascua ? 8 : 7, 9, 5, 6, 22].map((n) =>
    E.devo.piezas.find((p) => p.comp === n)).filter(Boolean);
  const amano = devoFavoritas().slice(0, 6);
  for (const p of comunes) if (amano.length < 10 && amano.indexOf(p) < 0) amano.push(p);
  const html = '<p class="pd-hoy-fecha">' + esc(fechaLarga(iso))
    + (dia ? '<span>' + esc(dia.t) + '</span>' : '') + '</p>'
    + tarjetas.map((x, i) => {
      const prim = pdPrimeras(x.piezas, 3);
      const resto = x.piezas.length - prim.length;
      return '<section class="pd-tarjeta" data-tarjeta="' + i + '">'
        + '<p class="pd-tarjeta-ojo">' + esc(x.ojo) + '</p>'
        + '<h2 class="pd-tarjeta-t">' + esc(x.t) + '</h2>'
        + pdLista(prim, x.t, { sinCortes: true })
        + (resto > 0 ? '<button type="button" class="pd-mas" data-todas="' + i
          + '">Ver las ' + x.piezas.length + ICONO.der + '</button>' : '')
        + '</section>';
    }).join('')
    + pdBanda('Siempre a mano')
    + '<div class="pd-amano">' + amano.map((p) => '<a href="#/oraciones/o/'
      + esc(p.id) + '" lang="la">' + (esFavorita(p.id) ? ICONO.estrella : '')
      + esc(tx(p.tla)) + '</a>').join('')
    + '<a class="pd-amano-mas" href="#/oraciones/p">Las del Compendio</a></div>'
    + pdBanda('Todo el devocionario')
    + pdBandas().map((b) => '<p class="pd-rejilla-t">' + esc(b.t) + '</p>'
      + '<div class="pd-rejilla">' + b.caps.map((c) => '<a href="'
        + pdEnlaceCap(c.c) + '"><span>' + esc(c.t) + '</span><span class="pd-n">'
        + c.n + '</span></a>').join('') + '</div>').join('')
    + pdOtrasEntradas();
  pdBuscador(() => html, { ids: [], href: '#/oraciones', rot: 'Devocionario' },
    (caja) => {
      pdVueltaAlTocar(caja);
      caja.addEventListener('click', (ev) => {
        const b = ev.target.closest('[data-todas]');
        if (!b) return;
        const x = tarjetas[+b.dataset.todas];
        b.closest('.pd-tarjeta').querySelector('.pd-lista').outerHTML =
          pdLista(x.piezas, x.t, { sinCortes: true });
        b.remove();
      });
    });
  pdColoca();
}

/* ---------------------------------------------------- el reparto */

function pdPortada() {
  const v = pdCual();
  if (v === 'b') return pdPortadaB();
  if (v === 'c') return pdPortadaC();
  if (v === 'd') return pdPortadaD();
  return pdPortadaA();
}

/** En las páginas que siguen siendo las de antes —la oración, la
 *  colección, el filtro, las formas, el Compendio, las favoritas— el
 *  «volver» de arriba se cambia por las migas; y en la oración, la ficha de
 *  insignias pasa a ser un renglón y la estrella sube junto a las migas. */
function pdRetoca(que, cual) {
  // las filas que esas páginas ponen sueltas, en su caja como las demás
  let caja = null;
  for (const n of [...vista.children]) {
    if (!n.classList.contains('pd-fila')) { caja = null; continue; }
    if (!caja) {
      caja = document.createElement('div');
      caja.className = 'pd-lista';
      n.before(caja);
    }
    caja.appendChild(n);
  }
  const atras = vista.querySelector('.devo-atras');
  if (!atras) return;
  let pasos = [['#/oraciones', 'Devocionario']];
  if (que === 'o') {
    const p = E.devoDe.get(cual);
    if (p) pasos = pdPasosDe(p);
    if (p && p.col) pasos.push(['#/oraciones/k/' + encodeURIComponent(p.col), p.colt]);
  } else if (que === 'k') {
    const partes = E.devoCol.get(cual);
    if (partes) pasos = pdPasosDe(partes[0]);
  } else if (que === 'f' && cual) {
    pasos.push(['#/oraciones/f', 'Por tipo']);
  }
  const tmp = document.createElement('div');
  tmp.innerHTML = pdMigas(pasos);
  const migas = tmp.firstChild;
  atras.replaceWith(migas);
  const fav = $('#devo-fav');
  if (fav) {
    fav.setAttribute('aria-label', 'Favorita');
    migas.appendChild(fav);
  }
}

const pdAntes = {
  verDevocionario: verDevocionario,
  devoFila: devoFila,
  devoFilaCol: devoFilaCol,
  devoLista: devoLista
};

devoFila = function (p, ctx, num, sinEstrella) {
  return pdCual() === 'actual' ? pdAntes.devoFila(p, ctx, num, sinEstrella)
    : pdFila(p, ctx, num, sinEstrella);
};
devoFilaCol = function (partes) {
  return pdCual() === 'actual' ? pdAntes.devoFilaCol(partes) : pdFilaCol(partes);
};
// en las pruebas, la lista no se vuelve a cortar por formas: la forma ya
// la dice la fila, y un corte más era un nivel más
devoLista = function (piezas, opc) {
  if (pdCual() === 'actual') return pdAntes.devoLista(piezas, opc);
  pdCalla = piezas.length > 1 && piezas.every((p) => p.f === piezas[0].f)
    ? piezas[0].f : null;
  const h = pdAntes.devoLista(piezas, Object.assign({}, opc, { sinCortes: true }));
  pdCalla = null;
  return h;
};

verDevocionario = async function (que, cual, mas) {
  const v = pdCual();
  pdBarra();
  if (v === 'actual' || que === 'o' || que === 'k' || que === 'f'
    || que === 'p' || que === 'm') {
    await pdAntes.verDevocionario(que, cual, mas);
    if (v !== 'actual') pdRetoca(que, cual);
    pdTrasPintar();
    return;
  }
  E.vista = 'devocionario';
  E.devoPieza = null;
  marcaBarra('portada');
  modoPanel('Devocionario');
  if (!E.devo) vista.innerHTML = '<p class="aviso">Abriendo…</p>';
  try {
    await cargaDevocionario();
  } catch (err) {
    vista.innerHTML = '<p class="aviso">No he podido abrir el devocionario ('
      + esc(err.message) + ').</p>';
    return;
  }
  if (v === 'b' && que === 'c' && cual) pdCapituloB(cual);
  else if (v === 'b' && que === 's' && cual) pdCapituloB(cual, mas);
  else if (v === 'c' && (que === 'c' || que === 's') && cual) pdPortadaC(cual, mas);
  else if (que === 'c' && cual) pdCapituloA(cual);
  else if (que === 's' && cual && mas) pdSeccionA(cual, mas);
  else pdPortada();
  pdTrasPintar();
};

function pdTrasPintar() {
  const r = document.documentElement.style;
  r.setProperty('--pd-cab', pdAltoCab() + 'px');
  r.setProperty('--pd-barra', ($('#barra') ? $('#barra').offsetHeight : 58) + 'px');
}

/* La tira de abajo, que cambia de prueba sin salir de donde se está. */
function pdBarra() {
  const en = location.hash.indexOf('#/oraciones') === 0;
  const v = pdCual();
  document.body.classList.toggle('pd-con-barra', en);
  document.body.classList.toggle('pd-on', en && v !== 'actual');
  document.body.dataset.prueba = en ? v : '';
  let b = $('#pd-barra');
  if (!en) { if (b) b.hidden = true; return; }
  if (!b) {
    b = document.createElement('div');
    b.id = 'pd-barra';
    b.className = 'pd-barra';
    b.setAttribute('role', 'group');
    b.setAttribute('aria-label', 'Pruebas de diseño del devocionario');
    document.body.appendChild(b);
    b.addEventListener('click', (ev) => {
      const x = ev.target.closest('[data-prueba]');
      if (!x || x.dataset.prueba === pdCual()) return;
      pdPon(x.dataset.prueba);
      enruta();
    });
  }
  b.hidden = false;
  const nombre = PD.find((x) => x[0] === v)[2];
  b.innerHTML = '<span class="pd-barra-n">' + esc(nombre) + '</span>'
    + PD.map(([k, l]) => '<button type="button" data-prueba="' + k + '"'
      + (k === v ? ' aria-pressed="true"' : '') + '>' + l + '</button>').join('');
}

// este oyente va antes que el de la app, así que aún se ve lo que se deja
window.addEventListener('hashchange', (ev) => {
  const antes = new URL(ev.oldURL).hash;
  if (antes.indexOf('#/oraciones') === 0 && antes.indexOf('#/oraciones/o/') !== 0) {
    pdPos[antes] = window.scrollY;
  }
  pdBarra();
});
