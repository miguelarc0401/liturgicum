"""Fase 5 - Resolucion: de la referencia al texto latino.

Toma data/index_master.json (con sus segmentos ya parseados) y saca los
versiculos correspondientes del corpus latino elegido:

    --fuente clementina   data/vulgata.json       (Biblia Sacra Clementina)
    --fuente nova         data/nova_vulgata.json  (Nova Vulgata, la liturgica)

Criterios:
  * Los sufijos a/b/c de los leccionarios modernos no existen en el texto
    latino: se toma el VERSICULO ENTERO y se deja constancia en el aparato.
  * Una cita puede tener tramos discontinuos (7, 1-3. 15-17); se conservan
    como tramos separados para que la maquetacion decida como marcarlos.
  * Todo versiculo que no exista se registra en unresolved*.csv. El objetivo
    es que no haya ni una sorpresa silenciosa.

Lo propio de la Nova Vulgata:
  * los nombres de los libros cambian (data/books_nova.csv);
  * los SALMOS van numerados por el hebreo, mientras el leccionario -y el
    propio Ordo lectionum Missae- los cita por el griego, asi que hay que
    renumerarlos (data/psalmi_lect_nova.csv);
  * el resto de la versificacion es ya la moderna, que es la que usa el
    leccionario, de modo que no hace falta remapear casi nada
    (data/versification_map_nova.csv, normalmente vacio);
  * en Jue 19 y Ba 6 la edicion imprime un encabezamiento sin numerar, que el
    corpus guarda con la clave "0" y que se recupera junto con el versiculo 1.

Salida: data/readings_latin[_nova].json, data/unresolved[_nova].csv,
        data/resolve_qa[_nova].txt

Uso:  python src/5_resolve.py [--fuente clementina|nova]
"""

import argparse
import csv
import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

FUENTES = {
    "clementina": {
        "corpus": "vulgata.json",
        "versificacion": "versification_map.csv",
        "salida": "readings_latin.json",
        "unresolved": "unresolved.csv",
        "qa": "resolve_qa.txt",
        "libros": None,
        "salmos": None,
    },
    "nova": {
        "corpus": "nova_vulgata.json",
        "versificacion": "versification_map_nova.csv",
        "salida": "readings_latin_nova.json",
        "unresolved": "unresolved_nova.csv",
        "qa": "resolve_qa_nova.txt",
        "libros": "books_nova.csv",
        "salmos": "psalmi_lect_nova.csv",
    },
}


def load_libros_nova(path):
    """Clementina -> Nova Vulgata, los 73 nombres de libro."""
    tabla = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            tabla[row["clementina"].strip()] = row["nova"].strip()
    return tabla


def load_salmos_nova(path):
    """Reglas de renumeracion de los salmos, del griego al hebreo."""
    reglas = []
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            reglas.append((int(row["sal_desde"]), int(row["sal_hasta"]),
                           int(row["vers_desde"]), int(row["vers_hasta"]),
                           row["hebreo"].strip(), int(row["offset"]),
                           row.get("nota", "")))
    return reglas


def remap_salmo(reglas, chap, verse, avisos):
    """(salmo hebreo, versiculo) a partir del salmo griego del leccionario."""
    for s1, s2, v1, v2, heb, off, nota in reglas:
        if s1 <= chap <= s2 and v1 <= verse <= v2:
            if heb == "=":
                nuevo = chap
            elif heb.startswith("+"):
                nuevo = chap + int(heb[1:])
            else:
                nuevo = int(heb)
            if off:
                avisos.append("Ps %d,%d -> %d,%d (%s)"
                              % (chap, verse, nuevo, verse + off, nota[:60]))
            return nuevo, verse + off
    avisos.append("Ps %d,%d SIN REGLA" % (chap, verse))
    return chap, verse


def load_versification(path):
    """Reglas modernas -> Clementina.

    Cada regla es (libro, cap, v1, v2, cap_destino, offset, expandir).
    'expandir' sirve para los casos en que la Clementina PARTE en dos un
    versiculo moderno (Jn 6,51): hay que traerse tambien el siguiente.
    """
    rules = []
    if not os.path.exists(path):
        return rules
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rules.append((row["libro_vulgata"].strip(), int(row["cap"]),
                          int(row["vers_desde"]), int(row["vers_hasta"]),
                          int(row["cap_destino"]), int(row["offset"]),
                          int(row.get("expandir") or 0)))
    return rules


def remap(ctx, book, chap, verse):
    """(cap, [versiculos]) de la numeracion del leccionario a la del corpus."""
    for b, c, v1, v2, cdst, off, exp in ctx["reglas"]:
        if b == book and c == chap and v1 <= verse <= v2:
            base = verse + off
            return cdst, list(range(base, base + 1 + exp))
    if ctx["salmos"] and book == "Psalmi":
        c, v = remap_salmo(ctx["salmos"], chap, verse, ctx["avisos"])
        return c, [v]
    return chap, [verse]


def verse_list(corpus, book, chap):
    ch = corpus.get(book, {}).get(str(chap))
    if not ch:
        return []
    return sorted(int(v) for v in ch if re.match(r"^\d+$", v))


def claves_de(ch, real_v, con_titulus):
    """Claves del corpus que hay que traer para un numero de versiculo.

    Ademas del numero pelado se recogen sus letras (Est 4, 17a-17k, 1 Par 4,
    18a-18b, Ez 40, 42a-42b), porque la Nova Vulgata parte algunos versiculos
    y el leccionario los cita con el numero entero. Y el encabezamiento sin
    numerar de Jue 19 y Ba 6, que vive en la clave "0", se recupera con el
    versiculo 1.
    """
    exacta = str(real_v)
    if exacta in ch:
        claves = [exacta]
    else:
        claves = [k for k in ch if re.match(r"^%d[a-z]+$" % real_v, k)]
    if con_titulus and real_v == 1 and "0" in ch:
        claves = ["0"] + claves
    return claves


def take(corpus, book, chap, first, last, missing, ctx, seen=None):
    """Versiculos [first..last]; traduce la numeracion y anota los que falten.

    La deduplicacion es necesaria porque la Clementina funde algunos
    versiculos modernos en uno solo (Hch 7,58-59; Mc 4,40-41; Ps 15,10-11):
    dos numeros del leccionario apuntan entonces al mismo texto.
    """
    out = []
    for v in range(first, last + 1):
        real_chap, real_vv = remap(ctx, book, chap, v)
        ch = corpus.get(book, {}).get(str(real_chap))
        if ch is None:
            missing.append("%s %s (capitulo inexistente)" % (book, real_chap))
            continue
        for real_v in real_vv:
            claves = claves_de(ch, real_v, ctx["titulus"])
            if not claves:
                if (book, str(real_chap), str(real_v)) in ctx["omitidos"]:
                    ctx["omisiones"].append("%s %s,%s" % (book, real_chap,
                                                          real_v))
                else:
                    missing.append("%s %s,%s" % (book, real_chap, real_v))
                continue
            for k in claves:
                if seen is not None:
                    if (real_chap, k) in seen:
                        continue
                    seen.add((real_chap, k))
                out.append({"cap": real_chap,
                            "vers": int(k) if k.isdigit() else k,
                            "texto": ch[k]})
    return out


def resolve_segment(corpus, book, seg, missing, ctx, seen=None):
    # capitulo entero
    if seg.get("desde") is None:
        vs = verse_list(corpus, book, seg["cap"])
        if not vs:
            missing.append("%s %s (capitulo inexistente)" % (book, seg["cap"]))
            return []
        return take(corpus, book, seg["cap"], vs[0], vs[-1], missing, ctx, seen)

    # tramo que cruza de capitulo: 8,23b - 9,3
    if "cap_hasta" in seg:
        out = []
        c1, c2 = seg["cap"], seg["cap_hasta"]
        first_ch = verse_list(corpus, book, c1)
        if not first_ch:
            missing.append("%s %s (capitulo inexistente)" % (book, c1))
            return out
        out += take(corpus, book, c1, seg["desde"], first_ch[-1], missing,
                    ctx, seen)
        for c in range(c1 + 1, c2):
            vs = verse_list(corpus, book, c)
            if vs:
                out += take(corpus, book, c, vs[0], vs[-1], missing, ctx, seen)
        out += take(corpus, book, c2, 1, seg["hasta"], missing, ctx, seen)
        return out

    return take(corpus, book, seg["cap"], seg["desde"], seg["hasta"], missing,
                ctx, seen)


def load_overrides(path):
    """Citas que no se resuelven con aritmetica y se dan tramo a tramo.

    El unico caso hasta ahora son las adiciones griegas de Ester, que la
    Vulgata pone como capitulos aparte y la Nova Vulgata dentro del cap. 4 con
    versiculos en letras, sin correspondencia versiculo a versiculo.
    """
    tabla = {}
    if not os.path.exists(path):
        return tabla
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            tramos = []
            cap = ""
            for grupo in row["tramos"].split(";"):
                claves = []
                for x in grupo.strip().split("."):
                    # "4:17p.17q.17r": el capitulo se escribe una sola vez
                    izq, sep, der = x.strip().partition(":")
                    if sep:
                        cap, v = izq.strip(), der.strip()
                    else:
                        v = izq.strip()
                    claves.append((cap, v))
                tramos.append(claves)
            tabla[row["cita_lect"].strip()] = {
                "libro": row["libro_nova"].strip(), "tramos": tramos,
                "cita": row["cita_nova"].strip(), "nota": row.get("nota", "")}
    return tabla


def resolve_override(corpus, ov, missing):
    tramos = []
    for grupo in ov["tramos"]:
        vs = []
        for cap, v in grupo:
            t = corpus.get(ov["libro"], {}).get(cap, {}).get(v)
            if t is None:
                missing.append("%s %s,%s (override)" % (ov["libro"], cap, v))
                continue
            vs.append({"cap": int(cap), "vers": v, "texto": t})
        if vs:
            tramos.append(vs)
    return tramos


def load_omissiones(path):
    """Versiculos que la Nova Vulgata declara que no trae (Mt 17,21...)."""
    fuera = set()
    if not os.path.exists(path):
        return fuera
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            fuera.add((row["libro"].strip(), row["cap"].strip(),
                       row["vers"].strip()))
    return fuera


def cita_renumerada(canonica, segs, libros_nova, salmos, avisos):
    """La cita en la numeracion del corpus, cuando no es la del leccionario.

    Solo cambia en los salmos: el leccionario (y el propio Ordo lectionum
    Missae) los cita por el griego, y la Nova Vulgata los imprime por el
    hebreo. Devuelve "" cuando las dos numeraciones coinciden.
    """
    if not salmos or not segs or segs[0].get("libro") != "Psalmi":
        return ""
    caps = []
    for s in segs:
        c, _ = remap_salmo(salmos, s["cap"], s.get("desde") or 1, avisos)
        if c not in caps:
            caps.append(c)
    if len(caps) == 1 and caps[0] == segs[0]["cap"]:
        return ""
    return "Ps " + "/".join(str(c) for c in caps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuente", default="clementina", choices=sorted(FUENTES),
                    help="corpus latino del que se saca el texto")
    ap.add_argument("--anexos", action="store_true",
                    help="resuelve data/anexos_index.json en vez del indice "
                         "maestro; misma maquinaria, otra entrada")
    args = ap.parse_args()
    cfg = dict(FUENTES[args.fuente])
    entrada = "index_master.json"
    if args.anexos:
        # Los anexos pasan por exactamente el mismo resolutor que las lecturas:
        # mismas reglas de versificacion, mismos overrides, misma renumeracion
        # de salmos. Lo unico que cambia es de donde vienen las filas y adonde
        # van, para no mezclar los recuentos del leccionario con los del anexo.
        entrada = "anexos_index.json"
        for k in ("salida", "unresolved", "qa"):
            cfg[k] = "anexos_" + cfg[k]

    rows = json.load(open(os.path.join(DATA, entrada), encoding="utf-8"))
    corpus = json.load(open(os.path.join(DATA, cfg["corpus"]),
                            encoding="utf-8"))
    reglas = load_versification(os.path.join(DATA, cfg["versificacion"]))
    libros_nova = (load_libros_nova(os.path.join(DATA, cfg["libros"]))
                   if cfg["libros"] else None)
    salmos = (load_salmos_nova(os.path.join(DATA, cfg["salmos"]))
              if cfg["salmos"] else None)
    ctx = {"reglas": reglas, "salmos": salmos, "avisos": [],
           "omitidos": load_omissiones(os.path.join(DATA,
                                                    "nova_omissiones.csv"))
           if args.fuente == "nova" else set(),
           "omisiones": [], "titulus": args.fuente == "nova"}
    print("fuente: %s (%s)" % (args.fuente, cfg["corpus"]))
    print("reglas de versificacion cargadas: %d" % len(reglas))
    if salmos:
        print("reglas de renumeracion de salmos: %d" % len(salmos))
    if libros_nova:
        faltan = sorted({r["libro_vulgata"] for r in rows
                         if r.get("libro_vulgata")
                         and r["libro_vulgata"] not in libros_nova})
        if faltan:
            raise SystemExit("libros sin equivalencia en books_nova.csv: %s"
                             % ", ".join(faltan))

    overrides = (load_overrides(os.path.join(DATA, "nova_overrides.csv"))
                 if args.fuente == "nova" else {})
    if overrides:
        print("citas resueltas a mano (overrides): %d" % len(overrides))

    out, unresolved = [], []
    n_ok = n_skip = n_override = 0
    verses_total = 0
    letters = Counter()
    books_used = Counter()

    def traduce(nombre):
        return libros_nova.get(nombre, nombre) if libros_nova else nombre

    for r in rows:
        segs = r.get("_segmentos")
        if not segs or not r.get("libro_vulgata"):
            n_skip += 1
            continue
        book = traduce(r["libro_vulgata"])
        missing = []
        tramos = []
        seen = set()
        ov = overrides.get(r["cita_normalizada"])
        if ov:
            book = ov["libro"]
            tramos = resolve_override(corpus, ov, missing)
            n_override += 1
        for seg in ([] if ov else segs):
            # un segmento puede traer su propio libro ("1S 3,9; Jn 6,68c")
            sbook = traduce(seg["libro"]) if seg.get("libro") else book
            vs = resolve_segment(corpus, sbook, seg, missing, ctx, seen)
            if vs:
                tramos.append(vs)
            for k in ("desde_let", "hasta_let"):
                if seg.get(k):
                    letters[seg[k]] += 1

        nv = sum(len(t) for t in tramos)
        verses_total += nv
        for lb in (r.get("libros") or [r["libro_vulgata"]]):
            books_used[traduce(lb)] += 1
        entry = {
            "archivo": r["archivo"], "cel_n": r.get("cel_n", 0),
            "orden": r["orden"],
            "leccionario": r["leccionario"], "ciclo": r["ciclo"],
            "celebracion": r["celebracion"], "tipo": r["tipo"],
            "variante": r["variante"], "canonica": r["cita_normalizada"],
            "canonica_corpus": (ov["cita"] if ov else
                                cita_renumerada(r["cita_normalizada"], segs,
                                                libros_nova, salmos,
                                                ctx["avisos"])),
            "libro_vulgata": book, "sigla": r.get("sigla", ""),
            "aprox_cf": r["aprox_cf"], "antifona_ref": r.get("antifona_ref", ""),
            "antifona_es": r.get("antifona", ""),
            "n_versiculos": nv, "tramos": tramos,
            "faltantes": missing or None,
        }
        # los anexos traen datos propios (a que anexo pertenecen, su numero en
        # la lista, su castellano); viajan tal cual hasta la composicion
        for k in ("_anexo", "_n", "_es", "_tiempo", "_seccion_pagina",
                  "_fecha", "_grado", "_comunes", "_opcion"):
            if k in r:
                entry[k] = r[k]
        out.append(entry)
        if missing:
            unresolved.append({
                "archivo": r["archivo"], "celebracion": r["celebracion"],
                "tipo": r["tipo"], "cita_cruda": r["cita_cruda"],
                "cita_normalizada": r["cita_normalizada"],
                "libro_vulgata": book, "faltan": "; ".join(missing[:12]),
            })
        else:
            n_ok += 1

    with open(os.path.join(DATA, cfg["salida"]), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    cols = ["archivo", "celebracion", "tipo", "cita_cruda",
            "cita_normalizada", "libro_vulgata", "faltan"]
    with open(os.path.join(DATA, cfg["unresolved"]), "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(unresolved)

    lines = []
    lines.append("fuente                          : %s" % args.fuente)
    lines.append("lecturas con referencia biblica : %d" % len(out))
    lines.append("resueltas del todo              : %d (%.1f%%)"
                 % (n_ok, 100.0 * n_ok / len(out) if out else 0))
    lines.append("con algun versiculo ausente     : %d" % len(unresolved))
    lines.append("sin referencia (aleluyas libres): %d" % n_skip)
    lines.append("versiculos latinos extraidos    : %d" % verses_total)
    if overrides:
        lines.append("citas resueltas por override    : %d" % n_override)
    if ctx["omisiones"]:
        lines.append("")
        lines.append("versiculos que la edicion NO TRAE porque faltan en el "
                     "texto critico (%d):" % len(ctx["omisiones"]))
        for x in sorted(set(ctx["omisiones"])):
            lines.append("   %s" % x)
    sin_regla = sorted({a for a in ctx["avisos"] if "SIN REGLA" in a})
    if sin_regla:
        lines.append("")
        lines.append("SALMOS SIN REGLA DE RENUMERACION (%d):" % len(sin_regla))
        lines.extend("   " + x for x in sin_regla[:40])
    renumerados = sorted({a for a in ctx["avisos"] if "SIN REGLA" not in a})
    if renumerados:
        lines.append("")
        lines.append("salmos renumerados con desplazamiento de versiculo (%d):"
                     % len(renumerados))
        lines.extend("   " + x for x in renumerados[:40])
    lines.append("")
    lines.append("sufijos a/b/c encontrados (se toma el versiculo entero):")
    for k, n in letters.most_common(12):
        lines.append("   -%-4s %d" % (k, n))
    lines.append("")
    lines.append("libros mas usados:")
    for b, n in books_used.most_common(15):
        lines.append("   %-24s %d lecturas" % (b, n))
    report = "\n".join(lines)
    print(report)
    with open(os.path.join(DATA, cfg["qa"]), "w", encoding="utf-8") as f:
        f.write(report + "\n")
    if unresolved:
        print("\nRevisa data/%s" % cfg["unresolved"])


if __name__ == "__main__":
    main()
