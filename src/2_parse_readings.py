"""Fase 2 - De las paginas HTML en cache a readings.json.

Recorre el cuerpo de cada pagina en orden y monta una maquina de estados sobre
las clases CSS del sitio:

    p.Santo       nombre de la celebracion (abre una celebracion nueva)
    p.tiempo      ciclo o ano ("Ciclo A", "Anos impares", "Ciclos A, B y C")
    p.centrorojo  cabecera de seccion: PRIMERA LECTURA / EVANGELIO / ...
    p.resumen     frase resumen, se aplica a la cita siguiente
    p.cita        LA CITA (o el salmo responsorial, que la lleva dentro)
    p.aleluya     cita del versiculo aleluyatico
    p.obien       marca que la cita siguiente es alternativa o forma breve
    p.salmo       primer parrafo con "R." = antifona del salmo

Salida: data/readings.json  +  data/parse_warnings.txt

Uso:  python src/2_parse_readings.py
"""

import html
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "texto")
DATA = os.path.join(ROOT, "data")

LECT_NAME = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V",
             "6": "VI", "7": "VII", "8": "VIII", "9": "IX"}

SECTION_RE = re.compile(
    r"^(primera|segunda|tercera|cuarta|quinta|sexta|septima|octava)\s+lectura$")

ORDINAL_N = {"primera": 1, "segunda": 2, "tercera": 3, "cuarta": 4,
             "quinta": 5, "sexta": 6, "septima": 7, "octava": 8}

# En los Comunes de los santos y en las misas rituales, votivas y por diversas
# necesidades el leccionario no dice "primera lectura": ofrece un repertorio
# agrupado por Testamento y numerado, y quien celebra elige. Sin estas
# cabeceras, las dos mil citas de los leccionarios VI y VIII quedan sin tipo.
SECCION_ALIAS = {
    "lecturas del antiguo testamento": "lectura_at",
    "lectura del antiguo testamento": "lectura_at",
    "primeras lecturas del antiguo testamento": "lectura_at",
    "primeras lecturas del antiguo testamento fuera del tiempo pascual":
        "lectura_at",
    "lecturas del nuevo testamento": "lectura_nt",
    "lectura del nuevo testamento": "lectura_nt",
    "primeras lecturas del nuevo testamento": "lectura_nt",
    "primera lectura del nuevo testamento": "lectura_nt",
    "primeras lecturas del nuevo testamento tiempo pascual": "lectura_nt",
    "segundas lecturas del nuevo testamento": "lectura_2",
    "segundas lecturas": "lectura_2",
    "primeras lecturas": "lectura_1",
    "primera": "lectura_1",
    "evangelios": "evangelio",
    "lecturas de la historia de la pasion del senor": "evangelio",
}

# el grado de la celebracion, que en el santoral va justo bajo el nombre
GRADOS = ("solemnidad", "fiesta", "memoria", "memoria libre",
          "memoria obligatoria")

# "1", "2", "3"...: el numero con que el libro ordena las opciones de un
# repertorio. Va delante de su lectura.
NUM_OPCION_RE = re.compile(r"^\d{1,2}$")

# clases que aportan estructura; el resto es cuerpo del texto y se ignora
STRUCT = ("Santo", "fecha", "tiempo", "centrorojo", "centrorojonum",
          "resumen", "cita", "aleluya", "obien", "obien2", "salmo",
          "palabra", "comunenlace")

# p.comunenlace: "Del Comun de pastores". En el leccionario V la mayoria de
# las memorias no tienen lecturas propias, solo esta remision al Comun; sin
# recogerla, esas celebraciones saldrian vacias y sin decir por que.
A_RE = re.compile(r'(?is)<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>')

# La indicacion expresa de lectura propia, que el Ordo lectionum Missae
# promete en su n. 83: «Hae lectiones, quamvis agatur de memoria, dici debent
# loco lectionum pro feriis occurrentium. Quoties de huiusmodi lectionibus
# agitur in memoria, id in hoc Ordine expresse suo loco indicatur.»
#
# La fuente la imprime en un p.obien, entre el grado y el primer rotulo. Son
# diez celebraciones, y son **las mismas diez** que marca el Ordo latino de
# 1981 (cotejado contra cache/olm1981_ocr.txt: «Lectio prior huius memoriae
# est propria», «Evangelium huius memoriae est proprium», «Lectiones huius
# memoriae sunt propriae»). Dos libros distintos que dicen lo mismo es lo que
# convierte esto en dato y no en interpretacion.
#
# Importa porque manda sobre la feria: en una memoria con lectura propia esa
# lectura **sustituye** a la del dia; en una memoria sin ella, lo que se lee
# es la feria y lo que la pagina del santo imprime son sugerencias del Comun
# (IGMR 357: «In memoriis Sanctorum, nisi habeantur propriae, leguntur de
# more lectiones feriae assignatae»).
PROPIAS_RE = re.compile(
    r"^(?:el|la|las|los)\s+"
    r"(primera lectura|segunda lectura|lecturas|lectura|evangelio)"
    r"\s+de\s+est[ae]\s+(?:memoria|fiesta|solemnidad|celebracion)"
    r"\s+(?:es|son)\s+propi[ao]s?\b")

# Que ranura declara propia cada una. "lecturas" en plural son todas.
PROPIAS_RANURA = {"primera lectura": "lectura_1",
                  "segunda lectura": "lectura_2",
                  "lectura": "lectura_1",
                  "evangelio": "evangelio",
                  "lecturas": "*"}

# algunas paginas vienen de Word con el atributo sin comillas (class=Santo):
# si se exige la comilla, la pagina entera pasa inadvertida (4371PTOV28.html)
P_RE = re.compile(r'<p\s+class=(?:"([^"]+)"|([A-Za-z][\w-]*))[^>]*>(.*?)</p>',
                  re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(s):
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = TAG_RE.sub("", s)
    s = html.unescape(s)
    s = s.replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_page(fname, raw):
    # El sitio declara iso-8859-1, pero 5 de las 757 paginas -exportadas desde
    # Word- traen bytes cp1252: 0x97 y 0x96, las rayas de dialogo de "-dice el
    # Senor-". En iso-8859-1 esos bytes son controles invisibles, asi que la
    # raya se perdia sin dar ningun error. cp1252 coincide con iso-8859-1 en
    # todo lo demas, de modo que las otras 752 se leen exactamente igual.
    text = raw.decode("cp1252", errors="replace")
    body = text[text.lower().find("<body"):]
    title = strip_tags(re.search(r"<title>(.*?)</title>", text, re.S | re.I).group(1)) \
        if re.search(r"<title>", text, re.I) else fname

    lect = LECT_NAME.get(fname[0], "?")
    celebrations = []
    warnings = []

    cur = None
    section = None          # tipo de lectura en curso
    pending_summary = None
    pending_alt = None      # None | "alternativa" | "forma_breve"
    pending_fecha = []      # p.fecha a la espera de su p.Santo
    pending_num = None      # numero de opcion dentro de un repertorio
    slot = 0

    def new_celebration(name):
        # cel_n distingue varias celebraciones dentro de una misma pagina
        # (Domingo de Ramos, Pentecostes...): sin el, (archivo, orden) no es
        # una clave unica
        c = {"cel_n": len(celebrations), "id": os.path.splitext(fname)[0],
             "lectionary": lect,
             "celebration": name, "cycle": None, "source_file": fname,
             "title": title, "readings": [], "fecha": None, "grado": None,
             "comunes": [], "propias": [], "propias_txt": None}
        if pending_fecha:
            c["fecha"] = " · ".join(pending_fecha)
            del pending_fecha[:]
        return c

    for cls_q, cls_nq, inner in P_RE.findall(body):
        cls = (cls_q or cls_nq).split()[0]
        if cls not in STRUCT:
            # cuerpo de la lectura: se guarda para poder cotejar despues el
            # latin con el castellano (comprobacion de versificacion)
            if cls in ("pnormal", "versosang", "salmo", "versiculo", "verso",
                       "votnormal", "ninoslector") \
                    and cur is not None and cur["readings"]:
                body_txt = strip_tags(inner)
                if body_txt:
                    cur["readings"][-1].setdefault("texto_es", []).append(body_txt)
            continue
        val = strip_tags(inner)
        n = norm(val)

        if cls == "Santo":
            if not val:
                continue
            if cur is not None and not cur["readings"]:
                # titulo partido en dos lineas ("Jueves santo" / "Misa de la
                # cena del Senor"): es la misma celebracion
                cur["celebration"] += " — " + val
                continue
            cur = new_celebration(val)
            celebrations.append(cur)
            section, slot, pending_summary, pending_alt = None, 0, None, None
            pending_num = None
            continue

        if cls == "fecha":
            if not val:
                continue
            # si la celebracion ya esta abierta y todavia no tiene lecturas, la
            # fecha es suya; si ya las tiene, es de la siguiente
            if cur is not None and not cur["readings"]:
                cur["fecha"] = (cur["fecha"] + " · " + val) if cur["fecha"]                     else val
            else:
                pending_fecha.append(val)
            continue

        if cur is None:
            cur = new_celebration(title)
            celebrations.append(cur)

        if cls == "comunenlace":
            for href, rot in A_RE.findall(inner):
                rot = strip_tags(rot)
                if rot:
                    cur["comunes"].append({
                        "texto": rot,
                        "archivo": href.split("/")[-1].split("#")[0]})
            if not A_RE.search(inner) and val:
                # La Natividad de san Juan Bautista trae el grado en este
                # parrafo y no en el centrorojo de los demas, y sin esto la
                # solemnidad se quedaba sin grado y con un «Comun» llamado
                # «Solemnidad». Es el unico comunenlace del leccionario que
                # no es un enlace, asi que se arregla por lo que dice.
                if n in GRADOS:
                    if cur["grado"] is None:
                        cur["grado"] = val
                else:
                    cur["comunes"].append({"texto": val, "archivo": ""})
            continue

        if cls == "tiempo":
            if val and cur["cycle"] is None:
                cur["cycle"] = val
            continue

        if cls in ("centrorojo", "centrorojonum"):
            m = SECTION_RE.match(n)
            if m:
                section = "lectura_%d" % ORDINAL_N[m.group(1)]
            elif n == "evangelio":
                section = "evangelio"
            elif n in ("epistola", "epistola "):
                section = "epistola"
            elif n.startswith("salmo"):
                section = "salmo"
            elif n in SECCION_ALIAS:
                section = SECCION_ALIAS[n]
            elif NUM_OPCION_RE.match(n):
                pending_num = n
            elif n in GRADOS and cur["grado"] is None:
                cur["grado"] = val
            # cualquier otro centrorojo es un subtitulo narrativo (pasiones)
            continue

        if cls == "resumen":
            pending_summary = val or None
            continue

        if cls in ("obien", "obien2"):
            if n.startswith("o bien"):
                pending_alt = "forma_breve" if "breve" in n else "alternativa"
            else:
                m = PROPIAS_RE.match(n)
                if m:
                    r = PROPIAS_RANURA[m.group(1)]
                    if r not in cur["propias"]:
                        cur["propias"].append(r)
                    cur["propias_txt"] = val
            continue

        if cls == "salmo":
            # antifona: primer parrafo del salmo, que empieza por "R."
            if cur["readings"] and cur["readings"][-1]["type"] == "salmo":
                r = cur["readings"][-1]
                if r.get("response") is None and re.match(r"^R\.?\s", val):
                    r["response"] = re.sub(r"^R\.?\s*", "", val).strip()
                elif val:
                    r.setdefault("texto_es", []).append(val)
            continue

        if cls == "aleluya":
            if n.startswith("versiculo") or not val:
                continue        # "Versiculos alternativos para el Aleluya"
            # la secuencia (Victimae paschali, Veni Sancte Spiritus...) no es
            # una cita biblica
            atype = "secuencia" if n.startswith("secuencia") else "aleluya"
            slot += 1
            cur["readings"].append({
                "slot": slot, "type": atype, "raw_cita": val,
                "summary": None, "response": None, "variant": pending_alt,
                "opcion": pending_num})
            pending_alt, pending_num = None, None
            continue

        if cls == "cita":
            if not val:
                continue
            is_psalm = "salmo responsorial" in n or n.startswith("salmo")
            rtype = "salmo" if is_psalm else section
            if rtype is None:
                # Paginas que ofrecen un repertorio numerado sin decir de que
                # (el sabado santo del leccionario IX, tres casos suletos en
                # III, VII y VIII). La formula que imprime el sitio lo dice:
                # "Lectura del santo evangelio segun..." es un evangelio y lo
                # demas es una lectura. Mejor eso que titular "DESCONOCIDO".
                rtype = "evangelio" if "evangelio" in n else "lectura_1"
                warnings.append("%s: cita sin seccion, deducida por la "
                                "formula como %s: %s"
                                % (fname, rtype, val[:60]))
            slot += 1
            cur["readings"].append({
                "slot": slot, "type": rtype, "raw_cita": val,
                "summary": pending_summary, "response": None,
                "variant": pending_alt, "opcion": pending_num})
            pending_summary, pending_alt, pending_num = None, None, None
            continue

    for c in celebrations:
        if not c["readings"]:
            if c["comunes"]:
                continue        # remite al Comun: es asi en el libro impreso
            warnings.append("%s: celebracion sin lecturas (%s)"
                            % (fname, c["celebration"][:50]))
        elif not any(r["type"] == "evangelio" for r in c["readings"]):
            warnings.append("%s: sin evangelio (%s)"
                            % (fname, c["celebration"][:50]))
    return celebrations, warnings


def main():
    out, warnings = [], []
    # paginas auxiliares que no son celebraciones (indices, listas de
    # aclamaciones del aleluya, textos comunes del salmo)
    skip = ("indice", "indtext", "inditext", "textcom", "aleluya", "aclam")
    files = sorted(f for f in os.listdir(CACHE)
                   if f.lower().endswith((".html", ".htm"))
                   and not any(s in f.lower() for s in skip))
    for fname in files:
        with open(os.path.join(CACHE, fname), "rb") as f:
            raw = f.read()
        cels, warns = parse_page(fname, raw)
        out += cels
        warnings += warns

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "readings.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    # Nueve memorias del santoral no traen lecturas propias: solo remiten al
    # Comun. No dan ninguna fila en el indice maestro, asi que sin este fichero
    # se caerian del documento y esos nueve dias quedarian en blanco.
    remisiones = [{"leccionario": c["lectionary"], "archivo": c["source_file"],
                   "cel_n": c["cel_n"], "celebracion": c["celebration"],
                   "fecha": c["fecha"], "grado": c["grado"],
                   "comunes": c["comunes"]}
                  for c in out if not c["readings"] and c["comunes"]]
    with open(os.path.join(DATA, "remisiones.json"), "w",
              encoding="utf-8") as f:
        json.dump(remisiones, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "parse_warnings.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(warnings))

    nread = sum(len(c["readings"]) for c in out)
    print("%d paginas -> %d celebraciones, %d lecturas" % (len(files), len(out), nread))
    import collections
    tc = collections.Counter(r["type"] for c in out for r in c["readings"])
    for t, n in tc.most_common():
        print("  %-14s %d" % (t, n))
    print("avisos: %d (data/parse_warnings.txt)" % len(warnings))
    print("remisiones al Comun sin lecturas propias: %d" % len(remisiones))
    # La indicacion expresa del n. 83 del Ordo lectionum. Se nombran una a una
    # porque son diez y porque han de seguir siendo las mismas diez: si la
    # fuente cambia de redaccion, aqui se ve en el acto.
    prop = [c for c in out if c["propias"]]
    print("lectura propia declarada por la fuente: %d" % len(prop))
    for c in prop:
        print("  %-11s %-44s %s -> %s"
              % (c["source_file"].replace(".html", ""), c["celebration"][:44],
                 (c["grado"] or "")[:13], ",".join(c["propias"])))


if __name__ == "__main__":
    main()
