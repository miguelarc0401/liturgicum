# -*- coding: utf-8 -*-
"""Fase 4b — el castellano que hay que ir a buscar fuera.

Lo que no está ni en los libros de la app ni en el apéndice del Compendio
hay que buscarlo oración por oración. Esta fase no inventa nada: cada
entrada de la tabla dice **de qué página sale el texto y qué trozo de ella
es la oración**, y el guión lo baja y lo recorta. Así el texto es el de la
fuente, letra por letra, y se puede volver a comprobar corriendo la orden.

El orden de preferencia de las fuentes es el de la cascada de la fase 4: la
Santa Sede y los episcopados antes que nadie, y después instituciones
eclesiásticas que publiquen el texto tradicional con su nombre. De cada una
se guarda la autoridad, el territorio y si es traducción aprobada o sólo
publicación: no es lo mismo, y la app lo dice en la ficha de la oración.

    datos/castellano_mano.json   ◀── las páginas de la tabla
    TRABAJO/fuentes/             el HTML bajado, que no se versiona

    python Enchiridion/src/4b_fuentes.py            # lo que falte
    python Enchiridion/src/4b_fuentes.py --forzar   # vuelve a bajarlo todo
"""

import argparse
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, TRABAJO

AGENTE = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/131.0 Safari/537.36 '
          '(uso personal y de estudio; Liturgicum)')

SANTA_SEDE = 'Santa Sede'
EWTN = 'EWTN (Eternal Word Television Network)'
OBRA_EWTN = 'Biblioteca de devociones de EWTN en español'
# El pie de las páginas de EWTN empieza siempre por la misma cita, y ahí
# se acaba la oración.
FIN_EWTN = r'^(No puedo llevar a Cristo|Sitios de noticias EWTN)'

# ---------------------------------------------------------------- la tabla
# pieza   la clave de la pieza en el devocionario (página#orden)
# desde   el renglón en que empieza la oración (regex), inclusive
# hasta   el renglón en que acaba (regex), exclusive; None = hasta el final
# oficial si es traducción litúrgica aprobada; publicar no es aprobar
FUENTES = [
    {
        'pieza': 'BVM/Laurentanae.html#0',
        'tes': 'Letanías de la Virgen',
        'url': 'https://www.vatican.va/special/rosary/documents/'
               'litanie-lauretane_sp.html',
        'desde': r'^Señor, ten piedad$',
        'hasta': None,
        'paso': 3,
        'autoridad': SANTA_SEDE,
        'obra': 'El Santo Rosario — Letanías de la Virgen, en el sitio de '
                'la Santa Sede',
        'territorio': 'universal',
        'oficial': True,
        'nota': 'La Santa Sede publica estas letanías con las tres '
                'invocaciones que añadió el papa Francisco en 2020 —Madre '
                'de la misericordia, Madre de la esperanza y Consuelo de '
                'los migrantes—, que son las mismas que trae el latín de '
                'al lado. El latín añade además las oraciones propias de '
                'Adviento, Navidad y Pascua, que esta página no tiene.',
    },
    {
        'pieza': 'Angeli/SancteMichael.html#0',
        'tes': 'Oración a san Miguel Arcángel',
        'url': 'https://www.ewtn.com/es/catolicismo/devociones/'
               'san-miguel-arcangel-15155',
        'desde': r'^San Miguel Arcángel,$',
        'hasta': r'^\(Aunque no es obligación',
        'paso': 4, 'autoridad': EWTN, 'obra': OBRA_EWTN,
        'territorio': None, 'oficial': False,
        'nota': 'Es la oración que mandó rezar León XIII después de la '
                'misa; el castellano es el tradicional, publicado por una '
                'institución católica, no una traducción litúrgica '
                'aprobada.',
    },
    {
        'pieza': 'Filius/LitSCI.html#0',
        'tes': 'Letanías del Sagrado Corazón de Jesús',
        'url': 'https://www.ewtn.com/es/catolicismo/devociones/'
               'letanias-del-sagrado-corazon-de-jesus-15239',
        'desde': r'^Señor, misericordia\.$',
        'hasta': FIN_EWTN,
        'paso': 4, 'autoridad': EWTN, 'obra': OBRA_EWTN,
        'territorio': None, 'oficial': False,
    },
    {
        'pieza': 'Euch/Tantum.html#0',
        'tes': 'Veneremos, pues, postrados',
        'url': 'https://www.ewtn.com/es/catolicismo/devociones/'
               'himno-pange-lingua-15208',
        'desde': r'^Veneremos, pues postrados$',
        'hasta': FIN_EWTN,
        'paso': 4, 'autoridad': EWTN, 'obra': OBRA_EWTN,
        'territorio': None, 'oficial': False,
        'nota': 'El Tantum ergo son las dos últimas estrofas del Pange '
                'lingua, y de ahí salen: la página las imprime dentro del '
                'himno.',
    },
    {
        'pieza': 'PostMissam/Thomae.html#0',
        'tes': 'Acción de gracias de santo Tomás de Aquino',
        'url': 'https://www.ewtn.com/es/catolicismo/devociones/'
               'oracion-de-accion-de-gracias-de-sto-tomas-de-aquino-15775',
        'desde': r'^Gracias te doy Señor Padre',
        'hasta': FIN_EWTN,
        'paso': 4, 'autoridad': EWTN, 'obra': OBRA_EWTN,
        'territorio': None, 'oficial': False,
    },
    {
        'pieza': 'Ioseph/AdTe.html#0',
        'tes': 'A vos, bienaventurado san José',
        'url': 'https://www.ewtn.com/es/catolicismo/devociones/'
               'san-jose-oracion-del-papa-leon-xiii-15189',
        'desde': r'^A vos, bienaventurado San José',
        'hasta': r'^Al Glorioso Patriarca San José$',
        'paso': 4, 'autoridad': EWTN, 'obra': OBRA_EWTN,
        'territorio': None, 'oficial': False,
        'nota': 'La oración que León XIII mandó añadir al rosario de '
                'octubre.',
    },
    {
        'pieza': 'Hymni/CorpusChristi/AdoroTe.html#0',
        'tes': 'Te adoro con devoción',
        'url': 'https://www.ewtn.com/es/catolicismo/devociones/'
               'adoro-te-devote-15773',
        'desde': r'^Te adoro con devoción',
        'hasta': FIN_EWTN,
        'paso': 4, 'autoridad': EWTN, 'obra': OBRA_EWTN,
        'territorio': None, 'oficial': False,
        'nota': 'Es traducción en prosa: el himno de santo Tomás va en '
                'verso, y aquí cada estrofa es un párrafo.',
    },
]


def baja(url, forzar=False):
    """El HTML de una página, cacheado en la carpeta de trabajo."""
    carpeta = os.path.join(TRABAJO, 'fuentes')
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta,
                        hashlib.sha256(url.encode()).hexdigest()[:16] + '.html')
    if os.path.exists(ruta) and not forzar:
        return open(ruta, 'rb').read()
    pet = urllib.request.Request(url, headers={'User-Agent': AGENTE})
    with urllib.request.urlopen(pet, timeout=60) as r:
        datos = r.read()
    with open(ruta, 'wb') as fh:
        fh.write(datos)
    time.sleep(0.5)
    return datos


def renglones(crudo):
    """Los renglones de texto de una página, sin etiquetas."""
    m = re.search(rb'(?i)charset=["\']?([\w-]+)', crudo[:4000])
    enc = (m.group(1).decode('ascii', 'replace') if m else 'utf-8')
    try:
        s = crudo.decode(enc, 'replace')
    except LookupError:
        s = crudo.decode('utf-8', 'replace')
    s = re.sub(r'(?is)<(script|style|head).*?</\1>', ' ', s)
    s = re.sub(r'(?i)<br\s*/?>|</p>|</tr>|</div>|</li>|</h\d>', '\n', s)
    s = re.sub(r'(?s)<[^>]+>', '', s)
    s = html.unescape(s).replace(' ', ' ')
    return [re.sub(r'[ \t]+', ' ', ln).strip() for ln in s.split('\n')]


def recorta(lineas, desde, hasta):
    i0 = 0
    if desde:
        r = re.compile(desde)
        for i, ln in enumerate(lineas):
            if r.search(ln):
                i0 = i
                break
        else:
            return None
    i1 = len(lineas)
    if hasta:
        r = re.compile(hasta)
        for i in range(i0 + 1, len(lineas)):
            if r.search(lineas[i]):
                i1 = i
                break
    trozo = [ln for ln in lineas[i0:i1]]
    while trozo and not trozo[0]:
        trozo.pop(0)
    while trozo and not trozo[-1]:
        trozo.pop()
    # los renglones vacíos de más, fuera; uno solo separa párrafos
    salida = []
    for ln in trozo:
        if ln or (salida and salida[-1]):
            salida.append(ln)
    return salida


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--forzar', action='store_true',
                    help='vuelve a bajar las páginas')
    args = ap.parse_args()

    piezas = {}
    for f in FUENTES:
        try:
            crudo = baja(f['url'], args.forzar)
        except Exception as e:
            print('¡ojo! no he podido bajar %s (%s)' % (f['url'], e))
            continue
        trozo = recorta(renglones(crudo), f.get('desde'), f.get('hasta'))
        if not trozo:
            print('¡ojo! no encuentro el texto en %s' % f['url'])
            continue
        fuente = {'autoridad': f['autoridad'], 'obra': f['obra'],
                  'url': f['url'], 'territorio': f['territorio'],
                  'oficial': bool(f.get('oficial'))}
        if f.get('nota'):
            fuente['aviso'] = f['nota']
        if f.get('que_es'):
            fuente['que_es'] = f['que_es']
        piezas[f['pieza']] = {'paso': f.get('paso', 4), 'tes': f.get('tes'),
                              'fuente': fuente, 'texto': trozo}
        print('%-40s %3d renglones  %s'
              % (f['pieza'], len(trozo), f['url'][:46]))

    ruta = os.path.join(DATOS, 'castellano_mano.json')
    with io.open(ruta, 'w', encoding='utf-8') as fh:
        json.dump({'fuente': 'fase 4b — castellano traído de fuera',
                   'piezas': piezas}, fh, ensure_ascii=False, indent=1,
                  sort_keys=True)
    print('%d piezas -> %s' % (len(piezas), ruta))


if __name__ == '__main__':
    main()
