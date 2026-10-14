# -*- coding: utf-8 -*-
"""Fase 4c — qué es cada pieza.

Un devocionario no se hojea sólo por *a quién* se reza: también por *qué es*
lo que se va a rezar. No es lo mismo abrir una letanía de seis minutos que
una jaculatoria de nueve palabras, y en una lista las dos ocupan la misma
fila. Esta fase le pone a cada pieza su forma, que es lo que después permite
filtrar el libro entero por ella.

**La forma no se adivina por el título: se lee en la hechura del texto.** Un
título puede mentir o faltar —hay cuatro piezas que se llaman «Dómine Jesu
Christe»—, pero la hechura no: una letanía tiene el Kýrie y una respuesta
que se repite veinte veces; una colecta es prosa y acaba en «Per Christum
Dóminum nostrum»; un himno son renglones cortos y parejos agrupados de
cuatro en cuatro; una conmemoración es antífona, versículo y oración, en ese
orden. Cada pieza deja escrito en el informe por qué señal se decidió.

Las veinticuatro formas, y de dónde sale cada nombre:

    de la Escritura    salmo · cántico · salterio
    del canto          himno · secuencia · antífona · aclamación · pregón
    del rezo en coro   letanía · preces · conmemoración · responsorio
    de la devoción     oficio parvo · novena · rosario · vía crucis ·
                       ejercicio · rito
    de la liturgia     oración (la colecta) · bendición
    del alma           jaculatoria · súplica · acto · ofrecimiento ·
                       consagración · acción de gracias
    de la doctrina     credo · fórmula
    y de varias        colección (una pieza que trae un juego de oraciones)

Donde la hechura miente hay una tabla a mano, como en los acentos: el *Te
Deum* acaba en versículos y no por eso deja de ser el himno ambrosiano, y el
*Ánima Christi* está en verso pero nadie lo llama himno. Son veinte piezas,
en `datos/formas_mano.csv`, cada una con su razón escrita.

    TRABAJO/piezas_ecl.json ──┬──▶ Enchiridion/datos/formas.csv
    datos/formas_mano.csv ────┘ └▶ Enchiridion/datos/formas_qa.txt

    python Enchiridion/src/4c_formas.py
"""

import argparse
import collections
import csv
import io
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, TRABAJO

# Las cinco secuencias que la liturgia romana conserva, por su íncipit. No
# son un género aparte por capricho: son las que se cantan en la misa entre
# el salmo y el Evangelio, y quien las busca las busca por eso.
SECUENCIAS = ('victimae paschali', 'veni sancte spiritus reple',
              'lauda sion', 'stabat mater dolorosa', 'dies irae',
              'veni sancte spiritus et emitte')

# Las antífonas finales de la Virgen, que cierran el día en el Breviario, y
# el Sub tuum, que es la oración mariana más antigua que se conserva.
ANTIFONAS = ('alma redemptoris mater', 'ave regina caelorum', 'regina caeli',
             'salve regina', 'sub tuum praesidium', 'inviolata')

# El final que marca una colecta: la fórmula con que la Iglesia cierra la
# oración presidencial, y que ninguna otra forma usa.
CIERRE = re.compile(
    r'(?i)(per christum d[oó]minum nostrum'
    r'|qui vivis et regnas|qui vivit et regnat'
    r'|per e[uú]mdem christum|per d[oó]minum nostrum'
    r'|in unit[aá]te sp[ií]ritus sancti'
    r'|qui tecum vivit et regnat)')

ARRANQUE_COLECTA = re.compile(
    r'(?i)^(deus,? qui|omn[ií]potens|conc[eé]de|pr[aæ]sta|exc[ií]ta'
    r'|d[oó]mine,? sancte pater|adsumus|act[ió][oó]nes nostras'
    r'|d[ií]rigere et sanctific[aá]re|v[ií]sita|d[eé]us,? [aá]ngulum)')

VERSICULO = re.compile(r'^\s*(V\.|R\.|℣|℟)')
KYRIE = re.compile(r'(?i)k[yý]rie,? el[eé]ison')
ORACION_SOLA = re.compile(r'(?i)^or[eé]mus')

# Una pieza que trae varias oraciones se anuncia en el título: el número
# («Tres», «Septem», «Quinque») o el reparto por días.
COLECCION = re.compile(
    r'(?i)(orati[oó]nes|precati[oó]nes|prayers)\b.*(tres|septem|quinque|'
    r's[ií]ngulis|hebd[oó]mad)|(tres|septem|quinque)\s+(orati[oó]nes|'
    r'precati[oó]nes)')

# La súplica medieval habla en primera persona y de corrido: «me», «mihi»,
# «ego». Sin eso, prosa larga es sólo prosa larga.
PRIMERA = re.compile(r'(?i)\b(me|mihi|meam|meum|mea|meis|ego|mihimet)\b')


def plano(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace(u'æ', 'ae').replace(u'œ', 'oe').replace('j', 'i')
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def renglones(p):
    """Los renglones latinos de una pieza, con su marca de rúbrica."""
    fuera = []
    for b in p['b']:
        for linea in (b.get('la') or []):
            texto = ''.join(x[1] for x in linea).strip()
            rubrica = bool(b.get('r')) or all(x[0][0] for x in linea if x[1])
            if texto:
                fuera.append((texto, rubrica))
    return fuera


def medidas(lineas):
    """Lo que hay que mirar de un texto para saber de qué forma es."""
    dichos = [t for t, rub in lineas if not rub]
    palabras = sum(len(t.split()) for t in dichos)
    versos = [t for t in dichos if not VERSICULO.match(t)]
    vr = [t for t in dichos if VERSICULO.match(t)]
    # la respuesta que más se repite, que es lo que hace una letanía
    repes = collections.Counter(
        plano(re.sub(r'^\s*(R\.|℟)\s*', '', t)) for t in vr
        if VERSICULO.match(t) and t.lstrip()[:2] in ('R.', '℟'))
    masrepe = repes.most_common(1)[0] if repes else ('', 0)
    largo = [len(t) for t in versos] or [0]
    return {
        'yo': len(PRIMERA.findall(' '.join(dichos))),
        'palabras': palabras,
        'lineas': len(dichos),
        'versos': len(versos),
        'vr': len(vr),
        'repe': masrepe[1],
        'kyrie': any(KYRIE.search(t) for t in dichos[:6]),
        'cierre': any(CIERRE.search(t) for t in dichos),
        'oremus': any(ORACION_SOLA.match(t) for t in dichos),
        'medio': sum(largo) / float(len(largo)),
        'primero': dichos[0] if dichos else '',
    }


def forma_de(p, m):
    """La forma de una pieza, y la señal por la que se decide.

    El orden importa: se va de lo que una sola señal basta para decidir —el
    título de un salmo, el Kýrie de una letanía— a lo que hay que deducir de
    la hechura, y lo último de todo es la prosa suelta."""
    t = plano(p['tla'])
    cat = p['cat']

    # --- lo decidido a mano, que son las piezas cuya hechura engaña
    if t in MANO:
        return MANO[t][0], MANO[t][1] + ' (a mano)'

    # --- una pieza que son varias
    if COLECCION.search(t):
        return 'colección', 'el título anuncia varias oraciones'

    # --- lo que la Escritura y el libro declaran por su nombre
    if cat.startswith('Psalmi') or t.startswith('psalmus'):
        return 'salmo', 'el título lo dice'
    if t.startswith(('psalmi graduales', 'septem psalmi', 'psalterium')):
        return 'salterio', 'una colección de salmos'
    if cat == 'Cantici' or t in ('benedicite dominum',):
        return 'cántico', 'cántico bíblico'
    if cat == 'Numeri':
        return 'fórmula', 'no es oración: es doctrina enumerada'
    if t.startswith('symbolum') or t == 'quicumque' \
       or 'professio fidei' in t:
        return 'credo', 'profesión de fe'

    # --- las devociones largas, que se reconocen por su nombre propio
    if 'officium parvum' in t or 'parvum officium' in t \
       or t.startswith('horae') or 'officium parvum' in plano(p.get('ten') or ''):
        return 'oficio parvo', 'oficio o horas'
    if t.startswith('novena'):
        return 'novena', 'nueve días'
    if 'viae crucis' in t or 'viam crucis' in t or 'stationum' in t:
        return 'vía crucis', 'las estaciones'
    if t.startswith('rosarium') or t.startswith('corona'):
        return 'rosario', 'rosario o coronilla'
    if t.startswith('exercitium'):
        return 'ejercicio', 'ejercicio de devoción'

    # --- lo que se canta
    if any(t.startswith(s) for s in SECUENCIAS) and m['versos'] >= 8:
        return 'secuencia', 'secuencia de la misa'
    if t in ANTIFONAS:
        return 'antífona', 'antífona del Breviario'
    if cat.startswith('Hymni') or 'hymnus' in t:
        return 'himno', 'el libro lo trae entre los himnos'

    # --- lo que se reza a dos coros
    if 'litaniae' in t:
        return 'letanía', 'el título lo dice'
    if m['kyrie'] and m['repe'] >= 6:
        return 'letanía', 'Kýrie y %d respuestas iguales' % m['repe']
    if m['repe'] >= 8:
        return 'letanía', '%d veces la misma respuesta' % m['repe']
    if t.startswith('commemoratio'):
        return 'conmemoración', 'el título lo dice'
    if m['vr'] >= 2 and m['oremus'] and m['cierre'] and m['versos'] <= 6:
        return 'conmemoración', 'antífona, versículo y oración'
    if t.startswith(('memorare', 'obsecro', 'recordare')):
        return 'súplica', 'el íncipit la nombra'
    if t.startswith('preces') or (m['vr'] >= 6 and not m['cierre']):
        return 'preces', 'serie de versículos'
    if m['repe'] >= 3 and m['versos'] >= 6 and m['medio'] < 46:
        return 'responsorio', 'verso con respuesta que vuelve'

    # --- lo que el alma dice por su cuenta
    if t.startswith('actus'):
        return 'acto', 'el título lo dice'
    if t.startswith(('oblatio', 'formula oblationis', 'suscipe')) \
       or t.startswith('tibi offerimus') or 'oblationis' in t:
        return 'ofrecimiento', 'se ofrece algo'
    if 'consecrati' in t or t.startswith('consecramus'):
        return 'consagración', 'se consagra algo'
    if 'gratiarum actio' in t or t.startswith('gratias'):
        return 'acción de gracias', 'el título lo dice'
    if t.startswith('benedictio'):
        return 'bendición', 'el título lo dice'
    # La súplica: la plegaria medieval larga, en primera persona y sin la
    # conclusión de la colecta. Se exige que el «yo» esté de verdad, porque
    # si no toda prosa larga acaba aquí dentro.
    if (m['palabras'] >= 200 and not m['cierre'] and m['vr'] == 0
            and m['medio'] > 60 and m['yo'] >= 6):
        return 'súplica', ('%d palabras en primera persona, sin cierre'
                           % m['palabras'])

    # --- el himno que el libro no puso entre los himnos
    if m['versos'] >= 8 and m['medio'] < 42 and m['vr'] <= 2:
        return 'himno', '%d renglones cortos y parejos' % m['versos']

    # --- lo corto
    if m['palabras'] <= 25 and m['vr'] == 0:
        return 'jaculatoria', '%d palabras' % m['palabras']

    # --- la oración de siempre
    if m['cierre']:
        return 'oración', 'acaba en la conclusión litúrgica'
    if ARRANQUE_COLECTA.match(m['primero']):
        return 'oración', 'empieza como una colecta'
    return 'oración', 'prosa suelta'


ORDEN = ['oración', 'himno', 'letanía', 'jaculatoria', 'conmemoración',
         'salmo', 'súplica', 'fórmula', 'oficio parvo', 'novena', 'acto',
         'secuencia', 'antífona', 'preces', 'responsorio', 'vía crucis',
         'rosario', 'cántico', 'credo', 'salterio', 'bendición',
         'ofrecimiento', 'consagración', 'acción de gracias', 'ejercicio',
         'colección', 'aclamación', 'pregón', 'rito']

MANO = {}


def carga_mano():
    """Las piezas decididas a mano, por su título latino."""
    ruta = os.path.join(DATOS, 'formas_mano.csv')
    if not os.path.exists(ruta):
        return
    with io.open(ruta, encoding='utf-8', newline='') as fh:
        for fila in csv.DictReader(fh):
            if fila.get('titulo'):
                MANO[plano(fila['titulo'])] = (fila['forma'], fila['senal'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()

    entrada = os.path.join(TRABAJO, 'piezas_ecl.json')
    if not os.path.exists(entrada):
        sys.exit('corre antes Enchiridion/src/3_eclesiastico.py')
    with io.open(entrada, encoding='utf-8') as fh:
        libro = json.load(fh)
    carga_mano()

    filas, cuenta, porque = [], collections.Counter(), collections.Counter()
    muestra = collections.defaultdict(list)
    for p in libro['piezas']:
        if 'duplicado_de' in p or not p['car_la']:
            continue
        lineas = renglones(p)
        if not lineas:
            continue
        m = medidas(lineas)
        forma, senal = forma_de(p, m)
        cuenta[forma] += 1
        porque[(forma, senal.split(':')[0])] += 1
        muestra[forma].append((m['palabras'], p['tla'], senal))
        filas.append({'id': p['id'], 'forma': forma, 'senal': senal,
                      'palabras': m['palabras'], 'titulo': p['tla']})

    os.makedirs(DATOS, exist_ok=True)
    ruta = os.path.join(DATOS, 'formas.csv')
    with io.open(ruta, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, ['id', 'forma', 'senal', 'palabras', 'titulo'])
        w.writeheader()
        for f in sorted(filas, key=lambda f: (ORDEN.index(f['forma'])
                                              if f['forma'] in ORDEN else 99,
                                              plano(f['titulo']))):
            w.writerow(f)

    qa = os.path.join(DATOS, 'formas_qa.txt')
    with io.open(qa, 'w', encoding='utf-8') as fh:
        fh.write(u'Qué es cada pieza del devocionario\n')
        fh.write(u'=' * 34 + u'\n\n%d piezas en %d formas.\n\n'
                 % (len(filas), len(cuenta)))
        for forma in ORDEN:
            if not cuenta[forma]:
                continue
            fh.write(u'\n%s  (%d)\n%s\n' % (forma.upper(), cuenta[forma],
                                            u'-' * 60))
            for pal, tit, senal in sorted(muestra[forma]):
                fh.write(u'  %5d  %-54s %s\n' % (pal, tit[:54], senal))
    print('%d piezas -> %s' % (len(filas), ruta))
    for forma in ORDEN:
        if cuenta[forma]:
            print('  %-18s %4d' % (forma, cuenta[forma]))


if __name__ == '__main__':
    main()
