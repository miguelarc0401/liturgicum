# -*- coding: utf-8 -*-
"""La fe de erratas de la app: lo que se corrige a mano en el texto, y que
ha de seguir corregido cada vez que se rehacen los datos.

Los textos de app/datos/ no se escriben a mano: los rehace cada libro desde
sus fuentes —las lecturas, src/15_app_data.py y 21_lect1977_app.py; las
horas, Breviarium/src/4_app.py; la misa, Missale/src/6_app.py; el
devocionario, Enchiridion/src/5_app.py—, y una errata corregida en el JSON
publicado volvería a salir en la siguiente pasada. Así que lo corregido se
apunta aparte, en data/fe_de_erratas.json, y cada una de esas fases llama a
`aplica()` justo antes de escribir su fichero.

Cada errata guarda el trozo como estaba y como queda, con unas palabras de
contexto, y los sitios donde se cambió: el fichero de app/datos/ y la ruta
dentro de él. Al rehacer, se cambia en esos sitios; si un sitio ya no está
—el libro se rehízo con otro orden—, el trozo se busca por todo el fichero y
se cambia sólo si sale en tantos sitios como faltan. Lo que no se encuentra
se dice, que es que la fuente cambió (o que ya trae la corrección).

Las erratas se corrigen desde la app, servida por Enchiridion/src/editar.py:
se selecciona el texto y se escribe como debe quedar. El servidor busca ese
texto en los datos publicados (`busca`), lo cambia y lo apunta (`corrige`),
y lo devuelve a como estaba si se deshace (`deshace`).
"""

import bisect
import datetime
import io
import json
import os
import re
import unicodedata
import uuid

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DATOS = os.path.join(RAIZ, 'app', 'datos')
FICHERO = os.path.join(RAIZ, 'data', 'fe_de_erratas.json')

NOTA = ('Las erratas corregidas a mano desde la app. Cada cambio dice el '
        'trozo como estaba («antes») y como queda («despues»), y en qué '
        'sitios: el fichero de app/datos/ y la ruta dentro de él. Lo escribe '
        'Enchiridion/src/editar.py y lo vuelve a aplicar cada fase que '
        'rehace los datos (src/erratas.py).')

# para decir dónde está un texto con palabras y no con el nombre del fichero
NOMBRES = {
    'horas.json': 'Liturgia de las Horas',
    'horas_dias.json': 'Horas, días',
    'lecturas_es.json': 'Lecturas en castellano',
    'lecturas_clementina.json': 'Lecturas, Clementina',
    'lecturas_nova.json': 'Lecturas, Nova Vulgata',
    'lecturas_lect1977.json': 'Lecturas, Misal de 1977',
    'misa.json': 'Misa',
    'misal_latino.json': 'Misal latino',
    'ordinario.json': 'Ordinario de la misa',
    'prefacios.json': 'Prefacios',
    'devocionario.json': 'Devocionario',
    'calendario.json': 'Calendario',
    'indice.json': 'Índice',
}


class Fallo(Exception):
    """Lo que no se puede hacer, dicho para quien lo pidió."""


# ------------------------------------------------------------ el texto llano
_MARCAS = re.compile('[̀-ͯ]')
_VISTAS = set()
_TRADUCE = {}


def _plano_letra(c):
    return (_MARCAS.sub('', unicodedata.normalize('NFD', c))
            .replace('æ', 'ae').replace('Æ', 'AE')
            .replace('œ', 'oe').replace('Œ', 'OE').lower())


def plano(t):
    """Sin diacríticos, con æ y œ desatadas y en minúscula: lo mismo que
    plano() de app.js. Es como se compara lo que la app enseña con lo que
    hay en los datos cuando no casan letra a letra: el latín con los acentos
    apagados, un rótulo que la app pone en otra caja. Va letra a letra, con
    una tabla, para que los 55 MB de datos se hagan en un momento y para
    que plano_con_mapa() diga lo mismo."""
    for c in set(t) - _VISTAS:
        p = _plano_letra(c)
        if p != c:
            _TRADUCE[ord(c)] = p
        _VISTAS.add(c)
    return t.translate(_TRADUCE)


def plano_con_mapa(t):
    """plano(t), y de qué letra de `t` sale cada una de las suyas (con una
    de más al final, la longitud de `t`)."""
    plano(t)
    letras, mapa = [], []
    for i, c in enumerate(t):
        x = _TRADUCE.get(ord(c), c)
        letras.append(x)
        mapa.extend([i] * len(x))
    mapa.append(len(t))
    return ''.join(letras), mapa


def _cod(t):
    """Cómo se escribe `t` dentro de un JSON de app/datos/, para buscarlo en
    el fichero tal cual antes de leerlo entero."""
    return json.dumps(t, ensure_ascii=False)[1:-1]


# ------------------------------------------------------------- los sitios
def sitio(obj, ruta):
    """El contenedor y la llave de la cadena que hay en `ruta`, o None si
    ahí ya no hay una cadena."""
    x = obj
    try:
        for k in ruta[:-1]:
            x = x[k]
        if isinstance(x[ruta[-1]], str):
            return x, ruta[-1]
    except (KeyError, IndexError, TypeError):
        pass
    return None


def cadenas(obj, prueba):
    """Las cadenas de `obj` —los valores, no las llaves— que pasan la
    prueba, cada una con su ruta."""
    salen, ruta = [], []

    def anda(x):
        if isinstance(x, str):
            if prueba(x):
                salen.append((tuple(ruta), x))
        elif isinstance(x, list):
            for i, y in enumerate(x):
                ruta.append(i)
                anda(y)
                ruta.pop()
        elif isinstance(x, dict):
            for k, y in x.items():
                ruta.append(k)
                anda(y)
                ruta.pop()
    anda(obj)
    return salen


def sustituye(texto, antes, despues):
    """Cambia `antes` por `despues` en `texto`, salvo donde ya está puesto
    `despues`: si «Dio» se corrigió en «Dios», aplicarlo otra vez no ha de
    dar «Dioss». Devuelve el texto y cuántas veces lo cambió."""
    puesto = []
    i = texto.find(despues)
    while i >= 0:
        puesto.append((i, i + len(despues)))
        i = texto.find(despues, i + 1)
    trozos, j, n = [], 0, 0
    i = texto.find(antes)
    while i >= 0:
        f = i + len(antes)
        if any(a <= i and f <= b for a, b in puesto):
            i = texto.find(antes, i + 1)
            continue
        trozos.append(texto[j:i])
        trozos.append(despues)
        j = f
        n += 1
        i = texto.find(antes, f)
    trozos.append(texto[j:])
    return ''.join(trozos), n


# --------------------------------------------- la fe de erratas en el disco
def lee():
    if not os.path.exists(FICHERO):
        return {'nota': NOTA, 'erratas': []}
    with io.open(FICHERO, encoding='utf-8') as fh:
        d = json.load(fh)
    return {'nota': NOTA, 'erratas': d.get('erratas') or []}


def escribe(d):
    with io.open(FICHERO, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1)
        fh.write('\n')


# ---------------------------------------------------- al rehacer los datos
def aplica(nombre, obj, di=print):
    """Pone en `obj` —el fichero `nombre` de app/datos/, a punto de
    escribirse— las erratas apuntadas para él. Devuelve cuántos sitios ha
    corregido; lo que ya no encuentra, lo dice."""
    puestas, ya, perdidas = 0, 0, []
    for e in lee()['erratas']:
        for c in e.get('cambios', []):
            antes, despues = c['antes'], c['despues']
            rutas = [s['r'] for s in c['sitios'] if s['f'] == nombre]
            faltan = 0
            for r in rutas:
                s = sitio(obj, r)
                if s is None:
                    faltan += 1
                    continue
                cont, k = s
                nuevo, n = sustituye(cont[k], antes, despues)
                if n:
                    cont[k] = nuevo
                    puestas += 1
                elif despues in cont[k]:
                    ya += 1
                else:
                    faltan += 1
            if not faltan:
                continue
            # el sitio se ha movido: el trozo se busca por todo el fichero,
            # y se cambia sólo si sale en tantos sitios como faltan, que si
            # sale en más ya no se sabe cuál era
            hay = cadenas(obj, lambda t: antes in t
                          and sustituye(t, antes, despues)[1] > 0)
            if hay and len(hay) <= faltan:
                for r, t in hay:
                    cont, k = sitio(obj, r)
                    cont[k] = sustituye(t, antes, despues)[0]
                    puestas += 1
            else:
                perdidas.append('«%s» (%s, %d %s)'
                                % (e.get('cambio') or antes, e['id'], faltan,
                                   'sitio' if faltan == 1 else 'sitios'))
    if puestas or perdidas:
        di('  fe de erratas: %d %s en %s'
           % (puestas, 'corregido' if puestas == 1 else 'corregidos', nombre)
           + (' (%d ya venían bien)' % ya if ya else ''))
    for p in perdidas:
        di('  AVISO fe de erratas: no encuentro %s en %s. La fuente ha '
           'cambiado; mira data/fe_de_erratas.json.' % (p, nombre))
    return puestas


# -------------------------------------------- lo publicado, para el editor
class Publicados:
    """Los ficheros de app/datos/, leídos una vez y vueltos a leer si
    cambian en el disco (una fase que se corre con el editor abierto)."""

    def __init__(self, carpeta=APP_DATOS):
        self.carpeta = carpeta
        self._crudo, self._llano, self._obj, self._hora = {}, {}, {}, {}

    def nombres(self):
        return sorted(f for f in os.listdir(self.carpeta)
                      if f.endswith('.json'))

    def _al_dia(self, f):
        h = os.path.getmtime(os.path.join(self.carpeta, f))
        if self._hora.get(f) != h:
            for c in (self._crudo, self._llano, self._obj):
                c.pop(f, None)
            self._hora[f] = h

    def crudo(self, f):
        self._al_dia(f)
        if f not in self._crudo:
            with io.open(os.path.join(self.carpeta, f), encoding='utf-8') as fh:
                self._crudo[f] = fh.read()
        return self._crudo[f]

    def llano(self, f):
        self._al_dia(f)
        if f not in self._llano:
            self._llano[f] = plano(self.crudo(f))
        return self._llano[f]

    def obj(self, f):
        self._al_dia(f)
        if f not in self._obj:
            self._obj[f] = json.loads(self.crudo(f))
        return self._obj[f]

    def guarda(self, f):
        """Escribe el fichero como lo escriben las fases —compacto y sin
        escapar los acentos—, de modo que lo que no se ha tocado queda
        igual byte a byte."""
        texto = json.dumps(self._obj[f], ensure_ascii=False,
                           separators=(',', ':'))
        ruta = os.path.join(self.carpeta, f)
        with io.open(ruta + '.tmp', 'w', encoding='utf-8') as fh:
            fh.write(texto)
        os.replace(ruta + '.tmp', ruta)
        # lo leído sigue valiendo: es lo que se acaba de escribir
        self._hora[f] = os.path.getmtime(ruta)
        self._crudo[f] = texto
        self._llano.pop(f, None)

    def donde(self, f, r):
        """El sitio dicho para quien lee: el libro, la clave y el rótulo de
        la pieza."""
        x, claves, rotulo = self.obj(f), [], ''
        for k in r[:-1]:
            x = x[k]
            if isinstance(k, str) and len(k) > 2:
                claves.append(k)
            if isinstance(x, dict):
                t = x.get('tes') or x.get('tla') or x.get('t') or x.get('r')
                if isinstance(t, list):
                    t = ''
                if isinstance(t, str) and t.strip():
                    rotulo = t.strip() + (' ' + x['c'] if isinstance(
                        x.get('c'), str) else '')
        partes = [NOMBRES.get(f, f)] + claves[-2:]
        if rotulo and rotulo not in claves:
            partes.append(rotulo)
        d = ' · '.join(partes)
        return d if len(d) <= 160 else d[:157] + '…'


# ------------------------------------------------------ buscar el texto
def _letra(c):
    return c.isalnum()


def _palabra(t, a, b):
    """[a, b) ensanchado a palabras enteras; si está vacío, con la palabra
    de delante y la de detrás."""
    if a == b:
        while a > 0 and not _letra(t[a - 1]):
            a -= 1
        while b < len(t) and not _letra(t[b]):
            b += 1
    while a > 0 and _letra(t[a - 1]):
        a -= 1
    while b < len(t) and _letra(t[b]):
        b += 1
    return a, b


def _desde(t, a, k, ini):
    """Dónde empieza un trozo que llega hasta `a` con unas `k` letras de
    contexto delante, sin partir palabra y no antes de `ini`."""
    if k is None:
        return ini
    i = max(ini, a - k)
    if i > ini and _letra(t[i - 1]):
        while i < a and _letra(t[i]):
            i += 1
    while i < a and t[i].isspace():
        i += 1
    return i


def _hasta(t, b, k, fin):
    if k is None:
        return fin
    i = min(fin, b + k)
    if i < fin and _letra(t[i]):
        while i > b and _letra(t[i - 1]):
            i -= 1
    while i > b and t[i - 1].isspace():
        i -= 1
    return i


# De más a menos contexto alrededor de lo cambiado: primero el texto entero
# que la app enseña, que es lo más seguro; luego trozos más cortos, porque lo
# que la app enseña de una vez puede venir de varias cadenas (los versículos
# sin número van de corrido) o llevar algo que la app le añade (el íncipit).
CONTEXTOS = ((None, None), (60, 60), (30, 30), (60, 0), (0, 60), (15, 15),
             (30, 0), (0, 30), (0, 0))


class Hallazgo:
    __slots__ = ('f', 'r', 's', 'i', 'exacto', 'fuerte')

    def __init__(self, f, r, s, i, exacto):
        self.f, self.r, self.s, self.i, self.exacto = f, r, s, i, exacto
        self.fuerte = False


def _casa_delante(dato, pagina):
    """Lo que hay delante en los datos casa con lo que la página enseña
    delante. Si la cadena empieza ahí, delante puede ir cualquier cosa (otra
    tirada, el número del versículo); si la cadena trae algo y la página no
    enseña nada, es otro sitio."""
    dato = dato.rsplit('\n', 1)[-1]
    if not dato:
        return True
    if not pagina:
        return False
    n = min(len(dato), len(pagina))
    return dato[-n:] == pagina[-n:]


def _casa_detras(dato, pagina):
    dato = dato.split('\n', 1)[0]
    if not dato:
        return True
    if not pagina:
        return False
    n = min(len(dato), len(pagina))
    return dato[:n] == pagina[:n]


def busca(pub, texto, nuevo, antes='', despues=''):
    """Dónde está, en los datos publicados, el texto que la app enseña.

    `texto` es lo que enseña la app en una tirada (un nodo de texto de la
    página) y `nuevo`, cómo ha de quedar; `antes` y `despues`, lo que la
    página enseña alrededor en el mismo renglón. Devuelve el plan: lo que
    cambia, los sitios seguros (el texto y lo de alrededor casan) y los
    otros (el mismo texto, con otra cosa alrededor)."""
    if not isinstance(texto, str) or not isinstance(nuevo, str):
        raise Fallo('Petición mal hecha.')
    if texto == nuevo:
        raise Fallo('No has cambiado nada.')
    if len(texto) > 20000 or len(nuevo) > 20000:
        raise Fallo('El texto es demasiado largo.')
    if '\n' in nuevo and '\n' not in texto:
        raise Fallo('Un salto de renglón no se puede añadir aquí: se '
                    'corrige el texto, no la maquetación.')
    n = len(texto)
    p = 0
    while p < min(n, len(nuevo)) and texto[p] == nuevo[p]:
        p += 1
    q = 0
    while (q < min(n, len(nuevo)) - p
           and texto[n - 1 - q] == nuevo[len(nuevo) - 1 - q]):
        q += 1
    e = n - q                              # [p, e) cambia; en el nuevo, [p, e2)
    e2 = len(nuevo) - q
    # lo que se busca es la palabra entera, y nunca los espacios de los
    # bordes, que suelen ser de la maquetación y no del texto
    ini = len(texto) - len(texto.lstrip())
    fin = len(texto.rstrip())
    a, b = _palabra(texto, p, e)
    a, b = max(a, ini), min(b, fin)
    if a >= b or p < a or e > b:
        raise Fallo('El cambio cae en los espacios del principio o del '
                    'final, que no son del texto.')
    plan = {'texto': texto, 'nuevo': nuevo, 'p': p, 'e': e, 'e2': e2,
            'cambio': {'de': texto[a:b], 'a': nuevo[a:b + e2 - e]}}

    izq = plano(antes or '')
    der = plano(despues or '')
    vistos = set()
    for kl, kr in CONTEXTOS:
        lo, hi = _desde(texto, a, kl, ini), _hasta(texto, b, kr, fin)
        if (lo, hi) in vistos or lo >= hi:
            continue
        vistos.add((lo, hi))
        trozo = texto[lo:hi]
        for exacto in (True, False):
            hay = _halla(pub, trozo, exacto)
            if not hay:
                continue
            delante = izq + plano(texto[:lo])
            detras = plano(texto[hi:]) + der
            for h in hay:
                if h.exacto:
                    s_ant, s_des = h.s[:h.i], h.s[h.i + len(trozo):]
                    h.fuerte = (_casa_delante(plano(s_ant), delante)
                                and _casa_detras(plano(s_des), detras))
                else:
                    ps = plano(h.s)
                    h.fuerte = (_casa_delante(ps[:h.i], delante)
                                and _casa_detras(ps[h.i + len(plano(trozo)):],
                                                 detras))
            plan.update(lo=lo, hi=hi, trozo=trozo,
                        fuertes=[h for h in hay if h.fuerte],
                        otros=[h for h in hay if not h.fuerte])
            return plan
    raise Fallo('No encuentro este texto en los datos de la app. Puede que '
                'la app lo componga (un rótulo, una fecha, un número) y no '
                'esté escrito así en ningún fichero.')


def _halla(pub, trozo, exacto):
    hay = []
    if exacto:
        cod = _cod(trozo)
        for f in pub.nombres():
            if cod not in pub.crudo(f):
                continue
            for r, s in cadenas(pub.obj(f), lambda t: trozo in t):
                i = s.find(trozo)
                while i >= 0:
                    hay.append(Hallazgo(f, r, s, i, True))
                    i = s.find(trozo, i + len(trozo))
        return hay
    llano = plano(trozo)
    if not llano.strip():
        return hay
    cod = _cod(llano)
    for f in pub.nombres():
        if cod not in pub.llano(f):
            continue
        for r, s in cadenas(pub.obj(f), lambda t: llano in plano(t)):
            ps = plano(s)
            i = ps.find(llano)
            while i >= 0:
                hay.append(Hallazgo(f, r, s, i, False))
                i = ps.find(llano, i + len(llano))
    return hay


def _en_el_dato(plan, h):
    """Dónde cae el cambio dentro de la cadena del hallazgo: [x, y) se
    sustituye por `pon`."""
    p, e, lo = plan['p'], plan['e'], plan['lo']
    pon = plan['nuevo'][p:plan['e2']]
    if h.exacto:
        return h.i + p - lo, h.i + e - lo, pon
    _, mapa_t = plano_con_mapa(plan['trozo'])
    _, mapa_s = plano_con_mapa(h.s)
    x = mapa_s[h.i + bisect.bisect_left(mapa_t, p - lo)]
    y = mapa_s[h.i + bisect.bisect_left(mapa_t, e - lo)]
    # lo que la app enseña en su caja y los datos traen en mayúsculas (un
    # rótulo) se escribe en mayúsculas, como lo de alrededor
    junto = h.s[x:y] if x < y else h.s[max(0, x - 1):x + 1]
    letras = [c for c in junto if c.isalpha()]
    if letras and all(c.isupper() for c in letras):
        pon = pon.upper()
    return x, y, pon


def _ventana(s, x, y, pon, k=24):
    """El trozo que se apunta en la fe de erratas: lo cambiado y unas
    palabras alrededor, hasta que salga una sola vez en su cadena."""
    a, b = _palabra(s, x, y)
    while True:
        lo, hi = _desde(s, a, k, 0), _hasta(s, b, k, len(s))
        antes = s[lo:hi]
        if s.count(antes) == 1 or (lo == 0 and hi == len(s)):
            return antes, s[lo:x] + pon + s[y:hi]
        k *= 2


def resumen(pub, plan, cuantos=40):
    """Lo que la ficha de la app enseña antes de guardar."""
    def lista(hs):
        return [pub.donde(h.f, h.r) for h in hs[:cuantos]]
    return {'cambio': plan['cambio'],
            'n': len(plan['fuertes']), 'sitios': lista(plan['fuertes']),
            'n_otros': len(plan['otros']), 'otros': lista(plan['otros'])}


def corrige(pub, datos):
    """Corrige en los datos publicados y lo apunta en la fe de erratas.
    `datos` es lo mismo que para buscar, más `otros` (corregir también
    donde lo de alrededor no casa) y `cuantos`, los sitios que la app
    enseñó: si ya no son esos, los datos han cambiado y no se toca nada."""
    plan = busca(pub, datos.get('texto'), datos.get('nuevo'),
                 datos.get('antes') or '', datos.get('despues') or '')
    elegidos = plan['fuertes'] + (plan['otros'] if datos.get('otros') else [])
    if not elegidos:
        raise Fallo('No hay ningún sitio marcado para corregir.')
    if datos.get('cuantos') != len(elegidos):
        raise Fallo('Los datos han cambiado desde que buscaste: vuelve a '
                    'buscar.')
    # cadena por cadena, de atrás adelante, para que lo cambiado no mueva
    # dónde cae lo que queda por cambiar
    por_cadena = {}
    for h in elegidos:
        por_cadena.setdefault((h.f, h.r), []).append(h)
    cambios, apuntes, tocados = [], {}, set()
    for (f, r), hs in por_cadena.items():
        s = hs[0].s
        nuevo, hasta = s, len(s) + 1
        for h in sorted(hs, key=lambda h: -h.i):
            x, y, pon = _en_el_dato(plan, h)
            if y > hasta:                     # se pisa con el de detrás
                continue
            antes, despues = _ventana(s, x, y, pon)
            apuntes.setdefault((antes, despues), []).append(
                {'f': f, 'r': list(r)})
            nuevo = nuevo[:x] + pon + nuevo[y:]
            hasta = x
        if nuevo == s:
            continue
        cont, k = sitio(pub.obj(f), r)
        cont[k] = nuevo
        tocados.add(f)
        cambios.append({'f': f, 'r': list(r), 'viejo': s, 'nuevo': nuevo})
    if not cambios:
        raise Fallo('No ha cambiado nada en los datos.')
    for f in sorted(tocados):
        pub.guarda(f)
    d = lee()
    hoy = datetime.date.today().isoformat()
    errata = {'id': 'e_' + hoy.replace('-', '') + '_' + uuid.uuid4().hex[:6],
              'fecha': hoy,
              'cambio': '%s → %s' % (plan['cambio']['de'],
                                     plan['cambio']['a']),
              'cambios': [{'antes': a, 'despues': b, 'sitios': ss}
                          for (a, b), ss in apuntes.items()]}
    d['erratas'].append(errata)
    escribe(d)
    print('  corregida: %s (%d %s)' % (errata['cambio'], len(cambios),
                                       'sitio' if len(cambios) == 1
                                       else 'sitios'))
    return {'id': errata['id'], 'cambio': errata['cambio'],
            'n': len(cambios), 'cambios': cambios, 'total': len(d['erratas'])}


def deshace(pub, eid):
    """Devuelve a como estaban los sitios de una errata y la borra de la
    fe de erratas."""
    d = lee()
    e = next((x for x in d['erratas'] if x['id'] == eid), None)
    if e is None:
        raise Fallo('Esa corrección ya no está en la fe de erratas.')
    cambios, tocados = [], set()
    for c in e.get('cambios', []):
        for st in c['sitios']:
            f = st['f']
            if not os.path.exists(os.path.join(pub.carpeta, f)):
                continue
            s = sitio(pub.obj(f), st['r'])
            if s is None:
                continue
            cont, k = s
            viejo = cont[k]
            nuevo, n = sustituye(viejo, c['despues'], c['antes'])
            if n:
                cont[k] = nuevo
                tocados.add(f)
                cambios.append({'f': f, 'r': st['r'], 'viejo': viejo,
                                'nuevo': nuevo})
    for f in sorted(tocados):
        pub.guarda(f)
    d['erratas'].remove(e)
    escribe(d)
    print('  deshecha: %s' % e.get('cambio', eid))
    return {'cambio': e.get('cambio', ''), 'n': len(cambios),
            'cambios': cambios, 'total': len(d['erratas'])}


def lista():
    """Las erratas apuntadas, la última delante."""
    return [{'id': e['id'], 'fecha': e.get('fecha', ''),
             'cambio': e.get('cambio', ''),
             'n': sum(len(c['sitios']) for c in e.get('cambios', []))}
            for e in reversed(lee()['erratas'])]
