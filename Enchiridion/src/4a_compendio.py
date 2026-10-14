# -*- coding: utf-8 -*-
"""Fase 4a — las oraciones comunes del Compendio del Catecismo.

La Santa Sede publica, al final del *Compendio del Catecismo de la Iglesia
Católica* (2005), un apéndice con las oraciones que todo católico sabe de
memoria, y lo publica **en dos columnas**: el castellano a la izquierda y el
latín a la derecha, oración por oración. Eso lo convierte en la fuente ideal
para el devocionario: no hay que suponer qué traducción corresponde a qué
oración latina, porque lo dice la propia página.

Son una treintena —la señal de la cruz, el Padre nuestro, el Ave María, el
Ángel de Dios, el Ángelus, la Salve, el Magníficat, el Benedictus, el Sub
tuum, el Te Deum, el Veni Creator, el Alma de Cristo, los actos de fe,
esperanza y caridad— y son justo las que más se rezan.

Lo que se guarda es el texto y de dónde sale. Son fórmulas tradicionales
—el Padre nuestro castellano no lo escribió el Compendio— y lo que la
página aporta es el testimonio de cómo las imprime hoy la Santa Sede.

    TRABAJO/compendio_ccc_sp.html  ──▶  Enchiridion/datos/compendio.json

    python Enchiridion/src/4a_compendio.py
"""

import argparse
import html
import io
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, TRABAJO

URL = ('https://www.vatican.va/archive/compendium_ccc/documents/'
       'archive_2005_compendium-ccc_sp.html')
AGENTE = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/131.0 Safari/537.36 '
          '(uso personal y de estudio; Liturgicum)')

FILA = re.compile(r'(?is)<tr[^>]*>(.*?)</tr>')
CELDA = re.compile(r'(?is)<td[^>]*>(.*?)</td>')
TITULO = re.compile(r'(?is)<b>(.*?)</b>')


def baja():
    ruta = os.path.join(TRABAJO, 'compendio_ccc_sp.html')
    if os.path.exists(ruta):
        return ruta
    os.makedirs(TRABAJO, exist_ok=True)
    pet = urllib.request.Request(URL, headers={'User-Agent': AGENTE})
    with urllib.request.urlopen(pet, timeout=60) as r:
        datos = r.read()
    with open(ruta, 'wb') as fh:
        fh.write(datos)
    return ruta


def limpia(celda):
    """(título, renglones) de una celda del apéndice."""
    tit = ''
    for m in TITULO.finditer(celda):
        t = re.sub(r'(?s)<[^>]+>', '', m.group(1))
        t = re.sub(r'\s+', ' ', html.unescape(t)).strip()
        if t:
            tit = (tit + t) if tit else t
        if tit:
            break
    cuerpo = TITULO.sub(' ', celda)
    cuerpo = re.sub(r'(?i)<br\s*/?>', '\n', cuerpo)
    cuerpo = re.sub(r'(?i)</p>|<p[^>]*>', '\n\n', cuerpo)
    cuerpo = re.sub(r'(?s)<[^>]+>', '', cuerpo)
    cuerpo = html.unescape(cuerpo).replace(' ', ' ')
    renglones = []
    for ln in cuerpo.split('\n'):
        ln = re.sub(r'[ \t]+', ' ', ln).strip()
        if ln or (renglones and renglones[-1]):
            renglones.append(ln)
    while renglones and not renglones[0]:
        renglones.pop(0)
    while renglones and not renglones[-1]:
        renglones.pop()
    return tit, renglones


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    ruta = baja()
    s = open(ruta, 'rb').read().decode('iso-8859-1')
    i = s.rfind('ORACIONES COMUNES')
    if i < 0:
        sys.exit('no encuentro el apéndice de oraciones comunes')

    oraciones = []
    for fila in FILA.findall(s[i:]):
        celdas = CELDA.findall(fila)
        if len(celdas) != 2:
            continue
        tes, es = limpia(celdas[0])
        tla, la = limpia(celdas[1])
        # detrás del apéndice hay otra tabla, de una letra por celda, que
        # no son oraciones: se exige cuerpo y título
        if len(' '.join(la)) < 40 or len(' '.join(es)) < 40:
            continue
        if not (tes or tla):
            continue
        # el título latino de la página viene a veces partido por la
        # ligadura («Ave, Marí» + «æ»), y así se vuelve a juntar
        if tla.endswith(('Marí', 'Mari')):
            tla += 'æ'
        oraciones.append({'tes': tes, 'tla': tla, 'es': es, 'la': la})

    salida = {
        'fuente': 'Compendio del Catecismo de la Iglesia Católica (2005), '
                  'apéndice «Oraciones comunes»',
        'autoridad': 'Santa Sede',
        'url': URL,
        'nota': 'La página imprime cada oración en dos columnas, el '
                'castellano enfrentado al latín: el emparejamiento es de '
                'la fuente, no de este proyecto.',
        'oraciones': oraciones,
    }
    destino = os.path.join(DATOS, 'compendio.json')
    with io.open(destino, 'w', encoding='utf-8') as fh:
        json.dump(salida, fh, ensure_ascii=False, indent=1)
    print('%d oraciones -> %s' % (len(oraciones), destino))
    for o in oraciones:
        print('  %-34s %s' % (o['tes'][:34], o['tla'][:34]))


if __name__ == '__main__':
    main()
