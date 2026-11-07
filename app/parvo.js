/* =============================================== el Oficio Parvo de la Virgen
 *
 * El Oficio Parvo de la Santísima Virgen según las rúbricas de 1954, del
 * epub que trajo el usuario el 2026-11-06 (Enchiridion/src/parvo.py lo pasa
 * a datos/parvo.json). Vive en el devocionario, pero se reza como las Horas:
 * la tira de las ocho horas arriba, la fecha con sus flechas, el carril, la
 * voz y el dedo que pasa de una hora a la siguiente.
 *
 * El libro ya viene compuesto: cada hora está escrita entera para cada uno de
 * sus cinco tiempos y para cada manera de rezarla (a solas, entre dos, en
 * comunidad). Lo que hace esto es **elegir**, por la fecha y por la hora:
 *
 *  · el tiempo: Adviento desde las Vísperas del sábado anterior al primer
 *    domingo hasta la Nona del 24 de diciembre; Navidad hasta las Completas
 *    del 2 de febrero; Septuagésima desde las Vísperas del sábado anterior
 *    hasta las Vísperas del Sábado Santo; el pascual desde sus Completas
 *    hasta la Nona del sábado después de Pentecostés; y el resto, «durante
 *    el año». Las Vísperas son las que cambian de tiempo: el mismo sábado
 *    reza Laudes de un tiempo y Vísperas del siguiente.
 *  · el nocturno de Maitines por el día de la semana;
 *  · la antífona final de la Virgen, que no cambia con el tiempo del oficio
 *    sino con el suyo (Alma Redemptóris hasta el 2 de febrero, Ave Regína
 *    hasta el Miércoles Santo, ninguna del Jueves al Sábado Santo, Regína
 *    cæli en Pascua y Salve el resto);
 *  · y lo que el libro deja dicho en rúbricas «si…»: la Septuagésima que
 *    empieza antes del 2 de febrero (Navidad con «Laus tibi» y sin Te Deum)
 *    y la Anunciación, que reza el oficio de Adviento, en Cuaresma con «Laus
 *    tibi». Hecho lo que la rúbrica manda, la rúbrica sobra y se quita; la
 *    que no toca ese día, también.
 *
 * Va montado encima de app.js sin tocarlo, como devo-vistas.js y
 * recorrido.js: reasigna `verDevocionario`, `cargaDevocionario`,
 * `loQueSeLee` y `conCarril`, y lo que app.js escucha por referencia (las
 * flechas de la fecha, la tira de las horas, el dedo) se recoge aquí antes
 * que allí.
 */

const PV_ID = 'parvo-bvm';

/** [clave, nombre, abreviatura en la tira] */
const PV_HORAS = [
  ['maitines', 'Maitines', 'Mai'], ['laudes', 'Laudes', 'Lau'],
  ['prima', 'Prima', 'Pri'], ['tercia', 'Tercia', 'Ter'],
  ['sexta', 'Sexta', 'Sex'], ['nona', 'Nona', 'Non'],
  ['visperas', 'Vísperas', 'Vís'], ['completas', 'Completas', 'Com']
];
/** el nombre de la página en el libro */
const PV_FICHERO = { laudes: 'laud', prima: 'prima', tercia: 'tertia',
  sexta: 'sexta', nona: 'nona', visperas: 'vesp', completas: 'compl' };
const PV_TIEMPOS = { ord: 'Durante el año', adv: 'Adviento',
  nat: 'Navidad', sept: 'Septuagésima', pasc: 'Tiempo pascual' };
const PV_MODOS = [['solo', 'A solas'], ['dos', 'Entre dos'],
  ['grupo', 'En comunidad']];
const PV_LENGUAS = [['la', 'Latín'], ['es', 'Español'], ['ambos', 'Los dos']];
const PV_ANTIFONAS = { alma: 'Alma Redemptóris Mater', ave: 'Ave, Regína cælórum',
  regina: 'Regína cæli', salve: 'Salve, Regína' };
/** Las secciones que se rezan por versos, y no de corrido. */
const PV_VERSO = new Set(['comienzo', 'invitatorio', 'himno', 'salmodia',
  'tedeum', 'cantico', 'antifona', 'conclusion']);

/* ------------------------------------------------------------ las fechas */

/** El domingo de Pascua (algoritmo anónimo gregoriano). */
function pvPascua(y) {
  const a = y % 19, b = Math.floor(y / 100), c = y % 100;
  const d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4), k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const mes = Math.floor((h + l - 7 * m + 114) / 31);
  const dia = ((h + l - 7 * m + 114) % 31) + 1;
  return y + '-' + String(mes).padStart(2, '0') + '-' + String(dia).padStart(2, '0');
}

function pvDiaSem(iso) { return new Date(iso + 'T12:00:00').getDay(); }

/** Las fechas que mandan en el año de `iso`. */
function pvMarcas(iso) {
  const y = +iso.slice(0, 4);
  const pascua = pvPascua(y);
  // el primer domingo de Adviento: cuatro antes del de Navidad
  const nav = y + '-12-25';
  const adv1 = suma(nav, -(pvDiaSem(nav) || 7) - 21);
  // La Anunciación cae en Semana Santa o en la octava de Pascua: pasa al
  // lunes después de la Dominica in albis. En domingo de Cuaresma: al lunes.
  let anun = y + '-03-25';
  let trasladada = false;
  if (anun >= suma(pascua, -7) && anun <= suma(pascua, 7)) {
    anun = suma(pascua, 8); trasladada = true;
  } else if (pvDiaSem(anun) === 0) {
    anun = suma(anun, 1); trasladada = true;
  }
  return {
    y: y, pascua: pascua,
    sabSept: suma(pascua, -64),     // el sábado anterior a Septuagésima
    jueSanto: suma(pascua, -3),
    sabSanto: suma(pascua, -1),
    sabPent: suma(pascua, 55),      // el sábado después de Pentecostés
    sabAdv: suma(adv1, -1),
    feb2: y + '-02-02',
    anun: anun, trasladada: trasladada
  };
}

const pvTarde = (hora) => hora === 'visperas' || hora === 'completas';

/** El tiempo del oficio y lo que ese día cambia en él. */
function pvTiempo(iso, hora) {
  const m = pvMarcas(iso);
  const tarde = pvTarde(hora);
  const comp = hora === 'completas';
  const md = iso.slice(5);
  const r = { t: 'ord', laus: false, sinTeDeum: false, purif: false,
    anun: false, trasladada: false };
  if (iso > m.sabAdv || (iso === m.sabAdv && tarde)) {
    r.t = md < '12-24' || (md === '12-24' && !tarde) ? 'adv' : 'nat';
  } else if (md <= '02-02') {
    r.t = 'nat';
    // la Septuagésima que empieza antes del 2 de febrero: el oficio sigue
    // siendo el de Navidad, pero con «Laus tibi» y sin Te Deum (el día de la
    // Purificación puede decirse)
    if (iso > m.sabSept || (iso === m.sabSept && tarde)) {
      r.laus = true;
      if (md === '02-02') r.purif = true;
      else r.sinTeDeum = true;
    }
  } else if (iso < m.sabSanto || (iso === m.sabSanto && !comp)) {
    r.t = iso > m.sabSept || (iso === m.sabSept && tarde) ? 'sept' : 'ord';
  } else if (iso < m.sabPent || (iso === m.sabPent && !tarde)) {
    r.t = 'pasc';
  }
  if (iso === m.anun) {
    r.anun = true;
    r.trasladada = m.trasladada;
    r.laus = r.t === 'sept';
    r.t = 'adv';
  }
  return r;
}

/** Maitines: I el domingo, lunes y jueves; II martes y viernes; III
 *  miércoles y sábado. */
function pvNocturno(iso) {
  return [1, 1, 2, 3, 1, 2, 3][pvDiaSem(iso)];
}

/** La antífona final que toca a esa hora de ese día, o null si no toca
 *  ninguna. Es lo que dicen las rúbricas del libro, y nada más: la Ave Regína
 *  «desde las Completas del 2 de febrero hasta el Miércoles Santo», la Regína
 *  cæli «desde las Completas del Sábado Santo»; del Jueves al Sábado Santo no
 *  dan ninguna, y no se dice (decidido por el usuario el 2026-11-06, aunque
 *  la página de Septuagésima trae la Ave Regína sin fecha). */
function pvAntifonaDe(iso, hora) {
  const m = pvMarcas(iso);
  const tarde = pvTarde(hora);
  const comp = hora === 'completas';
  if (iso < m.feb2 || (iso === m.feb2 && !comp)) return 'alma';
  if (iso < m.jueSanto) return 'ave';
  if (iso < m.sabSanto || (iso === m.sabSanto && !comp)) return null;
  if (iso < m.sabPent || (iso === m.sabPent && !tarde)) return 'regina';
  if (iso < m.sabAdv || (iso === m.sabAdv && !tarde)) return 'salve';
  return 'alma';
}

/** La hora que toca por el reloj. */
function pvHoraSugerida() {
  const h = new Date().getHours();
  if (h < 5) return 'maitines';
  if (h < 7) return 'laudes';
  if (h < 9) return 'prima';
  if (h < 12) return 'tercia';
  if (h < 15) return 'sexta';
  if (h < 17) return 'nona';
  if (h < 21) return 'visperas';
  return 'completas';
}

const pvNombreHora = (h) => (PV_HORAS.find((x) => x[0] === h) || [h, h])[1];

/* -------------------------------------------------------- los datos */

let pvPidiendo = null;
async function pvCarga() {
  if (E.parvoDatos) return;
  if (!pvPidiendo) {
    pvPidiendo = json('parvo.json').catch((err) => {
      pvPidiendo = null;
      throw err;
    });
  }
  E.parvoDatos = await pvPidiendo;
}

/** Cómo lo reza quien lo reza: en qué lengua y de qué manera. Se guarda en
 *  el aparato; la lengua empieza por la de la burbuja del devocionario. */
function pvCfg() {
  if (E.parvoCfg) return E.parvoCfg;
  let c = {};
  try { c = JSON.parse(localStorage.getItem('parvo') || '{}') || {}; } catch (_) {}
  E.parvoCfg = {
    l: PV_LENGUAS.some((x) => x[0] === c.l) ? c.l
      : (E.devoLengua === 'es' ? 'es' : 'la'),
    m: PV_MODOS.some((x) => x[0] === c.m) ? c.m : 'solo',
    // las oraciones antes y después del oficio: plegadas, salvo que se
    // hayan abierto, y así se quedan
    abre: c.abre && typeof c.abre === 'object' ? c.abre : {}
  };
  return E.parvoCfg;
}

/** Sin las rúbricas ni las indicaciones, para quien ya sabe cómo se reza
 *  (Ajustes, «Devocionario»). La guía las sigue enseñando: es para eso. */
function pvSinRubricas() { return E.cfg.parvoRubricas === 'no'; }

/** El color de sus horas: el azul de la Virgen o el de Ajustes y el
 *  devocionario (Ajustes, «Devocionario»). Un color fijado para toda la
 *  app sigue mandando: eso lo hace ponColor(). */
function pvColor() {
  return E.cfg.parvoColor === 'neutro' ? 'neutro' : 'azul';
}

/** Las oraciones antes y después del oficio, de la página del libro que
 *  las trae, para ponerlas plegadas al principio y al final de cada hora.
 *  Con su rúbrica delante —no son obligatorias, se dicen de rodillas—, y
 *  en el rótulo su comienzo, que es como se las conoce. */
function pvOraciones(k) {
  const g = E.parvoDatos.guia.oraciones || [];
  const i = g.findIndex((p) => p[0] === 'h' && p[4] === k);
  if (i < 0) return [];
  let j = i + 1;
  while (j < g.length && g[j][0] !== 'h') j++;
  const rub = g.find((p) => p[0] === 'r');
  const h = g[i].slice();
  h[2] = tx(k === 'antes' ? 'Aperi, Dómine' : 'Sacrosánctæ');
  return [h].concat(rub ? [rub] : [], g.slice(i + 1, j));
}

function pvGuardaCfg() {
  try { localStorage.setItem('parvo', JSON.stringify(E.parvoCfg)); } catch (_) {}
}

/* ------------------------------------------------- lo que se reza hoy */

/** La página del libro que toca, ya con lo de ese día hecho. */
function pvCompone(modo, iso, hora) {
  const P = E.parvoDatos;
  const K = P.claves;
  const f = pvTiempo(iso, hora);
  const noct = hora === 'maitines' ? pvNocturno(iso) : 0;
  const clave = modo + '_' + f.t + '_' + (noct ? 'mat' + noct : PV_FICHERO[hora]);
  let ps = (P.h[clave] || []).slice();
  // el «Allelúja» del comienzo: las dos rúbricas que dicen cuándo no se
  // dice se quitan siempre —o ya está hecho, o ese día no toca—
  ps = ps.filter((p) => !(p[0] === 'r' && (p[1] === K.r_laus_anunciacion
    || p[1] === K.r_laus_septuagesima)));
  if (f.laus) {
    ps = ps.map((p) => p[0] === 'u' && p[1] === K.alleluja
      ? ['u', K.laus].concat(p.slice(2)) : p);
  }
  // el Te Deum de Navidad cuando ya es Septuagésima
  if (f.t === 'nat' && noct) {
    if (f.sinTeDeum) ps = pvSinTeDeum(ps, modo, noct);
    else if (!f.purif) {
      ps = ps.filter((p) => !(p[0] === 'r' && p[1] === K.r_tedeum_septuagesima));
    }
  }
  const ant = pvAntifonaDe(iso, hora);
  // si esta hora la decía y hoy no se dice, se avisa arriba
  const sinAnt = !ant && ps.some((p) => p[0] === 'h' && p[4] === 'antifona');
  ps = pvAntifonas(ps, modo, ant);
  return { f: f, noct: noct, ant: ant, sinAnt: sinAnt, ps: ps };
}

/** En lugar del Te Deum, el tercer responsorio, «Felix namque», que el
 *  libro escribe en las Maitines de Septuagésima: las lecciones son las
 *  mismas, así que se toma de allí, de la misma manera y el mismo nocturno. */
function pvSinTeDeum(ps, modo, noct) {
  const i = ps.findIndex((p) => p[0] === 'h' && p[4] === 'tedeum');
  if (i < 0) return ps;
  let j = i + 1;
  while (j < ps.length && ps[j][0] !== 'h') j++;
  const s = E.parvoDatos.h[modo + '_sept_mat' + noct] || [];
  const a = s.findIndex((p) => p[0] === 'h' && p[4] === 'leccion3');
  if (a < 0) return ps;
  let b = a + 1;
  while (b < s.length && s[b][0] !== 't' && s[b][0] !== 'h') b++;
  let c = b;
  while (c < s.length && s[c][0] !== 'h') c++;
  if (b >= s.length || s[b][0] !== 't') return ps;
  return ps.slice(0, i).concat(s.slice(b, c), ps.slice(j));
}

function pvAntifonas(ps, modo, quiere) {
  const out = [];
  for (let i = 0; i < ps.length;) {
    const p = ps[i];
    if (!(p[0] === 'h' && p[4] === 'antifona')) { out.push(p); i++; continue; }
    let j = i + 1;
    while (j < ps.length && ps[j][0] !== 'h') j++;
    // los días que no se dice ninguna, la sección entera se va: con ella el
    // «Divínum auxílium», que es el cierre de la antífona
    if (quiere) {
      for (const q of pvUnaAntifona(ps.slice(i, j), modo, quiere)) out.push(q);
    }
    i = j;
  }
  return out;
}

/** Una sección de la antífona final: la rúbrica de cómo se dice, una o
 *  varias antífonas con su «desde… hasta», y el «Divínum auxílium» que la
 *  cierra. Se deja la que toca; si la página no la trae —la Anunciación en
 *  Cuaresma reza el oficio de Adviento, que sólo trae «Alma
 *  Redemptóris»—, se toma del libro, de la misma manera de rezarlo. */
function pvUnaAntifona(sec, modo, quiere) {
  const P = E.parvoDatos;
  const K = P.claves;
  const cabeza = [];
  const bloques = [];
  const cola = [];
  let k = 1;
  while (k < sec.length && sec[k][0] !== 't') cabeza.push(sec[k++]);
  let b = null;
  for (; k < sec.length; k++) {
    const p = sec[k];
    if (p[0] === 'u' && p[1] === K.divinum) {
      for (const q of sec.slice(k)) cola.push(q);
      break;
    }
    if (p[0] === 't') { b = { k: p[3], ps: [p] }; bloques.push(b); continue; }
    if (b) b.ps.push(p);
  }
  if (!quiere || !bloques.length) return sec;
  let cab = cabeza.filter((p) => !(p[0] === 'r' && K.r_una_sola.indexOf(p[1]) >= 0));
  let el = bloques.find((x) => x.k === quiere);
  if (!el) {
    const lib = P.antifonas[modo] && P.antifonas[modo][quiere];
    if (!lib) return sec;
    el = { k: quiere, ps: lib };
    // la de Pascua se dice de pie: con ella, su rúbrica
    if (quiere === 'regina') cab = pvCabezaDe(modo + '_pasc_compl') || cab;
  }
  return [sec[0]].concat(cab, el.ps, cola);
}

/** Las rúbricas con que empieza la antífona final de una página. */
function pvCabezaDe(clave) {
  const ps = E.parvoDatos.h[clave] || [];
  const i = ps.findIndex((p) => p[0] === 'h' && p[4] === 'antifona');
  if (i < 0) return null;
  const out = [];
  for (let k = i + 1; k < ps.length && ps[k][0] === 'r'; k++) out.push(ps[k]);
  return out;
}

/** Lo que el día tiene de particular, para debajo del título. */
function pvNota(c, iso) {
  const n = [];
  const f = c.f;
  if (f.anun) {
    n.push('Hoy, la Anunciación' + (f.trasladada ? ' (trasladada del 25 de '
      + 'marzo)' : '') + ': se reza el oficio de Adviento'
      + (f.laus ? ', con «Laus tibi» en lugar de «Allelúja»' : '') + '.');
  } else if (f.laus) {
    n.push('Ya empezó la Septuagésima: «Laus tibi» en lugar de «Allelúja»'
      + (c.noct ? (f.purif ? '; hoy, en la Purificación, puede decirse el '
        + 'Te Deum' : ', y el tercer responsorio en lugar del Te Deum') : '')
      + '.');
  }
  if (c.sinAnt) {
    n.push('Del Jueves al Sábado Santo no se dice antífona final de la '
      + 'Virgen: el libro da la Ave Regína hasta el Miércoles Santo, y la '
      + 'Regína cæli desde las Completas del Sábado Santo.');
  }
  if (c.noct) {
    n.push('Nocturno ' + romano(c.noct) + ', el de los '
      + ['', 'domingos, lunes y jueves', 'martes y viernes',
        'miércoles y sábados'][c.noct] + '.' + (pvSinRubricas() ? ''
        : ' Si se rezan la tarde anterior, son los del día siguiente: pasa '
          + 'al día con la flecha.'));
  }
  return n.join(' ');
}

/* ------------------------------------------------------------ pintar */

/** La marca de los datos, a HTML (ver parvo.py). */
function pvTexto(t, latin) {
  let h = esc(latin ? tx(t) : t);
  // entre llaves va lo rojo del renglón: las siglas (V., R., Ant.), que son
  // del texto, y las indicaciones —«(inclinación)», «(se levantan)»—, que
  // se van con las rúbricas cuando se quitan
  h = h.replace(/\{([^}]*)\}/g, (m, s) => '<b class="rub'
      + (/^(V\.|R\.|Ant\.)$/.test(s) ? '' : ' pv-ri') + '">' + s + '</b>')
    .replace(/\[([^\]]*)\]/g, '<b class="rub pv-rol">$1</b>')
    .replace(/[*†]/g, (c) => '<b class="rub pv-ast">' + c + '</b>')
    .replace(/\+/g, '<b class="rub pv-cz">✠</b>')
    .replace(/‹/g, '<i>').replace(/›/g, '</i>');
  return h;
}

/** Los renglones de un verso: la estrofa del himno trae los suyos. */
function pvRenglones(t, rol, latin, enVerso) {
  return t.split('\n').map((ln, i) => {
    let cl = 'ln';
    if (/^\{(V\.|R\.)\}/.test(ln)) cl += ' sigla';
    else if (/^\{Ant\.\}/.test(ln)) cl += ' ant';
    else if (enVerso && !/[*†\n]/.test(t) && t.length > 90) cl += ' pv-prosa';
    return '<span class="' + cl + '">'
      + (i === 0 && rol ? '<b class="rub pv-rol">' + esc(rol) + '</b>' : '')
      + pvTexto(ln, latin) + '</span>';
  }).join('');
}

/** Las piezas de una página, en secciones como las de la hora. Lo que va
 *  antes de la primera sección (la leyenda de quién es quién) sale aparte.
 *  `secs` se llena con lo que el carril y la voz saben de cada sección. */
function pvPinta(ps, secs, lengua, sinRub) {
  const U = E.parvoDatos.u;
  const R = E.parvoDatos.r;
  const antes = [];
  const out = [];
  let sec = null;
  let plegada = false;
  let bloque = [];
  let enVerso = false;
  const cierraBloque = () => {
    if (bloque.length) sec.push('<p class="estrofa-h">' + bloque.join('') + '</p>');
    bloque = [];
  };
  const cierraSec = () => {
    if (!sec) return;
    cierraBloque();
    out.push(sec.join('') + (plegada ? '</div>' : '') + '</section>');
    sec = null;
  };
  ps.forEach((p, i) => {
    if (p[0] === 'h') {
      cierraSec();
      const k = p[4] || 'sec';
      enVerso = PV_VERSO.has(k);
      secs.push({ cl: k, nombre: p[1] });
      const rot = '<span class="vs">' + esc(p[1]) + '</span>'
        + (p[2] ? ' <span class="llano pv-lt">' + esc(p[2]) + '</span>' : '');
      // Las oraciones antes y después del oficio van plegadas: no son
      // obligatorias, y abiertas en cada hora se rezarían de paso. El
      // rótulo es el botón; lo plegado ni se ve ni lo dice la voz.
      plegada = k === 'antes' || k === 'despues';
      const abierta = plegada && !!pvCfg().abre[k];
      sec = ['<section class="hora-sec pv-sec ' + (enVerso ? 'en-verso' : 'prosa')
        + (p[3] ? ' pv-cond' : '') + (plegada ? ' pv-plegada' : '')
        + (sinRub ? ' pv-sin-rub' : '')
        + '" data-cl="' + esc(k) + '">'
        + '<div class="sec-cab"><h2 class="rotulo">'
        + (plegada ? '<button type="button" class="pliega" data-pv-pliega="'
          + k + '" aria-expanded="' + abierta + '">' + rot + '</button>' : rot)
        + '</h2></div>' + (plegada ? '<div class="cuerpo"'
          + (abierta ? '' : ' hidden') + '>' : '')];
      return;
    }
    // sin rúbricas, sólo el texto: fuera la leyenda y los párrafos de
    // rúbrica; las siglas, los títulos y quién dice qué se quedan
    if (sinRub && (p[0] === 'l' || p[0] === 'r')) return;
    if (p[0] === 'l') { antes.push('<p class="pv-leg">' + pvTexto(R[p[1]]) + '</p>'); return; }
    if (!sec) {
      if (p[0] === 'r') antes.push('<p class="pv-leg">' + pvTexto(R[p[1]]) + '</p>');
      return;
    }
    if (p[0] === 'u') {
      const [la, es] = U[p[1]];
      const rol = p[2] || '';
      const marcas = p[3] || '';
      const cl = (marcas.indexOf('s') >= 0 ? ' pv-secreto' : '')
        + (marcas.indexOf('e') >= 0 ? ' pv-estrofa' : '');
      if (lengua === 'ambos') {
        cierraBloque();
        sec.push('<p class="estrofa-h bi-la' + cl + '" lang="la" data-pu="' + i
          + '">' + pvRenglones(la, rol, true, enVerso) + '</p>'
          + '<p class="estrofa-h pv-es' + cl + '" data-pu="' + i + 'e">'
          + pvRenglones(es, '', false, enVerso) + '</p>');
        return;
      }
      const t = lengua === 'es' ? es : la;
      const lns = pvRenglones(t, rol, lengua !== 'es', enVerso);
      // la antífona entera de un salmo y el comienzo de la del siguiente no
      // van en el mismo párrafo: entre las dos se pasa de salmo
      const esAnt = /^\{Ant\.\}/.test(la);
      if (esAnt && bloque.length && bloque[bloque.length - 1].indexOf('ln ant') >= 0) {
        cierraBloque();
      }
      if (cl) {
        cierraBloque();
        sec.push('<p class="estrofa-h' + cl + '"' + (lengua !== 'es' ? ' lang="la"' : '')
          + ' data-pu="' + i + '">' + lns + '</p>');
      } else {
        bloque.push(lns.replace('<span class="ln', '<span data-pu="' + i
          + '"' + (lengua !== 'es' ? ' lang="la"' : '') + ' class="ln'));
      }
      return;
    }
    cierraBloque();
    if (p[0] === 't') {
      sec.push('<p class="estrofa-h pv-t de-tit"><span class="ln tit"><b class="rub">'
        + pvTexto(p[1]) + (p[2] ? ' <span class="pv-lt">· ' + pvTexto(p[2])
          + '</span>' : '') + '</b></span></p>');
    } else if (p[0] === 'r') {
      sec.push('<p class="estrofa-h pv-r"><span class="ln solo-rub"><b class="rub">'
        + pvTexto(R[p[1]]) + '</b></span></p>');
    } else if (p[0] === 'p') {
      // el párrafo de la guía: explica, no manda, y va en tinta
      sec.push('<p class="pv-guia-p">' + pvTexto(R[p[1]]) + '</p>');
    } else if (p[0] === 'c') {
      sec.push('<p class="estrofa-h pv-c"><span class="ln solo-rub"><b class="rub">'
        + pvTexto(p[1]) + '</b></span></p>');
    }
  });
  cierraSec();
  return { antes: antes.join(''), html: out.join('') };
}

/** Las dos cosas que se eligen al empezar: la lengua y la manera. */
function pvAjustes() {
  const c = pvCfg();
  const grupo = (que, ops, sel, rot) => '<div class="alterna pv-elige" '
    + 'role="group" aria-label="' + rot + '">' + ops.map(([v, n]) =>
      '<button type="button" data-pv-' + que + '="' + v + '" aria-pressed="'
      + (v === sel) + '">' + n + '</button>').join('') + '</div>';
  return '<div class="pv-ajustes">'
    + grupo('lengua', PV_LENGUAS, c.l, 'La lengua')
    + grupo('modo', PV_MODOS, c.m, 'Cómo se reza') + '</div>';
}

function pvAtras(href, rot) {
  return '<a class="pv-atras" href="' + href + '">' + ICONO.izq + esc(rot) + '</a>';
}

function pvRuta(hora, iso) {
  return '#/oraciones/parvo/' + hora + (iso && iso !== hoyISO() ? '/' + iso : '');
}

function pvChips(hora) {
  const f = $('#formularios');
  f.className = 'chips finos horas pv-horas';
  f.innerHTML = PV_HORAS.map(([cl, nombre, breve]) => '<button type="button" '
    + 'data-pv-hora="' + cl + '"' + (cl === hora ? ' class="sel"' : '')
    + ' aria-label="' + esc(nombre) + '">' + esc(cl === hora ? nombre : breve)
    + '</button>').join('');
}

function pvActiva() {
  return E.vista === 'devocionario' && !!E.parvo && !!E.parvo.hora;
}

/** La hora del Oficio Parvo. */
async function pvVer(hora, iso) {
  const ruta = location.hash;
  E.vista = 'devocionario';
  E.devoPieza = null;
  E.ultimaDevo = ruta;
  marcaBarra('devocionario');
  const hoy = hoyISO();
  iso = /^\d{4}-\d\d-\d\d$/.test(iso || '') ? iso : hoy;
  hora = PV_HORAS.some((x) => x[0] === hora) ? hora : pvHoraSugerida();
  E.parvo = { iso: iso, hora: hora, secciones: [] };
  $('#cabecera').classList.remove('compacta', 'portada');
  limpiaCabExtra();
  marcaHoy(iso);
  ponFecha(iso);
  $('#celebraciones').innerHTML = '';
  ponColor(pvColor());
  $('#titulo-dia').textContent = pvNombreHora(hora);
  $('#subtitulo-dia').textContent = 'Oficio parvo';
  $('#nota-dia').style.display = 'none';
  pvChips(hora);
  if (!E.parvoDatos) vista.innerHTML = '<p class="aviso cargando">Abriendo el oficio…</p>';
  try {
    await pvCarga();
  } catch (err) {
    vista.innerHTML = '<p class="aviso">No he podido abrir el Oficio Parvo ('
      + esc(err.message) + ').</p>';
    return;
  }
  if (location.hash !== ruta) return;       // se fue a otra parte mientras
  const c = pvCompone(pvCfg().m, iso, hora);
  E.parvo.c = c;
  $('#subtitulo-dia').textContent = 'Oficio parvo · ' + PV_TIEMPOS[c.f.t];
  const nota = pvNota(c, iso);
  $('#nota-dia').textContent = nota;
  $('#nota-dia').style.display = nota ? '' : 'none';
  $('#cab-zoom').innerHTML = botonVoz() + controlZoom();
  pvPintaHora();
  cabeceraFija(true);
  colocaPosicion();
  vozTrasPintar();
}

/** El cuerpo de la hora; se repinta solo al cambiar la lengua o la manera. */
function pvPintaHora() {
  const secs = [];
  // la oración antes del oficio, justo antes del comienzo; la de después,
  // al final de todo
  const ps = E.parvo.c.ps;
  let i = ps.findIndex((p) => p[0] === 'h');
  if (i < 0) i = ps.length;
  const todo = ps.slice(0, i).concat(pvOraciones('antes'), ps.slice(i),
    pvOraciones('despues'));
  const r = pvPinta(todo, secs, pvCfg().l, pvSinRubricas());
  E.parvo.secciones = secs;
  vista.innerHTML = pvAtras('#/oraciones', 'Devocionario') + pvAjustes()
    + r.antes + r.html
    + '<p class="pv-pie"><a href="#/oraciones/parvo/guia">Cómo se reza y qué '
    + 'toca cada día</a></p>';
  pintaCarril(E.parvo);
}

/** Cambiar la lengua o la manera a media hora: el renglón que se leía se
 *  queda donde estaba; si con otra manera ya no está, la sección. */
function pvCambia(que, v) {
  const c = pvCfg();
  if (c[que] === v) return;
  // el primer verso que asoma bajo la cabecera, y su sección
  const cab = $('#cabecera').getBoundingClientRect().bottom;
  const arriba = document.body.classList.contains('cab-fija') ? Math.max(0, cab) : 0;
  let a = null;
  for (const el of vista.querySelectorAll('[data-pu]')) {
    const r = el.getBoundingClientRect();
    if (r.bottom > arriba + 4) { a = { el: el, y: r.top }; break; }
  }
  const s = a && a.el.closest('.hora-sec');
  const nSec = s ? [...vista.querySelectorAll('.hora-sec')].indexOf(s) : -1;
  const clave = a ? String(a.el.dataset.pu).replace(/e$/, '') : null;
  c[que] = v;
  pvGuardaCfg();
  if (que === 'm') E.parvo.c = pvCompone(v, E.parvo.iso, E.parvo.hora);
  pvPintaHora();
  // con otra lengua los versos son los mismos y en el mismo sitio del libro;
  // con otra manera, no (lleva más rúbricas), y se vuelve a la sección
  const el = que === 'l' && clave != null
    ? vista.querySelector('[data-pu="' + clave + '"]') : null;
  if (el && a && window.scrollY > 0) {
    window.scrollTo(0, Math.max(0, Math.round(window.scrollY
      + el.getBoundingClientRect().top - a.y)));
  } else if (nSec > 0) {
    vaASeccion(nSec, false);
  }
  vozTrasPintar();
}

/* ---------------------------------------------------------- la guía */

/** Lo que el libro explica para rezarlo, y lo que la app elige sola. */
async function pvGuia() {
  E.vista = 'devocionario';
  E.devoPieza = null;
  E.parvo = null;
  E.ultimaDevo = location.hash;
  marcaBarra('devocionario');
  modoPanel('Oficio parvo');
  ponColor(pvColor());
  $('#subtitulo-dia').textContent = 'Cómo se reza';
  if (!E.parvoDatos) vista.innerHTML = '<p class="aviso cargando">Abriendo…</p>';
  try {
    await pvCarga();
  } catch (err) {
    vista.innerHTML = '<p class="aviso">No he podido abrir el Oficio Parvo ('
      + esc(err.message) + ').</p>';
    return;
  }
  const P = E.parvoDatos;
  const l = pvCfg().l;
  const iso = hoyISO();
  const hora = pvHoraSugerida();
  const ahora = pvTiempo(iso, 'laudes');
  const tarde = pvTiempo(iso, 'visperas');
  const hoy = ['<b>' + esc(PV_TIEMPOS[ahora.t]) + '</b>'
    + (tarde.t !== ahora.t ? ', y desde las Vísperas, <b>'
      + esc(PV_TIEMPOS[tarde.t]) + '</b>' : ''),
  'Maitines del nocturno ' + romano(pvNocturno(iso)),
  pvAntifonaDe(iso, hora) ? 'antífona final: <i lang="la">'
    + esc(tx(PV_ANTIFONAS[pvAntifonaDe(iso, hora)])) + '</i>'
    : 'sin antífona final'];
  // con su ancla, para llegar desde el pie de la hora
  const parte = (k, ps) => '<div id="' + k + '">' + pvPinta(ps, [], l).html
    + '</div>';
  const partes = PV_MODOS.map(([m, n]) => '<section class="hora-sec pv-sec '
    + 'prosa"><div class="sec-cab"><h2 class="rotulo"><span class="vs">'
    + esc(n) + '</span></h2></div>' + P.partes[m].map((t) =>
      '<p class="pv-guia-p">' + pvTexto(t) + '</p>').join('') + '</section>')
    .join('');
  vista.innerHTML = pvAtras(pvRuta(hora, iso), 'Al oficio de ahora')
    + '<p class="devo-lede">El Oficio Parvo de la Santísima Virgen según las '
    + 'rúbricas de 1954, en latín y en castellano. La app elige sola, por la '
    + 'fecha y por la hora, cuál de sus cinco formas toca, el nocturno de '
    + 'Maitines y la antífona final de la Virgen, y hace lo que las rúbricas '
    + 'dejan dicho para la Septuagésima y la Anunciación.</p>'
    + '<p class="pv-hoy">Hoy: ' + hoy.join(' · ') + '.</p>'
    + pvAjustes()
    + parte('pv-calendario', P.guia.calendario)
    + partes
    + parte('pv-posturas', P.guia.posturas)
    + parte('pv-oraciones', P.guia.oraciones)
    + '<section class="hora-sec pv-sec prosa"><div class="sec-cab"><h2 '
    + 'class="rotulo"><span class="vs">De dónde sale</span></h2></div>'
    + '<p class="pv-guia-p">' + esc(P.fuente) + '.</p>'
    + '<p class="pv-guia-p">' + esc(P.derechos) + '</p></section>';
  colocaPosicion(() => {
    const id = (location.hash.split('#')[2] || '');
    const el = id && document.getElementById(id);
    if (!el) return false;
    el.scrollIntoView({ block: 'start' });
  });
}

/* ------------------------------------------- en el devocionario, una pieza
 * Para que el oficio salga donde se busca —en «A la Virgen y a los santos»,
 * entre los oficios parvos, en el buscador, en las favoritas— entra en el
 * libro como una pieza más, y abrirla lleva a la hora que toca. */
function pvMeteEnElDevocionario() {
  const d = E.devoTodo;
  if (!d || d.piezas.some((p) => p.id === PV_ID)) return;
  const tla = 'Offícium parvum Beátæ Maríæ Vírginis';
  const tes = 'Oficio parvo de la Santísima Virgen María';
  const p = { id: PV_ID, c: 'santos', s: 'La Santísima Virgen',
    f: 'oficio parvo', tla: tla, tes: tes,
    b: [{ t: [[[0, tla]]] }], es: [{ t: [[[0, tes]]] }],
    k: plano([tla, tes, 'oficio parvo de la virgen horas de la virgen '
      + 'officium parvum maitines laudes prima tercia sexta nona visperas '
      + 'completas'].join(' ')) };
  let i = d.piezas.findIndex((x) => x.c === 'santos' && x.s === p.s);
  if (i < 0) i = d.piezas.findIndex((x) => x.c === 'santos');
  if (i < 0) d.piezas.push(p);
  else d.piezas.splice(i, 0, p);
  E.devoDe.set(PV_ID, p);
  devoAplica();
}

/** La puerta, en la portada del devocionario: la hora que toca ahora. */
function pvPuerta() {
  const hora = pvHoraSugerida();
  const f = pvTiempo(hoyISO(), hora);
  return '<a class="devo-destacada pv-puerta" href="' + pvRuta(hora) + '">'
    + '<span class="devo-destacada-ojo">Oficio parvo de la Virgen</span>'
    + '<span class="devo-destacada-t">' + esc(pvNombreHora(hora)) + '</span>'
    + '<span class="devo-destacada-p">' + esc(PV_TIEMPOS[f.t])
    + ' · la hora que toca ahora, con lo que es propio de cada día.'
    + '</span><span class="devo-destacada-ir">' + ICONO.der + '</span></a>';
}

function pvPonPuerta() {
  if (vista.querySelector('.pv-puerta')) return;
  const t = document.createElement('div');
  t.innerHTML = pvPuerta();
  const a = t.firstChild;
  const res = $('#devo-res');
  const busca = vista.querySelector('.devo-busca');
  const lenguas = vista.querySelector('.devo-lenguas');
  if (res) res.before(a);
  else if (busca) busca.after(a);
  else if (lenguas) lenguas.after(a);
  else vista.prepend(a);
}

/* --------------------------------------------------- montado encima */

const pvAntes = {
  verDevocionario: verDevocionario,
  cargaDevocionario: cargaDevocionario,
  loQueSeLee: loQueSeLee,
  conCarril: conCarril
};

verDevocionario = async function (que, cual, mas) {
  // la guía puede llevar detrás su ancla: «guia#pv-oraciones»
  if (que === 'parvo' && /^guia(#|$)/.test(cual || '')) return pvGuia();
  if (que === 'parvo') return pvVer(cual, mas);
  if (que === 'o' && cual === PV_ID) return pvVer(null, null);
  E.parvo = null;
  await pvAntes.verDevocionario(que, cual, mas);
  if (!que && E.vista === 'devocionario') pvPonPuerta();
};

cargaDevocionario = async function () {
  await pvAntes.cargaDevocionario();
  pvMeteEnElDevocionario();
};

loQueSeLee = function () {
  if (pvActiva()) {
    return { v: 'parvo', k: 'p|' + E.parvo.iso + '|' + E.parvo.hora,
      secs: E.parvo.secciones, rot: 'Oficio parvo',
      nada: 'No hay nada que decir en esta hora.' };
  }
  return pvAntes.loQueSeLee();
};

conCarril = function () { return pvActiva() || pvAntes.conCarril(); };

/* La lengua y la manera, arriba de la hora y en la guía. */
/* Abrir o plegar la oración antes o después del oficio: sin repintar —el
 * texto ya está, escondido—, y como se deje se queda para las demás horas.
 * La voz se rehace, que lo abierto se dice y lo plegado no. */
vista.addEventListener('click', (ev) => {
  const b = ev.target.closest('[data-pv-pliega]');
  if (!b || !pvActiva()) return;
  const k = b.dataset.pvPliega;
  const c = pvCfg();
  c.abre = Object.assign({}, c.abre, { [k]: !c.abre[k] });
  pvGuardaCfg();
  const cuerpo = b.closest('.hora-sec').querySelector(':scope > .cuerpo');
  if (cuerpo) cuerpo.hidden = !c.abre[k];
  b.setAttribute('aria-expanded', String(!!c.abre[k]));
  rearmaVoz();
});

vista.addEventListener('click', (ev) => {
  const b = ev.target.closest('[data-pv-lengua], [data-pv-modo]');
  if (!b) return;
  const que = b.dataset.pvLengua ? 'l' : 'm';
  const v = b.dataset.pvLengua || b.dataset.pvModo;
  if (pvActiva()) { pvCambia(que, v); return; }
  if (E.vista === 'devocionario' && location.hash.indexOf('#/oraciones/parvo/guia') === 0) {
    pvCfg()[que] = v;
    pvGuardaCfg();
    const y = window.scrollY;
    pvGuia().then(() => window.scrollTo(0, y));
  }
});

/* Las flechas de la fecha, el «Hoy» y la tira de las horas son de app.js,
 * que las lleva a las Horas: dentro del Oficio Parvo se recogen antes, en
 * la captura, y se quedan aquí. */
document.addEventListener('click', (ev) => {
  if (!pvActiva()) return;
  const b = ev.target.closest('#anterior, #siguiente, #ir-hoy, '
    + '#formularios button[data-pv-hora]');
  if (!b) return;
  ev.stopPropagation();
  const p = E.parvo;
  if (b.id === 'anterior' || b.id === 'siguiente') {
    location.hash = pvRuta(p.hora, suma(p.iso, b.id === 'anterior' ? -1 : 1));
  } else if (b.id === 'ir-hoy') {
    location.hash = pvRuta(p.hora, hoyISO());
  } else if (b.dataset.pvHora !== p.hora) {
    location.hash = pvRuta(b.dataset.pvHora, p.iso);
  } else {
    window.scrollTo({ top: 0, behavior: suave() });
  }
}, true);

document.addEventListener('change', (ev) => {
  if (!pvActiva() || ev.target.id !== 'selector-fecha') return;
  ev.stopPropagation();
  if (ev.target.value) location.hash = pvRuta(E.parvo.hora, ev.target.value);
}, true);

/* El dedo pasa de una hora a la siguiente, como en las Horas, y se para en
 * los extremos: de Maitines no se sale hacia atrás ni de Completas hacia
 * delante. El toque que esconde la cabecera sigue siendo de app.js. */
let pvDedo = null;
document.addEventListener('touchstart', (ev) => {
  pvDedo = null;
  if (!pvActiva() || ev.touches.length !== 1) return;
  if (ev.target.closest('.chips, .alterna, .carril, #cabecera, #barra, '
    + '#voz, input, select, a, button, summary, label')) return;
  const t = ev.touches[0];
  pvDedo = { x: t.clientX, y: t.clientY, t: Date.now() };
}, { passive: true });

document.addEventListener('touchend', (ev) => {
  const d = pvDedo;
  pvDedo = null;
  if (!d || E.cfg.gestos === 'no' || !pvActiva()) return;
  const t = ev.changedTouches[0];
  const dx = t.clientX - d.x;
  const dy = t.clientY - d.y;
  if (Math.abs(dx) < 65 || Math.abs(dx) < Math.abs(dy) * 1.8) return;
  if (Date.now() - d.t > 700) return;
  const i = PV_HORAS.findIndex((x) => x[0] === E.parvo.hora) + (dx < 0 ? 1 : -1);
  if (i < 0 || i >= PV_HORAS.length) return;
  document.body.classList.remove('pantalla-limpia');
  E.entraDesde = dx < 0 ? 'izq' : 'der';
  location.hash = pvRuta(PV_HORAS[i][0], E.parvo.iso);
}, { passive: true });
