# -*- coding: utf-8 -*-
"""Fase 3c — misalcatolico.com → `datos/web/AAAA-MM.json`, como la fase 3.

La fase 3 parte los cien misalitos en días ya armados. Ésta hace lo mismo con
el sitio que trajo la 3b, y deja **la misma forma** —formularios con cabecera
y bloques rotulados—, para que la fase 4 pueda deshacer los días de las dos
fuentes con un solo código y la 5 contar testigos de las dos.

Lo que esta fuente añade sobre los misalitos:

  * **2016 y 2017 enteros**, y enero a mayo de 2018, que los misalitos no
    tienen (empiezan en junio de 2018);
  * **los dos formularios** cuando el día da opción. El misalito imprime el
    que el editor eligió —de ahí que la fase 4 tuviera que atribuir antes de
    contar—; aquí están los dos, uno detrás del otro;
  * la **fórmula** de cada lectura («Del santo Evangelio según san Marcos:
    1, 29-39») en renglón propio, y el **sumario** en otro, donde el misalito
    los lleva dentro del bloque corrido.

## El marcado no es uno, y por eso no se mira el marcado

Diez años de sitio son varias manos y varias plantillas. Medido sobre las
muestras antes de escribir esto:

| cómo rotula | dónde se vio |
|---|---|
| `<h3>` con la cita pegada al rótulo | 2026 |
| `<p>` que abre con `<strong>` | 2016, y la mayor parte de 2018-2024 |
| `<p>` a secas, en mayúsculas, y la cabecera en un `<h3>` | 2025 |
| todo en un solo `<p>`, partido por `<br>` | 2017 |

Cuatro plantillas serían cuatro ramas de código que envejecen mal. Así que
**el marcado no decide**: la tarjeta se aplana a renglones —cada `<br>` y
cada bloque cortan— y el rótulo se reconoce por el **vocabulario de la fase
3**, que es el mismo que se midió contra los cien misalitos. Que un renglón
viniera en `<h3>`, en `<strong>` o a pelo se guarda (`marca`) y se cuenta en
el informe, pero no cambia la decisión.

Lo editorial —la reflexión, el comentario, el tema del día— se reconoce y se
**guarda rotulado**, igual que hace la fase 3, para que la fase 4 lo deje
fuera a sabiendas y no por olvido.

    python Missale/src/3c_web.py
    python Missale/src/3c_web.py --anios 2016 2017      # sólo esos
    python Missale/src/3c_web.py --cotejo               # y el cotejo con la fase 3
"""

import argparse
import datetime as dt
import difflib
import glob
import importlib.util
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misal

from bs4 import BeautifulSoup

FUENTE = os.path.join(misal.TRABAJO, 'web', 'dias')
SECCIONES = os.path.join(misal.TRABAJO, 'web', 'secciones')
SALIDA = os.path.join(misal.DATOS, 'web')
MISALITOS = os.path.join(misal.DATOS, 'misalitos')
INFORME = os.path.join(misal.DATOS, 'web_qa.txt')

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado',
          'domingo']


def modulo(nombre):
    """Importa un script cuyo nombre empieza por un número (como src/13b)."""
    spec = importlib.util.spec_from_file_location(
        'm' + re.sub(r'\W', '', nombre),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# El vocabulario y el reconocedor de rótulos son los de la fase 3, cargados
# de ella y no copiados: si allí se corrige un rótulo mal escrito, aquí vale
# la corrección sin tener que acordarse.
F3 = modulo('3_extraer')
PIEZAS, EDITORIAL = F3.PIEZAS, F3.EDITORIAL
sinac = F3.sinac


# --------------------------------------------------------------------------
# A. de la página a renglones
# --------------------------------------------------------------------------

# La hojarasca de la tarjeta: anuncios, el pie del sitio y la navegación.
BASURA_CLASE = ('banner', 'adsbygoogle', 'mc-footer', 'mc-footer-links',
                'mc-footer-sub', 'd-flex', 'd-grid')
BASURA_TEXTO = re.compile(
    r'^\s*(fuente\s*:\s*misalcatolico|categoria\s*:|categoría\s*:|'
    r'publicado\s*:|anterior\s+siguiente|enlaces\s+útiles)', re.I)

# Las notas del propio sitio, que no son del libro.
NOTA_SITIO = re.compile(r'^\s*(nota|aviso)\s+(del\s+)?(sitio|editor)\b', re.I)


def parte_por_br(nodo):
    """El texto de un nodo, cortado donde la fuente puso un `<br>`."""
    trozos, actual = [], []
    for hijo in nodo.descendants:
        if getattr(hijo, 'name', None) == 'br':
            trozos.append(''.join(actual))
            actual = []
        elif isinstance(hijo, str):
            actual.append(hijo)
    trozos.append(''.join(actual))
    return [t for t in (re.sub(r'\s+', ' ', x).strip() for x in trozos) if t]


def junta_rotulos_partidos(lineas):
    """Vuelve a unir el rótulo que la fuente cortó a media palabra.

    La maqueta vieja parte «ACLAMACIÓN ANTES DEL / EVANGELIO Jn 10, 27» entre
    dos renglones, y entonces el segundo trozo —«EVANGELIO…»— se reconoce
    como el rótulo *Evangelio* y el día aparece con dos evangelios y sin
    aclamación. Es el mismo defecto que a la fase 3 le partía los testigos
    por el guión de renglón.

    No se adivina: sólo se junta cuando el renglón es, sin tildes ni caja, el
    **principio exacto** de un rótulo conocido, y el renglón siguiente lo
    completa. Así «EVANGELIO» suelto se queda como está.
    """
    out, i = [], 0
    while i < len(lineas):
        marca, t = lineas[i]
        if i + 1 < len(lineas):
            k = sinac(t).strip()
            cabe = [c for c in _LARGOS
                    if len(k) < len(sinac(c)) and sinac(c).startswith(k)]
            if k and cabe:
                sig = lineas[i + 1][1]
                unido = (t + ' ' + sig).strip()
                ku = sinac(unido)
                if any(ku.startswith(sinac(c)) for c in cabe):
                    out.append((marca, unido))
                    i += 2
                    continue
        out.append((marca, t))
        i += 1
    return out


def renglones_de(html):
    """La tarjeta del día, aplanada a `[(marca, texto), …]`.

    `marca` dice cómo venía el renglón —`'h3'`, `'strong'`, `'p'` o `'br'`—
    y se guarda sólo para el informe: la decisión la toma el vocabulario.

    Hay dos plantillas de sitio, no una: la de ahora envuelve el día en
    `div.mc-card.p-4`, y la anterior —la que conserva el archivo de la web,
    de donde salen los diciembres que el sitio vivo no sirve— en
    `div.card-body`, con la celebración en un `h1.fs-4` aparte. Se prueban en
    ese orden y lo demás del algoritmo no se entera.
    """
    s = BeautifulSoup(html, 'lxml')
    card = None
    for sel in ('main .mc-card.p-4', '.mc-card.p-4',
                'main .card-body', '.card-body'):
        c = s.select_one(sel)
        if c is not None:
            card = c
            break
    if card is None:
        return None, None
    # la plantilla vieja saca la celebración del cuerpo, a su cabecera
    cab_vieja = s.select_one('.card-header h1, .card-header')
    fecha_hero = None
    hero = s.select_one('.hero-card')
    if hero:
        for p in hero.select('p'):
            t = p.get_text(' ', strip=True)
            if re.search(r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}', t, re.I):
                fecha_hero = t
                break

    for mala in card.select(','.join('.' + c for c in BASURA_CLASE)):
        mala.decompose()
    for mala in card.select('ins, script, style, iframe, nav, button'):
        mala.decompose()

    out = []
    for nodo in card.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'div'],
                              recursive=True):
        # sólo las hojas: un div que contiene p's ya se verá por sus p's
        if nodo.find(['p', 'h3', 'li'], recursive=True):
            continue
        marca_base = nodo.name if nodo.name.startswith('h') else 'p'
        # el <strong> que abre el bloque es el rótulo de la maqueta vieja
        primero = None
        for hijo in nodo.children:
            if getattr(hijo, 'name', None) in ('strong', 'b'):
                primero = hijo
            elif isinstance(hijo, str) and not hijo.strip():
                continue
            break
        abre_fuerte = primero is not None

        # cada <br> corta renglón
        trozos = []
        actual = []
        for hijo in nodo.descendants:
            if getattr(hijo, 'name', None) == 'br':
                trozos.append(''.join(actual))
                actual = []
            elif isinstance(hijo, str):
                actual.append(hijo)
        trozos.append(''.join(actual))
        trozos = [re.sub(r'\s+', ' ', t).strip() for t in trozos]
        trozos = [t for t in trozos if t]
        if not trozos:
            continue
        for i, t in enumerate(trozos):
            if BASURA_TEXTO.match(t) or NOTA_SITIO.match(t):
                continue
            if i == 0 and abre_fuerte and marca_base == 'p':
                marca = 'strong'
            elif len(trozos) > 1:
                marca = 'br'
            else:
                marca = marca_base
            out.append((marca, t))

    # **El día que no viene en párrafos.** Una de las maquetas —2017 entera,
    # y días sueltos de otros años— no envuelve nada: deja el formulario como
    # texto a pelo dentro de la tarjeta, cortado sólo por `<br>`. Ahí el
    # recorrido de arriba no encuentra un solo bloque y el día se perdería en
    # silencio, que es lo peor que puede pasar. Se mide —lo recogido contra
    # lo que la tarjeta dice— y, si falta la mitad, se parte la tarjeta
    # entera por sus `<br>`.
    cuanto = len(re.sub(r'\s+', '', card.get_text(' ', strip=True)))
    tengo = sum(len(re.sub(r'\s+', '', t)) for _, t in out)
    if cuanto and tengo < 0.5 * cuanto:
        out = [('br', t) for t in parte_por_br(card)
               if not BASURA_TEXTO.match(t) and not NOTA_SITIO.match(t)]

    out = junta_rotulos_partidos(out)

    # La plantilla vieja nombra la celebración en su `card-header`, fuera del
    # cuerpo. Si no se le pone delante, la cabecera se queda sin color ni
    # grado y el día entero parece anónimo.
    if cab_vieja is not None:
        t = re.sub(r'\s+', ' ', cab_vieja.get_text(' ', strip=True))
        if t and not BASURA_TEXTO.match(t) and (not out or out[0][1] != t):
            out.insert(0, ('h1', t))
    return out, fecha_hero


# --------------------------------------------------------------------------
# B. qué es cada renglón
# --------------------------------------------------------------------------

_LARGOS = sorted(PIEZAS + EDITORIAL, key=len, reverse=True)

# Rótulos que sólo este sitio usa, y que no son ranura del formulario sino
# divisores de la misa. Se reconocen para que no se tomen por cuerpo.
DIVISORES = ['LITURGIA DE LA PALABRA', 'LITURGIA EUCARÍSTICA',
             'RITOS INICIALES', 'RITOS FINALES', 'RITO DE CONCLUSIÓN',
             'LITURGIA DE LA EUCARISTÍA']
_DIVISORES = {sinac(d) for d in DIVISORES}

# La fórmula con que empieza una lectura, que este sitio imprime en renglón
# propio. Es el ancla de la perícopa (lo midió la fase 6).
FORMULA = re.compile(
    r'^\s*(?:del?\s+(?:santo\s+)?(?:libro|primer|segundo|tercer|cuarto|'
    r'evangelio|profeta|apocalipsis|hechos|carta|cantar|salmo|los\s|la\s|'
    r'el\s)|lectura\s+(?:del|de)\s|comienzo\s+del?\s|'
    r'de\s+la\s+(?:carta|profecía|primera|segunda))', re.I)

# «R/. …» o «R. …»: la respuesta del pueblo.
RESPUESTA = re.compile(r'^\s*R\s*/?\s*\.', re.I)

# El sumario, que la fuente escribe entre corchetes.
SUMARIO = re.compile(r'^\s*\[(.+?)\]\s*$', re.S)

# La cita que va pegada al rótulo: lo que queda después de él.
CITA_LIMPIA = re.compile(r'^[\s:.–—-]+|[\s:.]+$')


def rotulo_de(linea):
    """`(canónico, crudo, resto)` si el renglón abre con un rótulo conocido.

    Se busca el rótulo entero al principio, del más largo al más corto, para
    que «ACLAMACIÓN ANTES DEL EVANGELIO» gane a «EVANGELIO». El sitio lo
    escribe unas veces en mayúsculas y otras no, y en 2026 lo da con la cita
    pegada y todo en mayúsculas, así que se compara sin tildes ni caja.
    """
    k = sinac(linea)
    for canon in _LARGOS:
        kc = sinac(canon)
        if k.startswith(kc):
            resto = linea[len(canon):] if len(linea) >= len(canon) else ''
            # el rótulo puede venir con la caja cambiada: se corta por largo
            resto = CITA_LIMPIA.sub('', resto)
            return canon, linea[:len(canon)], resto
    for d in _DIVISORES:
        if k.startswith(d):
            return 'DIVISOR', linea, ''
    return None, None, None


# --------------------------------------------------------------------------
# C. la cabecera
# --------------------------------------------------------------------------

# «Azul» es el de la Inmaculada en México, y faltaba: sin él, el 1 de enero
# titulaba «Azul Solemnidad. Jornada Mundial de…» y no se parecía a nada del
# calendario.
COLORES = ('blanco', 'verde', 'rojo', 'morado', 'violeta', 'rosa', 'rosado',
           'negro', 'azul')
GRADOS = ('solemnidad', 'fiesta', 'memoria obligatoria', 'memoria libre',
          'memoria', 'feria mayor', 'feria', 'conmemoración', 'vigilia')

RE_COLOR = re.compile(r'\b(' + '|'.join(COLORES) + r')\b', re.I)
RE_GRADO = re.compile(r'\b(' + '|'.join(g.replace(' ', r'\s+')
                                        for g in GRADOS) + r')\b', re.I)
# Las tres referencias del libro van seguidas en un renglón y separadas de
# cualquier manera —«MR p.170 (181); Lecc. I, p.444; LH de Solemnidad»—, así
# que cada patrón tiene que **pararse** donde empieza la siguiente: con sólo
# `/` y `|` de frontera, `mr` se tragaba la de Lecc. y la de LH enteras.
RE_MR = re.compile(r'\bMR[,.]?\s*pp?\.\s*[^/|;]*?(?=\s*(?:[/|;]|\bLecc|\bLH|$))',
                   re.I)
RE_LECC = re.compile(r'\bLecc\.?[^/|;]*?(?=\s*(?:[/|;]|\bLH|\bMR|$))', re.I)
RE_LH = re.compile(r'\bLH\b[^/|;]*?(?=\s*(?:[/|;]|\bMR|\bLecc|$))', re.I)
RE_OTROS = re.compile(r'^\s*otros\s+santos?\s*:\s*(.*)$', re.I)
# «Feria o San Hilario», «o memoria libre de san Hilario», «O Misa Por…»
RE_ALTERNA = re.compile(r'(?:^|[\s,;])[oO]\s+(misa\s+.{3,}|memoria\s+libre\s+'
                        r'de\s+.{3,}|san[a-z]*\s+.{3,}|beat[oa]s?\s+.{3,}|'
                        r'santos?\s+.{3,})$', re.I)
# el formato de 2025: «Color: Verde/Blanco - F. T. O.: Lunes de la 1a. semana…»
RE_2025 = re.compile(r'^\s*color\s*:\s*([^-]+?)\s*[-–]\s*(.*)$', re.I)
EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿️]')


def limpia_celebracion(t):
    """El renglón de la celebración sin lo que no la nombra: los emojis del
    color, las palabras de color, las tres referencias del libro y las barras
    con que la fuente las separa."""
    t = EMOJI.sub(' ', t or '')
    t = RE_MR.sub(' ', t)
    t = RE_LECC.sub(' ', t)
    t = RE_LH.sub(' ', t)
    for c in COLORES:
        t = re.sub(r'\b%s\b' % c, ' ', t, flags=re.I)
    t = re.sub(r'[/|]', ' ', t)
    return re.sub(r'\s{2,}', ' ', t).strip(' ,;.-–')


def cabecera_de(lineas, fecha):
    """Lo que la fuente nombra al lado del formulario, de sus cuatro maquetas.

    No se adivina el formato: se buscan las piezas —color, grado, la doble
    referencia `MR`/`Lecc.`, los otros santos, la alternativa— donde estén, y
    lo que no se reconoce se guarda en `crudo`, que es lo que la fase 4 relee
    cuando la atribución no le cuadra.
    """
    # `crudo` va como **lista de renglones**, no unida en una cadena: la fase
    # 4 lo recorre renglón a renglón en `alternativa_de` —busca un «o» solo y
    # se queda con el de abajo—, y si le llega una cadena lo recorre carácter
    # a carácter y no encuentra nunca la alternativa.
    crudo = [t for _, t in lineas]
    cab = {'dia': fecha.day, 'semana': SEMANA[fecha.weekday()],
           'fuente': 'web', 'color': None, 'grado': None, 'titulo': None,
           'subtitulo': None, 'resena': None, 'alterna': None,
           'otros_santos': None, 'mr': None, 'lecc': None, 'lh': None,
           'tema': None, 'citas': None, 'crudo': crudo}

    resto = []
    for marca, t in lineas:
        m = RE_OTROS.match(t)
        if m:
            cab['otros_santos'] = m.group(1).strip() or None
            continue
        resto.append((marca, t))

    # la doble referencia del libro: MR p. … / Lecc. … / LH …
    for marca, t in resto:
        for campo, rx in (('mr', RE_MR), ('lecc', RE_LECC), ('lh', RE_LH)):
            if cab[campo] is None:
                m = rx.search(t)
                if m:
                    cab[campo] = m.group(0).strip(' /|.,')

    # el renglón de la celebración: el primero que trae color o grado
    celebra = None
    donde = len(resto)
    for i, (marca, t) in enumerate(resto):
        m25 = RE_2025.match(t)
        if m25:
            cab['color'] = ' / '.join(
                c.strip().capitalize() for c in re.split(r'[/,]', m25.group(1))
                if c.strip())
            celebra, donde = m25.group(2).strip(), i
            break
        if RE_COLOR.search(t) or RE_GRADO.search(t):
            celebra, donde = t, i
            break
    if celebra is None and resto:
        celebra, donde = resto[0][1], 0

    if cab['color'] is None and celebra:
        cols = [c.capitalize() for c in RE_COLOR.findall(EMOJI.sub(' ', celebra))]
        if cols:
            cab['color'] = ' / '.join(dict.fromkeys(cols))

    if celebra:
        t = limpia_celebracion(celebra)
        g = RE_GRADO.search(t)
        if g:
            cab['grado'] = g.group(1).strip().capitalize()
        a = RE_ALTERNA.search(t)
        if a:
            cab['alterna'] = a.group(1).strip(' ,;.')
            t = t[:a.start()].strip(' ,;.-')
        # el grado no es parte del nombre: «Memoria Santos Basilio Magno…» no
        # se parece a nada del calendario, y «Santos Basilio Magno…» sí. Pero
        # si al quitárselo no queda nada, el grado **era** el título —«Feria»,
        # «Solemnidad»—, y vaciarlo sería perder el día.
        if g:
            sin_grado = re.sub(r'\s{2,}', ' ',
                               t[:g.start()] + ' ' + t[g.end():]).strip(' ,;.-–')
            if sin_grado:
                t = sin_grado
        cab['titulo'] = t or None

    # **El nombre de la celebración lo da la propia página, encima del
    # renglón del color** —«Santa María, Madre de Dios», «La Epifanía del
    # Señor»—, y es el campo del que depende la atribución de la fase 4, que
    # lo empareja contra el calendario. Sacarlo del renglón del color dejaba
    # títulos que no se parecen a nada, porque ese renglón lleva al lado el
    # grado, las páginas del Misal y la jornada que toque.
    #
    # La regla es de **posición, no de marcado**: en esta maqueta todos los
    # renglones de la cabecera abren con `<strong>`, el nombre incluido, así
    # que mirar la etiqueta no distingue nada. Y donde no hay nada encima del
    # color —el 13 de enero empieza por «Verde Feria O San Hilario»— manda el
    # renglón del color, que es lo que había antes.
    for marca, t in resto[:donde]:
        if rotulo_de(t)[0] or RE_OTROS.match(t):
            continue
        # el tema del día va en versales, y el nombre de la celebración no
        if t.isupper():
            continue
        # la tira de citas del día —«Nm 6, 22-27; Ga 4,4-7; Lc 2,16-21»—
        if ';' in t and re.search(r'\d', t):
            continue
        limpio = limpia_celebracion(t)
        if not limpio or not 4 <= len(limpio) <= 120:
            continue
        if not RE_GRADO.sub(' ', limpio).strip(' ,;.-–'):
            continue
        cab['titulo'] = limpio
        break

    # el tema del día y la línea de citas, que sólo trae la maqueta vieja
    for marca, t in resto:
        if cab['tema'] is None and t.isupper() and 8 < len(t) < 90 \
                and not rotulo_de(t)[0]:
            cab['tema'] = t
        if cab['citas'] is None and re.match(
                r'^[1-4]?\s?[A-ZÁÉÍÓÚ][a-zñáéíóú]{1,12}\.?\s+\d', t) \
                and ';' in t and len(t) < 120:
            cab['citas'] = t
    return cab


# --------------------------------------------------------------------------
# D. el día entero
# --------------------------------------------------------------------------

PRIMERA_RANURA = 'ANTÍFONA DE ENTRADA'


# Los encabezados de una página que trae sólo las lecturas: en vez de los
# rótulos del formulario, el nombre del libro de donde se lee.
LIBRO_BIBLICO = re.compile(
    r'^\s*(santo\s+)?(evangelio|libro|primer|segundo|tercer|cuarto|carta|'
    r'salmos?|profecía|hechos|apocalipsis|lamentaciones|cantar)\b', re.I)
SIN_MISA = re.compile(r'\bs[áa]bado\s+santo\b', re.I)


def por_que_no(lineas):
    """Por qué un día no dio ni un rótulo. Decirlo importa: un día vacío y un
    día que de verdad no tiene misa no son la misma cosa, y si el informe los
    mete en el mismo saco no hay manera de saber qué falta reparar."""
    todo = ' | '.join(t for _, t in lineas)
    if SIN_MISA.search(todo):
        return 'sin misa: es Sábado Santo, y la fuente lo explica en prosa'
    enc = [t for k, t in lineas if k in ('h1', 'h2', 'h3', 'strong')]
    if sum(1 for t in enc if LIBRO_BIBLICO.match(t)) >= 2:
        return ('sólo las lecturas, sin los propios: la fuente encabeza con '
                'el nombre del libro y no con el rótulo de la ranura')
    if len(todo) < 400:
        return 'la página está casi vacía (%d caracteres)' % len(todo)
    return 'sin rótulo ninguno, y con %d caracteres dentro' % len(todo)


def formularios_de(lineas, fecha):
    """Los formularios de un día: su cabecera y sus bloques rotulados.

    Un formulario nuevo empieza donde vuelve a salir la antífona de entrada,
    que es la primera ranura del Misal. Es así como este sitio imprime la
    opción de los días que la tienen —la feria y la memoria libre, una detrás
    de otra—, y es lo que los misalitos no dan.
    """
    # dónde está cada rótulo
    marcas = []
    for i, (marca, t) in enumerate(lineas):
        canon, crudo, resto = rotulo_de(t)
        marcas.append((canon, crudo, resto))

    cortes = [i for i, (c, _, _) in enumerate(marcas)
              if c == PRIMERA_RANURA]
    primero = next((i for i, (c, _, _) in enumerate(marcas)
                    if c and c != 'DIVISOR'), None)
    if primero is None:
        return [], ['%s: %s' % (fecha.isoformat(), por_que_no(lineas))]
    if not cortes:
        cortes = [primero]
    if cortes[0] > primero:
        # el día empieza por otra ranura (una vigilia, un día sin antífona)
        cortes = [primero] + cortes

    cab = cabecera_de(lineas[:cortes[0]], fecha)

    # Un trozo que no trae ni antífona de entrada ni colecta puede ser un
    # rito que va **antes** de la misa y que la fuente imprime seguido —la
    # bendición de las palmas del Domingo de Ramos, con su propio
    # evangelio—. Contarlo como opción haría creer a la fase 4 que ese día se
    # elegía entre una misa entera y un evangelio suelto.
    #
    # Pero no basta con que falten esas dos ranuras, y lo dijo el Viernes
    # Santo: su liturgia **no tiene** antífona de entrada ni colecta —empieza
    # en silencio—, y es la celebración del día, no un rito previo. Así que
    # la condición es relativa: es previo sólo si además hay otro trozo que
    # sí sea misa.
    trozos = []
    for n, ini in enumerate(cortes):
        fin = cortes[n + 1] if n + 1 < len(cortes) else len(lineas)
        bloques, sueltos = bloques_de(lineas[ini:fin], marcas[ini:fin])
        if not bloques:
            continue
        rs = {b['rotulo'] for b in bloques}
        entera = PRIMERA_RANURA in rs or 'ORACIÓN COLECTA' in rs
        trozos.append([bloques, sueltos, not entera])
    if not any(not t[2] for t in trozos):
        # ninguno la trae: es el día entero, como el Viernes Santo
        for t in trozos:
            t[2] = False

    cuantas_misas = sum(1 for _, _, previo in trozos if not previo)
    out, avisos = [], []
    orden = 0
    for bloques, sueltos, previo in trozos:
        c = dict(cab)
        c['opcion'] = None if previo else orden
        if not previo and orden and cab.get('alterna'):
            c['titulo'], c['alterna'] = cab['alterna'], cab['titulo']
        out.append({'fecha': fecha.isoformat(), 'cabecera': c,
                    'bloques': bloques,
                    'orden': -1 if previo else orden,
                    'parte': 'antes de la misa' if previo else 'misa',
                    'opciones': cuantas_misas})
        avisos += ['%s: %s' % (fecha.isoformat(), s) for s in sueltos]
        if not previo:
            orden += 1
    return out, avisos


def bloques_de(lineas, marcas):
    """Los bloques de un formulario: rótulo, cita, sumario, fórmula y texto."""
    bloques, sueltos = [], []
    actual = None
    for (marca, t), (canon, crudo, resto) in zip(lineas, marcas):
        if canon == 'DIVISOR':
            continue
        if canon:
            if actual:
                bloques.append(cierra(actual))
            # `clase` es lo que la fase 4 mira para decidir si un bloque entra
            # en el libro: sólo lee los de clase «pieza» y «rubrica», y se
            # salta lo demás. Sin ella se saltaría **todos**, y el día
            # entraría vacío sin que nadie se quejara.
            actual = {'clase': 'pieza' if canon in PIEZAS else 'editorial',
                      'rotulo': canon, 'crudo': crudo, 'cita': resto or None,
                      'marca': marca, 'sumario': None, 'formula': None,
                      'texto': []}
            continue
        if actual is None:
            sueltos.append('antes del primer rótulo: %r' % t[:60])
            continue
        m = SUMARIO.match(t)
        if m and actual['sumario'] is None and not actual['texto']:
            actual['sumario'] = m.group(1).strip()
            continue
        if actual['formula'] is None and not actual['texto'] \
                and FORMULA.match(t):
            actual['formula'] = t
            continue
        actual['texto'].append(t)
    if actual:
        bloques.append(cierra(actual))
    return bloques, sueltos


def cierra(b):
    """El bloque listo: el sumario y la fórmula fuera del cuerpo.

    **El sumario es lo que va delante de la fórmula**, y eso lo estableció la
    fase 6 midiendo los misalitos: por sí mismo no se distingue del cuerpo,
    pero la fórmula sí se reconoce, y entonces lo de antes es el sumario.
    Buscarlo sólo por los corchetes daba 3 sumarios en mil quinientos días,
    porque esta fuente los pone unas veces entre corchetes y otras a pelo —y
    a veces con el corchete partido entre dos renglones, que es peor que no
    tenerlo.
    """
    # el sumario entre corchetes, pegado al principio del cuerpo
    if b['sumario'] is None and b['texto']:
        m = re.match(r'^\s*\[(.+?)\]\s*(.*)$', b['texto'][0], re.S)
        if m:
            b['sumario'] = m.group(1).strip()
            if m.group(2).strip():
                b['texto'][0] = m.group(2).strip()
            else:
                b['texto'].pop(0)

    # la fórmula, dentro de los primeros renglones; lo que quede delante de
    # ella es el sumario, lleve corchetes o no
    if b['formula'] is None:
        for i, t in enumerate(b['texto'][:3]):
            if not FORMULA.match(t):
                continue
            b['formula'] = t
            delante = [x for x in b['texto'][:i]]
            del b['texto'][:i + 1]
            if delante and b['sumario'] is None:
                corchete = re.match(r'^\s*\[?(.+?)\]?\s*$',
                                    ' '.join(delante), re.S)
                b['sumario'] = corchete.group(1).strip() if corchete \
                    else ' '.join(delante)
            elif delante:
                b['texto'] = delante + b['texto']
            break
    return b


# --------------------------------------------------------------------------
# E. la pasada
# --------------------------------------------------------------------------

def lee_dia(ruta, fecha):
    html = open(ruta, encoding='utf-8', errors='replace').read()
    lineas, fecha_hero = renglones_de(html)
    if lineas is None:
        return [], ['%s: la página no trae tarjeta' % fecha.isoformat()], None
    forms, avisos = formularios_de(lineas, fecha)
    # el sitio nombra el día en su cabecera: se coteja con la fecha de la URL
    if fecha_hero:
        m = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', fecha_hero, re.I)
        if m:
            mes = sinac(m.group(2))
            nm = next((i + 1 for i, x in enumerate(MESES) if sinac(x) == mes), 0)
            if (int(m.group(1)), nm, int(m.group(3))) != \
                    (fecha.day, fecha.month, fecha.year):
                avisos.append('%s: la página se titula «%s»'
                              % (fecha.isoformat(), fecha_hero))
    marcas = Counter(m for m, _ in lineas)
    return forms, avisos, marcas


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--anios', nargs='*', type=int)
    ap.add_argument('--sin-secciones', action='store_true',
                    help='sólo los días, sin el Ordinario ni los prefacios')
    ap.add_argument('--cotejo', action='store_true',
                    help='además, el cotejo con los cien misalitos')
    args = ap.parse_args()

    if not os.path.isdir(FUENTE):
        sys.exit('no hay nada en %s: corre antes 3b_bajar.py' % FUENTE)
    os.makedirs(SALIDA, exist_ok=True)

    inf = Informe()
    inf.titulo('Fase 3c — misalcatolico.com, la segunda fuente castellana')

    por_mes = defaultdict(list)
    for ruta in sorted(glob.glob(os.path.join(FUENTE, '*', '*', '*.html'))):
        p = ruta.replace('\\', '/').split('/')
        a, m, d = int(p[-3]), int(p[-2]), int(p[-1][:2])
        if args.anios and a not in args.anios:
            continue
        por_mes[(a, m)].append((d, ruta))

    if not por_mes:
        sys.exit('no hay días que leer')

    marcas_tot = Counter()
    avisos_tot = []
    rotulos_tot = Counter()
    con_opcion = 0
    previos = 0
    repetidas = Counter()
    dias_tot = formas_tot = 0
    sin_tarjeta = []

    for (a, m), dias in sorted(por_mes.items()):
        forms, avisos = [], []
        for d, ruta in sorted(dias):
            try:
                fecha = dt.date(a, m, d)
            except ValueError:
                avisos.append('%04d-%02d-%02d: no es una fecha' % (a, m, d))
                continue
            fs, avs, marcas = lee_dia(ruta, fecha)
            if marcas is None:
                sin_tarjeta.append(fecha.isoformat())
            else:
                marcas_tot.update(marcas)
            if not fs:
                avisos += avs or ['%s: sin formulario' % fecha.isoformat()]
                continue
            dias_tot += 1
            if max(f['opciones'] for f in fs) > 1:
                con_opcion += 1
            previos += sum(1 for f in fs if f['parte'] != 'misa')
            for f in fs:
                rs = [b['rotulo'] for b in f['bloques']]
                rotulos_tot.update(rs)
                for r, n in Counter(rs).items():
                    if n > 1:
                        repetidas[r] += 1
            forms += fs
            avisos += avs
        formas_tot += len(forms)
        salida = os.path.join(SALIDA, '%04d-%02d.json' % (a, m))
        with open(salida, 'w', encoding='utf-8') as fh:
            json.dump({'fuente': 'misalcatolico.com', 'anio': a, 'mes': m,
                       'dias': len(dias), 'formularios': forms,
                       'avisos': avisos}, fh, ensure_ascii=False, indent=1)
        avisos_tot += avisos

    inf.di('%d meses, %d días con formulario, %d formularios.'
           % (len(por_mes), dias_tot, formas_tot))
    inf.di('%d días traen más de un formulario: la opción que el misalito no'
           % con_opcion)
    inf.di('da, porque su editor ya había elegido.')
    if previos:
        inf.di('%d trozos van antes de la misa y no son alternativa suya: la'
               % previos)
        inf.di('bendición de las palmas y lo que la Vigilia pascual pone')
        inf.di('delante. Quedan rotulados «antes de la misa».')
    inf.blanco()

    inf.sub('Cómo venía rotulado cada renglón')
    inf.di('El marcado no decide nada —el rótulo se reconoce por el')
    inf.di('vocabulario de la fase 3—, pero conviene saber con qué se topa:')
    inf.blanco()
    for marca, n in marcas_tot.most_common():
        inf.di('  %-8s %7d' % (marca, n))
    inf.blanco()

    inf.sub('Los rótulos que salieron, y cuántas veces')
    for r, n in rotulos_tot.most_common():
        inf.di('  %-34s %6d' % (r, n))
    inf.blanco()

    if repetidas:
        inf.sub('Ranuras que salen más de una vez en el mismo formulario')
        inf.di('No es un defecto del corte: es el Misal dando a elegir —dos')
        inf.di('colectas, dos antífonas— y la fuente imprimiendo las dos. Son')
        inf.di('alternativas, y la fase 4 las cuenta como tales.')
        inf.blanco()
        for r, n in repetidas.most_common():
            inf.di('  %-34s %6d formularios' % (r, n))
        inf.blanco()

    faltan = [r for r in PIEZAS if r not in rotulos_tot]
    if faltan:
        inf.di('No salió ninguna vez: ' + ', '.join(faltan))
        inf.blanco()

    if sin_tarjeta:
        inf.sub('Páginas sin tarjeta (%d)' % len(sin_tarjeta))
        for f in sin_tarjeta[:30]:
            inf.di('  ' + f)
        if len(sin_tarjeta) > 30:
            inf.di('  … y %d más' % (len(sin_tarjeta) - 30))
        inf.blanco()

    if avisos_tot:
        inf.sub('Avisos (%d)' % len(avisos_tot))
        for a in avisos_tot[:60]:
            inf.di('  ' + a)
        if len(avisos_tot) > 60:
            inf.di('  … y %d más, en los AAAA-MM.json' % (len(avisos_tot) - 60))
        inf.blanco()

    if not args.sin_secciones:
        secciones(inf)

    if args.cotejo:
        cotejo(inf)

    inf.escribe(INFORME)
    print('\n%d formularios en %s' % (formas_tot, SALIDA))
    print('informe en %s' % INFORME)


# --------------------------------------------------------------------------
# F. el cotejo con los cien misalitos
# --------------------------------------------------------------------------

def clave_texto(s):
    """El texto aplastado, para comparar dos fuentes que puntúan distinto."""
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s.lower())


def cotejo(inf):
    """Qué dicen las dos fuentes de los días que las dos tienen."""
    inf.sub('El cotejo con los cien misalitos')
    if not os.path.isdir(MISALITOS):
        inf.di('No hay %s: la fase 3 no se ha corrido.' % MISALITOS)
        return

    mis = {}
    for ruta in sorted(glob.glob(os.path.join(MISALITOS, '*.json'))):
        d = json.load(open(ruta, encoding='utf-8'))
        for f in d.get('formularios', []):
            if f.get('fecha'):
                mis.setdefault(f['fecha'], []).append(f)
    web = {}
    for ruta in sorted(glob.glob(os.path.join(SALIDA, '*.json'))):
        if os.path.basename(ruta) == 'secciones.json':
            continue
        d = json.load(open(ruta, encoding='utf-8'))
        for f in d.get('formularios', []):
            # la bendición de las palmas no se coteja con la misa del día
            if f.get('parte', 'misa') != 'misa':
                continue
            web.setdefault(f['fecha'], []).append(f)

    inf.di('misalitos: %d días    sitio: %d días' % (len(mis), len(web)))
    solo_web = sorted(set(web) - set(mis))
    solo_mis = sorted(set(mis) - set(web))
    ambos = sorted(set(web) & set(mis))
    inf.di('sólo en el sitio: %d    sólo en los misalitos: %d    en los dos: %d'
           % (len(solo_web), len(solo_mis), len(ambos)))
    if solo_web:
        inf.di('  del sitio, el primero %s y el último %s'
               % (solo_web[0], solo_web[-1]))
        por_anio = Counter(f[:4] for f in solo_web)
        inf.di('  por año: ' + ', '.join('%s: %d' % x
                                         for x in sorted(por_anio.items())))
    if solo_mis:
        inf.di('  de los misalitos, %d días que el sitio no da:' % len(solo_mis))
        for f in solo_mis[:20]:
            inf.di('    ' + f)
        if len(solo_mis) > 20:
            inf.di('    … y %d más' % (len(solo_mis) - 20))
    inf.blanco()

    # ¿Dicen lo mismo? Cada ranura del misalito se mide contra **todos** los
    # bloques de ese rótulo que el sitio imprime ese día, no contra uno.
    #
    # La primera versión los metía en un diccionario por rótulo y se quedaba
    # con el último, y eso falseaba la cuenta dos veces: en los 175
    # formularios con dos colectas comparaba una sola, y en los días con
    # opción comparaba la feria contra la memoria. Daba 60 % de discrepancia
    # donde no la había.
    ESCALA = [('palabra por palabra', 0.999), ('casi igual', 0.95),
              ('parecido', 0.80), ('flojo', 0.50)]
    bloques_web = defaultdict(lambda: defaultdict(list))
    for f, ws in web.items():
        for w in ws:
            for b in w['bloques']:
                bloques_web[f][b['rotulo']].append(' '.join(b['texto']))

    igual = Counter()
    por_ranura = defaultdict(Counter)
    for f in ambos:
        for b in mis[f][0]['bloques']:
            r, t = b['rotulo'], ' '.join(b['texto'])
            cands = bloques_web[f].get(r)
            if not cands:
                igual['la ranura no está en el sitio'] += 1
                continue
            ka = clave_texto(t)[:400]
            mejor = max(difflib.SequenceMatcher(None, ka,
                                                clave_texto(c)[:400]).ratio()
                        for c in cands)
            nombre = next((n for n, u in ESCALA if mejor >= u), 'distinto')
            igual[nombre] += 1
            por_ranura[r][nombre] += 1

    comparables = sum(v for k, v in igual.items()
                      if k != 'la ranura no está en el sitio')
    inf.di('Las ranuras de los %d días que están en las dos fuentes, cada una'
           % len(ambos))
    inf.di('medida contra todos los bloques de su rótulo que el sitio da:')
    inf.blanco()
    for nombre, _ in ESCALA + [('distinto', 0)]:
        n = igual.get(nombre, 0)
        inf.di('  %-24s %6d  %5.1f%%'
               % (nombre, n, 100.0 * n / comparables if comparables else 0))
    inf.di('  %-24s %6d' % ('no está en el sitio',
                            igual['la ranura no está en el sitio']))
    inf.blanco()

    inf.di('Y por ranura, lo que cuadra al 0,80 o mejor:')
    inf.blanco()
    for r, cc in sorted(por_ranura.items(), key=lambda x: -sum(x[1].values())):
        n = sum(cc.values())
        bien = cc['palabra por palabra'] + cc['casi igual'] + cc['parecido']
        inf.di('  %-34s %5d  %5.1f%%' % (r, n, 100.0 * bien / n))
    inf.blanco()
    inf.di('Las lecturas cuadran y los propios no, y eso **no es un defecto de')
    inf.di('la extracción: es el hallazgo.** La lectura la fija el leccionario')
    inf.di('—manda el día, se celebre lo que se celebre—, así que las dos')
    inf.di('fuentes dan la misma. El propio depende de **qué celebración')
    inf.di('eligió el editor** en una feria con memoria libre, y ahí cada uno')
    inf.di('eligió lo suyo: es exactamente lo que la fase 4 tuvo que atribuir')
    inf.di('antes de contar, y la razón de que este sitio valga —da los dos—.')
    inf.di('La reflexión cuadra un 0 %, como debe: es prosa del editor.')
    inf.blanco()

    inf.sub('Lo que esta fuente trae y los misalitos no imprimieron nunca')
    inf.di('No por días —eso es lo de arriba—, sino por **textos**: cuántas')
    inf.di('piezas distintas aparecen en el sitio que no están en ninguno de')
    inf.di('los cien misalitos, en ningún día. Es la cosecha neta, y la razón')
    inf.di('de todo esto.')
    inf.blanco()
    tex_mis = defaultdict(set)
    for fs in mis.values():
        for f in fs:
            for b in f['bloques']:
                t = clave_texto(' '.join(b['texto']))
                if len(t) > 24:
                    tex_mis[b['rotulo']].add(t)
    tex_web = defaultdict(set)
    for fs in web.values():
        for f in fs:
            for b in f['bloques']:
                t = clave_texto(' '.join(b['texto']))
                if len(t) > 24:
                    tex_web[b['rotulo']].add(t)
    inf.di('  %-34s %8s %8s %8s' % ('ranura', 'sitio', 'misal.', 'nuevos'))
    nuevos_tot = 0
    for r in [x for x in PIEZAS if x in tex_web]:
        nuevos = tex_web[r] - tex_mis.get(r, set())
        nuevos_tot += len(nuevos)
        inf.di('  %-34s %8d %8d %8d'
               % (r, len(tex_web[r]), len(tex_mis.get(r, set())), len(nuevos)))
    inf.blanco()
    inf.di('%d textos que los misalitos no tienen. Cuidado al leer esta cifra:'
           % nuevos_tot)
    inf.di('va aplastada y entera, así que una pieza que los dos traen con una')
    inf.di('palabra de diferencia cuenta como nueva. Es un techo, no un')
    inf.di('recuento; lo que de verdad entre en el libro lo dirá la fase 4')
    inf.di('cuando lea las dos fuentes y cuente testigos.')
    inf.blanco()

    inf.sub('El orden y la disposición')
    orden_web = Counter()
    orden_mis = Counter()
    for f, fs in web.items():
        orden_web[tuple(b['rotulo'] for b in fs[0]['bloques'])] += 1
    for f, fs in mis.items():
        orden_mis[tuple(b['rotulo'] for b in fs[0]['bloques'])] += 1
    inf.di('El sitio imprime %d secuencias distintas de rótulos; los'
           % len(orden_web))
    inf.di('misalitos, %d. Las cinco más frecuentes de cada uno:'
           % len(orden_mis))
    for nom, c in (('sitio', orden_web), ('misalitos', orden_mis)):
        inf.blanco()
        inf.di('  %s:' % nom)
        for seq, n in c.most_common(5):
            inf.di('    %4d  %s' % (n, ' · '.join(seq)))
    inf.blanco()

    # lo que el sitio da y el misalito no: fórmula y sumario en renglón propio
    con_formula = sum(1 for fs in web.values() for w in fs
                      for b in w['bloques'] if b.get('formula'))
    con_sumario = sum(1 for fs in web.values() for w in fs
                      for b in w['bloques'] if b.get('sumario'))
    inf.di('Del sitio salen %d fórmulas y %d sumarios en renglón propio, que'
           % (con_formula, con_sumario))
    inf.di('en el misalito van dentro del bloque corrido y la fase 6 tuvo que')
    inf.di('reconocer por su forma.')


# --------------------------------------------------------------------------
# G. las secciones que no son de un día
# --------------------------------------------------------------------------
#
# El sitio publica, además del día, el Ordinario y los prefacios enteros, el
# santoral mes a mes y el salterio. El Ordinario y los prefacios ya los tiene
# el proyecto del *Ordinario de la Misa* de México, que viene **numerado 1-146**
# y es el que manda; éstos valen como segundo testigo —para cotejar una
# lectura dudosa— y porque el sitio nombra cada prefacio, que es por donde la
# fase 1 los empareja.

ROMANOS = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
           'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12}
RE_PREFACIO = re.compile(r'^\s*prefacio', re.I)
# «Prefacio común I», «Prefacio I/B de Adviento», «PrefacioIV de Cuaresma»:
# el número cae antes o después de la familia, y a veces sin espacio delante.
RE_NUM = re.compile(r'\b(' + '|'.join(sorted(ROMANOS, key=len, reverse=True))
                    + r')\b(?:\s*/\s*([A-Z]))?')

QUIEN = re.compile(r'^\s*(C|T|D|S|P)\s*\.\s*', re.I)
QUIEN_LARGO = re.compile(
    r'^\s*(celebrante|todos|diácono|diacono|sacerdote|pueblo|lector|'
    r'ministro)\s*:\s*', re.I)
O_BIEN = re.compile(r'^\s*o\s+bien\s*:?\s*$', re.I)


# Las palabras que la fuente pone o quita sin que cambie de prefacio, y que
# por tanto no pueden formar parte de la llave: «Prefacio para los Domingos
# del Tiempo Ordinario» y «Prefacio para los Domingos en Tiempo Ordinario»
# son el mismo.
VACIAS = {'de', 'del', 'de la', 'de los', 'de las', 'la', 'el', 'los', 'las',
          'en', 'para', 'por', 'y', 'the'}


def nombre_prefacio(nombre):
    """`(familia, número, letra)` de como el sitio nombra un prefacio.

    La fuente no es consistente, y de tres maneras a la vez: el número cae
    antes o después de la familia («de Cuaresma I», «II de Cuaresma»), a
    veces va pegado a la palabra «Prefacio» («PrefacioIV»), y la familia
    cambia de caja y de palabras de relleno («para los Domingos **del**
    Tiempo Ordinario» y «para los Domingos **en** Tiempo Ordinario»). Hasta
    se come un espacio («laReconciliación»).

    Así que la familia se reduce a su llave: sin tildes, en minúscula, sin
    las palabras de relleno y con los pegotes separados. Es lo mismo que hizo
    la fase 1 con el Misal latino: emparejar por el número que la propia
    fuente da, no por como lo escribe.
    """
    t = re.sub(r'^\s*prefacio\s*', '', nombre, flags=re.I)
    m = RE_NUM.search(t)
    num = ROMANOS.get(m.group(1)) if m else None
    letra = m.group(2).upper() if m and m.group(2) else None
    fam = (t[:m.start()] + ' ' + t[m.end():]) if m else t
    # «laReconciliación» → «la Reconciliación»
    fam = re.sub(r'(?<=[a-zñáéíóú])(?=[A-ZÑÁÉÍÓÚ])', ' ', fam)
    fam = sinac(fam).replace('-', ' ')
    fam = ' '.join(p for p in fam.split() if p not in VACIAS)
    return (fam or None), num, letra


def lee_prefacios(ruta):
    """Los prefacios del sitio: nombre, título y cuerpo."""
    lineas, _ = renglones_de(open(ruta, encoding='utf-8',
                                  errors='replace').read())
    if not lineas:
        return []
    out, actual = [], None
    for marca, t in lineas:
        if marca == 'strong' and RE_PREFACIO.match(t):
            if actual:
                out.append(actual)
            fam, num, letra = nombre_prefacio(t)
            actual = {'nombre': t, 'familia': fam, 'numero': num,
                      'letra': letra, 'titulo': None, 'texto': []}
            continue
        if actual is None:
            continue
        if actual['titulo'] is None and marca == 'p' and len(t) < 110:
            actual['titulo'] = t
            continue
        actual['texto'].append(t)
    if actual:
        out.append(actual)
    return out


def lee_ordinario(ruta):
    """El Ordinario del sitio, renglón a renglón y diciendo qué es cada uno.

    Cuatro papeles, y los tres primeros se reconocen por su marca: `rótulo`
    (la sección, en mayúsculas), `dicho` (lo que alguien dice, que la fuente
    abre con «C.», «T.» o «Celebrante:»), `opción` (el «O bien:» que el Misal
    pone entre alternativas, y que es lo que permite elegir) y `rúbrica` (lo
    que queda: lo que se hace, no lo que se dice).
    """
    lineas, _ = renglones_de(open(ruta, encoding='utf-8',
                                  errors='replace').read())
    if not lineas:
        return []
    out = []
    for marca, t in lineas:
        if O_BIEN.match(t):
            out.append({'papel': 'opción', 'texto': t})
            continue
        m = QUIEN_LARGO.match(t) or QUIEN.match(t)
        if m:
            quien = m.group(1).strip().rstrip('.').upper()
            quien = {'C': 'celebrante', 'T': 'todos', 'D': 'diácono',
                     'S': 'sacerdote', 'P': 'pueblo'}.get(quien, quien.lower())
            out.append({'papel': 'dicho', 'quien': quien,
                        'texto': t[m.end():].strip()})
            continue
        es_rotulo = (t.isupper() and 4 < len(t) < 60) or \
            (marca == 'strong' and t.isupper())
        out.append({'papel': 'rótulo' if es_rotulo else 'rúbrica',
                    'texto': t})
    return out


def lee_lista(ruta):
    """Una página de lista —el santoral de un mes, un libro de salmos—."""
    lineas, _ = renglones_de(open(ruta, encoding='utf-8',
                                  errors='replace').read())
    return [t for _, t in (lineas or [])]


def secciones(inf):
    """Lo que el sitio publica aparte del día, a `datos/web/secciones.json`."""
    inf.sub('Las secciones que no son de un día')
    if not os.path.isdir(SECCIONES):
        inf.di('No hay %s: la fase 3b no las trajo.' % SECCIONES)
        return

    def ruta(nombre):
        f = os.path.join(SECCIONES, nombre + '.html')
        return f if os.path.exists(f) else None

    out = {}
    r = ruta('prefacios-de-la-misa')
    if r:
        out['prefacios'] = lee_prefacios(r)
        sin_num = [p['nombre'] for p in out['prefacios'] if p['numero'] is None]
        inf.di('%d prefacios. Familias: %s'
               % (len(out['prefacios']),
                  ', '.join('%s (%d)' % x for x in
                            Counter(p['familia'] for p in out['prefacios']
                                    if p['familia']).most_common())))
        if sin_num:
            inf.di('  sin número que leer (%d): %s'
                   % (len(sin_num), '; '.join(sin_num[:6])))
    r = ruta('ordinarios-de-la-misa')
    if r:
        out['ordinario'] = lee_ordinario(r)
        papeles = Counter(x['papel'] for x in out['ordinario'])
        inf.di('Ordinario: %d renglones (%s)'
               % (len(out['ordinario']),
                  ', '.join('%s %d' % (k, v) for k, v in papeles.most_common())))
        quienes = Counter(x.get('quien') for x in out['ordinario']
                          if x['papel'] == 'dicho')
        inf.di('  quien habla: ' + ', '.join('%s %d' % (k, v)
                                             for k, v in quienes.most_common()))
        inf.di('  «O bien» (que es lo que se puede elegir): %d'
               % papeles.get('opción', 0))

    santoral, salmos = {}, {}
    for f in sorted(glob.glob(os.path.join(SECCIONES, 'santoral__*.html'))):
        santoral[os.path.basename(f)[:-5].split('__')[1]] = lee_lista(f)
    for f in sorted(glob.glob(os.path.join(SECCIONES, 'libro-*salmos*.html'))):
        salmos[os.path.basename(f)[:-5]] = lee_lista(f)
    if santoral:
        out['santoral'] = santoral
        inf.di('Santoral: %d meses, %d renglones en total'
               % (len(santoral), sum(len(v) for v in santoral.values())))
    if salmos:
        out['salmos'] = salmos
        inf.di('Salterio: %d páginas, %d renglones'
               % (len(salmos), sum(len(v) for v in salmos.values())))

    if out:
        destino = os.path.join(SALIDA, 'secciones.json')
        with open(destino, 'w', encoding='utf-8') as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        inf.blanco()
        inf.di('En %s.' % destino)
    inf.blanco()
    inf.di('El Ordinario y los prefacios que manda el proyecto siguen siendo')
    inf.di('los del «Ordinario de la Misa» de México, que vienen numerados')
    inf.di('1-146 y se alinean con el Misal latino por ese número. Éstos son')
    inf.di('segundo testigo: sirven para cotejar un renglón dudoso.')


class Informe:
    """El informe, en el estilo de las demás fases: se lee, no se consulta."""

    def __init__(self):
        self.l = []

    def titulo(self, t):
        self.l += [t, '=' * len(t), '']

    def sub(self, t):
        self.l += ['', t, '-' * len(t), '']

    def di(self, t=''):
        self.l.append(t)

    def blanco(self):
        self.l.append('')

    def escribe(self, ruta):
        with open(ruta, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(self.l).rstrip() + '\n')


if __name__ == '__main__':
    main()
