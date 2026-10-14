# -*- coding: utf-8 -*-
"""Fase 5 — el devocionario para la app.

Junta lo de las fases anteriores en un solo fichero, `devocionario.json`, y
decide lo que se publica. Dos cosas se quedan fuera y a propósito:

  · **el inglés.** El aviso del sitio permite el uso personal y de estudio
    sin ánimo de lucro, que es el de esta app, pero la app está publicada en
    GitHub Pages y el repositorio es público, y la traducción inglesa es
    obra de Michael Martin. El latín de estas oraciones es texto tradicional
    y lleva siglos impreso; su inglés, no. Así que el inglés se queda en la
    carpeta de trabajo —bajado y guardado, por si algún día hay permiso— y
    de ahí no sale.
  · **el comentario.** La historia de cada oración y la nota de la
    indulgencia también son suyas, y además no son la oración. De la nota de
    procedencia sólo pasa el año, que es un dato.

Las categorías del sitio son carpetas («BVM», «Hymni/TempusPerAnnum») y aquí
se agrupan y se nombran en castellano, que es la lengua de la app. El orden
es el del sitio: de lo que todo el mundo reza a lo que reza quien busca.

    TRABAJO/piezas_ecl.json ──┐
    datos/castellano.json ────┴──▶  app/datos/devocionario.json

    python Enchiridion/src/5_app.py
"""

import argparse
import io
import json
import os
import re
import sys
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, SITIO, TRABAJO

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
APP = os.path.join(RAIZ, 'app', 'datos')

# Los grupos del devocionario, en el orden en que se enseñan, y qué
# carpetas del sitio caen en cada uno.
GRUPOS = [
    ('basico', 'Lo que se reza de memoria', ['Basics']),
    ('dia', 'Cada día', ['Cotidiana']),
    ('trinidad', 'La Santísima Trinidad', ['Trinitas']),
    ('padre', 'Dios Padre', ['Pater']),
    ('hijo', 'Nuestro Señor Jesucristo', ['Filius']),
    ('espiritu', 'El Espíritu Santo', ['Spiritus']),
    ('eucaristia', 'La Eucaristía', ['Euch']),
    ('misa', 'Antes y después de la misa', ['AnteMissam', 'PostMissam']),
    ('virgen', 'La Santísima Virgen', ['BVM']),
    ('jose', 'San José', ['Ioseph']),
    ('familia', 'La Sagrada Familia', ['SanctaFamilia']),
    ('angeles', 'Los ángeles', ['Angeli']),
    ('santos', 'Los santos', ['Sancti']),
    ('penitencia', 'Penitencia y confesión', ['Confessio']),
    ('tiempos', 'Los tiempos del año', ['InTemporibus']),
    ('himnos', 'Himnos', ['Hymni']),
    ('canticos', 'Cánticos del Evangelio', ['Cantici']),
    ('salmos', 'Salmos', ['Psalmi']),
    ('credos', 'Credos y profesiones de fe', ['Symbola']),
    ('numeros', 'De memoria, por números', ['Numeri']),
    ('varia', 'Otras oraciones', ['Varia', 'Introductio']),
]

# Dentro de un grupo, el rótulo de la subcarpeta.
SUBGRUPOS = {
    'Hymni/Adventus': 'Adviento',
    'Hymni/Nativitatis': 'Navidad',
    'Hymni/Epiphania': 'Epifanía',
    'Hymni/Quadragesimae': 'Cuaresma',
    'Hymni/Triduum': 'Triduo',
    'Hymni/Paschale': 'Pascua',
    'Hymni/Pentecoste': 'Pentecostés',
    'Hymni/CorpusChristi': 'Corpus Christi',
    'Hymni/OmnesSancti': 'Todos los Santos',
    'Hymni/TempusPerAnnum': 'Tiempo ordinario',
    'Hymni/Alii': 'Otros himnos',
    'Hymni/InTemporibus/Adventus': 'Adviento',
    'Hymni/InTemporibus/Quadragesimae': 'Cuaresma',
    'InTemporibus/Adventus': 'Adviento',
    'InTemporibus/Quadragesimae': 'Cuaresma',
    'InTemporibus/Nativitas': 'Navidad',
    'InTemporibus/Paschale': 'Pascua',
    'Psalmi/SixtoClementine': 'Vulgata Clementina',
    'Psalmi/NovaVulgata': 'Nova Vulgata',
    'Sancti/SAnna': 'Santa Ana',
    'Sancti/SAntoniusDePadova': 'San Antonio de Padua',
    'Sancti/SAugustinus': 'San Agustín',
    'Sancti/SBenedictusAb': 'San Benito',
    'Sancti/SFranciscusAssisiensis': 'San Francisco de Asís',
    'Sancti/SPatricius': 'San Patricio',
    'Sancti/SScholastica': 'Santa Escolástica',
}


def grupo_de(cat):
    for clave, _, carpetas in GRUPOS:
        for c in carpetas:
            if cat == c or cat.startswith(c + '/'):
                return clave
    return 'varia'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    entrada = os.path.join(TRABAJO, 'piezas_ecl.json')
    if not os.path.exists(entrada):
        sys.exit('corre antes Enchiridion/src/3_eclesiastico.py')
    with io.open(entrada, encoding='utf-8') as fh:
        libro = json.load(fh)
    ruta_es = os.path.join(DATOS, 'castellano.json')
    es = {}
    if os.path.exists(ruta_es):
        with io.open(ruta_es, encoding='utf-8') as fh:
            es = json.load(fh).get('piezas', {})

    cuenta = Counter()
    piezas = []
    for p in libro['piezas']:
        if 'duplicado_de' in p or not p['car_la']:
            cuenta['fuera: sin latín o duplicada'] += 1
            continue
        clave = p['pagina'].replace('thesaurus/', '') + '#' + str(p['orden'])
        bloques = []
        for b in p['b']:
            if not b['la']:
                continue          # rúbrica que Martin escribió sólo en inglés
            # la tirada viene de la fase 2 como [[rúbrica, cursiva], texto];
            # la app sólo necesita un número: 0 texto, 1 rúbrica, 2 cursiva
            ln = [[[(1 if x[0][0] else (2 if x[0][1] else 0)), x[1]]
                   for x in linea] for linea in b['la']]
            bl = OrderedDict([('t', ln)])
            if b['r']:
                bl['r'] = 1
            if b.get('h'):
                bl['h'] = b['h']
            bloques.append(bl)
        if not bloques:
            cuenta['fuera: sin latín'] += 1
            continue
        d = OrderedDict([
            ('id', p['id']),
            ('src', clave),
            ('g', grupo_de(p['cat'])),
            ('sub', SUBGRUPOS.get(p['cat'])),
            ('tla', p['tla']),
            ('b', bloques),
        ])
        if p['ortografia'] != 'eclesiástica':
            d['orto'] = p['ortografia']
        anio = (p['nota'] or {}).get('anio')
        if anio:
            d['anio'] = anio
        v = es.get(clave)
        if v:
            # el rótulo castellano de la lista: el título si lo tiene, y si
            # no, el primer renglón, que es como se conocen las oraciones
            # («Dios te salve, Reina y Madre de misericordia»)
            tes = v.get('tes')
            if not tes:
                for parr in v['t']:
                    for ln in parr:
                        t = ''.join(x[1] for x in ln).strip()
                        if t:
                            tes = t if len(t) <= 58 else t[:57].rstrip() + '…'
                            break
                    if tes:
                        break
            d['tes'] = tes
            d['es'] = v['t']
            d['fes'] = v['fuente']
            d['paso'] = v.get('paso')
            cuenta['con castellano'] += 1
        cuenta['publicadas'] += 1
        piezas.append(d)

    # El orden dentro de cada grupo: alfabético por el título latino, que
    # es como se busca en un devocionario. Los salmos no: ésos van por su
    # número, que es su nombre.
    ROMANOS = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500,
               'M': 1000}

    def numero_romano(t):
        m = re.match(r'(?i)^psalmus\s+([IVXLCDM]+)', t or '')
        if not m:
            return None
        n, previo = 0, 0
        for c in reversed(m.group(1).upper()):
            v = ROMANOS[c]
            n = n - v if v < previo else n + v
            previo = max(previo, v)
        return n

    def orden(d):
        import unicodedata
        t = unicodedata.normalize('NFD', d['tla'].lower())
        t = ''.join(c for c in t if not unicodedata.combining(c))
        return (d['sub'] or '', numero_romano(d['tla']) or 0, t)

    piezas.sort(key=lambda d: ([g[0] for g in GRUPOS].index(d['g']),
                               orden(d)))

    # Dos versiones de la misma oración se llaman igual —hay dos «Actus
    # Fídei», el de Gasparri y el tradicional—, y en una lista eso no se
    # puede distinguir. Se les pone al lado el año que la fuente da, y si no
    # lo da, el número de orden.
    from collections import defaultdict
    repes = defaultdict(list)
    for d in piezas:
        repes[(d['g'], d['tla'])].append(d)
    for grupo in repes.values():
        if len(grupo) < 2:
            continue
        for i, d in enumerate(grupo, 1):
            d['dist'] = d.get('anio') or ('versión %d' % i)

    # El índice de búsqueda. Se normaliza igual que `plano()` en la app
    # —sin diacríticos y con æ/œ desatadas— porque es esa función la que
    # prepara lo que el lector escribe. La jota no la desata, así que la
    # clave lleva también la forma con i: quien escriba «Iesu» encuentra
    # «Jesu», y quien escriba «Jesu» también.
    def pelado(s, jota=True):
        import unicodedata
        s = unicodedata.normalize('NFD', (s or '').lower())
        s = ''.join(c for c in s if not unicodedata.combining(c))
        s = s.replace('æ', 'ae').replace('œ', 'oe')
        if not jota:
            s = s.replace('j', 'i')
        return re.sub(r'\s+', ' ', s).strip()

    for d in piezas:
        titulos = d['tla'] + ' ' + (d.get('tes') or '')
        con = pelado(titulos)
        sin = pelado(titulos, jota=False)
        d['k'] = con if con == sin else con + ' ' + sin

    grupos = []
    for clave, nombre, _ in GRUPOS:
        n = sum(1 for d in piezas if d['g'] == clave)
        if n:
            grupos.append(OrderedDict([('g', clave), ('t', nombre),
                                       ('n', n)]))

    salida = OrderedDict([
        ('fuente', 'Thesaurus Precum Latinarum, de Michael Martin — '
                   + SITIO),
        ('derechos', 'Latín: texto tradicional. La transcripción es del '
                     'sitio, que permite el uso personal y de estudio sin '
                     'ánimo de lucro. Castellano: cada oración dice de '
                     'dónde sale.'),
        ('grupos', grupos),
        ('piezas', piezas),
    ])
    ruta = os.path.join(APP, 'devocionario.json')
    with io.open(ruta, 'w', encoding='utf-8') as fh:
        json.dump(salida, fh, ensure_ascii=False, separators=(',', ':'))

    print('%d piezas -> %s (%.1f MB)'
          % (len(piezas), ruta, os.path.getsize(ruta) / 1e6))
    for k, v in sorted(cuenta.items()):
        print('  %-30s %4d' % (k, v))
    for g in grupos:
        print('  %-12s %-34s %4d' % (g['g'], g['t'], g['n']))


if __name__ == '__main__':
    main()
