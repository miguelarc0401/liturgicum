"""Fase 9 - Acentuacion liturgica del texto latino (las dos fuentes).

Los libros liturgicos marcan con acento agudo la silaba tonica de toda palabra
de tres silabas o mas ("Dóminus", "Léctio", "quǽsumus"), para que se pueda leer
y cantar sin saber latin. La regla es "penultima si es larga, antepenultima si
es breve", y el problema esta en que la longitud de una penultima abierta no se
deduce de la ortografia: es lexica ("Dóminus" y "amícus" se escriben igual de
ambiguos).

Cada palabra se resuelve por orden de autoridad, y el modulo deja constancia de
por que la ha resuelto asi:

  1. data/acentos_overrides.csv     decision a mano (admite "-" = sin marca)
  2. posicion                       diptongo o penultima trabada -> penultima
  3. data/acentos_liturgico.csv     el uso liturgico realmente impreso
  4. hiato                          vocal ante vocal -> penultima breve
  5. data/acentos_cantidades.csv    cantidades vocalicas (Morpheus)
  6. data/acentos_terminaciones.csv terminaciones aprendidas del propio uso
  7. por omision                    penultima, y la forma queda en el informe

El paso 2 va delante del uso porque la posicion no falla: contrastada con las
52 000 formas acentuadas del corpus liturgico, las unicas discrepancias son
erratas del corpus. El paso 3 va delante del hiato porque el hiato falla justo
donde el leccionario tiene mas nombres propios: "María", "Elías", "illíus",
"diéi" llevan i larga, y el hiato las acentuaria en la antepenultima.

El lexico del uso guarda la POSICION EXACTA del acento dentro de la palabra, no
el numero de silaba: asi una palabra mal silabeada se sigue acentuando bien, y
la misma entrada sirve para las dos ortografias ("Isaíæ" y "Isaíae").

Las dos ortografias se reconcilian con dos tablas sacadas de la propia
Clementina, que escribe lo que la Nova Vulgata no:

  data/acentos_hiato.csv   donde 'ae'/'oe' no es diptongo ("Israël", "introëas")
  data/acentos_jota.csv    donde la i es consonante ("ejus" -> "eius")

Los lexicos los construyen:
    python src/13a_crawl_acentos.py     corpus acentuado + cantidades -> cache/
    python src/13b_build_acentos.py     cache/ -> data/acentos_*.csv

Uso:  python src/13_acentos.py [--fuente clementina|nova]
      python src/13_acentos.py --muestra "Lectio libri Isaiae prophetae"

Lo importan 8_render.py y 9_docx.py, que acentuan al escribir.
"""

import argparse
import csv
import os
import re
import sys
import unicodedata
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# --------------------------------------------------------------------------
# letras
# --------------------------------------------------------------------------
AGUDAS = {"á": "a", "é": "e", "í": "i", "ó": "o",
          "ú": "u", "ý": "y", "ǽ": "æ", "ǿ": "œ"}
PONER = {v: k for k, v in AGUDAS.items()}
DIERESIS = {"ë": "e", "ï": "i", "ö": "o", "ü": "u",
            "ÿ": "y", "ä": "a"}
LIGADURAS = {"æ": "ae", "œ": "oe"}
VOC = set("aeiouy") | set(LIGADURAS) | set(DIERESIS)
LETRAS = ("A-Za-zÆæŒœ" + "".join(AGUDAS)
          + "".join(k.upper() for k in AGUDAS) + "".join(DIERESIS)
          + "".join(k.upper() for k in DIERESIS))
PALABRA = re.compile("[" + LETRAS + "]+")
AGUDO_COMB = "́"

# Diptongos. El acento va en la PRIMERA vocal del diptongo ("exáudi",
# "gáudium": 2712 apariciones en el corpus liturgico) y en la ligadura cuando
# la hay ("quǽsumus": 5925 apariciones).
DIPTONGOS = ("ae", "oe", "au")
# 'eu' solo es diptongo en helenismos, y hay que decir cuales: en latin hace
# hiato, y de ahi "e-úntibus" y "e-úmdem" (de eo, ire) frente a "Euphráten" o
# "eunúchus". La lista sale del vocabulario de las dos ediciones: 35 formas
# empiezan por 'eu', y las de eo/is son las unicas de hiato.
EU_GRIEGO = ("heu", "seu", "neu", "ceu", "euge", "eunuch", "euphrat",
             "eupator", "eucharis", "eumeni", "eupolem", "eutych", "eunice",
             "eubul", "eurus", "euroaquilo", "euang", "europ", "eulog",
             "eudox", "euodi")
# 'u' consonantica detras de g/s (sanguis, lingua, suavis): no hace silaba
U_CONSONANTE = ("sangui", "sangue", "sanguo", "sanguin", "lingu", "unguent",
                "ungu", "exstingu", "extingu", "distingu", "pingu", "angui",
                "suav", "suad", "suas", "suesc", "suet", "consuet")
MUTA, LIQUIDA = set("pbtdcgf"), set("lr")


def _plano(w):
    """La palabra en minusculas y sin acentos, para analizarla."""
    s = unicodedata.normalize("NFC", w).lower()
    return "".join(AGUDAS.get(c, c) for c in s)


def desacentua(w):
    """Quita los acentos agudos, conservando mayusculas y ligaduras."""
    salida = []
    for c in unicodedata.normalize("NFC", w):
        if c == AGUDO_COMB:
            continue
        b = AGUDAS.get(c.lower())
        salida.append(c if b is None else (b.upper() if c.isupper() else b))
    return "".join(salida)


def esqueleto(w):
    """Las letras de la palabra sin acento ni dieresis, para comprobar que
    acentuar no le cambia ni le pierde ninguna."""
    s = desacentua(unicodedata.normalize("NFC", w)).lower()
    return "".join(DIERESIS.get(c, c) for c in s)


def clave_mapa(w):
    """(clave, mapa) - la clave comun a las dos ortografias y su mapa.

    La clave es la palabra en minusculas, sin acento ni dieresis, con 'æ'/'œ'
    desligadas y la j convertida en i: asi "ejus" y "eius", o "cæli" y "caeli",
    son la misma entrada. El mapa dice, para cada letra de la clave, de que
    letra de la palabra sale, que es lo que permite trasladar el acento.
    """
    clave, mapa = [], []
    for i, c in enumerate(_plano(w)):
        t = LIGADURAS.get(c) or DIERESIS.get(c) or ("i" if c == "j" else c)
        clave.append(t)
        mapa.extend([i] * len(t))
    return "".join(clave), mapa


def clave(w):
    return clave_mapa(w)[0]


def clave_cantidad(w):
    """Clave de Morpheus, que no distingue u de v."""
    return clave(w).replace("v", "u")


def nucleos(w, cortes=(), consonantes=()):
    """Nucleos vocalicos de la palabra, como spans (i, j) sobre ella.

    'cortes' son posiciones donde un 'ae'/'oe'/'au' no es diptongo sino hiato
    ("Israël", "Nicoláum"); 'consonantes' son posiciones donde la i no es vocal
    sino consonante ("eius", "maior"). Las dos cosas las escribe la Clementina
    -con dieresis y con j- y la Nova Vulgata no, asi que viajan en tablas.
    """
    base = _plano(w)
    n, out, i = len(base), [], 0
    while i < n:
        c = base[i]
        if c not in VOC or i in consonantes:
            i += 1
            continue
        # i inicial ante vocal: Iesus, Iacob, iam, iustus
        if c == "i" and i == 0 and n > 1 and base[1] in VOC:
            i += 1
            continue
        if c == "u" and i and base[i - 1] == "q":          # qui, quod, aqua
            i += 1
            continue
        if c == "u" and i and base[i - 1] in "gs" and i + 1 < n \
           and base[i + 1] in VOC \
           and any(base.startswith(p) or p in base[:i + 2]
                   for p in U_CONSONANTE):
            i += 1
            continue
        j = i + 1
        if i + 1 not in cortes:
            par = base[i:i + 2]
            if par in DIPTONGOS:
                j = i + 2
            elif par == "eu" and any(base.startswith(p) for p in EU_GRIEGO):
                j = i + 2
        out.append((i, j))
        i = j
    return out


def peso_penultima(w, nuc):
    """Peso de la penultima por su forma: True pesada, False breve, None lexico.

    Pesada si el nucleo es diptongo -escrito con dos letras o con ligadura-, si
    la silaba va trabada por dos consonantes o si detras hay x o z, que valen
    dos. No cuentan como dos la muta cum liquida ("ténebræ", "cáthedra": la
    br/dr pasa entera a la silaba siguiente) ni la h, que no es consonante.
    """
    base = _plano(w)
    (pi, pj), (ui, _) = nuc[-2], nuc[-1]
    if pj - pi == 2 or base[pi] in LIGADURAS:
        return True                                    # diptongo
    seg = (base[pj:ui].replace("qu", "q").replace("ch", "c")
           .replace("ph", "f").replace("th", "t").replace("rh", "r")
           .replace("h", ""))
    if not seg:
        return False                                   # vocal ante vocal
    if seg[0] in "xz":
        return True
    if len(seg) == 1:
        return None                                    # silaba abierta
    if len(seg) == 2 and seg[0] in MUTA and seg[1] in LIQUIDA:
        return None
    return True


def pon_agudo(w, i):
    """Pone el acento agudo en la letra i de la palabra.

    Si la letra llevaba dieresis, el agudo la sustituye: los libros liturgicos
    imprimen "Israélis" y "Michaélis", no "Israë́lis", porque el agudo ya avisa
    de que la vocal hace silaba aparte.
    """
    if i is None or not 0 <= i < len(w):
        return w
    c = w[i]
    if c.lower() in AGUDAS:                            # ya venia acentuada
        return w
    nueva = PONER.get(DIERESIS.get(c.lower(), c.lower()))
    if nueva is None:
        return w[:i + 1] + AGUDO_COMB + w[i + 1:]
    return w[:i] + (nueva.upper() if c.isupper() else nueva) + w[i + 1:]


# --------------------------------------------------------------------------
# el acentuador
# --------------------------------------------------------------------------
POR_OMISION = 2        # penultima: 62 % de las formas de penultima abierta
POR_AMBIGUA = 3        # cuando la cantidad es ambigua ("dividere" puede ser
                       # infinitivo o perfecto), el uso liturgico elige la
                       # antepenultima en 395 de las 516 formas medidas
MIN_TESTIGOS = 4       # apariciones para que el uso gane a la cantidad clasica
FUENTES_ORDEN = ["manual", "posicion", "uso", "cantidad (uso debil)",
                 "uso (variante ae/oe)", "sin marca (uso)", "hiato",
                 "cantidad", "prefijo",
                 "terminacion", "cantidad ambigua", "omision"]

# Prefijos latinos, de mas largo a mas corto. Un prefijo no cambia las tres
# ultimas silabas de la palabra, que son las que deciden el acento: si
# "tóllite" esta atestiguada, "extóllite" lleva el acento en la misma silaba
# contada desde el final.
PREFIJOS = ("praeter", "circum", "subter", "super", "trans", "inter", "intro",
            "prae", "post", "ante", "abs", "ad", "ab", "con", "com", "co",
            "de", "dis", "di", "ex", "in", "ob", "per", "pro", "red", "re",
            "se", "sub", "tra", "e", "a")


class Acentuador(object):
    """Acentua texto latino y cuenta de donde sale cada decision."""

    def __init__(self, data=DATA, exigir=True):
        self.uso = {}              # clave -> indice en la clave | "-"
        self.apar_uso = {}         # clave -> apariciones que la respaldan
        self.cantidad = {}         # clave -> nucleo desde el final
        self.cantidad_amb = set()  # claves con mas de un acento posible
        self.terminacion = []      # [(terminacion, nucleo)]
        self.hiato = {}            # clave -> {indices de corte}
        self.jota = {}             # clave -> {indices de i consonantica}
        self.overrides = {}        # clave -> nucleo | "-"
        self.cuenta = Counter()
        self.sin_resolver = Counter()
        self.revisables = {}
        self.ya_acentuadas = Counter()
        self._cache = {}
        self._carga(data, exigir)

    # ---------------------------------------------------------------- carga
    def _csv(self, data, nombre, exigir):
        ruta = os.path.join(data, nombre)
        if not os.path.exists(ruta):
            if exigir:
                raise SystemExit(
                    "falta data/%s: ejecuta\n"
                    "    python src/13a_crawl_acentos.py\n"
                    "    python src/13b_build_acentos.py" % nombre)
            return []
        with open(ruta, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def _carga(self, data, exigir):
        for r in self._csv(data, "acentos_liturgico.csv", exigir):
            a = (r["indice"] or "").strip()
            if not a:
                continue
            self.uso[r["forma"]] = a if a == "-" else int(a)
            self.apar_uso[r["forma"]] = int(r.get("apar_acento") or 0)
        for r in self._csv(data, "acentos_cantidades.csv", exigir):
            a = (r["acento"] or "").strip()
            if a.isdigit():
                self.cantidad[r["forma"]] = int(a)
            elif a:
                self.cantidad_amb.add(r["forma"])
        for r in self._csv(data, "acentos_terminaciones.csv", exigir):
            self.terminacion.append((r["terminacion"], int(r["acento"])))
        self.terminacion.sort(key=lambda x: -len(x[0]))
        for nombre, dest in (("acentos_hiato.csv", self.hiato),
                             ("acentos_jota.csv", self.jota)):
            for r in self._csv(data, nombre, exigir):
                dest[r["forma"]] = {int(x) for x in r["cortes"].split()
                                    if x.strip()}
        for r in self._csv(data, "acentos_overrides.csv", False):
            a = (r["acento"] or "").strip()
            if a:
                self.overrides[clave(r["forma"])] = a if a == "-" else int(a)

    # ------------------------------------------------------------- analisis
    def analiza(self, w):
        """(clave, mapa, nucleos) con los hiatos y las jotas ya aplicados."""
        k, mapa = clave_mapa(w)
        cortes = {mapa[i] for i in self.hiato.get(k, ()) if i < len(mapa)}
        cons = {mapa[i] for i in self.jota.get(k, ()) if i < len(mapa)}
        return k, mapa, nucleos(w, cortes, cons)

    def acento(self, w):
        """(letra de la palabra donde va el agudo o None, fuente).

        La cache va por palabra y no por clave: la respuesta es una posicion
        dentro de la palabra, y "prœlium" y "proelium" comparten clave pero no
        posiciones. La mayuscula inicial tambien cuenta, porque de ella depende
        que se respete el nombre propio que el uso deja desnudo.
        """
        if w in self._cache:
            return self._cache[w]
        r = self._acento(w)
        self._cache[w] = r
        return r

    def _nucleo_a_letra(self, nuc, pos):
        return nuc[len(nuc) - pos][0] if 2 <= pos <= len(nuc) else None

    def _letra_a_nucleo(self, nuc, letra):
        for n, (a, b) in enumerate(nuc):
            if a <= letra < b:
                return len(nuc) - n
        return None

    def _al_nucleo(self, nuc, letra):
        """Lleva el acento al principio de su nucleo.

        Hace falta porque el testigo puede escribir el diptongo con ligadura
        ("prǿlium") o con dos letras ("proélium"), y aqui el agudo va siempre en
        la primera vocal: "próelium".
        """
        for a, b in nuc:
            if a <= letra < b:
                return a
        return letra

    def _acento(self, w):
        k, mapa, nuc = self.analiza(w)
        if len(nuc) < 3:
            return None, "corta"
        if k in self.overrides:
            a = self.overrides[k]
            return ((None, "manual") if a == "-"
                    else (self._nucleo_a_letra(nuc, a), "manual"))
        peso = peso_penultima(w, nuc)
        if peso is True:
            return self._nucleo_a_letra(nuc, 2), "posicion"
        uso = self.uso.get(k)
        if uso == "-":
            # nombre propio que el uso liturgico deja sin marcar ("Israël",
            # "Isaac", "Aaron"): se respeta solo con mayuscula inicial
            if w[:1].isupper():
                return None, "sin marca (uso)"
        elif uso is not None and uso < len(mapa):
            letra = self._al_nucleo(nuc, mapa[uso])
            # cuando el uso se apoya en menos de cuatro apariciones y las
            # cantidades clasicas dicen otra cosa, mandan las cantidades: ahi
            # estan las erratas del corpus liturgico ("arbóri" por "árbori").
            # En hiato no: ahi Morpheus no marca la i larga de "María" ni la de
            # "intróeas", y el uso acierta aunque tenga un solo testigo.
            if peso is not False and self.apar_uso.get(k, 0) < MIN_TESTIGOS:
                q = self.cantidad.get(k) or self.cantidad.get(clave_cantidad(w))
                if q and q != self._letra_a_nucleo(nuc, letra):
                    return self._nucleo_a_letra(nuc, q), "cantidad (uso debil)"
            return letra, "uso"
        if uso is None:
            # la Nova Vulgata escribe "paenitemini" donde la Clementina escribe
            # "pœnitemini": es la misma palabra y el mismo acento
            for v in (k.replace("ae", "oe"), k.replace("oe", "ae")):
                idx = self.uso.get(v)
                if v != k and len(v) == len(k) and idx is not None \
                   and idx != "-" and idx < len(mapa):
                    return (self._al_nucleo(nuc, mapa[idx]),
                            "uso (variante ae/oe)")
        if peso is False:
            if w[:1].isupper():
                self.revisables[k] = ("hiato en nombre propio", w)
            return self._nucleo_a_letra(nuc, 3), "hiato"
        for cl in (k, clave_cantidad(w)):
            if cl in self.cantidad:
                return self._nucleo_a_letra(nuc, self.cantidad[cl]), "cantidad"
        p = self._por_prefijo(k)
        if p:
            return self._nucleo_a_letra(nuc, p), "prefijo"
        for t, a in self.terminacion:
            if k.endswith(t):
                return self._nucleo_a_letra(nuc, a), "terminacion"
        if k in self.cantidad_amb or clave_cantidad(w) in self.cantidad_amb:
            return self._nucleo_a_letra(nuc, POR_AMBIGUA), "cantidad ambigua"
        self.sin_resolver[w] += 1
        return self._nucleo_a_letra(nuc, POR_OMISION), "omision"

    def _por_prefijo(self, k):
        """Acento heredado de la palabra que queda al quitar un prefijo.

        "extollite" no esta en ningun lexico, pero "tóllite" si, y el prefijo no
        toca las tres ultimas silabas, que son las que deciden.
        """
        for pre in PREFIJOS:
            if not k.startswith(pre) or len(k) - len(pre) < 4:
                continue
            resto = k[len(pre):]
            nr = nucleos(resto, self.hiato.get(resto, ()),
                         self.jota.get(resto, ()))
            if len(nr) < 3:
                continue
            idx = self.uso.get(resto)
            if idx is not None and idx != "-":
                p = self._letra_a_nucleo(nr, idx)
                if p in (2, 3):
                    return p
            for cl in (resto, resto.replace("v", "u")):
                if cl in self.cantidad:
                    return self.cantidad[cl]
        return None

    # --------------------------------------------------------------- salida
    def palabra(self, w):
        if w.isupper() and len(w) > 1:   # las rubricas van en versales, sin acento
            self.cuenta["versal"] += 1
            return w
        if desacentua(w) != unicodedata.normalize("NFC", w):
            # ya venia acentuada en la fuente: la Nova Vulgata de vatican.va
            # trae algun acento suelto ("commoratío"), y no se toca
            self.cuenta["ya acentuada"] += 1
            self.ya_acentuadas[w] += 1
            return w
        letra, fuente = self.acento(w)
        self.cuenta[fuente] += 1
        return w if letra is None else pon_agudo(w, letra)

    def texto(self, t):
        if not t:
            return t
        return PALABRA.sub(lambda m: self.palabra(m.group(0)), t)


_ACT = None


def acentuador(exigir=True):
    """El acentuador del proceso, cargado una sola vez."""
    global _ACT
    if _ACT is None:
        _ACT = Acentuador(exigir=exigir)
    return _ACT


# --------------------------------------------------------------------------
# informe de cobertura
# --------------------------------------------------------------------------
FUENTES = {"clementina": ("readings_latin.json", "latin_formulas.csv"),
           "nova": ("readings_latin_nova.json", "latin_formulas_nova.csv")}


def formas_del_leccionario(fuente):
    """Cada forma latina que el leccionario llega a imprimir, con su frecuencia."""
    import json
    lecturas, formulas = FUENTES[fuente]
    formas = Counter()
    for e in json.load(open(os.path.join(DATA, lecturas), encoding="utf-8")):
        for tr in e["tramos"]:
            for v in tr:
                for w in PALABRA.findall(unicodedata.normalize("NFC",
                                                              v["texto"])):
                    formas[w] += 1
    with open(os.path.join(DATA, formulas), encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            for w in PALABRA.findall(row["formula"]):
                formas[w] += 1
    return formas


def informe(fuente):
    act = acentuador()
    formas = formas_del_leccionario(fuente)
    por_fuente, largas, n_formas, roto = Counter(), 0, 0, []
    sin_res = Counter()
    for w, n in formas.items():
        letra, f = act.acento(w)
        if f == "corta":
            continue
        largas += n
        n_formas += 1
        por_fuente[f] += n
        if f == "omision":
            sin_res[w] += n
        m = act.palabra(w)
        if esqueleto(m) != esqueleto(w):
            roto.append((w, m))

    L = ["Acentuacion liturgica - cobertura sobre %s" % FUENTES[fuente][0], ""]
    L.append("palabras de 3+ silabas: %d apariciones en %d formas distintas"
             % (largas, n_formas))
    L.append("")
    for f in FUENTES_ORDEN:
        if por_fuente.get(f):
            L.append("  %-20s %8d  %6.2f %%"
                     % (f, por_fuente[f], 100.0 * por_fuente[f] / largas))
    resuelto = largas - por_fuente.get("omision", 0)
    L += ["", "resueltas con fundamento: %d de %d (%.2f %%)"
          % (resuelto, largas, 100.0 * resuelto / largas),
          "integridad: %d formas cambiarian de letras al acentuar" % len(roto)]
    for w, m in roto[:20]:
        L.append("    %s -> %s" % (w, m))
    desnudas = Counter()
    for w, n in formas.items():
        if act.acento(w)[1] == "sin marca (uso)":
            desnudas[w] += n
    if desnudas:
        L += ["", "se dejan desnudas porque el uso liturgico no las marca "
              "(%d formas / %d apariciones);" % (len(desnudas),
                                                sum(desnudas.values())),
              "para marcarlas, poner su acento en data/acentos_overrides.csv:"]
        for w, n in desnudas.most_common(30):
            L.append("    %5d  %s" % (n, w))
    if act.ya_acentuadas:
        L += ["", "ya venian acentuadas en la fuente y no se han tocado "
              "(%d formas):" % len(act.ya_acentuadas)]
        for w, n in act.ya_acentuadas.most_common(20):
            L.append("    %5d  %s" % (n, w))
    L += ["", "sin fundamento (acentuadas en la penultima por omision): "
          "%d formas / %d apariciones" % (len(sin_res), sum(sin_res.values()))]
    for w, n in sin_res.most_common(80):
        L.append("    %4d  %-26s -> %s" % (n, w, act.palabra(w)))
    texto = "\n".join(L) + "\n"
    ruta = os.path.join(DATA, "acentos_cobertura_%s.txt" % fuente)
    open(ruta, "w", encoding="utf-8").write(texto)

    filas = [(w, act.palabra(w), n, "sin fundamento")
             for w, n in sin_res.most_common()]
    for k, (motivo, w) in sorted(act.revisables.items()):
        if w in formas:
            filas.append((w, act.palabra(w), formas[w], motivo))
    exc = os.path.join(DATA, "acentos_excepciones_%s.csv" % fuente)
    with open(exc, "w", encoding="utf-8", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["forma", "propuesta", "apariciones", "motivo"])
        wr.writerows(filas)
    sys.stdout.reconfigure(encoding="utf-8")
    print(texto)
    print(ruta[len(ROOT) + 1:])
    print("%-56s %5d filas" % (exc[len(ROOT) + 1:], len(filas)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuente", default="clementina", choices=sorted(FUENTES))
    ap.add_argument("--muestra", default=None,
                    help="acentua el texto dado y explica cada palabra")
    args = ap.parse_args()
    if args.muestra:
        sys.stdout.reconfigure(encoding="utf-8")
        act = acentuador()
        print(act.texto(args.muestra))
        for w in PALABRA.findall(args.muestra):
            letra, f = act.acento(w)
            print("  %-24s %-6s %s" % (w, letra, f))
        return
    informe(args.fuente)


if __name__ == "__main__":
    main()
