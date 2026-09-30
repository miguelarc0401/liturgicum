"""Fase 9b - Construccion de los lexicos de acentuacion.

Lee lo que trajo 13a_crawl_acentos.py y escribe en data/ seis tablas, todas
editables y todas con su medida al lado:

  acentos_liturgico.csv     las formas con el acento que imprimen los libros
                            liturgicos, guardado como posicion exacta dentro de
                            la palabra; "-" en las que el uso deja desnudas
                            ("Israël", "Isaac", "Aaron")
  acentos_cantidades.csv    el acento que se deduce de las cantidades vocalicas
                            de Morpheus, para lo que el uso no cubre
  acentos_terminaciones.csv terminaciones aprendidas del propio uso, con su
                            numero de casos y su grado de acuerdo
  acentos_hiato.csv         donde 'ae'/'oe' no es diptongo sino hiato; sale de
                            la dieresis de la Clementina ("Israël", "introëas"),
                            que la Nova Vulgata no escribe
  acentos_jota.csv          donde la i no es vocal sino consonante; sale de la j
                            de la Clementina ("ejus" -> "eius"), que la Nova
                            Vulgata tampoco escribe
  acentos_discrepancias.csv las formas en que el uso liturgico y las cantidades
                            clasicas no coinciden, con la que se elige y por que

Y un informe, data/acentos_qa.txt, con cuatro comprobaciones que no se suponen:

  1. Uso contra regla de posicion. La regla "penultima trabada -> penultima" se
     contrasta con las 52 000 formas acentuadas del corpus liturgico.
  2. Uso contra cantidades clasicas. Se cuentan las discrepancias y se separan
     las de hiato (donde manda el uso: "María", "illíus") de las demas.
  3. Validacion por retencion. Se construye el lexico *sin* el Salterio, se
     acentua con el el Salterio de nuestra Clementina y se compara palabra por
     palabra con el Salterio acentuado de los libros liturgicos: mide la
     maquinaria sobre texto que no ha visto.
  4. El mismo Salterio con el lexico completo, donde no falta ningun dato: ahi
     una discrepancia ya no es falta de informacion, es un fallo de la
     maquinaria.

Uso:  python src/13b_build_acentos.py [--sin-retencion]
"""

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, "cache", "acentos")
DIVINUM = os.path.join(CACHE, "divinum", "web", "www")
MACRONS = os.path.join(CACHE, "macrons.txt")
HOLDOUT = os.path.join(CACHE, "retencion")


def modulo(nombre):
    """Importa un script cuyo nombre empieza por un numero."""
    spec = importlib.util.spec_from_file_location(
        "m" + re.sub(r"\W", "", nombre), os.path.join(ROOT, "src",
                                                      nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


A = modulo("13_acentos")

# Lineas de Divinum Officium que no son texto liturgico sino marcas del
# programa: cabeceras [Seccion], referencias !Ps 24:1, inclusiones &Gloria,
# @Psalterium/..., $Qui vivis, reglas ;;Semiduplex;; y rubricas entre /: :/
MARCAS = ("#", "[", "!", "&", "@", "$", "_", ";;", "/:", "%", "v.")
RUBRICA = re.compile(r"/:.*?:/")
# la w y la k no son latinas: descartan los apellidos checos de los propios
# bohemios (Wenceslaus, Novotny), cuyo agudo marca cantidad y no tonica
NO_LATINA = re.compile(r"[wWkK]")

MIN_SIN_MARCA = 5        # apariciones para creer que el uso la deja desnuda
PROP_SIN_MARCA = 0.90    # y proporcion de ellas sobre el total
DOMINANCIA = 0.80        # acuerdo minimo entre las apariciones acentuadas
TERM_CASOS = 25          # casos minimos para aprender una terminacion
TERM_ACUERDO = 0.995
TERM_LARGO = (3, 8)

# Hiatos que la Clementina no marca con dieresis y que el uso liturgico delata
# al poner el acento donde parecia haber diptongo: los nombres griegos en -laos
# ("Nicoláum", no "Nicólaum").
HIATO_CURADO = {
    "nicolaus": 6, "nicolaum": 6, "nicolai": 6, "nicolao": 6, "nicolae": 6,
    "archelaus": 7, "archelaum": 7, "archelai": 7, "archelao": 7,
    "menelaus": 6, "menelaum": 6, "menelai": 6, "menelao": 6,
}


# --------------------------------------------------------------------------
# utilidades sobre la clave
# --------------------------------------------------------------------------
def inverso(mapa):
    """letra de la palabra -> primera letra de la clave que sale de ella."""
    inv = {}
    for ki, ti in enumerate(mapa):
        inv.setdefault(ti, ki)
    return inv


def nucleo_de(forma, indice, hia, jot):
    """Nucleo (desde el final) en que cae el indice dado de la clave."""
    nuc = A.nucleos(forma, hia.get(forma, ()), jot.get(forma, ()))
    for n, (a, b) in enumerate(nuc):
        if a <= indice < b:
            return len(nuc) - n, len(nuc)
    return None, len(nuc)


# --------------------------------------------------------------------------
# tablas que salen de la ortografia de la Clementina
# --------------------------------------------------------------------------
def formas_clementina():
    corpus = json.load(open(os.path.join(DATA, "vulgata.json"),
                            encoding="utf-8"))
    formas = set()
    for caps in corpus.values():
        for vv in caps.values():
            for t in vv.values():
                formas.update(A.PALABRA.findall(unicodedata.normalize("NFC", t)))
    return formas


def hiatos_y_jotas(formas):
    """Las dos tablas de ortografia, sacadas de la dieresis y de la j.

    La Clementina escribe "Israël" y "ejus"; la Nova Vulgata, "Israel" y
    "eius". La dieresis dice que ahi no hay diptongo y la j dice que la i es
    consonante, asi que la Clementina le presta a la Nova Vulgata las dos
    informaciones que ella no escribe.
    """
    hia, jot, testigo = {}, {}, {}
    for w in formas:
        bajo = A._plano(w)
        if not any(c in A.DIERESIS or c == "j" for c in bajo):
            continue
        k, mapa = A.clave_mapa(w)
        inv = inverso(mapa)
        for i, c in enumerate(bajo):
            if c in A.DIERESIS:
                hia.setdefault(k, set()).add(inv[i])
                testigo[k] = w
            elif c == "j":
                jot.setdefault(k, set()).add(inv[i])
                testigo.setdefault(k, w)
    for k, corte in HIATO_CURADO.items():
        hia.setdefault(k, set()).add(corte)
        testigo.setdefault(k, "uso liturgico")
    return hia, jot, testigo


# --------------------------------------------------------------------------
# cosecha del corpus liturgico acentuado
# --------------------------------------------------------------------------
def ficheros():
    for sub in ("horas/Latin", "missa/Latin"):
        raiz = os.path.join(DIVINUM, *sub.split("/"))
        for dp, _, fs in os.walk(raiz):
            for f in sorted(fs):
                if f.endswith(".txt"):
                    ruta = os.path.join(dp, f)
                    yield ruta, ("Psalterium" in ruta)


def cosecha(hia, jot, sin_salterio=False):
    """Recoge de los libros liturgicos donde ponen el acento.

    Devuelve (acentos, sin_marca, renglones): 'acentos' cuenta pares
    (clave, indice del acento en la clave); 'sin_marca' cuenta las palabras de
    3+ silabas que aparecen desnudas en renglones que si llevan acentos, que es
    la prueba de que el uso las deja sin marcar a proposito.
    """
    acentos, sin_marca, nl = Counter(), Counter(), 0
    for ruta, es_salterio in ficheros():
        if sin_salterio and es_salterio:
            continue
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                linea = unicodedata.normalize("NFC", linea).strip()
                if not linea or linea.startswith(MARCAS):
                    continue
                toks = A.PALABRA.findall(RUBRICA.sub(" ", linea))
                if not toks:
                    continue
                nl += 1
                acentuada = any(c in A.AGUDAS for t in toks for c in t.lower())
                for t in toks:
                    if NO_LATINA.search(t):
                        continue
                    k, mapa = A.clave_mapa(t)
                    nuc = A.nucleos(t, {mapa[i] for i in hia.get(k, ())
                                        if i < len(mapa)},
                                    {mapa[i] for i in jot.get(k, ())
                                     if i < len(mapa)})
                    if len(nuc) < 3:
                        continue
                    tl = unicodedata.normalize("NFC", t).lower()
                    marcadas = [i for i, c in enumerate(tl) if c in A.AGUDAS]
                    if len(marcadas) == 1:
                        inv = inverso(mapa)
                        idx = inv.get(marcadas[0])
                        # el latin nunca acentua la ultima silaba: si sale ahi,
                        # o es una palabra mal silabeada o no es latin
                        if idx is not None and marcadas[0] < nuc[-1][0]:
                            acentos[(k, idx)] += 1
                    elif not marcadas and acentuada:
                        sin_marca[k] += 1
    return acentos, sin_marca, nl


def decide(acentos, sin_marca):
    """Del recuento a una decision por forma, con su respaldo."""
    reparto = defaultdict(Counter)
    for (k, i), n in acentos.items():
        reparto[k][i] = n
    uso, conflictos = {}, {}
    for k in set(reparto) | set(sin_marca):
        ac = reparto.get(k, Counter())
        tot_ac, u = sum(ac.values()), sin_marca.get(k, 0)
        if u >= MIN_SIN_MARCA and u >= PROP_SIN_MARCA * (tot_ac + u):
            uso[k] = "-"
            continue
        if not tot_ac:
            continue
        i, n = max(ac.items(), key=lambda kv: kv[1])
        if n >= DOMINANCIA * tot_ac:
            uso[k] = i
        else:
            conflictos[k] = dict(ac)
    return uso, reparto, conflictos


# --------------------------------------------------------------------------
# el vocabulario del proyecto, para no guardar lexico de sobra
# --------------------------------------------------------------------------
def vocabulario():
    claves = set()
    for f in ("vulgata.json", "nova_vulgata.json"):
        corpus = json.load(open(os.path.join(DATA, f), encoding="utf-8"))
        for caps in corpus.values():
            for vv in caps.values():
                for t in vv.values():
                    for w in A.PALABRA.findall(unicodedata.normalize("NFC", t)):
                        claves.add(A.clave(w))
    for f in ("latin_formulas.csv", "latin_formulas_nova.csv"):
        with open(os.path.join(DATA, f), encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                for w in A.PALABRA.findall(row["formula"]):
                    claves.add(A.clave(w))
    return claves


# --------------------------------------------------------------------------
# cantidades vocalicas de Morpheus
# --------------------------------------------------------------------------
def acento_por_cantidad(macronizada):
    """Acento de una forma macronizada de Morpheus ('ju_sto_rum' = jūstōrum)."""
    largas, plano = set(), []
    for ch in macronizada.lower():
        if ch == "_":
            if plano:
                largas.add(len(plano) - 1)
            continue
        if ch == "^":
            continue
        plano.append(ch)
    w = "".join(plano)
    nuc = A.nucleos(w)
    if len(nuc) < 3:
        return None
    peso = A.peso_penultima(w, nuc)
    if peso is True:
        return 2
    if peso is False:
        return 3
    return 2 if nuc[-2][0] in largas else 3


def cantidades(claves):
    """clave -> {acentos posibles}, solo del vocabulario del proyecto."""
    utiles = {k.replace("v", "u") for k in claves}
    tabla, lineas = defaultdict(set), 0
    with open(MACRONS, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            p = linea.rstrip("\n").split("\t")
            if len(p) < 4 or not p[3]:
                continue
            lineas += 1
            k = A.clave_cantidad(p[0])
            if k not in utiles:
                continue
            a = acento_por_cantidad(p[3])
            if a:
                tabla[k].add(a)
    return tabla, lineas


# --------------------------------------------------------------------------
# terminaciones aprendidas del propio uso
# --------------------------------------------------------------------------
def terminaciones(uso, hia, jot):
    """Terminaciones que deciden el acento cuando la penultima es abierta.

    Se aprenden del uso liturgico, no se inventan: solo entran las que tienen al
    menos TERM_CASOS formas y TERM_ACUERDO de acuerdo entre ellas.
    """
    fin = defaultdict(Counter)
    for k, idx in uso.items():
        if idx == "-":
            continue
        nuc = A.nucleos(k, hia.get(k, ()), jot.get(k, ()))
        if len(nuc) < 3 or A.peso_penultima(k, nuc) is not None:
            continue
        p, _ = nucleo_de(k, idx, hia, jot)
        if p not in (2, 3):
            continue
        for n in range(TERM_LARGO[0], TERM_LARGO[1] + 1):
            if len(k) > n:
                fin[k[-n:]][p] += 1
    salida = []
    for t, c in fin.items():
        tot = sum(c.values())
        if tot < TERM_CASOS:
            continue
        p, n = max(c.items(), key=lambda kv: kv[1])
        if n >= TERM_ACUERDO * tot:
            salida.append((t, p, tot, n / float(tot)))
    salida.sort(key=lambda x: (-len(x[0]), -x[2]))
    return salida


# --------------------------------------------------------------------------
# escritura
# --------------------------------------------------------------------------
def escribe(ruta, cabecera, filas):
    with open(ruta, "w", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(cabecera)
        wr.writerows(filas)
    print("%-48s %7d filas" % (ruta[len(ROOT) + 1:], len(filas)))
    return ruta


def escribe_tablas(carpeta, uso, reparto, sin_marca, cant, term, hia, jot,
                   testigo, conflictos=()):
    os.makedirs(carpeta, exist_ok=True)
    filas = []
    for k in sorted(set(uso) | set(conflictos)):
        idx = uso.get(k, "")          # vacio = el corpus no se pone de acuerdo
        ac = reparto.get(k, Counter())
        nuc = ("-" if idx in ("-", "") else nucleo_de(k, idx, hia, jot)[0])
        filas.append([k, idx, nuc, sum(ac.values()), sin_marca.get(k, 0),
                      " ".join("%d:%d" % (i, n) for i, n in sorted(ac.items()))])
    escribe(os.path.join(carpeta, "acentos_liturgico.csv"),
            ["forma", "indice", "silaba", "apar_acento", "apar_sin_marca",
             "reparto"], filas)
    escribe(os.path.join(carpeta, "acentos_cantidades.csv"),
            ["forma", "acento", "analisis"],
            [[k, (str(next(iter(v))) if len(v) == 1
                  else "|".join(str(x) for x in sorted(v))), len(v)]
             for k, v in sorted(cant.items())])
    escribe(os.path.join(carpeta, "acentos_terminaciones.csv"),
            ["terminacion", "acento", "casos", "acuerdo"],
            [[t, p, n, "%.4f" % r] for t, p, n, r in term])
    escribe(os.path.join(carpeta, "acentos_hiato.csv"),
            ["forma", "cortes", "testigo"],
            [[k, " ".join(str(x) for x in sorted(v)), testigo.get(k, "")]
             for k, v in sorted(hia.items())])
    escribe(os.path.join(carpeta, "acentos_jota.csv"),
            ["forma", "cortes", "testigo"],
            [[k, " ".join(str(x) for x in sorted(v)), testigo.get(k, "")]
             for k, v in sorted(jot.items())])


# --------------------------------------------------------------------------
# comprobaciones
# --------------------------------------------------------------------------
def choques_posicion(uso, hia, jot):
    """Formas donde la regla de posicion y el uso liturgico no coinciden."""
    malos = []
    for k, idx in uso.items():
        if idx == "-":
            continue
        nuc = A.nucleos(k, hia.get(k, ()), jot.get(k, ()))
        if len(nuc) < 3 or A.peso_penultima(k, nuc) is not True:
            continue
        p, _ = nucleo_de(k, idx, hia, jot)
        if p != 2:
            malos.append((k, p))
    return malos


def discrepancias(uso, reparto, cant, hia, jot):
    """Uso liturgico contra cantidades clasicas, separando el hiato."""
    filas = []
    for k, idx in uso.items():
        if idx == "-":
            continue
        v = cant.get(k.replace("v", "u"))
        if not v or len(v) != 1:
            continue
        q = next(iter(v))
        p, _ = nucleo_de(k, idx, hia, jot)
        if p is None or q == p:
            continue
        nuc = A.nucleos(k, hia.get(k, ()), jot.get(k, ()))
        hiato = A.peso_penultima(k, nuc) is False
        apar = sum(reparto.get(k, Counter()).values())
        elegido = p if (hiato or apar >= A.MIN_TESTIGOS) else q
        filas.append([k, p, q, apar, "si" if hiato else "no", elegido,
                      "hiato: manda el uso" if hiato else
                      ("uso bien atestiguado" if apar >= A.MIN_TESTIGOS
                       else "uso con pocos testigos: manda la cantidad")])
    filas.sort(key=lambda f: -f[3])
    return filas


PSALMO = re.compile(r"^(\d+)\s*:\s*(\d+)([a-z]*)\s+(.*)$")
SIGNOS = re.compile(r"[*†‡~+]")


def salterio_liturgico():
    """(salmo, versiculo) -> texto acentuado del Salterio de los libros."""
    raiz = os.path.join(DIVINUM, "horas", "Latin", "Psalterium", "Psalmorum")
    texto = defaultdict(list)
    if not os.path.isdir(raiz):
        return {}
    for f in sorted(os.listdir(raiz)):
        if not f.endswith(".txt"):
            continue
        with open(os.path.join(raiz, f), encoding="utf-8",
                  errors="replace") as fh:
            for linea in fh:
                m = PSALMO.match(unicodedata.normalize("NFC", linea).strip())
                if m:
                    texto[(m.group(1), m.group(2))].append(
                        SIGNOS.sub(" ", m.group(4)))
    return {k: " ".join(v) for k, v in texto.items()}


def compara_salterio(act):
    """Acentua nuestro Salterio y lo compara con el de los libros liturgicos.

    Palabra por palabra, sin distinguir mayusculas, porque el Salterio empieza
    cada versiculo con mayuscula y nuestro texto no. Devuelve (ok, mal,
    versiculos sin alinear, errores).
    """
    ref = salterio_liturgico()
    corpus = json.load(open(os.path.join(DATA, "vulgata.json"),
                            encoding="utf-8"))["Psalmi"]
    ok = mal = sin_alinear = 0
    errores = Counter()
    for (cap, vers), acentuado in sorted(ref.items()):
        nuestro = corpus.get(cap, {}).get(vers)
        if not nuestro:
            continue
        a = A.PALABRA.findall(unicodedata.normalize("NFC", acentuado))
        b = A.PALABRA.findall(unicodedata.normalize("NFC", nuestro))
        if [A.clave(x) for x in a] != [A.clave(x) for x in b]:
            sin_alinear += 1
            continue
        for x, y in zip(a, b):
            _, _, nuc = act.analiza(y)
            if len(nuc) < 3:
                continue
            mio = act.palabra(y)
            if A.esqueleto(mio) != A.esqueleto(y):
                mal += 1
                errores[(y, mio, x + " [rompe la palabra]")] += 1
            elif mio.lower() == x.lower():
                ok += 1
            else:
                mal += 1
                nota = "" if A.desacentua(x) != x else "  [el uso la deja desnuda]"
                errores[(y, mio, x + nota)] += 1
    return ok, mal, sin_alinear, errores, len(ref)


def informe_salterio(titulo, act, cuantos=45):
    ok, mal, sin_alinear, errores, vers = compara_salterio(act)
    total = ok + mal
    L = ["", titulo,
         "   versiculos del Salterio comparados: %d; sin alinear por "
         "diferencias de texto: %d" % (vers, sin_alinear),
         "   palabras de 3+ silabas comparadas: %d" % total]
    if total:
        L += ["   coinciden con el Salterio impreso: %d (%.2f %%)"
              % (ok, 100.0 * ok / total),
              "   no coinciden: %d (%.2f %%)" % (mal, 100.0 * mal / total)]
    L.append("   discrepancias mas repetidas (forma / la nuestra / la impresa):")
    for (y, mio, x), n in errores.most_common(cuantos):
        L.append("     %4d  %-20s %-20s %s" % (n, y, mio, x))
    return L


def validacion_retencion(hia, jot, testigo, cant):
    """Construye un lexico sin el Salterio y mide con el el Salterio.

    Es la unica forma de medir la maquinaria sobre texto que no ha visto.
    """
    ac2, sm2, _ = cosecha(hia, jot, sin_salterio=True)
    uso2, rep2, _ = decide(ac2, sm2)
    term2 = terminaciones(uso2, hia, jot)
    escribe_tablas(HOLDOUT, uso2, rep2, sm2, cant, term2, hia, jot, testigo)
    src = os.path.join(DATA, "acentos_overrides.csv")
    if os.path.exists(src):
        open(os.path.join(HOLDOUT, "acentos_overrides.csv"), "w",
             encoding="utf-8").write(open(src, encoding="utf-8").read())
    return informe_salterio(
        "3. Validacion por retencion (lexico construido SIN el Salterio)",
        A.Acentuador(data=HOLDOUT, exigir=False))


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-retencion", action="store_true",
                    help="salta la validacion por retencion, que es la parte lenta")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not os.path.isdir(DIVINUM) or not os.path.exists(MACRONS):
        raise SystemExit("falta la cache: ejecuta antes "
                         "python src/13a_crawl_acentos.py")

    hia, jot, testigo = hiatos_y_jotas(formas_clementina())
    print("ortografia: %d formas con hiato de 'ae'/'oe', %d con i consonantica"
          % (len(hia), len(jot)))

    ac, sm, nl = cosecha(hia, jot)
    uso, reparto, conflictos = decide(ac, sm)
    n_desnudas = sum(1 for v in uso.values() if v == "-")
    print("corpus liturgico: %d renglones, %d formas con acento decidido, "
          "%d que el uso deja desnudas, %d en conflicto"
          % (nl, len(uso) - n_desnudas, n_desnudas, len(conflictos)))

    voc = vocabulario()
    cant, nlin = cantidades(voc)
    unicas = sum(1 for v in cant.values() if len(v) == 1)
    print("cantidades: %d analisis leidos, %d formas del proyecto, "
          "%d con acento unico" % (nlin, len(cant), unicas))

    term = terminaciones(uso, hia, jot)
    escribe_tablas(DATA, uso, reparto, sm, cant, term, hia, jot, testigo,
                   conflictos)

    choques = choques_posicion(uso, hia, jot)
    disc = discrepancias(uso, reparto, cant, hia, jot)
    escribe(os.path.join(DATA, "acentos_discrepancias.csv"),
            ["forma", "uso", "cantidad", "apar_uso", "hiato", "elegido",
             "motivo"], disc)

    L = ["Acentuacion liturgica - construccion de los lexicos", "",
         "Fuentes:",
         "  corpus liturgico acentuado (Divinum Officium): %d renglones" % nl,
         "  cantidades vocalicas (Morpheus, via CLTK): %d analisis" % nlin, "",
         "Tablas:",
         "  formas con acento del uso liturgico ... %6d" % (len(uso) - n_desnudas),
         "  formas que el uso deja desnudas ...... %6d" % n_desnudas,
         "  formas en conflicto (sin decidir) .... %6d" % len(conflictos),
         "  formas con acento por cantidades ..... %6d" % unicas,
         "  terminaciones aprendidas ............. %6d" % len(term),
         "  hiatos de 'ae'/'oe' .................. %6d" % len(hia),
         "  i consonanticas ...................... %6d" % len(jot), "",
         "1. Regla de posicion contra uso liturgico",
         "   La posicion (diptongo o penultima trabada) decide sin lexico. "
         "Formas en que",
         "   el uso dice otra cosa: %d de %d. Son erratas del corpus "
         "liturgico, y no" % (len(choques), len(uso) - n_desnudas),
         "   afectan al resultado porque la posicion se aplica antes que el uso."]
    for k, p in choques[:25]:
        L.append("     %-26s uso=%s" % (k, p))
    hi = [f for f in disc if f[4] == "si"]
    L += ["", "2. Uso liturgico contra cantidades clasicas",
          "   discrepancias: %d formas, de ellas %d en hiato" % (len(disc),
                                                                len(hi)),
          "   En hiato manda el uso ('María', 'illíus', 'diéi': i larga que la",
          "   cantidad de Morpheus no marca). Fuera del hiato manda el uso si "
          "tiene %d" % A.MIN_TESTIGOS,
          "   testigos o mas, y si no, la cantidad clasica.",
          "   Las 30 mas atestiguadas fuera del hiato:"]
    for f in [x for x in disc if x[4] == "no"][:30]:
        L.append("     %-24s uso=%s (%d)  cantidad=%s  -> %s"
                 % (f[0], f[1], f[3], f[2], f[5]))
    L += ["", "   Formas que el uso liturgico deja desnudas (se respeta solo en",
          "   nombre propio), las 40 mas frecuentes:"]
    desnudas = sorted(((sm.get(k, 0), k) for k, v in uso.items() if v == "-"),
                      reverse=True)
    for n, k in desnudas[:40]:
        L.append("     %5d  %s" % (n, k))

    if not args.sin_retencion:
        L += validacion_retencion(hia, jot, testigo, cant)
        # y con el lexico entero, donde el Salterio si esta: aqui una
        # discrepancia ya no es falta de datos, es un fallo de la maquinaria
        L += informe_salterio("4. El Salterio con el lexico completo",
                              A.Acentuador(data=DATA, exigir=False), 25)

    ruta = os.path.join(DATA, "acentos_qa.txt")
    open(ruta, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:16]))
    print("...")
    print(ruta[len(ROOT) + 1:])


if __name__ == "__main__":
    main()
