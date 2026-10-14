# -*- coding: utf-8 -*-
"""Fase 3 — del latín clásico al eclesiástico.

El sitio imprime el latín en ortografía clásica —«iustitia», «eius»,
«caelis», y sin un solo acento—, y los libros litúrgicos lo imprimen de
otra manera: «justítia», «ejus», «cælis». Son tres cambios, y ninguno es
de adorno:

  la jota     la i que suena como consonante se escribe j, y así se lee
              sin tropezar: «e-jus», no «e-i-us»;
  la ligadura ae y oe son un diptongo y se imprimen æ y œ, salvo donde no
              lo son y entonces llevan diéresis: «Israël»;
  el acento   toda palabra de tres sílabas o más lleva agudo en la tónica,
              porque los libros están hechos para rezarse en voz alta por
              quien no sabe latín.

Los tres salen de donde ya estaban en este proyecto. El acento lo pone el
acentuador de `src/13_acentos.py`, que resuelve cada palabra por orden de
autoridad —el uso impreso de 52 000 formas, las cantidades vocálicas, las
terminaciones aprendidas— y deja constancia de por qué. La jota y la
diéresis salen de los mismos testigos: la Vulgata Clementina escribe «ejus»
donde la Nova Vulgata escribe «eius», y el proyecto tiene las dos, verso a
verso, así que para cada palabra hay un testigo que dice si su i es
consonante o no. Donde no hay testigo deciden tres reglas:

  1. i inicial ante vocal          «iam» -> «jam»
  2. prefijo + raíz de jota        «adiuva» -> «adjuva», y no «deitas»
  3. vocal + i + vocal             «eius» -> «ejus», «maior» -> «major»

y lo que ninguna alcanza se queda como está y aparece en el informe. Las
decisiones a mano van en `Enchiridion/datos/jota.csv`, que manda sobre todo
lo demás.

Los salmos de la Nova Vulgata no se tocan más que en el acento: esa edición
escribe «iustus» y «caeli» a propósito, y en la app el leccionario de la
Nova Vulgata se sirve igual, con su ortografía, mientras la Clementina lleva
la suya. La ortografía es de la edición; el acento es de quien reza.

    TRABAJO/piezas.json  ──▶  TRABAJO/piezas_ecl.json
    Enchiridion/datos/eclesiastico_qa.txt

    python Enchiridion/src/3_eclesiastico.py
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchiridion import DATOS, TRABAJO

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, 'src'))
import importlib.util

_spec = importlib.util.spec_from_file_location(
    'acentos', os.path.join(RAIZ, 'src', '13_acentos.py'))
acentos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(acentos)

PALABRA = re.compile('[' + acentos.LETRAS + ']+')

# Las páginas que conservan su ortografía: la Nova Vulgata es una edición
# moderna y escribe «iustus» y «caeli» porque quiere.
SIN_TOCAR = ('Psalmi/NovaVulgata',)

# Raíces de jota: lo que sigue a un prefijo y lleva i consonante. Salen de
# iacio, iungo, iuro, iuvo, iudico, iustus, iubeo, ius.
RAICES_J = ('iac', 'iec', 'iic', 'ic', 'iect', 'iung', 'iunct', 'iug',
            'iur', 'iuv', 'iud', 'iust', 'iuss', 'iub', 'iuvenc')
PREFIJOS = ('circum', 'trans', 'super', 'inter', 'sub', 'con', 'com', 'dis',
            'per', 'prae', 'pro', 'red', 'sur', 'ab', 'ad', 'de', 'in',
            'ob', 're', 'se', 'e')

# La i inicial ante vocal es consonante salvo en las formas de eo/ire y de
# is/ea/id, donde es vocal y hace sílaba: «ubicúmque íero» no es «jero».
# El perfecto de ire se escribe con la misma i: ii, iit, ierunt, ieram,
# iero, isse. Y «Ierúsalem» o «Ieremías» sí llevan jota, pero ésas las dice
# el testigo y no llegan aquí.
NO_J_INICIAL = re.compile(
    r'^(iis(dem|que)?|iidem|iens|ient\w*|iunt'
    r'|ier(o|is|it|imus|itis|int|am|as|at|amus|atis|ant|unt|e|im)'
    r'|iit|iimus|istis|isse|iturus|io|iota|ii+)$')


# ------------------------------------------------------------ los testigos
def clave(w):
    return acentos.clave(w)


def frases(x):
    """Las frases latinas de un JSON del proyecto.

    Se dejan fuera las que llevan cifras: las citas del leccionario vienen
    en castellano y con el nombre del libro abreviado —«Jn 1,1-18 Evangelio
    según san Juan»—, y ese «Jn» haría creer que la i de «in» es
    consonante. Costó un «jn prǿlio» en todo el devocionario.
    """
    if isinstance(x, str):
        if len(x) > 20 and x.count(' ') >= 2 and not re.search(r'\d', x):
            yield x
    elif isinstance(x, dict):
        for v in x.values():
            for f in frases(v):
                yield f
    elif isinstance(x, (list, tuple)):
        for v in x:
            for f in frases(v):
                yield f


def testigos_del_proyecto():
    """Para cada clave, qué i son consonante según el testigo del proyecto.

    Devuelve (si, no): `si` lleva clave -> posiciones de la j, y `no` las
    claves que el testigo escribe sin jota ninguna.

    El testigo es uno solo: la Vulgata Clementina del leccionario, que es
    el único texto latino del proyecto impreso con jotas —el Misal de 2002
    escribe «iustítiæ» y la Nova Vulgata «iustitiae», así que ninguno de
    los dos puede decir dónde NO va una jota—. Sus 24 000 formas traen las
    dos respuestas: «ejus» dice que ahí la i es consonante, y «Isaíæ» dice
    que ahí no lo es, que es la mitad que las reglas no sabrían.
    """
    si, no = {}, {}
    ruta = os.path.join(RAIZ, 'app', 'datos', 'lecturas_clementina.json')
    if os.path.exists(ruta):
        with io.open(ruta, encoding='utf-8') as fh:
            libro = json.load(fh)
        for frase in frases(libro):
            for w in PALABRA.findall(frase):
                if len(w) < 3:
                    continue
                k, mapa = acentos.clave_mapa(w)
                plano = acentos._plano(w)
                jotas = {i for i, c in enumerate(k)
                         if c == 'i' and plano[mapa[i]] == 'j'}
                if jotas:
                    si.setdefault(k, set()).update(jotas)
                elif 'i' in k:
                    no[k] = no.get(k, 0) + 1
    # el léxico de jotas que ya construyó la fase 9 del leccionario
    ruta = os.path.join(RAIZ, 'data', 'acentos_jota.csv')
    if os.path.exists(ruta):
        with io.open(ruta, encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh):
                cortes = {int(x) for x in r['cortes'].split() if x.strip()}
                if cortes:
                    si.setdefault(r['forma'], set()).update(cortes)
    for k in si:
        no.pop(k, None)
    return si, no


def carga_tablas_del_devocionario(act):
    """Pone encima del acentuador las tablas que hizo la fase 3a.

    No se tocan las del leccionario: se añaden las formas que no estaban,
    que son las 2 948 cantidades vocálicas de Morpheus que la fase 9 no
    guardó —su léxico va recortado al vocabulario de la Vulgata— y las
    jotas y los hiatos que el Breviario imprime y el leccionario no tenía.
    """
    puestas = Counter()
    for r in _tabla('acentos_uso.csv'):
        a = (r.get('indice') or '').strip()
        if a and r['forma'] not in act.uso:
            act.uso[r['forma']] = a if a == '-' else int(a)
            act.apar_uso[r['forma']] = int(r.get('apar_acento') or 0)
            puestas['uso'] += 1
    for r in _tabla('acentos_cantidades.csv'):
        a = (r.get('acento') or '').strip()
        if r['forma'] in act.cantidad or r['forma'] in act.cantidad_amb:
            continue
        if a.isdigit():
            act.cantidad[r['forma']] = int(a)
            puestas['cantidad'] += 1
        elif a:
            act.cantidad_amb.add(r['forma'])
            puestas['cantidad ambigua'] += 1
    for nombre, dest in (('hiato_uso.csv', act.hiato),
                         ('jota_uso.csv', act.jota)):
        for r in _tabla(nombre):
            cortes = {int(x) for x in r['cortes'].split() if x.strip()}
            if cortes and r['forma'] not in dest:
                dest[r['forma']] = cortes
                puestas[nombre.split('_')[0]] += 1
    return puestas


def _tabla(nombre):
    ruta = os.path.join(DATOS, nombre)
    if not os.path.exists(ruta):
        return []
    with io.open(ruta, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def mano():
    """Las decisiones a mano: clave -> posiciones, o '-' para dejarla en i."""
    ruta = os.path.join(DATOS, 'jota_mano.csv')
    if not os.path.exists(ruta):
        return {}
    salida = {}
    with io.open(ruta, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            v = (r['cortes'] or '').strip()
            salida[clave(r['forma'])] = ('-' if v == '-' else
                                         {int(x) for x in v.split()})
    return salida


# -------------------------------------------------------------- las reglas
def por_regla(k):
    """(posiciones de la j, nombre de la regla) para una clave sin testigo."""
    n = len(k)
    pos = set()
    reglas = []
    # 1. i inicial ante vocal
    if (n > 2 and k[0] == 'i' and k[1] in 'aeou'
            and not NO_J_INICIAL.match(k)):
        pos.add(0)
        reglas.append('inicial')
    # 2. prefijo + raíz de jota
    for pre in PREFIJOS:
        if not k.startswith(pre):
            continue
        resto = k[len(pre):]
        if len(resto) < 3 or resto[0] != 'i':
            continue
        if (any(resto.startswith(r) for r in RAICES_J)
                and (resto[1] in 'aeou' or resto.startswith('iic'))):
            pos.add(len(pre))
            reglas.append('prefijo')
        break
    # 3. vocal + i + vocal, con la u de qu/gu/su que no es vocal
    for m in re.finditer(r'(?=([aeou])i([aeou]))', k):
        i = m.start() + 1
        antes = k[:i]
        if re.search(r'[qgs]u$', antes):
            continue
        pos.add(i)
        reglas.append('entre vocales')
    return pos, '+'.join(sorted(set(reglas)))


# ------------------------------------------------------ analogía de tema
# El devocionario trae 16 000 formas latinas y 750 no las resuelve ninguna
# de las autoridades del acentuador: son vocativos y palabras que la
# Vulgata no usa («ángele», «Cherubíne», «suppéditas»). Para ésas el
# acentuador pone la penúltima por omisión, que acierta el 62 % de las
# veces.
#
# Se puede hacer mejor sin inventar nada, porque la cantidad de una sílaba
# es del tema y no de la desinencia: si «ángelus», «ángeli» y «ángelo»
# llevan el acento en la antepenúltima, la sílaba «ge» es breve, y
# «ángele» lo lleva donde ellas. Basta agrupar las 52 000 formas del uso
# por su tema —la palabra hasta el último núcleo— y preguntar al grupo.
#
# Medido dejando fuera cada forma y preguntando a las demás, sobre las
# formas que el acentuador no resuelve por terminación, acierta el 95,9 %
# cuando una respuesta dobla a la otra. Lo que no dobla no se decide: se
# queda como estaba y aparece en el informe.

MIN_ANALOGIA = 2.0


def indice_analogia(act):
    """tema -> Counter({2: penúltima, 3: antepenúltima}) del uso impreso."""
    idx = {}
    for forma, pos in act.uso.items():
        if pos == '-' or not isinstance(pos, int):
            continue
        _, _, nuc = act.analiza(forma)
        if len(nuc) < 3 or acentos.peso_penultima(forma, nuc) is not None:
            continue
        n = act._letra_a_nucleo(nuc, pos)
        if n not in (2, 3):
            continue
        tema = forma[:nuc[-1][0]]
        idx.setdefault(tema, Counter())[n] += act.apar_uso.get(forma, 1) or 1
    return idx


# ----------------------------------------------------------- la conversión
class Eclesiastico(object):

    def __init__(self):
        self.si, self.no = testigos_del_proyecto()
        self.mano = mano()
        self.act = acentos.acentuador()
        self.anadidas = carga_tablas_del_devocionario(self.act)
        # el Breviario escribe «adjuva» y «Michaëlis»: eso es un testigo de
        # la jota y del hiato tan bueno como la Clementina
        for k, v in self.act.jota.items():
            self.si.setdefault(k, set()).update(v)
            self.no.pop(k, None)
        self.hiato = self.act.hiato
        self.cuenta = Counter()
        self.reglas = {}        # clave -> (regla, puesta)
        self.sin_testigo = Counter()
        self.analog = indice_analogia(self.act)
        self.acento_mano = {}
        for r in _tabla('acentos_mano.csv'):
            a = (r.get('acento') or '').strip()
            if a:
                self.acento_mano[clave(r['forma'])] = (
                    a if a == '-' else int(a))
        self.por_analogia = {}
        self.sin_acento = Counter()
        self._cache = {}

    # -- jota -------------------------------------------------------------
    def jotas(self, w):
        k = clave(w)
        if 'i' not in k:
            return set(), 'sin i'
        if k in self.mano:
            v = self.mano[k]
            return (set() if v == '-' else v), 'mano'
        if k in self.si:
            return self.si[k], 'uso'
        if k in self.no:
            return set(), 'uso (sin jota)'
        pos, regla = por_regla(k)
        return pos, ('regla: ' + regla if pos else 'sin regla')

    def pon_jota(self, w):
        pos, fuente = self.jotas(w)
        self.cuenta['jota ' + fuente] += 1
        if not pos:
            # sólo se apunta lo que podría llevar jota y no la lleva: i
            # inicial ante vocal, o i entre dos vocales. Lo demás («grátia»,
            # «fília») no es candidato y llenaría el informe de ruido.
            k = clave(w)
            if (fuente == 'sin regla'
                    and (re.match(r'^i[aeou]', k)
                         or re.search(r'(?<![qgs]u)[aeou]i[aeou]', k))):
                self.sin_testigo[k] += 1
            return w
        k, mapa = acentos.clave_mapa(w)
        letras = list(w)
        for i in sorted(pos):
            if i >= len(mapa):
                continue
            j = mapa[i]
            if letras[j].lower() != 'i':
                continue
            letras[j] = 'J' if letras[j].isupper() else 'j'
        puesta = ''.join(letras)
        if fuente.startswith('regla') and puesta != w:
            self.reglas.setdefault(clave(w), (fuente, w, puesta))
        return puesta

    # -- ligadura ---------------------------------------------------------
    def liga(self, w):
        """ae -> æ, oe -> œ, y diéresis donde el diptongo no lo es."""
        k = clave(w)
        cortes = self.hiato.get(k)
        if cortes:
            self.cuenta['hiato'] += 1
            return self._dieresis(w, cortes)
        salida = []
        i = 0
        plano = acentos._plano(w)
        while i < len(w):
            par = plano[i:i + 2]
            if par in ('ae', 'oe') and i + 1 < len(w):
                alta = w[i].isupper()
                lig = 'æ' if par == 'ae' else 'œ'
                salida.append(lig.upper() if alta else lig)
                self.cuenta['ligadura'] += 1
                i += 2
                continue
            salida.append(w[i])
            i += 1
        return ''.join(salida)

    def _dieresis(self, w, cortes):
        k, mapa = acentos.clave_mapa(w)
        letras = list(w)
        for i in cortes:
            if i >= len(mapa):
                continue
            j = mapa[i]
            c = letras[j].lower()
            d = {'e': 'ë', 'i': 'ï', 'o': 'ö', 'u': 'ü', 'a': 'ä',
                 'y': 'ÿ'}.get(c)
            if d:
                letras[j] = d.upper() if letras[j].isupper() else d
        return ''.join(letras)

    # -- acento -----------------------------------------------------------
    def analogia(self, w):
        """La sílaba que el tema de la palabra dice, o None si no lo dice."""
        k, mapa, nuc = self.act.analiza(w)
        if len(nuc) < 3 or acentos.peso_penultima(w, nuc) is not None:
            return None
        inverso = {}
        for i, j in enumerate(mapa):
            inverso.setdefault(j, i)
        corte = inverso.get(nuc[-1][0])
        if corte is None:
            return None
        c = self.analog.get(k[:corte])
        if not c:
            return None
        gana = max(c, key=c.get)
        pierde = c.get(3 if gana == 2 else 2, 0)
        if pierde and c[gana] < MIN_ANALOGIA * pierde:
            return None
        return gana

    def acentua(self, w):
        """Como el acentuador del proyecto, y donde él no sabe, por analogía."""
        if w.isupper() and len(w) > 1:
            self.cuenta['acento versal'] += 1
            return w
        if acentos.desacentua(w) != unicodedata.normalize('NFC', w):
            self.cuenta['acento ya puesto'] += 1
            return w
        k = clave(w)
        if k in self.acento_mano:
            a = self.acento_mano[k]
            self.cuenta['acento a mano'] += 1
            if a == '-':
                return w
            _, _, nuc = self.act.analiza(w)
            return acentos.pon_agudo(w, self.act._nucleo_a_letra(nuc, a))
        letra, fuente = self.act.acento(w)
        if fuente in ('omision', 'cantidad ambigua'):
            n = self.analogia(w)
            if n:
                _, _, nuc = self.act.analiza(w)
                otra = self.act._nucleo_a_letra(nuc, n)
                if otra is not None:
                    self.por_analogia[acentos.clave(w)] = (
                        w, acentos.pon_agudo(w, otra),
                        'igual' if otra == letra else 'corrige')
                    letra, fuente = otra, 'analogía'
            else:
                self.sin_acento[acentos.clave(w)] += 1
        self.cuenta['acento ' + fuente] += 1
        return w if letra is None else acentos.pon_agudo(w, letra)

    # -- todo junto -------------------------------------------------------
    def palabra(self, w, ligar=True):
        llave = (w, ligar)
        if llave in self._cache:
            return self._cache[llave]
        puesta = w
        if ligar:
            puesta = self.pon_jota(puesta)
            puesta = self.liga(puesta)
        puesta = self.acentua(puesta)
        # el esqueleto de la palabra no puede cambiar: sólo i->j, ae->æ y
        # el agudo, y eso lo comprueba el propio acentuador al revés
        self._cache[llave] = puesta
        return puesta

    def texto(self, t, ligar=True):
        if not t:
            return t
        return PALABRA.sub(lambda m: self.palabra(m.group(0), ligar), t)


def igual_salvo_ortografia(a, b):
    """Que la conversión no haya perdido ni añadido letras."""
    def pelado(s):
        s = ''.join(acentos.AGUDAS.get(c, acentos.DIERESIS.get(c, c))
                    for c in unicodedata.normalize('NFC', s.lower()))
        s = unicodedata.normalize('NFD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c))
        return s.replace('æ', 'ae').replace('œ', 'oe').replace('j', 'i')
    return pelado(a) == pelado(b)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--muestra', help='convierte un texto y lo imprime')
    args = ap.parse_args()

    ecl = Eclesiastico()
    if args.muestra:
        print(ecl.texto(args.muestra))
        return

    entrada = os.path.join(TRABAJO, 'piezas.json')
    if not os.path.exists(entrada):
        sys.exit('no hay piezas: corre antes Enchiridion/src/2_piezas.py')
    with io.open(entrada, encoding='utf-8') as fh:
        libro = json.load(fh)

    roto = []
    for p in libro['piezas']:
        ligar = not any(x in p['pagina'] for x in SIN_TOCAR)
        p['ortografia'] = 'eclesiástica' if ligar else 'nova vulgata'
        p['tla'] = ecl.texto(p['tla'], ligar) if p['tla'] else p['tla']
        for b in p['b']:
            for ln in b['la']:
                for tr in ln:
                    antes = tr[1]
                    tr[1] = ecl.texto(antes, ligar)
                    if not igual_salvo_ortografia(antes, tr[1]):
                        roto.append((p['pagina'], antes, tr[1]))

    salida = os.path.join(TRABAJO, 'piezas_ecl.json')
    libro['fuente'] = 'fase 3 — piezas en ortografía eclesiástica'
    with io.open(salida, 'w', encoding='utf-8') as fh:
        json.dump(libro, fh, ensure_ascii=False, indent=1)

    qa = os.path.join(DATOS, 'eclesiastico_qa.txt')
    with io.open(qa, 'w', encoding='utf-8') as fh:
        fh.write('de dónde sale cada decisión\n')
        for k, v in sorted(ecl.cuenta.items(), key=lambda x: (-x[1], x[0])):
            fh.write('  %7d  %s\n' % (v, k))
        fh.write('\njotas puestas por regla y no por testigo (%d)\n'
                 % len(ecl.reglas))
        for k in sorted(ecl.reglas):
            regla, antes, puesta = ecl.reglas[k]
            fh.write('  %-22s %-22s %s\n' % (antes, puesta, regla))
        fh.write('\ni ante vocal que nadie resuelve y se queda en i (%d)\n'
                 % len(ecl.sin_testigo))
        for k, n in ecl.sin_testigo.most_common():
            fh.write('  %-24s %d\n' % (k, n))
        corrige = [k for k, v in ecl.por_analogia.items()
                   if v[2] == 'corrige']
        fh.write('\nacentos puestos por analogía de tema (%d formas, y en '
                 '%d de ellas\nla analogía corrige la penúltima que el '
                 'acentuador pondría por omisión)\n'
                 % (len(ecl.por_analogia), len(corrige)))
        for k in sorted(ecl.por_analogia):
            antes, puesta, que = ecl.por_analogia[k]
            fh.write('  %-24s %-24s %s\n' % (antes, puesta, que))
        fh.write('\nacentos que no resuelve nadie, y van a la penúltima por '
                 'omisión (%d formas)\n' % len(ecl.sin_acento))
        for k, n in ecl.sin_acento.most_common():
            fh.write('  %-24s %d\n' % (k, n))
        if roto:
            fh.write('\nCONVERSIONES QUE CAMBIAN LETRAS (%d)\n' % len(roto))
            for pag, a, b in roto[:200]:
                fh.write('  %s\n    %s\n    %s\n' % (pag, a, b))
    print('%s' % salida)
    print('informe: %s' % qa)
    if roto:
        print('¡OJO! %d conversiones cambian letras: mira el informe'
              % len(roto))


if __name__ == '__main__':
    main()
