# -*- coding: utf-8 -*-
"""Lo común a las seis fases del Missale.

Tres fuentes y un solo criterio: **se parsea por rótulo, no por posición**.
El Misal latino rotula sus piezas (`Collecta`, `Super oblata`), el Ordinario
castellano numera sus rúbricas (1-146, las mismas que el latino), y los
misalitos titulan sus bloques (`ORACIÓN COLECTA`). En los tres casos la
etiqueta es literal y se cuenta, así que no hace falta adivinar dónde empieza
una pieza: hace falta reconocer su nombre.

Aquí viven: dónde se trabaja, la extracción de los PDF, la limpieza de lo
marginal y la forma canónica con que se cotejan dos textos.
"""

import math
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MISSALE = os.path.join(RAIZ, 'Missale')
DATOS = os.path.join(MISSALE, 'datos')
LIBRO = os.path.join(DATOS, 'libro')


# --- dónde se trabaja -----------------------------------------------------
# Los cien misalitos y los dos misales pesan 364 MB y su volcado en texto
# otros tantos. Ni una cosa ni la otra se versionan —se rehacen con una
# orden—, y la carpeta del proyecto está sincronizada con la nube: dejar ahí
# el volcado hace que cada pasada compita con la subida de la anterior, que
# es lo que ya se midió en el Breviarium. Con MISSALE_TRABAJO se le dice
# otro sitio.

def _trabajo():
    d = os.environ.get('MISSALE_TRABAJO')
    if d:
        return d
    base = (os.environ.get('LOCALAPPDATA')
            or os.environ.get('XDG_CACHE_HOME')
            or os.path.join(os.path.expanduser('~'), '.cache')
            or tempfile.gettempdir())
    return os.path.join(base, 'missale')


TRABAJO = _trabajo()
TEXTOS = os.path.join(TRABAJO, 'txt')


# La consola de Windows viene en cp1252 y el latín del Misal no cabe ahí.
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass


# --------------------------------------------------------------------------
# del PDF al texto
# --------------------------------------------------------------------------

def texto_de(pdf, nombre=None, layout=True):
    """El PDF en texto, una lista de líneas.

    Con `-layout`, que es lo que conserva los versos de las antífonas en su
    línea y la sangría de las rúbricas. Se extrae una vez y se guarda en la
    carpeta de trabajo; si el PDF es más nuevo que el volcado, se rehace.
    """
    os.makedirs(TEXTOS, exist_ok=True)
    nombre = nombre or os.path.splitext(os.path.basename(pdf))[0]
    destino = os.path.join(TEXTOS, nombre + '.txt')
    if (not os.path.exists(destino)
            or os.path.getmtime(destino) < os.path.getmtime(pdf)):
        orden = ['pdftotext', '-enc', 'UTF-8']
        if layout:
            orden.append('-layout')
        print(f'  pdftotext {nombre}…', flush=True)
        r = subprocess.run(orden + [pdf, destino])
        if r.returncode:
            sys.exit(f'pdftotext falló con {pdf}')
    with open(destino, encoding='utf-8') as f:
        return f.read().split('\n')


# --------------------------------------------------------------------------
# lo marginal
# --------------------------------------------------------------------------

# El encabezado de página repite el rótulo de la sección y añade el número:
# «HEBDOMADA II ADVENTUS 133», «ORDO MISSÆ 512». Son cuarenta en el Misal
# latino, y no son texto del libro.
ENCABEZADO = re.compile(r'^[^a-zàáâäèéêëìíîïòóôöùúûü]{4,}\s+(\d{1,4})\s*$')

# La nota al pie va numerada y empieza por la llamada: «57 Cf. Tertullianus…».
NOTA = re.compile(r'^\d{1,3}\s+(Cf\.|Cfr\.|Ibid|Vide|S\.|Conc\.|Const\.)')


def es_encabezado(linea):
    m = ENCABEZADO.match(linea)
    return m is not None


def pagina_de(linea):
    """El número de página si la línea es un encabezado; si no, None."""
    m = ENCABEZADO.match(linea)
    return int(m.group(1)) if m else None


def es_nota(linea):
    return bool(NOTA.match(linea))


def paginas_de(lineas):
    """La página física del PDF de cada línea, contando saltos de página.

    El Misal latino sólo imprime cuarenta encabezados de página en su capa de
    texto, así que la paginación del libro no se puede seguir por ahí. La
    física sí: el salto de página va en la línea, y con ella se puede abrir el
    PDF por donde el informe diga.
    """
    pags, p = [], 1
    for ln in lineas:
        pags.append(p)
        p += ln.count('\f')
    return pags


# --- las rúbricas espaciadas letra a letra --------------------------------
# Unas setenta rúbricas del Misal van «t r a c k e a d a s»: el PDF mete un
# espacio de verdad entre cada letra y los de palabra se pierden —medido en
# la geometría del fichero: todos los espacios valen 3.03, y los huecos entre
# letras, cero—. Ni pdftotext ni PyMuPDF pueden deshacerlo, porque la
# información no está.
#
# Lo que sí está es el resto del libro: 1.3 MB de latín de donde sale un
# vocabulario con su frecuencia. Con él la segmentación es un camino mínimo
# —el de Norvig: una palabra desconocida cuesta tanto más cuanto más larga—,
# y lo que no cuadre se escribe en el informe con las dos formas, la cruda y
# la segmentada, para que se arregle a mano y no para que pase por buena.

_PREFIJO_NUM = re.compile(r'^\s*(?:\d{1,3}\.\s+)?')


def es_suelta(linea):
    """Verdadero si la línea viene espaciada letra a letra."""
    trozos = [t for t in _PREFIJO_NUM.sub('', linea.strip()).split(' ') if t]
    if len(trozos) < 10:
        return False
    sueltos = sum(1 for t in trozos if len(t) == 1)
    return sueltos >= 10 and sueltos / len(trozos) >= 0.8


class Segmentador:
    """Recompone las palabras de una línea espaciada letra a letra.

    El vocabulario se saca de las líneas que **no** vienen espaciadas, así
    que no hay diccionario externo que mantener: el libro se explica solo.
    """

    PEAJE = 2.0        # lo que cuesta abrir palabra
    LARGO = 22         # la palabra latina más larga que se intenta

    def __init__(self, lineas, extra=()):
        self.voc = Counter()
        for ln in lineas:
            if es_suelta(ln):
                continue
            for w in re.findall(r'[A-Za-zÀ-ÿÆæŒœǼǽ]+', ln):
                self.voc[w.lower()] += 1
        for w in extra:
            self.voc[w.lower()] += 1
        self.n = sum(self.voc.values()) or 1
        self._ln = math.log(self.n)
        self._diez = math.log(10)

    def _coste(self, w):
        f = self.voc.get(w.lower())
        if f:
            return self.PEAJE - math.log(f / self.n)
        # desconocida: 10 / (N · 10^largo), que es caro y crece con el largo
        return self.PEAJE + self._ln + len(w) * self._diez

    def conocida(self, w):
        return w.lower() in self.voc

    def parte(self, cadena):
        """La cadena sin espacios → l