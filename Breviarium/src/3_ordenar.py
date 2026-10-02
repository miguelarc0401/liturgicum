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
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from breviario import CORPUS, clave

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
    """El ciclo dominical (A, B, C)."""
    return 'ABC'[anio % 3]


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
    """El común del que el día toma su oficio, si lo declara."""
    origen = (dia.get('origen') or '')
    m = re.search(r'com[uú]n\s+(?:de\s+)?(?:l[oa]s?\s+)?(.+)$', origen, re.I)
    return clave(m.group(1)) if m else None


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

def decide(casillas, textos, rotulos):
    """De cada casilla, el texto más atestiguado; los demás, variantes."""
    salida = {}
    con_variantes = 0
    for k, cuenta in casillas.items():
        orden = sorted(cuenta.items(),
                       key=lambda kv: (-len(kv[1]), kv[0]))
        h, testigos = orden[0]
        rot = rotulos.get(k)
        entrada = {
            'rotulo': rot.most_common(1)[0][0] if rot else None,
            'lineas': textos[h],
            'testigos': len(testigos),
            'desde': min(t['f'] for t in testigos),
        }
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
                    for sec in h['secciones']:
                        base = sec['clase']
                        n = repeticion[base]
                        repeticion[base] += 1
                        cl = base if n == 0 else f'{base}{n + 1}'
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
                                        (ks, ants, salmos_de(lineas)))
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
    for k, obs in sorted(antifonas.items()):
        propias, salmos = Counter(), defaultdict(Counter)
        for ks, ants, sal in obs:
            ferial = salterio_libro.get(ks)
            if ferial is None or antifonas_de(ferial['lineas']) == ants:
                continue
            propias[ants] += 1
            if sal:
                salmos[ants][sal] += 1
        if not propias:
            continue
        ants, n = propias.most_common(1)[0]
        if n < 2 or ants in del_salterio:
            dudosas.append(f'{k}: {n} de {len(obs)} años'
                           + (', son de otra semana del salterio'
                              if ants in del_salterio else ''))
            continue
        entrada = {'antifonas': list(ants), 'testigos': n, 'de': len(obs)}
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
        antifonas_libro[k] = entrada
    print(f'{len(antifonas_libro)} casillas con antífonas propias '
          f'({len(dudosas)} descartadas)', flush=True)

    candidatos = []
    for kf, cel, comun, rango, hora_cl, cl, hu, rot, testigo in propios:
        ferial_aqui = tiempo_libro.get(kf)
        igual = ferial_aqui and texto_de(ferial_aqui['lineas']) == hu
        if igual:
            cuentas['del santo pero ferial'] += 1
            continue
        candidatos.append((cel, comun, rango, hora_cl, cl, hu, rot, testigo))
        cuentas['propio de la celebración'] += 1

    # --------------------------------------------------------- tercera pasada
    # de lo propio, lo que sale con dos santos distintos del mismo común,
    # es del común
    por_comun = defaultdict(lambda: defaultdict(set))
    for cel, comun, _, hora_cl, cl, hu, _, _ in candidatos:
        if comun:
            por_comun[f'{comun}/{hora_cl}/{cl}'][hu].add(clave(cel))

    del_comun = {k: {h for h, s in hs.items() if len(s) > 1}
                 for k, hs in por_comun.items()}

    comunes = defaultdict(lambda: defaultdict(list))
    santoral = defaultdict(lambda: defaultdict(list))
    for cel, comun, rango, hora_cl, cl, hu, rot, testigo in candidatos:
        kc = f'{comun}/{hora_cl}/{cl}' if comun else None
        if kc and hu in del_comun.get(kc, ()):
            comunes[kc][hu].append(testigo)
            if rot:
                rotulos['com:' + kc][rot] += 1
            cuentas['a los comunes'] += 1
        else:
            k = f"{testigo['f'][5:]}/{clave(cel)}/{hora_cl}/{cl}"
            santoral[k][hu].append(testigo)
            if rot:
                rotulos['san:' + k][rot] += 1
            cuentas['al santoral'] += 1

    comunes_libro, var_c = decide(
        comunes, textos, {k[4:]: v for k, v in rotulos.items()
                          if k.startswith('com:')})
    santoral_libro, var_n = decide(
        santoral, textos, {k[4:]: v for k, v in rotulos.items()
                           if k.startswith('san:')})

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
