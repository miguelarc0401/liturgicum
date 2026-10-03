# -*- coding: utf-8 -*-
"""Fase 3: los cien misalitos → `datos/misalitos/AAAA-MM.json`.

Un misalito publica **días ya armados**. Esta fase no los desarma todavía
—eso es la fase 4—: los **parte**, y guarda cada formulario con sus bloques
rotulados, su página y su línea, en bruto.

Lo único que hay que acertar aquí es dónde empieza cada formulario, y eso no
se adivina: se mide. Hay dos anclas y ninguna de las dos basta sola.

**El pie de página** nombra el día entero —«jueves 1 de enero de 2026»— en los
cien ficheros. Pero una página puede llevar el final de un formulario y el
principio del siguiente, y entonces el pie nombra sólo uno de los dos; y la
fuente escribe mal siete de esos pies: cinco con el día de la semana
estropeado (`miécoles`, `viérnes`, `marte`, `sábados`, `sàbado`) y dos de
julio de 2023 con el **número** del día equivocado.

**La cabecera del formulario** —«1° jueves», «30 sábado»— es la buena: su día
de la semana cuadra con el calendario en las 3 031 veces que aparece, sin una
sola excepción. De ahí que el formulario se parta por la cabecera y el pie
quede para cotejar. Dos cosas hay que tolerarle:

 - `pdftotext -layout` le pega en la misma línea las cajas que en el papel van
   a su lado: «Se gana indulgencia plenaria rezando el Rosario    1° lunes»,
   «20 viernes     FERIA MAYOR DE ADVIENTO,». Así que la cabecera es una caja
   de la línea, no la línea;
 - un día de los 3 044 no la lleva (el 24 de agosto de 2025, que empieza
   directamente por su título). Ahí se cae a la línea del `MR p.`, y el
   informe lo dice.

Y hay dos publicaciones, no tres familias de maqueta: **La Santa Misa** de
Guadalajara (97 ficheros) y **Palabra Viva** de Yucatán (enero, febrero y
diciembre de 2021), que titula «2 de Enero / SÁBADO» y junta grado y color en
una línea («Memoria - Blanco»).
"""

import calendar
import datetime as dt
import difflib
import json
import os
import re
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misal

SALIDA = os.path.join(misal.DATOS, 'misalitos')

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
NMES = {m: i + 1 for i, m in enumerate(MESES)}
SEMANA = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado',
          'domingo']


def sinac(s):
    """El texto sin tildes y en minúscula, para comparar."""
    s = unicodedata.normalize('NFKD', s.lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


# --------------------------------------------------------------------------
# las páginas y lo marginal
# --------------------------------------------------------------------------

# El pie: el día entero, con el número de página delante o detrás, y en
# algunos ficheros de 2020 con la dirección del arzobispado al lado. El día de
# la semana se lee aparte y se cuadra con el calendario, porque la fuente lo
# estropea en cinco ficheros; por eso aquí es `\w+` y no la lista cerrada.
PIE = re.compile(
    r'([A-Za-zÁ-ÿ]{4,12})\s+(\d{1,2})\s*(?:°|º|\.)?\s*de\s+'
    r'(' + '|'.join(MESES) + r')'
    r'(?:\s+de\s+(\d{4}))?', re.I)

# Lo que acompaña al pie y no es el pie: la foliación y la dirección del sitio.
FURNITURA = re.compile(r'^\s*(?:\d{1,3}\s*)?(?:https?://\S+\s*)?|'
                       r'\s*(?:https?://\S+\s*)?(?:\d{1,3}\s*)?$')


def paginas(lineas):
    """El volcado partido por el salto de página de `pdftotext`.

    Devuelve una lista de `(primera_linea, [lineas])`, para que cada bloque
    sepa después en qué página del impreso cae.
    """
    pags, cur, ini = [], [], 0
    for i, ln in enumerate(lineas):
        if '\f' not in ln:
            cur.append(ln)
            continue
        trozos = ln.split('\f')
        cur.append(trozos[0])
        pags.append((ini, cur))
        for t in trozos[1:-1]:
            pags.append((i, [t]))
        cur, ini = [trozos[-1]], i
    pags.append((ini, cur))
    return pags


def pie_de(pag, mes, anio):
    """El día y la página impresa que el pie de esta página nombra.

    Devuelve `(dia, semana_impresa, pagina_impresa, linea)` o `None`. Mira
    sólo las dos primeras y las tres últimas líneas con texto, que es donde
    el pie cae: así una fecha del cuerpo («erigida el 4 de noviembre de
    1978») no se confunde con un pie. La línea se devuelve para borrarla: el
    pie no es texto del libro, y si se queda dentro aparece en mitad de una
    reseña o de una lectura.
    """
    idx = [k for k, l in enumerate(pag) if l.strip()]
    for k in idx[:2] + idx[-3:]:
        ln = pag[k]
        m = PIE.search(ln)
        if not m:
            continue
        # lo que rodea al pie ha de ser sólo foliación o la dirección del sitio
        resto = (ln[:m.start()] + ' ' + ln[m.end():]).strip()
        resto = re.sub(r'https?://\S+', '', resto)
        resto = re.sub(r'\d{1,3}', '', resto, count=2).strip()
        if resto:
            continue
        if sinac(m.group(3)) != MESES[mes - 1]:
            continue
        if m.group(4) and int(m.group(4)) != anio:
            continue
        nums = [int(x) for x in re.findall(r'\b(\d{1,3})\b',
                                           ln[:m.start()] + ln[m.end():])]
        return (int(m.group(2)), sinac(m.group(1)),
                (nums[0] if nums else None), k)
    return None


def semana_cercana(semana, dia, mes, anio, tope):
    """El día del mes que cae en ese día de la semana y está más cerca de
    `dia`. Es lo que repara los dos pies de julio de 2023, que traen el día de
    la semana bueno y el número de al lado."""
    if semana not in SEMANA:
        return None
    quiere = SEMANA.index(semana)
    cand = [d for d in range(1, tope + 1)
            if dt.date(anio, mes, d).weekday() == quiere]
    return min(cand, key=lambda d: abs(d - dia)) if cand else None


# --------------------------------------------------------------------------
# la cabecera del formulario
# --------------------------------------------------------------------------

# «1° jueves», «30 sábado»: una caja de la línea, no la línea entera.
CAB_SM = re.compile(r'(?:^\s*|\s{3,})(\d{1,2})\s*[°ºo]?\s+'
                    r'(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|'
                    r'domingo)(?=\s{3,}|\s*$)', re.I)
# Palabra Viva: «2 de Enero», y el día de la semana —si lo pone— debajo.
CAB_PV = re.compile(r'^\s*(\d{1,2})\s+de\s+([A-Za-zÁ-ÿ]+)\s*$')

# La referencia doble al Misal impreso, que toda celebración lleva.
MR = re.compile(r'\bMR\.?\s*p{1,2}\.?\s*\d')
MR_PARTES = re.compile(
    r'MR\.?\s*p{1,2}\.?\s*([\d\s,.\-]+?)\s*'
    r'(?:[\[(]\s*([\d\s,.\-]+?)\s*[\])])?\s*'
    r'(?:/\s*Lecc\.?\s*([^/]*?))?'
    r'(?:\.?\s*(LH\b.*))?$')

COLOR = re.compile(r'^(Blanco|Verde|Rojo|Morado|Rosa|Negro|Azul)'
                   r'(\s*[/yo]\s*(Blanco|Verde|Rojo|Morado|Rosa|Negro|Azul))*'
                   r'\.?$', re.I)
# El vocabulario del grado, medido sobre las 13 024 cajas distintas que las
# cabeceras traen: «Memoria,», «Feria de Pascua», «Feria mayor de Adviento,»,
# «Octava de Pascua», «Sólo Conmemoración.», y en Palabra Viva «Feria -
# Morado». Va en mayúsculas o en redonda según la página, así que no se mira
# la caja de la letra.
GRADO = re.compile(r'^(?:S[oó]lo\s+)?'
                   r'(Solemnidad|Fiesta|Memorias?(\s+libres?)?|'
                   r'Feria(\s+(mayor|de|despu[eé]s|privilegiada)\b.*)?|'
                   r'Conmemoraci[oó]n|Octava\b.*|Vigilia\b.*)'
                   r'(\s+o)?[,.]?$', re.I)
# Palabra Viva: «Memoria - Blanco», «Solemnidad - Blanco»
GRADO_COLOR = re.compile(r'^(.{4,30}?)\s*[-–]\s*'
                         r'((?:Blanco|Verde|Rojo|Morado|Rosa|Negro|Azul)'
                         r'(?:\s*[/yo]\s*'
                         r'(?:Blanco|Verde|Rojo|Morado|Rosa|Negro|Azul))*)'
                         r'\.?$', re.I)


# El título va en versales; su continuación empieza por conjunción o
# preposición en redonda («SANTOS BASILIO MAGNO / y GREGORIO NACIANZENO,»).
_ENLACE = re.compile(r'^(y|e|o|u|de|del|la|las|el|los|en|con)\s+(.*)$')


def es_titulo(caja):
    c = caja.strip(' ,.;:[]()')
    return bool(c) and c == c.upper() and any(x.isalpha() for x in c)


def continua_titulo(caja):
    m = _ENLACE.match(caja.strip())
    return bool(m) and es_titulo(m.group(2))


def cajas(linea):
    """Las cajas de una línea que `-layout` dejó pegadas, de tres en tres
    espacios arriba. Sin esto, «20 viernes     FERIA MAYOR DE ADVIENTO,» es
    una línea sin sentido en vez de dos rótulos."""
    return [c.strip() for c in re.split(r'\s{3,}', linea.strip()) if c.strip()]


# --------------------------------------------------------------------------
# los rótulos
# --------------------------------------------------------------------------

PIEZAS = ['ANTÍFONA DE ENTRADA', 'ORACIÓN COLECTA', 'PRIMERA LECTURA',
          'SALMO RESPONSORIAL', 'SEGUNDA LECTURA', 'SECUENCIA',
          'ACLAMACIÓN ANTES DEL EVANGELIO', 'EVANGELIO',
          'ORACIÓN SOBRE LAS OFRENDAS', 'ANTÍFONA DE LA COMUNIÓN',
          'ORACIÓN DESPUÉS DE LA COMUNIÓN', 'ORACIÓN SOBRE EL PUEBLO']

EDITORIAL = ['MONICIONES', 'MONICIÓN DE ENTRADA', 'MONICIÓN',
             'REFLEXIÓN', 'ORACIÓN DE LOS FIELES', 'ORACIÓN UNIVERSAL',
             'ORACIONES DE LOS FIELES', 'NOTA PASTORAL',
             'ACTIVIDAD DIOCESANA', 'ACTIVIDADES DIOCESANAS',
             'FIESTA PATRONAL', 'NUESTRA PORTADA', 'COMENTARIO']

# Las que la fuente escribe mal y hay que reconocer igual. Primero se busca
# el rótulo **entero** al principio de la caja —del más largo al más corto,
# para que «ACLAMACIÓN ANTES DEL EVANGELIO» gane a «EVANGELIO»—, y sólo lo
# que no cuadre así se busca por parecido, con el umbral alto. Cada
# reparación por parecido se nombra en el informe.
_LARGOS = sorted(PIEZAS + EDITORIAL, key=len, reverse=True)
_LLAVE = {sinac(r): r for r in PIEZAS + EDITORIAL}

# El rótulo son las mayúsculas del principio de la caja.
ROTULO = re.compile(r'^([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ\'ª ]{3,44})(?=[^A-ZÁÉÍÓÚÑÜ]|$)')


def rotulo_de(caja):
    """`(rótulo canónico, lo que la fuente escribió, el resto de la caja)`.

    Si la caja no empieza por un rótulo reconocible, `(None, None, None)`.
    """
    k = sinac(caja)
    for canon in _LARGOS:
        kc = sinac(canon)
        if not k.startswith(kc):
            continue
        # el rótulo va en versales, siempre, y eso hay que exigirlo: sin
        # ello, el «Evangelio, para que los oídos de los sordos se abran» de
        # una colecta pasa por rótulo de evangelio, y son 150 piezas falsas.
        cabo = caja[:len(canon)]
        if cabo != cabo.upper():
            continue
        # el rótulo ha de acabar ahí: si sigue otra mayúscula, es otro rótulo
        # más largo («EVANGELIOS»); si sigue minúscula, la fuente le pegó su
        # texto («SALMO RESPONSORIALdel salmo 66») y eso sí se admite.
        if len(caja) > len(canon) and caja[len(canon)].isupper():
            continue
        return canon, cabo, caja[len(canon):].strip()

    m = ROTULO.match(caja)
    if not m:
        return None, None, None
    crudo = m.group(1).strip()
    resto = caja[m.end():].strip()
    k = sinac(crudo)
    # la fuente escribe «ORACIÓN COLETA», «SALMO RESPONSORIA», «PUELO»…
    # Se prueba con las palabras del principio, de más a menos, porque a
    # veces -layout le pega la inicial de la cita.
    palabras = crudo.split()
    mejor = None
    for n in range(len(palabras), 0, -1):
        trozo = ' '.join(palabras[:n])
        for llave, canon in _LLAVE.items():
            r = difflib.SequenceMatcher(None, sinac(trozo), llave).ratio()
            if r >= 0.9 and (mejor is None or r > mejor[0]):
                mejor = (r, n, canon, trozo)
    if mejor is not None:
        _, n, canon, trozo = mejor
        sobra = ' '.join(palabras[n:])
        return canon, trozo, (sobra + ' ' + resto).strip()
    return None, None, None


# Las rúbricas que el propio Misal imprime, y que no son rótulo de pieza.
RUBRICAS = [
    ('@gloria', re.compile(r'^(No\s+)?[Ss]e\s+dice\s+(el\s+)?Gloria', re.I)),
    ('@credo', re.compile(r'^(No\s+)?[Ss]e\s+dice\s+(el\s+)?Credo', re.I)),
    ('@prefacio', re.compile(r'^Prefacio\b', re.I)),
    ('@plegaria', re.compile(r'^(Si\s+se\s+utiliza\s+el\s+Canon|'
                             r'En\s+las\s+otras\s+Plegarias|'
                             r'Plegaria\s+[Ee]ucar[ií]stica)', re.I)),
    ('@bendicion', re.compile(r'^(Puede\s+(utilizarse|darse)|'
                              r'Se\s+puede\s+dar)\b.*'
                              r'(bendici[oó]n|oraci[oó]n\s+sobre\s+el\s+pueblo)',
                              re.I)),
    ('@lecturas', re.compile(r'^Las\s+lecturas\b', re.I)),
    ('@obien', re.compile(r'^O\s+bien\s*:?\s*$', re.I)),
    ('@secuencia', re.compile(r'^(La\s+)?[Ss]ecuencia\b.*(opcional|obligat)',
                              re.I)),
]


def limpia_cita(resto):
    """La cita del rótulo, o nada. La fuente deja a veces sólo el punto que
    cerraba el renglón de arriba, y eso no es una cita."""
    c = (resto or '').strip(' .,:;—-')
    return c or None


def rubrica_de(caja):
    for nombre, pat in RUBRICAS:
        if pat.match(caja):
            return nombre
    return None


# El santoral mexicano. El misalito de Guadalajara añade, al pie del día, la
# reseña de un mártir o beato de México marcándolo con un asterisco: «* SAN
# SABÁS REYES SALAZAR» y su semblanza. No es un formulario —casi nunca trae
# oración propia—, pero es la reseña histórica que la app ha de dar, así que
# se guarda como bloque aparte en vez de quedar pegada a la última oración.
SANTORAL_MX = re.compile(r"^\*\s*([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ .,ª'-]{5,})$")


# Un día puede llevar más de una misa, y entonces el libro no repite la
# cabecera: la segunda se abre con su rótulo en versales y centrado. Son las
# tres misas de los Fieles Difuntos, las tres de Navidad y las vespertinas de
# las vigilias, que es justo lo que la app ha de dejar elegir.
SUBMISA = re.compile(
    r'^(?:(PRIMERA|SEGUNDA|TERCERA|CUARTA)\s+MISA'
    r'|MISA\s+(?:VESPERTINA|DE\s+LA\s+VIGILIA|DE\s+LA\s+AURORA'
    r'|DE\s+LA\s+NOCHE|DE\s+NOCHE\s+BUENA|DE\s+MEDIANOCHE'
    r'|DEL\s+D[IÍ]A))\b[^a-záéíóúñ]*$')


# --------------------------------------------------------------------------
# un fichero
# --------------------------------------------------------------------------

class Misalito:
    def __init__(self, pdf):
        self.pdf = pdf
        self.nombre = os.path.splitext(os.path.basename(pdf))[0]
        m = re.match(r'misal([A-Za-z]+)(\d{4})$', self.nombre)
        self.mes = NMES[sinac(m.group(1))]
        self.anio = int(m.group(2))
        self.tope = calendar.monthrange(self.anio, self.mes)[1]
        self.lineas = misal.texto_de(pdf, self.nombre)
        self.avisos = []
        self.recortes = 0
        self.columnas = 0
        cabeza = ' '.join(l for l in self.lineas[:80]).upper()
        self.familia = ('palabraviva' if 'PALABRA VIVA' in cabeza
                        else 'santamisa')

    # --- el mapa de páginas ------------------------------------------------
    def mapa(self):
        """Por cada línea, la página impresa y el día que su pie nombra."""
        self.pags = paginas(self.lineas)
        self.pag_de = {}
        self.dia_de = {}
        prev = 1
        for ini, pag in self.pags:
            fin = ini + len(pag)
            p = pie_de(pag, self.mes, self.anio)
            if p is None:
                continue
            dia, semana, impresa, k = p
            # el pie no es texto del libro: se quita. Se quita el trozo, no
            # la línea entera, porque la línea del salto de página lleva a la
            # vez el final de una página y el principio de la siguiente.
            if pag[k].strip():
                self.lineas[ini + k] = self.lineas[ini + k].replace(
                    pag[k], ' ' * len(pag[k]), 1)
            real = SEMANA[dt.date(self.anio, self.mes,
                                  min(dia, self.tope)).weekday()] \
                if 1 <= dia <= self.tope else None
            if real is not None and semana != real:
                # El pie se contradice: el número dice un día y la palabra
                # otro. Ninguno de los dos es de fiar por sí solo —la fuente
                # estropea unas veces la palabra («miécoles», «sábados») y
                # otras el número (julio de 2023, dos veces)—, así que lo
                # decide **la secuencia**: las páginas van en orden, y el día
                # no retrocede. Tras el 29 viene el 30, no el 28.
                otro = semana_cercana(semana, dia, self.mes, self.anio,
                                      self.tope)
                parecido = difflib.get_close_matches(semana, SEMANA, n=1,
                                                     cutoff=0.78)
                errata = parecido and parecido[0] == real
                cand = [d for d in (dia, otro)
                        if d is not None and d >= prev]
                # si la palabra es un día de la semana de verdad y no el de
                # la página anterior, la página empieza otro día
                if (not errata and semana in SEMANA
                        and SEMANA[dt.date(self.anio, self.mes,
                                           prev).weekday()] != semana):
                    cand = [d for d in cand if d != prev]
                if errata or not cand or min(cand) == dia:
                    self.avisos.append(
                        'pie de la p. %s: «%s %d de %s» — la fuente escribe '
                        'mal el día de la semana (es «%s»); el número '
                        'continúa la serie y se respeta'
                        % (impresa, semana, dia, MESES[self.mes - 1], real))
                    if not 1 <= dia <= self.tope:
                        continue
                else:
                    nuevo = min(cand)
                    self.avisos.append(
                        'pie de la p. %s: «%s %d de %s» — el %d de %s no es '
                        '%s sino %s, y la página anterior era el %d: manda '
                        'el día de la semana y la página se cuenta como el %d'
                        % (impresa, semana, dia, MESES[self.mes - 1], dia,
                           MESES[self.mes - 1], semana, real, prev, nuevo))
                    dia = nuevo
            if not 1 <= dia <= self.tope:
                continue
            for i in range(ini, fin):
                self.dia_de[i] = dia
                if impresa:
                    self.pag_de[i] = impresa
            prev = dia
        # las líneas sin pie heredan la página de la anterior
        ultima = None
        for i in range(len(self.lineas)):
            if i in self.pag_de:
                ultima = self.pag_de[i]
            elif ultima is not None:
                self.pag_de[i] = ultima

    # --- las cabeceras -----------------------------------------------------
    def cabeceras(self):
        """`[(linea, dia, semana, fuente)]`, en el orden del libro."""
        fuera = []
        if self.familia == 'santamisa':
            for i, ln in enumerate(self.lineas):
                for m in CAB_SM.finditer(ln):
                    dia, semana = int(m.group(1)), sinac(m.group(2))
                    if not 1 <= dia <= self.tope:
                        continue
                    if SEMANA[dt.date(self.anio, self.mes,
                                      dia).weekday()] != semana:
                        continue
                    fuera.append((i, dia, semana, 'cabecera'))
        else:
            for i, ln in enumerate(self.lineas):
                m = CAB_PV.match(ln)
                if not m or sinac(m.group(2)) not in NMES:
                    continue
                if NMES[sinac(m.group(2))] != self.mes:
                    continue
                dia = int(m.group(1))
                if not 1 <= dia <= self.tope:
                    continue
                # la referencia al Misal confirma que es una cabecera y no
                # una fecha del cuerpo
                if not any(MR.search(x) for x in self.lineas[i + 1:i + 12]):
                    continue
                semana = SEMANA[dt.date(self.anio, self.mes, dia).weekday()]
                fuera.append((i, dia, semana, 'cabecera'))
        # los días que no la llevan: se cae a la línea del «MR p.»
        vistos = {d for _, d, _, _ in fuera}
        faltan = [d for d in range(1, self.tope + 1) if d not in vistos]
        for dia in faltan:
            lins = sorted(i for i, d in self.dia_de.items() if d == dia)
            cand = next((i for i in lins if MR.search(self.lineas[i])), None)
            if cand is None:
                self.avisos.append(
                    'el día %d no tiene cabecera ni línea «MR p.»: no se '
                    'extrae' % dia)
                continue
            semana = SEMANA[dt.date(self.anio, self.mes, dia).weekday()]
            fuera.append((cand, dia, semana, 'mr'))
            self.avisos.append(
                'el día %d (%s) no lleva cabecera «%d %s»; el formulario se '
                'abre en su línea «MR p.», que la fuente sí imprime'
                % (dia, semana, dia, semana))
        fuera.sort()
        return fuera

    # --- un formulario -----------------------------------------------------
    def formulario(self, ini, fin, dia, semana, fuente, misa=None):
        cab = {'dia': dia, 'semana': semana, 'fuente': fuente,
               'color': None, 'grado': None, 'titulo': None,
               'subtitulo': None, 'resena': None, 'alterna': None,
               'mr': None, 'mr_paginas': None, 'lecc': None, 'lh': None,
               'crudo': []}
        bloques = []

        # 1) la cabecera: de su línea al primer rótulo, de pieza o editorial
        j = ini
        resto_cab = []
        while j < fin:
            cjs = cajas(self.lineas[j])
            if any(rotulo_de(c)[0] or rubrica_de(c) for c in cjs):
                break
            for c in cjs:
                if CAB_SM.search(self.lineas[j]) and re.match(
                        r'^\d{1,2}\s*[°ºo]?\s+\w+$', c):
                    continue
                if CAB_PV.match(c):
                    continue
                if re.match(r'^[A-ZÁÉÍÓÚÑÜ]{2,}$', c) and len(c) <= 9 \
                        and sinac(c) in SEMANA:
                    continue                      # el «SÁBADO» de Palabra Viva
                cab['crudo'].append(c)
                if MR.search(c):
                    cab['mr'] = c
                    mp = MR_PARTES.search(c)
                    if mp:
                        pgs = [int(x) for x in
                               re.findall(r'\d+', mp.group(1) or '')]
                        if mp.group(2):
                            pgs += [int(x) for x in
                                    re.findall(r'\d+', mp.group(2))]
                        cab['mr_paginas'] = pgs or None
                        cab['lecc'] = (mp.group(3) or '').strip(' .,') or None
                        cab['lh'] = (mp.group(4) or '').strip(' .') or None
                elif COLOR.match(c):
                    cab['color'] = c.rstrip('.')
                elif GRADO.match(c):
                    g = c.rstrip(',. ')
                    # «Feria o» abre una alternativa: la misa votiva que ese
                    # día se permite, y que viene en la caja siguiente
                    if re.search(r'\so$', g, re.I):
                        cab['grado'] = g[:-2].rstrip()
                        cab['_espera_alterna'] = True
                    else:
                        cab['grado'] = g
                elif GRADO_COLOR.match(c):
                    g = GRADO_COLOR.match(c)
                    cab['grado'], cab['color'] = g.group(1), g.group(2)
                elif cab.pop('_espera_alterna', False):
                    cab['alterna'] = c.rstrip('.')
                elif SUBMISA.match(c):
                    misa = misa or re.sub(r'\s+', ' ', c).strip(' .,')
                else:
                    resto_cab.append(c)
            j += 1
        cab.pop('_espera_alterna', None)

        # El título, el subtítulo y la reseña se reparten **sin mover de
        # sitio**: el orden de la página es el del libro, y concatenar
        # primero las mayúsculas y luego lo demás destroza una reseña de tres
        # renglones («…llevó una vida monástica y redactó / las reglas que
        # todavía observan los monjes / de Oriente»).
        #
        # El título va en versales, y su continuación empieza por una
        # conjunción en redonda: «SANTOS BASILIO MAGNO / y GREGORIO
        # NACIANZENO,». Lo que viene después en redonda es el subtítulo si es
        # un renglón corto sin punto —«Obispos y Doctores de la Iglesia»— y
        # la reseña si son frases.
        tit, resto = [], []
        for c in resto_cab:
            if (not resto and es_titulo(c)) or (tit and not resto
                                                and continua_titulo(c)):
                tit.append(c)
            else:
                resto.append(c)
        cab['titulo'] = ' '.join(tit).strip(' ,') or None
        sub = []
        while resto and len(resto[0]) < 50 and not resto[0].endswith('.'):
            sub.append(resto.pop(0))
        cab['subtitulo'] = ' '.join(sub) or None
        cab['resena'] = ' '.join(resto) or None

        # 2) los bloques, hasta que el formulario se cierre
        #
        # Lo que dice dónde acaba no es la maqueta: es el orden del Misal. La
        # oración después de la comunión es la última pieza propia, y tras
        # ella sólo caben la oración sobre el pueblo y las rúbricas. Si
        # aparece otra cosa, el formulario ya acabó: o empieza otra misa del
        # mismo día —«SEGUNDA MISA»— o lo que sigue es el aparato editorial
        # del día siguiente, que el misalito imprime antes de su cabecera.
        actual = None
        cerrado = False
        sigue = None
        parar = False
        abierto, rubrica_en = None, -9
        for i in range(j, fin):
            if parar:
                break
            cjs = cajas(self.lineas[i])
            for ci, c in enumerate(cjs):
                canon, crudo, resto = rotulo_de(c)
                rub = rubrica_de(c)
                if cerrado and canon and canon != 'ORACIÓN SOBRE EL PUEBLO':
                    parar = True
                    if canon in ('ANTÍFONA DE ENTRADA', 'ORACIÓN COLECTA'):
                        sigue = i            # otra misa del mismo día
                    break
                if SUBMISA.match(c) and actual is not None:
                    parar, sigue = True, i
                    break
                ms = SANTORAL_MX.match(c)
                if ms:
                    actual = {'clase': 'santoral', 'rotulo': ms.group(1),
                              'cita': None, 'sumario': None, 'texto': [],
                              '_lin': [], '_col': [],
                              'p': self.pag_de.get(i), 'l': i}
                    bloques.append(actual)
                    continue
                # Dentro de las moniciones, el editor rotula cada párrafo con
                # el nombre de la pieza que comenta y le pone dos puntos:
                # «EVANGELIO: [Mc 2, 23—3, 6] En franca polémica…». No es el
                # evangelio: es el comentario, y se queda dentro de su bloque.
                if (canon and resto.startswith(':') and actual is not None
                        and actual['clase'] == 'editorial'):
                    actual['texto'].append(c)
                    actual['_lin'].append(i)
                    actual['_col'].append((ci, len(cjs)))
                    continue
                if canon:
                    actual = {'clase': ('editorial' if canon in EDITORIAL
                                        else 'pieza'),
                              'rotulo': canon,
                              'cita': limpia_cita(resto),
                              'sumario': None, 'texto': [], '_lin': [], '_col': [],
                              'p': self.pag_de.get(i), 'l': i}
                    if crudo != canon:
                        actual['crudo'] = crudo
                        self.avisos.append(
                            'p. %s: la fuente rotula «%s»; se lee «%s»'
                            % (self.pag_de.get(i), crudo, canon))
                    bloques.append(actual)
                    abierto = i
                    if canon == 'ORACIÓN DESPUÉS DE LA COMUNIÓN':
                        cerrado = True
                elif rub:
                    actual = {'clase': 'rubrica', 'rotulo': rub,
                              'cita': None, 'sumario': None,
                              'texto': [c], '_lin': [i],
                              '_col': [(ci, len(cjs))],
                              'p': self.pag_de.get(i), 'l': i}
                    bloques.append(actual)
                    # la rúbrica sigue en el renglón de abajo si no hay línea
                    # en blanco en medio («Si se utiliza el Canon romano, se
                    # dice Reunidos en comunión... / propio, p. 557 [559]»),
                    # y acaba donde la fuente la corta
                    rubrica_en = i
                elif actual is not None and actual['clase'] == 'rubrica':
                    if i == rubrica_en + 1:
                        actual['texto'].append(c)
                        actual['_lin'].append(i)
                        actual['_col'].append((ci, len(cjs)))
                        rubrica_en = i
                    else:
                        actual = None
                elif actual is not None:
                    # Si la caja va en el mismo renglón del rótulo, es su
                    # cita: la fuente la alinea a la derecha —«ANTÍFONA DE
                    # ENTRADA        Cfr. Sir 44, 15. 14»— y `-layout` la
                    # deja como caja aparte, no como resto del rótulo.
                    if (abierto == i and actual['cita'] is None
                            and not actual['texto']
                            and actual['clase'] != 'editorial'):
                        actual['cita'] = limpia_cita(c)
                    elif (actual['sumario'] is None and not actual['texto']
                          and c.startswith('[') and c.endswith(']')):
                        actual['sumario'] = c[1:-1]
                    else:
                        actual['texto'].append(c)
                        actual['_lin'].append(i)
                        actual['_col'].append((ci, len(cjs)))

        # las colas editoriales que quedaran sueltas al final no son de este
        # día: son del siguiente, que el libro imprime antes de su cabecera
        while bloques and bloques[-1]['clase'] == 'editorial':
            bloques.pop()

        # Y por la misma razón se recorta la cola de cada bloque. El pie
        # nombra el día que **empieza** en esa página, así que la página en
        # que acaba un formulario puede llevar ya el pie del día siguiente
        # —y ahí sigue habiendo texto de este—: por eso se conserva la
        # página del propio rótulo y se tira lo que caiga en páginas
        # posteriores ya rotuladas con otro día, que es donde el misalito
        # imprime la reseña y las moniciones del día que viene.
        for b in bloques:
            pb = self.pag_de.get(b['l'])
            while b['texto']:
                k = b['_lin'][-1]
                if (self.dia_de.get(k, dia) > dia
                        and self.pag_de.get(k) != pb):
                    b['texto'].pop()
                    b['_lin'].pop()
                    b['_col'].pop()
                    self.recortes += 1
                else:
                    break
            # La secuencia —el Stabat Mater, el Victimæ paschali— va en dos
            # columnas, y `-layout` las entrelaza renglón a renglón: «La
            # Madre piadosa estaba / Y, porque a amarlo me anime, / junto a
            # la cruz, y lloraba». Las cajas ya vienen separadas, así que la
            # columna se deshace poniendo primero una y luego la otra.
            dobles = sum(1 for _, n in b['_col'] if n == 2)
            if len(b['_col']) >= 6 and dobles >= 0.6 * len(b['_col']):
                izq = [t for t, (ci, n) in zip(b['texto'], b['_col'])
                       if n < 2 or ci == 0]
                der = [t for t, (ci, n) in zip(b['texto'], b['_col'])
                       if n == 2 and ci == 1]
                b['texto'] = izq + der
                b['columnas'] = 2
                self.columnas += 1
            del b['_lin'], b['_col']
        return ({'fecha': '%04d-%02d-%02d' % (self.anio, self.mes, dia),
                 'p': self.pag_de.get(ini), 'l': ini, 'misa': misa,
                 'cabecera': cab, 'bloques': bloques}, sigue)

    # --- todo --------------------------------------------------------------
    def extrae(self):
        self.mapa()
        cabs = self.cabeceras()
        forms = []
        for n, (i, dia, semana, fuente) in enumerate(cabs):
            tope = cabs[n + 1][0] if n + 1 < len(cabs) else len(self.lineas)
            ini, misa = i, None
            while ini is not None and ini < tope:
                f, sigue = self.formulario(ini, tope, dia, semana, fuente,
                                           misa)
                forms.append(f)
                if sigue is None or sigue <= ini:
                    break
                # la misa siguiente del mismo día lleva su rótulo
                misa = next((re.sub(r'\s+', ' ', c).strip(' .,')
                             for k in range(sigue, min(sigue + 4, tope))
                             for c in cajas(self.lineas[k])
                             if SUBMISA.match(c)), None)
                ini, fuente = sigue, 'submisa'
        for f in forms:
            f['orden'] = sum(1 for g in forms[:forms.index(f)]
                             if g['fecha'] == f['fecha'])
        return {'fichero': self.nombre, 'anio': self.anio, 'mes': self.mes,
                'familia': self.familia, 'paginas': len(self.pags),
                'recortes': self.recortes, 'columnas': self.columnas,
                'formularios': forms, 'avisos': self.avisos}


# --------------------------------------------------------------------------
def main():
    inf = misal.Informe(os.path.join(misal.DATOS, 'extraer_qa.txt'),
                        'FASE 3 — LOS CIEN MISALITOS, DÍA POR DÍA')
    carpeta = os.path.join(misal.MISSALE, 'Misalitos')
    fich = sorted(f for f in os.listdir(carpeta) if f.endswith('.pdf'))
    os.makedirs(SALIDA, exist_ok=True)

    tot = Counter()
    por_fich, avisos = [], []
    rot_vistos, rot_malos = Counter(), Counter()
    votivas, misas, sin_lecturas = Counter(), Counter(), []
    for f in fich:
        m = Misalito(os.path.join(carpeta, f))
        d = m.extrae()
        ruta = os.path.join(SALIDA, '%04d-%02d.json' % (d['anio'], d['mes']))
        with open(ruta, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False, separators=(',', ':'))

        dias = {x['fecha'] for x in d['formularios']}
        esp = calendar.monthrange(d['anio'], d['mes'])[1]
        tot['ficheros'] += 1
        tot['formularios'] += len(d['formularios'])
        tot['dias'] += len(dias)
        tot['dias_esperados'] += esp
        tot['avisos'] += len(d['avisos'])
        tot['recortes'] += d['recortes']
        tot['columnas'] += d['columnas']
        for fo in d['formularios']:
            for b in fo['bloques']:
                tot[b['clase']] += 1
                if b['clase'] == 'pieza':
                    rot_vistos[b['rotulo']] += 1
                if b.get('crudo'):
                    rot_malos[(b['crudo'], b['rotulo'])] += 1
            if fo['cabecera']['fuente'] == 'mr':
                tot['cabeceras_suplidas'] += 1
            if fo['misa']:
                tot['submisas'] += 1
            if fo['cabecera']['alterna']:
                tot['alternas'] += 1
            for campo in ('color', 'grado', 'titulo', 'mr'):
                if not fo['cabecera'][campo]:
                    tot['sin_' + campo] += 1
            if fo['cabecera']['resena']:
                tot['con_resena'] += 1
            if fo['cabecera']['alterna']:
                votivas[fo['cabecera']['alterna']] += 1
            if fo['misa']:
                misas[fo['misa']] += 1
            rots = {b['rotulo'] for b in fo['bloques']}
            if not rots & {'PRIMERA LECTURA', 'EVANGELIO'}:
                sin_lecturas.append((d['fichero'], fo['fecha'], fo['orden'],
                                     fo['misa'] or fo['cabecera']['titulo']
                                     or fo['cabecera']['grado'] or '—'))
        por_fich.append((d['fichero'], d['familia'], len(dias), esp,
                         len(d['formularios']), len(d['avisos'])))
        avisos += [(d['fichero'], a) for a in d['avisos']]
        print('  %-22s %-12s %2d/%2d días  %3d formularios'
              % (d['fichero'], d['familia'], len(dias), esp,
                 len(d['formularios'])), flush=True)

    # --- el informe -------------------------------------------------------
    inf.di('Los cien misalitos, partidos en días y en formularios. Un fichero')
    inf.di('por mes en datos/misalitos/AAAA-MM.json, con cada formulario, su')
    inf.di('cabecera y sus bloques rotulados, en bruto.')
    inf.di()
    inf.di('ficheros                      : %d' % tot['ficheros'])
    inf.di('días del mes alcanzados       : %d de %d'
           % (tot['dias'], tot['dias_esperados']))
    inf.di('formularios                   : %d  (%.2f por día)'
           % (tot['formularios'],
              tot['formularios'] / float(tot['dias'] or 1)))
    inf.di('   con la cabecera suplida    : %d  (el día no la lleva y se abre '
           'en su «MR p.»)' % tot['cabeceras_suplidas'])
    inf.di('   de un día con más de una misa : %d  (la vigilia, la aurora, el '
           'día, las tres de los Difuntos)' % tot['submisas'])
    inf.di('bloques                       : %d piezas, %d rúbricas del Misal, '
           '%d editoriales, %d del santoral mexicano'
           % (tot['pieza'], tot['rubrica'], tot['editorial'],
              tot['santoral']))
    inf.di('formularios con reseña        : %d' % tot['con_resena'])
    inf.di('   con misa votiva permitida  : %d  («Feria o / Misa de Santa '
           'María en Sábado»)' % tot['alternas'])
    inf.di('párrafos recortados del día siguiente : %d' % tot['recortes'])
    inf.di('bloques en dos columnas, deshechos    : %d  (las secuencias)'
           % tot['columnas'])

    inf.titulo('Los días que faltan')
    faltan = [(n, d, e) for n, _, d, e, _, _ in por_fich if d < e]
    if not faltan:
        inf.di('Ninguno: los %d días de los cien meses tienen formulario.'
               % tot['dias'])
    else:
        for n, d, e in faltan:
            inf.di('   %-22s %d de %d' % (n, d, e))

    inf.titulo('Las piezas, contadas')
    for r in PIEZAS:
        inf.di('   %-32s %5d' % (r, rot_vistos[r]))
    inf.di()
    inf.di('De los campos de la cabecera, los que la fuente no da:')
    for campo in ('color', 'grado', 'titulo', 'mr'):
        inf.di('   sin %-10s %5d de %d'
               % (campo, tot['sin_' + campo], tot['formularios']))

    inf.titulo('Los rótulos que la fuente escribe mal')
    inf.di('Se reconocen por parecido con el rótulo bueno, y cada uno se')
    inf.di('nombra aquí. Lo que la fuente imprime mal no se corrige en')
    inf.di('silencio.')
    inf.di()
    if not rot_malos:
        inf.di('   ninguno')
    for (crudo, canon), n in rot_malos.most_common():
        inf.di('   %-38s → %-32s %d vez(ces)' % (crudo, canon, n))

    inf.titulo('Lo que el día deja elegir')
    inf.di('No es una lista que haya que inventar: el misalito la imprime.')
    inf.di()
    inf.di('Las misas de un mismo día, cuando hay más de una:')
    for m, n in misas.most_common():
        inf.di('   %-34s %4d' % (m[:34], n))
    inf.di()
    inf.di('Las misas votivas que el día permite en lugar de la feria '
           '(%d en total,' % sum(votivas.values()))
    inf.di('%d distintas):' % len(votivas))
    for m, n in votivas.most_common(28):
        inf.di('   %-54s %4d' % (m[:54], n))
    if len(votivas) > 28:
        inf.di('   … y %d más' % (len(votivas) - 28))

    inf.titulo('Los formularios sin lecturas')
    inf.di('%d de %d. No es un fallo del parseo: son las misas que remiten '
           'sus' % (len(sin_lecturas), tot['formularios']))
    inf.di('lecturas a otro sitio —«Las lecturas son las mismas de la misa '
           'del día»—,')
    inf.di('y la fase 4 las resuelve por ahí. Se nombran todas:')
    inf.di()
    for n, f, o, q in sin_lecturas:
        inf.di('   %-22s %s o%d  %s' % (n, f, o, str(q)[:44]))

    inf.titulo('Las dos publicaciones')
    pub = Counter(fa for _, fa, _, _, _, _ in por_fich)
    inf.di('No son tres familias de maqueta por años, como suponía el plan,')
    inf.di('sino dos publicaciones distintas:')
    inf.di()
    for fa, n in pub.most_common():
        inf.di('   %-14s %3d ficheros' % (fa, n))
    pv = [n for n, fa, _, _, _, _ in por_fich if fa == 'palabraviva']
    inf.di('   los de Palabra Viva: %s' % ', '.join(pv))

    inf.titulo('Lo que no cuadró, fichero por fichero')
    inf.di('%d avisos en total.' % tot['avisos'])
    inf.di()
    cur = None
    for n, a in avisos:
        if n != cur:
            inf.di('   %s' % n)
            cur = n
        inf.di('      %s' % a)

    inf.titulo('Cada fichero')
    inf.di('%-22s %-12s %5s %5s %5s' % ('fichero', 'publicación', 'días',
                                        'form.', 'avisos'))
    for n, fa, d, e, nf, na in por_fich:
        inf.di('%-22s %-12s %2d/%2d %5d %5d' % (n, fa, d, e, nf, na))

    inf.guarda()
    print('\n%d formularios en %d días, de %d ficheros'
          % (tot['formularios'], tot['dias'], tot['ficheros']))


if __name__ == '__main__':
    main()
