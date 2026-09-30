"""Fase 6c - Estructura del indice de cada leccionario.

Lee las cinco paginas indice que ya estan en cache (1000INDICE, 2000indice,
3000indice, 4000indice, 7000indice) y reconstruye su arbol tal como lo publica
el sitio: secciones (tiempos liturgicos, "ANO I / ANO II"), subgrupos
("Natividad del Senor", "Semana I") y entradas con su archivo de destino.

De ahi salen dos cosas:
  * el indice navegable de cada leccionario (8_render.py y 9_docx.py);
  * el orden canonico de las celebraciones en el cuerpo del documento.

Salida: data/toc.json  +  data/toc_qa.txt (cotejo contra lo ya parseado).

Uso:  python src/10_toc.py
"""

import html
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "texto")
DATA = os.path.join(ROOT, "data")

INDEXES = {
    "I": "1000INDICE.html",
    "II": "2000indice.html",
    "III": "3000indice.html",
    "IV": "4000indice.html",
    "V": "500indice.html",
    "VI": "6000indice.html",
    "VII": "7000indice.html",
    "VIII": "8000indice.html",
    "IX": "9000INDICE.html",
}

# clases que el sitio usa como cabecera de seccion y de subgrupo
CLASE_SECCION = {"centrorojo", "centrorojonum", "boldrojo", "subrojo"}
CLASE_GRUPO = {"titulodcha", "boldazul"}
# el leccionario VIII usa la MISMA clase para sus dos niveles de cabecera
# ("I. EN LA CELEBRACION DE..." y, dentro, "1. Para el catecumenado..."): los
# distingue solo la sangria, asi que aqui se decide por la profundidad
CLASE_SEGUN_SANGRIA = {"francesaAzul"}

# El leccionario VII pone sus entradas en <li class="lista">, no en <p>.
# blockquote / ol / ul son la sangria con la que el sitio marca que unas
# entradas dependen de la cabecera anterior (las cuatro misas de Navidad, los
# dias de cada semana): hay que seguirla para no colgar de una cabecera lo que
# ya no le pertenece.
P_RE = re.compile(
    r'(?is)<(/?)(blockquote|ol|ul)\b[^>]*>'
    r'|<(p|li)\b(?:[^>]*?class="?([\w-]+)"?)?[^>]*>(.*?)</\3>')
HREF_RE = re.compile(r'(?i)href="([^"]+)"')
ITEM_RE = re.compile(r'(?i)^(?:texto/)?(\d{3,4}[^#/]*\.html?)(#[^"]*)?$')
BR_RE = re.compile(r"(?i)<br\s*/?>")
SPAN_CLASE_RE = re.compile(r'(?is)^\s*(?:<br\s*/?>|\s)*<span\s+class="?([\w-]+)"?')


def texto_plano(body):
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", body))
    t = t.replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def es_mayusculas(t):
    letras = [c for c in t if c.isalpha()]
    return bool(letras) and all(c == c.upper() for c in letras)


def limpia_label(t):
    """'AÑO I (años impares):' -> 'Año I (años impares)'; quita puntos finales."""
    t = t.strip().rstrip(":.").strip()
    return re.sub(r"\s+", " ", t)


def slug_celebracion(archivo, cel_n):
    """Ancla estable: del archivo (sin extension) + numero de celebracion.

    Word exige nombres de marcador cortos, que empiecen por letra y sin signos.
    """
    base = re.sub(r"\.html?$", "", archivo, flags=re.I)
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9]+", "", base)
    return "c%s_%d" % (base[:34], cel_n)


def parse_indice(ruta):
    # cp1252 coincide con iso-8859-1 salvo en los bytes de control, donde
    # el sitio (exportado desde Word) mete comillas y rayas de dialogo
    raw = open(ruta, "rb").read().decode("cp1252", "replace")
    nodos = []
    titulo = subtitulo = None
    hubo_item = False

    prof = 0
    for cierre, contenedor, _tag, clase, body in P_RE.findall(raw):
        if contenedor:
            prof = max(0, prof - 1) if cierre else prof + 1
            continue
        clase = clase or ""
        if not clase:
            # el leccionario IX pone la cabecera dentro de un <span class=...>
            m = SPAN_CLASE_RE.match(body)
            if m:
                clase = m.group(1)
        txt = texto_plano(body)
        if not txt:
            continue
        hrefs = [h.strip() for h in HREF_RE.findall(body)]
        items = [m for m in (ITEM_RE.match(h) for h in hrefs) if m]

        if items:
            hubo_item = True
            # El leccionario V mete el mes entero en un solo parrafo, una
            # celebracion por linea ("2: <a>San Basilio...</a><br>"). Si se
            # toma solo el primer enlace se pierden diecisiete de dieciocho,
            # asi que el parrafo se parte por sus saltos de linea.
            trozos = BR_RE.split(body) if len(items) > 1 else [body]
            for trozo in trozos:
                t_txt = texto_plano(trozo)
                t_item = None
                for h in HREF_RE.findall(trozo):
                    m = ITEM_RE.match(h.strip())
                    if m:
                        t_item = m
                        break
                if t_item is None or not t_txt:
                    continue
                nodos.append({"nivel": 0, "sangria": prof,
                              "texto": limpia_label(t_txt),
                              "archivo": t_item.group(1),
                              "ancla_web": (t_item.group(2) or "").lstrip("#")})
            continue

        if hrefs:                        # enlaces internos del indice (#LE1...)
            continue
        if clase == "Santo" and titulo is None:
            titulo = txt
            continue
        if not hubo_item and subtitulo is None and \
                clase in CLASE_SECCION | {"tiempo"}:
            subtitulo = txt              # cabecera del leccionario, no seccion
            continue
        if clase in CLASE_SEGUN_SANGRIA:
            nodos.append({"nivel": 1 if prof == 0 else 2, "sangria": prof,
                          "texto": limpia_label(txt)})
        elif clase in CLASE_SECCION or (clase == "pnormal" and es_mayusculas(txt)):
            nodos.append({"nivel": 1, "sangria": prof,
                          "texto": limpia_label(txt)})
        elif clase in CLASE_GRUPO or clase == "pnormal":
            nodos.append({"nivel": 2, "sangria": prof,
                          "texto": limpia_label(txt)})

    # una cabecera sin ninguna entrada debajo (antes de la siguiente cabecera
    # de su mismo nivel o superior) no aporta nada al indice
    limpio = []
    for i, n in enumerate(nodos):
        if n["nivel"] == 0:
            limpio.append(n)
            continue
        vacia = True
        for x in nodos[i + 1:]:
            if x["nivel"] == 0:
                vacia = False
                break
            if x["nivel"] <= n["nivel"]:
                break
        if not vacia:
            limpio.append(n)
    return {"titulo": titulo or "", "subtitulo": subtitulo or "",
            "nodos": limpio}


def load_overrides():
    """Erratas del propio indice del sitio (enlaces que apuntan mal)."""
    ruta = os.path.join(DATA, "toc_overrides.csv")
    if not os.path.exists(ruta):
        return {}
    import csv
    ov = {}
    with open(ruta, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            clave = (row["leccionario"].strip(),
                     limpia_label(row["texto_item"]),
                     row["archivo_indice"].strip())
            ov[clave] = row["archivo_correcto"].strip()
    return ov


def main():
    overrides = load_overrides()
    aplicados = 0
    toc = {}
    for lect, fichero in INDEXES.items():
        ruta = os.path.join(CACHE, fichero)
        if not os.path.exists(ruta):
            print("FALTA el indice %s" % fichero)
            continue
        toc[lect] = parse_indice(ruta)
        for n in toc[lect]["nodos"]:
            if n["nivel"] != 0:
                continue
            nuevo = overrides.get((lect, n["texto"], n["archivo"]))
            if nuevo:
                n["archivo"] = nuevo
                n["corregido"] = True
                aplicados += 1
        n_items = sum(1 for n in toc[lect]["nodos"] if n["nivel"] == 0)
        print("%-4s %-46s %3d entradas, %2d secciones, %3d subgrupos"
              % (lect, toc[lect]["titulo"], n_items,
                 sum(1 for n in toc[lect]["nodos"] if n["nivel"] == 1),
                 sum(1 for n in toc[lect]["nodos"] if n["nivel"] == 2)))

    with open(os.path.join(DATA, "toc.json"), "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False, indent=1)

    # ---- cotejo contra las celebraciones ya parseadas -------------------
    entradas = json.load(open(os.path.join(DATA, "readings_latin.json"),
                              encoding="utf-8"))
    tiene = {}
    for e in entradas:
        tiene.setdefault(e["leccionario"], {}) \
             .setdefault(e["archivo"], set()).add(e.get("cel_n", 0))
    # las memorias que el libro resuelve remitiendo al Comun no dan lecturas,
    # pero si salen en el documento: no son huecos
    remis = {}
    ruta_rem = os.path.join(DATA, "remisiones.json")
    if os.path.exists(ruta_rem):
        for r in json.load(open(ruta_rem, encoding="utf-8")):
            remis.setdefault(r["leccionario"], set()).add(r["archivo"])

    qa = []
    for lect, arbol in toc.items():
        en_toc = []
        for n in arbol["nodos"]:
            if n["nivel"] == 0 and n["archivo"] not in en_toc:
                en_toc.append(n["archivo"])
        con_texto = tiene.get(lect, {})
        con_remision = remis.get(lect, set())
        sin_texto = [a for a in en_toc
                     if a not in con_texto and a not in con_remision]
        sin_indice = [a for a in con_texto if a not in en_toc]
        extra_cel = {a: sorted(v) for a, v in con_texto.items() if len(v) > 1}
        qa.append("Leccionario %s: %d entradas de indice, %d archivos con texto"
                  % (lect, len(en_toc), len(con_texto)))
        qa.append("  en el indice pero sin texto (%d): %s"
                  % (len(sin_texto), ", ".join(sin_texto) or "-"))
        qa.append("  con texto pero fuera del indice (%d): %s"
                  % (len(sin_indice), ", ".join(sin_indice) or "-"))
        qa.append("  resueltos con una remision al Comun (%d): %s"
                  % (len(con_remision),
                     ", ".join(sorted(con_remision)) or "-"))
        qa.append("  archivos con varias celebraciones (%d): %s"
                  % (len(extra_cel),
                     ", ".join("%s%s" % (a, v) for a, v in extra_cel.items())
                     or "-"))
        qa.append("")
    qa.append("erratas del indice corregidas por toc_overrides.csv: %d"
              % aplicados)
    salida = os.path.join(DATA, "toc_qa.txt")
    open(salida, "w", encoding="utf-8").write("\n".join(qa))
    print("\n".join(qa))
    print("-> data/toc.json  ·  %s" % salida)


if __name__ == "__main__":
    main()
