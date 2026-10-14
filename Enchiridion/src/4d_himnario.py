# -*- coding: utf-8 -*-
"""Fase 4d — a qué hora se canta cada himno.

En el sitio, 32 de los himnos están en una carpeta que se llama «Tiempo
ordinario», y no son de ningún tiempo: son **el himnario del día**. *Jam
lucis orto sídere* es de Prima, *Te lucis ante términum* de Completas, y la
serie de Vísperas —*Lucis Creátor óptime*, *Imménse cæli Cónditor*,
*Tellúris ingens Cónditor*…— es la de Gregorio Magno, un himno para cada día
de la semana, del domingo al sábado, siguiendo los días de la creación. Un
devocionario que los pone por orden alfabético pierde todo eso.

La hora no hay que deducirla: **el Breviario la dice**. El volcado de
Divinum Officium que la fase 3a ya usa para los acentos no es una lista de
palabras, es el libro entero, y sus ficheros traen los himnos en secciones
rotuladas con la hora, el día de la semana y el tiempo:

    [Hymnus Prima]                  la hora
    [Hymnus Day1 Laudes]            la hora y el día (Day0 es el domingo)
    [Hymnus Adv Vespera]            la hora y el tiempo
    [Day3 Hymnus]                   en Maitines, el día va delante
    @:Hymnus Day5 Vespera:s/a/b/    el que se canta cambiando dos versos

Se cotejan por el íncipit —las cuatro primeras palabras, sin acentos, sin
ligaduras y con la i y la j confundidas, que es como se compara el latín en
todo el proyecto—, y el cotejo es exacto: o casa el verso o no casa. Lo que
no casa se queda sin hora y en el devocionario sale en «sin hora en el
Breviario», que es la verdad.

    cache/acentos/divinum/ ──▶ Enchiridion/datos/himnario.csv
                            └▶ Enchiridion/datos/himnario_qa.txt

    python Enchiridion/src/4d_himnario.py
"""

import argparse
import collections
import csv
import io
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, TRABAJO

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
BREVIARIO = os.path.join(RAIZ, 'cache', 'acentos', 'divinum', 'web', 'www',
                         'horas', 'Latin')

HORA = {'Matutinum': 'Maitines', 'Laudes': 'Laudes', 'Prima': 'Prima',
        'Tertia': 'Tercia', 'Sexta': 'Sexta', 'Nona': 'Nona',
        'Vespera': 'Vísperas', 'Completorium': 'Completas'}
# El orden en que se rezan, que es el orden en que se enseñan.
HORAS = ['Maitines', 'Laudes', 'Prima', 'Tercia', 'Sexta', 'Nona',
         'Vísperas', 'Completas']
DIA = {'Day0': 'domingo', 'Day1': 'lunes', 'Day2': 'martes',
       'Day3': 'miércoles', 'Day4': 'jueves', 'Day5': 'viernes',
       'Day6': 'sábado'}
TIEMPO = {'Adv': 'Adviento', 'Nat': 'Navidad', 'Epi': 'Epifanía',
          'Quad': 'Cuaresma', 'Quad5': 'Pasión', 'Trid': 'Triduo',
          'Pasch': 'Pascua', 'Pasc': 'Pascua', 'Asc': 'Ascensión',
          'Pent': 'Pentecostés', 'Adv3': 'Adviento'}

# Las antífonas finales de la Virgen viven en un fichero aparte, por
# tiempos: son las que cierran Completas, y el Breviario cambia de una a
# otra con el año.
MARIANAS = {'Advent': 'Adviento', 'Nativiti': 'Navidad',
            'Quadragesimae': 'Cuaresma', 'Paschalis': 'Pascua',
            'Postpentecost': 'Tiempo ordinario'}

# Los tres cánticos del Evangelio no están rotulados por hora en el
# Breviario de Divinum Officium —van con los salmos—, pero su hora es la
# que esta misma app imprime en la Liturgia de las Horas, y no tiene
# variante: es de lo poco que se pone a mano aquí.
CANTICOS = {
    'benedictus dominus deus israel': ('Laudes', 'el cántico de Zacarías'),
    'magnificat anima mea dominum': ('Vísperas', 'el cántico de la Virgen'),
    'nunc dimittis servum tuum': ('Completas', 'el cántico de Simeón'),
}

SECCION = re.compile(r'(?m)^\[([^\]]+)\]\r?\n(.*?)(?=^\[|\Z)', re.S)
LLAVES = re.compile(r'\{[^}]*\}')
MARCA = re.compile(r'^\s*[vrVR]\.\s*')
SALTAR = ('$', '!', '_', '&', '#', '%')
SUSTITUCION = re.compile(r's/([^/]*)/([^/]*)/')


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace(u'æ', 'ae').replace(u'œ', 'oe').replace('j', 'i')
    s = re.sub(r'[^a-z ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def clave(s):
    """Las cuatro primeras palabras del verso, que son el nombre del himno."""
    p = plano(s).split()
    return ' '.join(p[:4]) if len(p) >= 3 else None


def primer_verso(cuerpo):
    for linea in cuerpo.split('\n'):
        t = LLAVES.sub('', linea).strip()
        if not t or t.startswith(SALTAR) or t.startswith('@'):
            continue
        return MARCA.sub('', t)
    return None


def lee_breviario():
    """Todas las secciones de himno del Breviario, con su hora y su día.

    Dos pasadas: la primera recoge los versos, y la segunda resuelve los
    reenvíos —`@:otra sección:s/este verso/aquel otro/`—, que son himnos que
    se cantan cambiando un verso y que de otro modo se quedarían fuera."""
    crudo, reenvios = {}, []
    for carpeta in ('Psalterium', 'Tempora', 'Commune', 'Sancti'):
        base = os.path.join(BREVIARIO, carpeta)
        for raiz, _, ficheros in os.walk(base):
            for fichero in ficheros:
                if not fichero.endswith('.txt'):
                    continue
                ruta = os.path.join(raiz, fichero)
                with io.open(ruta, encoding='utf-8', errors='replace') as fh:
                    texto = fh.read()
                for m in SECCION.finditer(texto):
                    etiqueta, cuerpo = m.group(1).strip(), m.group(2)
                    if 'Hymnus' not in etiqueta or 'HymnusM' in etiqueta:
                        continue
                    pistas = etiqueta.replace('_', ' ').split() + \
                        re.split(r'[^A-Za-z]+', fichero)
                    hora = next((HORA[p] for p in pistas if p in HORA), None)
                    dia = next((DIA[p] for p in pistas if p in DIA), None)
                    tpo = next((TIEMPO[p] for p in pistas if p in TIEMPO),
                               None)
                    ref = re.match(r'\s*@:([^:]+):?(.*)', cuerpo)
                    if ref:
                        reenvios.append((ref.group(1).strip(), ref.group(2),
                                         hora, dia, tpo, etiqueta, fichero))
                        continue
                    verso = primer_verso(cuerpo)
                    k = clave(verso) if verso else None
                    if k:
                        crudo.setdefault(k, (hora, dia, tpo, etiqueta,
                                             fichero))
                        crudo['@' + etiqueta] = verso
    # las antífonas finales, que no son himnos y tienen su propio fichero
    ruta = os.path.join(BREVIARIO, 'Psalterium', 'Mariaant.txt')
    if os.path.exists(ruta):
        with io.open(ruta, encoding='utf-8', errors='replace') as fh:
            texto = fh.read()
        for m in SECCION.finditer(texto):
            etiqueta, cuerpo = m.group(1).strip(), m.group(2)
            if etiqueta not in MARIANAS:
                continue
            k = clave(primer_verso(cuerpo) or '')
            if k:
                crudo.setdefault(k, ('Completas', None, MARIANAS[etiqueta],
                                     'antífona final de Completas',
                                     'Mariaant.txt'))
    for etiqueta, subs, hora, dia, tpo, eti2, fichero in reenvios:
        verso = crudo.get('@' + etiqueta)
        if not verso:
            continue
        for viejo, nuevo in SUSTITUCION.findall(subs):
            verso = verso.replace(viejo, nuevo)
        k = clave(verso)
        if k:
            crudo.setdefault(k, (hora, dia, tpo, eti2 + ' (reenvío)',
                                 fichero))
    return dict((k, v) for k, v in crudo.items() if not k.startswith('@'))


def incipits(p):
    """Por dónde se puede reconocer una pieza: su título y sus dos primeros
    renglones, porque el título a veces es un rótulo y no el verso."""
    fuera = [p['tla']]
    for b in p['b'][:2]:
        for linea in (b.get('la') or [])[:2]:
            fuera.append(''.join(x[1] for x in linea))
    return [k for k in (clave(x) for x in fuera) if k]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    if not os.path.isdir(BREVIARIO):
        sys.exit('falta el Breviario en cache/acentos/divinum '
                 '(lo baja python src/13a_crawl_acentos.py)')
    entrada = os.path.join(TRABAJO, 'piezas_ecl.json')
    if not os.path.exists(entrada):
        sys.exit('corre antes Enchiridion/src/3_eclesiastico.py')
    with io.open(entrada, encoding='utf-8') as fh:
        libro = json.load(fh)
    formas = {}
    ruta_formas = os.path.join(DATOS, 'formas.csv')
    if os.path.exists(ruta_formas):
        with io.open(ruta_formas, encoding='utf-8', newline='') as fh:
            formas = dict((f['id'], f['forma']) for f in csv.DictReader(fh))

    bre = lee_breviario()
    filas, sin = [], []
    for p in libro['piezas']:
        if 'duplicado_de' in p or not p['car_la']:
            continue
        forma = formas.get(p['id'], '')
        # sólo se le busca hora a lo que se canta: a una colecta no se le
        # pregunta por su hora, y un falso positivo ahí sería grave
        if forma not in ('himno', 'secuencia', 'antífona', 'cántico',
                         'pregón', 'aclamación'):
            continue
        hallado = None
        for k in incipits(p):
            if k in CANTICOS:
                hallado = (CANTICOS[k][0], None, None, CANTICOS[k][1],
                           '(a mano)')
                break
            if k in bre:
                hallado = bre[k]
                break
        if hallado:
            filas.append({'id': p['id'], 'titulo': p['tla'],
                          'hora': hallado[0] or '', 'dia': hallado[1] or '',
                          'tiempo': hallado[2] or '',
                          'seccion': hallado[3], 'fichero': hallado[4]})
        else:
            sin.append((forma, p['tla'], p['cat']))

    os.makedirs(DATOS, exist_ok=True)
    ruta = os.path.join(DATOS, 'himnario.csv')
    with io.open(ruta, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, ['id', 'titulo', 'hora', 'dia', 'tiempo',
                                'seccion', 'fichero'])
        w.writeheader()
        for f in sorted(filas, key=lambda f: (
                HORAS.index(f['hora']) if f['hora'] in HORAS else 99,
                f['dia'], plano(f['titulo']))):
            w.writerow(f)

    porhora = collections.Counter(f['hora'] or '(sin hora)' for f in filas)
    qa = os.path.join(DATOS, 'himnario_qa.txt')
    with io.open(qa, 'w', encoding='utf-8') as fh:
        fh.write(u'La hora de cada himno, según el Breviario\n')
        fh.write(u'=' * 41 + u'\n\n')
        fh.write(u'%d secciones de himno en el Breviario; %d piezas del '
                 u'devocionario casan con una, %d no.\n\n'
                 % (len(bre), len(filas), len(sin)))
        for h in HORAS + ['(sin hora)']:
            if not porhora[h]:
                continue
            fh.write(u'\n%s  (%d)\n%s\n' % (h.upper(), porhora[h], u'-' * 64))
            for f in sorted(filas, key=lambda f: (f['dia'], f['titulo'])):
                if (f['hora'] or '(sin hora)') != h:
                    continue
                fh.write(u'  %-44s %-10s %-12s %s\n'
                         % (f['titulo'][:44], f['dia'], f['tiempo'],
                            f['seccion']))
        fh.write(u'\n\nSIN HORA  (%d)\n%s\n' % (len(sin), u'-' * 64))
        for forma, tit, cat in sorted(sin):
            fh.write(u'  %-14s %-46s %s\n' % (forma, tit[:46], cat))
    print('%d piezas con hora -> %s' % (len(filas), ruta))
    for h in HORAS:
        if porhora[h]:
            print('  %-10s %3d' % (h, porhora[h]))
    if porhora['(sin hora)']:
        print('  %-10s %3d' % ('(sin hora)', porhora['(sin hora)']))
    print('  %-10s %3d' % ('sin casar', len(sin)))


if __name__ == '__main__':
    main()
