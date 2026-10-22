# -*- coding: utf-8 -*-
"""La misa de un año: las oraciones de cada formulario que la app abre.

    python src/revision/misa.py                      # de hoy a un año
    python src/revision/misa.py 2026-10-21 2027-10-20

Dos pruebas, por fecha y por celebración, con lo que la app junta al abrir
el formulario (los propios mexicanos encima, y en el común la colecta del
santo):

  · que ninguna colecta, oración sobre las ofrendas o poscomunión nombre a un
    santo que la celebración no nombra: el 5 de octubre santa Faustina
    rezaba las de san Tranquilino Ubiarco, que el misalito imprime ese día;
  · que las misas de los santos traigan colecta en castellano.

Escribe `Missale/datos/revision_qa.txt`.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import date, timedelta

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESDE = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
HASTA = sys.argv[2] if len(sys.argv) > 2 else (
    date.fromisoformat(DESDE) + timedelta(days=364)).isoformat()


def carga(nombre):
    with open(os.path.join(RAIZ, 'app', 'datos', nombre), encoding='utf-8') as f:
        return json.load(f)


def sinac(t):
    t = unicodedata.normalize('NFKD', (t or '').lower())
    return ''.join(c for c in t if not unicodedata.combining(c))


# como en Missale/src/4_piezas.py: María y José no cuentan, los nombran
# fiestas que no los llevan en el título
NOMBRA = re.compile(r'\b(?:san|santa|santo|santos|beato|beata|beatos)\s+'
                    r'((?:[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)(?:\s+(?:de\s+)?'
                    r'[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)*)')
NO_NOMBRAN = {'maria', 'jose', 'virgen', 'nuestro', 'nuestra', 'senor'}


def nombrados(texto):
    salida = set()
    for m in NOMBRA.finditer(texto or ''):
        salida |= {w for w in re.findall(r'[a-z]+', sinac(m.group(1)))
                   if len(w) >= 4 and w not in NO_NOMBRAN}
    return salida


def main():
    cal, ind, misa = (carga('calendario.json'), carga('indice.json'),
                      carga('misa.json'))
    dia_de = {d['s']: d for sec in ind['secciones'] for g in sec['g']
              for d in g['d']}
    malos, sin, vistos = [], [], set()
    f, fin = date.fromisoformat(DESDE), date.fromisoformat(HASTA)
    while f <= fin:
        iso, f = f.isoformat(), f + timedelta(days=1)
        for slug, _, m in (cal['fechas'].get(iso) or {}).get('c') or []:
            d = dia_de.get(slug)
            if not d:
                continue
            for b in d['b']:
                fm = misa['formularios'].get(b['k']) or misa['otros'].get(b['k'])
                if not fm:
                    continue
                p = dict(fm.get('p') or {})
                mx = misa['otros'].get('st/' + slug)
                if mx and mx.get('p') and mx.get('u') != fm.get('u'):
                    p.update(mx['p'])
                # el común toma la colecta del santo (app.js, colectaDelSanto)
                if not (p.get('colecta') or {}).get('t'):
                    for b2 in d['b']:
                        g = misa['formularios'].get(b2['k'])
                        if (b2['k'] != b['k'] and g
                                and ((g.get('p') or {}).get('colecta') or {}).get('t')):
                            p['colecta'] = g['p']['colecta']
                            break
                titulo = (m or {}).get('t') or d['t']
                del_titulo = set(re.findall(r'[a-z]+', sinac(titulo + ' ' + d['t'])))
                for pz in ('colecta', 'ofrendas', 'poscomunion'):
                    t = (p.get(pz) or {}).get('t')
                    clave = (slug, b['k'], pz)
                    if clave in vistos:
                        continue
                    vistos.add(clave)
                    if not t:
                        if (pz == 'colecta' and (m or {}).get('k') == 's'
                                and fm.get('v') != 'nada'):
                            sin.append((iso, titulo[:45], b['k'][:30]))
                        continue
                    n = nombrados(t)
                    if n and not (n & del_titulo):
                        malos.append((iso, titulo[:45], pz, sorted(n), t[:80]))

    ruta = os.path.join(RAIZ, 'Missale', 'datos', 'revision_qa.txt')
    with open(ruta, 'w', encoding='utf-8') as q:
        q.write(f'Revisión de las oraciones de la misa del {DESDE} al {HASTA}\n')
        q.write('=' * 60 + '\n\n')
        q.write(f'Nombran a un santo que la celebración no nombra: {len(malos)}\n')
        for x in malos:
            q.write(f'  {x}\n')
        q.write(f'\nMisas de santos sin colecta en castellano: {len(sin)}\n')
        for x in sin:
            q.write(f'  {x}\n')
    print('nombran a un santo que la celebración no nombra:', len(malos))
    print('misas de santos sin colecta en castellano:', len(sin))
    print('informe en', ruta)


if __name__ == '__main__':
    main()
