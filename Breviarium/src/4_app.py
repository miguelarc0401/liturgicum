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


def carga(nombre, base=LIBRO):
    ruta = os.path.join(base, nombre)
    if not os.path.exists(ruta):
        sys.exit(f'falta {ruta}: ¿se corrió la fase anterior?')
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)


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
    crc = zlib.crc32(b''.join(
        open(os.path.join(APP, f), 'rb').read()
        for f in sorted(os.listdir(APP)) if f != 'version.js')) & 0xffffffff
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
        if not cel or clave(cel) not in casillas or not ent:
            continue
        p, e = max(((parecido(e[2]['t'], cel), e) for e in ent),
                   key=lambda x: x[0])
        if p >= 0.5:
            votos[e[0]][clave(cel)] += 1
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
            comun_voto[clave(cel)][clave(m.group(1))] += 1
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
        'santoral': poda(santoral),
        'comunes': poda(comunes),
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


if __name__ == '__main__':
    main()
