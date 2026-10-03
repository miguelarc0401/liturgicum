# -*- coding: utf-8 -*-
"""Fase 1 — el Misal Romano 2002 en latín.

De `Missale/latin_missal2002_organized.pdf` salen, en una pasada:

  · los ~600 **formularios** del Propio del tiempo, del Propio de los santos,
    de los Comunes, de las misas rituales, por diversas necesidades, votivas
    y de difuntos, cada uno con sus cinco o seis piezas;
  · los **prefacios** comunes del cuerpo de prefacios (50) y la cuenta de los
    **propios** que los días citan sin que el cuerpo los imprima;
  · el **Ordo Missæ** con sus rúbricas numeradas 1-146 —las mismas que numera
    el Ordinario de México, que es lo que permite dar el bilingüe sin
    coserlo a mano—;
  · las **plegarias eucarísticas** I-IV, las de la reconciliación y las de
    diversas necesidades;
  · las **bendiciones solemnes** y las **oraciones sobre el pueblo**, que es
    justo lo que al castellano le falta.

El libro está rotulado, no maquetado: `Collecta` aparece 602 veces y
`Super oblata` 467, siempre al principio de línea y siempre con ese nombre.
De ahí que se parsee por rótulo. De la posición se mira sólo qué rótulo de
sección manda sobre cuál, y para eso basta una regla: un encabezado seguido
de piezas es un formulario, y un encabezado seguido de otro encabezado es una
sección.

La otra regla que lo hace posible: una oración latina acaba en su conclusión
(«Per Dóminum.», «Qui tecum.»), así que lo que venga después y antes del
rótulo siguiente es rúbrica y no oración. Son 1 742 conclusiones para 1 579
oraciones: alcanzan.

No depende de nada: ni del calendario, ni de los misalitos, ni de la fase 2.

    python Missale/src/1_latino.py

Deja `Missale/datos/misal_latino.json` y `Missale/datos/latino_qa.txt`.
Necesita `pdftotext` en el PATH.
"""

import json
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misal
from misal import DATOS, MISSALE, Informe, clave, desespacia, es_encabezado, pagina_de

PDF = os.path.join(MISSALE, 'latin_missal2002_organized.pdf')
SALIDA = os.path.join(DATOS, 'misal_latino.json')
QA = os.path.join(DATOS, 'latino_qa.txt')


# --------------------------------------------------------------------------
# el vocabulario del libro
# --------------------------------------------------------------------------

# Las partes de primer nivel, en el orden en que vienen; el tercer campo dice
# si la parte trae formularios. El título puede ocupar dos o tres líneas
# («MISSÆ ET ORATIONES / PRO VARIIS NECESSITATIBUS / VEL AD DIVERSA»): se
# busca la primera y se absorbe lo que siga en mayúsculas.
PARTES = [
    ('tempore',       'PROPRIUM DE TEMPORE', True),
    ('ordo',          'ORDO MISSÆ',          False),
    ('preces',        'PRECES EUCHARISTICÆ', False),
    ('ordo_unus',     'ORDO MISSÆ',          False),
    ('apendice_ordo', 'APPENDIX',            False),
    ('sanctis',       'PROPRIUM DE SANCTIS', True),
    ('communia',      'COMMUNIA',            True),
    ('rituales',      'MISSÆ RITUALES',      True),
    ('necessitatibus', 'MISSÆ ET ORATIONES', True),
    ('votivae',       'MISSÆ VOTIVÆ',        True),
    ('defunctorum',   'MISSÆ DEFUNCTORUM',   True),
    ('apendices',     'APPENDICES',          False),
    ('indices',       'INDICES',             False),
]

CON_FORMULARIOS = {i for i, _, c in PARTES if c}

# Los rótulos de pieza. El resto de la línea, cuando lo hay, es la cita
# bíblica de la antífona: «Ant. ad introitum Cf. Ps 24, 1-3».
PIEZAS = [
    ('entrada',     'Ant. ad introitum'),
    ('comunion',    'Ant. ad communionem'),
    ('colecta',     'Collecta'),
    ('ofrendas',    'Super oblata'),
    ('poscomunion', 'Post communionem'),
    ('pueblo',      'Oratio super populum'),
]
OBLIGATORIAS = ('entrada', 'colecta', 'ofrendas', 'comunion', 'poscomunion')
# Erratas del propio Misal 2002: el 3 de septiembre rotula «Super oblate».
# Se admiten como lo que son, y el informe las nombra una por una.
ERRATAS = {'Super oblate': 'Super oblata'}

# En el Triduo y en el Domingo de Ramos el rótulo va numerado con la rúbrica
# del día: «20. Collecta», «71. Ant. ad introitum». Son veinticuatro, y son
# los días que más importan del año, así que el número es opcional y se
# guarda: dice en qué rúbrica del rito cae la pieza.
ROTULO = re.compile(
    r'^(?:(\d{1,3})\.\s+)?('
    + '|'.join(re.escape(r) for _, r in PIEZAS)
    + '|' + '|'.join(re.escape(r) for r in ERRATAS) + r')\s*(.*)$')
NOMBRE_DE = {r: n for n, r in PIEZAS}
NOMBRE_DE.update({mal: NOMBRE_DE[bien] for mal, bien in ERRATAS.items()})

# «Vel:» abre una alternativa a la pieza en curso; cuando la alternativa es
# una antífona, trae su propia cita: «Vel: Io 10, 10».
ALTERNATIVA = re.compile(r'^Vel:\s*(.*)$')

# Las conclusiones de la oración. Aquí acaba el texto y empieza la rúbrica.
CONCLUSION = re.compile(
    r'^(Per Dóminum|Per Christum|Qui tecum|Qui vivis|Qui vivit|Per eúndem)\b')

# Las rúbricas que se guardan aparte porque dicen algo que la app necesita.
# La referencia al prefacio puede ir numerada con la rúbrica del día —«24.
# Præfatio: De dominica Passione.»— y el Misal la escribe una vez «Praefatio»,
# con ae en vez de æ.
PREFACIO_REF = re.compile(r'^(?:\d{1,3}\.\s+)?Pr[æa]e?fati[oæ]\b')
GLORIA = re.compile(r'^(Non )?[Dd]icitur Gló?ria in excélsis')
CREDO = re.compile(r'^(Non )?[Dd]icitur Credo\b')
COMUN_REF = re.compile(r'^(De Communi|Ut in Communi|Omnia de Communi|'
                       r'Omnia ut in Communi)\b')

# Un encabezado en mayúsculas: línea sin minúsculas, de cuatro caracteres
# arriba, que no sea el encabezado de página ni una respuesta del diálogo.
SIN_MINUSCULAS = re.compile(r'^[^a-zàáâäèéêëìíîïòóôöùúûüæœ]+$')
DIALOGO = re.compile(r'^(V\.|R\.|Amen|Sanctus|Hosánna|Benedíctus)\b')

# Los encabezados de día que no van en mayúsculas: las ferias del tiempo, los
# días de diciembre del Adviento, y las misas de la vigilia, la aurora y el
# día, que son una de las cosas que la app ha de dejar elegir.
DIA_MINUSCULA = re.compile(
    r'^(Feria\s+(?:secunda|tertia|quarta|quinta|sexta|[IVX]+)'
    r'(?:\s+[a-zæœ][\w\sæœáéíóúæ.“”]{0,45})?'
    r'|Sabbato(?:\s+[a-zæœ][\w\sæœáéíóú]{0,35})?'
    r'|Dominica\s+[\w\sæœáéíóú“”.]{1,50}'
    r'|Die\s+\d{1,2}\s+\w+'
    r'|Ad Missam[\w\s]{0,35}'
    r'|In octava[\w\s]{0,35})\s*$')

# El Común y las misas por diversas necesidades numeran sus formularios con
# una cifra o una letra sola en su línea: «1», «2», «A», «B». Es encabezado,
# no texto, y se comprueba: detrás viene un rótulo de pieza.
MARCA = re.compile(r'^(\d{1,3}|[A-Z])$')

# Los rótulos de sección con prefijo: «I. PRO SANCTA ECCLESIA»,
# «1. PRO ECCLESIA», «A. Extra tempus paschale», «I. Tempore “ per annum ”».
PREFIJADO = re.compile(r'^(?:([IVXL]{1,4})|(\d{1,3})|([A-Z]))\.\s+(\S.*)$')

# Las secciones anidan así —medido en el libro: «COMMUNE MARTYRUM» >
# «I. Tempore paschali» > «A. Pro pluribus martyribus» > «1»—, y con esa
# escala se arma la ruta de cada formulario sin mirar cuerpos de letra, que
# la capa de texto no conserva.
HONDURA = {'raiz': 0, 'rom': 1, 'num': 2, 'let': 3}

# El santoral ancla el día: «Die 2 ianuarii».
DIA_SANTORAL = re.compile(r'^Die\s+(\d{1,2})\s+(\w+)\s*$')
MESES = {'ianuarii': 1, 'februarii': 2, 'martii': 3, 'aprilis': 4,
         'maii': 5, 'iunii': 6, 'iulii': 7, 'augusti': 8,
         'septembris': 9, 'octobris': 10, 'novembris': 11, 'decembris': 12}

GRADOS = {'sollemnitas': 'sollemnitas', 'festum': 'festum',
          'memoria': 'memoria'}

# Lo que el libro pone entre el título y la primera pieza y no es ni grado ni
# oración: el color, la nota de uso. Se guarda como preámbulo del formulario.
COLOR = re.compile(r'^In hac Missa adhibetur color\b')

# El prefacio **propio** no está en el cuerpo de prefacios: vive dentro de su
# formulario, y el Misal lo imprime entero. Empieza por el diálogo, acaba en
# el Sanctus, y lo titula la línea de arriba —«Præfatio: De mysterio
# Pentecostes.»—. Son los de Pentecostés, la Trinidad, el Corpus, el Sagrado
# Corazón, Cristo Rey, la Transfiguración, la Santa Cruz, la Asunción… y en
# castellano no están en ningún juego: hay que cosecharlos de los misalitos.
DIALOGO_PREFACIO = re.compile(r'^V\.\s+Dóminus\s+vobíscum')
FIN_PREFACIO = re.compile(r'^Sanctus, Sanctus, Sanctus\b')
TONO = re.compile(r'^(Tonus\s|Textus sine cantu)')

PREFACIO_TITULO = re.compile(r'^PRÆFATIO\b')
NUMERADA = re.compile(r'^(\d{1,3})\.\s+(.*)$')


# --------------------------------------------------------------------------
# clasificación de líneas
# --------------------------------------------------------------------------

def es_encabezado_mayusculas(linea):
    """Verdadero si la línea es un rótulo en mayúsculas del libro."""
    s, _ = desespacia(linea)
    if len(s) < 4 or es_encabezado(linea) or DIALOGO.match(s):
        return False
    if not SIN_MINUSCULAS.match(s):
        return False
    # Un número romano solo, o una cifra, no es rótulo: es foliación o la
    # columna de una tabla.
    return bool(re.search(r'[A-ZÆŒÁÉÍÓÚ]{2}', s))


def hondura_de(texto):
    """A qué nivel cuelga un rótulo, por su prefijo. `None` si no lo tiene."""
    m = PREFIJADO.match(texto)
    if not m:
        return None
    return 'rom' if m.group(1) else 'num' if m.group(2) else 'let'


def clase_de(linea, siguiente, formularios=True):
    """Qué es la línea: `'mayus'`, `'dia'`, `'marca'`, `'sub'` o `None`.

    `siguiente` es la siguiente línea con texto, y hace falta para las
    marcas: una cifra sola es encabezado de formulario sólo si detrás viene
    un rótulo de pieza. Si no, es foliación, o la numeración de un verso, y
    entonces no abre nada.

    `formularios` dice si la parte los tiene. En el Ordo y en las plegarias
    no los hay y sí hay rúbricas numeradas —«1. Populo congregato…»—, que
    tienen la misma forma que un subtítulo prefijado y no son lo mismo: por
    eso allí ni las marcas ni los subtítulos cuentan.
    """
    s = linea.strip()
    # el rótulo de pieza manda: «20. Collecta» no es un subtítulo prefijado
    if ROTULO.match(s) or DIALOGO.match(s):
        return None
    if es_encabezado_mayusculas(s):
        return 'mayus'
    if DIA_MINUSCULA.match(s):
        return 'dia'
    if not formularios:
        return None
    if MARCA.match(s):
        return 'marca' if siguiente and ROTULO.match(siguiente) else None
    m = PREFIJADO.match(s)
    # sólo con prefijo de letra o de romano. Los subtítulos con cifra que
    # tiene el libro van todos en mayúsculas —«1. PRO ECCLESIA»— y los coge
    # la regla de arriba; una cifra con texto en minúsculas es una rúbrica
    # numerada del rito («68. Benedictio sollemnis») o una aclamación
    # («1. Per sua sancta vulnera»), y no abre sección ninguna.
    if (m and not m.group(2) and not SIN_MINUSCULAS.match(s)
            and es_titulo(m.group(4))):
        return 'sub'
    return None


def es_titulo(resto):
    """Verdadero si lo que sigue al prefijo es un título y no una frase.

    Un subtítulo del Misal es corto y no lleva puntuación de frase —«A. Extra
    tempus paschale», «I. Tempore “ per annum ”»—; una rúbrica numerada la
    lleva, o es larga, o acaba en coma porque sigue en la línea de abajo.
    """
    resto = resto.strip()
    # 45 es medido: el subtítulo más largo del Misal es «Aliæ orationes pro
    # Missa exsequiali», de 34; las rúbricas numeradas que se le parecen
    # empiezan en 57 («Cum sacerdos ad locum pro benedictione candelarum
    # statutum»).
    return (len(resto) <= 45
            and not re.search(r'[.,:;]', resto)
            and resto[:1].isupper())


def slug(texto):
    t = unicodedata.normalize('NFKD', texto.lower())
    t = t.replace('æ', 'ae').replace('œ', 'oe')
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r'[^a-z0-9]+', '-', t)
    return re.sub(r'-+', '-', t).strip('-')


def cita_limpia(ref):
    """La referencia a un prefacio, sin su aparato: «Præfatio I de beata
    Maria Virgine (in Missis votivis: Et te in veneratióne), p. 547, vel II,
    p. 548.» → «I de beata Maria Virgine».

    Se corta en el primer paréntesis, en la primera coma y en el primer
    «vel», porque de ahí en adelante lo que viene es la alternativa o la
    página, no el nombre."""
    r = re.sub(r'^(?:\d{1,3}\.\s+)?Pr[æa]e?fati[oæ]\s*:?\s*', '', ref)
    r = re.split(r'[(,]|\bvel\b|\bp{1,2}\.\s*\d', r)[0]
    return r.strip(' .,:;')


def limpia(lineas):
    while lineas and not lineas[0]:
        lineas.pop(0)
    while lineas and not lineas[-1]:
        lineas.pop()
    return lineas


# --------------------------------------------------------------------------
# el cuerpo del libro, partido en partes
# --------------------------------------------------------------------------

def partes_del(lineas, inf):
    """De la lista de líneas a [(id, titulo, desde, hasta)].

    Se busca cada rótulo de parte en el orden en que el libro los pone, a
    partir de donde acabó el anterior: así los rótulos que se repiten —ORDO
    MISSÆ sale dos veces, PRECES EUCHARISTICÆ también— caen donde deben sin
    tener que nombrarlos con un número de línea, que cambiaría si el volcado
    cambiase.
    """
    hallados, desde = [], 0
    for ident, rotulo, _ in PARTES:
        n = None
        for i in range(desde, len(lineas)):
            if (lineas[i].strip() == rotulo
                    or desespacia(lineas[i])[0] == rotulo):
                n = i
                break
        if n is None:
            inf.di(f'  ¡AVISO! no se halló la parte «{rotulo}» ({ident})')
            continue
        hallados.append((ident, rotulo, n))
        desde = n + 1

    partes = []
    for k, (ident, rotulo, n) in enumerate(hallados):
        fin = hallados[k + 1][2] if k + 1 < len(hallados) else len(lineas)
        titulo, j = [rotulo], n + 1
        while j < fin and j < n + 5:
            s = lineas[j].strip()
            if not s:
                j += 1
                continue
            if es_encabezado_mayusculas(s) and not DIA_MINUSCULA.match(s):
                titulo.append(desespacia(s)[0])
                j += 1
            else:
                break
        partes.append((ident, ' '.join(titulo), n + 1, fin))
    return partes


# --------------------------------------------------------------------------
# el bloque: un encabezado y lo que viene debajo
# --------------------------------------------------------------------------

class Bloque:
    def __init__(self, titulo, clase, linea, pagina, pdf):
        self.titulo = titulo        # las líneas del encabezado
        self.clase = clase          # 'mayus' | 'dia' | 'marca' | 'sub' | None
        self.linea = linea          # dónde empieza, en el volcado
        self.pagina = pagina        # la del libro, si un encabezado la dio
        self.pdf = pdf              # la física del PDF, siempre
        self.cuerpo = []            # [(número de línea, texto)]

    @property
    def tiene_piezas(self):
        return any(ROTULO.match(t) for _, t in self.cuerpo)

    @property
    def nombre(self):
        return ' · '.join(self.titulo)


def bloques_de(lineas, pdfs, desde, hasta, inf, formularios=True):
    """Parte el tramo en bloques: cada encabezado abre uno.

    Un encabezado puede ocupar varias líneas seguidas —el santoral titula en
    dos: «Ss. Basilii Magni et Gregorii Nazianzeni, / episcoporum et Ecclesiæ
    doctorum»—, y eso se resuelve mirando si la línea siguiente es también
    encabezado.
    """
    def siguiente_con_texto(k):
        for j in range(k + 1, min(hasta, k + 4)):
            t = lineas[j].replace('\f', '').strip()
            if t:
                return t
        return None

    bloques, pagina, i = [], None, desde
    while i < hasta:
        s = lineas[i].replace('\f', '').strip()
        if not s:
            if bloques and bloques[-1].cuerpo:
                bloques[-1].cuerpo.append((i + 1, ''))
            i += 1
            continue
        p = pagina_de(s)
        if p is not None:
            pagina = p
            i += 1
            continue
        if misal.es_nota(s):
            i += 1
            continue

        clase = clase_de(s, siguiente_con_texto(i), formularios)
        if clase:
            texto, reconocida = desespacia(s)
            if not reconocida:
                inf.di(f'  línea {i+1}: mayúsculas espaciadas sin entrada en '
                       f'la tabla ESPACIADAS: «{texto}»')
            # `-layout` deja huecos de veinte espacios dentro de un rótulo
            # partido en dos columnas: se juntan
            titulo, arranca = [re.sub(r'\s{2,}', ' ', texto)], i
            i += 1
            while i < hasta and clase == 'mayus':
                t = lineas[i].replace('\f', '').strip()
                if not t:
                    break
                if pagina_de(t) is not None:
                    pagina = pagina_de(t)
                    i += 1
                    continue
                # un rótulo con prefijo propio —«21. PRO PATRIA VEL
                # CIVITATE» debajo de «II. PRO CIRCUMSTANTIIS PUBLICIS»— no
                # es la segunda línea del de arriba: es el siguiente, y
                # pegarlos haría de dos encabezados uno
                if es_encabezado_mayusculas(t) and hondura_de(t) is None:
                    titulo.append(desespacia(t)[0])
                    i += 1
                    continue
                break
            bloques.append(Bloque(titulo, clase, arranca + 1, pagina,
                                  pdfs[arranca]))
            continue

        if not bloques:
            bloques.append(Bloque([], None, i + 1, pagina, pdfs[i]))
        bloques[-1].cuerpo.append((i + 1, s))
        i += 1
    return bloques


# --------------------------------------------------------------------------
# el formulario: las piezas de un bloque
# --------------------------------------------------------------------------

def piezas_del(bloque):
    """Las piezas, las rúbricas y las referencias de un bloque.

    Devuelve un diccionario. Las antífonas no tienen conclusión, así que se
    cierran en el rótulo siguiente; las oraciones se cierran en la suya, y lo
    que viene detrás es rúbrica.

    Lo que hay entre el título y el primer rótulo —el grado, el color, una
    nota de uso— va al `preambulo`, que se guarda entero: nada se tira.
    """
    piezas = OrderedDict()
    rubricas, prefacios, comunes, preambulo = [], [], [], []
    propios = []
    grado = None
    gloria = credo = None
    dentro = None       # el prefacio propio que se está copiando
    actual = None       # el diccionario donde se escribe ahora
    raiz = None         # la pieza a la que colgar una alternativa
    cerrada = False     # la oración en curso ya dio su conclusión

    def abre(nombre, cita, linea, de, rubrica=None):
        """Abre una pieza, o una alternativa si ya estaba abierta.

        `de` dice de dónde sale —`'rotulo'` si el libro la volvió a rotular,
        `'vel'` si la abrió un «Vel:»—, y con eso el informe puede cuadrar
        los rótulos contados contra los textos guardados.
        """
        nonlocal actual, raiz, cerrada
        if nombre in piezas:
            alt = {'cita': cita or None, 'texto': [], 'linea': linea,
                   'f': de, 'n': rubrica}
            piezas[nombre]['alt'].append(alt)
            actual = alt
        else:
            piezas[nombre] = {'cita': cita or None, 'texto': [], 'alt': [],
                              'linea': linea, 'f': de, 'n': rubrica}
            actual = piezas[nombre]
        raiz = piezas[nombre]
        cerrada = False

    for n, t in bloque.cuerpo:
        if dentro is not None:
            if t:
                dentro['texto'].append(t)
                if FIN_PREFACIO.match(t):
                    propios.append(dentro)
                    dentro = None
            continue

        if not t:
            if actual is not None and not cerrada and actual['texto']:
                actual['texto'].append('')
            continue

        if DIALOGO_PREFACIO.match(t):
            # el título es la última referencia «Præfatio…» que se vio
            dentro = {'titulo': prefacios[-1] if prefacios else None,
                      'texto': [t], 'linea': n}
            continue
        if TONO.match(t) and prefacios:
            rubricas.append(t)
            continue

        m = ROTULO.match(t)
        if m:
            abre(NOMBRE_DE[m.group(2)], m.group(3).strip(), n, 'rotulo',
                 int(m.group(1)) if m.group(1) else None)
            continue

        m = ALTERNATIVA.match(t)
        if m:
            if raiz is None:
                preambulo.append((n, t))
                continue
            alt = {'cita': m.group(1).strip() or None, 'texto': [],
                   'linea': n, 'f': 'vel', 'n': None}
            raiz['alt'].append(alt)
            actual, cerrada = alt, False
            continue

        if PREFACIO_REF.match(t):
            prefacios.append(t)
            continue
        if COMUN_REF.match(t):
            comunes.append(t)
            continue
        if GLORIA.match(t):
            gloria = not t.startswith('Non')
            continue
        if CREDO.match(t):
            credo = not t.startswith('Non')
            continue

        if actual is None:
            g = t.lower().strip('. ')
            if g in GRADOS:
                grado = GRADOS[g]
            elif COLOR.match(t):
                rubricas.append(t)
            else:
                preambulo.append((n, t))
            continue
        if cerrada:
            rubricas.append(t)
            continue

        actual['texto'].append(t)
        if CONCLUSION.match(t):
            cerrada = True

    for p in piezas.values():
        limpia(p['texto'])
        for a in p['alt']:
            limpia(a['texto'])
        if not p['alt']:
            del p['alt']
    if dentro is not None:        # se quedó abierto: lo dice el informe
        dentro['incompleto'] = True
        propios.append(dentro)
    return {'piezas': piezas, 'rubricas': rubricas, 'prefacio': prefacios,
            'comun': comunes, 'gloria': gloria, 'credo': credo,
            'grado': grado, 'preambulo': preambulo, 'propios': propios}


def formularios_de(ident, titulo_parte, bloques, formularios,
                   sin_piezas, preambulos, rubricas_vistas):
    """Los formularios de una parte, cada uno con la ruta de secciones que lo
    cobija y el encabezado mayor del que depende.

    `ruta` son las secciones abiertas, por hondura de prefijo: «COMMUNE
    MARTYRUM» > «I. Tempore paschali» > «A. Pro pluribus martyribus». `bajo`
    es el último encabezado en mayúsculas que **sí** era formulario —«DOMINICA
    II ADVENTUS»—, que es lo que da la semana a una feria.
    """
    ruta, bajo = OrderedDict(), None
    for b in bloques:
        cuerpo = [t for _, t in b.cuerpo if t]

        propia = hondura_de(b.titulo[0]) if b.titulo else None

        def abre_seccion(h):
            nonlocal bajo
            for k in list(ruta):
                if HONDURA[k] >= HONDURA[h]:
                    del ruta[k]
            ruta[h] = b.nombre
            if h == 'raiz':
                bajo = None

        if not b.tiene_piezas:
            if not b.titulo:
                continue
            # un santo que lo toma todo del común no imprime ninguna pieza,
            # sólo la referencia: ése sí es formulario
            if not any(COMUN_REF.match(t) for t in cuerpo):
                if b.clase in ('mayus', 'sub'):
                    abre_seccion(propia or 'raiz')
                else:
                    bajo = b.nombre
                if cuerpo:
                    sin_piezas.append((b.linea, b.nombre, cuerpo[:3]))
                continue

        d = piezas_del(b)
        for r in d['rubricas']:
            rubricas_vistas[r[:70]] += 1
        preambulos += [(b.linea, b.nombre) + s for s in d['preambulo']]

        md = DIA_SANTORAL.match(b.titulo[0])
        dia = ({'mes': MESES[md.group(2)], 'dia': int(md.group(1))}
               if md and md.group(2) in MESES else None)

        grado = d['grado']
        for t in b.titulo[1:]:
            g = t.lower().strip('. ')
            if g in GRADOS and grado is None:
                grado = GRADOS[g]

        # Un formulario con prefijo propio —«26. PRO HUMANO LABORE»— cuelga
        # de lo que esté por encima de su nivel, nunca de su hermana. Si hay
        # `bajo`, él manda y basta: es el domingo del que pende la feria, y
        # es lo más específico que hay.
        arriba = [v for k, v in ruta.items()
                  if propia is None or HONDURA[k] < HONDURA[propia]]
        if md:
            # el santoral ya lleva la fecha en el título: no cuelga de nada,
            # y lo que ayuda a leer el informe es el nombre del santo, que
            # el libro pone en la línea de debajo
            contexto = []
            if cuerpo and not ROTULO.match(cuerpo[0])                     and cuerpo[0].lower().strip('. ') not in GRADOS:
                b.titulo = b.titulo + [cuerpo[0]]
        elif bajo and b.clase in ('dia', 'marca'):
            # `bajo` es lo más cercano y lo más específico: el domingo del
            # que pende la feria, y basta él. Un rótulo en mayúsculas, en
            # cambio, no cuelga del anterior: es su hermano.
            contexto = [bajo]
        else:
            contexto = arriba
        base = slug(' '.join(filter(None, contexto + [b.nombre])))
        ident_f = f'{ident}/{base}' if base else f'{ident}/l{b.linea}'
        if ident_f in formularios:
            k = 2
            while f'{ident_f}~{k}' in formularios:
                k += 1
            ident_f = f'{ident_f}~{k}'

        formularios[ident_f] = {
            'parte': titulo_parte, 'ruta': list(ruta.values()), 'bajo': bajo,
            'titulo': b.titulo, 'grado': grado, 'dia': dia,
            'pagina': b.pagina, 'pdf': b.pdf, 'linea': b.linea,
            'piezas': d['piezas'], 'rubricas': d['rubricas'],
            'prefacio': d['prefacio'], 'comun': d['comun'],
            'gloria': d['gloria'], 'credo': d['credo'],
            'preambulo': [t for _, t in d['preambulo']],
            'propios': d['propios'],
        }
        # `bajo` sólo lo pone un encabezado sin prefijo: es el mecanismo del
        # temporal, donde la feria cuelga del domingo. Entre hermanas
        # numeradas —«10. PRO LAICIS», «11. IN ANNIVERSARIIS MATRIMONII»— no
        # hay dependencia, y encadenarlas haría nombres falsos.
        if b.clase == 'mayus' and not md and propia is None:
            bajo = b.nombre
        elif propia is not None:
            # también las secciones que resultaron ser formulario mandan en
            # la ruta: si no, la hermana siguiente heredaría su nombre
            abre_seccion(propia)
            bajo = None


# --------------------------------------------------------------------------
# las partes que no son formularios
# --------------------------------------------------------------------------

def prefacios_del(bloques):
    """Los prefacios del cuerpo de prefacios: título, epígrafe, la rúbrica
    numerada que dice cuándo se usa, y el texto desde el diálogo."""
    salida = OrderedDict()
    for b in bloques:
        if not PREFACIO_TITULO.match(b.titulo[0] if b.titulo else ''):
            continue
        titulo = ' '.join(b.titulo)
        epigrafe, n, rubrica, texto = None, None, [], []
        for _, t in b.cuerpo:
            if not t:
                if texto:
                    texto.append('')
                continue
            m = NUMERADA.match(t)
            if m and n is None and not texto:
                n = int(m.group(1))
                rubrica.append(m.group(2))
                continue
            if texto or t.startswith('V.'):
                texto.append(t)
            elif n is not None:
                rubrica.append(t)
            elif epigrafe is None:
                epigrafe = t
            else:
                epigrafe += ' ' + t
        ident = slug(titulo)
        if ident in salida:
            k = 2
            while f'{ident}-{k}' in salida:
                k += 1
            ident = f'{ident}-{k}'
        salida[ident] = {'titulo': titulo, 'epigrafe': epigrafe, 'n': n,
                         'rubrica': rubrica, 'texto': limpia(texto),
                         'juego': 'tiempo' if n is not None else 'comun',
                         'pagina': b.pagina, 'linea': b.linea}
    return salida


def numeradas_de(lineas, desde, hasta):
    """Las rúbricas numeradas de un tramo: `{n: {...}}`.

    Es lo que hace que el Ordo Missæ bilingüe no necesite costura: el número
    de rúbrica dice lo mismo aquí y en el Ordinario de México.
    """
    rub, n, pagina = OrderedDict(), None, None
    for i in range(desde, hasta):
        s = lineas[i].replace('\f', '').strip()
        if not s:
            if n is not None and rub[n]['lineas']:
                rub[n]['lineas'].append('')
            continue
        p = pagina_de(s)
        if p is not None:
            pagina = p
            continue
        if misal.es_nota(s):
            continue
        m = NUMERADA.match(s)
        if m:
            n = int(m.group(1))
            if n not in rub:
                rub[n] = {'n': n, 'lineas': [], 'pagina': pagina,
                          'linea': i + 1}
            if m.group(2):
                rub[n]['lineas'].append(m.group(2))
            continue
        if n is not None:
            rub[n]['lineas'].append(s)
    for r in rub.values():
        limpia(r['lineas'])
    return rub


PLEGARIA = re.compile(r'^(PREX EUCHARISTICA|PRECES EUCHARISTICÆ)\b')
ROMANO_SOLO = re.compile(r'^([IVX]{1,4})$')


def plegarias_en(lineas, desde, hasta, inf):
    """Las plegarias eucarísticas de un tramo.

    El Misal las rotula de tres maneras y las tres hacen falta:

      · «PREX EUCHARISTICA I / seu CANON ROMANUS», que es una plegaria;
      · «PRECES EUCHARISTICÆ / “ DE RECONCILIATIONE ”» y debajo «I» y «II»,
        que son dos;
      · «PREX EUCHARISTICA QUÆ IN MISSIS / PRO VARIIS NECESSITATIBUS /
        ADHIBERI POTEST» y debajo «I» a «IV» con su epígrafe, que son cuatro.

    De ahí que el rótulo en mayúsculas abra **familia** y el romano solo abra
    plegaria dentro de ella. La familia sin romanos debajo es ella misma una
    plegaria, y así salen las seis del cuerpo y las seis del apéndice.
    """
    salida = OrderedDict()
    rub_familia = {}
    familia, actual = None, None
    i = desde
    while i < hasta:
        t = lineas[i].replace('\f', '').strip()
        if not t or pagina_de(t) is not None or misal.es_nota(t):
            if actual and actual['texto']:
                actual['texto'].append('')
            i += 1
            continue

        if PLEGARIA.match(t) and es_encabezado_mayusculas(t):
            # el rótulo puede seguir en las líneas de mayúsculas de debajo,
            # con una línea en blanco entre medias: «PREX EUCHARISTICA /
            # (blanco) / “ DE RECONCILIATIONE ”»
            titulo, j, blancos = [t], i + 1, 0
            while j < hasta and blancos <= 1:
                u = lineas[j].replace('\f', '').strip()
                if not u:
                    blancos += 1
                    j += 1
                    continue
                if (es_encabezado_mayusculas(u) and not PLEGARIA.match(u)
                        and not ROMANO_SOLO.match(u)):
                    titulo.append(u)
                    j, blancos = j + 1, 0
                    continue
                break
            familia = ' '.join(titulo)
            actual = nueva_plegaria(salida, familia, i + 1)
            i = j
            continue

        if ROMANO_SOLO.match(t) and familia:
            # un romano solo debajo de una familia abre plegaria. Lo que la
            # familia llevaba escrito es su rúbrica de uso —cuándo se puede
            # usar— y pasa a las plegarias que cuelgan de ella, porque es de
            # ellas de lo que habla.
            if actual is not None and actual['titulo'] == familia:
                rub_familia[familia] = limpia(actual['texto'])
                del salida[actual['id']]
            actual = nueva_plegaria(salida, f'{familia} {t}', i + 1)
            actual['rubrica'] = rub_familia.get(familia, [])
            i += 1
            continue

        if actual is None:
            i += 1
            continue
        actual['texto'].append(t)
        i += 1

    for p in salida.values():
        limpia(p['texto'])
        del p['id']
    return salida


def nueva_plegaria(salida, titulo, linea):
    ident = slug(titulo)
    if ident in salida:
        k = 2
        while f'{ident}-{k}' in salida:
            k += 1
        ident = f'{ident}-{k}'
    salida[ident] = {'id': ident, 'titulo': titulo, 'texto': [],
                     'rubrica': [], 'linea': linea}
    return salida[ident]


def bendiciones_de(lineas, desde, hasta):
    """Las bendiciones solemnes, que el Misal numera dos veces.

    Primero por secciones en romanos —«I. In celebrationibus de tempore»,
    «II. De Sanctis», «III. In celebrationibus variis»— y dentro de cada una
    con cifra y título: «1. In Adventu», «2. In Nativitate Domini». La
    rúbrica de uso que abre la sección va aparte, en `rubrica`.
    """
    seccion = re.compile(r'^([IVX]{1,4})\.\s+(\S.{0,60})$')
    item = re.compile(r'^(\d{1,2})\.\s+(\S.{0,60})$')
    salida, rubrica, actual, sec = [], [], None, None
    # la numeración manda: un «9. Per annum, I» es el noveno porque va detrás
    # del octavo, y así una línea de texto que empiece por una cifra no
    # puede abrir una bendición que no toca
    siguiente = 1
    for i in range(desde, hasta):
        t = lineas[i].replace('\f', '').strip()
        if not t:
            if actual:
                actual['texto'].append('')
            continue
        if pagina_de(t) is not None:
            continue
        m = seccion.match(t)
        if m and not re.search(r'[.,;:]', m.group(2)):
            sec, actual = t, None
            continue
        m = item.match(t)
        if m and int(m.group(1)) == siguiente:
            actual = {'n': siguiente, 'seccion': sec,
                      'titulo': m.group(2).strip(), 'texto': [],
                      'linea': i + 1}
            salida.append(actual)
            siguiente += 1
            continue
        (actual['texto'] if actual else rubrica).append(t)
    for b in salida:
        limpia(b['texto'])
    return limpia(rubrica), salida


def super_populum_de(lineas, desde, hasta):
    """Las oraciones sobre el pueblo: numeradas en la misma línea del texto
    («1. Esto, Dómine, propítius plebi tuæ,»), y se cierran en su conclusión,
    como cualquier oración del Misal."""
    item = re.compile(r'^(\d{1,3})\.\s+(\S.*)$')
    salida, rubrica, actual = [], [], None
    for i in range(desde, hasta):
        t = lineas[i].replace('\f', '').strip()
        if not t or pagina_de(t) is not None:
            continue
        m = item.match(t)
        if m:
            actual = {'n': int(m.group(1)), 'texto': [m.group(2).strip()],
                      'linea': i + 1}
            salida.append(actual)
            continue
        if actual and not CONCLUSION.match(actual['texto'][-1]):
            actual['texto'].append(t)
        elif actual is None:
            rubrica.append(t)
    return limpia(rubrica), salida


# --------------------------------------------------------------------------
# la pasada
# --------------------------------------------------------------------------

def main():
    inf = Informe(QA, 'Fase 1 — el Misal Romano 2002 en latín')
    if not os.path.exists(PDF):
        sys.exit(f'falta {PDF}')
    lineas = misal.texto_de(PDF, 'latino')
    pdfs = misal.paginas_de(lineas)
    inf.di(f'fuente: {os.path.basename(PDF)}  ({len(lineas)} líneas de '
           f'texto, {pdfs[-1]} páginas)')

    inf.titulo('Las partes del libro')
    partes = partes_del(lineas, inf)
    for ident, titulo, d, h in partes:
        inf.di(f'  {ident:16s} {d:6d}-{h:<6d} p. {pdfs[d]:4d}  {titulo}')

    cuerpo_d = partes[0][2] - 1 if partes else 0
    cuerpo_h = next((d - 1 for i, _, d, _ in partes if i == 'indices'),
                    len(lineas))
    crudas = misal.texto_de(PDF, 'latino_raw', layout=False)
    cr_d = next((i for i, l in enumerate(crudas)
                 if l.strip() == 'PROPRIUM DE TEMPORE'), 0)
    cr_h = next((i for i, l in enumerate(crudas)
                 if i > cr_d and l.strip().replace(' ', '') == 'INDICES'),
                len(crudas))
    lineas, movidas, sin_emparejar = misal.repara_desplazadas(
        lineas, crudas, cuerpo_d, cuerpo_h, cr_d, cr_h)

    inf.titulo('Palabras que la extracción deja en el margen')
    inf.di('  Con `-layout`, pdftotext deja a veces una palabra en el margen')
    inf.di('  derecho de la línea de arriba, y la oración de debajo se queda')
    inf.di('  sin su última palabra. No se adivina dónde va: se compara con')
    inf.di('  el volcado `-raw` del mismo PDF, que trae el orden bueno, y se')
    inf.di('  mueve a donde él la pone.')
    inf.di('')
    inf.di(f'  palabras movidas: {len(movidas)}')
    for origen, destino, texto in movidas:
        inf.di(f'      «{texto}»: de la línea {origen} a la {destino}')
    pendientes = [t for t in sin_emparejar if t[0] != 'espaciada']
    espaciadas = [t for t in sin_emparejar if t[0] == 'espaciada']
    inf.di('')
    inf.di('  trozos de una letra, que son de las rúbricas espaciadas y se')
    inf.di(f'  recomponen en el paso siguiente: {len(espaciadas)}')
    inf.di(f'  trozos que no se pudieron emparejar: {len(pendientes)}')
    for que, donde, texto in pendientes:
        inf.di(f'      [{que}] línea {donde}: {texto}')
    inf.di('')
    inf.di('  Los rótulos de parte que salen como «sin pareja» no son un')
    inf.di('  problema: `-layout` los imprime dos veces —una por la cabecera')
    inf.di('  de página— y se quedan donde están, que es lo que hace falta')
    inf.di('  para partir el libro.')

    lineas, sueltas = misal.rehace_sueltas(lineas, cuerpo_d, cuerpo_h)
    inf.titulo('Rúbricas espaciadas letra a letra')
    inf.di('  El PDF las trae con un espacio de verdad entre cada letra y')
    inf.di('  los de palabra perdidos. Se recomponen con el vocabulario del')
    inf.di('  propio libro; lo que quede dudoso se nombra aquí.')
    inf.di('')
    dudosas = [c for c in sueltas if c[3] and c[3] != ['(de tabla)']]
    de_tabla = [c for c in sueltas if c[3] == ['(de tabla)']]
    inf.di(f'  líneas recompuestas: {len(sueltas)}')
    inf.di(f'    de la tabla SUELTAS, a mano: {len(de_tabla)}')
    inf.di(f'    con algún corte dudoso: {len(dudosas)}')
    inf.di('')
    for n, cruda, rehecha, señas in sueltas:
        if not rehecha:
            continue
        marca = f'   ← {", ".join(señas)}' if señas else ''
        inf.di(f'  línea {n}: {rehecha}{marca}')
    if dudosas:
        inf.di('')
        inf.di('  Las dudosas, con su forma cruda para poder cotejarlas:')
        for n, cruda, rehecha, señas in dudosas:
            inf.di(f'    línea {n}  [{", ".join(señas)}]')
            inf.di(f'      cruda  : {cruda[:150]}')
            inf.di(f'      rehecha: {rehecha}')

    formularios = OrderedDict()
    prefacios = OrderedDict()
    ordo = OrderedDict()
    plegarias = OrderedDict()
    bendiciones, super_populum = [], []
    rub_bend, rub_pop = [], []
    sin_piezas, preambulos = [], []
    rubricas_vistas = Counter()

    for ident, titulo, desde, hasta in partes:
        if ident == 'indices':
            continue
        bloques = bloques_de(lineas, pdfs, desde, hasta, inf,
                             ident in CON_FORMULARIOS)

        if ident in CON_FORMULARIOS:
            formularios_de(ident, titulo, bloques, formularios,
                           sin_piezas, preambulos, rubricas_vistas)

        elif ident in ('ordo', 'ordo_unus'):
            # el cuerpo de prefacios vive dentro de la parte del Ordo
            prefacios.update(prefacios_del(bloques))
            if ident == 'ordo':
                # la numeración 1-146 no se acaba con la parte: sigue por los
                # prefacios (33-82) y por las plegarias (83-123) y cierra con
                # el rito de comunión (124-146). Es una sola serie, y es la
                # que numera igual el Ordinario de México.
                fin = next((d - 1 for i, _, d, _ in partes
                            if i == 'ordo_unus'), hasta)
                ordo[ident] = numeradas_de(lineas, desde, fin)
            else:
                ordo[ident] = numeradas_de(lineas, desde, hasta)

        elif ident == 'preces':
            # Tres cosas distintas viven en esta parte y cada una se lee a su
            # modo: las plegarias eucarísticas, las bendiciones solemnes y
            # las oraciones sobre el pueblo. Los tramos se marcan por rótulo.
            def busca(rotulo, dd=desde):
                return next((i for i in range(dd, hasta)
                             if lineas[i].replace('\f', '').strip() == rotulo),
                            None)
            n_bend = busca('BENEDICTIONES SOLLEMNES')
            n_pop = busca('ORATIONES SUPER POPULUM')
            n_fin = busca('CANTUS AD PRECEM EUCHARISTICAM') or hasta

            prefacios.update(prefacios_del(bloques))
            # las plegarias acaban donde empieza el rito de comunión, que el
            # Ordo rotula en minúsculas y no en mayúsculas
            n_com = busca('Ritus communionis') or (n_bend or hasta)
            plegarias.update(plegarias_en(lineas, desde, n_com, inf))
            if n_bend is not None:
                rub_bend, bendiciones = bendiciones_de(
                    lineas, n_bend + 1, n_pop if n_pop else n_fin)
            if n_pop is not None:
                rub_pop, super_populum = super_populum_de(
                    lineas, n_pop + 1, n_fin)

        elif ident == 'apendice_ordo':
            # las de la reconciliación y la de diversas necesidades
            plegarias.update(plegarias_en(lineas, desde, hasta, inf))

    # ---- informe ---------------------------------------------------------

    inf.titulo('Formularios')
    inf.di(f'  total: {len(formularios)}')
    cuenta = Counter(k.split('/')[0] for k in formularios)
    for parte in [i for i, _, c in PARTES if c]:
        inf.di(f'    {parte:16s} {cuenta.get(parte, 0)}')

    inf.di('')
    inf.di('  Las piezas, contra lo que el rótulo cuenta en el cuerpo del')
    inf.di('  libro: la cuenta de la izquierda son los textos guardados —la')
    inf.di('  pieza más sus alternativas—, y han de cuadrar. La columna de')
    inf.di('  formularios dice en cuántos aparece la pieza, que es menos')
    inf.di('  porque un formulario puede traer tres colectas.')
    inf.di('')
    inf.di(f'    {"pieza":12s} {"de rót.":>7s} {"rótulos":>8s}  '
           f'{"formularios":>11s} {"de Vel:":>8s}')
    cuadran = True
    for n, rotulo in PIEZAS:
        de_rotulo = de_vel = 0
        for f in formularios.values():
            p = f['piezas'].get(n)
            if not p:
                continue
            de_rotulo += 1 if p['f'] == 'rotulo' else 0
            de_vel += 1 if p['f'] == 'vel' else 0
            for a in p.get('alt', []):
                if a['f'] == 'rotulo':
                    de_rotulo += 1
                else:
                    de_vel += 1
        enf = sum(1 for f in formularios.values() if n in f['piezas'])
        # el salto de página va dentro de la línea, así que la cuenta cruda
        # tiene que normalizar igual que el troceo, o no cuadran nunca
        # las erratas del libro cuentan para su pieza, o la cuenta cruda no
        # cuadraría con la guardada por un «Super oblate» mal impreso
        formas = [rotulo] + [mal for mal, bien in ERRATAS.items()
                             if bien == rotulo]
        patron = re.compile(r'^(?:\d{1,3}\.\s+)?(?:'
                            + '|'.join(re.escape(f) for f in formas) + ')')
        crudas = sum(
            1 for i, ln in enumerate(lineas)
            if cuerpo_d <= i < cuerpo_h
            and patron.match(ln.replace('', '').strip()))
        marca = '' if de_rotulo == crudas else '   ← ¡NO CUADRA!'
        if de_rotulo != crudas:
            cuadran = False
        inf.di(f'    {n:12s} {de_rotulo:7d} {crudas:8d}  {enf:11d}'
               f' {de_vel:8d}{marca}')
    vel = sum(1 for i, ln in enumerate(lineas)
              if cuerpo_d <= i < cuerpo_h
              and ln.replace('', '').strip().startswith('Vel:'))
    alt = sum(len(p.get('alt', [])) for f in formularios.values()
              for p in f['piezas'].values())
    inf.di('')
    inf.di(f'    «Vel:» en el cuerpo: {vel}')
    inf.di(f'    alternativas colgadas de una pieza: {alt}')
    inf.di('    (la diferencia son los «Vel:» del Ordo y de las plegarias, '
           'que no cuelgan de ninguna pieza, y los rótulos repetidos dentro '
           'de un mismo formulario, que también son alternativa)')
    inf.di('')
    inf.di(f'  ¿cuadran todos los rótulos del cuerpo? '
           f'{"sí" if cuadran else "NO — mirar arriba"}')

    inf.titulo('Formularios con alguna pieza ausente')
    inf.di('  Las cinco piezas del formulario completo son entrada, colecta,')
    inf.di('  ofrendas, comunión y poscomunión. Que falten no es siempre un')
    inf.di('  error: el santo que lo toma del común imprime sólo su colecta.')
    inf.di('')
    faltan = []
    for k, f in formularios.items():
        falta = [n for n in OBLIGATORIAS if n not in f['piezas']]
        if falta:
            faltan.append((k, f, falta))
    solo_colecta = [x for x in faltan
                    if set(x[2]) == set(OBLIGATORIAS) - {'colecta'}]
    inf.di(f'  con alguna ausente: {len(faltan)} de {len(formularios)}')
    inf.di(f'    de ellos, sólo con colecta: {len(solo_colecta)}')
    inf.di(f'    con referencia explícita al común: '
           f'{sum(1 for x in faltan if x[1]["comun"])}')
    inf.di('')
    for k, f, falta in faltan:
        if set(falta) == set(OBLIGATORIAS) - {'colecta'}:
            continue
        inf.di(f'  {k}')
        inf.di(f'      p. PDF {f["pdf"]}, línea {f["linea"]}: '
               f'{" · ".join(f["titulo"])}')
        inf.di(f'      falta: {", ".join(falta)}'
               + (f'   [común: {f["comun"][0][:50]}]' if f['comun'] else ''))

    # los prefacios propios, que viven dentro de su formulario, entran al
    # mismo diccionario con su juego: así la app no aprende dos sistemas
    for k, f in formularios.items():
        for pr in f['propios']:
            titulo = re.sub(r'^\d{1,3}\.\s+', '', pr['titulo'] or '')
            titulo = titulo.strip(' .')
            ident = slug(titulo) or f'propio-{pr["linea"]}'
            if ident in prefacios:
                prefacios[ident].setdefault('tambien_en', []).append(k)
                continue
            prefacios[ident] = {
                'titulo': titulo, 'epigrafe': None, 'n': None,
                'rubrica': [], 'texto': pr['texto'], 'juego': 'propio',
                'de': k, 'pagina': f['pagina'], 'linea': pr['linea'],
            }

    inf.titulo('Erratas del Misal admitidas al parsear')
    inf.di('  Rótulos que el libro imprime mal y que se aceptan como lo que')
    inf.di('  son. Si una deja de aparecer, el volcado cambió.')
    inf.di('')
    for mal, bien in ERRATAS.items():
        donde = [(i + 1, pdfs[i]) for i in range(cuerpo_d, cuerpo_h)
                 if lineas[i].replace('', '').strip().startswith(mal)]
        inf.di(f'  «{mal}» → «{bien}»: {len(donde)} vez/veces')
        for n, pg in donde:
            inf.di(f'      línea {n}, p. PDF {pg}')

    inf.titulo('Prefacios')
    por_juego = Counter(p['juego'] for p in prefacios.values())
    inf.di(f'  total: {len(prefacios)}')
    inf.di(f'      del cuerpo de prefacios (nn. 33-82): '
           f'{por_juego["tiempo"]}')
    inf.di(f'      propios, hallados dentro de un formulario: '
           f'{por_juego["propio"]}')
    ns = sorted(p['n'] for p in prefacios.values() if p['n'])
    if ns:
        inf.di(f'  numeración del cuerpo: de {ns[0]} a {ns[-1]}; huecos: '
               + str([n for n in range(ns[0], ns[-1] + 1) if n not in ns]))
    sin_texto = [k for k, p in prefacios.items() if len(p['texto']) < 10]
    inf.di(f'  con menos de diez líneas de texto: {len(sin_texto)}'
           + (f'  → {", ".join(sin_texto)}' if sin_texto else ''))
    inf.di('')
    inf.di('  El juego castellano del Ordinario de México tiene 67 y este')
    inf.di('  tiene 50 comunes: la tabla de correspondencia entre los dos la')
    inf.di('  hace la fase 2, y los diecisiete castellanos sin pareja los')
    inf.di('  nombra su informe uno a uno.')
    inf.di('')
    for k, p in prefacios.items():
        inf.di(f'  {k}   [{p["juego"]}]')
        inf.di(f'      {p["titulo"]}'
               + (f'  —  {p["epigrafe"]}' if p['epigrafe'] else ''))
        inf.di(f'      n. {p["n"]}, línea {p["linea"]}, '
               f'{len(p["texto"])} líneas')
        if p.get('de'):
            inf.di(f'      dentro de {p["de"]}')
        if p.get('tambien_en'):
            inf.di(f'      el mismo texto, en: '
                   f'{", ".join(p["tambien_en"])}')

    inf.titulo('Prefacios que los días citan y no se hallaron')
    inf.di('  Cada día cita el prefacio que le toca. Aquí se comprueba que')
    inf.di('  la cita tiene a quién referirse: contra los 50 del cuerpo y')
    inf.di('  contra los 52 propios cosechados. Lo que quede sin pareja o')
    inf.di('  es una referencia a un juego que el Misal no imprime, o es un')
    inf.di('  prefacio propio que se escapó, y hay que mirarlo.')
    inf.di('')
    citados = Counter()
    for f in formularios.values():
        for p in f['prefacio']:
            citados[cita_limpia(p)] += 1
    # el título del prefacio, en forma canónica y sin el «PRÆFATIO» de
    # cabecera, que la cita no repite igual
    # El día cita el prefacio de tres maneras: por su título («Præfatio I de
    # Adventu»), por su epígrafe («Præfatio: De Christo luce», que es el
    # epígrafe del I de Navidad) y por familia, sin número («Præfatio
    # paschalis», que vale por cualquiera de los cinco). Las tres se
    # resuelven, y cada una se cuenta aparte.
    por_titulo, por_epigrafe = {}, {}
    for k, p in prefacios.items():
        t = re.sub(r'^PR[ÆA]E?FATIO\s*:?\s*', '', p['titulo'],
                   flags=re.IGNORECASE)
        for forma in (t, t.replace(':', '')):
            por_titulo.setdefault(clave(forma), k)
        if p['epigrafe']:
            por_epigrafe.setdefault(clave(p['epigrafe']), k)

    exactas, epigrafes, familias, sueltas_pref = [], [], [], []
    for c, n in citados.most_common():
        cl = clave(c)
        if not cl:
            continue
        if cl in por_titulo:
            exactas.append((c, n, por_titulo[cl]))
        elif cl in por_epigrafe:
            epigrafes.append((c, n, por_epigrafe[cl]))
        else:
            cand = [k for k in list(por_titulo) + list(por_epigrafe)
                    if cl in k or k in cl]
            if cand:
                familias.append((c, n, len(cand)))
            else:
                sueltas_pref.append((c, n))
    inf.di(f'  referencias distintas citadas por los días: {len(citados)}')
    inf.di(f'  resueltas por título: {len(exactas)}')
    inf.di(f'  resueltas por epígrafe: {len(epigrafes)}')
    inf.di(f'  resueltas como familia: {len(familias)}')
    inf.di(f'  sin resolver: {len(sueltas_pref)}')
    inf.di('')
    inf.di('  Por epígrafe —el día nombra el epígrafe, no el título—:')
    for c, n, k in epigrafes:
        inf.di(f'  {n:4d} × {c}   → {k}')
    inf.di('')
    inf.di('  Por familia, con cuántos prefacios caben en cada una:')
    for c, n, cuantos in familias:
        inf.di(f'  {n:4d} × {c}   → {cuantos} prefacio(s)')
    inf.di('')
    inf.di('  Las que no resuelven, y por qué: «propria» y «et')
    inf.di('  intercessiones propriæ» no nombran a nadie —quieren decir «el')
    inf.di('  de esta misa», y lo resuelve el contexto, no el nombre—;')
    inf.di('  «defunctorum» es como el Misal escribe alguna vez «de')
    inf.di('  defunctis»; «de unitate christianorum» y «de Pentecoste ut in')
    inf.di('  Missa sequenti» remiten a otro formulario. Ninguna es texto')
    inf.di('  perdido: son maneras de citar que la fase 5 resuelve con el')
    inf.di('  formulario delante.')
    inf.di('')
    for c, n in sueltas_pref:
        inf.di(f'  {n:4d} × {c}')

    inf.titulo('Encabezados con cuerpo pero sin piezas')
    inf.di('  Son secciones con una nota debajo, o un formulario que el')
    inf.di('  parseo no supo leer. Si aquí aparece el nombre de un santo o de')
    inf.di('  un domingo, hay un formulario perdido y hay que mirarlo.')
    inf.di('')
    for linea, tit, cuerpo in sin_piezas:
        inf.di(f'  línea {linea}: {tit}')
        for c in cuerpo:
            inf.di(f'      {c[:95]}')

    inf.titulo('Preámbulos: lo que va entre el título y la primera pieza')
    inf.di('  El grado y el color se reconocen y se guardan en su campo. Lo')
    inf.di('  que sale aquí es lo demás: notas de uso del formulario. Se')
    inf.di('  guarda entero en el campo «preambulo», no se tira; se lista')
    inf.di('  para que se vea si alguna es en realidad una pieza perdida.')
    inf.di('')
    inf.di(f'  {len(preambulos)} líneas en {len({p[0] for p in preambulos})} '
           f'formularios')
    for linea, tit, n, t in preambulos[:150]:
        inf.di(f'  línea {n} ({tit[:45]}): {t[:85]}')
    if len(preambulos) > 150:
        inf.di(f'  … y {len(preambulos) - 150} más')

    inf.titulo('Rúbricas halladas dentro de los formularios')
    inf.di('  Son las líneas que vienen detrás de la conclusión de una')
    inf.di('  oración y antes del rótulo siguiente. Contadas para que se vea')
    inf.di('  si alguna es en realidad el verso de una oración mal cortada:')
    inf.di('  una «rúbrica» que sale una sola vez y parece verso, lo es.')
    inf.di('')
    unas = [r for r, n in rubricas_vistas.items() if n == 1]
    inf.di(f'  rúbricas distintas: {len(rubricas_vistas)}; '
           f'de una sola vez: {len(unas)}')
    inf.di('')
    inf.di('  Las repetidas, de más a menos:')
    for r, n in rubricas_vistas.most_common():
        if n > 1:
            inf.di(f'  {n:4d} × {r}')
    inf.di('')
    inf.di('  Las de una sola vez, que son las que hay que mirar:')
    for r in unas:
        inf.di(f'       {r}')

    inf.titulo('Ordo Missæ')
    for ident, rub in ordo.items():
        ns = sorted(rub)
        inf.di(f'  {ident}: {len(rub)} rúbricas numeradas, de '
               f'{ns[0] if ns else "-"} a {ns[-1] if ns else "-"}')
        if ns:
            huecos = [n for n in range(ns[0], ns[-1] + 1) if n not in rub]
            inf.di(f'      huecos: {huecos if huecos else "ninguno"}')
            vacias = [n for n in ns if not rub[n]['lineas']]
            inf.di(f'      sin texto: {vacias if vacias else "ninguna"}')
    inf.di('')
    inf.di('  La fase 2 alinea el Ordinario de México contra esta numeración.')

    inf.titulo('Plegarias eucarísticas')
    inf.di('  Las cuatro del Ordo, las dos de la reconciliación y las cuatro')
    inf.di('  formas de la de diversas necesidades. Las seis últimas son')
    inf.di('  justamente las que el Ordinario castellano no trae.')
    inf.di('')
    for k, p in plegarias.items():
        inf.di(f'  {k}')
        inf.di(f'      {p["titulo"]}')
        inf.di(f'      {len(p["texto"]):4d} líneas'
               + (f' (+{len(p["rubrica"])} de rúbrica de uso)'
                  if p['rubrica'] else '')
               + f', línea {p["linea"]}')
    cortas = [k for k, p in plegarias.items() if len(p['texto']) < 40]
    inf.di('')
    inf.di(f'  con menos de cuarenta líneas: {cortas if cortas else "ninguna"}')

    inf.titulo('Bendiciones solemnes y oraciones sobre el pueblo')
    inf.di('  Es lo que el Ordinario castellano no trae —sólo las menciona')
    inf.di('  en los nn. 142 y 143— y lo que los misalitos sólo dan en')
    inf.di('  Cuaresma: aquí están completas, en latín.')
    inf.di('')
    inf.di(f'  bendiciones solemnes: {len(bendiciones)}')
    sec = None
    for b in bendiciones:
        if b['seccion'] != sec:
            sec = b['seccion']
            inf.di(f'    {sec}')
        inf.di(f'      {b["n"]:3d}. {b["titulo"][:58]:58s} '
               f'{len(b["texto"]):3d} ln   línea {b["linea"]}')
    vacias = [b for b in bendiciones if not b['texto']]
    inf.di(f'    sin texto: {len(vacias)}')
    inf.di(f'  rúbrica de uso: {len(rub_bend)} líneas')
    inf.di('')
    inf.di(f'  oraciones sobre el pueblo: {len(super_populum)}')
    ns = [b['n'] for b in super_populum]
    if ns:
        inf.di(f'    numeradas de {ns[0]} a {ns[-1]}; huecos: '
               + str([n for n in range(ns[0], ns[-1] + 1) if n not in ns]))
    cortas = [b['n'] for b in super_populum if len(b['texto']) < 3]
    inf.di(f'    con menos de tres líneas: {cortas if cortas else "ninguna"}')
    inf.di(f'  rúbrica de uso: {len(rub_pop)} líneas')
    inf.di('')
    for b in super_populum:
        inf.di(f'    {b["n"]:3d}. {b["texto"][0][:80]}')

    datos = {
        'fuente': os.path.basename(PDF),
        'partes': [{'id': i, 'titulo': t} for i, t, _, _ in partes],
        'formularios': formularios,
        'prefacios': prefacios,
        'ordo': {k: list(v.values()) for k, v in ordo.items()},
        'plegarias': plegarias,
        'bendiciones': {'rubrica': rub_bend, 'piezas': bendiciones},
        'super_populum': {'rubrica': rub_pop, 'piezas': super_populum},
    }
    os.makedirs(DATOS, exist_ok=True)
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print(f'  {len(formularios)} formularios, {len(prefacios)} prefacios, '
          f'{sum(len(v) for v in ordo.values())} rúbricas del Ordo, '
          f'{len(plegarias)} plegarias')
    print(f'  → {os.path.relpath(SALIDA, misal.RAIZ)} '
          f'({os.path.getsize(SALIDA) / 1e6:.1f} MB)')
    inf.guarda()


if __name__ == '__main__':
    main()
