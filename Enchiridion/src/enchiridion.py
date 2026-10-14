# -*- coding: utf-8 -*-
"""Lo que comparten las fases del Enchiridion.

El devocionario sale de un sitio solo —el *Thesaurus Precum Latinarum* de
Michael Martin, <https://www.preces-latinae.org>—, que publica cada oración
en latín con su traducción inglesa al lado. El castellano no está ahí: hay
que buscarlo fuera, oración por oración, y de eso trata la fase 3.

Como en el Breviarium, el volcado del sitio no se versiona: son medio millar
de HTML que se vuelven a traer con una orden, y la carpeta del proyecto está
sincronizada con la nube. Con ENCHIRIDION_TRABAJO se le puede decir otro
sitio.
"""

import os
import re
import tempfile

SITIO = 'https://www.preces-latinae.org'
AVISO_DERECHOS = SITIO + '/Copyright_Notice.html'


def _trabajo():
    d = os.environ.get('ENCHIRIDION_TRABAJO')
    if d:
        return d
    base = (os.environ.get('LOCALAPPDATA')
            or os.environ.get('XDG_CACHE_HOME')
            or os.path.join(os.path.expanduser('~'), '.cache')
            or tempfile.gettempdir())
    return os.path.join(base, 'enchiridion')


TRABAJO = _trabajo()
FUENTE = os.path.join(TRABAJO, 'fuente')      # los HTML tal como se bajan

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, 'datos')


def ruta_de(url):
    """La ruta dentro de FUENTE que le toca a una URL del sitio."""
    p = re.sub(r'^https?://(www\.)?preces-latinae\.org/?', '', url)
    p = p.split('#')[0].split('?')[0]
    return os.path.join(FUENTE, *[x for x in p.split('/') if x])


def url_de(ruta):
    """La URL de la que salió un fichero del volcado."""
    rel = os.path.relpath(ruta, FUENTE).replace(os.sep, '/')
    return SITIO + '/' + rel
