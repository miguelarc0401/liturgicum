"""Fase 13 - El indice de textos: el leccionario leido al reves.

El tercer anexo del sitio es una tabla que, para cada pasaje biblico, dice en
que celebracion se lee. Es el indice inverso del leccionario, y responde a la
pregunta que un indice de celebraciones no puede responder: *donde se lee
Isaias 2, 1-5*.

Se construye **de nuestros propios datos**, no de la tabla del sitio, por dos
razones. La primera es cobertura: la tabla existe en cuatro de los cinco
leccionarios; `index_master.json` cubre las 3290 lecturas y esta auditado. La
segunda es que asi la tabla del sitio queda libre para lo que de verdad vale:
**ser un testigo independiente**.

Porque eso es lo interesante. La tabla y las paginas de dia son dos listados
distintos del mismo libro, escritos por separado, asi que cotejar una contra
otra encuentra erratas que ninguna de las dos declara. Es el tercer verificador
que §8.8 echaba en falta, con el limite obvio de que los dos salen de la misma
casa.

Salida:  data/indice_textos.json   libro -> pasajes -> donde se leen
         data/indice_textos_qa.txt el cotejo contra la tabla del sitio

Uso:  python src/17_indice_textos.py
"""

import html as _html
import importlib.util
import io
import json
import os
import re
import sys
import unicodedata
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, "cache", "texto")

# Las tablas que publica el sitio. El leccionario III no tiene la suya.
TABLAS = OrderedDict([
    ("I", "1070INDTEXT.html"),
    ("II", "2070INDITEXT.html"),
    ("IV", "4410INDITEXT.html"),
    ("VII", "7000INDITEXT.html"),
])


def modulo(nombre):
    spec = importlib.util.spec_from_file_location(
        "m" + re.sub(r"\W", "", nombre), os.path.join(ROOT, "src",
                                                      nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def limpio(c):
    t = re.sub(r"(?s)<[^>]+>", " ", c)
    t = re.sub(r"\s+", " ", _html.unescape(t).replace("\xa0", " ")).strip()
    # La tabla escribe el salto de capitulo con dos guiones ("Exodo 14,
    # 15--15, 1") donde el formulario usa raya. Sin esto, "14, 15--15, 1" se
    # lee como si acabara en el versiculo 1 del capitulo 14, y las 30 lecturas
    # que cruzan de capitulo salian todas como discrepancia.
    return re.sub(r"\s*--+\s*", "—", t)


def aliases_cortos(n3, books, aliases):
    """Los nombres cortos que usa la tabla y no usa nunca un formulario.

    El formulario escribe "Lectura de la carta del apóstol san Pablo a los
    Romanos"; la tabla escribe "Romanos". El alias se anade **solo si la
    ultima palabra del nombre identifica un unico libro**: "reyes" vale para
    cuatro, asi que queda fuera y su cita se declara no entendida en vez de
    adjudicarsela a uno al azar.

    Se hace aqui y no en 3_normalize_refs.py a proposito: aflojar el
    emparejamiento del leccionario para que le sirva a una tabla es cambiar lo
    que ya esta comprobado por comodidad.
    """
    ya = {a for a, _ in aliases}
    ultimas = {}
    for b in books:
        for n in b["es"]:
            palabras = n3.fold(n).strip().split()
            if palabras:
                ultimas.setdefault(palabras[-1], set()).add(b["vulgata"])
    nuevos = []
    for palabra, libros in ultimas.items():
        if len(libros) != 1 or palabra in ya or len(palabra) < 4:
            continue
        libro = next(b for b in books if b["vulgata"] == next(iter(libros)))
        nuevos.append((palabra, libro))
    salida = list(aliases) + nuevos
    salida.sort(key=lambda x: -len(x[0]))
    return salida, sorted(a for a, _ in nuevos)


def lee_tabla(archivo):
    """[(cita_cruda, archivo_destino, ancla, resumen)] de una tabla del sitio."""
    ruta = os.path.join(CACHE, archivo)
    if not os.path.exists(ruta):
        return None
    h = open(ruta, "rb").read().decode("cp1252", errors="replace")
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    filas = []
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", h):
        celdas = re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)
        if not celdas:
            continue
        cita = limpio(celdas[0])
        resumen = limpio(celdas[1]) if len(celdas) > 1 else ""
        m = re.search(r'href\s*=\s*"([^"#]+)(?:#([^"]*))?"', celdas[0], re.I)
        if not cita:
            continue
        if not m:                 # fila de cabecera: el nombre del libro
            filas.append((cita, None, None, resumen))
            continue
        filas.append((cita, m.group(1), m.group(2) or "", resumen))
    return filas


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    n3 = modulo("3_normalize_refs")
    books = json.load(open(os.path.join(DATA, "books.json"), encoding="utf-8"))
    aliases = n3.build_aliases(books)
    aliases_tabla, cortos = aliases_cortos(n3, books, aliases)
    psalm_book = next(b for b in books if b["vulgata"] == "Psalmi")
    corpus = json.load(open(os.path.join(DATA, "vulgata.json"),
                            encoding="utf-8"))
    un_capitulo = {n for n, ch in corpus.items() if len(ch) == 1}
    # books.json va por orden alfabetico de sigla espanola, que es el de
    # Siglas.docx; un indice de textos se lee en orden canonico, y ese ya lo
    # tenemos: el de los marcadores del PDF de la Vulgata.
    orden_libro = {n: i for i, n in enumerate(corpus)}
    nombre_es = {b["vulgata"]: b["es"][0] for b in books}
    sigla_de = {b["vulgata"]: b["sigla"] for b in books}

    filas = json.load(open(os.path.join(DATA, "index_master.json"),
                           encoding="utf-8"))
    cal = json.load(open(os.path.join(DATA, "calendario.json"),
                         encoding="utf-8"))
    # (leccionario, archivo, cel_n) -> el dia del calendario, para que el
    # indice pueda enlazar al sitio exacto del documento
    slug_de, dia_de = {}, {}
    for sec in cal["secciones"]:
        for g in sec["grupos"]:
            for d in g["dias"]:
                for b in d["bloques"]:
                    slug_de[tuple(b["clave"])] = d["slug"]
                    dia_de[tuple(b["clave"])] = d["titulo"]

    # ---- nuestro indice inverso ----------------------------------------
    porlibro = {}
    sin_cita = 0
    for r in filas:
        if r["ok"] != "si" or not r.get("libro_vulgata"):
            sin_cita += 1
            continue
        clave = (r["leccionario"], r["archivo"], r.get("cel_n", 0))
        segs = r.get("_segmentos") or []
        cap = segs[0]["cap"] if segs else 0
        desde = segs[0].get("desde") or 0
        entrada = porlibro.setdefault(r["libro_vulgata"], {}) \
                          .setdefault(r["cita_normalizada"],
                                      {"cap": cap, "desde": desde,
                                       "sigla": r.get("sigla", ""),
                                       "donde": []})
        # Un mismo pasaje en el mismo dia de los tres ciclos es **un** lugar,
        # no tres: la Vigilia pascual lee Gn 1 en A, B y C, y repetirla tres
        # veces en el indice solo estorba. Se junta por dia y se anotan los
        # ciclos.
        # Una pagina puede llevar dentro mas de una celebracion (la forma
        # breve del evangelio, los ciclos de Cuaresma); el calendario coloca
        # la principal. Si la clave exacta no esta, vale la de su pagina: es
        # el mismo dia, y asi el indice no lo nombra dos veces, una enlazada
        # y otra no.
        clave_pag = (r["leccionario"], r["archivo"], 0)
        dia = dia_de.get(clave) or dia_de.get(clave_pag) or r["celebracion"]
        slug = slug_de.get(clave) or slug_de.get(clave_pag) or ""
        donde = next((d for d in entrada["donde"]
                      if d["celebracion"] == dia and d["slug"] == slug), None)
        if donde is None:
            donde = {"celebracion": dia, "slug": slug, "ciclos": [],
                     "tipo": r["tipo"]}
            entrada["donde"].append(donde)
        c = (r["ciclo"] or "").strip()
        if c and c not in donde["ciclos"]:
            donde["ciclos"].append(c)

    salida = []
    n_pasajes = n_donde = 0
    for libro in sorted(porlibro, key=lambda b: orden_libro.get(b, 999)):
        pasajes = sorted(porlibro[libro].items(),
                         key=lambda kv: (kv[1]["cap"], kv[1]["desde"], kv[0]))
        salida.append({"libro": libro, "es": nombre_es.get(libro, libro),
                       "sigla": sigla_de.get(libro, ""),
                       "pasajes": [dict(v, cita=k) for k, v in pasajes]})
        n_pasajes += len(pasajes)
        n_donde += sum(len(v["donde"]) for _, v in pasajes)

    with open(os.path.join(DATA, "indice_textos.json"), "w",
              encoding="utf-8") as f:
        json.dump({"libros": salida}, f, ensure_ascii=False, indent=1)

    # ---- cotejo contra las tablas del sitio -----------------------------
    inf = ["EL INDICE DE TEXTOS", "",
           "construido de data/index_master.json:",
           "   libros   : %d" % len(salida),
           "   pasajes  : %d" % n_pasajes,
           "   lugares  : %d" % n_donde,
           "   lecturas sin cita biblica (no entran): %d" % sin_cita,
           "",
           "COTEJO contra las tablas del propio sitio (testigo independiente):",
           "   alias cortos anadidos para leer la tabla (%d): %s"
           % (len(cortos), ", ".join(cortos)),
           ""]

    nuestro = {}
    for r in filas:
        if r["ok"] == "si":
            nuestro.setdefault(r["archivo"], set()).add(r["cita_normalizada"])

    tot = coinciden = sin_pagina = no_entendidas = 0
    discrepan = []
    for lect, archivo in TABLAS.items():
        tabla = lee_tabla(archivo)
        if tabla is None:
            inf.append("   L%-4s %-24s NO ESTA EN CACHE" % (lect, archivo))
            continue
        n_lect = n_ok = 0
        for cita, destino, ancla, _ in tabla:
            if not destino:
                continue
            n_lect += 1
            tot += 1
            ref = n3.normalize(cita.rstrip(":").strip(), aliases_tabla, None,
                               psalm_book, un_capitulo)
            if not ref["ok"]:
                no_entendidas += 1
                continue
            if destino not in nuestro:
                sin_pagina += 1
                continue
            if ref["canonica"] in nuestro[destino]:
                coinciden += 1
                n_ok += 1
            else:
                discrepan.append((lect, destino, cita, ref["canonica"],
                                  sorted(nuestro[destino])))
        inf.append("   L%-4s %-24s %4d citas, %4d casan (%.1f%%)"
                   % (lect, archivo, n_lect, n_ok,
                      100.0 * n_ok / n_lect if n_lect else 0))

    inf.append("")
    inf.append("   citas de las tablas          : %d" % tot)
    inf.append("   casan con nuestro indice     : %d (%.1f%%)"
               % (coinciden, 100.0 * coinciden / tot if tot else 0))
    inf.append("   la cita de la tabla no se entiende : %d" % no_entendidas)
    inf.append("   apuntan a una pagina que no tenemos: %d" % sin_pagina)
    inf.append("   DISCREPAN                    : %d" % len(discrepan))
    inf.append("")
    if discrepan:
        inf.append("las discrepancias, una a una (lo que dice la tabla -> lo "
                   "que dice la pagina):")
        for lect, destino, cruda, canon, tiene in discrepan:
            inf.append("   L%-4s %-26s %-26s -> %s"
                       % (lect, destino, canon, ", ".join(tiene)[:70]))

    with open(os.path.join(DATA, "indice_textos_qa.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(inf) + "\n")
    print("\n".join(inf[:22]))
    print("-> data/indice_textos.json  ·  data/indice_textos_qa.txt")


if __name__ == "__main__":
    main()
