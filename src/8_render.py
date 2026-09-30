"""Fase 6 - Composicion del leccionario latino.  ENTREGABLE B.

Monta el leccionario en Markdown a partir de data/readings_latin.json, con la
estructura liturgica de siempre: tiempo liturgico, celebracion, formula de
introduccion propia de cada libro, texto latino y formula de cierre.

El esqueleto (tiempos, subgrupos y orden de las celebraciones) sale de
data/toc.json, que reproduce el indice del propio sitio; de ahi se genera
tambien el INDICE NAVEGABLE del principio: cada domingo o feria es un enlace
al lugar del documento donde esta su formulario.

Las formulas ("Lectio libri Isaiae prophetae"...) salen de
data/latin_formulas.csv, que es editable sin tocar codigo.

Uso:  python src/8_render.py [--leccionario I] [--salida out/lectionarium.md]
      python src/8_render.py --separados      (un fichero por leccionario)
"""

import argparse
import csv
import importlib.util
import json
import os
import re
import unicodedata
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "out")

# Las dos fuentes latinas. La Clementina es la Vulgata de siempre; la Nova
# Vulgata (1979, editio typica altera de 1986) es el texto que usan los libros
# liturgicos actuales: el Ordo lectionum Missae de 1981 la puso en lugar de la
# Vulgata que traia la edicion de 1969.
FUENTES = {
    "clementina": {
        "lecturas": "readings_latin.json",
        "corpus": "vulgata.json",
        "formulas": "latin_formulas.csv",
        "salida": "",
        "cabecera": ("Texto: *Biblia Sacra juxta Vulgatam Clementinam* "
                     "(ed. Michael Tweedale).\n"
                     "Estructura: *Leccionario* de Servicios Koinonía.\n"),
        "titulo": "Lectionarium Latinum",
    },
    "nova": {
        "lecturas": "readings_latin_nova.json",
        "corpus": "nova_vulgata.json",
        "formulas": "latin_formulas_nova.csv",
        "salida": "nova",
        "cabecera": ("Texto: *Nova Vulgata · Bibliorum Sacrorum editio*, "
                     "editio typica altera (Libreria Editrice Vaticana, 1986), "
                     "el texto latino de los libros litúrgicos vigentes.\n"
                     "Fórmulas de introducción: normas del *Ordo lectionum "
                     "Missae*, editio typica altera, 1981.\n"
                     "Estructura: *Leccionario* de Servicios Koinonía.\n"),
        "titulo": "Lectionarium Latinum · Nova Vulgata",
    },
}

TITULO = {
    "primera lectura": "LECTIO PRIMA",
    "segunda lectura": "LECTIO SECUNDA",
    "tercera lectura": "LECTIO TERTIA",
    "cuarta lectura": "LECTIO QUARTA",
    "quinta lectura": "LECTIO QUINTA",
    "sexta lectura": "LECTIO SEXTA",
    "septima lectura": "LECTIO SEPTIMA",
    "epistola": "EPISTOLA",
    # los repertorios de los Comunes y de las misas rituales y votivas: el
    # libro no las numera, las agrupa por Testamento
    "lectura del Antiguo Testamento": "LECTIO VETERIS TESTAMENTI",
    "lectura del Nuevo Testamento": "LECTIO NOVI TESTAMENTI",
    "salmo responsorial": "PSALMUS RESPONSORIUS",
    "aleluya": "ALLELUIA",
    "evangelio": "EVANGELIUM",
    "secuencia": "SEQUENTIA",
}
ORDEN_LECT = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX"]
NOMBRE_LECT = {
    "I": "Leccionario I · Dominical y festivo · Ciclo A",
    "II": "Leccionario II · Dominical y festivo · Ciclo B",
    "III": "Leccionario III · Dominical y festivo · Ciclo C",
    "IV": "Leccionario IV · Ferias del Tiempo Ordinario · Años I y II",
    "V": "Leccionario V · Propio y Común de los Santos",
    "VI": "Leccionario VI · Misas por diversas necesidades y votivas",
    "VII": "Leccionario VII · Ferias de Adviento, Navidad, Cuaresma y Pascua",
    "VIII": "Leccionario VIII · Misas rituales y de difuntos",
    "IX": "Leccionario IX · Misas con niños",
}
ARCHIVO_LECT = {
    "I": "Leccionario_I_Domingos_cicloA",
    "II": "Leccionario_II_Domingos_cicloB",
    "III": "Leccionario_III_Domingos_cicloC",
    "IV": "Leccionario_IV_Ferias_TiempoOrdinario",
    "V": "Leccionario_V_Propio_y_Comun_de_los_Santos",
    "VI": "Leccionario_VI_Misas_diversas_necesidades_y_votivas",
    "VII": "Leccionario_VII_Ferias_Adviento_Navidad_Cuaresma_Pascua",
    "VIII": "Leccionario_VIII_Misas_rituales_y_de_difuntos",
    "IX": "Leccionario_IX_Misas_con_ninos",
}
ARCHIVO_ANUAL = "Leccionario_ano_liturgico_completo"
# en un grupo de entradas cortas (los dias de una semana) el indice se aprieta
# en una sola linea en vez de gastar seis
INLINE_MAX_LARGO = 24
INLINE_MIN_ITEMS = 3


def load_formulas(nombre="latin_formulas.csv"):
    f, sig = {}, {}
    with open(os.path.join(DATA, nombre), encoding="utf-8",
              newline="") as fh:
        for row in csv.DictReader(fh):
            f[row["vulgata"].strip()] = ac(row["formula"].strip())
            sig[row["vulgata"].strip()] = row.get("sigla_lat", "").strip()
    return f, sig


# --------------------------------------------------------------------------
# acentuacion liturgica (fase 9): la pone 13_acentos.py, que decide palabra por
# palabra y deja su informe en data/acentos_cobertura_*.txt
# --------------------------------------------------------------------------
_ACENTOS = None


def activa_acentos(si=True):
    """Enciende o apaga la acentuacion de todo lo que se escriba a partir de aqui."""
    global _ACENTOS
    if not si:
        _ACENTOS = None
        return None
    _ACENTOS = modulo("13_acentos").acentuador()
    return _ACENTOS


def ac(texto):
    """El texto latino con sus acentos, si la acentuacion esta encendida."""
    return _ACENTOS.texto(texto) if _ACENTOS is not None else texto


def load_tituli_salmos():
    """Epigrafes de los salmos de la Nova Vulgata, tomados de su cursiva.

    La edicion los imprime en cursiva dentro del versiculo 1 ("Magistro chori.
    PSALMUS. David."). Son epigrafe, no texto del salmo, y como antifona
    estorban, asi que hay que poder quitarlos sin adivinar.
    """
    ruta = os.path.join(DATA, "nova_psalmi_tituli.csv")
    tabla = {}
    if not os.path.exists(ruta):
        return tabla
    with open(ruta, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            tabla[(row["salmo"].strip(), row["vers"].strip())] = \
                row["titulo"].strip()
    return tabla


def modulo(nombre):
    """Importa un script cuyo nombre empieza por un numero."""
    spec = importlib.util.spec_from_file_location(
        "m" + re.sub(r"\W", "", nombre),
        os.path.join(ROOT, "src", nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_t10 = None


def slug(archivo, cel_n):
    global _t10
    if _t10 is None:
        _t10 = modulo("10_toc")
    return _t10.slug_celebracion(archivo, cel_n)


def load_toc():
    ruta = os.path.join(DATA, "toc.json")
    if not os.path.exists(ruta):
        return {}
    return json.load(open(ruta, encoding="utf-8"))


_REMIS = None


def remisiones():
    """{(leccionario, archivo): remision} de las memorias sin lecturas propias.

    En el santoral hay nueve memorias que el libro resuelve con una linea -"Del
    Comun de pastores"- y nada mas. No dan ninguna lectura, asi que no llegan
    por readings_latin.json; sin esto, esos nueve dias se caerian del documento.
    """
    global _REMIS
    if _REMIS is None:
        ruta = os.path.join(DATA, "remisiones.json")
        _REMIS = {}
        if os.path.exists(ruta):
            for r in json.load(open(ruta, encoding="utf-8")):
                _REMIS[(r["leccionario"], r["archivo"])] = r
    return _REMIS


# --------------------------------------------------------------------------
# esqueleto: indice y orden del cuerpo, los dos de la misma lista de bloques
# --------------------------------------------------------------------------
def celebraciones(entradas):
    """{leccionario: OrderedDict[(archivo, cel_n)] -> [lecturas ordenadas]}"""
    por_lect = OrderedDict()
    for e in entradas:
        por_lect.setdefault(e["leccionario"], OrderedDict()) \
                .setdefault((e["archivo"], e.get("cel_n", 0)), []).append(e)
    for celebs in por_lect.values():
        for lecturas in celebs.values():
            lecturas.sort(key=lambda x: x["orden"])
    return por_lect


def etiqueta_secundaria(lecturas, hermanas):
    """Nombre para una celebracion extra dentro de una misma pagina.

    Cuando el sitio repite el nombre (los domingos de Cuaresma llevan dentro
    las lecturas del ciclo A), lo que las distingue es el ciclo.
    """
    cab = lecturas[0]
    nombre = cab["celebracion"]
    repetido = sum(1 for l in hermanas if l[0]["celebracion"] == nombre) > 1
    if repetido and cab.get("ciclo"):
        return "%s (%s)" % (nombre, cab["ciclo"])
    return nombre


def plan(lect, celebs, arbol):
    """Bloques que gobiernan a la vez el indice y el cuerpo del documento.

    Cada bloque es {'tipo': 'seccion'|'grupo'|'item', ...}. Los 'item' llevan
    su clave (archivo, cel_n), su ancla y si son una entrada repetida del
    indice (el sitio enlaza dos veces la misma pagina) o una celebracion
    secundaria dentro de la pagina.
    """
    bloques = []
    usadas = set()
    sin_texto = []
    hermanas = {}
    for (arch, cel_n), lecturas in celebs.items():
        hermanas.setdefault(arch, []).append(lecturas)

    for nodo in arbol.get("nodos", []):
        sang = nodo.get("sangria", 0)
        if nodo["nivel"] in (1, 2):
            bloques.append({"tipo": "seccion" if nodo["nivel"] == 1 else "grupo",
                            "texto": nodo["texto"], "sangria": sang})
            continue
        arch = nodo["archivo"]
        if arch not in hermanas:
            rem = remisiones().get((lect, arch))
            if rem is not None:
                bloques.append({"tipo": "remision", "texto": nodo["texto"],
                                "remision": rem, "sangria": sang,
                                "slug": slug(arch, rem.get("cel_n", 0)),
                                "repetida": False, "secundaria": False})
                continue
            if arch not in [a for a, _ in sin_texto]:
                sin_texto.append((arch, nodo["texto"]))
            continue
        claves = sorted(k for k in celebs if k[0] == arch)
        primera = claves[0]
        if primera in usadas:                 # el indice enlaza dos veces
            bloques.append({"tipo": "item", "texto": nodo["texto"],
                            "clave": primera, "slug": slug(*primera),
                            "sangria": sang,
                            "repetida": True, "secundaria": False})
            continue
        bloques.append({"tipo": "item", "texto": nodo["texto"],
                        "clave": primera, "slug": slug(*primera),
                        "sangria": sang,
                        "repetida": False, "secundaria": False})
        usadas.add(primera)
        for k in claves[1:]:
            if k in usadas:
                continue
            bloques.append({"tipo": "item",
                            "texto": etiqueta_secundaria(celebs[k],
                                                         hermanas[arch]),
                            "clave": k, "slug": slug(*k),
                            "sangria": sang + 1,
                            "repetida": False, "secundaria": True})
            usadas.add(k)

    sueltas = [k for k in celebs if k not in usadas]
    if sueltas:
        bloques.append({"tipo": "seccion", "texto": "OTROS TEXTOS",
                        "sangria": 0})
        for k in sueltas:
            bloques.append({"tipo": "item", "texto": celebs[k][0]["celebracion"],
                            "clave": k, "slug": slug(*k), "sangria": 0,
                            "repetida": False, "secundaria": False})

    # cabeceras que se quedaron sin ninguna entrada debajo
    limpio = []
    for i, b in enumerate(bloques):
        if b["tipo"] in ("item", "remision"):
            limpio.append(b)
            continue
        nivel = 1 if b["tipo"] == "seccion" else 2
        for x in bloques[i + 1:]:
            if x["tipo"] in ("item", "remision"):
                limpio.append(b)
                break
            if (1 if x["tipo"] == "seccion" else 2) <= nivel:
                break
    # la sangria del sitio es absoluta (depende de cuantos blockquote lleve
    # encima); para maquetar hace falta relativa al nivel de las entradas
    base = min([b["sangria"] for b in limpio
                if b["tipo"] in ("item", "remision")], default=0)
    for b in limpio:
        b["nivel_sangria"] = max(0, b["sangria"] - base)
    n_rem = sum(1 for b in limpio if b["tipo"] == "remision")
    return {"bloques": limpio, "sin_texto": sin_texto,
            "n_celebraciones": len(usadas) + len(sueltas) + n_rem}


def lineas_indice(bloques):
    """Decide la forma del indice: que va en su linea y que va apretado.

    Devuelve una lista de lineas ya resueltas, que Markdown y Word maquetan
    cada uno a su manera:
      {"tipo": "seccion", "texto": ...}
      {"tipo": "grupo",   "texto": ..., "sangria": n}
      {"tipo": "entradas", "sangria": n, "grupo": texto|None,
       "items": [bloque...], "inline": bool}
    """
    lineas = []
    pend_grupo = None
    i, n = 0, len(bloques)
    while i < n:
        b = bloques[i]
        if b["tipo"] == "seccion":
            if pend_grupo:
                lineas.append({"tipo": "grupo", "texto": pend_grupo["texto"],
                               "sangria": pend_grupo["nivel_sangria"]})
                pend_grupo = None
            lineas.append({"tipo": "seccion", "texto": b["texto"]})
            i += 1
            continue
        if b["tipo"] == "grupo":
            if pend_grupo:
                lineas.append({"tipo": "grupo", "texto": pend_grupo["texto"],
                               "sangria": pend_grupo["nivel_sangria"]})
            pend_grupo = b
            i += 1
            continue
        # tramo de entradas seguidas, partido por niveles de sangria
        j = i
        while j < n and bloques[j]["tipo"] in ("item", "remision"):
            j += 1
        k = i
        primero = True
        while k < j:
            m = k
            while m < j and (bloques[m]["nivel_sangria"]
                             == bloques[k]["nivel_sangria"]):
                m += 1
            tramo = bloques[k:m]
            inline = (len(tramo) >= INLINE_MIN_ITEMS and
                      all(len(x["texto"]) <= INLINE_MAX_LARGO for x in tramo))
            grupo = None
            sangria = tramo[0]["nivel_sangria"]
            if primero and pend_grupo is not None:
                if inline and sangria <= pend_grupo["nivel_sangria"]:
                    grupo = pend_grupo["texto"]      # cabecera y dias, una linea
                else:
                    lineas.append({"tipo": "grupo",
                                   "texto": pend_grupo["texto"],
                                   "sangria": pend_grupo["nivel_sangria"]})
                    # lo que cuelga de la cabecera va sangrado debajo de ella
                    sangria = max(sangria, pend_grupo["nivel_sangria"] + 1)
                pend_grupo = None
            lineas.append({"tipo": "entradas", "sangria": sangria,
                           "grupo": grupo, "items": tramo, "inline": inline})
            primero = False
            k = m
        i = j
    if pend_grupo:
        lineas.append({"tipo": "grupo", "texto": pend_grupo["texto"],
                       "sangria": pend_grupo["nivel_sangria"]})
    return lineas


# --------------------------------------------------------------------------
# texto latino
# --------------------------------------------------------------------------
def cita_latina(e, siglas):
    """Reescribe 'Sal 121,1-2' como 'Ps 121,1-2'.

    Con la Nova Vulgata se anade entre corchetes el numero del salmo en su
    numeracion. El leccionario -y el propio Ordo lectionum Missae de 1981- cita
    los salmos por el griego, que es la numeracion de la Vulgata, mientras que
    la Nova Vulgata los imprime por el hebreo. Se conserva la cita liturgica y
    se deja constancia de donde esta el texto.
    """
    c = e["canonica"]
    es, lat = e.get("sigla", ""), siglas.get(e["libro_vulgata"], "")
    if es and lat and c.startswith(es):
        c = lat + c[len(es):]
    otra = (e.get("canonica_corpus") or "").strip()
    if otra:
        c += " [%s]" % otra
    return c


# referencia de la antifona: "1", "cf. 7", "4bc", "cf. 7c y 10b"
ANTIF_RE = re.compile(r"(\d+)\s*[a-z]*", re.I)

# La Clementina mete el titulo del salmo dentro del versiculo 1
# ("Canticum graduum.", "In finem, psalmus David."). Como antifona estorba.
TITULO_SALMO_RE = re.compile(
    r"^(Alleluja|Canticum graduum|Psalmus David|Laudatio David|Oratio\b[^.]*"
    r"|In finem\b[^.]*|Intellectus\b[^.]*|Ipsi David|Huic David"
    r"|Victori\b[^.]*)[.,]\s*", re.I)


TITULI = {}      # epigrafes de los salmos; solo con la Nova Vulgata


def sin_titulo_salmo(t, cap=None, vers=None):
    """Quita el epigrafe del salmo.

    Con la Nova Vulgata se quita el epigrafe exacto que da la propia edicion en
    cursiva; con la Clementina hay que reconocerlo por sus formulas, porque el
    PDF no distingue la cursiva.
    """
    if TITULI:
        tit = TITULI.get((str(cap), str(vers)))
        if tit and t.startswith(tit):
            return t[len(tit):].strip()
        return t
    prev = None
    while prev != t:
        prev = t
        t = TITULO_SALMO_RE.sub("", t)
    return t


def antifona_latina(e, corpus):
    """Texto latino de la antifona, si su referencia apunta al mismo salmo."""
    ref = (e.get("antifona_ref") or "").strip()
    if not ref or not e["tramos"]:
        return None
    limpio = re.sub(r"^\s*(cf\.?:?\.?|cfr\.?)\s*", "", ref, flags=re.I)
    if re.search(r"[A-Za-z]{2,}", limpio):
        return None                    # apunta a otro libro: fuera de alcance
    nums = [int(m.group(1)) for m in ANTIF_RE.finditer(limpio)]
    if not nums:
        return None
    cap = e["tramos"][0][0]["cap"]
    libro = corpus.get(e["libro_vulgata"], {}).get(str(cap), {})
    partes = [sin_titulo_salmo(libro[str(n)], cap, n)
              for n in nums if str(n) in libro]
    return ac(" ".join(p for p in partes if p)) or None


def titulo_lectura(e):
    t = TITULO.get(e["tipo"], e["tipo"].upper())
    # el numero con que el libro ordena las opciones de un repertorio: sin el,
    # los doce evangelios de una misma misa votiva serian doce "EVANGELIUM"
    if e.get("_opcion"):
        t += " " + str(e["_opcion"])
    if e.get("variante") == "alternativa":
        t += " — Vel:"
    elif e.get("variante") == "forma_breve":
        t += " — Forma brevior:"
    return ac(t)          # las versales no se acentuan; "brévior" si


def verse_block(tramos, numerar=True, sep="\n\n[...]\n\n", salmo=False):
    """Texto latino; entre tramos va la marca de versiculos omitidos.

    En el salmo responsorial se quita el epigrafe ("Magistro chori. PSALMUS.
    David."), que los libros liturgicos no imprimen.
    """
    partes = []
    for tr in tramos:
        linea = []
        for v in tr:
            t = v["texto"]
            if salmo:
                t = sin_titulo_salmo(t, v["cap"], v["vers"])
                if not t:
                    continue
            t = ac(t)
            # el numero puede llevar letra (Est 4, 17n; 1 Par 4, 18a)
            linea.append("**%s** %s" % (v["vers"], t) if numerar else t)
        partes.append(" ".join(linea))
    return sep.join(partes)


# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------
def md_indice(bloques, sin_texto):
    out = ['## <a id="indice"></a>Índice\n']
    for ln in lineas_indice(bloques):
        if ln["tipo"] == "seccion":
            out.append("\n**%s**\n" % ln["texto"])
            continue
        sang = "  " * ln["sangria"]
        if ln["tipo"] == "grupo":
            out.append("%s- *%s*" % (sang, ln["texto"]))
            continue
        enlaces = []
        for b in ln["items"]:
            e = "[%s](#%s)" % (b["texto"], b["slug"])
            enlaces.append("↳ " + e if b["secundaria"] else e)
        if ln["inline"]:
            cabeza = "*%s*: " % ln["grupo"] if ln["grupo"] else ""
            out.append("%s- %s%s" % (sang, cabeza, " · ".join(enlaces)))
        else:
            for e in enlaces:
                out.append("%s- %s" % (sang, e))
    if sin_texto:
        out.append("\n> Entradas del índice sin formulario de lecturas "
                   "(introducciones, listas de aclamaciones, textos comunes): "
                   "%s." % "; ".join(t for _, t in sin_texto))
    return "\n".join(out)


def md_lecturas(lecturas, formulas, siglas, corpus, numerar, nivel=5):
    """Las lecturas de un formulario, con su formula, su cita y su texto."""
    out = []
    for e in lecturas:
        out.append("\n%s %s" % ("#" * nivel, titulo_lectura(e)))
        cita = cita_latina(e, siglas)
        if e.get("aprox_cf"):
            cita = "cf. " + cita
        if e["tipo"] in ("aleluya", "secuencia"):
            out.append("*%s*\n" % cita)
        else:
            formula = formulas.get(e["libro_vulgata"], "Lectio")
            out.append("**%s** &nbsp;&nbsp; *%s*\n" % (formula, cita))

        if e["tipo"] == "salmo responsorial":
            ant = antifona_latina(e, corpus)
            if ant:
                out.append("℟. *%s*\n" % ant)
            elif e.get("antifona_ref"):
                out.append("℟. *(%s)*\n" % e["antifona_ref"])
            # en el salmo los cortes son estrofas, no omisiones
            out.append(verse_block(e["tramos"], numerar, "\n\n℟.\n\n",
                                   salmo=True))
            out.append("\n℟.")
        else:
            out.append(verse_block(e["tramos"], numerar))
            if e["tipo"] not in ("aleluya", "secuencia"):
                out.append("\n*%s*" % ac("Verbum Domini."))
    return out


def md_remision(rem, ancla, con_volver=True):
    """Una memoria que el libro resuelve remitiendo al Comun."""
    out = ['\n#### <a id="%s"></a>%s' % (ancla, rem["celebracion"])]
    etiqueta = " · ".join(x for x in (rem.get("fecha"),
                                     rem.get("grado")) if x)
    if etiqueta:
        out.append("*%s*" % etiqueta)
    for r in rem.get("comunes") or []:
        out.append("\n> %s." % r["texto"].rstrip(" .;,"))
    if con_volver:
        out.append("\n<sup>[↑ Índice](#indice)</sup>")
    return "\n".join(out)


def md_celebracion(lecturas, ancla, formulas, siglas, corpus, numerar,
                   con_volver=True):
    cab = lecturas[0]
    out = ['\n#### <a id="%s"></a>%s' % (ancla, cab["celebracion"])]
    # el leccionario V va ordenado por dias del ano, y el dia forma parte del
    # encabezamiento de la celebracion, no es un adorno
    etiqueta = " · ".join(x for x in (cab.get("_fecha"), cab.get("_grado"))
                         if x)
    if etiqueta:
        out.append("*%s*" % etiqueta)
    if cab.get("ciclo"):
        out.append("*%s*" % cab["ciclo"])
    for rem in cab.get("_comunes") or []:
        out.append("\n> %s." % rem["texto"].rstrip(" .;,"))
    out += md_lecturas(lecturas, formulas, siglas, corpus, numerar, 5)
    if con_volver:
        out.append("\n<sup>[↑ Índice](#indice)</sup>")
    return "\n".join(out)


def md_leccionario(lect, celebs, arbol, formulas, siglas, corpus, numerar,
                   con_indice=True, indice_anexos=""):
    p = plan(lect, celebs, arbol)
    n_lect = sum(len(v) for v in celebs.values())
    n_vers = sum(e["n_versiculos"] for v in celebs.values() for e in v)
    out = ["\n\n# %s\n" % NOMBRE_LECT.get(lect, "Leccionario " + lect)]
    out.append("*Lectionarium Latinum* · " + CABECERA)
    out.append("%d celebraciones · %d lecturas · %d versículos.\n"
               % (p["n_celebraciones"], n_lect, n_vers))
    if con_indice:
        out.append(md_indice(p["bloques"], p["sin_texto"]))
        if indice_anexos:
            out.append(indice_anexos)
        out.append("\n---")
    for b in p["bloques"]:
        if b["tipo"] == "seccion":
            out.append("\n\n## %s" % b["texto"])
        elif b["tipo"] == "grupo":
            out.append("\n\n### %s" % b["texto"])
        elif b["tipo"] == "remision":
            out.append(md_remision(b["remision"], b["slug"], con_indice))
        elif not b["repetida"]:
            out.append(md_celebracion(celebs[b["clave"]], b["slug"], formulas,
                                      siglas, corpus, numerar, con_indice))
    return "\n".join(out), p


# --------------------------------------------------------------------------
# el ano liturgico de corrido: los cinco leccionarios en un solo documento
# --------------------------------------------------------------------------
def load_calendario():
    ruta = os.path.join(DATA, "calendario.json")
    if not os.path.exists(ruta):
        raise SystemExit("falta data/calendario.json: ejecuta "
                         "python src/12_calendario.py")
    return json.load(open(ruta, encoding="utf-8"))


def bloques_por_clave(entradas):
    """(leccionario, archivo, cel_n) -> lecturas ordenadas."""
    bl = {}
    for e in entradas:
        bl.setdefault((e["leccionario"], e["archivo"], e.get("cel_n", 0)),
                      []).append(e)
    for v in bl.values():
        v.sort(key=lambda x: x["orden"])
    return bl


def md_indice_anual(cal):
    """Una linea por semana: el domingo con sus ciclos y luego sus ferias."""
    out = ['## <a id="indice"></a>Índice del año\n']
    for sec in cal["secciones"]:
        out.append("\n**%s**\n" % sec["titulo"])
        for g in sec["grupos"]:
            enlaces = ["[%s](#%s)" % (d["titulo_indice"], d["slug"])
                       for d in g["dias"]]
            if not enlaces:
                continue
            if g["titulo"]:
                out.append("- *%s*: %s" % (g["titulo"], " · ".join(enlaces)))
            else:
                out.append("- %s" % " · ".join(enlaces))
    return "\n".join(out)


def md_anual(cal, bl, formulas, siglas, corpus, numerar, indice_anexos=""):
    n_lect = sum(len(v) for v in bl.values())
    out = ["# Leccionario latino · el año litúrgico completo\n",
           "*Lectionarium Latinum* · " + CABECERA,
           "Los cinco leccionarios en el orden del año: cada domingo con sus "
           "tres ciclos y, detrás, las ferias de su semana.\n"]
    dias = sum(len(g["dias"]) for s in cal["secciones"] for g in s["grupos"])
    out.append("%d días · %d formularios · %d lecturas.\n"
               % (dias, sum(len(d["bloques"]) for s in cal["secciones"]
                            for g in s["grupos"] for d in g["dias"]), n_lect))
    out.append(md_indice_anual(cal))
    if indice_anexos:
        out.append(indice_anexos)
    out.append("\n---")
    for sec in cal["secciones"]:
        out.append("\n\n## %s" % sec["titulo"])
        for g in sec["grupos"]:
            if g["titulo"]:
                out.append("\n### %s" % g["titulo"])
            for dia in g["dias"]:
                out.append('\n#### <a id="%s"></a>%s'
                           % (dia["slug"], dia["titulo"]))
                for b in dia["bloques"]:
                    lecturas = bl.get(tuple(b["clave"]))
                    if not lecturas:
                        continue
                    out.append("\n##### %s" % b["etiqueta"])
                    out += md_lecturas(lecturas, formulas, siglas, corpus,
                                       numerar, 6)
                out.append("\n<sup>[↑ Índice](#indice)</sup>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# los anexos (fase 12): versiculos alternativos del Aleluya y textos comunes
# --------------------------------------------------------------------------
def load_anexos(fuente):
    """(estructura, {(anexo, orden): lectura resuelta}, {(anexo, n): latin fijo})

    Los tres ficheros se leen aparte a proposito: `anexos.json` dice que hay y
    en que orden, `anexos_readings_latin*.json` trae el latin resuelto por el
    mismo resolutor que las lecturas, y `anexos_latin_fijo.csv` los quince
    textos que no son Escritura y por tanto no salen de la Vulgata.
    """
    ruta = os.path.join(DATA, "anexos.json")
    if not os.path.exists(ruta):
        return None, {}, {}
    meta = json.load(open(ruta, encoding="utf-8"))
    nombre = ("anexos_readings_latin.json" if fuente == "clementina"
              else "anexos_readings_latin_nova.json")
    lat = os.path.join(DATA, nombre)
    resueltas = {}
    if os.path.exists(lat):
        for e in json.load(open(lat, encoding="utf-8")):
            resueltas[(e.get("_anexo"), e["orden"])] = e
    fijo = {}
    ruta_fijo = os.path.join(DATA, "anexos_latin_fijo.csv")
    if os.path.exists(ruta_fijo):
        with open(ruta_fijo, encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                fijo[(row["anexo"].strip(), row["n"].strip())] = row
    return meta, resueltas, fijo


def sin_acento(t):
    """Quita el agudo y deja la dieresis y la ligadura, que no son acento."""
    return unicodedata.normalize(
        "NFC", "".join(c for c in unicodedata.normalize("NFD", t)
                       if c != "́"))


def texto_fijo(t):
    """El latin de la tabla fija ya viene acentuado; se le quita si toca."""
    return t if _ACENTOS is not None else sin_acento(t)


ANEXOS_ANCLA = "anexos"


def md_anexos(meta, resueltas, fijo, siglas, corpus, numerar, nivel=2):
    """Los anexos, como lista numerada: no son formularios de un dia."""
    if not meta:
        return "", []
    out = ['\n\n%s <a id="%s"></a>APÉNDICES' % ("#" * nivel, ANEXOS_ANCLA)]
    out.append("\nListas que el leccionario pone detrás de los formularios: "
               "los versículos que pueden sustituir al del día antes del "
               "Evangelio, y los salmos que pueden cantarse en lugar del "
               "propio.\n")
    indice, ausentes = [], []
    for a in meta["anexos"]:
        if a.get("ausente"):
            ausentes.append(a)
            continue
        ancla = "anexo_" + a["id"]
        indice.append((a, ancla))
        out.append('\n%s <a id="%s"></a>%s'
                   % ("#" * (nivel + 1), ancla, a["titulo"]))
        out.append("*%s*\n" % a["ambito"])
        tiempo = None
        for e in a["entradas"]:
            if e.get("tiempo") and e["tiempo"] != tiempo:
                tiempo = e["tiempo"]
                out.append("\n%s %s" % ("#" * (nivel + 2), tiempo))
            if e.get("sin_cita"):
                row = fijo.get((a["id"], str(e["n"])))
                if not row:
                    continue
                out.append("\n**%s.** %s" % (e["n"], texto_fijo(row["latin"])))
                continue
            lec = resueltas.get((a["id"], e["orden"]))
            if not lec or not lec["tramos"]:
                continue
            cita = cita_latina(lec, siglas)
            if lec.get("aprox_cf"):
                cita = "cf. " + cita
            es_salmo = lec["tipo"] == "salmo responsorial"
            if es_salmo:
                out.append("\n**%s**" % cita)
            else:
                out.append("\n**%s.** &nbsp;&nbsp; *%s*" % (e["n"], cita))
            if es_salmo:
                ant = antifona_latina(lec, corpus)
                if ant:
                    out.append("\n℟. *%s*\n" % ant)
                elif lec.get("antifona_ref"):
                    out.append("\n℟. *(%s)*\n" % lec["antifona_ref"])
                out.append(verse_block(lec["tramos"], numerar, "\n\n℟.\n\n",
                                       salmo=True))
                out.append("\n℟.")
            else:
                out.append("\n" + verse_block(lec["tramos"], False))
        if a.get("respuestas"):
            out.append("\n%s Respuestas salmódicas alternativas"
                       % ("#" * (nivel + 2)))
            out.append("\n> Estas respuestas son antífonas sin cita bíblica: "
                       "el leccionario no da su referencia, así que no hay de "
                       "dónde sacar su latín. Se dan en castellano.\n")
            for r in a["respuestas"]:
                out.append("- **%s** %s" % (r["tiempo"], r["es"]))
    if ausentes:
        out.append("\n> Faltan por incorporar %d listas cuyas páginas el "
                   "sitio no ha llegado a servir: %s. El rastreador las "
                   "vuelve a pedir en cada pasada."
                   % (len(ausentes),
                      "; ".join(a["ambito"] for a in ausentes)))
    return "\n".join(out), indice


IT_ANCLA = "indice_textos"
# abreviaturas para que cada pasaje quepa en una linea
CORTO = [(r"^Domingo\b", "Dom."), (r"^Lunes\b", "Lun."), (r"^Martes\b", "Mar."),
         (r"^Miércoles\b", "Mié."), (r"^Jueves\b", "Jue."),
         (r"^Viernes\b", "Vie."), (r"^Sábado\b", "Sáb."),
         (r"\b(?:del|de) Tiempo Ordinario\b", "T.O."),
         (r"\b(?:del|de) Adviento\b", "Adv."),
         (r"\b(?:del|de) Cuaresma\b", "Cuar."),
         (r"\b(?:del|de) Pascua\b", "Pasc."),
         (r"\b(?:del|de) Navidad\b", "Nav."),
         (r"\bde la (\d+)ª semana\b", r"\1ª sem."),
         (r"\bde la (\w+) semana\b", r"\1 sem.")]


def corto(t):
    for pat, rep in CORTO:
        t = re.sub(pat, rep, t)
    return re.sub(r"\s+", " ", t).strip()


def load_indice_textos():
    ruta = os.path.join(DATA, "indice_textos.json")
    if not os.path.exists(ruta):
        return None
    return json.load(open(ruta, encoding="utf-8"))


def cita_lat(cita, sigla_es, siglas, libro):
    lat = siglas.get(libro, "")
    if sigla_es and lat and cita.startswith(sigla_es):
        return lat + cita[len(sigla_es):]
    return cita


def md_indice_textos(it, siglas, nivel=2):
    """El leccionario al reves: cada pasaje, y donde se lee."""
    if not it:
        return "", ""
    out = ['\n\n%s <a id="%s"></a>ÍNDICE DE TEXTOS' % ("#" * nivel, IT_ANCLA)]
    n_p = sum(len(l["pasajes"]) for l in it["libros"])
    out.append("\nLos %d pasajes bíblicos del leccionario, por orden de libro "
               "y capítulo, con las celebraciones en que se leen.\n" % n_p)
    for libro in it["libros"]:
        out.append("\n%s %s" % ("#" * (nivel + 1), libro["es"]))
        for p in libro["pasajes"]:
            donde = " · ".join(
                "[%s](#%s)" % (corto(d["celebracion"]), d["slug"])
                if d["slug"] else corto(d["celebracion"])
                for d in p["donde"])
            out.append("- **%s** — %s"
                       % (cita_lat(p["cita"], p["sigla"], siglas,
                                   libro["libro"]), donde))
    return "\n".join(out), ('\n**<a href="#%s">ÍNDICE DE TEXTOS</a>** — los '
                            '%d pasajes bíblicos y dónde se leen\n'
                            % (IT_ANCLA, n_p))


def md_indice_anexos(indice):
    if not indice:
        return ""
    lineas = ['\n**<a href="#%s">APÉNDICES</a>**\n' % ANEXOS_ANCLA]
    for a, ancla in indice:
        lineas.append("- [%s · %s](#%s)" % (a["titulo"], a["ambito"], ancla))
    return "\n".join(lineas)


CABECERA = FUENTES["clementina"]["cabecera"]      # lo cambia main() si procede


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leccionario", default=None,
                    help="I, II, III, IV o VII; por defecto todos")
    ap.add_argument("--celebracion", default=None,
                    help="filtra por texto del nombre de la celebracion")
    ap.add_argument("--salida", default=None)
    ap.add_argument("--separados", action="store_true",
                    help="un fichero por leccionario, cada uno con su indice")
    ap.add_argument("--anual", action="store_true",
                    help="un solo documento en el orden del ano liturgico")
    ap.add_argument("--sin-numeros", action="store_true")
    ap.add_argument("--fuente", default="clementina", choices=sorted(FUENTES),
                    help="corpus latino: la Clementina o la Nova Vulgata")
    ap.add_argument("--sin-acentos", action="store_true",
                    help="sin acentuacion liturgica (por omision va acentuado)")
    ap.add_argument("--sin-anexos", action="store_true",
                    help="sin los apendices (por omision van al final)")
    ap.add_argument("--sin-indice-textos", action="store_true",
                    help="sin el indice de textos (por omision va al final)")
    args = ap.parse_args()
    cfg = FUENTES[args.fuente]
    activa_acentos(not args.sin_acentos)
    global CABECERA, OUT, TITULI
    CABECERA = cfg["cabecera"]
    if cfg["salida"]:
        OUT = os.path.join(OUT, cfg["salida"])
    if args.fuente == "nova":
        TITULI = load_tituli_salmos()

    entradas = json.load(open(os.path.join(DATA, cfg["lecturas"]),
                              encoding="utf-8"))
    if args.leccionario:
        entradas = [e for e in entradas if e["leccionario"] == args.leccionario]
    if args.celebracion:
        pat = args.celebracion.lower()
        entradas = [e for e in entradas if pat in e["celebracion"].lower()]
    if not entradas:
        raise SystemExit("ningun texto coincide con el filtro")

    formulas, siglas = load_formulas(cfg["formulas"])
    corpus = json.load(open(os.path.join(DATA, cfg["corpus"]),
                            encoding="utf-8"))
    toc = load_toc()
    numerar = not args.sin_numeros
    faltan = sorted({e["libro_vulgata"] for e in entradas
                     if e["libro_vulgata"] not in formulas})
    por_lect = celebraciones(entradas)
    # con un filtro por celebracion el indice no tiene sentido: el esqueleto
    # del leccionario entero quedaria lleno de entradas sin texto
    con_indice = not args.celebracion
    os.makedirs(OUT, exist_ok=True)

    # los apendices: las listas que el leccionario pone detras de los
    # formularios. Van al final de cada documento y con entrada en su indice.
    cuerpo_anexos, indice_anexos = "", []
    if not args.sin_anexos:
        meta, resueltas, fijo = load_anexos(args.fuente)
        cuerpo_anexos, indice_anexos = md_anexos(meta, resueltas, fijo, siglas,
                                                 corpus, numerar)
    md_ix_anexos = md_indice_anexos(indice_anexos)
    # El indice de textos enlaza a los dias del calendario, y esas anclas solo
    # existen en el documento anual: en los cinco leccionarios por separado las
    # celebraciones se anclan por pagina del sitio, no por dia del ano. Meterlo
    # ahi serian 395 enlaces rotos, asi que va solo donde funciona.
    cuerpo_it, md_ix_it = "", ""
    if args.anual and not args.sin_indice_textos:
        cuerpo_it, md_ix_it = md_indice_textos(load_indice_textos(), siglas)
    md_ix_anexos = (md_ix_anexos + md_ix_it) if md_ix_it else md_ix_anexos

    def escribe(ruta, texto):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto + "\n")
        print("%-72s %6d KB" % (ruta[len(ROOT) + 1:],
                                os.path.getsize(ruta) // 1024))

    if args.anual:
        texto = md_anual(load_calendario(), bloques_por_clave(entradas),
                         formulas, siglas, corpus, numerar, md_ix_anexos)
        escribe(args.salida or os.path.join(OUT, ARCHIVO_ANUAL + ".md"),
                texto + cuerpo_anexos + cuerpo_it)
    elif args.separados:
        for lect in ORDEN_LECT:
            if lect not in por_lect:
                continue
            cuerpo, _ = md_leccionario(lect, por_lect[lect], toc.get(lect, {}),
                                       formulas, siglas, corpus, numerar,
                                       con_indice, md_ix_anexos)
            escribe(os.path.join(OUT, ARCHIVO_LECT[lect] + ".md"),
                    cuerpo.lstrip() + cuerpo_anexos + cuerpo_it)
    else:
        partes = ["# " + cfg["titulo"] + "\n", CABECERA]
        indice_gral = ["\n## Contenido\n"]
        cuerpos = []
        for lect in ORDEN_LECT:
            if lect not in por_lect:
                continue
            indice_gral.append("- %s" % NOMBRE_LECT.get(lect, lect))
            cuerpo, _ = md_leccionario(lect, por_lect[lect], toc.get(lect, {}),
                                       formulas, siglas, corpus, numerar,
                                       con_indice)
            cuerpos.append(cuerpo)
        if indice_anexos:
            indice_gral.append("- Apéndices")
        total_v = sum(e["n_versiculos"] for e in entradas)
        partes.append("\n%d lecturas · %d versículos.\n"
                      % (len(entradas), total_v))
        partes.extend(indice_gral)
        partes.extend(cuerpos)
        salida = args.salida or os.path.join(OUT, "lectionarium.md")
        escribe(salida, "\n".join(partes) + cuerpo_anexos)

    if faltan:
        print("SIN FORMULA LATINA: %s" % ", ".join(faltan))


if __name__ == "__main__":
    main()
