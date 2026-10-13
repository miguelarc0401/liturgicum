"""Fase 21 - `app/datos/lecturas_lect1977.json`: el leccionario de 1977.

La fase 20 cosecho de los cuatro tomos lo que el libro **decide**; esta lo
arma para la app. No trae ni una letra del OCR: cada pieza se copia entera de
`lecturas_clementina.json` o de `lecturas_nova.json` -que el proyecto ya tiene
limpias y acentuadas-, y lo unico que se le anade de la cosecha es el incipit
liturgico y la redaccion de la formula, que no son texto biblico. Del incipit
se recorta lo que el texto ya diga, porque el libro a veces no lo anade sino
que reescribe con el el arranque de la pericopa (ver `recorta_incipit`).

**La regla, que es el hallazgo.** Medidos 5 484 puntos donde la Clementina y
la Nova difieren entre si en una palabra entera, el Misal de 1977 sigue:

    Nuevo Testamento ... la Nova Vulgata   (70,6 % contra 5,2 %)
    Salmos ............ el salterio de la Nova, numerado a la griega
                        (510 salmos contra 22)
    Antiguo Testamento  la Clementina      (82,5 % contra 1,9 %)

No es capricho: la Nova del Nuevo Testamento se publico en 1971 y el salterio
tambien, antes que este Misal; el Antiguo Testamento de la Nova no se cerro
hasta 1979, dos anos despues. De ahi que el libro sea mixto.

La regla se comprobo contra el voto pericopa a pericopa en las 768 pericopas
con dos o mas puntos decisivos: **coincide en el 99,5 %**. Las cuatro que
votan al reves lo hacen por un margen de un punto, dentro del ruido del OCR,
asi que no se les hace caso aparte.

**Lo que esto no es.** No es una transcripcion del libro de 1977: es una
reconstruccion por la regla, y donde el libro trae lectura propia -71 puntos
que no son ni de una ni de otra, como Col 3,12 `mansuetudinem, patientiam`,
una palabra de cada corpus- esta version dira lo que diga el corpus elegido.
Esos puntos estan listados en `Missale/datos/cotejo_1977_residuo.csv`. La
cabecera del fichero lo dice, para que no se tome por lo que no es.

Salida:  app/datos/lecturas_lect1977.json
         data/lect1977_app_qa.txt

Uso:  python src/21_lect1977_app.py
"""

import argparse
import collections
import csv
import difflib
import importlib.util
import io
import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DATA = os.path.join(RAIZ, "data")
DATOS = os.path.join(RAIZ, "app", "datos")


def modulo(nombre):
    """Importa un script cuyo nombre empieza por un numero."""
    spec = importlib.util.spec_from_file_location(
        "m" + re.sub(r"\W", "", nombre), os.path.join(AQUI, nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FASE20 = modulo("20_lect1977")

NUEVO_TESTAMENTO = {
    "Matthaeus", "Marcus", "Lucas", "Ioannes", "Actus Apostolorum",
    "Ad Romanos", "I Ad Corinthios", "II Ad Corinthios", "Ad Galatas",
    "Ad Ephesios", "Ad Philippenses", "Ad Colossenses",
    "I Ad Thessalonicenses", "II Ad Thessalonicenses", "I Ad Timotheum",
    "II Ad Timotheum", "Ad Titum", "Ad Philemonem", "Ad Hebraeos", "Iacobi",
    "I Petri", "II Petri", "I Ioannis", "II Ioannis", "III Ioannis", "Iudae",
    "Apocalypsis",
}

TITULO = "Lectionarium Latinum · Missale cum lectionibus, 1977"
CABECERA = (
    "Texto: reconstruido del Missale Romanum cum lectionibus "
    "(Libreria Editrice Vaticana, 1977).\n"
    "El libro de 1977 no se copia: se usa como árbitro. Él decide, "
    "perícopa por perícopa, qué texto latino se lee y cómo empieza; "
    "las letras las ponen la Vulgata Clementina y la Nova Vulgata, que es "
    "de donde el propio Misal las tomaba —la Nova en el Nuevo Testamento "
    "y en los salmos, la Clementina en el Antiguo—. Medido sobre 5 484 "
    "puntos de divergencia entre las dos versiones.\n"
    "Íncipits litúrgicos y fórmulas: del propio Misal de 1977. Donde "
    "el libro no añade el íncipit sino que reescribe con él el arranque "
    "de la perícopa, se recorta lo que el texto ya dice.\n"
    "Estructura: Leccionario de Servicios Koinonía."
)


def siglas_a_libro():
    m = {}
    with io.open(os.path.join(DATA, "latin_formulas_nova.csv"),
                 encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m[r["sigla_lat"]] = r["vulgata"]
    return m


def parte_cita(c):
    """'cf. Ps 121,1-2.4-5 [Ps 122]' -> ('Ps', [(121,1,2),(121,4,5)])"""
    if not c:
        return None, []
    c = re.sub(r"\s*\[[^\]]*\]\s*$", "", c)
    c = re.sub(r"^\s*cf\.\s*", "", c)
    m = re.match(r"^([1-3]\s)?([A-Za-zÀ-ɏ]+)\s*(.*)$", c)
    if not m:
        return None, []
    sigla = ((m.group(1) or "").strip() + " " + m.group(2)).strip()
    return sigla, FASE20.parse_cita(m.group(3))


# Los dos leccionarios del proyecto no escriben el latin igual: la Clementina
# usa `j` y las ligaduras (`Juda`, `ejus`, `caeli` con ae ligada, `quaesumus`
# con ae ligada y acentuada), y la Nova no usa ninguna de las dos (`Iuda`,
# `eius`, `Mattha'eum`). Como cinco de cada seis piezas de esta version salen
# de la Nova, las que salen de la Clementina se pasan a su manera, para que no
# convivan dos ortografias en la misma pagina. El Misal de 1977 escribe `I`
# como la Nova, y la ligadura como la Clementina; se elige la uniformidad.
#
# La `ae` acentuada va con el acento sobre la **a** (`Mattha'eum`), que es
# como la escribe la Nova; no se inventa, se copia de ella.
ORTOGRAFIA = {
    ord("j"): "i", ord("J"): "I",
    0x01FD: "áe", 0x01FC: "Áe",      # ae ligada acentuada
    0x00E6: "ae", 0x00C6: "Ae",                # ae ligada
    0x01FF: "óe",                          # oe ligada acentuada
    0x0153: "oe", 0x0152: "Oe",                # oe ligada
}


def a_la_nova(x):
    """Pasa una pieza de la Clementina a la ortografia de la Nova."""
    if isinstance(x, str):
        return x.translate(ORTOGRAFIA)
    if isinstance(x, list):
        return [a_la_nova(y) for y in x]
    if isinstance(x, dict):
        return {k: a_la_nova(v) for k, v in x.items()}
    return x


# --------------------------------------------------------------------------
# el incipit que el texto ya dice
# --------------------------------------------------------------------------
# El Misal de 1977 no siempre *anade* el incipit: a veces **reescribe** con el
# el arranque de la pericopa, para que se entienda suelta. Num 6, 22 dice en
# la Clementina `Locutusque est Dominus ad Moysen, dicens` y el libro lo
# imprime `Locutus est Dominus ad Moysen dicens`; Mt 16, 24 dice `Tunc Iesus
# dixit discipulis suis` y el libro `Dixit Iesus discipulis suis`. Pegar el
# incipit delante de ese texto lo dice dos veces seguidas.
#
# Asi que se le quita al incipit, por el final, el tramo que el texto ya dice.
# Por el final porque el incipit viene en tramos -`In diebus illis: Dixit
# Dominus ad Abram:`- y el que se repite es el ultimo: el marco generico se
# queda.
#
# El umbral esta medido, no elegido. Los tramos que de verdad se repiten
# llegan a 0,70 o mas -39 pasan de 0,85, uno queda en 0,81 y catorce en 0,70:
# `Dixit Iesus discipulis suis` contra `Tunc Iesus dixit discipulis suis`-; el
# primero que *no* se repite esta en 0,62 (`In illo tempore` contra `Ab initio
# autem creaturae masculum et feminam fecit eos`). Entre 0,62 y 0,70 no cae
# ningun caso, y el umbral se pone en ese hueco.
#
# Se recorta el incipit y nunca el texto: cortarle el versiculo seria editar
# la Escritura, que es lo unico que aqui no se toca. Donde el libro reescribe
# sin repetir -`Dixit Iesus discipulis suis` por `Respondit Iesus et dixit
# ei`- se quedan los dos, porque ninguno de los dos es falso.
PARECIDO = 0.68


def recorta_incipit(inc, tramos):
    """El incipit sin los tramos del final que el texto ya dice.

    Devuelve (incipit, cuantos tramos se han ido).
    """
    if not tramos or not tramos[0]:
        return inc, 0
    segs = [x for x in inc.rstrip(":").split(": ") if x]
    texto = FASE20.plano(" ".join(t for _, t in tramos[0]))
    fuera = 0
    while segs:
        p = FASE20.plano(segs[-1])
        if not p:
            segs.pop()
            continue
        hueco = max(3, len(p) // 4)
        r = difflib.SequenceMatcher(None, p, texto[:len(p) + hueco]).ratio()
        if r < PARECIDO:
            break
        segs.pop()
        fuera += 1
    return (": ".join(segs) + ":" if segs else ""), fuera


def formula_1977(libro, base):
    """La formula al modo del libro de 1977, sobre la ya acentuada del proyecto.

    A los profetas el proyecto los presenta `Lectio Prophetiae Ezechielis` o
    `Lectio libri Isaiae`, y el Misal de 1977 `Lectio libri <genitivo>
    prophetae`. El genitivo se toma **acentuado** de la formula del proyecto
    -ultima palabra-, en vez de reescribirlo aqui: asi el acento lo sigue
    poniendo la fase 13 y no se inventa ninguno.
    """
    regla = FASE20.FORMULA_1977.get(libro)
    if not regla:
        return base
    if regla != "profeta":
        return regla
    if not base:
        return base
    gen = base.split()[-1]
    return "Léctio libri %s prophétae" % gen


def main(argv=None):
    # `argv` para que la fase 15 pueda llamarla sin que le lleguen los suyos
    ap = argparse.ArgumentParser()
    ap.parse_args(argv)
    inf = ["El leccionario de 1977 para la app", ""]

    clem = json.load(io.open(os.path.join(DATOS, "lecturas_clementina.json"),
                             encoding="utf-8"))
    nova = json.load(io.open(os.path.join(DATOS, "lecturas_nova.json"),
                             encoding="utf-8"))
    bc, bn = clem["bloques"], nova["bloques"]
    if set(bc) != set(bn):
        inf.append("   AVISO: los dos leccionarios no traen las mismas claves")

    peri = json.load(io.open(os.path.join(DATA, "lect1977_pericopas.json"),
                             encoding="utf-8"))
    exacta, floja = {}, {}
    for p in peri:
        segs = [tuple(s) for s in p["segs"]]
        exacta[FASE20.clave_de(p["libro"], segs)] = p
        s0 = sorted(segs)[0]
        floja.setdefault((p["libro"], s0[0], s0[1]), p)

    s2l = siglas_a_libro()
    salida = collections.OrderedDict()
    cuenta = collections.Counter()
    sin_libro = collections.Counter()
    for clave in bn:
        piezas = []
        for i, pz_n in enumerate(bn[clave]):
            lista_c = bc.get(clave, [])
            pz_c = lista_c[i] if i < len(lista_c) else pz_n
            sigla, segs = parte_cita(pz_n.get("c"))
            libro = s2l.get(sigla)
            if libro is None:
                sin_libro[sigla or "?"] += 1
            if libro == "Psalmi" or libro in NUEVO_TESTAMENTO or libro is None:
                fuente, pz = "nova", dict(pz_n)
            else:
                fuente, pz = "clementina", a_la_nova(dict(pz_c))
                # el rotulo y la cita los pone siempre el mismo lado, para que
                # no se mezclen dos maneras de citar en la misma pagina
                pz["t"], pz["c"] = pz_n["t"], pz_n["c"]
                if "q" in pz_n:
                    pz["q"] = pz_n["q"]
                elif "q" in pz:
                    del pz["q"]
            cuenta[fuente] += 1
            if libro and "f" in pz_n:
                f = formula_1977(libro, pz_n.get("f"))
                if f:
                    pz["f"] = f
                    if f != pz_n.get("f"):
                        cuenta["formula al modo de 1977"] += 1
            p77 = None
            if libro and segs:
                p77 = exacta.get(FASE20.clave_de(libro, segs))
                if p77 is None:
                    s0 = sorted(segs)[0]
                    p77 = floja.get((libro, s0[0], s0[1]))
            if p77 is not None:
                cuenta["enganchada con el libro de 1977"] += 1
                if p77["incipit"] and pz.get("k") == "lectura":
                    inc, fuera = recorta_incipit(p77["incipit"], pz.get("g"))
                    if inc:
                        pz["i"] = inc
                        cuenta["con incipit"] += 1
                    cuenta["tramos de incipit que el texto ya decia"] += fuera
            piezas.append(pz)
        salida[clave] = piezas

    total = sum(len(v) for v in salida.values())
    inf.append("   %d bloques, %d piezas" % (len(salida), total))
    for k in ("clementina", "nova", "enganchada con el libro de 1977",
              "con incipit", "tramos de incipit que el texto ya decia",
              "formula al modo de 1977"):
        inf.append("      %5d  %s" % (cuenta[k], k))
    inf.append("      %5d  piezas enganchadas, de %d  (%.1f %%)"
               % (cuenta["enganchada con el libro de 1977"], total,
                  cuenta["enganchada con el libro de 1977"] * 100.0 / total))
    if sin_libro:
        inf.append("   siglas sin libro (se quedan con la Nova): %s"
                   % ", ".join("%s x%d" % kv for kv in sin_libro.most_common(8)))

    obj = {"fuente": "lect1977", "titulo": TITULO,
           "cabecera": CABECERA, "cierre": nova["cierre"], "bloques": salida}
    ruta = os.path.join(DATOS, "lecturas_lect1977.json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
    inf.append("")
    inf.append("escrito app/datos/lecturas_lect1977.json  (%d KB)"
               % (os.path.getsize(ruta) // 1024))

    with open(os.path.join(DATA, "lect1977_app_qa.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(inf) + "\n")
    print("\n".join(inf))


if __name__ == "__main__":
    main()
