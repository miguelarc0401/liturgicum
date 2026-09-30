"""Etapa 0 - Tabla de libros biblicos a partir de Siglas.docx.

Lee la tabla de 3 columnas (sigla | nombre en los leccionarios | nombre en la
Vulgata), desdobla las filas que agrupan varios libros ("1 y 2 Co" ->
"1 Co" + "2 Co") y comprueba que todo nombre de la Vulgata exista de verdad en
data/vulgata.json.

Salida: data/books.json

Uso:  python src/0_build_books.py
"""

import argparse
import json
import os
import re
import unicodedata
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCX = os.path.join(ROOT, "Siglas.docx")
DATA = os.path.join(ROOT, "data")

ORDINALS = {
    "1": ["Primera", "Primer", "Primero"],
    "2": ["Segunda", "Segundo"],
    "3": ["Tercera", "Tercero"],
}


def norm(s):
    """minusculas, sin tildes, sin puntuacion, espacios colapsados."""
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def read_table(path):
    """Filas de la primera tabla del .docx como listas de celdas."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    rows = []
    for tr in re.findall(r"<w:tr[ >].*?</w:tr>", xml, re.S):
        cells = []
        for tc in re.findall(r"<w:tc[ >].*?</w:tc>", tr, re.S):
            paras = []
            for p in re.findall(r"<w:p[ >].*?</w:p>", tc, re.S):
                txt = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S))
                txt = (txt.replace("&amp;", "&").replace("&lt;", "<")
                          .replace("&gt;", ">").replace("&quot;", '"')
                          .replace("&apos;", "'"))
                if txt.strip():
                    paras.append(txt.strip())
            cells.append(paras)
        if cells:
            rows.append(cells)
    return rows


def split_row(sigla, es_names, vulg):
    """Desdobla una fila en una o varias entradas de libro."""
    vulgs = [v.strip() for v in vulg.split("/")]

    # "Ecl (Qo)" / "Eclo (Si)": varias siglas para un mismo libro
    m = re.match(r"^\s*(\S+)\s*\((\S+)\)\s*$", sigla)
    if m and len(vulgs) == 1:
        return [{"sigla": m.group(1), "siglas_alt": [m.group(2)],
                 "es": es_names, "vulgata": vulgs[0]}]

    # "1 y 2 Co" / "1, 2 y 3 Jn": varios libros numerados
    m = re.match(r"^\s*([\d,\sy]+?)\s+(\S+)\s*$", sigla)
    if m and len(vulgs) > 1:
        nums = re.findall(r"\d", m.group(1))
        stem = m.group(2)
        # "Primera y segunda carta ... a los Corintios"  ->  lista de ordinales
        # ("Primera", "segunda") + resto ("carta ... a los Corintios")
        ord_re = re.compile(r"^(\w+(?:,\s*\w+)*)\s+y\s+(\w+)\s+(.+)$", re.S)
        out = []
        for i, num in enumerate(nums):
            es = []
            for name in es_names:
                m2 = ord_re.match(name)
                if m2:
                    words = [w.strip() for w in m2.group(1).split(",")]
                    words.append(m2.group(2))
                    rest = m2.group(3)
                    if i < len(words):
                        es.append("%s %s" % (words[i].capitalize(), rest))
                        continue
                # sin ordinales reconocibles: se antepone el numero
                es.append("%s %s" % (num, name))
            # variantes que el leccionario usa: "1 Corintios", "2 Pedro"...
            es.append("%s %s" % (num, stem))
            out.append({"sigla": "%s %s" % (num, stem), "siglas_alt": [],
                        "es": es, "vulgata": vulgs[i]})
        return out

    return [{"sigla": sigla.strip(), "siglas_alt": [],
             "es": es_names, "vulgata": vulgs[0]}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", default=DOCX,
                    help="ruta al Siglas.docx (usa una copia si Word lo tiene "
                         "abierto y bloqueado)")
    args = ap.parse_args()
    try:
        rows = read_table(args.docx)
    except PermissionError:
        raise SystemExit(
            "No se puede leer %s (bloqueado: seguramente abierto en Word). "
            "Cierralo, o pasa una copia con --docx RUTA_DE_LA_COPIA" % args.docx)
    books = []
    for cells in rows:
        if len(cells) < 3:
            continue
        sigla = " ".join(cells[0]).strip()
        es_names = cells[1]
        vulg = " ".join(cells[2]).strip()
        if not sigla or norm(sigla).startswith("abreviaci"):
            continue
        books += split_row(sigla, es_names, vulg)

    for b in books:
        b["match"] = sorted({norm(n) for n in b["es"]}, key=len, reverse=True)

    # --- validacion contra el corpus ---
    vpath = os.path.join(DATA, "vulgata.json")
    problems = []
    if os.path.exists(vpath):
        corpus = json.load(open(vpath, encoding="utf-8"))
        for b in books:
            if b["vulgata"] not in corpus:
                problems.append("%-8s -> '%s' NO existe en vulgata.json"
                                % (b["sigla"], b["vulgata"]))
    else:
        problems.append("data/vulgata.json no existe todavia; sin validar")

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "books.json"), "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=1)

    print("%d libros en la tabla" % len(books))
    for b in books:
        print("  %-8s %-28s %s" % (b["sigla"], b["vulgata"], b["es"][0][:52]))
    if problems:
        print("\nPROBLEMAS:")
        for p in problems:
            print("  " + p)
    else:
        print("\nTodos los nombres de la Vulgata existen en el corpus.")


if __name__ == "__main__":
    main()
