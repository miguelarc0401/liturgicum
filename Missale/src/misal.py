# -*- coding: utf-8 -*-
"""Lo común a las seis fases del Missale.

Tres fuentes y un solo criterio: **se parsea por rótulo, no por posición**.
El Misal latino rotula sus piezas (`Collecta`, `Super oblata`), el Ordinario
castellano numera sus rúbricas (1-146, las mismas que el latino), y los
misalitos titulan sus bloques (`ORACIÓN COLECTA`). En los tres casos la
etiqueta es literal y se cuenta, así que no hace falta adivinar dónde empieza
una pieza: hace falta reconocer su nombre.

Aquí viven: dónde se trabaja, la extracción de los PDF, la limpieza de lo
marginal y la forma canónica con que se cotejan dos textos.
"""

import difflib
import math
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MISSALE = os.path.join(RAIZ, 'Missale')
DATOS = os.path.join(MISSALE, 'datos')
LIBRO = os.path.join(DATOS, 'libro')


# --- dónde se trabaja -----------------------------------------------------
# Los cien misalitos y los dos misales pesan 364 MB y su volcado en texto
# otros tantos. Ni una cosa ni la otra se versionan —se rehacen con una
# orden—, y la carpeta del proyecto está sincronizada con la nube: dejar ahí
# el volcado hace que cada pasada compita con la subida de la anterior, que
# es lo que ya se midió en el Breviarium. Con MISSALE_TRABAJO se le dice
# otro sitio.

def _trabajo():
    d = os.environ.get('MISSALE_TRABAJO')
    if d:
        return d
    base = (os.environ.get('LOCALAPPDATA')
            or os.environ.get('XDG_CACHE_HOME')
            or os.path.join(os.path.expanduser('~'), '.cache')
            or tempfile.gettempdir())
    return os.path.join(base, 'missale')


TRABAJO = _trabajo()
TEXTOS = os.path.join(TRABAJO, 'txt')


# La consola de Windows viene en cp1252 y el latín del Misal no cabe ahí.
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass


# --------------------------------------------------------------------------
# del PDF al texto
# --------------------------------------------------------------------------

def texto_de(pdf, nombre=None, layout=True):
    """El PDF en texto, una lista de líneas.

    Con `-layout`, que es lo que conserva los versos de las antífonas en su
    línea y la sangría de las rúbricas. Se extrae una vez y se guarda en la
    carpeta de trabajo; si el PDF es más nuevo que el volcado, se rehace.
    """
    os.makedirs(TEXTOS, exist_ok=True)
    nombre = nombre or os.path.splitext(os.path.basename(pdf))[0]
    destino = os.path.join(TEXTOS, nombre + '.txt')
    if (not os.path.exists(destino)
            or os.path.getmtime(destino) < os.path.getmtime(pdf)):
        orden = ['pdftotext', '-enc', 'UTF-8']
        if layout:
            orden.append('-layout')
        print(f'  pdftotext {nombre}…', flush=True)
        r = subprocess.run(orden + [pdf, destino])
        if r.returncode:
            sys.exit(f'pdftotext falló con {pdf}')
    with open(destino, encoding='utf-8') as f:
        return f.read().split('\n')


# --------------------------------------------------------------------------
# lo marginal
# --------------------------------------------------------------------------

# El encabezado de página repite el rótulo de la sección y añade el número:
# «HEBDOMADA II ADVENTUS 133», «ORDO MISSÆ 512». Son cuarenta en el Misal
# latino, y no son texto del libro.
ENCABEZADO = re.compile(r'^[^a-zàáâäèéêëìíîïòóôöùúûü]{4,}\s+(\d{1,4})\s*$')

# La nota al pie va numerada y empieza por la llamada: «57 Cf. Tertullianus…».
NOTA = re.compile(r'^\d{1,3}\s+(Cf\.|Cfr\.|Ibid|Vide|S\.|Conc\.|Const\.)')


def es_encabezado(linea):
    m = ENCABEZADO.match(linea)
    return m is not None


def pagina_de(linea):
    """El número de página si la línea es un encabezado; si no, None."""
    m = ENCABEZADO.match(linea)
    return int(m.group(1)) if m else None


def es_nota(linea):
    return bool(NOTA.match(linea))


# --- las palabras que `-layout` deja en el margen --------------------------
# pdftotext con `-layout` deja a veces una palabra en el margen derecho de la
# línea de arriba: «Feria quarta            mereámur.», y la oración de
# debajo se queda sin su última palabra. En el cuerpo del Misal latino son
# treinta y tres, y no son un detalle: una deja «meam» fuera de la antífona
# de entrada del jueves después de Ceniza, y otra tapa el rótulo del
# PREFACIO I DE SANTA MARÍA VIRGEN, que es el que más citan los días.
#
# No hay que adivinar dónde va cada una: `-raw` trae el mismo cuerpo con el
# orden bueno —las dos extracciones coinciden en 143 367 palabras de 143 390,
# y lo que difiere son justo estos saltos—, así que la reparación es un diff
# entre las dos y mover la palabra a donde la segunda dice. Nada se inventa
# y nada se pierde: lo que no se pueda emparejar va al informe.

MARGINADA = re.compile(
    r'^.{4,}\s{5,}[a-záéíóúæœǽ][^\s]{2,15}\s*$')


def _trozos(lineas, desde, hasta):
    """Los trozos separados por espacios de un tramo, con su procedencia:
    `(texto, línea, desde, hasta)`. Se parte por espacios y no por palabras
    para que la puntuación siga pegada a lo suyo."""
    out = []
    for i in range(desde, hasta):
        for m in re.finditer(r'\S+', lineas[i].replace('\f', ' ')):
            out.append((m.group(0), i, m.start(), m.end()))
    return out


def repara_desplazadas(lay, raw, dl, hl, dr, hr):
    """Devuelve `(lineas, movidas, sin_emparejar)`.

    `lay` y `raw` son los dos volcados del mismo PDF, y `dl..hl` / `dr..hr`
    el cuerpo de cada uno. Se comparan trozo a trozo: lo que en uno falta y
    en el otro sobra es una palabra desplazada, y se lleva a donde el segundo
    volcado la pone.
    """
    A = _trozos(lay, dl, hl)
    B = _trozos(raw, dr, hr)
    sm = difflib.SequenceMatcher(None, [t[0] for t in A], [t[0] for t in B],
                                 autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']

    # El emparejamiento va trozo a trozo, no bloque a bloque: a veces el
    # diff agrupa de otra manera en cada lado —«(p. 956). erexísti,» contra
    # «(p. 956).» y «mirabíliter erexísti,»— y por bloques no cuadrarían.
    sobran = []        # (texto, índice de A donde va) según `raw`
    for tag, i1, i2, l1, l2 in ops:
        if tag in ('insert', 'replace'):
            for k in range(l1, l2):
                sobran.append([B[k][0], i1, False, k])

    quitar = set()          # índices de A que se van
    poner = {}              # índice de A ante el cual se insertan trozos
    movidas, sin_emparejar = [], []

    for tag, i1, i2, l1, l2 in ops:
        if tag not in ('delete', 'replace'):
            continue
        for k in range(i1, i2):
            texto = A[k][0]
            # las rúbricas espaciadas letra a letra caen en otro sitio en
            # cada volcado y se recomponen aparte: aquí no se tocan
            if len(texto) == 1:
                sin_emparejar.append(('espaciada', A[k][1] + 1, texto))
                continue
            cand = [s for s in sobran if s[0] == texto and not s[2]]
            if not cand:
                sin_emparejar.append(('sin pareja', A[k][1] + 1, texto))
                continue
            # el más cercano, que es el que el salto de columna produjo
            s = min(cand, key=lambda s: abs(s[1] - k))
            s[2] = True
            quitar.add(k)
            poner.setdefault(s[1], []).append((s[3], texto))
            destino = A[s[1]][1] if s[1] < len(A) else A[-1][1]
            movidas.append((A[k][1] + 1, destino + 1, texto))
    for s in sobran:
        if not s[2] and len(s[0]) > 1:
            sin_emparejar.append(('sobra en raw', s[1], s[0]))

    # cuando dos trozos van al mismo sitio, el orden lo da `raw`
    poner = {k: [t for _, t in sorted(v)] for k, v in poner.items()}

    # rehacer las líneas del tramo con los trozos que quedan. Un trozo que
    # se inserta ante el primero de su línea va al final de la de arriba:
    # ahí es donde `-layout` lo quitó, y donde el lector lo espera.
    primero_de = {}
    for k, (_, ln, _, _) in enumerate(A):
        primero_de.setdefault(ln, k)

    por_linea = {}
    for k, (texto, ln, _, _) in enumerate(A):
        if k in poner:
            if primero_de.get(ln) == k:
                anterior = next((l for l in range(ln - 1, -1, -1)
                                 if l in por_linea), None)
                if anterior is not None:
                    por_linea[anterior].extend(poner[k])
                else:
                    por_linea.setdefault(ln, []).extend(poner[k])
            else:
                por_linea.setdefault(ln, []).extend(poner[k])
        if k not in quitar:
            por_linea.setdefault(ln, []).append(texto)
    if len(A) in poner:
        por_linea.setdefault(A[-1][1], []).extend(poner[len(A)])

    nuevas = list(lay)
    for ln, trozos in por_linea.items():
        # se conserva la sangría, que es lo que `-layout` aporta
        sangria = len(lay[ln]) - len(lay[ln].lstrip())
        salto = '\f' if '\f' in lay[ln] else ''
        nuevas[ln] = salto + ' ' * sangria + ' '.join(trozos)
    for ln in range(dl, hl):
        if ln not in por_linea and lay[ln].strip():
            nuevas[ln] = ''
    return nuevas, movidas, sin_emparejar


def paginas_de(lineas):
    """La página física del PDF de cada línea, contando saltos de página.

    El Misal latino sólo imprime cuarenta encabezados de página en su capa de
    texto, así que la paginación del libro no se puede seguir por ahí. La
    física sí: el salto de página va en la línea, y con ella se puede abrir el
    PDF por donde el informe diga.
    """
    pags, p = [], 1
    for ln in lineas:
        pags.append(p)
        p += ln.count('\f')
    return pags


# --- las rúbricas espaciadas letra a letra --------------------------------
# Unas setenta rúbricas del Misal van «t r a c k e a d a s»: el PDF mete un
# espacio de verdad entre cada letra y los de palabra se pierden —medido en
# la geometría del fichero: todos los espacios valen 3.03, y los huecos entre
# letras, cero—. Ni pdftotext ni PyMuPDF pueden deshacerlo, porque la
# información no está.
#
# Lo que sí está es el resto del libro: 1.3 MB de latín de donde sale un
# vocabulario con su frecuencia. Con él la segmentación es un camino mínimo
# —el de Norvig: una palabra desconocida cuesta tanto más cuanto más larga—,
# y lo que no cuadre se escribe en el informe con las dos formas, la cruda y
# la segmentada, para que se arregle a mano y no para que pase por buena.

_PREFIJO_NUM = re.compile(r'^\s*(?:\d{1,3}\.\s+)?')

# Las palabras que el Misal usa **sólo** dentro de estas rúbricas: no están
# en ninguna otra línea del libro, así que el vocabulario no las tiene y la
# segmentación las parte en dos («præ ferendo», «conc ord et»). Se nombran
# aquí, que es menos frágil que corregir la línea entera: una palabra vale
# para todas las rúbricas donde salga.
VOCABULARIO_EXTRA = (
    'omnino nudum tobaleis implentibus præferendo concordet observabilis '
    'duplex recitari communicavit'
).split()

# Y las que ni con vocabulario salen, porque el modelo de frecuencias
# prefiere lo frecuente: «quid» pierde contra «qui», que es diez veces más
# común, y deja la «d» pegada a lo que sigue. La clave es la línea colapsada,
# que no cambia si se vuelve a extraer el PDF.
SUELTAS = {
    'ViriGalilǽi,quidadmiráminiaspiciéntesincælum?':
        'Viri Galilǽi, quid admirámini aspiciéntes in cælum?',
}


def es_suelta(linea, abierta=False):
    """Verdadero si la línea viene espaciada letra a letra.

    Con `abierta` la condición se relaja: la última línea de una rúbrica
    espaciada puede ser «t i b u s .», cinco caracteres, y hay que cogerla o
    la palabra partida por el guión se queda a medias.
    """
    trozos = [t for t in _PREFIJO_NUM.sub('', linea.strip()).split(' ') if t]
    minimo = 3 if abierta else 10
    if len(trozos) < minimo:
        return False
    sueltos = sum(1 for t in trozos if len(t) == 1)
    return sueltos >= minimo and sueltos / len(trozos) >= 0.8


# Las únicas palabras latinas de una letra. Un trozo de una letra que no sea
# una de éstas delata que la segmentación partió una palabra en dos.
UNA_LETRA = {'a', 'e', 'o'}


def sospechosas(trozos, seg):
    """Lo que delata una segmentación mal hecha, sin tener que leerla.

    Tres señales, y las tres se cuentan: una palabra que el libro no usa en
    ninguna otra parte; un trozo de una letra que no es palabra; y dos trozos
    seguidos cuya unión **sí** es palabra del libro, que es exactamente lo
    que pasa cuando «præparatum» sale «præ paratum».
    """
    palabras = [t for t in trozos if t.isalpha()]
    # «n.», «p.», «b)»: una letra seguida de punto o paréntesis es una
    # abreviatura o una viñeta del libro, no una palabra partida
    marca = {t for t, sig in zip(trozos, trozos[1:])
             if len(t) == 1 and sig and sig[0] in '.)'}
    malas = []
    for w in palabras:
        if not seg.conocida(w):
            malas.append(w)
        elif len(w) == 1 and w.lower() not in UNA_LETRA and w not in marca:
            malas.append(w)
    for a, b in zip(palabras, palabras[1:]):
        if seg.conocida(a + b) and seg.voc[(a + b).lower()] >= 2:
            malas.append(f'{a}|{b}')
    return malas


class Segmentador:
    """Recompone las palabras de una línea espaciada letra a letra.

    El vocabulario se saca de las líneas que **no** vienen espaciadas, así
    que no hay diccionario externo que mantener: el libro se explica solo.
    """

    PEAJE = 2.0        # lo que cuesta abrir palabra
    LARGO = 22         # la palabra latina más larga que se intenta
    PORLETRA = 3.2     # lo que cuesta cada letra de una palabra desconocida
    # 3.2 es medido, no elegido: con 2.3 quedan cuatro rúbricas mal, con 3.6
    # empieza a partir en dos las palabras largas de verdad («observa bilis»).

    def __init__(self, lineas, extra=()):
        self.voc = Counter()
        for ln in lineas:
            if es_suelta(ln):
                continue
            for w in re.findall(r'[A-Za-zÀ-ÿÆæŒœǼǽ]+', ln):
                self.voc[w.lower()] += 1
        for w in extra:
            self.voc[w.lower()] += 1
        self.n = sum(self.voc.values()) or 1
        self._ln = math.log(self.n)

    def _coste(self, w):
        f = self.voc.get(w.lower())
        if f:
            return self.PEAJE - math.log(f / self.n)
        # desconocida: caro, y tanto más cuanto más larga, que es lo que
        # impide que se tome media línea por una palabra
        return self.PEAJE + self._ln + len(w) * self.PORLETRA

    def conocida(self, w):
        return w.lower() in self.voc

    def parte(self, cadena):
        """La cadena sin espacios → lista de palabras y signos.

        `\\x01` es frontera dura: con ella se marca el salto de línea del
        original, para devolver el resultado con sus líneas.
        """
        n = len(cadena)
        mejor = [None] * (n + 1)
        mejor[0] = (0.0, [])
        for i in range(n):
            if mejor[i] is None:
                continue
            c, w = mejor[i]
            if not cadena[i].isalpha():
                # las cifras van juntas: «1 0 1 2» es la página 1012
                j = i
                while j < n and cadena[j].isdigit():
                    j += 1
                j = max(j, i + 1)
                cand = (c, w + [cadena[i:j]])
                if mejor[j] is None or cand[0] < mejor[j][0]:
                    mejor[j] = cand
                continue
            for j in range(i + 1, min(n, i + self.LARGO) + 1):
                t = cadena[i:j]
                if not t[-1].isalpha():
                    break
                cand = (c + self._coste(t), w + [t])
                if mejor[j] is None or cand[0] < mejor[j][0]:
                    mejor[j] = cand
        return mejor[n][1] if mejor[n] else None


def _pega(trozos):
    """Las palabras y signos, otra vez en una línea con los espacios donde
    van: delante de un signo de cierre no, detrás de uno de apertura no."""
    salida = ''
    for t in trozos:
        if not t:
            continue
        if t[0] in ',.;:)]!?”' or (salida and salida[-1] in '([“'):
            salida += t
        elif t == '-' or (salida and salida[-1] == '-'):
            salida += t
        else:
            salida += (' ' if salida else '') + t
    return salida


def rehace_sueltas(lineas, desde=0, hasta=None, extra=VOCABULARIO_EXTRA):
    """Devuelve `(lineas, casos)` con las rúbricas espaciadas recompuestas.

    `casos` es una lista de `(numero_de_linea, cruda, rehecha, sospechas)`:
    con las sospechas no vacías, la línea puede estar mal cortada y el
    informe la nombra para que se mire.
    """
    hasta = len(lineas) if hasta is None else hasta
    seg = Segmentador(lineas, extra)
    nuevas, casos = list(lineas), []

    # primero la tabla: lo puesto a mano manda sobre el modelo
    for j in range(desde, hasta):
        if not es_suelta(lineas[j]):
            continue
        colapsada = re.sub(r'(?<=\S) (?=\S)', '',
                           _PREFIJO_NUM.sub('', lineas[j].strip()))
        if colapsada in SUELTAS:
            m = re.match(r'^\s*(\d{1,3}\.)\s', lineas[j])
            nuevas[j] = ((m.group(1) + ' ') if m else '') + SUELTAS[colapsada]
            casos.append((j + 1, lineas[j].strip(), nuevas[j], ['(de tabla)']))
    lineas = nuevas
    nuevas = list(lineas)

    i = desde
    while i < hasta:
        if not es_suelta(lineas[i]):
            i += 1
            continue
        carrera = []
        while i < hasta and es_suelta(lineas[i], abierta=bool(carrera)):
            carrera.append(i)
            i += 1

        # el número de rúbrica se conserva aparte: no entra en la segmentación
        m = re.match(r'^\s*(\d{1,3}\.)\s', lineas[carrera[0]])
        prefijo = (m.group(1) + ' ') if m else ''

        cadena = ''
        for k, j in enumerate(carrera):
            s = re.sub(r'(?<=\S) (?=\S)', '',
                       _PREFIJO_NUM.sub('', lineas[j].strip()))
            if s.endswith('-'):
                cadena += s[:-1]          # guión de partición: se deshace
            else:
                cadena += s + ('\x01' if k < len(carrera) - 1 else '')

        trozos = seg.parte(cadena)
        if trozos is None:
            for j in carrera:
                casos.append((j + 1, lineas[j].strip(), None, ['(sin camino)']))
            continue

        partes, acc = [], []
        for t in trozos:
            if t == '\x01':
                partes.append(acc)
                acc = []
            else:
                acc.append(t)
        partes.append(acc)

        # las líneas unidas por guión se quedan vacías: el texto va en la
        # primera de la carrera, que es donde el lector lo espera
        while len(partes) < len(carrera):
            partes.append([])
        for k, j in enumerate(carrera):
            texto = _pega(partes[k]) if k < len(partes) else ''
            if k == 0:
                texto = prefijo + texto
            nuevas[j] = texto
            casos.append((j + 1, lineas[j].strip(), texto,
                          sospechosas(partes[k], seg) if k < len(partes)
                          else []))
    return nuevas, casos


# --- las mayúsculas espaciadas --------------------------------------------
# Cinco rótulos del Misal van con una letra por carácter y los espacios de
# palabra perdidos: «I N F E R I I S A D V E N T U S». No se pueden
# segmentar sin un diccionario, así que van en tabla, y lo que no esté en la
# tabla se escribe en el informe en vez de dejarlo roto.

ESPACIADAS = {
    'INFERIISADVENTUS': 'IN FERIIS ADVENTUS',
    'INSOLLEMNITATIBUSDOMINI': 'IN SOLLEMNITATIBUS DOMINI',
    'BENEDICTIONESINFINEMISSÆ': 'BENEDICTIONES IN FINE MISSÆ',
    'ETORATIONESSUPERPOPULUM': 'ET ORATIONES SUPER POPULUM',
    'ORDOMISSÆ': 'ORDO MISSÆ',
    'INDICES': 'INDICES',
}

_ESPACIADA = re.compile(r'^(?:[A-ZÆŒÁÉÍÓÚ]\s)+[A-ZÆŒÁÉÍÓÚ]$')


def desespacia(linea):
    """«I N F E R I I S …» → «IN FERIIS …». Devuelve (texto, reconocida)."""
    s = linea.strip()
    if not _ESPACIADA.match(s):
        return s, True
    junto = s.replace(' ', '')
    if junto in ESPACIADAS:
        return ESPACIADAS[junto], True
    return junto, False


# --------------------------------------------------------------------------
# el PDF en tiradas de color
# --------------------------------------------------------------------------
# El Ordinario de México marca sus rúbricas **en rojo** (#c0504d: 7 789
# caracteres rojos contra 9 978 negros en las veinte primeras páginas), igual
# que la fuente de la Liturgia de las Horas. Así que no hay que adivinar por
# la sangría —que aquí no sirve: el texto rezado está a la izquierda en las
# primeras páginas y a cinco espacios en las plegarias, porque la capitular
# mueve la caja— sino leer el color, que es lo que el libro dice.
#
# De ahí que esto devuelva *líneas de tiradas*, en el mismo formato que
# `Breviarium/src/breviario.py`: cada línea es una lista de `(rojo, texto)`,
# de modo que no se pierde qué parte de un verso es rúbrica —el «V/.», el
# «N.» del Papa, el corchete de lo que puede omitirse— y qué parte se reza.

ROJO_MX = 0xc0504d          # el rojo de las rúbricas del Ordinario
TITULO_MIN = 19.5           # de ahí arriba y en negro, es rótulo de sección
CAPITULAR_MIN = 19.0        # de ahí arriba y en rojo, es capitular


def tiradas_de(pdf, rojo=ROJO_MX):
    """El PDF en líneas de tiradas `(rojo, texto)`.

    Devuelve una lista de diccionarios con, por cada línea: la página física
    (`p`), la impresa si un encabezado la dio (`pag`), el cuerpo de letra
    predominante (`tam`), y las tiradas.

    Tres cosas hay que deshacer del original, y las tres son de maqueta:

    **La capitular.** La letra que abre la oración va en rojo y a veces a
    cuerpo veinte: es la primera letra de lo que se reza, no una rúbrica, así
    que pasa a negro y se pega a su palabra («E» + «l cual» → «El cual»).

    **La marca de la capitular.** Delante de ella el fichero lleva una
    etiqueta roja de dos o tres letras —«CP», «CC», «C1»…— que no se imprime
    en el papel. Se retira y se devuelve aparte, en `marca`.

    **El espacio entre palabras**, que a veces es una tirada propia y además
    roja. Si se tirara por estar en blanco, saldría «Glorifiquenal Señor»:
    así que se conserva y se pega a lo que lleve delante.
    """
    import fitz                      # PyMuPDF, sólo hace falta aquí

    marca_re = re.compile(r'^(?:C[0-9P-T]|[A-Z]{2,4}[0-9]?)$')
    doc = fitz.open(pdf)
    lineas = []
    for n, hoja in enumerate(doc, 1):
        for bloque in hoja.get_text('dict')['blocks']:
            for ln in bloque.get('lines', []):
                spans = list(ln['spans'])
                if not any(s['text'].strip() for s in spans):
                    continue

                # el cuerpo predominante, de lo que tiene texto
                tam = Counter(round(s['size'], 1) for s in spans
                              if s['text'].strip()).most_common(1)[0][0]

                # la marca de la capitular, si la hay
                marca = None
                llenos = [s for s in spans if s['text'].strip()]
                if (llenos and llenos[0]['color'] == rojo
                        and marca_re.match(llenos[0]['text'].strip())
                        and len(llenos) > 1):
                    marca = llenos[0]['text'].strip()
                    spans = spans[spans.index(llenos[0]) + 1:]

                piezas, blanco = [], ''
                for k, s in enumerate(spans):
                    if not s['text'].strip():
                        blanco += s['text']      # el espacio, que se guarda
                        continue
                    txt = blanco + s['text']
                    blanco = ''
                    # capitular: una letra roja, o grande, o seguida de
                    # minúscula que continúa la palabra
                    siguiente = next((x for x in spans[k + 1:]
                                      if x['text'].strip()), None)
                    cap = (s['color'] == rojo
                           and len(s['text'].strip()) == 1
                           and s['text'].strip().isalpha()
                           and (s['size'] >= CAPITULAR_MIN
                                or (siguiente is not None
                                    and siguiente['color'] != rojo
                                    and siguiente['text'][:1].islower())))
                    piezas.append({'rojo': s['color'] == rojo and not cap,
                                   'texto': txt.strip() if cap else txt,
                                   'pega': cap})

                tiradas = []
                for p in piezas:
                    if tiradas and (tiradas[-1][2] or p['pega']):
                        tiradas[-1] = (tiradas[-1][0],
                                       tiradas[-1][1] + p['texto'].lstrip(),
                                       False)
                    elif tiradas and tiradas[-1][0] == p['rojo']:
                        tiradas[-1] = (p['rojo'],
                                       tiradas[-1][1] + p['texto'], False)
                    else:
                        tiradas.append((p['rojo'], p['texto'], p['pega']))

                tiradas = [(r, re.sub(r'\s+', ' ', t)) for r, t, _ in tiradas]
                tiradas = [(r, t) for r, t in tiradas if t.strip()]
                if not tiradas:
                    continue
                tiradas[0] = (tiradas[0][0], tiradas[0][1].lstrip())
                tiradas[-1] = (tiradas[-1][0], tiradas[-1][1].rstrip())
                tiradas = [(r, t) for r, t in tiradas if t]
                if not tiradas:
                    continue

                lineas.append({'p': n, 'pag': None, 'tam': tam,
                               'marca': marca, 'tiradas': tiradas})
    return lineas


def plano(linea):
    """El texto de una línea de tiradas, sin distinguir rúbrica de oración."""
    return ''.join(t for _, t in linea['tiradas']).strip()


def es_rubrica(linea):
    """Verdadero si toda la línea va en rojo: un rótulo, una indicación.

    Una línea con rojo **y** negro no es rúbrica: es texto rezado con una
    marca dentro («con tu servidor el Papa N.»), y se guarda entera."""
    return bool(linea['tiradas']) and all(r for r, _ in linea['tiradas'])


def solo_negro(linea):
    return bool(linea['tiradas']) and not any(r for r, _ in linea['tiradas'])


# --------------------------------------------------------------------------
# cotejo de textos
# --------------------------------------------------------------------------

def clave(texto):
    """Forma canónica de un texto, para compararlo con otro.

    Quita tildes, signos y mayúsculas: lo que queda son las letras. Dos
    textos con la misma clave son el mismo texto aunque uno escriba
    «quǽsumus» y el otro «quæsumus», o difieran en un acento.
    """
    t = unicodedata.normalize('NFKD', texto.lower())
    t = t.replace('æ', 'ae').replace('œ', 'oe')
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r'[^a-z0-9ñ ]+', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def tripletas(texto):
    """Las tripletas de palabras de un texto, para reconocer dos impresiones
    del mismo pasaje aunque difieran en una palabra. Es lo que la fase 4
    necesita para buscar una oración en todo el corpus."""
    p = clave(texto).split()
    return {' '.join(p[i:i + 3]) for i in range(len(p) - 2)}


# --------------------------------------------------------------------------
# informes
# --------------------------------------------------------------------------

class Informe:
    """El informe de una fase. La regla del proyecto: lo que no se pudo
    resolver se escribe, no se calla."""

    def __init__(self, ruta, titulo):
        self.ruta = ruta
        self.lineas = [titulo, '=' * len(titulo), '']

    def di(self, texto=''):
        self.lineas.append(texto)

    def titulo(self, texto):
        self.lineas += ['', texto, '-' * len(texto), '']

    def guarda(self):
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        with open(self.ruta, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.lineas) + '\n')
        print(f'  informe → {os.path.relpath(self.ruta, RAIZ)}')
