# -*- coding: utf-8 -*-
"""Fase 5 — el devocionario para la app.

Junta lo de las fases anteriores en un solo fichero, `devocionario.json`, y
decide dos cosas: **lo que se publica** y **cómo se ordena**.

Lo que no se publica, y a propósito:

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

El orden es lo que cambió el 2026-10-14. Antes eran las carpetas del sitio
renombradas —veintiún grupos—, y las carpetas del sitio **mezclan tres
criterios en el mismo nivel**: a quién se reza (Trinidad, Virgen, san José),
qué es la pieza (himnos, salmos, credos) y cuándo se reza (antes de la misa,
los tiempos del año). De ahí salían dos cosas que estorbaban: el año
litúrgico vivía en dos sitios —«Los tiempos del año», tres piezas, y
cuarenta y tres himnos de tiempo en otra carpeta—, y las treinta y dos de
«Himnos · Tiempo ordinario», que no son de ningún tiempo sino el himnario
del día, quedaban en una lista alfabética que no enseña nada.

Ahora el libro tiene **once capítulos, por cuándo y a quién**, y una regla
sola:

    una pieza vive en un solo sitio —cuándo o a quién—, y lo que la pieza
    es (letanía, himno, novena) no es una carpeta: es una señal en la fila
    y un filtro que atraviesa el libro entero.

La forma la pone la fase 4c y la hora del himno la 4d. Y hay una tercera
cosa que el orden necesita: **las colecciones**. Hay piezas que no son
oraciones sueltas sino partes de una sola devoción —las nueve novenas de
letanías a san Benito, los siete días de su semana, los trece salmos en sus
dos ediciones—, y en una lista ocupaban veintiséis filas que no se podían
distinguir. Van plegadas en una fila que se abre.

    TRABAJO/piezas_ecl.json ─┐
    datos/castellano.json ───┼──▶  app/datos/devocionario.json
    datos/formas.csv ────────┤
    datos/himnario.csv ──────┘

    python Enchiridion/src/5_app.py
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
from collections import Counter, OrderedDict, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, SITIO, TRABAJO

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
APP = os.path.join(RAIZ, 'app', 'datos')

# ---------------------------------------------------------------- el libro
# Los once capítulos, en el orden en que se enseñan: primero lo que se reza
# de memoria, después el día, la misa y la confesión, que es lo que tiene
# hora fija; después el año y las horas; después a quién se reza; y al final
# lo que se busca cuando hace falta.
CAPITULOS = [
    ('comunes', 'Las oraciones comunes', 'Lo que se reza de memoria'),
    ('dia', 'El día', 'Al levantarse, a la mesa, al acostarse'),
    ('misa', 'La misa', 'Antes, después, y la comunión'),
    ('confesion', 'La confesión', 'Antes y después, y los penitenciales'),
    ('anio', 'El año litúrgico', 'De Adviento a Todos los Santos'),
    ('horas', 'Las horas del día', 'El himnario del Breviario'),
    ('dios', 'A Dios', 'Trinidad, Padre, Hijo, Espíritu, Eucaristía'),
    ('santos', 'A la Virgen y a los santos', 'Y a san José y a los ángeles'),
    ('necesidad', 'En cada necesidad', 'Por la paz, de viaje, por los difuntos'),
    ('escritura', 'La Escritura', 'Salmos y cánticos'),
    ('doctrina', 'Para saber de memoria', 'Credos y fórmulas de la doctrina'),
]

# Dentro de un capítulo, las secciones van en el orden del libro, no en el
# del alfabeto ni en el del tamaño: la Virgen antes que los santos, Adviento
# antes que Pascua, y las horas en el orden en que se rezan.
ORDEN_SECCIONES = {
    'misa': ['Antes de la misa', 'Antes y después', 'La comunión',
             'Después de la misa'],
    'anio': ['Adviento', 'Navidad', 'Epifanía', 'Cuaresma', 'Triduo',
             'Pascua', 'Pentecostés', 'Corpus Christi', 'Todos los Santos'],
    'horas': ['Maitines', 'Laudes', 'Prima', 'Tercia', 'Sexta', 'Nona',
              'Vísperas', 'Completas', 'Sin hora en el Breviario'],
    'dios': ['La Santísima Trinidad', 'Dios Padre',
             'Nuestro Señor Jesucristo', 'El Sagrado Corazón',
             'La santa Cruz', 'La Pasión', 'La Preciosísima Sangre',
             'El santo Nombre', 'La Divina Misericordia',
             'El Espíritu Santo', 'El Santísimo Sacramento'],
    'santos': ['La Santísima Virgen', 'La Inmaculada', 'Los Dolores',
               'La Virgen del Carmen', 'Las antífonas finales', 'San José',
               'La Sagrada Familia', 'El ángel de la guarda', 'San Miguel',
               'San Gabriel', 'San Rafael', 'Los ángeles',
               'Todos los santos'],
    'escritura': ['Salmos', 'Cánticos del Evangelio',
                  'Salterios devocionales'],
    'doctrina': ['Credos', 'Fórmulas para saber de memoria'],
    'necesidad': ['Por la paz', 'Por el Papa', 'Por los padres',
                  'Por el trabajo', 'Antes de estudiar',
                  'Antes de conectarse', 'De viaje', 'Por los que no creen',
                  'Por los bienhechores', 'Al empezar una reunión',
                  'Por todas las cosas', 'Por la buena muerte',
                  'Por los agonizantes', 'Por los difuntos',
                  'Otras ocasiones'],
    'dia': ['La mañana', 'La mesa', 'La noche'],
}

# De dónde le viene a cada forma su nombre. No es adorno: es la respuesta a
# «qué es esto», y agrupadas así las veintiocho se leen de una vez, que en
# una lista plana no se leen.
FAMILIAS = [
    ('De la Escritura', ['salmo', 'cántico', 'salterio']),
    ('Del canto', ['himno', 'secuencia', 'antífona', 'aclamación',
                   'pregón']),
    ('Del rezo en coro', ['letanía', 'preces', 'conmemoración',
                          'responsorio']),
    ('De la devoción', ['oficio parvo', 'novena', 'rosario', 'vía crucis',
                        'ejercicio', 'rito']),
    ('De la liturgia', ['oración', 'bendición']),
    ('De lo que uno dice', ['jaculatoria', 'súplica', 'acto',
                            'ofrecimiento', 'consagración',
                            'acción de gracias']),
    ('De la doctrina', ['credo', 'fórmula']),
    ('Varias en una', ['colección']),
]

# Las veintidós del apéndice del Compendio del Catecismo, en el orden del
# libro. No son un capítulo aparte —el Magníficat vive con los cánticos y el
# Rosario con la Virgen—, pero llevan su marca donde estén: son las que la
# Iglesia pone a quien empieza.
COMPENDIO = ['signum crucis', 'doxologia minor', 'oratio dominica',
             'ave maria', 'angele dei', 'requiem aeternam', 'angelus',
             'regina caeli', 'salve regina', 'magnificat',
             'sub tuum praesidium', 'benedictus', 'te deum',
             'veni creator spiritus', 'veni sancte spiritus', 'anima christi',
             'memorare o piissima virgo maria', 'rosarium', 'actus fidei',
             'actus spei', 'actus caritatis', 'actus contritionis']

# Lo que se reza por una necesidad concreta, que en el sitio estaba
# repartido entre «Varia» y las carpetas de cada santo.
NECESIDAD = {
    'oratio pro pace': 'Por la paz',
    'da domine propitius pacem': 'Por la paz',
    'oratio pro summo pontifice': 'Por el Papa',
    'deus omnium fidelium pastor': 'Por el Papa',
    'deus qui nos patrem et matrem honorare': 'Por los padres',
    'oratio s thomae aquinatis ante studium': 'Antes de estudiar',
    'oratio ante colligationem': 'Antes de conectarse',
    'itinerarium': 'De viaje',
    'oratio s francisci xaverii': 'Por los que no creen',
    'pro defuncto nominatim': 'Por los difuntos',
    'pro defuncta nominatim': 'Por los difuntos',
    'ordo commendationis animae': 'Por los agonizantes',
    'oratio ad ss trinitatem pro felici morte': 'Por la buena muerte',
    'adsumus': 'Al empezar una reunión',
    'oratio universalis': 'Por todas las cosas',
    'deus qui ad maiestatis tuae gloriam': 'Por los bienhechores',
    'oratio sancti genesii': 'Por el propio oficio',
    'adiutor laborantium': 'Por el trabajo',
}

# Las piezas que son partes de una sola devoción. La clave es la colección;
# el número es el orden dentro de ella.
SEMANA = ['dominica', 'feria secunda', 'feria tertia', 'feria quarta',
          'feria quinta', 'feria sexta', 'sabbato']
ROMANOS_NOVENA = ['', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix']
LETANIAS_BENITO = ['i litaniae', 'ii aliae de eodem', 'iii aliae de eodem']

ROMANOS = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}


def plano(s, jota=True):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace(u'æ', 'ae').replace(u'œ', 'oe')
    if not jota:
        s = s.replace('j', 'i')
    return re.sub(r'\s+', ' ', s).strip()


def pelado(s, jota=True):
    """Como plano(), pero además sin puntuación: para comparar títulos.

    Con `jota=False` desata la jota en i, que es como se escriben las
    tablas de este módulo y la mitad del índice de búsqueda: quien escriba
    «Ioseph» tiene que encontrar «Joseph», y quien escriba «Joseph»
    también."""
    s = plano(s)
    if not jota:
        s = s.replace('j', 'i')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', s)).strip()


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


def seccion_dios(t, g):
    """A quién se reza dentro del capítulo «A Dios»."""
    if g == 'trinidad':
        return 'La Santísima Trinidad'
    if g == 'padre':
        return 'Dios Padre'
    if g == 'espiritu':
        return 'El Espíritu Santo'
    if g == 'eucaristia':
        return 'El Santísimo Sacramento'
    if 'cordis iesu' in t or 'cor iesu' in t or 'divinum cor' in t:
        return 'El Sagrado Corazón'
    if 'crux' in t or 'crucis' in t or 'crucifixum' in t or 'cruce' in t:
        return 'La santa Cruz'
    if 'nominis' in t or 'nomine' in t:
        return 'El santo Nombre'
    if 'sanguinis' in t or 'sanguine' in t:
        return 'La Preciosísima Sangre'
    if 'passion' in t:
        return 'La Pasión'
    if 'misericord' in t:
        return 'La Divina Misericordia'
    return 'Nuestro Señor Jesucristo'


def seccion_santos(g, t):
    """A quién se reza dentro del capítulo de la Virgen y los santos."""
    if g == 'jose':
        return 'San José'
    if g == 'familia':
        return 'La Sagrada Familia'
    if g == 'angeles':
        if 'michael' in t or 'michaele' in t or 'michaelis' in t:
            return 'San Miguel'
        if 'raphael' in t:
            return 'San Rafael'
        if 'gabriel' in t:
            return 'San Gabriel'
        if 'custod' in t or 'angelo proprio' in t or 'angele qui meus' in t:
            return 'El ángel de la guarda'
        return 'Los ángeles'
    if 'immaculat' in t or 'conceptionis' in t or 'sine labe' in t \
       or 'tota pulchra' in t or 'intemerata' in t or 'pura et immaculata' in t:
        return 'La Inmaculada'
    if 'dolor' in t:
        return 'Los Dolores'
    if 'carmeli' in t:
        return 'La Virgen del Carmen'
    if t in ('alma redemptoris mater', 'ave regina caelorum', 'regina caeli',
             'salve regina', 'sub tuum praesidium'):
        return 'Las antífonas finales'
    return 'La Santísima Virgen'


# Qué carpeta del sitio cae en qué grupo de los de antes. Se conserva porque
# el reparto por capítulos se apoya en él, y porque la ficha de cada pieza
# dice de qué carpeta del sitio salió.
CARPETAS = [
    ('basico', ['Basics']), ('dia', ['Cotidiana']),
    ('trinidad', ['Trinitas']), ('padre', ['Pater']), ('hijo', ['Filius']),
    ('espiritu', ['Spiritus']), ('eucaristia', ['Euch']),
    ('misa', ['AnteMissam', 'PostMissam']), ('virgen', ['BVM']),
    ('jose', ['Ioseph']), ('familia', ['SanctaFamilia']),
    ('angeles', ['Angeli']), ('santos', ['Sancti']),
    ('penitencia', ['Confessio']), ('tiempos', ['InTemporibus']),
    ('himnos', ['Hymni']), ('canticos', ['Cantici']), ('salmos', ['Psalmi']),
    ('credos', ['Symbola']), ('numeros', ['Numeri']),
    ('varia', ['Varia', 'Introductio']),
]

# El tiempo del año, cuando la carpeta lo dice.
TIEMPOS = {
    'Hymni/Adventus': 'Adviento', 'Hymni/Nativitatis': 'Navidad',
    'Hymni/Epiphania': 'Epifanía', 'Hymni/Quadragesimae': 'Cuaresma',
    'Hymni/Triduum': 'Triduo', 'Hymni/Paschale': 'Pascua',
    'Hymni/Pentecoste': 'Pentecostés', 'Hymni/CorpusChristi': 'Corpus Christi',
    'Hymni/OmnesSancti': 'Todos los Santos',
    'Hymni/InTemporibus/Adventus': 'Adviento',
    'Hymni/InTemporibus/Quadragesimae': 'Cuaresma',
    'InTemporibus/Adventus': 'Adviento',
    'InTemporibus/Quadragesimae': 'Cuaresma',
    'InTemporibus/Nativitas': 'Navidad', 'InTemporibus/Paschale': 'Pascua',
}

# Los santos que tienen sección propia en el sitio.
SANTOS = {
    'Sancti/SAnna': 'Santa Ana',
    'Sancti/SAntoniusDePadova': 'San Antonio de Padua',
    'Sancti/SAugustinus': 'San Agustín', 'Sancti/SBenedictusAb': 'San Benito',
    'Sancti/SFranciscusAssisiensis': 'San Francisco de Asís',
    'Sancti/SPatricius': 'San Patricio',
    'Sancti/SScholastica': 'Santa Escolástica',
}


def grupo_de(cat):
    for clave, carpetas in CARPETAS:
        for c in carpetas:
            if cat == c or cat.startswith(c + '/'):
                return clave
    return 'varia'


def coloca(p, g, t, forma, hora):
    """El capítulo y la sección de una pieza. Devuelve (capítulo, sección).

    Es el corazón del orden nuevo, y va de lo más concreto a lo más general:
    primero lo que se reza en un momento fijo —la mesa, la misa, la
    confesión—, después lo que se reza en un tiempo —el año, las horas—, y
    sólo al final lo que se ordena por a quién se le reza."""
    cat = p['cat']
    if g == 'basico' and forma != 'bendición':
        return 'comunes', None
    if t in ('requiem aeternam', 'anima christi', 'actus contritionis'):
        return 'comunes', None
    if forma == 'bendición':
        return 'dia', 'La mesa'
    if t in NECESIDAD:
        return 'necesidad', NECESIDAD[t]
    if g == 'dia':
        # el Ángelus y las de la mañana por un lado, la visita de la noche
        # por otro: es lo que distingue una hora de otra
        if 'visita' in t or 'noct' in t:
            return 'dia', 'La noche'
        return 'dia', 'La mañana'
    if g == 'misa':
        if 'communion' in t or 'eucharistiae' in t:
            return 'misa', 'La comunión'
        if 'post' in t:
            return 'misa', 'Después de la misa'
        if 'ante' in t or 'intensionis' in t:
            return 'misa', 'Antes de la misa'
        return 'misa', 'Antes y después'
    if g == 'penitencia':
        return 'confesion', None
    if g in ('himnos', 'tiempos'):
        tpo = TIEMPOS.get(cat)
        if tpo:
            return 'anio', tpo
        # lo que queda es el himnario del día: por la hora que diga el
        # Breviario, y lo que no casa se dice que no casa
        return 'horas', hora or 'Sin hora en el Breviario'
    if g in ('trinidad', 'padre', 'hijo', 'espiritu', 'eucaristia'):
        return 'dios', seccion_dios(t, g)
    if g in ('virgen', 'jose', 'familia', 'angeles'):
        return 'santos', seccion_santos(g, t)
    if g == 'santos':
        return 'santos', SANTOS.get(cat, 'Todos los santos')
    if g == 'salmos':
        return 'escritura', 'Salmos'
    if g == 'canticos':
        return 'escritura', 'Cánticos del Evangelio'
    if g == 'credos':
        return 'doctrina', 'Credos'
    if g == 'numeros':
        return 'doctrina', 'Fórmulas para saber de memoria'
    # «Varia», que es donde el sitio dejó lo que no cabía en ningún sitio
    if forma == 'salterio':
        return 'escritura', 'Salterios devocionales'
    if forma == 'credo':
        return 'doctrina', 'Credos'
    if 'maria' in t or 'virgo' in t or 'mater' in t or 'deipara' in t:
        return 'santos', seccion_santos('virgen', t)
    if 'iesu' in t or 'christe' in t or 'christi' in t or 'crucis' in t:
        return 'dios', seccion_dios(t, 'hijo')
    return 'necesidad', 'Otras ocasiones'


def coleccion_de(t, g, tla):
    """Si la pieza es parte de una devoción, cuál, qué son sus partes y en
    qué lugar va."""
    if t.startswith('novena litaniarum ad sanctum benedictum'):
        cola = t[len('novena litaniarum ad sanctum benedictum'):].strip(' ,')
        n = ROMANOS_NOVENA.index(cola) + 1 if cola in ROMANOS_NOVENA else 1
        return ('benito-novena', 'Novena de letanías a san Benito', 'días', n)
    if t in SEMANA:
        return ('benito-semana', 'San Benito, por los días de la semana',
                'días', SEMANA.index(t) + 1)
    if t in LETANIAS_BENITO:
        return ('benito-letanias', 'Tres letanías de san Benito', 'letanías',
                LETANIAS_BENITO.index(t) + 1)
    if g == 'salmos':
        n = numero_romano(tla)
        if n:
            # el mismo salmo en sus dos ediciones latinas: una fila, dos
            # textos, que es como se compara
            return ('salmo-%d' % n, 'Salmo %s'
                    % re.match(r'(?i)^psalmus\s+([IVXLCDM]+)',
                               tla).group(1).upper(),
                    'ediciones', 0 if 'nova' in t else 1)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    entrada = os.path.join(TRABAJO, 'piezas_ecl.json')
    if not os.path.exists(entrada):
        sys.exit('corre antes Enchiridion/src/3_eclesiastico.py')
    with io.open(entrada, encoding='utf-8') as fh:
        libro = json.load(fh)
    es = {}
    ruta_es = os.path.join(DATOS, 'castellano.json')
    if os.path.exists(ruta_es):
        with io.open(ruta_es, encoding='utf-8') as fh:
            es = json.load(fh).get('piezas', {})
    formas, senales = {}, {}
    ruta_formas = os.path.join(DATOS, 'formas.csv')
    if os.path.exists(ruta_formas):
        with io.open(ruta_formas, encoding='utf-8', newline='') as fh:
            for f in csv.DictReader(fh):
                formas[f['id']] = f['forma']
                senales[f['id']] = f['senal']
    horas = {}
    ruta_hor = os.path.join(DATOS, 'himnario.csv')
    if os.path.exists(ruta_hor):
        with io.open(ruta_hor, encoding='utf-8', newline='') as fh:
            for f in csv.DictReader(fh):
                horas[f['id']] = (f['hora'], f['dia'], f['tiempo'],
                                  f['seccion'])

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

        # las tablas de este módulo están escritas con la i, no con la jota
        t = pelado(p['tla'], jota=False)
        g = grupo_de(p['cat'])
        forma = formas.get(p['id'], 'oración')
        hora = horas.get(p['id'], ('', '', '', ''))
        cap, sec = coloca(p, g, t, forma, hora[0])
        palabras = sum(len(''.join(x[1] for x in linea).split())
                       for b in bloques for linea in b['t'])

        d = OrderedDict([
            ('id', p['id']),
            ('src', clave),
            ('c', cap),
            ('s', sec),
            ('f', forma),
            ('tla', p['tla']),
            ('b', bloques),
            ('pal', palabras),
        ])
        col = coleccion_de(t, g, p['tla'])
        if col:
            d['col'], d['colt'], d['colq'], d['coli'] = col
        if hora[0]:
            d['hora'] = hora[0]
            if hora[1]:
                d['dia'] = hora[1]
            if hora[2]:
                d['tpo'] = hora[2]
            d['hsrc'] = hora[3]
        if t in COMPENDIO:
            d['comp'] = COMPENDIO.index(t) + 1
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
                        x = ''.join(y[1] for y in ln).strip()
                        if x:
                            tes = x if len(x) <= 58 else x[:57].rstrip() + '…'
                            break
                    if tes:
                        break
            d['tes'] = tes
            d['es'] = v['t']
            d['fes'] = v['fuente']
            d['paso'] = v.get('paso')
            cuenta['con castellano'] += 1
        cuenta['publicadas'] += 1
        cuenta['forma: ' + forma] += 1
        piezas.append(d)

    # ------------------------------------------------------------ el orden
    # dentro de una sección, por el título latino, que es como se busca en
    # un devocionario; los salmos por su número, que es su nombre; y las
    # partes de una colección, por su sitio en ella.
    orden_cap = [c[0] for c in CAPITULOS]

    def orden_seccion(cap, sec):
        lista = ORDEN_SECCIONES.get(cap, [])
        if sec in lista:
            return (0, lista.index(sec), '')
        return (1, 0, plano(sec or '', jota=False))

    def orden(d):
        # una colección ocupa en la lista el sitio de su nombre, y sus
        # partes van seguidas y en su orden, no cada una por su título
        return (orden_cap.index(d['c']),
                orden_seccion(d['c'], d['s']),
                numero_romano(d['tla']) or 0,
                pelado(d.get('colt') or d['tla'], jota=False),
                d.get('coli', 0))

    piezas.sort(key=orden)

    # La marca del Compendio se pone por el título, y hay títulos con dos y
    # tres versiones: tres «Veni, Sancte Spíritus», dos «Actus Fídei». La
    # que lleva la marca es la que el Compendio emparejó de verdad —la que
    # trajo su castellano de allí, paso 3—, y si no emparejó ninguna, la más
    # corta, que es la forma común. Marcarlas todas sería decir que el
    # Compendio imprime tres oraciones distintas con el mismo nombre.
    porcomp = defaultdict(list)
    for d in piezas:
        if d.get('comp'):
            porcomp[d['comp']].append(d)
    for grupo in porcomp.values():
        if len(grupo) < 2:
            continue
        buena = ([d for d in grupo if d.get('paso') == 3]
                 or sorted(grupo, key=lambda d: d['pal']))[0]
        for d in grupo:
            if d is not buena:
                del d['comp']

    # Dos versiones de la misma oración se llaman igual —hay dos «Actus
    # Fídei», el de Gasparri y el tradicional—, y en una lista eso no se
    # puede distinguir. Se les pone al lado el año que la fuente da, y si no
    # lo da, el primer renglón, que es lo que de verdad las separa.
    repes = defaultdict(list)
    for d in piezas:
        repes[pelado(d['tla'])].append(d)
    for grupo in repes.values():
        if len(grupo) < 2:
            continue
        for i, d in enumerate(grupo, 1):
            if d.get('anio'):
                d['dist'] = d['anio']
                continue
            primero = ''
            for b in d['b']:
                for ln in b['t']:
                    x = ''.join(y[1] for y in ln).strip()
                    if x and pelado(x) != pelado(d['tla']):
                        primero = x
                        break
                if primero:
                    break
            primero = re.sub(r'^(V\.|R\.)\s*', '', primero)
            d['dist'] = (primero[:40].rstrip() + '…') if len(primero) > 40 \
                else (primero or 'versión %d' % i)

    # ---------------------------------------------- el índice de búsqueda
    # Se normaliza igual que `plano()` en la app —sin diacríticos y con æ/œ
    # desatadas— porque es esa función la que prepara lo que el lector
    # escribe. La jota no la desata, así que la clave lleva también la forma
    # con i: quien escriba «Iesu» encuentra «Jesu», y al revés. Y lleva la
    # forma, para que quien escriba «letanía» encuentre las letanías.
    for d in piezas:
        titulos = ' '.join([d['tla'], d.get('tes') or '', d['f'],
                            d.get('colt') or '', d.get('s') or ''])
        con = pelado(titulos)
        sin = pelado(titulos, jota=False)
        d['k'] = con if con == sin else con + ' ' + sin

    # ------------------------------------------------- lo que ve la portada
    caps = []
    for clave, titulo, pista in CAPITULOS:
        dentro = [d for d in piezas if d['c'] == clave]
        if not dentro:
            continue
        secs, vistas = [], set()
        for d in dentro:
            if d['s'] and d['s'] not in vistas:
                vistas.add(d['s'])
                secs.append(OrderedDict([
                    ('s', d['s']),
                    ('n', sum(1 for x in dentro if x['s'] == d['s'])),
                ]))
        caps.append(OrderedDict([
            ('c', clave), ('t', titulo), ('p', pista), ('n', len(dentro)),
            ('secs', secs),
        ]))

    # las formas, para los filtros: en orden de cuántas hay, que es el orden
    # en que sirven
    cuentaf = Counter(d['f'] for d in piezas)
    familia_de = {}
    for nombre, cuales in FAMILIAS:
        for f in cuales:
            familia_de[f] = nombre
    formas_app = [OrderedDict([('f', f), ('n', n),
                               ('fam', familia_de.get(f, 'Otras'))])
                  for f, n in cuentaf.most_common()]
    sin_familia = [f for f in cuentaf if f not in familia_de]
    if sin_familia:
        print('  ¡formas sin familia!: ' + ', '.join(sorted(sin_familia)))

    salida = OrderedDict([
        ('fuente', 'Thesaurus Precum Latinarum, de Michael Martin — ' + SITIO),
        ('derechos', 'Latín: texto tradicional. La transcripción es del '
                     'sitio, que permite el uso personal y de estudio sin '
                     'ánimo de lucro. Castellano: cada oración dice de '
                     'dónde sale.'),
        ('caps', caps),
        # las formas van por cuántas hay —que es el orden en que sirven de
        # filtro—, y las familias en el orden del libro, que es el que
        # explica de dónde le viene a cada forma su nombre
        ('formas', formas_app),
        ('familias', [f[0] for f in FAMILIAS
                      if any(x['fam'] == f[0] for x in formas_app)]),
        ('piezas', piezas),
    ])
    ruta = os.path.join(APP, 'devocionario.json')
    with io.open(ruta, 'w', encoding='utf-8') as fh:
        json.dump(salida, fh, ensure_ascii=False, separators=(',', ':'))

    print('%d piezas -> %s (%.1f MB)'
          % (len(piezas), ruta, os.path.getsize(ruta) / 1e6))
    for k in sorted(k for k in cuenta if not k.startswith('forma:')):
        print('  %-30s %4d' % (k, cuenta[k]))
    print()
    for c in caps:
        print('  %-11s %-28s %4d  (%d secciones)'
              % (c['c'], c['t'], c['n'], len(c['secs'])))
    print()
    print('  formas: ' + ', '.join('%s %d' % (f['f'], f['n'])
                                   for f in formas_app))
    cols = Counter(d.get('colt') for d in piezas if d.get('colt'))
    print('  colecciones: ' + ', '.join('%s (%d)' % (k, v)
                                        for k, v in cols.most_common()))


if __name__ == '__main__':
    main()
