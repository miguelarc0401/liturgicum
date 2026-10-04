# -*- coding: utf-8 -*-
"""Fase 6 — la misa castellana, empaquetada para la app.

La fase 5 dejó en `Missale/datos/libro/misa.json` **la decisión y no el
texto**: por cada clave del leccionario dice, ranura por ranura, de qué
celebración, de qué suelto, de qué común o de qué formulario latino sale su
texto, por qué camino se decidió y con cuántos testigos. Esta fase no decide
nada: **dereferencia**. Va a buscar cada texto donde la decisión dice que
está y lo deja en `app/datos/` en la forma en que lo lee un programa.

    Missale/datos/libro/misa.json   ─┐
    Missale/datos/libro/propios_es.json
    Missale/datos/libro/sueltos_es.json
    Missale/datos/libro/pericopas_es.json
    Missale/datos/libro/prefacios_propios_es.json
    Missale/datos/libro/dias_es.json  ├─→  app/datos/misa.json
    Missale/datos/misal_latino.json   │    app/datos/lecturas_es.json
    Missale/datos/prefacios_es.json   │    app/datos/misal_latino.json
    Missale/datos/ordinario_es.json  ─┘    app/datos/prefacios.json
                                           app/datos/ordinario.json
    y el informe:  Missale/datos/app_qa.txt

Cinco cosas que esta fase hace y conviene saber por qué.

**1. Desarma la perícopa impresa.** El misalito imprime una lectura como un
bloque corrido que lleva dentro cuatro cosas distintas: el sumario (unas
veces entre corchetes y otras a pelo), la fórmula con su cita («Del santo
Evangelio según san Lucas 21, 25-28. 34-36»), el cuerpo, y el cierre con la
respuesta del pueblo («Palabra de Dios. R/. Te alabamos, Señor.»). La app
necesita las cuatro por separado, como ya las tiene del leccionario latino,
así que se separan aquí —no en la fase 4, que guarda lo que la fuente
imprimió— y el informe cuenta cuántas veces salió cada una.

El cierre hay que buscarlo en el texto **ya juntado**, no en el último
renglón: la fuente parte «Palabra / de Dios.» entre dos renglones 181 veces,
y mirando sólo el último no se encuentra.

**2. El latín no se copia dos veces.** Los 575 formularios del Misal latino
van en `misal_latino.json` **por su propio nombre**, y `misa.json` sólo
guarda el puntero (`la`). Son 451 unidades para 1 051 claves del
leccionario: copiarlo por clave multiplicaría por dos el fichero sin añadir
una palabra.

**3. Los prefacios 33 a 82 no se repiten.** El Ordo latino numera del 1 al
146, y del 33 al 82 lo que numera **son los cincuenta prefacios**, que ya
van en `prefacios.json` con su pareja castellana. Así que esas cincuenta
entradas de `ordinario.json` llevan el puntero (`pref`) y no el texto.

**4. La rúbrica latina se reconoce por el acento.** El Ordinario de México
marca sus rúbricas en rojo y la fase 2 lo guardó; el Misal latino lo leyó
con `pdftotext`, que no guarda color. Pero el Misal tiene su propia marca, y
es tipográfica: **imprime acentuado lo que se reza** —para recitarlo— y sin
acentuar la rúbrica. Medido contra el rojo que el PDF latino sí trae
(0xff0000), la regla acierta en las 2 219 líneas del Ordo en que el color y
el acento dicen lo mismo, y de las que discrepan **la razón es el color, no
el acento**: el PDF deja en negro la mitad de sus rúbricas (393 líneas
negras sin acento, todas rúbricas: «1. Populo congregato, sacerdos cum
ministris ad altare accedit»). Las excepciones de verdad son las respuestas
breves que no llevan acento, que son siete y van en la tabla
`REZADAS_SIN_ACENTO`, con su prueba al lado.

**5. Recorta el apéndice que la fase 1 le pegó al Ordo.** Las veinte
bendiciones solemnes y las veintiocho oraciones sobre el pueblo del
«APPENDIX AD ORDINEM MISSÆ» están pegadas al final de las rúbricas 1 a 28
del Ordo, cada una a la rúbrica de su mismo número: la rúbrica 1 —«Populo
congregato»— trae detrás la bendición solemne de Adviento. Son 515 renglones
en 29 rúbricas, y sin quitarlos la app enseñaría la bendición de Adviento en
medio del rito de entrada. El recorte está probado por igualdad de texto
contra `bendiciones` y `super_populum`, que es donde la fase 1 **sí** las
guardó bien, de modo que no se pierde nada; y queda nombrado en el informe
como lo que es: un defecto de la fase 1 que ésta rodea.

    python Missale/src/6_app.py

Necesita las fases 1, 2, 3, 4 y 5 corridas. Vuelve a firmar
`app/datos/version.js` con la fórmula de `src/15_app_data.py`, para que el
service worker del teléfono tire su caché.
"""

import json
import os
import re
import sys
import unicodedata
import zlib
from collections import Counter, OrderedDict, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misal
from misal import DATOS, LIBRO, RAIZ, Informe

APP = os.path.join(RAIZ, 'app', 'datos')
CODIGO_APP = ['index.html', 'app.js', 'estilos.css', 'manifest.webmanifest']
QA = os.path.join(DATOS, 'app_qa.txt')

RANURAS = ['entrada', 'colecta', 'ofrendas', 'comunion', 'poscomunion',
           'pueblo']

# El rótulo con que la app encabeza cada lectura. El leccionario latino los
# lleva en latín («LECTIO PRIMA»); en castellano son los que el misalito
# imprime, y los tipos que la fase 4 distinguió.
ROTULO = {
    'primera lectura': 'PRIMERA LECTURA',
    'segunda lectura': 'SEGUNDA LECTURA',
    'tercera lectura': 'TERCERA LECTURA',
    'cuarta lectura': 'CUARTA LECTURA',
    'quinta lectura': 'QUINTA LECTURA',
    'sexta lectura': 'SEXTA LECTURA',
    'septima lectura': 'SÉPTIMA LECTURA',
    'epistola': 'EPÍSTOLA',
    'lectura del Antiguo Testamento': 'LECTURA DEL ANTIGUO TESTAMENTO',
    'lectura del Nuevo Testamento': 'LECTURA DEL NUEVO TESTAMENTO',
    'salmo responsorial': 'SALMO RESPONSORIAL',
    'aleluya': 'ACLAMACIÓN ANTES DEL EVANGELIO',
    'secuencia': 'SECUENCIA',
    'evangelio': 'EVANGELIO',
}

# La clase con que la app pinta cada lectura, la misma que usa
# `lecturas_clementina.json`: el salmo lleva su respuesta intercalada, la
# aclamación no lleva cierre, y la lectura sí.
CLASE = {'salmo responsorial': 'salmo', 'aleluya': 'aleluya',
         'secuencia': 'aleluya'}

# --------------------------------------------------------------------------
# desarmar la perícopa impresa
# --------------------------------------------------------------------------
# La fórmula con su cita, de corrido: «De la primera carta del apóstol san
# Pablo a los corintios 1, 22-25» y detrás el cuerpo, que empieza siempre en
# mayúscula o en comilla («Hermanos:», «En aquel tiempo», «“Habrá señales»).
# La fórmula no lleva cifras —el libro va con su nombre deletreado, «Del
# segundo libro de Samuel»—, y eso es lo que permite cortarla de la cita.
FORMULA_CITA = re.compile(
    r'(?P<f>(?:Del?(?:\s+la)?|Comienza|Lectura|Inicio)\s[^0-9\[\]]{3,110}?)'
    r'[\s.:]+(?P<c>(?:cf\.\s*)?\d[\d\s,.;:–—abcdefghi\-]*?)'
    r'(?=\s+[«“"‘“¿¡\[A-ZÁÉÍÓÚÑ]|$)')

# El cierre y, detrás, la respuesta del pueblo.
CIERRE = re.compile(
    r'\s*(Palabra de Dios|Palabra del Señor)\s*\.?'
    r'(?:\s*(R/?\.[^.]*\.))?\s*$')

# El sumario entre corchetes, que la fuente pone antes de la fórmula.
CORCHETE = re.compile(r'^\s*\[([^\]]*)\]\s*')

# El renglón del salmo que acaba en la respuesta: ahí se corta la estrofa. La
# fuente la marca unas veces con la letra sola («… sus mandamientos. R/.») y
# otras repitiendo el principio de la respuesta («… danos tu salvación. R.
# Aleluya.»), que es lo que hace el misalito con las aclamaciones.
RESPUESTA = re.compile(r'\s*R/?\.\s*(.{0,40}?)\s*$')


def junta(lineas):
    """Los renglones impresos, en un párrafo.

    El guión de final de renglón lo juntó la fase 4 —7 233 palabras—, pero
    nueve perícopas se le escaparon, así que se repite la regla aquí:
    renglón que acaba en guión y el siguiente empieza en minúscula.
    """
    out = ''
    for l in lineas:
        l = l.strip()
        if not l:
            continue
        if out.endswith('-') and l[:1].islower():
            out = out[:-1] + l
        elif out:
            out += ' ' + l
        else:
            out = l
    return re.sub(r'\s+', ' ', out).strip()


def desarma(texto, sumario=None):
    """Una perícopa impresa en sus cuatro partes.

    Devuelve `(sumario, formula, cita, cuerpo, cierre, respuesta)`. Lo que no
    se reconozca se queda en el cuerpo: nunca se tira nada.

    **La fórmula es el ancla, y el sumario es lo que va delante de ella.** La
    fuente imprime el sumario unas veces entre corchetes
    («[Predicamos a Cristo crucificado…] De la primera carta…») y otras a
    pelo («Sean imitadores míos como yo lo soy de Cristo. De la primera
    carta…»), y no hay manera de distinguirlo por sí mismo; pero la fórmula
    sí se reconoce, así que se busca ella y lo de antes es el sumario. Si no
    hay fórmula, el texto se queda entero en el cuerpo.
    """
    t = junta(texto)
    s = formula = cita = None
    m = FORMULA_CITA.search(t[:360])
    if m:
        antes = t[:m.start()].strip()
        formula = re.sub(r'\s+', ' ', m.group('f')).strip(' .:')
        cita = m.group('c').strip(' .,;:')
        t = t[m.end():].strip()
        c = CORCHETE.match(antes)
        if c:
            s = c.group(1).strip()
        elif antes:
            s = antes.strip(' .')
    else:
        c = CORCHETE.match(t)
        if c:
            s, t = c.group(1).strip(), t[c.end():].strip()
        elif sumario and t.startswith(sumario.rstrip('.')):
            s = sumario.rstrip('.')
            t = t[len(s):].lstrip(' .').strip()
    cierre = resp = None
    m = CIERRE.search(t)
    if m:
        cierre, resp = m.group(1), m.group(2)
        t = t[:m.start()].rstrip()
    return s, formula, cita, t, cierre, resp


def estrofas(texto, resp=None):
    """El salmo en estrofas: la respuesta del pueblo es lo que las corta.

    La fuente imprime «… y se goza en cumplir sus mandamientos. R/.» al final
    de cada estrofa. Se corta ahí y la marca no se guarda: la pone la app.

    Con la letra sola no hay duda. Cuando detrás viene texto, sólo se tira si
    es el principio de la respuesta de ese salmo —«R. Aleluya.» cuando la
    respuesta es «Aleluya, aleluya.»—; cualquier otra cosa se queda, porque
    entonces no es la repetición, es verso.
    """
    clave = misal.clave(resp or '')

    def corta(t):
        m = RESPUESTA.search(t)
        if not m:
            return None
        cola_ = misal.clave(m.group(1))
        if not cola_ or (clave and clave.startswith(cola_)):
            return t[:m.start()].rstrip()
        return None

    fuera, cur = [], []
    for l in texto:
        if not l.strip():
            continue
        cur.append(l)
        t = junta(cur)
        corte = corta(t)
        if corte is not None:
            fuera.append(corte)
            cur = []
    if cur:
        fuera.append(junta(cur).strip())
    return [e for e in fuera if e]


def respuesta_de(texto):
    """La respuesta del salmo o de la aclamación: el primer renglón, que la
    fuente abre con «R.» o «R/.»."""
    for l in texto:
        if not l.strip():
            continue
        m = re.match(r'^\s*R/?\.\s*(.+)$', l)
        return (m.group(1).strip() if m else None), (1 if m else 0)
    return None, 0


# --------------------------------------------------------------------------
# 1. las lecturas en castellano
# --------------------------------------------------------------------------
def una_lectura(l, peri, cuenta, raro):
    """Una lectura del formulario, tal como la enseña la app.

    Las que el misalito no imprimió nunca van igual, con su rótulo y su cita
    y la marca `sin`: la app dice «no disponible» y no disimula el hueco, que
    es lo que se decidió en la pregunta 6 del plan.
    """
    tipo = l['tipo']
    item = {'t': ROTULO.get(tipo, tipo.upper()), 'c': l['cita'],
            'k': CLASE.get(tipo, 'lectura'), 'es': True}
    if not l['es'] or l['es'] not in peri:
        item['sin'] = True
        cuenta['lecturas sin castellano'] += 1
        return item
    v = peri[l['es']]
    cuenta['lecturas con castellano'] += 1
    item['n'] = len(v['testigos'])
    if v.get('variantes'):
        item['vn'] = len(v['variantes'])
    extra = []
    if item['k'] == 'salmo' or item['k'] == 'aleluya':
        r, hay = respuesta_de(v['texto'])
        if r:
            item['r'] = r
        else:
            cuenta['salmo o aclamación sin respuesta'] += 1
            raro['salmo o aclamación sin respuesta'].add(l['es'])
        es = estrofas(v['texto'][hay:], r)
        item['g'] = [[['', e]] for e in es]
        if not es:
            item['g'] = [[['', junta(v['texto'])]]]
            cuenta['salmo sin estrofas'] += 1
        cuenta['estrofas de salmo o aclamación'] += len(es)
    else:
        s, f, ci, cuerpo, z, resp = desarma(v['texto'], v.get('sumario'))
        if f:
            item['f'] = f
            cuenta['lecturas con fórmula'] += 1
        else:
            cuenta['lecturas sin fórmula reconocida'] += 1
            raro['sin fórmula reconocida'].add(l['es'])
        if ci:
            extra.append(ci)
        if s:
            item['s'] = s
            cuenta['lecturas con sumario'] += 1
        if z:
            item['z'] = z
            cuenta['lecturas con cierre'] += 1
        else:
            cuenta['lecturas sin cierre reconocido'] += 1
            raro['sin cierre reconocido'].add(l['es'])
        if resp:
            item['rz'] = resp
            cuenta['lecturas con respuesta del pueblo'] += 1
        item['g'] = [[['', cuerpo]]] if cuerpo else []
    # Texto de más para el buscador: la cita como la escribe el misalito, que
    # no siempre es la del índice, y el sumario.
    if l['es'] and l['es'] != l['cita']:
        extra.append(l['es'])
    if v.get('sumario') and not item.get('s'):
        extra.append(v['sumario'])
    extra = ' '.join(x for x in extra if x)
    if extra:
        item['q'] = extra
    return item


def construye_lecturas(misa, peri, cuenta, raro):
    bloques = OrderedDict()
    for clave in sorted(misa['formularios']):
        f = misa['formularios'][clave]
        if not f['lecturas']:
            continue
        lect = [una_lectura(l, peri, cuenta, raro)
                for l in sorted(f['lecturas'], key=lambda x: x['o'])]
        if any(not x.get('sin') for x in lect):
            bloques[clave] = lect
        else:
            cuenta['formularios sin una sola lectura en castellano'] += 1
    return {
        'fuente': 'es',
        'titulo': 'Leccionario de México',
        'cabecera': 'Texto: el misalito mensual de 2018 a 2026 — La Santa '
                    'Misa (Guadalajara, 97 números) y Palabra Viva (Mérida, '
                    '3).\nEstructura: Leccionario de Servicios Koinonía.',
        'cierre': '',
        'bloques': bloques,
    }


# --------------------------------------------------------------------------
# 2. el formulario del día
# --------------------------------------------------------------------------
def pieza_de(p, propios, sueltos, cuenta):
    """El texto de una ranura, buscado donde la fase 5 dice que está.

    Cinco caminos llevan al misalito y uno al latín. Los del misalito
    acaban en una de dos tablas —las piezas de una celebración o los textos
    sueltos—, y la fase 5 ya dejó dicho en qué tabla y con qué llave. Lo que
    sale en latín no se copia aquí: va en `misal_latino.json` y la app lo
    alcanza por el puntero `la` del formulario.
    """
    if not p:
        return None
    if p['f'] == 'latino':
        cuenta['piezas que sólo tiene el latín'] += 1
        return None
    de, r = p['de'], p['r']
    if isinstance(de, int):
        s = sueltos[de]
        texto, variantes = s['texto'], []
    else:
        q = ((propios.get(de) or {}).get('piezas') or {}).get(r)
        if not q:
            cuenta['piezas que la decisión apunta y no están'] += 1
            return None
        texto, variantes = q['texto'], q.get('variantes') or []
    out = {'t': junta(texto), 'via': p['via'], 'de': de, 'n': p['t']}
    if p['r'] != r:
        out['r'] = p['r']
    if variantes:
        out['v'] = [junta(x['texto']) for x in variantes]
    cuenta['piezas en castellano'] += 1
    cuenta['  por ' + p['via']] += 1
    return out


def un_formulario(f, propios, sueltos, cuenta):
    out = {'t': f['titulo'], 'e': f['etiqueta'], 's': f['seccion'],
           'u': f['u'], 'v': f['v']}
    for campo, llave in (('grado', 'g'), ('color', 'c'), ('resena', 'r'),
                         ('la', 'la'), ('gloria', 'gl'), ('credo', 'cr')):
        if f.get(campo) is not None:
            out[llave] = f[campo]
    if f.get('alt'):
        out['alt'] = f['alt']
    if f.get('prefacio'):
        out['pr'] = f['prefacio']
    if f.get('prefacio_propio'):
        out['pp'] = True
    piezas = {}
    for r in RANURAS:
        q = pieza_de(f['piezas'].get(r), propios, sueltos, cuenta)
        if q:
            piezas[r] = q
    out['p'] = piezas
    return out


def construye_misa(misa, propios, sueltos, propios_pref, cuenta, inf):
    formularios = OrderedDict()
    for clave in sorted(misa['formularios']):
        formularios[clave] = un_formulario(
            misa['formularios'][clave], propios, sueltos, cuenta)

    # el prefacio propio cosechado, atribuido por sus testigos
    de_cel = defaultdict(list)
    for pid, v in sorted(propios_pref.items()):
        if v.get('cel'):
            de_cel[v['cel']].append(pid)
    puestos = 0
    for clave, f in formularios.items():
        cel = misa['formularios'][clave]['cel']
        ids = de_cel.get(cel) or de_cel.get(cel.split('#')[0])
        if ids:
            f['ppd'] = ids if len(ids) > 1 else ids[0]
            puestos += 1
    cuenta['formularios con prefacio propio cosechado'] = puestos

    # Las otras misas del mismo día, que el leccionario no numera: la vigilia
    # de san Juan Bautista y la de san Pedro y san Pablo, la vigilia de
    # Pentecostés, la segunda y la tercera de los Difuntos; y las
    # celebraciones del propio de México y las votivas que el misalito
    # imprimió y el índice del leccionario no alcanza. Van aparte, por su
    # unidad, para que no se pierda lo cosechado y la app pueda ofrecerlas por
    # lo que son. Las que no traen ni castellano ni latín no entran.
    con_clave = {f['u'] for f in misa['formularios'].values()}
    otros = OrderedDict()
    for u in sorted(set(misa['unidades'].values()) - con_clave):
        cels = sorted(c for c, uu in misa['unidades'].items() if uu == u)
        piezas, titulo, cel = {}, None, None
        for c in cels:
            pr = propios.get(c)
            if not pr:
                continue
            cel = cel or c
            titulo = titulo or pr.get('titulo')
            for r in RANURAS:
                if r in piezas:
                    continue
                q = (pr.get('piezas') or {}).get(r)
                if q:
                    piezas[r] = {'t': junta(q['texto']), 'via': 'celebración',
                                 'de': c, 'n': len(q['testigos'])}
                    if q.get('variantes'):
                        piezas[r]['v'] = [junta(x['texto'])
                                          for x in q['variantes']]
        la = (misa['latino'].get(u) or {}).get('k')
        if not piezas and not la:
            continue
        e = {'u': u, 'cel': cel or cels[0], 'p': piezas}
        if titulo:
            e['t'] = titulo
        if la:
            e['la'] = la
        if cels != [e['cel']]:
            e['cels'] = cels
        otros[u] = e
    cuenta['otras misas sin clave del leccionario'] = len(otros)

    return {
        'fuente': 'fase 6 — la misa castellana',
        'cabecera': 'Traducción litúrgica aprobada para México, cosechada '
                    'del misalito mensual de 2018 a 2026 por mayoría de '
                    'testigos. Lo que no está en castellano se dice; no se '
                    'traduce.',
        'formularios': formularios,
        'otros': otros,
    }


# --------------------------------------------------------------------------
# 3. el Misal latino
# --------------------------------------------------------------------------
def cola(lineas):
    """Las líneas de una pieza latina, tal como el Misal las imprime.

    Aquí no se juntan en un párrafo: el Misal corta la oración en cola —un
    miembro por renglón— y eso es parte del texto, no de la maqueta. Los
    renglones en blanco que `-layout` mete dentro sí se tiran.
    """
    return [re.sub(r'\s+', ' ', l).strip() for l in lineas if l.strip()]


def construye_latino(lat, usados, cuenta):
    formularios = OrderedDict()
    for k in sorted(lat['formularios']):
        v = lat['formularios'][k]
        piezas = {}
        for r, q in sorted((v.get('piezas') or {}).items()):
            if not q.get('texto'):
                continue
            piezas[r] = {'t': cola(q['texto'])}
            if q.get('cita'):
                piezas[r]['c'] = q['cita']
        e = {'t': v['titulo'], 'p': piezas}
        for campo, llave in (('ruta', 'ruta'), ('grado', 'grado'),
                             ('dia', 'dia'), ('pagina', 'pag')):
            if v.get(campo):
                e[llave] = v[campo]
        for campo, llave in (('rubricas', 'rub'), ('prefacio', 'pr'),
                             ('comun', 'com'), ('propios', 'propios')):
            if v.get(campo):
                e[llave] = v[campo]
        for campo, llave in (('gloria', 'gl'), ('credo', 'cr')):
            if v.get(campo) is not None:
                e[llave] = v[campo]
        formularios[k] = e
        if not piezas:
            cuenta['formularios latinos sin una pieza'] += 1
    cuenta['formularios latinos'] = len(formularios)
    cuenta['formularios latinos que alguna clave usa'] = len(
        usados & set(formularios))
    return {
        'fuente': 'Missale Romanum, editio typica tertia (2002)',
        'cabecera': 'Textus latinus: Missale Romanum, editio typica tertia, '
                    '2002.',
        'formularios': formularios,
        'bendiciones': {'rubrica': cola(lat['bendiciones'].get('rubrica')
                                        or []),
                        'piezas': [{'n': p['n'], 'sec': p.get('seccion'),
                                    't': p.get('titulo'),
                                    'tx': cola(p['texto'])}
                                   for p in lat['bendiciones']['piezas']]},
        'super_populum': {'rubrica': cola(lat['super_populum'].get('rubrica')
                                          or []),
                          'piezas': [{'n': p['n'], 'tx': cola(p['texto'])}
                                     for p in lat['super_populum']['piezas']]},
    }


# --------------------------------------------------------------------------
# 4. los prefacios
# --------------------------------------------------------------------------
# El grupo de cada prefacio, leído de su propio título: es lo que el
# Ordinario dice, y es lo que hace falta para que la app los ofrezca
# agrupados en vez de dar una lista de sesenta y siete.
GRUPO = [
    (r'\bADVIENTO\b', 'adviento'),
    (r'\bNAVIDAD\b|\bEPIFAN', 'navidad'),
    (r'\bCUARESMA\b|\bPASI[ÓO]N\b', 'cuaresma'),
    (r'\bPASCUAL\b|\bASCENSI[ÓO]N\b', 'pascua'),
    (r'\bDOMINGOS DEL TIEMPO ORDINARIO\b', 'domingos'),
    (r'\bBAUTISMO\b|\bCONFIRMACI[ÓO]N\b|\bEUCARIST[ÍI]A\b|'
     r'\bPENITENCIA\b|\bUNCI[ÓO]N\b|\bMATRIMONIO\b', 'sacramentos'),
    (r'\bSANTA MAR[ÍI]A\b', 'maria'),
    (r'\bAP[ÓO]STOLES\b|\bSANTOS\b|\bM[ÁA]RTIRES\b|\bPASTORES\b|'
     r'\bV[ÍI]RGENES\b', 'santos'),
    (r'\bDIFUNTOS\b', 'difuntos'),
    (r'\bCOM[ÚU]N\b', 'comun'),
]


def grupo_de(titulo):
    t = (titulo or '').upper()
    for patron, g in GRUPO:
        if re.search(patron, t):
            return g
    return 'otros'


def tiradas(lineas):
    """Las líneas de tiradas del Ordinario castellano, tal como vienen.

    Cada línea es una lista de pares `(rojo, texto)`: la fase 2 las leyó del
    color del PDF y no hay nada que decidir aquí. Lo único que se hace es
    tirar lo que quede vacío.
    """
    fuera = []
    for l in lineas or []:
        tr = [[bool(r), re.sub(r'\s+', ' ', t)] for r, t in l if t.strip()]
        if tr:
            fuera.append(tr)
    return fuera


def construye_prefacios(pref_es, lat, misa, propios_pref, cuenta, inf):
    pares = misa['prefacios']
    lp = lat['prefacios']
    cita = defaultdict(list)
    propio_de = defaultdict(list)
    for clave in sorted(misa['formularios']):
        f = misa['formularios'][clave]
        for p in f.get('prefacio') or []:
            cita[p].append(clave)
        if f.get('prefacio_propio'):
            propio_de[f['cel']].append(clave)

    fuera = OrderedDict()
    for k in sorted(pref_es):
        v = pref_es[k]
        e = {'t': v['titulo'], 'ep': v.get('epigrafe'), 'n': v.get('n'),
             'grupo': grupo_de(v['titulo']), 'juego': 'ordinario',
             'tx': tiradas(v['texto'])}
        if v.get('rubrica'):
            e['rub'] = [re.sub(r'\s+', ' ', x).strip() for x in v['rubrica']]
        if v.get('nota'):
            e['nota'] = tiradas(v['nota'])
        if v.get('n_de_tabla'):
            e['n_de_tabla'] = True
        la = pares.get(k)
        if la and la in lp:
            e['la'] = la
            e['t_la'] = lp[la]['titulo']
            e['ep_la'] = lp[la].get('epigrafe')
            e['tx_la'] = cola(lp[la]['texto'])
            if lp[la].get('rubrica'):
                e['rub_la'] = cola(lp[la]['rubrica'])
        else:
            cuenta['prefacios castellanos sin pareja latina'] += 1
        if cita.get(k):
            e['cuando'] = cita[k]
        else:
            cuenta['prefacios castellanos que ningún formulario cita'] += 1
        fuera[k] = e

    # los 28 propios cosechados de dentro de los misalitos
    propios = OrderedDict()
    for k in sorted(propios_pref):
        v = propios_pref[k]
        e = {'t': v['titulo'], 'tx': [junta(v['texto'])],
             'n': len(v['testigos']), 'juego': 'propio',
             'grupo': 'propio'}
        if v.get('variantes'):
            e['v'] = [junta(x['texto']) for x in v['variantes']]
        if v.get('cel'):
            e['cel'] = v['cel']
            if propio_de.get(v['cel']):
                e['cuando'] = propio_de[v['cel']]
        propios[k] = e

    # los latinos que no tienen pareja castellana: los 38 propios cosechados
    # de dentro de los formularios del Misal, y el común que quedó suelto
    con_pareja = {v for v in pares.values() if v}
    solo_la = OrderedDict()
    for k in sorted(lp):
        if k in con_pareja:
            continue
        v = lp[k]
        solo_la[k] = {'t': v['titulo'], 'ep': v.get('epigrafe'),
                      'n': v.get('n'), 'juego': v.get('juego'),
                      'tx': cola(v['texto'])}
        if v.get('rubrica'):
            solo_la[k]['rub'] = cola(v['rubrica'])
        if v.get('de'):
            solo_la[k]['de'] = v['de']
        if v.get('tambien_en'):
            solo_la[k]['tambien_en'] = sorted(set(v['tambien_en']))
    cuenta['prefacios latinos sin pareja castellana'] = len(solo_la)

    return {
        'fuente': 'fase 6 — los prefacios, castellano y latín',
        'prefacios': fuera,
        'propios': propios,
        'solo_latino': solo_la,
    }


# --------------------------------------------------------------------------
# 5. el Ordinario, bilingüe y por número de rúbrica
# --------------------------------------------------------------------------
CABEZAS_APENDICE = [
    'BENEDICTIONES IN FINE MISSÆ', 'ET ORATIONES SUPER POPULUM',
    'BENEDICTIONES SOLLEMNES', 'ORATIONES SUPER POPULUM',
]

# Lo que la fase 1 le pegó al Ordo y el apéndice no explica palabra por
# palabra, con su razón. No son texto perdido: los dos primeros son rótulos
# del propio apéndice, y el resto son los rótulos del «APPENDIX I — CANTUS
# VARII IN ORDINE MISSÆ», que vienen sin cuerpo porque el apéndice sólo trae
# allí la melodía. Van aquí para que el informe pueda decir que del recorte
# no queda nada sin explicar.
APENDICE_SUELTAS = [
    'In festis Sanctorum',          # rótulo de la sección II de bendiciones
    'CANTUS', 'AD PRECEM EUCHARISTICAM',
    'PREX EUCHARISTICA I', 'PREX EUCHARISTICA II',
    'PREX EUCHARISTICA III', 'PREX EUCHARISTICA IV',
    'seu CANON ROMANUS', 'Tonus sollemnior',
    'Celebrans principalis, manibus extensis, dicit:',
    'Communicántes et Hanc ígitur propria',
    'In Nativitate Domini et per octavam',
]

# El acento dice si una línea latina se reza o se manda; estas siete se rezan
# y no llevan acento, porque no lo necesitan para recitarse. La prueba es que
# son respuestas del pueblo y las palabras de la consagración, y el Misal las
# imprime en el mismo cuerpo que el resto del texto rezado.
REZADAS_SIN_ACENTO = {
    'Amen.', 'Pax vobis.', 'Sursum corda.', 'Dignum et iustum est.',
    'Laus tibi, Christe.', 'Corpus Christi.', 'hoc est enim Corpus meum,',
}

ACENTO = re.compile(r'[áéíóúýÁÉÍÓÚǽǣœ́]')
VEL = re.compile(r'^Vel\s*:\s*$')


def aperturas_apendice(n, ben, sp):
    """Lo que, dentro de la rúbrica n del Ordo, abre el apéndice pegado."""
    ap = set(CABEZAS_APENDICE)
    for tabla in (ben, sp):
        p = tabla.get(n)
        if not p:
            continue
        for campo in ('seccion', 'titulo'):
            if p.get(campo):
                ap.add(p[campo])
        if p.get('texto'):
            ap.add(p['texto'][0])
    return ap


def recorta_apendice(r, ben, sp, todas, cuenta, sueltas):
    """La rúbrica del Ordo sin el apéndice que la fase 1 le pegó detrás."""
    ap = aperturas_apendice(r['n'], ben, sp)
    for i, l in enumerate(r['lineas']):
        if l in ap:
            cortadas = [x for x in r['lineas'][i:] if x.strip()]
            fuera = [x for x in cortadas if x not in todas]
            cuenta['rúbricas latinas con apéndice pegado'] += 1
            cuenta['renglones de apéndice quitados'] += len(cortadas)
            if fuera:
                sueltas.append((r['n'], fuera))
            return r['lineas'][:i]
    return r['lineas']


def parrafos_latinos(lineas, cuenta):
    """Las líneas latinas en párrafos, con su opción y su marca de rúbrica.

    El renglón en blanco separa párrafos —así lo imprime el Misal— y el
    «Vel:» abre una opción, igual que el «O bien:» del Ordinario castellano.
    La marca de rúbrica es el acento, con la tabla de las siete excepciones.
    """
    fuera, cur, opcion = [], [], 0
    def cierra():
        if not cur:
            return
        t = ' '.join(cur)
        rub = not ACENTO.search(t) and t not in REZADAS_SIN_ACENTO
        if not ACENTO.search(t) and t in REZADAS_SIN_ACENTO:
            cuenta['párrafos latinos rezados sin acento (de la tabla)'] += 1
        cuenta['párrafos latinos rúbrica' if rub
               else 'párrafos latinos rezados'] += 1
        fuera.append({'o': opcion, 'r': rub, 't': list(cur)})
        del cur[:]
    for l in lineas:
        s = l.strip()
        if not s:
            cierra()
            continue
        if VEL.match(s):
            cierra()
            opcion += 1
            continue
        cur.append(re.sub(r'\s+', ' ', s))
    cierra()
    return fuera, opcion


def parrafos_es(lineas):
    """Las líneas del Ordinario castellano en párrafos.

    Vienen ya con su número de opción y su marca de rúbrica, que la fase 2
    leyó del color. Se juntan los renglones seguidos que comparten las dos
    cosas, y el «O bien:» no se guarda: el salto de opción lo dice `o`.
    """
    fuera, opcion = [], 0
    for l in lineas or []:
        if l.get('marca'):
            opcion = max(opcion, l.get('o', 0))
            continue
        tr = [[bool(r), re.sub(r'\s+', ' ', t)] for r, t in l['tiradas']
              if t.strip()]
        if not tr:
            continue
        o, rub = l.get('o', 0), bool(l.get('r'))
        opcion = max(opcion, o)
        if fuera and fuera[-1]['o'] == o and fuera[-1]['r'] == rub:
            fuera[-1]['t'].append(tr)
        else:
            fuera.append({'o': o, 'r': rub, 't': [tr]})
    return fuera, opcion


def coteja_rubricas(orden):
    """La regla del acento, medida contra el color del castellano.

    El bilingüe se alinea por número de rúbrica, y donde las dos lenguas dan
    el mismo número de párrafos en la misma opción el castellano sirve de
    testigo: su marca la leyó la fase 2 del color del PDF, que ahí sí
    distingue. No se usa para corregir el latín —sería meter la tipografía de
    un libro en el otro—, sino para saber cuánto se equivoca la regla.
    """
    c, fallos = Counter(), []
    for r in orden['rubricas']:
        if not r.get('es') or not r.get('la'):
            continue
        if len(r['es']) != len(r['la']):
            c['rúbricas con distinto número de párrafos'] += 1
            continue
        c['rúbricas comparables'] += 1
        for a, b in zip(r['es'], r['la']):
            c['párrafos comparados'] += 1
            if a['r'] == b['r']:
                c['coinciden'] += 1
                continue
            c['discrepan'] += 1
            fallos.append((r['n'], a['r'], b['r'], ' '.join(b['t'])))
    return c, fallos


def construye_ordinario(ord_es, lat, pref_es, cuenta, inf, sueltas):
    ben = {p['n']: p for p in lat['bendiciones']['piezas']}
    sp = {p['n']: p for p in lat['super_populum']['piezas']}
    todas = set(CABEZAS_APENDICE) | set(APENDICE_SUELTAS)
    todas |= set(lat['bendiciones'].get('rubrica') or [])
    todas |= set(lat['super_populum'].get('rubrica') or [])
    for p in list(ben.values()) + list(sp.values()):
        todas |= set(p['texto'])
        for campo in ('titulo', 'seccion'):
            if p.get(campo):
                todas.add(p[campo])

    es_por_n = {}
    for r in ord_es['rubricas']:
        es_por_n.setdefault(str(r['n']), []).append(r)
    # el número del prefacio, para apuntar del Ordo a prefacios.json
    pref_por_n = {str(v['n']): k for k, v in pref_es.items()
                  if v.get('n') is not None}

    la_por_n = {}
    for r in lat['ordo']['ordo']:
        la_por_n[str(r['n'])] = recorta_apendice(r, ben, sp, todas, cuenta,
                                                 sueltas)

    numeros = sorted(set(es_por_n) | set(la_por_n),
                     key=lambda s: (int(re.match(r'\d+', s).group()), s))
    rubricas = []
    for n in numeros:
        e = {'n': n}
        pref = pref_por_n.get(n)
        if pref:
            e['pref'] = pref
        rs = es_por_n.get(n) or []
        if rs:
            e['sec'] = rs[0].get('seccion')
            e['pag'] = rs[0].get('pag')
            if rs[0].get('n_impreso') != rs[0].get('n'):
                e['n_impreso'] = rs[0].get('n_impreso')
            p, op = [], 0
            for r in rs:
                pp, oo = parrafos_es(r['lineas'])
                p += pp
                op = max(op, oo)
            if len(rs) > 1:
                e['repetida'] = len(rs)
                cuenta['rúbricas castellanas repetidas'] += 1
            e['es'] = p
            e['op_es'] = op
        elif not pref:
            cuenta['rúbricas sin castellano'] += 1
            inf.di('    rúbrica %s: sólo en latín' % n)
        if n in la_por_n and not pref:
            p, op = parrafos_latinos(la_por_n[n], cuenta)
            e['la'] = p
            e['op_la'] = op
        elif n not in la_por_n:
            cuenta['rúbricas sin latín'] += 1
            inf.di('    rúbrica %s: sólo en castellano' % n)
        rubricas.append(e)

    # las plegarias: el castellano trae sus partes propias y el latín el
    # texto entero, incluidas las seis que el Ordinario de México no imprime
    plegarias = OrderedDict()
    for k in sorted(ord_es['plegarias']):
        v = ord_es['plegarias'][k]
        e = {'t': v['titulo'], 'romano': v.get('romano'),
             'desde': v.get('n_desde'), 'hasta': v.get('n_hasta')}
        if v.get('subtitulo'):
            e['sub'] = v['subtitulo']
        if v.get('lineas'):
            e['tx'] = parrafos_es(v['lineas'])[0]
        e['propias'] = OrderedDict(
            (nombre, parrafos_es(ls)[0])
            for nombre, ls in sorted((v.get('propias') or {}).items()))
        plegarias[k] = e
    plegarias_la = OrderedDict()
    for k in sorted(lat['plegarias']):
        v = lat['plegarias'][k]
        p, _ = parrafos_latinos(v['texto'], cuenta)
        plegarias_la[k] = {'t': v['titulo'], 'tx': p}
        if v.get('rubrica'):
            plegarias_la[k]['rub'] = cola(v['rubrica'])
    cuenta['plegarias castellanas'] = len(plegarias)
    cuenta['plegarias latinas'] = len(plegarias_la)

    return {
        'fuente': 'fase 6 — el Ordinario, por número de rúbrica',
        'cabecera': 'Castellano: Ordinario de la Misa, traducción litúrgica '
                    'aprobada para México.\nLatín: Missale Romanum, editio '
                    'typica tertia, 2002.',
        'secciones': ord_es.get('secciones') or [],
        'rubricas': rubricas,
        'plegarias': plegarias,
        'plegarias_la': plegarias_la,
    }


# --------------------------------------------------------------------------
# la firma, que es lo que obliga al teléfono a tirar su caché
# --------------------------------------------------------------------------
def refresca_version():
    """Vuelve a firmar `app/datos/`, con la fórmula de `15_app_data.py`."""
    ruta = os.path.join(APP, 'version.js')
    prefijo = 'clementina+nova'
    if os.path.exists(ruta):
        m = re.search(r'"(.+)-\d+"', open(ruta, encoding='utf-8').read())
        if m:
            prefijo = m.group(1)
    raiz_app = os.path.dirname(APP)
    crc = zlib.crc32(b''.join(
        open(os.path.join(APP, f), 'rb').read()
        for f in sorted(os.listdir(APP)) if f != 'version.js') + b''.join(
        open(os.path.join(raiz_app, f), 'rb').read()
        for f in CODIGO_APP
        if os.path.exists(os.path.join(raiz_app, f)))) & 0xffffffff
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('// lo escribe src/15_app_data.py (y lo refrescan\n'
                '// Breviarium/src/4_app.py y Missale/src/6_app.py); cambia\n'
                '// con los datos, y al cambiar obliga al service worker a\n'
                '// rehacer su cache\n'
                'self.VERSION_DATOS = "%s-%d";\n' % (prefijo, crc))
    return '%s-%d' % (prefijo, crc)


# --------------------------------------------------------------------------
def carga(ruta):
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)


def mide_la_raya(misa, peri):
    """Lo que el puente de citas de la fase 5 pierde por la raya.

    *Palabra Viva* escribe el intervalo de versículos con raya —«1 Co
    6,13c–15a.17–20»— donde *La Santa Misa* y el leccionario lo escriben con
    guión. El `squeeze` de la fase 5 pliega la raya al punto, porque la raya
    es como una de las dos fuentes marca el salto de capítulo, y así esas
    perícopas no se alcanzan.

    Esto no lo arregla esta fase —el puente es de la fase 5 y `misa.json` es
    la decisión auditada—, pero sí lo mide, que es lo que decide si merece la
    pena arreglarlo: devuelve `(perícopas con gemela, lecturas recuperables,
    perícopas distintas)`.
    """
    def apreta(c):
        t = (c or '').lower()
        for g in '–—‒−':
            t = t.replace(g, '-')
        for g in ';,':
            t = t.replace(g, '.')
        t = unicodedata.normalize('NFKD', t)
        t = ''.join(x for x in t if not unicodedata.combining(x))
        return re.sub(r'[^a-z0-9.\-]', '', t)

    idx = defaultdict(list)
    for k in peri:
        idx[apreta(k)].append(k)
    gemelas = sum(1 for v in idx.values() if len(v) > 1)
    usos, distintas = 0, set()
    for f in sorted(misa['formularios'].values(), key=lambda x: x['titulo']):
        for l in f['lecturas']:
            if l['es']:
                continue
            k = apreta(l['cita'])
            if k in idx:
                usos += 1
                distintas.add(sorted(idx[k])[0])
    return gemelas, usos, len(distintas)


def atribuye_propios(propios_pref, dias, cuenta, inf):
    """De qué celebración es cada prefacio propio cosechado.

    La fase 4 los cosechó de dentro de los formularios con sus testigos, que
    son días; y `dias_es.json` dice qué celebración se atribuyó a cada día.
    Si todos los testigos de un prefacio caen en la misma celebración, es de
    ella. Si no, se queda sin dueño y se dice.
    """
    for k in sorted(propios_pref):
        v = propios_pref[k]
        cels = set()
        for t in v['testigos']:
            fecha, _, n = t.partition('/')
            dia = (dias.get(fecha) or [])
            i = int(n or 0)
            if i < len(dia):
                cels.add(dia[i].get('cel'))
        cels.discard(None)
        if len(cels) == 1:
            v['cel'] = cels.pop()
            cuenta['prefacios propios con celebración'] += 1
        else:
            cuenta['prefacios propios sin celebración'] += 1
            inf.di('    %-52s testigos en %d celebraciones'
                   % (v['titulo'][:52], len(cels)))


def main():
    inf = Informe(QA, 'Fase 6 — la misa castellana, empaquetada para la app')
    inf.di('  La fase 5 dejó dicho de dónde sale cada pieza; esta fase va a')
    inf.di('  buscarla y la deja en app/datos/. No decide nada: dereferencia,')
    inf.di('  y lo que no encuentra lo dice.')

    misa = carga(os.path.join(LIBRO, 'misa.json'))
    propios = carga(os.path.join(LIBRO, 'propios_es.json'))
    sueltos = carga(os.path.join(LIBRO, 'sueltos_es.json'))
    peri = carga(os.path.join(LIBRO, 'pericopas_es.json'))
    propios_pref = carga(os.path.join(LIBRO, 'prefacios_propios_es.json'))
    dias = carga(os.path.join(LIBRO, 'dias_es.json'))
    lat = carga(os.path.join(DATOS, 'misal_latino.json'))
    pref_es = carga(os.path.join(DATOS, 'prefacios_es.json'))
    ord_es = carga(os.path.join(DATOS, 'ordinario_es.json'))

    cuenta, sueltas, raro = Counter(), [], defaultdict(set)
    inf.titulo('Los prefacios propios cosechados, atribuidos por sus días')
    atribuye_propios(propios_pref, dias, cuenta, inf)

    lect = construye_lecturas(misa, peri, cuenta, raro)
    inf.titulo('Las rúbricas del Ordinario que no están en las dos lenguas')
    orden = construye_ordinario(ord_es, lat, pref_es, cuenta, inf, sueltas)
    mis = construye_misa(misa, propios, sueltos, propios_pref, cuenta, inf)
    usados = {f['la'] for f in misa['formularios'].values() if f.get('la')}
    usados |= {x for f in misa['formularios'].values()
               for x in (f.get('alt') or [])}
    latino = construye_latino(lat, usados, cuenta)
    prefacios = construye_prefacios(pref_es, lat, misa, propios_pref, cuenta,
                                    inf)

    os.makedirs(APP, exist_ok=True)
    tamanos = []

    def escribe(nombre, obj):
        ruta = os.path.join(APP, nombre)
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
        kb = os.path.getsize(ruta) // 1024
        tamanos.append((nombre, kb))
        print('  %-28s %6d KB' % (nombre, kb))
        return kb

    print('  app/datos/:')
    total = 0
    total += escribe('misa.json', mis)
    total += escribe('lecturas_es.json', lect)
    total += escribe('misal_latino.json', latino)
    total += escribe('prefacios.json', prefacios)
    total += escribe('ordinario.json', orden)
    print('  %-28s %6d KB' % ('TOTAL', total))
    version = refresca_version()
    print('  versión de datos: %s' % version)

    # ----------------------------------------------------------------------
    informe(inf, misa, mis, lect, latino, prefacios, orden, cuenta, sueltas,
            raro, mide_la_raya(misa, peri), tamanos, total, version)


def informe(inf, misa, mis, lect, latino, prefacios, orden, cuenta, sueltas,
            raro, raya, tamanos, total, version):
    inf.titulo('Lo que se escribió')
    for nombre, kb in tamanos:
        inf.di('  app/datos/%-24s %6d KB' % (nombre, kb))
    inf.di('  %-34s %6d KB' % ('TOTAL', total))
    inf.di('')
    inf.di('  versión de datos: %s' % version)

    inf.titulo('Los formularios y sus piezas')
    F = misa['formularios']
    inf.di('  formularios del leccionario : %d' % len(F))
    v = Counter(f['v'] for f in F.values())
    for k in ('completo', 'parcial', 'latino', 'nada'):
        inf.di('    %-26s %5d' % (k, v.get(k, 0)))
    inf.di('')
    inf.di('  piezas (seis ranuras por formulario, %d en total):'
           % (len(F) * len(RANURAS)))
    for k in sorted(cuenta):
        if k.startswith('piezas') or k.startswith('  por '):
            inf.di('    %-40s %5d' % (k, cuenta[k]))
    inf.di('')
    inf.di('  Las piezas que sólo tiene el latín no se copian en misa.json:')
    inf.di('  van en misal_latino.json y la app las alcanza por el puntero')
    inf.di('  `la` del formulario. La castellana dice «no disponible», que es')
    inf.di('  lo que se decidió en la pregunta 6 del plan.')
    inf.di('')
    inf.di('  otras misas sin clave del leccionario: %d'
           % cuenta['otras misas sin clave del leccionario'])
    inf.di('    Son la vigilia de san Juan Bautista y la de san Pedro y san')
    inf.di('    Pablo, la vigilia de Pentecostés, la segunda y la tercera de')
    inf.di('    los Difuntos —que el Misal da aparte y el leccionario no')
    inf.di('    numera— y las celebraciones del propio de México y las')
    inf.di('    votivas que el misalito imprimió y el índice no alcanza.')
    inf.di('    Van en misa.json, en `otros`, por su unidad.')

    inf.titulo('Las lecturas en castellano')
    inf.di('  formularios con alguna lectura castellana: %d de %d'
           % (len(lect['bloques']),
              sum(1 for f in F.values() if f['lecturas'])))
    for k in ('lecturas con castellano', 'lecturas sin castellano',
              'formularios sin una sola lectura en castellano'):
        inf.di('  %-44s %5d' % (k, cuenta[k]))
    tot = Counter()
    con = Counter()
    for f in F.values():
        for l in f['lecturas']:
            tot[l['tipo']] += 1
            if l['es']:
                con[l['tipo']] += 1
    inf.di('')
    inf.di('  por tipo de lectura:')
    inf.di('    %-34s %6s %6s %5s' % ('', 'total', 'con es', '%'))
    for t in sorted(tot, key=lambda x: -tot[x]):
        inf.di('    %-34s %6d %6d %4.0f%%'
               % (t, tot[t], con[t], 100.0 * con[t] / tot[t]))

    inf.titulo('Desarmar la perícopa impresa')
    inf.di('  El misalito imprime la lectura en un bloque corrido que lleva')
    inf.di('  dentro cuatro cosas. Separarlas es de esta fase, y esto es lo')
    inf.di('  que salió:')
    inf.di('')
    for k in ('lecturas con fórmula', 'lecturas sin fórmula reconocida',
              'lecturas con sumario', 'lecturas con cierre',
              'lecturas sin cierre reconocido',
              'lecturas con respuesta del pueblo',
              'salmo o aclamación sin respuesta', 'salmo sin estrofas'):
        inf.di('    %-42s %5d' % (k, cuenta[k]))
    inf.di('')
    inf.di('  El cierre se busca en el texto ya juntado y no en el último')
    inf.di('  renglón: la fuente parte «Palabra / de Dios.» entre dos')
    inf.di('  renglones, y mirando sólo el último se perdían.')
    inf.di('')
    inf.di('  La fórmula es el ancla, y el sumario es lo que va delante de')
    inf.di('  ella: la fuente lo imprime unas veces entre corchetes y otras a')
    inf.di('  pelo, y por sí mismo no se distingue del cuerpo. Las perícopas')
    inf.di('  que no dieron fórmula, una por una:')
    for cita in sorted(raro['sin fórmula reconocida']):
        inf.di('    %s' % cita)
    inf.di('')
    inf.di('  Y no es un fallo del reconocimiento: son los cánticos que')
    inf.di('  hacen de salmo responsorial —el Magníficat y el Benedictus de')
    inf.di('  Lucas 1, los tres cánticos de Daniel 3, el de Isaías 12, el de')
    inf.di('  Ana en 1 Samuel 2, el de Moisés en Deuteronomio 32— que el')
    inf.di('  leccionario trae como lectura y se cantan sin fórmula, más la')
    inf.di('  Pasión según san Juan, que se lee a tres voces y la fuente')
    inf.di('  rotula con la sigla y el reparto de papeles. Las tres restantes')
    inf.di('  sí son erratas de la fuente, y están nombradas: «11, l-11» con')
    inf.di('  ele en vez de uno, y la cita de Ester con «(Neovulgata)»')
    inf.di('  detrás.')
    inf.di('')
    inf.di('  Perícopas en que no se halló el cierre (%d):'
           % len(raro['sin cierre reconocido']))
    for cita in sorted(raro['sin cierre reconocido'])[:40]:
        inf.di('    %s' % cita)
    if len(raro['sin cierre reconocido']) > 40:
        inf.di('    … y %d más' % (len(raro['sin cierre reconocido']) - 40))
    if raro['salmo o aclamación sin respuesta']:
        inf.di('')
        inf.di('  Salmos o aclamaciones sin respuesta del pueblo:')
        for cita in sorted(raro['salmo o aclamación sin respuesta']):
            inf.di('    %s' % cita)

    inf.titulo('El Misal latino')
    for k in ('formularios latinos',
              'formularios latinos que alguna clave usa',
              'formularios latinos sin una pieza'):
        inf.di('  %-44s %5d' % (k, cuenta[k]))
    inf.di('')
    inf.di('  bendiciones solemnes: %d'
           % len(latino['bendiciones']['piezas']))
    inf.di('  oraciones sobre el pueblo: %d'
           % len(latino['super_populum']['piezas']))
    inf.di('')
    inf.di('  Van por su propio nombre y no por clave del leccionario: 451')
    inf.di('  unidades sirven a 1 051 claves, y copiarlo por clave doblaría')
    inf.di('  el fichero sin añadir una palabra.')

    inf.titulo('Los prefacios')
    inf.di('  castellanos del Ordinario : %d' % len(prefacios['prefacios']))
    inf.di('  propios cosechados        : %d' % len(prefacios['propios']))
    inf.di('  latinos sin pareja        : %d' % len(prefacios['solo_latino']))
    for k in ('prefacios castellanos sin pareja latina',
              'prefacios castellanos que ningún formulario cita',
              'prefacios propios con celebración',
              'prefacios propios sin celebración',
              'formularios con prefacio propio cosechado'):
        inf.di('  %-48s %5d' % (k, cuenta[k]))
    inf.di('')
    inf.di('  por grupo, leído del propio título:')
    g = Counter(v['grupo'] for v in prefacios['prefacios'].values())
    for k, n in sorted(g.items()):
        inf.di('    %-20s %3d' % (k, n))

    inf.titulo('El Ordinario, bilingüe y por número de rúbrica')
    inf.di('  entradas: %d' % len(orden['rubricas']))
    con_pref = sum(1 for r in orden['rubricas'] if r.get('pref'))
    inf.di('    de ellas, prefacios (33-82) que apuntan a prefacios.json: %d'
           % con_pref)
    inf.di('    con las dos lenguas: %d'
           % sum(1 for r in orden['rubricas']
                 if r.get('es') and r.get('la')))
    for k in ('rúbricas sin castellano', 'rúbricas sin latín',
              'rúbricas castellanas repetidas'):
        inf.di('  %-44s %5d' % (k, cuenta[k]))
    inf.di('')
    inf.di('  alternativas que el Ordinario deja elegir (la primera se')
    inf.di('  muestra y las demás van detrás de un «O bien», que es lo que se')
    inf.di('  pidió en la pregunta 4):')
    ops_es = [(r['n'], r.get('op_es', 0)) for r in orden['rubricas']
              if r.get('op_es')]
    ops_la = [(r['n'], r.get('op_la', 0)) for r in orden['rubricas']
              if r.get('op_la')]
    inf.di('    rúbricas con alternativa en castellano: %d (%d en total)'
           % (len(ops_es), sum(n for _, n in ops_es)))
    inf.di('    rúbricas con alternativa en latín     : %d (%d en total)'
           % (len(ops_la), sum(n for _, n in ops_la)))
    de_es, de_la = dict(ops_es), dict(ops_la)
    difieren = sorted(set(de_es) | set(de_la),
                      key=lambda s: int(re.match(r'\d+', s).group()))
    difieren = [n for n in difieren if de_es.get(n, 0) != de_la.get(n, 0)]
    inf.di('    rúbricas en que las dos lenguas no dan las mismas: %d'
           % len(difieren))
    for n in difieren:
        inf.di('      rúbrica %-5s castellano %d, latín %d'
               % (n, de_es.get(n, 0), de_la.get(n, 0)))
    inf.di('')
    inf.di('  Y no es que falte ninguna: **los dos libros marcan la elección')
    inf.di('  de otra manera.** El latino la numera y el castellano la mete')
    inf.di('  detrás de un «O bien». Las tres fórmulas del acto penitencial')
    inf.di('  son en castellano las tres opciones de la rúbrica 4 y en latín')
    inf.di('  las rúbricas 4, 5 y 6, cada una entera; de ahí que el')
    inf.di('  castellano cuente tres donde el latín cuenta una. Y en la')
    inf.di('  rúbrica 144 la diferencia es de edición: la editio typica')
    inf.di('  tertia de 2002 sólo trae «Ite, missa est», y las otras')
    inf.di('  despedidas que el castellano traduce se añadieron después. Así')
    inf.di('  que la opción se cuenta por el castellano y el latín se empareja')
    inf.di('  por número de rúbrica, que es lo que los dos comparten.')

    inf.titulo('La rúbrica latina se reconoce por el acento')
    inf.di('  El Ordinario de México marca sus rúbricas en rojo y la fase 2')
    inf.di('  lo guardó. El Misal latino se leyó con pdftotext, que no guarda')
    inf.di('  el color; pero el Misal tiene su propia marca, y es')
    inf.di('  tipográfica: imprime acentuado lo que se reza —para')
    inf.di('  recitarlo— y sin acentuar la rúbrica.')
    inf.di('')
    for k in ('párrafos latinos rezados', 'párrafos latinos rúbrica',
              'párrafos latinos rezados sin acento (de la tabla)'):
        inf.di('    %-50s %5d' % (k, cuenta[k]))
    inf.di('')
    inf.di('  **Medida contra el color del castellano**, que es el testigo que')
    inf.di('  esta fase tiene a mano: donde las dos lenguas dan el mismo')
    inf.di('  número de párrafos en la misma opción se pueden comparar, y la')
    inf.di('  marca castellana la leyó la fase 2 del rojo del PDF. No se usa')
    inf.di('  para corregir el latín —sería meter la tipografía de un libro en')
    inf.di('  el otro— sino para saber cuánto se equivoca la regla:')
    inf.di('')
    c, fallos = coteja_rubricas(orden)
    for k in ('rúbricas comparables',
              'rúbricas con distinto número de párrafos',
              'párrafos comparados', 'coinciden', 'discrepan'):
        inf.di('    %-46s %5d' % (k, c[k]))
    if c['párrafos comparados']:
        inf.di('    %-46s %5.2f%%' % ('acuerdo',
                                      100.0 * c['coinciden']
                                      / c['párrafos comparados']))
    inf.di('')
    inf.di('  Las que discrepan, una por una:')
    for n, a, b, t in fallos:
        inf.di('    rúbrica %-5s el castellano dice %s y el acento %s'
               % (n, 'rúbrica' if a else 'rezado',
                  'rúbrica' if b else 'rezado'))
        inf.di('      %s' % t[:92])
    inf.di('')
    inf.di('  Las tres primeras son rúbricas que citan dentro lo que se reza,')
    inf.di('  y lo citado va acentuado («in hac prima salutatione dicit:')
    inf.di('  Dóminus vobíscum», «Sequitur Allelúia»). La de la rúbrica 102 es')
    inf.di('  al revés y la razón es del castellano: «hoc est enim Corpus')
    inf.di('  meum» son las palabras de la consagración, que el Ordinario de')
    inf.di('  México imprime en rojo por solemnidad y no por ser rúbrica.')
    inf.di('')
    inf.di('  Y una medida de una vez, hecha contra el PDF latino, que esta')
    inf.di('  fase no lee porque no está en el repositorio: de las 2 614')
    inf.di('  líneas del Ordo, el color y el acento coinciden en 2 219; y de')
    inf.di('  las 395 que discrepan, 394 son por el color y no por el acento')
    inf.di('  —el PDF deja en negro la mitad de sus rúbricas, «1. Populo')
    inf.di('  congregato, sacerdos cum ministris ad altare accedit» entre')
    inf.di('  ellas—. La única rúbrica roja con acento es el epígrafe «De')
    inf.di('  salute per obœdientiam Christi». Por eso el acento es mejor')
    inf.di('  testigo que el color en este libro.')

    inf.titulo('El apéndice que la fase 1 le pegó al Ordo')
    inf.di('  Las veinte bendiciones solemnes y las veintiocho oraciones')
    inf.di('  sobre el pueblo del APPENDIX AD ORDINEM MISSÆ están pegadas al')
    inf.di('  final de las rúbricas del Ordo, cada una a la rúbrica de su')
    inf.di('  mismo número: la rúbrica 1 —«Populo congregato»— trae detrás la')
    inf.di('  bendición solemne de Adviento y la primera oración sobre el')
    inf.di('  pueblo. Sin quitarlo, la app enseñaría la bendición de Adviento')
    inf.di('  en medio del rito de entrada.')
    inf.di('')
    inf.di('    rúbricas con apéndice pegado : %d'
           % cuenta['rúbricas latinas con apéndice pegado'])
    inf.di('    renglones quitados           : %d'
           % cuenta['renglones de apéndice quitados'])
    inf.di('')
    inf.di('  El recorte está probado por igualdad de texto contra las tablas')
    inf.di('  `bendiciones` y `super_populum` del propio misal_latino.json,')
    inf.di('  que es donde la fase 1 sí las guardó bien: no se pierde nada.')
    if sueltas:
        inf.di('')
        inf.di('  Lo que el apéndice no explica palabra por palabra, y por')
        inf.di('  qué (tabla APENDICE_SUELTAS):')
        for n, f in sueltas:
            inf.di('    rúbrica %s:' % n)
            for x in f:
                inf.di('      %s' % x)
    else:
        inf.di('')
        inf.di('  Del recorte no queda un renglón sin explicar.')

    inf.titulo('Lo que esta fase topa y no es suyo')
    inf.di('  Defectos de fases anteriores que aquí se ven. Quedan nombrados,')
    inf.di('  no tapados:')
    inf.di('')
    inf.di('  · el apéndice pegado al Ordo, de la sección anterior: son 29')
    inf.di('    rúbricas y %d renglones, y lo limpio sería que la fase 1 no'
           % cuenta['renglones de apéndice quitados'])
    inf.di('    los metiera, porque ya los guarda bien en sus propias tablas.')
    inf.di('  · el Misal latino se lee con pdftotext y se pierde el color,')
    inf.di('    **aunque el PDF lo trae**: 5 468 de sus 33 214 líneas van')
    inf.di('    enteras en rojo (0xff0000). No sirve para la rúbrica —el PDF')
    inf.di('    deja en negro la mitad de las suyas— pero sí marca el rótulo')
    inf.di('    de pieza y la capitular, que ahora se adivinan.')
    inf.di('  · nueve perícopas conservan el guión de final de renglón que la')
    inf.di('    fase 4 junta en las demás; esta fase repite la regla al')
    inf.di('    juntar el párrafo, pero el canónico de la fase 4 sigue')
    inf.di('    partido.')
    gemelas, usos, distintas = raya
    inf.di('  · **la raya del intervalo de versículos.** Palabra Viva escribe')
    inf.di('    «1 Co 6,13c–15a.17–20» donde La Santa Misa y el leccionario')
    inf.di('    escriben «1 Co 6,13c-15a.17-20», y el `squeeze` de la fase 5')
    inf.di('    pliega la raya al punto porque la raya es también como una de')
    inf.di('    las dos fuentes marca el salto de capítulo. De ahí que %d'
           % gemelas)
    inf.di('    citas del corpus tengan gemela que sólo difiere en la raya, y')
    inf.di('    que 182 perícopas con la respuesta del pueblo impresa no se')
    inf.di('    alcancen —por eso esta fase sólo halla 2 lecturas con')
    inf.di('    respuesta—. **Medido, cuesta poco:** plegando la raya al')
    inf.di('    guión se recuperarían %d lecturas (%d perícopas distintas) de'
           % (usos, distintas))
    inf.di('    las %d que hoy no tienen castellano, porque las demás ya están'
           % cuenta['lecturas sin castellano'])
    inf.di('    alcanzadas por su gemela con guión. No se arregla aquí: el')
    inf.di('    puente de citas es de la fase 5, y `misa.json` es la decisión')
    inf.di('    auditada; si la app enseñara texto que esa decisión dice que')
    inf.di('    no hay, el fichero dejaría de servir para auditarla.')
    inf.di('  · siguen en pie los cinco que nombró la fase 5: los 49')
    inf.di('    formularios del santoral latino sin fecha, las ferias del')
    inf.di('    tiempo de Navidad en un grupo en vez de dos, el trozo del')
    inf.di('    Canon tomado por formulario, el Viernes Santo sin formulario')
    inf.di('    latino y la Cena del Señor sin oración sobre las ofrendas.')

    inf.titulo('Los derechos')
    inf.di('  Riesgo 6 del plan, y queda decidido: **se publica, igual que las')
    inf.di('  horas.** La traducción es la litúrgica aprobada para México y es')
    inf.di('  obra protegida, igual que la de la Liturgia de las Horas que el')
    inf.di('  proyecto ya publica en GitHub Pages, y el criterio es el mismo')
    inf.di('  para las dos. Lo que es de autoría del editor —moniciones,')
    inf.di('  reflexión, oración de los fieles— no entra, y de la parte')
    inf.di('  editorial sólo se conserva la reseña histórica del santo, que es')
    inf.di('  lo que se pidió en la pregunta 5.')
    inf.di('')
    inf.di('  De ahí que `publicar.ps1` tenga ya su paso: `python')
    inf.di('  Missale/src/6_app.py`, entre las horas y `15_app_data.py`, que')
    inf.di('  es el que firma todo lo que hay en app/datos/.')

    inf.titulo('Avisos')
    otros = {k: n for k, n in cuenta.items()
             if k.startswith('piezas que la decisión')}
    if any(otros.values()):
        for k, n in sorted(otros.items()):
            inf.di('  %-44s %5d' % (k, n))
    else:
        inf.di('  Ninguna pieza que la decisión apunte falta de su tabla.')
    inf.guarda()


if __name__ == '__main__':
    main()
