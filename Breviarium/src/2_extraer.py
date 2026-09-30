# -*- coding: utf-8 -*-
"""Fase 2 — de los 29 000 HTML a un corpus diario estructurado.

Lee `cache/breviarium/AAAA/mes/dd/*.htm` y escribe, un fichero por año,
`Breviarium/datos/dias/AAAA.json`: cada día con su clasificación
litúrgica (tiempo, semana, salterio, celebración) y cada hora partida en
sus secciones (invitatorio, himno, salmodia, lectura breve, preces…).

Aquí no se decide nada: sólo se lee lo que el original dice. Ordenar por
tiempos, comunes y santoral es cosa de la fase 3.

    python Breviarium/src/2_extraer.py
"""

import difflib
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from breviario import (CORPUS, FUENTE, HORAS, MESES, clave, es_roja,
                       es_rubrica, lineas_de, pardo_de, plano)

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESTINO = CORPUS
QA = os.path.join(RAIZ, 'Breviarium', 'datos', 'extraer_qa.txt')


# --------------------------------------------------------------------------
# los rótulos que parten una hora en secciones
# --------------------------------------------------------------------------

EXACTOS = {
    'invocacion inicial': 'invocacion',
    'invitatorio': 'invitatorio',
    'salmodia': 'salmodia',
    'primera lectura': 'lectura1',
    'segunda lectura': 'lectura2',
    'cantico evangelico': 'cantico_evangelico',
    'preces': 'preces',
    'oracion': 'oracion',
    'conclusion': 'conclusion',
    'examen de conciencia': 'examen',
    'bendicion': 'bendicion',
    'te deum': 'te_deum',
    'himno te deum': 'te_deum',
    'padre nuestro': 'padrenuestro',
}

PREFIJOS = [
    ('responsorio breve', 'responsorio_breve'),
    ('responsorio', 'responsorio'),
    ('lectura breve', 'lectura_breve'),
    ('himno', 'himno'),
    ('antifona final', 'antifona_final'),
    ('antiphona final', 'antifona_final'),
    ('oracion', 'oracion'),
]

# títulos de hora: la primera línea roja del fichero
TITULO_HORA = re.compile(
    r'^(i+ )?(visperas|laudes|completas|oficio de lectura|hora (tercia|sexta|nona)'
    r'|tercia|sexta|nona)\b')


def clase_de_rotulo(texto):
    """A qué sección abre este rótulo, o None si no abre ninguna."""
    c = clave(texto)
    if not c:
        return None
    if c in EXACTOS:
        return EXACTOS[c]
    for pref, cl in PREFIJOS:
        if c.startswith(pref):
            return cl
    return None


def es_salmo(texto):
    """Los rótulos rojos que dentro de la salmodia abren un salmo o cántico."""
    c = clave(texto)
    return bool(re.match(r'^(salmo|cantico|canticos)\b', c))


# --------------------------------------------------------------------------
# la cabecera del día (index.htm)
# --------------------------------------------------------------------------

TIEMPOS = {
    'tiempo de adviento': 'Adviento',
    'tiempo de navidad': 'Navidad',
    'tiempo de cuaresma': 'Cuaresma',
    'tiempo pascual': 'Pascua',
    'tiempo ordinario': 'Ordinario',
    'triduo pascual': 'Triduo',
    'semana santa': 'Cuaresma',
}

RANGOS = ['SOLEMNIDAD', 'FIESTA', 'MEMORIA LIBRE', 'MEMORIA', 'CONMEMORACIÓN',
          'CONMEMORACION']

ROMANOS = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
           'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13,
           'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18,
           'XIX': 19, 'XX': 20, 'XXI': 21, 'XXII': 22, 'XXIII': 23,
           'XXIV': 24, 'XXV': 25, 'XXVI': 26, 'XXVII': 27, 'XXVIII': 28,
           'XXIX': 29, 'XXX': 30, 'XXXI': 31, 'XXXII': 32, 'XXXIII': 33,
           'XXXIV': 34}

DIAS = ['DOMINGO', 'LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES',
        'SÁBADO']


def es_versal(texto):
    """Verdadero si el texto va todo en versales (así van los títulos)."""
    letras = [c for c in texto if c.isalpha()]
    return bool(letras) and all(c.isupper() for c in letras)


def cabecera(ruta):
    """Lo que el índice del día dice de sí mismo."""
    lineas = lineas_de(ruta)
    # las líneas del encabezado van hasta la tabla de enlaces
    utiles = []
    for ln in lineas:
        t = plano(ln)
        if clave(t) in ('oficio de lectura', 'laudes', 'tercia'):
            break
        if t:
            utiles.append(t)

    d = {'tiempo': None, 'titulo': None, 'nota': None, 'salterio': None,
         'origen': None, 'celebracion': None, 'rango': None, 'resena': None,
         'cabecera': utiles}

    if not utiles:
        return d

    # 1ª línea: el tiempo litúrgico. La fuente es un volcado hecho a mano y
    # alguna errata se le escapa —«TIEMPO ORDINQRIO», 30-XI-2024—, y una
    # errata así inventaría un tiempo litúrgico entero. Así que, si no
    # coincide exacto, se busca el más parecido entre los que existen; y
    # sólo si tampoco se parece a ninguno se deja tal cual.
    c0 = clave(utiles[0])
    d['tiempo'] = TIEMPOS.get(c0)
    if d['tiempo'] is None:
        cerca = difflib.get_close_matches(c0, TIEMPOS, n=1, cutoff=0.85)
        d['tiempo'] = TIEMPOS[cerca[0]] if cerca else utiles[0].strip().title()

    # El día viene en versales, y puede ir partido en varias líneas; la
    # nota («De la Feria. Salterio I») no va en versales. Ésa es toda la
    # diferencia, y basta para separarlos.
    titulo, nota = [], []
    for t in utiles[1:]:
        if re.match(r'^\d{1,2} de [a-záéíóú]+$', t.strip(), re.I):
            break
        if nota or not es_versal(t):
            nota.append(t)
        else:
            titulo.append(t)
    d['titulo'] = ' '.join(titulo).strip() or None
    d['nota'] = ' '.join(nota).strip() or None

    if d['nota']:
        m = re.search(r'salterio\s+([IVX]+)', d['nota'], re.I)
        if m:
            d['salterio'] = ROMANOS.get(m.group(1).upper())
        prim = d['nota'].split('.')[0].strip()
        d['origen'] = prim or None

    # La celebración del santoral va en pardo. Pero en pardo van también
    # los enlaces a los oficios alternativos («haga click aquí») y alguna
    # advertencia suelta, así que sólo cuenta como celebración el pardo
    # que declara su rango: solemnidad, fiesta, memoria, conmemoración.
    junto = ' '.join(t for t in (pardo_de(ln) for ln in lineas) if t)
    for rango in RANGOS:
        if rango in junto.upper():
            d['rango'] = ('MEMORIA LIBRE' if 'MEMORIA LIBRE' in junto.upper()
                          else rango)
            break
    if d['rango']:
        # El nombre va delante del rango, y detrás del rango viene la
        # reseña biográfica. Casi siempre el rango va entre paréntesis
        # —«SANTA TERESA DE JESÚS. (MEMORIA) Nació en Ávila…»— pero no
        # siempre, así que se corta por lo que aparezca antes: el
        # paréntesis o la palabra del rango.
        cortes = [junto.find('(')]
        m = re.search(re.escape(d['rango']), junto, re.I)
        if m:
            cortes.append(m.start())
        cortes = [c for c in cortes if c > 0]
        corte = min(cortes) if cortes else len(junto)
        d['celebracion'] = junto[:corte].strip(' .,;:·-')

        tras = junto[corte:]
        tras = re.sub(r'^\s*[(\[]?\s*' + re.escape(d['rango']) + r'\s*[)\]]?\.?',
                      '', tras, flags=re.I)
        tras = re.sub(r'haga click aqu[ií]\.?', '', tras, flags=re.I)
        d['resena'] = tras.strip(' .,;:·-') or None

    # semana y día de la semana, del título
    if d['titulo']:
        T = d['titulo'].upper()
        m = re.search(r'SEMANA\s+([IVX]+)', T)
        if m:
            d['semana'] = ROMANOS.get(m.group(1))
        for i, nd in enumerate(DIAS):
            if T.startswith(nd) or f' {nd}' in T:
                d['dia_semana'] = i
                break
    return d


# --------------------------------------------------------------------------
# una hora, partida en secciones
# --------------------------------------------------------------------------

def hora(ruta):
    lineas = lineas_de(ruta)
    titulo, subtitulo = None, None
    secciones = []
    act = None
    i = 0

    # título y subtítulo: las primeras rojas
    while i < len(lineas):
        t = plano(lineas[i])
        if not t:
            i += 1
            continue
        if es_rubrica(lineas[i]) and TITULO_HORA.match(clave(t)):
            titulo = t
            i += 1
            break
        break

    while i < len(lineas):
        t = plano(lineas[i])
        if not t:
            i += 1
            continue
        if es_rubrica(lineas[i]) and t.startswith('('):
            subtitulo = t
            i += 1
        break

    def abre(cl, rotulo):
        nonlocal act
        act = {'clase': cl, 'rotulo': rotulo, 'lineas': []}
        secciones.append(act)

    for ln in lineas[i:]:
        t = plano(ln)
        if es_rubrica(ln) and t:
            cl = clase_de_rotulo(t)
            if cl and not (act and act['clase'] == 'salmodia' and es_salmo(t)):
                abre(cl, t)
                continue
        if act is None:
            abre('preambulo', None)
        act['lineas'].append([[1 if es_roja(c) else 0, s] for c, s in ln])

    for s in secciones:
        while s['lineas'] and not ''.join(x for _, x in s['lineas'][-1]).strip():
            s['lineas'].pop()

    return {'titulo': titulo, 'subtitulo': subtitulo, 'secciones': secciones}


# --------------------------------------------------------------------------

def oficio_de(dir_dia, fecha, cuentas, avisos, etiqueta=''):
    """Un oficio completo: su cabecera, sus horas, y sus alternativas.

    Un día normal tiene siete horas sueltas en su carpeta. Algunos días
    —el 1 de mayo, sin ir más lejos: la feria o san José obrero— ofrecen
    dos o tres oficios a elegir, cada uno en una subcarpeta numerada. Se
    recogen igual, y colgando del día al que pertenecen.
    """
    idx = os.path.join(dir_dia, 'index.htm')
    reg = cabecera(idx) if os.path.exists(idx) else {}
    if not os.path.exists(idx):
        avisos.append(f'{fecha}{etiqueta}: sin index.htm')
    reg['horas'] = {}
    for cl, _ in HORAS:
        f = os.path.join(dir_dia, cl + '.htm')
        if os.path.exists(f):
            try:
                reg['horas'][cl] = hora(f)
                cuentas[cl] += 1
            except Exception as e:                      # noqa: BLE001
                avisos.append(f'{fecha}{etiqueta}/{cl}: {e}')
        elif not etiqueta:
            cuentas['falta_' + cl] += 1

    ev = os.path.join(dir_dia, 'evangelio.htm')
    if os.path.exists(ev):
        reg['evangelio'] = hora(ev)
        cuentas['evangelio'] += 1

    for h in reg['horas'].values():
        for sec in h['secciones']:
            cuentas['sec:' + sec['clase']] += 1

    opciones = sorted(d for d in os.listdir(dir_dia)
                      if d.isdigit() and os.path.isdir(os.path.join(dir_dia, d)))
    if opciones:
        reg['opciones'] = [
            oficio_de(os.path.join(dir_dia, o), fecha, cuentas, avisos,
                      f'{etiqueta}/{o}')
            for o in opciones]
        cuentas['dias_con_opciones'] += 1
    return reg


def main():
    os.makedirs(DESTINO, exist_ok=True)
    cuentas, avisos, resumen = Counter(), [], []

    for anio in sorted(os.listdir(FUENTE)):
        dir_anio = os.path.join(FUENTE, anio)
        if not (anio.isdigit() and os.path.isdir(dir_anio)):
            continue
        dias = {}
        for mes in sorted(os.listdir(dir_anio)):
            if mes not in MESES:
                continue
            dir_mes = os.path.join(dir_anio, mes)
            for dd in sorted(os.listdir(dir_mes)):
                dir_dia = os.path.join(dir_mes, dd)
                if not (dd.isdigit() and os.path.isdir(dir_dia)):
                    continue
                fecha = f'{anio}-{MESES[mes]:02d}-{int(dd):02d}'
                reg = oficio_de(dir_dia, fecha, cuentas, avisos)
                reg['fecha'] = fecha
                if not reg.get('tiempo'):
                    avisos.append(f'{fecha}: cabecera sin tiempo')
                if reg.get('celebracion'):
                    cuentas['con_celebracion'] += 1
                dias[fecha] = reg

        ruta = os.path.join(DESTINO, anio + '.json')
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(dias, f, ensure_ascii=False, separators=(',', ':'))
        resumen.append(f'{anio}: {len(dias):3d} días  '
                       f'{os.path.getsize(ruta) / 1e6:6.1f} MB')
        print(resumen[-1], flush=True)

    with open(QA, 'w', encoding='utf-8') as f:
        f.write('Fase 2 — extracción del corpus diario\n')
        f.write('=' * 60 + '\n\n')
        f.write('\n'.join(resumen) + '\n\n')
        f.write('Horas y secciones halladas\n' + '-' * 40 + '\n')
        for k, v in sorted(cuentas.items()):
            f.write(f'{v:8d}  {k}\n')
        f.write(f'\nAvisos: {len(avisos)}\n' + '-' * 40 + '\n')
        for a in avisos[:500]:
            f.write(a + '\n')
    print(f'\nQA en {QA}  ({len(avisos)} avisos)')


if __name__ == '__main__':
    main()
