"""Fase 5b - Comprobacion de que el latin extraido es de verdad el pasaje citado.

Un desfase de versificacion entre la numeracion moderna del leccionario y la
Vulgata Clementina no produce ningun error: produce el texto EQUIVOCADO en
silencio. Esta fase lo caza con dos comprobaciones independientes.

1. RECUENTO. Los versiculos que pide la cita frente a los que se extrajeron.
   Una diferencia delata que la Clementina funde o parte versiculos ahi.

2. COTEJO DE NOMBRES PROPIOS. El castellano de la propia pagina y el latin
   extraido deben compartir los nombres propios y las cifras (Jerusalen /
   Jerusalem, David, Moises / Moyses, 12, 40...). Una puntuacion baja delata
   que se extrajo otro pasaje.

Ninguna de las dos prueba nada por si sola: sirven para ordenar las lecturas de
mas a menos sospechosa y revisar solo la cola.

Salida: data/crosscheck.csv (ordenado por sospecha) y un resumen por pantalla.

Uso:  python src/6_crosscheck.py [--peores 25]
"""

import argparse
import csv
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

STOP = {"senor", "dios", "jesus", "cristo", "el", "la", "en", "y", "de", "que",
        "palabra", "aleluya", "hermanos", "amen", "r", "dominus", "deus",
        "et", "in", "qui", "quia", "autem", "enim", "ait", "dixit"}


def deacc(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def fold_token(t):
    """Reduce una palabra a una raiz comparable entre castellano y latin.

    No es linguistica seria: solo neutraliza las diferencias graficas mas
    constantes (ae/oe -> e, j/i, v/u, ph/f, th/t, ch/c, qu/c, h muda,
    consonantes dobles) para que 'Jerusalén' y 'Jerusalem', o 'eterna' y
    'æterna', caigan en la misma clave.
    """
    t = deacc(t).lower()
    for a, b in (("ae", "e"), ("oe", "e"), ("æ", "e"), ("œ", "e"),
                 ("j", "i"), ("v", "u"), ("y", "i"), ("k", "c"),
                 ("ph", "f"), ("th", "t"), ("ch", "c"), ("qu", "c"),
                 ("h", ""), ("mm", "m"), ("ll", "l"), ("ss", "s")):
        t = t.replace(a, b)
    return t


def keys(text, nmin=4):
    """Claves comparables: raices de palabras largas, mas las cifras."""
    out = set()
    for tok in re.findall(r"\b\d+\b", text):
        out.add("#" + tok)
    for tok in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúüñÆæŒœë]{5,}", text):
        f = fold_token(tok)
        if len(f) >= nmin and f[:nmin] not in STOP:
            out.add(f[:nmin])
    return out


def cited_verses(segs):
    """Versiculos DISTINTOS que pide la cita.

    Hay que contar unicos porque el leccionario trocea un mismo versiculo en
    sub-versiculos ("29, 10. 11abc. 11d-12a. 12bcd" son solo 10, 11 y 12).
    """
    vv = set()
    for s in segs:
        if "cap_hasta" in s or s.get("desde") is None:
            return None            # no se puede saber sin mirar el corpus
        for v in range(s["desde"], s["hasta"] + 1):
            vv.add((s["cap"], v))
    return len(vv)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peores", type=int, default=25)
    ap.add_argument("--fuente", default="clementina",
                    choices=["clementina", "nova"],
                    help="corpus latino contra el que se coteja el castellano")
    args = ap.parse_args()
    suf = "" if args.fuente == "clementina" else "_nova"

    index = {(r["archivo"], r.get("cel_n", 0), r["orden"]): r for r in
             json.load(open(os.path.join(DATA, "index_master.json"),
                            encoding="utf-8"))}
    readings = json.load(open(os.path.join(DATA, "readings.json"),
                              encoding="utf-8"))
    es_text = {}
    for c in readings:
        for r in c["readings"]:
            es_text[(c["source_file"], c.get("cel_n", 0), r["slot"])] =                 " ".join(r.get("texto_es", []))

    latin = json.load(open(os.path.join(DATA, "readings_latin%s.json" % suf),
                           encoding="utf-8"))

    # reglas de versificacion, para saber que descuadres ya estan explicados
    rules = []
    rpath = os.path.join(DATA, "versification_map%s.csv" % suf)
    if os.path.exists(rpath):
        with open(rpath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rules.append((row["libro_vulgata"].strip(), int(row["cap"]),
                              int(row["vers_desde"]), int(row["vers_hasta"])))

    # la Nova Vulgata declara que no trae ciertos versiculos, porque faltan en
    # el texto critico (Mc 9,44; Jn 5,4; Hch 8,37...). Cuando el leccionario
    # los pide, el recuento baja y eso NO es un error de versificacion.
    omitidos = []
    opath = os.path.join(DATA, "nova_omissiones.csv")
    if suf and os.path.exists(opath):
        with open(opath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                omitidos.append((row["libro"].strip(), int(row["cap"]),
                                 int(row["vers"])))
    # y las citas que se resuelven a mano (las adiciones griegas de Ester)
    overrides = set()
    vpath = os.path.join(DATA, "nova_overrides.csv")
    if suf and os.path.exists(vpath):
        with open(vpath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                overrides.add(row["cita_lect"].strip())

    def explained(book, segs, cita=""):
        if cita in overrides:
            return True
        for s in segs:
            if s.get("desde") is None:
                continue
            c = s["cap"]
            for b, rc, v1, v2 in rules:
                if b == s.get("libro", book) and rc == c \
                        and not (s["hasta"] < v1 or s["desde"] > v2):
                    return True
            for b, rc, v in omitidos:
                if b == book and rc == c and s["desde"] <= v <= s["hasta"]:
                    return True
        return False

    rows = []
    for e in latin:
        k = (e["archivo"], e.get("cel_n", 0), e["orden"])
        idx = index.get(k)
        segs = (idx or {}).get("_segmentos") or []
        pedidos = cited_verses(segs)
        obtenidos = e["n_versiculos"]
        desfase = "" if pedidos is None else (obtenidos - pedidos)

        es = es_text.get(k, "")
        la = " ".join(v["texto"] for t in e["tramos"] for v in t)
        kes, kla = keys(es), keys(la)
        comunes = kes & kla
        score = len(comunes) / len(kes) if kes else None

        rows.append({
            "archivo": e["archivo"], "orden": e["orden"],
            "celebracion": e["celebracion"], "tipo": e["tipo"],
            "cita": e["canonica"], "libro": e["libro_vulgata"],
            "vv_pedidos": "" if pedidos is None else pedidos,
            "vv_obtenidos": obtenidos, "desfase": desfase,
            "explicado": "si" if (desfase and explained(e["libro_vulgata"], segs, e["canonica"]))
                         else "",
            "nombres_es": len(kes), "nombres_comunes": len(comunes),
            "coincidencia": "" if score is None else round(score, 3),
            "solo_en_es": " ".join(sorted(kes - kla)[:8]),
        })

    # sospecha: primero el desfase de recuento, luego la baja coincidencia
    def suspicion(r):
        if r["explicado"] == "si":
            d = 0            # descuadre ya justificado por una regla
        else:
            d = abs(r["desfase"]) if isinstance(r["desfase"], int) else 0
        s = r["coincidencia"] if isinstance(r["coincidencia"], float) else 1.0
        comparable = isinstance(r["coincidencia"], float) and r["nombres_es"] >= 8
        return (-d, s if comparable else 1.0)

    rows.sort(key=suspicion)

    with open(os.path.join(DATA, "crosscheck%s.csv" % suf), "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    con_desfase = [r for r in rows if isinstance(r["desfase"], int) and r["desfase"]]
    sin_explicar = [r for r in con_desfase if r["explicado"] != "si"]
    comparables = [r for r in rows
                   if isinstance(r["coincidencia"], float) and r["nombres_es"] >= 8]
    # umbral calibrado: con emparejamientos al azar la coincidencia mediana
    # es 0.02 y el percentil 90 es 0.067; por debajo de 0.07 conviene mirar
    bajos = [r for r in comparables if r["coincidencia"] < 0.07]

    print("lecturas comprobadas            : %d" % len(rows))
    print("con desfase de recuento         : %d" % len(con_desfase))
    print("  ya explicado por una regla    : %d" % (len(con_desfase) - len(sin_explicar)))
    print("  SIN EXPLICAR                  : %d" % len(sin_explicar))
    print("cotejables por nombres propios  : %d" % len(comparables))
    print("  coincidencia < 7%% (revisar)    : %d" % len(bajos))
    if comparables:
        med = sorted(r["coincidencia"] for r in comparables)[len(comparables) // 2]
        print("  coincidencia mediana           : %.2f" % med)
    print("\n--- las %d mas sospechosas ---" % args.peores)
    for r in rows[:args.peores]:
        print("  %-22s %-20s ped=%-3s obt=%-3s desf=%-3s coinc=%-5s %s"
              % (r["celebracion"][:22], r["cita"][:20], r["vv_pedidos"],
                 r["vv_obtenidos"], r["desfase"], r["coincidencia"],
                 r["solo_en_es"][:34]))
    print("\ndetalle completo en data/crosscheck%s.csv" % suf)


if __name__ == "__main__":
    main()
