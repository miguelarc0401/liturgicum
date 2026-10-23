/* Service worker: lo que hace que la app abra sin conexión.
 *
 * Estrategia: caché primero, para todo. El leccionario no cambia de un día
 * para otro, así que pedir la red antes de mirar la caché sólo serviría para
 * que la app tarde cuando no hay cobertura, que es justo cuando hace falta.
 *
 * La versión de la caché la manda datos/version.js, que reescribe
 * src/15_app_data.py con una firma de los propios datos: si los datos cambian,
 * la firma cambia, y este worker llena una caché nueva.
 *
 * La vieja no se tira hasta que la nueva está entera. Antes se tiraba al
 * activarse, y lo pesado se bajaba suelto, sin que nada mantuviera vivo al
 * worker: el teléfono lo dormía a medias, y tras cada publicación la app se
 * quedaba sin la misa ni las horas hasta volver a tener red.
 */
importScripts('datos/version.js');

const CACHE = 'leccionario-' + (self.VERSION_DATOS || 'sin-version');

/* Lo imprescindible para que la app abra y funcione entera. */
const FICHEROS = [
  './',
  'index.html',
  'estilos.css',
  'app.js',
  'nativo.js',
  'manifest.webmanifest',
  'icono.svg',
  'icono-32.png',
  'icono-180.png',
  'icono-192.png',
  'datos/version.js',
  // PROVISIONAL, mientras duren las pruebas de diseño del devocionario
  'devo-pruebas.css',
  'devo-pruebas.js',
  'datos/indice.json',
  'datos/calendario.json',
  'datos/lecturas_clementina.json'
];

/* Lo que pesa se guarda igual —el objetivo es poder rezar sin cobertura—
 * pero después, para que instalar la app no dependa de bajarlo todo de
 * golpe con mala conexión: cada versión latina de más son casi 6 MB, y la
 * liturgia de las horas, con sus ocho años de testigos destilados, unos 25.
 * Mientras tanto la app funciona, y las horas se cargan cuando se piden. */
const DESPUES = [
  // los dos iconos grandes pesan 850 kB entre los dos -son una foto de la
  // tapa, con su grano, y eso no comprime-; Android se los baja el solo al
  // instalar, y aqui estan nada mas que para cuando no haya red
  'icono-512.png',
  'icono-maskable-512.png',
  'datos/lecturas_nova.json',
  'datos/lecturas_lect1977.json',
  'datos/lecturas_es.json',
  // el Misal entero: el formulario del dia (misa.json, 2,4 MB), su gemelo
  // latino, los prefacios y el Ordinario. Son 3,6 MB entre los cuatro, y la
  // misa no se arma sin los cuatro: app.js los pide juntos la primera vez
  // que se abre la vista, asi que o estan todos cacheados o no sirve ninguno
  'datos/misa.json',
  'datos/misal_latino.json',
  'datos/prefacios.json',
  'datos/ordinario.json',
  'datos/horas_dias.json',
  'datos/horas.json',
  // el devocionario: 1 MB de oraciones que no hacen falta para abrir la app
  // ni para rezar la misa ni las horas, y que la vista pide cuando se entra
  'datos/devocionario.json',
  // el motor de la voz de Piper; lo que él trae de fuera —el modelo, el
  // wasm— lo guarda él en su propia caché, que ésta no toca
  'piper.js',
  // las tres letras que la app lleva dentro, Garamond, Tinos y Alegreya:
  // 840 kB entre las dieciséis, y sin ellas, sin red, se leería con la de libro
  'fuentes/alegreya-400-900-cursiva-latin-ext.woff2',
  'fuentes/alegreya-400-900-cursiva-latin.woff2',
  'fuentes/alegreya-400-900-latin-ext.woff2',
  'fuentes/alegreya-400-900-latin.woff2',
  'fuentes/ebgaramond-400-800-cursiva-latin-ext.woff2',
  'fuentes/ebgaramond-400-800-cursiva-latin.woff2',
  'fuentes/ebgaramond-400-800-latin-ext.woff2',
  'fuentes/ebgaramond-400-800-latin.woff2',
  'fuentes/tinos-400-cursiva-latin-ext.woff2',
  'fuentes/tinos-400-cursiva-latin.woff2',
  'fuentes/tinos-400-latin-ext.woff2',
  'fuentes/tinos-400-latin.woff2',
  'fuentes/tinos-700-cursiva-latin-ext.woff2',
  'fuentes/tinos-700-cursiva-latin.woff2',
  'fuentes/tinos-700-latin-ext.woff2',
  'fuentes/tinos-700-latin.woff2'
];

/* Baja a la caché los ficheros que todavía no estén. Devuelve true si al
 * acabar no falta ninguno: un 404 cuenta como hecho —el servidor dice que
 * no existe, y esperarlo no lo hará aparecer—; un fallo de red, no. */
async function guarda(c, ficheros) {
  let entera = true;
  // de uno en uno: si falla un fichero suelto, el resto de la app queda
  // instalada igual y el fallo se ve en la consola en vez de tumbarlo todo
  await Promise.all(ficheros.map(async (f) => {
    if (await c.match(f)) return;
    try {
      const r = await fetch(new Request(f, { cache: 'reload' }));
      if (r.ok) await c.put(f, r);
      else console.warn('sin cachear:', f, r.status);
    } catch (e) {
      entera = false;
      console.warn('sin cachear:', f, e);
    }
  }));
  return entera;
}

/* Completa la caché de esta versión y, cuando está entera, tira las de
 * versiones anteriores, que hasta entonces sirven de respaldo sin red. Se
 * llama al instalar y cada vez que se abre la app, dentro de un waitUntil
 * para que el sistema no duerma al worker a mitad de la descarga; si aun así
 * se corta, la vez siguiente sigue donde lo dejó. */
let llenando = null;
function completa() {
  if (!llenando) {
    llenando = (async () => {
      const c = await caches.open(CACHE);
      if (!(await guarda(c, FICHEROS.concat(DESPUES)))) return;
      for (const k of await caches.keys()) {
        if (k !== CACHE && k.startsWith('leccionario-')) await caches.delete(k);
      }
    })().finally(() => { llenando = null; });
  }
  return llenando;
}

self.addEventListener('install', (ev) => {
  ev.waitUntil((async () => {
    await guarda(await caches.open(CACHE), FICHEROS);
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (ev) => {
  // sin esperar a completa(): mientras el worker se activa las peticiones
  // de la página esperan, y lo pesado puede tardar minutos
  ev.waitUntil(self.clients.claim());
  completa();
});

/* La página lo pide al abrir y al volver a primer plano. */
self.addEventListener('message', (ev) => {
  if (ev.data === 'completa') ev.waitUntil(completa());
});

self.addEventListener('fetch', (ev) => {
  const req = ev.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  if (req.mode === 'navigate') ev.waitUntil(completa());
  ev.respondWith((async () => {
    const c = await caches.open(CACHE);
    const guardado = await c.match(req, { ignoreSearch: true });
    if (guardado) return guardado;
    try {
      const red = await fetch(req);
      if (red.ok) c.put(req, red.clone());
      return red;
    } catch (e) {
      // sin red y sin la versión nueva: la de antes, que para rezar sirve
      const viejo = await caches.match(req, { ignoreSearch: true });
      if (viejo) return viejo;
      // navegación sin red y sin caché: al menos que se abra la app
      if (req.mode === 'navigate') {
        const inicio = await caches.match('index.html');
        if (inicio) return inicio;
      }
      throw e;
    }
  })());
});
