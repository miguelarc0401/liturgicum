/* Service worker: lo que hace que la app abra sin conexión.
 *
 * Estrategia: caché primero, para todo. El leccionario no cambia de un día
 * para otro, así que pedir la red antes de mirar la caché sólo serviría para
 * que la app tarde cuando no hay cobertura, que es justo cuando hace falta.
 *
 * La versión de la caché la manda datos/version.js, que reescribe
 * src/15_app_data.py con una firma de los propios datos: si los datos cambian,
 * la firma cambia, y este worker tira la caché vieja y la vuelve a llenar.
 */
importScripts('datos/version.js');

const CACHE = 'leccionario-' + (self.VERSION_DATOS || 'sin-version');

/* Lo imprescindible para que la app abra y funcione entera. */
const FICHEROS = [
  './',
  'index.html',
  'estilos.css',
  'app.js',
  'manifest.webmanifest',
  'icono.svg',
  'icono-32.png',
  'icono-180.png',
  'icono-192.png',
  'icono-512.png',
  'icono-maskable-512.png',
  'datos/version.js',
  'datos/indice.json',
  'datos/calendario.json',
  'datos/lecturas_clementina.json'
];

/* Lo que pesa se guarda igual —el objetivo es poder rezar sin cobertura—
 * pero después, para que instalar la app no dependa de bajarlo todo de
 * golpe con mala conexión: la segunda versión latina son casi 6 MB, y la
 * liturgia de las horas, con sus ocho años de testigos destilados, unos 25.
 * Mientras tanto la app funciona, y las horas se cargan cuando se piden. */
const DESPUES = [
  'datos/lecturas_nova.json',
  'datos/horas_dias.json',
  'datos/horas.json'
];

async function guarda(c, ficheros) {
  // de uno en uno: si falla un fichero suelto, el resto de la app queda
  // instalada igual y el fallo se ve en la consola en vez de tumbarlo todo
  await Promise.all(ficheros.map((f) =>
    c.add(new Request(f, { cache: 'reload' }))
      .catch((e) => console.warn('sin cachear:', f, e))));
}

self.addEventListener('install', (ev) => {
  ev.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await guarda(c, FICHEROS);
    guarda(c, DESPUES);            // sin await: no retrasa la instalación
    self.skipWaiting();
  })());
});

self.addEventListener('activate', (ev) => {
  ev.waitUntil((async () => {
    for (const k of await caches.keys()) {
      if (k !== CACHE && k.startsWith('leccionario-')) await caches.delete(k);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (ev) => {
  const req = ev.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  ev.respondWith((async () => {
    const guardado = await caches.match(req, { ignoreSearch: true });
    if (guardado) return guardado;
    try {
      const red = await fetch(req);
      if (red.ok) (await caches.open(CACHE)).put(req, red.clone());
      return red;
    } catch (e) {
      // navegación sin red y sin caché: al menos que se abra la app
      if (req.mode === 'navigate') {
        const inicio = await caches.match('index.html');
        if (inicio) return inicio;
      }
      throw e;
    }
  })());
});
