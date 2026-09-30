"""Fase 12 - Los anexos del leccionario.

El sitio publica, detras de los formularios de cada dia, tres cosas que el
parser de celebraciones (`2_parse_readings.py`) no reconoce porque **no tienen
`p.Santo`**: no son el formulario de un dia, son listas.

  1. **Versiculos alternativos para el Aleluya**, una lista numerada por cada
     tiempo liturgico. Citas biblicas: se resuelven al latin como cualquier
     otra lectura.
  2. **Textos comunes para el canto del salmo responsorial**: respuestas
     salmodicas por tiempo y salmos enteros que pueden cantarse en lugar del
     propio del dia. Tambien son citas.
  3. **Indice de textos**: una tabla que dice, para cada pasaje biblico, en que
     celebracion se lee. No es texto que anadir al leccionario, sino su indice
     inverso; se trata aparte (`18_indice_textos.py`).

Lo que las hace parseables no son las clases -el sitio las usa con descuido: el
mismo numero aparece unas veces como `centrorojonum` y otras como `pnormal`-
sino **el ancla**: en las paginas de aleluya, todo parrafo `p.aleluya` es una
cita, y el texto castellano es lo que viene detras hasta el siguiente numero.
En las de textos comunes el ancla es el parrafo que empieza por "Salmo" seguido
de una cifra.

Varias paginas repiten el mismo anexo una vez por ciclo (`1068aleluyaTO`,
`2068aleluyaTO`, `3068aleluyaTO`, `400aleluyaTO`) y **no son identicas**: hay
entradas de mas y erratas sueltas. Se toma la mas completa y las diferencias se
anotan en el informe, como se hizo con los dias comunes en §7.8.

Salida:  data/anexos.json        los anexos, tal cual se leen
         data/anexos_index.json  una fila por cita, en el formato que ya come
                                 5_resolve.py (mismas claves que index_master)
         data/anexos_qa.txt      el informe

Uso:  python src/16_parse_anexos.py
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

# --------------------------------------------------------------------------
# El catalogo de anexos. Explicito a proposito: los nombres de fichero del
# sitio no siguen ninguna regla (701, 7002, 70705, 400...), asi que adivinarlos
# seria mas fragil que escribirlos. Cuando un anexo tiene varias copias -una
# por ciclo- van todas y se queda la mas completa.
# --------------------------------------------------------------------------
CATALOGO = [
    {"id": "aleluya_adviento_1_16", "tipo": "aleluya",
     "titulo": "Versículos alternativos para el Aleluya",
     "ambito": "Ferias de Adviento hasta el 16 de diciembre",
     "seccion": "TIEMPO DE ADVIENTO",
     "archivos": ["701AleluyaAdviento.html"]},
    {"id": "aleluya_adviento_17_24", "tipo": "aleluya",
     "titulo": "Versículos alternativos para el Aleluya",
     "ambito": "Ferias de Adviento del 17 al 24 de diciembre",
     "seccion": "TIEMPO DE ADVIENTO",
     "archivos": ["7002AleluyaAdviento18_24.html"]},
    {"id": "aleluya_navidad_antes_epifania", "tipo": "aleluya",
     "titulo": "Versículos alternativos para el Aleluya",
     "ambito": "Ferias del tiempo de Navidad antes de la Epifanía",
     "seccion": "TIEMPO DE NAVIDAD",
     "archivos": ["7003Aleluya_Navidad_antes de Epifania.html"]},
    {"id": "aleluya_navidad_despues_epifania", "tipo": "aleluya",
     "titulo": "Versículos alternativos para el Aleluya",
     "ambito": "Ferias del tiempo de Navidad después de la Epifanía",
     "seccion": "TIEMPO DE NAVIDAD",
     "archivos": ["7004Aleluya_Navidad_despues de Epifania.html"]},
    {"id": "aclamaciones_cuaresma", "tipo": "aleluya",
     "titulo": "Aclamaciones y versículos antes del Evangelio",
     "ambito": "Tiempo de Cuaresma",
     "seccion": "TIEMPO DE CUARESMA",
     "archivos": ["70705AleluyaCuaresma.html", "1017AclamCU.html",
                  "2019AclamCU.html", "30171AclamCU.html"]},
    {"id": "aleluya_pascua_antes_ascension", "tipo": "aleluya",
     "titulo": "Versículos alternativos para el Aleluya",
     "ambito": "Ferias del tiempo pascual antes de la Ascensión",
     "seccion": "TIEMPO PASCUAL",
     "archivos": ["7006AleluyaPascua_antes_de Ascension.html"]},
    {"id": "aleluya_pascua_despues_ascension", "tipo": "aleluya",
     "titulo": "Versículos alternativos para el Aleluya",
     "ambito": "Ferias del tiempo pascual después de la Ascensión",
     "seccion": "TIEMPO PASCUAL",
     "archivos": ["70707AleluyaPascua_despues_de Ascension.html"]},
    {"id": "aleluya_ordinario", "tipo": "aleluya",
     "titulo": "Versículos alternativos para el Aleluya",
     "ambito": "Domingos y ferias del Tiempo Ordinario",
     "seccion": "TIEMPO ORDINARIO",
     "archivos": ["3068aleluyaTO.html", "1068aleluyaTO.html",
                  "2068aleluyaTO.html", "400aleluyaTO.html"]},
    {"id": "salmos_comunes", "tipo": "salmos",
     "titulo": "Textos comunes para el canto del salmo responsorial",
     "ambito": "Domingos y fiestas",
     "seccion": "TEXTOS COMUNES",
     "archivos": ["2069TEXTCOM.html", "1069TEXTCOM.html", "3069TEXTCOM.html"]},
    {"id": "salmos_comunes_ferias", "tipo": "salmos",
     "titulo": "Textos comunes para el canto del salmo responsorial",
     "ambito": "Ferias del Tiempo Ordinario",
     "seccion": "TEXTOS COMUNES",
     "archivos": ["4409TEXTCOM.html"]},
]

# El 7124Textos_comunes.html si lleva <p class="Santo">, asi que el parser de
# celebraciones ya lo recogio y sale en los documentos como una celebracion
# mas (la seccion APENDICE de calendario.json). No se toca aqui.
YA_EN_EL_LECCIONARIO = {"7124Textos_comunes.html"}

SECCION_ORDEN = ["TIEMPO DE ADVIENTO", "TIEMPO DE NAVIDAD",
                 "TIEMPO DE CUARESMA", "TIEMPO PASCUAL", "TIEMPO ORDINARIO",
                 "TEXTOS COMUNES"]


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


# --------------------------------------------------------------------------
# lectura del HTML
# --------------------------------------------------------------------------
def parrafos(archivo):
    """[(clase, texto)] de una pagina, en orden y ya sin marcado."""
    ruta = os.path.join(CACHE, archivo)
    if not os.path.exists(ruta):
        return None
    # El sitio declara iso-8859-1, pero 5 paginas exportadas desde Word traen
    # bytes cp1252 (0x97 = raya de dialogo). En iso-8859-1 esos bytes son
    # controles invisibles, asi que la raya desaparecia sin avisar. cp1252 es
    # identica a iso-8859-1 salvo en ese tramo, de modo que leerlas asi no
    # cambia ninguna de las otras 752.
    h = open(ruta, "rb").read().decode("cp1252", errors="replace")
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    h = re.sub(r"(?i)<br\s*/?>", " ", h)
    salida = []
    # el atributo puede ir con comillas o sin ellas (paginas exportadas de Word)
    for m in re.finditer(r"(?is)<p([^>]*)>(.*?)</p>", h):
        cls = re.search(r"class\s*=\s*[\"']?([A-Za-z0-9_]+)", m.group(1))
        t = re.sub(r"(?s)<[^>]+>", "", m.group(2))
        t = _html.unescape(t).replace("\xa0", " ")
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            salida.append((cls.group(1).lower() if cls else "", t))
    return salida


NUM_RE = re.compile(r"^\s*(\d{1,3})\s*[.\-)]*\s*$")
NUM_TEXTO_RE = re.compile(r"^\s*(\d{1,3})\s*[.\-)]+\s*(\S.*)$")
SALMO_RE = re.compile(r"^\s*salmo\s+\d", re.I)
ALELUYA_RE = re.compile(r"^\s*aleluya\b", re.I)
# cualquiera de estas clases puede llevar un encabezamiento; el sitio no
# distingue el titulo de la pagina de los rotulos de dentro
CLASES_TITULO = {"encabazul", "tiempo", "tabinacel", "titulo", "santo",
                 "centrorojo"}
PROSA = ("estos textos pueden usarse", "el salmo se toma", "sin embargo",
         "ordenacion general", "aclamaciones", "versiculos")


def parsea_aleluyas(ps, archivo):
    """Las paginas de versiculos del Aleluya y de aclamaciones.

    Dos clases de entrada, y las dos llevan numero:

    * con **cita** — el ancla es `p.aleluya`, o un parrafo que empiece por
      "Aleluya"; el castellano es lo que viene detras.
    * **sin cita** — las ocho aclamaciones de Cuaresma ("Gloria y alabanza a
      ti, Cristo") y las siete antifonas «O» del 17 al 24 de diciembre. No son
      Escritura, asi que su latin no sale de la Vulgata sino de la tabla fija
      `data/anexos_latin_fijo.csv`.

    Lo que no se puede usar aqui son las clases CSS: el mismo numero aparece
    como `centrorojonum`, como `centrorojo` y como `pnormal` segun la pagina.
    Manda la **forma del parrafo**: un numero suelto es un numero, venga con la
    clase que venga.
    """
    titulos, entradas = [], []
    seccion = ""
    n_pendiente = None
    actual = None
    ultimo_n = 0

    def abre(n, cita):
        nonlocal ultimo_n
        nuevo = {"n": n or str(len(entradas) + 1), "raw_cita": cita,
                 "es": [], "seccion": seccion}
        entradas.append(nuevo)
        ultimo_n = int(nuevo["n"]) if str(nuevo["n"]).isdigit() else ultimo_n
        return nuevo

    for cls, t in ps:
        m = NUM_RE.match(t)
        if m:                                   # un numero suelto, sea cual sea
            n_pendiente = m.group(1)            # su clase
            actual = None
            continue
        if cls in CLASES_TITULO:
            if not entradas:
                titulos.append(t)
            seccion = t
            actual = None
            ultimo_n = 0            # cada seccion vuelve a numerar desde 1
            continue
        if cls == "aleluya" or ALELUYA_RE.match(t):
            actual = abre(n_pendiente, t)
            n_pendiente = None
            continue
        # "1.- Gloria y alabanza a ti, Cristo." abre entrada aunque haya una
        # abierta: son ocho parrafos seguidos, cada uno con su numero. Se exige
        # que el numero continue la serie para no partir un versiculo que
        # empiece por una cifra.
        m = NUM_TEXTO_RE.match(t)
        if (m and int(m.group(1)) == ultimo_n + 1
                and not any(p in norm(t) for p in PROSA)):
            actual = abre(m.group(1), None)
            actual["es"].append(m.group(2).strip())
            n_pendiente = None
            continue
        if actual is not None:
            actual["es"].append(t)
            continue
        if n_pendiente is not None:             # numero y luego texto: sin cita
            actual = abre(n_pendiente, None)
            actual["es"].append(t)
            n_pendiente = None
            continue
        if not entradas:
            titulos.append(t)                   # prosa introductoria
    for e in entradas:
        e["es"] = " ".join(e["es"]).strip()
    return titulos, entradas, []


def parsea_salmos(ps, archivo):
    """Las paginas de textos comunes: respuestas por tiempo y salmos enteros.

    El ancla es el parrafo que empieza por "Salmo" y una cifra. El rotulo del
    tiempo es el ultimo `p.obien` que no sea un "O bien:".
    """
    titulos, respuestas, salmos = [], [], []
    seccion = ""
    tiempo = ""
    actual = None
    for cls, t in ps:
        if cls in CLASES_TITULO:
            if not salmos:
                titulos.append(t)
            seccion = t
            actual = None
            continue
        if cls == "enlaces" or cls == "obiendcha":
            continue
        es_obien = re.match(r"^\s*o\s+bien\b", t, re.I)
        if cls in ("obien", "obien2") and not es_obien:
            # "Tiempo de Adviento:" / "a) con un salmo de alabanza:"
            tiempo = t.rstrip(":").strip()
            resto = ""
            if ":" in t and not t.rstrip().endswith(":"):
                tiempo, resto = t.split(":", 1)
                tiempo = tiempo.strip()
                resto = resto.strip()
            actual = None
            if resto:
                respuestas.append({"tiempo": tiempo, "es": resto})
            continue
        if SALMO_RE.match(t):
            actual = {"tiempo": tiempo, "raw_cita": t, "antifona_es": "",
                      "es": [], "seccion": seccion}
            salmos.append(actual)
            continue
        if cls == "salmosub":
            texto = re.sub(r"^\s*R\.?\s*", "", t).strip()
            if actual is not None:
                actual["antifona_es"] = (
                    (actual["antifona_es"] + " / " + texto).strip(" /")
                    if actual["antifona_es"] else texto)
            else:
                respuestas.append({"tiempo": tiempo, "es": texto})
            continue
        if cls in ("salmo",) and actual is not None:
            actual["es"].append(t)
            continue
        if cls in ("pnormal", "cita", "") and actual is not None:
            actual["es"].append(t)
            continue
        if cls in ("pnormal", "") and "respuesta" in norm(seccion):
            respuestas.append({"tiempo": tiempo, "es": t})
    for s in salmos:
        s["es"] = " ".join(s["es"]).strip()
    return titulos, respuestas, salmos


# --------------------------------------------------------------------------
def elige_copia(anexo, normaliza, inf):
    """De las copias de un anexo, la mejor; el resto queda anotado.

    "Mejor" no es "la que trae mas parrafos", que es facil de contar y no dice
    nada: es **la que mas citas normaliza**. La diferencia no es teorica. Las
    cuatro copias de las aclamaciones de Cuaresma traen las mismas 16 citas,
    pero tres de ellas escriben "Am 5," sin el versiculo y la del leccionario
    VII escribe "Am 5, 14"; contando parrafos ganaba una copia con la errata.
    """
    leidas = []
    for archivo in anexo["archivos"]:
        ps = parrafos(archivo)
        if ps is None:
            inf.append("   %-46s NO ESTA EN CACHE" % archivo)
            continue
        if anexo["tipo"] == "aleluya":
            titulos, entradas, _ = parsea_aleluyas(ps, archivo)
            resp = []
        else:
            titulos, resp, entradas = parsea_salmos(ps, archivo)
        con_cita = [e for e in entradas if e.get("raw_cita")]
        ok = sum(1 for e in con_cita
                 if normaliza(archivo, e["raw_cita"], anexo["tipo"])["ok"])
        leidas.append({"archivo": archivo, "titulos": titulos,
                       "entradas": entradas, "respuestas": resp,
                       "ok": ok, "citas": len(con_cita)})
    if not leidas:
        return None
    leidas.sort(key=lambda x: (x["ok"], len(x["entradas"]), -len(x["archivo"])),
                reverse=True)
    if len(leidas) > 1:
        cuentas = ", ".join("%s %d/%d" % (x["archivo"], x["ok"], x["citas"])
                            for x in leidas)
        inf.append("   %-32s %d copias, se toma %s  (citas que normalizan: %s)"
                   % (anexo["id"], len(leidas), leidas[0]["archivo"], cuentas))
    return leidas[0]


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    n3 = modulo("3_normalize_refs")
    books = json.load(open(os.path.join(DATA, "books.json"), encoding="utf-8"))
    aliases = n3.build_aliases(books)
    psalm_book = next(b for b in books if b["vulgata"] == "Psalmi")
    corpus = json.load(open(os.path.join(DATA, "vulgata.json"),
                            encoding="utf-8"))
    un_capitulo = {n for n, ch in corpus.items() if len(ch) == 1}

    # las mismas erratas del sitio que corrige 3_normalize_refs.py; el fichero
    # es el mismo y se edita igual
    erratas = {}
    ruta_ov = os.path.join(DATA, n3.OVERRIDES_FILE)
    if os.path.exists(ruta_ov):
        import csv
        with open(ruta_ov, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                erratas[(row["archivo"].strip(),
                         row["cita_cruda"].strip())] = \
                    row["cita_correcta"].strip()
    usadas = set()

    def normaliza(archivo, raw, tipo):
        cruda = erratas.get((archivo, raw.strip()))
        if cruda:
            usadas.add((archivo, raw.strip()))
            raw = cruda
        rtype = "aleluya" if tipo == "aleluya" else "salmo"
        ref = n3.normalize(raw, aliases, rtype, psalm_book, un_capitulo)
        ref["usada"] = raw
        return ref

    inf = ["LOS ANEXOS DEL LECCIONARIO", ""]
    inf.append("copias del mismo anexo:")

    anexos, filas, fallos, faltan_paginas, fijos = [], [], [], [], []
    for pos, cat in enumerate(CATALOGO):
        cat = dict(cat, orden_cat=pos)
        elegida = elige_copia(cat, normaliza, inf)
        if elegida is None:
            faltan_paginas.append(cat)
            anexos.append(dict(cat, archivo=None, entradas=[],
                               respuestas=[], ausente=True))
            continue
        archivo = elegida["archivo"]
        entradas = elegida["entradas"]
        salida = dict(cat)
        salida.update({"archivo": archivo,
                       "titulos_pagina": elegida["titulos"],
                       "respuestas": elegida["respuestas"],
                       "ausente": False})
        limpias = []
        for i, e in enumerate(entradas, 1):
            if not e.get("raw_cita"):
                # aclamacion o antifona «O»: no es Escritura, su latin sale de
                # la tabla fija
                limpias.append({"n": e.get("n", str(i)), "orden": i,
                                "raw_cita": "", "canonica": "",
                                "es": e.get("es", ""),
                                "tiempo": e.get("tiempo", ""),
                                "antifona_es": e.get("antifona_es", ""),
                                "seccion": e.get("seccion", ""),
                                "sin_cita": True, "ok": False})
                fijos.append((cat["id"], e.get("n", str(i)), e.get("es", "")))
                continue
            rtype = "aleluya" if cat["tipo"] == "aleluya" else "salmo"
            ref = normaliza(archivo, e["raw_cita"], cat["tipo"])
            fila = {
                "leccionario": "ANEXO", "ciclo": "",
                "celebracion": "%s · %s" % (cat["titulo"], cat["ambito"]),
                "archivo": archivo, "cel_n": 0, "orden": i,
                "tipo": "aleluya" if rtype == "aleluya" else "salmo responsorial",
                "variante": "", "cita_cruda": e["raw_cita"],
                "sigla": ref.get("sigla", ""), "libro_es": ref.get("es", ""),
                "libro_vulgata": ref.get("vulgata", ""),
                "cita_normalizada": ref.get("canonica", ""),
                "aprox_cf": "si" if ref.get("aprox") else "",
                "antifona_ref": ref.get("resp") or "",
                "resumen": "", "antifona": e.get("antifona_es", ""),
                "ok": "si" if ref["ok"] else "NO",
                "motivo": "" if ref["ok"] else ref["motivo"],
                "_anexo": cat["id"], "_n": e.get("n", str(i)),
                "_es": e.get("es", ""), "_tiempo": e.get("tiempo", ""),
                "_seccion_pagina": e.get("seccion", ""),
            }
            fila["_segmentos"] = ref.get("segmentos")
            fila["libros"] = ref.get("libros") or (
                [ref["vulgata"]] if ref.get("vulgata") else [])
            filas.append(fila)
            limpias.append({"n": fila["_n"], "orden": i,
                            "raw_cita": e["raw_cita"],
                            "canonica": fila["cita_normalizada"],
                            "es": fila["_es"], "tiempo": fila["_tiempo"],
                            "antifona_es": fila["antifona"],
                            "seccion": fila["_seccion_pagina"],
                            "sin_cita": False, "ok": ref["ok"]})
            if not ref["ok"] and not ref.get("benigno"):
                fallos.append("%-22s %-16s %-60s -> %s"
                              % (cat["id"], fila["tipo"],
                                 e["raw_cita"][:60], ref["motivo"]))
        salida["entradas"] = limpias
        anexos.append(salida)

    # el orden es el del catalogo, que es el del ano liturgico; ordenar por el
    # id daria "17_24" antes que "1_16", que es lo que hace el alfabeto
    orden = {s: i for i, s in enumerate(SECCION_ORDEN)}
    anexos.sort(key=lambda a: (orden.get(a["seccion"], 99), a["orden_cat"]))

    with open(os.path.join(DATA, "anexos.json"), "w", encoding="utf-8") as f:
        json.dump({"anexos": anexos}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "anexos_index.json"), "w",
              encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=1)

    ok = sum(1 for r in filas if r["ok"] == "si")
    benignas = sum(1 for r in filas if r["motivo"] == "sin cita biblica")
    n_resp = sum(len(a["respuestas"]) for a in anexos)
    inf.append("")
    inf.append("anexos del catalogo          : %d" % len(CATALOGO))
    inf.append("anexos sin su pagina         : %d" % len(faltan_paginas))
    for cat in faltan_paginas:
        inf.append("   %-34s %s" % (cat["id"], cat["archivos"][0]))
    inf.append("citas encontradas            : %d" % len(filas))
    inf.append("citas normalizadas           : %d (%.1f%%)"
               % (ok, 100.0 * ok / len(filas) if filas else 0))
    inf.append("sin cita biblica (benigno)   : %d" % benignas)
    inf.append("FALLOS                       : %d" % len(fallos))
    for f_ in fallos:
        inf.append("   " + f_)
    inf.append("erratas del sitio corregidas : %d (citation_overrides.csv)"
               % len(usadas))
    for a, c in sorted(usadas):
        inf.append("   %-46s %s" % (a, c[:50]))
    inf.append("textos que no son Escritura  : %d (latin de "
               "anexos_latin_fijo.csv)" % len(fijos))
    inf.append("respuestas salmodicas        : %d (solo castellano: son "
               "antifonas sin cita)" % n_resp)
    inf.append("")
    inf.append("por anexo:")
    for a in anexos:
        con = sum(1 for e in a["entradas"] if not e.get("sin_cita"))
        sin = len(a["entradas"]) - con
        inf.append("   %-34s %-46s %3d citas %2d sin cita%s"
                   % (a["id"], a["archivo"] or "(sin pagina)", con, sin,
                      "   AUSENTE" if a["ausente"] else ""))

    with open(os.path.join(DATA, "anexos_qa.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(inf) + "\n")
    print("\n".join(inf))


if __name__ == "__main__":
    main()
