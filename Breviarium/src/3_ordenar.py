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

RANGOS_PROPIOS = ('SOLEMNIDAD', 'FIESTA', 'MEMORIA', 'MEMORIA LIBRE')


# --------------------------------------------------------------------------
# el año litúrgico de una fecha
# --------------------------------------------------------------------------

def anio_liturgico(fecha, inicios):
    a = int(fecha[:4])
    ini = inicios.get(a)
    return a + 1 if (ini and fecha >= ini) else a


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
    santos = defaultdict(Counter)
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
                            continue

                        kf = hueco_ferial(of, hora_cl, cl)
                        if kf is None:
                            avisos.append(f'{fecha} {hora_cl}/{cl}: sin tiempo')
                            cuentas['sin_sitio'] += 1
                            continue

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
