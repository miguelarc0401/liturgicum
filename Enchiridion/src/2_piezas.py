# -*- coding: utf-8 -*-
"""Fase 2 — deshacer el volcado en piezas.

Una página del sitio no es una oración: es una *página*, y puede llevar
dentro varias. El HTML, escrito a mano y siempre igual desde 1998, lo dice
con tres formas que se reconocen sin ambigüedad:

  · la cabecera de la página —celda al 60% con el título en dos renglones,
    el latino y el inglés— titula todo lo que viene debajo;
  · un `div` centrado con esos mismos dos renglones abre una pieza nueva
    dentro de la página: los actos de fe, esperanza y caridad, cada uno con
    su título, viven en una sola página;
  · la oración misma va en tabla de dos columnas al 48%, el latín a la
    izquierda y el inglés a la derecha, y cada fila es una estrofa, un
    versículo o un párrafo.

Todo lo demás de la página es de Michael Martin —la historia de la oración,
el comentario, la indulgencia— y no se guarda: no es la oración. Sí se
guarda la línea de procedencia que a veces precede a una versión («By
Pietro Cardinal Gasparri, Catechismus Catholicus, (1931)»), porque es lo
único que distingue dos versiones de la misma oración, y de ella se saca el
año.

Dentro de la celda hay cuatro marcas que significan algo y se conservan:

  <b>V.</b> <b>R.</b>          el versículo y su respuesta
  <font size="-1" color=rojo>  la rúbrica, que es rúbrica también en latín
  <i>…</i>                     lo que se dice sólo en ciertos casos
  <br>                         el renglón del verso

y dos que no y se van: el `<sup>` de las notas al pie de Martin, y la
versalita roja con que el sitio abre cada oración. Esa versalita es una
trampa: el HTML dice «<font +3>A</font><font +1>DORO</font> te devote», que
en texto llano sería «ADORO te devote», y lo que hay que escribir es «Adoro
te devote». Se baja a minúscula, y los nombres propios se levantan otra vez
con el vocabulario del propio proyecto —el Misal latino y el Ordinario, que
son miles de páginas de latín con sus mayúsculas puestas—. Las 86
versalitas de más de una palabra quedan listadas en el informe, que es
donde se ven los aciertos y los fallos de esa reparación.

Salida:
    TRABAJO/piezas.json              las piezas, con el latín y el inglés
    Enchiridion/datos/piezas_qa.txt  qué se extrajo y qué hay que mirar

El inglés se queda en la carpeta de trabajo: el aviso del sitio permite el
uso personal y de estudio, y la traducción inglesa es de Martin. Lo que la
app publica lo decide la fase 5, y de ahí no sale.

    python Enchiridion/src/2_piezas.py
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, FUENTE, TRABAJO, url_de

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

# La cabecera de la página y el título de una pieza dentro de ella.
CABECERA = re.compile(
    r'(?is)<td[^>]*width:\s*60%[^>]*>\s*<b>\s*<font[^>]*>(.*?)</font>')
TITULO_PIEZA = re.compile(
    r'(?is)<div[^>]*text-align:\s*center[^>]*>\s*<b>\s*'
    r'<font[^>]*size="\+1"[^>]*>(.*?)</font>\s*</b>\s*</div>')

TABLA = re.compile(r'(?is)<table([^>]*)>(.*?)</table>')
FILA = re.compile(r'(?is)<tr[^>]*>(.*?)(?=<tr[^>]*>|</tbody>|</table>|$)')
CELDA_48 = re.compile(r'(?is)<td[^>]*width:\s*48%[^>]*>(.*?)</td>')
CELDA = re.compile(r'(?is)<td[^>]*>(.*?)</td>')

# La tabla de la oración lleva cellpadding="10" y las del comentario
# cellpadding="2": es la única señal que distingue el texto rezado de lo
# que Martin cuenta sobre él, y el sitio la respeta en las 532 tablas.
ES_ORACION = re.compile(r'(?i)cellpadding\s*=\s*"?10"?')

# El rojo hace dos oficios, y los separa el cuerpo de la letra: grande
# (+1, +2, +3) es la versalita con que abre la oración, y pequeño (-1) es
# la rúbrica. La versalita viene en dos fuentes seguidas —la capital y el
# resto de la palabra— o en una sola.
VERSALITA = re.compile(
    r'(?is)<font[^>]*size="\+[123]"[^>]*#?AF0000[^>]*>(.*?)</font>'
    r'(?:\s*<font[^>]*size="\+[123]"[^>]*#?AF0000[^>]*>(.*?)</font>)?')
ROJO = re.compile(r'(?is)<font[^>]*size="-\d"[^>]*#?AF0000[^>]*>(.*?)</font>')

# Un renglón centrado y en negrita titula —«Ad Matutinum», el nombre del
# salmo—, y en cursiva es el epígrafe con que el Oficio lo encabeza. El
# sitio anida las dos etiquetas en los dos órdenes, y da igual cuál.
CENTRADO = re.compile(r'(?is)^((?:<(?:b|i|center)>\s*)+)(.*?)'
                      r'((?:\s*</(?:b|i|center)>)+)$')

ANIO = re.compile(r'\((\d{3,4})\)|\b(1[0-9]{3}|20[0-2][0-9])\b')

# Procedencia metida como fila dentro de la tabla de la oración, que es
# como se separan las versiones en las páginas de una sola columna.
PROCEDENCIA = re.compile(
    r'(?i)^\s*(by|attributed|from|composed|translation|a traditional|'
    r'another|version)\b')

# Para saber en qué lengua está una columna sola: las diez palabras más
# frecuentes de cada lengua en el propio corpus bastan y sobran.
VOCES_LA = set('et in te qui nos non ad per cum est tuum tuae domine deus '
               'me mihi tui sancta sancte nobis quae ut ex'.split())
VOCES_EN = set('the and of thou thee thy to that with for our we are is '
               'from his who have shall all may this'.split())

# marcas internas que sobreviven al borrado de etiquetas
RUB_A, RUB_C = '\x01', '\x02'
CUR_A, CUR_C = '\x04', '\x05'
VER_A, VER_C = '\x06', '\x07'
MARCAS = RUB_A + RUB_C + CUR_A + CUR_C + VER_A + VER_C

# Lo que el inglés escribe con mayúscula dentro de la versalita. El latín
# lo sabe el propio proyecto (lexico_mayusculas); el inglés no hace falta
# que lo sepa bien, porque no se publica.
PROPIOS_EN = {
    'god', 'lord', 'jesus', 'christ', 'mary', 'joseph', 'michael',
    'gabriel', 'raphael', 'holy', 'spirit', 'father', 'son', 'virgin',
    'saint', 'amen', 'i', 'o', 'thee', 'thou', 'thy', 'thine', 'he',
    'him', 'his', 'who', 'queen', 'mother', 'heart', 'cross', 'church',
    'almighty', 'blessed', 'sacrament', 'angel', 'king',
}

PROPIOS = set()          # el léxico latino, lo pone main()
VERSALITAS = []          # [(lado, crudo, puesto)] para el informe


# --------------------------------------------------------------- el texto
def sin_tildes(w):
    w = (w.replace('æ', 'ae').replace('Æ', 'Ae').replace('œ', 'oe')
         .replace('Œ', 'Oe').replace('ǽ', 'ae').replace('Ǽ', 'Ae'))
    w = ''.join(c for c in unicodedata.normalize('NFD', w)
                if not unicodedata.combining(c))
    return w.replace('j', 'i').replace('J', 'I').lower()


def arregla_versalita(palabra, lado):
    """«ADORO» -> «Adoro»; «AVE MARIA» -> «Ave Maria».

    La versalita baja entera a minúscula y luego se levantan los nombres
    propios: el latín con el vocabulario del proyecto, el inglés con una
    lista corta. La primera letra se queda alta siempre.
    """
    propios = PROPIOS if lado == 'la' else PROPIOS_EN
    salida = []
    for trozo in re.split(r'(\W+)', palabra.lower()):
        if trozo and trozo[0].isalpha():
            clave = sin_tildes(trozo) if lado == 'la' else trozo
            if clave in propios:
                trozo = trozo[0].upper() + trozo[1:]
        salida.append(trozo)
    puesto = ''.join(salida).lstrip()
    if puesto:
        puesto = puesto[0].upper() + puesto[1:]
        hueco = palabra[:len(palabra) - len(palabra.lstrip())]
        puesto = hueco + puesto
    if len(palabra.split()) > 1:
        VERSALITAS.append((lado, palabra, puesto))
    return puesto


def limpia(frag, lado):
    """El texto de una celda, en párrafos de renglones de tiradas.

    Devuelve [[ [(estado, texto), …] , …], …]: párrafos, renglones y
    tiradas, donde estado es (rúbrica, cursiva).
    """
    s = re.sub(r'(?is)<sup>.*?</sup>', '', frag)
    s = VERSALITA.sub(lambda m: _versalita(m, lado), s)
    s = ROJO.sub(lambda m: RUB_A + m.group(1) + RUB_C, s)
    s = re.sub(r'(?is)<b>\s*(V\.|R\.|℟\.?|℣\.?)\s*</b>', r'\1 ', s)
    s = re.sub(r'(?is)<i>|<em>', CUR_A, s)
    s = re.sub(r'(?is)</i>|</em>', CUR_C, s)
    s = re.sub(r'(?is)<br\s*/?>', '\n', s)
    s = re.sub(r'(?is)<p\s*/?>|</p>', '\n\n', s)
    s = re.sub(r'(?s)<[^>]+>', '', s)
    s = html.unescape(s).replace(' ', ' ')

    parrafos = []
    for parrafo in re.split(r'\n\s*\n', s):
        renglones = [ln for ln in (_tiradas(x) for x in parrafo.split('\n'))
                     if ln]
        if renglones:
            parrafos.append(renglones)
    return parrafos


def _versalita(m, lado):
    inicial = re.sub(r'(?s)<[^>]+>', '', m.group(1) or '')
    resto = re.sub(r'(?s)<[^>]+>', '', m.group(2) or '')
    palabra = html.unescape(inicial + resto)
    if not palabra.strip():
        return palabra
    return arregla_versalita(palabra, lado)


def _tiradas(cruda):
    """Un renglón en [(estado, texto)], ya sin marcas internas."""
    salida, actual = [], []
    rub = cur = 0
    estado = (False, False)

    def vuelca():
        if actual:
            salida.append([estado, ''.join(actual)])
            del actual[:]

    for ch in cruda:
        if ch in MARCAS:
            vuelca()
            if ch == RUB_A:
                rub += 1
            elif ch == RUB_C:
                rub = max(0, rub - 1)
            elif ch == CUR_A:
                cur += 1
            elif ch == CUR_C:
                cur = max(0, cur - 1)
            estado = (bool(rub), bool(cur))
            continue
        actual.append(ch)
    vuelca()

    junto = []
    for est, t in salida:
        if junto and junto[-1][0] == est:
            junto[-1][1] += t
        else:
            junto.append([est, t])
    for tr in junto:
        tr[1] = re.sub(r'[ \t]+', ' ', tr[1])
    while junto and not junto[0][1].strip():
        junto.pop(0)
    while junto and not junto[-1][1].strip():
        junto.pop()
    if junto:
        junto[0][1] = junto[0][1].lstrip()
        junto[-1][1] = junto[-1][1].rstrip()
    return [(e, t) for e, t in junto if t]


def texto_llano(parrafos):
    return '\n\n'.join('\n'.join(''.join(t for _, t in ln) for ln in p)
                       for p in parrafos)


# ------------------------------------------------------- la página entera
def titulo_doble(frag):
    """«Signum Crucis<br>Sign of the Cross» -> (latín, inglés)."""
    partes = [re.sub(r'(?s)<[^>]+>', '', p)
              for p in re.split(r'(?is)<br\s*/?>', frag)]
    partes = [re.sub(r'\s+', ' ', html.unescape(p)).strip() for p in partes]
    partes = [p for p in partes if p]
    return (partes[0] if partes else '',
            ' '.join(partes[1:]) if len(partes) > 1 else '')


def procedencia(tabla):
    """La línea de procedencia de una versión, si la tabla es una de ésas."""
    celdas = CELDA.findall(tabla)
    if len(celdas) != 1:
        return None
    nota = re.sub(r'\s+', ' ', texto_llano(limpia(celdas[0], 'en'))).strip()
    if not nota or len(nota) > 400:
        return None
    m = ANIO.search(nota)
    return {'nota': nota, 'anio': (m.group(1) or m.group(2)) if m else None}


def clase_centrada(cruda):
    """1 si la celda entera es un titular, 2 si es un epígrafe, 0 si no."""
    t = re.sub(r'(?is)</?span[^>]*>', '', cruda).strip()
    m = CENTRADO.match(t)
    if not m:
        return 0
    etiquetas = set(x.lower() for x in re.findall(r'(?i)<(b|i|center)>',
                                                  m.group(1)))
    if 'center' not in etiquetas:
        return 0
    return 1 if 'b' in etiquetas else (2 if 'i' in etiquetas else 0)


def es_latin(texto):
    """Qué lengua habla una columna sola, por sus palabras de oficio."""
    voces = re.findall(r"[A-Za-zÀ-ÿ']+", texto.lower())
    if not voces:
        return True
    la = sum(1 for v in voces if v in VOCES_LA)
    en = sum(1 for v in voces if v in VOCES_EN)
    return la >= en


def piezas_de(ruta):
    """(clase de la página, piezas) en el orden en que están."""
    s = open(ruta, 'rb').read().decode('iso-8859-1', 'replace')
    if re.search(r'(?i)<meta[^>]*http-equiv\s*=\s*"?refresh', s):
        return 'redirección', []

    cab = CABECERA.search(s)
    tla, ten = titulo_doble(cab.group(1)) if cab else ('', '')

    marcas = [(m.start(), 'titulo', m.group(1))
              for m in TITULO_PIEZA.finditer(s)]
    marcas += [(m.start(), 'tabla', m.group(0), m.group(1))
               for m in TABLA.finditer(s)]
    marcas.sort(key=lambda x: x[0])

    piezas, actual, nota = [], None, None

    def abre(variante=False):
        p = {'tla': (actual or {}).get('tla', tla),
             'ten': (actual or {}).get('ten', ten), 'b': [], 'nota': None,
             'variante': variante}
        piezas.append(p)
        return p

    for marca in marcas:
        tipo, dato = marca[1], marca[2]
        if tipo == 'titulo':
            pla, pen = titulo_doble(dato)
            actual = {'tla': pla, 'ten': pen, 'b': [], 'nota': None,
                      'variante': False}
            piezas.append(actual)
            nota = None
            continue
        if not ES_ORACION.search(marca[3]):
            p = procedencia(dato)
            if p:
                nota = p
            continue
        if actual is None:
            actual = abre()
        if nota:
            if actual['b']:
                actual = abre(variante=True)
            actual['nota'] = nota
            nota = None

        for fila in FILA.findall(dato):
            pares = CELDA_48.findall(fila)
            cruda = pares[0] if pares else ''
            if pares:
                la = limpia(pares[0], 'la')
                en = limpia(pares[1], 'en') if len(pares) > 1 else []
                # Algunas rúbricas las escribió Martin en inglés y están en
                # las dos columnas: «Ending according to the 1962 Missal».
                # Eso no es latín, y en la columna del latín no pinta nada.
                llano = texto_llano(la)
                if len(llano.split()) > 4 and not es_latin(llano):
                    if not en:
                        en = la
                    la = []
            else:
                celdas = CELDA.findall(fila)
                if not celdas:
                    continue
                cruda = celdas[0]
                llano = re.sub(r'(?s)<[^>]+>', ' ', celdas[0])
                llano = re.sub(r'\s+', ' ', html.unescape(llano)).strip()
                if not llano:
                    continue
                # En las páginas de una columna la procedencia de cada
                # versión va dentro de la tabla, como una fila más.
                if len(llano) < 140 and PROCEDENCIA.match(llano):
                    if actual['b']:
                        actual = abre(variante=True)
                    m = ANIO.search(llano)
                    actual['nota'] = {
                        'nota': llano,
                        'anio': (m.group(1) or m.group(2)) if m else None}
                    continue
                if es_latin(llano):
                    la, en = limpia(celdas[0], 'la'), []
                else:
                    la, en = [], limpia(celdas[0], 'en')
            centrada = clase_centrada(cruda)
            for i in range(max(len(la), len(en))):
                bla = la[i] if i < len(la) else []
                ben = en[i] if i < len(en) else []
                if not bla and not ben:
                    continue
                lado = bla or ben
                rub = all(e[0][0] for ln in lado for e in ln)
                b = {'r': 1 if rub else 0, 'la': bla, 'en': ben}
                if centrada:
                    b['h'] = centrada
                actual['b'].append(b)
    piezas = [p for p in piezas if p['b']]
    return ('oración' if piezas else 'sin oración'), piezas


# ------------------------------------------------------------- mayúsculas
def lexico_mayusculas():
    """Palabras que el latín litúrgico escribe con mayúscula en medio de la
    frase, contadas en el Misal latino, el Ordinario y los prefacios."""
    alta, baja = Counter(), Counter()
    for nombre in ('misal_latino.json', 'ordinario.json', 'prefacios.json'):
        ruta = os.path.join(RAIZ, 'app', 'datos', nombre)
        if not os.path.exists(ruta):
            continue
        with open(ruta, encoding='utf-8') as fh:
            texto = fh.read()
        for frase in re.findall(r'"([^"\\]{8,})"', texto):
            palabras = re.findall(r"[A-Za-zÀ-ÿǼǽÆæŒœ]+", frase)
            for w in palabras[1:]:
                if len(w) < 3:
                    continue
                clave = sin_tildes(w)
                (alta if w[0].isupper() else baja)[clave] += 1
    return {w for w, n in alta.items()
            if n >= 3 and n >= 4 * baja.get(w, 0)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    if not os.path.isdir(FUENTE):
        sys.exit('no hay volcado: corre primero Enchiridion/src/1_bajar.py')

    PROPIOS.update(lexico_mayusculas())
    print('%d formas latinas con mayúscula propia' % len(PROPIOS))

    cuenta = Counter()
    todo = []
    for d, _, fs in os.walk(FUENTE):
        for f in sorted(fs):
            if not f.lower().endswith(('.html', '.htm')):
                continue
            ruta = os.path.join(d, f)
            clase, piezas = piezas_de(ruta)
            cuenta[clase] += 1
            if not piezas:
                continue
            rel = os.path.relpath(ruta, FUENTE).replace(os.sep, '/')
            cat = '/'.join(rel.split('/')[1:-1]) or '-'
            for i, p in enumerate(piezas):
                la = texto_llano([b['la'] for b in p['b'] if b['la']])
                en = texto_llano([b['en'] for b in p['b'] if b['en']])
                todo.append(OrderedDict([
                    ('id', 'pl_' + hashlib.sha256(
                        (rel + '#' + str(i)).encode()).hexdigest()[:12]),
                    ('pagina', rel), ('url', url_de(ruta)), ('cat', cat),
                    ('orden', i), ('tla', p['tla']), ('ten', p['ten']),
                    ('nota', p['nota']),
                    ('variante', p.get('variante', False)),
                    ('sha_la', hashlib.sha256(la.encode()).hexdigest()),
                    ('n_bloques', len(p['b'])),
                    ('car_la', len(la)), ('car_en', len(en)),
                    ('b', [dict(
                        [('r', b['r'])]
                        + ([('h', b['h'])] if b.get('h') else [])
                        + [('la', [[list(x) for x in ln] for ln in b['la']]),
                           ('en', [[list(x) for x in ln] for ln in b['en']])])
                        for b in p['b']]),
                ]))

    # Duplicados exactos: varios himnos están dos veces, uno en Hymni/ y
    # otro en su tiempo litúrgico. Manda el de la ruta más honda, que es el
    # que el índice enlaza.
    por_sha = {}
    for p in todo:
        if p['car_la']:
            por_sha.setdefault(p['sha_la'], []).append(p)
    for ps in por_sha.values():
        if len(ps) < 2:
            continue
        ps.sort(key=lambda p: (-p['pagina'].count('/'), p['pagina']))
        for p in ps[1:]:
            p['duplicado_de'] = ps[0]['id']

    os.makedirs(TRABAJO, exist_ok=True)
    os.makedirs(DATOS, exist_ok=True)
    salida = os.path.join(TRABAJO, 'piezas.json')
    with open(salida, 'w', encoding='utf-8') as fh:
        json.dump({'fuente': 'fase 2 — piezas del Thesaurus Precum Latinarum',
                   'piezas': todo}, fh, ensure_ascii=False, indent=1)

    unicas = [p for p in todo if 'duplicado_de' not in p]
    con_la = [p for p in unicas if p['car_la']]
    qa = os.path.join(DATOS, 'piezas_qa.txt')
    with open(qa, 'w', encoding='utf-8') as fh:
        fh.write('páginas por clase\n')
        for k, v in cuenta.most_common():
            fh.write('  %5d  %s\n' % (v, k))
        fh.write('\npiezas:          %d\n' % len(todo))
        fh.write('duplicadas:      %d\n' % (len(todo) - len(unicas)))
        fh.write('únicas:          %d\n' % len(unicas))
        fh.write('  con latín:     %d\n' % len(con_la))
        fh.write('  sólo inglés:   %d\n'
                 % len([p for p in unicas if not p['car_la']]))
        fh.write('  sólo latín:    %d\n'
                 % len([p for p in unicas if not p['car_en']]))
        fh.write('\npiezas por categoría\n')
        for k, v in Counter(p['cat'] for p in unicas).most_common():
            fh.write('  %5d  %s\n' % (v, k))
        fh.write('\npáginas con más de una pieza\n')
        for k, v in sorted(Counter(p['pagina'] for p in unicas).items(),
                           key=lambda x: (-x[1], x[0])):
            if v > 1:
                fh.write('  %4d  %s\n' % (v, k))
        fh.write('\nversalitas de más de una palabra (%d)\n'
                 % len([x for x in VERSALITAS if x[0] == 'la']))
        for lado, crudo, puesto in VERSALITAS:
            if lado == 'la':
                fh.write('  %-34s %s\n' % (crudo, puesto))
        fh.write('\nsólo inglés (revisar)\n')
        for p in unicas:
            if not p['car_la']:
                fh.write('  %s  %s\n' % (p['pagina'], p['tla'] or p['ten']))
        fh.write('\nsin título (revisar)\n')
        for p in unicas:
            if not p['tla']:
                fh.write('  %s\n' % p['pagina'])
    print('%d piezas (%d únicas, %d con latín) -> %s'
          % (len(todo), len(unicas), len(con_la), salida))
    print('informe: ' + qa)


if __name__ == '__main__':
    main()
