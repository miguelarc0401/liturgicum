# -*- coding: utf-8 -*-
"""Fase 1 — traer el volcado de liturgiadelashoras.github.io.

La traducción litúrgica en uso en México la publica día a día el sitio
<https://liturgiadelashoras.github.io>. No hay detrás ninguna base de
datos ni ninguna API: el sitio *es* el archivo. Su repositorio guarda, en
`sync/AAAA/mes/dd/`, un HTML por hora —oficio, laudes, tercia, sexta,
nona, vísperas, completas— y un `index.htm` que dice qué día litúrgico es
y de dónde se toma el oficio. Unos 29 000 ficheros, de 2019 a hoy.

Eso es lo que se baja aquí, tal cual, a una carpeta de trabajo fuera del
proyecto (la dice `breviario.TRABAJO`), porque se vuelve a traer con esta
orden y no se versiona.

    python Breviarium/src/1_bajar.py            # baja o actualiza
    python Breviarium/src/1_bajar.py --forzar   # lo tira y lo vuelve a traer
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

ORIGEN = 'https://github.com/liturgiadelashoras/liturgiadelashoras.github.io.git'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from breviario import FUENTE as DESTINO


def corre(orden, cwd=None):
    print('  $ ' + ' '.join(orden), flush=True)
    r = subprocess.run(orden, cwd=cwd)
    if r.returncode:
        sys.exit(f'falló: {" ".join(orden)}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--forzar', action='store_true',
                    help='borra lo que haya y lo baja de nuevo')
    args = ap.parse_args()

    if args.forzar and os.path.isdir(DESTINO):
        print(f'borrando {DESTINO}…', flush=True)
        shutil.rmtree(DESTINO)

    if os.path.isdir(DESTINO) and os.listdir(DESTINO):
        print(f'ya está en {DESTINO}; con --forzar se vuelve a traer.')
        return

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='breviarium-')
    clon = os.path.join(tmp, 'sitio')
    try:
        print('clonando el sitio (son 29 000 ficheros, tarda)…', flush=True)
        corre(['git', 'clone', '--depth', '1', ORIGEN, clon])

        sync = os.path.join(clon, 'sync')
        if not os.path.isdir(sync):
            sys.exit('el clon no trae sync/: ¿cambió el sitio de sitio?')

        os.makedirs(DESTINO, exist_ok=True)
        anios = sorted(d for d in os.listdir(sync)
                       if d.isdigit() and os.path.isdir(os.path.join(sync, d)))
        for a in anios:
            print(f'  {a}…', flush=True)
            shutil.copytree(os.path.join(sync, a),
                            os.path.join(DESTINO, a), dirs_exist_ok=True)
        print(f'\n{len(anios)} años en {DESTINO}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
