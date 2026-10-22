# -*- coding: utf-8 -*-
"""La Liturgia de las Horas de un año, tal como la arma la app, contra la fuente.

    python src/revision/horas.py                      # de hoy a un año
    python src/revision/horas.py 2026-10-21 2027-10-20

Arma cada hora de cada fecha con el mismo app.js que corre en el teléfono
(`arma.js`, con node) y la revisa de dos maneras, sección por sección:

  1. de forma: que la sección diga lo que su nombre dice —una oración que
     acaba en su conclusión, una lectura con cuerpo, un responsorio con R. y
     V., una salmodia con antífonas y salmos…— y que la hora las tenga todas.
     Así salió, el 21 de octubre de 2026, la lectura de Habacuc en el sitio
     de la oración.
  2. de fuente: que el texto sea el que la fuente publicó en un día igual —el
     mismo día del tiempo, las mismas celebraciones con el mismo grado, el
     mismo año ferial para la lectura bíblica y el mismo ciclo para las
     antífonas del domingo— de 2019 a hoy. La fuente no sigue siempre el
     calendario de México (celebra la Epifanía el 6, Nuestra Señora de
     Itatí…): un día suyo sólo atestigua si reza lo que la app pone ese día.
     Las primeras vísperas se cotejan con las del día al que pertenecen.

Escribe `Breviarium/datos/revision_qa.txt`. Lo que sale «distinto» no es
siempre un error —la fuente se equivoca a veces, y la app elige por omisión
cosas que la fuente no (la salmodia complementaria en Tercia y Nona)—, pero
es por donde hay que mirar.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta

raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
desde = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
hasta = sys.argv[2] if len(sys.argv) > 2 else (
    date.fromisoformat(desde) + timedelta(days=364)).isoformat()
armado = os.path.join(tempfile.mkdtemp(prefix='revision-'), 'armado.json')
subprocess.run(['node', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'arma.js'), raiz, desde, hasta, armado],
               check=True)
sys.path.insert(0, os.path.join(raiz, 'Breviarium', 'src'))
from breviario import CORPUS, clave  # noqa: E402

A = json.load(open(armado, encoding='utf-8'))
TEXTOS = A['textos']
DIAS_APP = A['dias']
HD = json.load(open(os.path.join(raiz, 'app', 'datos', 'horas_dias.json'),
                    encoding='utf-8'))['dias']
CAL = json.load(open(os.path.join(raiz, 'app', 'datos', 'calendario.json'),
                     encoding='utf-8'))
ANIOS = sorted(((m['inicio'], m) for m in CAL['anios'].values()))


def anio_de(iso):
    hallado = None
    for ini, m in ANIOS:
        if ini <= iso:
            hallado = m
        else:
            break
    return hallado or {}


def suma(iso, n):
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


# ---------------------------------------------------------------- el texto
def llano(lineas):
    t = ' '.join(''.join(x for _, x in ln) for ln in (lineas or []))
    t = unicodedata.normalize('NFC', t.replace('\xa0', ' '))
    t = re.sub(r'\bpapa (Francisco|León|N\.)', 'papa N.', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'\s+([,.;:!?»)])', r'\1', t)
    t = re.sub(r'([«(¿¡])\s+', r'\1', t)
    return t


def negro(lineas):
    return re.sub(r'\s+', ' ', ' '.join(
        ''.join(x for r, x in ln if not r) for ln in (lineas or []))).strip()


def parecido(a, b):
    if a == b:
        return 1.0
    pa, pb = a.split(), b.split()
    return difflib.SequenceMatcher(None, pa, pb, autojunk=False).ratio()


# ----------------------------------------------------- la fuente, por días
def secciones_fuente(h):
    """Las secciones de una hora de la fuente, numeradas como la fase 3."""
    rep = Counter()
    ult = None
    out = {}
    for sec in h['secciones']:
        base = sec['clase']
        n = rep[base]
        rep[base] += 1
        cl = base if n == 0 else f'{base}{n + 1}'
        if base == 'responsorio' and ult == 'lectura2':
            cl = 'responsorio2'
        if base in ('lectura1', 'lectura2'):
            ult = base
        t = llano(sec['lineas'])
        if not t:
            continue
        out.setdefault(cl, (sec.get('rotulo') or '', sec['lineas'], t))
    return out


FUENTE = {}        # fecha -> [ {hora: {cl: (rot, lineas, texto)}} por opción ]
CABE = {}          # fecha -> cabecera de la fuente
for nombre in sorted(os.listdir(CORPUS)):
    if not nombre.endswith('.json'):
        continue
    for fecha, reg in json.load(open(os.path.join(CORPUS, nombre),
                                     encoding='utf-8')).items():
        variantes = []

        def recoge(r):
            variantes.append({h: secciones_fuente(x)
                              for h, x in (r.get('horas') or {}).items()})
            for o in r.get('opciones') or []:
                recoge(o)
        recoge(reg)
        FUENTE[fecha] = variantes
        CABE[fecha] = {'celebracion': reg.get('celebracion'),
                       'rango': reg.get('rango'), 'titulo': reg.get('titulo'),
                       'resena': reg.get('resena')}


# ---------------------------------------------------- qué día es igual a otro
def ident(iso):
    e = HD.get(iso)
    if not e:
        return None
    return (e.get('k'), e.get('kf'),
            tuple((c[0], c[3]) for c in e.get('c') or []),
            e.get('cm'), e.get('w'), e.get('v'))


FUERTES = ('Adviento', 'Cuaresma', 'Pascua')


def rango(iso):
    """El número de la Tabla de los días litúrgicos: cuanto menor, más manda."""
    e = HD.get(iso) or {}
    rs = [c[4] for c in e.get('c') or [] if c[3] != 'MEMORIA LIBRE' and c[4]]
    if e.get('d') == 0:
        rs.append(2 if e.get('t') in FUERTES else 6)
    if not rs:
        rs.append(9 if (e.get('kf') or e.get('t') == 'Cuaresma') else 13)
    return min(rs)


def tiene_primeras(iso):
    e = HD.get(iso) or {}
    return e.get('d') == 0 or any(c[3] == 'SOLEMNIDAD' for c in e.get('c') or [])


def son_primeras(iso):
    """¿Las vísperas de este día son ya las primeras del siguiente?"""
    man = suma(iso, 1)
    return tiene_primeras(man) and rango(man) < rango(iso)


def ident_hora(iso, hora):
    if hora in ('visperas', 'completas') and son_primeras(iso):
        return ('I', ident(suma(iso, 1)))
    return (ident(iso), None)


VACIAS = set('de del la las los el y san santa santo santos santas beato beata '
             'virgen martir martires presbitero obispo papa senor nuestro '
             'nuestra cristo jesucristo santisima santisimo bienaventurada '
             'iglesia doctor doctores apostol apostoles evangelista religiosa '
             'religioso abad diacono companeros solemnidad fiesta memoria '
             'presbiteros obispos virgenes'.split())


def palabras(t):
    return {p for p in clave(t or '').split() if p not in VACIAS and len(p) > 2}


def mismo_nombre(a, b):
    pa, pb = palabras(a), palabras(b)
    return len(pa & pb) >= max(1, min(len(pa), len(pb)) // 2)


def que_rezo(f):
    """Qué rezó la fuente ese día, en los términos de la app: 'feria', la
    clave del santo que la app tiene ese día, o None si no es ninguna de las
    dos cosas (otro calendario: la fuente celebró la Epifanía el miércoles 6
    de 2021, que la app pasa al domingo 3, o Nuestra Señora de Itatí).

    En las memorias libres la fuente unas veces reza la feria y otras el
    santo, y cada año sólo atestigua lo que rezó."""
    e = HD.get(f) or {}
    cab = CABE.get(f) or {}
    m = re.search(r'(\d+) de (enero|diciembre)$', e.get('kf') or '')
    if m and int(m[1]) != int(f[8:10]):
        return None
    cs = e.get('c') or []
    cel = cab.get('celebracion')
    if not cel:
        if (not cs or e.get('cm')
                or all(c[3] == 'MEMORIA LIBRE' for c in cs)):
            return 'feria'
        return None
    for c in cs:
        if mismo_nombre(c[2], cel):
            return c[0]
    return None


REZO = {f: que_rezo(f) for f in FUENTE}
CONFORME = {f: REZO[f] is not None for f in FUENTE}
POR_IDENT = defaultdict(list)
for f in FUENTE:
    if not CONFORME[f]:
        continue
    for h in ('oficio', 'laudes', 'tercia', 'sexta', 'nona', 'visperas',
              'completas'):
        ih = ident_hora(f, h)
        if ih[0] == 'I' and not CONFORME.get(suma(f, 1), False):
            continue
        POR_IDENT[(h, ih)].append(f)
POR_K = defaultdict(list)          # días en que la fuente rezó la feria
POR_KF = defaultdict(list)         # días con texto por fecha, por su fecha
POR_SANTO = defaultdict(list)      # días en que la fuente rezó al santo
for f in FUENTE:
    e = HD.get(f) or {}
    if REZO[f] == 'feria':
        POR_K[(e.get('k'), e.get('kf'))].append(f)
        if e.get('kf'):
            POR_KF[e['kf']].append(f)
    elif REZO[f]:
        POR_SANTO[REZO[f]].append(f)


def de_la_opcion(op):
    return 'feria' if op['modo'] == 'feria' else op['op']


# lo que depende del año ferial y del ciclo dominical
DE_ANIO = {'lectura1', 'responsorio'}


def filtra(fechas, iso, hora, cl):
    a = anio_de(iso)
    out = fechas
    if hora == 'oficio' and cl in DE_ANIO:
        out = [f for f in out if anio_de(f).get('ferial') == a.get('ferial')]
    e = HD.get(iso) or {}
    if cl == 'cantico_evangelico' and e.get('d') == 0:
        out = [f for f in out if anio_de(f).get('ciclo') == a.get('ciclo')]
    if (cl == 'cantico_evangelico' and hora == 'visperas' and son_primeras(iso)
            and (HD.get(suma(iso, 1)) or {}).get('d') == 0):
        c = anio_de(suma(iso, 1)).get('ciclo')
        out = [f for f in out if anio_de(suma(f, 1)).get('ciclo') == c]
    return out


def textos_testigo(fechas, hora, cl):
    """Los textos de la sección en esos días (todas las opciones del día)."""
    cl_f = {'apertura': 'invitatorio'}.get(cl, cl)
    out = []
    for f in fechas:
        for var in FUENTE[f]:
            s = var.get(hora, {}).get(cl_f)
            if s is None and cl_f == 'invitatorio':
                s = var.get(hora, {}).get('preambulo')
            if s:
                out.append((f, s))
    return out


# ------------------------------------------------------- la prueba de forma
CIERRES = re.compile(
    r'(por nuestro señor|por jesucristo|por cristo|que vive y reina|vives y '
    r'reinas|por los siglos de los siglos|amén\.?$|tú que vives|el cual vive|'
    r'él, que vive|que contigo vive|por él, que)', re.I)


def forma(hora, cl, c):
    """Qué le falta a la pieza para ser lo que su sección dice."""
    l = c['l'] if c else []
    t = llano(l)
    n = negro(l)
    malo = []
    if not t:
        return ['vacía']
    base = re.sub(r'\d+$', '', cl)
    if base == 'oracion':
        if not CIERRES.search(t):
            malo.append('oración sin conclusión')
        if len(n) > 1400:
            malo.append(f'oración larguísima ({len(n)} letras)')
    elif base in ('lectura1', 'lectura2') or cl == 'conm_lectura':
        if len(n) < 400:
            malo.append(f'lectura sin cuerpo ({len(n)} letras)')
    elif base in ('responsorio', 'conm_resp'):
        if not (re.search(r'\bR\.', t) and re.search(r'\bV\.', t)):
            malo.append('responsorio sin R./V.')
        if len(n) > 900:
            malo.append(f'responsorio larguísimo ({len(n)} letras)')
    elif base == 'salmodia':
        if not re.search(r'\bAnt', t):
            malo.append('salmodia sin antífona')
        if not re.search(r'\b(salmo|cántico|cantico)\b', t, re.I):
            malo.append('salmodia sin salmo')
    elif base == 'cantico_evangelico':
        if not re.search(r'\bAnt', t):
            malo.append('cántico sin antífona')
        if not re.search(r'(Bendito sea el Señor|Proclama mi alma|Ahora, Señor|'
                         r'Ahora Señor)', t):
            malo.append('cántico sin Benedictus/Magníficat/Nunc dimittis')
    elif base == 'himno':
        if len([x for x in l if negro([x])]) < 4:
            malo.append('himno de menos de cuatro versos')
    elif base == 'preces':
        if len(n) < 150:
            malo.append('preces cortas')
    elif base == 'lectura_breve':
        if len(n) < 30:
            malo.append('lectura breve vacía')
        if len(n) > 1500:
            malo.append(f'lectura breve larguísima ({len(n)} letras)')
    elif base == 'responsorio_breve':
        if not re.search(r'\bR\.', t):
            malo.append('responsorio breve sin R.')
    return malo


DEBE = {
    'oficio': ['apertura', 'himno', 'salmodia', 'lectura1', 'responsorio',
               'lectura2', 'responsorio2', 'oracion', 'conclusion'],
    'laudes': ['apertura', 'himno', 'salmodia', 'lectura_breve',
               'responsorio_breve', 'cantico_evangelico', 'preces', 'oracion',
               'conclusion'],
    'tercia': ['invocacion', 'himno', 'salmodia', 'lectura_breve', 'oracion',
               'conclusion'],
    'visperas': ['invocacion', 'himno', 'salmodia', 'lectura_breve',
                 'responsorio_breve', 'cantico_evangelico', 'preces', 'oracion',
                 'conclusion'],
    'completas': ['invocacion', 'examen', 'himno', 'salmodia', 'lectura_breve',
                  'responsorio_breve', 'cantico_evangelico', 'oracion',
                  'bendicion', 'antifona_final'],
}
DEBE['sexta'] = DEBE['nona'] = DEBE['tercia']


# ------------------------------------------------------------ la revisión
def texto_alt(a):
    return TEXTOS[a[2]] if a[2] >= 0 else None


def compara(iso, hora, op, s):
    """Estado de una sección frente a sus testigos."""
    cl = s['cl']
    if cl in ('conclusion', 'invocacion', 'examen', 'bendicion',
              'antifona_final') or cl.startswith('conm'):
        return None                     # el ordinario y lo añadido: aparte
    if cl == 'apertura':
        f = (s.get('formas') or {}).get('invitatorio')
        if not f:
            return None
        alts = f['alts']
        i = f['i']
    else:
        alts, i = s['alts'], s['i']
    elegido = texto_alt(alts[i])
    if cl == 'resena':
        mio = llano(elegido['l'])
        testigos = [(f, CABE[f]['resena']) for f in POR_SANTO.get(op['op'], [])
                    if CABE.get(f, {}).get('resena')]
        if not testigos:
            return ('sin_testigo', 0, 0.0, None)
        mejor = max(parecido(mio, llano([[[0, t]]])) for _, t in testigos)
        return ('igual' if mejor > 0.98 else 'distinto', len(testigos), mejor,
                None)
    nivel = 'dia'
    quien = de_la_opcion(op)
    ih = ident_hora(iso, hora)
    if ih[0] == 'I':
        cand = filtra(POR_IDENT.get((hora, ih), []), iso, hora, cl)
    else:
        cand = filtra([f for f in POR_IDENT.get((hora, ih), [])
                       if REZO[f] == quien], iso, hora, cl)
    if not cand:
        nivel = 'pieza'
        aid = alts[i][0]
        e = HD.get(iso) or {}
        if aid.startswith('dia') or aid.startswith('sal-') or op['modo'] == 'feria':
            cand = filtra(POR_K.get((e.get('k'), e.get('kf')), []), iso, hora,
                          cl)
        else:
            cand = filtra(POR_SANTO.get(op['op'], []), iso, hora, cl)
        # los días que van por fecha (la octava, la semana de la Epifanía):
        # sus textos son de la fecha y no del día de la semana, salvo los
        # salmos y lo que el sábado es ya del domingo
        if (not cand and e.get('kf') and cl != 'salmodia' and op['modo'] == 'feria'
                and hora != 'completas'
                and not (hora == 'visperas' and e.get('d') == 6)):
            nivel = 'fecha'
            cand = filtra(POR_KF.get(e['kf'], []), iso, hora, cl)
    tes = textos_testigo(cand, hora, cl)
    if not tes:
        return ('sin_testigo', 0, 0.0, nivel)

    def norm(c):
        if cl == 'apertura':      # del invitatorio sólo la antífona es del día
            ls = [ln for ln in c['l'] if ln and ln[0][0] and
                  re.match(r'\s*Ant', ln[0][1])]
            return llano(ls[:1])
        return llano(c['l'])

    def norm_f(s3):
        if cl == 'apertura':
            ls = [ln for ln in s3[1] if ln and ln[0][0] and
                  re.match(r'\s*Ant', ln[0][1])]
            return llano(ls[:1])
        return s3[2]
    mio = norm(elegido)
    suyos = Counter(norm_f(s3) for _, s3 in tes)
    if mio in suyos:
        return ('igual', len(tes), 1.0, nivel)
    for j, a in enumerate(alts):
        if j != i and texto_alt(a) and norm(texto_alt(a)) in suyos:
            return ('otra_opcion', len(tes), 1.0, nivel, a[0])
    mejor = max(parecido(mio, t) for t in suyos)
    return ('parecido' if mejor >= 0.9 else 'distinto', len(tes), mejor,
            nivel)


informe = []
cuenta = Counter()
por_cl = defaultdict(Counter)
for iso in sorted(DIAS_APP):
    dia = DIAS_APP[iso]
    for hora, ops in dia['horas'].items():
        for op in ops:
            cls = [s['cl'] for s in op['secs']]
            faltan = [c for c in DEBE[hora] if c not in cls]
            dup = [c for c, n in Counter(cls).items() if n > 1]
            for s in op['secs']:
                a = s['alts'][s['i']] if s['alts'] else None
                c = texto_alt(a) if a else None
                malo = forma(hora, s['cl'], c)
                st = compara(iso, hora, op, s)
                if st and op['def']:
                    cuenta[st[0]] += 1
                    por_cl[(hora, s['cl'])][st[0]] += 1
                informe.append({
                    'def': op['def'], 'modo': op['modo'],
                    'iso': iso, 'hora': hora, 'op': op['op'], 't': op['t'],
                    'g': op['g'], 'cl': s['cl'],
                    'alt': a[0] if a else None, 'n_alts': len(s['alts']),
                    'f': (c or {}).get('f') or '',
                    'rot': (c or {}).get('r') or '',
                    'inicio': negro((c or {}).get('l'))[:90],
                    'forma': malo, 'fuente': list(st) if st else None})
            if (faltan or dup) and op['def']:
                informe.append({'iso': iso, 'hora': hora, 'op': op['op'],
                                't': op['t'], 'cl': '*', 'faltan': faltan,
                                'dup': dup})

def texto_testigo(iso, hora, x, op):
    """El testigo más parecido, para ponerlo al lado en el informe."""
    ih = ident_hora(iso, hora)
    if ih[0] == 'I':
        cand = filtra(POR_IDENT.get((hora, ih), []), iso, hora, x['cl'])
    else:
        cand = filtra([f for f in POR_IDENT.get((hora, ih), [])
                       if REZO[f] == de_la_opcion(op)], iso, hora, x['cl'])
    tes = textos_testigo(cand, hora, x['cl'])
    return (tes[0][0], negro(tes[0][1][1])[:110]) if tes else (None, '')


ruta = os.path.join(raiz, 'Breviarium', 'datos', 'revision_qa.txt')
with open(ruta, 'w', encoding='utf-8') as f:
    w = lambda *a: f.write(' '.join(str(x) for x in a) + '\n')  # noqa: E731
    w(f'Revisión de las horas del {desde} al {hasta}, contra la fuente')
    w('=' * 60)
    w()
    w('días de la fuente que rezan lo que la app pone ese día:',
      sum(CONFORME.values()), 'de', len(CONFORME))
    w('secciones (celebración por omisión):')
    for k, n in cuenta.most_common():
        w(f'  {n:7d}  {k}')
    w()
    w('Horas con secciones de menos o repetidas')
    w('-' * 40)
    for x in informe:
        if x.get('cl') == '*':
            w(' ', x['iso'], x['hora'], x['t'][:50], 'faltan:', x['faltan'],
              'repetidas:', x['dup'])
    w()
    w('Secciones que no dicen lo que su nombre dice')
    w('-' * 40)
    for x in informe:
        if x.get('forma'):
            w(' ', x['iso'], x['hora'], x['cl'], ('' if x['def'] else '(opción) ')
              + x['t'][:40], x['forma'], '|', x['inicio'][:60])
    w()
    w('Distintas de la fuente en un día igual')
    w('-' * 40)
    for x in informe:
        st = x.get('fuente')
        if not (x.get('def') and st and st[0] == 'distinto'):
            continue
        op = next(o for o in DIAS_APP[x['iso']]['horas'][x['hora']] if o['def'])
        f_t, t_t = texto_testigo(x['iso'], x['hora'], x, op)
        w(' ', x['iso'], x['hora'], x['cl'], f'[{x["t"][:40]}]',
          f'parecido {st[2]:.2f}', 'primeras vísperas' if ident_hora(
              x['iso'], x['hora'])[0] == 'I' else '')
        w('      app :', x['inicio'][:110])
        if f_t:
            w(f'      {f_t}:', t_t)
print('días de la fuente conformes:', sum(CONFORME.values()), 'de', len(CONFORME))
print('estados frente a la fuente:', dict(cuenta))
print('defectos de forma (todas las opciones):',
      sum(1 for r in informe if r.get('forma')))
print('horas con secciones de menos o repetidas:',
      sum(1 for r in informe if r.get('cl') == '*'))
print('informe en', ruta)
