"""Fase 3 - De las citas en bruto al indice maestro.  ENTREGABLE A.

Convierte cada "Lectura del libro de Isaias 2, 1-5" en una referencia
canonica y verificable:

    libro (es) = Isaias | sigla = Is | vulgata = Isaias
    segmentos  = [{cap:2, desde:1, hasta:5}]
    canonica   = "Is 2,1-5"

Gramatica cubierta:
    2, 1-5            7, 1-3. 15-17       109, 1. 2. 3. 4
    13, 11-14a        88, 4-5. 27 y 29    1, 1-4; 2, 1-2
    8, 23b-9, 3       (salto de capitulo, con guion largo en el original)
    Sal 84,8          Cf. Mt 4, 23        (R.: cf. Is 35, 4)

Salida: data/index_master.json, data/index_master.csv,
        data/unparsed_citations.txt

Uso:  python src/3_normalize_refs.py
"""

import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# plegado de acentos que NO cambia la longitud de la cadena
FOLD = str.maketrans("áàäâéèëêíìïîóòöôúùüûñçÁÀÄÂÉÈËÊÍÌÏÎÓÒÖÔÚÙÜÛÑÇ",
                     "aaaaeeeeiiiioooouuuuncAAAAEEEEIIIIOOOOUUUUNC")

TYPE_LABEL = {
    "lectura_1": "primera lectura", "lectura_2": "segunda lectura",
    "lectura_3": "tercera lectura", "lectura_4": "cuarta lectura",
    "lectura_5": "quinta lectura", "lectura_6": "sexta lectura",
    "lectura_7": "septima lectura", "lectura_8": "octava lectura",
    "salmo": "salmo responsorial", "aleluya": "aleluya",
    "evangelio": "evangelio", "epistola": "epistola",
    "secuencia": "secuencia",
    # los repertorios de los Comunes y de las misas rituales y votivas
    "lectura_at": "lectura del Antiguo Testamento",
    "lectura_nt": "lectura del Nuevo Testamento",
}

# alias que el leccionario usa y que no salen tal cual de Siglas.docx
EXTRA_ALIASES = {
    "Psalmi": ["salmo", "salmos", "sal"],
    "Actus Apostolorum": ["hechos de los apostoles", "hechos"],
    "Apocalypsis": ["apocalipsis"],
    "Canticum Canticorum": ["cantar de los cantares"],
    "Ecclesiasticus": ["eclesiastico", "siracida"],
    "Ecclesiastes": ["eclesiastes", "qohelet"],
    "Lamentationes": ["lamentaciones"],
    "Ad Corinthios I": ["1 cor", "1 co"],
    "Ad Corinthios II": ["2 cor", "2 co"],
    "Ad Timotheum I": ["1 tim", "1 tm"],
    "Ad Timotheum II": ["2 tim", "2 tm"],
    "Ad Thessalonicenses I": ["1 tes", "1 ts"],
    "Ad Thessalonicenses II": ["2 tes", "2 ts"],
    "Petri I": ["1 pe", "1 p"],
    "Petri II": ["2 pe", "2 p"],
}

# erratas del sitio: (archivo, cita cruda) -> cita corregida
OVERRIDES_FILE = "citation_overrides.csv"

# los cuatro evangelios, para el control de coherencia de main()
EVANGELIOS = {"Matthæus", "Marcus", "Lucas", "Joannes"}


def fold(s):
    """minusculas y sin tildes, conservando la longitud (indices validos)."""
    return s.translate(FOLD).lower()


# --------------------------------------------------------------------------
# tabla de alias
# --------------------------------------------------------------------------
def build_aliases(books):
    """lista de (alias_plegado, libro) ordenada de mas largo a mas corto."""
    aliases = []
    for b in books:
        names = set()
        for n in b["es"]:
            f = fold(n).strip()
            names.add(f)
            # "Primero libro de los Reyes" -> "primer libro de los Reyes"
            if f.startswith("primero "):
                names.add("primer " + f[8:])
            # el leccionario suele omitir "Libro de(l)"
            m = re.match(r"^libro de(l| los| la| las)?\s+(.+)$", f)
            if m:
                names.add(m.group(2))
            m = re.match(r"^profecia de\s+(.+)$", f)
            if m:
                names.add(m.group(1))
            m = re.match(r"^evangelio segun san\s+(.+)$", f)
            if m:
                names.add(m.group(1))
            # el leccionario a veces anade o quita "carta"
            # "carta del apostol san Pablo a los Romanos" ->
            # "carta de san Pablo a los Romanos"
            if "del apostol san " in f:
                names.add(f.replace("del apostol san ", "de san ", 1))
            if " carta " in f or f.startswith("carta "):
                names.add(re.sub(r"\bcarta\s+", "", f, count=1).strip())
            else:
                m = re.match(r"^(primera|segunda|tercera)\s+(.+)$", f)
                if m:
                    names.add("%s carta %s" % (m.group(1), m.group(2)))
        names.add(fold(b["sigla"]))
        # libros numerados citados por su nombre corto: "1Cronicas 29, 10",
        # "1Samuel 2, 1", "2Corintios 5, 19"
        mnum = re.match(r"^(\d)\s", b["sigla"])
        if mnum:
            for n in list(names):
                last = n.split()[-1] if n.split() else ""
                if len(last) >= 4:
                    names.add("%s %s" % (mnum.group(1), last))
        for s in b.get("siglas_alt", []):
            names.add(fold(s))
        for a in EXTRA_ALIASES.get(b["vulgata"], []):
            names.add(a)
        for n in names:
            n = re.sub(r"\s+", " ", n).strip()
            if n:
                aliases.append((n, b))
    aliases.sort(key=lambda x: -len(x[0]))
    return aliases


# siglas o nombres pegados al numero: "1Tm 3, 16", "1Crónicas 29, 10"
GLUED_RE = re.compile(r"(\d)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{0,11})(\s+\d)")

# "Salmo 113A" = Heb 114 (Clem 113,1-8);  "Salmo 113B" = Heb 115 (Clem 113,9-26)
PSALM_AB_RE = re.compile(r"\b113\s*([AB])\b", re.I)


def find_book(cita, aliases):
    """(libro, resto_numerico) buscando el alias mas largo seguido de cifras."""
    cita = GLUED_RE.sub(r"\1 \2\3", cita)
    f = fold(cita)
    best = None
    for alias, book in aliases:
        start = 0
        while True:
            i = f.find(alias, start)
            if i < 0:
                break
            start = i + 1
            # debe empezar en frontera de palabra
            if i > 0 and (f[i - 1].isalnum()):
                continue
            j = i + len(alias)
            rest = cita[j:].lstrip("  .,:")
            if rest[:1].isdigit():
                cand = (len(alias), j, book, rest)
                if best is None or cand[0] > best[0] or \
                        (cand[0] == best[0] and cand[1] > best[1]):
                    best = cand
    if best is None:
        return None, None
    return best[2], best[3]


# --------------------------------------------------------------------------
# rangos
# --------------------------------------------------------------------------
VERSE_RE = re.compile(r"^(\d+)\s*([a-z]*)$", re.I)
DASHES = "—–‒‐‑"


def split_verse(tok):
    m = VERSE_RE.match(tok.strip())
    if not m:
        return None
    return int(m.group(1)), m.group(2).lower()


def parse_tail(tail, default_chapter=None, single_chapter=False):
    """Devuelve (segmentos, resto_no_entendido)."""
    tail = tail.strip()
    # el guion largo separa capitulos; el corto, versiculos
    tail = re.sub(r"\s*[%s]\s*" % DASHES, "—", tail)
    tail = tail.replace("—", "|")          # marcador de rango amplio
    tail = re.sub(r"\s+y\s+", ". ", tail)
    segments, leftover = [], []
    # en los libros de un solo capitulo la cita omite el capitulo
    # ("Filemon 9b-10. 12-17")
    chapter = default_chapter

    for chunk in re.split(r"\s*;\s*", tail):
        chunk = chunk.strip(" .")
        if not chunk:
            continue
        # En un salto de capitulo ("32|4, 4") la coma pertenece al salto, no
        # separa tramos: se protege con ~ para que no la parta el split de
        # abajo. Asi funciona igual suelto ("18, 1|19, 42") que dentro de una
        # lista ("3, 9-15. 32|4, 4").
        chunk = re.sub(r"(\d+[a-z]*)\s*\|\s*(\d+)\s*,\s*(\d+[a-z]*)",
                       r"\1|\2~\3", chunk, flags=re.I)

        # el capitulo se separa normalmente con coma, pero el sitio usa a
        # veces punto ("24. 1-2. 8-12") o nada ("50 12-13").
        # En los libros de un solo capitulo no hay capitulo que extraer:
        # "Judas: 17. 20b-25" son los versiculos 17 y 20b-25.
        m = None
        if not single_chapter:
            m = re.match(r"^\s*(\d+)\s*[,.]\s*(\d.*)$", chunk)
            if m is None:
                m = re.match(r"^\s*(\d+)\s+(\d.*)$", chunk)
        if m:
            chapter = int(m.group(1))
            items = m.group(2)
        elif chapter is not None:
            items = chunk
        else:
            # capitulo entero sin versiculos: "Salmo 117"
            if re.fullmatch(r"\d+", chunk):
                segments.append({"cap": int(chunk), "desde": None,
                                 "desde_let": "", "hasta": None, "hasta_let": ""})
                chapter = int(chunk)
                continue
            leftover.append(chunk)
            continue

        # el sitio a veces separa los tramos con coma o con un simple espacio
        # en lugar del punto: "10, 1-12, 17-20"  /  "12, 5-7 11-13"
        for item in re.split(r"\s*[.,]\s*|\s+(?=\d)", items):
            item = item.strip(" .")
            if not item:
                continue
            # salto de capitulo: "23b|9~3"  =  de 23b hasta el cap. 9, v. 3
            cm = re.match(r"^(\d+)([a-z]*)\|(\d+)~(\d+)([a-z]*)$", item, re.I)
            if cm:
                segments.append({"cap": chapter, "desde": int(cm.group(1)),
                                 "desde_let": cm.group(2).lower(),
                                 "cap_hasta": int(cm.group(3)),
                                 "hasta": int(cm.group(4)),
                                 "hasta_let": cm.group(5).lower()})
                chapter = int(cm.group(3))
                continue
            if "|" in item or "~" in item:
                leftover.append(item)
                continue
            parts = re.split(r"\s*-\s*", item)
            if len(parts) == 1:
                v = split_verse(parts[0])
                if not v:
                    leftover.append(item)
                    continue
                segments.append({"cap": chapter, "desde": v[0], "desde_let": v[1],
                                 "hasta": v[0], "hasta_let": v[1]})
            elif len(parts) == 2:
                a, b = split_verse(parts[0]), split_verse(parts[1])
                if not a or not b:
                    leftover.append(item)
                    continue
                segments.append({"cap": chapter, "desde": a[0], "desde_let": a[1],
                                 "hasta": b[0], "hasta_let": b[1]})
            else:
                leftover.append(item)
    return segments, leftover


def canonical(segments):
    """Cadena canonica; admite segmentos de libros distintos ("1 S 3,9; Jn 6,68c")."""
    out, last_chap, last_book = [], None, None
    for s in segments:
        if s["sigla"] != last_book:
            if out:
                out.append("; " + s["sigla"] + " ")
            else:
                out.append(s["sigla"] + " ")
            last_book, last_chap = s["sigla"], None
        elif out and not out[-1].endswith(" "):
            out.append(".")
        if "cap_hasta" in s:
            desde = "%d%s" % (s["desde"], s["desde_let"])
            if s["cap"] != last_chap:
                desde = "%d,%s" % (s["cap"], desde)
            out.append("%s—%d,%d%s" % (desde, s["cap_hasta"], s["hasta"],
                                       s["hasta_let"]))
            last_chap = s["cap_hasta"]
            continue
        if s["desde"] is None:
            out.append("%d" % s["cap"])
            last_chap = s["cap"]
            continue
        piece = "%d%s" % (s["desde"], s["desde_let"])
        if (s["hasta"], s["hasta_let"]) != (s["desde"], s["desde_let"]):
            piece += "-%d%s" % (s["hasta"], s["hasta_let"])
        if s["cap"] != last_chap:
            out.append("%d,%s" % (s["cap"], piece))
            last_chap = s["cap"]
        else:
            out.append(piece)
    return "".join(out).strip()


# --------------------------------------------------------------------------
RESP_RE = re.compile(r"\(\s*R\.?\s*:?\.?\s*(.*?)\s*\)\s*$", re.I)
PREFIX_CF = re.compile(r"^\s*(cf\.?|cfr\.?)\s*", re.I)


def normalize(raw, aliases, rtype=None, psalm_book=None, one_chapter=()):
    """Devuelve el diccionario de referencia de una cita en bruto."""
    cita = raw.strip()
    ref_resp = None
    m = RESP_RE.search(cita)
    if m:
        ref_resp = m.group(1)
        cita = cita[:m.start()].strip()
    if rtype == "secuencia":
        return {"ok": False, "motivo": "sin cita biblica", "raw": raw,
                "benigno": True}
    cita = re.sub(r"^\s*(aleluya|salmo responsorial|interleccional)\s*:?\s*",
                  "", cita, flags=re.I)
    # el Salmo 113 de la Vulgata se cita partido en 113A y 113B
    ab = PSALM_AB_RE.search(cita)
    psalm_offset = 0
    if ab:
        psalm_offset = 8 if ab.group(1).upper() == "B" else 0
        cita = PSALM_AB_RE.sub("113", cita)
    approx = bool(PREFIX_CF.search(cita))
    cita = PREFIX_CF.sub("", cita)
    if not cita or not any(c.isdigit() for c in cita):
        # aleluyas dados como texto suelto, sin referencia biblica
        return {"ok": False, "motivo": "sin cita biblica", "raw": raw,
                "benigno": True}

    # el ';' puede separar tramos del mismo libro ("1, 1-4; 2, 1-2") o
    # introducir otro libro ("1S 3, 9; Jn 6, 68c")
    segments, leftover = [], []
    book = cur = None
    last_chapter = None
    for part in re.split(r"\s*;\s*", cita):
        part = part.strip()
        if not part:
            continue
        b, tail = find_book(part, aliases)
        if b is None and cur is None and rtype == "salmo" and psalm_book:
            # "Salmo responsorial: 22, 1-3a. ..." omite la palabra Salmo
            m = re.match(r"^\s*(\d+\s*[,.].*)$", part)
            if m:
                b, tail = psalm_book, m.group(1)
        if b is None:
            if cur is None:
                return {"ok": False, "motivo": "libro no reconocido",
                        "raw": raw, "resp": ref_resp}
            b, tail = cur, part          # continuacion del mismo libro
        cur = b
        if book is None:
            book = b
        solo_un_cap = b["vulgata"] in one_chapter
        default_chap = 1 if solo_un_cap else last_chapter
        segs, left = parse_tail(tail, default_chap, solo_un_cap)
        for s in segs:
            s["sigla"] = b["sigla"]
            s["libro"] = b["vulgata"]
            if psalm_offset:
                for k in ("desde", "hasta"):
                    if s.get(k) is not None:
                        s[k] += psalm_offset
            last_chapter = s.get("cap_hasta", s["cap"])
        segments += segs
        leftover += left

    if not segments:
        return {"ok": False, "motivo": "rango no entendido: %r" % cita,
                "raw": raw, "resp": ref_resp}
    libros = []
    for s in segments:
        if s["libro"] not in libros:
            libros.append(s["libro"])
    return {"ok": True, "raw": raw, "sigla": book["sigla"], "es": book["es"][0],
            "vulgata": book["vulgata"], "libros": libros, "segmentos": segments,
            "canonica": canonical(segments),
            "aprox": approx, "resp": ref_resp,
            "resto_no_entendido": leftover or None}


def main():
    books = json.load(open(os.path.join(DATA, "books.json"), encoding="utf-8"))
    aliases = build_aliases(books)
    psalm_book = next(b for b in books if b["vulgata"] == "Psalmi")
    corpus = json.load(open(os.path.join(DATA, "vulgata.json"), encoding="utf-8"))
    one_chapter = {name for name, ch in corpus.items() if len(ch) == 1}

    # erratas conocidas del sitio, corregibles a mano sin tocar codigo
    overrides = {}
    opath = os.path.join(DATA, OVERRIDES_FILE)
    if os.path.exists(opath):
        with open(opath, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                overrides[(row["archivo"].strip(),
                           row["cita_cruda"].strip())] = row["cita_correcta"].strip()
    readings = json.load(open(os.path.join(DATA, "readings.json"), encoding="utf-8"))

    rows, failures = [], []
    for cel in readings:
        for r in cel["readings"]:
            raw_cita = overrides.get((cel["source_file"], r["raw_cita"].strip()),
                                     r["raw_cita"])
            ref = normalize(raw_cita, aliases, r["type"], psalm_book, one_chapter)
            row = {
                "leccionario": cel["lectionary"],
                "ciclo": cel.get("cycle") or "",
                "celebracion": cel["celebration"],
                # con "_" delante para que no ensucien el CSV del indice
                # maestro: son datos de la celebracion, no de la cita
                "_fecha": cel.get("fecha") or "",
                "_grado": cel.get("grado") or "",
                "_comunes": cel.get("comunes") or [],
                "_opcion": r.get("opcion") or "",
                "archivo": cel["source_file"],
                "cel_n": cel.get("cel_n", 0),
                "orden": r["slot"],
                "tipo": TYPE_LABEL.get(r["type"], r["type"]),
                "variante": r.get("variant") or "",
                "cita_cruda": r["raw_cita"],
                "sigla": ref.get("sigla", ""),
                "libro_es": ref.get("es", ""),
                "libro_vulgata": ref.get("vulgata", ""),
                "cita_normalizada": ref.get("canonica", ""),
                "aprox_cf": "si" if ref.get("aprox") else "",
                "antifona_ref": ref.get("resp") or "",
                "resumen": r.get("summary") or "",
                "antifona": r.get("response") or "",
                "ok": "si" if ref["ok"] else "NO",
                "motivo": "" if ref["ok"] else ref["motivo"],
            }
            row["_segmentos"] = ref.get("segmentos")
            row["libros"] = ref.get("libros") or ([ref["vulgata"]]
                                                  if ref.get("vulgata") else [])
            rows.append(row)
            if not ref["ok"] and not ref.get("benigno"):
                failures.append("%-14s %-18s %s   -> %s"
                                % (cel["source_file"], row["tipo"],
                                   r["raw_cita"][:70], ref["motivo"]))
            # Una cita que dice "carta" no puede resolverse en un evangelio.
            # Parece de perogrullo y no lo es: el sitio escribio una vez "la
            # primera carta DE apostol san Juan", sin la l, y como ese nombre
            # no casaba con ningun alias, el emparejamiento por el nombre mas
            # largo se quedo con "Juan" -el evangelio- y el leccionario
            # imprimio Jn 5,1-6 donde tocaba 1 Jn 5,1-6. Ni un recuento ni un
            # versiculo ausente: el texto equivocado, en silencio, un domingo.
            if (ref["ok"] and ref.get("vulgata") in EVANGELIOS
                    and re.search(r"\b(carta|ep[íi]stola)\b", raw_cita, re.I)):
                failures.append("%-14s %-18s %s   -> CONTRADICCION: la cita "
                                "dice 'carta' y se ha resuelto en %s"
                                % (cel["source_file"], row["tipo"],
                                   raw_cita[:70], ref["vulgata"]))

    with open(os.path.join(DATA, "index_master.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    cols = [c for c in rows[0] if not c.startswith("_")]
    with open(os.path.join(DATA, "index_master.csv"), "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(DATA, "unparsed_citations.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(failures))

    ok = sum(1 for r in rows if r["ok"] == "si")
    benign = sum(1 for r in rows if r["motivo"] == "sin cita biblica")
    print("%d citas: %d normalizadas (%.1f%%), %d sin cita biblica, %d fallidas"
          % (len(rows), ok, 100.0 * ok / len(rows), benign, len(failures)))
    print("  data/index_master.csv  /  .json")
    if failures:
        print("  fallos en data/unparsed_citations.txt")


if __name__ == "__main__":
    main()
