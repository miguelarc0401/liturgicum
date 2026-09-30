"""Fase 5c - Buscador automatico de desfases de versificacion.

Alinear a mano cada libro no escala. Este barrido prueba, para CADA lectura,
desplazamientos de -3 a +3 versiculos y se queda con el que mejor casa con el
castellano de la propia pagina, usando el mismo cotejo de raices que
6_crosscheck.py.

No decide nada: PROPONE. Si un desfase distinto de 0 puntua claramente mejor
que el 0, la lectura sale en la lista para que una persona la verifique y, si
procede, anada la regla a data/versification_map.csv.

El cotejo es debil en poesia (los salmos comparten pocas raices con el latin),
asi que solo se examinan lecturas con texto suficiente.

Salida: data/offset_proposals.csv

Uso:  python src/7_offset_scan.py [--margen 0.04] [--min-vv 4]
"""

import argparse
import csv
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--margen", type=float, default=0.04,
                    help="cuanto debe mejorar el desfase frente a 0")
    ap.add_argument("--min-vv", type=int, default=4)
    ap.add_argument("--rango", type=int, default=3)
    args = ap.parse_args()

    cc = load_module("cc", os.path.join(ROOT, "src", "6_crosscheck.py"))
    rs = load_module("rs", os.path.join(ROOT, "src", "5_resolve.py"))

    corpus = json.load(open(os.path.join(DATA, "vulgata.json"), encoding="utf-8"))
    rules = rs.load_versification(os.path.join(DATA, "versification_map.csv"))
    index = {(r["archivo"], r.get("cel_n", 0), r["orden"]): r for r in
             json.load(open(os.path.join(DATA, "index_master.json"),
                            encoding="utf-8"))}
    readings = json.load(open(os.path.join(DATA, "readings.json"),
                              encoding="utf-8"))
    es_text = {}
    for c in readings:
        for r in c["readings"]:
            es_text[(c["source_file"], c.get("cel_n", 0), r["slot"])] = \
                " ".join(r.get("texto_es", []))

    def extract(book, segs, shift):
        """Texto latino de la cita aplicando un desplazamiento adicional."""
        missing, out = [], []
        for seg in segs:
            s = dict(seg)
            for k in ("desde", "hasta"):
                if s.get(k) is not None:
                    s[k] += shift
            if s.get("desde") is not None and s["desde"] < 1:
                return None
            vs = rs.resolve_segment(corpus, s.get("libro", book), s, missing,
                                    rules, set())
            out += vs
        if missing or not out:
            return None
        return " ".join(v["texto"] for v in out)

    proposals = []
    examined = 0
    for key, r in index.items():
        segs = r.get("_segmentos")
        if not segs or not r.get("libro_vulgata"):
            continue
        if any("cap_hasta" in s or s.get("desde") is None for s in segs):
            continue
        nvv = sum(s["hasta"] - s["desde"] + 1 for s in segs)
        if nvv < args.min_vv:
            continue
        es = es_text.get(key, "")
        kes = cc.keys(es)
        if len(kes) < 12:
            continue
        examined += 1

        scores = {}
        for shift in range(-args.rango, args.rango + 1):
            la = extract(r["libro_vulgata"], segs, shift)
            if la is None:
                continue
            kla = cc.keys(la)
            scores[shift] = len(kes & kla) / len(kes)
        if 0 not in scores:
            continue
        best = max(scores, key=lambda s: scores[s])
        if best != 0 and scores[best] - scores[0] >= args.margen:
            proposals.append({
                "archivo": r["archivo"], "celebracion": r["celebracion"],
                "tipo": r["tipo"], "cita": r["cita_normalizada"],
                "libro_vulgata": r["libro_vulgata"],
                "desfase_propuesto": best,
                "coincidencia_0": round(scores[0], 3),
                "coincidencia_propuesta": round(scores[best], 3),
                "mejora": round(scores[best] - scores[0], 3),
            })

    proposals.sort(key=lambda p: -p["mejora"])
    if proposals:
        with open(os.path.join(DATA, "offset_proposals.csv"), "w",
                  encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(proposals[0]))
            w.writeheader()
            w.writerows(proposals)

    print("lecturas examinadas          : %d" % examined)
    print("con un desfase mejor que 0   : %d" % len(proposals))
    for p in proposals[:30]:
        print("  %-22s %-22s %-18s despl=%+d  %.3f -> %.3f"
              % (p["celebracion"][:22], p["cita"][:22], p["libro_vulgata"][:18],
                 p["desfase_propuesto"], p["coincidencia_0"],
                 p["coincidencia_propuesta"]))
    if proposals:
        print("\ndetalle en data/offset_proposals.csv "
              "(son PROPUESTAS: hay que verificarlas antes de crear la regla)")


if __name__ == "__main__":
    main()
