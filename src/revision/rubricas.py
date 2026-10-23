# -*- coding: utf-8 -*-
"""La Liturgia de las Horas de un año, contra las rúbricas.

    python src/revision/rubricas.py                      # de hoy a un año
    python src/revision/rubricas.py 2026-10-21 2027-10-21

`horas.py` coteja con lo que la fuente rezó otros años, y eso no basta: el
calendario de este año no es el de hace tres —las fechas caen en otro día de
la semana, las solemnidades se trasladan—, y la fuente sigue el calendario
argentino, no el de México. Esto mira cada día con las normas, sin la fuente:

  · vísperas: cuándo son las primeras del día siguiente (domingo o
    solemnidad que lo supera en la Tabla de los días litúrgicos; PNLH 61) y
    si los textos son de la celebración que toca;
  · Completas: las del domingo I tras las primeras vísperas, las del domingo
    II tras las segundas, y las del día de la semana los demás días
    (PNLH 88);
  · el Te Deum: domingos fuera de Cuaresma, solemnidades, fiestas y las
    octavas de Pascua y Navidad, y nunca en ferias ni memorias (PNLH 68);
  · nada de «aleluya» en Cuaresma, ni en la invocación;
  · las memorias en días privilegiados (Cuaresma, del 17 al 24 de diciembre,
    la octava de Navidad) son conmemoración (PNLH 238-239);
  · la Hora intermedia de las solemnidades entre semana, con la salmodia
    complementaria (Ordinario);
  · la semana del salterio, y Santa María en sábado;
  · el grado: que una fiesta no tome «del día» lo que es del propio o del
    común, y que una memoria tenga su lectura hagiográfica y su oración
    (PNLH 134-135, 234-235).

Escribe `Breviarium/datos/rubricas_qa.txt`.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESDE = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
HASTA = sys.argv[2] if len(sys.argv) > 2 else (
    date.fromisoformat(DESDE) + timedelta(days=364)).isoformat()

FUERTES = ('Adviento', 'Cuaresma', 'Pascua')
COMPLEMENTARIA = {'tercia': {119, 120, 121}, 'sexta': {122, 123, 124},
                  'nona': {125, 126, 127}}
# el primer salmo de las Completas de cada día (domingo I, el del sábado)
COMPLETAS = {0: 90, 1: 85, 2: 142, 3: 30, 4: 15, 5: 87, 6: 4}


def suma(iso, n):
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def arma():
    salida = os.path.join(tempfile.mkdtemp(prefix='rubricas-'), 'armado.json')
    # un día antes y uno después, para las vísperas y las Completas
    subprocess.run(['node', os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'arma.js'), RAIZ, suma(DESDE, -1),
        suma(HASTA, 1), salida], check=True)
    with open(salida, encoding='utf-8') as f:
        return json.load(f)


A = arma()
TEXTOS, DIAS = A['textos'], A['dias']
with open(os.path.join(RAIZ, 'app', 'datos', 'calendario.json'),
          encoding='utf-8') as f:
    CAL = json.load(f)
PASCUA = {int(a): m['pascua'] for a, m in CAL['anios'].items()}


def pascua_de(iso):
    return PASCUA[int(iso[:4])]


def ceniza(iso):
    return suma(pascua_de(iso), -46)


def en_cuaresma(iso):
    """Del miércoles de Ceniza a la Vigilia: sin aleluya."""
    return ceniza(iso) <= iso < pascua_de(iso)


def triduo(iso):
    return suma(pascua_de(iso), -3) <= iso < pascua_de(iso)


def octava_pascua(iso):
    return pascua_de(iso) <= iso <= suma(pascua_de(iso), 7)


def octava_navidad(iso):
    return iso[5:] >= '12-25' or iso[5:] == '01-01'


def opcion(iso, hora, cual=None):
    """La celebración de esa hora: la que la app pone por omisión."""
    ops = (DIAS.get(iso) or {}).get('horas', {}).get(hora) or []
    return next((o for o in ops if (o['op'] == cual if cual else o['def'])),
                None)


def texto(op, cl):
    s = next((s for s in (op or {}).get('secs', []) if s['cl'] == cl), None)
    if not s or not s['alts']:
        return ''
    k = s['alts'][s['i']][2]
    if k < 0:
        return ''
    return re.sub(r'\s+', ' ', ' '.join(
        ''.join(t for _, t in ln) for ln in TEXTOS[k]['l'])).strip()


def oracion(op, cl='oracion'):
    """La oración, sin el «OREMOS» ni la conclusión: lo que la identifica."""
    t = re.sub(r'^OREMOS,?\s*', '', texto(op, cl), flags=re.I)
    return t[:80]


def salmos(op):
    return [int(n) for n in re.findall(r'\bSalmo (\d+)', texto(op, 'salmodia'))]


def rango(iso):
    """El número de la Tabla de lo que se celebra ese día (menor manda)."""
    e = (DIAS.get(iso) or {}).get('d') or {}
    op = opcion(iso, 'laudes')
    rs = []
    for c in e.get('c') or []:
        if op and op['op'] == c[0] and op['modo'] != 'conmemoracion':
            rs.append(c[4] or 12)
    if triduo(iso):
        rs.append(1)
    if iso[5:] == '12-25':
        rs.append(2)
    if e.get('d') == 0:
        rs.append(2 if e.get('t') in FUERTES else 6)
    if octava_pascua(iso) or iso == ceniza(iso) or (
            suma(pascua_de(iso), -7) < iso < pascua_de(iso)):
        rs.append(2)
    if e.get('t') == 'Cuaresma' or e.get('kf') or octava_navidad(iso):
        rs.append(9)
    rs.append(13)
    return min(rs)


def solemne(iso):
    """Solemnidad: la del santoral o la del tiempo (Navidad)."""
    e = (DIAS.get(iso) or {}).get('d') or {}
    op = opcion(iso, 'laudes')
    return iso[5:] == '12-25' or bool(op and op['g'] == 'SOLEMNIDAD')


def tiene_primeras(iso):
    e = (DIAS.get(iso) or {}).get('d') or {}
    return e.get('d') == 0 or solemne(iso)


def son_primeras(iso):
    man = suma(iso, 1)
    if triduo(iso) or triduo(man):
        return False
    # el sábado de la octava de Pascua: las primeras del domingo II, aunque
    # los dos días sean del n. 2
    if octava_pascua(iso) and (DIAS.get(man) or {}).get('d', {}).get('d') == 0:
        return True
    return tiene_primeras(man) and rango(man) < rango(iso)


GRADO_FIESTA = {
    'oficio': ['invitatorio', 'himno', 'salmodia', 'lectura1', 'responsorio',
               'lectura2', 'responsorio2', 'oracion'],
    'laudes': ['invitatorio', 'himno', 'salmodia', 'lectura_breve',
               'responsorio_breve', 'cantico_evangelico', 'preces', 'oracion'],
    'tercia': ['lectura_breve', 'oracion'], 'sexta': ['lectura_breve', 'oracion'],
    'nona': ['lectura_breve', 'oracion'],
    'visperas': ['himno', 'salmodia', 'lectura_breve', 'responsorio_breve',
                 'cantico_evangelico', 'preces', 'oracion'],
}
GRADO_MEMORIA = ('lectura2', 'responsorio2', 'oracion')
ELIGE_MEMORIA = ('lectura_breve', 'cantico_evangelico', 'preces')


def elegidas(op, cl):
    """Los ids de las opciones de una sección (el invitatorio está dentro
    del comienzo de la hora), o None si la hora no la tiene."""
    for s in op.get('secs', []):
        if s['cl'] == cl:
            return [a[0] for a in s['alts']]
        if cl == 'invitatorio' and s.get('formas', {}).get('invitatorio'):
            return [a[0] for a in s['formas']['invitatorio']['alts']]
    return None


hallazgos = defaultdict(list)
cuenta = Counter()
d0 = date.fromisoformat(DESDE)
while d0 <= date.fromisoformat(HASTA):
    iso = d0.isoformat()
    d0 += timedelta(days=1)
    dia = DIAS.get(iso)
    if not dia or not dia.get('d'):
        hallazgos['sin día'].append(iso)
        continue
    e = dia['d']
    man = suma(iso, 1)
    tit = e.get('tt', '')

    # --- vísperas: ¿las de quién? ---------------------------------------
    vis = opcion(iso, 'visperas')
    if vis and not triduo(iso):
        cuenta['vísperas'] += 1
        primeras = son_primeras(iso)
        dice = (vis.get('vis') or {})
        app_primeras = dice.get('n') == 1 and dice.get('iso') == man
        if primeras != app_primeras:
            hallazgos['vísperas: la app no decide como la Tabla'].append(
                f'{iso} {tit} — tocan {"las primeras de mañana" if primeras else "las de hoy"}'
                f', la app dice {dice or "vísperas sin más"}')
        # los textos: la oración de vísperas ha de ser la de Laudes de la
        # celebración que toca, si es domingo, solemnidad o fiesta
        dueno = man if primeras else iso
        lau = opcion(dueno, 'laudes')
        celebra = (rango(dueno) <= 8 or (DIAS[dueno]['d'].get('d') == 0))
        # en la octava de Navidad, las vísperas de san Esteban, san Juan y los
        # Inocentes son de la octava; y las primeras vísperas de las
        # solemnidades con misa de vigilia llevan la oración de la vigilia
        # (Navidad tiene en Laudes la oración de la misa de la aurora y en
        # Vísperas la de la misa del día)
        if '12-25' <= dueno[5:] <= '12-28':
            celebra = False
        vigilia = primeras and (dueno[5:] in ('06-24', '06-29', '08-15')
                                or 'pentecost' in (DIAS[dueno]['d'].get('k') or ''))
        if celebra and not vigilia and lau and oracion(vis) and oracion(lau) and \
                oracion(vis) != oracion(lau):
            hallazgos['vísperas: la oración no es la de la celebración'].append(
                f'{iso} {tit} → {"primeras de " + DIAS[man]["d"].get("tt", "") if primeras else "de hoy"}'
                f'\n      vísperas: {oracion(vis)}\n      laudes:   {oracion(lau)}')

    # --- Completas -----------------------------------------------------
    com = opcion(iso, 'completas')
    if com:
        cuenta['completas'] += 1
        ss = salmos(com)
        if son_primeras(iso):
            quiere = {4}
        elif e.get('d') == 0 or solemne(iso):
            quiere = {90}
        else:
            quiere = {COMPLETAS[e.get('d')]}
        if octava_pascua(iso) or octava_navidad(iso):
            quiere = {4, 90}
        if triduo(iso):                   # del domingo, tras las II Vísperas
            quiere = {90}
        # y su oración: tras las segundas vísperas del domingo, «Humildemente
        # te pedimos…»; tras las de una solemnidad entre semana, «Visita,
        # Señor, esta habitación…» (Completas del domingo II, en el tomo)
        o = oracion(com)
        if 90 in quiere and len(quiere) == 1 and not triduo(iso):
            pide = 'Humildemente' if e.get('d') == 0 else 'Visita, Señor'
            if not o.startswith(pide):
                hallazgos['completas: la oración no es la que toca'].append(
                    f'{iso} {tit} — «{o[:50]}…», tocaba «{pide}…»')
        if not ss:
            hallazgos['completas sin salmodia'].append(f'{iso} {tit}')
        elif ss[0] not in quiere:
            hallazgos['completas: no son las que tocan'].append(
                f'{iso} {tit} — empieza por el salmo {ss[0]}, tocaba '
                + ' o '.join(str(q) for q in sorted(quiere)))

    # --- Te Deum -------------------------------------------------------
    of = opcion(iso, 'oficio')
    if of and not triduo(iso):
        cuenta['oficio'] += 1
        hay = any('alegres te cantamos' in texto(of, s['cl']).lower()
                  for s in of['secs'])
        domingo = e.get('d') == 0
        quiere = ((domingo and e.get('t') != 'Cuaresma')
                  or (of['modo'] == 'entero' and of['g'] in ('SOLEMNIDAD', 'FIESTA'))
                  or (of['modo'] == 'feria' and (octava_pascua(iso)
                                                 or octava_navidad(iso))))
        if domingo and e.get('t') == 'Cuaresma':
            quiere = False
        if hay != quiere:
            hallazgos['Te Deum'].append(
                f'{iso} {tit} [{of["t"][:40]}] — {"sobra" if hay else "falta"}')

    # --- aleluya en Cuaresma -------------------------------------------
    if en_cuaresma(iso) and not triduo(iso):
        for h in ('oficio', 'laudes', 'tercia', 'sexta', 'nona', 'visperas',
                  'completas'):
            op = opcion(iso, h)
            for s in (op or {}).get('secs', []):
                t = texto(op, s['cl'])
                if re.search(r'\baleluya\b', t, re.I):
                    hallazgos['aleluya en Cuaresma'].append(
                        f'{iso} {h} {s["cl"]} — …{t[max(0, t.lower().find("aleluya") - 50):t.lower().find("aleluya") + 10]}')

    # --- memorias en días privilegiados -----------------------------------
    privilegiado = ((e.get('t') == 'Cuaresma' and e.get('d') != 0)
                    or ('12-17' <= iso[5:] <= '12-24')
                    or ('12-29' <= iso[5:] <= '12-31'))
    for c in e.get('c') or []:
        if c[3].startswith('MEMORIA') and privilegiado and not e.get('cm'):
            hallazgos['memoria en día privilegiado sin conmemoración'].append(
                f'{iso} {tit} — {c[2]}')

    # --- la Hora intermedia de las solemnidades ---------------------------
    for h in ('tercia', 'sexta', 'nona'):
        op = opcion(iso, h)
        if not op or op['g'] != 'SOLEMNIDAD' or e.get('d') == 0:
            continue
        cuenta['intermedia de solemnidad'] += 1
        ss = set(salmos(op))
        if ss and not ss <= COMPLEMENTARIA[h] and ss & {117, 118}:
            hallazgos['intermedia de solemnidad entre semana sin la complementaria'].append(
                f'{iso} {h} {op["t"][:45]} — salmos {sorted(ss)}')

    # --- semana del salterio --------------------------------------------
    m = re.fullmatch(r'(Ordinario|Adviento|Cuaresma|Pascua)/(\d+)/\d', e.get('k') or '')
    if m and not (m[1] == 'Pascua' and m[2] == '1'):
        quiere = (int(m[2]) - 1) % 4 + 1
        if e.get('p') != quiere:
            hallazgos['semana del salterio'].append(
                f'{iso} {tit} — p={e.get("p")}, toca {quiere}')

    # --- el grado: de dónde sale cada sección -----------------------------
    # Una fiesta lo toma todo de lo propio o del común, salvo la salmodia de
    # la Hora intermedia, que es la de la feria (lo dice el Propio de cada
    # fiesta); una memoria, la lectura hagiográfica, su responsorio y la
    # oración, y lo demás a elegir (PNLH 234-235). «Del día» donde no toca es
    # que al común le falta la pieza.
    for h, cls in GRADO_FIESTA.items():
        op = opcion(iso, h)
        if not op or op['modo'] == 'feria' or op['op'] == 'smv':
            continue
        vis = op.get('vis') or {}
        if h == 'visperas' and (vis.get('n') == 1 and vis.get('iso') == man
                                or e.get('v')):
            continue                  # son las primeras vísperas de mañana
        if op['modo'] == 'entero' and op['g'] in ('FIESTA', 'SOLEMNIDAD'):
            pide = cls
        elif op['modo'] == 'memoria' and h in ('oficio', 'laudes', 'visperas'):
            pide = [c for c in cls if c in GRADO_MEMORIA]
        else:
            continue
        cuenta[f'secciones de {op["g"].lower()}'] += len(pide)
        for cl in pide:
            ids = elegidas(op, cl)
            if ids is None:
                hallazgos[f'{op["g"].lower()}: falta la sección'].append(
                    f'{iso} {h} {cl} — {op["t"]}')
            elif ids and all(i.startswith(('dia', 'sal-')) for i in ids):
                hallazgos[f'{op["g"].lower()}: del día donde toca lo propio '
                          f'o el común'].append(f'{iso} {h} {cl} — {op["t"]}')
        if op['modo'] == 'memoria':
            for cl in ELIGE_MEMORIA:
                ids = elegidas(op, cl)
                if ids and all(i.startswith('dia') for i in ids):
                    hallazgos['memoria: sin propio ni común que elegir'].append(
                        f'{iso} {h} {cl} — {op["t"]}')

    # --- Santa María en sábado ------------------------------------------
    lau = (dia.get('horas') or {}).get('laudes') or []
    ofrece = any(o['op'] == 'smv' for o in lau)
    quiere = (e.get('d') == 6 and e.get('t') == 'Ordinario' and not e.get('cm')
              and not any(not c[3].endswith('LIBRE') for c in e.get('c') or []))
    if ofrece != quiere:
        hallazgos['Santa María en sábado'].append(
            f'{iso} {tit} — {"se ofrece y no cabe" if ofrece else "cabe y no se ofrece"}')

ruta = os.path.join(RAIZ, 'Breviarium', 'datos', 'rubricas_qa.txt')
with open(ruta, 'w', encoding='utf-8') as f:
    f.write(f'Las horas del {DESDE} al {HASTA}, contra las rúbricas\n')
    f.write('=' * 60 + '\n\n')
    for k, n in cuenta.items():
        f.write(f'{n:6d}  {k} revisadas\n')
    f.write('\n')
    for k, v in hallazgos.items():
        f.write(f'{k}: {len(v)}\n' + '-' * 40 + '\n')
        for x in v:
            f.write(f'  {x}\n')
        f.write('\n')
for k, v in hallazgos.items():
    print(f'{len(v):5d}  {k}')
print('informe en', ruta)
