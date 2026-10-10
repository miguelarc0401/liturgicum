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
  // la misa: el Ordinario intercalado, y lo que se elige en él
  ordinario: 'plegado', latinBi: 'clementina', ordoOps: {},
  // qué se enseña del formulario (Ajustes, «Qué se enseña de la misa»)
  misaVer: 'todo', misaSecs: null,
  // el formato del texto (Ajustes, «Formato del texto»)
  // el interlineado es un numero: el alto del renglon en centesimas del
  // cuerpo de la letra (162 son 1,62), y se mueve de cinco en cinco
  letra: 'serif', interlinea: 162, medida: 'normal', justifica: 'si',
  particion: 'si', cruces: 'si', despierto: false,
  // y el de cada sección por su cuenta, cuando uno para todas no basta:
  // `fmt` es grupo -> {justifica, interlinea, particion}, y lo que un grupo
  // no diga lo sigue diciendo el general
  fmtUno: 'si', fmt: {},
  // el color de la app: el litúrgico del día, o uno fijo
  color: 'dia',
  // al rezar (Ajustes, «Liturgia de las Horas»)
  carril: 'si', gestos: 'si', rezadas: 'si'
};

const E = {              // todo el estado de la app
  cfg: Object.assign({}, POR_OMISION),
  indice: null, cal: null, lecturas: null,
  lecturasEs: null,      // la pareja castellana, en el bilingüe
  misa: null, latino: null, prefacios: null, ordinario: null,
  rubrica: null,         // nº de rúbrica -> la rúbrica del Ordo
  misaVista: null,       // el formulario que se está leyendo, ya armado
  lects: null,           // las lecturas compuestas del día: {pares, ops, …}
  slugMisa: null,        // la celebración cuyo formulario se está viendo
  celsMisa: null,        // todas las celebraciones de esa fecha
  misaOps: {},           // lo elegido en cada misa (el prefacio, las lecturas)
  pliegues: {},          // qué secciones del Ordinario están abiertas
  horas: null, horasDias: null, hora: null,
  oficio: null,          // la hora que se está rezando, con sus opciones
  horasCel: null,        // la celebración elegida, cuando hay donde elegir
  elecciones: {},        // lo elegido en cada sección, mientras dura la sesión
  diaDe: new Map(),      // slug -> día del índice
  diaDeClave: new Map(), // clave de formulario -> día
  colorDe: new Map(),    // slug -> color litúrgico
  busqueda: null,
  sitios: {},           // fecha|hora -> dónde se dejó esa hora, y cuándo
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

/** La lengua en que se está leyendo, para nombrarla donde hace falta. */
function lengua() {
  return E.cfg.fuente === 'es' ? 'el castellano' : 'el latín';
}

/** El nombre de la versión que se está leyendo, para decirlo en un aviso. */
function nombreFuente() {
  return { clementina: 'la Vulgata Clementina', nova: 'la Nova Vulgata',
    es: 'el castellano', bi: 'el bilingüe' }[E.cfg.fuente] || E.cfg.fuente;
}

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
  guardaSitioHora();
}

/* Cada hora guarda el suyo: volver a Laudes es volver donde se dejó
 * Laudes, no a lo que en Vísperas quedaba a la misma altura. Se olvida al
 * cambiar de día —cada día es otro oficio— y al cabo de un minuto sin
 * volver a ella, que entonces ya no se está siguiendo el mismo rezo. */
const OLVIDO = 60000;

function guardaSitioHora() {
  if (E.vista !== 'horas' || !E.fecha || !E.hora) return;
  E.sitios[E.fecha + '|' + E.hora] = { y: window.scrollY, t: Date.now() };
}

function vuelveAlSitioHora(iso, hora) {
  const s = E.sitios[iso + '|' + hora];
  if (!s || Date.now() - s.t > OLVIDO) return false;
  window.scrollTo(0, s.y);
  return true;
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
  return { fecha: E.fecha, hora: E.hora, cl: cual.dataset.cl,
    dentro: corte - cual.getBoundingClientRect().top };
}

function vuelveADonde(d) {
  if (!d || d.fecha !== E.fecha || d.hora !== E.hora) return false;
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
  numeraInterlineado();
}
function guardaCfg() {
  try { localStorage.setItem('cfg', JSON.stringify(E.cfg)); } catch (_) {}
}

/* El interlineado fueron cuatro nombres y ahora es un numero. Lo que quedo
 * guardado con un nombre se convierte al abrir, y con los numeros que la
 * hoja de estilo le daba entonces: quien tenia «holgado» sigue viendo
 * exactamente el renglon que tenia, y a partir de ahi lo mueve. Vale igual
 * para el general y para lo que diga cada seccion por su cuenta. */
const RENGLON_NOMBRE = { compacto: 142, normal: 162, holgado: 188,
  suelto: 215 };
const RENGLON_MIN = 120, RENGLON_MAX = 260, RENGLON_PASO = 5;

function numeraInterlineado() {
  const n = (v) => (typeof v === 'number' ? v : RENGLON_NOMBRE[v]);
  E.cfg.interlinea = n(E.cfg.interlinea) || POR_OMISION.interlinea;
  const fmt = {};
  for (const g of Object.keys(E.cfg.fmt || {})) {
    const f = Object.assign({}, E.cfg.fmt[g]);
    if ('interlinea' in f) {
      const v = n(f.interlinea);
      if (v) f.interlinea = v; else delete f.interlinea;
    }
    fmt[g] = f;
  }
  E.cfg.fmt = fmt;
}
function aplicaCfg() {
  const b = document.body.dataset;
  b.tema = E.cfg.tema;
  b.letra = E.cfg.letra;
  b.medida = E.cfg.medida;
  b.justifica = E.cfg.justifica;
  b.particion = E.cfg.particion;
  b.cruces = E.cfg.cruces;
  // el interlineado es un numero y no uno de cuatro nombres, asi que no
  // cuelga de un atributo del <body> sino de la variable misma
  const est = document.documentElement.style;
  const [r, rv] = renglones(E.cfg.interlinea);
  est.setProperty('--interlinea', r);
  est.setProperty('--interlinea-verso', rv);
  est.setProperty('--cuerpo', (E.cfg.tam / 100 * 1.0625).toFixed(3) + 'rem');
  aplicaFormatoSecs();
  ponColor(null);
  velaPantalla();
}

/* -------------------------------------------- el color, y el de cada día
 *
 * El color litúrgico tiñe la cabecera, las rúbricas y los controles, y
 * cambia al pasar de un día a otro. Quien no lo quiera cambiando puede
 * fijar uno en Ajustes, y entonces manda ése en toda la app; el del día se
 * sigue guardando, porque es el que vuelve en cuanto se deja de fijar. El
 * calendario no entra en el trato: allí el color de cada día es lo que se
 * está leyendo, no un adorno.
 */
function ponColor(c) {
  if (c) E.colorDia = c;
  document.body.dataset.color = E.cfg.color === 'dia'
    ? (E.colorDia || 'neutro') : E.cfg.color;
}

/* --------------------------------------------- el formato, sección a sección
 *
 * La alineación, el interlineado y la partición de palabras se pueden decir
 * una vez para todo —que es lo que la app traía— o sección por sección: un
 * salmo y una lectura no se leen igual, y quien justifica la lectura no
 * tiene por qué justificar el salmo.
 *
 * Las secciones se agrupan por lo que son y no por el libro en que salen:
 * la primera lectura de la misa y la lectura breve de Vísperas son la misma
 * clase de texto, y quien las quiere a la izquierda las quiere las dos. Lo
 * que no cae en ningún grupo —la reseña del día, la invocación, la
 * conclusión, el examen de conciencia— sigue el formato general, y eso es
 * deliberado: son renglones sueltos, no secciones que se lean seguidas.
 *
 * Cada grupo es una clase en su `<section>` (`fmt-salmos`, `fmt-lecturas`…)
 * y lo que se haya dicho de él vive en una hoja de estilo que se rehace al
 * cambiarlo: un grupo que no dice nada no sale de ella, y entonces hereda
 * del <body> lo que diga el general.
 *
 * El cuarto campo es la forma de su muestra en Ajustes, que no es un dibujo
 * sino el mismo texto con las mismas clases.
 */
const GRUPO_FMT = [
  ['lecturas', 'Lecturas',
    'Las de la misa —la primera, la segunda y el Evangelio— y las del '
    + 'Oficio: la bíblica, la patrística y la lectura breve de las demás '
    + 'horas.', 'prosa'],
  ['salmos', 'Salmos y cánticos',
    'El salmo responsorial de la misa y la aclamación antes del Evangelio; '
    + 'la salmodia de cada hora, el invitatorio y el cántico evangélico.',
    'verso'],
  ['himnos', 'Himnos',
    'El de cada hora, los que se pueden escoger y el Te Deum del Oficio de '
    + 'lectura.', 'verso'],
  ['antifonas', 'Antífonas',
    'Las de entrada y de comunión de la misa, y la antífona final de la '
    + 'Virgen en Completas.', 'ant'],
  ['oraciones', 'Oraciones',
    'La colecta, la oración sobre las ofrendas, la de después de la '
    + 'comunión, la oración sobre el pueblo y la oración de cada hora.',
    'prosa'],
  ['preces', 'Preces y responsorios',
    'La oración de los fieles de la misa, las preces de Laudes y Vísperas y '
    + 'los responsorios del Oficio y de las horas menores.', 'preces'],
  ['ordinario', 'El Ordinario de la misa',
    'Las 146 rúbricas del Ordo intercaladas donde van, con el prefacio y la '
    + 'plegaria eucarística.', 'ordo']
];

/* De qué grupo es cada sección. Las claves son las de la hora
 * (`horas.json`, el orden de cada hora) y las de la misa (`ROTULO_SEC`). */
const FMT_DE_SEC = {
  lectura1: 'lecturas', lectura2: 'lecturas', lectura12: 'lecturas',
  lectura_breve: 'lecturas', conm_lectura: 'lecturas',
  salmodia: 'salmos', salmodia2: 'salmos', cantico_evangelico: 'salmos',
  invitatorio: 'salmos',
  himno: 'himnos', himno2: 'himnos',
  antifona_final: 'antifonas', entrada: 'antifonas', comunion: 'antifonas',
  oracion: 'oraciones', oracion2: 'oraciones', oracion3: 'oraciones',
  colecta: 'oraciones', ofrendas: 'oraciones', poscomunion: 'oraciones',
  pueblo: 'oraciones',
  preces: 'preces', responsorio: 'preces', responsorio2: 'preces',
  responsorio_breve: 'preces', conm_resp: 'preces', fieles: 'preces',
  // el prefacio es del día, pero se lee como el Ordinario en que va metido
  prefacio: 'ordinario'
};

/* Las lecturas de la misa no son una sección fija sino las que traiga el
 * día, así que su grupo sale de su clase (`claseLectura`). */
const FMT_DE_LECTURA = {
  'lect:lectura': 'lecturas', 'lect:evangelio': 'lecturas',
  'lect:salmo': 'salmos', 'lect:aleluya': 'salmos'
};

/* La tabla manda sobre el Ordinario, y no al revés: la oración de los fieles
 * va en el Ordo —el Misal pone ahí su rúbrica y no las intenciones—, pero
 * quien ajusta las preces espera que ésa vaya con ellas. */
function grupoFmt(s) {
  if (s.k) return FMT_DE_LECTURA[s.k] || 'lecturas';
  return FMT_DE_SEC[s.cl] || (s.ordo ? 'ordinario' : '');
}

/** La clase que lleva la sección, o nada si no es de ningún grupo. */
function claseFmt(g) { return g ? ' fmt-' + g : ''; }

/* El interlineado, en los dos números que la hoja necesita: el de la prosa
 * y el de los versos, que van más apretados —un renglón de salmo es corto y
 * el aire lo pone el renglón siguiente, no el espacio entre líneas—.
 *
 * El segundo sale del primero y no de una tabla, porque el primero ya no es
 * uno de cuatro escalones sino cualquier número: lo que se guarda es la
 * proporción que tenían esos cuatro (1,62 de prosa iban con 1,50 de verso),
 * de modo que quien no toque nada siga viendo lo mismo y quien lo mueva se
 * lleve los dos renglones a la vez. */
function renglones(n) {
  const p = n / 100;
  return [p.toFixed(2), (1 + (p - 1) * 0.806).toFixed(2)];
}

/** El interlineado en cifras de leer: «1,62», y entre paréntesis cuando es
 *  prestado del general y no de la sección. */
function cifraRenglon(v, heredada) {
  const t = (v / 100).toFixed(2).replace('.', ',');
  return heredada ? '(' + t + ')' : t;
}

/** Lo que se haya dicho de cada grupo, en una hoja de estilo que se rehace
 *  entera al cambiarlo. Con un solo formato para todas no se escribe nada:
 *  manda el <body> y no hay nada que pisar. */
function aplicaFormatoSecs() {
  let css = '';
  if (E.cfg.fmtUno !== 'si') {
    for (const g of GRUPO_FMT) {
      const f = (E.cfg.fmt || {})[g[0]] || {};
      const d = [];
      if (f.interlinea) {
        const r = renglones(f.interlinea);
        d.push('--interlinea:' + r[0], '--interlinea-verso:' + r[1]);
      }
      if (f.justifica) {
        d.push('--alinea:' + (f.justifica === 'no' ? 'left' : 'justify'));
      }
      if (f.particion) {
        d.push('--parte:' + (f.particion === 'no' ? 'manual' : 'auto'));
      }
      if (d.length) css += '.fmt-' + g[0] + '{' + d.join(';') + '}\n';
    }
  }
  let h = document.getElementById('fmt-secs');
  if (!h) {
    h = document.createElement('style');
    h.id = 'fmt-secs';
    document.head.appendChild(h);
  }
  h.textContent = css;
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

/* El bilingüe son dos leccionarios a la vez: el latino que se estuviera
 * leyendo —el que se elija en Ajustes queda recordado, así que quien prefiere
 * la Nova la sigue teniendo— y el castellano. Los dos traen los mismos
 * bloques en el mismo orden para las mismas claves (comprobado: 1 035 claves
 * y ni una desigual), así que la pareja de cada lectura es la que ocupa su
 * mismo sitio. `E.lecturas` sigue siendo el latino, que es sobre el que se
 * busca. */
async function cargaLecturas(fuente) {
  const la = fuente === 'bi' ? (E.cfg.latinBi || 'clementina') : fuente;
  if (!E.lecturas || E.lecturas.fuente !== la) {
    E.lecturas = await json('lecturas_' + la + '.json');
    E.busqueda = null;
  }
  if (fuente === 'bi' && !E.lecturasEs) {
    E.lecturasEs = await json('lecturas_es.json');
  }
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

/** Una lectura, y en el bilingüe su pareja al lado. Los dos leccionarios
 *  dan los mismos bloques en el mismo orden, así que la pareja es la que
 *  ocupa su mismo sitio: no hay que casar nada. */
function pintaLectura(l, l2) {
  // el grupo del formato: un salmo y una lectura no se leen igual, y en
  // Ajustes se puede decir de cada uno
  const g = claseFmt(FMT_DE_LECTURA[claseLectura(l)] || 'lecturas');
  if (!l2) {
    return '<section class="lect' + g + '">' + cuerpoLectura(l) + '</section>';
  }
  return '<section class="lect' + g + '"><div class="bi">'
    + '<div class="bi-la" lang="la">' + cuerpoLectura(l) + '</div>'
    + '<div class="bi-es">' + cuerpoLectura(l2) + '</div></div></section>';
}

function cuerpoLectura(l) {
  const h = [];
  // La acentuación litúrgica es del latín: es un agudo que se le pone a la
  // vocal tónica para recitar, y quitárselo al castellano sería estropearle
  // la ortografía. `l.es` lo dice pieza por pieza, no la fuente entera,
  // porque el leccionario latino trae alguna cosa en castellano.
  const t = (s) => esc(l.es ? s : tx(s));
  if (l.t) h.push('<h3 class="rubrica">' + t(l.t) + '</h3>');
  // La cita es la del leccionario. Cuando el misalito imprime el texto con
  // otros versículos del mismo capítulo —el leccionario de México escoge a
  // veces otras estrofas del mismo salmo— el texto que se lee abajo es el de
  // la cita castellana, no el de la latina, y eso se dice: `l.ces`.
  const cita = esc(l.c) + (l.ces
    ? '<span class="cita-es"> · en castellano, ' + esc(l.ces) + '</span>'
    : '');
  if (l.f) {
    h.push('<p class="formula">' + t(l.f)
      + '<span class="cita">' + cita + '</span></p>');
  } else if (l.c) {
    h.push('<p class="formula"><span class="cita">' + cita
      + '</span></p>');
  }
  // Lo que el misalito no imprimió en los nueve años: se dice y no se tapa,
  // y no se traduce del latín. El latín está a un cambio de ajuste.
  if (l.sin) {
    return h.join('') + '<p class="omision">No disponible en castellano. '
      + 'En latín, sí.</p>';
  }
  if (l.s) h.push('<p class="sumario">' + t(l.s) + '</p>');
  if (l.k === 'salmo' || l.k === 'aleluya') {
    if (l.r) h.push('<p class="antifona">℟. ' + t(l.r) + '</p>');
    else if (l.rr) h.push('<p class="antifona">℟. (' + esc(l.rr) + ')</p>');
  }
  if (l.k === 'salmo') {
    h.push(versos(l.g, '<p class="resp">℟.</p>', l.es));
    h.push('<p class="resp">℟.</p>');
  } else {
    h.push(versos(l.g, null, l.es));
    // el cierre: el castellano lo trae por lectura, porque cambia («Palabra
    // de Dios» en la lectura y «Palabra del Señor» en el evangelio); el
    // latino es uno para todo el libro y vive en la cabecera del fichero
    const z = l.z || (l.k === 'lectura' && !l.es ? E.lecturas.cierre : '');
    if (z) h.push('<p class="cierre">' + t(z) + '</p>');
    if (l.rz) h.push('<p class="resp">' + t(l.rz) + '</p>');
    else if (l.r && l.k === 'aleluya') {
      h.push('<p class="resp">℟. ' + t(l.r) + '</p>');
    }
  }
  return h.join('');
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
/* El título ha de **empezar** por el nombre de la celebración mariana, con
 * su artículo o sin él. Nombrar a la Virgen no es ser de la Virgen: «San
 * José, esposo de santa María Virgen» es de san José y va de blanco, y lo
 * mismo «Santos Joaquín y Ana, padres de la Santísima Virgen María» y los
 * Siervos de santa María. Son los cuatro títulos del índice que decían azul
 * sin serlo; los quince que sí lo son siguen diciéndolo. */
const DE_LA_VIRGEN = new RegExp('^(?:(?:el|la|los|las) )?(?:' + [
  'santisima virgen maria', 'nuestra senora', 'santa maria virgen',
  'santa maria madre', 'inmaculada concepcion', 'inmaculado corazon',
  'la asuncion de la', 'la natividad de la santisima',
  'la visitacion de la santisima', 'la presentacion de la santisima',
  'maria madre de la iglesia', 'la virgen maria', 'santa maria en sabado'
].join('|') + ')');

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

/* ------------------------------------------- las lecturas que hoy se leen
 *
 * **En una memoria no se leen las lecturas del santo: se lee la feria.** Lo
 * manda el Ordo lectionum Missae (n. 83) y lo repite la Instrucción general
 * del Misal (n. 357): «In memoriis Sanctorum, nisi habeantur propriae,
 * leguntur de more lectiones feriae assignatae». Lo que la página del santo
 * imprime son, en 149 de las 162 memorias, las sugerencias del Común a las
 * que ella misma remite —«Del Común de pastores»—, y el mismo n. 83 dice
 * qué son: «Agitur tamen de suggestionibus».
 *
 * Cuándo sí manda el santo lo dice la fuente **expresamente**, y el n. 83
 * promete que lo dirá: «Quoties de huiusmodi lectionibus agitur in memoria,
 * id in hoc Ordine expresse suo loco indicatur». Son diez celebraciones, y
 * son **las mismas diez** en el leccionario castellano («el evangelio de
 * esta memoria es propio») y en el Ordo latino de 1981 («Evangelium huius
 * memoriae est proprium»). Dos libros que dicen lo mismo es lo que
 * convierte esto en dato; viene resuelto en el índice (`ld` y `lp`).
 *
 * Y una cosa que no está en los libros y sí en las fuentes diarias, medida
 * sobre los cien misalitos y los once años del sitio: **la pieza que
 * acompaña se va con la que manda.** El salmo va con la primera lectura y
 * la aclamación con el Evangelio, porque así los compone el leccionario. El
 * 29 de julio de 2023, Santa Marta, el misalito imprimió la primera lectura
 * y el salmo de la feria y la aclamación y el evangelio de la santa.
 *
 * Las cifras, de 3 942 días cotejados contra lo que la fuente imprimió:
 *
 *   memorias que remiten al Común   feria 306/352 · 297/350 · 283/346 · 326/362
 *   memorias con lecturas apropiadas feria  70/70 ·  68/70 ·  62/66 ·  58/73
 *   las diez, en la ranura declarada santo, y la acompañante con ella
 */
const ACOMPANA = { l1: 'lect:salmo', ev: 'lect:aleluya' };
const RANURA_CLASE = { l1: 'lect:lectura', l2: 'lect:lectura',
  ev: 'lect:evangelio' };

/** El bloque que el calendario eligió para una celebración de la fecha. */
function bloqueDe(cel) {
  const d = cel && cel.dia;
  if (!d || !d.b || !d.b.length) return null;
  const i = (cel.bloque >= 0 && cel.bloque < d.b.length) ? cel.bloque : 0;
  return d.b[i];
}

/** Los pares [clave, índice] de un bloque entero, en su orden. */
function paresDe(k) {
  return ((E.lecturas.bloques || {})[k] || []).map((_, i) => [k, i]);
}

/** Las lecturas de un par, en la fuente que esté puesta. */
function lecturaDePar(p) {
  return ((E.lecturas.bloques || {})[p[0]] || [])[p[1]] || null;
}

/** Compone las lecturas del día: cuáles se leen y qué se puede elegir.
 *
 *  Devuelve `{pares, ops, i, nota}`. `ops` son las opciones que de verdad
 *  hay —y sólo las hay cuando la celebración tiene algo suyo, que es lo que
 *  pedía el encargo: no ofrecer «otra lectura» donde el libro no la da—.
 */
function composicionLecturas(slug, cels, clave) {
  const cel = (cels || []).find((o) => o.slug === slug);
  const d = E.diaDe.get(slug);
  const propias = paresDe(clave);
  if (!cel || !d) return { pares: propias, ops: null, i: 0, nota: '' };
  const esMemoria = /^memoria/i.test((cel.m && cel.m.g) || d.g || '');
  const feria = (cels || []).find((o) => o.m && o.m.f && o.slug !== slug);
  const kFeria = feria && (bloqueDe(feria) || {}).k;
  // `ld` sólo lo lleva el santoral, y sin él no se sabe de dónde son las
  // lecturas de esa celebración: entonces no se toca nada. Es lo que deja
  // fuera a la misa de **Santa María en sábado**, que no es una entrada del
  // santoral sino el Común de la Virgen abierto a propósito, y cuyas
  // lecturas son las de ese Común —así lo dice su propia rúbrica—.
  if (!esMemoria || !d.ld || !kFeria
      || !(E.lecturas.bloques || {})[kFeria]) {
    return { pares: propias, ops: null, i: 0, nota: '' };
  }

  // la feria, que es lo que se lee, con lo que el libro declara propio
  // puesto en su sitio
  const deFeria = paresDe(kFeria);
  const lp = d.lp || [];
  let pares = deFeria;
  if (lp.indexOf('*') >= 0) {
    pares = propias;
  } else if (lp.length) {
    const quita = new Set();
    for (const r of lp) {
      if (RANURA_CLASE[r]) quita.add(RANURA_CLASE[r]);
      if (ACOMPANA[r]) quita.add(ACOMPANA[r]);
    }
    const mete = propias.filter((p) => {
      const l = lecturaDePar(p);
      return l && quita.has(claseLectura(l));
    });
    // Si la celebración no trae nada de esa clase, no se quita nada: antes
    // que dejar al día sin Evangelio, se deja el de la feria.
    if (!mete.length) {
      pares = deFeria;
    } else {
      // en el sitio de la primera que sustituye, y en el orden del libro
      pares = [];
      let puesto = false;
      for (const p of deFeria) {
        const l = lecturaDePar(p);
        if (l && quita.has(claseLectura(l))) {
          if (!puesto) { pares = pares.concat(mete); puesto = true; }
          continue;
        }
        pares.push(p);
      }
      if (!puesto) pares = pares.concat(mete);
    }
  }

  // el rótulo del botón no lleva el nombre de la celebración: cortado por
  // la primera coma deja «De Santos Cirilo» y «De Dedicación de las
  // basílicas de Sa…». El nombre entero va en el título, que es donde cabe.
  const ops = [];
  ops.push({ id: 'dia', rot: 'De la feria', tit: feria.m.t });
  if (d.ld === 'propias' || d.ld === 'apropiadas') {
    ops.push({ id: 'santo', rot: 'De la memoria', tit: d.t });
  }
  let nota = '';
  if (lp.indexOf('*') >= 0) {
    nota = 'Las lecturas de esta memoria son propias: se leen en lugar de '
      + 'las de la feria.';
  } else if (lp.length) {
    const q = lp.indexOf('l1') >= 0 ? 'la primera lectura, y con ella el '
      + 'salmo,' : 'el Evangelio, y con él la aclamación,';
    nota = 'En esta memoria ' + q + ' es propio: se lee en lugar del de la '
      + 'feria. Lo demás es de la feria.';
  } else if (d.ld === 'apropiadas') {
    nota = 'Las lecturas del día son las de la feria. Esta memoria tiene '
      + 'además lecturas apropiadas, que pueden tomarse si una razón '
      + 'pastoral lo aconseja (OLM 83).';
  } else {
    nota = 'Las lecturas del día son las de la feria: esta memoria no '
      + 'tiene lecturas propias, y las que su formulario ofrece son las '
      + 'del ' + (d.b[1] ? (d.b[1].e || '').toLowerCase() : 'Común')
      + ', a las que el leccionario remite (IGMR 357).';
  }

  let i = 0;
  if (ops.length > 1) {
    const q = (E.misaOps[clave] || {}).lecturas;
    i = Math.max(0, ops.findIndex((o) => o.id === q));
    if (i > 0) pares = propias;
  }
  return { pares: pares, ops: ops.length > 1 ? ops : null, i: i, nota: nota };
}

/* ------------------------------------------- las oraciones que hoy se dicen
 *
 * Dos reglas de la Instrucción general del Misal, las dos sobre lo mismo:
 * qué se puede tomar de otro sitio y qué no.
 *
 * **n. 363**, en las memorias: «dicitur collecta propria vel, si deest, de
 * Communi congruenti; orationes vero super oblata et post Communionem, nisi
 * sint propriae, sumi possunt aut e Communi aut e feriis temporis
 * currentis». La colecta es siempre del santo —y así sale ya, en 152 de las
 * 163 memorias es la suya—; las otras dos, cuando **no** son propias, se
 * pueden tomar de la feria. Son 23 ofrendas y 13 poscomuniones.
 *
 * **n. 355 a)**, en las ferias privilegiadas: en el Adviento del 17 al 24,
 * en la octava de Navidad y en las ferias de Cuaresma, «dicitur Missa de
 * die liturgico occurrente; de memoria autem in calendario generali eo die
 * forte inscripta sumi potest collecta». La misa es del día y del santo
 * sólo se puede tomar **la colecta**. Son 522 días del calendario, y hasta
 * ahora la app no decía ni que el santo estuviera ahí.
 *
 * El rango 9 de la Tabla de los días litúrgicos es exactamente ese
 * conjunto: el Miércoles de Ceniza y las ferias de la Semana Santa, que el
 * n. 355 exceptúa, son de rango 2 y no entran.
 */
function composicionOraciones(slug, cels, clave) {
  const vacio = { ops: null, nota: '', claveOtra: null };
  const cel = (cels || []).find((o) => o.slug === slug);
  const d = E.diaDe.get(slug);
  if (!cel || !d || !E.misa) return vacio;
  const f = E.misa.formularios[clave];
  const m = cel.m || {};

  // la conmemoración: la misa es de la feria y del santo sólo la colecta
  if (m.k === 't' && m.r === 9) {
    const san = (cels || []).find((o) => o.m && o.m.k === 's' && !o.m.z);
    const k = san && (bloqueDe(san) || {}).k;
    if (!san || !k || !E.misa.formularios[k]) return vacio;
    return { claveOtra: k, otra: san, porOmision: { colecta: 'dia' },
      ops: { colecta: [{ id: 'dia', rot: 'De la feria', tit: d.t },
        { id: 'otra', rot: 'De la memoria', tit: san.m.t }] },
      nota: 'Hoy la misa es del día. De ' + corto(san.m.t) + ' ('
        + (san.m.g || 'memoria').toLowerCase() + ') puede tomarse la '
        + 'colecta, y sólo ella (IGMR 355 a).' };
  }

  // la memoria: lo que no es propio puede venir de la feria
  if (!f || !/^memoria/i.test(m.g || d.g || '')) return vacio;
  const feria = (cels || []).find((o) => o.m && o.m.f && o.slug !== slug);
  const k = feria && (bloqueDe(feria) || {}).k;
  if (!k || !E.misa.formularios[k]) return vacio;
  const ops = {};
  const porOmision = {};
  for (const ran of ['ofrendas', 'poscomunion']) {
    const p = (f.p || {})[ran];
    const q = (E.misa.formularios[k].p || {})[ran];
    if (!q || (p && p.via === 'celebración')) continue;
    ops[ran] = [{ id: 'dia', rot: p ? 'Del común' : 'No la trae',
      tit: 'Como la trae el formulario de la memoria' },
    { id: 'otra', rot: 'De la feria', tit: feria.m.t }];
    // si la memoria no trae nada en esa ranura, lo que se dice es la feria:
    // dejar la ranura en blanco sería enseñar un hueco donde hay texto
    porOmision[ran] = p ? 'dia' : 'otra';
  }
  if (!Object.keys(ops).length) return vacio;
  return { claveOtra: k, otra: feria, ops: ops, porOmision: porOmision,
    nota: 'La oración sobre las ofrendas y la de después de la comunión, '
      + 'cuando no son propias de la memoria, pueden tomarse del común o de '
      + 'la feria (IGMR 363).' };
}

/** El formulario del que sale una ranura, con la opción elegida. */
function formularioDe(ranura, f, lat, clave) {
  const O = E.oraciones;
  if (!O || !O.ops || !O.ops[ranura]) return { f: f, lat: lat };
  const q = (E.misaOps[clave] || {})['or_' + ranura]
    || (O.porOmision || {})[ranura] || 'dia';
  if (q !== 'otra') return { f: f, lat: lat };
  const g = E.misa.formularios[O.claveOtra];
  return { f: g || f, lat: (g && g.la) ? (E.latino.formularios[g.la] || null)
    : null };
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
  // la fecha del formulario que se está viendo, que no siempre es `E.fecha`:
  // desde el índice se abre un formulario sin día, y entonces no hay fecha
  // que mirar. La usan los propios de la plegaria para saber si es domingo.
  E.isoMisa = iso || null;
  E.celMisa = null;
  // se borra aquí y no al componerla: si el formulario no llega a pintarse,
  // lo que quede de la misa anterior pintaría sus lecturas en ésta
  E.lects = null;
  E.slugMisa = null;
  E.celsMisa = null;
  const d = E.diaDe.get(slug);
  if (!d) { vista.innerHTML = '<p class="aviso">No encuentro ese día.</p>'; return; }
  if (bloque >= d.b.length || bloque < 0) bloque = 0;
  const b = d.b[bloque];
  const cel = (cels || []).find((o) => o.slug === slug);
  // y la celebración misma, con su rango de la Tabla de los días
  // litúrgicos: el Gloria y el Credo lo necesitan (`feriaSinGloriaNiCredo`)
  E.celMisa = (cel && cel.m) || null;
  ponColor(((cel && cel.m.smv) || esDeLaVirgen(d.t))
    ? 'azul' : E.colorDe.get(slug) || 'neutro');
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
  // el tamaño de la letra, también en la misa: el formulario se lee igual
  // que la hora, y la cabecera es la que se queda arriba al bajar
  $('#cab-zoom').innerHTML = controlZoom();
  pintaChipsCelebraciones(cels || [], slug);
  pintaChipsFormularios(d, bloque);
  pintaNota(cel, val);
  // Qué lecturas se leen hoy, que en una memoria no son las del santo.
  //
  // Se compone **antes** de rendirse: el 31 de enero la fuente castellana
  // no imprime las lecturas propias de san Juan Bosco —ni las de él ni las
  // de otros ocho santos, porque ese día reza por la feria—, y la app decía
  // «este formulario no está en castellano» teniendo delante las de la
  // feria, que son justo las que hoy se leen.
  E.slugMisa = slug;
  E.celsMisa = cels || [];
  E.lects = composicionLecturas(slug, E.celsMisa, b.k);
  const hoy = E.lects.pares.map(lecturaDePar).filter(Boolean);
  if (!hoy.length) {
    vista.innerHTML = '<p class="aviso">Este formulario no está en '
      + esc(nombreFuente()) + '.</p>';
    return;
  }
  pintaCuerpoMisa(b.k, hoy);
  if (iso) { E.ultimaMisa = location.hash; cabeceraFija(true); }
  colocaPosicion();
}

/* El cuerpo de la misa: el formulario entero si los cuatro ficheros del
 * Misal ya están, y las lecturas solas mientras no estén. Son 3,8 MB que no
 * se precachean, así que la primera misa de la sesión se abre por las
 * lecturas —que es lo que se busca— y el formulario entra cuando llega. */
function pintaCuerpoMisa(clave, lects) {
  E.claveMisa = clave;
  const entero = E.misa ? pintaMisaEntera(clave, lects) : null;
  if (entero) {
    vista.innerHTML = entero;
    pintaCarril(E.misaVista);
    aprietaCabeceras();
    return;
  }
  E.misaVista = null;
  limpiaCarril();
  vista.innerHTML = lects.map((l, i) =>
    pintaLectura(l, parejaEs(clave, i))).join('')
    + (E.misa ? '' : '<p class="aviso cargando">Abriendo el formulario…</p>');
  if (E.misa) return;
  cargaMisa().then((bien) => {
    if (E.vista !== 'hoy' || E.claveMisa !== clave) return;
    if (bien) {
      const h = pintaMisaEntera(clave, lects);
      if (h) {
        vista.innerHTML = h;
        pintaCarril(E.misaVista);
        aprietaCabeceras();
        return;
      }
    }
    const aviso = vista.querySelector('.aviso.cargando');
    if (!aviso) return;
    aviso.classList.remove('cargando');
    aviso.textContent = bien
      ? 'De esta misa el Misal no trae formulario: sólo sus lecturas.'
      : 'No he podido abrir el formulario de la misa. Es lo único de la app '
        + 'que no viene guardado de antemano —son 3,8 MB—: la primera vez '
        + 'hace falta conexión, y después queda en el teléfono.';
  });
}

/* ========================================================= la misa entera
 *
 * La sección «Misa» enseñaba las lecturas; lo que el Misal imprime es el
 * formulario entero. Aquí se arma: los propios en su sitio, las lecturas
 * dentro, el Ordinario intercalado donde va —plegado, porque no se lee cada
 * día, pero cuando se busca se busca ahí— y lo que queda a elegir.
 *
 * Aquí no se decide nada, igual que con las lecturas: `datos/misa.json` trae
 * cada pieza ya resuelta y auditada por el módulo Missale —de qué
 * celebración sale, por qué camino y con cuántos testigos—,
 * `misal_latino.json` el Misal de 2002 por su propio nombre,
 * `prefacios.json` los dos juegos emparejados por número de rúbrica y
 * `ordinario.json` las 146 rúbricas del Ordo en las dos lenguas. Son 3,8 MB
 * que el service worker no precachea a propósito —serían 3,8 MB inútiles en
 * el teléfono de quien sólo lee las lecturas—, pero que sí guarda en cuanto
 * se piden: la primera misa necesita conexión y de ahí en adelante no. Si no
 * llegan, las lecturas se enseñan igual y se dice qué es lo que falta.
 */
let _pidiendoMisa = null;

async function cargaMisa() {
  if (E.misa) return true;
  if (!_pidiendoMisa) {
    _pidiendoMisa = Promise.all([json('misa.json'), json('misal_latino.json'),
      json('prefacios.json'), json('ordinario.json')]).then(([m, l, p, o]) => {
      E.misa = m; E.latino = l; E.prefacios = p; E.ordinario = o;
      E.rubrica = new Map(o.rubricas.map((r) => [String(r.n), r]));
      return true;
    }, () => { _pidiendoMisa = null; return false; });
  }
  return _pidiendoMisa;
}

/* La lengua del formulario es la misma que la de las lecturas, que es la que
 * se elige en Ajustes: el castellano es la traducción de México cosechada
 * del misalito, el latín el Misal típico de 2002, y en bilingüe van los dos.
 * Se emparejan rúbrica a rúbrica, que es lo que los dos libros comparten:
 * el Ordinario de México numera como el latino. */
function conLatin() { return E.cfg.fuente !== 'es'; }
function conCastellano() { return E.cfg.fuente === 'es' || E.cfg.fuente === 'bi'; }

/* Los rótulos de sección que el Ordinario imprime pegados al final de la
 * rúbrica anterior —el libro los compone como un titulillo y el volcado los
 * deja donde caen—: «PLEGARIA EUCARÍSTICA» al final de la oración sobre las
 * ofrendas, «Fórmula II» al final del Yo confieso, «Ritus conclusionis» al
 * final de la poscomunión. Se quitan por el texto, uno por uno y nombrados:
 * si la fuente cambia una letra, no se quita nada. */
const ROTULO_PEGADO = new Set([
  'Acto Penitencial', 'Actus pænitentialis *',
  'Fórmula I', 'Fórmula II', 'Fórmula III',
  'Liturgia verbi', 'Liturgia eucharistica',
  'PLEGARIA EUCARÍSTICA', 'PREX EUCHARISTICA', 'PREX EUCHARISTICA II',
  'PREX EUCHARISTICA III', 'PREX EUCHARISTICA IV',
  'PRÆFATIO I DE ADVENTU', 'De duobus adventibus Christi',
  'Ritus communionis', 'Ritus conclusionis'
]);

function textoLinea(ln) { return ln.map((tr) => tr[1]).join('').trim(); }

/** Una línea del Ordinario castellano: viene en tiradas, y el rojo es la
 *  rúbrica (así la marca el PDF del Ordinario de México). */
function lineaEs(ln) {
  return '<span class="ln">' + ln.map((tr) => tr[0]
    ? '<i class="rub">' + esc(tr[1]) + '</i>' : esc(tr[1])).join('')
    + '</span>';
}

/** Los párrafos de un lado del Ordo, en su lengua. El latín pasa por `tx()`
 *  porque su acentuación es la litúrgica y se puede apagar en Ajustes; el
 *  castellano va tal cual, que quitarle las tildes sería estropearlo. */
function ordoBloques(bs, lado) {
  const h = [];
  for (const b of bs || []) {
    const lns = (b.t || []).filter((ln) => !ROTULO_PEGADO.has(
      lado === 'es' ? textoLinea(ln) : String(ln).trim()));
    if (!lns.length) continue;
    // La rúbrica es prosa y sus renglones son los del PDF: se juntan, que
    // partidos no dicen nada. Lo que se reza va por renglones, que así lo
    // compone el Misal —en unidades de sentido, para recitarlo— y así se
    // lee: con sangría francesa, como los salmos.
    if (b.r) {
      const t = lado === 'es'
        ? lns.map(textoLinea).join(' ')
        : lns.map((ln) => String(ln).trim()).join(' ');
      h.push('<p class="ordo-p ordo-rub"><span class="ln">'
        + esc(lado === 'es' ? t : tx(t)) + '</span></p>');
      continue;
    }
    h.push('<p class="ordo-p">' + lns.map((ln) => lado === 'es'
      ? lineaEs(ln) : '<span class="ln">' + esc(tx(ln)) + '</span>')
      .join('') + '</p>');
  }
  return h.join('');
}

/** Renglones llanos —los prefacios, las bendiciones del apéndice—, que no
 *  vienen en tiradas sino en texto seguido. Van en un solo párrafo: lo que
 *  el Misal parte son unidades de sentido, no párrafos. */
function ordoLlano(xs, lado) {
  if (!(xs || []).length) return '';
  return '<p class="ordo-p">' + xs.map((s) => '<span class="ln">'
    + esc(lado === 'la' ? tx(s) : s) + '</span>').join('') + '</p>';
}

/** Las dos lenguas, enfrentadas. En una pantalla estrecha no caben dos
 *  columnas, así que van una debajo de otra y el latín lleva su filete. */
function bilingue(hla, hes) {
  if (!hla) return hes || '';
  if (!hes) return hla;
  return '<div class="bi"><div class="bi-la" lang="la">' + hla + '</div>'
    + '<div class="bi-es">' + hes + '</div></div>';
}

/* ------------------------------------------------------ lo que se elige
 *
 * Qué bloques de una rúbrica son de cada alternativa, medido sobre el
 * fichero y escrito aquí uno por uno. No se deduce, y no se puede: los dos
 * libros no ordenan igual sus alternativas —el latino dice «Dóminus
 * vobíscum» en tercer lugar y el castellano «El Señor esté con ustedes» en
 * el primero—, el latino da una sola invitación al acto penitencial donde el
 * castellano da cuatro, y en el Misterio de la fe la numeración de la fuente
 * no coincide con las tres aclamaciones, porque las dos primeras fórmulas
 * comparten la respuesta del pueblo.
 *
 * `com` son los bloques que van siempre —la rúbrica que introduce, la
 * respuesta del pueblo, lo que sigue—; cada opción añade los suyos, y se
 * imprimen en el orden del libro. Una rúbrica que no esté aquí se imprime
 * entera, con sus alternativas seguidas, igual que el libro las imprime: no
 * se pierde nada por no estar.
 */
const ELIGE = {
  saludo: { rot: 'Saludo', n: '2',
    com: { es: [0, 4, 5, 6, 7], la: [0, 4, 5, 6, 7] },
    ops: [['I', [1], [3]], ['II', [2], [1]], ['III', [3], [2]]] },
  penit_inv: { rot: 'Invitación', n: '4', com: { es: [0], la: [0] },
    ops: [['I', [1], [1]], ['II', [2], [1]], ['III', [3], [1]],
      ['IV', [4], [1]]] },
  oren: { rot: 'Oren, hermanos', n: '29',
    com: { es: [0, 4, 5], la: [0, 2, 3] },
    ops: [['I', [1], [1]], ['II', [2], [1]], ['III', [3], [1]]] },
  padrenuestro: { rot: 'Invitación', n: '124',
    com: { es: [0, 5, 6], la: [0, 2, 3] },
    ops: [['I', [1], [1]], ['II', [2], [1]], ['III', [3], [1]],
      ['IV', [4], [1]]] },
  paz: { rot: 'Invitación a la paz', n: '128',
    com: { es: [0, 5], la: [0, 2] },
    ops: [['I', [1], [1]], ['II', [2], [1]], ['III', [3], [1]],
      ['IV', [4], [1]]] },
  antes_com: { rot: 'Antes de comulgar', n: '131',
    com: { es: [0], la: [0] }, ops: [['I', [1], [1]], ['II', [2], [2]]] },
  despedida: { rot: 'Despedida', n: '144',
    com: { es: [0, 7, 8], la: [0, 2, 3] },
    ops: [['I', [1], [1]], ['II', [2], [1]], ['III', [3], [1]],
      ['IV', [4], [1]], ['V', [5, 6], [1]]] },
  // el Misterio de la fe vive dentro de cada plegaria, y cambia de rúbrica
  // con ella (91, 104, 112 y 121): las cuatro traen los mismos bloques
  misterio: { rot: 'Misterio de la fe', com: { es: [], la: [] },
    ops: [['I', [0, 1, 2, 3, 4], [0, 1, 2, 3]],
      ['II', [0, 5, 6, 7, 8], [0, 1, 2, 4]],
      ['III', [0, 9, 10, 11], [0, 1, 2, 5]]] }
};

/** La elección que lleva cada rúbrica, para que `ordoUna()` la encuentre. */
const ELIGE_DE_RUBRICA = { 2: 'saludo', 4: 'penit_inv', 29: 'oren',
  124: 'padrenuestro', 128: 'paz', 131: 'antes_com', 144: 'despedida',
  91: 'misterio', 104: 'misterio', 112: 'misterio', 121: 'misterio' };

/* Las tres fórmulas del acto penitencial no son tres alternativas de una
 * rúbrica: son tres rúbricas. La primera va pegada detrás de las cuatro
 * invitaciones de la rúbrica 4, y las otras dos son las rúbricas 5 y 6
 * enteras menos su encabezamiento, porque el latino repite la invitación en
 * cada una y el castellano la dice una sola vez. */
const PENITENCIAL = [['I', '4', 5, 2], ['II', '5', 0, 2], ['III', '6', 0, 2]];

/* El símbolo tampoco: el niceno-constantinopolitano es la rúbrica 18 y el de
 * los apóstoles la 19. */
const SIMBOLO = [['Niceno', '18', 'Símbolo niceno-constantinopolitano'],
  ['Apóstoles', '19', 'Símbolo de los apóstoles']];

/** Lo elegido en cada sitio. Lo del Ordinario —el saludo, la despedida, la
 *  plegaria— es de quien celebra y no del día, así que se recuerda con los
 *  demás ajustes; el prefacio es del día y va con la sesión. */
function elegido(id, cuantas) {
  const v = (E.cfg.ordoOps || {})[id];
  const i = typeof v === 'number' ? v : parseInt(v, 10);
  return (i >= 0 && i < cuantas) ? i : 0;
}

function guardaElegido(id, v) {
  if (!E.cfg.ordoOps) E.cfg.ordoOps = {};
  E.cfg.ordoOps[id] = v;
  guardaCfg();
}

/** Los bloques de una rúbrica que tocan, con la opción elegida. */
function bloquesElegidos(r, lado, e, i) {
  const bs = r[lado] || [];
  if (!e) return bs;
  const op = e.ops[i] || e.ops[0];
  const quiero = new Set((e.com[lado] || []).concat(
    lado === 'es' ? op[1] : op[2]));
  return bs.filter((_, j) => quiero.has(j));
}

/** Los párrafos castellanos de una rúbrica de la plegaria que el día pide.
 *
 *  La fase 6 marcó con `p` los que son propios de un día o de una misa
 *  ritual; los que no llevan marca son la plegaria misma y van siempre. Se
 *  quita lo que hoy no se dice, y se deja lo que sí.
 *
 *  **Sólo el castellano.** El Misal latino no imprime estos propios donde el
 *  Ordinario de México los imprime —la rúbrica 105 latina trae el «Meménto»
 *  de difuntos donde la castellana trae los seis «Acuérdate»—, y los dos
 *  libros están alineados por número de rúbrica y no por párrafo. Llevar la
 *  clasificación de uno al otro sería meter la composición de un libro en el
 *  otro, que es justo lo que el informe de la fase 6 mide y rechaza. El latín
 *  se enseña como el Misal lo imprime. */
function bloquesDelDia(bs) {
  if (!_fMisa || !bs.some((b) => b.p)) return bs;
  const cuales = propiosQueTocan(bs.map((b) => b.p), _fMisa);
  return bs.filter((b) => !b.p || cuales.has(b.p.q));
}

/** Cuáles de unos propios toca decir hoy, por su `cual`.
 *
 *  Los del tiempo se emparejan por la unidad del Misal —`tri/cena` es el
 *  Jueves Santo, `pas/oct/3` el miércoles de la octava de Pascua—, y el del
 *  domingo no lleva unidad porque el domingo no es una temporada sino un día
 *  de la semana. **Y va el último**, porque así lo manda su propia rúbrica:
 *  «en los domingos, cuando no hay otro recuerdo más propio». La Navidad, la
 *  Epifanía, la Pascua, la Ascensión y Pentecostés caen en domingo y traen el
 *  suyo; si entra alguno de ésos, el del domingo no.
 *
 *  Los rituales no los decide el día —un bautismo o un funeral caen en
 *  cualquiera—, así que nunca entran por aquí: la tira de detrás los ofrece
 *  juntos y plegados, que es donde quien celebra los busca. */
function propiosQueTocan(ps, f) {
  const fuera = new Set();
  let domingo = null;
  for (const q of ps) {
    if (!q || q.c !== 'tiempo') continue;
    if (!q.u && !q.d) { domingo = q; continue; }
    if ((q.u || []).indexOf(f.u) >= 0 || enTramo(q.d)) fuera.add(q.q);
  }
  if (domingo && !fuera.size && esDomingo(f)) fuera.add(domingo.q);
  return fuera;
}

/** Si el día que se está viendo cae en un tramo de fechas `['12-25','01-01']`.
 *
 *  Hace falta para la octava de Navidad y sólo para ella: dentro caen san
 *  Esteban el 26, san Juan el 27 y los Santos Inocentes el 28, cuyo
 *  formulario es del santoral y no de Navidad, de modo que la unidad del
 *  Misal no los alcanza y el Misal manda el «Reunidos en comunión» de la
 *  Natividad los ocho días. El tramo cruza el año, así que se compara en mes
 *  y día y se admite la vuelta. Sin fecha —el formulario abierto desde el
 *  índice— no se puede decir, y entonces manda la unidad sola. */
function enTramo(d) {
  if (!d || !E.isoMisa) return false;
  const hoy = E.isoMisa.slice(5);
  return d[0] <= d[1] ? (hoy >= d[0] && hoy <= d[1])
    : (hoy >= d[0] || hoy <= d[1]);
}

/** Una rúbrica del Ordo, en las lenguas que toquen. */
function ordoUna(n) {
  const r = E.rubrica.get(String(n));
  if (!r || r.pref) return '';
  const id = ELIGE_DE_RUBRICA[n];
  const e = id ? ELIGE[id] : null;
  const i = e ? elegido(id, e.ops.length) : 0;
  return bilingue(
    conLatin() ? ordoBloques(bloquesElegidos(r, 'la', e, i), 'la') : '',
    conCastellano()
      ? ordoBloques(bloquesDelDia(bloquesElegidos(r, 'es', e, i)), 'es') : '');
}

/* El día que no tiene misa no tiene Ordinario, ni suelto ni pegado a un
 * propio: lo pone `armaMisa` al empezar a armar el formulario. */
let _sinOrdo = false;

/* Y el formulario que se está armando, por la misma razón: las rúbricas
 * numeradas de la plegaria eucarística llevan dentro propios del tiempo —las
 * seis variantes del «Acuérdate, Señor, de tu Iglesia» en la 105, el «Hanc
 * ígitur» del Jueves Santo y de la Pascua en la 87—, y para saber cuál toca
 * hay que saber qué día se está viendo. `ordoUna` no lo recibe: pinta una
 * rúbrica por su número y la llaman desde doce sitios. */
let _fMisa = null;

/* Si las rúbricas del Ordinario se pintan. El día que no hay misa no las
 * tiene. Y el ajuste del Ordinario decide en el modo entero, que es el que
 * trae el Ordo completo se pida o no; en el modo breve y en el propio la
 * decisión ya está tomada pieza por pieza —el Gloria y la oración de los
 * fieles son rúbricas suyas, y se piden por su nombre—, así que allí no
 * manda. */
function hayOrdinario() {
  if (_sinOrdo) return false;
  return E.cfg.misaVer !== 'todo' || E.cfg.ordinario !== 'no';
}

/** Varias rúbricas seguidas. */
function ordo(ns) {
  if (!hayOrdinario()) return '';
  return ns.map(ordoUna).filter(Boolean).join('');
}

/* Las rúbricas del Ordo que caen dentro de una sección que no es suya —la
 * de la colecta antes de la colecta, la de la comunión alrededor de la
 * antífona— también se pliegan: si no, la rúbrica se lleva media pantalla y
 * el texto que se busca queda debajo. Van bajo un rótulo menudo, para que se
 * vea que están y no estorben. */
function ordoPlegado(ns, id) {
  // y sólo en el modo entero: una rúbrica suelta no es una de las piezas
  // que se eligen, y quien pidió unas piezas pidió ésas y no sus bordes
  if (E.cfg.misaVer !== 'todo') return '';
  const h = ordo(ns);
  if (!h || E.cfg.ordinario === 'abierto') return h;
  const abierta = !!E.pliegues[id];
  return '<div class="plegable"><button type="button" class="pliega menuda" '
    + 'data-pliega="' + esc(id) + '" aria-expanded="' + abierta + '">'
    + 'Rúbricas</button><div class="cuerpo"' + (abierta ? '' : ' hidden')
    + '>' + (abierta ? h : '') + '</div></div>';
}

/** Una rúbrica desde cierto bloque hasta el final, que es como se toman las
 *  fórmulas del acto penitencial. */
function ordoDesde(n, des, dla) {
  const r = E.rubrica.get(String(n));
  if (!r) return '';
  return bilingue(
    conLatin() ? ordoBloques((r.la || []).slice(dla), 'la') : '',
    conCastellano()
      ? ordoBloques(bloquesDelDia((r.es || []).slice(des)), 'es') : '');
}

/** Las primeras palabras de un texto: con eso se reconoce una alternativa
 *  sin leerla entera, y es lo que va en el título del botón. */
function primeras(t, n) {
  const p = String(t || '').replace(/\s+/g, ' ').trim().split(' ');
  const c = n || 7;
  return p.slice(0, c).join(' ') + (p.length > c ? '…' : '');
}

/** El primer texto —no rúbrica— de una alternativa, para nombrarla. */
function incipitOpcion(n, id, i) {
  const r = E.rubrica.get(String(n));
  const e = ELIGE[id];
  if (!r || !e) return '';
  for (const lado of ['es', 'la']) {
    if (!r[lado]) continue;
    for (const b of bloquesElegidos(r, lado, e, i)) {
      if (b.r || !b.t.length) continue;
      return primeras(lado === 'es' ? textoLinea(b.t[0]) : b.t[0]);
    }
  }
  return '';
}

/* -------------------------------------------------- los propios del día
 *
 * De dónde salió el texto castellano. La mayoría viene de la celebración o
 * de otra del mismo formulario del Misal, y eso no hace falta decirlo; los
 * caminos más flojos sí se dicen, que es la regla del proyecto: lo que no se
 * pudo resolver del todo se escribe, no se disimula.
 */
const POR_DONDE = {
  'día': ['del día', 'No se pudo atribuir a la celebración: es lo que el '
    + 'misalito imprimió esos días, y todos los días de la celebración que '
    + 'traen algo aquí traen lo mismo'],
  'común': ['del común', 'Del común que el santoral ofrece a esta '
    + 'celebración'],
  'suelto': ['del común', 'De un texto de los comunes que cae entero en '
    + 'este formulario del Misal'],
  'gemela': ['otra misa', 'El misalito no imprimió esta oración aquí, pero '
    + 'el Misal latino da en esta misa la misma oración que en otra que sí '
    + 'está en castellano, y es la que se enseña']
};

/** Una pieza propia del formulario: la antífona de entrada, la colecta, la
 *  oración sobre las ofrendas, la de comunión, la de después. */
function pintaPieza(f, lat, ranura) {
  const p = (f.p || {})[ranura];
  const l = lat && lat.p ? lat.p[ranura] : null;
  if (!p && !l) return '';
  let hes = '';
  if (conCastellano()) {
    if (p) {
      const d = POR_DONDE[p.via];
      hes = '<p class="texto">' + esc(p.t) + '</p>' + (d
        ? '<p class="testigo" title="' + esc(d[1] + '. ' + (p.n || 1)
          + (p.n === 1 ? ' testigo' : ' testigos') + ' en los cien '
          + 'misalitos') + '">' + esc(d[0]) + '</p>' : '');
    } else {
      hes = '<p class="omision">No disponible en castellano. '
        + 'En latín, sí.</p>';
    }
  }
  let hla = '';
  if (conLatin()) {
    if (l) {
      hla = '<p class="texto" lang="la">' + esc(tx((l.t || []).join(' ')))
        + '</p>' + (l.c ? '<p class="formula"><span class="cita">'
          + esc(l.c) + '</span></p>' : '');
    } else if (!conCastellano()) {
      hla = '<p class="omision">El Misal latino no trae esta pieza en este '
        + 'formulario.</p>';
    }
  }
  return bilingue(hla, hes);
}

/* --------------------------------------------------------- los prefacios */

/** Un prefacio, venga del juego castellano, de los propios cosechados del
 *  misalito o de los que sólo existen en el Misal latino. */
function pintaPrefacio(id) {
  const P = E.prefacios;
  const p = P.prefacios[id] || P.propios[id] || P.solo_latino[id];
  if (!p) return '<p class="omision">No encuentro ese prefacio.</p>';
  const soloLa = !!P.solo_latino[id];
  const cosechado = !!P.propios[id];
  let hes = '';
  if (conCastellano()) {
    hes = soloLa
      ? '<p class="omision">No disponible en castellano: este prefacio sólo '
        + 'está en el Misal latino.</p>'
      : '<h3 class="rubrica">' + esc(p.t) + '</h3>'
        + (p.ep ? '<p class="epigrafe">' + esc(p.ep) + '</p>' : '')
        // el prefacio es un solo bloque de renglones, no un párrafo por
        // renglón: lo que el Misal parte son unidades de sentido
        + (cosechado ? ordoLlano(p.tx, 'es')
          : ordoBloques([{ o: 0, r: false, t: p.tx || [] }], 'es'))
        + (p.rub ? '<p class="ordo-p ordo-rub">' + esc(p.rub.join(' '))
          + '</p>' : '');
  }
  let hla = '';
  if (conLatin()) {
    const tl = soloLa ? p.tx : p.tx_la;
    hla = tl
      ? '<h3 class="rubrica" lang="la">' + esc(tx(p.t_la || p.t)) + '</h3>'
        + (p.ep_la ? '<p class="epigrafe" lang="la">' + esc(tx(p.ep_la))
          + '</p>' : '') + ordoLlano(tl, 'la')
      : (conCastellano() ? '' : '<p class="omision">Este prefacio no está en '
        + 'el Misal latino.</p>');
    if (!tl && conCastellano()) {
      hla = '<p class="omision">Sin pareja en el Misal latino.</p>';
    }
  }
  return bilingue(hla, hes);
}

/** Los prefacios que el día marca, con el propio cosechado primero. */
function prefaciosDe(clave, f) {
  const P = E.prefacios;
  const ops = [];
  const mete = (id) => {
    if (!id || ops.some((o) => o.id === id)) return;
    const p = P.prefacios[id] || P.propios[id] || P.solo_latino[id];
    if (p) ops.push({ id: id, t: p.t });
  };
  mete(f.ppd);
  for (const id of f.pr || []) mete(id);
  for (const [id, p] of Object.entries(P.prefacios)) {
    if ((p.cuando || []).includes(clave)) mete(id);
  }
  return ops;
}

/* Cuando el Misal no marca prefacio —y en los domingos del tiempo ordinario
 * no lo marca, porque los ocho están a elección— no se inventa uno: se
 * ofrece el juego del tiempo, que es lo que el libro manda tomar, y se dice
 * que la elección es libre dentro de él. Lo que no cae en un tiempo va a los
 * comunes, que es lo que su propia rúbrica dice: «se dice en las misas que
 * carecen de prefacio propio y no deben tomar un prefacio del tiempo». */
const GRUPO_DEL_TIEMPO = {
  'TIEMPO DE ADVIENTO': 'adviento', 'TIEMPO DE NAVIDAD': 'navidad',
  'TIEMPO DE CUARESMA': 'cuaresma',
  'TRIDUO PASCUAL Y TIEMPO DE PASCUA': 'pascua',
  'PROPIO DE LOS SANTOS': 'santos', 'COMÚN DE LOS SANTOS': 'santos',
  'OTROS FORMULARIOS DEL PROPIO DE LOS SANTOS': 'santos'
};

function grupoDelTiempo(f) {
  if (f.s === 'TIEMPO ORDINARIO' && /^Ciclo/.test(f.e || '')) return 'domingos';
  return GRUPO_DEL_TIEMPO[f.s] || 'comun';
}

function prefaciosDelTiempo(f) {
  const g = grupoDelTiempo(f);
  return Object.entries(E.prefacios.prefacios)
    .filter(([, p]) => p.grupo === g).map(([id, p]) => ({ id: id, t: p.t }));
}

const GRUPO_PREF = [['adviento', 'Adviento'], ['navidad', 'Navidad'],
  ['cuaresma', 'Cuaresma'], ['pascua', 'Pascua'],
  ['domingos', 'Domingos del tiempo ordinario'],
  ['maria', 'Santa María Virgen'], ['santos', 'Santos'],
  ['sacramentos', 'Sacramentos'], ['difuntos', 'Difuntos'],
  ['comun', 'Comunes']];

const GRUPO_PREF_ROT = {};
for (const [g, rot] of GRUPO_PREF) GRUPO_PREF_ROT[g] = rot.toLowerCase();

/** El selector del prefacio. Son 67 castellanos, 28 propios cosechados y 39
 *  que sólo existen en latín: eso no cabe en una burbuja de botones. */
function selectorPrefacio(cual, arriba, rotArriba) {
  const P = E.prefacios;
  const op = (id, t) => '<option value="' + esc(id) + '"'
    + (id === cual ? ' selected' : '') + '>' + esc(t) + '</option>';
  const h = ['<select class="elige" data-elige="prefacio" '
    + 'aria-label="Elegir el prefacio">'];
  if ((arriba || []).length) {
    h.push('<optgroup label="' + esc(rotArriba) + '">');
    for (const o of arriba) h.push(op(o.id, o.t));
    h.push('</optgroup>');
  }
  const por = {};
  for (const [id, p] of Object.entries(P.prefacios)) {
    (por[p.grupo] = por[p.grupo] || []).push([id, p.t]);
  }
  for (const [g, rot] of GRUPO_PREF) {
    if (!por[g]) continue;
    h.push('<optgroup label="' + esc(rot) + '">');
    for (const [id, t] of por[g]) h.push(op(id, t));
    h.push('</optgroup>');
  }
  h.push('<optgroup label="Propios, cosechados del misalito">');
  for (const [id, p] of Object.entries(P.propios)) h.push(op(id, p.t));
  h.push('</optgroup><optgroup label="Sólo en el Misal latino">');
  for (const [id, p] of Object.entries(P.solo_latino)) h.push(op(id, p.t));
  return h.join('') + '</optgroup></select>';
}

/* --------------------------------------------------------- las plegarias */

/** Las que se ofrecen: las cuatro del Ordinario, en las dos lenguas y
 *  numeradas rúbrica a rúbrica, y las seis que sólo trae el Misal latino
 *  —las dos de la reconciliación y las cuatro de diversas necesidades—. */
function plegariasDe() {
  const O = E.ordinario;
  const ops = Object.entries(O.plegarias).map(([id, p]) =>
    ({ id: id, t: p.t }));
  for (const [id, p] of Object.entries(O.plegarias_la)) {
    if (/^prex-eucharistica-i{1,3}$|^prex-eucharistica-iv$/.test(id)) continue;
    ops.push({ id: id, t: p.t, soloLa: true });
  }
  return ops;
}

/* --------------------------------- los propios de la plegaria eucarística
 *
 * Cada plegaria lleva detrás una tira de propios: el «Reunidos en comunión»
 * de la primera y las «Intercesiones particulares» de las otras tres. El
 * Ordinario los imprime todos seguidos, cada uno con la rúbrica que dice
 * cuándo se usa —«En el Jueves Santo:», «En la misa del matrimonio:»—, porque
 * el libro se lee con el dedo y quien celebra salta al que le toca. Una app
 * no se lee con el dedo, y enseñarlos todos es enseñar en un martes del
 * Tiempo Ordinario lo que se dice en la Vigilia Pascual.
 *
 * Así que la fase 6 los clasificó por su rúbrica y aquí se escoge el del día.
 * Dos clases, porque no dependen de lo mismo:
 *
 *   `tiempo`  lo decide el día litúrgico, y el día se sabe: la unidad del
 *             Misal que la fase 5 dio al formulario —`tri/cena` es el Jueves
 *             Santo, `pas/oct/3` el miércoles de la octava de Pascua— y, para
 *             los domingos, el día de la semana.
 *   `ritual`  lo decide la misa que se celebra y no el día: un bautismo, una
 *             confirmación, una primera comunión, una boda, un funeral. El
 *             calendario no lo sabe y la app no se lo inventa: no se esconden
 *             por el día, van juntos y plegados, rotulados por lo que son.
 *
 * Y el domingo va detrás de los demás porque así lo manda su propia rúbrica:
 * «cuando no hay otro Reunidos en comunión propio». La Navidad, la Epifanía,
 * la Pascua, la Ascensión y Pentecostés caen en domingo y traen el suyo; si
 * alguno de ésos entra, el del domingo no.
 */

/** Si el formulario que se está viendo es de un domingo.
 *
 *  La fecha lo dice cuando la hay, y es el camino bueno: se mira a mediodía,
 *  que a medianoche el huso puede correr el día. Cuando no la hay —el
 *  formulario abierto desde el índice, sin fecha— lo dice el propio
 *  formulario: en el Tiempo Ordinario el leccionario le pone al domingo la
 *  etiqueta del ciclo dominical y a las ferias la del año ferial, y en las
 *  temporadas la unidad del Misal acaba en el día de la semana, `/0` el
 *  domingo. */
function esDomingo(f) {
  if (E.isoMisa) return new Date(E.isoMisa + 'T12:00:00').getDay() === 0;
  if (f.s === 'TIEMPO ORDINARIO' && /^Ciclo/.test(f.e || '')) return true;
  return /^(adv|cua|pas)\/\d+\/0$/.test(f.u || '');
}

/** Los propios de una tira que el día pide, y los rituales aparte.
 *
 *  Devuelve `{ dia: [...], ritual: [...] }`: lo primero se enseña, lo segundo
 *  se pliega. Lo que la fase 6 marcó `sigue` no es propio de nada —es el
 *  final de la intercesión de la plegaria IV, que el volcado del PDF arrastró
 *  a esta tira— y va siempre. */
function propiosDelDia(ps, f) {
  const cuales = propiosQueTocan((ps || []).map((q) =>
    ({ c: q.clase, q: q.cual, u: q.u, d: q.d })), f);
  const dia = [];
  const ritual = [];
  for (const q of ps || []) {
    if (q.clase === 'ritual') ritual.push(q);
    else if (q.clase === 'sigue' || cuales.has(q.cual)) dia.push(q);
  }
  // Una tirada que sigue y no reza nada es una indicación de gesto que cierra
  // el propio anterior —la plegaria II acaba sus intercesiones particulares
  // con un «Junta las manos.»—: si hoy no se dice ninguna, tampoco se hace el
  // gesto, y dejarla sola bajo el rótulo de la tira sería un título sin
  // nada debajo. La que sí reza —el final de la intercesión de la plegaria
  // IV— va siempre, que es texto de la plegaria y no propio de nadie.
  const reza = (q) => (q.bs || []).some((b) => !b.r);
  if (!dia.some((q) => q.clase !== 'sigue' || reza(q))) {
    return { dia: dia.filter(reza), ritual: ritual };
  }
  return { dia: dia, ritual: ritual };
}

/** Un propio pintado: su rúbrica y su texto, como vienen del Ordinario. */
function pintaPropio(q) {
  return ordoBloques(q.bs, 'es');
}

function pintaPropias(p, f) {
  if (!conCastellano()) return '';
  const h = [];
  for (const [rot, ps] of Object.entries(p.propias || {})) {
    const { dia, ritual } = propiosDelDia(ps, f);
    const cuerpo = dia.map(pintaPropio).join('');
    if (cuerpo) {
      h.push('<div class="sub"><h3 class="rubrica">'
        + esc(bonitoRotulo(rot)) + '</h3>' + cuerpo + '</div>');
    }
    if (!ritual.length) continue;
    // las rituales, plegadas y nombradas: el día no las puede decidir, pero
    // quien celebra un bautismo o un funeral las busca aquí
    const id = 'r-pleg-ritual';
    const abierta = !!E.pliegues[id];
    h.push('<div class="sub"><div class="plegable"><button type="button" '
      + 'class="pliega menuda" data-pliega="' + id + '" aria-expanded="'
      + abierta + '">' + esc(ritual.map((q) => q.rot).join(' · '))
      + '</button><div class="cuerpo"' + (abierta ? '' : ' hidden') + '>'
      + (abierta ? '<p class="ordo-p ordo-rub"><span class="ln">'
        + esc('Estos propios no los decide el día, sino la misa que se '
          + 'celebra, y eso el calendario no lo sabe.') + '</span></p>'
        + ritual.map(pintaPropio).join('') : '')
      + '</div></div></div>');
  }
  return h.join('');
}

function pintaPlegaria(id, f) {
  const O = E.ordinario;
  const p = O.plegarias[id];
  if (p) {
    const ns = [];
    for (let n = p.desde; n <= p.hasta; n++) ns.push(String(n));
    return ns.map(ordoUna).filter(Boolean).join('') + pintaPropias(p, f);
  }
  const l = O.plegarias_la[id];
  if (!l) return '<p class="omision">No encuentro esa plegaria.</p>';
  return (conLatin() ? '<h3 class="rubrica" lang="la">' + esc(tx(l.t))
    + '</h3>' + (l.rub ? ordoBloques([{ o: 0, r: true, t: l.rub }], 'la') : '')
    + ordoBloques(l.tx, 'la') : '')
    + (conCastellano() ? '<p class="omision">No disponible en castellano: '
      + 'el Ordinario de México sólo trae las cuatro plegarias del Misal; '
      + 'ésta está en latín.</p>' : '');
}

/** «REUNIDOS EN COMUNIÓN PROPIOS» es como lo rotula la fuente. */
function bonitoRotulo(t) {
  const s = String(t).toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/* ------------------------------ la bendición solemne y sobre el pueblo
 * El Ordinario de México no las trae y el misalito sólo imprime la oración
 * sobre el pueblo de la Cuaresma —ésa va en su sitio, como un propio más—.
 * Las veinte bendiciones solemnes y las veintiocho oraciones sobre el pueblo
 * del apéndice del Misal están en latín, y así se ofrecen. */
function bendicionesDe() {
  const L = E.latino;
  const ops = [['', 'La bendición sencilla']];
  for (const p of (L.bendiciones || {}).piezas || []) {
    ops.push(['b' + p.n, 'Solemne ' + p.n + ' · ' + (p.t || '')]);
  }
  for (const p of (L.super_populum || {}).piezas || []) {
    ops.push(['s' + p.n, 'Super populum ' + p.n + ' · '
      + primeras((p.tx || [])[0], 5)]);
  }
  return ops;
}

function pintaBendicion(id) {
  if (!id || !conLatin()) return '';
  const L = E.latino;
  const caja = id[0] === 'b' ? L.bendiciones : L.super_populum;
  const p = (caja.piezas || []).find((x) => String(x.n) === id.slice(1));
  if (!p) return '';
  return '<div class="sub" lang="la">'
    + (p.t ? '<h3 class="rubrica">' + esc(tx(p.t)) + '</h3>' : '')
    + ordoBloques([{ o: 0, r: true, t: caja.rubrica || [] },
      { o: 0, r: false, t: p.tx || [] }], 'la') + '</div>';
}

/* -------------------------------------------------- armar el formulario */

/** Dónde van las rúbricas del Ordo entre las lecturas. */
function ordoDeLectura(l, i) {
  if (i === 0) return ['10'];
  if (l.k === 'salmo') return ['11'];
  if (l.k === 'aleluya') return ['13'];
  if (l.k === 'lectura' && /evangeli/i.test(l.t || '')) return ['14', '15'];
  return ['12'];
}

const ROTULO_SEC = {
  resena: 'Reseña', laslecturas: 'Las lecturas',
  lasoraciones: 'Las oraciones',
  entrada: 'Antífona de entrada',
  inicio: 'Ritos iniciales', penitencial: 'Acto penitencial',
  gloria: 'Gloria', colecta: 'Oración colecta',
  tras_evangelio: 'Después del Evangelio', credo: 'Profesión de fe',
  fieles: 'Oración de los fieles',
  ofertorio: 'Preparación de las ofrendas',
  ofrendas: 'Oración sobre las ofrendas', prefacio: 'Prefacio',
  plegaria: 'Plegaria eucarística', comunion_rito: 'Rito de comunión',
  comunion: 'Antífona de comunión',
  poscomunion: 'Oración después de la comunión',
  pueblo: 'Oración sobre el pueblo', conclusion: 'Rito de conclusión'
};

/* ------------------------------------------------ qué se enseña del misal
 *
 * El formulario entero son veintidós piezas, y tres cuartas partes de lo
 * que ocupan son el Ordinario. Quien se sabe la misa no necesita leerlo: le
 * basta lo que cambia cada día. Así que hay tres modos, y los tres salen de
 * esta misma lista —el entero, que la pasa toda; el breve, que pasa lo que
 * cambia y se dice; y el propio, que pasa lo que se haya marcado en
 * Ajustes— y `armaMisa` sólo decide aquí si una pieza entra, nunca en qué
 * orden: el orden es el del formulario y lo pone el Misal.
 *
 * Las lecturas no son una pieza fija sino las que traiga el día, y por eso
 * se eligen por su clase. El Evangelio se reconoce por el rótulo, igual que
 * en `ordoDeLectura`, porque el leccionario lo marca ahí y no en `k`: para
 * el fichero de lecturas un Evangelio es una lectura más.
 *
 * El tercer campo dice que la pieza es del Ordinario, y la lista de Ajustes
 * lo advierte: son las que no cambian de un día para otro.
 */
const MISA_PIEZAS = [
  ['resena', 'Reseña del día'],
  ['entrada', 'Antífona de entrada'],
  ['inicio', 'Ritos iniciales', 1],
  ['penitencial', 'Acto penitencial', 1],
  ['gloria', 'Gloria'],
  ['colecta', 'Oración colecta'],
  ['lect:lectura', 'Primera lectura, y segunda'],
  ['lect:salmo', 'Salmo responsorial'],
  ['lect:aleluya', 'Aclamación antes del Evangelio'],
  ['lect:evangelio', 'Evangelio'],
  ['tras_evangelio', 'Después del Evangelio', 1],
  ['credo', 'Profesión de fe'],
  ['fieles', 'Oración de los fieles'],
  ['ofertorio', 'Preparación de las ofrendas', 1],
  ['ofrendas', 'Oración sobre las ofrendas'],
  ['prefacio', 'Prefacio'],
  ['plegaria', 'Plegaria eucarística', 1],
  ['comunion_rito', 'Rito de comunión', 1],
  ['comunion', 'Antífona de comunión'],
  ['poscomunion', 'Oración después de la comunión'],
  ['pueblo', 'Oración sobre el pueblo'],
  ['conclusion', 'Rito de conclusión', 1]
];

/* El modo breve. El Gloria está en la lista, pero que salga o no no lo
 * decide esta lista: lo decide el nivel litúrgico del día, con la marca
 * `gl` del formulario y la enmienda de `feriaSinGloriaNiCredo`. Estar aquí
 * sólo quiere decir que el modo breve no lo tapa.
 *
 * La profesión de fe no entra: no se pidió. Y la oración sobre el pueblo
 * tampoco: es una bendición del rito de conclusión, no la oración que
 * cierra el formulario, que es la de después de la comunión. */
const MISA_BREVE = ['entrada', 'gloria', 'colecta', 'lect:lectura',
  'lect:salmo', 'lect:aleluya', 'lect:evangelio', 'fieles', 'ofrendas',
  'comunion', 'poscomunion'];

/* Lo que no se quita nunca, porque no es una pieza de la misa: el selector
 * de cuál de las misas del día se lee, el de dónde son las lecturas de hoy
 * —que en una memoria son las de la feria, y conviene decirlo esté puesto
 * el modo que esté— y el aviso del Viernes Santo de que hoy no hay misa. */
const MISA_SIEMPRE = ['lamisa', 'laslecturas', 'lasoraciones', 'sinmisa'];

/** La clase con la que se elige una lectura. El Evangelio va aparte: es lo
 *  que se busca cuando se busca una sola. */
function claseLectura(l) {
  return 'lect:' + (l.k === 'lectura' && /evangeli/i.test(l.t || '')
    ? 'evangelio' : (l.k || 'lectura'));
}

/** Las piezas que toca enseñar, o `null` en el modo entero, que no mide. */
function piezasPuestas() {
  if (E.cfg.misaVer === 'breve') return MISA_BREVE;
  if (E.cfg.misaVer === 'propio') {
    return Array.isArray(E.cfg.misaSecs) ? E.cfg.misaSecs
      : MISA_PIEZAS.map((x) => x[0]);
  }
  return null;
}

/* El Gloria y la profesión de fe los marca el formulario del Misal —`gl` y
 * `cr`, cosechados del misalito—, pero el formulario no siempre es del día:
 * las ferias del tiempo ordinario toman el del domingo de su semana, y con
 * él se traían su Gloria y su Credo. Una feria no dice ninguno de los dos
 * (IGMR 53 y 68: los domingos fuera de Adviento y Cuaresma, las
 * solemnidades, las fiestas y las celebraciones peculiares más solemnes),
 * así que la feria los quita.
 *
 * Qué es feria no lo cuenta la app: lo trae resuelto el calendario del
 * proyecto —`f` en la celebración— con su rango de la Tabla de los días
 * litúrgicos. Y se mira el rango 13, que son las ferias de Adviento hasta
 * el 16 de diciembre, las de Navidad desde el 2 de enero, las de Pascua y
 * las del tiempo ordinario, ninguna de las cuales los dice. Las del rango 9
 * no se tocan: ahí están los días de la octava de Navidad, que sí los
 * dicen, y ésos el formulario los acierta porque es suyo.
 *
 * Sin día —un formulario abierto desde el índice— no hay rango que mirar, y
 * entonces se enseña como el Misal lo imprime. */
function feriaSinGloriaNiCredo() {
  const m = E.celMisa;
  return !!(m && m.k === 't' && m.f && m.r === 13);
}

/** Si una pieza del formulario entra. */
function quierePieza(id) {
  if (MISA_SIEMPRE.indexOf(id) >= 0) return true;
  const ps = piezasPuestas();
  return !ps || ps.indexOf(id) >= 0;
}

/** El rótulo de una lectura, para el carril. */
function rotuloCorto(l) {
  const t = (l.t || '').replace(/\s+/g, ' ').trim();
  if (!t) return 'Lectura';
  const c = t.charAt(0) + t.slice(1).toLowerCase();
  return c.length > 22 ? c.slice(0, 21) + '…' : c;
}

/* Las otras misas del mismo día. El leccionario numera las que tienen
 * lecturas propias —las tres de Navidad son tres formularios suyos, y salen
 * en la tira de arriba—; las que no numera viven en `otros` colgando de la
 * misma unidad del Misal con un sufijo: la vespertina de la vigilia de san
 * Juan Bautista y de los Apóstoles, y la segunda y la tercera de Difuntos.
 * Cambian los propios y no las lecturas, así que se eligen aquí dentro. */
function otrasMisas(f) {
  const ops = [{ id: '', rot: 'Del día', tit: 'La misa del día' }];
  const pre = f.u + '#';
  for (const [k, v] of Object.entries(E.misa.otros || {})) {
    if (k.indexOf(pre) !== 0) continue;
    const nombre = bonitoRotulo(String(v.cel || k).split('#')[1]
      .replace(/-/g, ' '));
    ops.push({ id: k, rot: bonitoRotulo(nombre.replace(/^Misa /i, '')),
      tit: nombre });
  }
  return ops.length > 1 ? ops : null;
}

/* El Viernes Santo no se celebra la misa, y el Ordinario no pinta nada ahí:
 * poner detrás de sus lecturas el acto penitencial y la plegaria eucarística
 * sería decir que se reza lo que la Iglesia hoy no reza. Va por la unidad del
 * Misal, que es el nombre estable que le dio la fase 5, y nombrado: lo demás
 * del día —la poscomunión, la oración sobre el pueblo— es suyo y se queda.
 * La razón la da el propio misalito en la reseña de ese día. */
const SIN_MISA = {
  'tri/pasion': 'Hoy no se celebra la misa: la Iglesia omite por completo '
    + 'el sacrificio eucarístico, y el Ordinario no entra aquí. Lo que se '
    + 'hace es la celebración de la Pasión del Señor.'
};

/** El formulario entero, sección por sección. */
function armaMisa(clave, lects) {
  let f = E.misa.formularios[clave] || (E.misa.otros || {})[clave];
  if (!f) return null;
  const lat = f.la ? (E.latino.formularios[f.la] || null) : null;
  const otras = f.u ? otrasMisas(f) : null;
  let iMisa = 0;
  if (otras) {
    const quiere = (E.misaOps[clave] || {}).misa;
    iMisa = Math.max(0, otras.findIndex((o) => o.id === quiere));
    if (iMisa > 0) {
      // la otra misa cambia los propios; el latín, las lecturas y lo que el
      // día manda siguen siendo los del formulario
      f = Object.assign({}, f, { p: E.misa.otros[otras[iMisa].id].p || {} });
    }
  }
  const sinMisa = SIN_MISA[f.u];
  _sinOrdo = !!sinMisa;
  _fMisa = f;
  // qué oraciones se pueden tomar de otro sitio. Se calcula aquí y no al
  // pintar el formulario porque necesita `misa.json`, que llega aparte.
  E.oraciones = (E.slugMisa && !iMisa)
    ? composicionOraciones(E.slugMisa, E.celsMisa || [], clave)
    : { ops: null, nota: '', claveOtra: null };
  const ORA = E.oraciones;
  /** Una pieza propia, con la opción elegida y su selector. */
  /* Una pieza propia, con la opción elegida.
   *
   * Cuando no está en ninguna de las dos lenguas, `pintaPieza` devuelve
   * vacío y la sección salía con su rótulo y la rúbrica del Ordo debajo,
   * sin una palabra: parecía rota. Se dice lo que pasa, que es lo que se
   * hace en todo lo demás. Son 74 ranuras de formularios que el calendario
   * alcanza —las ferias del 2 al 7 de enero, sobre todo, que la fase 1 dejó
   * sin latín—, y la oración sobre el pueblo, que no entra aquí porque sólo
   * la tiene la Cuaresma y su sección no se pinta si no hay nada. */
  const pieza = (ran) => {
    const o = formularioDe(ran, f, lat, clave);
    const h = pintaPieza(o.f, o.lat, ran);
    if (h || ran === 'pueblo') return h;
    return '<p class="omision">El Misal no trae esta oración en este '
      + 'formulario, ni en castellano ni en latín.</p>';
  };
  const eligeOra = (ran) => {
    if (!ORA.ops || !ORA.ops[ran]) return {};
    const alts = ORA.ops[ran];
    const q = (E.misaOps[clave] || {})['or_' + ran]
      || (ORA.porOmision || {})[ran] || 'dia';
    return { elige: 'or_' + ran, alts: alts,
      i: Math.max(0, alts.findIndex((x) => x.id === q)) };
  };
  const hayOrdo = hayOrdinario();
  const S = [];
  // la pieza que el modo no quiere no se arma: aquí se decide si entra, y
  // el orden sigue siendo el del formulario
  const sec = (cl, cuerpo, extra) => {
    if (!cuerpo || !quierePieza(cl)) return;
    S.push(Object.assign({ cl: cl, rot: ROTULO_SEC[cl] || cl,
      cuerpo: cuerpo }, extra || {}));
  };
  const ordoSec = (cl, cuerpo, extra) => {
    if (hayOrdo) sec(cl, cuerpo, Object.assign({ ordo: true }, extra || {}));
  };
  const alterna = (id, n) => {
    const e = ELIGE[id];
    const i = elegido(id, e.ops.length);
    return { elige: id, i: i, alts: e.ops.map((o, j) =>
      ({ id: String(j), rot: o[0], tit: incipitOpcion(n, id, j) })) };
  };

  if (otras) {
    sec('lamisa', '<p class="ordo-p ordo-rub"><span class="ln">'
      + esc('Este día tiene más de una misa, y el Misal les da propios '
        + 'distintos. Las lecturas son las mismas.') + '</span></p>',
    { elige: 'misa_variante', i: iMisa, alts: otras, rot: 'La misa' });
  }
  if (sinMisa) {
    sec('sinmisa', '<p class="ordo-p ordo-rub"><span class="ln">'
      + esc(sinMisa) + '</span></p>', { rot: 'La celebración de hoy' });
  }
  // de dónde son las lecturas de hoy, y lo que se puede elegir. Sale sólo
  // cuando hay algo que decir: en un domingo o una fiesta las lecturas son
  // las del formulario y no hay nada que advertir.
  const L = E.lects || {};
  if (L.nota && (lects || []).length) {
    sec('laslecturas', '<p class="ordo-p ordo-rub"><span class="ln">'
      + esc(L.nota) + '</span></p>',
    Object.assign({ rot: 'Las lecturas' },
      L.ops ? { elige: 'lecturas', i: L.i, alts: L.ops } : {}));
  }
  if (f.r) sec('resena', '<p class="texto">' + esc(f.r) + '</p>');
  // lo que las rúbricas dejan tomar de otro formulario: la colecta del
  // santo en una feria privilegiada, y en una memoria lo que no es propio
  if (ORA.nota) {
    sec('lasoraciones', '<p class="ordo-p ordo-rub"><span class="ln">'
      + esc(ORA.nota) + '</span></p>', { rot: 'Las oraciones' });
  }
  sec('entrada', pieza('entrada'));
  ordoSec('inicio', ordo(['1', '2', '3']), alterna('saludo', '2'));
  if (hayOrdo) {
    const iF = elegido('penit_form', PENITENCIAL.length);
    const F = PENITENCIAL[iF];
    sec('penitencial', ordoUna('4')
      + subCab('penit_form', 'Fórmula', PENITENCIAL.map((x, j) =>
        ({ id: String(j), rot: x[0], tit: '' })), iF)
      + ordoDesde(F[1], F[2], F[3]) + ordo(['7']),
    Object.assign({ ordo: true }, alterna('penit_inv', '4')));
  }
  if (f.gl && !feriaSinGloriaNiCredo()) ordoSec('gloria', ordo(['8']));
  sec('colecta', ordoPlegado(['9'], 'r-colecta') + pieza('colecta'),
    eligeOra('colecta'));

  (lects || []).forEach((l, i) => {
    if (!quierePieza(claseLectura(l))) return;
    const l2 = parejaEs(clave, i);
    S.push({ cl: 'lect' + i, rot: null, lectura: true, nombre: rotuloCorto(l),
      k: claseLectura(l),
      cuerpo: ordoPlegado(ordoDeLectura(l, i), 'r-lect' + i)
        + pintaLectura(l, l2) });
  });
  if ((lects || []).length) ordoSec('tras_evangelio', ordo(['16', '17']));
  if (f.cr && !feriaSinGloriaNiCredo()) {
    const i = elegido('simbolo', SIMBOLO.length);
    ordoSec('credo', ordoUna(SIMBOLO[i][1]), { elige: 'simbolo', i: i,
      alts: SIMBOLO.map((x, j) =>
        ({ id: String(j), rot: x[0], tit: x[2] })) });
  }
  ordoSec('fieles', ordo(['20']));
  ordoSec('ofertorio', ordo(['21', '22', '23', '24', '25', '26', '27', '28',
    '29']), alterna('oren', '29'));
  sec('ofrendas', pieza('ofrendas')
    + ordoPlegado(['30'], 'r-ofrendas'), eligeOra('ofrendas'));

  // el prefacio es del día, así que se da aunque el Ordinario esté apagado;
  // el día que no hay misa no tiene prefacio ni plegaria
  if (!sinMisa) {
    const marcados = prefaciosDe(clave, f);
    const prefs = marcados.length ? marcados : prefaciosDelTiempo(f);
    const guardado = (E.misaOps[clave] || {}).prefacio;
    const idPref = guardado || (prefs[0] ? prefs[0].id : 'prefacio-comun-i');
    sec('prefacio', ordoPlegado(['31'], 'r-prefacio')
      + (marcados.length ? '' : '<p class="ordo-p ordo-rub"><span class="ln">'
        + esc('El Misal no marca prefacio para esta misa: se toma uno de los '
          + (grupoDelTiempo(f) === 'comun' ? 'comunes'
            : 'de ' + GRUPO_PREF_ROT[grupoDelTiempo(f)]) + ', a elección.')
        + '</span></p>')
      + pintaPrefacio(idPref)
      + (f.pp && !f.ppd ? '<p class="testigo" title="El misalito dice que '
        + 'esta misa tiene prefacio propio, pero no llegó a imprimirlo en '
        + 'los cien números">tiene prefacio propio, y no está</p>' : ''),
    // los del tiempo no se repiten arriba: ya están en su grupo, y una
    // opción repetida en un <select> deja el marcado en la última
    { selPref: selectorPrefacio(idPref, marcados, 'El que marca el día') });
  }

  const plegs = plegariasDe();
  const quiere = (E.cfg.ordoOps || {}).plegaria;
  const idPleg = plegs.some((x) => x.id === quiere) ? quiere
    : 'plegaria-eucaristica-ii';
  ordoSec('plegaria', pintaPlegaria(idPleg, f),
    { selPleg: plegs, idPleg: idPleg,
      rot: (plegs.find((x) => x.id === idPleg) || {}).t
        || ROTULO_SEC.plegaria });

  ordoSec('comunion_rito', ordo(['124', '125', '126', '127', '128', '129',
    '130', '131', '132', '133', '134', '135', '136']),
  alterna('padrenuestro', '124'));
  sec('comunion', pieza('comunion'));
  sec('poscomunion', ordoPlegado(['137', '138', '139'], 'r-poscomunion')
    + pieza('poscomunion')
    + ordoPlegado(['139b'], 'r-poscomunion2'), eligeOra('poscomunion'));
  sec('pueblo', pieza('pueblo'));
  const idBen = (E.cfg.ordoOps || {}).bendicion || '';
  ordoSec('conclusion', ordo(['140', '141', '142', '143'])
    + pintaBendicion(idBen) + ordoUna('144') + ordo(['145', '146']),
  Object.assign({ selBen: bendicionesDe(), idBen: idBen },
    alterna('despedida', '144')));
  return { clave: clave, f: f, lat: lat, secciones: S };
}

/** La lectura castellana que hace pareja con la latina, en el bilingüe.
 *
 *  Los dos leccionarios dan los mismos bloques en el mismo orden, así que
 *  la pareja es la que ocupa su mismo sitio. Lo que ya no vale es contar
 *  desde el principio del formulario: en una memoria las lecturas vienen de
 *  dos bloques distintos —el de la feria y el del santo—, y la pareja hay
 *  que buscarla en el bloque de donde salió cada una. Eso es `E.lects.pares`. */
function parejaEs(clave, i) {
  if (E.cfg.fuente !== 'bi' || !E.lecturasEs) return null;
  const p = (E.lects && E.lects.pares) ? E.lects.pares[i] : null;
  const k = p ? p[0] : clave;
  const j = p ? p[1] : i;
  return (E.lecturasEs.bloques[k] || [])[j] || null;
}

/** Un selector de los pequeños, dentro del cuerpo de una sección. */
function subCab(id, rot, alts, i) {
  return '<div class="sub-cab"><span class="sub-rot">' + esc(rot) + '</span>'
    + '<div class="alterna" data-elige="' + esc(id) + '" role="group" '
    + 'aria-label="' + esc(rot) + '">'
    + alts.map((a, j) => '<button type="button" aria-pressed="' + (j === i)
      + '" data-op="' + esc(a.id) + '"'
      + (a.tit ? ' title="' + esc(a.tit) + '"' : '') + '>' + esc(a.rot)
      + '</button>').join('') + '</div></div>';
}

function selectorLargo(id, rot, ops, cual) {
  return '<div class="sub-cab"><span class="sub-rot">' + esc(rot) + '</span>'
    + '<select class="elige" data-elige="' + esc(id) + '" aria-label="'
    + esc(rot) + '">' + ops.map(([v, t]) => '<option value="' + esc(v) + '"'
      + (v === cual ? ' selected' : '') + '>' + esc(t) + '</option>').join('')
    + '</select></div>';
}

function pintaMisaSec(s) {
  const h = [];
  const sel = s.elige
    ? '<div class="alterna" data-elige="' + esc(s.elige) + '" role="group" '
      + 'aria-label="' + esc((ELIGE[s.elige] || {}).rot || s.rot || 'Elegir')
      + '">'
      + s.alts.map((a, j) => '<button type="button" aria-pressed="'
        + (j === s.i) + '" data-op="' + esc(a.id) + '"'
        + (a.tit ? ' title="' + esc(a.tit) + '" aria-label="'
          + esc(a.rot + ': ' + a.tit) + '"' : '') + '>' + esc(a.rot)
        + '</button>').join('') + '</div>'
    : '';
  // plegado sólo en el modo entero: el Ordinario entra ahí se pida o no, y
  // si no se plegara taparía los propios. En los otros dos modos la pieza
  // se pidió por su nombre, y una pieza plegada es sólo un rótulo
  const plegable = !!s.ordo && E.cfg.misaVer === 'todo'
    && E.cfg.ordinario !== 'abierto';
  const abierta = !plegable || !!E.pliegues[s.cl];
  if (s.rot) {
    h.push('<div class="sec-cab"><h2 class="rotulo">'
      + (plegable ? '<button type="button" class="pliega" data-pliega="'
        + esc(s.cl) + '" aria-expanded="' + abierta + '">' : '')
      + '<span class="vs">' + esc(s.rot) + '</span>'
      + (plegable ? '</button>' : '') + '</h2>' + sel + '</div>');
  } else if (sel) {
    h.push('<div class="sec-cab"><h2 class="rotulo"></h2>' + sel + '</div>');
  }
  const cuerpo = [];
  if (s.selPref) {
    cuerpo.push('<div class="sub-cab"><span class="sub-rot">El prefacio'
      + '</span>' + s.selPref + '</div>');
  }
  if (s.selPleg) {
    cuerpo.push(selectorLargo('plegaria', 'La plegaria',
      s.selPleg.map((p) => [p.id, p.t + (p.soloLa ? ' · sólo en latín' : '')]),
      s.idPleg));
  }
  cuerpo.push(s.cuerpo);
  if (s.selBen) {
    cuerpo.push(selectorLargo('bendicion', 'Bendición final', s.selBen,
      s.idBen));
  }
  // lo que está plegado no se mete en la página: el Ordinario entero son
  // tres cuartas partes del formulario, y pasar de día pintándolo para
  // tenerlo escondido cuesta más que pintarlo cuando se abra
  h.push('<div class="cuerpo"' + (abierta ? '' : ' hidden') + '>'
    + (abierta ? cuerpo.join('') : '') + '</div>');
  return '<section class="hora-sec misa-sec' + (s.ordo ? ' es-ordo' : '')
    + claseFmt(grupoFmt(s))
    + '" data-cl="' + esc(s.cl) + '">' + h.join('') + '</section>';
}

/** El formulario entero, pintado. Devuelve null si esa clave no está en
 *  `misa.json`, y entonces se enseñan las lecturas solas. */
function pintaMisaEntera(clave, lects) {
  const o = armaMisa(clave, lects);
  E.misaVista = o;
  if (!o) return null;
  return o.secciones.map(pintaMisaSec).join('');
}

/** Las lecturas que hoy se leen de una clave, ya compuestas: en una memoria
 *  no son las del bloque del santo sino las de la feria. */
function lecturasPuestas(clave) {
  if (E.lects && E.lects.pares) {
    return E.lects.pares.map(lecturaDePar).filter(Boolean);
  }
  return (E.lecturas.bloques || {})[clave] || [];
}

/** Repintar una sección sola: cambiar el saludo no ha de mover el resto. */
function repintaMisaSec(cl) {
  const v = E.misaVista;
  if (!v) return;
  const nuevo = armaMisa(v.clave, lecturasPuestas(v.clave));
  if (!nuevo) return;
  E.misaVista = nuevo;
  const s = nuevo.secciones.find((x) => x.cl === cl);
  const caja = document.querySelector('#vista .misa-sec[data-cl="' + cl
    + '"]');
  if (!s || !caja) return;
  const t = document.createElement('template');
  t.innerHTML = pintaMisaSec(s);
  const nueva = t.content.firstElementChild;
  nueva.classList.add('cambia');
  caja.replaceWith(nueva);
  const cab = nueva.querySelector('.sec-cab');
  if (cab) aprietaCabecera(cab);
}

/** Tocar en la misa: plegar una sección del Ordinario, o elegir. */
function alTocarMisa(ev) {
  if (E.vista !== 'hoy' || !E.misaVista) return;
  const pl = ev.target.closest('.pliega');
  if (pl) {
    const cl = pl.dataset.pliega;
    E.pliegues[cl] = !E.pliegues[cl];
    guardaPliegues();
    const sec = pl.closest('.misa-sec');
    const arriba = sec.getBoundingClientRect().top;
    repintaMisaSec(sec.dataset.cl);
    // la sección crece hacia abajo: el renglón donde está el dedo se queda
    // donde estaba, que si no el texto da un salto al abrirse
    const nueva = document.querySelector('#vista .misa-sec[data-cl="'
      + sec.dataset.cl + '"]');
    if (nueva) {
      window.scrollBy(0, nueva.getBoundingClientRect().top - arriba);
      const b2 = nueva.querySelector('[data-pliega="' + cl + '"]');
      if (b2) b2.focus({ preventScroll: true });
    }
    return;
  }
  const b = ev.target.closest('.alterna button');
  if (!b) return;
  const grupo = b.closest('.alterna');
  const id = grupo.dataset.elige;
  const sec = b.closest('.misa-sec');
  if (!id || !sec) return;
  // la otra misa del día cambia todos los propios, no una sección: se
  // repinta el formulario entero y se vuelve donde se estaba
  if (id === 'misa_variante' || id === 'lecturas') {
    const c = E.misaVista.clave;
    E.misaOps[c] = Object.assign({}, E.misaOps[c],
      id === 'lecturas' ? { lecturas: b.dataset.op }
        : { misa: b.dataset.op });
    guardaMisaOps();
    const y = window.scrollY;
    // de dónde son las lecturas cambia las lecturas y nada más, pero son
    // varias secciones: se repinta el formulario entero
    if (id === 'lecturas' && E.celsMisa) {
      E.lects = composicionLecturas(E.slugMisa, E.celsMisa, c);
    }
    pintaCuerpoMisa(c, lecturasPuestas(c));
    window.scrollTo(0, y);
    return;
  }
  // de dónde sale una oración es del día, no de quien celebra: va con la
  // sesión, como el prefacio, y no con los ajustes
  if (id.indexOf('or_') === 0) {
    const c = E.misaVista.clave;
    const x = {}; x[id] = b.dataset.op;
    E.misaOps[c] = Object.assign({}, E.misaOps[c], x);
    guardaMisaOps();
    repintaMisaSec(sec.dataset.cl);
    return;
  }
  guardaElegido(id, +b.dataset.op);
  repintaMisaSec(sec.dataset.cl);
}

/** Los selectores largos: el prefacio, la plegaria, la bendición. */
function alElegirEnMisa(ev) {
  const s = ev.target.closest('select.elige');
  if (!s || E.vista !== 'hoy' || !E.misaVista) return;
  const id = s.dataset.elige;
  if (id === 'prefacio') {
    const c = E.misaVista.clave;
    E.misaOps[c] = Object.assign({}, E.misaOps[c], { prefacio: s.value });
    guardaMisaOps();
  } else {
    guardaElegido(id, s.value);
  }
  const sec = s.closest('.misa-sec');
  if (sec) repintaMisaSec(sec.dataset.cl);
}

function cargaMisaOps() {
  try {
    E.misaOps = JSON.parse(sessionStorage.getItem('misaOps') || '{}');
  } catch (_) { E.misaOps = {}; }
  // y qué partes del Ordinario se dejaron abiertas: quien sigue la misa las
  // abre una vez, no una por día
  try {
    E.pliegues = JSON.parse(sessionStorage.getItem('pliegues') || '{}');
  } catch (_) { E.pliegues = {}; }
}

function guardaPliegues() {
  try {
    sessionStorage.setItem('pliegues', JSON.stringify(E.pliegues));
  } catch (_) { /* sin almacenamiento: vale para esta vista */ }
}

function guardaMisaOps() {
  try {
    sessionStorage.setItem('misaOps', JSON.stringify(E.misaOps));
  } catch (_) { /* sin almacenamiento: vale para esta vista */ }
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
    ponColor('neutro');
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
  $('#cab-zoom').innerHTML = '';
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
  // El alto propio de cada tira. `scrollHeight` lo da aunque el alto
  // impuesto la recorte, que es justamente lo que hay que medir: con tres
  // celebraciones posibles la tira lleva dos renglones y antes se cortaba.
  for (const [id, v] of [['celebraciones', '--alto-celebraciones'],
    ['formularios', '--alto-formularios'], ['nota-dia', '--alto-nota']]) {
    const el = document.getElementById(id);
    est.setProperty(v, (el ? el.scrollHeight : 0) + 'px');
  }
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
  // Y de paso, los marcos escondidos: si ya no cabe esconderlos —se ha
  // puesto de pie, o se ha salido a una vista que no se lee— vuelven. El
  // giro avisa por su cuenta, pero no todos los teléfonos lo cuentan igual,
  // y esto cuesta una comparación por desplazamiento.
  if (document.body.classList.contains('pantalla-limpia')
      && !cabeSinMarcos()) {
    document.body.classList.remove('pantalla-limpia');
  }
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

/* ---------------------------------------------- la pantalla, sin marcos
 * Con el teléfono de lado caben diez renglones, y de ellos la cabecera y la
 * barra se llevan tres. Un toque en el texto las esconde del todo —fuera de
 * la pantalla, no atenuadas— y otro las devuelve: mientras se lee no se
 * necesita ninguna de las dos, y el alto que sobra es justo el que falta.
 *
 * Sólo tumbado, que es donde el alto falta —de pie la cabecera ya se pliega
 * al bajar—, y sólo en las vistas que se leen, que son las que la pliegan:
 * en el calendario y en los paneles la barra es la única manera de salir, y
 * esconderla sería dejar a quien toca sin puerta.
 *
 * El relleno del <body> que guardaba el sitio de la cabecera se va con ella,
 * de modo que el texto subiría de golpe. No sube: se repone el renglón que
 * se estaba leyendo, igual que al cambiar el cuerpo de la letra, y lo que se
 * gana sale por arriba —los renglones que la cabecera tapaba— sin que nada
 * se mueva debajo del ojo.
 */
const ACOSTADO = window.matchMedia
  ? window.matchMedia('(orientation: landscape)') : null;

/** Si esconderlas tiene sentido aquí y ahora. */
function cabeSinMarcos() {
  return !!(ACOSTADO && ACOSTADO.matches)
    && document.body.classList.contains('cab-fija');
}

function ponPantallaLimpia(si) {
  const b = document.body;
  if (si && !cabeSinMarcos()) return;
  if (si === b.classList.contains('pantalla-limpia')) return;
  const ancla = anclaDeLectura();
  b.classList.toggle('pantalla-limpia', si);
  if (ancla) reponeAncla(ancla);
  else if (_altoCab) {
    // sin un bloque de texto donde anclarse, el relleno a mano
    window.scrollTo(0, Math.max(0,
      window.scrollY + (si ? -_altoCab : _altoCab)));
  }
  _ultimoY = Math.max(0, window.scrollY);
  _saltoHasta = Date.now() + 400;
}

function alternaPantallaLimpia() {
  if (!cabeSinMarcos()) return;
  ponPantallaLimpia(!document.body.classList.contains('pantalla-limpia'));
}

/* Al ponerse de pie los marcos vuelven, y vuelven de verdad: no basta con
 * que la hoja de estilo deje de aplicarlos: la clase se quita, que si no al
 * acostarse otra vez la cabecera se iría sin que nadie la hubiera tocado.
 * El aviso lo da la consulta misma, que es quien sabe cuándo deja de valer;
 * el `resize` no siempre llega al girar. */
if (ACOSTADO && ACOSTADO.addEventListener) {
  ACOSTADO.addEventListener('change', () => {
    if (!ACOSTADO.matches) {
      document.body.classList.remove('pantalla-limpia');
    }
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
  ponColor('neutro');
}

function verIndice() {
  E.vista = 'indice';
  // el índice se abre desde el calendario, y es allí donde se vuelve
  marcaBarra('calendario');
  modoPanel('Índice del leccionario');
  // el buscador salió de la barra de abajo: es cosa del leccionario, y
  // aquí está a mano de quien lo hojea. Busca en la lengua que se esté
  // leyendo, que es la que el lector tiene en la cabeza
  const h = ['<a class="enlace-buscar" href="#/buscar">' + ICONO.buscar
    + 'Buscar en ' + lengua() + ' del leccionario</a>'];
  // todas las secciones plegadas: así lo primero que se ve es el índice de
  // los índices —los ocho leccionarios y los apéndices—, y no la lista
  // entera del primero
  E.indice.secciones.forEach((sec) => {
    h.push('<details class="sec"><summary>' + esc(sec.t) + '</summary>');
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
  // el azul de la Virgen, como al abrir el día: el libro dice blanco, pero
  // la costumbre —y en México la de Guadalupe sobre todas— lo quiere azul
  const color = (p.m.smv || esDeLaVirgen(p.t)) ? 'azul'
    : E.colorDe.get(p.slug) || 'neutro';
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
      // en castellano hay lecturas sin texto —las que el misalito no imprimió
      // en nueve años—, y van sin tramos: no se indexan, pero su cita sí
      const t = (l.g || []).map((tr) => tr.map((v) => v[1]).join(' '))
        .join(' ');
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
  modoPanel('Buscar en ' + lengua());
  vista.innerHTML = '<input class="campo" id="q" type="search" '
    + 'placeholder="' + (E.cfg.fuente === 'es' ? 'Palabra o cita (Is 2,1)'
      : 'Palabra latina o cita (Is 2,1)') + '" value="' + esc(q || '')
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
 * tenga renglones de sobra donde lucirse.
 *
 * Y como el formato se puede decir sección por sección, cada trozo lleva
 * además la clase de su grupo: el salmo, la del salmo; la lectura, la de la
 * lectura. Así la muestra de cada pestaña enseña su propio formato. */
const LN_M = (t, cl) => '<span class="ln' + (cl ? ' ' + cl : '') + '">'
  + t + '</span>';
const RUB_M = (t) => '<b class="rub">' + esc(t) + '</b>';

const PROSA_M = 'Hermanos: Estad siempre alegres en el Señor; os lo repito, '
  + 'estad alegres. Que vuestra mesura la conozcan todos los hombres. El '
  + 'Señor está cerca. Nada os preocupe; sino que, en toda ocasión, en la '
  + 'oración y en la súplica, con acción de gracias, vuestras peticiones '
  + 'sean presentadas a Dios.';

function muestraVerso(cl) {
  return '<section class="hora-sec en-verso' + cl + '">'
    + '<p class="estrofa-h">'
    + LN_M(RUB_M('Ant.') + ' ' + esc('El Señor es mi pastor') + ' ' + CRUZ,
      'sigla')
    + '</p><p class="estrofa-h">'
    + LN_M(RUB_M('SALMO 22') + esc('   El buen pastor'), 'tit')
    + LN_M(esc('El Señor es mi pastor, nada me falta:'))
    + LN_M(CRUZ + ' ' + esc('en verdes praderas me hace recostar;'))
    + LN_M(esc('me conduce hacia fuentes tranquilas'))
    + LN_M(esc('y repara mis fuerzas.'))
    + '</p></section>';
}

function muestraProsa(cl, rot) {
  return '<section class="hora-sec prosa' + cl + '">'
    + (rot ? '<div class="sec-cab"><h2 class="rotulo">' + esc(rot)
      + '</h2></div>' : '')
    + '<p class="estrofa-h">' + LN_M(esc(PROSA_M)) + '</p></section>';
}

function muestraFormato() {
  return '<div class="muestra" aria-hidden="true">'
    + muestraVerso(claseFmt('salmos'))
    + muestraProsa(claseFmt('lecturas'), 'Lectura breve')
    + '</div>';
}

/** La muestra de un grupo, con su clase puesta: cada pestaña enseña su
 *  propio formato y no una imitación del general. */
function muestraGrupo(g, forma) {
  const cl = claseFmt(g);
  const caja = (h) => '<div class="muestra chica" aria-hidden="true">' + h
    + '</div>';
  if (forma === 'verso') return caja(muestraVerso(cl));
  if (forma === 'prosa') return caja(muestraProsa(cl, ''));
  if (forma === 'ant') {
    return caja('<section class="lect' + cl + '">'
      + '<p class="antifona">℟. '
      + esc('El Señor es mi pastor, nada me falta.') + '</p>'
      + '<p class="texto">' + esc('Cantad al Señor un cántico nuevo, '
        + 'porque ha hecho maravillas.') + '</p></section>');
  }
  if (forma === 'preces') {
    return caja('<section class="hora-sec prosa' + cl + '">'
      + '<p class="estrofa-h">'
      + LN_M(RUB_M('—') + ' ' + esc('Para que tu Iglesia dé testimonio de '
        + 'tu amor delante de todos los hombres, te rogamos, Señor.'))
      + LN_M(RUB_M('R.') + ' ' + esc('Escúchanos, Señor.'), 'prez-r')
      + '</p></section>');
  }
  // el Ordinario: su rúbrica y lo que se reza, con la sangría del Misal
  return caja('<section class="hora-sec misa-sec' + cl + '">'
    + '<p class="ordo-p ordo-rub">'
    + LN_M(esc('El sacerdote, con las manos juntas, prosigue:')) + '</p>'
    + '<p class="ordo-p">'
    + LN_M(esc('Santo, Santo, Santo es el Señor, Dios del universo.'))
    + LN_M(esc('Llenos están el cielo y la tierra de tu gloria.'))
    + '</p></section>');
}

/* ------------------------------------------- el interlineado, al paso
 * El renglón no tiene cuatro medidas: tiene todas las de en medio, y la que
 * se busca no se sabe de antemano —depende del cuerpo de la letra, de la
 * fuente que el teléfono sirva y de la vista de quien lee—. Así que no es
 * una lista de nombres sino un número: menos, la cifra y más, y la muestra
 * justo encima para ver el renglón mientras se aprieta.
 *
 * `grupo` es la sección cuando el mando es de una sección, y entonces el
 * número puede estar sin decir: se enseña el del general entre paréntesis y
 * en gris —es prestado— y el primer toque parte de ahí.
 */
function pasoInterlinea(grupo) {
  const propio = grupo
    ? (((E.cfg.fmt || {})[grupo] || {}).interlinea || 0) : 0;
  const v = propio || E.cfg.interlinea;
  const boton = (d, rot) => '<button type="button" data-paso="' + d + '"'
    + (grupo ? ' data-grupo="' + grupo + '"' : '')
    + ' aria-label="' + rot + ' interlineado"'
    + ((d < 0 ? v <= RENGLON_MIN : v >= RENGLON_MAX) ? ' disabled' : '')
    + '>' + (d < 0 ? '−' : '+') + '</button>';
  return '<div class="paso" role="group" aria-label="Interlineado"'
    + (grupo ? ' data-grupo="' + grupo + '"' : '') + '>'
    + boton(-RENGLON_PASO, 'Menos')
    + '<span class="cifra' + (grupo && !propio ? ' heredada' : '')
    + '" aria-live="polite">' + cifraRenglon(v, !!grupo && !propio)
    + '</span>'
    + boton(RENGLON_PASO, 'Más') + '</div>';
}

/** El mando, al día: la cifra, los dos topes y el botón que devuelve la
 *  sección al general. Se toca lo que cambia y no se repinta Ajustes, que
 *  cerraría la pestaña y dejaría al dedo buscando el botón. */
function refrescaPaso(grupo) {
  const caja = document.querySelector(grupo
    ? '.paso[data-grupo="' + grupo + '"]' : '.paso:not([data-grupo])');
  if (!caja) return;
  const propio = grupo
    ? (((E.cfg.fmt || {})[grupo] || {}).interlinea || 0) : 0;
  const v = propio || E.cfg.interlinea;
  const prestado = !!grupo && !propio;
  const c = caja.querySelector('.cifra');
  c.textContent = cifraRenglon(v, prestado);
  c.classList.toggle('heredada', prestado);
  caja.querySelectorAll('[data-paso]').forEach((b) => {
    b.disabled = Number(b.dataset.paso) < 0 ? v <= RENGLON_MIN
      : v >= RENGLON_MAX;
  });
  const vg = document.querySelector('.vuelve-general[data-grupo="'
    + grupo + '"]');
  if (vg) vg.disabled = !propio;
}

/** Todos los mandos a la vez: al mover el general se mueve también la cifra
 *  prestada de las secciones que no dicen nada. */
function refrescaPasos() {
  refrescaPaso('');
  for (const g of GRUPO_FMT) refrescaPaso(g[0]);
}

/* Un toque en «menos» o en «más» mueve el número cinco centésimas; «Igual
 * que todas» borra lo que la sección decía, y entonces vuelve a seguir al
 * general. Lo que se ve cambia en el sitio —la muestra está encima— y
 * Ajustes no se repinta. */
function alTocarPaso(ev) {
  const b = ev.target.closest('[data-paso], .vuelve-general');
  if (!b || E.vista !== 'ajustes') return;
  const grupo = b.dataset.grupo || '';
  const propio = grupo
    ? (((E.cfg.fmt || {})[grupo] || {}).interlinea || 0) : 0;
  const base = propio || E.cfg.interlinea;
  let v = 0;
  if (b.dataset.paso) {
    v = Math.max(RENGLON_MIN,
      Math.min(RENGLON_MAX, base + Number(b.dataset.paso)));
    if (v === base && (propio || !grupo)) return;   // ya estaba en el tope
  } else if (!propio) {
    return;                            // no decía nada: nada que deshacer
  }
  if (grupo) {
    const f = Object.assign({}, (E.cfg.fmt || {})[grupo]);
    if (v) f.interlinea = v; else delete f.interlinea;
    const fmt = Object.assign({}, E.cfg.fmt);
    fmt[grupo] = f;
    E.cfg.fmt = fmt;
    guardaCfg();
    aplicaFormatoSecs();
  } else {
    E.cfg.interlinea = v;
    guardaCfg();
    aplicaCfg();
  }
  refrescaPasos();
}

/* Una pestaña por sección, con su muestra y sus tres mandos. «Igual que
 * todas» no guarda nada: es la ausencia de valor, y entonces manda el
 * formato general. */
function bloqueFmt(g) {
  const selFmt = (campo, etiqueta, ops) => {
    const v = (((E.cfg.fmt || {})[g[0]] || {})[campo]) || '';
    return '<div class="ajuste"><label for="aj-f-' + g[0] + '-' + campo
      + '">' + etiqueta + '</label><select id="aj-f-' + g[0] + '-' + campo
      + '" data-fmt="' + g[0] + '" data-campo="' + campo + '">'
      + ops.map(([x, t]) => '<option value="' + x + '"'
        + (v === x ? ' selected' : '') + '>' + t + '</option>').join('')
      + '</select></div>';
  };
  return '<details class="fmt-grupo"><summary>' + esc(g[1]) + '</summary>'
    + '<div class="fmt-cuerpo"><p class="pista-g">' + esc(g[2]) + '</p>'
    + muestraGrupo(g[0], g[3])
    + selFmt('justifica', 'Alineación', [['', 'Igual que todas'],
      ['si', 'Justificado'], ['no', 'A la izquierda']])
    + '<div class="ajuste ancho"><span class="eti">Interlineado</span>'
    + '<div class="mandos-paso">' + pasoInterlinea(g[0])
    + '<button type="button" class="vuelve-general" data-grupo="' + g[0]
    + '"' + ((((E.cfg.fmt || {})[g[0]] || {}).interlinea) ? '' : ' disabled')
    + '>Igual que todas</button></div></div>'
    + selFmt('particion', 'Partir las palabras', [['', 'Igual que todas'],
      ['si', 'Sí'], ['no', 'No']])
    + '</div></details>';
}

/* La lista de piezas del modo propio: casillas en el orden del formulario,
 * las del Ordinario dichas, que son las que no cambian de un día para otro
 * y casi todo el bulto. El rótulo es el mismo que llevará la sección al
 * pintarse, para que se reconozca lo que se marca. */
function piezasDeLaMisa() {
  const puestas = piezasPuestas() || [];
  return '<div class="ajuste ancho piezas"><label>Las piezas'
    + '<span class="pista">En el orden de la misa. El Gloria y la profesión '
    + 'de fe salen sólo los días que el Misal los manda, aunque aquí estén '
    + 'marcados: eso lo dice el formulario del día y no se toca desde '
    + 'aquí.</span></label><div class="casillas">'
    + MISA_PIEZAS.map(([id, rot, deOrdo]) =>
      '<label class="casilla"><input type="checkbox" data-pieza="' + esc(id)
      + '"' + (puestas.indexOf(id) >= 0 ? ' checked' : '') + '><span>'
      + esc(rot) + (deOrdo ? '<em> · del Ordinario</em>' : '')
      + '</span></label>').join('')
    + '</div></div>';
}

/* Qué pestaña de Ajustes estaba abierta. La vista se rehace entera al
 * cambiar la versión o el modo de la misa, y una pestaña que se cierra sola
 * deja al dedo buscando dónde estaba. Se recuerda para ese repintado y se
 * gasta en él: al volver a Ajustes manda otra vez la de siempre. */
let _ajustesAbiertas = null;

function recuerdaAjustes() {
  const t = {};
  document.querySelectorAll('.ajustes-sec').forEach((d) => {
    t[d.dataset.sec] = d.open;
  });
  _ajustesAbiertas = t;
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
  // cuatro pantallas de deslizar para cambiar una cosa. Todas vienen
  // plegadas, de modo que lo primero que se ve es de qué se puede hablar;
  // sólo se queda abierta la que lo estuviera cuando la vista se rehace
  // sola (al cambiar de versión, o el modo de la misa).
  const ajuste = (titulo) => '</div></details>'
    + '<details class="ajustes-sec" data-sec="' + esc(titulo) + '"'
    + ((_ajustesAbiertas && _ajustesAbiertas[titulo]) ? ' open' : '')
    + '><summary>' + titulo + '</summary><div class="ajustes-cuerpo">';
  vista.innerHTML = [
    ajuste('La lengua de la misa'),
    sel('fuente', 'Versión',
      'La Nova Vulgata es el latín de los libros litúrgicos vigentes; la '
      + 'Clementina, la Vulgata de siempre. El castellano es la traducción '
      + 'litúrgica aprobada para México, cosechada del misalito mensual de '
      + '2018 a 2026: dos de cada tres lecturas la tienen, y lo que no se '
      + 'imprimió nunca lo dice en su sitio. El bilingüe enfrenta las dos, '
      + 'y el latín que pone es el último que se haya elegido aquí.',
      [['clementina', 'Vulgata Clementina'], ['nova', 'Nova Vulgata'],
        ['es', 'Castellano · misalito de México'],
        ['bi', 'Bilingüe · latín y castellano']]),
    sel('acentos', 'Acentuación litúrgica',
      'El acento tónico marcado, como en los libros de coro.',
      [[true, 'Sí'], [false, 'No']]),
    sel('numeros', 'Números de versículo', '', [[true, 'Sí'], [false, 'No']]),
    ajuste('Qué se enseña de la misa'),
    sel('misaVer', 'Del formulario, enseñar',
      'Tres cuartas partes del formulario son el Ordinario, que no cambia '
      + 'de un día para otro. Lo breve deja lo que sí: antífona de entrada, '
      + 'el Gloria los días que lo lleva, la colecta, las lecturas con su '
      + 'salmo y su aclamación, la oración de los fieles, la de las '
      + 'ofrendas, la antífona de comunión y la oración después de la '
      + 'comunión.',
      [['todo', 'Todo, en el orden de la misa'],
        ['breve', 'Lo breve: lo que cambia y se dice'],
        ['propio', 'Lo que yo elija']]),
    E.cfg.misaVer === 'propio' ? piezasDeLaMisa() : '',
    // el ajuste del Ordinario sólo manda en el modo entero: en los otros
    // dos lo que entra se decide pieza por pieza, y ofrecerlo ahí sería
    // ofrecer un mando que no mueve nada
    E.cfg.misaVer === 'todo'
      ? sel('ordinario', 'El ordinario de la misa',
        'El Ordo Missæ intercalado donde va, con sus 146 rúbricas en las '
        + 'dos lenguas. No se lee cada día, pero cuando se busca se busca '
        + 'ahí: viene plegado y se abre tocando su rótulo.',
        [['plegado', 'Plegado'], ['abierto', 'Abierto'],
          ['no', 'No: sólo los propios y las lecturas']])
      : '',
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
    sel('fmtUno', 'Un solo formato para todo',
      'La alineación, el interlineado y la partición de palabras, los '
      + 'mismos en toda la app. Diciendo «no», cada sección puede llevar el '
      + 'suyo —los salmos de una manera y las lecturas de otra—, y lo que '
      + 'una sección no diga lo sigue diciendo el general.',
      [['si', 'Sí'], ['no', 'No: cada sección']]),
    E.cfg.fmtUno === 'si' ? ''
      : '<p class="pista-g">Lo que sigue vale para toda la app; cada '
        + 'sección, más abajo, puede decir otra cosa.</p>',
    '<div class="ajuste"><span class="eti">Interlineado'
    + '<span class="pista">El alto del renglón, en veces el cuerpo de la '
    + 'letra. No hay cuatro medidas sino todas: se mueve de cinco en cinco '
    + 'centésimas, y la muestra de arriba es el renglón de verdad.</span>'
    + '</span>' + pasoInterlinea('') + '</div>',
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
    E.cfg.fmtUno === 'si' ? ''
      : '<h2 class="seccion">El formato de cada sección</h2>'
        + GRUPO_FMT.map((g) => bloqueFmt(g)).join(''),
    ajuste('Aspecto'),
    sel('letra', 'Tipo de letra',
      'Ninguna se descarga: la app tiene que abrir sin conexión, así que lo '
      + 'que se elige no es una fuente sino un aire, y lo sirve la que el '
      + 'teléfono ya tenga. Las de remates se leen como un libro —la de '
      + 'periódico es la que más cabe en el renglón—; las de palo seco, '
      + 'mejor con la letra muy pequeña o muy grande, y la ancha con poca '
      + 'luz.',
      [['serif', 'De libro'], ['antigua', 'De misal'],
        ['gruesa', 'De libro, gruesa'], ['periodico', 'De periódico'],
        ['sans', 'De pantalla'], ['humanista', 'De pantalla, suave'],
        ['ancha', 'De pantalla, ancha']]),
    sel('tema', 'Color del papel', '',
      [['auto', 'Según el teléfono'], ['claro', 'Claro'],
        ['sepia', 'Sepia'], ['oscuro', 'Oscuro'], ['noche', 'De noche']]),
    sel('color', 'El color de la app',
      'El litúrgico tiñe la cabecera, las rúbricas y los controles, y '
      + 'cambia de un día a otro: verde en el tiempo ordinario, morado en '
      + 'Adviento y Cuaresma, rojo en los mártires. Quien prefiera uno '
      + 'quieto lo dice aquí; el calendario sigue enseñando el de cada día, '
      + 'porque allí el color es lo que se lee.',
      [['dia', 'El del día'], ['verde', 'Verde'], ['rojo', 'Rojo'],
        ['morado', 'Morado'], ['blanco', 'Dorado'], ['azul', 'Azul'],
        ['neutro', 'Granate']]),
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
    sel('carril', 'Índice al borde',
      'Las cintas del breviario: una raya por sección al borde de la caja, '
      + 'más larga la de donde vas. Tocar una lleva a su sección. Sirve '
      + 'igual para la hora y para el formulario de la misa.',
      [['si', 'Sí'], ['no', 'No']]),
    sel('gestos', 'Deslizar para cambiar de hora',
      'Arrastrar sobre el texto pasa a la hora siguiente o a la anterior, y '
      + 'de Completas al Oficio de lectura del día siguiente.',
      [['si', 'Sí'], ['no', 'No']]),
    sel('rezadas', 'Marcar lo ya rezado hoy',
      'Una rayita bajo las horas de hoy que ya has rezado. No hay que decir '
      + 'nada: queda marcada aquella cuyo final has llegado a leer.',
      [['si', 'Sí'], ['no', 'No']]),
    '<p class="pie">' + esc(E.lecturas.cabecera)
    + (E.cfg.fuente === 'bi' && E.lecturasEs
      ? '<br><br>' + esc(E.lecturasEs.cabecera) : '')
    + (E.misa ? '<br><br>' + esc(E.misa.cabecera) : '') + '<br><br>'
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

  _ajustesAbiertas = null;
  colocaPosicion();
}

/** Un solo oyente para todos los ajustes: la vista se repinta a menudo y
 *  colgar oyentes en cada repintado los iría acumulando. Los controles van
 *  con el prefijo `aj-` para no chocar con los `id` de la página. */
async function alCambiarAjuste(ev) {
  if (E.vista !== 'ajustes') return;
  // las casillas del modo propio no son un ajuste con nombre sino una
  // lista, y se guarda en el orden del formulario para que `armaMisa` no
  // tenga que ordenarla después
  const pieza = ev.target.dataset.pieza;
  if (pieza) {
    const puestas = piezasPuestas() || [];
    const quedan = ev.target.checked ? puestas.concat([pieza])
      : puestas.filter((x) => x !== pieza);
    E.cfg.misaSecs = MISA_PIEZAS.map((x) => x[0])
      .filter((x) => quedan.indexOf(x) >= 0);
    guardaCfg();
    return;
  }
  // el formato de una sección tampoco es un ajuste con nombre, sino una
  // casilla de la tabla `fmt`: sin valor, se borra, y entonces esa sección
  // vuelve a seguir al general
  const grupo = ev.target.dataset.fmt;
  if (grupo) {
    const f = Object.assign({}, (E.cfg.fmt || {})[grupo]);
    if (ev.target.value) f[ev.target.dataset.campo] = ev.target.value;
    else delete f[ev.target.dataset.campo];
    const fmt = Object.assign({}, E.cfg.fmt);
    fmt[grupo] = f;
    E.cfg.fmt = fmt;
    guardaCfg();
    aplicaFormatoSecs();
    return;
  }
  const id = (ev.target.id || '').replace(/^aj-/, '');
  if (!(id in E.cfg)) return;
  let v = ev.target.value;
  if (v === 'true' || v === 'false') v = (v === 'true');
  if (id === 'misaVer') {
    // al pasar a elegir, la lista empieza por lo que se estaba viendo: no
    // ha de quitar ni añadir nada, sólo dejar tocarlo
    if (v === 'propio') {
      E.cfg.misaSecs = (piezasPuestas()
        || MISA_PIEZAS.map((x) => x[0])).slice();
    }
    E.cfg.misaVer = v;
    guardaCfg();
    recuerdaAjustes();
    verAjustes();      // aparece la lista, y el Ordinario deja de mandar
    return;
  }
  E.cfg[id] = id === 'tam' ? +v : v;
  guardaCfg();
  aplicaCfg();
  if (id === 'fmtUno') {
    recuerdaAjustes();
    verAjustes();      // aparecen, o se van, las pestañas de cada sección
    return;
  }
  if (id === 'tam') {
    const pct = $('#aj-tam-pct');
    if (pct) pct.textContent = E.cfg.tam + '%';
  }
  if (id === 'fuente') {
    // el latín elegido se recuerda, para que el bilingüe ponga el que se
    // estaba leyendo y no uno a la fuerza
    if (v === 'clementina' || v === 'nova') E.cfg.latinBi = v;
    guardaCfg();
    recuerdaAjustes();
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
    ponColor(esDeLaVirgen(dia && dia.t) ? 'azul'
      : E.colorDe.get(cels[0].slug) || 'neutro');
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
    '<span class="tarjeta-p">El leccionario romano en '
    + (E.cfg.fuente === 'es' ? 'castellano' : 'latín')
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
// La memoria del sábado no pasa de Laudes: en la Hora intermedia no se hace
// mención de las memorias, y las vísperas del sábado son las primeras del
// domingo. Así que sólo se ofrece donde se puede rezar.
const HORAS_SMV = ['oficio', 'laudes'];
const SMV = {
  id: 'smv', t: 'Santa María Virgen en sábado', g: 'MEMORIA LIBRE',
  modo: 'memoria', smv: 1
};

function cabeSantaMaria(d, hora) {
  return HORAS_SMV.includes(hora) && d.d === 6 && d.t === 'Ordinario' && !d.cm
    && !(d.c || []).some((c) => !/LIBRE/.test(c[3] || ''));
}

/** Qué oficios puede rezar quien abre el día, y cuál sale primero. */
function celebracionesHoras(d, hora) {
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
  const libres = cabeSantaMaria(d, hora) ? cs.concat([SMV]) : cs;
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

/* La burbuja de las opciones no pasa de la mitad del renglón —la otra mitad
 * es del rótulo, que también hay que leerlo—, y dentro de esa mitad tienen
 * que verse todas: una opción que no se ve no sirve. Para que quepan se
 * abrevian, en dos grados. El primero es el de siempre, el que se lee sin
 * pensar («Past.», «Ss. varones»); el segundo, para cuando ni ése basta, es
 * lo más corto que todavía se reconoce («Ss. var.», «Día»). De cuál se usa
 * en cada sección decide la app al pintar, midiendo. */
const ABREVIA = [
  [/^Santos varones$/, 'Ss. varones'], [/^Santas mujeres$/, 'Stas. mujeres'],
  [/^Santa María$/, 'Sta. María'], [/^Un mártir$/, 'Un márt.'],
  [/^Mártires$/, 'Márt.'], [/^Apóstoles$/, 'Apóst.'],
  [/^Doctores$/, 'Doct.'], [/^Pastores$/, 'Past.'],
  [/^Vírgenes$/, 'Vírg.'], [/^Propio$/, 'Prop.'],
  [/^Complementaria$/, 'Compl.'], [/^Común$/, 'Com.'],
  [/^Dedicación$/, 'Dedic.'], [/^Del día$/, 'Del día']
];

const ABREVIA_MIN = [
  [/^Santos varones$/, 'Ss. var.'], [/^Santas mujeres$/, 'Stas. muj.'],
  [/^Santa María$/, 'Sta. M.'], [/^Un mártir$/, 'Márt.'],
  [/^Mártires$/, 'Márt.'], [/^Apóstoles$/, 'Ap.'],
  [/^Doctores$/, 'Doct.'], [/^Pastores$/, 'Past.'],
  [/^Vírgenes$/, 'Vírg.'], [/^Propio$/, 'Prop.'],
  [/^Complementaria$/, 'Compl.'], [/^Común$/, 'Com.'],
  [/^Dedicación$/, 'Dedic.'], [/^Del día$/, 'Día']
];

function abreviaCon(tabla, rot) {
  for (const [rx, c] of tabla) if (rx.test(rot)) return c;
  // «Pastores II», «Santa María II»: la lectura segunda de un común
  const m = /^(.+?) ([IVX]+)$/.exec(rot);
  return m ? abreviaCon(tabla, m[1]) + ' ' + m[2] : rot;
}
const abrevia = (rot) => abreviaCon(ABREVIA, rot);
const abreviaMin = (rot) => abreviaCon(ABREVIA_MIN, rot);

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
      if (solo && d.d === 0) ponDelante(alts, i, HIMNO_DOMINGO[hora]);
    }
  }
  return alts;
}

/* El himno de la Hora intermedia, los domingos.
 *
 * La fuente da primero el himno del día y detrás el juego del tiempo, y lo
 * que da por «del día» es lo que aquel año imprimió la web: de los treinta
 * y un domingos del tiempo ordinario, en dieciséis puso en Sexta «Cuando la
 * luz del día está en su cumbre» y en quince «Este mundo del hombre, en que
 * él se afana», que es de los de entre semana —los otros dos de ese juego
 * cantan al trabajo, y éste al Señor—. El libro lo señala para el domingo,
 * así que el domingo sale el primero y los demás detrás, en su orden.
 *
 * No se quita nada: el himno del día sigue estando, con su número, y quien
 * lo quiera lo toca. Y donde ese himno no se ofrece —la Cuaresma tiene los
 * suyos y no lo trae—, esto no mueve nada.
 */
const HIMNO_DOMINGO = { sexta: 'cuando la luz del dia esta en su cumbre' };

/** Pone delante del grupo de himnos el que empieza así, y renumera. */
function ponDelante(alts, i, incipitLlano) {
  if (!incipitLlano) return;
  const k = alts.findIndex((a, j) => j > i
    && plano(incipit(a.c)).startsWith(incipitLlano));
  if (k < 0) return;
  alts.splice(i, 0, alts.splice(k, 1)[0]);
  for (let j = i; j < alts.length; j++) alts[j].rot = ROMANOS[j - i];
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
  const L = E.horas;
  const e = op.cel
    && (L.antifonas || {})[op.cel[1] + '/' + op.cel[0] + '/' + hora];
  if (!e || !e.a || !e.a.length) return null;
  // De dónde salen los salmos lo dice el libro impreso con una rúbrica que
  // la fuente no escribe, porque la aplica: «se toma la salmodia del
  // domingo I», «los salmos, del Común de pastores», o los escribe enteros
  // porque son suyos. Las tres formas se reconocen —`l` los propios, `s` la
  // casilla del salterio, `c` el común—, y el texto sale siempre de la
  // fuente. Si no dice nada, son los del día.
  let fuente = dia, rotulo = 'Con los salmos del día';
  if (e.l) {
    fuente = { l: e.l };
    rotulo = 'Con sus salmos propios';
  } else if (e.s) {
    const [sem, ds] = e.s.split('/');
    const otra = L.salterio[d.t + '/' + e.s + '/' + hora]
      || L.salterio['Ordinario/' + e.s + '/' + hora];
    if (otra) {
      fuente = otra;
      rotulo = 'Salmos del ' + DIAS_SEM[+ds] + ' ' + ROMANOS[+sem - 1];
    }
  } else if (e.c) {
    const otra = L.comunes[e.c + '/' + hora + '/salmodia'];
    if (otra) {
      fuente = otra;
      rotulo = 'Salmos del Común de '
        + (L.rotulo_comun[e.c] || '').toLowerCase();
    }
  }
  const piezas = despieza(fuente.l);
  if (!piezas.salmos.length) return null;
  // la rúbrica del libro, tal como la escribe, cuando la hay
  const tit = e.r ? e.r.replace(/\s*\.\s*$/, '')
    : 'Antífonas propias · ' + rotulo;
  return [
    { id: 'propio', rot: 'Propio', tit: tit,
      c: { r: dia.r || 'SALMODIA', l: compone(e.a, piezas.salmos), f: e.f } },
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
  // Del común o del día: sólo donde hay las dos cosas. Los himnos
  // numerados de la Hora intermedia son todos «del día», y ahí este ajuste
  // no tiene nada que escoger: manda el orden en que se ofrecen, que el
  // domingo pone delante el himno del domingo.
  if (i < 0 && alts.some((o) => !o.id.startsWith('dia'))) {
    i = alts.findIndex((o) => E.cfg.hComun === 'dia'
      ? o.id === 'dia' : !o.id.startsWith('dia'));
  }
  return Math.max(0, i);
}

/** El orden de las secciones. La invocación inicial va delante (el orden
 *  recuperado del volcado la dejaba al final de Laudes), y el preámbulo
 *  del Oficio es el invitatorio con otra forma, que ya ocupa su sitio. */
/* Lo que la cosecha dejó de más y la hora no lleva.
 *
 * La fuente publica por fechas, y una página no siempre trae una sola hora.
 * Detrás de las Vísperas del día imprime a veces la cabecera y la oración
 * de las primeras vísperas de la solemnidad que entra —«LA EPIFANÍA DEL
 * SEÑOR», «de la Asunción de la Santísima Virgen María»—; y detrás del
 * Oficio de lectura, la oración de la feria los días que llevan memoria, o
 * la misma otra vez. Al cosechar, aquello quedó como `preambulo`,
 * `oracion2` y `oracion3` de ese día, y pintarlo es poner una segunda
 * oración después de la conclusión: en la memoria de Nuestra Señora del
 * Rosario salían la de la Virgen y detrás la del tiempo ordinario. Son
 * veinte piezas en todo el año y ninguna se reza donde sale.
 *
 * En el Oficio, `preambulo` es además otra cosa —la segunda forma del
 * invitatorio—, y por eso `pieza()` lo busca por su clave: aquí sólo se
 * quita de la fila, no del libro.
 */
const DE_MAS = ['preambulo', 'oracion2', 'oracion3'];

function ordenDe(hora) {
  let o = (E.horas.orden[hora] || []).slice()
    .filter((cl) => !DE_MAS.includes(cl));
  // el invitatorio abre el día, y el día lo abren el Oficio o Laudes: en
  // Vísperas es otro resto de la misma clase
  if (hora !== 'oficio' && hora !== 'laudes') {
    o = o.filter((cl) => cl !== 'invitatorio');
  }
  // El Te Deum: la fuente lo rotula «Himno: Señor, Dios eterno» y el libro
  // lo guarda como un segundo himno, que el orden recuperado dejaba detrás
  // de la conclusión. Va después del segundo responsorio (Ordinario).
  if (hora === 'oficio' && o.includes('himno2')) {
    o = o.filter((cl) => cl !== 'himno2');
    const r = o.indexOf('responsorio2');
    o.splice(r < 0 ? o.length : r + 1, 0, 'himno2');
  }
  // Un sábado del año la fuente dejó la primera lectura bíblica en una
  // casilla de más, `lectura12`, con la suya vacía; el orden la mandaba
  // detrás de la conclusión. Va donde va: delante de su responsorio.
  if (hora === 'oficio' && o.includes('lectura12')) {
    o = o.filter((cl) => cl !== 'lectura12');
    const r = o.indexOf('responsorio');
    o.splice(r < 0 ? o.length : r, 0, 'lectura12');
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
  const cels = celebracionesHoras(d, hora);
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

/* ------------------------------------------------- rótulos y versalitas
 * En el libro van en versalitas los rótulos que estructuran la hora, y sólo
 * ellos: la palabra que nombra la pieza. Lo que la acompaña —la cita de la
 * lectura breve, el nombre del salmo, el comienzo del himno— va en letra
 * normal. La fuente escribe esos nombres en mayúsculas, que es su manera de
 * marcarlos en un HTML sin estilos; aquí se les devuelve su caja, que es la
 * que se lee, y las versalitas quedan para lo que de verdad las lleva.
 *
 * La fuente tampoco acentúa las mayúsculas («ORACION», «ANTIFONA»): al
 * bajarlas a minúsculas la tilde hace falta, así que se repone. */
const TILDES = [
  ['ANTIFONA', 'ANTÍFONA'], ['SANTISIMA', 'SANTÍSIMA'],
  ['ORACION', 'ORACIÓN'], ['CANTICO', 'CÁNTICO'],
  ['EVANGELICO', 'EVANGÉLICO'], ['BENDICION', 'BENDICIÓN'],
  ['INVOCACION', 'INVOCACIÓN'], ['CONCLUSION', 'CONCLUSIÓN'],
  ['MARIA', 'MARÍA'], ['ULTIMA', 'ÚLTIMA']
];

/* Lo que no baja del todo: los nombres de Dios y los propios, que vuelven a
 * su caja —«CRISTO» se lee «Cristo», no a gritos—, y las letras y cifras que
 * son de la cita («Salmo 18 A», «I», «II»), que no se tocan. Van sin tildes
 * y sin eñe: se comparan contra plano(), que se las quita. */
const MAYUSCULA = new Set(('dios senor cristo jesus jesucristo espiritu padre '
  + 'hijo verbo mesias cordero trinidad virgen maria iglesia israel jerusalen '
  + 'sion egipto juda sinai david moises abraham isaac jacob samuel elias '
  + 'pedro pablo juan mateo marcos lucas andres santiago tomas felipe '
  + 'esteban zacarias simeon isabel ana jose miguel gabriel rafael benedictus '
  + 'magnificat pascua navidad adviento cuaresma pentecostes epifania '
  + 'resurreccion ascension sabado domingo').split(' '));

function esMayuscula(p) {
  const l = p.replace(/[^A-Za-zÁÉÍÓÚÜÑ]/g, '');
  return l.length > 0 && l === l.toUpperCase();
}

/** La inicial en alta, si la palabra no la trae ya. */
const mayusculaInicial = (p) => /\p{Lu}/u.test(p) ? p
  : p.replace(/\p{Ll}/u, (c) => c.toUpperCase());

/** Una palabra en mayúsculas, devuelta a su caja: a minúscula, o a su
 *  inicial en alta si es un nombre propio. `trasCifra` dice si la palabra
 *  de antes era un número: «Salmo 18 A» lleva ahí una letra de la cita, y
 *  «el siervo doliente Y Cristo», la conjunción, que sí baja. */
function bajaPalabra(p, trasCifra) {
  const n = plano(p).replace(/[^a-z]/g, '');
  if (!n) return p;
  if (MAYUSCULA.has(n)) return mayusculaInicial(p.toLowerCase());
  // «I», «II»: los números romanos son de la cita y no se tocan
  if (/^[IVX]+$/.test(p.replace(/[^A-Za-z]/g, ''))) return p;
  // «18 A», «9 B»: la letra que numera un salmo tampoco
  if (n.length < 2 && trasCifra) return p;
  return p.toLowerCase();
}

/** Las mayúsculas de una rúbrica, devueltas a su caja: minúsculas, con la
 *  primera en alta y los nombres propios intactos. Lo que ya viene en caja
 *  mixta no se toca, que entonces la fuente ya lo escribió como se lee. */
function cajaNormal(t) {
  if (!t) return '';
  let s = t;
  for (const [de, a] of TILDES) s = s.split(de).join(a);
  let primera = true, anterior = '';
  return s.split(/(\s+)/).map((p) => {
    if (!p.trim()) return p;
    const prev = anterior;
    anterior = p;
    if (!esMayuscula(p)) return p;
    const b = bajaPalabra(p, /\d/.test(prev));
    if (b === p) return p;
    // la primera que baja abre la frase, y abre con mayúscula
    const r = primera ? mayusculaInicial(b) : b;
    primera = false;
    return r;
  }).join('');
}

/* Las palabras que van en versalitas, y cómo se escriben: todas las que
 * nombran una pieza de la hora, que son las que en el libro las llevan. Lo
 * que las acompaña —la cita de la lectura breve, el comienzo del himno— va
 * detrás en letra normal. El orden importa: «RESPONSORIO BREVE» antes que
 * «RESPONSORIO», y «LECTURA BREVE» antes que nada más que empiece igual. */
const VERSALITAS = [
  [/^INVOCACI[ÓO]N\s+INICIAL/i, 'Invocación inicial'],
  [/^INVITATORIO/i, 'Invitatorio'],
  [/^EXAMEN\s+DE\s+CONCIENCIA/i, 'Examen de conciencia'],
  [/^HIMNO\s*:?/i, 'Himno:'],
  [/^SALMODIA/i, 'Salmodia'],
  [/^PRIMERA\s+LECTURA/i, 'Primera lectura'],
  [/^SEGUNDA\s+LECTURA/i, 'Segunda lectura'],
  [/^LECTURA\s+BREVE/i, 'Lectura breve'],
  [/^RESPONSORIO\s+BREVE/i, 'Responsorio breve'],
  [/^RESPONSORIO/i, 'Responsorio'],
  [/^C[ÁA]NTICO\s+EVANG[ÉE]LICO/i, 'Cántico evangélico'],
  [/^PRECES/i, 'Preces'],
  [/^ORACI[ÓO]N\s*\.?/i, 'Oración'],
  [/^BENDICI[ÓO]N/i, 'Bendición'],
  // de este rótulo sólo nombra la pieza «Antífona final»; lo que sigue es
  // de quién es, y va en letra normal y en su caja, que la fuente lo
  // escribe todo en mayúsculas
  [/^ANT[ÍI]FONA\s+FINAL\s+DE\s+LA\s+SANT[ÍI]SIMA\s+VIRGEN/i,
    'Antífona final', ' de la Santísima Virgen'],
  [/^ANT[ÍI]FONA\s+FINAL/i, 'Antífona final'],
  [/^CONCLUSI[ÓO]N/i, 'Conclusión']
];

/* Y dentro de la salmodia, el título de cada salmo y de cada cántico: la
 * palabra en versalitas y el nombre en letra normal. */
const VERSALITAS_TIT = [
  [/^SALMO\b/i, 'Salmo'],
  [/^C[ÁA]NTICO\s+DE\s+(\S+?)\s*\.?(?=\s|$)/i,
    (m) => 'Cántico de ' + mayusculaInicial(cajaNormal(m[1])) + '.'],
  [/^C[ÁA]NTICO\s*:?/i, 'Cántico:']
];

/** Un rótulo, partido en lo que va en versalitas y lo que no. */
function enVersalitas(t, tabla) {
  const s = (t || '').trim();
  for (const [rx, como, resto] of tabla) {
    const m = rx.exec(s);
    if (!m) continue;
    // lo que acompaña al rótulo —la cita, el comienzo del himno, el nombre
    // del salmo— va en letra normal, pero no más grande que las versalitas:
    // nombra menos y no tiene por qué pesar más
    const llano = (resto || '')
      + cajaNormal(s.slice(m[0].length)).replace(/^\s+/, ' ');
    return '<span class="vs">' + esc(typeof como === 'function'
      ? como(m) : como) + '</span>'
      + (llano ? '<span class="llano">' + esc(llano) + '</span>' : '');
  }
  // y el rótulo que no nombra ninguna pieza —«Los salmos y el cántico se
  // toman del Común de un mártir»— es una rúbrica entera: va en letra
  // normal, y del mismo cuerpo que las versalitas
  return '<span class="llano">' + esc(cajaNormal(s)) + '</span>';
}

/* El texto va tal cual: la acentuación que se puede apagar en Ajustes es la
 * del latín, y quitarle las tildes al castellano sería estropearlo. */
function pintaSeccionHora(s) {
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
      + s.alts.map((a, j) => {
        const cor = abrevia(a.rot), min = abreviaMin(a.rot);
        // el rótulo entero y sus dos abreviaturas van los tres puestos: cuál
        // se ve lo decide el CSS, según lo que la app haya medido. Y el
        // nombre accesible es siempre el largo, se vea o no.
        return '<button type="button" aria-pressed="'
        + (j === s.i) + '" data-op="' + esc(a.id) + '"'
        + ' title="' + esc(a.tit || a.rot) + '" aria-label="'
        + esc(a.tit ? a.rot + ': ' + a.tit : a.rot) + '"'
        + '>' + (cor === a.rot && min === a.rot ? esc(a.rot)
          : '<span class="largo">' + esc(a.rot) + '</span>'
            + '<span class="corto">' + esc(cor) + '</span>'
            + '<span class="minimo">' + esc(min) + '</span>')
        + '</button>';
      }).join('') + '</div>';
  if (o.c.r || selector || ed) {
    h.push('<div class="sec-cab"><h2 class="rotulo">'
      + enVersalitas(o.c.r, VERSALITAS)
      + ed + '</h2>' + selector + '</div>');
  }
  h.push(pintaLineas(o.c.l, PROSA.test(s.cl), s.cl));
  return '<section class="hora-sec' + (/^conm/.test(s.cl) ? ' conm' : '')
    + (PROSA.test(s.cl) ? ' prosa' : ' en-verso') + claseFmt(grupoFmt(s))
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

/* Las preces son dos partes: la invitación de quien preside, que acaba en
 * dos puntos, y la respuesta de todos, que va detrás y se repite después de
 * cada prez. A media prez el libro deja sitio para las intenciones libres,
 * y quien reza, al llegar allí, ya no tiene la respuesta a la vista: se ha
 * quedado arriba. Se repone debajo de la rúbrica, en cursiva y sangrada,
 * para que se vea que es la misma y no una prez más. */
const LIBRES = /se pueden a[ñn]adir algunas intenciones/i;

function respuestaGeneral(lineas) {
  const bloques = [];
  let b = [];
  for (const ln of lineas) {
    const t = ln.map((tr) => tr[1]).join('').trim();
    if (t) { b.push(t); continue; }
    if (b.length) { bloques.push(b); b = []; }
    if (bloques.length > 1) break;
  }
  if (b.length) bloques.push(b);
  if (bloques.length < 2 || bloques[1].length !== 1) return '';
  if (!/:\s*$/.test(bloques[0].join(' '))) return '';
  return bloques[1][0];
}

const CRUZ = '<span class="cruz" aria-hidden="true">†</span>';

/* La «N.» de las preces es el hueco de un nombre —el del papa, el del
 * obispo del lugar—, no una palabra del texto: va del color del día, como
 * las rúbricas, para que al llegar a ella se vea que ahí se dice un nombre
 * y no una letra. Se marca sobre el texto ya escapado, y sólo cuando va
 * suelta: «N.» entre letras es otra cosa. */
const RX_NOMBRE = /(^|[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ])N\./g;
const marcaNombre = (h) => h.replace(RX_NOMBRE, '$1<b class="rub">N.</b>');

function pintaLineas(lineas, prosa, seccion) {
  const marcas = cruces(lineas);
  const resp = seccion === 'preces' ? respuestas(lineas) : null;
  const respG = seccion === 'preces' ? respuestaGeneral(lineas) : '';
  const bloques = [];
  let actual = [];
  const cierra = () => {
    if (actual.length) bloques.push(actual);
    actual = [];
  };
  lineas.forEach((ln, i) => {
    const crudo = ln.map((tr) => tr[1]).join('');
    if (!crudo.trim()) { cierra(); return; }
    let cl = 'ln';
    const tit = esTituloSalmo(ln);
    const soloRub = !tit && ln.every((tr) => tr[0] || !tr[1].trim());
    if (tit) cl += ' tit';
    else if (soloRub) cl += ' solo-rub';
    // los «V.» y los «R.» cuelgan de su sigla; la antífona no, que es un
    // texto seguido y la sangría le partía el renglón sin falta
    else if (ln[0][0] && /^\s*Ant/.test(ln[0][1])) cl += ' ant';
    else if (ln[0][0] && /^\s*(V\.|R\.)/.test(ln[0][1])) cl += ' sigla';
    if (resp && resp.has(i)) cl += ' prez-r';
    // El título del salmo y los titulillos de la lectura son rúbrica
    // entera: de ellos sólo «Salmo» o «Cántico» va en versalitas, y el
    // nombre en su caja. Lo demás va tirada a tirada, con su rojo.
    const t = tit
      ? '<b class="rub">' + enVersalitas(crudo, VERSALITAS_TIT) + '</b>'
      : soloRub
        ? '<b class="rub">' + esc(cajaNormal(crudo)) + '</b>'
        : ln.map((tr) => tr[0]
          ? '<b class="rub">' + esc(tr[1]) + '</b>'
          : marcaNombre(esc(tr[1]))).join('');
    actual.push({ sigla: cl.includes(' sigla'),
      h: '<span class="' + cl + '">'
        + (marcas.ini.has(i) ? CRUZ + ' ' : '') + t
        + (marcas.fin.has(i) ? ' ' + CRUZ : '') + '</span>' });
    // Al llegar a las intenciones libres, la respuesta de todos se ha
    // quedado quince renglones más arriba: se repone aquí debajo, con su
    // «R.» delante —del color del día, como las demás siglas— para que se
    // lea como lo que es, la respuesta, y no como una prez más.
    if (respG && soloRub && LIBRES.test(crudo)) {
      actual.push({ h: '<span class="ln prez-libre">'
        + '<b class="rub">R.</b> ' + marcaNombre(esc(respG)) + '</span>' });
    }
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

/* Las opciones de una sección se ven todas o no sirven: antes se metían en
 * una tira que se deslizaba, y lo que no cabía no existía. La burbuja no
 * pasa de la mitad del renglón —la otra mitad es del rótulo, que también
 * hay que leerlo—, y ése es su límite siempre, baje o no a su renglón.
 *
 * Son dos aprietos distintos y se resuelven por separado. Primero la
 * burbuja, dentro de su mitad: se abrevian las opciones que no están
 * elegidas, se achica la letra de los botones, se abrevia también la
 * elegida y, en el último extremo, todas van en lo más corto que se
 * reconoce. Después el rótulo, en la mitad que le queda: un punto menos, y
 * otro; y si ni así entra, se lleva el renglón entero y la burbuja baja
 * debajo, pegada a la derecha. Hace falta medirlo —el ancho de un texto no
 * se sabe hasta que está puesto—, así que se hace al pintar. */
function aprietaCabeceras() {
  document.querySelectorAll('#vista .sec-cab').forEach(aprietaCabecera);
}

function aprietaCabecera(c) {
  const r = c.querySelector('.rotulo');
  const a = c.querySelector('.alterna');
  if (!r || !a) return;
  const cabeBurbuja = () => a.scrollWidth <= a.clientWidth + 1;
  const cabeRotulo = () => r.scrollWidth <= r.clientWidth + 1;
  c.classList.remove('apretado', 'muy-apretado', 'parte');
  a.classList.remove('cortas', 'menuda', 'cortas-todas', 'minimas',
    'desborda');
  // La burbuja, en su mitad: se cede lo menos que haga falta, y en este
  // orden, que es el que menos estorba a quien lee. Cada grado de
  // abreviatura sustituye al anterior —son tres maneras de escribir lo
  // mismo, no tres capas—; la letra menuda va aparte, que es otro eje.
  const grado = (cl) => {
    a.classList.remove('cortas', 'cortas-todas', 'minimas');
    a.classList.add(cl);
  };
  if (!cabeBurbuja()) {
    grado('cortas');
    if (!cabeBurbuja()) {
      a.classList.add('menuda');
      if (!cabeBurbuja()) {
        grado('cortas-todas');
        if (!cabeBurbuja()) grado('minimas');
      }
    }
  }
  // Y si ni en lo más corto cabe —cuatro opciones de rótulo largo—, se le
  // da el renglón entero: la mitad es la regla mientras sirva para que se
  // vean todas, que es para lo que está; rota no serviría de nada.
  if (!cabeBurbuja()) {
    a.classList.add('desborda');
    c.classList.add('parte');
  }
  // y el rótulo, en la que le queda
  if (cabeRotulo()) return;
  c.classList.add('apretado');
  if (cabeRotulo()) return;
  c.classList.add('muy-apretado');
  if (cabeRotulo()) return;
  // Ni así —un rótulo largo no entra en media pantalla de teléfono—:
  // entonces el rótulo se lleva su renglón entero y la burbuja baja debajo,
  // pegada a la derecha. La burbuja se queda como estaba: su mitad es la
  // misma arriba que abajo, y lo que ya cabía en ella sigue cabiendo.
  c.classList.remove('apretado', 'muy-apretado');
  c.classList.add('parte');
}

/** Cambia una sección por su versión nueva, sin tocar el resto de la hora. */
function repintaSeccion(caja, s) {
  const t = document.createElement('template');
  t.innerHTML = pintaSeccionHora(s);
  const nueva = t.content.firstElementChild;
  nueva.classList.add('cambia');
  caja.replaceWith(nueva);
  aprietaCabecera(nueva.querySelector('.sec-cab'));
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

/** La entrada del calendario que corresponde al oficio que se reza: la de
 *  su mismo título y, si no la hay, la del tiempo. De ella salen el color
 *  del día y su grado. */
function entradaDelOficio(iso, titulo) {
  const val = entradasDe(iso);
  if (!val) return null;
  return val.c.find((x) => x[2] && x[2].t === titulo)
    || val.c.find((x) => x[2] && x[2].k === 't') || val.c[0];
}

/** El color del día, del calendario de la misa: el del santo si se reza
 *  su oficio, el del tiempo si no. */
function colorHoras(iso, titulo, op) {
  if (op && op.smv) return 'azul';
  if (esDeLaVirgen(titulo)) return 'azul';
  const e = entradaDelOficio(iso, titulo);
  if (!e) return 'neutro';
  return E.colorDe.get(e[0]) || 'neutro';
}

/* ------------------------------------------ primeras y segundas vísperas
 *
 * Un domingo y una solemnidad tienen dos vísperas: las primeras, la tarde
 * de antes, y las segundas, la suya. Cuál de las dos se canta esa tarde no
 * se decide aquí: lo decide la Tabla de los días litúrgicos, y el n. 61 de
 * los Principios y normas lo dice con todas las letras — «si coinciden las
 * II Vísperas del oficio del día corriente y las I Vísperas del día
 * siguiente, prevalecen las vísperas de la celebración que ocupa el lugar
 * superior en la tabla; en caso de igualdad, las del día corriente»—. Así
 * que se comparan los dos rangos, que es lo que el calendario del proyecto
 * guarda en `r`, y gana el menor; el empate, para hoy.
 *
 * Una misa de vigilia no es una celebración con vísperas: el 24 de
 * diciembre el calendario del leccionario pone ahí la misa de la vigilia de
 * Navidad, con su rango 2, y si contara, las primeras vísperas de Navidad
 * —que son justamente las de esa tarde— empatarían consigo mismas y se
 * perderían. Se pasa de largo, y el rango del día lo pone la celebración
 * que viene detrás: el 24 de diciembre, feria mayor de Adviento. Salvo que
 * no haya otra: el Sábado santo, cuya única entrada es la Vigilia pascual,
 * es un día de rango 1 por sí mismo y así se queda —y entonces el empate
 * con la Pascua deja sus vísperas, que es lo que manda el libro—.
 *
 * El rótulo y el color son una cosa, y los textos, otra, y la segunda se
 * mide (ver `conTextosDeManana`). La fuente publica por fechas, así que en
 * la víspera de una solemnidad publica sus primeras vísperas y al
 * cosecharla fueron a parar a la casilla de ese día: las del domingo, a la
 * del sábado —medido: el sábado de la semana VII de Pascua trae el himno
 * «Ven, Creador» y la antífona «Ven, Espíritu Santo», que son las de
 * Pentecostés—, y las de una solemnidad de entre semana, al santo de la
 * víspera —el 14 de agosto, san Maximiliano María Kolbe guarda las primeras
 * vísperas de la Asunción, y así todos los años, porque el santoral va por
 * fecha—. Pero no siempre: la víspera de la Inmaculada, del 8 de diciembre,
 * trae las vísperas de san Ambrosio y de las de la solemnidad sólo la
 * oración, y lo mismo la de san José. Cuando eso pasa, el rótulo y el color
 * se ponen igual, porque son los que corresponden a la hora que se reza, y
 * la nota del día lo advierte.
 */
const VIGILIA = /^(misa de la vigilia|vigilia)\b/i;

/** La celebración que gana un día, saltándose la misa de vigilia —que es de
 *  la solemnidad del día siguiente, no del día en que se imprime— mientras
 *  quede otra detrás. */
function celebracionDelDia(iso) {
  const val = entradasDe(iso);
  if (!val) return null;
  return val.c.find((x) => x[2] && !VIGILIA.test(x[2].t || '')) || val.c[0];
}

/** El lugar que ocupa en la Tabla: cuanto menor, más manda. */
function rangoDeLaTabla(e) { return (e && e[2] && e[2].r) || 99; }

/** ¿Tiene ese día primeras vísperas? Las tienen los domingos y las
 *  solemnidades (PNLH 61); y lo que gana un domingo está por encima de él
 *  —una fiesta del Señor, el Domingo de Pascua—, así que también. */
function conPrimerasVisperas(iso, e) {
  if (!e || !e[2] || VIGILIA.test(e[2].t || '')) return false;
  return new Date(iso + 'T12:00:00').getDay() === 0
    || gradoCal(e[2]) === 'Solemnidad';
}

function cualVisperas(iso, hora, d, op) {
  if (hora !== 'visperas') return null;
  const cuales = (e, num, cuando, textos) => ({
    n: num, rot: num === 1 ? 'Primeras vísperas' : 'Segundas vísperas',
    iso: cuando, m: e[2], t: tituloCal(e[0], e[2]), g: gradoCal(e[2]),
    textos: textos
  });
  // ¿gana el día que entra?
  const man = suma(iso, 1);
  const e1 = celebracionDelDia(man);
  if (conPrimerasVisperas(man, e1)
      && rangoDeLaTabla(e1) < rangoDeLaTabla(celebracionDelDia(iso))) {
    // en la casilla del sábado están de verdad las vísperas del domingo;
    // las de una solemnidad de entre semana, no, y eso se dice debajo
    return cuales(e1, 1, man, d.d === 6 && /\/\d+\//.test(d.k));
  }
  // si no, son las segundas de hoy, cuando hoy las tiene. La conmemoración
  // no cambia el oficio, que sigue siendo de la feria.
  const conm = !!(op && op.modo === 'conmemoracion');
  const e2 = entradaDelOficio(iso, conm ? d.tt : (op && op.t));
  if (!e2 || !e2[2] || VIGILIA.test(e2[2].t || '')) return null;
  return (d.d === 0 || gradoCal(e2[2]) === 'Solemnidad')
    ? cuales(e2, 2, iso, true) : null;
}

/** La oración de una hora, en bruto: el testigo de a qué celebración
 *  pertenece, porque la oración es la de la celebración y de nadie más. */
function oracionDe(o) {
  const s = o && o.secciones.find((x) => x.cl === 'oracion');
  return s ? JSON.stringify(s.alts[s.i].c.l) : '';
}

/* ¿Lo que se enseña esta tarde es ya el oficio del día siguiente? No se
 * supone: se mide, y el testigo es la oración de las Laudes de hoy. Si la
 * de Vísperas es la misma, las vísperas son del día que acaba; si es otra,
 * el día ya ha cambiado de celebración y lo que hay delante son las
 * primeras vísperas de mañana.
 *
 * Se descartó comparar con la oración de mañana, que parecía lo obvio: no
 * vale, porque una solemnidad con vigilia tiene **dos** oraciones, la de la
 * vigilia y la del día —la Asunción, sin ir más lejos—, y el testigo daba
 * negativo justo donde los textos sí eran los suyos. */
function conTextosDeManana(o, vis) {
  if (!vis || vis.n !== 1 || vis.textos) return;
  const tarde = oracionDe(o);
  const manana = oracionDe(armaHora(o.iso, 'laudes', o.op.id));
  vis.textos = !!tarde && !!manana && tarde !== manana;
}

function notaHoras(o, vis) {
  const n = [], d = o.dia;
  // el rótulo dice «Primeras vísperas» y el color es el del día que entra,
  // pero el texto de debajo no siempre es el suyo: cuando la fuente no dio
  // las primeras vísperas de esa solemnidad, se enseña lo del día que
  // acaba, y más vale decirlo que dejar que se note rezando
  if (vis && vis.n === 1 && !vis.textos) {
    n.push('Esta tarde son ya las primeras vísperas de ' + vis.t + ', y así '
      + 'se titulan; pero la fuente no guarda aquí sus textos, así que el '
      + 'oficio que sigue es el del día que acaba.');
  }
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
  if (E.horasCel === SMV.id && !o.op.smv) {
    n.push('La memoria de Santa María en sábado no pasa de Laudes: en la '
      + 'Hora intermedia no se hace mención de las memorias, y las vísperas '
      + 'del sábado son las primeras del domingo.');
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
    ponColor('neutro');
    $('#titulo-dia').textContent = 'Sin oficio';
    $('#subtitulo-dia').textContent = '';
    vista.innerHTML = '<p class="aviso">Esta fecha cae fuera del calendario '
      + 'que trae la app (' + E.horasDias.rango[0] + '–'
      + E.horasDias.rango[1] + ').</p>';
    return;
  }
  // La celebración elegida viaja con la hora: pasar de Laudes a Vísperas no
  // debe devolver a quien reza al oficio que no escogió. Y si esta hora no
  // puede rezar la que se pidió —la Virgen del sábado no pasa de Laudes—,
  // se recuerda igual, que al volver a Laudes se sigue queriendo aquélla.
  E.horasCel = idCel && !o.cels.ops.some((x) => x.id === idCel) ? idCel
    : (o.cels.ops.length > 1 ? o.op.id : null);
  pintaChipsCelebracionesHoras(o);
  const d = o.dia;
  // Vísperas no es siempre sólo «Vísperas»: cuando son las primeras o las
  // segundas de un domingo o de una solemnidad, se dice, y las primeras son
  // ya del día siguiente —suyo el color, y suyo el nombre de debajo—. Se
  // calcula antes que la nota, que es la que avisa cuando el texto no
  // acompaña al rótulo.
  const vis = cualVisperas(iso, hora, d, o.op);
  conTextosDeManana(o, vis);
  notaHoras(o, vis);
  // la conmemoración no cambia el oficio, que sigue siendo de la feria: ni
  // su título ni su color
  const conm = o.op.modo === 'conmemoracion';
  const primeras = !!vis && vis.n === 1;
  ponColor(primeras ? colorHoras(vis.iso, vis.m.t, null)
    : colorHoras(iso, conm ? d.tt : o.op.t, o.op));
  $('#titulo-dia').textContent = vis ? vis.rot
    : HORAS.find((x) => x[0] === hora)[1];
  const partes = [primeras ? vis.t : (conm ? d.tt : o.op.t)];
  if (primeras) {
    // «Domingo XXXI · Domingo» no dice nada: el grado sólo cuando añade
    if (vis.g !== 'Domingo') partes.push(vis.g);
  } else if (o.op.g && !conm) partes.push(bonito(o.op.g));
  if (d.p) partes.push('Salterio ' + ['', 'I', 'II', 'III', 'IV'][d.p]);
  $('#subtitulo-dia').textContent = partes.join(' · ');
  // el tamaño de la letra, en la cabecera: es la que se queda arriba al
  // bajar, así que las dos aes están a mano a media hora y no sólo al
  // empezar, y no le quitan sitio al selector de la sección
  $('#cab-zoom').innerHTML = controlZoom();
  vista.innerHTML = o.secciones.length
    ? o.secciones.map((x) => pintaSeccionHora(x)).join('')
    : '<p class="aviso">No tengo los textos de esta hora para este día.</p>';
  cabeceraFija(true);
  pintaCarril(o);
  // después del carril: es él quien estrecha la caja, y el rótulo se mide
  // contra el ancho que de verdad le queda
  aprietaCabeceras();
  // el mismo oficio en otra forma —del santo, de la feria— se sigue donde
  // se iba; otra hora, donde se dejó aquélla
  colocaPosicion(() => vuelveADonde(E.donde) || vuelveAlSitioHora(iso, hora));
}

/* ---------------------------------------------- el tamaño, a la mano
 * Que la letra se ve chica se nota rezando, no en Ajustes: dos aes en la
 * cabecera, discretas y al final del renglón donde se lee lo que se celebra.
 * Van ahí y no sobre el primer rótulo porque la cabecera es la que se queda
 * arriba al bajar: así están a mano a media hora y no sólo al empezar, y no
 * le quitan sitio al selector de la sección. Es el mismo ajuste de siempre,
 * así que queda puesto para todo. */
function controlZoom() {
  // sin el tanto por ciento: comparte renglón con el título de la hora, y
  // no cabe un número más. Lo que se cambia se ve solo.
  return '<div class="zoom" role="group" aria-label="Tamaño de la letra">'
    + '<button type="button" data-zoom="-5" aria-label="Letra más pequeña">'
    + 'A</button>'
    + '<button type="button" data-zoom="5" aria-label="Letra más grande">'
    + 'A</button></div>';
}

/* ------------------------------------------- el renglón, donde estaba
 * Cambiar el cuerpo de la letra cambia el alto de todo lo que va por encima
 * del renglón que se está leyendo, y entonces ese renglón se va de la
 * pantalla: con la letra más grande, hacia abajo; con la más chica, hacia
 * arriba. Y se va justo cuando más estorba, que es a media oración.
 *
 * Así que antes de tocar nada se toma nota de dónde está el primer bloque de
 * texto que asoma por debajo de la cabecera y de cuánto le falta para llegar
 * a ella; después se repone ahí. No es el alto de la página lo que se
 * conserva —ése cambia a propósito— sino el sitio de ese bloque, que es lo
 * que el ojo está mirando.
 */
const ANCLAS = '.estrofa-h, .ordo-p, .texto, .antifona, .cita, .cierre, '
  + '.sec-cab';

function anclaDeLectura() {
  const cab = $('#cabecera');
  const arriba = document.body.classList.contains('cab-fija')
    ? Math.max(0, cab.getBoundingClientRect().bottom) : 0;
  const els = vista.querySelectorAll(ANCLAS);
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.bottom > arriba + 4) return { el: el, y: r.top };
  }
  return null;
}

function reponeAncla(a) {
  if (!a || !a.el.isConnected) return;
  const d = a.el.getBoundingClientRect().top - a.y;
  if (Math.abs(d) < 1) return;
  window.scrollTo(0, Math.max(0, Math.round(window.scrollY + d)));
}

function alTocarZoom(ev) {
  const b = ev.target.closest('[data-zoom]');
  if (!b) return;
  const v = Math.min(200, Math.max(80, E.cfg.tam + Number(b.dataset.zoom)));
  if (v === E.cfg.tam) return;
  E.cfg.tam = v;
  guardaCfg();
  const plegado = _plegado;
  const ancla = anclaDeLectura();
  aplicaCfg();
  aprietaCabeceras();
  if (document.body.classList.contains('cab-fija')) {
    mideCabecera();
    // La letra cambia de cuerpo y la página de alto, y al acortarse le mueve
    // el desplazamiento a quien está leyendo. Eso no es un dedo subiendo: la
    // cabecera se queda como estaba —plegada, si lo estaba— y vuelve a
    // desplegarse cuando de verdad se suba. Sin esto, achicar la letra a
    // media hora abría la cabecera entera y tapaba el renglón.
    ponPliegue(plegado);
  }
  // y el renglón que se estaba leyendo vuelve a donde estaba: medir la
  // cabecera le ha cambiado el relleno al <body>, así que esto va al final
  reponeAncla(ancla);
  _ultimoY = Math.max(0, window.scrollY);
  _saltoHasta = Date.now() + 400;
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

/** El carril sirve a las dos cosas largas que tiene la app: la hora y, desde
 *  que la misa se enseña entera, el formulario. */
function conCarril() {
  return E.vista === 'horas' || (E.vista === 'hoy' && !!E.misaVista);
}

function nombreSeccion(s) {
  // la misa trae su nombre puesto; la hora lo saca de su rótulo
  if (s.nombre || s.rot) return s.nombre || s.rot;
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

function vaASeccion(i, animado) {
  const sec = document.querySelectorAll('#vista .hora-sec')[i];
  if (!sec) return;
  // se salta a un sitio lejano del texto: la cabecera se queda plegada,
  // que es como está al bajar, y el renglón cae justo debajo de ella
  ponPliegue(1);
  _saltoHasta = Date.now() + (animado ? 800 : 400);
  sec.scrollIntoView({ block: 'start', behavior: animado ? suave() : 'auto' });
  if (animado) {
    setTimeout(() => { _saltoHasta = 0; alDesplazarCabecera(); }, 820);
  }
}

/* Con el teclado el botón se activa y se va a su sección; el dedo y el ratón
 * pasan por los punteros, más abajo, que es donde se recoge el arrastre. */
function alTocarCarril(ev) {
  const b = ev.target.closest('button');
  if (!b || !conCarril() || ev.detail) return;
  vaASeccion(Array.prototype.indexOf.call($('#carril').children, b), true);
}

/* ------------------------------------------------- el carril, arrastrando
 * Las cintas de un breviario se buscan con el pulgar sin levantarlo: se
 * recorre el canto hasta dar con la que se quería. Aquí igual: el dedo baja
 * por la tira y la hora va pasando por debajo, con el nombre de la sección
 * en que va a la vista. Tocar una raya sigue llevando a la suya, con su
 * movimiento; arrastrando no, que entonces el movimiento va detrás del dedo
 * y lo que se busca no se ve nunca. */
let _arrastra = null;

/** La raya que le toca a una altura de la pantalla: la más cercana, para
 *  que el dedo no tenga que acertar y los extremos respondan. */
function rayaDelCarril(y) {
  let n = -1, cerca = Infinity;
  Array.from($('#carril').children).forEach((b, i) => {
    const r = b.getBoundingClientRect();
    const d = Math.abs((r.top + r.bottom) / 2 - y);
    if (d < cerca) { cerca = d; n = i; }
  });
  return n;
}

function marcaRaya(n) {
  $('#carril').querySelectorAll('button').forEach((b, i) =>
    b.classList.toggle('en', i === n));
}

function alEmpezarCarril(ev) {
  const c = $('#carril');
  if (c.hidden || !conCarril() || ev.button > 0) return;
  _arrastra = { n: rayaDelCarril(ev.clientY), movido: false,
    id: ev.pointerId };
  c.classList.add('arrastrando');
  marcaRaya(_arrastra.n);
  try { c.setPointerCapture(ev.pointerId); } catch (e) { /* da igual */ }
}

function alMoverCarril(ev) {
  if (!_arrastra) return;
  ev.preventDefault();
  const n = rayaDelCarril(ev.clientY);
  if (n < 0 || n === _arrastra.n) return;
  _arrastra.n = n;
  _arrastra.movido = true;
  marcaRaya(n);
  vaASeccion(n, false);
}

function alSoltarCarril() {
  const d = _arrastra;
  if (!d) return;
  _arrastra = null;
  const c = $('#carril');
  c.classList.remove('arrastrando');
  marcaRaya(-1);
  try { c.releasePointerCapture(d.id); } catch (e) { /* da igual */ }
  if (d.movido) {
    _saltoHasta = 0;
    alDesplazarCabecera();
    actualizaCarril();
  } else if (d.n >= 0) {
    vaASeccion(d.n, true);
  }
}

/* --------------------------------------------------- deslizar de hora
 * El dedo pasa de una hora a la siguiente y se para en los extremos: del
 * Oficio de lectura no se sale hacia atrás ni de Completas hacia delante.
 * Cambiar de día es cosa de las flechas de la fecha, que es donde se ve lo
 * que se hace. El gesto no se recoge donde ya hay algo que se desliza a
 * dedo —las tiras de la cabecera, los selectores, el carril—. */
let _dedo = null;

/* El dedo se apunta siempre, no sólo cuando los gestos están puestos: de un
 * mismo apunte salen dos cosas distintas —el arrastre que cambia de hora y
 * el toque que esconde la cabecera y la barra—, y cada una pone sus
 * condiciones al soltar. Lo que no se apunta es lo que se toca para algo:
 * un botón, un enlace, una tira de la cabecera. */
function alEmpezarGesto(ev) {
  _dedo = null;
  if (ev.touches.length !== 1) return;
  if (ev.target.closest('.chips, .alterna, .carril, #cabecera, #barra, '
    + 'input, select, a, button, summary, label')) return;
  const t = ev.touches[0];
  _dedo = { x: t.clientX, y: t.clientY, t: Date.now(),
    sy: Math.max(0, window.scrollY) };
}

function alAcabarGesto(ev) {
  const d = _dedo;
  _dedo = null;
  if (!d) return;
  const t = ev.changedTouches[0];
  const dx = t.clientX - d.x;
  const dy = t.clientY - d.y;
  const sel = window.getSelection();
  // Un toque: el dedo no se ha movido, la página tampoco —no era un
  // arrastre corto que la deslizó—, no se ha quedado quieto encima (eso es
  // alguien eligiendo texto) y no hay nada elegido. Tumbado, esconde la
  // cabecera y la barra; de pie no hace nada, que ahí no sobra ni falta.
  if (Math.abs(dx) < 12 && Math.abs(dy) < 12 && Date.now() - d.t < 350
      && Math.abs(Math.max(0, window.scrollY) - d.sy) < 4
      && !(sel && sel.toString())) {
    alternaPantallaLimpia();
    return;
  }
  if (E.cfg.gestos === 'no' || E.vista !== 'horas' || !E.oficio) return;
  // ancho de sobra, más ancho que alto, y de una vez: un arrastre lento
  // es alguien buscando dónde poner el dedo, no un gesto
  if (Math.abs(dx) < 65 || Math.abs(dx) < Math.abs(dy) * 1.8) return;
  if (Date.now() - d.t > 700) return;
  otraHora(dx < 0 ? 1 : -1);
}

function otraHora(n) {
  const i = HORAS.findIndex((x) => x[0] === E.hora) + n;
  if (i < 0 || i >= HORAS.length) return;
  E.entraDesde = n > 0 ? 'izq' : 'der';
  location.hash = '#/h/' + (E.fecha || hoyISO()) + '/' + HORAS[i][0]
    + (E.horasCel ? '/' + encodeURIComponent(E.horasCel) : '');
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
  if (!conCarril() || _enDesplazamiento) return;
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
  cargaMisaOps();
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
  vista.addEventListener('change', alElegirEnMisa);
  vista.addEventListener('click', alTocarPaso);
  vista.addEventListener('click', alElegirOpcion);
  vista.addEventListener('click', alTocarMisa);
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
  $('#cab-zoom').addEventListener('click', alTocarZoom);
  vista.addEventListener('input', alEscribirCalendario);
  window.addEventListener('scroll', () => {
    alDesplazarCalendario();
    alDesplazarCabecera();
    alDesplazarHoras();
  }, { passive: true });
  $('#carril').addEventListener('click', alTocarCarril);
  $('#carril').addEventListener('pointerdown', alEmpezarCarril);
  $('#carril').addEventListener('pointermove', alMoverCarril);
  $('#carril').addEventListener('pointerup', alSoltarCarril);
  $('#carril').addEventListener('pointercancel', alSoltarCarril);
  document.addEventListener('touchstart', alEmpezarGesto, { passive: true });
  document.addEventListener('touchend', alAcabarGesto, { passive: true });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) velaPantalla();
  });
  window.addEventListener('resize', () => {
    // al ponerse de pie los marcos vuelven: esconderlos es cosa del
    // teléfono tumbado, y en vertical la cabecera ya se pliega al bajar
    if (!cabeSinMarcos()) {
      document.body.classList.remove('pantalla-limpia');
    }
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
