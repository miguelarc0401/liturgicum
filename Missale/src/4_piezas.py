# -*- coding: utf-8 -*-
"""Fase 4 — deshacer los días: de los cien misalitos a las piezas del libro.

La fase 3 partió los cien misalitos en 3 286 **días ya armados**. Esta fase
hace el camino contrario: guarda cada pieza **una vez**, en su sitio, con sus
testigos y sus variantes, para que el día se arme al celebrarlo.

Deja en `Missale/datos/libro/`:

  · `pericopas_es.json` — las lecturas **por cita**. La pieza viene con su
    cita («Del primer libro de Samuel 1, 9-20»), así que no hay que adivinar
    qué es: se normaliza a la misma forma que el índice del leccionario
    (`1 S 1,9-20`) y se cotejan los dos.
  · `propios_es.json` — los propios (antífonas y oraciones) **por
    celebración**, con el texto canónico decidido por mayoría de testigos y
    las variantes guardadas con los días que las respaldan.
  · `prefacios_propios_es.json` — los prefacios que no están en ninguno de
    los dos juegos comunes porque viven dentro de su formulario, y que el
    misalito **imprime enteros** dentro de la rúbrica del día.
  · `dias_es.json` — el puente para la fase 5: cada formulario con la
    celebración a la que se atribuyó, lo que la fuente nombró al lado y la
    cita de cada lectura.

**Lo que esta fase descubre, y que no estaba en el plan.** En las ferias del
tiempo ordinario el misalito **no imprime la feria**: imprime el formulario
que el editor eligió ese año, y lo dice al lado de la cabecera. El mismo
miércoles de la 11ª semana trae en ocho años la misa por la santificación del
trabajo, la de san Romualdo, la del Espíritu Santo, la de los laicos y la
oración de la feria. Por tanto **la mayoría de testigos no se puede tomar por
fecha**: hay que atribuir cada texto a la celebración que de verdad explica
los días en que aparece, y sólo entonces contar.

La atribución se mide, no se supone. Para cada texto se mira el conjunto de
días en que la fuente lo imprimió y se busca la celebración presente en
**todos** ellos. Si la fuente nombra la alternativa al lado de la cabecera
(«Feria o / Misa de los laicos», «o SAN ROMUALDO, Abad»), manda lo que la
fuente nombra; si no, manda la celebración que el calendario del proyecto
pone ese día. Lo que no se explica por ninguna va al informe y no entra.

    python Missale/src/4_piezas.py

Necesita el calendario desde 2018 (`python src/18_santoral.py`, que ya lo hace
por defecto) y la fase 3 corrida.
"""

import glob
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misal
from misal import DATOS, LIBRO, RAIZ, Informe, clave

DATA = os.path.join(RAIZ, 'data')
MISALITOS = os.path.join(DATOS, 'misalitos')
# La segunda fuente castellana, que la fase 3c deja en la misma forma.
WEB = os.path.join(DATOS, 'web')
QA = os.path.join(DATOS, 'piezas_qa.txt')


def sinac(s):
    """El texto sin tildes y en minúscula, para comparar."""
    s = unicodedata.normalize('NFKD', (s or '').lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


# --------------------------------------------------------------------------
# las ranuras del formulario
# --------------------------------------------------------------------------

# El rótulo que imprime la fuente (ya corregido por la fase 3) y la ranura
# del formulario. El orden es el del Misal, que es el que la app pinta.
RANURAS = [
    ('ANTÍFONA DE ENTRADA',            'entrada',     'propio'),
    ('ORACIÓN COLECTA',                'colecta',     'propio'),
    ('PRIMERA LECTURA',                'primera',     'lectura'),
    ('SALMO RESPONSORIAL',             'salmo',       'lectura'),
    ('SEGUNDA LECTURA',                'segunda',     'lectura'),
    ('TERCERA LECTURA',                'tercera',     'lectura'),
    ('CUARTA LECTURA',                 'cuarta',      'lectura'),
    ('QUINTA LECTURA',                 'quinta',      'lectura'),
    ('SEXTA LECTURA',                  'sexta',       'lectura'),
    ('SÉPTIMA LECTURA',                'septima',     'lectura'),
    ('EPÍSTOLA',                       'epistola',    'lectura'),
    ('SECUENCIA',                      'secuencia',   'lectura'),
    ('ACLAMACIÓN ANTES DEL EVANGELIO', 'aclamacion',  'lectura'),
    ('EVANGELIO',                      'evangelio',   'lectura'),
    ('ORACIÓN SOBRE LAS OFRENDAS',     'ofrendas',    'propio'),
    ('ANTÍFONA DE LA COMUNIÓN',        'comunion',    'propio'),
    ('ORACIÓN DESPUÉS DE LA COMUNIÓN', 'poscomunion', 'propio'),
    ('ORACIÓN SOBRE EL PUEBLO',        'pueblo',      'propio'),
]

# Dos rótulos más que no son ranura nueva, sino otro nombre de una que ya
# está: el sitio rotula «ACLAMACIÓN» a secas, y los dos días que leen la
# Pasión —el Domingo de Ramos y el Viernes Santo— rotulan su evangelio con
# ella. El leccionario los llama por la ranura, no por el rótulo, así que
# aquí se les da la de siempre.
OTRO_ROTULO = {
    'ACLAMACIÓN': 'aclamacion',
    'PASIÓN DE NUESTRO SEÑOR JESUCRISTO': 'evangelio',
}
DE_ROTULO = {r: s for r, s, _ in RANURAS}
DE_ROTULO.update(OTRO_ROTULO)
CLASE_DE = {s: c for _, s, c in RANURAS}
PROPIOS = [s for _, s, c in RANURAS if c == 'propio']
LECTURAS = [s for _, s, c in RANURAS if c == 'lectura']


# --------------------------------------------------------------------------
# A. la cabecera: lo que la fuente nombra al lado
# --------------------------------------------------------------------------
#
# La fase 3 guardó la alternativa en tres campos distintos según cómo cayera
# la maqueta: en `alterna` cuando la cabecera parte «Feria o» y el nombre en
# dos renglones, en `resena` cuando va en uno solo («o Misa por la
# santificación del trabajo humano «B»») y en `subtitulo` cuando la
# alternativa es un santo («o SAN ROMUALDO, Abad»). Son la misma cosa, y de
# ella depende la atribución entera, así que aquí se vuelve a leer del campo
# `crudo` —que la fase 3 guardó precisamente para esto— y se unifica.

ALTERNATIVA = re.compile(r'^\s*(?:feria\s+)?o\s+(.{3,})$', re.I)
SOLO_O = re.compile(r'^\s*(?:feria\s*)?o\s*$', re.I)


def alternativa_de(cab):
    """Lo que la fuente ofrece *en lugar de* lo que titula el día.

    Devuelve `(nombre, clase)` con clase 'misa' si es una misa votiva o del
    común, 'santo' si es una celebración, o `(None, None)` si el día no
    ofrece nada.
    """
    crudo = cab.get('crudo') or []
    for i, ln in enumerate(crudo):
        if SOLO_O.match(ln) and i + 1 < len(crudo):
            return _clasifica(crudo[i + 1])
        m = ALTERNATIVA.match(ln)
        if m:
            return _clasifica(m.group(1))
    # la fase 3 ya lo había separado: vale igual
    if cab.get('alterna'):
        return _clasifica(cab['alterna'])
    return None, None


def _clasifica(nombre):
    nombre = re.sub(r'\s+', ' ', nombre or '').strip(' .,;')
    if not nombre:
        return None, None
    if re.match(r'^misa\b', nombre, re.I):
        return nombre, 'misa'
    # Un santo viene en versales. Un renglón en minúsculas no es un nombre de
    # celebración: es prosa que la maqueta dejó al lado, y no se atribuye.
    letras = [c for c in nombre if c.isalpha()]
    if letras and sum(1 for c in letras if c.isupper()) / len(letras) > 0.7:
        return nombre, 'santo'
    return nombre, None


# «MR pp. 731 y 923 [752 y 962]»: dos formularios, no un intervalo. La fase 3
# dejó `mr_paginas` en null en 245 casos porque su patrón no contaba con la
# «y». La página del Misal impreso no decide nada —una sola página puede abrir
# un común con diez colectas distintas—, pero corrobora.
MR = re.compile(r'MR\s*pp?\.?\s*([\d\s,y–—-]+?)\s*(?:\[|/|$)', re.I)


def paginas_mr(cab):
    m = MR.search(cab.get('mr') or '')
    if not m:
        return None
    return re.sub(r'\s+', ' ', m.group(1)).strip(' ,-') or None


# --------------------------------------------------------------------------
# B. las citas
# --------------------------------------------------------------------------
#
# La pieza viene con su cita, y eso es lo que permite comprobar el
# emparejamiento por un camino independiente del calendario. Hay dos formas:
#
#  · las lecturas la llevan **dentro del texto**, en el renglón del incipit:
#    «Del primer libro de Samuel 1, 9-20», «Del santo Evangelio según san
#    Marcos 1, 14-20». Son 141 formas distintas en el corpus, todas con el
#    mismo armazón, y el nombre del libro sale de `data/books.json`, que es
#    la tabla puente que el leccionario ya usa;
#  · las antífonas y la aclamación la llevan **en su propio campo**, y ahí ya
#    viene en sigla («Cfr. Sal 33, 6»), que es la forma del leccionario.

# El armazón del incipit, que se quita para quedarse con el nombre del libro.
EVANGELIO_DE = re.compile(
    r'^\s*(?:lectura\s+)?del\s+santo\s+evangelio\s+seg[uú]n\s+(?:san\s+)?',
    re.I)
ARMAZON = re.compile(
    r'^\s*(?:santa\s+)?(?:lectura|comienzo|principio|inicio)?\s*'
    r'(?:de\s+la|de\s+los|de\s+las|del|de)?\s*', re.I)

ORDINAL = {'primer': 1, 'primero': 1, 'primera': 1, 'segundo': 2,
           'segunda': 2, 'tercer': 3, 'tercero': 3, 'tercera': 3,
           'cuarto': 4, 'cuarta': 4}

# Lo que el nombre del libro lleva encima y no distingue a un libro de otro.
# El ordinal también se quita —se ha leído antes, de la misma cadena—, porque
# si no «primer libro de los Reyes» y «segundo libro de los Reyes» caerían en
# dos claves distintas y ninguna de las dos estaría en la tabla.
RELLENO = re.compile(
    r'\b(libros?|cartas?|profecias?|profeta|apostol|apostoles|san|santo|'
    r'santa|evangelio|segun|de|del|los|las|el|la|a|al|y|parte|'
    r'primer[ao]?|segund[ao]|tercer[ao]?|cuart[ao]|forma|breve|larga|'
    r'[123])\b', re.I)

# Lo que la fuente antepone a la cita y no es la cita: la llamada a nota, la
# cruz del evangelio, el «Cfr.» —que además imprime cinco veces partido,
# «C fr.»— y el rótulo del salmo cuando además trae la sigla.
DELANTE = re.compile(
    r'^[^0-9A-Za-zÁ-ÿ]*(?:(?:c\s*fr?|cf)\s*\.?\s*|fr\.\s*)?'
    r'(?:del?\s+salmos?\s*:?\s*|salmos?\s*:\s*)?', re.I)

# El número que sigue al nombre del libro: capítulo, versículos y lo que la
# fuente le cuelgue. «1, 9-20», «2, 23—3, 6», «6, 8-9a. 9c-10».
NUMERO = re.compile(r'(\d{1,3}\s*[,.]\s*[\dl][\d\s.,;:a-e–—-]*)')
SIGLA_SUELTA = re.compile(
    r'^((?:[123]\s*)?[A-ZÁ-Ú][A-Za-zÁ-ÿ]{0,5}\.?)\s*([\dl].*)$')

# **El renglón que es la cita y nada más.** El salmo responsorial no siempre
# trae su cita pegada al rótulo: la mitad de las veces la fuente la imprime en
# el renglón de debajo —«Del salmo 71, 2. 7-8. 10-11. 12-13 R/. Que te adoren,
# Señor…»—, y ahí no la leía nadie: 3 268 salmos entraban sin cita, y una
# lectura sin cita no llega a ser perícopa, porque la perícopa se guarda **por
# cita**. Se lee ese renglón, cortado por la respuesta del pueblo, y sólo
# cuando una vez cortado no queda más que el nombre de un libro y números: es
# lo que distingue la cita del cuerpo del salmo, que empieza por palabras. El
# nombre del libro es **obligatorio** —un renglón que abre con un número a
# secas no vale—, porque `del_campo` da por salmo lo que empieza por cifra y
# el «11, 25» de una aclamación entraba como salmo 11.
CITA_SOLA = re.compile(
    r'^\s*(?:del?\s+(?:los\s+)?salmos?\b[\s:.]*'
    r'|(?:[123]\s*)?[A-ZÁ-Ú][A-Za-zÁ-ÿ]{0,12}\.?\s+)'
    r'[\dl][\dl\s.,;:a-e–—()y-]*$', re.I)

# «R/.», «R.», «R/»: donde empieza la respuesta del pueblo y acaba la cita.
RESPUESTA_DEL_PUEBLO = re.compile(r'\s*R\s*/?\s*\.')

# Las siglas con que la fuente cita, que no son las del leccionario. No se
# adivinan: son las 74 formas que el corpus usa y `books.json` no reconoce,
# contadas una por una. Las que ya coinciden con la sigla del leccionario no
# hacen falta aquí.
ALIAS_SIGLAS = {
    'apoc': 'Ap', 'sir': 'Eclo', 'ecli': 'Eclo', 'sab': 'Sb', 'heb': 'Hb',
    'hech': 'Hch', 'hechos': 'Hch', 'rom': 'Rm', 'gal': 'Ga', 'dan': 'Dn',
    'jer': 'Jr', 'bar': 'Ba', 'lam': 'Lm', 'mal': 'Ml', 'zac': 'Za',
    'prov': 'Pr', 'sant': 'St', 'stgo': 'St', 'tit': 'Tt', 'tob': 'Tb',
    'deut': 'Dt', 'gen': 'Gn', 'hab': 'Ha', 'fil': 'Flp', 'flm': 'Flm',
    'cant': 'Ct', 'num': 'Nm', 'lev': 'Lv', 'jos': 'Jos', 'jue': 'Jc',
    'neh': 'Ne', 'esd': 'Esd', 'ecle': 'Ecl', 'qoh': 'Ecl', 'miq': 'Mi',
    'sof': 'So', 'nah': 'Na', 'joel': 'Jl', 'abd': 'Ab', 'jon': 'Jon',
    'os': 'Os', 'am': 'Am', 'ag': 'Ag',
    # los dobles: la sigla sin el número, que `con_ordinal` le repone
    'cor': '1 Co', 'cro': '1 Cro', 'cron': '1 Cro', 'cr': '1 Cro',
    'pe': '1 P', 'pedro': '1 P', 'tes': '1 Ts', 'tim': '1 Tm',
    'sam': '1 S', 'reyes': '1 R', 'rey': '1 R', 'mac': '1 M',
}

# Los libros de un solo capítulo. El misalito cita «Judas 17.20-25» —el
# número es el versículo, porque no hay capítulo que citar— y el índice del
# leccionario escribe «Judas 1,17.20b-25», con el capítulo 1 explícito. Las
# dos formas dicen lo mismo y hay que escribir una.
UNICAPITULO = {'Judas', 'Flm', 'Ab', '2 Jn', '3 Jn'}

# Lo que la fuente imprime mal, con su prueba al lado. No se corrige en
# silencio: lo que esté aquí sale nombrado en el informe.
ERRATAS = {
    # Isaías tiene 66 capítulos, así que «Is 149» no existe; y el texto que
    # va debajo —«Entonen al Señor un canto nuevo, en la reunión litúrgica»—
    # es el salmo 149, en la ranura del salmo responsorial, tres veces.
    'Is 149': 'Sal 149',
}

EXTRA_LIBROS = {
    'apocalipsis juan': 'Ap', 'apocalipsis': 'Ap',
    'eclesiastico siracide': 'Eclo', 'siracide': 'Eclo',
    'eclesiastico sirac': 'Eclo', 'sirac': 'Eclo', 'eclesiastico': 'Eclo',
    'cantar cantares': 'Ct', 'qohelet': 'Ecl', 'eclesiastes': 'Ecl',
    'eclesiastes qohelet': 'Ecl',
    'hechos': 'Hch', 'hechos apostoles': 'Hch',
    'lamentaciones jeremias': 'Lm', 'lamentaciones': 'Lm',
    'mateo': 'Mt', 'marcos': 'Mc', 'lucas': 'Lc', 'juan': 'Jn',
    'santiago': 'St', 'judas': 'Judas', 'hebreos': 'Hb',
    'romanos': 'Rm', 'colosenses': 'Col', 'efesios': 'Ef',
    'filipenses': 'Flp', 'galatas': 'Ga', 'filemon': 'Flm',
    'tito': 'Tt', 'timoteo': '1 Tm', 'tesalonicenses': '1 Ts',
    'corintios': '1 Co', 'pedro': '1 P', 'reyes': '1 R',
    'samuel': '1 S', 'macabeos': '1 M', 'cronicas': '1 Cro',
    'salmos': 'Sal', 'salmo': 'Sal', 'sabiduria': 'Sb',
    'genesis': 'Gn', 'exodo': 'Ex', 'levitico': 'Lv', 'numeros': 'Nm',
    'deuteronomio': 'Dt', 'josue': 'Jos', 'jueces': 'Jc', 'rut': 'Rt',
    'esdras': 'Esd', 'nehemias': 'Ne', 'tobias': 'Tb', 'judit': 'Jdt',
    'ester': 'Est', 'job': 'Jb', 'proverbios': 'Pr',
}


def nucleo(nombre):
    """Las palabras que nombran el libro, sin el armazón ni el ordinal.

    Las letras sueltas separadas por un espacio se juntan antes: el PDF
    imprime catorce veces «M t», «L c» y «J n», que son la sigla con la caja
    partida, no dos palabras.
    """
    t = sinac(nombre)
    t = re.sub(r'\b([a-z])\s+([a-z])\b', r'\1\2', t)
    t = re.sub(r'[^a-z0-9ñ]+', ' ', t)
    t = RELLENO.sub(' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def tabla_de_libros():
    """Del nombre del libro en castellano a su sigla.

    Sale de `data/books.json`, que es la tabla que el leccionario ya usa, con
    la clave reducida a las palabras que de verdad nombran el libro: así
    «Del libro del profeta Isaías» y «Libro de Isaías» caen en la misma.
    """
    tabla = {}
    for e in json.load(open(os.path.join(DATA, 'books.json'),
                            encoding='utf-8')):
        nombres = list(e['es']) + list(e.get('match') or [])
        nombres.append(e['sigla'])
        nombres += list(e.get('siglas_alt') or [])
        for n in nombres:
            k = nucleo(n)
            if k:
                tabla.setdefault(k, e['sigla'])
    for k, v in EXTRA_LIBROS.items():
        tabla.setdefault(k, v)
    for k, v in ALIAS_SIGLAS.items():
        tabla.setdefault(k, v)
    return tabla


def ordinal_de(nombre):
    """El 1/2/3 del libro, escrito con letra o con cifra."""
    t = sinac(nombre)
    m = re.search(r'\b([123])\b', t)
    if m:
        return int(m.group(1))
    for p, n in ORDINAL.items():
        if re.search(r'\b' + p + r'\b', t):
            return n
    return None


def con_ordinal(sigla, n):
    """`1 S` dado `1 S` y 2 → `2 S`. Los libros simples no se tocan."""
    m = re.match(r'^([123])\s+(.*)$', sigla)
    if not m or not n:
        return sigla
    return '%d %s' % (n, m.group(2))


def normaliza_numero(resto, reparos=None):
    """«1, 9-20» → «1,9-20». La forma del índice del leccionario.

    Y una reparación nombrada: la fuente imprime once veces una ele donde va
    un uno («del salmo Sal 95, l-2a»). En un número de versículo una ele
    suelta no puede ser otra cosa, así que se repone el uno y el reparo se
    cuenta para el informe.
    """
    t = re.sub(r'\s+', '', resto)
    if 'l' in t:
        reparada = re.sub(r'(?<![a-z])l(?![a-z])', '1', t)
        if reparada != t and reparos is not None:
            reparos[resto.strip()] += 1
        t = reparada
    t = t.strip('.,;:-')
    # La coma separa el capítulo de los versículos **una vez**; de ahí en
    # adelante la fuente escribe unas veces punto y otras coma o dos puntos
    # («Sal 89,2,3-4,10,14.16», «Sal 95, l-2a: 2b-3»), y si no se unifica el
    # mismo salmo entra dos veces con la mitad de los testigos cada una.
    cabeza, sep, cola = t.partition(',')
    if sep:
        cola = re.sub(r'[,;:]', '.', cola)
        t = cabeza + ',' + cola
    else:
        # «Lc 9.57-62»: el punto está donde va la coma del capítulo
        t = re.sub(r'^(\d{1,3})\.', r'\1,', t)
    return t.replace('Y', 'y')


def squeeze(cita):
    """La forma con la que se cotejan dos citas, pase lo que pase con la
    puntuación. El salto de capítulo lo escribe el índice unas veces con raya
    («Jn 15,26—16,4a») y otras con punto («Gn 41,55-57.42,5-7»), y el
    misalito con punto y coma («Hch 11,21-26;13,1-3»): las tres formas dicen
    lo mismo, así que para cotejar las tres van a punto. El guión corto sí
    distingue, porque es el que marca el intervalo de versículos."""
    t = sinac(cita or '')
    for g in '–—‒;':
        t = t.replace(g, '.')
    t = t.replace('−', '-')
    return re.sub(r'[^a-z0-9,.\-]', '', t)


# --------------------------------------------------------------------------
# el renglón partido
# --------------------------------------------------------------------------
#
# El PDF corta la palabra al final del renglón y deja el guión: «…divino
# poder dispon-» / «gas nuestros corazones…». Si no se junta, los ocho
# testigos de una misma oración se parten en dos grupos y la mayoría decide
# sobre un reparto falso —y el texto canónico sale con «dispon- gas» dentro—.
# Se junta cuando el renglón acaba en guión y el siguiente empieza en
# minúscula, que es el único caso en que el guión no es del texto.

PARTIDA = re.compile(r'-$')


def junta(lineas, reparos=None):
    """Las líneas con las palabras partidas por el renglón ya enteras."""
    salida = []
    for ln in lineas:
        if (salida and PARTIDA.search(salida[-1])
                and re.match(r'^[a-záéíóúüñ]', ln)):
            corte = re.split(r'\s+', salida[-1])[-1][:-1]
            salida[-1] = salida[-1][:-1] + re.split(r'\s+', ln, 1)[0]
            resto = re.split(r'\s+', ln, 1)
            if reparos is not None:
                reparos[corte + '|' + resto[0][:14]] += 1
            if len(resto) > 1:
                salida.append(resto[1])
            continue
        salida.append(ln)
    return salida


class Citas:
    """Lee la cita de una pieza. Lo que no sepa leer lo cuenta y lo nombra."""

    EVANGELISTAS = ('Mt', 'Mc', 'Lc', 'Jn')

    def __init__(self):
        self.tabla = tabla_de_libros()
        self.fallos = Counter()
        self.leidas = Counter()
        self.reparos = Counter()
        self.erratas = Counter()
        self.letras = Counter()

    def remata(self, sigla, numero):
        """La cita ya leída, puesta en la forma del índice del leccionario.

        Tres cosas, y las tres son diferencias de escritura entre las dos
        ediciones, no lecturas dudosas:

         · los libros de un solo capítulo llevan el capítulo 1 explícito;
         · el misalito parte algunos salmos con una letra («Sal 113A», «Sal
           18B») y da otros con la doble numeración entre paréntesis («Sal
           87(86)»); el índice no hace ni lo uno ni lo otro, y los
           versículos bastan para distinguir las dos mitades;
         · y lo que la fuente imprime mal va por la tabla de erratas.
        """
        if sigla in UNICAPITULO and numero:
            cabeza, sep, cola = numero.partition(',')
            numero = '1,' + cabeza + ('.' + cola if sep and cola else '')
        if sigla == 'Sal' and numero:
            cabeza, sep, cola = numero.partition(',')
            # Sólo cuando el capítulo es exactamente un número con una letra
            # pegada («113A») o con la otra numeración entre paréntesis
            # («87(86)»). Sin esa estrechez, la regla recortaba la última
            # letra de citas que la fuente ya había impreso mal y donde no
            # hay nada que reparar, sino que decir.
            limpia = None
            if re.fullmatch(r'\d{1,3}[A-Za-z]', cabeza):
                limpia = cabeza[:-1]
            elif re.fullmatch(r'\d{1,3}\(\d{1,3}\)', cabeza):
                limpia = cabeza.split('(')[0]
            if limpia:
                self.letras[cabeza] += 1
                numero = limpia + (sep + cola if sep else '')
        cita = sigla + (' ' + numero if numero else '')
        for mal, bien in ERRATAS.items():
            if cita == mal or cita.startswith(mal + ' ') or \
                    cita.startswith(mal + ','):
                arreglada = bien + cita[len(mal):]
                self.erratas[(cita, arreglada)] += 1
                return arreglada
        return cita

    def sigla_de(self, nombre):
        """La sigla del libro que nombra `nombre`, o None.

        Busca la clave entera y, si no la halla, los prefijos de palabras de
        izquierda a derecha: así «libro del profeta Isaías: Is» cae en
        «isaias» y «libro del Eclesiastés (Cohélet)» en «eclesiastes», sin
        una tabla por cada manera de escribirlo.
        """
        n = re.sub(r'(?<=\d)(?=[A-Za-zÁ-ÿ])', ' ', nombre)   # «1Cor» → «1 Cor»
        ordinal = ordinal_de(n)
        k = nucleo(n)
        if not k:
            return None
        tk = k.split()
        for largo in range(len(tk), 0, -1):
            cand = ' '.join(tk[:largo])
            for prueba in (cand, cand + 's', cand.rstrip('s')):
                if prueba in self.tabla:
                    return con_ordinal(self.tabla[prueba], ordinal)
        return None

    def del_incipit(self, lineas):
        """La cita de una lectura, del renglón del incipit.

        El incipit no es siempre el primer renglón: delante puede ir el
        sumario entre corchetes. Y a veces la cita se parte en dos renglones
        («…a Filemón 9b-» / «10.12-17»), así que se prueba también cada
        renglón pegado al siguiente.
        """
        ls = [ln for ln in (lineas or [])[:6]]
        for i, ln in enumerate(ls[:5]):
            c = self._una(ln)
            if c:
                return c
            if ln.rstrip().endswith(('-', '–', '—')) and i + 1 < len(ls):
                c = self._una(ln.rstrip() + ls[i + 1].lstrip())
                if c:
                    return c
        return None

    def del_campo(self, cita):
        """La cita de una antífona o de la aclamación, de su propio campo.

        Viene ya en sigla, pero escrita a mano: «Cfr. Sal 33, 6», «del salmo
        115», «Jn 3, 16».
        """
        if not cita:
            return None
        t = re.sub(r'\s+', ' ', cita).strip()
        if t.startswith('['):             # «[Opcional]», que no es una cita
            return None
        t = DELANTE.sub('', t, count=1)
        # La sigla primero: el misalito rotula «del salmo» también los
        # cánticos, y detrás del rótulo viene el libro («del salmo 1 Samuel
        # 2, 1. 4-5»). Si se diera por supuesto que lo que sigue a «salmo» es
        # un número de salmo, el cántico de Ana entraría como salmo 1.
        m = SIGLA_SUELTA.match(t)
        if m:
            sigla = self.sigla_de(m.group(1))
            if sigla:
                resto = m.group(2)
                # «Sal 1Cron 29,10», «Sal 2Tim 1,10»: el rótulo es «Sal» y el
                # libro viene detrás, porque el misalito llama salmo también
                # al cántico. Si lo que sigue a la sigla vuelve a parecer una
                # cita, la de dentro es la de verdad.
                if sigla == 'Sal':
                    m2 = SIGLA_SUELTA.match(resto)
                    if m2:
                        dentro = self.sigla_de(m2.group(1))
                        if dentro and dentro != 'Sal':
                            self.leidas['sigla'] += 1
                            return self.remata(dentro, normaliza_numero(
                                m2.group(2), self.reparos))
                self.leidas['sigla'] += 1
                return self.remata(sigla, normaliza_numero(resto,
                                                           self.reparos))
        if re.match(r'^[\dl]', t):
            self.leidas['salmo'] += 1
            return self.remata('Sal', normaliza_numero(t, self.reparos))
        return self._una(t)

    def del_renglon(self, lineas):
        """La cita del salmo, del renglón que no es más que ella.

        `del_campo` lee la cita de su propio campo y `del_incipit` la del
        incipit de la lectura; esto lee la tercera manera en que la fuente la
        imprime, y es la del salmo responsorial: un renglón propio, con la
        respuesta del pueblo detrás. Se corta por la respuesta y se exige que
        lo que queda sea **sólo** un libro y números, que es lo que lo
        distingue del cuerpo. Lo laxo aquí sale caro: sin esa exigencia, un
        «De la segunda carta del apóstol san Pablo a los tesalonicenses» se
        leía como el salmo 1 y una aclamación entera como el salmo 11.
        """
        for ln in (lineas or [])[:1]:
            m = RESPUESTA_DEL_PUEBLO.search(ln)
            t = (ln[:m.start()] if m else ln).strip()
            if not t or len(t) > 80 or not CITA_SOLA.match(t):
                return None
            antes = self.leidas.copy()
            c = self.del_campo(t)
            if c:
                # la cuenta es de **dónde** salió la cita, no de qué camino la
                # leyó: se deshace lo que `del_campo` apuntó al pasar
                self.leidas.clear()
                self.leidas.update(antes)
                self.leidas['renglón'] += 1
            return c
        return None

    def _una(self, linea):
        t = re.sub(r'\s+', ' ', (linea or '').strip())
        if not t:
            return None
        t = re.sub(r'^\[[^\]]*\]\s*', '', t)      # el sumario, si va delante
        t = DELANTE.sub('', t, count=1)
        m = NUMERO.search(t)
        if not m:
            return None
        nombre, resto = t[:m.start()], m.group(1)
        if not nombre.strip():
            return None
        evang = bool(EVANGELIO_DE.match(nombre))
        if evang:
            nombre = EVANGELIO_DE.sub('', nombre, count=1)
        else:
            nombre = ARMAZON.sub('', nombre, count=1)
        sigla = self.sigla_de(nombre)
        if not sigla:
            self.fallos[nombre.strip()[:48]] += 1
            return None
        if evang and sigla not in self.EVANGELISTAS:
            self.fallos['(evangelio) ' + nombre.strip()[:36]] += 1
            return None
        self.leidas['incipit'] += 1
        return self.remata(sigla, normaliza_numero(resto, self.reparos))


# --------------------------------------------------------------------------
# C. el calendario: qué se podía celebrar cada día
# --------------------------------------------------------------------------

VACIAS = {'san', 'santa', 'santo', 'santos', 'santas', 'beato', 'beata',
          'obispo', 'obispos', 'presbitero', 'presbiteros', 'martir',
          'martires', 'virgen', 'virgenes', 'abad', 'religiosa', 'religioso',
          'doctor', 'doctora', 'iglesia', 'misa', 'del', 'los', 'las',
          'nuestra', 'senora', 'papa', 'diacono', 'apostol', 'apostoles',
          'memoria', 'fiesta', 'solemnidad', 'libre'}


def palabras(t):
    p = {w for w in re.findall(r'[a-z0-9]+', sinac(t)) if len(w) > 2}
    return p - VACIAS


def parecido(a, b):
    """Las palabras que comparten dos títulos, sobre las del más corto. El
    misalito escribe «SAN ROMUALDO, Abad» y el calendario «San Romualdo,
    abad»; pero también «SANTA TERESA DE CALCUTA» donde el calendario pone
    «Santa Teresa de Calcuta, religiosa»."""
    pa, pb = palabras(a), palabras(b)
    if not pa or not pb:
        return 0.0
    return len(pa & pb) / min(len(pa), len(pb))


def slug(nombre):
    t = sinac(nombre)
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t[:60]


MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def nombre_de_fecha(base):
    """`md_05-17` → «celebración del 17 de mayo». La celebración existe —el
    misalito la reza— pero el calendario del proyecto no le da nombre, y
    poner uno inventado sería peor que decir dónde está."""
    m = re.match(r'^md_(\d{2})-(\d{2})$', base)
    if not m:
        return base
    return 'celebración del %d de %s' % (int(m.group(2)),
                                         MESES[int(m.group(1)) - 1])


def candidatos_del_dia(cal):
    """fecha → [(id, k, grado, título)] en orden de precedencia.

    El calendario del proyecto trae ya resuelta la precedencia, y trae
    también las memorias libres que ese día **se podían** celebrar aunque no
    manden: son justo las que el misalito reza unos años y no otros, así que
    hacen falta todas.
    """
    return {iso: [(o[0], o[2].get('k'), o[2].get('g'), o[2].get('t'))
                  for o in e['c']]
            for iso, e in cal['fechas'].items()}


def santoral_por_fecha(cal):
    """(mes, día) → [entradas del santoral], para reconocer al santo que la
    fuente nombra al lado de la cabecera."""
    por = defaultdict(list)
    for e in cal['santoral']:
        if e.get('mes') and e.get('dia'):
            por[(e['mes'], e['dia'])].append(e)
    return por


def comunes_del_santoral(cal):
    """id de celebración → {id del común: etiqueta}.

    El santoral del proyecto ya dice de qué común puede tomar sus textos cada
    santo —«Común de pastores», «Común de doctores de la Iglesia»—, con la
    clave del leccionario. Eso es lo que permite **nombrar** un común en vez
    de dejar su texto suelto: una antífona que se imprime en los días de
    cuarenta santos distintos no es de ninguno de ellos, pero sí del común
    que los cuarenta comparten, y el reparto no hay que suponerlo porque
    está medido en el santoral.
    """
    por = {}
    etiquetas = {}
    for e in cal['santoral']:
        cs = {}
        for b in e.get('bloques') or []:
            if b['etiqueta'] == 'Propio':
                continue
            cid = 'comun_' + b['clave'][1].replace('.html', '')
            cs[cid] = b['etiqueta']
            etiquetas[cid] = b['etiqueta']
        if cs:
            por[e['slug']] = cs
    return por, etiquetas


# --------------------------------------------------------------------------
# la carga
# --------------------------------------------------------------------------

class Formulario:
    """Un formulario del misalito, con lo que hace falta para atribuirlo."""

    def __init__(self, mes, orden, bruto, citas, reparos=None):
        self.fichero = mes
        self.fecha = bruto['fecha']
        self.orden = orden      # el de ese día, no el del mes
        self.origen = 'misalito'  # lo pone `carga`; aquí, el valor de siempre
        self.misa = bruto.get('misa')
        self.cab = bruto['cabecera']
        self.mr = paginas_mr(self.cab)
        self.alt, self.alt_clase = alternativa_de(self.cab)
        self.titulo = self.cab.get('titulo')
        self.resena = self.cab.get('resena')
        self.piezas = {}          # ranura → {texto, cita, sumario}
        self.otras = []           # las lecturas de una ranura repetida
        self.rubricas = []
        self.cel = None           # la celebración a la que se atribuye
        for b in bruto['bloques']:
            if b['clase'] == 'rubrica':
                self.rubricas.append(
                    dict(b, texto=junta([ln for ln in b['texto']
                                         if ln.strip()], reparos)))
                continue
            if b['clase'] != 'pieza':
                continue
            ran = DE_ROTULO.get(b.get('rotulo'))
            if not ran:
                continue
            # **Una ranura repetida no es un bloque de sobra.** El formulario
            # tiene una ranura de cada cosa, y la primera manda: es lo que
            # decide qué se atribuye a la celebración y qué cita lleva el día.
            # Pero la Vigilia Pascual canta **ocho** salmos y la fuente
            # imprime, en los días que dan opción, la memoria detrás de la
            # feria sin repetir la antífona de entrada, así que la segunda
            # misa entera entra como repetición. Tirarlas perdía 279 lecturas
            # impresas —los salmos de la Vigilia entre ellas—, y son perícopas
            # buenas: la perícopa se guarda por cita y no por ranura, así que
            # van aparte, a la cosecha, sin tocar ni la atribución ni el día.
            repetida = ran in self.piezas
            if repetida and CLASE_DE[ran] != 'lectura':
                continue
            texto = junta([ln for ln in b['texto'] if ln.strip()], reparos)
            if not texto:
                continue
            if CLASE_DE[ran] == 'lectura':
                cita = (citas.del_campo(b.get('cita'))
                        or citas.del_incipit(texto)
                        or citas.del_renglon(texto))
            else:
                cita = citas.del_campo(b.get('cita'))
            pieza = {'texto': texto, 'cita': cita,
                     'sumario': b.get('sumario')}
            if repetida:
                self.otras.append(dict(pieza, ranura=ran))
            else:
                self.piezas[ran] = pieza

    @property
    def testigo(self):
        return '%s/%d' % (self.fecha, self.orden)

    @property
    def anio(self):
        return int(self.fecha[:4])


def carga(citas, reparos=None):
    """Los formularios de las **dos** fuentes castellanas, en un solo montón.

    Los cien misalitos (fase 3) y el sitio misalcatolico.com (fase 3c), que
    deja su cosecha en la misma forma precisamente para poder entrar por
    aquí. Cada formulario se queda con el nombre de su fuente en `origen`,
    porque de eso depende leer bien el recuento de testigos: dos fuentes que
    publican el mismo día no son dos testigos independientes de la
    *elección* del editor, aunque sí de su *texto*.

    El sitio imprime además lo que va **antes** de la misa —la bendición de
    las palmas, con su propio evangelio—, y eso no es un formulario del
    Misal: se deja fuera aquí, no en la fase 3c, que lo guarda rotulado.
    """
    # Primero se juntan en bruto, y luego se numeran: el número de testigo
    # —`fecha/n`— tiene que ser el **mismo** que la posición que el
    # formulario ocupa en la lista de su día en `dias_es.json`, porque la
    # fase 5 cruza las dos cosas por esa cadena (`lo_impreso` contra
    # `dias_por_cel`). Numerar por fuente los descuadraría en cuanto un día
    # lo traigan las dos, y el paso «del día» de la cascada —el que salva lo
    # que no se puede atribuir— empezaría a fallar en silencio.
    crudos = []
    for origen, carpeta in (('misalito', MISALITOS), ('sitio', WEB)):
        if not os.path.isdir(carpeta):
            continue
        for ruta in sorted(glob.glob(os.path.join(carpeta, '*.json'))):
            mes = os.path.basename(ruta)[:-5]
            if mes == 'secciones':
                continue
            d = json.load(open(ruta, encoding='utf-8'))
            brutos = [b for b in d['formularios']
                      if b.get('parte', 'misa') == 'misa' and b.get('fecha')]
            # `unico` sigue siendo **por fuente**: dice que ese editor
            # imprimió un solo formulario ese día, o sea que no le dio
            # opción, y de eso depende la atribución. Contarlo sobre las dos
            # fuentes lo volvería falso casi siempre, porque casi todos los
            # días los traen las dos.
            cuantas = Counter(b['fecha'] for b in brutos)
            for bruto in brutos:
                crudos.append((origen, mes, bruto,
                               cuantas[bruto['fecha']] == 1))

    formularios = []
    deldia = Counter()
    for origen, mes, bruto, unico in crudos:
        n = deldia[bruto['fecha']]
        deldia[bruto['fecha']] += 1
        f = Formulario(mes, n, bruto, citas, reparos)
        f.unico = unico
        f.origen = origen
        formularios.append(f)
    return formularios


# --------------------------------------------------------------------------
# D. los prefacios que el día nombra, y los que el día imprime
# --------------------------------------------------------------------------
#
# La rúbrica del prefacio hace dos cosas distintas, y hay que separarlas:
#
#  · **nombra** uno de los 67 del Ordinario —«Prefacio I o III de Adviento,
#    pp. 484-486»—, y entonces lo que hace falta es resolver la referencia
#    contra `prefacios_es.json`. Son 502 rúbricas;
#  · **imprime uno entero**, y entonces es un prefacio **propio**, de los que
#    no están en ningún juego común porque viven dentro de su formulario
#    —Pentecostés, la Transfiguración, la Asunción, san Juan Bautista—. Son
#    200 rúbricas, y de ellas salen los propios con sus testigos.

ROMANOS = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']
ORDEN_ROMANO = {r: i + 1 for i, r in enumerate(ROMANOS)}

# «PREFACIO: La misión del Precursor. En verdad es justo…»: el título va
# delante del texto, y el texto empieza siempre por la misma fórmula, que es
# lo que separa un prefacio impreso de una referencia.
IMPRESO = re.compile(r'\bEn verdad es justo\b')
TITULO_IMPRESO = re.compile(
    r'^\s*PREFACIO\s*:?\s*(.{0,90}?)\s*\.?\s*(?=En verdad es justo)')

# «Prefacio I o III de Adviento», «Prefacio I-V de Pascua», «Prefacio de la
# Epifanía». Los números pueden venir sueltos («I o II»), en intervalo
# («I-III») o no venir.
# El número puede ir delante del nombre («Prefacio I o III de Adviento») o
# detrás («Prefacio común I», «Prefacio pascual II»), así que no se puede
# exigir en un sitio: se coge el trozo entero y se le saca el número donde
# esté. Con el número exigido delante, los nueve prefacios comunes y los
# cinco pascuales se quedaban sin resolver, que eran 257 referencias.
REFERENCIA = re.compile(r'Prefacio\s+([^,.;:()\[\]—]{1,80})', re.I)
ROMANO = re.compile(r'\b([IVX]{1,4})\b')


def numeros_de(trozo):
    """«I o III» → [1, 3]; «I-V» → [1, 2, 3, 4, 5]."""
    if not trozo:
        return []
    ns = [ORDEN_ROMANO[r.lower()] for r in re.findall(r'[IVX]+', trozo)
          if r.lower() in ORDEN_ROMANO]
    if re.search(r'[-–]', trozo) and len(ns) == 2 and ns[0] < ns[1]:
        return list(range(ns[0], ns[1] + 1))
    return ns


# Las palabras que sobran en el nombre de un prefacio. **No** vale la lista
# de los títulos de santos: ahí «apóstoles», «mártires» y «vírgenes» son
# ruido que estorba, y aquí son precisamente lo que nombra el prefacio. Con
# la lista de los santos, «Prefacio I o II de los Apóstoles» se quedaba sin
# una palabra con que buscar, y eran 213 referencias sin resolver.
VACIAS_PREF = {'prefacio', 'del', 'los', 'las', 'para', 'con', 'que',
               'este', 'dice'}


def palabras_pref(t):
    p = {w for w in re.findall(r'[a-z0-9]+', sinac(t)) if len(w) > 2}
    return p - VACIAS_PREF


def casa_titulo(nombre, numero, prefacios, clave_titulo='titulo'):
    """La referencia del día contra los títulos de los prefacios.

    Se exige que el número romano coincida y que las palabras del nombre
    estén en el título. La comparación es por prefijo de cinco letras porque
    el día cita «de Pascua» y el Ordinario titula «PREFACIO PASCUAL».
    Devuelve la lista de los que casan, que para una referencia sin número
    —«Prefacio de los santos mártires»— son los dos del juego.
    """
    pal = palabras_pref(nombre)
    if not pal:
        return []
    puntos = []
    for pid, p in prefacios.items():
        titulo = p[clave_titulo]
        tpal = palabras_pref(ROMANO.sub(' ', titulo))
        if not tpal:
            continue
        n_tit = numeros_de(' '.join(ROMANO.findall(titulo)))
        if numero and (not n_tit or n_tit[0] != numero):
            continue
        casan = sum(1 for w in pal if any(t[:5] == w[:5] for t in tpal))
        punt = casan / len(pal)
        if punt >= 0.6:
            puntos.append((punt, -len(tpal), pid, bool(n_tit)))
    if not puntos:
        return []
    puntos.sort(reverse=True)
    # Sin número en la referencia manda el título sin número, si lo hay; si
    # no, valen todos los del juego, que es lo que el día ofrece.
    if numero is None:
        sin_n = [p for p in puntos if not p[3] and p[0] == puntos[0][0]]
        if sin_n:
            return [sin_n[0][2]]
        return sorted(p[2] for p in puntos if p[0] == puntos[0][0])
    return [puntos[0][2]]


class Prefacios:
    """Los prefacios del día: los que nombra y los que imprime."""

    def __init__(self, prefacios_es):
        self.comunes = prefacios_es
        self.propios = defaultdict(lambda: {'textos': Counter(),
                                            'por_clave': {},
                                            'testigos': defaultdict(list)})
        self.sin_resolver = Counter()
        self.sin_nombre = Counter()
        self.citados = Counter()
        self.crudas = defaultdict(list)
        self.veces = 0
        self.sin_contar = 0

    def lee(self, f):
        """Apunta lo que el formulario dice del prefacio.

        En dos pasadas, y hace falta que sean dos: un día cita «Prefacio de
        Pentecostés», que no está en los 67 del Ordinario porque es **propio**
        y vive dentro de su formulario. Para resolver esa referencia hay que
        haber cosechado antes los propios, y los propios salen de los días.
        Así que la primera pasada cosecha y apunta, y `resuelve` empareja.
        """
        for b in f.rubricas:
            if b.get('rotulo') != '@prefacio':
                continue
            texto = [ln for ln in b['texto'] if ln.strip()]
            entero = ' '.join(texto)
            if IMPRESO.search(entero):
                self._propio(f, texto, entero)
                self.crudas[f.testigo].append('@propio')
                continue
            for m in REFERENCIA.finditer(entero):
                self.crudas[f.testigo].append(m.group(1))

    def resuelve(self, propios_cosechados):
        """De las referencias apuntadas a los identificadores. testigo → ids."""
        memoria = {}
        salida = {}
        for testigo, trozos in self.crudas.items():
            ids = []
            for trozo in trozos:
                if trozo not in memoria:
                    memoria[trozo] = self._uno(trozo, propios_cosechados)
                # el recuento es de apariciones, no de formas: la referencia
                # se resuelve una vez y se cuenta todas
                self.veces += len(memoria[trozo])
                if not memoria[trozo]:
                    self.sin_contar += 1
                ids += memoria[trozo]
            vistos, orden = set(), []
            for p in ids:
                if p not in vistos:
                    vistos.add(p)
                    orden.append(p)
            salida[testigo] = orden
        return salida

    def _uno(self, trozo, propios_cosechados):
        if trozo == '@propio':
            return ['@propio']
        # «Prefacio propio» (y «Prefacio propio, pp. 864»): la rúbrica remite
        # al prefacio del propio formulario, y no nombra ninguno.
        if re.match(r'^\s*propi[ao]s?\b', trozo, re.I):
            self.citados['@propio'] += 1
            return ['@propio']
        if not palabras_pref(ROMANO.sub(' ', trozo)):
            self.sin_nombre[re.sub(r'\s+', ' ', trozo).strip()[:40]] += 1
            return []
        ns = numeros_de(trozo)
        nombre = ROMANO.sub(' ', trozo)
        hallados = []
        for n in (ns or [None]):
            pids = casa_titulo(nombre, n, self.comunes)
            if not pids:
                pids = casa_titulo(nombre, n, propios_cosechados)
            if pids:
                for pid in pids:
                    hallados.append(pid)
                    self.citados[pid] += 1
            else:
                etiqueta = 'Prefacio %s%s' % (
                    ('%s ' % n) if n else '',
                    re.sub(r'\s+', ' ', nombre).strip()[:46])
                self.sin_resolver[etiqueta] += 1
        return hallados

    def _propio(self, f, texto, entero):
        m = TITULO_IMPRESO.match(entero)
        titulo = re.sub(r'\s+', ' ', m.group(1)).strip(' .:') if m else ''
        if not titulo:
            titulo = 'sin título'
        pid = 'propio-' + slug(titulo)
        # el cuerpo empieza en «En verdad es justo»
        cuerpo = list(texto)
        for i, ln in enumerate(cuerpo):
            if IMPRESO.search(ln):
                cuerpo = cuerpo[i:]
                cuerpo[0] = IMPRESO.sub('En verdad es justo',
                                        cuerpo[0][IMPRESO.search(
                                            cuerpo[0]).start():], count=1)
                break
        ck = clave(' '.join(cuerpo))
        p = self.propios[pid]
        p['titulo'] = titulo
        p['textos'][ck] += 1
        p['por_clave'].setdefault(ck, cuerpo)
        p['testigos'][ck].append(f.testigo)


# --------------------------------------------------------------------------
# E. la atribución: a qué celebración pertenece cada texto
# --------------------------------------------------------------------------

def candidatos(f, cal_fechas, santoral_md, comunes_de, avisos):
    """Las celebraciones que podrían explicar este formulario.

    Son las del calendario del proyecto para esa fecha, más la que la fuente
    nombra al lado de la cabecera, que es la que de verdad manda cuando está.
    Si el formulario es una de las misas propias de un día con varias (la
    vespertina de la vigilia, la de la aurora, la del día), todas llevan el
    sufijo de esa misa: lo que se reza en la vigilia no es testigo de lo que
    se reza en el día.
    """
    # El sufijo de la misa sólo cuando el día de verdad trae más de una. La
    # fuente rotula «MISA DEL DÍA» unos años y otros no —el 24 de junio lo
    # rotula en 2020 y 2021 y lo calla en los otros siete—, así que
    # sufijarlo siempre dejaba el mismo texto en dos juegos de candidatos que
    # no se cortan, y las cinco piezas de san Juan Bautista se quedaban
    # huérfanas. Si el día trae una sola misa, el formulario vale como
    # testigo de las dos formas.
    sufijos = ['']
    if f.misa:
        sufijos = ['#' + slug(f.misa)] + ([''] if f.unico else [])
    sufijo = sufijos[0]
    ids = {}
    for cid, k, grado, titulo in cal_fechas.get(f.fecha, []):
        for s in sufijos:
            ids[cid + s] = ('calendario', titulo)
    # La fecha del año, siempre. El misalito celebra santos que el calendario
    # del proyecto no trae —san Pascual Bailón, santa Rita, Nuestra Señora de
    # Fátima: el propio de México—, y sin esto sus textos no tienen ninguna
    # celebración que los explique y se quedan fuera. Un texto que sólo
    # aparece los 17 de mayo es de una celebración del 17 de mayo, se llame
    # como se llame, y eso no hay que suponerlo: se mide igual que lo demás.
    for s in sufijos:
        ids['md_' + f.fecha[5:] + s] = ('fecha', None)
    # Y los comunes de los santos que ese día se podían celebrar.
    for cid, k, grado, titulo in cal_fechas.get(f.fecha, []):
        for com, etiqueta in (comunes_de.get(cid) or {}).items():
            for s in sufijos:
                ids[com + s] = ('comun', etiqueta)
    etiqueta = None
    if f.alt_clase == 'misa':
        etiqueta = 'vot_' + slug(f.alt)
        ids[etiqueta + sufijo] = ('fuente', f.alt)
    elif f.alt_clase == 'santo':
        mes, dia = int(f.fecha[5:7]), int(f.fecha[8:10])
        mejor, punt = None, 0.0
        for e in santoral_md.get((mes, dia), []):
            p = parecido(f.alt, e['titulo'])
            if p > punt:
                mejor, punt = e, p
        if mejor and punt >= 0.5:
            etiqueta = mejor['slug']
            ids[etiqueta + sufijo] = ('fuente', mejor['titulo'])
        else:
            etiqueta = 'san_' + slug(f.alt)
            ids[etiqueta + sufijo] = ('fuente', f.alt)
            avisos.append((f.testigo, 'la fuente ofrece «%s» y el calendario '
                           'no trae ese santo ese día' % f.alt[:44]))
    f.etiqueta = (etiqueta + sufijo) if etiqueta else None
    # La celebración que la cabecera titula, que decide entre dos santos del
    # mismo día.
    f.titulada = None
    if f.titulo:
        mejor, punt = None, 0.0
        for cid, k, grado, titulo in cal_fechas.get(f.fecha, []):
            p = parecido(f.titulo, titulo or '')
            if p > punt:
                mejor, punt = cid + sufijo, p
        if punt >= 0.5:
            f.titulada = mejor
        else:
            # Y si lo que titula no está entre las celebraciones que el
            # calendario pone ese día, se busca **en todo el santoral**,
            # porque son los **traslados**: en 2022 el 24 de junio fue el
            # Sagrado Corazón y el misalito pasó la Natividad de san Juan
            # Bautista al 23, donde el calendario del proyecto sólo tiene la
            # feria. Con un solo día así, la intersección de celebraciones se
            # queda vacía y las cinco piezas de la solemnidad se van
            # huérfanas. Manda lo que la fuente titula, que es la regla del
            # módulo; el umbral es más alto porque aquí la fecha no acota, y
            # el empate descarta.
            cands_s = []
            for lista in santoral_md.values():
                for e in lista:
                    p = parecido(f.titulo, e['titulo'])
                    if p >= 0.7:
                        cands_s.append((p, e['slug'], e['titulo']))
            cands_s.sort(reverse=True)
            if cands_s and (len(cands_s) == 1 or cands_s[0][0] > cands_s[1][0]):
                f.titulada = cands_s[0][1] + sufijo
                for s in sufijos:
                    ids[cands_s[0][1] + s] = ('trasladada', cands_s[0][2])
                avisos.append((f.testigo, 'la fuente titula «%s» y el '
                               'calendario no lo pone ese día: se toma de su '
                               'fecha propia' % f.titulo[:40]))
    return ids


def atribuye(formularios, cands, cuantos):
    """Para cada ranura y cada texto, la celebración que lo explica.

    La regla, y es la que hay que no volver a derivar: **manda el conjunto de
    días**. Un texto pertenece a la celebración que está presente en todos
    los días en que la fuente lo imprimió, y a ninguna si no hay ninguna así.
    Entre varias, manda la que la fuente nombra; después, la que la cabecera
    titula; después, el santo antes que el tiempo, porque el tiempo está
    todos los días y no distingue; y a igualdad, la de menos días, que es la
    más específica.
    """
    donde = defaultdict(lambda: defaultdict(list))
    textos = {}
    for f in formularios:
        for ran, p in f.piezas.items():
            if CLASE_DE[ran] != 'propio':
                continue
            ck = clave(' '.join(p['texto']))
            if not ck:
                continue
            donde[ran][ck].append(f)
            textos.setdefault((ran, ck), p)

    asignado = {}       # (ranura, ck) → (id, motivo)
    huerfanos = []
    salvo = []          # lo atribuido con una excepción, para el informe
    for ran, porclave in donde.items():
        for ck, fs in porclave.items():
            comunes = None
            for f in fs:
                ids = set(cands[f.testigo])
                comunes = ids if comunes is None else (comunes & ids)
            excepcion = None
            if not comunes:
                # Todos los días menos uno. La fuente se desvía de vez en
                # cuando del calendario del proyecto —en 2022 el 24 de junio
                # fue el Sagrado Corazón y pasó la Natividad de san Juan
                # Bautista al 23, diciéndolo en un corchete que no vuelve a
                # usar—, y con un solo día así la intersección se queda
                # vacía y las cinco piezas de una solemnidad se van
                # huérfanas. Se admite **una** excepción, y sólo con cuatro
                # días o más, y la excepción se nombra en el informe.
                if len(fs) >= 4:
                    cobertura = Counter()
                    for f in fs:
                        for cid in cands[f.testigo]:
                            cobertura[cid] += 1
                    tope = len(fs) - 1
                    mejores = [c for c, n in cobertura.items() if n >= tope]
                    if mejores:
                        comunes = set(mejores)
                        excepcion = [f.testigo for f in fs
                                     if not (set(cands[f.testigo])
                                             & comunes)]
            if not comunes:
                huerfanos.append((ran, ck, fs))
                continue
            nombradas = {f.etiqueta for f in fs if f.etiqueta}
            tituladas = {f.titulada for f in fs if f.titulada}
            elegida = None
            for grupo in (nombradas & comunes, tituladas & comunes):
                if len(grupo) == 1:
                    elegida = next(iter(grupo))
                    break
            if elegida is None:
                santos = sorted(c for c in comunes
                                if c.split('#')[0].startswith(('st_', 'san_')))
                votivas = sorted(c for c in comunes
                                 if c.split('#')[0].startswith('vot_'))
                fechas = sorted(c for c in comunes
                                if c.split('#')[0].startswith('md_'))
                comun = sorted(c for c in comunes
                               if c.split('#')[0].startswith('comun_'))
                tiempo = sorted(c for c in comunes
                                if c.split('#')[0].startswith('d'))
                for grupo in (votivas, santos, fechas, comun, tiempo,
                              sorted(comunes)):
                    if grupo:
                        elegida = min(grupo, key=lambda c: (cuantos[c], c))
                        break
            motivo = ('fuente' if elegida in nombradas else
                      'cabecera' if elegida in tituladas else
                      'fecha' if elegida.startswith('md_') else
                      'común' if elegida.startswith('comun_') else
                      'calendario')
            if excepcion:
                motivo = 'casi todos'
                salvo.append((ran, elegida, len(fs), excepcion))
            asignado[(ran, ck)] = (elegida, motivo)
    return donde, textos, asignado, huerfanos, salvo


# --------------------------------------------------------------------------
# F. el texto canónico y sus variantes
# --------------------------------------------------------------------------

def canoniza(grupos):
    """De {clave: (texto, [testigos])} al canónico y sus variantes.

    Manda la mayoría de testigos. A igualdad manda la clave, que no es un
    criterio litúrgico pero **es el mismo en todas las pasadas**: una
    construcción que cambia de resultado entre dos ejecuciones vuelve a
    firmar los datos y obliga al teléfono a descargarlos otra vez.
    """
    orden = sorted(grupos.items(),
                   key=lambda kv: (-len(kv[1][1]), kv[0]))
    (_, (texto, testigos)) = orden[0]
    variantes = [{'texto': t, 'testigos': sorted(w)}
                 for _, (t, w) in orden[1:]]
    empate = len(orden) > 1 and len(orden[1][1][1]) == len(testigos)
    return texto, sorted(testigos), variantes, empate


# --------------------------------------------------------------------------
# el riesgo 3: las lecturas propias que nunca se imprimen
# --------------------------------------------------------------------------

def lecturas_del_leccionario():
    """(leccionario, archivo, cel) → [(tipo, cita)] del índice del proyecto."""
    por_clave = defaultdict(list)
    for e in json.load(open(os.path.join(DATA, 'index_master.json'),
                            encoding='utf-8')):
        if not e.get('cita_normalizada'):
            continue
        k = (e['leccionario'], e['archivo'], e['cel_n'])
        por_clave[k].append((e['tipo'], e['cita_normalizada']))
    return por_clave


def mide_riesgo_tres(cal, formularios, por_clave):
    """Cuántas lecturas propias de las memorias no se imprimen nunca.

    Era el riesgo 3 del plan y la primera cosa que esta fase debía medir: el
    misalito reza la feria en las memorias, así que las lecturas propias del
    leccionario V de muchos santos pueden no aparecer **ni una vez** en ocho
    años. Se mide por tres caminos, de más exigente a menos: impresa en el
    día del santo, impresa en cualquier otro día del corpus (que es lo que
    recupera el corpus por cita), y nunca impresa.
    """
    # las citas del corpus, y en qué días
    dondecita = defaultdict(set)
    for f in formularios:
        # las de sus ranuras y las de más, porque la pregunta de aquí es si la
        # perícopa está impresa en algún sitio, y las de más lo están
        for ran, p in ([(r, q) for r, q in f.piezas.items()]
                       + [(q['ranura'], q) for q in f.otras]):
            if CLASE_DE[ran] == 'lectura' and p['cita']:
                dondecita[squeeze(p['cita'])].add(f.fecha)

    filas = []
    for e in cal['santoral']:
        propio = next((b for b in e.get('bloques') or []
                       if b['etiqueta'] == 'Propio'), None)
        if not propio:
            continue
        k = tuple(propio['clave'])
        lect = [(t, c) for t, c in por_clave.get(k, [])
                if t in ('primera lectura', 'segunda lectura', 'evangelio',
                         'lectura del Antiguo Testamento',
                         'lectura del Nuevo Testamento')]
        if not lect:
            continue
        mmdd = '%02d-%02d' % (e['mes'], e['dia'])
        en_su_dia = otro_dia = nunca = 0
        detalle = []
        for tipo, cita in lect:
            dias = dondecita.get(squeeze(cita), set())
            if any(d[5:] == mmdd for d in dias):
                en_su_dia += 1
                donde = 'su día'
            elif dias:
                otro_dia += 1
                donde = 'otro día'
            else:
                nunca += 1
                donde = 'nunca'
            detalle.append((tipo, cita, donde))
        filas.append({'slug': e['slug'], 'titulo': e['titulo'],
                      'grado': e['rotulo_grado'], 'mmdd': mmdd,
                      'total': len(lect), 'en_su_dia': en_su_dia,
                      'otro_dia': otro_dia, 'nunca': nunca,
                      'detalle': detalle})
    return filas, dondecita


# --------------------------------------------------------------------------
# el informe y la salida
# --------------------------------------------------------------------------

def main():
    cal = json.load(open(os.path.join(DATA, 'calendario_completo.json'),
                         encoding='utf-8'))
    prefacios_es = json.load(open(os.path.join(DATOS, 'prefacios_es.json'),
                                  encoding='utf-8'))
    cal_fechas = candidatos_del_dia(cal)
    santoral_md = santoral_por_fecha(cal)
    comunes_de, etiquetas_comun = comunes_del_santoral(cal)
    titulo_de = dict(etiquetas_comun)
    for e in cal['santoral']:
        titulo_de[e['slug']] = e['titulo']
    for iso, cs in cal_fechas.items():
        for cid, k, grado, titulo in cs:
            titulo_de.setdefault(cid, titulo)

    print('Fase 4 — las piezas del misalito')
    citas = Citas()
    reparos_guion = Counter()
    formularios = carga(citas, reparos_guion)
    por_origen = Counter(f.origen for f in formularios)
    print('  %d formularios de las dos fuentes castellanas (%s)'
          % (len(formularios),
             ', '.join('%s %d' % x for x in sorted(por_origen.items()))))
    print('  %d palabras partidas por el renglón, juntadas'
          % sum(reparos_guion.values()))

    # --- los candidatos de cada formulario -------------------------------
    avisos = []
    cands = {}
    cuantos = Counter()
    for f in formularios:
        cands[f.testigo] = candidatos(f, cal_fechas, santoral_md,
                                      comunes_de, avisos)
        if f.origen == 'misalito':
            for cid in cands[f.testigo]:
                cuantos[cid] += 1
    con_alt = sum(1 for f in formularios if f.alt_clase)
    rescatadas = sum(1 for f in formularios
                     if f.alt_clase and not f.cab.get('alterna'))
    print('  %d formularios ofrecen una alternativa (%d las guardaba la '
          'fase 3 en otro campo)' % (con_alt, rescatadas))

    # --- la atribución ----------------------------------------------------
    #
    # **Atribuye sólo el misalito, y eso no es desconfianza de la otra
    # fuente: es que atribuir y leer no son el mismo trabajo.**
    #
    # La atribución supone «un formulario por día», porque un formulario por
    # día es lo que el editor del misalito eligió, y de esa elección se
    # deduce a qué celebración pertenece cada texto: un texto que sale con
    # dos santos distintos del mismo común es del común. El sitio imprime
    # **los dos** formularios de los días con opción, que para leer es una
    # ventaja y para deducir es ruido: al entrar los dos, el reparto cambia y
    # la deducción se lleva textos de donde estaban.
    #
    # Medido con sólo enero de 2016 añadido —380 formularios—: 75 textos
    # canónicos cambiaban, 109 piezas desaparecían, y en el común de los
    # pastores una comunión con **41 testigos** quedaba sustituida por otra
    # con 9, perdiendo 61 de los 77 testigos de esa pieza. Con los once años
    # sería mucho peor.
    #
    # Y la medida dice además por dónde sí entra: cotejadas las dos fuentes
    # día por día, **las lecturas coinciden el 93-96 % y los propios el
    # 46-63 %**. No es casualidad ni calidad desigual: la lectura la fija el
    # leccionario —manda el día, se celebre lo que se celebre— y el propio
    # depende de qué celebración se eligió. Así que el sitio entra de pleno
    # en la cosecha de perícopas, que se agrupa **por cita** y no mira la
    # atribución, y se queda fuera de ésta.
    para_atribuir = [f for f in formularios if f.origen == 'misalito']
    donde, textos, asignado, huerfanos, salvo = atribuye(
        para_atribuir, cands, cuantos)

    # --- los propios por celebración -------------------------------------
    porcel = defaultdict(lambda: defaultdict(dict))
    motivos = Counter()
    for (ran, ck), (cid, motivo) in asignado.items():
        p = textos[(ran, ck)]
        fs = donde[ran][ck]
        porcel[cid][ran][ck] = (p['texto'], [f.testigo for f in fs])
        motivos[motivo] += 1

    # los prefacios que cada día nombra, y los propios que imprime
    pref = Prefacios(prefacios_es)
    pref_por_cel = defaultdict(Counter)
    celde = {}
    gloria = defaultdict(Counter)
    credo = defaultdict(Counter)
    resena = defaultdict(Counter)
    for f in formularios:
        cid = f.etiqueta or f.titulada or (
            (cands[f.testigo] and sorted(cands[f.testigo])[0]) or None)
        f.cel = cid
        celde[f.testigo] = cid
        pref.lee(f)
        for b in f.rubricas:
            if b.get('rotulo') == '@gloria' and cid:
                gloria[cid][not re.search(r'\bno\s+se\s+dice\b',
                                          ' '.join(b['texto']), re.I)] += 1
            if b.get('rotulo') == '@credo' and cid:
                credo[cid][not re.search(r'\bno\s+se\s+dice\b',
                                         ' '.join(b['texto']), re.I)] += 1
        if f.resena and cid and not re.match(r'^\s*o\s', f.resena):
            resena[cid][re.sub(r'\s+', ' ', f.resena).strip()] += 1

    # Los prefacios propios, antes de resolver las referencias: un día cita
    # «Prefacio de Pentecostés», que no está en los 67 del Ordinario, y sin
    # los propios cosechados esa referencia no tiene contra qué casar.
    cosecha = {}
    for pid in sorted(pref.propios):
        pp = pref.propios[pid]
        grupos = {ck: (pp['por_clave'][ck], pp['testigos'][ck])
                  for ck in pp['textos']}
        texto, testigos, variantes, _ = canoniza(grupos)
        cosecha[pid] = {'titulo': pp['titulo'], 'texto': texto,
                        'testigos': testigos, 'variantes': variantes}
    # Un mismo prefacio con dos títulos es uno: la fuente imprime seis veces
    # «María Magdalena: ‹Apóstola› de los Apóstoles» y una «‹Apóstol›», con
    # el mismo texto debajo. Manda el título de más testigos y el otro queda
    # apuntado, que es lo que se hace con cualquier variante.
    prefacios_propios = {}
    por_texto = defaultdict(list)
    for pid, p in cosecha.items():
        por_texto[clave(' '.join(p['texto']))].append(pid)
    titulos_juntados = []
    for ck in sorted(por_texto):
        pids = sorted(por_texto[ck],
                      key=lambda q: (-len(cosecha[q]['testigos']), q))
        p = dict(cosecha[pids[0]])
        if len(pids) > 1:
            p['otros_titulos'] = [cosecha[q]['titulo'] for q in pids[1:]]
            for q in pids[1:]:
                p['testigos'] = sorted(p['testigos']
                                       + cosecha[q]['testigos'])
                p['variantes'] = p['variantes'] + cosecha[q]['variantes']
                titulos_juntados.append((cosecha[q]['titulo'], p['titulo']))
        prefacios_propios[pids[0]] = p
    for testigo, ids in pref.resuelve(prefacios_propios).items():
        cel = celde.get(testigo)
        if cel:
            for pid in ids:
                pref_por_cel[cel][pid] += 1

    propios = {}
    un_testigo = []
    empates = []
    for cid in sorted(porcel):
        piezas = {}
        for ran in PROPIOS:
            if ran not in porcel[cid]:
                continue
            grupos = {ck: v for ck, v in porcel[cid][ran].items()}
            texto, testigos, variantes, empate = canoniza(grupos)
            piezas[ran] = {'texto': texto, 'testigos': testigos,
                           'variantes': variantes}
            if len(testigos) == 1 and not variantes:
                un_testigo.append((cid, ran, testigos[0]))
            if empate:
                empates.append((cid, ran, len(testigos), len(variantes)))
        if not piezas:
            continue
        base = cid.split('#')[0]
        clase = ('santoral' if base.startswith(('st_', 'san_')) else
                 'votiva' if base.startswith('vot_') else
                 'común' if base.startswith('comun_') else
                 'fecha' if base.startswith('md_') else
                 'tiempo' if base.startswith('d') else 'suelta')
        ent = {'titulo': titulo_de.get(base) or nombre_de_fecha(base),
               'clase': clase, 'piezas': piezas}
        if '#' in cid:
            ent['misa'] = cid.split('#', 1)[1]
        if pref_por_cel.get(cid):
            ent['prefacio'] = [p for p, _ in
                               sorted(pref_por_cel[cid].items(),
                                      key=lambda kv: (-kv[1], kv[0]))]
        for nombre, tabla in (('gloria', gloria), ('credo', credo)):
            if tabla.get(cid):
                ent[nombre] = max(tabla[cid].items(),
                                  key=lambda kv: (kv[1], kv[0]))[0]
        if resena.get(cid):
            ent['resena'] = max(resena[cid].items(),
                                key=lambda kv: (kv[1], kv[0]))[0]
        propios[cid] = ent

    # --- las perícopas por cita ------------------------------------------
    porcita = defaultdict(lambda: defaultdict(dict))
    tipos = defaultdict(Counter)
    sumarios = defaultdict(Counter)
    sin_cita = Counter()
    for f in formularios:
        # las de sus ranuras y las de más, que son lecturas igual: la Vigilia
        # con sus ocho salmos y la memoria que la fuente imprime detrás de la
        # feria. El testigo es el mismo formulario, y por eso no se apunta dos
        # veces en la misma perícopa.
        for ran, p in ([(r, q) for r, q in f.piezas.items()]
                       + [(q['ranura'], q) for q in f.otras]):
            if CLASE_DE[ran] != 'lectura':
                continue
            if not p['cita']:
                sin_cita[ran] += 1
                continue
            cita = p['cita']
            ck = clave(' '.join(p['texto']))
            d = porcita[cita][ck]
            if d:
                if f.testigo not in d[1]:
                    d[1].append(f.testigo)
            else:
                porcita[cita][ck] = (p['texto'], [f.testigo])
            tipos[cita][ran] += 1
            if p['sumario']:
                sumarios[cita][re.sub(r'\s+', ' ', p['sumario']).strip()] += 1

    pericopas = {}
    for cita in sorted(porcita):
        texto, testigos, variantes, _ = canoniza(porcita[cita])
        ent = {'texto': texto, 'testigos': testigos,
               'tipos': dict(sorted(tipos[cita].items())),
               'variantes': variantes}
        if sumarios.get(cita):
            ent['sumario'] = max(sumarios[cita].items(),
                                 key=lambda kv: (kv[1], kv[0]))[0]
        pericopas[cita] = ent

    # --- el puente para la fase 5 ----------------------------------------
    dias = {}
    for f in formularios:
        e = {'cel': f.cel, 'fichero': f.fichero,
             'lecturas': {ran: f.piezas[ran]['cita']
                          for ran in LECTURAS if ran in f.piezas},
             'propios': {ran: asignado.get(
                 (ran, clave(' '.join(f.piezas[ran]['texto']))), (None,))[0]
                 for ran in PROPIOS if ran in f.piezas}}
        if f.misa:
            e['misa'] = f.misa
        if f.alt:
            e['ofrece'] = f.alt
        if f.titulo:
            e['titulo'] = f.titulo
        dias.setdefault(f.fecha, []).append(e)

    # --- los textos que ninguna celebración explica ----------------------
    #
    # Son, casi todos, los comunes: una colecta del Común de pastores sirve a
    # varios santos y entonces no hay una celebración presente en todos sus
    # días. No se pueden poner en `propios_es.json` sin mentir, pero tampoco
    # se tiran: van aparte, con los días en que se imprimieron y con las
    # celebraciones que esos días traían, que es lo que la fase 5 necesita
    # para casarlos con el común que el santoral ya nombra.
    # Y no sirve atribuirlos al común que más días cubra: la antífona «El que
    # quiera venir conmigo» se imprime en 72 días, y el común que más cubre
    # —el de santos y santas— sólo llega a 37, porque la antífona está en
    # varios comunes a la vez. Lo que sí se puede dar hecho es **el reparto
    # medido**: cuántos de sus días ofrecía cada común. Con eso y con los
    # comunes del Misal latino, que los trae enteros, la fase 5 los coloca.
    sueltos = []
    for ran, ck, fs in sorted(huerfanos, key=lambda h: (h[0], h[1])):
        p = textos[(ran, ck)]
        comun = Counter()
        otras = Counter()
        for f in fs:
            for cid in cands[f.testigo]:
                (comun if cid.startswith('comun_') else otras)[cid] += 1
        sueltos.append({
            'ranura': ran, 'texto': p['texto'],
            'testigos': sorted(f.testigo for f in fs),
            'comunes': dict(sorted(comun.items(), key=lambda kv: (-kv[1],
                                                                 kv[0]))),
            'celebraciones': [c for c, _ in sorted(
                otras.items(), key=lambda kv: (-kv[1], kv[0]))[:12]]})

    # --- el riesgo 3 ------------------------------------------------------
    por_clave = lecturas_del_leccionario()
    filas, dondecita = mide_riesgo_tres(cal, formularios, por_clave)

    # El cotejo con el índice del leccionario, que es el camino independiente
    # del calendario: si el lector de citas leyera mal, saldría aquí. Pero una
    # cita que el índice no tiene no es por sí misma un fallo —las dos
    # ediciones letrean los versículos distinto, «1 P 2,20-25» contra
    # «1 P 2,20b-25»—, así que se separa lo que el índice no conoce **ni por
    # el capítulo**, que es lo que de verdad delataría un error de lectura.
    del_leccionario = {squeeze(c) for v in por_clave.values() for _, c in v}
    capitulos = {c.split(',')[0] for c in del_leccionario}
    desconocidas = sorted(c for c in dondecita if c not in del_leccionario)
    ni_el_capitulo = sorted(c for c in desconocidas
                            if c.split(',')[0] not in capitulos)

    os.makedirs(LIBRO, exist_ok=True)
    for nombre, dato in (('propios_es', propios), ('pericopas_es', pericopas),
                         ('prefacios_propios_es', prefacios_propios),
                         ('sueltos_es', sueltos), ('dias_es', dias)):
        ruta = os.path.join(LIBRO, nombre + '.json')
        with open(ruta, 'w', encoding='utf-8') as fh:
            json.dump(dato, fh, ensure_ascii=False,
                      sort_keys=isinstance(dato, dict),
                      separators=(',', ':'))
        print('  %-26s %6d entradas  %5d KB'
              % (nombre + '.json', len(dato),
                 os.path.getsize(ruta) // 1024))

    informe(cal, formularios, citas, propios, pericopas, prefacios_propios,
            pref, asignado, motivos, huerfanos, un_testigo, empates,
            sin_cita, filas, desconocidas, ni_el_capitulo, dondecita,
            avisos, cuantos, reparos_guion, titulos_juntados, salvo)


def informe(cal, formularios, citas, propios, pericopas, prefacios_propios,
            pref, asignado, motivos, huerfanos, un_testigo, empates,
            sin_cita, filas, desconocidas, ni_el_capitulo, dondecita,
            avisos, cuantos, reparos_guion, titulos_juntados, salvo):
    inf = Informe(QA, 'FASE 4 — LAS PIEZAS, POR CELEBRACIÓN Y POR CITA')
    inf.di('Los cien misalitos deshechos: cada pieza una vez, con sus')
    inf.di('testigos y sus variantes. Lo que no se pudo atribuir está aquí,')
    inf.di('nombrado, y no ha entrado en los ficheros.')
    inf.di()
    inf.di('formularios leídos            : %d' % len(formularios))
    inf.di('celebraciones con propios     : %d' % len(propios))
    inf.di('perícopas distintas por cita  : %d' % len(pericopas))
    inf.di('prefacios propios cosechados  : %d' % len(prefacios_propios))
    inf.di('textos propios atribuidos     : %d' % len(asignado))
    inf.di('   por lo que nombra la fuente: %d' % motivos['fuente'])
    inf.di('   por lo que titula el día   : %d' % motivos['cabecera'])
    inf.di('   por la fecha del año       : %d' % motivos['fecha'])
    inf.di('   por el común que comparten : %d' % motivos['común'])
    inf.di('   por el calendario          : %d' % motivos['calendario'])
    inf.di('   por todos sus días menos uno: %d' % motivos['casi todos'])
    inf.di('textos sin celebración que los explique: %d'
           % len(huerfanos))
    inf.di('   (van aparte, en sueltos_es.json, con sus días)')

    # ---- el riesgo 3, que es lo primero que esta fase debía medir -------
    inf.titulo('El riesgo 3: las lecturas propias que nunca se imprimen')
    inf.di('El misalito reza la feria en las memorias, así que las lecturas')
    inf.di('propias del leccionario V de muchos santos pueden no aparecer ni')
    inf.di('una vez en ocho años. Esto es cuánto, medido, y es la primera')
    inf.di('cosa que el plan pedía de esta fase.')
    inf.di()
    por_grado = defaultdict(lambda: Counter())
    for fi in filas:
        g = por_grado[fi['grado']]
        g['celebraciones'] += 1
        g['lecturas'] += fi['total']
        g['su dia'] += fi['en_su_dia']
        g['otro dia'] += fi['otro_dia']
        g['nunca'] += fi['nunca']
        if fi['nunca'] == fi['total']:
            g['ninguna'] += 1
        elif fi['en_su_dia'] == fi['total']:
            g['todas en su dia'] += 1
    inf.di('%-16s %6s %8s %8s %8s %8s %9s' % (
        'grado', 'celebr', 'lecturas', 'su día', 'otro día', 'nunca',
        'sin una'))
    orden = ['Solemnidad', 'Fiesta', 'Memoria', 'Memoria libre',
             'Conmemoración']
    for g in orden + [k for k in sorted(por_grado) if k not in orden]:
        if g not in por_grado:
            continue
        c = por_grado[g]
        inf.di('%-16s %6d %8d %8d %8d %8d %9d'
               % (g, c['celebraciones'], c['lecturas'], c['su dia'],
                  c['otro dia'], c['nunca'], c['ninguna']))
    tot = Counter()
    for c in por_grado.values():
        tot.update(c)
    inf.di('%-16s %6d %8d %8d %8d %8d %9d'
           % ('TOTAL', tot['celebraciones'], tot['lecturas'], tot['su dia'],
              tot['otro dia'], tot['nunca'], tot['ninguna']))
    inf.di()
    inf.di('«su día»   : la perícopa está impresa en un día del santo;')
    inf.di('«otro día» : no, pero sí en otro día del corpus, y de ahí la')
    inf.di('             recupera el corpus por cita;')
    inf.di('«nunca»    : no está en los cien misalitos, de ninguna manera;')
    inf.di('«sin una»  : celebraciones de las que no se imprimió ni una.')
    inf.di()
    sin_ninguna = [fi for fi in filas if fi['nunca'] == fi['total']]
    inf.di('Las %d celebraciones de las que no hay ni una lectura propia:'
           % len(sin_ninguna))
    for fi in sorted(sin_ninguna, key=lambda f: f['mmdd']):
        inf.di('   %s  %-14s %-46s %s' % (
            fi['mmdd'], fi['grado'][:14], fi['titulo'][:46],
            ', '.join(c for _, c, _ in fi['detalle'])[:44]))

    # ---- lo que la fuente nombra al lado -------------------------------
    inf.titulo('Lo que la fuente nombra al lado, y que la fase 3 repartía '
               'en tres campos')
    inf.di('De esto depende la atribución entera, y es el hallazgo de esta')
    inf.di('fase: en las ferias del tiempo ordinario el misalito no imprime')
    inf.di('la feria, sino el formulario que el editor eligió ese año, y lo')
    inf.di('dice al lado de la cabecera. La fase 3 lo guardaba en `alterna`,')
    inf.di('en `resena` o en `subtitulo` según cayera la maqueta; aquí se')
    inf.di('vuelve a leer del campo `crudo` y se unifica.')
    inf.di()
    cl = Counter(f.alt_clase for f in formularios if f.alt_clase)
    campo = Counter()
    for f in formularios:
        if not f.alt_clase:
            continue
        campo['alterna' if f.cab.get('alterna') else
              'resena' if f.cab.get('resena') else
              'subtitulo' if f.cab.get('subtitulo') else 'crudo'] += 1
    for k, n in cl.most_common():
        inf.di('   alternativa que es una %-6s : %4d' % (k, n))
    inf.di()
    for k, n in campo.most_common():
        inf.di('   la fase 3 la tenía en %-10s : %4d' % (k, n))

    # ---- las lecturas de más --------------------------------------------
    inf.titulo('Las lecturas de más: la misma ranura, otra vez')
    inf.di('El formulario tiene una ranura de cada cosa y la primera manda,')
    inf.di('pero la fuente imprime en un mismo formulario más de una lectura')
    inf.di('de la misma ranura en dos casos: la Vigilia Pascual, que canta')
    inf.di('nueve lecturas y ocho salmos, y los días que dan opción, donde el')
    inf.di('sitio pone la memoria detrás de la feria sin repetir la antífona')
    inf.di('de entrada, así que las dos misas entran como un formulario. Antes')
    inf.di('se tiraban; ahora van a la cosecha de perícopas, que se guarda por')
    inf.di('cita y no por ranura, sin tocar la atribución ni el día.')
    inf.di()
    demas = Counter()
    por_anio = Counter()
    for f in formularios:
        for q in f.otras:
            demas[(f.origen, q['ranura'])] += 1
            por_anio[(f.origen, f.anio)] += 1
    inf.di('  %-12s %8s %8s' % ('ranura', 'misalito', 'sitio'))
    for ran in LECTURAS:
        a, b = demas[('misalito', ran)], demas[('sitio', ran)]
        if a or b:
            inf.di('  %-12s %8d %8d' % (ran, a, b))
    inf.di('  %-12s %8d %8d' % ('TOTAL',
                                sum(n for (o, _), n in demas.items()
                                    if o == 'misalito'),
                                sum(n for (o, _), n in demas.items()
                                    if o == 'sitio')))
    inf.di()
    inf.di('Y por años, que dice de dónde salen: el sitio imprime los dos')
    inf.di('formularios en los años viejos y uno solo en los nuevos.')
    inf.di()
    for (origen, anio), n in sorted(por_anio.items()):
        inf.di('   %-9s %d  %4d' % (origen, anio, n))

    # ---- las citas ------------------------------------------------------
    inf.titulo('Las citas')
    inf.di('La pieza viene con su cita, y por eso el emparejamiento no se')
    inf.di('adivina. Leídas: %d del incipit, %d de su propio campo, %d del'
           % (citas.leidas['incipit'], citas.leidas['sigla'],
              citas.leidas['salmo']))
    inf.di('rótulo del salmo y %d del renglón que no es más que la cita, que'
           % citas.leidas['renglón'])
    inf.di('es como la fuente imprime la del salmo responsorial la mitad de')
    inf.di('las veces. Ese renglón no lo leía nadie, y una lectura sin cita no')
    inf.di('llega a perícopa.')
    inf.di()
    inf.di('Lecturas sin cita, por ranura (la fuente no siempre la da; en')
    inf.di('las antífonas es lo normal, en una lectura es que el incipit se')
    inf.di('partió o que remite a otro día):')
    for ran in LECTURAS:
        if sin_cita.get(ran):
            inf.di('   %-12s %4d' % (ran, sin_cita[ran]))
    inf.di()
    inf.di('Nombres de libro que no se supieron leer: %d formas, %d casos.'
           % (len(citas.fallos), sum(citas.fallos.values())))
    for k, n in citas.fallos.most_common():
        inf.di('   %4d  %r' % (n, k))
    inf.titulo('Lo que se repara, y con qué prueba')
    inf.di('Nada de esto se corrige en silencio.')
    inf.di()
    inf.di('**El renglón partido.** El PDF corta la palabra al final del')
    inf.di('renglón y deja el guión («…divino poder dispon-» / «gas nuestros')
    inf.di('corazones…»). Si no se junta, los ocho testigos de una misma')
    inf.di('oración se parten en dos grupos, la mayoría decide sobre un')
    inf.di('reparto falso y el texto canónico sale con «dispon- gas» dentro.')
    inf.di('Se junta cuando el renglón acaba en guión y el siguiente empieza')
    inf.di('en minúscula, que es el único caso en que el guión no es del')
    inf.di('texto: **%d palabras**.' % sum(reparos_guion.values()))
    inf.di()
    for k, nn in reparos_guion.most_common(12):
        a, _, b = k.partition('|')
        inf.di('   %4d  %s- / %s   →   %s' % (nn, a, b, a + b))
    inf.di('   … y %d formas más' % max(0, len(reparos_guion) - 12))
    inf.di()
    inf.di('**Los salmos partidos con letra.** El misalito escribe «Sal')
    inf.di('113A», «Sal 18B» y «Sal 87(86)»; el índice del leccionario no')
    inf.di('hace ni lo uno ni lo otro, y los versículos bastan para')
    inf.di('distinguir las dos mitades: %d casos en %d formas.'
           % (sum(citas.letras.values()), len(citas.letras)))
    for k, nn in citas.letras.most_common(10):
        inf.di('   %4d  %s' % (nn, k))
    inf.di()
    inf.di('**Las erratas de la fuente**, con su prueba:')
    if citas.erratas:
        for (mal, bien), nn in citas.erratas.most_common():
            inf.di('   %4d  %-26s →   %s' % (nn, mal, bien))
        inf.di()
        inf.di('   «Is 149»: Isaías tiene 66 capítulos, así que ese capítulo')
        inf.di('   no existe; va en la ranura del salmo responsorial y el')
        inf.di('   texto que lleva debajo es el salmo 149.')
    else:
        inf.di('   ninguna')
    if titulos_juntados:
        inf.di()
        inf.di('**Dos títulos para un mismo prefacio**, juntados por el texto:')
        for a, b in titulos_juntados:
            inf.di('   «%s» → «%s»' % (a[:44], b[:44]))
    inf.di()
    inf.di('**La ele por el uno**: %d casos en %d formas. En un'
           % (sum(citas.reparos.values()), len(citas.reparos)))
    inf.di('número de versículo una ele suelta no puede ser otra cosa, pero')
    inf.di('se nombra igual:')
    for k, n in citas.reparos.most_common(20):
        inf.di('   %4d  %r' % (n, k))
    if len(citas.reparos) > 20:
        inf.di('   … y %d formas más' % (len(citas.reparos) - 20))
    inf.di()
    inf.di('El cotejo con el índice del leccionario, que es el camino')
    inf.di('independiente del calendario: si el lector de citas leyera mal,')
    inf.di('saldría aquí.')
    inf.di()
    inf.di('   citas distintas en el corpus                   : %d'
           % len(dondecita))
    inf.di('   que el índice tiene igual                      : %d'
           % (len(dondecita) - len(desconocidas)))
    inf.di('   que el índice no tiene con esos versículos     : %d'
           % (len(desconocidas) - len(ni_el_capitulo)))
    inf.di('   que el índice no tiene ni por el capítulo      : %d'
           % len(ni_el_capitulo))
    inf.di()
    inf.di('La fila del medio no es un fallo y conviene no confundirla con')
    inf.di('uno: son las dos ediciones letreando distinto el mismo pasaje')
    inf.di('—«1 P 2,20-25» en el misalito, «1 P 2,20b-25» en el índice—, o')
    inf.di('eligiendo un versículo más o uno menos. La que delataría un error')
    inf.di('de lectura es la última, porque un libro y un capítulo que el')
    inf.di('leccionario no usa nunca sería una sigla mal resuelta:')
    for c in ni_el_capitulo[:70]:
        inf.di('   %s' % c)
    if len(ni_el_capitulo) > 70:
        inf.di('   … y %d más' % (len(ni_el_capitulo) - 70))

    # ---- los testigos ---------------------------------------------------
    inf.titulo('Los testigos: lo que está decidido y lo que no')
    cuenta = Counter()
    for cid, e in propios.items():
        for ran, p in e['piezas'].items():
            cuenta[len(p['testigos'])] += 1
    inf.di('Piezas propias por número de testigos del texto canónico:')
    for n in sorted(cuenta):
        inf.di('   %2d testigo(s) : %5d piezas' % (n, cuenta[n]))
    inf.di()
    con_var = sum(1 for e in propios.values() for p in e['piezas'].values()
                  if p['variantes'])
    inf.di('Piezas con variantes (la fuente no imprimió lo mismo todos los')
    inf.di('años): %d. La variante se guarda con los días que la respaldan,'
           % con_var)
    inf.di('que es lo que impide que una errata de un año se imponga a los')
    inf.di('otros siete.')
    inf.di()
    inf.di('Piezas decididas a la fuerza por empate de testigos: %d. Es el'
           % len(empates))
    inf.di('único sitio donde la mayoría no decide, y conviene mirarlas:')
    for cid, ran, nt, nv in empates[:40]:
        inf.di('   %-34s %-12s %d testigos, %d variantes'
               % (cid[:34], ran, nt, nv))
    if len(empates) > 40:
        inf.di('   … y %d más' % (len(empates) - 40))
    inf.di()
    inf.di('Piezas con un solo testigo y sin variante: %d. Entran, pero el'
           % len(un_testigo))
    inf.di('texto no está confirmado por nadie más:')
    for cid, ran, w in un_testigo[:40]:
        inf.di('   %-34s %-12s %s' % (cid[:34], ran, w))
    if len(un_testigo) > 40:
        inf.di('   … y %d más' % (len(un_testigo) - 40))

    # ---- los huérfanos --------------------------------------------------
    inf.titulo('Lo atribuido con una excepción')
    inf.di('%d textos se atribuyeron a una celebración que explica todos sus'
           % len(salvo))
    inf.di('días **menos uno**. Se admite una sola excepción, y sólo con')
    inf.di('cuatro días o más, porque la fuente se desvía de vez en cuando')
    inf.di('del calendario del proyecto: en 2022 el 24 de junio fue el')
    inf.di('Sagrado Corazón y el misalito pasó la Natividad de san Juan')
    inf.di('Bautista al 23, diciéndolo en un corchete —«[Anticipada del día')
    inf.di('24]»— que no vuelve a usar en los cien ficheros. Con un solo día')
    inf.di('así, la intersección se quedaba vacía y las cinco piezas de una')
    inf.di('solemnidad se iban con los textos sueltos. Cada excepción, por')
    inf.di('su nombre:')
    inf.di()
    cuenta_salvo = Counter()
    for ran, cel, n_dias, exc in salvo:
        for w in exc:
            cuenta_salvo[(cel, w)] += 1
    for (cel, w), n in sorted(cuenta_salvo.items(),
                              key=lambda kv: (-kv[1], kv[0]))[:40]:
        inf.di('   %-34s salvo %s  (%d piezas)' % (cel[:34], w, n))
    if len(cuenta_salvo) > 40:
        inf.di('   … y %d más' % (len(cuenta_salvo) - 40))

    inf.titulo('Los textos que ninguna celebración explica: los comunes')
    inf.di('%d textos aparecen en días que no comparten ninguna celebración,'
           % len(huerfanos))
    inf.di('y no es un fallo: son los **comunes**. La antífona «En medio de la')
    inf.di('Iglesia abrió su boca» se imprime en los días de cuarenta santos')
    inf.di('distintos, así que no es de ninguno de ellos.')
    inf.di()
    inf.di('Y tampoco se pueden atribuir al común que más días cubra, que es')
    inf.di('lo primero que se intenta: el reparto medido lo desmiente. «El')
    inf.di('que quiera venir conmigo» sale en 72 días y el común que más')
    inf.di('cubre —santos y santas— llega a 37, porque la antífona está en')
    inf.di('varios comunes a la vez. Lo que sí entra hecho en')
    inf.di('`sueltos_es.json` es ese reparto, común por común, que con los')
    inf.di('comunes del Misal latino —que los trae enteros— es lo que la')
    inf.di('fase 5 necesita para colocarlos.')
    inf.di()
    inf.di('Los %d que sí son de un solo común (el común que ofrecen todos'
           % motivos['común'])
    inf.di('sus días, sin una excepción) han entrado en `propios_es.json`.')
    inf.di()
    inf.di('%-12s %5s  %s' % ('ranura', 'días', 'texto'))
    for ran, ck, fs in sorted(huerfanos,
                              key=lambda h: (-len(h[2]), h[0]))[:40]:
        inf.di('   %-12s %4d  %s' % (ran, len(fs), ck[:56]))
    if len(huerfanos) > 40:
        inf.di('   … y %d más' % (len(huerfanos) - 40))

    # ---- los prefacios --------------------------------------------------
    inf.titulo('Los prefacios')
    inf.di('La rúbrica del prefacio hace dos cosas: nombra uno de los 67 del')
    inf.di('Ordinario, o imprime entero uno **propio**, de los que no están')
    inf.di('en ningún juego común porque viven dentro de su formulario.')
    inf.di()
    inf.di('referencias del día resueltas             : %d' % pref.veces)
    inf.di('   prefacios del Ordinario que algún día cita : %d de 67'
           % len([p for p in pref.citados if p in pref.comunes]))
    inf.di('   días que remiten al prefacio propio del formulario : %d'
           % pref.citados.get('@propio', 0))
    inf.di('referencias que no se supieron resolver   : %d, en %d formas'
           % (pref.sin_contar, len(pref.sin_resolver) + len(pref.sin_nombre)))
    inf.di('prefacios propios cosechados              : %d'
           % len(prefacios_propios))
    inf.di()
    inf.di('Los prefacios propios, con sus testigos:')
    for pid in sorted(prefacios_propios,
                      key=lambda p: (-len(prefacios_propios[p]['testigos']),
                                     p)):
        p = prefacios_propios[pid]
        inf.di('   %3d testigos  %-52s %s'
               % (len(p['testigos']), p['titulo'][:52],
                  'variantes: %d' % len(p['variantes'])
                  if p['variantes'] else ''))
    inf.di()
    sin_citar = [p for p in pref.comunes if p not in pref.citados]
    inf.di('Los %d prefacios del Ordinario que ningún día cita (no es un'
           % len(sin_citar))
    inf.di('fallo: son los que no se usan en el tiempo ni en el santoral,')
    inf.di('sino en los rituales, y la app los ofrecerá igual):')
    for p in sorted(sin_citar):
        inf.di('   %s' % pref.comunes[p]['titulo'])
    inf.di()
    if pref.sin_resolver:
        inf.di('Las referencias que no casaron con ningún título:')
        for k, n in pref.sin_resolver.most_common(40):
            inf.di('   %4d  %s' % (n, k))

    # ---- las oraciones sobre el pueblo ----------------------------------
    inf.titulo('Las oraciones sobre el pueblo')
    con_pueblo = {cid: e for cid, e in propios.items()
                  if 'pueblo' in e['piezas']}
    inf.di('El Ordinario de México no las trae: sólo las menciona en los')
    inf.di('números 142 y 143. Los misalitos sí las imprimen, y aquí están:')
    inf.di('%d celebraciones con oración sobre el pueblo.' % len(con_pueblo))
    inf.di()
    for cid in sorted(con_pueblo,
                      key=lambda c: -len(con_pueblo[c]['piezas']['pueblo']
                                         ['testigos']))[:30]:
        e = con_pueblo[cid]
        inf.di('   %2d testigos  %-34s %s'
               % (len(e['piezas']['pueblo']['testigos']), cid[:34],
                  e['titulo'][:40]))
    if len(con_pueblo) > 30:
        inf.di('   … y %d más' % (len(con_pueblo) - 30))

    # ---- las celebraciones, de más a menos completas -------------------
    inf.titulo('Las celebraciones y lo que tienen')
    por_clase = Counter(e['clase'] for e in propios.values())
    for k, n in por_clase.most_common():
        inf.di('   %-10s %5d' % (k, n))
    inf.di()
    completas = sum(1 for e in propios.values()
                    if all(r in e['piezas'] for r in
                           ('entrada', 'colecta', 'ofrendas', 'comunion',
                            'poscomunion')))
    inf.di('Con las cinco piezas del formulario completas: %d de %d. Que la'
           % (completas, len(propios)))
    inf.di('mayoría no las tenga todas no es un hueco del parseo: es lo que')
    inf.di('el misalito imprime. En una memoria pone la colecta del santo y')
    inf.di('deja las antífonas de la feria, así que el santo se queda con su')
    inf.di('colecta y nada más, y es correcto —la app tomará las demás de')
    inf.di('donde el día las toma—. Lo que falta, ranura por ranura:')
    inf.di()
    faltan = Counter()
    for e in propios.values():
        for r in ('entrada', 'colecta', 'ofrendas', 'comunion',
                  'poscomunion'):
            if r not in e['piezas']:
                faltan[r] += 1
    for r, n in faltan.most_common():
        inf.di('   sin %-12s %5d celebraciones' % (r, n))

    # ---- los avisos -----------------------------------------------------
    if avisos:
        inf.titulo('Las celebraciones que el calendario del proyecto no trae')
        propias_mx = sorted({c for c in propios
                             if c.split('#')[0].startswith('san_')})
        inf.di('Los %d avisos son todos de lo mismo, y es un hallazgo, no un'
               % len(avisos))
        inf.di('fallo: el misalito ofrece santos que el calendario del')
        inf.di('proyecto no tiene, porque son el **propio de México** —los')
        inf.di('mártires cristeros, los santos de Guadalajara— y el')
        inf.di('calendario se armó con el general. Sus textos entran, con')
        inf.di('identificador `san_…`: son %d celebraciones.' % len(propias_mx))
        inf.di()
        for c in propias_mx[:60]:
            e = propios[c]
            inf.di('   %-46s %s' % (c[:46],
                                    ', '.join(sorted(e['piezas']))[:40]))
        if len(propias_mx) > 60:
            inf.di('   … y %d más' % (len(propias_mx) - 60))
        inf.di()
        inf.di('Y los avisos, día por día:')
        inf.di()
        for w, a in avisos[:120]:
            inf.di('   %-14s %s' % (w, a))
        if len(avisos) > 120:
            inf.di('   … y %d más' % (len(avisos) - 120))

    inf.guarda()


if __name__ == '__main__':
    main()
