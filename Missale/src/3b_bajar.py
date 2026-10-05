# -*- coding: utf-8 -*-
"""Fase 3b — traer misalcatolico.com, la segunda fuente castellana.

Los cien misalitos de la fase 3 son **una** cosecha: la de Guadalajara, de
junio de 2018 a octubre de 2026, y con el formulario que el editor eligió
para cada día. Este sitio publica lo mismo —la misa del día en la traducción
de México— pero **de 2016 a 2026**, y en los años viejos imprime *los dos*
formularios cuando el día da opción (feria *o* memoria), que es justo lo que
al deshacer los días de la fase 4 hubo que atribuir a mano.

No hay API: el sitio *es* el archivo, igual que el de las horas. Y tiene
índice, así que **no se adivinan las fechas**: se enumeran.

    /misal-catolico-anual          los once años
    /misal-AAAA                    los doce meses de un año
    /misal/AAAA/mesAAAA            los días de un mes
    /misa/D-de-mes-de-AAAA         el formulario de un día

Y al lado, las secciones que no son del día y valen por sí mismas:
`/ordinarios-de-la-misa`, `/prefacios-de-la-misa`, `/santoral/mes` (12),
los cinco libros de `/libro-de-los-salmos` y `/calendario/AAAA/mes`.

`robots.txt` del sitio permite el rastreo a todos los agentes, y nombra a
ClaudeBot entre ellos. Aun así se baja de uno en uno y con pausa: son unas
4 150 páginas y no hay prisa ninguna.

Se guarda **fuera del proyecto** —en `misal.TRABAJO/web`—, por lo mismo que
el volcado de los misalitos: 130 MB en una carpeta sincronizada con la nube
hacen que cada pasada compita con la subida de la anterior.

    python Missale/src/3b_bajar.py                 # baja o reanuda
    python Missale/src/3b_bajar.py --anios 2016 2017
    python Missale/src/3b_bajar.py --forzar        # vuelve a traerlo todo
    python Missale/src/3b_bajar.py --pausa 0.3     # más rápido, si urge
"""

import argparse
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import misal

import requests

SITIO = 'https://misalcatolico.com'
INDICE = '/misal-catolico-anual'
DESTINO = os.path.join(misal.TRABAJO, 'web')
MANIFIESTO = os.path.join(DESTINO, 'manifiesto.json')

# El navegador con el que se mira el sitio a mano. Se manda tal cual: pedirlo
# como un navegador es lo que hace que el servidor devuelva la página y no
# una pantalla de cortesía.
AGENTE = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
NMES = {m: i + 1 for i, m in enumerate(MESES)}

# Las secciones que no son de un día. Las dos primeras traen el texto; las
# demás son índices y se siguen un nivel.
SECCIONES = [
    '/ordinarios-de-la-misa',
    '/prefacios-de-la-misa',
    '/santoral',
    '/libro-de-los-salmos',
    '/calendario-liturgico',
]

ENLACE = re.compile(r'''href\s*=\s*["']([^"']+)["']''', re.I)


# --------------------------------------------------------------------------
# traer una página
# --------------------------------------------------------------------------

class Cliente:
    """Una sola conexión, con pausa, reintentos y memoria de lo que falla.

    Tres cosas que el sitio hace y hay que tolerarle:

      * **redirecciones a sí mismo.** Unas pocas URL que el índice del mes
        enlaza con normalidad contestan `301` hacia la misma dirección, una y
        otra vez. Se cortan a la tercera y se anotan como ausentes, que es lo
        que son; cuatro días medidos en la primera pasada (25-XII-2021,
        20 y 31-XII-2025 entre ellos);
      * **cortes de conexión**, que se reintentan con espera creciente;
      * **páginas sin formulario**, que llegan con `200` y hay que dejar que
        las cuente la fase 3c, no ésta: aquí sólo se guarda lo que llega.
    """

    def __init__(self, pausa=0.7, intentos=4):
        self.s = requests.Session()
        self.s.headers.update({
            'User-Agent': AGENTE,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'es-MX,es;q=0.9',
        })
        self.s.max_redirects = 3
        self.pausa = pausa
        self.intentos = intentos
        self.traidas = 0

    def trae(self, ruta):
        """El HTML de una ruta, o `None` con el motivo anotado."""
        url = SITIO + ruta if ruta.startswith('/') else ruta
        espera = 1.5
        for intento in range(1, self.intentos + 1):
            try:
                r = self.s.get(url, timeout=45)
            except requests.TooManyRedirects:
                return None, 'bucle de redirección'
            except requests.RequestException as e:
                if intento == self.intentos:
                    return None, type(e).__name__
                time.sleep(espera)
                espera *= 2
                continue
            self.traidas += 1
            # una pausa con algo de azar, para no marcar un compás exacto
            time.sleep(self.pausa * (0.7 + 0.6 * random.random()))
            if r.status_code == 200:
                return r.text, None
            if r.status_code in (429, 500, 502, 503, 504):
                if intento == self.intentos:
                    return None, 'HTTP %d' % r.status_code
                time.sleep(espera)
                espera *= 2
                continue
            return None, 'HTTP %d' % r.status_code
        return None, 'sin intentos'


# --------------------------------------------------------------------------
# el archivo de la web, para lo que el sitio vivo no sirve
# --------------------------------------------------------------------------
#
# **Diciembre no se puede bajar del sitio.** Todos los días de diciembre, de
# todos los años, contestan `301` hacia su propia dirección: un bucle. No es
# un freno ni una maqueta distinta, es un defecto del servidor, y se midió
# así: el índice del mes los enlaza con normalidad y los sirve el 404 cuando
# se le cambia una letra, de modo que la URL es la buena y la redirección es
# suya. Son 31 días por año —341 en total—, y son Adviento y Navidad.
#
# El archivo de la web los conserva. Su índice se pide **una vez** para todo
# el sitio (3 718 URL en una sola petición) en vez de preguntar día por día.
# Lo que vuelve es la plantilla *anterior* del sitio, que la fase 3c también
# sabe leer: por eso se guardan en el mismo sitio que los vivos.

CDX = ('http://web.archive.org/cdx/search/cdx?url=misalcatolico.com/misa/*'
       '&output=json&filter=statuscode:200&fl=timestamp,original'
       '&collapse=urlkey')
ARCHIVO = 'https://web.archive.org/web/%sid_/%s'
CACHE_CDX = os.path.join(DESTINO, 'cdx.json')


def indice_del_archivo(cl):
    """`{ruta del sitio: sello de tiempo}` de lo que el archivo guarda.

    Se pide una vez y **se guarda en disco**: es el mismo índice para todo el
    sitio, no cambia de una pasada a otra y pedirlo es lo que el archivo
    limita con más mano. Y se reintenta, como las páginas: pedido justo
    después de una tanda de peticiones contesta que no, y a los dos minutos
    contesta las 3 718 URL sin pestañear. Sin reintento, una pasada entera se
    quedaba sin diciembres por un `429` de un segundo.
    """
    if os.path.exists(CACHE_CDX):
        try:
            return json.load(open(CACHE_CDX, encoding='utf-8'))
        except (ValueError, OSError):
            pass
    filas, espera = None, 15.0
    for intento in range(1, 6):
        try:
            r = cl.s.get(CDX, timeout=180)
            r.raise_for_status()
            filas = r.json()
            break
        except (requests.RequestException, ValueError) as e:
            print('  el índice del archivo no vino (%s), intento %d de 5'
                  % (type(e).__name__, intento), flush=True)
            if intento == 5:
                return {}
            time.sleep(espera)
            espera *= 1.6
    out = {}
    for fila in filas[1:]:
        if len(fila) < 2:
            continue
        sello, url = fila[0], fila[1]
        ruta = url.split('misalcatolico.com', 1)[-1].split('?')[0].rstrip('/')
        if DIA.match(ruta):
            out[ruta] = sello
    try:
        json.dump(out, open(CACHE_CDX, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1, sort_keys=True)
    except OSError:
        pass
    return out


def recupera_del_archivo(rutas, cl, manif):
    """Trae del archivo de la web las rutas que el sitio vivo no dio.

    El archivo limita el paso y contesta `429` cuando se le pide de seguido,
    así que aquí la pausa es otra —más larga— y el `429` espera y reintenta
    en vez de darse por vencido.
    """
    if not rutas:
        return []
    print('\nel sitio no dio %d días; mirando el archivo de la web…'
          % len(rutas), flush=True)
    idx = indice_del_archivo(cl)
    if not idx:
        return [(r, 'sin índice del archivo') for r in rutas]
    tengo = [r for r in rutas if r in idx]
    print('  el archivo guarda %d de los %d' % (len(tengo), len(rutas)),
          flush=True)
    fallan = [(r, 'no está en el archivo') for r in rutas if r not in idx]

    for i, ruta in enumerate(tengo, 1):
        url = ARCHIVO % (idx[ruta], SITIO + ruta)
        espera = 10.0
        for intento in range(1, 6):
            try:
                r = cl.s.get(url, timeout=90)
            except requests.RequestException as e:
                if intento == 5:
                    fallan.append((ruta, 'archivo: ' + type(e).__name__))
                    break
                time.sleep(espera)
                espera *= 1.6
                continue
            if r.status_code == 200 and len(r.text) > 2000:
                guarda(ruta, r.text)
                manif[ruta] = {'bytes': len(r.text), 'archivo': idx[ruta]}
                break
            if r.status_code in (429, 503):
                if intento == 5:
                    fallan.append((ruta, 'archivo: HTTP %d' % r.status_code))
                    break
                time.sleep(espera)
                espera *= 1.6
                continue
            fallan.append((ruta, 'archivo: HTTP %d' % r.status_code))
            break
        time.sleep(2.5 + 1.5 * random.random())
        if i % 25 == 0 or i == len(tengo):
            print('  %d/%d del archivo' % (i, len(tengo)), flush=True)
    return fallan


def enlaces(html):
    """Las rutas del sitio que una página enlaza, sin el dominio."""
    out = []
    for h in ENLACE.findall(html or ''):
        h = h.strip()
        if h.startswith(SITIO):
            h = h[len(SITIO):]
        if h.startswith('/') and not h.startswith('//'):
            out.append(h.split('#')[0].rstrip('/') or '/')
    return out


# --------------------------------------------------------------------------
# dónde se guarda cada cosa
# --------------------------------------------------------------------------

DIA = re.compile(r'^/misa/(\d{1,2})-de-([a-zñáéíóú]+)-de-(\d{4})$', re.I)


def ruta_local(ruta):
    """El fichero donde va una ruta del sitio.

    Los días se guardan por fecha —`dias/2016/01/13.html`— y no por su URL,
    porque la fecha es la llave con la que la fase 3c los coteja contra los
    misalitos. Lo demás va con el nombre de su ruta.
    """
    m = DIA.match(ruta)
    if m:
        d, mes, a = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        if mes in NMES:
            return os.path.join(DESTINO, 'dias', '%04d' % a,
                                '%02d' % NMES[mes], '%02d.html' % d)
    nombre = ruta.strip('/').replace('/', '__') or 'raiz'
    sub = 'indices' if nombre.startswith('misal') else 'secciones'
    return os.path.join(DESTINO, sub, nombre + '.html')


def guarda(ruta, html):
    f = ruta_local(ruta)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(html)
    return f


# --------------------------------------------------------------------------
# la pasada
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--anios', nargs='*', type=int,
                    help='sólo estos años (por omisión, los que diga el índice)')
    ap.add_argument('--forzar', action='store_true',
                    help='vuelve a traer lo que ya esté bajado')
    ap.add_argument('--pausa', type=float, default=0.7,
                    help='segundos entre peticiones (0.7 por omisión)')
    ap.add_argument('--sin-secciones', action='store_true',
                    help='sólo los días, sin el ordinario ni los prefacios')
    ap.add_argument('--sin-archivo', action='store_true',
                    help='no mirar el archivo de la web por los diciembres')
    args = ap.parse_args()

    os.makedirs(DESTINO, exist_ok=True)
    cl = Cliente(pausa=args.pausa)
    manif = {}
    if os.path.exists(MANIFIESTO) and not args.forzar:
        try:
            manif = json.load(open(MANIFIESTO, encoding='utf-8'))
        except (ValueError, OSError):
            manif = {}

    def pide(ruta, releer=False):
        """Trae una ruta si hace falta; devuelve su HTML (de disco o de la red)."""
        f = ruta_local(ruta)
        if os.path.exists(f) and not args.forzar:
            if releer:
                return open(f, encoding='utf-8', errors='replace').read(), 'disco'
            return None, 'disco'
        html, mal = cl.trae(ruta)
        if html is None:
            manif[ruta] = {'falla': mal}
            return None, mal
        guarda(ruta, html)
        manif[ruta] = {'bytes': len(html)}
        return html, 'red'

    # --- el índice y los años ---------------------------------------------
    print('índice…', flush=True)
    html, de = pide(INDICE, releer=True)
    if html is None:
        sys.exit('no se pudo traer %s: %s' % (INDICE, de))
    anios = sorted({int(m) for m in re.findall(r'^/misal-(\d{4})$', '\n'.join(
        enlaces(html)), re.M)})
    if not anios:
        anios = sorted({int(m.group(1)) for m in
                        (re.match(r'^/misal-(\d{4})$', r) for r in enlaces(html))
                        if m})
    if args.anios:
        anios = [a for a in anios if a in args.anios]
    print('  %d años: %s' % (len(anios), ', '.join(str(a) for a in anios)),
          flush=True)

    # --- los meses de cada año y los días de cada mes ---------------------
    dias = []
    for a in anios:
        html, de = pide('/misal-%d' % a, releer=True)
        if html is None:
            print('  %d: no se pudo traer el año (%s)' % (a, de), flush=True)
            continue
        meses = [r for r in enlaces(html)
                 if re.match(r'^/misal/%d/[a-z]+%d$' % (a, a), r)]
        meses = sorted(set(meses), key=lambda r: NMES.get(
            re.sub(r'\d', '', r.rsplit('/', 1)[1]), 99))
        n0 = len(dias)
        for r in meses:
            hm, de = pide(r, releer=True)
            if hm is None:
                print('    %s: %s' % (r, de), flush=True)
                continue
            dias += [d for d in enlaces(hm) if DIA.match(d)]
        print('  %d: %d meses, %d días' % (a, len(meses), len(dias) - n0),
              flush=True)

    dias = sorted(set(dias), key=lambda r: (
        int(DIA.match(r).group(3)), NMES.get(DIA.match(r).group(2).lower(), 99),
        int(DIA.match(r).group(1))))

    # --- las secciones que no son del día ---------------------------------
    otras = []
    if not args.sin_secciones and not args.anios:
        for s in SECCIONES:
            hs, de = pide(s, releer=True)
            if hs is None:
                print('  %s: %s' % (s, de), flush=True)
                continue
            for r in enlaces(hs):
                if re.match(r'^/(santoral|calendario)/', r) or \
                   re.match(r'^/libro-[a-z-]*salmos[a-z-]*$', r):
                    otras.append(r)
        otras = sorted(set(otras))
        print('  %d páginas de sección' % len(otras), flush=True)

    # --- el cuerpo de la pasada -------------------------------------------
    cola = dias + otras
    pend = [r for r in cola
            if args.forzar or not os.path.exists(ruta_local(r))]
    print('\n%d páginas, %d por traer' % (len(cola), len(pend)), flush=True)
    if pend:
        seg = len(pend) * args.pausa
        print('  (unos %d min a %.1f s por página)' % (seg / 60 + 1, args.pausa),
              flush=True)

    fallan = []
    t0 = time.time()
    for i, r in enumerate(pend, 1):
        html, de = pide(r)
        if html is None and de != 'disco':
            fallan.append((r, de))
        if i % 100 == 0 or i == len(pend):
            hecho = i / len(pend)
            queda = (time.time() - t0) / max(hecho, 1e-9) * (1 - hecho)
            print('  %d/%d  (%.0f%%, quedan ~%d min, %d fallan)'
                  % (i, len(pend), 100 * hecho, queda / 60 + 0.5, len(fallan)),
                  flush=True)

    # --- los días que el sitio no sirve, del archivo de la web ------------
    if not args.sin_archivo:
        huerfanos = [r for r in dias if not os.path.exists(ruta_local(r))]
        fallan = [f for f in fallan if f[0] not in set(huerfanos)]
        fallan += recupera_del_archivo(huerfanos, cl, manif)

    with open(MANIFIESTO, 'w', encoding='utf-8') as fh:
        json.dump(manif, fh, ensure_ascii=False, indent=1, sort_keys=True)

    # --- lo que hay al terminar -------------------------------------------
    hay = sum(1 for r in dias if os.path.exists(ruta_local(r)))
    print('\n%d días en disco de %d enlazados, en %s' % (hay, len(dias), DESTINO))
    if fallan:
        print('\n%d que no se pudieron traer:' % len(fallan))
        for r, mal in fallan[:40]:
            print('   %-44s %s' % (r, mal))
        if len(fallan) > 40:
            print('   … y %d más (están en el manifiesto)' % (len(fallan) - 40))
        print('\nUna pasada más los reintenta: lo bajado no se vuelve a pedir.')


if __name__ == '__main__':
    main()
