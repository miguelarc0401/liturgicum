# -*- coding: utf-8 -*-
"""Fase 4 — el castellano del devocionario.

El sitio no tiene castellano: tiene latín e inglés. El castellano hay que
buscarlo oración por oración, y no todas lo tienen. El orden es éste, y de
cada pieza se guarda por cuál de los cuatro pasos llegó:

  1. la traducción oficial mexicana, donde la haya (Catecismo, oracionario
     o devocionario aprobado por el episcopado);
  2. **la que ya está dentro de esta app**, cuando la pieza es literalmente
     la misma: la Liturgia de las Horas y el Misal en la traducción que se
     usa en México están en `app/datos/`, y traen el Padre nuestro, el
     Gloria, los dos Credos, el Confiteor, el Sanctus, las cuatro antífonas
     finales de la Virgen, los tres cánticos evangélicos y los salmos. No
     hay mejor castellano que ése para este proyecto: es el aprobado, es el
     que el usuario reza, y ya está cotejado;
  3. la Santa Sede u otro episcopado, diciendo de qué país es;
  4. una versión tradicional castellana de fuente eclesiástica verificable,
     marcada como no oficial.

Y donde no hay ninguna, la pieza se queda en latín y aparece en la lista de
pendientes del informe. `null` no significa que no exista traducción:
significa que aquí no se ha verificado.

El paso 2 no se escribe a mano, se saca de los libros. Con el Ordinario es
exacto porque el Ordinario de la app es bilingüe —el Misal latino de 2002
enfrentado a la traducción mexicana—, así que la pieza latina del
devocionario se busca en el latín del Ordinario y el castellano viene con
él, emparejado por el propio libro y no por una suposición. Las antífonas,
los cánticos y los salmos salen de la Liturgia de las Horas por su íncipit
castellano, que es lo que una tabla de este guión dice pieza por pieza.

Entradas:
    TRABAJO/piezas_ecl.json                 las piezas, ya en eclesiástico
    app/datos/ordinario.json, horas.json    los libros aprobados de la app
    Enchiridion/datos/castellano_mano.json  lo buscado fuera, a mano

Salida:
    Enchiridion/datos/castellano.json       todo junto, con su procedencia
    Enchiridion/datos/castellano_qa.txt     cobertura y pendientes

    python Enchiridion/src/4_castellano.py
    python Enchiridion/src/4_castellano.py --busca "Bajo tu amparo"
"""

import argparse
import difflib
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
APP = os.path.join(RAIZ, 'app', 'datos')

CEM = 'Conferencia del Episcopado Mexicano'
LH = 'Liturgia de las Horas, edición en uso en México'
MISAL = 'Misal Romano, traducción litúrgica aprobada para México'

# Las piezas cuyo castellano está en la Liturgia de las Horas de la app.
# Cada una dice dónde buscarlo —el íncipit castellano— y qué recortar: en el
# libro, el cántico y la antífona van juntos, y la antífona no es del
# cántico. 'desde' es el renglón de rúbrica tras el cual empieza la pieza.
DE_LAS_HORAS = [
    ('BVM/SalveRegina.html#0', 'Dios te salve, Reina', None, None,
     'antífona final de la Santísima Virgen'),
    ('BVM/AlmaRed.html#0', 'Madre del Redentor', None, None,
     'antífona final de la Santísima Virgen'),
    ('BVM/AveRegina.html#0', 'Salve, Reina de los cielos', None, None,
     'antífona final de la Santísima Virgen'),
    ('BVM/SubTuum.html#0', 'Bajo tu amparo nos acogemos', None, None,
     'antífona final de la Santísima Virgen'),
    ('BVM/ReginaCaeli.html#0', 'Reina del cielo, alégrate', None, None,
     'antífona final de la Santísima Virgen, en Pascua'),
    ('Cotidiana/Visita.html#0', 'Visita, Señor, esta habitación', None,
     r'(?i)^(ant|salmo|lectura|responsorio)', 'la oración de Completas'),
    ('Cantici/Magnificat.html#0', 'Proclama mi alma la grandeza',
     r'(?i)cántico de maría', r'(?i)^ant', 'cántico evangélico de Vísperas'),
    ('Cantici/Benedictus.html#0', 'Bendito sea el Señor, Dios de Israel',
     r'(?i)cántico de zacarías', r'(?i)^ant',
     'cántico evangélico de Laudes'),
    ('Cantici/Nunc.html#0', 'puedes dejar a tu siervo',
     r'(?i)cántico de simeón', r'(?i)^ant',
     'cántico evangélico de Completas'),
]

# Las piezas que están en el Ordinario y el parecido no alcanza a casar sin
# ayuda, porque el libro lleva la rúbrica metida entre los renglones de la
# oración («a las palabras que siguen todos se inclinan») y eso, contado
# letra por letra, las separa. Aquí se dice la rúbrica del Ordinario y se
# toma su castellano, que es el mismo libro aprobado.
DEL_ORDINARIO = [
    ('Basics/Apostolorum.html#0', '19', 'el Credo de los Apóstoles'),
]

# Piezas que el Ordinario no puede dar limpias, y por qué. El Padre nuestro
# va en el Misal pegado a la invitación del sacerdote —«Llenos de alegría
# por ser hijos de Dios, digamos confiadamente»—, que no es la oración; el
# Compendio del Catecismo lo imprime solo, y ése es el que entra.
NI_DEL_ORDINARIO = {
    'Basics/OraDom.html#0',
}

# Los trece salmos que el sitio publica —los siete penitenciales y seis
# más—, cada uno en sus dos ediciones latinas. El castellano de los trece
# está en el salterio de la Liturgia de las Horas, que es la traducción
# aprobada que se reza en México, y se numera como la Vulgata, igual que
# ellos. Tres vienen partidos en el oficio, porque son largos y se rezan en
# dos o tres veces; aquí se vuelven a juntar en el orden del salmo. Dos los
# imprime recortados, y eso se dice.
ROMANO = {1: 'I', 6: 'VI', 31: 'XXXI', 37: 'XXXVII', 50: 'L',
          83: 'LXXXIII', 84: 'LXXXIV', 85: 'LXXXV', 101: 'CI',
          115: 'CXV', 129: 'CXXIX', 142: 'CXLII', 150: 'CL'}
SALMOS = [
    (1, [None], None),
    (6, [None], None),
    (31, [None], None),
    (37, ['I', 'II', 'III'], None),
    (50, [None], None),
    (83, [None], None),
    (84, [None], None),
    (85, [None], None),
    (101, ['I', 'II', 'III'], None),
    (115, [None], None),
    (129, [None], None),
    (142, [None], 'La Liturgia de las Horas imprime de este salmo los '
                  'versículos 1-11; el latín de al lado va entero.'),
    (150, [None], None),
]
SALTERIO = [('Psalmi/SixtoClementine/Psalm%s.html#0', 'Vulgata Clementina'),
            ('Psalmi/NovaVulgata/Psalm%s.html#0', 'Nova Vulgata')]

# La doxología con que el oficio cierra cada salmo no es del salmo.
DOXOLOGIA = re.compile(r'(?i)^(gloria al padre|como era en el principio)')

# Oraciones que están en el apéndice del Compendio y que el parecido no
# casa solo, porque el sitio imprime otra recensión del mismo texto. La
# diferencia se dice aquí y se enseña en la ficha de la oración.
DEL_COMPENDIO = [
    ('Basics/AngeleDei.html#0', 'Angele Dei',
     'El latín de esta versión añade «hódie, hac nocte» —hoy, esta '
     'noche—, que el castellano del Compendio no trae.'),
    ('Trinitas/TeDeum.html#0', 'Te Deum',
     'El Compendio escribe «universæ» donde el sitio escribe «univérsæ», '
     'y alguna palabra suelta cambia; el texto es el mismo himno.'),
    ('Cotidiana/Angelus.html#0', 'Angelus Domini',
     'El Compendio abrevia las avemarías («Dios te salve, María…») que '
     'el latín de al lado imprime enteras.'),
]

PUNT = re.compile(r'[^\w\s]', re.UNICODE)


def pelado(s):
    """El texto comparable: sin acentos, sin ligaduras, sin puntuación."""
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = (s.replace('æ', 'ae').replace('œ', 'oe').replace('j', 'i')
         .replace('v', 'u').replace('y', 'i'))
    return re.sub(r'\s+', ' ', PUNT.sub(' ', s)).strip()


def carga(nombre):
    ruta = os.path.join(APP, nombre)
    if not os.path.exists(ruta):
        return None
    with io.open(ruta, encoding='utf-8') as fh:
        return json.load(fh)


def renglon(ln):
    """Un renglón de los libros de la app -> (rúbrica, texto)."""
    if isinstance(ln, str):
        return False, ln
    if not ln:
        return False, ''
    return bool(ln[0][0]), ''.join(x[1] for x in ln)


def objetos(x, ruta=()):
    """Los bloques {r, l} de la Liturgia de las Horas, con su ruta."""
    if isinstance(x, dict):
        if isinstance(x.get('l'), list):
            yield ruta, x
        for k, v in x.items():
            for y in objetos(v, ruta + (str(k),)):
                yield y
    elif isinstance(x, list):
        for i, v in enumerate(x):
            for y in objetos(v, ruta + (str(i),)):
                yield y


# ------------------------------------------------- paso 2a: el Ordinario
def indice_del_ordinario():
    """Latín del Ordinario -> (castellano, de qué rúbrica sale).

    El Ordinario de la app lleva las dos lenguas rúbrica por rúbrica, así
    que el emparejamiento lo hace el libro: aquí sólo se indexa.
    """
    o = carga('ordinario.json')
    if not o:
        return []
    indice = []
    for r in o.get('rubricas', []):
        la = [b for b in r.get('la', []) if not b.get('r')]
        es = [b for b in r.get('es', []) if not b.get('r')]
        if not la or not es:
            continue
        donde = 'rúbrica %s' % r.get('n')
        # bloque por bloque, y la rúbrica entera: el Credo del Ordinario va
        # partido en varios bloques y la oración del devocionario es uno
        for i, bla in enumerate(la):
            if i >= len(es):
                break
            tla = ' '.join(renglon(x)[1] for x in bla.get('t', []))
            tes = [t for r_, t in map(renglon, es[i].get('t', []))
                   if not r_]
            if len(pelado(tla)) >= 12:
                indice.append((pelado(tla), tla, tes, donde))
        # El Credo va en dos bloques de latín y uno de castellano, así que
        # emparejar por posición no lo alcanza: se indexa también la rúbrica
        # entera, un lado contra el otro. Si no es la misma oración, el
        # parecido lo dirá.
        if len(la) > 1 or len(es) > 1:
            tla = ' '.join(renglon(x)[1] for b in la
                           for x in b.get('t', []))
            tes = [t for r_, t in map(
                renglon, [x for b in es for x in b.get('t', [])]) if not r_]
            if len(pelado(tla)) >= 12:
                indice.append((pelado(tla), tla, tes, donde + ' (entera)'))
    return indice


# Parecido mínimo para decir que el latín del Ordinario y el de la pieza son
# la misma oración, y parecido desde el cual la pareja se apunta en el
# informe para mirarla. Un «et» de más no la cambia; el Confíteor
# tridentino, que nombra a san Miguel y a los apóstoles, sí es otra oración,
# y se queda en 0,25.
IGUALES = 0.93
PARECIDAS = 0.80


def del_ordinario(pieza, indice, casi=None):
    """El castellano del Ordinario para una pieza, si es la misma pieza."""
    texto = pelado(' '.join(
        t for b in pieza['b'] for ln in b['la'] for _, t in ln if not b['r']))
    if len(texto) < 12:
        return None
    mejor = (0, None)
    for fila in indice:
        # dos textos que no miden casi lo mismo no son la misma oración, y
        # comparar letra por letra el Canon Romano con cada letanía cuesta
        # minutos: el largo descarta antes y gratis
        corto, largo = sorted((len(fila[0]), len(texto)))
        if not largo or corto / float(largo) < PARECIDAS:
            continue
        sm = difflib.SequenceMatcher(None, fila[0], texto)
        if sm.quick_ratio() < PARECIDAS:
            continue
        r = sm.ratio()
        if r > mejor[0]:
            mejor = (r, fila)
    r, fila = mejor
    if not fila:
        return None
    clave, tla, tes, donde = fila
    if r < IGUALES:
        if casi is not None and r >= PARECIDAS:
            casi.append((r, donde, texto[:60], clave[:60]))
        return None
    return {
        'paso': 2,
        'texto': tes,
        'parecido': round(r, 3),
        'fuente': {'autoridad': CEM, 'obra': MISAL,
                   'territorio': 'MX', 'oficial': True,
                   'donde': 'app/datos/ordinario.json, ' + donde,
                   'latin_del_libro': tla[:120]},
    }


def castellano_de_rubrica(n):
    """El castellano de una rúbrica del Ordinario, por su número."""
    o = carga('ordinario.json')
    for r in (o or {}).get('rubricas', []):
        if str(r.get('n')) != str(n):
            continue
        lineas = []
        for b in r.get('es', []):
            if b.get('r'):
                continue
            for x in b.get('t', []):
                rub, t = renglon(x)
                if not rub:
                    lineas.append(t)
            lineas.append('')
        while lineas and not lineas[-1]:
            lineas.pop()
        return lineas
    return None


# ----------------------------------------- paso 2b: la Liturgia de las Horas
def de_las_horas(incipit, desde, hasta):
    """El bloque de la Liturgia de las Horas que empieza por ese íncipit."""
    h = carga('horas.json')
    if not h:
        return None, None
    for ruta, ob in objetos(h):
        lineas = [renglon(ln) for ln in ob['l']]
        if not any(incipit in t for _, t in lineas):
            continue
        i0, i1 = 0, len(lineas)
        if desde:
            for i, (_, t) in enumerate(lineas):
                if re.search(desde, t):
                    i0 = i + 1
                    break
        else:
            for i, (_, t) in enumerate(lineas):
                if incipit in t:
                    i0 = i
                    break
        if hasta:
            for i in range(i0, len(lineas)):
                if lineas[i][0] and re.search(hasta, lineas[i][1].strip()):
                    i1 = i
                    break
        trozo = [t for rub, t in lineas[i0:i1] if not rub]
        while trozo and not trozo[0].strip():
            trozo.pop(0)
        while trozo and not trozo[-1].strip():
            trozo.pop()
        if trozo:
            return trozo, '/'.join(ruta)
    return None, None


def del_salterio(n, parte):
    """Los renglones de un salmo —o de una de sus partes— en el oficio."""
    h = carga('horas.json')
    if not h:
        return None, None
    if parte:
        cab = re.compile(r'^Salmo\s+%d\b[^A-Za-z]*%s\b' % (n, parte))
    else:
        cab = re.compile(r'^Salmo\s+%d\b(?![^A-Za-z]*[IVX]+\b)' % n)
    for ruta, ob in objetos(h):
        lineas = [renglon(ln) for ln in ob['l']]
        i0 = None
        for i, (rub, t) in enumerate(lineas):
            if rub and cab.match(t.strip()):
                i0 = i + 1
                break
        if i0 is None:
            continue
        trozo = []
        for rub, t in lineas[i0:]:
            if rub:
                break
            if DOXOLOGIA.match(t.strip()):
                break
            trozo.append(t)
        while trozo and not trozo[0].strip():
            trozo.pop(0)
        while trozo and not trozo[-1].strip():
            trozo.pop()
        if len(trozo) > 2:
            return trozo, '/'.join(ruta)
    return None, None


# ------------------------------------------- paso 2d: el Misal entero
def indice_del_misal():
    """Latín del Misal de 2002 -> castellano del Misal de México.

    Los dos ficheros de la app van por las mismas claves —el formulario y
    el nombre de la pieza—, así que la colecta latina de un día y su
    traducción son la misma entrada en los dos. El devocionario está lleno
    de oraciones que son colectas del Misal, y así se emparejan sin
    suponer: por el latín, que es el que el libro imprime al lado.
    """
    la = carga('misal_latino.json')
    es = carga('misa.json')
    if not la or not es:
        return []
    castellano = {}
    for clave, form in (es.get('formularios') or {}).items():
        u = form.get('la')
        if not u:
            continue
        for nombre, pieza in (form.get('p') or {}).items():
            t = pieza.get('t')
            if t:
                castellano.setdefault((u, nombre), t)
    indice = []
    for u, form in (la.get('formularios') or {}).items():
        for nombre, pieza in (form.get('p') or {}).items():
            tes = castellano.get((u, nombre))
            if not tes:
                continue
            tla = ' '.join(pieza.get('t') or [])
            if len(pelado(tla)) < 40:
                continue
            indice.append((pelado(tla), tla, [tes],
                           '%s · %s' % (u, nombre)))
    return indice


# ------------------------------- paso 3: el Compendio del Catecismo
def indice_del_compendio():
    """Latín del apéndice del Compendio -> su castellano, emparejados ya."""
    ruta = os.path.join(DATOS, 'compendio.json')
    if not os.path.exists(ruta):
        return [], None
    with io.open(ruta, encoding='utf-8') as fh:
        d = json.load(fh)
    indice = []
    for o in d['oraciones']:
        tla = ' '.join(o['la'])
        if len(pelado(tla)) >= 20:
            indice.append((pelado(tla), tla, o['es'],
                           o['tes'] or o['tla'], o['tla']))
    return indice, d


def del_compendio(pieza, indice, casi=None):
    """El castellano del Compendio para una pieza, si es la misma oración."""
    texto = pelado(' '.join(
        t for b in pieza['b'] for ln in b['la'] for _, t in ln if not b['r']))
    if len(texto) < 20:
        return None
    mejor = (0, None)
    for fila in indice:
        corto, largo = sorted((len(fila[0]), len(texto)))
        if not largo or corto / float(largo) < PARECIDAS:
            continue
        sm = difflib.SequenceMatcher(None, fila[0], texto)
        if sm.quick_ratio() < PARECIDAS:
            continue
        r = sm.ratio()
        if r > mejor[0]:
            mejor = (r, fila)
    r, fila = mejor
    if not fila:
        return None
    if r < IGUALES:
        if casi is not None and r >= PARECIDAS:
            casi.append((r, 'Compendio: ' + fila[4], texto[:60], fila[0][:60]))
        return None
    return {'texto': fila[2], 'tes': fila[3], 'parecido': round(r, 3),
            'latin_del_libro': fila[1][:120]}


# --------------------------------------------------------------- lo de mano
def de_mano():
    ruta = os.path.join(DATOS, 'castellano_mano.json')
    if not os.path.exists(ruta):
        return {}
    with io.open(ruta, encoding='utf-8') as fh:
        return json.load(fh).get('piezas', {})


def parrafos(texto):
    """De una lista de renglones a párrafos de tiradas, como la app espera."""
    salida, actual = [], []
    for ln in texto:
        if isinstance(ln, str) and not ln.strip():
            if actual:
                salida.append(actual)
                actual = []
            continue
        if isinstance(ln, str):
            actual.append([[0, ln.strip()]])
        else:
            actual.append([[int(bool(x[0])), x[1]] for x in ln])
    if actual:
        salida.append(actual)
    return salida


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--busca', help='busca una frase en los libros de la app')
    args = ap.parse_args()

    if args.busca:
        h = carga('horas.json')
        for ruta, ob in objetos(h or {}):
            for ln in ob['l']:
                rub, t = renglon(ln)
                if args.busca.lower() in t.lower():
                    print('%-70s %s%s' % ('/'.join(ruta),
                                          'R ' if rub else '  ', t[:90]))
                    break
        return

    entrada = os.path.join(TRABAJO, 'piezas_ecl.json')
    if not os.path.exists(entrada):
        sys.exit('corre antes Enchiridion/src/3_eclesiastico.py')
    with io.open(entrada, encoding='utf-8') as fh:
        libro = json.load(fh)
    piezas = {p['pagina'].replace('thesaurus/', '') + '#' + str(p['orden']): p
              for p in libro['piezas'] if 'duplicado_de' not in p}

    salida, cuenta = {}, Counter()

    # paso 2a — el Ordinario, emparejado por su propio latín
    indice = indice_del_ordinario()
    casi = []
    for clave, p in piezas.items():
        if clave in NI_DEL_ORDINARIO:
            continue
        hallado = del_ordinario(p, indice, casi)
        if hallado:
            salida[clave] = {
                'paso': 2, 'fuente': hallado['fuente'],
                'parecido': hallado['parecido'],
                't': parrafos(hallado['texto']),
            }
            cuenta['del Ordinario'] += 1

    for clave, n, que in DEL_ORDINARIO:
        if clave not in piezas:
            print('¡ojo! no hay pieza %s' % clave)
            continue
        lineas = castellano_de_rubrica(n)
        if not lineas:
            print('¡ojo! no hay rúbrica %s en el Ordinario' % n)
            continue
        salida[clave] = {
            'paso': 2,
            'fuente': {'autoridad': CEM, 'obra': MISAL, 'territorio': 'MX',
                       'oficial': True, 'que_es': que,
                       'donde': 'app/datos/ordinario.json, rúbrica %s' % n},
            't': parrafos(lineas),
        }
        cuenta['del Ordinario'] += 1

    # paso 2b — la Liturgia de las Horas, por su íncipit
    for clave, incipit, desde, hasta, que in DE_LAS_HORAS:
        if clave not in piezas:
            print('¡ojo! no hay pieza %s' % clave)
            continue
        trozo, ruta = de_las_horas(incipit, desde, hasta)
        if not trozo:
            print('¡ojo! no encuentro «%s» en la Liturgia de las Horas'
                  % incipit)
            continue
        salida[clave] = {
            'paso': 2,
            'fuente': {'autoridad': CEM, 'obra': LH, 'territorio': 'MX',
                       'oficial': True, 'que_es': que,
                       'donde': 'app/datos/horas.json, ' + ruta},
            't': parrafos(trozo),
        }
        cuenta['de la Liturgia de las Horas'] += 1

    # paso 2c — el salterio, salmo por salmo y para las dos ediciones
    for n, partes, aviso in SALMOS:
        trozos, rutas = [], []
        for parte in partes:
            t, ruta = del_salterio(n, parte)
            if not t:
                print('¡ojo! no encuentro el salmo %d%s en el oficio'
                      % (n, ' (' + parte + ')' if parte else ''))
                trozos = None
                break
            if trozos:
                trozos.append('')
            trozos.extend(t)
            rutas.append(ruta)
        if not trozos:
            continue
        for molde, edicion in SALTERIO:
            clave = molde % ROMANO[n]
            if clave not in piezas:
                print('¡ojo! no hay pieza %s' % clave)
                continue
            fuente = {'autoridad': CEM, 'obra': LH, 'territorio': 'MX',
                      'oficial': True,
                      'que_es': 'el salmo %d del salterio' % n,
                      'donde': 'app/datos/horas.json, ' + '; '.join(rutas)}
            if aviso:
                fuente['aviso'] = aviso
            if len(partes) > 1:
                fuente['aviso'] = ('El oficio reza este salmo en %d partes, '
                                   'y aquí van seguidas.' % len(partes))
            salida[clave] = {'paso': 2, 'fuente': fuente,
                             't': parrafos(trozos)}
            cuenta['del salterio'] += 1

    # paso 2d — el Misal entero: muchas oraciones del devocionario son
    # colectas, y el Misal de la app las trae en las dos lenguas
    indice_m = indice_del_misal()
    print('%d piezas del Misal con las dos lenguas' % len(indice_m))
    for clave, p in piezas.items():
        if clave in salida:
            continue
        hallado = del_ordinario(p, indice_m, casi)
        if not hallado:
            continue
        f = hallado['fuente']
        f['obra'] = MISAL
        f['donde'] = ('app/datos/misa.json y misal_latino.json, '
                      + f['donde'].split(', ', 1)[-1])
        salida[clave] = {'paso': 2, 'fuente': f,
                         'parecido': hallado['parecido'],
                         't': parrafos(hallado['texto'])}
        cuenta['del Misal'] += 1

    # paso 3 — el Compendio del Catecismo, que publica la Santa Sede con
    # las dos lenguas enfrentadas. Sólo donde no haya ya traducción
    # aprobada para México: ésa manda, y es la que el usuario reza.
    indice_c, meta_c = indice_del_compendio()
    for clave, p in piezas.items():
        if clave in salida:
            continue
        hallado = del_compendio(p, indice_c, casi)
        if not hallado:
            continue
        salida[clave] = {
            'paso': 3, 'tes': hallado['tes'],
            'parecido': hallado['parecido'],
            'fuente': {'autoridad': meta_c['autoridad'],
                       'obra': meta_c['fuente'], 'url': meta_c['url'],
                       'territorio': 'universal', 'oficial': True,
                       'que_es': 'publicación de la Santa Sede; fórmula '
                                 'tradicional, no traducción litúrgica '
                                 'aprobada para México',
                       'latin_del_libro': hallado['latin_del_libro']},
            't': parrafos(hallado['texto']),
        }
        cuenta['del Compendio del Catecismo'] += 1

    por_titulo = {f[4]: f for f in indice_c}
    for clave, titulo, aviso in DEL_COMPENDIO:
        if clave in salida or clave not in piezas:
            continue
        f = por_titulo.get(titulo)
        if not f:
            print('¡ojo! el Compendio no trae «%s»' % titulo)
            continue
        salida[clave] = {
            'paso': 3, 'tes': f[3],
            'fuente': {'autoridad': meta_c['autoridad'],
                       'obra': meta_c['fuente'], 'url': meta_c['url'],
                       'territorio': 'universal', 'oficial': True,
                       'que_es': 'publicación de la Santa Sede; fórmula '
                                 'tradicional, no traducción litúrgica '
                                 'aprobada para México',
                       'aviso': aviso,
                       'latin_del_libro': f[1][:120]},
            't': parrafos(f[2]),
        }
        cuenta['del Compendio del Catecismo'] += 1

    # pasos 1, 3 y 4 — lo buscado fuera, a mano
    for clave, v in de_mano().items():
        if clave not in piezas:
            print('¡ojo! castellano a mano para una pieza que no existe: %s'
                  % clave)
            continue
        entrada_mano = dict(v)
        entrada_mano['t'] = parrafos(v['texto'] if 'texto' in v else v['t'])
        entrada_mano.pop('texto', None)
        salida[clave] = entrada_mano
        cuenta['a mano, paso %s' % v.get('paso', '?')] += 1

    # el íncipit latino se guarda para poder comprobar que, si alguna vez
    # cambian las piezas, el castellano sigue siendo el de esta oración
    for clave, v in salida.items():
        p = piezas[clave]
        la = ' '.join(t for b in p['b'] for ln in b['la'] for _, t in ln)
        v['incipit_la'] = la[:70]
        v.setdefault('tes', None)

    ruta = os.path.join(DATOS, 'castellano.json')
    with io.open(ruta, 'w', encoding='utf-8') as fh:
        json.dump({'fuente': 'fase 4 — el castellano del devocionario',
                   'piezas': salida}, fh, ensure_ascii=False, indent=1,
                  sort_keys=True)

    qa = os.path.join(DATOS, 'castellano_qa.txt')
    with io.open(qa, 'w', encoding='utf-8') as fh:
        fh.write('piezas con latín .......... %4d\n' % len(piezas))
        fh.write('piezas con castellano ..... %4d\n' % len(salida))
        for k, v in sorted(cuenta.items()):
            fh.write('  %-34s %4d\n' % (k, v))
        fh.write('\ncon castellano\n')
        for clave in sorted(salida):
            v = salida[clave]
            fh.write('  %-46s paso %s  %s\n'
                     % (clave, v.get('paso'),
                        (v['fuente'].get('obra') or '')[:46]))
        fh.write('\npendientes de castellano (%d)\n'
                 % (len(piezas) - len(salida)))
        for clave in sorted(piezas):
            if clave not in salida:
                fh.write('  %-46s %s\n' % (clave, piezas[clave]['tla'][:40]))
    print('%d de %d piezas con castellano -> %s'
          % (len(salida), len(piezas), ruta))
    print('informe: ' + qa)


if __name__ == '__main__':
    main()
