# -*- coding: utf-8 -*-
"""El Oficio Parvo de la Santísima Virgen, del epub a la app.

El libro lo trajo el usuario el 2026-11-06 —«Oficio Parvo de la Santísima
Virgen María (1954) · Latín–Español»—: el latín de Divinum Officium
(«Divino Afflatu – 1954», licencia MIT) con una traducción castellana verso
a verso y las rúbricas para rezarlo a solas, entre dos y en comunidad.

**El libro ya viene compuesto.** Cada hora está escrita entera para cada
tiempo y cada manera de rezarla: 3 maneras × 5 tiempos × 10 horas (Maitines
va tres veces, una por nocturno) = 150 páginas. No se recompone nada: la
fuente manda, y la app sólo elige cuál de las 150 toca hoy (ver parvo.js).
Lo que sí hace esta fase es no repetir: el mismo salmo está en decenas de
páginas, así que cada verso se guarda una vez en una tabla y las páginas lo
citan por su número.

En el epub, todo es de cinco piezas, y así pasa a la app:

    <h2>Salmodia <span class='lt'>Psalmi</span></h2>    ["h", es, lt, caja]
    <h3>Psalmus 92 <span class='lt'>· Salmo 92</span>  ["t", es, lt]
    <p class='r'>De pie…</p>                            ["r", n]   rúbrica
    <p class='ref'>Cant 6, 8</p>                        ["c", cita]
    <div class='u'><p class='la'>…<p class='es'>…        ["u", n, papel, marcas]
    <p class='leg'>A dirige…</p>                        ["l", n]   leyenda
    <p>, <p class='idx'> (sólo en la guía)              ["p", n]   párrafo

`caja` dice que la sección va dentro de un recuadro (`div.box`), que en el
libro es lo que se dice sólo en un caso («Final — Si no siguen Laudes»).
`papel` es la etiqueta azul de quién lo dice (A, B, Ambos; H, C, I, II, L,
Todos), que en el libro va al principio del latín. Las marcas: `s` en
secreto, `e` estrofa de himno.

Dentro del texto, lo rojo va marcado con signos que el texto no usa —se
comprueba aquí que no los use—:

    {V.} {R.} {Ant.} {(inclinación)}   sigla o rúbrica de renglón
    *  †                               las pausas del verso
    +                                  la señal de la cruz
    [A]                                una etiqueta de papel dentro del texto
    \\n                                 el salto de renglón del himno
    ‹…›                                cursiva

    python Enchiridion/src/parvo.py [ruta del epub]
"""

import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, OrderedDict

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
EPUB = os.path.join(RAIZ, 'Enchiridion',
                    'Oficio_Parvo_BVM_1954_latin_espanol.epub')
SALIDA = os.path.join(RAIZ, 'app', 'datos', 'parvo.json')
QA = os.path.join(RAIZ, 'Enchiridion', 'datos', 'parvo_qa.txt')

NS = '{http://www.w3.org/1999/xhtml}'
MODOS = ['solo', 'dos', 'grupo']
TIEMPOS = ['ord', 'adv', 'nat', 'sept', 'pasc']
HORAS = ['mat1', 'mat2', 'mat3', 'laud', 'prima', 'tertia', 'sexta', 'nona',
         'vesp', 'compl']
RESERVADOS = '{}[]*†+‹›'


def clases(el):
    return (el.get('class') or '').split()


def limpio(t):
    return re.sub(r'\s+', ' ', t or '')


class Texto:
    """Pasa el contenido de un elemento a la marca de la app."""

    def __init__(self, qa):
        self.qa = qa

    def __call__(self, el, papel_fuera=False):
        """Devuelve (texto, papel). Con `papel_fuera`, la etiqueta azul con
        que empieza el texto sale aparte —es la del renglón— y las demás se
        quedan dentro."""
        partes = []
        papel = None

        def texto_llano(t):
            for c in RESERVADOS:
                if c in (t or ''):
                    self.qa['signo reservado en el texto: ' + c] += 1
            partes.append(limpio(t))

        def recorre(e, dentro=False):
            nonlocal papel
            if dentro:
                tag = e.tag.replace(NS, '')
                cl = clases(e)
                cuerpo = limpio(''.join(e.itertext()))
                if tag == 'br':
                    partes.append('\n')
                elif tag == 'span' and 'rl' in cl:
                    if papel_fuera and papel is None and not ''.join(partes).strip():
                        papel = cuerpo.strip()
                    else:
                        partes.append('[' + cuerpo.strip() + ']')
                elif tag == 'span' and ('vr' in cl or 'ri' in cl):
                    partes.append('{' + cuerpo.strip() + '}')
                elif tag == 'span' and 'ast' in cl:
                    partes.append(cuerpo.strip())
                    if cuerpo.strip() not in ('*', '†'):
                        self.qa['ast raro: ' + cuerpo] += 1
                elif tag == 'span' and 'cz' in cl:
                    partes.append('+')
                    if cuerpo.strip() != '+':
                        self.qa['cz raro: ' + cuerpo] += 1
                elif tag == 'i':
                    partes.append('‹' + cuerpo + '›')
                elif tag in ('b', 'a', 'span'):
                    if tag == 'span':
                        self.qa['span sin clase conocida: ' + ' '.join(cl)] += 1
                    texto_llano(cuerpo)
                else:
                    self.qa['etiqueta en línea: ' + tag] += 1
                    texto_llano(cuerpo)
                texto_llano(e.tail)
                return
            texto_llano(e.text)
            for h in e:
                recorre(h, True)

        recorre(el)
        t = ''.join(partes)
        t = re.sub(r'[ \t]*\n[ \t]*', '\n', t).strip()
        t = re.sub(r' {2,}', ' ', t)
        return t, papel


def cuerpo(raiz):
    return raiz.find(NS + 'body')


# El nombre corto de cada sección, por el título castellano del libro: es lo
# que la app mira para saber qué es cada cosa (el Te Deum que se quita, la
# antífona final que se elige) sin depender de la letra del título.
SECCIONES = [
    (r'^Comienzo', 'comienzo'), (r'^Invitatorio', 'invitatorio'),
    (r'^Himno', 'himno'), (r'^Salmodia', 'salmodia'),
    (r'^Lecci[óo]n I$', 'leccion1'), (r'^Lecci[óo]n II$', 'leccion2'),
    (r'^Lecci[óo]n III$', 'leccion3'), (r'^Te Deum', 'tedeum'),
    (r'^Cap[íi]tula', 'capitula'), (r'^Benedictus', 'cantico'),
    (r'^Magn[íi]ficat', 'cantico'), (r'^Nunc dim', 'cantico'),
    (r'^Oraci[óo]n', 'oracion'), (r'^Conmemoraci[óo]n', 'conm'),
    (r'^Conclusi[óo]n', 'conclusion'), (r'^Final', 'final'),
    (r'^Ant[íi]fona final', 'antifona'), (r'^Al terminar', 'terminar'),
]


def clave_seccion(es):
    for rx, k in SECCIONES:
        if re.search(rx, es):
            return k
    return ''


# Las cuatro antífonas finales de la Virgen, por su comienzo.
ANTIFONAS = [('Alma Redempt', 'alma'), ('Ave, Reg', 'ave'),
             ('Regína cæli', 'regina'), ('Salve, Reg', 'salve')]


def clave_antifona(es, qa):
    for ini, k in ANTIFONAS:
        if es.startswith(ini):
            return k
    qa['antífona final sin clave: ' + es] += 1
    return ''


def biblioteca_antifonas(horas, U):
    """Cada antífona final, por manera, tal como la trae el libro: del
    rótulo hasta antes de la siguiente, o del «Divínum auxílium» que cierra
    la sección. La app la saca de aquí cuando el tiempo del oficio y el de
    la antífona no coinciden —la Anunciación en Cuaresma reza el oficio de
    Adviento, que sólo trae «Alma Redemptóris»—."""
    lib = OrderedDict((m, OrderedDict()) for m in MODOS)
    for n, ps in horas.items():
        m = n.split('_')[0]
        dentro = False
        actual = None
        for p in ps:
            if p[0] == 'h':
                dentro = p[4] == 'antifona'
                actual = None
                continue
            if not dentro:
                continue
            if p[0] == 't':
                actual = p[3]
                if actual in lib[m]:
                    actual = None          # ya está: la primera manda
                else:
                    lib[m][actual] = [p]
                continue
            if p[0] == 'u' and U[p[1]][0].startswith('{V.} Divínum auxílium'):
                actual = None
                continue
            if actual:
                lib[m][actual].append(p)
    return lib


def piezas_de(body, tx, tabla_u, tabla_r, qa, nombre, con_h1=False):
    """Las piezas de una página, en orden. En las de la guía el título de
    la página es una sección más (`con_h1`): su entradilla va antes del
    primer apartado y, sin él, se quedaría sin rótulo."""
    out = []

    def u_de(div):
        la = es = None
        papel = None
        for p in div:
            c = clases(p)
            if 'la' in c:
                la, papel = tx(p, papel_fuera=True)
            elif 'es' in c:
                es, otro = tx(p, papel_fuera=True)
                if otro:
                    qa['papel en el castellano'] += 1
            else:
                qa['hijo raro de div.u: ' + ' '.join(c)] += 1
        if la is None or es is None:
            qa['div.u sin una de las dos lenguas'] += 1
            qa['  en ' + nombre] += 1
        clave = (la or '', es or '')
        if clave not in tabla_u:
            tabla_u[clave] = len(tabla_u)
        marcas = ''
        c = clases(div)
        if 'secreto' in c:
            marcas += 's'
        if 'st' in c:
            marcas += 'e'
        pieza = ['u', tabla_u[clave]]
        if papel or marcas:
            pieza.append(papel or '')
        if marcas:
            pieza.append(marcas)
        return pieza

    def r_de(t):
        if t not in tabla_r:
            tabla_r[t] = len(tabla_r)
        return tabla_r[t]

    def titulo(h):
        lt = h.find(NS + 'span')
        es = limpio(h.text).strip()
        lat = ''
        if lt is not None and 'lt' in clases(lt):
            lat = limpio(''.join(lt.itertext())).strip()
            lat = re.sub(r'^[·—–-]\s*', '', lat)
            if lt.tail and lt.tail.strip():
                qa['texto tras el latín del título'] += 1
        else:
            es = limpio(''.join(h.itertext())).strip()
        return es, lat

    seccion = [None]

    def recorre(cont, caja):
        for el in cont:
            tag = el.tag.replace(NS, '')
            c = clases(el)
            if tag == 'h1' and con_h1:
                seccion[0] = 'guia'
                out.append(['h', limpio(''.join(el.itertext())).strip(), '',
                            0, 'guia'])
                continue
            if tag == 'h1' or (tag == 'p' and ('sub' in c or 'nav' in c)):
                continue
            if tag == 'div' and 'box' in c:
                recorre(el, 1)
            elif tag == 'div' and 'u' in c:
                out.append(u_de(el))
            elif tag == 'h2':
                es, lat = titulo(el)
                k = clave_seccion(es)
                seccion[0] = k
                out.append(['h', es, lat, caja, k])
            elif tag == 'h3':
                es, lat = titulo(el)
                t = ['t', es, lat]
                if seccion[0] == 'antifona':
                    t.append(clave_antifona(es, qa))
                out.append(t)
            elif tag == 'p' and 'r' in c:
                out.append(['r', r_de(tx(el)[0])])
            elif tag == 'p' and 'ref' in c:
                out.append(['c', tx(el)[0]])
            elif tag == 'p' and 'leg' in c:
                out.append(['l', r_de(tx(el)[0])])
            elif tag == 'p' and ('idx' in c or 'small' in c or not c):
                # el párrafo de la guía, que explica y no manda: en tinta
                out.append(['p', r_de(tx(el)[0])])
            elif tag == 'table':
                # el cuadro de la guía: cada fila, su rótulo y lo que dice
                for tr in el:
                    celdas = [tx(td)[0] for td in tr
                              if td.tag.replace(NS, '') == 'td']
                    if len(celdas) == 2:
                        out.append(['t', celdas[0], ''])
                        out.append(['p', r_de(celdas[1])])
            else:
                qa['elemento raro: %s.%s' % (tag, '.'.join(c))] += 1

    recorre(body, 0)
    return out


def intro_de(body, tx, tabla_u, tabla_r, qa, nombre):
    """La explicación del principio de cada parte, hasta el primer tiempo:
    quién es quién y qué cambia al rezarlo así."""
    out = []
    for el in body:
        tag = el.tag.replace(NS, '')
        c = clases(el)
        if tag == 'h2':
            break
        if tag == 'h1':
            continue
        if tag == 'p':
            out.append(tx(el)[0])
    return out


def tiempos_de(body, tx):
    """Los cinco tiempos, con su nombre y su «desde… hasta», del índice."""
    out = OrderedDict()
    actual = None
    for el in body:
        tag = el.tag.replace(NS, '')
        if tag == 'h2' and el.get('id') in TIEMPOS:
            actual = el.get('id')
            out[actual] = [limpio(''.join(el.itertext())).strip(), '']
        elif actual and tag == 'p' and 'r' in clases(el) and not out[actual][1]:
            out[actual][1] = tx(el)[0]
    return out


def claves_de(U, R):
    """Los versos y las rúbricas que la app tiene que reconocer, por su
    índice: si el libro cambia y alguno ya no está, esto falla aquí y no en
    el teléfono."""
    def u_que(f):
        hay = [i for i, (la, es) in enumerate(U) if f(la)]
        assert len(hay) == 1, hay
        return hay[0]

    def r_que(ini, varias=False):
        hay = [i for i, t in enumerate(R) if t.startswith(ini)]
        assert hay if varias else len(hay) == 1, (ini, hay)
        return hay if varias else hay[0]

    return OrderedDict([
        ('alleluja', u_que(lambda la: la == 'Allelúja.')),
        ('laus', u_que(lambda la: la.startswith('Laus tibi, Dómine'))),
        # el versículo que cierra la sección de la antífona final, después
        # de la que se haya dicho: lo que va detrás no es de ninguna
        ('divinum', u_que(lambda la: la.startswith('{V.} Divínum auxílium'))),
        ('r_laus_anunciacion', r_que('El 25 de marzo, si cae en Cuaresma')),
        ('r_laus_septuagesima',
         r_que('Si ya ha comenzado la Septuagésima (puede')),
        ('r_tedeum_septuagesima',
         r_que('Si ya ha comenzado la Septuagésima, en lugar del Te Deum')),
        ('r_una_sola', r_que('Se dice una sola', True)),
    ])


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else EPUB
    qa = Counter()
    tx = Texto(qa)
    tabla_u = OrderedDict()
    tabla_r = OrderedDict()
    horas = OrderedDict()
    partes = OrderedDict()
    with zipfile.ZipFile(ruta) as z:
        def lee(n):
            return ET.fromstring(z.read('OEBPS/' + n))
        for m in MODOS:
            partes[m] = intro_de(cuerpo(lee(m + '_index.xhtml')), tx,
                                 tabla_u, tabla_r, qa, m)
            for t in TIEMPOS:
                for h in HORAS:
                    n = '%s_%s_%s' % (m, t, h)
                    horas[n] = piezas_de(cuerpo(lee(n + '.xhtml')), tx, tabla_u,
                                         tabla_r, qa, n)
        guia = OrderedDict()
        for n in ('calendario', 'posturas', 'oraciones'):
            guia[n] = piezas_de(cuerpo(lee(n + '.xhtml')), tx, tabla_u,
                                tabla_r, qa, n, con_h1=True)
        tiempos = tiempos_de(cuerpo(lee('solo_index.xhtml')), tx)
        opf = z.read('OEBPS/content.opf').decode('utf-8')
    derechos = re.search(r'<dc:rights>(.*?)</dc:rights>', opf)
    U = [list(k) for k in tabla_u]
    R = list(tabla_r)
    datos = OrderedDict([
        ('fuente', 'Oficio Parvo de la Santísima Virgen María (1954), '
                   'latín y español, con rúbricas para rezo solo, en pareja '
                   'y en comunidad'),
        ('derechos', derechos.group(1) if derechos else ''),
        ('tiempos', tiempos),
        ('claves', claves_de(U, R)),
        ('u', U),
        ('r', R),
        ('partes', partes),
        ('guia', guia),
        ('antifonas', biblioteca_antifonas(horas, U)),
        ('h', horas),
    ])
    with open(SALIDA, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(datos, fh, ensure_ascii=False, separators=(',', ':'))
    tam = os.path.getsize(SALIDA)
    # el informe: lo que se ha visto raro, y lo que hay
    lineas = ['# El Oficio Parvo — informe de la extracción', '',
              'epub: ' + os.path.basename(ruta),
              'páginas: %d' % len(horas),
              'versos distintos: %d' % len(tabla_u),
              'rúbricas distintas: %d' % len(tabla_r),
              'parvo.json: %d bytes' % tam, '']
    papeles = Counter()
    secciones = Counter()
    for n, ps in horas.items():
        for p in ps:
            if p[0] == 'u' and len(p) > 2 and p[2]:
                papeles[n.split('_')[0] + ' ' + p[2]] += 1
            if p[0] == 'h':
                secciones['%-12s %s%s' % (p[4] or '¿?', p[1],
                                          ' (recuadro)' if p[3] else '')] += 1
    lineas.append('## Lo raro (debe estar vacío salvo lo explicado)')
    for k, v in sorted(qa.items()):
        lineas.append('%6d  %s' % (v, k))
    lineas += ['', '## Etiquetas de papel por manera']
    for k, v in sorted(papeles.items()):
        lineas.append('%6d  %s' % (v, k))
    lineas += ['', '## Secciones']
    for k, v in secciones.most_common():
        lineas.append('%6d  %s' % (v, k))
    with open(QA, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lineas) + '\n')
    print('parvo.json: %d páginas, %d versos, %d rúbricas, %d bytes'
          % (len(horas), len(tabla_u), len(tabla_r), tam))
    if qa:
        print('raro:', dict(qa))


if __name__ == '__main__':
    main()
