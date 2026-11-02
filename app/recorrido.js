/* El recorrido: lo que se le enseña a quien acaba de instalar la app.
 *
 * No es una burbuja que explica un botón y se va. Va por capítulos, y cada
 * paso en la pantalla de verdad: se oscurece todo menos lo que se señala, y
 * la tarjeta dice qué es. Los gestos —que no se ven, y por eso nadie los
 * encuentra solo— no se cuentan: se piden. La tarjeta dice qué hacer, una
 * mano dibujada lo hace encima, y el paso no se da por bueno hasta que el
 * dedo de quien aprende lo ha hecho (o lo salta). Lo que se cambia
 * practicando se deshace en el paso siguiente, también practicando: la letra
 * que se agranda se vuelve a achicar, el día de mañana vuelve a hoy, la hora
 * a la que se pasa vuelve a Laudes.
 *
 * Va montado encima de app.js, como devo-vistas.js, sin tocarlo: lee su
 * estado (E), navega por sus rutas y añade su fila al pie de Ajustes
 * envolviendo verAjustes. Se abre solo una vez, en la portada de un teléfono
 * que aún no ha guardado ningún ajuste —el de quien acaba de instalarla—, y
 * después siempre desde Ajustes.
 */
'use strict';

const RC = {
  abierto: false,
  cap: 0, paso: 0,
  seguido: false,      // los capítulos de un tirón, o uno suelto del índice
  memo: {},            // lo que un paso apunta para el siguiente
  hecho: false,        // la tarea del paso, cumplida
  vuelta: 0,           // cada paso nuevo deja viejo al anterior
  raiz: null, tarjeta: null, indice: null, foco: null, mano: null, velos: []
};

const rcHoy = () => '#/d/' + hoyISO();
const rcLaudes = () => '#/h/' + hoyISO() + '/laudes';
const rcEn = (s) => document.querySelector(s);
const rcLimpia = () => document.body.classList.contains('pantalla-limpia');
/* El dedo se pide sólo donde hay dedo: con ratón, el toque que esconde la
 * cabecera y el deslizar no existen, y el paso se queda en explicarlos. */
const rcTactil = () => matchMedia('(pointer: coarse)').matches;
const rcInstalada = () => enElApk()
  || matchMedia('(display-mode: standalone)').matches
  || navigator.standalone === true;

/* ------------------------------------------------------- los capítulos
 * Cada paso puede llevar:
 *   ir      la ruta a la que hay que estar (un texto o una función)
 *   el      lo que se señala: un selector, o una función que da el elemento
 *   t, x    el título y lo que se explica
 *   haz     la tarea, si el paso se practica; y entonces `listo(memo)`, que
 *           dice cuándo está hecha, y `gesto`, la mano que la enseña
 *   donde   dónde va la mano, si no es encima de `el`
 *   libre   la pantalla entera se deja tocar: el gesto va sobre el texto
 *   tactil  la tarea sólo se pide con dedo; con ratón se explica nada más
 *   si      el paso sólo sale si esto da verdadero
 *   empieza lo que se apunta en `memo` al entrar */
const CAPITULOS = [
  { id: 'libros', t: 'Los tres libros', p: 'La portada y la barra de abajo',
    pasos: [
      { ir: '#/menu', el: '.portada-elige .tarjeta[href^="#/d/"]',
        t: 'La misa de hoy',
        x: 'Las lecturas del día —y si lo pides, el formulario entero—, en '
          + 'castellano, en latín o en las dos lenguas.' },
      { el: () => [rcEn('.portada-elige .con-tira'), rcEn('.portada-horas')],
        t: 'La Liturgia de las Horas',
        x: 'Abre por la hora que toca según el reloj. Debajo van las siete '
          + 'de hoy, con la que toca marcada: tocando otra, vas a ella.' },
      { el: '.portada-elige .tarjeta[href="#/oraciones"]',
        t: 'El devocionario',
        x: 'Las oraciones de la Iglesia en latín, con su castellano donde lo '
          + 'hay. No va por fechas: se reza cuando se quiere, y las que '
          + 'marques con la estrella quedan entre tus favoritas.' },
      { el: '#barra', t: 'La barra de abajo',
        x: 'Desde cualquier página, a cualquiera de los libros. Si tocas el '
          + 'de la página en que ya estás, te sube al principio.' }
    ] },

  { id: 'dias', t: 'De un día a otro', p: 'La fecha, las flechas y «Hoy»',
    pasos: [
      { ir: rcHoy, el: '.fila-fecha', t: 'La fecha',
        x: 'Lo que ves es siempre de un día. Tocando la fecha se salta a '
          + 'cualquier otro del calendario.' },
      { el: '#siguiente', t: 'Pasar de día',
        x: 'Las flechas, a los lados, llevan al día anterior y al siguiente.',
        haz: 'Toca la flecha de la derecha.', gesto: 'toque',
        empieza: (m) => { m.dia = E.fecha; },
        listo: (m) => E.fecha === suma(m.dia, 1) },
      { el: '#ir-hoy', si: () => !rcEn('#ir-hoy').hidden, t: 'Volver a hoy',
        x: 'Fuera de hoy sale este botón, abajo a la derecha.',
        haz: 'Tócalo para volver.', gesto: 'toque',
        listo: () => E.fecha === hoyISO() },
      { el: '#celebraciones',
        si: () => rcEn('#celebraciones').children.length > 1,
        t: 'Cuando hay que elegir',
        x: 'Hay días que dejan elegir —la memoria o la feria, una misa u '
          + 'otra—. Las opciones van aquí, bajo el título.' }
    ] },

  { id: 'leer', t: 'Leer a gusto', p: 'La letra, la cabecera y la pantalla entera',
    pasos: [
      { ir: rcHoy, el: '#cab-zoom .zoom', donde: '#cab-zoom [data-zoom="5"]',
        si: () => E.cfg.tam < 200, t: 'El tamaño de la letra',
        x: 'Las dos aes de la cabecera la achican y la agrandan sin salir de '
          + 'lo que lees, y el renglón que leías se queda donde estaba.',
        haz: 'Toca la A grande.', gesto: 'toque',
        empieza: (m) => { m.tam = E.cfg.tam; },
        listo: (m) => E.cfg.tam > m.tam },
      { el: '#cab-zoom .zoom', donde: '#cab-zoom [data-zoom="-5"]',
        si: (m) => m.tam !== undefined && E.cfg.tam > m.tam,
        t: 'Y de vuelta',
        x: 'Lo que eliges queda puesto para toda la app. En Ajustes está el '
          + 'mismo mando, con una muestra del texto.',
        haz: 'Toca la A pequeña para dejarla como estaba.', gesto: 'toque',
        listo: (m) => E.cfg.tam <= m.tam },
      { libre: true, t: 'La cabecera se recoge',
        x: 'Al bajar leyendo, la cabecera se pliega y le deja el sitio al '
          + 'texto; al subir un poco, vuelve.',
        haz: 'Baja un poco por el texto.', gesto: 'sube',
        listo: () => window.scrollY > 160 },
      { libre: true, tactil: true, t: 'La pantalla entera',
        x: 'Un toque en el texto esconde la cabecera y la barra, y te quedas '
          + 'sólo con lo que rezas. Con el teléfono de lado es cuando más se '
          + 'agradece.',
        haz: 'Toca una vez el texto.', gesto: 'toque',
        listo: () => rcLimpia() },
      { libre: true, tactil: true, si: () => rcLimpia(), t: 'Y vuelven',
        x: 'Otro toque las devuelve. Al pasar a otra hora vuelven solas.',
        haz: 'Toca otra vez el texto.', gesto: 'toque',
        listo: () => !rcLimpia() }
    ] },

  { id: 'horas', t: 'Rezar las horas', p: 'De una hora a otra, y las cintas del borde',
    pasos: [
      { ir: rcLaudes, el: '#formularios', t: 'Las siete horas',
        x: 'Arriba van las horas del día: la que rezas, con su nombre entero. '
          + 'Toca otra para pasar a ella.' },
      { libre: true, tactil: true, si: () => E.cfg.gestos !== 'no',
        t: 'Con el dedo',
        x: 'También se pasa de hora sin subir a la cabecera.',
        haz: 'Desliza el dedo sobre el texto, de derecha a izquierda.',
        gesto: 'izq',
        empieza: (m) => { m.hora = E.hora; },
        listo: (m) => !!E.hora && E.hora !== m.hora },
      { libre: true, tactil: true, si: (m) => !!m.hora && E.hora !== m.hora,
        t: 'Y hacia atrás',
        x: 'Al revés, a la anterior. Del Oficio de lectura no se sale hacia '
          + 'atrás, ni de Completas hacia delante: para cambiar de día están '
          + 'las flechas.',
        haz: 'Desliza de izquierda a derecha para volver a Laudes.',
        gesto: 'der', listo: (m) => E.hora === m.hora },
      { el: '#carril', si: () => !rcEn('#carril').hidden,
        t: 'Las cintas del borde',
        x: 'Como las de un breviario: una raya por sección, más larga la de '
          + 'donde vas. Un toque lleva a su sección, y arrastrando el pulgar '
          + 'por ellas la hora va pasando debajo, con el nombre de cada una.',
        haz: 'Toca una raya, o arrastra el dedo por ellas.', gesto: 'abajo',
        empieza: (m) => { m.y = window.scrollY; },
        listo: (m) => Math.abs(window.scrollY - m.y) > 60 },
      { el: () => vista.querySelector('.alterna'),
        si: () => !!vista.querySelector('.alterna'), t: 'Lo que se elige',
        x: 'Donde las rúbricas dejan elegir —el invitatorio o la invocación, '
          + 'lo del común o lo del día—, la sección trae su selector.' }
    ] },

  { id: 'ajustes', t: 'A tu gusto', p: 'Ajustes: la letra, el papel, la lengua',
    pasos: [
      { ir: '#/ajustes', el: '.aj-intro', t: 'Ajustes',
        x: 'Lo que eliges aquí vale desde ese momento y queda guardado en el '
          + 'teléfono: no hay que guardar nada. Bajo el nombre de cada '
          + 'pestaña ves lo que tiene puesto.' },
      { el: 'details[data-clave="formato"] > summary',
        t: 'Las pestañas se abren',
        x: 'Cada una se abre tocándola. Al pie trae «Restablecer valores», '
          + 'que pide dos toques para no borrar nada por descuido.',
        haz: 'Abre «Formato del texto».', gesto: 'toque',
        listo: () => !!(rcEn('details[data-clave="formato"]') || {}).open },
      { el: 'details[data-clave="formato"] .muestra',
        si: () => !!(rcEn('details[data-clave="formato"]') || {}).open,
        t: 'La muestra',
        x: 'Es el texto de verdad, con las mismas reglas: el tamaño, el '
          + 'interlineado, el justificado. Lo que ves aquí es lo que verás '
          + 'rezando.' },
      { el: 'details[data-clave="aspecto"] > summary', t: 'Aspecto',
        x: 'La letra, el color del papel y el de la app. Hay un papel «De '
          + 'noche», ámbar sobre negro, para rezar Completas a oscuras.' },
      { el: () => [rcEn('details[data-clave="lengua"]'),
        rcEn('details[data-clave="misa"]')],
      t: 'La misa',
      x: 'La lengua —el castellano, tres latines o los dos enfrentados— y '
          + 'cuánto se enseña: lo breve, todo con el Ordinario, o lo que tú '
          + 'elijas pieza por pieza.' },
      { el: 'details[data-clave="horas"] > summary', t: 'Las horas',
        x: 'Aquí se apagan las cintas del borde y el deslizar, si te '
          + 'estorban, y se pide una rayita bajo las horas que ya rezaste '
          + 'hoy.' },
      { el: 'details[data-clave="abrir"] > summary', t: 'Al abrir la app',
        x: 'Si siempre vas al mismo libro, dilo aquí y la app abrirá por él '
          + 'sin preguntar.' },
      { el: '.aj-recorrido', t: 'Y este recorrido',
        x: 'Aquí lo tienes para volver a verlo cuando quieras, entero o por '
          + 'capítulos.' }
    ] },

  { id: 'voz', t: 'Sin cobertura y en voz alta', p: 'Para el coche, el campo y el viaje',
    pasos: [
      { ir: rcHoy, el: '#dale-voz', si: () => !!rcEn('#dale-voz'),
        t: 'En voz alta',
        x: 'El altavoz de la cabecera reza lo que tienes delante, sección por '
          + 'sección, y sigue con la pantalla apagada. Abajo salen sus '
          + 'mandos: atrás, pausa y adelante.' },
      { ir: '#/ajustes', el: 'details[data-clave="voz"] > summary',
        t: 'La voz',
        x: 'Aquí se elige la voz, la velocidad y si al acabar una hora sigue '
          + 'con la siguiente. La voz de Piper se baja una vez, con wifi, y '
          + 'después habla sin red.' },
      { t: 'Sin cobertura',
        x: 'La app guarda en el teléfono lo que necesita la primera vez que '
          + 'tiene red: la misa, las horas y el devocionario. Déjala abierta '
          + 'un rato con wifi el primer día, y después reza donde sea.' },
      { si: () => !rcInstalada(), t: 'Con su icono',
        x: 'Para tenerla en la pantalla de inicio como cualquier otra app: en '
          + 'Chrome, el menú ⋮ y «Instalar app» (o «Añadir a pantalla de '
          + 'inicio»); en el iPhone, Compartir y «Añadir a pantalla de '
          + 'inicio».' }
    ] }
];

/* Lo que no se ve, en una tabla: para quien ya hizo el recorrido y sólo
 * quiere acordarse de un gesto. */
const RC_GESTOS = [
  ['Un toque en el texto', 'esconde la cabecera y la barra; otro, las devuelve'],
  ['Deslizar a los lados', 'en las horas, la siguiente o la anterior'],
  ['Las rayas del borde', 'tocar una, o arrastrar el pulgar, salta de sección'],
  ['Las dos aes', 'la letra, más chica o más grande'],
  ['La fecha', 'cualquier día del calendario; «Hoy» te devuelve'],
  ['La sección en la que estás', 'tocarla en la barra sube al principio']
];

/* --------------------------------------------------------- lo guardado */
function rcLee() {
  try {
    return JSON.parse(localStorage.getItem('recorrido') || '{}') || {};
  } catch (_) { return {}; }
}

function rcGuarda(cambio) {
  const o = Object.assign(rcLee(), cambio);
  try { localStorage.setItem('recorrido', JSON.stringify(o)); } catch (_) {}
}

function rcHechos() { return rcLee().hechos || {}; }

/* ------------------------------------------------------------ el montaje
 * Cuatro velos alrededor de lo que se señala, y no uno con un agujero: el
 * agujero tiene que dejar pasar el dedo —para tocar la flecha, para
 * arrastrar por el carril— y lo de fuera no, que un toque perdido no ha de
 * sacar a nadie del recorrido. Lo oscuro lo pone la sombra del foco, que es
 * la que se mueve con suavidad de un sitio a otro. */
function rcMonta() {
  if (RC.raiz) return;
  const r = RC.raiz = document.createElement('div');
  r.id = 'recorrido';
  r.className = 'rc';
  r.hidden = true;
  r.innerHTML = '<div class="rc-foco" aria-hidden="true"></div>'
    + '<div class="rc-velo"></div><div class="rc-velo"></div>'
    + '<div class="rc-velo"></div><div class="rc-velo"></div>'
    + '<div class="rc-mano" aria-hidden="true"><i></i></div>'
    + '<section class="rc-tarjeta" role="dialog" aria-labelledby="rc-t" '
    + 'aria-live="polite"></section>'
    + '<div class="rc-indice" hidden></div>';
  document.body.appendChild(r);
  RC.foco = r.querySelector('.rc-foco');
  RC.velos = Array.from(r.querySelectorAll('.rc-velo'));
  RC.mano = r.querySelector('.rc-mano');
  RC.tarjeta = r.querySelector('.rc-tarjeta');
  RC.indice = r.querySelector('.rc-indice');
  // el toque que esconde la cabecera lo recoge app.js en el documento: lo
  // que se toca en el recorrido no ha de llegarle, o leer la tarjeta
  // escondería la cabecera
  ['touchstart', 'touchend'].forEach((t) =>
    r.addEventListener(t, (ev) => ev.stopPropagation(), { passive: true }));
  r.addEventListener('click', rcAlTocar);
}

function rcAlTocar(ev) {
  const b = ev.target.closest('[data-rc]');
  if (!b) return;
  const q = b.dataset.rc;
  if (q === 'sigue') return rcSigue();
  if (q === 'atras') return rcPaso(RC.cap, RC.paso - 1, -1);
  if (q === 'salir' || q === 'cierra') return rcCierra();
  if (q === 'empieza') {
    const h = rcHechos();
    const k = CAPITULOS.findIndex((c) => !h[c.id]);
    return rcEmpieza(k < 0 ? 0 : k, true);
  }
  if (q === 'cap') return rcEmpieza(+b.dataset.k, false);
  if (q === 'portada') { rcCierra(); location.hash = '#/menu'; }
}

document.addEventListener('keydown', (ev) => {
  if (!RC.abierto) return;
  if (ev.key === 'Escape') { ev.preventDefault(); rcCierra(); return; }
  if (!RC.indice.hidden) return;
  if (ev.key === 'ArrowRight') rcSigue();
  if (ev.key === 'ArrowLeft') rcPaso(RC.cap, RC.paso - 1, -1);
});

/* --------------------------------------------------------------- el índice
 * La puerta del recorrido: los capítulos, con los vistos marcados, y los
 * gestos en una tabla. La primera vez lleva además la bienvenida. */
function rcAbreIndice(como) {
  rcMonta();
  const o = como || {};
  const h = rcHechos();
  const vistos = CAPITULOS.filter((c) => h[c.id]).length;
  const sigue = CAPITULOS.findIndex((c) => !h[c.id]);
  RC.abierto = true;
  RC.raiz.hidden = false;
  RC.raiz.className = 'rc en-indice';
  RC.tarjeta.hidden = true;
  RC.indice.hidden = false;
  rcGuarda({ visto: 1 });
  const caps = CAPITULOS.map((c, k) => '<li><button type="button" data-rc="cap" '
    + 'data-k="' + k + '"' + (h[c.id] ? ' class="hecho"' : '') + '>'
    + '<span class="rc-num" aria-hidden="true">' + (h[c.id] ? '✓' : k + 1)
    + '</span><span class="rc-ct">' + esc(c.t) + (h[c.id]
      ? '<span class="rc-visto">, visto</span>' : '') + '</span>'
    + '<span class="rc-cp">' + esc(c.p) + ' · ' + c.pasos.length
    + ' pasos</span></button></li>').join('');
  const gestos = RC_GESTOS.map(([g, d]) =>
    '<dt>' + esc(g) + '</dt><dd>' + esc(d) + '</dd>').join('');
  RC.indice.innerHTML = '<div class="rc-hoja" role="dialog" aria-modal="true" '
    + 'aria-labelledby="rc-it">'
    + '<button type="button" class="rc-cierra" data-rc="cierra" '
    + 'aria-label="Cerrar">' + ICONO.cerrar + '</button>'
    + '<p class="rc-sobre">' + (o.fin ? 'Recorrido terminado'
      : o.bienvenida ? 'Para empezar' : 'Recorrido de la app') + '</p>'
    + '<h2 class="rc-it" id="rc-it">' + (o.fin ? 'Ya está' : 'Liturgicum')
    + '</h2>'
    + '<p class="rc-intro">' + (o.fin
      ? 'Lo que falta lo irás encontrando rezando. Si se te olvida un gesto, '
        + 'aquí abajo están todos.'
      : 'La app lleva dentro tres libros —la misa, la Liturgia de las Horas '
        + 'y el devocionario— y se reza sin cobertura. En unos minutos te '
        + 'enseño dónde está cada cosa y los gestos que no se ven: ésos no te '
        + 'los cuento, te los pido.') + '</p>'
    + '<ol class="rc-caps">' + caps + '</ol>'
    + (o.fin
      ? '<button type="button" class="rc-boton" data-rc="portada">Ir a la '
        + 'portada</button>'
      : '<button type="button" class="rc-boton" data-rc="empieza">'
        + (vistos === 0 ? 'Empezar'
          : sigue < 0 ? 'Verlo otra vez'
            : 'Seguir por «' + esc(CAPITULOS[sigue].t) + '»') + '</button>'
        + '<button type="button" class="rc-boton-b" data-rc="cierra">'
        + (o.bienvenida ? 'Ahora no' : 'Cerrar') + '</button>')
    + '<details class="rc-gestos"' + (o.fin ? ' open' : '') + '><summary>'
    + 'Los gestos, de un vistazo</summary><dl>' + gestos + '</dl></details>'
    + (o.bienvenida
      ? '<p class="rc-nota">Lo tienes siempre en Ajustes, al pie de «El año '
        + 'y la app».</p>' : '')
    + '</div>';
  rcPara();
  RC.indice.scrollTop = 0;
  const b = RC.indice.querySelector('.rc-boton');
  if (b) b.focus({ preventScroll: true });
}

/* Salir a media lección deja la app donde estaba: quien sale es que ya
 * quiere usarla. */
function rcCierra() {
  if (!RC.raiz) return;
  RC.vuelta++;
  rcPara();
  RC.abierto = false;
  RC.raiz.hidden = true;
  RC.indice.hidden = true;
  RC.tarjeta.hidden = true;
}

/* ---------------------------------------------------------------- los pasos */
function rcEmpieza(cap, seguido) {
  RC.seguido = seguido;
  RC.memo = {};
  RC.indice.hidden = true;
  RC.tarjeta.hidden = false;
  rcPaso(cap, 0, 1);
}

function rcSigue() {
  if (RC.indice.hidden === false) return;
  rcPaso(RC.cap, RC.paso + 1, 1);
}

/** Se pasa al paso i del capítulo, saltando los que no tocan aquí —el
 *  carril apagado, un día sin nada que elegir— en la dirección en que se
 *  iba. Si el paso lleva ruta, se va a ella y se espera a que la vista esté
 *  pintada antes de buscar lo que se señala. */
async function rcPaso(cap, i, dir) {
  const v = ++RC.vuelta;
  const c = CAPITULOS[cap];
  if (i < 0) {
    if (cap > 0 && RC.seguido) {
      return rcPaso(cap - 1, CAPITULOS[cap - 1].pasos.length - 1, -1);
    }
    i = 0;
    dir = 1;
  }
  if (i >= c.pasos.length) return rcFinCapitulo(cap);
  if (cap !== RC.cap) RC.memo = {};
  RC.cap = cap;
  RC.paso = i;
  RC.hecho = false;
  const p = c.pasos[i];
  // la ruta del paso; y volviendo atrás, la del último que la dijo, que hay
  // que estar donde estaba aquel paso. Hacia delante no: el paso de «Hoy»
  // se da en el día de mañana al que llevó el anterior
  let ruta = p.ir || null;
  for (let k = i - 1; dir < 0 && k >= 0 && !ruta; k--) {
    ruta = c.pasos[k].ir || null;
  }
  ruta = typeof ruta === 'function' ? ruta() : ruta;
  if (ruta && location.hash !== ruta) location.hash = ruta;
  await rcEsperaVista(v);
  if (v !== RC.vuelta) return;
  if (p.si && !p.si(RC.memo)) return rcPaso(cap, i + dir, dir);
  const el = p.el ? await rcEsperaEl(p.el, v) : null;
  if (v !== RC.vuelta) return;
  if (p.el && !el) return rcPaso(cap, i + dir, dir);
  if (p.empieza) p.empieza(RC.memo);
  RC.p = p;
  RC.el = el;
  RC.tarea = !!p.haz && !(p.tactil && !rcTactil());
  if (el) rcALaVista(el);
  rcPintaTarjeta(c, p, i);
  RC.raiz.className = 'rc' + (p.libre ? ' libre' : '')
    + (el ? '' : ' sin-foco') + (RC.tarea ? ' haciendo' : '');
  rcMueve();
  rcBucle(v);
}

function rcFinCapitulo(cap) {
  const h = rcHechos();
  h[CAPITULOS[cap].id] = 1;
  rcGuarda({ hechos: h });
  if (RC.seguido && cap + 1 < CAPITULOS.length) {
    RC.memo = {};
    return rcPaso(cap + 1, 0, 1);
  }
  const todos = CAPITULOS.every((c) => h[c.id]);
  rcAbreIndice({ fin: RC.seguido || todos });
}

/** La vista de la ruta, ya pintada: la de las horas tarda lo que tarda en
 *  cargar el oficio, la de la misa el formulario. */
function rcEsperaVista(v) {
  return new Promise((listo) => {
    const t0 = Date.now();
    const mira = () => {
      if (v !== RC.vuelta) return listo();
      const pintada = !vista.querySelector('#arranque, .aviso.cargando');
      if ((pintada && Date.now() - t0 > 120) || Date.now() - t0 > 8000) {
        return listo();
      }
      setTimeout(mira, 80);
    };
    mira();
  });
}

function rcBusca(el) {
  const x = typeof el === 'function' ? el() : document.querySelector(el);
  const xs = (Array.isArray(x) ? x : [x]).filter((e) => e && e.isConnected
    && e.getClientRects().length);
  return xs.length ? xs : null;
}

function rcEsperaEl(el, v) {
  return new Promise((listo) => {
    const t0 = Date.now();
    const mira = () => {
      if (v !== RC.vuelta) return listo(null);
      const x = rcBusca(el);
      if (x || Date.now() - t0 > 1500) return listo(x);
      setTimeout(mira, 80);
    };
    mira();
  });
}

/** Lo que se señala dentro de la página se trae al medio; lo de la cabecera
 *  y la barra ya está a la vista. */
function rcALaVista(xs) {
  const el = xs[0];
  if (!vista.contains(el)) return;
  const r = el.getBoundingClientRect();
  const arriba = rcEn('#cabecera').getBoundingClientRect().bottom;
  if (r.top >= arriba + 8 && r.bottom <= window.innerHeight * 0.6) return;
  el.scrollIntoView({ block: 'center', behavior: suave() });
}

function rcPintaTarjeta(c, p, i) {
  const n = c.pasos.length;
  const ultimo = i === n - 1 && (!RC.seguido || RC.cap === CAPITULOS.length - 1);
  const puntos = c.pasos.map((_, k) => '<i' + (k === i ? ' class="en"'
    : k < i ? ' class="ya"' : '') + '></i>').join('');
  RC.tarjeta.innerHTML = '<p class="rc-cap">' + (RC.cap + 1) + ' de '
    + CAPITULOS.length + ' · ' + esc(c.t) + '</p>'
    + '<h2 class="rc-t" id="rc-t">' + esc(p.t) + '</h2>'
    + '<p class="rc-x">' + esc(p.x) + '</p>'
    + (RC.tarea ? '<p class="rc-haz"><span class="rc-punto" aria-hidden="true">'
      + '</span><span>' + esc(p.haz) + '</span></p>'
      // sin dedo, el gesto no se pide, pero se dice cuál es
      : p.haz ? '<p class="rc-x rc-tel">En el teléfono: '
        + esc(p.haz.charAt(0).toLowerCase() + p.haz.slice(1)) + '</p>' : '')
    + '<div class="rc-pie">'
    + '<button type="button" class="rc-salir" data-rc="salir">Salir</button>'
    + '<span class="rc-puntos" role="img" aria-label="Paso ' + (i + 1)
    + ' de ' + n + '">' + puntos + '</span>'
    + '<button type="button" class="rc-atras" data-rc="atras" '
    + 'aria-label="Paso anterior"' + (i === 0 && (RC.cap === 0 || !RC.seguido)
      ? ' disabled' : '') + '>' + ICONO.izq + '</button>'
    + '<button type="button" class="rc-sigue' + (RC.tarea ? ' salta' : '')
    + '" data-rc="sigue">' + (RC.tarea ? 'Saltar'
      : ultimo ? 'Terminar' : 'Siguiente') + '</button>'
    + '</div>';
  // la tarjeta, del lado en que no estorba: donde quede más sitio libre
  let abajo = true;
  if (RC.el && !p.libre) {
    const r = rcRect(RC.el);
    abajo = window.innerHeight - r.bottom >= r.top;
  }
  RC.tarjeta.classList.toggle('arriba', !abajo);
  RC.tarjeta.classList.remove('entra');
  void RC.tarjeta.offsetWidth;
  RC.tarjeta.classList.add('entra');
}

/** La tarea, cumplida: se dice, y al momento se sigue. */
function rcHecho(v) {
  RC.hecho = true;
  RC.raiz.classList.remove('haciendo');
  RC.raiz.classList.add('hecho');
  const haz = RC.tarjeta.querySelector('.rc-haz');
  if (haz) {
    haz.classList.add('hecha');
    haz.innerHTML = '<span class="rc-bien" aria-hidden="true">✓</span>'
      + '<span>Eso es.</span>';
  }
  const b = RC.tarjeta.querySelector('.rc-sigue');
  if (b) { b.classList.remove('salta'); b.textContent = 'Siguiente'; }
  setTimeout(() => { if (v === RC.vuelta) rcSigue(); }, 1100);
}

/* ------------------------------------------------------- foco, velos, mano */
function rcRect(xs) {
  let t = Infinity, l = Infinity, b = -Infinity, d = -Infinity;
  xs.forEach((e) => {
    const r = e.getBoundingClientRect();
    t = Math.min(t, r.top); l = Math.min(l, r.left);
    b = Math.max(b, r.bottom); d = Math.max(d, r.right);
  });
  const m = 6;
  const W = window.innerWidth, H = window.innerHeight;
  return { top: Math.max(0, t - m), left: Math.max(0, l - m),
    bottom: Math.min(H, b + m), right: Math.min(W, d + m) };
}

/* Al cambiar de paso el foco viaja con transición; mientras dura el paso
 * va pegado a lo que señala, que se mueve con la página. */
function rcMueve() {
  RC.raiz.classList.add('mueve');
  clearTimeout(RC._mueve);
  RC._mueve = setTimeout(() => RC.raiz.classList.remove('mueve'), 420);
}

function rcCaja(div, t, l, w, h) {
  const s = div.style;
  if (w <= 0 || h <= 0) { s.display = 'none'; return; }
  s.display = 'block';
  s.top = t + 'px'; s.left = l + 'px'; s.width = w + 'px'; s.height = h + 'px';
}

function rcColoca() {
  const p = RC.p;
  if (!p) return;
  const W = window.innerWidth, H = window.innerHeight;
  // lo que se señala puede rehacerse —Ajustes se repinta al tocar un
  // mando—: se vuelve a buscar en vez de perderlo
  if (RC.el && !RC.el.every((e) => e.isConnected) && p.el) {
    RC.el = rcBusca(p.el) || RC.el;
  }
  const r = RC.el ? rcRect(RC.el) : null;
  const [v0, v1, v2, v3] = RC.velos;
  if (p.libre) {
    // el gesto va sobre el texto, y el texto se ha de ver entero
    RC.foco.style.display = 'none';
  } else if (r) {
    rcCaja(RC.foco, r.top, r.left, r.right - r.left, r.bottom - r.top);
    // mientras la página viaja hasta lo señalado, la tarjeta busca el lado
    // que le va a quedar libre
    if (RC.raiz.classList.contains('mueve')) {
      RC.tarjeta.classList.toggle('arriba', H - r.bottom < r.top);
    }
  } else {
    rcCaja(RC.foco, H / 2, W / 2, 0.01, 0.01);
  }
  if (p.libre) {
    RC.velos.forEach((x) => { x.style.display = 'none'; });
  } else if (!r || !RC.tarea) {
    // sólo mirar: no se toca nada más que la tarjeta
    rcCaja(v0, 0, 0, W, H);
    [v1, v2, v3].forEach((x) => { x.style.display = 'none'; });
  } else {
    rcCaja(v0, 0, 0, W, r.top);
    rcCaja(v1, r.bottom, 0, W, H - r.bottom);
    rcCaja(v2, r.top, 0, r.left, r.bottom - r.top);
    rcCaja(v3, r.top, r.right, W - r.right, r.bottom - r.top);
  }
  // la mano: sobre lo que se toca, o en medio del texto
  const m = RC.mano;
  if (!RC.tarea || RC.hecho || !p.gesto) {
    m.className = 'rc-mano';
    return;
  }
  let x = W / 2, y = H * 0.46;
  const sobre = p.donde ? rcBusca(p.donde) : RC.el;
  if (sobre && !p.libre) {
    const q = rcRect(sobre);
    // en lo ancho —una pestaña de Ajustes—, la yema hacia la flecha del
    // final, que en medio tapaba el nombre que se pide tocar
    x = q.right - q.left > 220 ? q.right - 48 : (q.left + q.right) / 2;
    y = p.gesto === 'abajo' ? q.top + Math.min(60, (q.bottom - q.top) / 4)
      : (q.top + q.bottom) / 2;
  }
  // el carril va pegado al borde: la mano, entera dentro de la pantalla
  m.style.left = Math.max(28, Math.min(W - 28, x)) + 'px';
  m.style.top = y + 'px';
  m.className = 'rc-mano g-' + p.gesto;
}

/* Un cuadro de cada vez, sólo mientras hay paso: coloca y, de tanto en
 * tanto, mira si la tarea ya está hecha. */
function rcBucle(v) {
  cancelAnimationFrame(RC._bucle);
  let ultima = 0;
  const cuadro = (t) => {
    if (v !== RC.vuelta || !RC.abierto) return;
    rcColoca();
    if (RC.tarea && !RC.hecho && t - ultima > 120) {
      ultima = t;
      if (RC.p.listo && RC.p.listo(RC.memo)) rcHecho(v);
    }
    RC._bucle = requestAnimationFrame(cuadro);
  };
  RC._bucle = requestAnimationFrame(cuadro);
}

function rcPara() {
  cancelAnimationFrame(RC._bucle);
  RC.p = null;
  RC.el = null;
  if (!RC.raiz) return;
  RC.mano.className = 'rc-mano';
  RC.foco.style.display = 'none';
  RC.velos.forEach((x) => { x.style.display = 'none'; });
}

/* ------------------------------------------------- la fila de Ajustes
 * Al pie de «El año y la app», después de «Al abrir la app»: es de la app
 * y no de ningún libro, y quien busca cómo se usa algo mira en Ajustes. */
const _rcVerAjustes = verAjustes;
verAjustes = function () {
  _rcVerAjustes.apply(this, arguments);
  const tras = vista.querySelector('details[data-clave="abrir"]');
  if (!tras) return;
  const h = rcHechos();
  const vistos = CAPITULOS.filter((c) => h[c.id]).length;
  tras.insertAdjacentHTML('afterend', '<button type="button" '
    + 'class="ajustes-sec aj-recorrido" data-recorrido>'
    + '<span class="aj-icono">' + svg('<circle cx="12" cy="12" r="8.5"/>'
      + '<path d="m14.8 9.2-1.9 3.7-3.7 1.9 1.9-3.7z"/>') + '</span>'
    + '<span class="aj-cab"><span class="aj-t">Recorrido de la app</span>'
    + '<span class="aj-resumen">' + (vistos === 0
      ? 'Dónde está cada cosa, y los gestos, paso a paso'
      : vistos === CAPITULOS.length ? 'Visto entero · los gestos, de un vistazo'
        : vistos + ' de ' + CAPITULOS.length + ' capítulos vistos')
    + '</span></span><span class="aj-flecha" aria-hidden="true"></span>'
    + '</button>');
};

document.addEventListener('click', (ev) => {
  if (ev.target.closest('[data-recorrido]')) rcAbreIndice();
});

/* ------------------------------------------------------- la primera vez
 * Sin ningún ajuste guardado y sin haber visto nunca el recorrido es un
 * teléfono que acaba de instalar la app: se le ofrece en cuanto la portada
 * está pintada. Si abrió por otra ruta —un enlace a la misa de hoy—, se
 * espera a que llegue a la portada; si no llega, será la próxima vez. */
(function rcPrimeraVez() {
  let nuevo = false;
  try {
    nuevo = !localStorage.getItem('cfg') && !localStorage.getItem('recorrido');
  } catch (_) { return; }
  if (!nuevo) return;
  const mira = () => {
    if (RC.abierto || rcLee().visto) return;
    if (E.vista === 'portada' && vista.querySelector('.portada-elige')) {
      rcAbreIndice({ bienvenida: true });
      return;
    }
    setTimeout(mira, 400);
  };
  setTimeout(mira, 700);
})();
