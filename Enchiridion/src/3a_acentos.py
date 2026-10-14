# -*- coding: utf-8 -*-
"""Fase 3a — las tablas de acentuación del vocabulario del devocionario.

La fase 9 del leccionario (`src/13_acentos.py`) sabe acentuar latín, pero sus
léxicos están recortados al vocabulario de la Vulgata: así lo dice
`13b_build_acentos.py`, «para no guardar lexico de sobra». El devocionario
trae 16 000 formas y 4 000 no están en la Vulgata —vocativos («ángele»,
«Cherubíne»), el latín de los himnos medievales, el de las letanías—, y para
ésas el acentuador no tiene a quién preguntar y pone la penúltima por
omisión, que acierta dos veces de cada tres.

No hace falta inventar nada: las dos fuentes de la fase 9a están bajadas y
no se usaron del todo.

  · **El uso impreso.** Divinum Officium publica el Breviario y el Misal
    romanos ya acentuados y en esta misma ortografía («quǽsumus», «ejus»):
    6 000 ficheros que la fase 9 cosecha enteros y luego tira todo lo que no
    es de la Vulgata. Ahí están los himnos del Breviario, el Oficio Parvo,
    las letanías y las oraciones antes y después de la misa, que es la mitad
    del devocionario. Y lo están con su acento y con su jota puestos por el
    libro, no por una regla.

  · **Las cantidades vocálicas** de Morpheus: 755 000 análisis con la vocal
    larga marcada, de los que la fase 9 guardó 32 000.

Aquí se cosechan las dos otra vez, con el mismo método y los mismos
umbrales, para el vocabulario del devocionario, y salen cuatro tablas que la
fase 3 pone encima de las del leccionario sin tocarlas:

    Enchiridion/datos/acentos_uso.csv         dónde pone el acento el libro
    Enchiridion/datos/acentos_cantidades.csv  qué dice la cantidad vocálica
    Enchiridion/datos/jota_uso.csv            qué i escribe el libro con j
    Enchiridion/datos/hiato_uso.csv           dónde el libro parte el diptongo

Las dos primeras las entiende el acentuador tal cual. Las dos últimas son la
ortografía, y valen por lo que no dicen tanto como por lo que dicen: si el
Breviario imprime «adjuva», ahí la i es consonante y no hace falta deducirlo.

    python Enchiridion/src/3a_acentos.py

Hay que haber corrido antes `python src/13a_crawl_acentos.py`, que es quien
baja el corpus y las cantidades a `cache/acentos/`.
"""

import argparse
import csv
import importlib.util
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, TRABAJO

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
CACHE = os.path.join(RAIZ, 'cache', 'acentos')


def modulo(nombre):
    spec = importlib.util.spec_from_file_location(
        'm' + re.sub(r'\W', '', nombre),
        os.path.join(RAIZ, 'src', nombre + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A = modulo('13_acentos')
B = modulo('13b_build_acentos')


def vocabulario_del_devocionario():
    """Las claves latinas de las piezas, y sus formas tal como vienen."""
    ruta = os.path.join(TRABAJO, 'piezas.json')
    if not os.path.exists(ruta):
        sys.exit('no hay piezas: corre antes Enchiridion/src/2_piezas.py')
    with io.open(ruta, encoding='utf-8') as fh:
        libro = json.load(fh)
    claves = set()
    for p in libro['piezas']:
        for texto in [p['tla']] + [t for b in p['b'] for ln in b['la']
                                   for _, t in ln]:
            for w in A.PALABRA.findall(unicodedata.normalize('NFC', texto)):
                claves.add(A.clave(w))
    return claves


def formas_del_uso():
    """Todas las formas latinas que imprime Divinum Officium."""
    formas = set()
    for ruta, _ in B.ficheros():
        with io.open(ruta, encoding='utf-8', errors='replace') as fh:
            for linea in fh:
                linea = unicodedata.normalize('NFC', linea).strip()
                if not linea or linea.startswith(B.MARCAS):
                    continue
                for t in A.PALABRA.findall(B.RUBRICA.sub(' ', linea)):
                    if not B.NO_LATINA.search(t):
                        formas.add(t)
    return formas


# Lo que parece jota en los libros y no lo es. El Breviario conserva la
# tipografía antigua, que escribe la doble i final como «ij» —«alijs»,
# «desiderijs», y los numerales «ij», «vj», «xij»—, y ahí la j es una i
# larga de imprenta, no una consonante. La consonante siempre va delante de
# vocal, así que basta mirar la letra siguiente. Y una errata suelta
# —«quja» por «quia»— se queda fuera por la regla de siempre: detrás de qu
# la i no es consonante.
VOCALES = 'aeiouy'


def limpia_jotas(jot):
    buenas = {}
    for k, pos in jot.items():
        if len(k) < 3:
            continue
        ps = {i for i in pos
              if i + 1 < len(k) and k[i + 1] in VOCALES
              and not re.search(r'[qgs]u$', k[:i])}
        if ps:
            buenas[k] = ps
    return buenas


# La diéresis dice que lo que parece diptongo no lo es, y sólo significa
# algo encima de la segunda vocal de ae, oe, au o eu. En el corpus hay
# unas pocas ä y ë que son ruido del volcado («regnäre», «quäm»), y así
# se van.
DIPTONGO = ('ae', 'oe', 'au', 'eu')


def limpia_hiatos(hia):
    buenas = {}
    for k, pos in hia.items():
        ps = {i for i in pos if i > 0 and k[i - 1:i + 1] in DIPTONGO}
        if ps:
            buenas[k] = ps
    return buenas


def ya_en_el_leccionario(nombre, columna='forma'):
    """Las claves que ya trae una tabla del leccionario, para no repetirlas."""
    ruta = os.path.join(RAIZ, 'data', nombre)
    if not os.path.exists(ruta):
        return set()
    with io.open(ruta, encoding='utf-8', newline='') as fh:
        return {r[columna] for r in csv.DictReader(fh)}


def escribe(ruta, cabecera, filas):
    with io.open(ruta, 'w', encoding='utf-8', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(cabecera)
        wr.writerows(filas)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    if not os.path.isdir(os.path.join(CACHE, 'divinum')):
        sys.exit('falta cache/acentos/divinum: corre antes\n'
                 '    python src/13a_crawl_acentos.py')

    claves = vocabulario_del_devocionario()
    print('%d claves latinas en el devocionario' % len(claves))

    # 1. la ortografía del libro: jotas y hiatos de todo lo que imprime
    formas = formas_del_uso()
    print('%d formas en el corpus litúrgico impreso' % len(formas))
    hia_u, jot_u, testigo = B.hiatos_y_jotas(formas)
    jot_u, hia_u = limpia_jotas(jot_u), limpia_hiatos(hia_u)

    # las tablas del leccionario, que son las que ya sabe el acentuador
    hia_l = {r['forma']: {int(x) for x in r['cortes'].split()}
             for r in _csv(os.path.join(RAIZ, 'data', 'acentos_hiato.csv'))}
    jot_l = {r['forma']: {int(x) for x in r['cortes'].split()}
             for r in _csv(os.path.join(RAIZ, 'data', 'acentos_jota.csv'))}
    hia = dict(hia_l)
    hia.update({k: v for k, v in hia_u.items() if k not in hia_l})
    jot = dict(jot_l)
    jot.update({k: v for k, v in jot_u.items() if k not in jot_l})

    nuevas_jot = [(k, v) for k, v in jot_u.items()
                  if k in claves and k not in jot_l]
    nuevas_hia = [(k, v) for k, v in hia_u.items()
                  if k in claves and k not in hia_l]
    escribe(os.path.join(DATOS, 'jota_uso.csv'),
            ['forma', 'cortes', 'testigo'],
            [(k, ' '.join(str(x) for x in sorted(v)), testigo.get(k, ''))
             for k, v in sorted(nuevas_jot)])
    escribe(os.path.join(DATOS, 'hiato_uso.csv'),
            ['forma', 'cortes', 'testigo'],
            [(k, ' '.join(str(x) for x in sorted(v)), testigo.get(k, ''))
             for k, v in sorted(nuevas_hia)])
    print('jotas nuevas: %d   hiatos nuevos: %d'
          % (len(nuevas_jot), len(nuevas_hia)))

    # 2. el acento impreso, cosechado con el método de la fase 9b
    cuenta, sin_marca, nl = B.cosecha(hia, jot)
    uso, reparto, conflictos = B.decide(cuenta, sin_marca)
    print('%d renglones cosechados, %d formas con acento decidido'
          % (nl, len(uso)))
    ya = ya_en_el_leccionario('acentos_liturgico.csv')
    filas = []
    for k in sorted(set(uso) & claves):
        if k in ya:
            continue
        ac = reparto.get(k, Counter())
        filas.append((k, uso[k], sum(ac.values()), sin_marca.get(k, 0)))
    escribe(os.path.join(DATOS, 'acentos_uso.csv'),
            ['forma', 'indice', 'apar_acento', 'apar_sin_marca'], filas)
    print('acentos del uso nuevos para el devocionario: %d' % len(filas))

    # 3. las cantidades vocálicas de las que no haya uso
    cant, lineas = B.cantidades(claves)
    ya_cant = ya_en_el_leccionario('acentos_cantidades.csv')
    filas_c = []
    for k in sorted(claves & set(cant)):
        if k in ya_cant:
            continue
        v = sorted(cant[k])
        filas_c.append((k, v[0] if len(v) == 1 else 'ambigua',
                        ' '.join(str(x) for x in v)))
    escribe(os.path.join(DATOS, 'acentos_cantidades.csv'),
            ['forma', 'acento', 'analisis'], filas_c)
    print('cantidades nuevas para el devocionario: %d (de %d análisis)'
          % (len(filas_c), lineas))

    qa = os.path.join(DATOS, 'acentos_qa.txt')
    with io.open(qa, 'w', encoding='utf-8') as fh:
        fh.write('tablas de acentuación del devocionario\n\n')
        fh.write('claves latinas del devocionario ........ %6d\n' % len(claves))
        fh.write('formas del corpus litúrgico impreso .... %6d\n' % len(formas))
        fh.write('renglones cosechados .................. %6d\n' % nl)
        fh.write('\nlo que sale para el devocionario y no estaba\n')
        fh.write('  acento del uso impreso .............. %6d\n' % len(filas))
        fh.write('  cantidades vocálicas ................ %6d\n' % len(filas_c))
        fh.write('  jotas ............................... %6d\n'
                 % len(nuevas_jot))
        fh.write('  hiatos .............................. %6d\n'
                 % len(nuevas_hia))
        chocan = sorted(set(conflictos) & claves)
        fh.write('\nformas en que el uso impreso no se pone de acuerdo '
                 'consigo mismo (%d)\n' % len(chocan))
        for k in chocan:
            fh.write('  %-24s %s\n' % (k, conflictos[k]))
        fh.write('\njotas nuevas, con el testigo que las dice\n')
        for k, v in sorted(nuevas_jot):
            fh.write('  %-24s %-8s %s\n'
                     % (k, ' '.join(str(x) for x in sorted(v)),
                        testigo.get(k, '')))
    print('informe: ' + qa)


def _csv(ruta):
    if not os.path.exists(ruta):
        return []
    with io.open(ruta, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


if __name__ == '__main__':
    main()
