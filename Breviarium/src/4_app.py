# -*- coding: utf-8 -*-
"""Fase 4 — el libro de horas, empaquetado para la app.

La app no vuelve a resolver nada: ésa es la regla del proyecto, y aquí se
respeta. Este módulo deja dos ficheros en `app/datos/`:

    horas.json        el libro entero, sin las variantes (que son el
                      aparato crítico y viven en Breviarium/datos/libro/)
    horas_dias.json   fecha civil -> coordenadas del oficio de ese día

El segundo es el que hace el trabajo. Para las fechas del volcado
(2019-2026) el tiempo y la semana salen de la propia fuente, exactos. Para
las demás —el calendario del leccionario llega a 2060— se derivan: el
tiempo y la semana, del calendario del proyecto; el día de la semana, de la
fecha; el salterio, de la semana.

Qué santo se celebra, y con qué grado, sale siempre del calendario del
proyecto, que ya resolvió la precedencia con la Tabla de los días
litúrgicos: así las horas dicen lo mismo que la misa. De la fuente sólo se
aprende dónde están los textos de cada celebración.

Los días señalados —el Triduo, la Navidad, la Epifanía— no se numeran por
semana, y la fuente y el leccionario les dan nombres distintos. La
correspondencia no se tabula a mano: se **aprende** de los años en que los
dos calendarios se solapan, que es para lo que la fase 3 dejó
`dias_fuente.json`.

    python Breviarium/src/4_app.py
"""

import datetime as dt
import difflib
import json
import os
import re
import sys
import zlib
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from breviario import clave

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIBRO = os.path.join(RAIZ, 'Breviarium', 'datos', 'libro')
APP = os.path.join(RAIZ, 'app', 'datos')
QA = os.path.join(RAIZ, 'Breviarium', 'datos', 'app_qa.txt')

# el tiempo litúrgico de cada sección del leccionario
TIEMPO_SECCION = {
    'TIEMPO DE ADVIENTO': 'Adviento',
    'TIEMPO DE NAVIDAD': 'Navidad',
    'TIEMPO DE CUARESMA': 'Cuaresma',
    'TRIDUO PASCUAL Y TIEMPO DE PASCUA': 'Pascua',
    'SOLEMNIDADES DEL SEÑOR EN EL TIEMPO ORDINARIO': 'Ordinario',
    'TIEMPO ORDINARIO': 'Ordinario',
}

ORDINALES = {
    'primera': 1, 'segunda': 2, 'tercera': 3, 'cuarta': 4, 'quinta': 5,
    'sexta': 6, 'séptima': 7, 'septima': 7, 'octava': 8,
}
ROMANOS = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
           'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13,
           'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19,
           'XX': 20, 'XXI': 21, 'XXII': 22, 'XXIII': 23, 'XXIV': 24,
           'XXV': 25, 'XXVI': 26, 'XXVII': 27, 'XXVIII': 28, 'XXIX': 29,
           'XXX': 30, 'XXXI': 31, 'XXXII': 32, 'XXXIII': 33, 'XXXIV': 34}


def semana_de(titulo_grupo):
    """El número de semana que declara el título de un grupo."""
    if not titulo_grupo:
        return None
    t = titulo_grupo.strip()
    m = re.search(r'\b(\d{1,2})[ªº]?\s+semana', t, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r'\bsemana\s+([IVX]+)\b', t, re.I)
    if m:
        return ROMANOS.get(m.group(1).upper())
    m = re.search(r'^([IVX]+)\s+semana', t, re.I)
    if m:
        return ROMANOS.get(m.group(1).upper())
    for pal, n in ORDINALES.items():
        if re.search(r'\b' + pal + r'\s+semana', t, re.I):
            return n
    return None


# Para comparar el nombre que da la fuente con el que da el calendario:
# «SAN JERÓNIMO, presbítero y doctor de la iglesia» y «San Jerónimo,
# presbítero y doctor de la Iglesia» son el mismo; «La Epifanía del Señor» y
# «El Bautismo del Señor» no, aunque compartan el Señor.
VACIAS = set('de del la las los el y en san santa santo santos santas '
             'senor domingo semana tiempo ordinario solemnidad'.split())


def fichas(t):
    return {w for w in clave(t).split() if w not in VACIAS and len(w) > 2}


def parecido(calendario, fuente):
    """De 0 a 1: cuánto del nombre más largo está en el otro."""
    # «En la Argentina: … En México: SAN FELIPE DE JESÚS»: el calendario del
    # proyecto es el latinoamericano, y la traducción, la de México
    if 'En México:' in fuente:
        fuente = fuente.split('En México:')[1]
    a, b = fichas(calendario), fichas(fuente)
    if not a or not b:
        return 0
    return len(a & b) / max(len(a), len(b))


# El rótulo corto de cada común, para el selector de la app: «Del día ·
# Doctores». Se nombra por el último que cita («pastores… y del común de
# doctores» trae los textos de doctores: lo dice la medida, no la teoría).
ROTULOS_COMUN = [
    ('doctores', 'Doctores'), ('pastores', 'Pastores'),
    ('apostoles', 'Apóstoles'), ('un martir', 'Un mártir'),
    ('varios martires', 'Mártires'), ('virgenes', 'Vírgenes'),
    ('santas mujeres', 'Santas mujeres'), ('santos varones', 'Santos varones'),
    ('santisima virgen maria', 'Santa María'), ('dedicacion', 'Dedicación'),
]


def rotulo_de_comun(nombre):
    ultimo = nombre.split(' y del comun de ')[-1]
    for prefijo, rotulo in ROTULOS_COMUN:
        if ultimo.startswith(prefijo):
            return rotulo
    return ultimo.capitalize()


def carga(nombre, base=LIBRO, opcional=False):
    ruta = os.path.join(base, nombre)
    if not os.path.exists(ruta):
        if opcional:
            return None
        sys.exit(f'falta {ruta}: ¿se corrió la fase anterior?')
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)


def comunes_del_pdf(texto, titulo, existentes):
    """«Del Común de un mártir o de pastores: para un presbítero» -> las
    claves de comunes.json que le corresponden, en el mismo orden.

    El libro sólo tiene los comunes que la fuente dejó medir (los que salen
    con dos santos distintos), así que se mapea a lo que hay y se calla lo
    que no: el «Común de santos varones» a secas no está, y prestarle el de
    los religiosos a un rey sería peor que dejar la feria, que las rúbricas
    también permiten."""
    if not texto:
        return []
    t = clave(texto)
    plural = re.search(r'\b(santos|martires|companeros|hermanos)\b',
                       clave(titulo)) or ' y san' in clave(titulo)
    claves = list(re.finditer(
        r'pastores|doctores|un martir|varios martires|martires|virgenes|'
        r'santas mujeres|santos varones|santa maria|santisima virgen|'
        r'apostoles', t))
    lista = []
    for n, m in enumerate(claves):
        tras = t[m.end():claves[n + 1].start() if n + 1 < len(claves)
                 else len(t)]
        w = m.group(0)
        if w == 'pastores':
            k = ('pastores para un santo obispo' if 'obispo' in tras
                 else 'pastores para un santo presbitero'
                 if 'presbitero' in tras else 'pastores')
        elif w == 'doctores':
            k = 'doctores de la iglesia'
        elif w == 'martires':
            k = 'varios martires' if plural else 'un martir'
        elif w == 'santos varones':
            k = ('santos varones para los santos religiosos'
                 if 'religios' in tras else
                 'santos varones para los santos educadores'
                 if 'educador' in tras else None)
        elif w in ('santa maria', 'santisima virgen'):
            k = 'santisima virgen maria'
        else:
            k = w
        if k and k in existentes and k not in lista:
            lista.append(k)
    return lista


FAMILIA = [('lectura_breve', 'breve'), ('responsorio_breve', 'responsorio'),
           ('lectura', 'lectura'), ('responsorio', 'responsorio'),
           ('oracion', 'oracion'), ('himno', 'himno'), ('preces', 'preces'),
           ('cantico_evangelico', 'antifona'), ('invitatorio', 'antifona')]


def familia(cl):
    return next((f for p, f in FAMILIA if cl.startswith(p)), None)


def palabras(lineas, rojo=False):
    return clave(' '.join(''.join(s for c, s in ln if rojo or not c)
                          for ln in lineas)).split()


def tripletas(ws):
    return {' '.join(ws[i:i + 3]) for i in range(len(ws) - 2)}


CONCLUSION = re.compile(r'\b(por nuestro senor jesucristo|por jesucristo nuestro '
                        r'senor|por cristo nuestro senor|el que vive y reina|'
                        r'que vive y reina|que vives y reinas|gloria al padre)\b')


def sin_conclusion(ws):
    """Las palabras de una oración sin su conclusión, que es la misma en
    todas y haría parecidas oraciones que no lo son."""
    m = CONCLUSION.search(' '.join(ws))
    return ' '.join(ws)[:m.start()].split() if m else ws


class Equivalencias:
    """Todo lo que ya tiene el libro de la fuente, para buscar en él un texto
    del PDF antes de usarlo.

    La traducción que manda es la de la fuente. Un texto que el PDF da para
    un santo que la fuente no publicó puede estar en la fuente en otro sitio:
    la misma lectura patrística en una feria, el mismo responsorio en un
    común, la misma antífona en otro santo. Si está, se usa el de la fuente,
    aunque difiera en alguna palabra (es lo que se espera de dos ediciones del
    mismo texto). Se compara por tripletas de palabras, que aguantan esas
    diferencias y no confunden un texto con otro."""

    def __init__(self, libros):
        self.piezas = []                         # (familia, rótulo, líneas, dónde)
        self.indice = defaultdict(lambda: defaultdict(set))
        self.antifonas = []                      # (clave, texto, dónde)
        for nombre, libro in libros:
            for k, v in libro.items():
                cl = k.rsplit('/', 1)[-1]
                fam = familia(cl)
                if not fam:
                    continue
                for nv, ls in enumerate([v['lineas']] + [
                        x['lineas'] for x in v.get('variantes', [])]):
                    if fam == 'antifona':
                        for ln in ls:
                            if es_antifona(ln) and len(ln) > 1:
                                t = ''.join(s for _, s in ln[1:]).strip()
                                if t:
                                    self.antifonas.append(
                                        (clave(t), t, f'{nombre}: {k}'))
                        continue
                    n = len(self.piezas)
                    # el rótulo (que en el responsorio lleva la cita) es el
                    # del texto canónico: una variante no lo tiene propio
                    self.piezas.append((fam, v['rotulo'] if nv == 0 else None,
                                        ls, f'{nombre}: {k}'
                                        + (f' (variante de otro año)' if nv
                                           else '')))
                    for tr in tripletas(sin_conclusion(palabras(ls))[:200]):
                        self.indice[fam][tr].add(n)

    def busca(self, cl, lineas):
        """La pieza de la fuente que es este mismo texto, o None."""
        fam = familia(cl)
        ws = sin_conclusion(palabras(lineas))[:200]
        trs = tripletas(ws)
        if not fam or len(trs) < 4:
            return None
        votos = Counter()
        for tr in trs:
            for n in self.indice[fam].get(tr, ()):
                votos[n] += 1
        if not votos:
            return None
        n, c = votos.most_common(1)[0]
        # proporción de las tripletas del PDF que están en la fuente: dos
        # ediciones del mismo texto pasan con holgura de la mitad; textos
        # distintos que comparten fórmulas («por nuestro Señor Jesucristo»)
        # se quedan muy por debajo
        if c / len(trs) >= self.UMBRAL.get(fam, 0.5):
            return self.piezas[n]
        return None

    # Una lectura larga que comparte la mitad de sus tripletas es la misma;
    # un responsorio, no: repite su respuesta y dos responsorios con la misma
    # respuesta y distinto versículo pasarían. A los cortos se les pide más.
    UMBRAL = {'lectura': 0.45, 'responsorio': 0.7, 'breve': 0.7,
              'oracion': 0.6, 'himno': 0.5, 'preces': 0.5}

    def antifona(self, texto):
        k = clave(texto)
        mejor = (0, None)
        pal = set(k.split())
        for ka, t, donde in self.antifonas:
            if abs(len(ka) - len(k)) > max(25, len(k) // 2):
                continue
            if len(pal & set(ka.split())) < max(3, len(pal) // 3):
                continue
            r = difflib.SequenceMatcher(None, k, ka).ratio()
            if r > mejor[0]:
                mejor = (r, (t, donde))
        return mejor[1] if mejor[0] >= 0.75 else None


def quita_aleluya(t):
    """«… sobre roca firme. Aleluya.» -> «… sobre roca firme.»"""
    s = re.sub(r'[\s,;]*\b[Aa]leluya\b[.,;!]*', '', t)
    if t.rstrip().endswith('.') and not s.rstrip().endswith(('.', '!', '?', '»')):
        s = s.rstrip() + '.'
    return s if s.strip() else t


def unifica_santos(santoral):
    """(mm-dd, nombre) -> nombre con el que se queda, para los nombres de un
    mismo día que sólo difieren en artículos y palabras vacías."""
    por_dia = defaultdict(Counter)
    for k in santoral:
        md, s = k.split('/', 2)[:2]
        por_dia[md][s] += 1
    alias = {}
    for md, nombres in por_dia.items():
        grupos = defaultdict(list)
        for s in nombres:
            grupos[frozenset(fichas(s))].append(s)
        for g in grupos.values():
            if len(g) > 1:
                queda = max(g, key=lambda s: (nombres[s], s))
                for s in g:
                    if s != queda:
                        alias[(md, s)] = queda
    return alias


def parecido_laxo(a, b):
    """Como `parecido`, pero una palabra casa con otra si una empieza o
    acaba con la otra: «Primeros mártires de la Iglesia de Roma» y «Santos
    protomártires de la santa Iglesia romana» son la misma celebración."""
    x, y = fichas(a), fichas(b)
    if not x or not y:
        return 0
    casan = sum(1 for w in x if any(
        w == v or (min(len(w), len(v)) >= 4
                   and (w.startswith(v) or v.startswith(w)
                        or w.endswith(v) or v.endswith(w))) for v in y))
    return casan / max(len(x), len(y))


def es_antifona(ln):
    return bool(ln) and ln[0][0] == 1 and ln[0][1].strip().startswith('Ant')


def incipit(lineas, n=6):
    """Las primeras palabras de un texto, para reconocer el mismo himno
    aunque un año traiga una errata en la tercera estrofa."""
    for ln in lineas:
        t = clave(''.join(s for c, s in ln if not c))
        if t:
            return ' '.join(t.split()[:n])
    return ''


def opciones_distintas(pares):
    """[(lineas, testigos)] -> [lineas], sin repetir himno y por orden de
    testigos."""
    mejor = {}
    for ls, n in pares:
        k = incipit(ls)
        if k and (k not in mejor or n > mejor[k][1]):
            mejor[k] = (ls, n)
    return [ls for ls, _ in sorted(mejor.values(), key=lambda x: -x[1])]


def poda(libro):
    """El libro sin el aparato crítico: sólo el texto que se reza."""
    return {k: {'r': v['rotulo'], 'l': v['lineas']} for k, v in libro.items()}


def refresca_version():
    """Vuelve a firmar `app/datos/`, con la fórmula de `15_app_data.py`."""
    ruta = os.path.join(APP, 'version.js')
    prefijo = 'clementina+nova'
    if os.path.exists(ruta):
        m = re.search(r'"(.+)-\d+"', open(ruta, encoding='utf-8').read())
        if m:
            prefijo = m.group(1)
    # los datos y el código de la app: un cambio en app.js también tiene que
    # llegar al teléfono
    raiz_app = os.path.dirname(APP)
    crc = zlib.crc32(b''.join(
        open(os.path.join(APP, f), 'rb').read()
        for f in sorted(os.listdir(APP)) if f != 'version.js') + b''.join(
        open(os.path.join(raiz_app, f), 'rb').read()
        for f in ('index.html', 'app.js', 'estilos.css', 'manifest.webmanifest')
        if os.path.exists(os.path.join(raiz_app, f)))) & 0xffffffff
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('// lo escribe src/15_app_data.py (y lo refresca\n'
                '// Breviarium/src/4_app.py); cambia con los datos, y al\n'
                '// cambiar obliga al service worker a rehacer su cache\n'
                f'self.VERSION_DATOS = "{prefijo}-{crc}";\n')
    return f'{prefijo}-{crc}'


def main():
    os.makedirs(APP, exist_ok=True)

    ordinario = carga('ordinario.json')
    salterio = carga('salterio.json')
    tiempo = carga('tiempo.json')
    santoral = carga('santoral.json')
    comunes = carga('comunes.json')
    fuente = carga('dias_fuente.json')
    resenas = carga('resenas.json', opcional=True) or {}
    pdf = carga('pdf_santoral.json', opcional=True) or []

    # Un mismo santo puede salir en la fuente con dos nombres que sólo
    # difieren en el artículo: «LA EXALTACIÓN DE LA SANTA CRUZ» unos años y
    # «EXALTACIÓN DE LA SANTA CRUZ» otros. Si no se juntan, cada nombre se
    # queda con la mitad de los textos. Se juntan bajo el que tiene más.
    alias = unifica_santos(santoral)
    nombre_unico = {s: c for (_, s), c in alias.items()}
    juntos = {}
    for k, v in santoral.items():                 # primero el nombre que queda
        md, s, resto = k.split('/', 2)
        if (md, s) not in alias:
            juntos[k] = v
    for k, v in santoral.items():                 # luego lo que aporta el otro
        md, s, resto = k.split('/', 2)
        if (md, s) in alias:
            juntos.setdefault(f'{md}/{alias[(md, s)]}/{resto}', v)
    santoral = juntos
    resenas = {f'{k.split("/", 1)[0]}/'
               f'{nombre_unico.get(k.split("/", 1)[1], k.split("/", 1)[1])}': v
               for k, v in resenas.items()}

    lecc = carga('calendario.json', os.path.join(RAIZ, 'data'))
    civil = carga('calendario_completo.json', os.path.join(RAIZ, 'data'))

    # --- slug del leccionario -> (tiempo, semana) -------------------------
    coord_slug = {}
    for sec in lecc['secciones']:
        ti = TIEMPO_SECCION.get(sec['titulo'])
        for g in sec['grupos']:
            sem = semana_de(g.get('titulo'))
            for d in g['dias']:
                coord_slug[d['slug']] = (ti, sem, d.get('titulo'))

    # --- se aprende qué día litúrgico es cada casilla del leccionario -----
    # Los títulos del leccionario y los de la fuente no coinciden —«17 de
    # diciembre» aquí, «SÁBADO DE LA SEMANA III» allá—, y traducirlos a mano
    # sería una tabla larga y frágil. No hace falta: en los años en que los
    # dos calendarios se solapan, la misma fecha lleva los dos nombres, y de
    # ahí sale la correspondencia sola.
    #
    # Se aprende de la casilla **del tiempo** de cada fecha, no de la que
    # gana: cuando gana un santo, su casilla es de fecha fija y no dice nada
    # del tiempo, mientras que la del tiempo sigue ahí debajo y es la que
    # vale para los demás años.
    aprendido = defaultdict(Counter)
    for fecha, cab in fuente.items():
        ent = civil['fechas'].get(fecha, {}).get('c')
        if not ent or not cab.get('tiempo'):
            continue
        # San Esteban, san Juan y los Santos Inocentes no tienen debajo
        # ninguna casilla del tiempo: dentro de la octava de Navidad, la
        # fiesta *es* el día. En ese caso se aprende de la suya.
        temporal = next((e for e in ent if (e[2] or {}).get('k') == 't'),
                        ent[0])
        if cab.get('semana') is not None:
            coord = (cab['tiempo'], cab['semana'], None)
        else:
            coord = (cab['tiempo'], None, clave(cab.get('titulo') or ''))
        aprendido[temporal[0]][coord] += 1
    aprendido = {s: c.most_common(1)[0][0] for s, c in aprendido.items()}

    # --- qué celebración del calendario es cada santo del libro -----------
    # Qué se celebra cada día, y con qué grado, no lo decide este módulo: lo
    # decide el calendario del proyecto, que ya resolvió la concurrencia con
    # la Tabla de los días litúrgicos (src/18_santoral.py) y es el mismo que
    # sigue la misa. Pegar el santo por fecha fija, como se hacía antes, lo
    # sacaba en domingo (san Francisco el 4 de octubre de 2026) y ponía las
    # fiestas móviles en la fecha en que cayeron el año del volcado.
    #
    # Lo que hace falta aquí es saber en qué casillas del santoral están los
    # textos de cada celebración del calendario. Tampoco eso se tabula a
    # mano: se aprende de las fechas en que la fuente y el calendario se
    # solapan, por el nombre.
    casillas = defaultdict(Counter)         # santo -> {mm-dd: nº de casillas}
    for k in santoral:
        md, santo = k.split('/', 2)[:2]
        casillas[santo][md] += 1

    votos = defaultdict(Counter)
    for fecha, cab in fuente.items():
        cel = cab.get('celebracion')
        ent = civil['fechas'].get(fecha, {}).get('c') or []
        nombre = nombre_unico.get(clave(cel or ''), clave(cel or ''))
        if not cel or nombre not in casillas or not ent:
            continue
        p, e = max(((parecido(e[2]['t'], cel), e) for e in ent),
                   key=lambda x: x[0])
        if p >= 0.5:
            votos[e[0]][nombre] += 1
    santo_de_slug = {slug: c.most_common(1)[0][0] for slug, c in votos.items()}
    n_aprendidos = len(santo_de_slug)

    # Lo que no coincidió nunca se busca por el nombre: los santos, entre
    # los de su misma fecha; las celebraciones del Señor, entre todas, porque
    # la fuente y el calendario pueden no ponerlas el mismo día (la
    # Epifanía, el 6 de enero allá y en domingo aquí).
    titulos = {}
    for ent in civil['fechas'].values():
        for slug, _, m in ent.get('c') or []:
            titulos.setdefault(slug, m)
    for slug, m in titulos.items():
        if slug in santo_de_slug:
            continue
        f = re.match(r'st_(\d\d)(\d\d)_', slug)
        if f:
            cands = [s for s, mds in casillas.items()
                     if f'{f[1]}-{f[2]}' in mds]
        elif m.get('k') == 't' and (m.get('r') or 99) <= 5:
            cands = list(casillas)
        else:
            continue
        if cands:
            p, s = max((parecido(m['t'].split(':')[-1], s), s) for s in cands)
            if p >= 0.5:
                santo_de_slug[slug] = s

    def md_de(santo, fecha):
        """En qué fecha del santoral buscar sus textos: la suya si la tiene;
        si no —las fiestas móviles—, la más completa."""
        mds = casillas[santo]
        return fecha[5:] if fecha[5:] in mds else mds.most_common(1)[0][0]

    def grado(m):
        if m.get('g'):
            return m['g'].upper()
        r = m.get('r') or 99                  # las del Señor, por su número
        return 'SOLEMNIDAD' if r <= 4 else 'FIESTA' if r <= 8 else 'MEMORIA'

    # --- de qué común toma su oficio cada santo ---------------------------
    # La app arma el día en cascada —lo del santo, si no lo de su común, si
    # no lo del tiempo— y para el segundo escalón necesita saber cuál es el
    # común de cada santo. Lo dice el propio volcado, en la línea que
    # encabeza el día («Del Común de pastores. Salterio III»).
    #
    # Pueden ser dos: «del común de pastores, o del común de doctores». En
    # las memorias las rúbricas dejan elegir, y la app ofrece los dos; por
    # eso se guarda una lista, con el que usó la fuente delante.
    comun_voto = defaultdict(Counter)
    for cab in fuente.values():
        cel, origen = cab.get('celebracion'), cab.get('origen') or ''
        m = re.search(r'com[uú]n\s+(?:de\s+)?(?:l[oa]s?\s+)?(.+)$', origen, re.I)
        if cel and m:
            comun_voto[nombre_unico.get(clave(cel), clave(cel))][
                clave(m.group(1))] += 1
    nombres_comunes = sorted({k.split('/', 1)[0] for k in comunes})

    def comunes_de(nombre):
        nombre = re.sub(r'\s+salterio\s+[ivx]+$', '', nombre)
        partes = [nombre] + nombre.split(' y del comun de ')
        lista = []
        for p in partes:
            k = p if p in nombres_comunes else next(iter(
                difflib.get_close_matches(p, nombres_comunes, 1, 0.9)), None)
            if k and k not in lista:
                lista.append(k)
        return lista
    comun_de_santo = {}
    for s, c in comun_voto.items():
        lista = comunes_de(c.most_common(1)[0][0])
        if lista:
            comun_de_santo[s] = lista
    rotulo_comun = {k: rotulo_de_comun(k) for k in nombres_comunes}

    # --- lo que la fuente no trae: el Propio de los santos de los PDF -----
    # La fuente reza la feria en las memorias libres, así que de san Bruno,
    # santa Eduviges y otros sesenta no publicó nunca nada. Los cuatro tomos
    # en PDF sí los traen (fase 3b). Se usan sólo para lo que falta, y todo
    # lo que se toma de ahí lleva la marca `f: 'pdf'` y queda en el informe:
    # es la traducción de la Conferencia Episcopal Española, no la de México.
    extra = {}                                  # piezas nuevas del santoral
    desde_pdf, rellenos, resenas_pdf = [], [], []
    pdf_por_md = defaultdict(list)
    for e in pdf:
        if e.get('titulo'):
            pdf_por_md[e['md']].append(e)

    def entrada_pdf(md, titulo):
        cands = [(parecido_laxo(titulo, e['titulo']), e)
                 for e in pdf_por_md.get(md, [])]
        if not cands:
            return None
        p, e = max(cands, key=lambda x: x[0])
        return e if p >= 0.5 else None

    # El PDF da del cántico evangélico sólo la antífona («Ant. … Benedictus»):
    # el cántico entero se arma con el de cualquier feria, cambiando la
    # antífona del principio y la del final.
    plantillas = {}

    def cantico_con(hora, ant):
        if hora not in plantillas:
            plantillas[hora] = None
            for k in sorted(tiempo):
                if k.startswith('Ordinario/') and \
                        k.endswith(f'/{hora}/cantico_evangelico'):
                    ls = tiempo[k]['lineas']
                    ants = [ln for ln in ls if es_antifona(ln)]
                    if len(ants) >= 2 and all(len(ln) >= 2 for ln in ants):
                        plantillas[hora] = (tiempo[k]['rotulo'], ls)
                        break
        if not plantillas[hora]:
            return None
        rot, ls = plantillas[hora]
        return {'r': rot, 'l': [[[1, 'Ant. '], [0, ant]] if es_antifona(ln)
                                else ln for ln in ls], 'f': 'pdf'}

    # La traducción que manda es la de la fuente: antes de usar un texto del
    # PDF se busca en todo el libro, con sus variantes, y si está se usa el
    # de la fuente aunque difiera en alguna palabra.
    equiv = Equivalencias([('santoral', santoral), ('comunes', comunes),
                           ('tiempo', tiempo), ('salterio', salterio),
                           ('ordinario', ordinario)])
    hallados = []                     # (celebración, sección, dónde estaba)

    def pieza_del_pdf(md, santo, k, p, titulo):
        hora, cl = k.split('/')
        # Lo hallado puede ser la forma pascual del mismo texto («… roca
        # firme. Aleluya.»): si el PDF no lo trae, el santo cae fuera de
        # Pascua y el aleluya sobra.
        sin_aleluya = 'aleluya' not in clave(json.dumps(p, ensure_ascii=False))
        if cl == 'cantico_evangelico':
            h = equiv.antifona(p['ant'][0])
            ant = h[0] if h else p['ant'][0]
            if h and sin_aleluya:
                ant = quita_aleluya(ant)
            c = cantico_con(hora, ant)
            if c and h:
                del c['f']
                hallados.append((titulo, k, h[1]))
        else:
            h = equiv.busca(cl, p['l'])
            if h:
                ls = h[2]
                if sin_aleluya:
                    ls = [[[r, quita_aleluya(t) if not r else t]
                           for r, t in ln] for ln in ls]
                c = {'r': h[1] or p['r'], 'l': ls}
                hallados.append((titulo, k, h[3]))
            else:
                c = {'r': p['r'], 'l': p['l'], 'f': 'pdf'}
        if c:
            extra[f'{md}/{santo}/{k}'] = c

    def resena_pieza(texto, de_pdf=False):
        c = {'r': None, 'l': [[], [[0, texto]]]}
        if de_pdf:
            c['f'] = 'pdf'
        return c

    HORAS_PDF = ('oficio', 'laudes', 'visperas')
    for slug, m in sorted(titulos.items(), key=lambda x: x[0]):
        fm = re.match(r'st_(\d\d)(\d\d)_', slug)
        if not fm or m.get('k') != 's':
            continue
        md = f'{fm[1]}-{fm[2]}'
        e = entrada_pdf(md, m['t'])
        if slug not in santo_de_slug:
            # la celebración entera, del PDF
            if not e or 'oficio/lectura2' not in e['piezas']:
                continue
            santo = clave(e['titulo'])
            for k, p in e['piezas'].items():
                if k.split('/')[0] in HORAS_PDF:
                    pieza_del_pdf(md, santo, k, p, m["t"])
            # la reseña, también primero la de la fuente si la dio en otra
            # fecha (santo Toribio: el 27 de abril, que es su día en Perú)
            r = next((v for k, v in resenas.items()
                      if k.endswith('/' + santo)), None)
            if r:
                extra[f'{md}/{santo}/oficio/resena'] = resena_pieza(r)
            elif e.get('resena'):
                extra[f'{md}/{santo}/oficio/resena'] = resena_pieza(
                    e['resena'], True)
            lista = comunes_del_pdf(e.get('comun'), e['titulo'],
                                    nombres_comunes)
            if lista:
                comun_de_santo[santo] = lista
            santo_de_slug[slug] = santo
            casillas[santo][md] += 1
            desde_pdf.append((m['t'], grado(m), e, lista))
            continue
        santo = santo_de_slug[slug]
        md_s = md if md in casillas[santo] else \
            casillas[santo].most_common(1)[0][0]
        # la reseña: la de la fuente, y si no la dio, la del PDF
        r = resenas.get(f'{md_s}/{santo}') or next(
            (v for k, v in resenas.items() if k.endswith('/' + santo)), None)
        if r:
            extra[f'{md_s}/{santo}/oficio/resena'] = resena_pieza(r)
        elif e and e.get('resena'):
            extra[f'{md_s}/{santo}/oficio/resena'] = resena_pieza(
                e['resena'], True)
            resenas_pdf.append(m['t'])
        # la lectura hagiográfica, su responsorio y la oración: si ni el
        # santo ni su común las tienen
        if not e:
            continue
        for k in ('oficio/lectura2', 'oficio/responsorio2', 'oficio/oracion',
                  'laudes/oracion', 'visperas/oracion'):
            if k not in e['piezas']:
                continue
            tiene = f'{md_s}/{santo}/{k}' in santoral or any(
                f'{c}/{k}' in comunes for c in comun_de_santo.get(santo, []))
            if tiene:
                continue
            # la oración del santo es la misma en todas las horas: si la
            # fuente la da en alguna, ésa
            otra = next((santoral[f'{md_s}/{santo}/{h}/oracion']
                         for h in ('laudes', 'oficio', 'visperas')
                         if k.endswith('oracion')
                         and f'{md_s}/{santo}/{h}/oracion' in santoral), None)
            if otra:
                extra[f'{md_s}/{santo}/{k}'] = {'r': otra['rotulo'],
                                                'l': otra['lineas']}
                hallados.append((m['t'], k, 'la misma oración, en otra hora'))
            else:
                pieza_del_pdf(md_s, santo, k, e["piezas"][k], m["t"])
            rellenos.append((m['t'], k))

    # --- los himnos que se pueden escoger ----------------------------------
    # «En el Oficio dominical y ferial, se dice el himno que se indica en el
    # Salterio […]. Pueden usarse también otros cantos oportunos» (Ordinario).
    # De cada himno se guardan los otros que la fuente dio en ese mismo día en
    # otros años; de Completas, todos los del tiempo, que son pocos y se
    # turnan; y de la antífona final de la Virgen, las cuatro del Ordinario
    # —en Pascua, sólo «Reina del cielo»—.
    otros_himnos = {}
    for k, v in tiempo.items():
        if k.endswith('/himno') and v.get('variantes'):
            otros = [ls for ls in opciones_distintas(
                [(x['lineas'], x['testigos']) for x in v['variantes']])
                if incipit(ls) != incipit(v['lineas'])]
            if otros:
                otros_himnos[k] = [{'r': v['rotulo'], 'l': ls} for ls in otros]
    pool = defaultdict(list)
    for k, v in tiempo.items():
        p = k.split('/')
        if p[-2:] == ['completas', 'himno']:
            pool[p[0]] += [(v['lineas'], v['testigos'])] + [
                (x['lineas'], x['testigos']) for x in v.get('variantes', [])]
    himnos_completas = {t: [{'r': 'HIMNO', 'l': ls}
                            for ls in opciones_distintas(pares)]
                        for t, pares in pool.items()}
    pool = defaultdict(list)
    for k, v in ordinario.items():
        if k.endswith('/completas/antifona_final'):
            pool[k.split('/')[0]] += [(v['lineas'], v['testigos'])] + [
                (x['lineas'], x['testigos']) for x in v.get('variantes', [])]
    ORDEN_ANT = ['dios te salve reina', 'madre del redentor',
                 'salve reina de los cielos', 'bajo tu amparo',
                 'reina del cielo alegrate']

    def puesto(ls):
        i = incipit(ls)
        return next((n for n, o in enumerate(ORDEN_ANT) if i.startswith(o)),
                    99)
    todas = opciones_distintas([x for pares in pool.values() for x in pares])
    antifonas_finales = {}
    for t in pool:
        if t == 'Pascua':
            lista = [ls for ls in todas if puesto(ls) == 4]
        else:
            lista = [ls for ls in todas if puesto(ls) < 4]
        antifonas_finales[t] = [{'r': 'ANTIFONA FINAL DE LA SANTISIMA VIRGEN',
                                 'l': ls} for ls in sorted(lista, key=puesto)]

    # --- fecha -> coordenadas ---------------------------------------------
    dias, cuentas, avisos, sin_textos = {}, Counter(), [], Counter()
    huecos_tiempo = {k.rsplit('/', 2)[0] for k in tiempo}

    for fecha, ent in sorted(civil['fechas'].items()):
        if not ent.get('c'):
            continue
        d = dt.date.fromisoformat(fecha)
        ds = (d.weekday() + 1) % 7                     # 0 = domingo
        meta = ent['c'][0][2] or {}
        temporal = next((e for e in ent['c'] if (e[2] or {}).get('k') == 't'),
                        ent['c'][0])
        slug = temporal[0]

        cab = fuente.get(fecha)
        if cab and cab.get('tiempo'):
            # el volcado lo dice él mismo, y no hay fuente mejor
            ti, sem = cab['tiempo'], cab.get('semana')
            if cab.get('dia_semana') is not None:
                ds = cab['dia_semana']
            salt = cab.get('salterio')
            titulo_clave = clave(cab.get('titulo') or '')
            cuentas['del volcado'] += 1
        elif slug in aprendido:
            ti, sem, titulo_clave = aprendido[slug]
            salt = ((sem - 1) % 4) + 1 if sem else None
            cuentas['aprendido del volcado'] += 1
        else:
            ti, sem, _ = coord_slug.get(slug, (None, None, None))
            if not ti:
                avisos.append(f'{fecha}: sin tiempo ({slug} '
                              f'«{meta.get("t")}»)')
                cuentas['sin tiempo'] += 1
                continue
            salt = ((sem - 1) % 4) + 1 if sem else None
            titulo_clave = clave((coord_slug.get(slug) or (None, None, ''))[2]
                                 or '')
            cuentas['del calendario del leccionario'] += 1

        clave_dia = (f'{ti}/{sem}/{ds}' if sem is not None
                     else f'{ti}/@/{titulo_clave}')

        if clave_dia not in huecos_tiempo:
            cuentas['sin textos del tiempo'] += 1

        # el título es el del día del tiempo; el del santo, si se celebra,
        # lo pone la app, que es la que sabe si quien reza lo ha elegido
        reg = {'t': ti, 'k': clave_dia, 'd': ds, 'tt': temporal[2]['t']}
        if salt:
            reg['p'] = salt

        # Las celebraciones con textos, en el orden de precedencia del
        # calendario y sin las impedidas: [santo, mm-dd, título, grado,
        # número en la Tabla]. `w` dice si la primera es la que gana el día.
        # `cm`, que gana una feria privilegiada (la Cuaresma, del 17 al 24
        # de diciembre, la octava de Navidad: el n. 9 de la Tabla), y
        # entonces las memorias que vienen detrás sólo pueden hacerse como
        # conmemoración (Principios y normas generales, nn. 238-239).
        cels = []
        for i, (sl, _, m) in enumerate(ent['c']):
            if m.get('z'):
                continue
            s = santo_de_slug.get(sl)
            if s:
                cels.append([s, md_de(s, fecha), m['t'], grado(m),
                             m.get('r')])
                if i == 0:
                    reg['w'] = 1
            elif i == 0 and m.get('k') == 's':
                # se celebra algo de lo que la fuente no dio nunca textos:
                # la app lo dice en vez de callárselo
                reg['x'] = [m['t'], grado(m)]
                cuentas['celebración sin textos'] += 1
                sin_textos[f'{m["t"]} ({grado(m).lower()})'] += 1
        primera = ent['c'][0][2]
        if cels:
            reg['c'] = cels
            if (not reg.get('w') and primera.get('k') == 't'
                    and (primera.get('r') or 99) <= 9):
                reg['cm'] = 1
                cuentas['con conmemoración posible'] += 1
            else:
                cuentas['con santo'] += 1

        # Las vísperas del sábado son las primeras del domingo, que en la
        # Tabla está por encima de cualquier memoria y de las fiestas de los
        # santos: esas no tienen vísperas ese día («si coinciden, prevalecen
        # las de la celebración de mayor grado», PNLH 61). Y la fuente guarda
        # las primeras vísperas del domingo en el sábado, así que la app sólo
        # tiene que saber que ese día las vísperas son «del día». Sólo en las
        # semanas numeradas: en Navidad el sábado no tiene casilla propia.
        manana = civil['fechas'].get(str(d + dt.timedelta(days=1)), {})
        if cels and ds == 6 and sem is not None and manana.get('c'):
            r_dom = manana['c'][0][2].get('r') or 99
            if r_dom < (cels[0][4] or 99):
                reg['v'] = 1

        dias[fecha] = reg

    # --- se escribe --------------------------------------------------------
    libro = {
        'orden': carga('orden.json'),
        'comun_de': comun_de_santo,
        'rotulo_comun': rotulo_comun,
        'ordinario': poda(ordinario),
        'salterio': poda(salterio),
        'tiempo': poda(tiempo),
        'santoral': dict(poda(santoral), **extra),
        'comunes': poda(comunes),
        'otros_himnos': otros_himnos,
        'himnos_completas': himnos_completas,
        'antifonas_finales': antifonas_finales,
    }
    ruta_libro = os.path.join(APP, 'horas.json')
    with open(ruta_libro, 'w', encoding='utf-8') as f:
        json.dump(libro, f, ensure_ascii=False, separators=(',', ':'))

    ruta_dias = os.path.join(APP, 'horas_dias.json')
    with open(ruta_dias, 'w', encoding='utf-8') as f:
        json.dump({'rango': civil['rango'], 'dias': dias}, f,
                  ensure_ascii=False, separators=(',', ':'))

    # El teléfono no se entera de que los textos han cambiado por arte de
    # magia: su service worker guarda la app entera en caché, y lo que le
    # obliga a tirarla es la firma de `datos/version.js`, que la escribe
    # `src/15_app_data.py` sobre todo lo que hay en `app/datos/`. Si las
    # horas se rehacen después de aquélla, la firma se queda vieja y el
    # teléfono sigue rezando con los textos de antes. Así que se refresca
    # con la misma fórmula, y da igual cuál de las dos corra última.
    refresca_version()

    mb1 = os.path.getsize(ruta_libro) / 1e6
    mb2 = os.path.getsize(ruta_dias) / 1e6
    casillas = sum(len(libro[k]) for k in
                   ('ordinario', 'salterio', 'tiempo', 'santoral', 'comunes'))
    print(f'horas.json       {mb1:6.1f} MB  ({casillas} casillas)')
    print(f'horas_dias.json  {mb2:6.1f} MB  ({len(dias)} fechas)')

    with open(QA, 'w', encoding='utf-8') as f:
        f.write('Fase 4 — el libro de horas empaquetado para la app\n')
        f.write('=' * 58 + '\n\n')
        f.write(f'horas.json       {mb1:6.1f} MB\n')
        f.write(f'horas_dias.json  {mb2:6.1f} MB  {len(dias)} fechas\n\n')
        for k in ('ordinario', 'salterio', 'tiempo', 'santoral', 'comunes'):
            f.write(f'{len(libro[k]):8d}  casillas en {k}\n')
        f.write(f'{len(comun_de_santo):8d}  santos con común conocido\n')
        f.write(f'{len(santo_de_slug):8d}  celebraciones del calendario con '
                f'textos ({n_aprendidos} aprendidas del volcado, '
                f'{len(santo_de_slug) - n_aprendidos} por el nombre)\n')
        f.write('\nCómo se resolvió cada fecha\n' + '-' * 44 + '\n')
        for k, v in sorted(cuentas.items()):
            f.write(f'{v:8d}  {k}\n')
        f.write('\nDías del leccionario cuyas coordenadas se aprendieron '
                f'del volcado: {len(aprendido)}\n')
        f.write('\nCelebraciones del calendario -> casillas del santoral\n'
                + '-' * 44 + '\n')
        for sl, santo in sorted(santo_de_slug.items(),
                                key=lambda x: titulos[x[0]]['t']):
            f.write(f'  {titulos[sl]["t"]}  ->  {santo}\n')
        if sin_textos:
            f.write('\nSe celebran, pero la fuente no dio nunca sus textos '
                    '(el oficio sale de la feria)\n' + '-' * 44 + '\n')
            for t, n in sin_textos.most_common():
                f.write(f'{n:8d}  {t}\n')
        if avisos:
            f.write(f'\nAvisos: {len(avisos)}\n' + '-' * 44 + '\n')
            for a in avisos[:200]:
                f.write(a + '\n')
    print(f'\nQA en {QA}')

    escribe_informe_pdf(desde_pdf, rellenos, resenas_pdf, sin_textos,
                        santo_de_slug, titulos, santoral, comunes,
                        comun_de_santo, casillas_de(santoral), entrada_pdf,
                        hallados, extra)


def casillas_de(santoral):
    c = defaultdict(Counter)
    for k in santoral:
        md, santo = k.split('/', 2)[:2]
        c[santo][md] += 1
    return c


INFORME = os.path.join(RAIZ, 'Breviarium', 'datos', 'pdf_usado.txt')
NOMBRE_SECCION = {
    'oficio/lectura2': 'segunda lectura', 'oficio/responsorio2': 'responsorio',
    'oficio/oracion': 'oración', 'laudes/oracion': 'oración de Laudes',
    'visperas/oracion': 'oración de Vísperas',
    'laudes/cantico_evangelico': 'antífona del Benedictus',
    'visperas/cantico_evangelico': 'antífona del Magníficat',
    'laudes/himno': 'himno de Laudes', 'visperas/himno': 'himno de Vísperas',
    'oficio/himno': 'himno del Oficio', 'laudes/lectura_breve':
    'lectura breve de Laudes', 'visperas/lectura_breve':
    'lectura breve de Vísperas', 'laudes/preces': 'preces de Laudes',
    'visperas/preces': 'preces de Vísperas', 'oficio/lectura1':
    'primera lectura', 'laudes/responsorio_breve': 'responsorio breve de '
    'Laudes', 'visperas/responsorio_breve': 'responsorio breve de Vísperas',
}


CITA = re.compile(r'(?:Cf\.\s*)?(?:[1-3]\s?)?[A-ZÁÉÍÓÚ][a-záéíóúñ]{0,6}\.?\s*'
                  r'\d+\s*,\s*\d+[a-z]?(?:[\s\d,.;:–\-a-zA-Záéíóú]*\d[a-z]?)?')


def cita_de(rotulo, lineas):
    """La cita bíblica de una pieza: en el rótulo («RESPONSORIO Mt 5, 3-4»),
    o en sus primeras líneas («De la carta a los Romanos 8, 28-30»)."""
    for t in [rotulo or ''] + [''.join(s for _, s in ln) for ln in lineas[:4]]:
        m = re.search(r'(?:[1-3]\s?)?[A-Za-zÁÉÍÓÚáéíóúñ]+\.?\s*\d+\s*,\s*\d+'
                      r'[\d\s,.;:abc\-–]*(?:\s?[1-3]?\s?[A-Z][a-z]{0,3}\s?\d+\s*,'
                      r'[\d\s,.;:abc\-–]*)*', t)
        if m:
            return m.group(0).strip(' .;,')[:60]
    return None


def numeros(cita):
    """Los números de una cita sin el del libro («1 Co 15, 9» -> 15, 9):
    así «1Co», «1 Co» y «Co» no cuentan como citas distintas."""
    trozos = re.split(r';', cita or '')
    out = []
    for t in trozos:
        m = re.search(r'\d+\s*,\s*\d+.*$', t)
        if m:
            out += re.findall(r'\d+', m.group(0))
    return tuple(out)


def autor_de(lineas):
    """La primera línea de una lectura no bíblica: «De una carta de san
    Bruno, presbítero, a sus hijos cartujos»."""
    for ln in lineas[:4]:
        t = ''.join(s for c, s in ln if not c).strip()
        if t:
            return t[:90]
    return None


def escribe_informe_pdf(desde_pdf, rellenos, resenas_pdf, sin_textos,
                        santo_de_slug, titulos, santoral, comunes,
                        comun_de_santo, casillas, entrada_pdf, hallados,
                        extra):
    """El informe para quien reza: qué se tomó de los PDF (la traducción
    española), qué sigue sin textos en ninguna parte, y en qué difieren los
    PDF de la fuente en los santos que tienen los dos."""
    def plano(lineas):
        return clave(' '.join(''.join(s for _, s in ln) for ln in lineas))

    cotejo = []
    for slug, santo in sorted(santo_de_slug.items(),
                              key=lambda x: (x[0][3:7], x[0])):
        fm = re.match(r'st_(\d\d)(\d\d)_', slug)
        if not fm:
            continue
        md = f'{fm[1]}-{fm[2]}'
        e = entrada_pdf(md, titulos[slug]['t'])
        if not e or any(d[2] is e for d in desde_pdf):
            continue
        mds = casillas.get(santo) or {}
        md_s = md if md in mds else (max(mds, key=mds.get) if mds else md)
        notas = []
        for k, p in sorted(e['piezas'].items()):
            if k.split('/')[0] not in ('oficio', 'laudes', 'visperas') \
                    or k not in NOMBRE_SECCION:
                continue
            propio = santoral.get(f'{md_s}/{santo}/{k}')
            del_comun = any(f'{c}/{k}' in comunes
                            for c in comun_de_santo.get(santo, []))
            nombre = NOMBRE_SECCION[k]
            cl = k.split('/')[1]
            if not propio:
                notas.append(f'{nombre}: el PDF la trae propia; la fuente la '
                             + ('toma del común' if del_comun
                                else 'toma de la feria'))
                continue
            # La oración y las preces son el mismo texto en dos traducciones
            # (la española y la mexicana del Misal): no se cotejan, porque
            # saldrían todas «distintas» sin serlo. Se coteja lo que se puede
            # comparar sin traducción de por medio: las citas, el autor de la
            # lectura, y el comienzo de antífonas e himnos.
            if cl in ('oracion', 'preces'):
                continue
            if cl in ('lectura1', 'lectura_breve', 'responsorio',
                      'responsorio2', 'responsorio_breve'):
                a = cita_de(p.get('r'), p.get('l') or [])
                b = cita_de(propio.get('rotulo'), propio['lineas'])
                if a and b and numeros(a) != numeros(b):
                    notas.append(f'{nombre}: cita distinta — PDF «{a}», '
                                 f'fuente «{b}»')
            elif cl == 'lectura2':
                a, b = autor_de(p['l']), autor_de(propio['lineas'])
                if a and b and difflib.SequenceMatcher(
                        None, clave(a)[:60], clave(b)[:60]).ratio() < 0.6:
                    notas.append(f'{nombre}: otra lectura — PDF «{a}», '
                                 f'fuente «{b}»')
            elif cl == 'cantico_evangelico':
                a = p['ant'][0]
                b = next((''.join(s for _, s in ln[1:])
                          for ln in propio['lineas'] if es_antifona(ln)), '')
                if a and b and difflib.SequenceMatcher(
                        None, clave(a), clave(b)).ratio() < 0.5:
                    notas.append(f'{nombre}: otra antífona — PDF «{a}», '
                                 f'fuente «{b.strip()}»')
            elif cl == 'himno':
                a, b = incipit(p['l'], 5), incipit(propio['lineas'], 5)
                if a and b and a != b:
                    notas.append(f'{nombre}: otro himno — PDF «{a}…», '
                                 f'fuente «{b}…»')
        if notas:
            cotejo.append((titulos[slug]['t'], md, notas))

    with open(INFORME, 'w', encoding='utf-8') as f:
        f.write('Lo que se tomó de los PDF del Breviarium\n')
        f.write('=' * 60 + '\n\n')
        f.write('La fuente de los textos es liturgiadelashoras.github.io, en la\n'
                'traducción de México. Lo que sigue no estaba en ninguno de sus\n'
                'años y se tomó de los cuatro tomos en PDF, que traen la\n'
                'traducción de la Conferencia Episcopal Española. En la app esos\n'
                'textos llevan la marca «f: pdf».\n\n')
        en_fuente = defaultdict(dict)
        for t, k, donde in hallados:
            en_fuente[t][k] = donde
        f.write(f'1. Celebraciones que la fuente no publicó nunca: '
                f'{len(desde_pdf)}\n' + '-' * 60 + '\n'
                'De cada texto del PDF se buscó primero si estaba en la fuente\n'
                '(en otro día, en un común, en otro año): lo que se halló va\n'
                'con la traducción de la fuente; lo demás, con la del PDF.\n\n')
        for t, g, e, lista in sorted(desde_pdf, key=lambda x: x[2]['md']):
            ks = [k for k in sorted(e['piezas'])
                  if k.split('/')[0] in ('oficio', 'laudes', 'visperas')
                  and k in NOMBRE_SECCION]
            # la oración es una sola: se nombra una vez
            if 'oficio/oracion' in ks:
                ks = [k for k in ks if k not in ('laudes/oracion',
                                                 'visperas/oracion')]
            de_pdf = [NOMBRE_SECCION[k] for k in ks if k not in en_fuente[t]]
            de_fte = [NOMBRE_SECCION[k] for k in ks if k in en_fuente[t]]
            d, m = e['md'][3:], e['md'][:2]
            f.write(f'{d}/{m}  {t} ({g.lower()})\n')
            if de_pdf:
                f.write(f'        del PDF: {", ".join(de_pdf)}'
                        f'{", reseña" if e.get("resena") else ""}\n')
            if de_fte:
                f.write(f'        hallado en la fuente: {", ".join(de_fte)}\n')
            f.write(f'        común: {e.get("comun") or "—"}'
                    f'{"  →  " + ", ".join(lista) if lista else "  →  (ninguno de los que hay: lo demás, de la feria)"}\n')
        f.write(f'\n2. Santos con textos de la fuente a los que les faltaba '
                f'algo: {len(rellenos)}\n' + '-' * 60 + '\n')
        for t, k in rellenos:
            f.write(f'  {t}: {NOMBRE_SECCION.get(k, k)}'
                    f'{" (hallado en la fuente: " + en_fuente[t][k] + ")" if k in en_fuente[t] else " (del PDF)"}\n')
        f.write(f'\n   Textos del PDF que ya estaban en la fuente y se usan '
                f'con su traducción: {len(hallados)}\n')
        for t, k, donde in hallados:
            f.write(f'     {t} — {NOMBRE_SECCION.get(k, k)}  ←  {donde}\n')
        f.write(f'\n3. Reseñas biográficas tomadas del PDF: {len(resenas_pdf)}\n'
                + '-' * 60 + '\n')
        for t in resenas_pdf:
            f.write(f'  {t}\n')
        f.write('\n4. Se celebran, y no hay textos ni en la fuente ni en los '
                'PDF\n' + '-' * 60 + '\n')
        for t, n in sin_textos.most_common():
            f.write(f'  {t}\n')
        f.write('\n5. Cotejo PDF / fuente en los santos que tienen los dos\n'
                + '-' * 60 + '\n'
                'Aquí no se cambió nada: manda la fuente. Sólo se apunta.\n\n')
        for t, md, notas in cotejo:
            f.write(f'{md[3:]}/{md[:2]}  {t}\n')
            for n in notas:
                f.write(f'        · {n}\n')
    print(f'Informe de lo tomado del PDF en {INFORME}')


if __name__ == '__main__':
    main()
