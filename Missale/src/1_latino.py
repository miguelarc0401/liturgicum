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
ROTULO = re.compile(r'^(' + '|'.join(re.escape(r) for _, r in PIEZAS)
                    + r')\s*(.*)$')
NOMBRE_DE = {r: n for n, r in PIEZAS}

# «Vel:» abre una alternativa a la pieza en curso; cuando la alternativa es
# una antífona, trae su propia cita: «Vel: Io 10, 10».
ALTERNATIVA = re.compile(r'^Vel:\s*(.*)$')

# Las conclusiones de la oración. Aquí acaba el texto y empieza la rúbrica.
CONCLUSION = re.compile(
    r'^(Per Dóminum|Per Christum|Qui tecum|Qui vivis|Qui vivit|Per eúndem)\b')

# Las rúbricas que se guardan aparte porque dicen algo que la app necesita.
PREFACIO_REF = re.compile(r'^Præfati[oæ]\b')
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

# El santoral ancla el día: «Die 2 ianuarii».
DIA_SANTORAL = re.compile(r'^Die\s+(\d{1,2})\s+(\w+)\s*$')
MESES = {'ianuarii': 1, 'februarii': 2, 'martii': 3, 'aprilis': 4,
         'maii': 5, 'iunii': 6, 'iulii': 7, 'augusti': 8,
         'septembris': 9, 'octobris': 10, 'novembris': 11, 'decembris': 12}

GRADOS = {'sollemnitas': 'sollemnitas', 'festum': 'festum',
          'memoria': 'memoria'}

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


def slug(texto):
    t = unicodedata.normalize('NFKD', texto.lower())
    t = t.replace('æ', 'ae').replace('œ', 'oe')
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r'[^a-z0-9]+', '-', t)
    return re.sub(r'-+', '-', t).strip('-')


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
        while j < fin and j < n + 4:
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
    def __init__(self, titulo, linea, pagina):
        self.titulo = titulo        # las líneas del encabezado
        self.linea = linea          # dónde empieza, en el volcado
        self.pagina = pagina
        self.cuerpo = []            # [(número de línea, texto)]

    @property
    def tiene_piezas(self):
        return any(ROTULO.match(t) for _, t in self.cuerpo)

    @property
    def nombre(self):
        return ' · '.join(self.titulo)


def bloques_de(lineas, desde, hasta, inf):
    """Parte el tramo en bloques: cada encabezado abre uno.

    Un encabezado puede ocupar varias líneas seguidas —el santoral titula en
    dos: «Ss. Basilii Magni et Gregorii Nazianzeni, / episcoporum et Ecclesiæ
    doctorum»—, y eso se resuelve mirando si la línea siguiente es también
    encabezado.
    """
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

        mayus = es_encabezado_mayusculas(s)
        if mayus or DIA_MINUSCULA.match(s):
            texto, reconocida = desespacia(s)
            if not reconocida:
                inf.di(f'  línea {i+1}: mayúsculas espaciadas sin entrada en '
                       f'la tabla ESPACIADAS: «{texto}»')
            titulo = [texto]
            i += 1
            while i < hasta:
                t = lineas[i].replace('\f', '').strip()
                if not t:
                    break
                if pagina_de(t) is not None:
                    pagina = pagina_de(t)
                    i += 1
                    continue
                if mayus and es_encabezado_mayusculas(t):
                    titulo.append(desespacia(t)[0])
                    i += 1
                    continue
                break
            bloques.append(Bloque(titulo, i, pagina))
            continue

        if not bloques:
            bloques.append(Bloque([], i + 1, pagina))
        bloques[-1].cuerpo.append((i + 1, s))
        i += 1
    return bloques


# --------------------------------------------------------------------------
# el formulario: las piezas de un bloque
# --------------------------------------------------------------------------

def piezas_del(bloque):
    """Las piezas, las rúbricas y las referencias de un bloque.

    Devuelve `(piezas, rubricas, prefacios, comunes, gloria, credo, sueltas)`.
    Las antífonas no tienen conclusión, así que se cierran en el rótulo
    siguiente; las oraciones se cierran en la suya, y lo que viene detrás es
    rúbrica.
    """
    piezas = OrderedDict()
    rubricas, prefacios, comunes, sueltas = [], [], [], []
    gloria = credo = None
    actual = None       # el diccionario donde se escribe ahora
    raiz = None         # la pieza a la que colgar una alternativa
    cerrada = False     # la oración en curso ya dio su conclusión

    def abre(nombre, cita, linea):
        nonlocal actual, raiz, cerrada
        if nombre in piezas:
            # un segundo «Collecta» en el mismo bloque es alternativa
            alt = {'cita': cita or None, 'texto': [], 'linea': linea}
            piezas[nombre]['alt'].append(alt)
            actual = alt
        else:
            piezas[nombre] = {'cita': cita or None, 'texto': [], 'alt': [],
                              'linea': linea}
            actual = piezas[nombre]
        raiz = piezas[nombre]
        cerrada = False

    for n, t in bloque.cuerpo:
        if not t:
            if actual is not None and not cerrada and actual['texto']:
                actual['texto'].append('')
            continue

        m = ROTULO.match(t)
        if m:
            abre(NOMBRE_DE[m.group(1)], m.group(2).strip(), n)
            continue

        m = ALTERNATIVA.match(t)
        if m:
            if raiz is None:
                sueltas.append((n, t))
                continue
            alt = {'cita': m.group(1).strip() or None, 'texto': [], 'linea': n}
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
            rubricas.append(t)
            continue
        if CREDO.match(t):
            credo = not t.startswith('Non')
            rubricas.append(t)
            continue

        if actual is None:
            sueltas.append((n, t))
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
    return piezas, rubricas, prefacios, comunes, gloria, credo, sueltas


def formularios_de(ident, titulo_parte, bloques, inf, formularios,
                   sin_piezas, sueltas_todas, rubricas_vistas):
    """Los formularios de una parte, con su sección y su encabezado mayor.

    `seccion` es el último rótulo en mayúsculas que no era formulario
    («TEMPUS ADVENTUS», «IANUARIUS»); `bajo` es el último que sí lo era
    («DOMINICA II ADVENTUS»), que es lo que da la semana a una feria.
    """
    seccion = bajo = None
    for b in bloques:
        cuerpo = [t for _, t in b.cuerpo if t]

        if not b.tiene_piezas:
            if not b.titulo:
                continue
            # un santo que lo toma todo del común no imprime ninguna pieza,
            # sólo la referencia: ése sí es formulario
            if not any(COMUN_REF.match(t) for t in cuerpo):
                if es_encabezado_mayusculas(b.titulo[0]):
                    seccion, bajo = b.nombre, None
                else:
                    bajo = b.nombre
                if cuerpo:
                    sin_piezas.append((b.linea, b.nombre, cuerpo[:3]))
                continue

        pz, rub, pref, com, gl, cr, sue = piezas_del(b)
        for r in rub:
            rubricas_vistas[r[:70]] += 1
        sueltas_todas += [(b.linea, b.nombre) + s for s in sue]

        md = DIA_SANTORAL.match(b.titulo[0])
        dia = ({'mes': MESES[md.group(2)], 'dia': int(md.group(1))}
               if md and md.group(2) in MESES else None)

        grado = None
        for t in list(b.titulo[1:]) + cuerpo[:2]:
            g = t.lower().strip('. ')
            if g in GRADOS and grado is None:
                grado = GRADOS[g]

        base = slug(' '.join(filter(None, [None if md else bajo, b.nombre])))
        ident_f = f'{ident}/{base}' if base else f'{ident}/l{b.linea}'
        if ident_f in formularios:
            k = 2
            while f'{ident_f}~{k}' in formularios:
                k += 1
            ident_f = f'{ident_f}~{k}'

        formularios[ident_f] = {
            'parte': titulo_parte, 'seccion': seccion, 'bajo': bajo,
            'titulo': b.titulo, 'grado': grado, 'dia': dia,
            'pagina': b.pagina, 'linea': b.linea,
            'piezas': pz, 'rubricas': rub, 'prefacio': pref, 'comun': com,
            'gloria': gl, 'credo': cr,
        }
        if es_encabezado_mayusculas(b.titulo[0]) and not md:
            bajo = b.nombre


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


def plegarias_de(bloques):
    """Las plegarias eucarísticas, por rótulo; cada una con sus partes
    propias —los «Communicantes propria», las intercesiones— tal como el
    libro las imprime debajo."""
    salida, actual = OrderedDict(), None
    for b in bloques:
        titulo = ' '.join(b.titulo)
        if re.match(r'^PREX EUCHARISTICA', titulo):
            ident = slug(titulo)
            if ident in salida:
                k = 2
                while f'{ident}-{k}' in salida:
                    k += 1
                ident = f'{ident}-{k}'
            actual = ident
            salida[actual] = {'titulo': titulo, 'texto': [],
                              'propias': OrderedDict(),
                              'pagina': b.pagina, 'linea': b.linea}
            destino = salida[actual]['texto']
        elif actual and titulo:
            salida[actual]['propias'].setdefault(titulo, [])
            destino = salida[actual]['propias'][titulo]
        elif actual:
            destino = salida[actual]['texto']
        else:
            continue
        destino += [t for _, t in b.cuerpo]
    for p in salida.values():
        limpia(p['texto'])
        for v in p['propias'].values():
            limpia(v)
    return salida


def lista_de(bloque):
    """Una pieza con título y texto: una bendición solemne, una oración sobre
    el pueblo."""
    cuerpo = limpia([t for _, t in bloque.cuerpo])
    titulo = ' '.join(bloque.titulo)
    if not titulo and not cuerpo:
        return None
    return {'titulo': titulo, 'texto': cuerpo, 'pagina': bloque.pagina,
            'linea': bloque.linea}


# --------------------------------------------------------------------------
# la pasada
# --------------------------------------------------------------------------

def main():
    inf = Informe(QA, 'Fase 1 — el Misal Romano 2002 en latín')
    if not os.path.exists(PDF):
        sys.exit(f'falta {PDF}')
    lineas = misal.texto_de(PDF, 'latino')
    inf.di(f'fuente: {os.path.basename(PDF)}  ({len(lineas)} líneas de texto)')

    inf.titulo('Las partes del libro')
    partes = partes_del(lineas, inf)
    for ident, titulo, d, h in partes:
        inf.di(f'  {ident:16s} {d:6d}-{h:<6d} {titulo}')

    formularios = OrderedDict()
    prefacios = OrderedDict()
    ordo = OrderedDict()
    plegarias = OrderedDict()
    bendiciones, super_populum = [], []
    sin_piezas, sueltas_todas = [], []
    rubricas_vistas = Counter()

    for ident, titulo, desde, hasta in partes:
        if ident == 'indices':
            continue
        bloques = bloques_de(lineas, desde, hasta, inf)

        if ident in CON_FORMULARIOS:
            formularios_de(ident, titulo, bloques, inf, formularios,
                           sin_piezas, sueltas_todas, rubricas_vistas)

        elif ident in ('ordo', 'ordo_unus'):
            # el cuerpo de prefacios vive dentro de la parte del Ordo
            prefacios.update(prefacios_del(bloques))
            ordo[ident] = numeradas_de(lineas, desde, hasta)

        elif ident == 'preces':
            prefacios.update(prefacios_del(bloques))
            plegarias.update(plegarias_de(bloques))
            tramo = None
            for b in bloques:
                tit = ' '.join(b.titulo)
                if tit == 'BENEDICTIONES SOLLEMNES':
                    tramo = 'bendiciones'
                    continue
                if tit == 'ORATIONES SUPER POPULUM':
                    tramo = 'populum'
                    continue
                if re.match(r'^(ORDO MISSÆ|AD PRECEM|PREX |PRÆFATIO)', tit):
                    tramo = None
                pieza = lista_de(b) if tramo else None
                if pieza and tramo == 'bendiciones':
                    bendiciones.append(pieza)
                elif pieza and tramo == 'populum':
                    super_populum.append(pieza)

        elif ident == 'apendice_ordo':
            plegarias.update(plegarias_de(bloques))

    # ---- informe ---------------------------------------------------------

    inf.titulo('Formularios')
    inf.di(f'  total: {len(formularios)}')
    cuenta = Counter(k.split('/')[0] for k in formularios)
    for parte in [i for i, _, c in PARTES if c]:
        inf.di(f'    {parte:16s} {cuenta.get(parte, 0)}')
    tiene = Counter()
    for f in formularios.values():
        for n in f['piezas']:
            tiene[n] += 1
    inf.di('')
    inf.di('  piezas halladas (entre paréntesis, lo que el rótulo cuenta en')
    inf.di('  el volcado entero, índices incluidos):')
    for n, rotulo in PIEZAS:
        crudas = sum(1 for ln in lineas if ln.strip().startswith(rotulo))
        inf.di(f'    {n:12s} {tiene.get(n, 0):5d}   ({crudas})')
    alt = sum(len(p.get('alt', [])) for f in formularios.values()
              for p in f['piezas'].values())
    inf.di(f'    alternativas («Vel:») colgadas de una pieza: {alt}')

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
        inf.di(f'      p. {f["pagina"]}, línea {f["linea"]}: {" · ".join(f["titulo"])}')
        inf.di(f'      falta: {", ".join(falta)}'
               + (f'   [común: {f["comun"][0][:50]}]' if f['comun'] else ''))

    inf.titulo('Prefacios')
    inf.di(f'  del cuerpo de prefacios: {len(prefacios)}')
    por_juego = Counter(p['juego'] for p in prefacios.values())
    inf.di(f'      con rúbrica numerada (del tiempo): {por_juego["tiempo"]}')
    inf.di(f'      sin ella: {por_juego["comun"]}')
    sin_texto = [k for k, p in prefacios.items() if len(p['texto']) < 10]
    inf.di(f'  con menos de diez líneas de texto: {len(sin_texto)}'
           + (f'  → {", ".join(sin_texto)}' if sin_texto else ''))
    inf.di('')
    for k, p in prefacios.items():
        inf.di(f'  {k}')
        inf.di(f'      {p["titulo"]}'
               + (f'  —  {p["epigrafe"]}' if p['epigrafe'] else ''))
        inf.di(f'      n. {p["n"]}, p. {p["pagina"]}, '
               f'{len(p["texto"])} líneas')

    inf.titulo('Prefacios que los días citan y el cuerpo no imprime')
    inf.di('  Son los **propios**: Pentecostés, la Trinidad, el Corpus, el')
    inf.di('  Sagrado Corazón… El Misal los imprime dentro de su formulario,')
    inf.di('  no en el cuerpo de prefacios. En castellano saldrán de los')
    inf.di('  misalitos (fase 4); aquí se cuentan para saber cuántos son.')
    inf.di('')
    citados = Counter()
    for f in formularios.values():
        for p in f['prefacio']:
            limpio = re.sub(r'\s*,?\s*p{1,2}\.\s*[\d\-,\s]+\.?$', '', p)
            citados[limpio.strip(' .,')] += 1
    conocidos = {clave(p['titulo']) for p in prefacios.values()}
    huerfanas = [(c, n) for c, n in citados.most_common()
                 if clave(c) not in conocidos]
    inf.di(f'  referencias distintas citadas por los días: {len(citados)}')
    inf.di(f'  de ellas, sin prefacio homónimo en el cuerpo: {len(huerfanas)}')
    inf.di('')
    for c, n in huerfanas:
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

    inf.titulo('Texto sin rótulo que lo acoja')
    inf.di('  Líneas que cayeron dentro de un bloque antes de su primer')
    inf.di('  rótulo de pieza. Las de las secciones son normales (una nota);')
    inf.di('  las de un formulario, no.')
    inf.di('')
    inf.di(f'  {len(sueltas_todas)} líneas')
    for linea, tit, n, t in sueltas_todas[:150]:
        inf.di(f'  línea {n} (bloque de {linea}: {tit[:45]}): {t[:80]}')
    if len(sueltas_todas) > 150:
        inf.di(f'  … y {len(sueltas_todas) - 150} más')

    inf.titulo('Rúbricas halladas dentro de los formularios')
    inf.di('  Contadas para que se vea si alguna es en realidad el verso de')
    inf.di('  una oración mal cortada: una «rúbrica» que sale una sola vez y')
    inf.di('  parece verso, lo es.')
    inf.di('')
    for r, n in rubricas_vistas.most_common():
        inf.di(f'  {n:4d} × {r}')

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
    for k, p in plegarias.items():
        inf.di(f'  {k}')
        inf.di(f'      {len(p["texto"]):4d} líneas, '
               f'{len(p["propias"])} partes propias, p. {p["pagina"]}')
        for t in p['propias']:
            inf.di(f'        {t}')

    inf.titulo('Bendiciones solemnes y oraciones sobre el pueblo')
    inf.di('  Es lo que el Ordinario castellano no trae y los misalitos sólo')
    inf.di('  dan en Cuaresma: aquí están completas, en latín.')
    inf.di('')
    inf.di(f'  bendiciones solemnes: {len(bendiciones)}')
    for b in bendiciones:
        inf.di(f'      p. {b["pagina"]}  {len(b["texto"]):3d} ln  '
               f'{b["titulo"][:70]}')
    inf.di(f'  oraciones sobre el pueblo: {len(super_populum)}')
    for b in super_populum:
        inf.di(f'      p. {b["pagina"]}  {len(b["texto"]):3d} ln  '
               f'{b["titulo"][:70]}')

    datos = {
        'fuente': os.path.basename(PDF),
        'partes': [{'id': i, 'titulo': t} for i, t, _, _ in partes],
        'formularios': formularios,
        'prefacios': prefacios,
        'ordo': {k: list(v.values()) for k, v in ordo.items()},
        'plegarias': plegarias,
        'bendiciones': bendiciones,
        'super_populum': super_populum,
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
