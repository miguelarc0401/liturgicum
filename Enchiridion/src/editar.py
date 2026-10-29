# -*- coding: utf-8 -*-
"""El editor del devocionario: la app, servida en este ordenador, con
permiso para decidir qué oraciones se quedan en el libro.

    python Enchiridion/src/editar.py            # abre http://127.0.0.1:8780/#/oraciones

La app publicada es estática —GitHub Pages y el APK—, y desde ahí no se
puede escribir en el repositorio. Aquí sí: este servidor sirve `app/` como
cualquier otro y además contesta a cinco órdenes, que la app sólo descubre
cuando la abre él (en la portada del devocionario aparece la caja del
editor):

    estado     lo quitado y lo agregado hasta ahora
    quitar     una oración sale del libro
    devolver   una quitada vuelve
    guardar    una oración nueva, o una nueva corregida
    borrar     una nueva desaparece del todo

Cada orden escribe `Enchiridion/datos/seleccion.json` y vuelve a correr la
fase 5, que es la que lo aplica: `app/datos/devocionario.json` sale ya sin
las quitadas y con las nuevas, y lo que cambia lo ven todos cuando se
publica con `.\\publicar.ps1`. Si la fase 5 falla, el fichero vuelve a como
estaba y la app dice por qué.

Sólo escucha en 127.0.0.1, y las órdenes sólo se aceptan de la propia app
—mismo origen y cuerpo JSON—, para que una página cualquiera abierta en el
navegador no pueda mandarlas. No lleva service worker: el que se sirve se
borra a sí mismo, para que lo que se ve sea siempre lo último que se ha
escrito y no lo que quedó en la caché.
"""

import argparse
import datetime
import http.server
import importlib.util
import io
import json
import os
import subprocess
import sys
import threading
import uuid
import webbrowser

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from enchiridion import DATOS, TRABAJO  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(AQUI))
APP = os.path.join(RAIZ, 'app')
FASE5 = os.path.join(AQUI, '5_app.py')
SELECCION = os.path.join(DATOS, 'seleccion.json')
QUITADAS = os.path.join(TRABAJO, 'devocionario_quitadas.json')
PUBLICADO = os.path.join(APP, 'datos', 'devocionario.json')

NOTA = ('Lo que el editor del devocionario ha decidido: las oraciones que '
        'quitó, por su id, y las que agregó, con su texto. Lo escribe '
        'Enchiridion/src/editar.py y lo aplica la fase 5.')

# lo que se puede elegir al agregar: los capítulos y las formas son los de
# la fase 5, que es la que los entiende
_spec = importlib.util.spec_from_file_location('fase5', FASE5)
_fase5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fase5)
CAPITULOS = [c[0] for c in _fase5.CAPITULOS]
FORMAS = [f for _, fs in _fase5.FAMILIAS for f in fs]

MAX_TEXTO = 30000
MAX_TITULO = 240

# la app hace una cosa cada vez; dos órdenes seguidas no se pisan
CERROJO = threading.Lock()

SIN_SW = (
    '// El editor no lleva service worker: lo que se ve ha de ser siempre lo\n'
    '// último que se ha escrito. Éste se borra a sí mismo y a su caché.\n'
    "self.addEventListener('install', () => self.skipWaiting());\n"
    "self.addEventListener('activate', (ev) => ev.waitUntil((async () => {\n"
    '  for (const k of await caches.keys()) await caches.delete(k);\n'
    '  await self.registration.unregister();\n'
    '})()));\n')


class Fallo(Exception):
    """Lo que no se puede hacer, dicho para quien lo pidió."""


def hoy():
    return datetime.date.today().isoformat()


def lee_seleccion():
    if not os.path.exists(SELECCION):
        return {'nota': NOTA, 'quitadas': {}, 'nuevas': []}
    with io.open(SELECCION, encoding='utf-8') as fh:
        s = json.load(fh)
    return {'nota': NOTA, 'quitadas': s.get('quitadas') or {},
            'nuevas': s.get('nuevas') or []}


def escribe_seleccion(s):
    with io.open(SELECCION, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(s, fh, ensure_ascii=False, indent=1)
        fh.write('\n')


def publicadas():
    """Las piezas que el devocionario tiene ahora, por su id."""
    with io.open(PUBLICADO, encoding='utf-8') as fh:
        return {p['id']: p for p in json.load(fh)['piezas']}


def estado():
    quitadas = []
    if os.path.exists(QUITADAS):
        with io.open(QUITADAS, encoding='utf-8') as fh:
            quitadas = json.load(fh).get('piezas', [])
    s = lee_seleccion()
    return {'editor': 'enchiridion', 'quitadas': quitadas,
            'nuevas': s['nuevas'],
            'fichero': os.path.relpath(SELECCION, RAIZ).replace(os.sep, '/')}


def aplica(cambia):
    """Cambia la selección y rehace el devocionario. Si la fase 5 falla, la
    selección vuelve a como estaba: lo que la app enseña y lo que dice el
    fichero no se separan nunca."""
    with CERROJO:
        antes = None
        if os.path.exists(SELECCION):
            with io.open(SELECCION, encoding='utf-8') as fh:
                antes = fh.read()
        s = lee_seleccion()
        dicho = cambia(s)
        escribe_seleccion(s)
        r = subprocess.run([sys.executable, FASE5], cwd=RAIZ,
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        if r.returncode != 0:
            if antes is None:
                os.remove(SELECCION)
            else:
                with io.open(SELECCION, 'w', encoding='utf-8',
                             newline='\n') as fh:
                    fh.write(antes)
            cola = (r.stderr or r.stdout or '').strip().splitlines()[-6:]
            raise Fallo('La fase 5 ha fallado y no se ha cambiado nada:\n'
                        + '\n'.join(cola))
        print('  ' + dicho)
        return estado()


# ----------------------------------------------------------- las órdenes
def quitar(datos):
    pid = str(datos.get('id') or '')

    def cambia(s):
        nueva = next((n for n in s['nuevas'] if n['id'] == pid), None)
        p = nueva or publicadas().get(pid)
        if not p:
            raise Fallo('Esa oración no está en el devocionario.')
        s['quitadas'][pid] = {
            'tla': p.get('tla') or '', 'tes': p.get('tes') or '',
            'src': p.get('src') or 'editor', 'fecha': hoy()}
        return 'quitada: ' + (p.get('tla') or p.get('tes') or pid)
    return aplica(cambia)


def devolver(datos):
    pid = str(datos.get('id') or '')

    def cambia(s):
        q = s['quitadas'].pop(pid, None)
        if q is None:
            raise Fallo('Esa oración no estaba quitada.')
        return 'devuelta: ' + (q.get('tla') or q.get('tes') or pid)
    return aplica(cambia)


def _texto(datos, k, maximo):
    v = datos.get(k)
    v = v.strip() if isinstance(v, str) else ''
    if len(v) > maximo:
        raise Fallo('«%s» es demasiado largo.' % k)
    return v


def guardar(datos):
    p = datos.get('pieza') or {}
    c = p.get('c')
    if c not in CAPITULOS:
        raise Fallo('Hay que elegir el capítulo.')
    f = p.get('f') or 'oración'
    if f not in FORMAS:
        raise Fallo('Esa forma no la conoce el devocionario: %s.' % f)
    limpia = {
        'c': c,
        's': _texto(p, 's', MAX_TITULO),
        'f': f,
        'tla': _texto(p, 'tla', MAX_TITULO),
        'la': _texto(p, 'la', MAX_TEXTO),
        'fla': _texto(p, 'fla', MAX_TITULO),
        'tes': _texto(p, 'tes', MAX_TITULO),
        'es': _texto(p, 'es', MAX_TEXTO),
        'fes': _texto(p, 'fes', MAX_TITULO),
        'url': _texto(p, 'url', MAX_TITULO),
        'oficial': bool(p.get('oficial')),
    }
    if not limpia['la'] and not limpia['es']:
        raise Fallo('Falta el texto de la oración, en latín o en castellano.')
    if limpia['la'] and not limpia['tla']:
        raise Fallo('La oración en latín necesita su título latino.')
    if limpia['url'] and not limpia['url'].startswith(('http://', 'https://')):
        raise Fallo('El enlace ha de empezar por http:// o https://.')
    pid = str(p.get('id') or '')
    hecho = {}

    def cambia(s):
        vieja = next((n for n in s['nuevas'] if n['id'] == pid), None)
        if pid and not vieja:
            raise Fallo('Esa oración nueva ya no está.')
        if vieja:
            vieja.update(limpia)
            vieja['cambio'] = hoy()
            hecho['id'] = pid
            return 'corregida: ' + (limpia['tla'] or limpia['tes'] or pid)
        nuevo = 'nv_' + uuid.uuid4().hex[:12]
        s['nuevas'].append(dict({'id': nuevo, 'fecha': hoy()}, **limpia))
        hecho['id'] = nuevo
        return 'agregada: ' + (limpia['tla'] or limpia['tes'])
    est = aplica(cambia)
    return {'id': hecho['id'], 'estado': est}


def borrar(datos):
    pid = str(datos.get('id') or '')

    def cambia(s):
        vieja = next((n for n in s['nuevas'] if n['id'] == pid), None)
        if not vieja:
            raise Fallo('Sólo se borran del todo las oraciones agregadas aquí.')
        s['nuevas'].remove(vieja)
        s['quitadas'].pop(pid, None)
        return 'borrada: ' + (vieja.get('tla') or vieja.get('tes') or pid)
    return aplica(cambia)


ORDENES = {
    'estado': lambda datos: estado(),
    'quitar': quitar,
    'devolver': devolver,
    'guardar': guardar,
    'borrar': borrar,
}


# ------------------------------------------------------------ el servidor
class Editor(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *a, **k):
        super().__init__(*a, directory=APP, **k)

    def end_headers(self):
        # nada de caché: tras cada cambio la app vuelve a pedir el
        # devocionario y ha de llegarle el que se acaba de escribir
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        pass                      # se dice lo que se cambia, no cada fichero

    def _de_aqui(self):
        """La petición viene de la app de este servidor, no de otra página:
        el Host es el nuestro y el Origin, si lo trae, también."""
        host = self.headers.get('Host', '')
        nuestro = {'127.0.0.1:%d' % self.server.server_port,
                   'localhost:%d' % self.server.server_port}
        if host not in nuestro:
            return False
        origen = self.headers.get('Origin')
        return origen is None or origen in {'http://' + h for h in nuestro}

    def _responde(self, codigo, cuerpo):
        datos = json.dumps(cuerpo, ensure_ascii=False).encode('utf-8')
        self.send_response(codigo)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        if not self._de_aqui():
            self.send_error(403)
            return
        if self.path.split('?')[0] == '/sw.js':
            datos = SIN_SW.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/javascript; charset=utf-8')
            self.send_header('Content-Length', str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)
            return
        super().do_GET()

    def do_POST(self):
        orden = self.path.split('?')[0]
        if not orden.startswith('/__editor/') or not self._de_aqui():
            self.send_error(403)
            return
        hace = ORDENES.get(orden[len('/__editor/'):])
        if not hace:
            self.send_error(404)
            return
        if not self.headers.get('Content-Type', '').startswith(
                'application/json'):
            self.send_error(415)
            return
        try:
            largo = int(self.headers.get('Content-Length') or 0)
            datos = json.loads(self.rfile.read(largo) or b'{}')
            if not isinstance(datos, dict):
                raise ValueError
        except ValueError:
            self._responde(400, {'ok': False, 'error': 'Petición mal hecha.'})
            return
        try:
            r = hace(datos)
        except Fallo as e:
            self._responde(400, {'ok': False, 'error': str(e)})
            return
        except Exception as e:      # noqa: BLE001 — se dice y se sigue
            print('  ¡error!: %r' % e)
            self._responde(500, {'ok': False, 'error': repr(e)})
            return
        if 'estado' in r:
            self._responde(200, dict(r, ok=True))
        else:
            self._responde(200, {'ok': True, 'estado': r})


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--puerto', type=int, default=8780)
    ap.add_argument('--sin-abrir', action='store_true',
                    help='no abre el navegador')
    a = ap.parse_args()
    # la consola de Windows no sabe escribir «Caritátis» con todas sus letras
    sys.stdout.reconfigure(errors='replace')
    if not os.path.exists(os.path.join(TRABAJO, 'piezas_ecl.json')):
        sys.exit('Falta la carpeta de trabajo del Enchiridion (%s): corre '
                 'antes las fases 1 a 3, como dice Enchiridion/LEEME.md.'
                 % TRABAJO)
    # que las quitadas estén escritas aunque nadie haya corrido la fase 5
    if not os.path.exists(QUITADAS):
        subprocess.run([sys.executable, FASE5], cwd=RAIZ, check=True,
                       capture_output=True)
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', a.puerto), Editor)
    url = 'http://127.0.0.1:%d/#/oraciones' % a.puerto
    print('El editor del devocionario, en ' + url)
    print('Lo que se cambie va a ' + os.path.relpath(SELECCION, RAIZ))
    print('Para pararlo, Ctrl+C.')
    if not a.sin_abrir:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == '__main__':
    main()
