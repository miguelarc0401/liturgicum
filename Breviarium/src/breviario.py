# -*- coding: utf-8 -*-
"""Lectura de los ficheros de liturgiadelashoras.github.io.

Los ficheros son HTML de los años noventa: no hay clases ni etiquetas
semánticas, sólo `<FONT COLOR>` y `<BR>`. Pero son de una regularidad
absoluta, y en esa regularidad está toda la información:

  · rojo  (#FF0000)  → rúbrica: rótulos de sección, «V.», «R.», «Ant.»,
                       los títulos de los salmos, las indicaciones.
  · negro (#000000)  → el texto que se reza.
  · pardo (#9E5806)  → en el índice del día, la celebración del santoral.
  · `<BR>`           → salto de línea; dos seguidos, cambio de párrafo.

De ahí que todo lo que sigue trabaje con *líneas de tiradas*: cada línea
es una lista de tiradas `(rojo, texto)`, de modo que no se pierde qué
parte de un verso es rúbrica y qué parte es oración.
"""

import os
import re
import tempfile
import unicodedata
from bs4 import BeautifulSoup, NavigableString, Tag


# --- dónde se trabaja -----------------------------------------------------
# El volcado son 29 000 ficheros y el corpus que sale de ellos pesa 200 MB,
# y ni una cosa ni la otra se versionan: se rehacen con una orden. Por eso
# no viven dentro de la carpeta del proyecto. Si estuvieran, y la carpeta
# está sincronizada con la nube —que es el caso—, cada pasada dispara una
# subida de cientos de megas que compite por el disco con la pasada
# siguiente: medido, multiplica por quince lo que tarda la extracción.
#
# Con BREVIARIUM_TRABAJO se le puede decir otro sitio.

def _trabajo():
    d = os.environ.get('BREVIARIUM_TRABAJO')
    if d:
        return d
    base = (os.environ.get('LOCALAPPDATA')
            or os.environ.get('XDG_CACHE_HOME')
            or os.path.join(os.path.expanduser('~'), '.cache')
            or tempfile.gettempdir())
    return os.path.join(base, 'breviarium')


TRABAJO = _trabajo()
FUENTE = os.path.join(TRABAJO, 'fuente')     # los HTML tal como se bajan
CORPUS = os.path.join(TRABAJO, 'dias')       # un día armado, por año

# --- colores del original -------------------------------------------------

ROJO = {'#FF0000', '#F00', 'RED'}
PARDO = {'#9E5806'}

# --- las ocho horas, en el orden en que se rezan --------------------------

HORAS = [
    ('oficio',    'Oficio de Lectura'),
    ('laudes',    'Laudes'),
    ('tercia',    'Tercia'),
    ('sexta',     'Sexta'),
    ('nona',      'Nona'),
    ('visperas',  'Vísperas'),
    ('completas', 'Completas'),
]

MESES = {
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12,
}


# --------------------------------------------------------------------------
# lectura del HTML
# --------------------------------------------------------------------------

def _texto_plano(cadena):
    cadena = cadena.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', cadena)


def lineas_de(ruta):
    """El fichero, hecho lista de líneas; cada línea, lista de `(color, texto)`.

    El color se devuelve tal cual viene del original, para que quien lea
    distinga la rúbrica roja del pardo con que se anuncia la celebración.
    """
    with open(ruta, 'rb') as f:
        html = f.read().decode('iso-8859-1', errors='replace')

    sopa = BeautifulSoup(html, 'html.parser')
    cuerpo = sopa.find(id='cuerpo') or sopa.body
    if cuerpo is None:
        return []

    lineas, actual, pila = [], [], ['#000000']

    def empuja(txt):
        if not txt:
            return
        c = pila[-1].upper()
        if actual and actual[-1][0] == c:
            actual[-1] = (c, actual[-1][1] + txt)
        else:
            actual.append((c, txt))

    def corta():
        lineas.append(list(actual))
        actual.clear()

    def anda(nodo):
        for hijo in nodo.children:
            if isinstance(hijo, NavigableString):
                empuja(str(hijo))
            elif isinstance(hijo, Tag):
                n = hijo.name.lower()
                if n == 'br':
                    corta()
                elif n in ('script', 'style'):
                    continue
                elif n == 'font':
                    pila.append(hijo.get('color') or pila[-1])
                    anda(hijo)
                    pila.pop()
                elif n in ('p', 'div', 'center', 'table', 'tr'):
                    anda(hijo)
                    if n in ('p', 'tr'):
                        corta()
                else:
                    anda(hijo)

    anda(cuerpo)
    corta()

    # limpieza: espacios normalizados, tiradas vacías fuera
    limpias = []
    for ln in lineas:
        t = [(c, _texto_plano(s)) for c, s in ln]
        t = [(c, s) for c, s in t if s.strip()]
        if t:
            t[0] = (t[0][0], t[0][1].lstrip())
            t[-1] = (t[-1][0], t[-1][1].rstrip())
            t = [(c, s) for c, s in t if s]
        limpias.append(t)
    return limpias


def plano(linea):
    """El texto de una línea, sin distinguir rúbrica de oración."""
    return ''.join(s for _, s in linea).strip()


def es_roja(color):
    return color.upper() in ROJO


def es_rubrica(linea):
    """Verdadero si la línea entera va en rojo (un rótulo, una indicación)."""
    return bool(linea) and all(es_roja(c) for c, _ in linea)


def pardo_de(linea):
    """El texto en pardo de una línea: con el que se anuncia la celebración."""
    return ''.join(s for c, s in linea if c.upper() in PARDO).strip()


# --------------------------------------------------------------------------
# cotejo de textos
# --------------------------------------------------------------------------

def clave(texto):
    """Forma canónica de un texto, para compararlo con otro.

    Quita tildes, signos y mayúsculas: lo que queda son las letras. Dos
    textos con la misma clave son el mismo texto aunque uno escriba
    «Ant 1.» y el otro «Ant. 1» o le falte un acento.
    """
    t = unicodedata.normalize('NFKD', texto.lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r'[^a-z0-9ñ ]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def clave_de_lineas(lineas):
    """La clave de un bloque entero de líneas."""
    return clave(' '.join(plano(ln) for ln in lineas if plano(ln)))
