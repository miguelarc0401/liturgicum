# -*- coding: utf-8 -*-
"""Fase 2 — el Ordinario de la Misa de México, en castellano.

De `Missale/Ordinario de la Misa México (1).pdf` salen:

  · las **146 rúbricas** del Ordo Missæ con su texto y sus alternativas, y
    **alineadas con el latín por su número**, que es el hallazgo que ahorra
    una fase entera: el castellano numera 1-146 y el latino 1-146, y el
    número dice lo mismo en los dos, así que el bilingüe no hay que coserlo;
  · los **67 prefacios** con su título y su epígrafe;
  · las **plegarias eucarísticas I-IV** con sus partes propias —el *Reunidos
    en comunión*, las *Intercesiones particulares*, los insertos—.

Dos cosas hacen que esto se pueda leer sin adivinar nada:

**El color.** El Ordinario imprime sus rúbricas **en rojo** (#c0504d), igual
que la fuente de la Liturgia de las Horas, y eso separa lo que se reza de lo
que se indica. La sangría no sirve: el texto rezado va a la izquierda en las
primeras páginas y a cinco espacios en las plegarias, porque la capitular
mueve la caja. El color no cambia.

**El número.** Las rúbricas van numeradas, y la numeración es monótona: eso
permite corregir las nueve que el libro imprime mal —hay dos «7.», falta el
«8.», y en el rito de comunión aparecen un «144.» y un «153.» donde van el
130 y el 139— sin inventar nada, porque sólo cabe un número en cada hueco. El
informe las nombra una por una con su página.

**Y el hallazgo de los prefacios**, que es lo que desarma el riesgo más
difícil de ver de este módulo: el Ordinario numera **sólo los 50 prefacios
que existen en el Misal latino**, y les da el mismo número (33-82); los 17
que el latín no tiene van **sin número**. La correspondencia latín↔castellano
no hay que construirla a mano ni deducirla del título: la fuente la dice, y
este informe la imprime entera, con los 17 sin pareja nombrados uno a uno.

    python Missale/src/2_ordinario.py

Deja `Missale/datos/ordinario_es.json`, `Missale/datos/prefacios_es.json` y
`Missale/datos/ordinario_qa.txt`. Necesita PyMuPDF.
"""

import glob
import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misal
from misal import DATOS, MISSALE, Informe, es_rubrica, plano, solo_negro

LATINO = os.path.join(DATOS, 'misal_latino.json')
SALIDA = os.path.join(DATOS, 'ordinario_es.json')
PREFACIOS = os.path.join(DATOS, 'prefacios_es.json')
QA = os.path.join(DATOS, 'ordinario_qa.txt')

# El nombre del fichero viene en NFD en el disco («Me» + acento suelto), así
# que se busca por comodín en vez de escribirlo: con el nombre escrito a mano
# no abre.
PATRON = os.path.join(MISSALE, 'Ordinario*.pdf')


# --------------------------------------------------------------------------
# el vocabulario del libro
# --------------------------------------------------------------------------

# Las cinco partes del Ordinario, nombradas. El Ordo Missæ es un libro
# cerrado y pequeño: nombrarlas es más honrado que una heurística de cuerpo
# de letra, que confundiría el rótulo con las palabras de la consagración,
# que van en mayúsculas y a cuerpo 20. Si alguna no apareciera, el informe lo
# dice en vez de callarlo.
SECCIONES = ['RITOS INICIALES', 'LITURGIA DE LA PALABRA',
             'LITURGIA EUCARÍSTICA', 'RITO DE COMUNIÓN',
             'RITO DE CONCLUSIÓN']

# Los rótulos de las partes propias de las plegarias: el «Reunidos en
# comunión» con sus ocho propios del tiempo y las intercesiones de las
# plegarias II, III y IV.
PROPIAS = ['REUNIDOS EN COMUNIÓN PROPIOS', 'INTERCESIONES PARTICULARES']

TITULO_MEDIO = 15.5             # los prefacios y las plegarias

NUMERADA = re.compile(r'^(\d{1,3})\.\s*(.*)$')
ALTERNATIVA = re.compile(r'^O\s+bien\s*:?\s*$', re.IGNORECASE)
PREFACIO = re.compile(r'^PREFACIO\b')
PLEGARIA = re.compile(r'^PLEGARIA EUCARÍSTICA\s+([IVX]+)\s*$')
FIN_PREFACIO = re.compile(r'^Santo,\s*Santo,\s*Santo')

# El encabezado de página: el número y el rótulo de la sección, a cuerpo
# pequeño. En la página par va «82 ORDINARIO DE LA MISA» y en la impar
# «PLEGARIA EUCARÍSTICA I85», con el número pegado.
ENCABEZADO_TAM = 11.6
ENCABEZADO = re.compile(r'^(?:(\d{1,3})\s*(?=[A-ZÁÉÍÓÚ])|)'
                        r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ \.,ºª]{4,})'
                        r'(?:\s*(\d{1,3}))?\s*$')

SIN_MINUSCULAS = re.compile(r'^[^a-záéíóúüñ]+$')

# El original separa las alternativas con una regla de guiones bajos. Es
# maqueta: la alternativa ya se sabe por el «O bien:», y la raya no se guarda.
REGLA = re.compile(r'^[_\s]{4,}$')


def slug(texto):
    t = unicodedata.normalize('NFKD', texto.lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r'[^a-z0-9]+', '-', t)
    return re.sub(r'-+', '-', t).strip('-')


def es_titulo(linea, minimo=TITULO_MEDIO):
    """Un rótulo: a cuerpo grande, en negro y sin minúsculas."""
    return (linea['tam'] >= minimo and solo_negro(linea)
            and SIN_MINUSCULAS.match(plano(linea)) is not None
            and len(plano(linea)) > 4)


# --------------------------------------------------------------------------
# lo marginal
# --------------------------------------------------------------------------

def quita_encabezados(lineas, inf):
    """Fuera el encabezado de página, y de paso se apunta la página impresa.

    Devuelve `(lineas, cuantos)`. El número de página sirve para cotejar con
    el libro de papel, que es para lo que están las páginas.
    """
    limpias, pagina, fuera = [], None, 0
    for ln in lineas:
        t = plano(ln)
        if ln['tam'] <= ENCABEZADO_TAM and not re.search(r'[a-záéíóú]', t):
            m = ENCABEZADO.match(t)
            if m and (m.group(1) or m.group(3)):
                pagina = int(m.group(1) or m.group(3))
                fuera += 1
                continue
        ln['pag'] = pagina
        limpias.append(ln)
    return limpias, fuera


# --------------------------------------------------------------------------
# las rúbricas numeradas, y las nueve que el libro numera mal
# --------------------------------------------------------------------------

# Las tres que la monotonía no alcanza, puestas a mano y con su prueba al
# lado. No son conjeturas: cada una se coteja con la rúbrica latina del mismo
# número, que es la que dice qué va ahí.
#
#  · «Toma la patena…» es la doxología de la plegaria III, y el latino la
#    numera 114; el Ordinario la imprime detrás del inserto de difuntos
#    (115) y le pone otra vez el 116, que es el de la nota del prefacio.
#    Queda un 116 repetido y un hueco en el 114, y encajan.
#  · «Después el sacerdote… dice la oración después de la comunión» lleva un
#    153, que no existe en una serie que acaba en 146. El latino mete esa
#    indicación dentro de su 139, así que el castellano partió el 139 en dos:
#    se guarda como 139b y la app la da detrás de la 139.
#  · El PREFACIO II DE LA SANTÍSIMA EUCARISTÍA sale sin número, y el 61 está
#    vacío. El latino numera 61 a PRÆFATIO II DE SS.MA EUCHARISTIA, cuyo
#    epígrafe —«De fructibus Ss.mæ Eucharistiæ»— es palabra por palabra el
#    castellano «LOS FRUTOS DE LA SANTÍSIMA EUCARISTÍA». No hay otra.

# La clave es el número impreso **y** un trozo del texto: la doxología sale
# una vez en cada plegaria y las demás están bien numeradas, así que por el
# texto solo se corregirían también las buenas.
CORRECCIONES = [
    (116, 'Toma la patena con el pan consagrado y el cáliz', 114,
     'es la doxología de la plegaria III, que el latino numera 114; el '
     'Ordinario la imprime detrás del inserto de difuntos y le repite el 116 '
     'de la nota del prefacio'),
    (153, 'dice la oración después de la comunión', '139b',
     'el 153 no existe en una serie de 146; el latino lleva esa indicación '
     'dentro de su 139, así que el castellano partió esa rúbrica en dos'),
]

# Y el prefacio que el Ordinario imprime sin su número.
PREFACIO_SIN_NUMERO = [
    ('PREFACIO II DE LA SANTÍSIMA EUCARISTÍA', 61,
     'el latino numera 61 a PRÆFATIO II DE SS.MA EUCHARISTIA, y su epígrafe '
     '«De fructibus Ss.mæ Eucharistiæ» es el castellano «LOS FRUTOS DE LA '
     'SANTÍSIMA EUCARISTÍA»'),
]


def numeros_corregidos(lineas):
    """`(crudos, arreglos, huecos, sobrantes)` de las rúbricas numeradas.

    La numeración va de 1 a 146 y es monótona, y eso basta para corregir las
    que el libro imprime mal **sin adivinar**, porque la de después lo avala:
    si donde debería ir el n la impresión pone otra cosa y la siguiente es
    n+1, entonces la de en medio es el n y no hay otra posibilidad. Es la
    misma regla con que se cuentan las bendiciones solemnes del latino.

    Lo que el testigo no avala se deja como está —que es lo que hay que
    hacer con el 62, donde el hueco del 61 es real: el Ordinario imprime ese
    prefacio sin número porque el latino también lo numera y el castellano
    se lo saltó— y el informe lo nombra.
    """
    crudos = []
    for i, ln in enumerate(lineas):
        # el número va en negro y la indicación en rojo: la línea es mixta
        m = NUMERADA.match(plano(ln))
        if m and ln['tam'] <= 13 and not solo_negro(ln):
            crudos.append((i, int(m.group(1))))

    arreglos, a_mano, previo = {}, {}, 0
    for k, (i, n) in enumerate(crudos):
        texto = plano(lineas[i])
        tabla = next((c for c in CORRECCIONES
                      if c[0] == n and c[1] in texto), None)
        if tabla:
            a_mano[i] = (n, tabla[2], tabla[3])
            if isinstance(tabla[2], int):
                previo = tabla[2]
            continue
        if n == previo + 1:
            previo = n
            continue
        siguiente = crudos[k + 1][1] if k + 1 < len(crudos) else None
        if siguiente == previo + 2:
            arreglos[i] = (n, previo + 1)
            previo = previo + 1
        else:
            arreglos[i] = (n, None)
            previo = n

    finales = []
    for i, n in crudos:
        if i in a_mano:
            finales.append(a_mano[i][1])
        else:
            finales.append(arreglos.get(i, (n, n))[1] or n)
    enteros = [n for n in finales if isinstance(n, int)]
    huecos = sorted(set(range(1, 147)) - set(enteros))
    repes = sorted({n for n in enteros if enteros.count(n) > 1})
    sobrantes = sorted(n for n in enteros if n > 146)
    return crudos, arreglos, a_mano, huecos, repes, sobrantes


# --------------------------------------------------------------------------
# la pasada: del PDF a las rúbricas, los prefacios y las plegarias
# --------------------------------------------------------------------------

def lee(lineas, inf):
    """Las secciones, las 146 rúbricas, los 67 prefacios y las 4 plegarias.

    Un recorrido y un estado: el rótulo que manda. Dentro de una rúbrica,
    cada «O bien:» abre una opción, y las líneas se guardan con el número de
    opción a la que pertenecen —0 la primera, que es la que la app muestra, y
    1, 2, 3… las que guarda detrás de un «O bien»—.
    """
    crudos, arreglos, a_mano, huecos, repes, sobrantes = \
        numeros_corregidos(lineas)
    de_linea = {}
    for i, n in crudos:
        if i in a_mano:
            de_linea[i] = (n, a_mano[i][1])
        else:
            de_linea[i] = (n, arreglos.get(i, (n, n))[1] or n)

    secciones, rubricas, prefacios, plegarias = [], OrderedDict(), \
        OrderedDict(), OrderedDict()
    seccion = None
    actual = None          # la rúbrica en curso
    opcion = 0
    pref = None            # el prefacio en curso
    pleg = None            # la plegaria en curso
    propia = None          # la parte propia en curso, dentro de la plegaria
    sin_rubrica = []       # texto que no cayó en ninguna rúbrica

    reglas = 0
    for i, ln in enumerate(lineas):
        t = plano(ln)
        if REGLA.match(t):
            reglas += 1
            continue

        # --- rótulos -----------------------------------------------------
        if t in SECCIONES and solo_negro(ln) and ln['tam'] >= TITULO_MEDIO:
            seccion = t
            secciones.append({'titulo': t, 'pag': ln['pag'], 'i': i})
            actual = pref = pleg = None
            continue

        if t in PROPIAS and pleg is not None:
            propia = t
            pleg['propias'][t] = []
            actual = None
            continue

        m = PLEGARIA.match(t)
        if m and ln['tam'] >= TITULO_MEDIO:
            ident = slug(t)
            # el subtítulo va debajo: «PLEGARIA EUCARÍSTICA I / o CANON
            # ROMANO»
            sub = None
            if i + 1 < len(lineas):
                st = plano(lineas[i + 1])
                if re.match(r'^o\s+[A-ZÁÉÍÓÚ]', st) and len(st) < 40:
                    sub = st
            pleg = {'titulo': t, 'subtitulo': sub, 'romano': m.group(1),
                    'pag': ln['pag'], 'i': i, 'lineas': [],
                    'propias': OrderedDict()}
            plegarias[ident] = pleg
            seccion = t
            actual = pref = propia = None
            continue

        if PREFACIO.match(t) and ln['tam'] >= TITULO_MEDIO and solo_negro(ln):
            # el título puede seguir en la línea de abajo («PREFACIO I PARA
            # LOS DOMINGOS / DEL TIEMPO ORDINARIO»)
            titulo = t
            if (i + 1 < len(lineas) and es_titulo(lineas[i + 1], TITULO_MEDIO)
                    and not PREFACIO.match(plano(lineas[i + 1]))
                    and not PLEGARIA.match(plano(lineas[i + 1]))):
                titulo += ' ' + plano(lineas[i + 1])
            if pref is not None and pref['titulo'] == titulo:
                continue            # la segunda línea del título de arriba
            ident = slug(titulo)
            if ident in prefacios:
                continue
            puesto = next((c for c in PREFACIO_SIN_NUMERO
                           if c[0] == titulo), None)
            pref = {'titulo': titulo, 'epigrafe': None,
                    'n': puesto[1] if puesto else None,
                    'n_de_tabla': bool(puesto),
                    'rubrica': [], 'texto': [], 'nota': [],
                    'pag': ln['pag'], 'i': i}
            prefacios[ident] = pref
            actual = pleg = None
            continue

        # --- dentro de un prefacio ---------------------------------------
        if pref is not None:
            if pref['epigrafe'] is None and es_rubrica(ln) \
                    and SIN_MINUSCULAS.match(t):
                pref['epigrafe'] = t
                continue
            if i in de_linea and not pref['texto']:
                pref['n'] = de_linea[i][1]
                resto = NUMERADA.match(t).group(2)
                if resto:
                    pref['rubrica'].append(resto)
                continue
            if es_rubrica(ln) and not pref['texto']:
                pref['rubrica'].append(t)
                continue
            if es_titulo(ln, TITULO_MEDIO) and SIN_MINUSCULAS.match(t):
                continue            # resto del título, ya absorbido
            if pref['texto'] and FIN_PREFACIO.match(
                    plano({'tiradas': pref['texto'][-1]})):
                # ya dio el Sanctus: lo que viene detrás es la nota de uso
                # del prefacio —«Si se usa el Canon romano, se dice Reunidos
                # en comunión propio»—, y es de él, no de la rúbrica de al
                # lado
                pref['nota'].append(ln['tiradas'])
                continue
            pref['texto'].append(ln['tiradas'])
            continue

        # --- una rúbrica numerada ----------------------------------------
        if i in de_linea:
            propia = None
            impreso, bueno = de_linea[i]
            resto = NUMERADA.match(t).group(2)
            actual = {'n': bueno, 'n_impreso': impreso, 'seccion': seccion,
                      'pag': ln['pag'], 'i': i, 'lineas': []}
            if bueno in rubricas:
                actual['repetida'] = True
                k = 2
                while f'{bueno}~{k}' in rubricas:
                    k += 1
                rubricas[f'{bueno}~{k}'] = actual
            else:
                rubricas[bueno] = actual
            opcion = 0
            if resto:
                actual['lineas'].append({'o': 0, 'r': True,
                                         'tiradas': [(True, resto)]})
            continue

        # --- dentro de una plegaria, pero fuera de rúbrica ---------------
        if pleg is not None and pleg.get('subtitulo') == t:
            continue

        if ALTERNATIVA.match(t):
            if actual is not None:
                opcion += 1
                actual['lineas'].append({'o': opcion, 'r': True,
                                         'tiradas': ln['tiradas'],
                                         'marca': True})
            elif pleg is not None:
                pleg['lineas'].append({'r': True, 'tiradas': ln['tiradas'],
                                       'marca': True})
            continue

        if actual is not None:
            actual['lineas'].append({'o': opcion, 'r': es_rubrica(ln),
                                     'tiradas': ln['tiradas']})
            continue
        if pleg is not None:
            destino = (pleg['propias'][propia] if propia
                       else pleg['lineas'])
            destino.append({'r': es_rubrica(ln), 'tiradas': ln['tiradas']})
            continue
        sin_rubrica.append((i, ln['pag'], t))

    return {'secciones': secciones, 'rubricas': rubricas,
            'prefacios': prefacios, 'plegarias': plegarias,
            'reglas': reglas,
            'sin_rubrica': sin_rubrica, 'crudos': crudos,
            'arreglos': arreglos, 'a_mano': a_mano, 'huecos': huecos,
            'repes': repes, 'sobrantes': sobrantes}


# --------------------------------------------------------------------------
# el cotejo con el latín
# --------------------------------------------------------------------------

def coteja_ordo(rubricas, prefacios, latino, inf):
    """Las 146 rúbricas, una al lado de la otra. Lo que no cuadre se escribe.

    No se compara el texto —son dos lenguas— sino que **existan las dos** con
    el mismo número, que es lo que el libro promete. Y se imprime el
    principio de cada una para que se vea de un golpe si el número dice lo
    mismo en los dos: es la comprobación que el plan hizo a mano con once
    rúbricas, aquí con las ciento cuarenta y seis.
    """
    la = {r['n']: r for r in latino.get('ordo', {}).get('ordo', [])}
    es = {n: r for n, r in rubricas.items() if isinstance(n, int)}
    # las rúbricas 33-82 son los prefacios, y en castellano viven en su
    # propio fichero: para el cotejo se traen aquí, que es donde el libro
    # las tiene
    for k, p in prefacios.items():
        if p.get('n'):
            es[p['n']] = {'n': p['n'], 'lineas': [
                {'tiradas': [(True, f'[{p["titulo"]}] ' + ' '.join(
                    p['rubrica'])[:70])]}]}
    inf.di(f'  rúbricas en latín: {len(la)}   en castellano: {len(es)}')
    solo_la = sorted(set(la) - set(es))
    solo_es = sorted(set(es) - set(la))
    inf.di(f'  sólo en latín: {solo_la if solo_la else "ninguna"}')
    inf.di(f'  sólo en castellano: {solo_es if solo_es else "ninguna"}')
    inf.di('')
    inf.di('  Las dos lenguas, rúbrica a rúbrica. La columna de la izquierda')
    inf.di('  es el castellano y la de la derecha el latín; si el número no')
    inf.di('  dijera lo mismo en los dos, se vería aquí.')
    inf.di('')
    for n in range(1, 147):
        e, l = es.get(n), la.get(n)
        te = (' '.join(plano({'tiradas': x['tiradas']})
                       for x in e['lineas'][:2])[:62] if e else '—')
        tl = (' '.join(l['lineas'][:2])[:62] if l else '—')
        marca = '' if (e and l) else '   ← ¡FALTA UNA!'
        inf.di(f'  {n:3d}  es: {te}{marca}')
        inf.di(f'       la: {tl}')
    return solo_la, solo_es


def coteja_prefacios(prefacios, latino, inf):
    """Los dos juegos de prefacios, con su tabla de correspondencia.

    Es el riesgo que el plan daba por más difícil de ver —«saldrían textos
    cruzados, y cruzados de una manera difícil de notar, porque los dos
    serían prefacios de Adviento y los dos sonarían bien»— y resulta que la
    fuente lo resuelve: el Ordinario numera sólo los que tiene el latín, con
    el número del latín. Aquí se comprueba por dos caminos: por el número y
    por el epígrafe, que el castellano traduce del latino.
    """
    la = latino.get('prefacios', {})
    la_n = {p['n']: (k, p) for k, p in la.items() if p.get('n')}
    es_n = {p['n']: (k, p) for k, p in prefacios.items() if p.get('n')}

    inf.di(f'  prefacios castellanos: {len(prefacios)}')
    inf.di(f'      numerados (= los que tiene el latín): {len(es_n)}')
    inf.di(f'      sin número (= los que el latín no tiene): '
           f'{len(prefacios) - len(es_n)}')
    inf.di(f'  prefacios latinos del cuerpo (nn. 33-82): {len(la_n)}')
    inf.di('')

    tabla, sin_pareja_la = [], []
    for n in sorted(la_n):
        kl, pl = la_n[n]
        if n in es_n:
            ke, pe = es_n[n]
            # el segundo camino: el epígrafe. No se traduce palabra por
            # palabra, pero las palabras llenas coinciden casi siempre, y
            # cuando no, se dice.
            tabla.append((n, ke, kl, pe, pl))
        else:
            sin_pareja_la.append((n, kl, pl))

    inf.di('  La tabla de correspondencia, por número de rúbrica:')
    inf.di('')
    for n, ke, kl, pe, pl in tabla:
        inf.di(f'  {n:3d}  es  {pe["titulo"]}')
        inf.di(f'       epígrafe  {pe["epigrafe"]}')
        inf.di(f'       la  {pl["titulo"]}')
        inf.di(f'       epígrafe  {pl["epigrafe"]}')
    inf.di('')
    inf.di(f'  latinos sin pareja castellana: {len(sin_pareja_la)}')
    for n, kl, pl in sin_pareja_la:
        inf.di(f'      {n:3d}  {pl["titulo"]}  —  {pl["epigrafe"]}')

    sueltos = [(k, p) for k, p in prefacios.items() if not p.get('n')]
    inf.di('')
    inf.di('  Los castellanos sin número, que son los que el juego común')
    inf.di(f'  latino no tiene ({len(sueltos)}). Varios de ellos sí están en')
    inf.di('  el Misal latino, pero dentro de las misas rituales —el del')
    inf.di('  bautismo, la confirmación, la penitencia, la unción—, y hay')
    inf.di('  que ir a buscarlos ahí; los demás son propios del juego')
    inf.di('  castellano y no tienen latín que mostrar.')
    inf.di('')
    for k, p in sueltos:
        inf.di(f'      {p["titulo"]}')
        inf.di(f'          {p["epigrafe"]}')
    return tabla, sin_pareja_la, sueltos


# --------------------------------------------------------------------------
# la pasada
# --------------------------------------------------------------------------

def main():
    inf = Informe(QA, 'Fase 2 — el Ordinario de la Misa de México')
    hallados = glob.glob(PATRON)
    if not hallados:
        sys.exit(f'falta el PDF del Ordinario ({PATRON})')
    pdf = hallados[0]
    inf.di(f'fuente: {os.path.basename(pdf)}')

    lineas = misal.tiradas_de(pdf)
    inf.di(f'        {len(lineas)} líneas de tiradas')
    rojas = sum(1 for ln in lineas if es_rubrica(ln))
    negras = sum(1 for ln in lineas if solo_negro(ln))
    inf.di(f'        {rojas} enteramente en rojo (rúbrica), {negras} en negro '
           f'(texto), {len(lineas) - rojas - negras} mixtas')
    inf.di('')
    inf.di('  Las mixtas son texto rezado con una marca dentro: el «V/.» del')
    inf.di('  diálogo, el «N.» del Papa, el corchete de lo que puede')
    inf.di('  omitirse. Se guardan enteras, con su color tirada a tirada.')

    lineas, fuera = quita_encabezados(lineas, inf)
    inf.di('')
    inf.di(f'  encabezados de página retirados: {fuera}')

    d = lee(lineas, inf)
    inf.di(f'  reglas decorativas retiradas: {d["reglas"]}')

    inf.titulo('Las secciones')
    for s in d['secciones']:
        inf.di(f'  p. {s["pag"]}  {s["titulo"]}')

    inf.titulo('La numeración de las rúbricas, y lo que el libro imprime mal')
    inf.di('  La serie va de 1 a 146 y es monótona, y eso basta para corregir')
    inf.di('  casi todo sin adivinar: si un número rompe la serie y el')
    inf.di('  siguiente es el que vendría después del que falta, el de en')
    inf.di('  medio sólo puede ser ése. El que el testigo no avale se deja')
    inf.di('  como está, porque un hueco puede ser real: el 61 lo es.')
    inf.di('')
    inf.di(f'  rúbricas numeradas halladas: {len(d["crudos"])}')
    inf.di('')
    hechos = {i: v for i, v in d['arreglos'].items() if v[1]}
    quietos = {i: v for i, v in d['arreglos'].items() if not v[1]}
    inf.di(f'  corregidas por la serie: {len(hechos)}')
    for i, (impreso, bueno) in sorted(hechos.items()):
        ln = lineas[i]
        inf.di(f'      p. {ln["pag"]}: el libro pone «{impreso}.» y es el '
               f'{bueno}')
        inf.di(f'          {plano(ln)[:88]}')
    inf.di('')
    inf.di(f'  corregidas a mano, con su prueba: {len(d["a_mano"])}')
    for i, (impreso, bueno, por_que) in sorted(d['a_mano'].items()):
        ln = lineas[i]
        inf.di(f'      p. {ln["pag"]}: el libro pone «{impreso}.» y es el '
               f'{bueno}')
        inf.di(f'          {plano(ln)[:88]}')
        inf.di(f'          porque {por_que}')
    inf.di('')
    inf.di(f'  números fuera de serie que **no** son error: {len(quietos)}')
    inf.di('      Son los que vienen detrás de un hueco real o de una')
    inf.di('      corrección, y están bien como están.')
    for i, (impreso, _) in sorted(quietos.items()):
        ln = lineas[i]
        inf.di(f'      p. {ln["pag"]}: «{impreso}.» — {plano(ln)[:78]}')
    inf.di('')
    inf.di(f'  huecos que quedan en 1-146: '
           f'{d["huecos"] if d["huecos"] else "ninguno"}')
    inf.di(f'  números repetidos que quedan: '
           f'{d["repes"] if d["repes"] else "ninguno"}')
    inf.di(f'  números mayores de 146 que quedan: '
           f'{d["sobrantes"] if d["sobrantes"] else "ninguno"}')
    if d['huecos']:
        inf.di('')
        inf.di('  Los huecos, con la rúbrica latina del mismo número al lado,')
        inf.di('  que es lo que dice si falta texto o si el castellano lo')
        inf.di('  metió dentro de la rúbrica de antes:')
        inf.di('')
        if os.path.exists(LATINO):
            with open(LATINO, encoding='utf-8') as f:
                la = {r['n']: r for r in json.load(f)['ordo']['ordo']}
            es = d['rubricas']
            for n in d['huecos']:
                inf.di(f'      {n}')
                r = la.get(n)
                inf.di(f'          la: {" ".join(r["lineas"][:2])[:85] if r else "—"}')
                ant = es.get(n - 1)
                if ant:
                    t = ' '.join(plano({'tiradas': x['tiradas']})
                                 for x in ant['lineas'][:3])
                    inf.di(f'          es {n-1}: {t[:85]}')

    inf.titulo('Las alternativas: lo que el Ordinario deja elegir')
    inf.di('  Cada «O bien:» abre una opción dentro de su rúbrica. La')
    inf.di('  primera es la que la app muestra; las demás quedan detrás de')
    inf.di('  un «O bien», que es lo que se pidió para quien reza.')
    inf.di('')
    con_op = [(n, r) for n, r in d['rubricas'].items()
              if max((x['o'] for x in r['lineas']), default=0) > 0]
    total_op = sum(max(x['o'] for x in r['lineas']) for _, r in con_op)
    inf.di(f'  rúbricas con alternativa: {len(con_op)}')
    inf.di(f'  alternativas en total: {total_op}')
    inf.di('')
    for n, r in con_op:
        cuantas = max(x['o'] for x in r['lineas'])
        inf.di(f'  n. {n} ({r["seccion"]}), p. {r["pag"]}: '
               f'{cuantas + 1} opciones')
        for o in range(cuantas + 1):
            prim = next((plano({'tiradas': x['tiradas']})
                         for x in r['lineas']
                         if x['o'] == o and not x['r']), '(sólo rúbrica)')
            inf.di(f'      {o}: {prim[:78]}')

    inf.titulo('Las plegarias eucarísticas')
    inf.di('  Cada plegaria son las rúbricas 83-123 de la serie, así que no')
    inf.di('  se guardan dos veces: aquí va de qué número a qué número llega')
    inf.di('  cada una, y sus partes propias, que es lo que el Ordinario')
    inf.di('  abre a elegir.')
    inf.di('')
    for k, p in d['plegarias'].items():
        suyas = sorted(r['n'] for r in d['rubricas'].values()
                       if r['seccion'] == p['titulo']
                       and isinstance(r['n'], int))
        p['n_desde'] = suyas[0] if suyas else None
        p['n_hasta'] = suyas[-1] if suyas else None
        inf.di(f'  {p["titulo"]}'
               + (f' {p["subtitulo"]}' if p.get('subtitulo') else '')
               + f'  (p. {p["pag"]})')
        inf.di(f'      rúbricas {p["n_desde"]}-{p["n_hasta"]} '
               f'({len(suyas)} en total)')
        for nombre, lns in p['propias'].items():
            trozos = [plano({'tiradas': x['tiradas']}) for x in lns if x['r']]
            inf.di(f'      {nombre}: {len(lns)} líneas, '
                   f'{len(trozos)} indicaciones')
            for x in trozos:
                inf.di(f'          {x[:76]}')
        if p['lineas']:
            inf.di(f'      ¡AVISO! {len(p["lineas"])} líneas fuera de rúbrica '
                   f'y fuera de parte propia:')
            for x in p['lineas'][:6]:
                inf.di(f'          {plano({"tiradas": x["tiradas"]})[:76]}')

    inf.titulo('Los prefacios')
    if os.path.exists(LATINO):
        with open(LATINO, encoding='utf-8') as f:
            latino = json.load(f)
        coteja_prefacios(d['prefacios'], latino, inf)
    else:
        inf.di('  ¡AVISO! no está misal_latino.json: ejecuta primero la fase')
        inf.di('  1 y vuelve, que el cotejo de los dos juegos es lo que')
        inf.di('  impide cruzar los textos.')
        for k, p in d['prefacios'].items():
            inf.di(f'  n. {p["n"]}  {p["titulo"]}  —  {p["epigrafe"]}')

    inf.titulo('El Ordo bilingüe: las 146 rúbricas, una contra otra')
    if os.path.exists(LATINO):
        coteja_ordo(d['rubricas'], d['prefacios'], latino, inf)
    else:
        inf.di('  (hace falta la fase 1)')

    inf.titulo('Texto que no cayó en ninguna rúbrica')
    inf.di('  Debería ser sólo lo que va antes de la rúbrica 1 y los rótulos')
    inf.di('  que ya se guardaron aparte. Si aquí sale una oración, hay')
    inf.di('  texto perdido.')
    inf.di('')
    inf.di(f'  {len(d["sin_rubrica"])} líneas')
    for i, pag, t in d['sin_rubrica'][:80]:
        inf.di(f'      p. {pag}, línea {i}: {t[:85]}')
    if len(d['sin_rubrica']) > 80:
        inf.di(f'      … y {len(d["sin_rubrica"]) - 80} más')

    # ---- a disco ---------------------------------------------------------
    ordinario = {
        'fuente': os.path.basename(pdf),
        'secciones': d['secciones'],
        'rubricas': [d['rubricas'][k] for k in sorted(
            d['rubricas'], key=lambda x: (x if isinstance(x, int) else 999))],
        'plegarias': d['plegarias'],
    }
    os.makedirs(DATOS, exist_ok=True)
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump(ordinario, f, ensure_ascii=False, indent=1)
    with open(PREFACIOS, 'w', encoding='utf-8') as f:
        json.dump(d['prefacios'], f, ensure_ascii=False, indent=1)

    print(f'  {len(d["rubricas"])} rúbricas, {len(d["prefacios"])} prefacios, '
          f'{len(d["plegarias"])} plegarias')
    print(f'  -> {os.path.relpath(SALIDA, misal.RAIZ)} '
          f'({os.path.getsize(SALIDA) / 1e6:.1f} MB)')
    print(f'  -> {os.path.relpath(PREFACIOS, misal.RAIZ)} '
          f'({os.path.getsize(PREFACIOS) / 1e6:.1f} MB)')
    inf.guarda()


if __name__ == '__main__':
    main()
