# -*- coding: utf-8 -*-
"""Fase 3b — el Propio de los santos de los cuatro tomos en PDF.

La fuente (liturgiadelashoras.github.io) publica cada día el oficio que
rezó, y en una memoria libre rezó siempre la feria: san Bruno, santa
Eduviges, san Juan Damasceno y otros sesenta santos no aparecen en ninguno
de sus ocho años, y no es que se perdieran, es que nunca se publicaron
(comprobado sobre el volcado entero y sobre la historia del repositorio,
que empieza en 2019).

Los cuatro tomos de `Breviarium/*.pdf` sí los traen, y además traen la
reseña de cada santo y la indicación del común del que toma lo que no
tiene propio. Esta fase lee su Propio de los santos y lo deja, sección por
sección y en el mismo formato de líneas de tiradas que el resto del libro,
en `datos/libro/pdf_santoral.json`.

Aquí tampoco se decide nada: la fase 4 usa estas entradas sólo para lo que
la fuente no tiene, y lo apunta en su informe. La traducción de los PDF es
la de la Conferencia Episcopal Española, no la de México: por eso es
siempre el último recurso, nunca la primera opción.

    python Breviarium/src/3b_pdf.py

Necesita `pdftotext` (poppler) en el PATH.
"""

import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from breviario import TRABAJO, clave

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDFS = os.path.join(RAIZ, 'Breviarium')
LIBRO = os.path.join(RAIZ, 'Breviarium', 'datos', 'libro')
QA = os.path.join(RAIZ, 'Breviarium', 'datos', 'pdf_qa.txt')
TEXTOS = os.path.join(TRABAJO, 'pdf')

TOMOS = [
    ('I', 'LH_I_ADVIENTO_NAVIDAD'),
    ('II', 'LH_II_CUARESMA_PASCUA'),
    ('III', 'LH_III_TIEMPO_ORDINARIO_I'),
    ('IV', 'LH_IV_TIEMPO_ORDINARIO_II'),
]

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


# --------------------------------------------------------------------------
# del PDF al texto
# --------------------------------------------------------------------------

def texto_de(nombre):
    """El tomo en texto, con la maquetación física (`-layout`): conserva los
    versos de los himnos en su línea, y los párrafos de la prosa sangrados.
    Se extrae una vez y se guarda en la carpeta de trabajo."""
    os.makedirs(TEXTOS, exist_ok=True)
    destino = os.path.join(TEXTOS, nombre + '.txt')
    pdf = os.path.join(PDFS, nombre + '.pdf')
    if (not os.path.exists(destino)
            or os.path.getmtime(destino) < os.path.getmtime(pdf)):
        print(f'  pdftotext {nombre}…', flush=True)
        r = subprocess.run(['pdftotext', '-enc', 'UTF-8', '-layout', pdf,
                            destino])
        if r.returncode:
            sys.exit(f'pdftotext falló con {pdf}')
    with open(destino, encoding='utf-8') as f:
        return f.read().split('\n')


def tramo_del_santoral(lineas):
    """Del rótulo del Propio de los santos al de los Oficios comunes. El
    índice del principio y los apéndices del final repiten esos rótulos, así
    que vale el tramo más largo."""
    ini = [i for i, l in enumerate(lineas)
           if l.strip().rstrip('!') == 'PROPIO DE LOS SANTOS']
    fin = [i for i, l in enumerate(lineas)
           if l.strip().rstrip('!') == 'OFICIOS COMUNES']
    # cada rótulo de comienzo con el primer rótulo de fin que lo sigue, sin
    # otro comienzo en medio: si no, el índice del tomo se tragaría el
    # Propio del tiempo entero
    mejor = (0, 0)
    for a in ini:
        b = next((x for x in fin if x > a), None)
        if b is None or any(a < x < b for x in ini):
            continue
        if b - a > mejor[1] - mejor[0]:
            mejor = (a, b)
    return lineas[mejor[0] + 1:mejor[1]]


CABECERA = re.compile(r'^\s*\f?\s*LITURGIA DE LAS HORAS\b.*TOMO', re.I)
PAGINA = re.compile(r'^\s*\f?\s*-?\d{1,4}-?\s*$')
PAGINA_AL_FINAL = re.compile(r'\s{6,}-?\d{1,4}-?\s*$')

HORAS_PDF = {
    'oficio de lectura': 'oficio', 'laudes': 'laudes', 'visperas': 'visperas',
    'i visperas': 'i_visperas', 'ii visperas': 'visperas',
    'primeras visperas': 'i_visperas', 'segundas visperas': 'visperas',
    'hora intermedia': 'intermedia', 'tercia': 'tercia', 'sexta': 'sexta',
    'nona': 'nona', 'completas': 'completas', 'invitatorio': 'invitatorio',
    # san Juan Diego, en el tomo I: las dos horas con un mismo formulario
    'laudes y visperas': 'laudes_visperas',
}


def es_hora(t):
    return HORAS_PDF.get(clave(t))


def limpia(lineas):
    """Fuera las cabeceras y los números de página. Donde había un salto de
    página queda la marca `None`, porque un párrafo puede seguir al otro
    lado y hay que saberlo para coserlo."""
    salida = []
    for l in lineas:
        l = l.replace('\f', '').replace('­', '').rstrip()
        if CABECERA.match(l):
            salida.append(None)
            continue
        if PAGINA.match(l):
            continue
        # el rótulo del mes («FEBRERO») que abre cada mes del santoral
        if l.strip().lower() in MESES and l.strip().isupper():
            continue
        l = PAGINA_AL_FINAL.sub('', l)
        # «HIMNO        Laudes»: el rótulo de la hora, centrado, cae en la
        # misma línea física que el de la sección. Se separan, y la hora va
        # delante, que es donde está en la página.
        partes = re.split(r'\s{2,}', l.strip())
        if len(partes) > 1 and any(es_hora(p) for p in partes):
            horas = [p for p in partes if es_hora(p)]
            otras = [p for p in partes if not es_hora(p)]
            for p in horas + otras:
                salida.append(p)
            continue
        salida.append(l)
    return salida


# --------------------------------------------------------------------------
# las entradas de cada santo
# --------------------------------------------------------------------------

# El «de» es optativo: el tomo IV rotula «22 octubre» a san Juan Pablo II, y
# con el «de» obligatorio esa fecha no abría entrada y el oficio entero del
# papa —reseña, lectura, responsorio y oración— se pegaba al de san Pablo de
# la Cruz, el último del 19. Es la única fecha de los cuatro tomos sin «de».
FECHA = re.compile(r'^(?:El mismo(?: día)?\s+)?(\d{1,2})\s+(?:de\s+)?('
                   + '|'.join(MESES) + r')$', re.I)
# el rótulo de una celebración movible, que abre entrada aunque no sea fecha;
# «Jueves de la II semana de Pascua» (la Santa Faz) también, que si no se
# pegaba a san Vicente Ferrer
MOVIBLE = re.compile(
    r'^(?:Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[áa]bado|Domingo)\b'
    r'[^.]*\b(?:despu[eé]s|siguiente|anterior|posterior|antes|semana)\b',
    re.I)
GRADOS = {'memoria': 'MEMORIA', 'fiesta': 'FIESTA',
          'solemnidad': 'SOLEMNIDAD', 'memoria libre': 'MEMORIA LIBRE'}


def es_versal(t):
    letras = [c for c in t if c.isalpha()]
    return len(letras) > 2 and all(c.isupper() for c in letras)


# Las rúbricas que van entre el título y el oficio y no son reseña: dónde se
# celebra con otro grado, dónde están los himnos latinos, qué se hace en
# Cuaresma…
RUBRICA_PREVIA = re.compile(
    r'^(Los himnos latinos|En (el )?Per[uú]|En España|Fuera de España|'
    r'Propio de|Del Propio|Todo |Cuando |En los (países|lugares)|'
    r'En algunos|En la|En el tiempo|Para la conmemoración|Basílica|'
    r'República|Mercedarios|Madrid|\(El día|Donde |Si )')
# «En España: Solemnidad. Fuera de España: Fiesta Nació en Betsaida…»
SITIOS = re.compile(r'^((?:En|Fuera de|Propio de|Del Propio de)\s[^:.]{2,60}:'
                    r'\s*(?:Solemnidad|Fiesta|Memoria(?: libre)?)\.?\s*)+')


def trocea(lineas):
    """El santoral, partido en entradas: una por cada «6 de octubre»."""
    entradas, act = [], None
    mismo_dia = False
    for n, l in enumerate(lineas):
        t = (l or '').strip()
        if t in ('El mismo día', 'El mismo'):
            mismo_dia = True
            continue
        # No todas las celebraciones del Propio de los santos tienen fecha
        # fija: «Lunes después del II domingo de Pascua — san Vicente
        # Ferrer», «Jueves después de Pentecostés — Jesucristo, sumo y
        # eterno sacerdote». Sin cortar por ahí, el oficio entero de esas
        # cinco se pegaba al del santo anterior, y san Pío V salía con las
        # antífonas de san Vicente. El día movible no se guarda —de las
        # fiestas movibles sabe el calendario del proyecto, que es quien
        # las coloca—, pero el corte sí.
        if MOVIBLE.match(t) and len(t) < 80:
            sig = next((x.strip() for x in lineas[n + 1:n + 6]
                        if x and x.strip()), '')
            if es_versal(sig) and not es_hora(sig) and not seccion_de(sig)[0]:
                act = {'md': None, 'mismo_dia': False, 'lineas': []}
                entradas.append(act)
                mismo_dia = False
                continue
        m = FECHA.match(t)
        if m:
            act = {'md': f'{MESES.index(m.group(2).lower()) + 1:02d}-'
                         f'{int(m.group(1)):02d}',
                   'mismo_dia': mismo_dia or t.startswith('El mismo'),
                   'lineas': []}
            entradas.append(act)
            mismo_dia = False
            continue
        if act is not None:
            act['lineas'].append(l)
    return entradas


CASI_FECHA = re.compile(r'^(?:El mismo\b\D*)?\d{1,2}\b.*\b(?:'
                        + '|'.join(MESES) + r')\b', re.I)
DIA_SEMANA = re.compile(
    r'^(?:Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[áa]bado|Domingo)\b', re.I)


def cortes_dudosos(lineas):
    """Los rótulos que parecen de día y no abren entrada: una fecha centrada
    que FECHA no reconoce, o un día de la semana con un título en versales
    detrás que MOVIBLE deja pasar. Lo que hay debajo se pega al santo
    anterior sin que nada falle, así que va al informe para que se vea."""
    dudosos = []
    for n, l in enumerate(lineas):
        if not l:
            continue
        t = l.strip()
        centrada = len(l) - len(l.lstrip()) >= 15
        if centrada and len(t) <= 40 and CASI_FECHA.search(t) \
                and not FECHA.match(t) and not t.startswith('('):
            dudosos.append((n, t))
            continue
        if DIA_SEMANA.match(t) and len(t) < 80 and not MOVIBLE.match(t):
            sig = next((x.strip() for x in lineas[n + 1:n + 6]
                        if x and x.strip()), '')
            if es_versal(sig) and not es_hora(sig) and not seccion_de(sig)[0]:
                dudosos.append((n, t))
    return dudosos


# Los rótulos de sección del PDF, a las clases del libro. El orden importa:
# «RESPONSORIO BREVE» antes que «Responsorio».
SECCIONES = [
    (re.compile(r'^PRIMERA LECTURA\b'), 'lectura1'),
    (re.compile(r'^SEGUNDA LECTURA\b'), 'lectura2'),
    (re.compile(r'^RESPONSORIO BREVE\b', re.I), 'responsorio_breve'),
    (re.compile(r'^Responsorio\b', re.I), 'responsorio'),
    (re.compile(r'^LECTURA BREVE\b', re.I), 'lectura_breve'),
    (re.compile(r'^C[ÁA]NTICO EVANG[ÉE]LICO\b', re.I), 'cantico_evangelico'),
    (re.compile(r'^PRECES\b'), 'preces'),
    (re.compile(r'^HIMNO\b(?!\s+Te Deum)'), 'himno'),
    (re.compile(r'^Himno Te Deum', re.I), 'te_deum'),
    (re.compile(r'^SALMODIA\b'), 'salmodia'),
    (re.compile(r'^(ORACIÓN|Oración|ORACION|Oracion)\b'), 'oracion'),
]


def seccion_de(t):
    for rx, cl in SECCIONES:
        if rx.match(t):
            return cl, t[rx.match(t).end():].strip()
    return None, None


def parrafos(lineas, verso=False):
    """Las líneas físicas de una sección, hechas párrafos.

    En la prosa, un párrafo empieza con sangría o tras una línea en blanco,
    y un salto de página no lo corta si la frase sigue al otro lado. En los
    himnos (`verso`), cada línea es un verso y la línea en blanco separa las
    estrofas."""
    out, act = [], []
    pendiente_pagina = False

    def cierra():
        nonlocal act
        if act:
            out.append(' '.join(act))
        act = []

    blanco = False
    for l in lineas:
        if l is None:
            pendiente_pagina = True
            continue
        t = l.strip()
        if not t or re.fullmatch(r'[*\s]+', t):
            if verso:
                cierra()
                if out and out[-1] != '':
                    out.append('')
            blanco = True
            continue
        sangria = len(l) - len(l.lstrip())
        if verso:
            if pendiente_pagina and act and not re.search(r'[.!?»:;,]$', act[-1]) \
                    and t[0].islower():
                act[-1] += ' ' + t
            else:
                cierra()
                act.append(t)
            pendiente_pagina = blanco = False
            continue
        # Un salto de página no corta el párrafo si la frase sigue al otro
        # lado: la línea de antes no acaba en punto, o la de después empieza
        # en minúscula. La línea en blanco que deja la maqueta antes del pie
        # de página no cuenta.
        cosido = pendiente_pagina and act and (
            not re.search(r'[.!?»”"):]$', act[-1]) or t[0].islower())
        if not cosido and act and (
                blanco or pendiente_pagina or sangria >= 2
                or re.match(r'^(R\.|V\.|Ant\.|—|-\s)', t)):
            cierra()
        if cosido and act[-1].endswith('-'):
            act[-1] = act[-1][:-1] + t
        else:
            act.append(t)
        pendiente_pagina = blanco = False
    cierra()
    while out and out[-1] == '':
        out.pop()
    return out


def runs(texto):
    """Un párrafo, partido en tiradas: lo que es rúbrica («R.», «V.»,
    «Ant.», el asterisco del responsorio) va en rojo, como en la fuente."""
    t = texto
    m = re.match(r'^(R\.|V\.|Ant\.(?:\s*\d\.?)?|—)\s*', t)
    salida = []
    if m:
        salida.append([1, m.group(1) + ' '])
        t = t[m.end():]
    trozos = re.split(r'\s\*\s', t)
    for n, tr in enumerate(trozos):
        if n:
            salida.append([1, '*'])
        salida.append([0, (' ' if n else '') + tr
                       + (' ' if n < len(trozos) - 1 else '')])
    return salida


def a_lineas(pars, rojas=()):
    """Párrafos a líneas de tiradas, con una línea vacía delante, que es
    como las guarda la fuente."""
    out = [[]]
    for p in pars:
        if p == '':
            out.append([])
        elif p in rojas:
            out.append([[1, p]])
        else:
            out.append(runs(p))
    return out


def lee_entrada(e):
    """De las líneas de una entrada, su título, grado, reseña, común y
    secciones."""
    ls = e['lineas']
    i = 0
    # el título: líneas en versales, una o dos
    titulo = []
    while i < len(ls):
        t = (ls[i] or '').strip()
        if not t:
            if titulo:
                # un título partido en dos líneas con un blanco en medio
                j = i + 1
                while j < len(ls) and not (ls[j] or '').strip():
                    j += 1
                if j < len(ls) and es_versal((ls[j] or '').strip()) \
                        and not es_hora((ls[j] or '').strip()) \
                        and not seccion_de((ls[j] or '').strip())[0]:
                    i = j
                    continue
                i += 1
                break
            i += 1
            continue
        if es_versal(t) and not seccion_de(t)[0]:
            titulo.append(t)
            i += 1
            continue
        break
    e['titulo'] = ' '.join(titulo).strip()

    # Lo que va entre el título y la primera hora: el grado, la reseña, la
    # indicación del común y alguna rúbrica suelta (dónde se celebra cómo,
    # dónde están los himnos latinos). Se junta en párrafos y se clasifica
    # cada uno.
    previo = []
    while i < len(ls):
        t = (ls[i] or '').strip()
        if ls[i] is not None and t and (es_hora(t) or seccion_de(t)[0]):
            break
        previo.append(ls[i])
        i += 1
    grado = None
    resena, comun, notas = [], [], []
    for p in parrafos(previo):
        if not p:
            continue
        m = re.match(r'^(Memoria libre|Memoria|Fiesta|Solemnidad)\b\.?\s*(.*)$', p)
        if m and grado is None and not resena:
            grado = GRADOS[m.group(1).lower()]
            p = m.group(2).strip()
            if not p:
                continue
        # la indicación del común puede ir pegada al final de la reseña, sin
        # línea en blanco: se corta por ella
        mc = re.search(r'\b(?:Del|del|Todo del|Todo como en el|Como en el)\s+'
                       r'(?:[Cc]om[uú]n|Oficio de (?:la feria|difuntos))', p)
        if mc:
            comun.append(p[mc.start():])
            p = p[:mc.start()].strip()
            if not p:
                continue
        if RUBRICA_PREVIA.match(p) or (comun and len(p) < 160):
            notas.append(p)
            continue
        p = SITIOS.sub('', p).strip()
        if p:
            resena.append(p)
    e['grado'] = grado
    e['resena'] = ' '.join(resena).strip() or None
    e['comun'] = ' '.join(comun).strip() or None
    e['notas'] = notas

    # las horas y sus secciones
    hora, sec, secciones, orden = None, None, {}, []
    texto_sec = []
    cuenta_resp = Counter()

    def guarda():
        if hora and sec and texto_sec is not None:
            # «Laudes y vísperas»: lo mismo en las dos (el cántico, en cada
            # una el suyo, que la fase 4 arma con la antífona)
            for h in (('laudes', 'visperas') if hora == 'laudes_visperas'
                      else (hora,)):
                secciones.setdefault(f'{h}/{sec}', []).extend(texto_sec)

    while i < len(ls):
        l = ls[i]
        t = (l or '').strip()
        h = es_hora(t) if l is not None else None
        if h:
            guarda()
            # el invitatorio es sólo su antífona, sin rótulo de sección
            hora, sec, texto_sec = h, SIN_ROTULO.get(h), []
            if sec == 'antifona':
                sec = None
            i += 1
            continue
        cl, resto = seccion_de(t) if l is not None else (None, None)
        # Las antífonas de la salmodia detrás del himno sin el rótulo
        # «SALMODIA» (las Laudes de Jesucristo, sumo y eterno sacerdote, en
        # el tomo III): un «Ant. 1.» no es un verso, abre la salmodia
        if not cl and sec == 'himno' and l is not None and ABRE_ANT_PDF.match(t):
            guarda()
            sec, texto_sec = 'salmodia', [l]
            if (hora, sec) not in orden:
                orden.append((hora, sec))
            i += 1
            continue
        if cl:
            guarda()
            if cl == 'responsorio' and hora == 'oficio':
                # el que sigue a la segunda lectura es el segundo
                cl = 'responsorio2' if 'oficio/lectura2' in secciones \
                    or sec == 'lectura2' else 'responsorio'
            if hora is None:
                # la «SEGUNDA LECTURA» va siempre en el Oficio de lectura,
                # aunque la maqueta deje su rótulo detrás
                hora = 'oficio' if cl in ('lectura1', 'lectura2') else hora
            sec = cl
            texto_sec = [resto] if resto else []
            if (hora, sec) not in orden:
                orden.append((hora, sec))
            i += 1
            continue
        texto_sec.append(l)
        i += 1
    guarda()
    e['secciones_crudas'] = secciones
    del e['lineas']
    return e


# --------------------------------------------------------------------------
# cada sección, a líneas de tiradas
# --------------------------------------------------------------------------

def separa_cabeza(pars):
    """De una lectura: la cita o el autor, la referencia entre paréntesis y
    el título en versales; luego el texto."""
    cabeza, i = [], 0
    while i < len(pars) and i < 4:
        p = pars[i]
        if es_versal(p) or p.startswith('(') or (i == 0) \
                or (cabeza and not cabeza[-1].endswith(')')
                    and not es_versal(cabeza[-1]) and len(p) < 140
                    and p.startswith('(')):
            cabeza.append(p)
            i += 1
            # (la referencia en mayúsculas, «(SALMO 61, 4: CCL 39…)», no es
            # el título: va detrás)
            if es_versal(p) and not p.startswith('('):
                # el título largo sigue centrado en el renglón de abajo
                # («… CUALIDADES Y LOS DEBERES DE / LOS OBISPOS»)
                while i < len(pars) and es_versal(pars[i]) \
                        and len(pars[i]) < 80:
                    cabeza[-1] += ' ' + pars[i]
                    i += 1
                break
            continue
        break
    return cabeza, pars[i:]


def lectura(lineas):
    pars = [p for p in parrafos(lineas) if p]
    cabeza, cuerpo = separa_cabeza(pars)
    out = [[]]
    for p in cabeza:
        if es_versal(p) and not p.startswith('('):
            out += [[], [[1, p]]]
            continue
        # el autor y, en su línea, la referencia entre paréntesis
        m = re.match(r'^(.*\S)\s+(\([^()]*(?:\([^()]*\)[^()]*)*\))$', p)
        if m and not p.startswith('('):
            out += [[[0, m.group(1)]], [[0, m.group(2)]]]
        else:
            out.append([[0, p]])
    for p in cuerpo:
        out += [[], [[0, p]]]
    return out


def responsorio(lineas, cita=''):
    pars = [p for p in parrafos(lineas) if p]
    # «R. … * … V. … R. …» puede venir en un solo párrafo
    junto = ' '.join(pars)
    # la remisión que sigue al responsorio en las memorias
    junto = re.sub(r'\s*La( oración (conclusiva )?como en (las )?Laudes\.?)?\s*$',
                   '', junto)
    trozos = re.split(r'\s(?=(?:R|V)\.\s)', junto)
    if trozos and not re.match(r'^(R|V)\.', trozos[0]):
        cita = (cita + ' ' + trozos.pop(0)).strip()
    return cita, [[]] + [runs(t) for t in trozos]


# El PDF abrevia de varias maneras: «Él que vive y reina contigo.», «Él, que
# vive y reina.» (san Juan Pablo II), «Por nuestro Señor Jesucristo, tu
# Hijo.» (san Alfonso)
FINALES = [
    (r'Por nuestro Señor Jesucristo(?:, tu Hijo)?\.?$',
     'Por nuestro Señor Jesucristo, tu Hijo, que vive y reina contigo en la '
     'unidad del Espíritu Santo y es Dios, por los siglos de los siglos. Amén'),
    (r'[ÉE]l,? que vive y reina(?: contigo)?\.?$',
     'Él, que vive y reina contigo en la unidad del Espíritu Santo y es '
     'Dios, por los siglos de los siglos. Amén'),
    (r'Que vive y reina(?: contigo)?\.?$',
     'Que vive y reina contigo en la unidad del Espíritu Santo y es Dios, '
     'por los siglos de los siglos. Amén'),
    (r'Que vives y reinas\.?$',
     'Que vives y reinas por los siglos de los siglos. Amén'),
]


def oracion(lineas):
    """La oración, con la conclusión larga, que es como la da la fuente en
    el Oficio, Laudes y Vísperas (el PDF la abrevia)."""
    t = ' '.join(p for p in parrafos(lineas) if p).strip()
    t = re.sub(r'^La oración conclusiva.*$', '', t).strip()
    t = re.sub(r'\s+Cuando se celebra como [^.]*:?\s*$', '', t).strip()
    for rx, largo in FINALES:
        t2 = re.sub(rx, largo, t)
        if t2 != t:
            t = t2
            break
    return [[], [[0, t]]] if t else None


def antifona(lineas):
    """La antífona del cántico evangélico: de «Ant.» hasta «Benedictus»."""
    pars = [p for p in parrafos(lineas) if p]
    ants = []
    for p in pars:
        if re.match(r'^(Benedictus|Magn[iíl]ficat|Nunc dimittis)\b', p):
            break
        if re.match(r'^O bien', p, re.I):
            continue
        p = re.sub(r'^Ant\.\s*', '', p)
        # «… te trae preparada. Magnificat La oración conclusiva…», y «…
        # Aquí está su Dios. Cuando se rezan Laudes: Benedictus»
        p = re.split(r'\s+(?:Benedictus|Magn[iíl]ficat|Cuando se rezan|'
                     r'El salmo (?:del )?[Ii]nvitatorio)\b', p)[0].strip()
        if p:
            ants.append(p)
    return ants


# --------------------------------------------------------------------------
# la salmodia: lo que el libro dice de ella y la fuente no escribe
# --------------------------------------------------------------------------
# La fuente publica días ya armados: pone los salmos que toca y calla de
# dónde los toma. El libro impreso sí lo dice, y lo dice de tres maneras:
#
#   «Los salmos y el cántico se toman del domingo de la I semana del Salterio»
#   «Los salmos y el cántico se toman del Común de pastores»
#   —o los escribe enteros, uno detrás de otro, porque son suyos.
#
# Esa rúbrica es la que faltaba. De los salmos escritos se guarda sólo su
# *título* («Salmo 33 I», «Cántico Ap 11, 17-18»): el texto que vale es el
# de la fuente —es su traducción la que reza la app—, y con el título se
# sabe cuáles son. Lo que se toma del PDF es la indicación, no el salmo.

DIAS_SEM_PDF = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves',
                'viernes', 'sábado']
ROMANOS_PDF = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}

# «del domingo de la I semana del Salterio», «del domingo de la semana I del
# Salterio»: el día va delante y el número de la semana a un lado o a otro
DEL_SALTERIO = re.compile(
    r'\b(domingo|lunes|martes|mi[eé]rcoles|jueves|viernes|s[áa]bado)\b'
    r'(?:(?:\s+de)?\s+la\s+(?:(I{1,3}|IV)\s+semana|semana\s+(I{1,3}|IV))'
    r'|\s+(I{1,3}|IV))\s+del\s+[Ss]alterio', re.I)
DEL_COMUN = re.compile(r'[Cc]om[uú]n\s+de\b')
DE_LA_FERIA = re.compile(r'\bde la feria\b', re.I)
# la rúbrica habla de los salmos, no es una antífona ni un verso
DICE_SALMOS = re.compile(r'^(?:Los salmos|El salmo|Los dos salmos|Salmos|'
                         r'Los c[áa]nticos|El c[áa]ntico|'
                         r'Todo\s+(?:del|lo|como))\b')
TITULO_SALMO_PDF = re.compile(r'^(Salmo|C[áa]ntico)\b')
ABRE_ANT_PDF = re.compile(r'^Ant\.?\s*(\d)\s*\.?\s*')
# La antífona y la rúbrica que la sigue caen a veces en el mismo párrafo: el
# libro las pone en renglones seguidos, sin blanco ni sangría en medio, y
# entonces «Ant. 1. Establezco hostilidades…» se traía detrás «Los salmos y
# el cántico se toman del Común de Santa María Virgen». Se cortan las dos.
PARTE_ANT = re.compile(r'\s+(?=Ant\.\s*\d\s*\.)|'
                       r'(?<=[.!?»])\s+(?=(?:Los salmos|El salmo|'
                       r'Los dos salmos|Los c[áa]nticos|El c[áa]ntico)\b)')


def dia_del_salterio(t):
    """«del domingo de la I semana del Salterio» -> «1/0», la casilla del
    salterio, en la misma forma en que la nombra `antifonas.json`."""
    m = DEL_SALTERIO.search(t)
    if not m:
        return None
    sem = ROMANOS_PDF.get(
        (m.group(2) or m.group(3) or m.group(4) or '').upper())
    dia = clave(m.group(1))
    ds = next((n for n, d in enumerate(DIAS_SEM_PDF) if clave(d) == dia), None)
    return f'{sem}/{ds}' if sem and ds is not None else None


def titulos_de_salmos(lineas):
    """Los títulos de los salmos que el libro escribe enteros. Se leen de las
    líneas físicas y no de los párrafos: el título va centrado, y la maqueta
    deja a veces el primer verso en su misma línea («Salmo 8        Señor,
    dueño nuestro,»)."""
    out = []
    for l in lineas:
        if l is None:
            continue
        t = l.strip()
        if not TITULO_SALMO_PDF.match(t):
            continue
        t = re.sub(r'\s+', ' ', re.split(r'\s{2,}', t)[0]).strip(' .,')
        if t and t not in out:
            out.append(t)
    return out


def salmodia(lineas):
    """La salmodia de una celebración, como la trae el libro impreso: sus
    antífonas, de dónde salen los salmos y la rúbrica que lo dice."""
    pars = []
    for p in parrafos(lineas):
        if p:
            pars += [x.strip() for x in PARTE_ANT.split(p) if x.strip()]
    ants, rubricas = [], []
    for p in pars:
        m = ABRE_ANT_PDF.match(p)
        if m:
            ants.append((int(m.group(1)), p[m.end():].strip()))
            continue
        if p.startswith('Ant'):            # la que repite al final del salmo
            continue
        if DICE_SALMOS.match(p):
            rubricas.append(p)
    # las antífonas, en el orden que les da su número, y sin repetir
    ants = [t for _, t in sorted(ants, key=lambda x: x[0]) if t]
    titulos = titulos_de_salmos(lineas)
    rub = ' '.join(rubricas).strip()
    de = None
    if rub:
        sal = dia_del_salterio(rub)
        if sal:
            de = {'salterio': sal}
        elif DEL_COMUN.search(rub):
            de = {'comun': rub}
        elif DE_LA_FERIA.search(rub):
            de = {'feria': 1}
    # los salmos escritos enteros manda sobre cualquier rúbrica suelta: son
    # los suyos, y están ahí porque no se toman de ninguna otra parte
    if titulos and not de:
        de = {'propios': titulos}
    if not ants and not de:
        return None
    pieza = {'r': 'SALMODIA'}
    if ants:
        pieza['ant'] = ants
    if de:
        pieza['de'] = de
        # el texto de la rúbrica vale cuando dice de dónde salen los salmos;
        # si no apunta a ninguna parte no es una rúbrica de la salmodia
        if rub:
            pieza['rub'] = rub
    if titulos:
        pieza['salmos'] = titulos
    return pieza


def himno(lineas):
    versos = parrafos(lineas, verso=True)
    primero = next((v for v in versos if v), '')
    # «HIMNO, como en las Laudes», «El himno como en las I Vísperas»: es una
    # remisión, no un himno
    if re.match(r'^(,|como en|el himno como|del común|propio)', primero, re.I):
        return None
    out = [[]]
    for v in versos:
        if re.match(r'^(El himno latino|Pueden usarse|O bien)', v):
            break
        out.append([] if v == '' else [[0, v]])
    return out if len(out) > 2 else None


def secciones_de(e):
    """Las secciones crudas de una entrada, hechas piezas del libro."""
    piezas, avisos = {}, []
    crudas = e['secciones_crudas']
    for k, ls in crudas.items():
        pieza = pieza_de(k, ls)
        if pieza is False:
            avisos.append(f'{e["md"]} {e["titulo"]}: sección {k} sin tratar')
        elif pieza:
            piezas[k] = pieza
    # La oración del santo es la misma en todas las horas: en las memorias el
    # PDF la da una vez, en el Oficio («La oración conclusiva como en las
    # Laudes», o al revés), y la app la busca en cada hora.
    orac = piezas.get('oficio/oracion') or piezas.get('laudes/oracion')
    if orac:
        for k in ('oficio/oracion', 'laudes/oracion', 'visperas/oracion'):
            piezas.setdefault(k, orac)
    return piezas, avisos


def pieza_de(k, ls):
    """Las líneas crudas de una sección (`hora/sección`), hechas pieza del
    libro; None si no hay nada que guardar, False si la sección no se sabe
    tratar."""
    hora, cl = k.split('/')
    if cl == 'te_deum':
        return None
    cuerpo = list(ls)
    if cl in ('lectura1', 'lectura2'):
        pieza = {'r': 'PRIMERA LECTURA' if cl == 'lectura1'
                 else 'SEGUNDA LECTURA', 'l': lectura(cuerpo)}
    elif cl in ('responsorio', 'responsorio2', 'responsorio_breve'):
        primera = next((l.strip() for l in cuerpo if l and l.strip()), '')
        cita = ''
        if primera and not re.match(r'^(R|V)\.', primera):
            cita = primera
            cuerpo = cuerpo[cuerpo.index(next(
                l for l in cuerpo if l and l.strip())) + 1:]
        cita, ls2 = responsorio(cuerpo, cita)
        rot = 'RESPONSORIO BREVE' if cl == 'responsorio_breve' \
            else 'RESPONSORIO'
        pieza = {'r': (rot + ' ' + cita).strip(), 'l': ls2}
    elif cl == 'oracion':
        ls2 = oracion(cuerpo)
        if not ls2:
            return None
        pieza = {'r': 'ORACION', 'l': ls2}
    elif cl in ('cantico_evangelico', 'invitatorio', 'antifona'):
        ants = antifona(cuerpo)
        if not ants:
            return None
        pieza = {'r': {'cantico_evangelico': 'CÁNTICO EVANGÉLICO',
                       'invitatorio': 'INVITATORIO'}.get(cl, 'ANTÍFONA'),
                 'ant': ants}
    elif cl == 'himno':
        ls2 = himno(cuerpo)
        if not ls2:
            return None
        pieza = {'r': 'HIMNO', 'l': ls2}
    elif cl == 'lectura_breve':
        pars = [p for p in parrafos(cuerpo) if p]
        cita = ''
        if pars and len(pars[0]) < 40 and re.search(r'\d', pars[0]):
            cita = pars.pop(0)
        # el versículo que sigue a la lectura breve de la Hora
        # intermedia lleva su «V.» y su «R.» en rojo, como en la fuente
        pieza = {'r': ('LECTURA BREVE ' + cita).strip(),
                 'l': [[]] + [runs(p) if re.match(r'^(V|R)\.\s', p)
                              else [[0, p]] for p in pars]}
    elif cl == 'salmodia':
        pieza = salmodia(cuerpo)
        if not pieza:
            return None
    elif cl == 'preces':
        # La rúbrica de las intenciones libres va en su renglón y en
        # rojo; la maqueta la deja pegada a la última petición, y con
        # ella la invitación al Padre nuestro, que va detrás aparte.
        pars, rubricas = [], set()
        for p in parrafos(cuerpo):
            trozos = re.split(r'\s*(Se pueden añadir algunas intenciones '
                              r'libres\.)\s*', p)
            for t in trozos:
                if t.startswith('Se pueden añadir'):
                    rubricas.add(t)
                if t or not p:
                    pars.append(t)
        pieza = {'r': 'PRECES', 'l': [[]] + [
            [[1, p]] if p in rubricas else runs(p) if p else []
            for p in pars if not p.startswith('Padre nuestro')]}
    else:
        return False
    return pieza


# --------------------------------------------------------------------------
# los Oficios comunes
# --------------------------------------------------------------------------
# De un común, la fase 3 sólo sabe lo que rezan con él dos santos distintos,
# y eso es casi siempre lo de las memorias: el himno, la lectura breve, las
# preces. Lo que sólo se reza en las fiestas —la salmodia del Oficio y de
# las Vísperas, las lecturas del Oficio, la antífona del Benedictus de un
# obispo, la lectura breve de Tercia— no lo midió nunca: la fuente es
# argentina y casi no tiene fiestas que lo tomen del común. San Rafael
# Guízar, que en México es fiesta y lo toma todo del Común de pastores,
# salía con la salmodia, las lecturas y el Benedictus de la feria.
#
# El tomo IV trae los comunes enteros, y aquí se leen hora por hora y
# sección por sección, con sus variantes: dentro de una sección el libro
# dice «Para un santo papa u obispo:», «Para un santo presbítero:», «O bien:»
# y da otro texto. Cada variante se guarda con su rótulo; cuál va con cada
# común de la app lo decide la fase 4, que además busca cada texto en la
# fuente antes de tomarlo de aquí.

TOMO_COMUNES = 'LH_IV_TIEMPO_ORDINARIO_II'

# el rótulo de cada común, al nombre con que lo conoce el libro de la fuente
# Al final de los santos varones y las santas mujeres vienen tres comunes
# más cortos —los religiosos, los que se consagraron a una actividad
# caritativa, los educadores—, que toman todo de aquéllos «excepto lo
# siguiente». Van delante, que «santos varones» lo nombran todos.
NOMBRE_COMUN = [('religiosos', 'santos varones para los santos religiosos'),
                ('consagrado', 'santos varones para los santos que '
                 'se distinguieron por el ejercicio de las obras de '
                 'misericordia'),
                ('educadores', 'santos varones para los santos educadores'),
                ('dedicacion', 'dedicacion de una iglesia'),
                ('virgen maria', 'santisima virgen maria'),
                ('apostoles', 'apostoles'),
                ('varios martires', 'varios martires'),
                ('un martir', 'un martir'), ('pastores', 'pastores'),
                ('doctores', 'doctores de la iglesia'),
                ('virgenes', 'virgenes'), ('santos varones', 'santos varones'),
                ('santas mujeres', 'santas mujeres')]

TITULO_COMUN = re.compile(r'^(?:COMÚN DE\b.*|PARA VARIOS MÁRTIRES|'
                          r'PARA UN MÁRTIR|MEMORIA DE SANTA MARÍA EN SÁBADO|'
                          r'PARA RELIGIOSOS|PARA EDUCADORES|'
                          r'PARA LOS QUE SE HAN CONSAGRADO A UNA)$')
# «En el tiempo ordinario:», delante de la otra primera lectura de los
# religiosos (la de antes es la de los tiempos fuertes)
EN_EL_TIEMPO = re.compile(r'^En el tiempo (?:de )?([^:]{3,60}):$')

# «Para un santo papa u obispo:», «Para una mártir», «Antífona para un santo
# papa u obispo: Sacerdote del Altísimo…», «Para varios santos: Los ojos del
# Señor…». Sólo cuando nombra a quién: «Para que te prepares…» es prosa, y
# «Para vosotros, el misterio del Padre;», un verso.
VARIANTE = re.compile(
    r'^(?:Ant[íi]fona\s+)?[Pp]ara\s+((?:un|una|unos|unas|varios|varias|los|'
    r'las|santos|santas)\s+(?:santos?|santas?|m[áa]rtir(?:es)?|mujer(?:es)?|'
    r'v[íi]rgen(?:es)?|pastor(?:es)?|pap[ao]s?)\b[^:]*?)\s*(?::\s*(.*))?$')
# «O bien:», «O bien esta otra:», «O bien esta otra, especialmente para un
# santo obispo:», «O bien, para una santa que vivió en el matrimonio:»,
# «O bien: Finísimo fue el lino.»
O_BIEN = re.compile(r'^O bien\b(?:\s+esta\s+[Oo]tra)?\s*,?\s*'
                    r'(?:(?:especialmente\s+)?para\s+([^:]+):)?\s*:?\s*(.*)$')
# lo que en una antífona es rúbrica y no texto: «Cuando se usa la salmodia
# complementaria…», el rótulo «Antífona» suelto, la apertura del invitatorio
RUBRICA_ANT = re.compile(r'^(?:Cuando se\b|Si (?:se|es|antes)\b|'
                         r'Ant[íi]fona\s*:?$|[VR]\.\s|El salmo del\b|'
                         r'Se (?:dice|toma|añade)\b|La oraci[oó]n\b)')
# la sección que abre cada hora sin rótulo propio: el invitatorio es sólo su
# antífona, y la de Tercia, Sexta y Nona va delante de la lectura breve
SIN_ROTULO = {'invitatorio': 'invitatorio', 'tercia': 'antifona',
              'sexta': 'antifona', 'nona': 'antifona'}


def tramo_de_los_comunes(lineas):
    """De «OFICIOS COMUNES» a «OFICIO DE DIFUNTOS»: el tramo más largo, que
    el índice del tomo repite los dos rótulos."""
    ini = [i for i, l in enumerate(lineas) if l.strip() == 'OFICIOS COMUNES']
    fin = [i for i, l in enumerate(lineas) if l.strip() == 'OFICIO DE DIFUNTOS']
    mejor = (0, 0)
    for a in ini:
        b = next((x for x in fin if x > a), None)
        if b is not None and b - a > mejor[1] - mejor[0]:
            mejor = (a, b)
    return lineas[mejor[0] + 1:mejor[1]]


def nombre_del_comun(titulo):
    t = clave(titulo)
    if 'sabado' in t:
        return None
    return next((n for k, n in NOMBRE_COMUN if k in t), None)


def secciones_del_comun(lineas):
    """Las líneas de un común, repartidas por (hora/sección, variante).

    La variante cambia con cada «Para …:» y cada «O bien:», y vuelve a la
    general con cada rótulo de sección. El responsorio va con su lectura:
    las del Oficio traen una por variante, cada una con el suyo, así que un
    «Para un santo presbítero:» después de un responsorio vuelve a abrir la
    lectura."""
    crudas = defaultdict(list)
    orden = []
    hora, sec, var = None, None, ''
    vista_l2 = False

    def pon(l):
        if hora and sec:
            k = (f'{hora}/{sec}', var)
            if k not in crudas:
                orden.append(k)
            crudas[k].append(l)

    for l in lineas:
        t = (l or '').strip()
        if l is not None and t:
            h = es_hora(t)
            if h:
                hora, sec, var = h, SIN_ROTULO.get(h), ''
                vista_l2 = False
                continue
            cl, resto = seccion_de(t)
            if cl:
                if cl == 'responsorio' and hora == 'oficio' and vista_l2:
                    cl = 'responsorio2'
                if cl == 'lectura2':
                    vista_l2 = True
                if not (cl.startswith('responsorio') and sec
                        and sec.startswith('lectura')):
                    var = ''
                sec = cl
                if resto:
                    pon(resto)
                continue
            m = VARIANTE.match(t) if len(t) < 120 else None
            if m and not l.startswith(' '):
                var = clave(m.group(1))
                if sec in ('responsorio', 'responsorio2'):
                    sec = 'lectura1' if sec == 'responsorio' else 'lectura2'
                if m.group(2):
                    pon(m.group(2))
                continue
            m = O_BIEN.match(t) if not l.startswith(' ') else None
            mt = EN_EL_TIEMPO.match(t) if not l.startswith(' ') else None
            if m or mt:
                var = (clave(mt.group(1)) if mt else clave(m.group(1))
                       if m.group(1) else var + '+')
                if sec in ('responsorio', 'responsorio2'):
                    sec = 'lectura1' if sec == 'responsorio' else 'lectura2'
                if m and m.group(2):
                    pon(m.group(2))
                continue
        pon(l)
    return [(k, var, crudas[(k, var)]) for k, var in orden]


def salmos_por_antifona(lineas):
    """Los salmos que el libro escribe enteros, uno por antífona: sus
    títulos y sus versos, renglón a renglón, como los da la fuente. La fase
    4 busca en la fuente el mismo salmo, y sólo si no lo halla usa éste. Y
    el versículo que cierra la salmodia del Oficio."""
    tramos, act = [], None
    verso, ant_abierta = [], False
    for l in lineas:
        if l is None:
            continue
        t = l.strip()
        m = ABRE_ANT_PDF.match(t)
        if m:
            act = {'tit': [], 'l': []}
            tramos.append(act)
            ant_abierta = True
            continue
        if not t:
            ant_abierta = False
            if act and act['l'] and act['l'][-1]:
                act['l'].append([])
            continue
        if t.startswith('Ant'):            # la que se repite al final
            act, ant_abierta = None, False
            continue
        if re.match(r'^(V|R)\.\s', t):
            verso.append(runs(t))
            continue
        if act is None or DICE_SALMOS.match(t):
            continue
        if ant_abierta and not act['tit'] and not act['l']:
            continue                       # la antífona que sigue en otra línea
        if re.match(r'^(Salmo|C[áa]ntico)\b', t, re.I) \
                or re.fullmatch(r'[IV]{1,3}', t):
            act['tit'].append(re.sub(r'\s+', ' ', re.split(r'\s{2,}', t)[0]))
            resto = re.split(r'\s{2,}', t)[1:]
            if resto:
                act['l'].append([[0, ' '.join(resto)]])
            ant_abierta = False
            continue
        act['l'].append([[0, t]])
        ant_abierta = False
    for a in tramos:
        while a['l'] and not a['l'][-1]:
            a['l'].pop()
        while a['l'] and not a['l'][0]:
            a['l'].pop(0)
    return [a for a in tramos if a['l']], verso


def oficios_comunes():
    lineas = limpia(tramo_de_los_comunes(texto_de(TOMO_COMUNES)))
    bloques, act = [], None
    for l in lineas:
        t = (l or '').strip()
        if l is not None and TITULO_COMUN.match(t):
            act = {'titulo': t, 'lineas': []}
            bloques.append(act)
            continue
        if act is not None:
            act['lineas'].append(l)
    salida, avisos = {}, []
    for b in bloques:
        nombre = nombre_del_comun(b['titulo'])
        if not nombre:
            continue
        # «Del Común de pastores, excepto lo siguiente:» (el de doctores)
        cab = ' '.join((x or '').strip() for x in b['lineas'][:6])
        m = re.search(r'[Dd]el Com[uú]n de ([^,.:]+?)(?:,? o de [^,.:]+)?,? '
                      r'excepto', cab)
        piezas = defaultdict(list)
        for k, var, ls in secciones_del_comun(b['lineas']):
            if k.endswith('/oracion'):
                continue           # «Se dice la oración del día», con «san N.»
            p = pieza_de(k, ls)
            if p is False:
                avisos.append(f'{nombre}: sección {k} sin tratar')
                continue
            if p and 'ant' in p and not k.endswith('/salmodia'):
                p['ant'] = [a for a in p['ant'] if not RUBRICA_ANT.match(a)]
                if not p['ant']:
                    p = None
            # una variante sin texto (el rótulo «Para un mártir:» con la
            # lectura debajo de otro) o una remisión («Se toman los textos
            # más aptos…») no es una pieza
            texto = ' '.join(t for ln in (p or {}).get('l', [])
                             for _, t in ln).strip()
            if not p or ('l' in p and (not texto or texto.startswith(
                    ('Se toman', 'Se dice', 'Como en')))):
                continue
            if k.endswith('/salmodia'):
                p['tramos'], verso = salmos_por_antifona(ls)
                if verso:
                    p['verso'] = verso
            piezas[k].append({'v': var, 'p': p})
        salida[nombre] = {'titulo': b['titulo'], 'piezas': dict(piezas)}
        if m:
            salida[nombre]['excepto'] = nombre_del_comun(m.group(1))
    return salida, avisos


# --------------------------------------------------------------------------
# las ferias de Navidad que van por fecha
# --------------------------------------------------------------------------
# Del 2 de enero al Bautismo el propio del tiempo va por fecha
# (breviario.va_por_fecha). La fuente celebró siempre la Epifanía el 6 y el
# 2 de enero cae siempre en la memoria de san Basilio y san Gregorio, así que
# de cuatro días no publicó nunca la feria: el 2, el 6 y el 7 antes de una
# Epifanía en domingo, y el sábado después de la Epifanía (el 12). El tomo I
# los trae; se leen todos, y la fase 4 usa sólo lo que la fuente no tiene, y
# antes de usarlo lo busca en ella.

FERIA_FECHA = re.compile(r'^\s{6,}(\d{1,2}) DE ENERO\b\s*(.*?)\s*!?\s*$')
# lo que viene detrás de la última feria de cada tramo: el Bautismo («Domingo
# después del 6 de enero»), la Epifanía («DESDE LA SOLEMNIDAD DE LA
# EPIFANÍA», «6 de enero»)
FIN_FERIA = re.compile(r'^\s*(?:\d{1,2} de (?:enero|diciembre)\s*$|'
                       r'EL BAUTISMO DEL SE|LA EPIFAN|SANTA MAR[ÍI]A,? MADRE|'
                       r'Domingo despu[ée]s del 6 de enero|DESDE LA SOLEMNIDAD)')


def clave_de_feria(dia, resto):
    """«2 DE ENERO» -> «Navidad/@/2 de enero», la casilla de la fase 3. El 7
    de enero sin más es el de antes de una Epifanía en domingo 8, y no el
    «7 de enero o lunes después del domingo de Epifanía»: van aparte."""
    if int(dia) == 7 and not resto:
        return 'Navidad/@/antes de la Epifanía, 7 de enero'
    return f'Navidad/@/{int(dia)} de enero'


def por_anios(ls):
    """El Oficio de una feria con la primera lectura de los dos años: dos
    juegos de líneas, uno con la del año I y otro con la del año II."""
    t = [(l or '').strip() for l in ls]
    try:
        i1, i2 = t.index('Año I:'), t.index('Año II:')
        fin = next(n for n in range(i2, len(t)) if t[n].startswith('SEGUNDA LECTURA'))
    except (ValueError, StopIteration):
        return {'': ls}
    return {'I': ls[:i1] + ls[i1 + 1:i2] + ls[fin:],
            'II': ls[:i1] + ls[i2 + 1:fin] + ls[fin:]}


def ferias_de_navidad():
    lineas = limpia(texto_de('LH_I_ADVIENTO_NAVIDAD'))
    bloques, act = [], None
    for l in lineas:
        m = FERIA_FECHA.match(l or '')
        if m:
            act = {'k': clave_de_feria(m.group(1), m.group(2)),
                   'lineas': [f'{m.group(1)} DE ENERO']}
            bloques.append(act)
            continue
        if act is not None and l is not None and FIN_FERIA.match(l):
            act = None
            continue
        if act is not None:
            act['lineas'].append(l)
    salida = {}
    for b in bloques:
        juegos = por_anios(b['lineas'])
        piezas = {}
        for anio, ls in juegos.items():
            e = lee_entrada({'md': None, 'lineas': list(ls)})
            p, _ = secciones_de(e)
            for k, v in p.items():
                if k in ('oficio/lectura1', 'oficio/responsorio') and anio:
                    piezas.setdefault(k, {})[anio] = v
                else:
                    piezas.setdefault(k, v)
        # «Oración como en las Laudes»: es la de Laudes
        laudes = piezas.get('laudes/oracion')
        for k in list(piezas):
            if k.endswith('/oracion') and k != 'laudes/oracion':
                texto = ''.join(t for ln in piezas[k]['l'] for _, t in ln)
                if laudes and re.match(r'^\s*como en', texto, re.I):
                    piezas[k] = laudes
        # la versión más completa, si un día sale dos veces (índice y cuerpo)
        if len(piezas) > len(salida.get(b['k'], {})):
            salida[b['k']] = piezas
    return salida


# Los domingos del tiempo ordinario, de los tomos III y IV. La fuente no los
# tiene todos: es argentina, y el domingo que sigue a la Trinidad es allí
# siempre el Corpus, de modo que el IX no lo rezó nunca como domingo del
# tiempo, y en México sí lo es (el Corpus va en jueves). De cada domingo se
# toma sólo lo suyo —las lecturas del Oficio, con sus dos años; las
# antífonas del Benedictus y del Magníficat, con sus tres ciclos; la
# oración—, que lo demás es del salterio.
DOMINGO_TO = re.compile(r'^\s*DOMINGO ([IVXL]+) DEL TIEMPO ORDINARIO\s*!?\s*$')
FIN_DOMINGO = re.compile(r'^\s*(?:LUNES\b|SEMANA [IVXL]+ DEL TIEMPO ORDINARIO)')
ROMANO = {'I': 1, 'V': 5, 'X': 10, 'L': 50}


def de_romano(r):
    n = 0
    for a, b in zip(r, r[1:] + ' '):
        v = ROMANO[a]
        n += -v if b != ' ' and ROMANO[b] > v else v
    return n


def por_ciclos(p):
    """«Año A: … Año B: … Año C: … O bien: …» -> {'A': …, 'B': …, 'C': …}"""
    t = ' '.join(x for x in (p.get('ant') or []) if x != 'Antífona')
    t = re.split(r'\s*O bien:', t)[0]
    partes = re.split(r'\s*Año ([ABC]):\s*', t)
    return {partes[i]: partes[i + 1].strip()
            for i in range(1, len(partes) - 1, 2) if partes[i + 1].strip()}


def domingos_del_ordinario():
    salida = {}
    for nombre in ('LH_III_TIEMPO_ORDINARIO_I', 'LH_IV_TIEMPO_ORDINARIO_II'):
        lineas = limpia(texto_de(nombre))
        i = 0
        while i < len(lineas):
            m = DOMINGO_TO.match(lineas[i] or '')
            if not m:
                i += 1
                continue
            j = i + 1
            while j < len(lineas) and not (lineas[j] and (
                    FIN_DOMINGO.match(lineas[j]) or DOMINGO_TO.match(lineas[j]))):
                j += 1
            bloque, i = lineas[i:j], j
            if len(bloque) < 40:               # el índice del tomo
                continue
            piezas = {}
            for anio, ls in por_anios(bloque).items():
                e = lee_entrada({'md': None, 'lineas': list(ls)})
                p, _ = secciones_de(e)
                for k, v in p.items():
                    hora, cl = k.split('/')
                    if hora not in ('i_visperas', 'oficio', 'laudes', 'visperas'):
                        continue
                    if cl == 'cantico_evangelico':
                        ciclos = por_ciclos(v)
                        if ciclos:
                            piezas.setdefault(k, {'ciclos': ciclos})
                    elif cl in ('lectura1', 'responsorio') and anio:
                        piezas.setdefault(k, {})[anio] = v
                    elif cl in ('lectura2', 'responsorio2', 'oracion'):
                        piezas.setdefault(k, v)
            k = f'Ordinario/{de_romano(m.group(1))}/0'
            if len(piezas) > len(salida.get(k, {})):
                salida[k] = piezas
    return salida


def main():
    entradas, avisos, dudosos = [], [], []
    for tomo, nombre in TOMOS:
        lineas = limpia(tramo_del_santoral(texto_de(nombre)))
        dudosos += [(tomo, n, t) for n, t in cortes_dudosos(lineas)]
        for e in trocea(lineas):
            e['tomo'] = tomo
            lee_entrada(e)
            e['piezas'], av = secciones_de(e)
            avisos += av
            del e['secciones_crudas']
            entradas.append(e)

    # Un santo cuyo propio cae entre dos tomos (enero, febrero, mayo…) sale
    # en los dos: se queda la entrada más completa.
    por_clave = {}
    for e in entradas:
        k = (e['md'], clave(e['titulo']))
        prev = por_clave.get(k)
        if prev is None or len(e['piezas']) > len(prev['piezas']):
            por_clave[k] = e
    # las movibles van al final, que no tienen fecha por la que ordenarlas
    finales = sorted(por_clave.values(),
                     key=lambda e: (e['md'] or '99-99', e['titulo'] or ''))

    os.makedirs(LIBRO, exist_ok=True)
    with open(os.path.join(LIBRO, 'pdf_santoral.json'), 'w',
              encoding='utf-8') as f:
        json.dump(finales, f, ensure_ascii=False, indent=0)

    ferias = ferias_de_navidad()
    domingos = domingos_del_ordinario()
    with open(os.path.join(LIBRO, 'pdf_tiempo.json'), 'w',
              encoding='utf-8') as f:
        json.dump(dict(ferias, **domingos), f, ensure_ascii=False, indent=0)
    print(f'{len(ferias)} ferias de Navidad por fecha: '
          + ', '.join(k.split('/')[-1] for k in ferias))
    print(f'{len(domingos)} domingos del tiempo ordinario')

    comunes, av_comunes = oficios_comunes()
    avisos += av_comunes
    with open(os.path.join(LIBRO, 'pdf_comunes.json'), 'w',
              encoding='utf-8') as f:
        json.dump(comunes, f, ensure_ascii=False, indent=0)
    print(f'{len(comunes)} oficios comunes: '
          + ', '.join(f'{n} ({len(c["piezas"])})' for n, c in comunes.items()))

    cuenta = Counter()
    for e in finales:
        for k in e['piezas']:
            cuenta[k] += 1
    with open(QA, 'w', encoding='utf-8') as f:
        f.write('Fase 3b — el Propio de los santos de los PDF\n')
        f.write('=' * 50 + '\n\n')
        f.write(f'Entradas leídas: {len(entradas)}; distintas: '
                f'{len(finales)}\n\n')
        f.write('Secciones halladas\n' + '-' * 30 + '\n')
        for k, v in sorted(cuenta.items()):
            f.write(f'{v:6d}  {k}\n')
        sin = [e for e in finales if not e['piezas']]
        f.write(f'\nEntradas sin ninguna sección: {len(sin)}\n')
        for e in sin:
            f.write(f'  {e["md"]}  {e["titulo"]}  [{e["tomo"]}]\n')
        f.write(f'\nRótulos de día que no abren entrada (lo de debajo se '
                f'pega al santo anterior): {len(dudosos)}\n')
        for tomo, n, t in dudosos:
            f.write(f'  tomo {tomo}, línea {n}: «{t}»\n')
        f.write(f'\nAvisos: {len(avisos)}\n')
        for a in avisos:
            f.write('  ' + a + '\n')
        f.write('\nEntradas\n' + '-' * 30 + '\n')
        for e in finales:
            f.write(f'{e["md"] or "movible"}  {e["titulo"]}  '
                    f'({e["grado"] or "—"}; '
                    f'tomo {e["tomo"]})\n      común: {e["comun"]}\n'
                    f'      {", ".join(sorted(e["piezas"]))}\n')
    print(f'{len(finales)} entradas; QA en {QA}')


if __name__ == '__main__':
    main()
