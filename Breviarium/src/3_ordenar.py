# -*- coding: utf-8 -*-
"""Fase 3 — del corpus diario al libro: tiempos, salterio, santoral, comunes.

La fuente publica *días ya armados*: cada 15 de marzo trae sus Laudes
enteras, con lo que ese día toma del salterio, lo que toma del propio del
tiempo y lo que toma del santo, todo seguido y sin costuras. Un libro de
horas hace el camino contrario: guarda cada pieza **una sola vez**, en su
sitio, y el día se arma al rezarlo.

Deshacer esa costura no se adivina: se **mide**, y en tres pasadas.

**Primera — el ferial.** Los días que no celebran a nadie dan el propio
del tiempo puro: agrupados por `(tiempo, semana, día, hora, sección)`, y
la salmodia por `(tiempo, salterio, día, hora)`. Ocho años de testigos
deciden por mayoría, y lo que no es unánime se guarda como variante, que
muchas veces no es errata sino el ciclo dominical asomando.

**Segunda — lo propio.** En una memoria casi todo el oficio sigue siendo
ferial: sólo algunas piezas son del santo. Cuál es cuál no hace falta
suponerlo —se compara—. Cada sección de un día con celebración se coteja
con la del mismo hueco ferial: si dice lo mismo, es del tiempo y no se
toca; si dice otra cosa, es propia.

**Tercera — los comunes.** De lo propio, lo que un día toma «del Común de
los pastores» aparecerá igual en los demás pastores. Así que un texto que
sale con **dos santos distintos del mismo común** es del común; el que
sale con uno solo es de ese santo. También aquí la prueba es el recuento,
no la conjetura.

    python Breviarium/src/3_ordenar.py
"""

import datetime as dt
import difflib
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from breviario import CORPUS, clave, clave_por_fecha, va_por_fecha

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIAS = CORPUS
LIBRO = os.path.join(RAIZ, 'Breviarium', 'datos', 'libro')
QA = os.path.join(RAIZ, 'Breviarium', 'datos', 'ordenar_qa.txt')

# Lo que no cambia ni con el tiempo ni con el santo: es el ordinario.
ORDINARIO = {'invocacion', 'conclusion', 'padrenuestro', 'bendicion',
             'examen', 'antifona_final'}

# La conmemoración de todos los fieles difuntos (2 de noviembre) es un oficio
# entero, el de difuntos, y la fuente la declara con ese rango: si no
# contara como celebración, sus textos irían a parar al hueco ferial del día
# de la semana en que cayó cada año.
RANGOS_PROPIOS = ('SOLEMNIDAD', 'FIESTA', 'MEMORIA', 'MEMORIA LIBRE',
                  'CONMEMORACIÓN')

# La lectura bíblica del Oficio sigue el ciclo de dos años: el mismo hueco
# del tiempo trae una lectura los años impares (I) y otra los pares (II).
# Medido en el volcado: en 307 de los 350 días del tiempo las dos lecturas
# son distintas y cada año repite siempre la suya. La mayoría de todos los
# años, que es lo que guarda `tiempo.json`, se queda con una sola.
BIENAL = ('lectura1', 'responsorio')

# Lo propio de un santo y lo de los comunes no es lo mismo todo el año: en
# Pascua el libro trae otras lecturas breves, otros responsorios, otras
# antífonas y hasta otros himnos («Fuera del tiempo pascual / En tiempo
# pascual», «T. P. Aleluya»). Medido: el común de un mártir da en Laudes
# «El que se aborrece a sí mismo…» todo el año, y en Pascua «Estad alegres
# y contentos… Aleluya»; el de apóstoles, otro himno. Sin el tiempo en la
# clave, gana la forma que tenga más testigos y sale en el otro tiempo.
PASCUA = 'Pascua'
INTERMEDIAS = ('tercia', 'sexta', 'nona')


# --------------------------------------------------------------------------
# el año litúrgico de una fecha
# --------------------------------------------------------------------------

def primer_domingo_de_adviento(anio):
    """El domingo que cae del 27 de noviembre al 3 de diciembre."""
    d = dt.date(anio, 11, 27)
    return (d + dt.timedelta(days=(6 - d.weekday()) % 7)).isoformat()


def anio_liturgico(fecha, inicios):
    # El calendario del proyecto empieza en 2024 y el volcado en 2019: sin
    # el cálculo, el Adviento de 2019 a 2022 contaba en el año civil que
    # acababa, con el ciclo y el año ferial del año anterior.
    a = int(fecha[:4])
    ini = inicios.get(a) or primer_domingo_de_adviento(a)
    return a + 1 if fecha >= ini else a


def ciclo_de(anio):
    """El ciclo dominical (A, B, C): el año litúrgico 2026 es A, 2025 C.
    (Hasta el 2026-10-14 decía 'ABC'[anio % 3], corrido una letra; no se
    notaba porque nadie lo leía.)"""
    return 'CAB'[anio % 3]


def ferial_de(anio):
    """El año ferial del Oficio de Lectura: I los impares, II los pares."""
    return 'I' if anio % 2 else 'II'


# --------------------------------------------------------------------------
# coordenadas
# --------------------------------------------------------------------------

def hueco_ferial(dia, hora_cl, clase):
    """Dónde va esta sección si el día no celebra a nadie."""
    tiempo, sem, ds = dia.get('tiempo'), dia.get('semana'), dia.get('dia_semana')
    if not tiempo:
        return None
    # del 17 al 24 de diciembre, la octava de Navidad y del 2 de enero al
    # Bautismo, por fecha (breviario.va_por_fecha)
    if dia.get('fecha') and va_por_fecha(tiempo, dia['fecha'], ds, hora_cl,
                                         clase):
        return f"{clave_por_fecha(tiempo, dia['fecha'])}/{hora_cl}/{clase}"
    if sem is not None and ds is not None:
        return f'{tiempo}/{sem}/{ds}/{hora_cl}/{clase}'
    return f"{tiempo}/@/{clave(dia.get('titulo') or '')}/{hora_cl}/{clase}"


def hueco_salterio(dia, hora_cl):
    """La salmodia ferial. No basta el número del salterio: los salmos
    vuelven cada cuatro semanas y sus antífonas no —Adviento, Cuaresma y
    Pascua tienen las suyas—. Medido sobre ocho años, la clave sin el
    tiempo deja el 0 % de casillas con un solo texto; con él, el 85 %."""
    if not dia.get('salterio') or dia.get('dia_semana') is None:
        return None
    return f"{dia['tiempo']}/{dia['salterio']}/{dia['dia_semana']}/{hora_cl}"


def comun_de(dia):
    """El común del que el día toma su oficio, si lo declara.

    La cabecera lleva a veces el salterio pegado («Del Común de un mártir.
    Salterio I»), y entonces cada semana del salterio era un común distinto:
    los testigos del mártir se repartían en cinco montones y ganaba la forma
    pascual, que era la única que no se había partido. El salterio se quita."""
    origen = (dia.get('origen') or '')
    m = re.search(r'com[uú]n\s+(?:de\s+)?(?:l[oa]s?\s+)?(.+)$', origen, re.I)
    if not m:
        return None
    return re.sub(r'\s+salterio\s+[ivx]+$', '', clave(m.group(1))) or None


def unifica_comunes(nombres):
    """nombre -> el nombre con que se queda, para las erratas de la cabecera
    («un martrir», «pastores para una santo obispo»): se juntan con el más
    usado de los que difieren de él en una o dos letras. Un parecido
    relativo no vale: en los nombres largos, «papa» por «obispo» o «santas
    mujeres» por «santos varones» lo pasaban, y son otro común."""
    def letras_distintas(a, b):
        return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2
                   in difflib.SequenceMatcher(None, a, b).get_opcodes()
                   if op != 'equal')
    orden = [n for n, _ in sorted(nombres.items(), key=lambda x: (-x[1], x[0]))]
    canon = {}
    for n in orden:
        if n in canon:
            continue
        canon[n] = n
        for m in orden:
            if m not in canon and letras_distintas(n, m) <= 2:
                canon[m] = n
    return canon


def incipit(lineas, n=6):
    """Las primeras palabras de un texto: con ellas se reconoce un himno."""
    for ln in lineas:
        t = clave(''.join(s for rojo, s in ln if not rojo))
        if t:
            return ' '.join(t.split()[:n])
    return ''


ABRE_ANT = re.compile(r'^\s*Ant\b')
# el titulo va a veces en mayusculas («SALMO 62») y a veces no
TITULO_SALMO = re.compile(r'^\s*(salmo|c[áa]ntico)\b', re.I)


def antifonas_de(lineas):
    """Las antífonas con que abre cada salmo de una salmodia.

    Una salmodia es antífona, salmo, antífona repetida, y así tres veces.
    Lo del santo son las antífonas; los salmos son los del salterio que
    toque ese día, y por eso la salmodia entera cambia de un año a otro
    aunque la celebración sea la misma —y por eso no hay mayoría que valga
    si se mide entera—. Se recogen sólo las que abren, es decir, las que van
    delante de un título de salmo: la repetición del final no cuenta.
    """
    salida = []
    for i, ln in enumerate(lineas):
        if not (ln and ln[0][0] and ABRE_ANT.match(ln[0][1])):
            continue
        j = i + 1
        while j < len(lineas) and not lineas[j]:
            j += 1
        if (j < len(lineas) and lineas[j] and lineas[j][0][0]
                and TITULO_SALMO.match(lineas[j][0][1])):
            t = ' '.join(x for rojo, x in ln if not rojo).strip()
            if t:
                salida.append(re.sub(r'\s+', ' ', t))
    return tuple(salida)


def salmos_de(lineas):
    """Los títulos de los salmos de una salmodia, que son los que la
    identifican: «Salmo 62», «Cántico: Dn 3», «Salmo 149»."""
    return tuple(re.sub(r'\s+', ' ', ln[0][1]).strip()
                 for ln in lineas
                 if ln and ln[0][0] and TITULO_SALMO.match(ln[0][1]))


def donde_estan_esos_salmos(salterio_libro):
    """Un índice de los salmos del salterio: qué semana y qué día los tiene.

    Sirve para leer una rúbrica que el libro escribe y la fuente no: «se
    toma la salmodia del domingo I». La fuente no la escribe, la *aplica* —
    pone esos salmos y no los del día—, así que la rúbrica se recupera
    mirando qué casilla del salterio trae los salmos que la fuente puso.
    Se indexa sólo el tiempo ordinario, porque los salmos de una misma
    casilla son los mismos en todos los tiempos y sólo cambian las
    antífonas, que aquí se sustituyen de todos modos.
    """
    indice = {}
    for k, v in salterio_libro.items():
        tiempo, sem, dia, hora = k.split('/')
        if tiempo != 'Ordinario':
            continue
        sal = salmos_de(v['lineas'])
        if sal:
            indice.setdefault((hora, sal), (sem, dia))
    return indice


def texto_de(lineas):
    return clave(' '.join(''.join(t for _, t in ln) for ln in lineas))


# --------------------------------------------------------------------------

def parecidos(a, b):
    """Dos textos (en clave) que son el mismo salvo el aleluya y poco más:
    la forma pascual y la de todo el año de una antífona o un responsorio."""
    def palabras(t):
        return re.sub(r'\baleluya\b', ' ', t).split()
    return difflib.SequenceMatcher(None, palabras(a),
                                   palabras(b)).ratio() >= 0.8


def mayoria(cuenta):
    """{texto: testigos} -> [(texto, testigos)], el más atestiguado delante."""
    return sorted(cuenta.items(), key=lambda kv: (-len(kv[1]), kv[0]))


def decide(casillas, textos, rotulos, rot_texto=None, por_tiempo=False):
    """De cada casilla, el texto más atestiguado; los demás, variantes.

    El rótulo es el del texto elegido, si se sabe (`rot_texto`): en la
    lectura breve lleva la cita, y la forma pascual tiene otra.

    Con `por_tiempo`, el texto de todo el año sale de los testigos de fuera
    de Pascua, y el de Pascua de los suyos; si dicen otra cosa, éste va en
    `pascua`. Si la casilla sólo tiene testigos de Pascua, lo dice
    `solo_pascua`, porque entonces lo de todo el año es la forma pascual."""
    salida = {}
    con_variantes = 0

    def rotulo(k, h):
        rot = (rot_texto or {}).get((k, h)) or rotulos.get(k)
        return rot.most_common(1)[0][0] if rot else None

    for k, cuenta in casillas.items():
        orden = mayoria(cuenta)
        pascual = None
        if por_tiempo:
            fuera = {h: [t for t in ts if t['t'] != PASCUA]
                     for h, ts in cuenta.items()}
            fuera = {h: ts for h, ts in fuera.items() if ts}
            en_pascua = {h: [t for t in ts if t['t'] == PASCUA]
                         for h, ts in cuenta.items()}
            en_pascua = {h: ts for h, ts in en_pascua.items() if ts}
            # Los empates de un tiempo los deshacen los testigos de todos los
            # años: san Felipe Neri cae fuera de Pascua dos de ocho, y uno de
            # ellos (2026) la fuente le dejó las Vísperas de la Trinidad del
            # domingo anterior; uno contra uno, ganaba el orden alfabético.
            def mayoria_en(parte):
                return sorted(parte.items(), key=lambda kv: (
                    -len(kv[1]), -len(cuenta[kv[0]]), kv[0]))[0]
            if fuera:
                h = mayoria_en(fuera)[0]
                # Un testigo solo fuera de Pascua que no se parece a lo que
                # dicen los de Pascua no basta: es más fácil que sea un resto
                # de otro día que la forma de todo el año. Entonces se hace
                # como si sólo hubiera Pascua, y la fase 4 le quita el
                # aleluya.
                if (len(fuera[h]) == 1 and en_pascua and not parecidos(
                        h, mayoria_en(en_pascua)[0])):
                    fuera = {}
            if fuera:
                orden = [(h, cuenta[h])] + [x for x in orden if x[0] != h]
            # La forma de Pascua ha de ser de Pascua: un texto que sale sobre
            # todo en Pascua. No vale el más rezado en Pascua, porque la
            # fuente no es constante: en el común de un mártir, san
            # Estanislao lleva todos los años la forma pascual («Estad
            # alegres y contentos…») y san Justino y san Bonifacio, cayendo
            # en Pascua, la de todo el año —y san Justino, en el ordinario,
            # a veces la pascual—. Y un texto que sale también en Adviento o
            # en el ordinario tanto como en Pascua no es la forma pascual del
            # común sino lo que traen unas pocas celebraciones que coinciden
            # (las fiestas de la Virgen con «Vi la ciudad santa»), y no debe
            # cambiar el común en Pascua para todas las demás. Con el aleluya
            # que la forma de todo el año no tiene se pide menos.
            if en_pascua:
                general = h if fuera else None

                # Lo que sale fuera de Pascua puede ser la forma pascual que
                # se escapa (san Justino la rezó en el ordinario) o un uso de
                # verdad de otro tiempo (la Inmaculada y Guadalupe, en
                # Adviento). Se distingue por quién la reza: si fuera de
                # Pascua sólo la dicen celebraciones que también la dicen en
                # Pascua, se ha escapado.
                def de_pascua(hh):
                    cuota = len(en_pascua[hh]) / len(cuenta[hh])
                    fuera_de = {t.get('s') for t in cuenta[hh]
                                if t['t'] != PASCUA}
                    escapada = fuera_de <= {t.get('s') for t in en_pascua[hh]}
                    return cuota >= 0.6 or (cuota >= 0.4 and (escapada or (
                        'aleluya' in hh.split()
                        and general and 'aleluya' not in general.split())))
                cands = [hh for hh in en_pascua if hh != general
                         and len(en_pascua[hh]) >= 2 and de_pascua(hh)]
                if cands:
                    hp = max(cands, key=lambda hh: (
                        len(en_pascua[hh]), len(cuenta[hh]), hh))
                    pascual = (hp, en_pascua[hp])
        h, testigos = orden[0]
        entrada = {
            'rotulo': rotulo(k, h),
            'lineas': textos[h],
            'testigos': len(testigos),
            'desde': min(t['f'] for t in testigos),
        }
        if por_tiempo:
            if not fuera:
                entrada['solo_pascua'] = True
            elif pascual and pascual[0] != h:
                entrada['pascua'] = {'rotulo': rotulo(k, pascual[0]),
                                     'lineas': textos[pascual[0]],
                                     'testigos': len(pascual[1])}
        if len(orden) > 1:
            con_variantes += 1
            entrada['variantes'] = [{
                'lineas': textos[hh],
                'testigos': len(tt),
                'ciclos': sorted({t['c'] for t in tt}),
                'feriales': sorted({t['l'] for t in tt}),
                'tiempos': sorted({t['t'] for t in tt if t['t']}),
                'fechas': sorted(t['f'] for t in tt)[:8],
            } for hh, tt in orden[1:]]
        salida[k] = entrada
    return salida, con_variantes


def main():
    os.makedirs(LIBRO, exist_ok=True)

    inicios = {}
    civil = os.path.join(RAIZ, 'data', 'calendario_civil.json')
    if os.path.exists(civil):
        with open(civil, encoding='utf-8') as f:
            for _, d in json.load(f)['anios'].items():
                inicios[int(d['inicio'][:4])] = d['inicio']

    cabeceras = {}                                # fecha  -> cómo se clasifica
    secuencias = defaultdict(Counter)             # el orden de cada hora
    textos = {}                                   # huella -> lineas
    rotulos = defaultdict(Counter)                # clave  -> rótulos vistos
    ferial = defaultdict(lambda: defaultdict(list))
    salterio = defaultdict(lambda: defaultdict(list))
    ordinario = defaultdict(lambda: defaultdict(list))
    propios = []                                  # los días que celebran
    antifonas = defaultdict(list)                 # celebración/hora -> antífonas
    bienal = defaultdict(lambda: defaultdict(Counter))  # hueco -> año -> textos
    rotulos_bienal = defaultdict(Counter)         # (hueco, texto) -> rótulos
    santos = defaultdict(Counter)
    resenas = defaultdict(Counter)                # mm-dd/santo -> reseñas
    cuentas, avisos = Counter(), []
    dias_vistos = 0

    # ---------------------------------------------------------- primera pasada
    for fich in sorted(os.listdir(DIAS)):
        if not fich.endswith('.json'):
            continue
        with open(os.path.join(DIAS, fich), encoding='utf-8') as f:
            anio_dias = json.load(f)
        for fecha, dia in sorted(anio_dias.items()):
            dias_vistos += 1
            al = anio_liturgico(fecha, inicios)
            testigo = {'f': fecha, 'c': ciclo_de(al), 'l': ferial_de(al),
                       't': dia.get('tiempo')}

            # Algunas subcarpetas de opción no traen index.htm propio:
            # entonces valen la clasificación y la celebración del día que
            # las contiene, que es de donde cuelgan.
            oficios = [dia]
            for op in (dia.get('opciones') or []):
                heredado = {k: v for k, v in dia.items()
                            if k not in ('horas', 'opciones', 'evangelio')}
                heredado.update({k: v for k, v in op.items() if v is not None})
                # Pero la opción que se declara «De la Feria» o «Propio del
                # Tiempo» es la feria que se puede rezar en vez de la
                # memoria, y no celebra a nadie aunque no lo diga. Heredando
                # el santo, sus textos se tomaban por propios: a san Justino
                # le salía de himno de Laudes el del lunes de la semana IX.
                # (Ningún oficio principal con santo lleva esa cabecera:
                # medido sobre el volcado entero.)
                if re.search(r'\bferia\b|propio del tiempo',
                             op.get('origen') or '', re.I):
                    heredado['celebracion'] = heredado['rango'] = None
                oficios.append(heredado)

            cabeceras[fecha] = {
                k: dia.get(k) for k in
                ('tiempo', 'titulo', 'semana', 'dia_semana', 'salterio',
                 'origen', 'celebracion', 'rango')}

            for of in oficios:
                of.setdefault('fecha', fecha)
                cel = of.get('celebracion')
                rango = of.get('rango')
                celebra = bool(cel and rango in RANGOS_PROPIOS)
                if celebra:
                    santos[fecha[5:]][cel] += 1
                    # la reseña biográfica del índice del día: también por
                    # mayoría de años, por si alguno trae una errata
                    if of.get('resena'):
                        resenas[f'{fecha[5:]}/{clave(cel)}'][of['resena']] += 1

                for hora_cl, h in (of.get('horas') or {}).items():
                    # Una misma clase puede salir dos veces en la misma
                    # hora: el Oficio de Lectura tiene dos lecturas y, tras
                    # cada una, su responsorio. Si las dos fueran a la
                    # misma casilla se pisarían, así que la repetición se
                    # numera: `responsorio`, `responsorio2`…
                    repeticion = Counter()
                    secuencia = []
                    ultima_lectura = None
                    for sec in h['secciones']:
                        base = sec['clase']
                        n = repeticion[base]
                        repeticion[base] += 1
                        cl = base if n == 0 else f'{base}{n + 1}'
                        # El responsorio es el de la lectura que lo precede.
                        # Unos ochenta días el Oficio no trae la primera
                        # lectura (el domingo que impide una memoria, que la
                        # fuente publica igual), y el responsorio de la
                        # hagiográfica salía numerado como el primero: santa
                        # Inés tenía por responsorio bíblico «Celebremos la
                        # festividad de santa Inés».
                        if base == 'responsorio' and ultima_lectura == 'lectura2':
                            cl = 'responsorio2'
                        if base in ('lectura1', 'lectura2'):
                            ultima_lectura = base
                        lineas = sec['lineas']
                        hu = texto_de(lineas)
                        if not hu:
                            continue
                        textos.setdefault(hu, lineas)
                        rot = sec.get('rotulo')
                        secuencia.append(cl)

                        if base in ORDINARIO:
                            # El ordinario tampoco es del todo invariable:
                            # en Cuaresma la invocación inicial calla el
                            # «Aleluya», y la antífona final de la Virgen
                            # cambia en Pascua. Comprobado en la fuente. Así
                            # que también aquí entra el tiempo, y la app
                            # recurre a la forma sin tiempo si falta.
                            kt = f"{of.get('tiempo') or '@'}/{hora_cl}/{cl}"
                            ordinario[kt][hu].append(testigo)
                            if rot:
                                rotulos['ord:' + kt][rot] += 1
                            cuentas['ordinario'] += 1
                            continue

                        ks = hueco_salterio(of, hora_cl) if base == 'salmodia' else None
                        if ks:
                            salterio[ks][hu].append(testigo)
                            if rot:
                                rotulos['sal:' + ks][rot] += 1
                            cuentas['salterio'] += 1
                            # Lo que un santo tiene propio en la salmodia son
                            # sus antífonas, no sus salmos: se apuntan aparte
                            # para cotejarlas luego con las del salterio.
                            if celebra:
                                ants = antifonas_de(lineas)
                                if ants:
                                    kant = (fecha[5:] + '/' + clave(cel)
                                            + '/' + hora_cl)
                                    antifonas[kant].append(
                                        (ks, ants, salmos_de(lineas), hu,
                                         testigo['t']))
                            continue

                        kf = hueco_ferial(of, hora_cl, cl)
                        if kf is None:
                            avisos.append(f'{fecha} {hora_cl}/{cl}: sin tiempo')
                            cuentas['sin_sitio'] += 1
                            continue

                        # En las memorias la lectura bíblica es la del
                        # tiempo, así que también ellas atestiguan el año
                        if (hora_cl == 'oficio' and cl in BIENAL and (
                                not celebra
                                or rango in ('MEMORIA', 'MEMORIA LIBRE'))):
                            bienal[kf][testigo['l']][hu] += 1
                            if rot:
                                rotulos_bienal[(kf, hu)][rot] += 1

                        if celebra:
                            propios.append((kf, cel, comun_de(of), rango,
                                            hora_cl, cl, hu, rot, testigo))
                        else:
                            ferial[kf][hu].append(testigo)
                            if rot:
                                rotulos['tie:' + kf][rot] += 1
                            cuentas['tiempo'] += 1

                    secuencias[hora_cl][tuple(secuencia)] += 1

    print(f'{dias_vistos} días leídos; {len(textos)} textos distintos',
          flush=True)

    # --------------------------------------------------------- el libro ferial
    tiempo_libro, var_t = decide(
        ferial, textos, {k[4:]: v for k, v in rotulos.items()
                         if k.startswith('tie:')})
    salterio_libro, var_s = decide(
        salterio, textos, {k[4:]: v for k, v in rotulos.items()
                           if k.startswith('sal:')})
    ordinario_libro, var_o = decide(
        ordinario, textos, {k[4:]: v for k, v in rotulos.items()
                            if k.startswith('ord:')})

    # --------------------------------------------------------- segunda pasada
    # una sección de un día que celebra es propia sólo si dice algo
    # distinto de lo que dice el mismo hueco ferial
    # Las antífonas propias de cada celebración: las que no son las del
    # salterio. Que difieran de las del hueco de ese día no basta —la fuente
    # no siempre reza el salterio que le tocaría—, así que se exige además
    # que no sean las de ninguna otra semana del salterio: si lo fueran,
    # serían del salterio y no del santo. Y dos años al menos han de darlas,
    # para que una errata de un año no se tome por el propio.
    del_salterio = {antifonas_de(v['lineas']) for v in salterio_libro.values()}
    del_salterio.discard(())
    donde = donde_estan_esos_salmos(salterio_libro)
    antifonas_libro, dudosas = {}, []
    # los salmos de cada casilla del salterio, para saber si unos salmos son
    # de alguna casilla o de ninguna
    salmos_del_salterio = {salmos_de(v['lineas'])
                           for v in salterio_libro.values()}
    salmos_del_salterio.discard(())
    def sin_aleluya(ants):
        return tuple(re.sub(r'\baleluya\b', '', clave(a)).strip()
                     for a in ants)

    def antifonas_medidas(k, obs, todos, cual=''):
        """Las antífonas propias que dan estos testigos, o None. Los dos
        años que se exigen se cuentan en `todos`, con aleluya o sin él: un
        año en Pascua y otro fuera dicen las mismas antífonas."""
        propias, salmos = Counter(), defaultdict(Counter)
        enteras = defaultdict(Counter)
        for ks, ants, sal, hu, _ in obs:
            ferial = salterio_libro.get(ks)
            if ferial is None or antifonas_de(ferial['lineas']) == ants:
                continue
            propias[ants] += 1
            if sal:
                salmos[ants][sal] += 1
                enteras[(ants, sal)][hu] += 1
        if not propias:
            return None
        ants, n = propias.most_common(1)[0]
        n_todos = sum(1 for ks, a, *_ in todos
                      if sin_aleluya(a) == sin_aleluya(ants)
                      and salterio_libro.get(ks) is not None
                      and antifonas_de(salterio_libro[ks]['lineas']) != a)
        if n_todos < 2 or ants in del_salterio:
            dudosas.append(f'{k}{cual}: {n} de {len(obs)} años'
                           + (', son de otra semana del salterio'
                              if ants in del_salterio else ''))
            return None
        return ants, n, salmos, enteras

    for k, obs in sorted(antifonas.items()):
        # Las de Pascua se miden aparte: llevan su aleluya, y donde el santo
        # cae unos años en Pascua y otros no, la mayoría de todos los años
        # se quedaba con una forma y la sacaba también en el otro tiempo.
        fuera = [o for o in obs if o[4] != PASCUA]
        en_pascua = [o for o in obs if o[4] == PASCUA]
        medida = antifonas_medidas(k, fuera, obs) if fuera else None
        pascual = antifonas_medidas(k, en_pascua, obs, ' (en Pascua)') \
            if en_pascua else None
        solo_pascua = medida is None and pascual is not None
        if solo_pascua:
            medida, pascual = pascual, None
        if medida is None:
            continue
        ants, n, salmos, enteras = medida
        entrada = {'antifonas': list(ants), 'testigos': n, 'de': len(obs)}
        if solo_pascua:
            entrada['solo_pascua'] = True
        elif pascual and pascual[0] != ants:
            entrada['pascua'] = list(pascual[0])
        # «Se toma la salmodia del domingo I»: el libro lo dice con una
        # rúbrica y la fuente no la escribe, la aplica. Si los salmos que
        # puso son siempre los mismos aunque el día caiga en otra semana
        # del salterio, es que la celebración los tiene señalados, y se
        # apunta de qué casilla son para que la app los traiga de allí.
        hora_cl = k.rsplit('/', 1)[-1]
        if salmos[ants]:
            sal, ns = salmos[ants].most_common(1)[0]
            casilla = donde.get((hora_cl, sal))
            if casilla and ns >= 2 and ns * 2 >= n:
                entrada['salmos'] = '/'.join(casilla)
                entrada['salmos_testigos'] = ns
            elif (not casilla and sal not in salmos_del_salterio
                    and ns >= 2 and ns * 2 >= n):
                # Y hay celebraciones cuyos salmos no son de ninguna casilla
                # del salterio: los tiene señalados ella, y el libro los
                # escribe enteros (los Ángeles Custodios en vísperas, la
                # Transfiguración, la Exaltación de la Cruz…). También eso lo
                # dice la medida: unos mismos salmos todos los años, cayendo
                # el día en semanas distintas del salterio, y que no son los
                # de ninguna semana. Se guarda la salmodia entera, que de
                # ella saca la app los salmos y les pone estas antífonas.
                hu, _ = enteras[(ants, sal)].most_common(1)[0]
                entrada['salmodia'] = textos[hu]
                entrada['salmos_testigos'] = ns
                entrada['salmos_titulos'] = list(sal)
        antifonas_libro[k] = entrada
    print(f'{len(antifonas_libro)} casillas con antífonas propias '
          f'({len(dudosas)} descartadas)', flush=True)

    # Lo que es del día no es propio, aunque lo diga un día que celebra. No
    # basta con el texto que el hueco ferial tiene por canónico: la fuente
    # reza a veces el otro himno del día, o la lectura del otro año del ciclo
    # bienal, y eso salía como propio del santo. Y hay tres cosas que el
    # libro no toma nunca del santo ni del común, porque son del día:
    #  · las Completas, salvo en las solemnidades, que llevan las del domingo
    #    («Completas: todo del salterio», Ordinario);
    #  · el himno de la Hora intermedia, que «se escoge según la Hora que se
    #    celebra, y el Tiempo litúrgico apropiado» (Ordinario), también en
    #    las fiestas. El del común de apóstoles era «Al Señor confesamos,
    #    ¡aleluya!» —el de Tercia en Pascua— y salía en Santiago y en san
    #    Bartolomé;
    #  · la salmodia del salterio. Un día que celebra sin decir su semana del
    #    salterio no tiene hueco de salterio, y lo que rezó ese año —los
    #    salmos de la feria con sus antífonas, el miércoles que tocara— se
    #    tomaba por propio: el común de apóstoles tenía en Tercia la
    #    complementaria de Pascua, y el de la Virgen, en Laudes, el salmo 50
    #    del viernes. Se reconoce porque todas sus antífonas son del salterio.
    textos_del_hueco = defaultdict(set)
    for k, v in tiempo_libro.items():
        for ls in [v['lineas']] + [x['lineas'] for x in v.get('variantes', [])]:
            textos_del_hueco[k].add(texto_de(ls))
    # sólo el texto canónico de cada casilla: entre las variantes del
    # salterio están las salmodias propias de las fiestas que declararon su
    # semana, y con ellas las antífonas de los apóstoles pasaban por feriales
    # Y sin el de Navidad: después de la Epifanía y en los días de la octava
    # el salterio repite las antífonas de la Epifanía y de la octava («El
    # misterio, escondido desde el comienzo de los siglos», «José y María, la
    # madre de Jesús, estaban maravillados»), y con ellas la Epifanía y Santa
    # María, Madre de Dios, se quedaban sin su Hora intermedia.
    ants_del_salterio = set()
    for k, v in salterio_libro.items():
        if not k.startswith('Navidad/'):
            ants_del_salterio.update(clave(a)
                                     for a in antifonas_de(v['lineas']))
    himnos_del_dia = set()
    for k, v in tiempo_libro.items():
        p = k.split('/')
        if p[-1] == 'himno' and p[-2] in INTERMEDIAS:
            for ls in [v['lineas']] + [x['lineas']
                                       for x in v.get('variantes', [])]:
                himnos_del_dia.add(incipit(ls))
    himnos_del_dia.discard('')

    candidatos = []
    for kf, cel, comun, rango, hora_cl, cl, hu, rot, testigo in propios:
        if hu in textos_del_hueco.get(kf, ()):
            cuentas['del santo pero ferial'] += 1
            continue
        if hora_cl == 'completas' and rango not in ('SOLEMNIDAD',
                                                    'CONMEMORACIÓN'):
            cuentas['del santo pero ferial: completas'] += 1
            continue
        # «En la Hora intermedia nunca se hace mención de las memorias de
        # los santos» (Ordinario): lo que la fuente rezó en ellas es la feria
        # —la oración de Tercia del salterio salía como del común de un
        # mártir—
        if hora_cl in INTERMEDIAS and rango in ('MEMORIA', 'MEMORIA LIBRE'):
            cuentas['del santo pero ferial: Hora intermedia de una '
                    'memoria'] += 1
            continue
        if (hora_cl in INTERMEDIAS and cl == 'himno'
                and incipit(textos[hu]) in himnos_del_dia):
            cuentas['del santo pero ferial: himno de la Hora intermedia'] += 1
            continue
        if cl == 'salmodia':
            ants = antifonas_de(textos[hu])
            if ants and all(clave(a) in ants_del_salterio for a in ants):
                cuentas['del santo pero ferial: salmodia del salterio'] += 1
                continue
        candidatos.append((cel, comun, rango, hora_cl, cl, hu, rot, testigo))
        cuentas['propio de la celebración'] += 1

    # --------------------------------------------------------- tercera pasada
    # de lo propio, lo que sale con dos santos distintos del mismo común,
    # es del común. Antes se juntan los comunes que sólo difieren en una
    # errata de la cabecera, que si no se repartían los testigos.
    canon = unifica_comunes(Counter(c[1] for c in candidatos if c[1]))
    candidatos = [(cel, canon.get(comun, comun), *resto)
                  for cel, comun, *resto in candidatos]
    juntados = sorted((m, n) for m, n in canon.items() if m != n)

    por_comun = defaultdict(lambda: defaultdict(set))
    for cel, comun, _, hora_cl, cl, hu, _, _ in candidatos:
        # las Completas que quedan son de solemnidades, y son las del
        # domingo: de ningún común
        if comun and hora_cl != 'completas':
            por_comun[f'{comun}/{hora_cl}/{cl}'][hu].add(clave(cel))

    del_comun = {k: {h for h, s in hs.items() if len(s) > 1}
                 for k, hs in por_comun.items()}

    comunes = defaultdict(lambda: defaultdict(list))
    santoral = defaultdict(lambda: defaultdict(list))
    rot_texto = defaultdict(Counter)
    for cel, comun, rango, hora_cl, cl, hu, rot, testigo in candidatos:
        kc = f'{comun}/{hora_cl}/{cl}' if comun else None
        if kc and hu in del_comun.get(kc, ()):
            # con quién se rezó, para saber si una forma pascual se escapa
            comunes[kc][hu].append(dict(testigo, s=clave(cel)))
            if rot:
                rotulos['com:' + kc][rot] += 1
                rot_texto[(kc, hu)][rot] += 1
            cuentas['a los comunes'] += 1
        else:
            k = f"{testigo['f'][5:]}/{clave(cel)}/{hora_cl}/{cl}"
            santoral[k][hu].append(testigo)
            if rot:
                rotulos['san:' + k][rot] += 1
                rot_texto[(k, hu)][rot] += 1
            cuentas['al santoral'] += 1

    # Lo que el santoral sólo tiene de un año, cuando la celebración se rezó
    # tres o más, no es suyo: los otros años dijeron otra cosa (su común, la
    # feria) y éste es un resto. El 13 de junio de 2020 la fuente puso en las
    # vísperas de san Antonio de Padua las primeras del Corpus, y como lo
    # suyo de los otros siete años es del común, aquello quedaba solo en el
    # santoral y, siendo «propio», tapaba al común todos los años.
    anios = defaultdict(set)
    for kf, cel, comun, rango, hora_cl, cl, hu, rot, testigo in propios:
        anios[f"{testigo['f'][5:]}/{clave(cel)}/{hora_cl}/{cl}"].add(
            testigo['f'][:4])
    sueltos = sorted(k for k, cuenta in santoral.items()
                     if max(len(ts) for ts in cuenta.values()) == 1
                     and len(anios[k]) >= 3)
    for k in sueltos:
        del santoral[k]
    cuentas['al santoral, pero de un año solo entre tres o más '
            '(fuera)'] += len(sueltos)

    comunes_libro, var_c = decide(
        comunes, textos, {k[4:]: v for k, v in rotulos.items()
                          if k.startswith('com:')}, rot_texto, True)
    santoral_libro, var_n = decide(
        santoral, textos, {k[4:]: v for k, v in rotulos.items()
                           if k.startswith('san:')}, rot_texto, True)

    # ------------------------------------------------------------- se escribe
    libros = [('ordinario', ordinario_libro, var_o),
              ('salterio', salterio_libro, var_s),
              ('tiempo', tiempo_libro, var_t),
              ('santoral', santoral_libro, var_n),
              ('comunes', comunes_libro, var_c)]
    lineas_qa = []
    for nombre, datos, var in libros:
        ruta = os.path.join(LIBRO, nombre + '.json')
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, separators=(',', ':'))
        mb = os.path.getsize(ruta) / 1e6
        pc = 100 * var / len(datos) if datos else 0
        lineas_qa.append(f'{nombre:10s} {len(datos):6d} casillas  {mb:6.1f} MB  '
                         f'con variantes: {var} ({pc:.0f} %)')
        if nombre in ('santoral', 'comunes'):
            np = sum(1 for v in datos.values() if 'pascua' in v)
            ns = sum(1 for v in datos.values() if v.get('solo_pascua'))
            lineas_qa[-1] += (f'\n           {np} con forma propia de Pascua, '
                              f'{ns} atestiguadas sólo en Pascua')
        print(lineas_qa[-1], flush=True)
    if juntados:
        lineas_qa.append('comunes que sólo diferían en una errata de la '
                         'cabecera: ' + '; '.join(f'«{m}» -> «{n}»'
                                                  for m, n in juntados))
        print(lineas_qa[-1], flush=True)

    # El ciclo de dos años: de cada hueco, el texto de cada año, por mayoría
    # dentro de ese año. Sólo se guardan los huecos en que los años difieren.
    bienal_libro = {}
    for kf, por_anio in sorted(bienal.items()):
        elegido = {a: c.most_common(1)[0] for a, c in por_anio.items()}
        if len(elegido) < 2 or len({h for h, _ in elegido.values()}) < 2:
            continue
        bienal_libro[kf] = {a: {
            'rotulo': (rotulos_bienal[(kf, hu)].most_common(1)[0][0]
                       if rotulos_bienal[(kf, hu)] else None),
            'lineas': textos[hu],
            'testigos': n,
        } for a, (hu, n) in sorted(elegido.items())}
    with open(os.path.join(LIBRO, 'bienal.json'), 'w', encoding='utf-8') as f:
        json.dump(bienal_libro, f, ensure_ascii=False, separators=(',', ':'))
    lineas_qa.append(f'bienal     {len(bienal_libro):6d} casillas  (lectura '
                     f'bíblica del Oficio, distinta en los años I y II)')
    print(lineas_qa[-1], flush=True)

    # El ciclo dominical: las antífonas del Benedictus y del Magníficat del
    # domingo salen de su evangelio, y el evangelio cambia con el ciclo A, B
    # o C. La mayoría de todos los años se quedaba con la de uno solo y la
    # sacaba en los otros dos: el domingo XI del ordinario daba siempre
    # «Mujer, quedan perdonados tus pecados», que es del año C. Se decide por
    # mayoría dentro de cada ciclo, como el ciclo bienal, en los domingos, en
    # las vísperas del sábado (que son las primeras del domingo) y en los
    # días sin semana (la Sagrada Familia, el Bautismo…). Sólo se guarda lo
    # que de verdad cambia: dos antífonas distintas por lo menos.
    def antifona_de(lineas):
        for ln in lineas:
            if ln and ln[0][0] and ABRE_ANT.match(ln[0][1]):
                return clave(''.join(t for rojo, t in ln if not rojo))
        return ''
    # Un ciclo con un solo testigo puede ser un resto de otro día: el sábado
    # de la semana VII que fue víspera de la Trinidad trajo «Gracias a ti,
    # Señor Dios, Trinidad». Se reconoce porque esa antífona es la de otra
    # casilla del libro.
    ant_de_otra = defaultdict(set)
    for k, v in tiempo_libro.items():
        if k.endswith('/cantico_evangelico'):
            ant_de_otra[antifona_de(v['lineas'])].add(k)
    ciclo_libro = {}
    for kf, cuenta in sorted(ferial.items()):
        p = kf.split('/')
        if p[-1] != 'cantico_evangelico' or p[-2] not in ('laudes', 'visperas'):
            continue
        if not (p[1] == '@' or p[2] == '0'
                or (p[2] == '6' and p[-2] == 'visperas')):
            continue
        por_ciclo = defaultdict(Counter)
        for hu, ts in cuenta.items():
            for t in ts:
                por_ciclo[t['c']][hu] += 1
        # el empate, por los testigos de todos los años, y luego por el texto
        elegido = {c: max(cnt.items(),
                          key=lambda x: (x[1], len(cuenta[x[0]]), x[0]))
                   for c, cnt in por_ciclo.items()}
        elegido = {c: (hu, n) for c, (hu, n) in elegido.items()
                   if n > 1 or not (ant_de_otra.get(antifona_de(textos[hu]),
                                                    set()) - {kf})}
        ants = {antifona_de(textos[hu]) for hu, _ in elegido.values()}
        if len({' '.join(a.split()[:5]) for a in ants}) < 2:
            continue
        ciclo_libro[kf] = {c: {
            'rotulo': (rotulos['tie:' + kf].most_common(1)[0][0]
                       if rotulos['tie:' + kf] else None),
            'lineas': textos[hu],
            'testigos': n,
        } for c, (hu, n) in sorted(elegido.items())}
    with open(os.path.join(LIBRO, 'ciclo.json'), 'w', encoding='utf-8') as f:
        json.dump(ciclo_libro, f, ensure_ascii=False, separators=(',', ':'))
    lineas_qa.append(f'ciclo      {len(ciclo_libro):6d} casillas  (antífona '
                     f'evangélica del domingo, distinta en los ciclos A, B y C)')
    print(lineas_qa[-1], flush=True)

    with open(os.path.join(LIBRO, 'antifonas.json'), 'w', encoding='utf-8') as f:
        json.dump(antifonas_libro, f, ensure_ascii=False, indent=1)
    lineas_qa.append(f'antifonas  {len(antifonas_libro):6d} casillas  (las '
                     f'propias de una celebración, sobre los salmos del día; '
                     f'{len(dudosas)} descartadas)')
    print(lineas_qa[-1], flush=True)

    with open(os.path.join(LIBRO, 'resenas.json'), 'w', encoding='utf-8') as f:
        json.dump({k: c.most_common(1)[0][0] for k, c in sorted(resenas.items())},
                  f, ensure_ascii=False, indent=1)

    with open(os.path.join(LIBRO, 'santoral_indice.json'), 'w',
              encoding='utf-8') as f:
        json.dump({d: c.most_common() for d, c in sorted(santos.items())},
                  f, ensure_ascii=False, indent=1)

    # Cómo se clasificó cada uno de los días del volcado. Es la piedra de
    # toque de la fase 4: comparando estas fechas con las del calendario
    # del proyecto se aprende la correspondencia entre los nombres que da
    # la fuente a los días señalados y los que les da el leccionario, sin
    # tener que tabularla a mano.
    with open(os.path.join(LIBRO, 'dias_fuente.json'), 'w',
              encoding='utf-8') as f:
        json.dump(cabeceras, f, ensure_ascii=False, indent=1)

    # En qué orden van las secciones de cada hora. El libro guarda cada
    # pieza por separado y pierde el orden en que se rezan; se recupera
    # aquí tomando la secuencia que más días repiten, que es la del oficio
    # corriente. Promediar posiciones no vale: los días irregulares —la
    # Vigilia pascual, un oficio con dos lecturas de más— arrastran la
    # media y acaban colando la conclusión antes del final. Lo que esos
    # días traen de más se añade detrás, para no perderlo.
    orden = {}
    for hora_cl, secs in secuencias.items():
        comun_ = list(secs.most_common(1)[0][0])
        extra = [k for seq in secs for k in seq if k not in comun_]
        orden[hora_cl] = comun_ + sorted(set(extra))
    with open(os.path.join(LIBRO, 'orden.json'), 'w', encoding='utf-8') as f:
        json.dump(orden, f, ensure_ascii=False, indent=1)

    with open(QA, 'w', encoding='utf-8') as f:
        f.write('Fase 3 — el libro: tiempos, salterio, santoral, comunes\n')
        f.write('=' * 62 + '\n\n')
        f.write(f'Días leídos: {dias_vistos}\n')
        f.write(f'Textos distintos: {len(textos)}\n\n')
        f.write('\n'.join(lineas_qa) + '\n\n')
        f.write('Cómo se repartieron las secciones\n' + '-' * 44 + '\n')
        for k, v in sorted(cuentas.items()):
            f.write(f'{v:8d}  {k}\n')
        f.write(f'\nDías del año con celebración: {len(santos)}\n')
        if avisos:
            f.write(f'\nAvisos: {len(avisos)}\n' + '-' * 44 + '\n')
            for a in avisos[:300]:
                f.write(a + '\n')
    print(f'\nQA en {QA}')


if __name__ == '__main__':
    main()
