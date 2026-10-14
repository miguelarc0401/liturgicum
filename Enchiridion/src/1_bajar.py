# -*- coding: utf-8 -*-
"""Fase 1 — traer el volcado de preces-latinae.org.

El sitio *es* el libro: no hay detrás ninguna base de datos ni ninguna API.
Cada oración vive en su propia página de HTML escrito a mano en 1998, con el
latín en la columna de la izquierda y el inglés en la de la derecha, y las
páginas se enlazan entre sí de tres maneras: por el índice de materias
(`preces.html`), por la página de cada categoría (`thesaurus/BVM.html`) y en
cadena, cada oración con la siguiente («Prev» / «Next»).

Por eso aquí no se parte de una lista de URL: se recorre el sitio entero
desde el índice siguiendo cuanto enlace salga, y la cadena «Next» garantiza
que no se queda fuera una oración por no estar en ningún índice. Se baja todo
el HTML y nada más —ni imágenes ni la cuenta de visitas—, tal cual viene, sin
decodificarlo: las páginas son ISO-8859-1 y de eso se encarga la fase 2.

Una recopilación anterior intentó esto con un navegador y se quedó en 178 de
las 495 páginas: el cliente bloqueaba la mayoría (ERR_BLOCKED_BY_CLIENT). Con
una petición normal el sitio responde sin problema, y de ahí este guión.

El aviso del sitio permite —y anima— el uso personal y de estudio sin ánimo
de lucro, que es el de este proyecto. Se va despacio a propósito, con una
pausa entre páginas, porque medio millar de peticiones seguidas a un sitio
personal no es uso cortés.

    python Enchiridion/src/1_bajar.py            # baja lo que falte
    python Enchiridion/src/1_bajar.py --forzar   # lo tira y lo trae de nuevo
"""

import argparse
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import FUENTE, SITIO, TRABAJO, ruta_de

# El sitio se sirve igual con y sin www; se normaliza a uno para no bajar
# cada página dos veces.
DOMINIOS = ('preces-latinae.org', 'www.preces-latinae.org')

# Un navegador cualquiera, diciendo para qué: el sitio no sirve nada a quien
# no manda User-Agent.
AGENTE = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/131.0 Safari/537.36 '
          '(uso personal y de estudio; Liturgicum)')

PAUSA = 0.5          # segundos entre páginas
REINTENTOS = 3

ARRANQUE = [SITIO + '/preces.html', SITIO + '/index.html']

ENLACE = re.compile(rb'(?is)<a\s[^>]*href\s*=\s*["\']([^"\'>]+)["\']')


def absoluta(base, href):
    """La URL absoluta de un href, o None si no es una página del sitio."""
    href = href.decode('iso-8859-1', 'replace').strip()
    href = href.split('#')[0].split('?')[0]
    if not href or href.startswith(('mailto:', 'javascript:')):
        return None
    u = urllib.parse.urljoin(base, href)
    m = re.match(r'^https?://([^/]+)(/.*)?$', u)
    if not m or m.group(1).lower() not in DOMINIOS:
        return None
    camino = m.group(2) or '/'
    if not re.search(r'\.html?$', camino, re.I):
        return None
    return SITIO + camino


def trae(url):
    """Los bytes de una página, o None si el sitio no la da."""
    for intento in range(REINTENTOS):
        try:
            pet = urllib.request.Request(url, headers={'User-Agent': AGENTE})
            with urllib.request.urlopen(pet, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            espera = 2 * (intento + 1)
        except Exception:
            espera = 2 * (intento + 1)
        if intento + 1 < REINTENTOS:
            time.sleep(espera)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--forzar', action='store_true',
                    help='borra el volcado y lo baja de nuevo')
    args = ap.parse_args()

    if args.forzar and os.path.isdir(FUENTE):
        print('borrando ' + FUENTE + '…', flush=True)
        shutil.rmtree(FUENTE)
    os.makedirs(FUENTE, exist_ok=True)

    cola = list(ARRANQUE)
    vistas = set(cola)
    bajadas, cacheadas, fallos = 0, 0, []

    while cola:
        url = cola.pop(0)
        destino = ruta_de(url)
        crudo = None
        if os.path.exists(destino) and not args.forzar:
            with open(destino, 'rb') as fh:
                crudo = fh.read()
            cacheadas += 1
        else:
            crudo = trae(url)
            if crudo is None:
                fallos.append(url)
                print('  !  ' + url, flush=True)
                continue
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, 'wb') as fh:
                fh.write(crudo)
            bajadas += 1
            if bajadas % 25 == 0:
                print('  %d bajadas, %d en cola' % (bajadas, len(cola)),
                      flush=True)
            time.sleep(PAUSA)

        for href in ENLACE.findall(crudo):
            u = absoluta(url, href)
            if u and u not in vistas:
                vistas.add(u)
                cola.append(u)

    informe = os.path.join(TRABAJO, 'bajar_qa.txt')
    with open(informe, 'w', encoding='utf-8') as fh:
        fh.write('paginas vistas:    %d\n' % len(vistas))
        fh.write('paginas bajadas:   %d\n' % bajadas)
        fh.write('ya estaban:        %d\n' % cacheadas)
        fh.write('no las dio:        %d\n' % len(fallos))
        for u in sorted(fallos):
            fh.write('  ' + u + '\n')

    print('\n%d páginas en %s' % (len(vistas) - len(fallos), FUENTE))
    print('%d bajadas ahora, %d ya estaban, %d sin respuesta'
          % (bajadas, cacheadas, len(fallos)))
    print('informe: ' + informe)


if __name__ == '__main__':
    main()
