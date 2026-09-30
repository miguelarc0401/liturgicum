# -*- coding: utf-8 -*-
"""Fase 4 — el libro de horas, empaquetado para la app.

La app no vuelve a resolver nada: ésa es la regla del proyecto, y aquí se
respeta. Este módulo deja dos ficheros en `app/datos/`:

    horas.json        el libro entero, sin las variantes (que son el
                      aparato crítico y viven en Breviarium/datos/libro/)
    horas_dias.json   fecha civil -> coordenadas del oficio de ese día

El segundo es el que hace el trabajo. Para las fechas del volcado
(2019-2026) sale de la propia fuente, exacta. Para las demás —el
calendario del leccionario llega a 2060— se deriva: el tiempo y la semana,
del calendario del proyecto; el día de la semana, de la fecha; el salterio,
de la semana; y el santo, del santoral, que es de fecha fija.

Los días señalados —el Triduo, la Navidad, la Epifanía— no se numeran por
semana, y la fuente y el leccionario les dan nombres distintos. La
correspondencia no se tabula a mano: se **aprende** de los años en que los
dos calendarios se solapan, que es para lo que la fase 3 dejó
`dias_fuente.json`.

    python Breviarium/src/4_app.py
"""

import datetime as dt
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

    # --- el santoral, por fecha fija --------------------------------------
    # Cuando en una fecha se ha celebrado más de una cosa a lo largo de los
    # ocho años (los días que ofrecen oficios alternativos), manda el que
    # más veces salió.
    indice_santos = carga('santoral_indice.json')
    santo_de_fecha = {}
    for md, lista in indice_santos.items():
        casillas = {k.split('/', 2)[1] for k in santoral
                    if k.startswith(md + '/')}
        for nombre, _ in lista:
            if clave(nombre) in casillas:
                santo_de_fecha[md] = (clave(nombre), nombre)
                break

    # el rango con que se celebra cada santo, para poder decirlo y para
    # poder saltárselo cuando es memoria libre y así lo prefiera quien reza
    rango_voto = defaultdict(Counter)
    for cab in fuente.values():
        if cab.get('celebracion') and cab.get('rango'):
            rango_voto[clave(cab['celebracion'])][cab['rango']] += 1
    rango_de_santo = {k: c.most_common(1)[0][0] for k, c in rango_voto.items()}

    # --- de qué común toma su oficio cada santo ---------------------------
    # La app arma el día en cascada —lo del santo, si no lo de su común, si
    # no lo del tiempo— y para el segundo escalón necesita saber cuál es el
    # común de cada santo. Lo dice el propio volcado, en la línea que
    # encabeza el día («Del Común de pastores. Salterio III»).
    comun_voto = defaultdict(Counter)
    for cab in fuente.values():
        cel, origen = cab.get('celebracion'), cab.get('origen') or ''
        m = re.search(r'com[uú]n\s+(?:de\s+)?(?:l[oa]s?\s+)?(.+)$', origen, re.I)
        if cel and m:
            comun_voto[clave(cel)][clave(m.group(1))] += 1
    comun_de_santo = {s: c.most_common(1)[0][0] for s, c in comun_voto.items()}

    # --- fecha -> coordenadas ---------------------------------------------
    dias, cuentas, avisos = {}, Counter(), []
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

        reg = {'t': ti, 'k': clave_dia, 'd': ds, 'tt': meta.get('t')}
        if salt:
            reg['p'] = salt

        # el santo: de fecha fija, y sólo si el día lo admite
        md = fecha[5:]
        if cab and cab.get('celebracion'):
            reg['s'] = clave(cab['celebracion'])
            reg['st'] = cab['celebracion']
            reg['g'] = cab.get('rango')
            cuentas['con santo (del volcado)'] += 1
        elif md in santo_de_fecha:
            reg['s'], reg['st'] = santo_de_fecha[md]
            reg['g'] = rango_de_santo.get(reg['s'])
            cuentas['con santo (por fecha fija)'] += 1

        dias[fecha] = reg

    # --- se escribe --------------------------------------------------------
    libro = {
        'orden': carga('orden.json'),
        'comun_de': comun_de_santo,
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
        f.write('\nCómo se resolvió cada fecha\n' + '-' * 44 + '\n')
        for k, v in sorted(cuentas.items()):
            f.write(f'{v:8d}  {k}\n')
        f.write('\nDías del leccionario cuyas coordenadas se aprendieron '
                f'del volcado: {len(aprendido)}\n')
        if avisos:
            f.write(f'\nAvisos: {len(avisos)}\n' + '-' * 44 + '\n')
            for a in avisos[:200]:
                f.write(a + '\n')
    print(f'\nQA en {QA}')


if __name__ == '__main__':
    main()
