# -*- coding: utf-8 -*-
"""Fase 5 — el resolvedor: de las piezas al formulario del día.

Las cuatro fases anteriores dejaron las piezas sueltas y cada una con su
propia manera de nombrar las cosas: el Misal latino las guarda por el nombre
que el libro imprime (`sanctis/die-13-ianuarii-s-hilarii-…`), la cosecha de
los misalitos por la celebración del calendario del proyecto (`st_0113_2`), y
el leccionario por la clave que ya usan `indice.json` y `calendario.json`
(`I|1001AAVD01.html|0`). Esta fase las junta, y lo hace por donde el Misal
mismo las junta: **el formulario**.

Deja en `Missale/datos/libro/misa.json` una entrada por cada clave del
leccionario, y en `Missale/datos/resolver_qa.txt` el informe que importa: por
qué camino se emparejó cada una, cuántos testigos la respaldan y, si no tiene
castellano, por qué no.

**La unidad del Misal no es el día: es el formulario.** Es el hallazgo de esta
fase y es lo que recupera buena parte de lo que la 4 dejó fuera. El Misal
imprime *una* colecta para toda la primera semana del tiempo ordinario, y el
misalito la imprime el lunes de un año y el martes de otro; la fase 4, que
atribuía por celebración, no encontraba ninguna presente en todos sus días y
el texto se iba a `sueltos_es.json`. Al agrupar por formulario latino —los
siete días de la semana I son uno— el texto vuelve a su sitio con todos sus
testigos. Y el misalito lo dice además con su propio nombre, «Misa de la I
Semana del Tiempo Ordinario», que la fase 4 guardó como `vot_misa-de-la-i-…`:
dos caminos independientes que dicen lo mismo.

La cascada con que se resuelve cada ranura, en este orden, y cada paso queda
escrito en el informe:

  1. el texto de la propia celebración;
  2. el de otra celebración del mismo formulario del Misal;
  3. un texto suelto cuyos días caen todos en ese formulario;
  4. el común que la celebración ofrece, que el santoral del proyecto nombra;
  5. el latín, marcado como latín;
  6. nada, y se dice que nada.

    python Missale/src/5_resolver.py

Necesita las fases 1, 2, 3 y 4 corridas y el calendario desde 2018
(`python src/18_santoral.py`).
"""

import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misal
from misal import DATOS, LIBRO, RAIZ, Informe

DATA = os.path.join(RAIZ, 'data')
APP = os.path.join(RAIZ, 'app', 'datos')
QA = os.path.join(DATOS, 'resolver_qa.txt')
SALIDA = os.path.join(LIBRO, 'misa.json')

RANURAS = ['entrada', 'colecta', 'ofrendas', 'comunion', 'poscomunion',
           'pueblo']


def sinac(s):
    """El texto sin tildes y en minúscula, para comparar."""
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = s.replace('æ', 'ae').replace('œ', 'oe')
    return ''.join(c for c in s if not unicodedata.combining(c))


def squeeze(cita):
    """La forma con la que se cotejan dos citas.

    La fase 4 lleva a punto el salto de capítulo, que la fuente escribe con
    raya, con punto o con punto y coma según quién lo imprima. Aquí hace falta
    un paso más, y se ve en un caso: el misalito da «Mc 2,23–3.6» y el índice
    del leccionario «Mc 2,23—3,6», que es el mismo pasaje escrito con la coma
    donde el otro pone el punto. Así que la coma va al punto también: lo que
    distingue de verdad es el guión, que marca el intervalo de versículos, y
    ése se queda.
    """
    t = sinac(cita or '')
    for g in '–—‒;,':
        t = t.replace(g, '.')
    t = t.replace('−', '-')
    return re.sub(r'[^a-z0-9.\-]', '', t)


def versiculos(cita):
    """La cita leída: el libro y el conjunto de versículos que abarca.

    `squeeze` aplasta la cita y compara las dos formas letra a letra; eso basta
    cuando los dos libros la escriben igual, y en un tercio de los casos no lo
    hacen. Aquí se lee de verdad, y entonces tres maneras distintas de escribir
    el mismo pasaje caen en el mismo conjunto:

      * **el enlace.** El misalito une dos versículos de una estrofa con la
        conjunción —«Sal 79,9y12»— donde el índice del leccionario pone un
        punto —«Sal 79,9.12»—. Es la diferencia que dejaba sin castellano el
        salmo del domingo XXVII del Tiempo Ordinario.
      * **la letra.** El leccionario cita medio versículo —«Jn 8,12b»— y el
        misalito imprime el versículo —«Jn 8,12»—. Es el mismo renglón: la
        letra dice qué parte se lee, no qué versículo es.
      * **la raya.** El intervalo se escribe con guión, con raya o con semirraya
        según quién lo imprima: «Is 55,1-11» y «Is 55,1–11».

    Devuelve `None` cuando la cita no se deja leer —el salto de capítulo
    «Hb 7,25—8,6» no se deja, y los cánticos que se citan por el libro solo
    tampoco—; quien llama se queda entonces sin este camino, que es lo honrado.
    """
    t = sinac(cita or '').strip()
    for g in '–—‒−':
        t = t.replace(g, '-')
    m = re.match(r'^([1-3]?\s*[a-z][a-z0-9ñ ]*?)\s*(\d.*)$', t)
    if not m:
        return None
    libro = re.sub(r'[^a-z0-9]', '', m.group(1))
    # el enlace, antes de partir: la conjunción entre dos números separa dos
    # versículos igual que el punto, y el libro la escribe pegada —«9y12»— o
    # con espacios —«9 y 12»—. El latino del misalito usa «et».
    resto = re.sub(r'(?<=[0-9a-z])\s*(?:y|et)\s*(?=[0-9])', '.', m.group(2))
    cap, vs = None, set()
    for trozo in re.split(r'[.;]', resto):
        trozo = trozo.strip()
        if not trozo:
            continue
        # «79,9» abre capítulo; de ahí en adelante los trozos son versículos
        if ',' in trozo:
            antes, trozo = trozo.split(',', 1)
            antes, trozo = antes.strip(), trozo.strip()
            if re.fullmatch(r'\d+', antes):
                cap = antes
        mm = re.fullmatch(r'(\d+)[a-z]*\s*-\s*(\d+)[a-z]*', trozo)
        if mm:
            a, b = int(mm.group(1)), int(mm.group(2))
            if cap is None or b < a:
                return None
            vs |= {(cap, str(v)) for v in range(a, b + 1)}
            continue
        mm = re.fullmatch(r'(\d+)[a-z]*', trozo)
        if mm:
            if cap is None:          # el primer número es el capítulo
                cap = mm.group(1)
            else:
                vs.add((cap, mm.group(1)))
            continue
        return None
    return (libro, frozenset(vs)) if vs else None


def libro_y_capitulo(cita):
    """El sitio de la Escritura: el libro y el primer capítulo que la cita
    nombra. Vale también para las citas que `versiculos` no sabe leer, porque
    el libro y el capítulo se ven aunque la lista de versículos no."""
    r = versiculos(cita)
    if r:
        return r[0], min(int(c) for c, _ in r[1])
    t = sinac(cita or '').strip()
    for g in '–—‒−':
        t = t.replace(g, '-')
    m = re.match(r'^([1-3]?\s*[a-z][a-z0-9ñ ]*?)\s*(\d+)', t)
    return (re.sub(r'[^a-z0-9]', '', m.group(1)), int(m.group(2))) if m else None


def mismo_libro(a, b):
    """Dos nombres de libro que son el mismo. Iguales, o uno es el otro con el
    numeral delante: el volcado del misalito pierde a veces el «1» de «1 Jn» y
    lo imprime «Jn», y se ve porque la primera lectura de la Pascua es la
    primera carta de san Juan diez días seguidos."""
    return (a == b
            or bool(re.fullmatch('[123]' + re.escape(b), a))
            or bool(re.fullmatch('[123]' + re.escape(a), b)))


def misma_pericopa(cita_lecc, cita_es):
    """Si la cita del leccionario y la del misalito hablan del mismo pasaje, y
    por qué se dice que sí. Es la guarda de la ruta del día: el día y la ranura
    dicen cuál es la lectura, y esto comprueba que no se ha colado la de otra
    celebración del mismo día.

    Devuelve `'versículos'` cuando los dos conjuntos de versículos se tocan,
    `'libro y capítulo'` cuando alguna de las dos citas no se deja leer y sólo
    se pudo cotejar el sitio, y `None` cuando no es el mismo pasaje.
    """
    a, b = libro_y_capitulo(cita_lecc), libro_y_capitulo(cita_es)
    if not a or not b or a[1] != b[1] or not mismo_libro(a[0], b[0]):
        return None
    va, vb = versiculos(cita_lecc), versiculos(cita_es)
    if va and vb:
        return 'versículos' if (va[1] & vb[1]) else None
    return 'libro y capítulo'


# --------------------------------------------------------------------------
# la unidad del Misal: una clave canónica a los dos lados
# --------------------------------------------------------------------------
# El Misal latino nombra sus formularios del tiempo en latín y el calendario
# del proyecto en castellano, pero los dos dicen lo mismo: temporada, semana y
# día de la semana. Así que no hay que emparejar nombres: se reduce cada lado
# a la misma clave —`cua/3/5` es el viernes de la tercera semana de Cuaresma,
# lo escriba quien lo escriba— y lo que no reduzca a ninguna va al informe.

ROMANO = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7,
          'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13,
          'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18,
          'xix': 19, 'xx': 20, 'xxi': 21, 'xxii': 22, 'xxiii': 23,
          'xxiv': 24, 'xxv': 25, 'xxvi': 26, 'xxvii': 27, 'xxviii': 28,
          'xxix': 29, 'xxx': 30, 'xxxi': 31, 'xxxii': 32, 'xxxiii': 33,
          'xxxiv': 34}

FERIA_LA = {'dominica': 0, 'feria-secunda': 1, 'feria-tertia': 2,
            'feria-quarta': 3, 'feria-quinta': 4, 'feria-sexta': 5,
            'sabbato': 6}

DIA_ES = {'domingo': 0, 'lunes': 1, 'martes': 2, 'miercoles': 3,
          'jueves': 4, 'viernes': 5, 'sabado': 6}

# «1ª», «segunda», «II»: el proyecto escribe el ordinal de las tres maneras
ORDINAL_ES = {'primera': 1, 'segunda': 2, 'tercera': 3, 'cuarta': 4,
              'quinta': 5, 'sexta': 6, 'septima': 7, 'octava': 8,
              'novena': 9, 'decima': 10}

# Los formularios latinos que no se reducen por regla, porque el libro los
# titula con su nombre y no con su sitio. Son pocos y van nombrados.
UNIDAD_LA = {
    'tempore/in-nativitate-domini-ad-missam-in-vigilia': 'nav/vigilia',
    'tempore/in-nativitate-domini-ad-missam-in-nocte': 'nav/noche',
    'tempore/in-nativitate-domini-ad-missam-in-aurora': 'nav/aurora',
    'tempore/in-nativitate-domini-ad-missam-in-die': 'nav/dia',
    'tempore/in-nativitate-domini-s-familiae-iesu-mariae-et-ioseph':
        'nav/familia',
    'tempore/sollemnitas-sanctae-dei-genetricis-mariae': 'nav/mdd',
    'tempore/sollemnitas-dominica-ii-post-nativitatem': 'nav/dom2',
    'tempore/in-epiphania-domini-ad-missam-in-vigilia': 'epi/vigilia',
    'tempore/in-epiphania-domini-ad-missam-in-die': 'epi/dia',
    'tempore/in-feriis-temporis-nativitatis-in-baptismate-domini':
        'nav/bautismo',
    'tempore/tempus-quadragesimae-feria-quarta-cinerum': 'cua/ceniza',
    'tempore/feria-quarta-cinerum-feria-quinta-post-cineres': 'cua/ceniza/4',
    'tempore/feria-quarta-cinerum-feria-sexta-post-cineres': 'cua/ceniza/5',
    'tempore/feria-quarta-cinerum-sabbato-post-cineres': 'cua/ceniza/6',
    'tempore/hebdomada-sancta-dominica-in-palmis-de-passione-domini':
        'ss/ramos/procesion',
    'tempore/hebdomada-sancta-ad-missam': 'ss/ramos',
    'tempore/hebdomada-sancta-feria-ii-hebdomadae-sanctae': 'ss/1',
    'tempore/hebdomada-sancta-feria-iii-hebdomadae-sanctae': 'ss/2',
    'tempore/hebdomada-sancta-feria-iv-hebdomadae-sanctae': 'ss/3',
    'tempore/feria-v-hebdomadae-sanctae-ad-missam-chrismatis': 'ss/crismal',
    'tempore/feria-v-in-cena-domini-ad-missam-vespertinam': 'tri/cena',
    'tempore/dominica-paschae-in-resurrectione-domini-vigilia-paschalis-in-'
    'nocte-sancta': 'tri/vigilia',
    'tempore/vigilia-paschalis-in-nocte-sancta-ad-missam-in-die': 'pas/dia',
    'tempore/feria-quarta-ad-missam-matutinam': 'pas/6/3',
    'tempore/in-ascensione-domini-ad-missam-in-vigilia': 'asc/vigilia',
    'tempore/in-ascensione-domini-ad-missam-in-die': 'asc/dia',
    'tempore/in-ascensione-domini-feria-quinta': 'pas/6/4',
    'tempore/in-ascensione-domini-feria-sexta': 'pas/6/5',
    'tempore/in-ascensione-domini-sabbato': 'pas/6/6',
    'tempore/in-ascensione-domini-dominica-vii-paschae': 'pas/7/0',
    'tempore/sabbato-ad-missam-matutinam': 'pas/7/6',
    'tempore/dominica-pentecostes-ad-missam-in-vigilia': 'pen/vigilia',
    'tempore/dominica-pentecostes-ad-missam-in-die': 'pen/dia',
    'tempore/in-sollemnitatibus-domini-per-annum-occurrentibus-sanctissimae-'
    'trinitatis': 'sol/trinidad',
    'tempore/in-sollemnitatibus-domini-per-annum-occurrentibus-sanctissimi-'
    'corporis-et-sanguinis-christi': 'sol/corpus',
    'tempore/in-sollemnitatibus-domini-per-annum-occurrentibus-sacratissimi-'
    'cordis-iesu': 'sol/corazon',
    'tempore/in-sollemnitatibus-domini-per-annum-occurrentibus-domini-nostri-'
    'iesu-christi-universorum-regis': 'sol/rey',
}


def unidad_latina(k, v, avisos):
    """La clave canónica de un formulario latino del tiempo, o None."""
    if k in UNIDAD_LA:
        return UNIDAD_LA[k]
    s = k.split('/', 1)[1]

    m = re.match(r'^tempus-adventus-dominica-([ivx]+)-adventus$', s)
    if m:
        return 'adv/%d/0' % ROMANO[m.group(1)]
    m = re.match(r'^dominica-([ivx]+)-adventus-(.+)$', s)
    if m and m.group(2) in FERIA_LA:
        return 'adv/%d/%d' % (ROMANO[m.group(1)], FERIA_LA[m.group(2)])
    m = re.match(r'^die-(\d+)-decembris-de-[iv]+-die-infra-octavam', s)
    if m:
        return 'nav/dic%d' % int(m.group(1))
    m = re.match(r'^die-(\d+)-decembris(-ad-missam-matutinam)?$', s)
    if m:
        return 'adv/dic/%d' % int(m.group(1))
    m = re.match(r'^in-feriis-temporis-nativitatis-(.+)$', s)
    if m and m.group(1) in FERIA_LA:
        return 'nav/feria/%d' % FERIA_LA[m.group(1)]
    m = re.match(r'^tempus-quadragesimae-dominica-([ivx]+)-in-quadragesima$',
                 s)
    if m:
        return 'cua/%d/0' % ROMANO[m.group(1)]
    m = re.match(r'^dominica-([ivx]+)-in-quadragesima-(.+)$', s)
    if m and m.group(2) in FERIA_LA:
        return 'cua/%d/%d' % (ROMANO[m.group(1)], FERIA_LA[m.group(2)])
    m = re.match(r'^dominica-paschae-in-resurrectione-domini-feria-([ivx]+)-'
                 r'infra-octavam-paschae$', s)
    if m:
        return 'pas/oct/%d' % (ROMANO[m.group(1)] - 1)
    if s == ('dominica-paschae-in-resurrectione-domini-sabbato-infra-octavam-'
             'paschae'):
        return 'pas/oct/6'
    m = re.match(r'^dominica-paschae-in-resurrectione-domini-dominica-([ivx]+)'
                 r'-paschae$', s)
    if m:
        return 'pas/%d/0' % ROMANO[m.group(1)]
    m = re.match(r'^dominica-([ivx]+)-paschae-(.+)$', s)
    if m and m.group(2) in FERIA_LA:
        return 'pas/%d/%d' % (ROMANO[m.group(1)], FERIA_LA[m.group(2)])
    m = re.match(r'^missae-dominicales-et-cotidianae-(?:dominica|hebdomada)-'
                 r'([ivx]+)-per-annum$', s)
    if m:
        return 'to/%d' % ROMANO[m.group(1)]
    avisos.append(('latino del tiempo sin unidad', k, ' / '.join(v['titulo'])))
    return None


# Lo que el calendario del proyecto titula con nombre propio. La clave de la
# izquierda es el identificador de la celebración, que no cambia.
UNIDAD_ES = {
    'd1_0_0': 'nav/vigilia', 'd1_0_1': 'nav/noche', 'd1_0_2': 'nav/aurora',
    'd1_0_3': 'nav/dia',
    'd1_1_0': 'nav/familia', 'd1_1_1': 'nav/dic29', 'd1_1_2': 'nav/dic30',
    'd1_1_3': 'nav/dic31', 'd1_1_4': 'nav/mdd',
    'd1_2_0': 'nav/dom2', 'd1_4_0': 'epi/dia', 'd1_6_0': 'nav/bautismo',
    'd2_0_0': 'cua/ceniza', 'd2_0_1': 'cua/ceniza/4',
    'd2_0_2': 'cua/ceniza/5', 'd2_0_3': 'cua/ceniza/6',
    'd2_6_0': 'ss/ramos', 'd2_6_1': 'ss/1', 'd2_6_2': 'ss/2',
    'd2_6_3': 'ss/3', 'd2_6_4': 'ss/crismal',
    'd3_0_0': 'tri/cena', 'd3_0_1': 'tri/pasion', 'd3_0_2': 'tri/vigilia',
    'd3_0_3': 'pas/dia',
    'd3_7_0': 'asc/dia', 'd3_9_0': 'pen/dia',
    'd4_0_0': 'sol/trinidad', 'd4_0_1': 'sol/corpus',
    'd4_0_2': 'sol/corazon',
    'd5_33_0': 'sol/rey',
}

SEMANA_DE = {'adviento': 'adv', 'cuaresma': 'cua', 'pascua': 'pas',
             'tiempo ordinario': 'to'}


def semanal(temporada, semana, dia):
    """La clave de un día de una semana del tiempo.

    En el tiempo ordinario el día no entra: el Misal imprime **un** formulario
    por semana —«HEBDOMADA XI PER ANNUM»— y es el que se reza el domingo y los
    seis días siguientes. En Adviento, Cuaresma y Pascua sí, porque ahí el
    Misal da un formulario propio a cada feria.
    """
    if temporada == 'to':
        return 'to/%d' % semana
    return '%s/%d/%d' % (temporada, semana, dia)


def unidad_es(cel, titulo, avisos):
    """La clave canónica de una celebración del tiempo del proyecto, o None."""
    if cel in UNIDAD_ES:
        return UNIDAD_ES[cel]
    t = sinac(titulo)

    # «Lunes de la octava de Pascua»
    m = re.match(r'^(\w+) de la octava de pascua$', t)
    if m and m.group(1) in DIA_ES:
        return 'pas/oct/%d' % DIA_ES[m.group(1)]
    # «17 de diciembre»
    m = re.match(r'^(\d+) de diciembre$', t)
    if m:
        return 'adv/dic/%d' % int(m.group(1))
    # «7 de enero — Lunes después de Epifanía»
    m = re.match(r'^\d+ de enero.* (\w+) despues de epifania$', t)
    if m and m.group(1) in DIA_ES:
        return 'nav/feria/%d' % DIA_ES[m.group(1)]
    # «2 de enero»: las ferias de antes de la Epifanía
    m = re.match(r'^(\d+) de enero$', t)
    if m:
        return 'nav/ante/%d' % int(m.group(1))
    # «Domingo I de Adviento», «Domingo II del Tiempo Ordinario»
    m = re.match(r'^domingo ([ivx]+) del? (.+)$', t)
    if m and m.group(2) in SEMANA_DE:
        return semanal(SEMANA_DE[m.group(2)], ROMANO[m.group(1)], 0)
    # «Lunes de la 1ª semana de Adviento», «… de la segunda semana de Pascua»
    m = re.match(r'^(\w+) de la (\d+)[ªa]? semana del? (.+)$', t) or \
        re.match(r'^(\w+) de la (\w+) semana del? (.+)$', t)
    if m and m.group(1) in DIA_ES and m.group(3) in SEMANA_DE:
        n = m.group(2)
        n = int(n) if n.isdigit() else ORDINAL_ES.get(n)
        if n:
            return semanal(SEMANA_DE[m.group(3)], n, DIA_ES[m.group(1)])
    if t == 'misa de libre eleccion':
        return None
    avisos.append(('celebración del tiempo sin unidad', cel, titulo))
    return None


# --------------------------------------------------------------------------
# el santoral: la fecha, y cuando la fecha no basta, el nombre
# --------------------------------------------------------------------------
# El Misal latino fecha sus formularios del santoral («Die 13 ianuarii»), y el
# santoral del proyecto también, así que la fecha empareja 144 de los 193. Los
# 49 restantes son justo los mayores —la Anunciación, san José, la Asunción,
# Todos los Santos, la Inmaculada— y no es casualidad: son los que el Misal
# titula con capitular, y la fase 1 se come la primera letra del rótulo del
# mes («IANUARIUS» → `anuarius`) y pierde con ella el renglón de la fecha. Es
# un defecto de la fase 1, está medido y va al informe; aquí se repara sin
# inventar nada, por dos caminos que se comprueban uno contra otro:
#
#   · el orden del libro, que no retrocede: un formulario sin fecha entre el
#     del 24 de enero y el del 26 está en el 25;
#   · el nombre, que en latín y en castellano es casi el mismo una vez que se
#     pliegan las terminaciones y el «ct» que el castellano hace «t»
#     (sanctorum → santos).
#
# El umbral del parecido no se elige a ojo: los 144 formularios que sí traen
# fecha son la prueba, porque de ellos se conoce la pareja buena, y el informe
# imprime la distribución.

HONOR = {'s', 'ss', 'sancti', 'sanctae', 'beatae', 'beati', 'san', 'santa',
         'santo', 'beato', 'beata', 'de', 'del', 'la', 'las', 'los', 'el',
         'y', 'et', 'vel', 'in', 'e', 'ad', 'missam', 'die',
         'nuestra', 'nuestro', 'senora', 'senor'}

# Las cuatro parejas que ni la fecha ni el nombre pueden decidir, y por qué.
# El latín y el castellano llaman a estos santos con palabras distintas
# —Ludovicus es Luis, Elisabeth es Isabel, Stephanus es Esteban—, así que el
# parecido del nombre vale cero, y el orden del libro no basta donde el día
# trae dos celebraciones: el 25 de agosto son san Luis y san José de
# Calasanz, y elegir por orden sería elegir a ciegas.
PUENTE_SANTORAL = {
    'sanctis/in-assumptione-beatae-mariae-virginis-s-ludovici': 'st_0825_121',
    'sanctis/in-assumptione-beatae-mariae-virginis-s-stephani-hungariae':
        'st_0816_114',
    'sanctis/iulius-s-elisabeth-lusitaniae': 'st_0704_84',
    'sanctis/in-commemoratione-omnium-fidelium-defunctorum-s-elisabeth-'
    'hungariae': 'st_1117_172',
}

MESES_LA = {'ianuarii': 1, 'februarii': 2, 'martii': 3, 'aprilis': 4,
            'maii': 5, 'iunii': 6, 'iulii': 7, 'augusti': 8,
            'septembris': 9, 'octobris': 10, 'novembris': 11,
            'decembris': 12}


def pliega(p):
    """Una palabra plegada, para que el latín y el castellano se reconozcan.

    El castellano hace «t» el «ct» latino (sanctorum → santos), «f» el «ph»
    (Philippi → Felipe), «e» el «æ» (præsentatione → presentación), «i» la
    «y» y la «j» (martyr → mártir, Iudae → Judas), y dobla menos consonantes.
    Plegado eso, las dos palabras empiezan igual, y es por el principio por
    donde se comparan: la terminación es justamente lo que cambia.
    """
    p = sinac(p)
    for a, b in (('ae', 'e'), ('oe', 'e'), ('ct', 't'), ('ph', 'f'),
                 ('th', 't'), ('y', 'i'), ('j', 'i'), ('k', 'c'),
                 ('qu', 'c'), ('h', ''), ('v', 'b'), ('z', 's'), ('x', 's')):
        p = p.replace(a, b)
    return re.sub(r'([a-z])\1', r'\1', p)


def misma_palabra(x, y):
    """Si dos palabras plegadas son la misma. Cuatro letras iguales por el
    principio bastan —«dotoris» y «dotor», «santorum» y «santos»—, y tres
    sólo cuando una de las dos no tiene más: con tres en palabras largas
    «martyris» pasaría por «Marcos»."""
    n = 0
    for a, b in zip(x, y):
        if a != b:
            break
        n += 1
    return n >= 4 or (n >= 3 and min(len(x), len(y)) <= 4)


BOILERPLATE = re.compile(r'^(?:ad missam(?: in (?:vigilia|die|nocte|aurora))?'
                         r'|\d+|[ivx]+\.?|[a-e]\.?)$', re.I)


def nombre_latino(v):
    """El nombre con que se reconoce un formulario latino.

    Lo normal es el título, sin el renglón de la fecha, que no nombra al santo
    y mete palabras que no son suyas. Pero hay formularios cuyo título es sólo
    «Ad Missam in Vigilia» o un número, porque el nombre está en el rótulo de
    la sección: ahí se toma el rótulo, que es lo que el libro dice.
    """
    ts = [t for t in v['titulo']
          if not re.match(r'^Die \d+ \w+$', t.strip())
          and not BOILERPLATE.match(t.strip())]
    if ts:
        return ' '.join(ts)
    return (v['ruta'] or [''])[0]


def trozos(nombre):
    """Las palabras con que se compara un nombre, sin los honoríficos.

    El honorífico se quita, pero sólo cuando va delante de algo: «santo» es
    honorífico en «Santa Marta» y es el nombre en «Espíritu Santo» y en «Todos
    los Santos». La regla es la posición, que es la que el castellano usa: lo
    último que queda es el nombre, y no se tira.
    """
    nombre = re.sub(r'^Die \d+ \w+\b', '', nombre.strip())
    ps = [p for p in re.split(r'[^0-9a-zà-ÿ]+', sinac(nombre))
          if p and len(p) > 2 and not p.isdigit()]
    return {pliega(p) for i, p in enumerate(ps)
            if p not in HONOR or i == len(ps) - 1}


def parecido(a, b):
    """0 a 1. Se divide por el más corto: «S. Hilarii, episcopi et Ecclesiæ
    doctoris» y «San Hilario, obispo y doctor de la Iglesia» no tienen el
    mismo número de palabras y no por eso dicen cosas distintas."""
    ta, tb = trozos(a), trozos(b)
    if not ta or not tb:
        return 0.0
    casan = sum(1 for x in ta if any(misma_palabra(x, y) for y in tb))
    return min(casan, min(len(ta), len(tb))) / min(len(ta), len(tb))


def puntua(a, b):
    """Como `parecido`, pero para elegir entre varios rótulos que empatan.

    «Misa por los ministros de la Iglesia» se parece del todo a «POR LA
    IGLESIA» y del todo a «POR LOS MINISTROS DE LA IGLESIA», porque la
    proporción se divide por el más corto. Entre los dos manda el que casa más
    palabras, y a igualdad de palabras casadas el que deja menos sin casar:
    ésa es la diferencia entre el rótulo general y el que de verdad nombra la
    misa.
    """
    ta, tb = trozos(a), trozos(b)
    if not ta or not tb:
        return (0.0, 0, 0)
    casan = sum(1 for x in ta if any(misma_palabra(x, y) for y in tb))
    casan = min(casan, len(ta), len(tb))
    return (casan / min(len(ta), len(tb)), casan, casan - len(tb))


def fecha_de_latino(k, v):
    """(mes, día) de un formulario del santoral latino, si el libro la da."""
    if v.get('dia'):
        return (v['dia']['mes'], v['dia']['dia'])
    for t in v['titulo']:
        m = re.match(r'^Die (\d+) (\w+)', t)
        if m and m.group(2).lower() in MESES_LA:
            return (MESES_LA[m.group(2).lower()], int(m.group(1)))
    return None


def corchetes(lat):
    """Para cada formulario del santoral latino sin fecha, entre qué dos
    fechas lo deja el orden del libro. El libro va en orden y el día no
    retrocede: eso acota, y a veces basta para fijarlo."""
    ks = sorted((k for k in lat if k.startswith('sanctis/')),
                key=lambda k: lat[k]['linea'])
    fechas = [fecha_de_latino(k, lat[k]) for k in ks]
    fuera = {}
    for i, k in enumerate(ks):
        if fechas[i]:
            continue
        antes = next((fechas[j] for j in range(i - 1, -1, -1) if fechas[j]),
                     None)
        luego = next((fechas[j] for j in range(i + 1, len(ks)) if fechas[j]),
                     None)
        fuera[k] = (antes, luego)
    return ks, fechas, fuera


def dentro(f, antes, luego):
    """Si la fecha (mes, día) cae entre las dos del corchete."""
    if antes and f < antes:
        return False
    if luego and f > luego:
        return False
    return True


# --------------------------------------------------------------------------
# los comunes
# --------------------------------------------------------------------------
# Siete en el proyecto y sesenta formularios en el Misal, porque el Misal
# abre cada común en sus casos —«pro uno martyre», «pro pluribus»— y el
# leccionario da un solo juego de lecturas para todos. Así que la pareja es
# uno a varios, y los varios entran como alternativas en el orden del libro.

COMUNES = {
    '5223COMDBA': 'communia/in-anniversario-dedicationis-',
    '5224COMSVI': 'communia/commune-beatae-mariae-virginis-',
    '5225COMMAR': 'communia/commune-martyrum-',
    '5226COMPAS': 'communia/commune-pastorum-',
    '5227COMDOC': 'communia/commune-doctorum-ecclesiae-',
    '5228COMVIR': 'communia/commune-virginum-',
    '5229COMSAN': 'communia/commune-sanctorum-et-sanctarum-',
}


# --------------------------------------------------------------------------
# las misas por diversas necesidades, votivas, rituales y de difuntos
# --------------------------------------------------------------------------
# Éstas son los 171 formularios que ninguna fecha alcanza, y el castellano de
# los misalitos no las trae: de ellas sólo hay latín, y es lo que se decidió
# mostrar. La pareja no hace falta adivinarla por el nombre, porque el
# leccionario las numera **en el orden del Misal y con los títulos del Misal
# traducidos**, y cuando junta varias en un solo juego de lecturas las nombra
# todas separadas por raya: «POR LA PATRIA O POR LA CIUDAD — POR LOS QUE
# GOBIERNAN — …» son cinco del Misal con una sola lectura. Así que se recorren
# las dos listas en paralelo, consumiendo del Misal tantos formularios como
# títulos en mayúscula trae el del leccionario, y lo que no cuadre se escribe.

def partes_del_titulo(t):
    """Los títulos que un rótulo del leccionario junta con raya. Sólo cuentan
    los que van en mayúscula: los demás son remisiones a una celebración
    («POR LA FAMILIA — La Sagrada Familia»), no otro formulario del Misal."""
    trozos = [x.strip() for x in re.split(r'\s[—–-]\s', t)]
    caps = [x for x in trozos if x and x == x.upper()]
    return caps or trozos[:1]


def items_latinos(lat, parte):
    """Los formularios de una parte del Misal, agrupados por el número de
    item que el libro les da: `…-1-pro-ecclesia-a` y `…-b` son el mismo item
    con dos formularios, y el leccionario les da una sola lectura."""
    ks = sorted((k for k in lat if k.startswith(parte + '/')),
                key=lambda k: lat[k]['linea'])
    grupos, visto = [], {}
    for k in ks:
        s = k.split('/', 1)[1]
        # el item es todo menos la letra o el número final de variante
        base = re.sub(r'-(?:[a-e]|\d+)$', '', s)
        base = re.sub(r'-(?:[a-e])$', '', base)
        if base in visto:
            grupos[visto[base]][1].append(k)
        else:
            visto[base] = len(grupos)
            grupos.append((base, [k]))
    return grupos


# --------------------------------------------------------------------------
# la carga
# --------------------------------------------------------------------------

def carga():
    def jj(*p):
        with open(os.path.join(*p), encoding='utf-8') as f:
            return json.load(f)
    d = {
        'lat': jj(DATOS, 'misal_latino.json'),
        'pref_es': jj(DATOS, 'prefacios_es.json'),
        'propios': jj(LIBRO, 'propios_es.json'),
        'pericopas': jj(LIBRO, 'pericopas_es.json'),
        'pref_propios': jj(LIBRO, 'prefacios_propios_es.json'),
        'sueltos': jj(LIBRO, 'sueltos_es.json'),
        'dias': jj(LIBRO, 'dias_es.json'),
        'cal': jj(DATA, 'calendario_completo.json'),
        'indice': jj(APP, 'indice.json')['secciones'],
        'imaster': jj(DATA, 'index_master.json'),
    }
    return d


def celebraciones_del_indice(indice):
    """clave del leccionario → (celebración, título, sección, etiqueta), y la
    lista de celebraciones en el orden del índice."""
    porclave, cels = {}, []
    for sec in indice:
        for g in sec['g']:
            for dd in g['d']:
                cels.append((dd['s'], dd['t'], sec['t'], g.get('t') or ''))
                for b in dd.get('b') or []:
                    porclave[b['k']] = (dd['s'], dd['t'], sec['t'],
                                        b.get('e') or '')
    return porclave, cels


# --------------------------------------------------------------------------
# el puente: celebración ↔ formulario del Misal
# --------------------------------------------------------------------------

def otros_del_santoral(indice):
    """La sección «otros formularios del propio de los santos» como si fuera
    santoral: diecinueve celebraciones que el calendario del proyecto no pone
    ningún día —no están en el general— pero que el leccionario sí trae, y su
    identificador lleva la fecha detrás (`lv_5122ta0809`, el 9 de agosto)."""
    salida = []
    for g in indice[8]['g']:
        for dd in g['d']:
            m = re.search(r'ta(\d{2})(\d{2})(?:_\d+)?$', dd['s'])
            if not m:
                continue
            mes, dia = int(m.group(1)), int(m.group(2))
            if not (1 <= mes <= 12 and 1 <= dia <= 31):
                continue
            salida.append({'slug': dd['s'], 'titulo': dd['t'], 'mes': mes,
                           'dia': dia})
    return salida


def puente_santoral(lat, cal, inf_filas, avisos, otros=()):
    """celebración del santoral → formulario latino, por fecha y por nombre.

    Tres caminos, y cada uno queda escrito: la fecha cuando el libro la da y
    es la de una sola celebración; la fecha más el nombre cuando ese día hay
    varias; y el orden del libro más el nombre para los 49 formularios a los
    que la fase 1 les comió el renglón de la fecha.
    """
    porfecha = defaultdict(list)
    for e in list(cal['santoral']) + list(otros):
        if e.get('mes') and e.get('dia'):
            porfecha[(e['mes'], e['dia'])].append(e)
    por_slug = {e['slug']: e for cs in porfecha.values() for e in cs}

    ks, fechas, fuera = corchetes(lat)
    pareja, de_quien = {}, {}

    # 0: las parejas que ni la fecha ni el nombre pueden decidir
    for k, slug in PUENTE_SANTORAL.items():
        if k not in lat:
            avisos.append(('la tabla nombra un latino que no existe', k, slug))
            continue
        if slug not in por_slug:
            avisos.append(('la tabla nombra una celebración que no existe',
                           k, slug))
            continue
        e = por_slug[slug]
        pareja[k], de_quien[slug] = slug, k
        inf_filas.append((slug, k, 'la tabla', None,
                          '%02d-%02d' % (e['mes'], e['dia']), e['titulo']))

    # 1 y 2: los que traen fecha
    for k, f in zip(ks, fechas):
        if not f or k in pareja:
            continue
        cands = [c for c in porfecha.get(f, []) if c['slug'] not in de_quien]
        if not cands:
            avisos.append(('latino con fecha que el santoral no tiene', k,
                           '%02d-%02d' % f))
            continue
        if len(cands) == 1:
            elegido, via, sc = cands[0], 'fecha', None
        else:
            puntos = sorted(((parecido(nombre_latino(lat[k]), c['titulo']), c)
                             for c in cands), key=lambda x: -x[0])
            elegido, sc = puntos[0][1], puntos[0][0]
            via = 'fecha y nombre'
            if sc < 0.2:
                avisos.append(('varias celebraciones el mismo día y ninguna '
                               'se parece', k, '%02d-%02d: %s' %
                               (f[0], f[1], ', '.join(c['titulo']
                                                      for c in cands))))
                continue
        if elegido['slug'] in de_quien:
            avisos.append(('dos latinos para la misma celebración',
                           elegido['slug'], '%s y %s'
                           % (de_quien[elegido['slug']], k)))
            continue
        pareja[k] = elegido['slug']
        de_quien[elegido['slug']] = k
        inf_filas.append((elegido['slug'], k, via, sc,
                          '%02d-%02d' % f, elegido['titulo']))

    # 3: los que no traen fecha, por el corchete del libro y el nombre
    gaps = defaultdict(list)
    for k in ks:
        if k in fuera:
            gaps[fuera[k]].append(k)
    alternos = {}
    for (antes, luego), sinfecha in sorted(
            gaps.items(), key=lambda x: (x[0][0] or (0, 0))):
        grupos = agrupa_variantes([k for k in sinfecha if k not in pareja])
        libres = [e for f, cs in sorted(porfecha.items()) for e in cs
                  if dentro(f, antes, luego) and f != antes and f != luego
                  and e['slug'] not in de_quien]
        elegidos = casa_en_orden([g[0] for g in grupos], libres, lat)
        for (jefe, resto), (e, sc) in zip(grupos, elegidos):
            if e is None:
                avisos.append(('latino sin fecha y sin celebración que lo '
                               'explique', jefe, 'entre %s y %s; libres: %s'
                               % (antes, luego,
                                  ', '.join(x['titulo'] for x in libres)
                                  or 'ninguna')))
                continue
            pareja[jefe] = e['slug']
            de_quien[e['slug']] = jefe
            if resto:
                alternos[e['slug']] = resto
            inf_filas.append((e['slug'], jefe,
                              'orden del libro y nombre' if sc else
                              'orden del libro, sin que el nombre lo confirme',
                              sc, '%02d-%02d' % (e['mes'], e['dia']),
                              e['titulo']))
    return pareja, de_quien, alternos


def agrupa_variantes(ks):
    """Los formularios que son del mismo día, juntos.

    La Natividad de san Juan Bautista trae en el Misal la misa de la vigilia y
    la del día, y los Fieles Difuntos tres formularios numerados: son una sola
    celebración del calendario con varias misas, no varias celebraciones. Se
    reconocen porque el libro los cuelga del mismo rótulo, que es lo que el
    identificador guarda delante de `-ad-missam-…` o del número. El que manda
    es la misa del día, y los demás quedan como alternativas en el orden del
    libro, que es lo que hace falta para poder elegirlas.
    """
    grupos, donde = [], {}
    for k in ks:
        s = k.split('/', 1)[1]
        base = re.sub(r'-ad-missam(-in-(?:vigilia|die|nocte|aurora))?$', '', s)
        base = re.sub(r'-\d+$', '', base)
        if base in donde:
            grupos[donde[base]].append(k)
        else:
            donde[base] = len(grupos)
            grupos.append([k])
    salida = []
    for g in grupos:
        jefe = next((k for k in g if k.endswith('-in-die')), g[0])
        salida.append((jefe, [k for k in g if k != jefe]))
    return salida


def casa_en_orden(sinfecha, libres, lat):
    """Empareja dos listas que van las dos en orden del libro, sin cruzarlas.

    Los formularios sin fecha de un mismo hueco van en el orden del Misal, y
    las celebraciones libres de ese hueco en el orden del calendario: la
    pareja, por tanto, no puede cruzarse. Con eso y el parecido del nombre, la
    mejor asignación es un camino, y se calcula entero en vez de ir eligiendo
    lo mejor de cada uno por separado —que es lo que cruza las parejas—.
    """
    n, mm = len(sinfecha), len(libres)
    s = [[parecido(nombre_latino(lat[k]), e['titulo']) for e in libres]
         for k in sinfecha]
    # mejor[i][j]: mejor puntuación emparejando los i primeros latinos con los
    # j primeros libres
    mejor = [[0.0] * (mm + 1) for _ in range(n + 1)]
    de = [[None] * (mm + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(0, mm + 1):
            # dejar el latino i sin pareja
            a = mejor[i - 1][j] - 0.01
            mejor[i][j], de[i][j] = a, 'salta'
            if j:
                # una pareja que el nombre no confirma vale poco, pero más que
                # dejar los dos sueltos: el orden del libro ya es un testigo
                b = mejor[i - 1][j - 1] + (s[i - 1][j - 1] or 0.02)
                if b > mejor[i][j]:
                    mejor[i][j], de[i][j] = b, 'casa'
                c = mejor[i][j - 1]
                if c > mejor[i][j]:
                    mejor[i][j], de[i][j] = c, 'libre'
    # el camino de vuelta
    out = [None] * n
    i, j = n, mm
    while i > 0:
        if de[i][j] == 'casa':
            out[i - 1] = (libres[j - 1], s[i - 1][j - 1])
            i, j = i - 1, j - 1
        elif de[i][j] == 'libre':
            j -= 1
        else:
            out[i - 1] = (None, None)
            i -= 1
    return out


def puente_misas(lat, indice, avisos, inf_filas):
    """Las misas por diversas necesidades, votivas, rituales y de difuntos.

    El leccionario las numera en el orden del Misal y con sus títulos
    traducidos, así que se recorren las dos listas a la par. Cada rótulo del
    leccionario consume del Misal tantos items como títulos en mayúscula trae.
    """
    pareja = {}
    plan = [(10, ['necessitatibus', 'votivae']),
            (11, ['rituales', 'defunctorum'])]
    for si, partes in plan:
        destino = [dd for g in indice[si]['g'] for dd in g['d']]
        items = [g for p in partes for g in items_latinos(lat, p)]
        i = 0
        for dd in destino:
            n = len(partes_del_titulo(dd['t']))
            toma = items[i:i + n]
            i += n
            if not toma:
                avisos.append(('rótulo del leccionario sin formulario latino',
                               dd['s'], dd['t'][:60]))
                continue
            pareja[dd['s']] = [k for _, ks in toma for k in ks]
            inf_filas.append((dd['s'], toma[0][1][0], 'orden del libro',
                              None, '%d item%s' % (n, '' if n == 1 else 's'),
                              dd['t'][:60]))
        if i < len(items):
            avisos.append(('items del Misal que ningún rótulo del leccionario '
                           'consume', partes[0],
                           ', '.join(b for b, _ in items[i:])))
    return pareja


# --------------------------------------------------------------------------
# la unidad de cualquier celebración
# --------------------------------------------------------------------------
# Las cuatro fases nombran las celebraciones de cinco maneras —`d5_0_1` el
# calendario, `st_0113_2` el santoral, `comun_5226COMPAS` los comunes,
# `lvi_6009plla` el leccionario, y `vot_…`, `san_…` y `md_…` lo que la fase 4
# tuvo que inventar porque el misalito lo rezaba y el calendario no lo tiene—.
# La unidad las junta: dos identificadores con la misma unidad son el mismo
# formulario del Misal, y ahí es donde la mayoría de testigos vuelve a tener
# sentido.

SEMANA_TO = re.compile(r'^vot_misa-de-la-([ivx]+)-semana-del-tiempo-'
                       r'ordinario$')


# Un día puede tener varias misas, y la fase 4 las separó con un sufijo detrás
# del identificador: `md_12-25#misa-de-la-aurora`, `st_1102_162#segunda-misa`,
# `d2_6_4#misa-vespertina-de-la-cena-del-senor`. El sufijo dice qué misa es, y
# el día dice de qué celebración. Son los días mayores del año —las tres misas
# de Navidad, las tres de los Difuntos, la vespertina de la Cena del Señor, las
# vigilias— y con el sufijo sin resolver se quedaban fuera.

SUFIJO_FIJO = {
    'misa-de-noche-buena': 'nav/noche',
    'misa-de-la-aurora': 'nav/aurora',
    'misa-vespertina-de-la-cena-del-senor': 'tri/cena',
}

ORDEN_MISA = {'primera-misa': '', 'segunda-misa': '#2', 'tercera-misa': '#3'}


def primera_del_dia(cal, fecha):
    """La celebración que el calendario pone primero ese día."""
    c = cal['fechas'].get(fecha, {}).get('c') or []
    return c[0][0] if c else None


def manda_una(fechas, saca):
    """De qué celebración son estos días, admitiendo una desviada.

    Es la misma regla que la fase 4 tuvo que admitir y por la misma razón: la
    fuente también traslada. El 24 de junio de 2022 fue el Sagrado Corazón y el
    misalito pasó la vigilia de san Juan Bautista un día antes, de modo que uno
    de los cuatro días apunta a otra celebración. Con cuatro días o más se
    admite uno desviado; con menos, no.
    """
    cuenta = Counter(filter(None, (saca(f) for f in fechas)))
    if not cuenta:
        return None
    cel, n = cuenta.most_common(1)[0]
    if n == len(fechas) or (len(fechas) >= 4 and n == len(fechas) - 1):
        return cel
    return None


# La vigilia que el Misal imprime aparte, cuando la tiene: su unidad ya existe
# y no hay que inventarle otra.
VIGILIA_DE = {'nav/dia': 'nav/vigilia', 'epi/dia': 'epi/vigilia',
              'asc/dia': 'asc/vigilia', 'pen/dia': 'pen/vigilia'}


def unidad_de_misa(cel, titulo, avisos, fechas_de, cal, titulo_de):
    """La unidad de una de las varias misas de un día, por su sufijo."""
    base, suf = cel.split('#', 1)
    fechas = fechas_de.get(cel) or []
    if suf in SUFIJO_FIJO:
        return SUFIJO_FIJO[suf]

    def unidad(c):
        return unidad_de_cel(c, (titulo_de or {}).get(c) or titulo, avisos,
                             fechas_de, cal, titulo_de)

    if suf == 'misa-del-dia':
        # «misa del día» es la de Navidad el 25 de diciembre, y en cualquier
        # otra fecha es la principal de la celebración, que es la base
        if fechas and all(f[5:] == '12-25' for f in fechas):
            return 'nav/dia'
        return unidad(base)
    if suf in ORDEN_MISA:
        c = manda_una(fechas, lambda f: primera_del_dia(cal, f))
        if c:
            return unidad(c) + ORDEN_MISA[suf]
    if suf == 'misa-vespertina-de-la-vigilia':
        c = manda_una(fechas, lambda f: primera_del_dia(
            cal, (date.fromisoformat(f) + timedelta(days=1)).isoformat()))
        if c:
            u = unidad(c)
            return VIGILIA_DE.get(u) or (u + '#vigilia')
    avisos.append(('misa de un día que el sufijo no sitúa', cel,
                   ', '.join(fechas) or 'sin días'))
    return 'cel/' + cel


def unidad_de_cel(cel, titulo, avisos, fechas_de=None, cal=None,
                  titulo_de=None):
    """La unidad del Misal a la que pertenece una celebración."""
    if '#' in cel:
        return unidad_de_misa(cel, titulo, avisos, fechas_de or {}, cal,
                              titulo_de)
    if cel.startswith('d') and re.match(r'^d\d+_\d+_\d+$', cel):
        u = unidad_es(cel, titulo, avisos)
        return u or ('cel/' + cel)
    m = re.match(r'^(?:comun_|lv_)(\d+com\w+)$', cel, re.I)
    if m:
        return 'com/' + m.group(1).lower()
    if cel.startswith(('lvi_', 'lviii_')):
        return 'misa/' + cel
    m = SEMANA_TO.match(cel)
    if m:
        # el misalito lo dice con su propio nombre: «Misa de la I Semana del
        # Tiempo Ordinario» es el formulario que el Misal titula HEBDOMADA I
        return 'to/%d' % ROMANO[m.group(1)]
    if cel.startswith('md_'):
        return 'fecha/' + cel[3:]
    if cel.startswith(('st_', 'san_', 'lv_')):
        return 'st/' + cel
    if cel.startswith(('vot_', 'anexo_')):
        return 'cel/' + cel
    avisos.append(('celebración de clase desconocida', cel, titulo or ''))
    return 'cel/' + cel


def puente_votivas(propios, misas, indice, inf_filas, avisos):
    """Las misas votivas que el misalito reza y el leccionario numera.

    En las ferias el editor elige a menudo una votiva —«Misa por los laicos»,
    «Misa del Espíritu Santo»—, y la fase 4 las guardó con el nombre que el
    misalito imprime. El leccionario las tiene todas, con el título del Misal
    traducido, así que la pareja se busca por el nombre, que aquí es
    castellano contra castellano y no latín contra castellano: el parecido
    sirve de otra manera, y se exige más.
    """
    destino = []
    for si in (10, 11):
        for g in indice[si]['g']:
            for dd in g['d']:
                if dd['t'].startswith('Leccionario'):
                    # el índice del proyecto no le guardó título a este
                    # bloque y dejó el de la sección: con eso no se puede
                    # emparejar, y emparejar con eso es peor que no hacerlo
                    avisos.append(('rótulo del leccionario sin título propio',
                                   dd['s'], dd['t']))
                    continue
                for t in partes_del_titulo(dd['t']):
                    destino.append((dd['s'], t))
    pareja = {}
    for cel in sorted(propios):
        if not cel.startswith('vot_') or SEMANA_TO.match(cel):
            continue
        # La fase 4 guardó como título el propio identificador, así que el
        # nombre sale de él: fuera el `vot_` y el `misa-` del principio, que
        # no dicen nada y además se parecen a todo.
        nombre = re.sub(r'^misa ', '', cel[4:].replace('-', ' '))
        puntos = sorted(((puntua(nombre, t), s, t) for s, t in destino),
                        key=lambda x: (tuple(-v for v in x[0]), x[1]))
        # se exige la mitad de las palabras, y que no haya un segundo rótulo
        # que empate con el primero: con dos empatados no se elige, se escribe
        mejor = puntos[0][0] if puntos else (0, 0, 0)
        segundo = next((p[0] for p in puntos[1:] if p[1] != puntos[0][1]),
                       (0, 0, 0))
        if mejor[0] >= 0.5 and mejor > segundo:
            pareja[cel] = puntos[0][1]
            inf_filas.append((cel, puntos[0][1], mejor[0], nombre,
                              puntos[0][2]))
        else:
            avisos.append(('votiva del misalito sin rótulo del leccionario',
                           cel, '%s (lo más parecido, %.2f: %s; el siguiente, '
                                '%.2f)' % (nombre, mejor[0],
                                           puntos[0][2] if puntos else '—',
                                           segundo[0])))
    return pareja


# --------------------------------------------------------------------------
# la cascada
# --------------------------------------------------------------------------

def mejor_de(cands, propios, ranura, vale=None):
    """De varias celebraciones que ofrecen la misma ranura, la que más
    testigos trae. Y si dos traen texto distinto, se dice.

    `vale` deja fuera a las que no son testigo bastante (ver `flojo`): sin
    él, la feria que se acaba de descartar por tener un solo testigo volvía
    a entrar por la puerta de al lado, como hermana de la misma unidad.
    """
    con = [(len(propios[c]['piezas'][ranura]['testigos']), c) for c in cands
           if ranura in propios[c]['piezas']
           and (vale is None or vale(c, propios[c]['piezas'][ranura]))]
    if not con:
        return None, []
    con.sort(key=lambda x: (-x[0], x[1]))
    jefe = con[0][1]
    otros = [c for _, c in con[1:]
             if propios[c]['piezas'][ranura]['texto'] !=
             propios[jefe]['piezas'][ranura]['texto']]
    return jefe, otros


def lo_impreso(propios, sueltos):
    """(fecha, nº de formulario) → {ranura: de dónde salió el texto}.

    Es la vuelta de los testigos: la fase 4 guardó, para cada pieza, los días
    en que la fuente la imprime; esto los vuelve a poner por día, para poder
    preguntar lo contrario —qué imprimió el misalito ese día en esa ranura—,
    que es lo que hace falta para el cuarto paso de la cascada.
    """
    por = defaultdict(dict)
    for cel, v in propios.items():
        for r, p in v['piezas'].items():
            for t in p['testigos']:
                por[t][r] = ('celebración', cel)
            for alt in p['variantes']:
                for t in alt['testigos']:
                    por[t][r] = ('celebración', cel)
    for i, s in enumerate(sueltos):
        for t in s['testigos']:
            por[t][s['ranura']] = ('suelto', i)
    return por


def dias_por_cel(dias):
    """celebración → los días en que la fase 4 le atribuyó un formulario."""
    por = defaultdict(list)
    for fecha, forms in dias.items():
        for i, f in enumerate(forms):
            if f.get('cel'):
                por[f['cel']].append('%s/%d' % (fecha, i))
    return por


def fechas_por_cel(dias_de, propios):
    """celebración → las fechas en que la fuente la imprime.

    Hacen falta las dos procedencias. El día nombra la celebración a la que se
    atribuyó su formulario, pero una pieza puede estar guardada bajo otro
    identificador —las tres misas del 25 de diciembre están en el día como
    `d1_0_1#misa-del-dia` y en las piezas como `md_12-25#misa-del-dia`—, y sin
    los testigos de la pieza esa misa se queda sin fechas y sin sitio.
    """
    por = defaultdict(set)
    for cel, ts in dias_de.items():
        por[cel] |= {t.split('/')[0] for t in ts}
    for cel, v in propios.items():
        for p in v['piezas'].values():
            por[cel] |= {t.split('/')[0] for t in p['testigos']}
            for alt in p['variantes']:
                por[cel] |= {t.split('/')[0] for t in alt['testigos']}
    return {c: sorted(fs) for c, fs in por.items()}


def otra_misa_entera(t, cel, dias):
    """Si ese día el editor imprimió, entera, otra misa que no es ésta.

    **El día que imprime otra misa no es testigo de la del calendario.** El
    domingo XXIX del tiempo ordinario es en México el DOMUND, y el misalito
    imprime la misa por la evangelización de los pueblos en siete de los
    nueve años del corpus; ocho de esos nueve lo dicen en el subtítulo y la
    fase 4 ya los atribuye a la votiva, pero el 20 de octubre de 2019 no lo
    dice —lo lleva en el título, «JORNADA MUNDIAL DE LAS MISIONES»— y
    seguía votando como si fuera el domingo. Con él, la ranura de la
    antífona de entrada tenía tres textos distintos y no entraba ninguno,
    teniendo la fuente impresa la del domingo —«Te invoco, Dios mío, porque
    tú me respondes»— dos años, el 17 de octubre de 2021 y el 16 de octubre
    de 2022, y letra por letra la misma.

    No se adivina: se mira lo que la fase 4 atribuyó pieza por pieza ese
    día. Si **todas** las ranuras que traen algo apuntan a una sola
    celebración, y es una votiva o una misa ritual y no ésta, ese día rezó
    aquella misa. Se exige que sean todas y que sean tres o más, porque dos
    ranuras coincidentes las repite el editor sin querer.
    """
    forms = dias.get(t.split('/')[0]) or []
    i = int(t.split('/')[1])
    if i >= len(forms):
        return False
    de = [c for c in (forms[i].get('propios') or {}).values() if c]
    if len(de) < 3 or len(set(de)) != 1:
        return False
    otra = de[0]
    return otra != cel and otra.split('#')[0].startswith(('vot_', 'rit_'))


def del_dia(cel, ranura, dias_de, impreso, dias):
    """Lo que el misalito imprimió en esa ranura los días de esa celebración.

    Es un testigo más flojo que los tres anteriores y hay que decirlo: el
    texto puede ser de otro formulario del Misal y el editor repetirlo —la
    oración sobre las ofrendas del Adviento sale en veintiún días de tres
    semanas distintas—, así que no prueba que la pieza **sea** de esta
    celebración. Pero sí prueba lo que ese día se rezó, que es lo que la app
    tiene que mostrar, y por eso entra marcado como «del día».

    Se exige que todos los días de la celebración que traen algo en esa ranura
    traigan lo mismo. Con uno que discrepe, no entra. Y no cuentan los días
    en que el editor imprimió **otra misa entera**, que es lo que dice
    `otra_misa_entera`: ésos no hablan de esta celebración.
    """
    vistos = {impreso.get(t, {}).get(ranura)
              for t in dias_de.get(cel, [])
              if not otra_misa_entera(t, cel, dias)}
    vistos.discard(None)
    if len(vistos) != 1:
        return None, len(vistos)
    return vistos.pop(), 1


def flojo(cel, unidad, ranura, p, propios, por_unidad):
    """Si una feria del tiempo ordinario basta como testigo de esa ranura.

    **En el tiempo ordinario el Misal da un formulario por semana**
    (`HEBDOMADA XI PER ANNUM`), y ese formulario es el del domingo: la feria
    no tiene oraciones suyas. Lo que el misalito imprime una feria de enero
    no es, por tanto, la feria, sino lo que el editor eligió ese año —que es
    el hallazgo que gobierna la fase 4—. Así que:

      · **si el domingo de esa semana trae la ranura, manda el domingo** y
        la feria no cuenta, tenga los testigos que tenga;
      · si no lo trae —la 1ª semana no tiene domingo, se lo lleva el Bautismo
        del Señor—, hace falta más de un testigo, porque uno solo puede ser
        una votiva.

    Medido sobre el fichero: **35 piezas** de trece ferias de enero y febrero
    se colaban así, y ninguna era la feria. Eran la misa por la unidad de los
    cristianos (la semana del 18 al 25 de enero: «Que todos sean uno, como
    tú, Padre, en mí y yo en ti»), la de difuntos («Ninguno de nosotros vive
    para sí mismo»), la de Santa María en sábado («Bendita eres Tú, Virgen
    María») y la de Guadalupe, que de ahí se repartía por el paso de la
    unidad a los seis días de su semana.

    El domingo nunca es flojo: ése sí lo imprime el misalito como lo que es.
    """
    # sólo el temporal: `_0` es el domingo en los identificadores del tiempo
    # (`d5_10_0`), y en el santoral ese mismo sufijo es otra cosa
    if not unidad.startswith('to/') or not cel.startswith('d') \
            or cel.endswith('_0'):
        return False
    for otro in por_unidad.get(unidad, []):
        if otro.startswith('d') and otro.endswith('_0') \
                and ranura in propios.get(otro, {}).get('piezas', {}):
            return True
    return not p or len(p['testigos']) < 2


def resuelve(cel, unidad, propios, por_unidad, sueltos_de, comunes_de,
             latino, lat, dias_de, impreso, sueltos, dias):
    """Las seis ranuras de un formulario, cada una con el camino por el que se
    resolvió. El orden de la cascada es el del plan: la propia celebración, el
    mismo formulario del Misal, un texto suelto que cae en él, lo que el
    misalito imprimió esos días, el común que la celebración ofrece, el latín,
    y nada."""
    piezas, discrepan = {}, []
    hermanos = [c for c in por_unidad.get(unidad, []) if c != cel]
    flojas = []
    for r in RANURAS:
        p = propios.get(cel, {}).get('piezas', {}).get(r)
        if p and flojo(cel, unidad, r, p, propios, por_unidad):
            flojas.append((r, p['testigos'][0], len(p['testigos'])))
            p = None
        if p:
            piezas[r] = {'f': 'misalito', 'via': 'celebración', 'de': cel,
                         'r': r, 't': len(p['testigos']),
                         'v': len(p['variantes'])}
            continue
        jefe, otros = mejor_de(
            hermanos, propios, r,
            lambda c, q: not flojo(c, unidad, r, q, propios, por_unidad))
        if jefe:
            p = propios[jefe]['piezas'][r]
            piezas[r] = {'f': 'misalito', 'via': 'unidad', 'de': jefe, 'r': r,
                         't': len(p['testigos']), 'v': len(p['variantes'])}
            if otros:
                discrepan.append(('unidad', r, jefe, otros))
            continue
        i = next((i for i, rr in sueltos_de.get(unidad, []) if rr == r), None)
        if i is not None:
            piezas[r] = {'f': 'misalito', 'via': 'suelto', 'de': i, 'r': r,
                         't': len(sueltos[i]['testigos']), 'v': None}
            continue
        cual, cuantos = del_dia(cel, r, dias_de, impreso, dias)
        if cual:
            clase, quien = cual
            if clase == 'suelto':
                piezas[r] = {'f': 'misalito', 'via': 'día', 'de': quien,
                             'r': r, 't': len(sueltos[quien]['testigos']),
                             'v': None, 'd': len(dias_de.get(cel, []))}
            else:
                p = propios[quien]['piezas'][r]
                piezas[r] = {'f': 'misalito', 'via': 'día', 'de': quien,
                             'r': r, 't': len(p['testigos']),
                             'v': len(p['variantes']),
                             'd': len(dias_de.get(cel, []))}
            continue
        if cuantos > 1:
            discrepan.append(('día', r, None, sorted(
                '%s %s' % x for x in {impreso.get(t, {}).get(r)
                                      for t in dias_de.get(cel, [])}
                - {None})))
        hecho = False
        for cm in comunes_de.get(cel, []):
            p = propios.get(cm, {}).get('piezas', {}).get(r)
            if p:
                piezas[r] = {'f': 'misalito', 'via': 'común', 'de': cm,
                             'r': r, 't': len(p['testigos']),
                             'v': len(p['variantes'])}
                hecho = True
                break
        if hecho:
            continue
        kla = latino.get(unidad, {}).get('k')
        if kla and r in lat[kla]['piezas']:
            piezas[r] = {'f': 'latino', 'via': 'latino', 'de': kla, 'r': r,
                         't': None, 'v': None}
            continue
        piezas[r] = None
    for r, quien, n in flojas:
        discrepan.append(('flojo', r, quien, n))
    return piezas, discrepan


PRINCIPALES = ['entrada', 'colecta', 'ofrendas', 'comunion', 'poscomunion']


def veredicto(piezas, tiene_latino):
    """Cómo queda un formulario: con castellano entero, a medias, sólo en
    latín, o sin nada. Las cinco piezas que cuentan son las que el Misal
    imprime en todo formulario; la oración sobre el pueblo es de la Cuaresma y
    no entra en la cuenta."""
    es = sum(1 for r in PRINCIPALES
             if piezas.get(r) and piezas[r]['f'] == 'misalito')
    if es == len(PRINCIPALES):
        return 'completo'
    if es:
        return 'parcial'
    return 'latino' if tiene_latino else 'nada'


# --------------------------------------------------------------------------
# el informe
# --------------------------------------------------------------------------

VEREDICTOS = [('completo', 'con las cinco piezas en castellano'),
              ('parcial', 'con alguna pieza en castellano'),
              ('latino', 'sólo en latín'),
              ('nada', 'sin nada, ni latín')]

VIAS = [('celebración', 'de la propia celebración'),
        ('unidad', 'de otra celebración del mismo formulario del Misal'),
        ('suelto', 'de un texto suelto que cae en ese formulario'),
        ('día', 'de lo que el misalito imprimió esos días'),
        ('común', 'del común que la celebración ofrece'),
        ('gemela', 'de otro formulario con la misma oración latina'),
        ('latino', 'del Misal latino, en latín')]


# --------------------------------------------------------------------------
# el último paso: la misma oración latina, que en otro sitio sí tiene
# castellano
# --------------------------------------------------------------------------
#
# El Misal no estrena una oración por formulario: la misma colecta sirve a
# varios días, y la misma poscomunión recorre media Cuaresma. Cuando una
# ranura se queda sin castellano, antes de rendirla al latín conviene mirar
# si **ese mismo texto latino** está traducido en otro formulario. Es lo que
# pide el encargo: «comparar las oraciones en latín y español para armar el
# misal en español con los elementos que tenemos».
#
# Dos cautelas, y las dos importan:
#
#  · **Sólo se mira lo bien atribuido.** El índice se arma únicamente con
#    las ranuras resueltas `celebración` o `unidad`, que son aquellas en que
#    el castellano y el latín son del mismo formulario. Con las demás el
#    emparejamiento se corrompe: medido sobre el fichero, tomando todas las
#    vías salían 302 casos y entre ellos «Ego clamávi, quóniam exaudísti me»
#    emparejado con «El Señor puso sus ojos en la humildad de su esclava»,
#    que es el Magníficat. Acotado, salen 103 y los casados son los suyos.
#
#  · **Se exige unanimidad.** Si el mismo texto latino tiene dos castellanos
#    distintos, no se elige: se deja en latín y el informe lo nombra. Elegir
#    el más repetido sería inventar una traducción.
def gemelas(formularios, lat, cuenta):
    """Rellena con su gemela las ranuras que sólo tienen latín."""
    idx = {}
    for f in formularios.values():
        kla = f.get('la')
        if not kla or kla not in lat:
            continue
        for r, p in (f.get('piezas') or {}).items():
            if not p or p.get('via') not in ('celebración', 'unidad'):
                continue
            q = lat[kla]['piezas'].get(r)
            if not q or not q.get('texto'):
                continue
            k = (r, misal.clave(' '.join(q['texto'])))
            if not k[1]:
                continue
            idx.setdefault(k, set()).add((p['de'], p['r']))

    puestas, ambiguas = 0, []
    for clave_f, f in sorted(formularios.items()):
        kla = f.get('la')
        if not kla or kla not in lat:
            continue
        for r, p in list((f.get('piezas') or {}).items()):
            if p and p.get('via') != 'latino':
                continue
            q = lat[kla]['piezas'].get(r)
            if not q or not q.get('texto'):
                continue
            k = (r, misal.clave(' '.join(q['texto'])))
            cands = idx.get(k)
            if not cands:
                continue
            if len(cands) > 1:
                ambiguas.append((clave_f, r, len(cands)))
                continue
            de, rr = next(iter(cands))
            f['piezas'][r] = {'f': 'misalito', 'via': 'gemela', 'de': de,
                              'r': rr, 't': None, 'v': None, 'la': kla}
            puestas += 1
        f['v'] = veredicto(f['piezas'], bool(kla))
    cuenta['gemelas'] = puestas
    cuenta['gemelas_ambiguas'] = ambiguas
    return puestas, ambiguas


def tabla(inf, filas, cab=None):
    if cab:
        inf.di('    ' + cab)
    for f in filas:
        inf.di('    ' + f)


def informe(d, formularios, unidades, latino, por_unidad, sueltos_u,
            sueltos_de, pref, pref_sueltos, cuenta_citas, difieren,
            discrepancias, fsant, fmisas, fvot, avisos, cuenta_rutas,
            cuenta_gem):
    lat = d['lat']['formularios']
    inf = Informe(QA, 'FASE 5 — EL RESOLVEDOR: EL FORMULARIO DEL DÍA')
    inf.di('Las piezas de las cuatro fases anteriores puestas en su')
    inf.di('formulario, y por cada uno de los del leccionario: si tiene')
    inf.di('castellano, por qué camino, con cuántos testigos, y si no lo')
    inf.di('tiene, por qué no.')
    inf.di()

    ver = Counter(f['v'] for f in formularios.values())
    inf.di('formularios del leccionario     : %d' % len(formularios))
    for k, q in VEREDICTOS:
        inf.di('   %-28s : %4d  (%.0f %%)'
               % (q, ver[k], 100.0 * ver[k] / max(1, len(formularios))))
    piezas = Counter()
    for f in formularios.values():
        for r, p in f['piezas'].items():
            piezas[p['via'] if p else 'nada'] += 1
    inf.di('piezas resueltas                : %d'
           % (len(formularios) * len(RANURAS)))
    for k, q in VIAS:
        inf.di('   %-28s : %4d' % (q, piezas[k]))
    inf.di('   %-28s : %4d' % ('sin nada', piezas['nada']))

    # --- el hallazgo -----------------------------------------------------
    inf.titulo('La unidad del Misal no es el día: es el formulario')
    inf.di('  El Misal imprime una colecta para toda la primera semana del')
    inf.di('  tiempo ordinario, y el misalito la imprime el lunes de un año y')
    inf.di('  el martes de otro. La fase 4, que atribuía por celebración, no')
    inf.di('  encontraba ninguna presente en todos sus días y el texto se iba')
    inf.di('  a los sueltos. Agrupando por formulario latino vuelve a su')
    inf.di('  sitio. Esto es cuánto recupera, medido:')
    inf.di()
    inf.di('    piezas que vienen de otra celebración del mismo')
    inf.di('    formulario del Misal                        : %d'
           % piezas['unidad'])
    inf.di('    piezas que vienen de un texto suelto colocado: %d'
           % piezas['suelto'])
    colocados = sum(1 for u in sueltos_u.values() if u)
    inf.di('    textos sueltos de la fase 4                 : %d'
           % len(sueltos_u))
    inf.di('       colocados en un formulario               : %d' % colocados)
    inf.di('       que siguen sin formulario                : %d'
           % (len(sueltos_u) - colocados))
    unidades_con_varias = [(u, cs) for u, cs in sorted(por_unidad.items())
                           if len(cs) > 1]
    inf.di()
    inf.di('    formularios del Misal a los que el corpus llega por más de')
    inf.di('    un identificador: %d. Los diez con más:'
           % len(unidades_con_varias))
    for u, cs in sorted(unidades_con_varias, key=lambda x: -len(x[1]))[:10]:
        inf.di('      %-14s %d: %s' % (u, len(cs), ', '.join(sorted(cs))[:90]))

    # --- el puente -------------------------------------------------------
    inf.titulo('El puente con el Misal latino')
    nla = len(lat)
    usados = set()
    for v in latino.values():
        usados.add(v['k'])
        usados.update(v['alt'])
    inf.di('  formularios del Misal latino          : %d' % nla)
    inf.di('  colocados en una unidad               : %d' % len(usados))
    inf.di('  sin colocar                           : %d' % (nla - len(usados)))
    inf.di('  unidades con formulario latino        : %d' % len(latino))
    sinla = [k for k, f in sorted(formularios.items()) if not f['la']]
    inf.di('  formularios del leccionario sin latín : %d' % len(sinla))
    inf.di()
    inf.di('  El santoral, por el camino con que se emparejó cada uno:')
    for via, n in Counter(f[2] for f in fsant).most_common():
        inf.di('    %-48s %4d' % (via, n))
    inf.di()
    inf.di('  Las parejas que el nombre no pudo confirmar, una por una. El')
    inf.di('  latín y el castellano llaman a estos santos con palabras')
    inf.di('  distintas, y lo que las empareja es el orden del libro:')
    for f in fsant:
        if f[2].startswith('orden') and not f[3]:
            inf.di('    %-14s %-56s %s' % (f[0], f[1].split('/', 1)[1][:56],
                                           f[5][:40]))
    inf.di()
    inf.di('  Las cuatro de la tabla, y por qué están en ella: Ludovicus es')
    inf.di('  Luis, Elisabeth es Isabel y Stephanus es Esteban, de modo que')
    inf.di('  el parecido del nombre vale cero; y el 25 de agosto trae dos')
    inf.di('  celebraciones, así que el orden del libro tendría que elegir a')
    inf.di('  ciegas entre san Luis y san José de Calasanz.')
    for f in fsant:
        if f[2] == 'la tabla':
            inf.di('    %-14s %-56s %s' % (f[0], f[1].split('/', 1)[1][:56],
                                           f[5][:40]))

    inf.titulo('Las misas por diversas necesidades, votivas, rituales y de '
               'difuntos')
    inf.di('  El leccionario las numera en el orden del Misal y con sus')
    inf.di('  títulos traducidos, y cuando junta varias en un solo juego de')
    inf.di('  lecturas las nombra todas separadas por raya. Así que se')
    inf.di('  recorren las dos listas a la par, y cada rótulo del')
    inf.di('  leccionario consume del Misal tantos formularios como títulos')
    inf.di('  en mayúscula trae.')
    inf.di()
    inf.di('  rótulos del leccionario emparejados: %d' % len(fmisas))
    inf.di()
    inf.di('  Y las votivas que el misalito reza en las ferias, emparejadas')
    inf.di('  con el rótulo del leccionario por el nombre, que aquí es')
    inf.di('  castellano contra castellano:')
    inf.di()
    inf.di('  votivas del misalito con rótulo: %d' % len(fvot))
    for cel, s, sc, t1, t2 in sorted(fvot, key=lambda x: (x[2], x[0])):
        inf.di('    %.2f  %-46s %-14s %s' % (sc, t1[:46], s, t2[:44]))

    # --- formulario por formulario ---------------------------------------
    inf.titulo('Los formularios, uno por uno')
    inf.di('  Por sección, y dentro de cada una por veredicto:')
    inf.di()
    porsec = defaultdict(Counter)
    for f in formularios.values():
        porsec[f['seccion']][f['v']] += 1
    inf.di('    %-46s %8s %8s %7s %6s' % ('sección', 'completo', 'parcial',
                                          'latino', 'nada'))
    for sec in sorted(porsec, key=lambda s: -sum(porsec[s].values())):
        c = porsec[sec]
        inf.di('    %-46s %8d %8d %7d %6d'
               % (sec[:46], c['completo'], c['parcial'], c['latino'],
                  c['nada']))
    inf.di()
    inf.di('  Y la lista entera, con la vía de cada pieza y los testigos del')
    inf.di('  texto canónico. Las letras son: C la propia celebración, U otra')
    inf.di('  celebración del mismo formulario del Misal, S un texto suelto,')
    inf.di('  D lo que el misalito imprimió esos días, M el común, L el')
    inf.di('  latín, y un punto que no hay nada.')
    inf.di()
    letra = {'celebración': 'C', 'unidad': 'U', 'suelto': 'S', 'día': 'D',
             'común': 'M', 'gemela': 'G', 'latino': 'L'}
    inf.di('    %-26s %-7s %-44s %s' % ('clave', 'piezas', 'celebración',
                                        'testigos'))
    for clave, f in sorted(formularios.items(),
                           key=lambda x: (x[1]['seccion'], x[0])):
        mapa = ''.join(letra.get(f['piezas'][r]['via'], '?')
                       if f['piezas'].get(r) else '.' for r in RANURAS)
        ts = [p['t'] for r in PRINCIPALES
              if (p := f['piezas'].get(r)) and p['t']]
        inf.di('    %-26s %-7s %-44s %s'
               % (clave, mapa, (f['titulo'] or '')[:44],
                  min(ts) if ts else '—'))

    # --- las lecturas -----------------------------------------------------
    inf.titulo('Las lecturas: por qué ruta se halla la castellana')
    inf.di('  La cita que el índice del leccionario da y la que el misalito')
    inf.di('  imprime son la misma en dos de cada tres lecturas, y en la otra')
    inf.di('  no, aunque el pasaje sí lo sea. Tres rutas, por este orden:')
    inf.di()
    inf.di('    1. la cita, aplastada —los dos libros la escriben igual—;')
    inf.di('    2. los versículos: la cita leída cae en el mismo conjunto')
    inf.di('       aunque esté escrita de otra manera;')
    inf.di('    3. el día y la ranura: el calendario dice que el misalito')
    inf.di('       imprimió esa lectura ahí, y la cita confirma el pasaje.')
    inf.di()
    for k in ('  por la cita', '  por los versículos',
              '  por el día y la ranura',
              '    y la cita lo confirma por versículos',
              '    y la cita lo confirma por libro y capítulo',
              '    y abarca otros versículos, y se dice',
              '  sin castellano',
              '  la impresión que el día respalda',
              '    y no era la canónica, y se cambia',
              '  la que el día respalda pierde estrofas, y no se toca',
              '  el día no respalda ninguna impresión'):
        if cuenta_rutas.get(k):
            inf.di('    %-42s %6d' % (k, cuenta_rutas[k]))
    inf.di()
    inf.di('  **Y hallada la perícopa, cuál de sus impresiones.** La cita no')
    inf.di('  identifica el salmo: «Sal 104, 2-3. 4-5. 6-7» son tres salmos')
    inf.di('  del leccionario de México con los mismos versículos y tres')
    inf.di('  respuestas distintas —el miércoles de la 14ª semana responde')
    inf.di('  «Recurramos al Señor y a su poder», el sábado de la 27ª «El')
    inf.di('  Señor nunca olvida sus promesas» y el jueves de la 31ª «El que')
    inf.di('  busca al Señor será dichoso»—. Agrupados por la cita caen en')
    inf.di('  una sola perícopa, y el canónico de la fase 4 —el que más')
    inf.di('  testigos trae— se imprimía en los tres días: la respuesta era')
    inf.di('  de otro día. No es una cuarta ruta, porque no busca perícopa:')
    inf.di('  hallada por cualquiera de las tres, los días que el calendario')
    inf.di('  da a este formulario dicen cuál de sus impresiones es la suya,')
    inf.di('  y entre varias manda el sitio, que es la fuente principal del')
    inf.di('  texto de las lecturas. Si ninguno la respalda, no se toca nada.')
    inf.di()
    inf.di('  **La segunda ruta es la cita leída y no aplastada.** Aplastada,')
    inf.di('  tres maneras de escribir el mismo pasaje son tres citas')
    inf.di('  distintas, y las tres aparecen en la fuente:')
    inf.di()
    inf.di('    el enlace   el misalito une dos versículos de una estrofa con')
    inf.di('                la conjunción —«Sal 79,9y12»— donde el índice')
    inf.di('                pone un punto —«Sal 79,9.12»—. Es el salmo del')
    inf.di('                domingo XXVII del Tiempo Ordinario, que la primera')
    inf.di('                versión daba por no impreso y está en el misalito')
    inf.di('                de octubre de 2020 y en el de octubre de 2023.')
    inf.di('    la letra    el leccionario cita medio versículo —«Jn 8,12b»—')
    inf.di('                y el misalito imprime el versículo —«Jn 8,12»—.')
    inf.di('    la raya     el intervalo va con guión, con raya o con')
    inf.di('                semirraya según quién lo imprima: «Is 55,1-11» y')
    inf.di('                «Is 55,1–11».')
    inf.di()
    inf.di('  **La tercera no compara citas: compara calendarios.** Y por eso')
    inf.di('  alcanza lo que ninguna comparación de citas alcanza: los salmos')
    inf.di('  cuya cita el volcado dejó ilegible —«Sal 49» a secas,')
    inf.di('  «Sal 68,8-1014y17.33-35»— y los que el misalito imprime con')
    inf.di('  otros versículos del mismo salmo, que es lo que el leccionario')
    inf.di('  de México hace a menudo.')
    inf.di()
    inf.di('  **Y lleva guarda, porque el día solo engaña.** El domingo IX del')
    inf.di('  Tiempo Ordinario del ciclo A cae casi siempre en la Trinidad y no')
    inf.di('  se celebra: el misalito de aquel día imprime las lecturas de la')
    inf.di('  Trinidad, y el día sin más se las daría al domingo IX. Así que')
    inf.di('  la cita del misalito tiene que nombrar el mismo libro y el mismo')
    inf.di('  capítulo, y —cuando las dos citas se dejan leer— tocarse en')
    inf.di('  algún versículo. La guarda descarta el evangelio de san Mateo')
    inf.di('  13,1-9 en la fiesta de santos Joaquín y Ana, que manda 13,16-17:')
    inf.di('  mismo capítulo, ningún versículo en común, no es la misma')
    inf.di('  perícopa.')
    inf.di()
    inf.titulo('Las lecturas: el cotejo de citas')
    inf.di('  Esto es la prueba de que el emparejamiento no es una')
    inf.di('  coincidencia de calendario. Por cada día de los cien misalitos')
    inf.di('  se busca la clave del leccionario que su celebración tiene ese')
    inf.di('  día y se comparan las citas que uno imprime con las que el otro')
    inf.di('  manda:')
    inf.di()
    for k, n in cuenta_citas.most_common():
        inf.di('    %-52s %6d' % (k, n))
    inf.di()
    total = sum(1 for f in formularios.values() for x in f['lecturas'])
    con = sum(1 for f in formularios.values() for x in f['lecturas']
              if x['es'])
    inf.di('  lecturas que los formularios mandan   : %d' % total)
    inf.di('  con texto castellano, por las tres rutas: %d  (%.0f %%)'
           % (con, 100.0 * con / max(1, total)))
    inf.di('  sin texto castellano                  : %d' % (total - con))
    inf.di()
    portipo = defaultdict(Counter)
    for f in formularios.values():
        for x in f['lecturas']:
            portipo[x['tipo']]['sí' if x['es'] else 'no'] += 1
    inf.di('    %-34s %6s %6s' % ('tipo', 'con', 'sin'))
    for t in sorted(portipo, key=lambda t: -sum(portipo[t].values())):
        inf.di('    %-34s %6d %6d' % (t, portipo[t]['sí'], portipo[t]['no']))
    inf.di()
    inf.di('  Las citas que no están en ninguna celebración de su día son %d,'
           % len(difieren))
    inf.di('  y no se reparten al azar:')
    inf.di()
    for r, n in Counter(x[3] for x in difieren).most_common():
        inf.di('    %-14s %5d' % (r, n))
    inf.di()
    inf.di('  Dos tercios son el salmo y la aclamación, y ahí la diferencia no')
    inf.di('  es de formulario sino de versículos: el leccionario mexicano')
    inf.di('  elige otros del mismo salmo, y el verso del aleluya lo cambia')
    inf.di('  más todavía. Lo que de verdad dice que el editor rezó otra cosa')
    inf.di('  son la primera lectura y el evangelio, y son %d de las %d.'
           % (sum(1 for x in difieren if x[3] in ('primera', 'evangelio')),
              len(difieren)))
    inf.di()
    inf.di('  Las veinte primeras, para que se vea:')
    for x in difieren[:20]:
        inf.di('    %s/%d  %-28s %-12s %-18s %s'
               % (x[0], x[1], x[2][:28], x[3], x[4][:18], x[5]))

    # --- lo que no cuadró -------------------------------------------------
    inf.titulo('Las celebraciones de una misma unidad que no dicen lo mismo')
    inf.di('  Dos celebraciones del mismo formulario del Misal han de traer')
    inf.di('  el mismo texto. Cuando no lo traen manda la que más testigos')
    inf.di('  tiene, y la otra queda aquí escrita, que es donde se ve si el')
    inf.di('  agrupamiento se pasó de listo:')
    inf.di()
    unid = [x for x in discrepancias if x[2] == 'unidad']
    inf.di('  casos: %d' % len(unid))
    for x in unid[:40]:
        inf.di('    %-26s %-12s manda %-14s y no %s'
               % (x[0], x[3], x[4], ', '.join(x[5])[:46]))

    inf.titulo('Los días de una celebración que no imprimen lo mismo')
    inf.di('  El cuarto paso de la cascada —lo que el misalito imprimió esos')
    inf.di('  días— exige que todos los días de la celebración traigan lo')
    inf.di('  mismo en esa ranura. Cuando no, no entra nada y la pieza baja al')
    inf.di('  común o al latín. Suele ser el domingo del tiempo ordinario, que')
    inf.di('  en ocho años cae unas veces en su semana y otras lo desplaza una')
    inf.di('  solemnidad:')
    inf.di()
    dd_ = [x for x in discrepancias if x[2] == 'día']
    inf.di('  casos: %d' % len(dd_))
    for x in dd_[:40]:
        inf.di('    %-26s %-12s %-14s %s'
               % (x[0], x[3], x[1], ', '.join(x[5])[:52]))

    inf.titulo('Las piezas que se cayeron por tener un solo testigo')
    inf.di('  El Misal da un formulario por semana en el tiempo ordinario, y')
    inf.di('  ese formulario es el del domingo: la feria no tiene oraciones')
    inf.di('  suyas. Lo que el misalito imprime una feria de enero es lo que')
    inf.di('  el editor eligió ese año. Así que si el domingo de la semana')
    inf.di('  trae la ranura, manda el domingo; y si no la trae, hace falta')
    inf.di('  más de un testigo. Casi todas son de enero y febrero de 2021:')
    inf.di()
    fl = [x for x in discrepancias if x[2] == 'flojo']
    inf.di('  casos: %d' % len(fl))
    for x in fl[:40]:
        inf.di('    %-26s %-12s %-12s %d testigo%s, el primero %s'
               % (x[0], x[1], x[3], x[5], '' if x[5] == 1 else 's', x[4]))

    inf.titulo('Las ranuras rescatadas por su gemela latina')
    inf.di('  La misma oración latina, traducida en otro formulario. Sólo se')
    inf.di('  toma de las ranuras bien atribuidas (celebración o unidad) y')
    inf.di('  sólo si el castellano es uno: con dos no se elige.')
    inf.di()
    inf.di('  rescatadas: %d' % cuenta_gem.get('gemelas', 0))
    amb = cuenta_gem.get('gemelas_ambiguas') or []
    inf.di('  dejadas en latín por tener dos castellanos: %d' % len(amb))
    for x in amb[:25]:
        inf.di('    %-30s %-12s %d castellanos' % x)

    inf.titulo('Los textos sueltos que siguen sueltos')
    inf.di('  Un texto suelto se coloca cuando todos sus días caen en el')
    inf.di('  mismo formulario del Misal. Los que no, siguen fuera, y es')
    inf.di('  correcto que lo estén: son los de los comunes, que están en')
    inf.di('  varios a la vez, y la fase 4 ya midió su reparto.')
    inf.di()
    sin = [i for i, u in sueltos_u.items() if not u]
    inf.di('  sin colocar: %d' % len(sin))
    porran = Counter(d['sueltos'][i]['ranura'] for i in sin)
    for r, n in porran.most_common():
        inf.di('    %-14s %4d' % (r, n))

    inf.titulo('Los prefacios')
    inf.di('  Por el número de rúbrica, que es lo único que los dos juegos')
    inf.di('  comparten. Nunca por el orden: «Prefacio III de Adviento» no')
    inf.di('  tiene tercero latino al que corresponder, y emparejarlos por')
    inf.di('  posición daría textos cruzados de los difíciles de notar.')
    inf.di()
    inf.di('  prefacios castellanos          : %d' % len(pref))
    inf.di('  con pareja en el Misal latino  : %d'
           % sum(1 for v in pref.values() if v))
    inf.di('  sin pareja, y marcados         : %d' % len(pref_sueltos))
    for k, n, t in pref_sueltos:
        inf.di('    %-46s %s' % (t[:46], 'n. %s' % n if n else 'sin número'))
    inf.di()
    citados = Counter()
    for f in formularios.values():
        for x in f['prefacio']:
            citados[x] += 1
    inf.di('  prefacios que algún formulario cita: %d' % len(citados))
    nadie = [k for k in pref if k not in citados]
    inf.di('  prefacios que ningún formulario cita: %d' % len(nadie))
    for k in sorted(nadie):
        inf.di('    %s' % d['pref_es'][k]['titulo'])

    inf.titulo('Lo que esta fase topa y no es suyo')
    inf.di('  Son defectos de fases anteriores que aquí se ven porque aquí se')
    inf.di('  juntan las piezas. Quedan nombrados, no tapados:')
    inf.di()
    inf.di('  · los 49 formularios del santoral latino a los que la fase 1 no')
    inf.di('    les guardó la fecha —son los que el Misal titula con el')
    inf.di('    rótulo del mes, y con él se pierde el renglón «Die N')
    inf.di('    mensis»—. Esta fase los coloca por el orden del libro y el')
    inf.di('    nombre, y los %d que ni así se confirman van arriba uno por'
           % sum(1 for f in fsant if f[2].startswith('orden') and not f[3]))
    inf.di('    uno. Lo limpio sería que la fase 1 leyera la fecha.')
    inf.di('  · las ferias del tiempo de Navidad. El Misal las imprime en dos')
    inf.di('    grupos, «a die 2 ianuarii» y «post sollemnitatem Epiphaniæ»,')
    inf.di('    y la fase 1 sólo guardó seis formularios con la rúbrica del')
    inf.di('    segundo grupo metida dentro del primero. De ahí que las seis')
    inf.di('    ferias del 2 al 7 de enero se queden sin formulario latino.')
    inf.di('  · `tempore/feria-v-in-cena-domini-v-simul-quoque-cum-beatis-')
    inf.di('    videamus` no es un formulario: es un trozo del Canon Romano')
    inf.di('    que la fase 1 tomó por rótulo.')
    inf.di('  · el Viernes Santo no tiene formulario latino. Entre la misa')
    inf.di('    vespertina de la Cena del Señor y la Vigilia pascual la fase 1')
    inf.di('    no guardó nada, y la celebración de la Pasión del Señor sí')
    inf.di('    tiene oraciones en el Misal.')
    inf.di('  · la misa vespertina de la Cena del Señor se queda sin oración')
    inf.di('    sobre las ofrendas en las dos lenguas: el misalito no la')
    inf.di('    atribuyó y el formulario latino tampoco la trae.')
    inf.di()
    inf.di('  Y una cosa que no es defecto de nadie y conviene saber: las')
    inf.di('  misas que el Misal da aparte y el leccionario no —la vigilia de')
    inf.di('  san Juan Bautista, la de san Pedro y san Pablo, la segunda y la')
    inf.di('  tercera de los Difuntos— no tienen clave del leccionario, así')
    inf.di('  que no salen en la lista de formularios. Están en la tabla de')
    inf.di('  unidades, con su `#vigilia`, `#2` o `#3`, para que la fase 6')
    inf.di('  pueda ofrecerlas como lo que son: otra misa del mismo día.')

    inf.titulo('Avisos')
    inf.di('  Todo lo que no se pudo resolver, por clase y uno por uno.')
    inf.di()
    for clase, n in Counter(a[0] for a in avisos).most_common():
        inf.di('  %-56s %4d' % (clase, n))
    inf.di()
    for a in sorted(avisos):
        inf.di('    %s' % a[0])
        inf.di('      %s' % a[1])
        if a[2]:
            inf.di('      %s' % str(a[2])[:200])
    inf.guarda()


# --------------------------------------------------------------------------
# las lecturas: por cita, no por formulario
# --------------------------------------------------------------------------
# El leccionario dice qué se lee en cada formulario y con qué cita; la cosecha
# de los misalitos guarda cada perícopa una vez, por cita. Así que el
# emparejamiento no se adivina: se comprueba. Y como una perícopa impresa en
# el día de un santo sirve igual en cualquier otro formulario que la mande,
# el corpus por cita recupera lo que el día del santo nunca imprimió.

TIPOS_LECTURA = ('primera lectura', 'segunda lectura', 'tercera lectura',
                 'cuarta lectura', 'quinta lectura', 'sexta lectura',
                 'septima lectura', 'epistola', 'evangelio',
                 'salmo responsorial', 'aleluya', 'secuencia',
                 'lectura del Antiguo Testamento',
                 'lectura del Nuevo Testamento')


def lecturas_por_clave(imaster):
    """clave del leccionario → sus lecturas en orden, con su cita."""
    por = defaultdict(list)
    for e in imaster:
        if not e.get('cita_normalizada'):
            continue
        k = '%s|%s|%d' % (e['leccionario'], e['archivo'], e['cel_n'])
        por[k].append({'o': e.get('orden'), 'tipo': e['tipo'],
                       'cita': e['cita_normalizada'],
                       'variante': e.get('variante') or ''})
    for k in por:
        por[k].sort(key=lambda x: (x['o'] or 0))
    return por


def indice_de_pericopas(pericopas):
    """La cita apretada → la clave con que la fase 4 la guardó.

    Dos citas que sólo difieren en cómo se escribe el salto de capítulo son la
    misma, y la fase 4 guardó las dos formas por separado —«1 Co 10,31-11.1» y
    «1 Co 10,31—11.1» están las dos—. Al apretarlas caen en la misma, y manda
    la que más testigos trae.
    """
    por = {}
    for cita, v in pericopas.items():
        q = squeeze(cita)
        if q not in por or len(v['testigos']) > len(pericopas[por[q]]
                                                   ['testigos']):
            por[q] = cita
    return por


def pericopas_por_versiculos(pericopas):
    """(libro, conjunto de versículos) → la clave de la fase 4 que más testigos
    trae. Es el índice de la segunda ruta: la cita leída y no aplastada."""
    por = {}
    for cita, v in pericopas.items():
        r = versiculos(cita)
        if not r:
            continue
        if r not in por or len(v['testigos']) > len(pericopas[por[r]]
                                                   ['testigos']):
            por[r] = cita
    return por


def pericopas_por_dia(dias, cal, porclave_lect, bloques, anio_de):
    """(clave del leccionario, tipo, orden) → las citas que el misalito imprimió
    en esa ranura, con cuántos días lo hicieron.

    Es el índice de la tercera ruta, y la evidencia que trae no es la cita sino
    **el calendario**: si el 8 de octubre de 2023 era el domingo XXVII del
    Tiempo Ordinario del ciclo A y el misalito de aquel mes imprimió ese día un
    salmo responsorial, ese salmo es el salmo de ese formulario, lo escriba la
    cita como lo escriba. Por eso recupera los salmos cuya cita el volcado dejó
    ilegible —«Sal 49» a secas, «Sal 68,8-1014y17.33-35»—, que ninguna
    comparación de citas alcanza.

    Sólo se apunta la ranura cuando el formulario del leccionario tiene **una
    sola** lectura de ese tipo: donde la Vigilia Pascual manda siete lecturas
    del Antiguo Testamento no hay manera de saber a cuál corresponde la que el
    misalito imprimió, y adivinar sería peor que no decir nada.
    """
    cand = defaultdict(Counter)
    for fecha, forms in sorted(dias.items()):
        anio = anio_de(fecha) or ('A', 'I')
        for f in forms:
            k = clave_del_ciclo(bloques.get(f.get('cel')) or [], *anio)
            if not k:
                continue
            por_ranura = defaultdict(list)
            for x in porclave_lect.get(k) or []:
                por_ranura[RANURA_DE_TIPO.get(x['tipo'])].append(x)
            for ranura, cita in (f.get('lecturas') or {}).items():
                if not cita:
                    continue
                xs = por_ranura.get(ranura) or []
                if len(xs) == 1:
                    cand[(k, xs[0]['tipo'], xs[0]['o'])][cita] += 1
    return cand


# El misalito rotula sus lecturas por su sitio en la misa y el leccionario por
# lo que son; es la misma ranura con dos nombres.
#
# Las lecturas numeradas de la Vigilia Pascual y la epístola **tienen ahora
# ranura propia**: la fuente las rotula («TERCERA LECTURA», «EPÍSTOLA») y la
# fase 3 ya reconoce esos rótulos, así que no hay que meterlas todas en la
# primera. Importa para la ruta del día, que sólo se atreve cuando el
# formulario tiene una sola lectura de ese tipo: con las nueve en la primera
# no se atrevía nunca, y la Vigilia se quedaba sin esa ruta.
#
# Los dos testamentos sí siguen en la primera: son el nombre que el
# leccionario da a la lectura de las misas rituales —«lectura del Antiguo
# Testamento»— y la fuente las imprime en la primera ranura, sin rotularlas
# así.
RANURA_DE_TIPO = {
    'primera lectura': 'primera', 'segunda lectura': 'segunda',
    'salmo responsorial': 'salmo', 'aleluya': 'aclamacion',
    'evangelio': 'evangelio', 'secuencia': 'secuencia',
    'epistola': 'epistola',
    'lectura del Antiguo Testamento': 'primera',
    'lectura del Nuevo Testamento': 'primera',
    'tercera lectura': 'tercera', 'cuarta lectura': 'cuarta',
    'quinta lectura': 'quinta', 'sexta lectura': 'sexta',
    'septima lectura': 'septima',
}


def mismos_versiculos(a, b):
    """Si las dos citas abarcan exactamente los mismos versículos. `False`
    cuando alguna no se deja leer: entonces no se puede afirmar que sí."""
    va, vb = versiculos(a), versiculos(b)
    return bool(va and vb and va == vb)


def empareja_lectura(clave, x, pericopas, idx_cita, idx_vers, cand, cuenta):
    """La perícopa castellana de una lectura del formulario, y por qué ruta.

    Tres rutas, en este orden, y cada una se apunta en el informe:

      1. **la cita**, aplastada: los dos libros la escriben igual;
      2. **los versículos**: la cita dice el mismo pasaje de otra manera —el
         enlace, la letra, la raya—, y leída cae en el mismo conjunto;
      3. **el día y la ranura**: el calendario dice que el misalito imprimió
         esa lectura en esa ranura de ese formulario, y la cita confirma que es
         del mismo libro y capítulo. Deciden los testigos: la cita que más días
         imprimieron.

    Las dos últimas son de esta fase y no estaban: la primera versión dejaba
    sin castellano un tercio de las lecturas que el misalito sí había impreso.
    """
    v = idx_cita.get(squeeze(x['cita']))
    if v:
        cuenta['  por la cita'] += 1
        return v, 'cita', False
    r = versiculos(x['cita'])
    v = idx_vers.get(r) if r else None
    if v:
        cuenta['  por los versículos'] += 1
        return v, 'versículos', False
    c = cand.get((clave, x['tipo'], x['o']))
    if c:
        # Las candidatas del día, partidas por lo que su cita permite cotejar:
        # las que dan versículos y se tocan con los del leccionario, y las que
        # no dan versículos porque el volcado dejó la cita ilegible.
        buenas, aciegas, rechazada = Counter(), Counter(), False
        for cita, n in c.items():
            if cita not in pericopas:
                continue
            modo = misma_pericopa(x['cita'], cita)
            if modo == 'versículos':
                buenas[cita] = n
            elif modo == 'libro y capítulo':
                aciegas[cita] = n
            elif libro_y_capitulo(cita) == libro_y_capitulo(x['cita']):
                # misma capítulo y ningún versículo en común: el misalito canta
                # otra cosa de ese capítulo
                rechazada = True
        # **Manda el testigo que se puede leer.** La ilegible sólo vale cuando
        # no hay ninguna legible de ese capítulo, ni aceptada ni rechazada: si
        # una legible del mismo capítulo se rechazó por no tocarse con los
        # versículos del leccionario, la ilegible es casi seguro lo mismo que
        # ella. Es el salmo 113 del lunes de la V semana de Pascua: el Misal
        # manda 113,9-10.11-12.23-24 —la segunda mitad del salmo— y el
        # misalito imprimió dos veces 113,1-2.3-4.15-16 y una vez «Sal 113» a
        # secas, y las tres son la primera mitad.
        elegidas = buenas or (Counter() if rechazada else aciegas)
        if elegidas:
            v = elegidas.most_common(1)[0][0]
            cuenta['  por el día y la ranura'] += 1
            cuenta['    y la cita lo confirma por %s'
                   % misma_pericopa(x['cita'], v)] += 1
            # Sólo esta ruta puede dar un texto que no abarque exactamente los
            # versículos que el leccionario manda: las dos primeras exigen la
            # misma cita o el mismo conjunto. Cuando pasa, se dice, y la app lo
            # enseña con las dos citas.
            otros = not mismos_versiculos(x['cita'], v)
            if otros:
                cuenta['    y abarca otros versículos, y se dice'] += 1
            return v, 'día', otros
    cuenta['  sin castellano'] += 1
    return None, None, False


def dias_por_clave(dias, cal, bloques, anio_de):
    """clave del leccionario → los testigos (`fecha/n`) que el calendario le da.

    Es el mismo cálculo que `pericopas_por_dia` —la celebración del día y el
    ciclo que le toca dan la clave del formulario—, pero guardando el testigo
    en vez de la cita, y sin exigir que la ranura sea única: aquí no se
    adivina ninguna ranura, sólo se pregunta **qué días son de este
    formulario**. Con eso se desempata, más abajo, cuál de las impresiones de
    una perícopa es la de este formulario y no la de otro día que la cita
    comparte.
    """
    por = defaultdict(set)
    for fecha, forms in dias.items():
        anio = anio_de(fecha) or ('A', 'I')
        # Las del calendario **y** la que el día eligió, que no son la misma
        # cosa: el sábado de la 27ª semana el editor imprime a menudo la misa
        # de Santa María en sábado, y entonces el `cel` del día es la votiva
        # —con los formularios del leccionario de la votiva— mientras que las
        # lecturas que imprime son **las de la feria**, porque el leccionario
        # lo fija el día y no la misa que se elija. Tomando sólo el `cel` del
        # día, el sábado de la 27ª semana se quedaba con dos testigos de once
        # años, los dos del sitio, y ninguno de los cinco misalitos que sí lo
        # imprimieron.
        cels = {f.get('cel') for f in forms}
        cels |= {c[0] for c in
                 (cal['fechas'].get(fecha, {}).get('c') or [])}
        cels.discard(None)
        ks = {clave_del_ciclo(bloques.get(c) or [], *anio) for c in cels}
        ks.discard(None)
        for k in ks:
            por[k] |= {'%s/%d' % (fecha, i) for i in range(len(forms))}
    return por


def del_sitio(dias):
    """Los testigos que vienen del sitio y no del misalito."""
    return {'%s/%d' % (fecha, i)
            for fecha, forms in dias.items()
            for i, f in enumerate(forms)
            if f.get('origen') == 'sitio'}


# La marca de respuesta del pueblo, para contar estrofas sin desarmar el
# salmo: la fase 6 corta en ella y aquí sólo se cuenta. Vale de medida de
# si un volcado está completo, porque la cita es la misma en todas las
# impresiones de una perícopa y por tanto las estrofas también.
MARCA = re.compile(r'(?:^|(?<=[\s.,;:!?…«»“”")]))R/?\.')


def cuantas_marcas(texto):
    return len(MARCA.findall(' '.join(texto)))


def variante_del_dia(peri, suyos, sitio, cuenta):
    """Cuál de las impresiones de una perícopa es la de *este* formulario.

    **La cita no identifica el salmo.** La fase 4 agrupa las lecturas por la
    cita, y «Sal 104, 2-3. 4-5. 6-7» son tres salmos del leccionario de
    México con los mismos versículos y tres respuestas distintas: el miércoles
    de la 14ª semana responde «Recurramos al Señor y a su poder», el sábado de
    la 27ª «El Señor nunca olvida sus promesas» y el jueves de la 31ª «El que
    busca al Señor será dichoso». Agrupados por la cita caen en una sola
    perícopa, y el canónico —el que más testigos trae— se imprimía en los
    tres días. La respuesta era de otro día.

    Lo que los distingue está medido y es el calendario: `suyos` son los días
    que el calendario da a **este** formulario. Gana el grupo —el canónico o
    una de sus variantes— que esos días respaldan; entre varios, el que tenga
    algún testigo del sitio, que es la fuente principal del texto de las
    lecturas, y después el de más días suyos. Si ninguno los tiene, no se
    toca nada: manda el canónico de la fase 4.

    **Y no se cambia a costa de perder texto.** Se exige que la impresión
    elegida marque al menos tantas respuestas del pueblo como la canónica:
    la cita es la misma en todas las impresiones de una perícopa, de modo
    que las estrofas también lo son, y un volcado que marque menos es un
    volcado incompleto. Medido: con esta guarda el salmo 121 del sábado de
    la 29ª semana se queda con la respuesta de Pascua —«Vayamos con alegría
    al encuentro del Señor. **Aleluya**», que en octubre no se dice— antes
    que perder su tercera estrofa, y se dice en el informe. Sin ella se
    perdían 21 estrofas de tres salmos.

    Devuelve el índice del grupo —0 el canónico, n la variante n-1— y no el
    texto, porque `misa.json` es la decisión y no el libro: el texto lo sigue
    sacando la fase 6 de `pericopas_es.json`.
    """
    grupos = [(peri['testigos'], peri['texto'])] + [
        (v['testigos'], v['texto']) for v in peri.get('variantes') or []]
    if len(grupos) == 1:
        return 0
    minimo = cuantas_marcas(grupos[0][1])
    elegido, punt, cortas = 0, None, False
    for i, (ts, tx) in enumerate(grupos):
        mios = [t for t in ts if t in suyos]
        if not mios:
            continue
        if cuantas_marcas(tx) < minimo:
            cortas = True
            continue
        p = (0 if any(t in sitio for t in mios) else 1,
             -len(mios), -len(ts), i)
        if punt is None or p < punt:
            elegido, punt = i, p
    if punt is None:
        if cortas:
            cuenta['  la que el día respalda pierde estrofas, y no se toca']                 += 1
        else:
            cuenta['  el día no respalda ninguna impresión'] += 1
        return 0
    cuenta['  la impresión que el día respalda'] += 1
    if elegido:
        cuenta['    y no era la canónica, y se cambia'] += 1
    return elegido


def anio_liturgico(cal):
    """fecha → el ciclo dominical y el año ferial que le toca.

    El año litúrgico no empieza el 1 de enero: el calendario del proyecto dice
    dónde empieza cada uno, y es lo que decide si un día de diciembre lee el
    ciclo del año civil que acaba o el del que viene.
    """
    tramos = sorted((v['inicio'], v['ciclo'], v['ferial'])
                    for v in cal['anios'].values())

    def de(fecha):
        elegido = None
        for inicio, ciclo, ferial in tramos:
            if inicio <= fecha:
                elegido = (ciclo, ferial)
            else:
                break
        return elegido
    return de


def bloques_de_cel(indice):
    """celebración → sus formularios del leccionario, con su etiqueta."""
    por = defaultdict(list)
    for sec in indice:
        for g in sec['g']:
            for dd in g['d']:
                for b in dd.get('b') or []:
                    por[dd['s']].append((b.get('e') or '', b['k']))
    return por


def clave_del_ciclo(bloques, ciclo, ferial):
    """De los formularios de una celebración, el que toca ese año. El orden es
    el del propio índice: el ciclo dominical, el año ferial, el que sirve para
    los tres, y el propio del santo."""
    for quiere in ('Ciclo %s' % ciclo, 'Año %s' % ferial, 'Ciclos A, B y C',
                   'Propio'):
        for e, k in bloques:
            if e.startswith(quiere):
                return k
    return bloques[0][1] if bloques else None


def coteja_citas(dias, cal, porclave_lect, bloques, anio_de, avisos):
    """La prueba de que el emparejamiento no es una coincidencia de calendario.

    Por cada día de los cien misalitos se mira la celebración a la que la fase
    4 atribuyó su formulario, se busca en el calendario la clave del
    leccionario que esa celebración tiene ese día, y se comparan las citas que
    el misalito imprime con las que el leccionario manda. Si los dos caminos
    —la fecha y la cita— dicen lo mismo, el emparejamiento está probado; si no,
    se cuenta y se nombra.
    """
    cuenta = Counter()
    difieren = []
    for fecha, forms in sorted(dias.items()):
        anio = anio_de(fecha) or ('A', 'I')
        deldia = set()
        for o in cal['fechas'].get(fecha, {}).get('c', []):
            k = clave_del_ciclo(bloques.get(o[0], []), *anio)
            deldia |= {squeeze(x['cita']) for x in porclave_lect.get(k, [])}
        for i, f in enumerate(forms):
            cel = f.get('cel')
            citas = {r: c for r, c in (f.get('lecturas') or {}).items() if c}
            if not citas:
                cuenta['el misalito no imprime lecturas'] += 1
                continue
            bs = bloques.get(cel) or []
            kciclo = clave_del_ciclo(bs, *anio)
            suyas = {squeeze(x['cita']) for _, k in bs
                     for x in porclave_lect.get(k, [])}
            for ranura, cita in sorted(citas.items()):
                q = squeeze(cita)
                if q in suyas:
                    cuenta['la cita es la que el leccionario da a esa '
                           'celebración'] += 1
                elif q in deldia:
                    cuenta['la cita es la de otra celebración del mismo día '
                           '—la feria, casi siempre'] += 1
                else:
                    cuenta['la cita no está en ninguna celebración de ese '
                           'día'] += 1
                    difieren.append((fecha, i, cel, ranura, cita,
                                     kciclo or '—'))
    return cuenta, difieren


# --------------------------------------------------------------------------
# los prefacios
# --------------------------------------------------------------------------

def puente_prefacios(pref_es, pref_la, avisos):
    """El castellano y el latín por el número de rúbrica, que es lo único que
    los dos juegos comparten. Los diecisiete castellanos sin número son los
    que el juego común latino no tiene —varios están en el Misal, pero dentro
    de las misas rituales— y van marcados como tales, no emparejados a ojo."""
    porn = {}
    for k, v in pref_la.items():
        if v.get('n'):
            porn.setdefault(v['n'], []).append(k)
    pareja, sueltos = {}, []
    for k, v in sorted(pref_es.items(), key=lambda x: (x[1]['n'] or 0)):
        n = v.get('n')
        cands = porn.get(n) if n and not v.get('n_de_tabla') else None
        if cands and len(cands) == 1:
            pareja[k] = cands[0]
        else:
            pareja[k] = None
            sueltos.append((k, n, v['titulo']))
            if cands and len(cands) > 1:
                avisos.append(('dos prefacios latinos con el mismo número',
                               k, ', '.join(cands)))
    return pareja, sueltos


# --------------------------------------------------------------------------
# la salida y el informe
# --------------------------------------------------------------------------

def main():
    d = carga()
    lat = d['lat']['formularios']
    propios, sueltos, dias = d['propios'], d['sueltos'], d['dias']
    cal, indice = d['cal'], d['indice']
    avisos = []
    fsant, fmisas, fvot, ftiempo = [], [], [], []

    porclave, cels = celebraciones_del_indice(indice)
    porclave_lect = lecturas_por_clave(d['imaster'])
    # las tres rutas con que se busca la perícopa castellana, cada una con su
    # índice: la cita aplastada, la cita leída y el calendario
    idx_peri = indice_de_pericopas(d['pericopas'])
    idx_vers = pericopas_por_versiculos(d['pericopas'])
    cand_dia = pericopas_por_dia(dias, cal, porclave_lect,
                                 bloques_de_cel(indice), anio_liturgico(cal))
    # y el desempate de la impresión, que no es una cuarta ruta: hallada la
    # perícopa por cualquiera de las tres, dice cuál de sus impresiones es la
    # de este formulario
    dias_clave = dias_por_clave(dias, cal, bloques_de_cel(indice),
                                anio_liturgico(cal))
    sitio = del_sitio(dias)
    cuenta_rutas = Counter()

    # --- el puente latino ------------------------------------------------
    pareja_sant, dequien_sant, alternos = puente_santoral(
        lat, cal, fsant, avisos, otros_del_santoral(indice))
    pareja_misas = puente_misas(lat, indice, avisos, fmisas)

    # el tiempo, por la clave canónica
    ula = {}
    for k, v in lat.items():
        if k.startswith('tempore/'):
            u = unidad_latina(k, v, avisos)
            if u:
                ula.setdefault(u, []).append(k)
    for k in lat:
        if k.startswith('communia/'):
            for cod, pre in COMUNES.items():
                if k.startswith(pre):
                    ula.setdefault('com/' + cod.lower(), []).append(k)

    # --- la unidad de cada celebración -----------------------------------
    dias_de = dias_por_cel(dias)
    fechas_de = fechas_por_cel(dias_de, propios)
    titulo_de = {c: t for c, t, _, _ in cels}
    for c in propios:
        titulo_de.setdefault(c, propios[c].get('titulo') or c)
    pareja_vot = puente_votivas(propios, pareja_misas, indice, fvot, avisos)

    unidades = {}
    for c in sorted(set(list(titulo_de) + list(propios))):
        if c in pareja_vot:
            unidades[c] = 'misa/' + pareja_vot[c]
        else:
            unidades[c] = unidad_de_cel(c, titulo_de.get(c), avisos,
                                        fechas_de, cal, titulo_de)
    # el santoral: el latino va a la unidad de su celebración
    for kla, slug in pareja_sant.items():
        u = unidades.get(slug)
        if u:
            ula.setdefault(u, []).append(kla)
            for extra in alternos.get(slug, []):
                ula.setdefault(u, []).append(extra)
    for cel, kls in pareja_misas.items():
        ula.setdefault('misa/' + cel, []).extend(kls)

    latino = {}
    for u, ks in ula.items():
        ks = sorted(set(ks), key=lambda k: lat[k]['linea'])
        latino[u] = {'k': ks[0], 'alt': ks[1:]}

    por_unidad = defaultdict(list)
    for c, u in unidades.items():
        if c in propios:
            por_unidad[u].append(c)

    # --- los textos sueltos: a la unidad en que caen todos sus días -------
    # Un día puede estar atribuido a una celebración que no tiene textos
    # propios —el misalito nombra «Misa de la I Semana del Tiempo Ordinario» y
    # todas sus piezas se fueron a los sueltos—, y esa celebración no está en
    # la tabla de unidades porque la tabla se hace con las que sí los tienen.
    # Hay que darle unidad igual: si no, ese día se perdería y el texto se
    # colocaría con un testigo menos del que tiene.
    def unidad_de(cel):
        if cel not in unidades:
            unidades[cel] = unidad_de_cel(cel, titulo_de.get(cel), avisos,
                                          fechas_de, cal, titulo_de)
        return unidades[cel]

    sueltos_de = defaultdict(list)
    sueltos_u = {}
    for i, s in enumerate(sueltos):
        us = set()
        for t in s['testigos']:
            fecha, j = t.split('/')
            forms = dias.get(fecha) or []
            if int(j) < len(forms) and forms[int(j)].get('cel'):
                us.add(unidad_de(forms[int(j)]['cel']))
        us.discard(None)
        if len(us) == 1:
            u = us.pop()
            sueltos_u[i] = u
            sueltos_de[u].append((i, s['ranura']))
        else:
            sueltos_u[i] = None

    # --- los comunes que cada celebración ofrece --------------------------
    comunes_de = {}
    for e in cal['santoral']:
        cs = ['com/' + b['clave'][1].replace('.html', '').lower()
              for b in e.get('bloques') or [] if b['etiqueta'] != 'Propio']
        if cs:
            comunes_de[e['slug']] = [c for u in cs
                                     for c in por_unidad.get(u, [])]

    # --- el formulario, clave por clave -----------------------------------
    impreso = lo_impreso(propios, sueltos)
    formularios, discrepancias = {}, []
    sant_por_slug = {e['slug']: e for e in cal['santoral']}
    for clave, (cel, titulo, seccion, etiqueta) in sorted(porclave.items()):
        u = unidades.get(cel) or ('cel/' + cel)
        la = latino.get(u, {})
        piezas, disc = resuelve(cel, u, propios, por_unidad, sueltos_de,
                                comunes_de, latino, lat, dias_de, impreso,
                                sueltos, dias)
        discrepancias += [(clave, cel) + x for x in disc]
        pr, prop = [], None
        for c in [cel] + [x for x in por_unidad.get(u, []) if x != cel]:
            for x in propios.get(c, {}).get('prefacio') or []:
                if x == '@propio':
                    prop = prop or '@propio'
                elif x not in pr:
                    pr.append(x)
        sant = sant_por_slug.get(cel, {})
        gl = cr = None
        for c in [cel] + [x for x in por_unidad.get(u, []) if x != cel]:
            if 'gloria' in propios.get(c, {}):
                gl = propios[c]['gloria'] if gl is None else gl
            if 'credo' in propios.get(c, {}):
                cr = propios[c]['credo'] if cr is None else cr
        if gl is None and la.get('k'):
            gl = lat[la['k']].get('gloria')
        if cr is None and la.get('k'):
            cr = lat[la['k']].get('credo')
        lecturas = []
        for x in porclave_lect.get(clave, []):
            cita_es, via, otros = empareja_lectura(
                clave, x, d['pericopas'], idx_peri, idx_vers, cand_dia,
                cuenta_rutas)
            vi = (variante_del_dia(d['pericopas'][cita_es],
                                   dias_clave.get(clave) or set(), sitio,
                                   cuenta_rutas) if cita_es else 0)
            e = {'o': x['o'], 'tipo': x['tipo'], 'cita': x['cita'],
                 'es': cita_es, 'via_es': via, 'otros_vers': otros,
                 't': (len(d['pericopas'][cita_es]['testigos'])
                       if cita_es else None)}
            if vi:
                p = d['pericopas'][cita_es]['variantes'][vi - 1]
                e['vi'] = vi
                e['t'] = len(p['testigos'])
            lecturas.append(e)
        formularios[clave] = {
            'cel': cel, 'titulo': titulo, 'seccion': seccion,
            'etiqueta': etiqueta, 'u': u, 'la': la.get('k'),
            'alt': la.get('alt') or [],
            'grado': sant.get('rotulo_grado'), 'color': sant.get('color'),
            'resena': (propios.get(cel, {}) or {}).get('resena'),
            'gloria': gl, 'credo': cr, 'prefacio': pr,
            'prefacio_propio': prop,
            'piezas': piezas, 'lecturas': lecturas,
            'v': veredicto(piezas, bool(la.get('k')))}

    # el último paso de la cascada, que necesita todos los formularios ya
    # resueltos para poder preguntar «¿esta oración latina está traducida en
    # otro sitio?»
    cuenta_gem = {}
    n_gem, gem_amb = gemelas(formularios, lat, cuenta_gem)
    print('  gemelas: %d ranuras rescatadas del latín, %d ambiguas'
          % (n_gem, len(gem_amb)))

    pref, pref_sueltos = puente_prefacios(d['pref_es'], d['lat']['prefacios'],
                                          avisos)
    cuenta_citas, difieren = coteja_citas(
        dias, cal, porclave_lect, bloques_de_cel(indice),
        anio_liturgico(cal), avisos)

    salida = {
        'fuente': 'fase 5 — el resolvedor',
        'unidades': unidades,
        'latino': latino,
        'formularios': formularios,
        'prefacios': pref,
        'sueltos': {str(i): u for i, u in sueltos_u.items()},
    }
    os.makedirs(LIBRO, exist_ok=True)
    with open(SALIDA, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, sort_keys=True, indent=1)
    print('  %s: %d formularios' % (os.path.relpath(SALIDA, RAIZ),
                                    len(formularios)))

    informe(d, formularios, unidades, latino, por_unidad, sueltos_u,
            sueltos_de, pref, pref_sueltos, cuenta_citas, difieren,
            discrepancias, fsant, fmisas, fvot, avisos, cuenta_rutas,
            cuenta_gem)


if __name__ == '__main__':
    main()
