"""Fase 4 - Corpus de la Vulgata Clementina a partir de vulgate.pdf.

Parsea el PDF apoyandose en su firma tipografica:

    24.2 pt  -> numero de capitulo
    ~14 pt   -> titulo del libro (se descarta)
    ~6 pt    -> numero de versiculo (volado)
    10 pt    -> texto biblico
    10 pt SC -> encabezado corrido (se descarta)

Maneja la division silabica de LaTeX al final de renglon (praedesti- / natus)
y normaliza ligaduras y dieresis descompuestas.

Salida: data/vulgata.json  ->  {libro: {capitulo: {versiculo: texto}}}
        data/vulgata_qa.txt -> informe de control de calidad

Uso:  python src/4_build_vulgate.py [--keep-french-spacing]
"""

import argparse
import json
import os
import re
import unicodedata

import fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = os.path.join(ROOT, "vulgate.pdf")
DATA = os.path.join(ROOT, "data")

SIZE_CHAPTER = 20.0     # >= esto es numero de capitulo
SIZE_TITLE = 12.0       # >= esto (y < CHAPTER) es titulo de libro
SIZE_VERSE = 7.5        # < esto es numero de versiculo
SC_CABECERA = 0.13      # franja superior donde vive el encabezado corrido

LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}

# Capitulos esperados en la Vulgata Clementina, para el control de calidad.
EXPECTED_CHAPTERS = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numeri": 36,
    "Deuteronomium": 34, "Josue": 24, "Judicum": 21, "Ruth": 4,
    "Regum I": 31, "Regum II": 24, "Regum III": 22, "Regum IV": 25,
    "Paralipomenon I": 29, "Paralipomenon II": 36, "Esdræ": 10,
    "Nehemiæ": 13, "Tobiæ": 14, "Judith": 16, "Esther": 16,
    "Job": 42, "Psalmi": 150, "Proverbia": 31, "Ecclesiastes": 12,
    "Canticum Canticorum": 8, "Sapientia": 19, "Ecclesiasticus": 51,
    "Isaias": 66, "Jeremias": 52, "Lamentationes": 5, "Baruch": 6,
    "Ezechiel": 48, "Daniel": 14, "Osee": 14, "Joel": 3, "Amos": 9,
    "Abdias": 1, "Jonas": 4, "Michæa": 7, "Nahum": 3, "Habacuc": 3,
    "Sophonias": 3, "Aggæus": 2, "Zacharias": 14, "Malachias": 4,
    "Machabæorum I": 16, "Machabæorum II": 15,
    "Matthæus": 28, "Marcus": 16, "Lucas": 24, "Joannes": 21,
    "Actus Apostolorum": 28, "Ad Romanos": 16, "Ad Corinthios I": 16,
    "Ad Corinthios II": 13, "Ad Galatas": 6, "Ad Ephesios": 6,
    "Ad Philippenses": 4, "Ad Colossenses": 4, "Ad Thessalonicenses I": 5,
    "Ad Thessalonicenses II": 3, "Ad Timotheum I": 6, "Ad Timotheum II": 4,
    "Ad Titum": 3, "Ad Philemonem": 1, "Ad Hebræos": 13, "Jacobi": 5,
    "Petri I": 5, "Petri II": 3, "Joannis I": 5, "Joannis II": 1,
    "Joannis III": 1, "Judæ": 1, "Apocalypsis": 22,
}


def clean(text, french_spacing=False):
    for lig, rep in LIGATURES.items():
        text = text.replace(lig, rep)
    # dieresis descompuesta:  Isra¨el -> Israël
    text = re.sub("¨([aeiouAEIOU])",
                  lambda m: unicodedata.normalize("NFC", m.group(1) + "̈"),
                  text)
    text = text.replace(" ", " ")
    if not french_spacing:
        text = re.sub(r"\s+([;:?!])", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def tokenize_page(page):
    """Convierte una pagina en eventos ('chap'|'verse'|'text'|'eol', valor)."""
    height = page.rect.height
    events = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line["spans"]
            if not spans:
                continue
            # Encabezado corrido. Va en versalitas, pero la inicial esta en
            # redonda ('M' + 'atthæus'), asi que no vale con exigir que TODOS
            # los spans sean versalitas: se colaba el nombre del libro en
            # mitad del versiculo que cruzaba el salto de pagina.
            # Lo que lo distingue sin lugar a dudas es la banda en la que cae:
            # ninguna linea de texto corrido del PDF empieza por encima del
            # 14.8 % del alto, y todas las cabeceras estan en el 10.4 %.
            if spans and any("SC" in s["font"] for s in spans) \
                    and line["bbox"][1] < height * SC_CABECERA:
                continue
            if all("SC" in s["font"] for s in spans):
                continue
            joined = "".join(s["text"] for s in spans).strip()
            # numero de pagina al pie
            if joined.isdigit() and line["bbox"][1] > height * 0.88:
                continue

            produced = False
            prev_verse = False        # el token anterior fue cifra de versiculo
            for s in spans:
                size, txt = s["size"], s["text"]
                stripped = txt.strip()
                if size >= SIZE_CHAPTER:
                    if stripped.isdigit():
                        events.append(("chap", int(stripped)))
                        produced = True
                    prev_verse = False
                elif size >= SIZE_TITLE:
                    prev_verse = False          # titulo de libro: se descarta
                elif size < SIZE_VERSE:
                    if not stripped:
                        continue                # espacio fino junto a la cifra
                    if stripped.isdigit():
                        if prev_verse and events and events[-1][0] == "verse":
                            # cifra partida en dos spans (p. ej. 1 + 2 = 12)
                            events[-1] = ("verse", int(str(events[-1][1]) + stripped))
                        else:
                            events.append(("verse", int(stripped)))
                        produced = True
                        prev_verse = True
                else:
                    if txt:
                        events.append(("text", txt))
                        produced = True
                    prev_verse = False
            if produced:
                events.append(("eol", None))
    return events


def parse_book(doc, first_page, last_page):
    """Devuelve {capitulo: {versiculo: texto}} para el rango de paginas dado."""
    chapters, chap, verse, buf = {}, None, None, []

    def flush():
        if chap is None or verse is None:
            return
        text = "".join(buf).strip()
        if not text:
            return
        chapters.setdefault(chap, {})
        if verse in chapters[chap]:
            chapters[chap][verse] += " " + text
        else:
            chapters[chap][verse] = text

    for pno in range(first_page, last_page):
        for kind, value in tokenize_page(doc[pno]):
            if kind == "chap":
                flush()
                buf = []
                chap, verse = value, 1
            elif kind == "verse":
                flush()
                buf = []
                verse = value
            elif kind == "text":
                if chap is None:
                    # libros de un solo capitulo (Abdias, Philemon, 2-3 Jn,
                    # Judas) no llevan numeral de capitulo impreso
                    chap, verse = 1, 1
                buf.append(value)
            elif kind == "eol":
                if buf:
                    tail = "".join(buf)
                    if tail.endswith("-"):
                        buf = [tail[:-1]]       # palabra partida: se une
                    elif not tail.endswith(" "):
                        buf.append(" ")
    flush()
    return chapters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-french-spacing", action="store_true")
    args = ap.parse_args()

    doc = fitz.open(PDF)
    toc = [e for e in doc.get_toc() if e[0] == 1]
    books, qa = {}, []

    for i, (_, name, start) in enumerate(toc):
        if name.startswith("Præfationes"):
            continue
        # ojo: los numeros del indice del PDF ya son indices base 0
        end = toc[i + 1][2] if i + 1 < len(toc) else doc.page_count
        chapters = parse_book(doc, start, end)
        out = {}
        for c in sorted(chapters):
            out[str(c)] = {str(v): clean(chapters[c][v], args.keep_french_spacing)
                           for v in sorted(chapters[c])}
        books[name] = out

        # --- control de calidad ---
        nums = sorted(int(c) for c in out)
        expected = EXPECTED_CHAPTERS.get(name)
        problems = []
        if expected is not None and len(nums) != expected:
            problems.append("capitulos %d, esperados %d" % (len(nums), expected))
        if nums and nums != list(range(1, len(nums) + 1)):
            missing = sorted(set(range(1, max(nums) + 1)) - set(nums))
            problems.append("capitulos no contiguos, faltan %s" % missing[:10])
        for c in out:
            vn = sorted(int(v) for v in out[c])
            if not vn:
                problems.append("cap %s vacio" % c)
            elif vn != list(range(1, len(vn) + 1)):
                gaps = sorted(set(range(1, max(vn) + 1)) - set(vn))
                problems.append("cap %s versiculos con huecos %s" % (c, gaps[:8]))
        nverses = sum(len(v) for v in out.values())
        line = "%-24s cap=%3d vers=%5d %s" % (
            name, len(nums), nverses,
            ("  <-- " + " | ".join(problems)) if problems else "ok")
        qa.append(line)
        print(line)

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "vulgata.json"), "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=0)

    total_v = sum(len(ch) for b in books.values() for ch in b.values())
    summary = "\nTOTAL: %d libros, %d capitulos, %d versiculos" % (
        len(books), sum(len(b) for b in books.values()), total_v)
    print(summary)
    with open(os.path.join(DATA, "vulgata_qa.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(qa) + summary + "\n")


if __name__ == "__main__":
    main()
