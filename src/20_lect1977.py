"""Fase 20 - El leccionario latino de 1977, cosechado de sus cuatro tomos.

`Missale/Missale cum Lectionarium/` son los cuatro tomos del *Missale Romanum
cum lectionibus* (Libreria Editrice Vaticana, 1977): 7 793 paginas con el
leccionario entero en latin dentro del Misal.

**De estos PDF no sale ni una letra que se publique.** Llevan capa de texto,
pero es un OCR malo de una pagina impresa que esta limpia y acentuada entera:
el agudo solo sobrevive sobre la `e` (97 261 `e` acentuadas frente a 15 `a`,
7 `i`, 5 `o` y 2 `u`), la `o` acentuada sale como el digito `6` doce mil veces
dentro de palabra, la `ae` ligada sale como `re`, y queda ruido suelto que
ninguna regla arregla (`cum`->`curo`, `sociati`->`sodati`, `lumine`->`lamine`).
Lo medido esta en `Missale/Leccionario-1977.md`.

Asi que el libro no se usa como fuente de letras sino como **arbitro**: dice
que texto latino es, que versiculos se leen y como empieza cada pericopa. Las
letras las ponen la Clementina y la Nova Vulgata, que el proyecto ya tiene
limpias y acentuadas.

Lo que esta fase deja medido, perícopa a pericopa:

* **La cita**, que es la llave para engancharla con `data/index_master.json`.
* **El incipit liturgico** -`In illo tempore:`, `Fratres:`, `In diebus
  illis:`-, que no esta en ningun corpus porque no es texto biblico sino
  leccionario. No se copia del OCR: se reconoce cual de las formas conocidas
  es y se escribe la forma canonica, bien acentuada, de la tabla de abajo.
* **La formula** con que el libro presenta cada lectura, que en varios libros
  esta redactada de otro modo que `data/latin_formulas_nova.csv`.

Dos trampas que costaron el parseo:

1. La tabla del proyecto dice `Lectio Prophetiae Ezechielis`, pero el Misal de
   1977 presenta a **todos los profetas** como `Lectio libri <genitivo>
   prophetae`. Sin las entradas de `ALIAS_FORMULA` se caian Isaias, Jeremias,
   Ezequiel y los doce profetas menores enteros.
2. El mismo libro llama **Siracidae** a lo que la tabla llama *Ecclesiastici*,
   y entonces 73 pericopas se iban a Esdras.

Salida:  data/lect1977_pericopas.json   lo cosechado, pericopa a pericopa
         data/lect1977_qa.txt           el informe

Uso:  python src/20_lect1977.py
"""

import argparse
import collections
import csv
import difflib
import io
import json
import os
import re
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DATA = os.path.join(RAIZ, "data")
TOMOS = os.path.join(RAIZ, "Missale", "Missale cum Lectionarium")
PATRON = "Missale Romanum cum lectionibus 1977 Vol %s-4.pdf"


# --------------------------------------------------------------------------
# normalizacion
# --------------------------------------------------------------------------
def sin_tildes(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def plano(s):
    """Forma de cotejo: sin tildes, minuscula, ae/oe desarmados, j->i, v->u."""
    s = s.replace("æ", "ae").replace("Æ", "Ae")
    s = s.replace("œ", "oe").replace("Œ", "Oe")
    s = sin_tildes(s).lower().replace("j", "i").replace("v", "u")
    return re.sub(r"[^a-z]", "", s)


# --------------------------------------------------------------------------
# las formulas, con lo que el Misal de 1977 redacta de otro modo
# --------------------------------------------------------------------------
_PROFETAS = {
    "Isaiae": ("Isaias", "Is"), "Ieremiae": ("Ieremias", "Ier"),
    "Ezechielis": ("Ezechiel", "Ez"), "Danielis": ("Daniel", "Dan"),
    "Osee": ("Osee", "Os"), "Ioelis": ("Ioel", "Ioel"),
    "Amos": ("Amos", "Am"), "Abdiae": ("Abdias", "Abd"),
    "Ionae": ("Ionas", "Ion"), "Michaeae": ("Michaeas", "Mic"),
    "Nahum": ("Nahum", "Nah"), "Habacuc": ("Habacuc", "Hab"),
    "Sophoniae": ("Sophonias", "Soph"), "Aggaei": ("Aggaeus", "Agg"),
    "Zachariae": ("Zacharias", "Zac"), "Malachiae": ("Malachias", "Mal"),
    "Baruch": ("Baruch", "Bar"),
}

ALIAS_FORMULA = {
    "Lectio libri Siracidae": ("Ecclesiasticus", "Sir"),
    "Lectio Cantici canticorum": ("Canticum Canticorum", "Cant"),
    "Lectio libri Lamentationum": ("Lamentationes", "Lam"),
    "Lectio libri Numeri": ("Numeri", "Num"),
    "Lectio libri Tobiae": ("Thobis", "Tob"),
    "Lectio libri primi Machabaeorum": ("I Maccabaeorum", "1 Mac"),
    "Lectio libri secundi Machabaeorum": ("II Maccabaeorum", "2 Mac"),
}
for _gen, _par in _PROFETAS.items():
    ALIAS_FORMULA["Lectio libri %s prophetae" % _gen] = _par

# Como redacta el propio libro la formula, donde difiere de la tabla del
# proyecto. **No se escribe aqui la cadena acentuada entera**: a los profetas
# el acento del genitivo ya se lo pone la fase 13 sobre la tabla del proyecto,
# y rehacerlo aqui a mano seria inventarse acentos (Michaeae, Aggaei, Ionae no
# son obvios). Se guarda solo la **regla**, y la fase 21 la aplica sobre la
# formula ya acentuada que el proyecto tiene.
#
#   "profeta"  -> "Lectio libri <genitivo acentuado> prophetae"
#   una cadena -> esa, tal cual (son las que si son seguras de acentuar)
FORMULA_1977 = {
    "Ecclesiasticus": "Léctio libri Siracídae",
    "Canticum Canticorum": "Léctio Cántici canticórum",
    "Lamentationes": "Léctio libri Lamentatiónum",
    "Numeri": "Léctio libri Númeri",
    "Thobis": "Léctio libri Tobíae",
    "I Maccabaeorum": "Léctio libri primi Machabaeórum",
    "II Maccabaeorum": "Léctio libri secúndi Machabaeórum",
}
for _gen, _par in _PROFETAS.items():
    FORMULA_1977[_par[0]] = "profeta"


def formulas():
    """formula normalizada -> (libro_vulgata, sigla)."""
    out = {}
    with io.open(os.path.join(DATA, "latin_formulas_nova.csv"),
                 encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[plano(r["formula"])] = (r["vulgata"], r["sigla_lat"])
    for k, v in ALIAS_FORMULA.items():
        out[plano(k)] = v
    return out


# --------------------------------------------------------------------------
# los incipits: se reconocen, no se copian
# --------------------------------------------------------------------------
# El OCR escribe `In illo tempore` de tres maneras y `discipulis` de cuatro.
# De modo que del OCR se toma solo **cual** de las formas conocidas es, y lo
# que se guarda es la forma canonica de esta tabla, escrita y acentuada aqui.
# Lo que no case con ninguna no se inventa: se deja sin incipit y se cuenta.
INCIPITS = [
    ("In illo témpore", "inillotempore"),
    ("Fratres", "fratres"),
    ("In diébus illis", "indiebusillis"),
    ("Caríssimi", "carissimi"),
    ("Caríssime", "carissime"),
    ("Dixit Iesus discípulis suis", "dixitiesusdiscipulissuis"),
    ("Locútus est Móyses pópulo dicens", "locutusestmoysespopulodicens"),
    ("Locútus est Dóminus ad Móysen dicens",
     "locutusestdominusadmoysendicens"),
    ("Ait Deus", "aitdeus"),
    ("Dixit Dóminus ad Abram", "dixitdominusadabram"),
    ("Haec dicit Dóminus", "haecdicitdominus"),
    ("In illa hora", "inillahora"),
]


def canoniza_incipit(trozo):
    """Devuelve la forma canonica, o None si no es ninguna de las conocidas."""
    p = plano(trozo)
    if not p:
        return None
    mejor, sc = None, 0.0
    for bueno, clave in INCIPITS:
        r = difflib.SequenceMatcher(None, p, clave).ratio()
        if r > sc:
            mejor, sc = bueno, r
    return mejor if sc >= 0.82 else None


def incipit_de(cuerpo):
    """Los primeros segmentos del cuerpo que sean incipit conocido."""
    trozos = cuerpo.split(":")
    out = []
    for t in trozos[:2]:
        if len(t) > 90:
            break
        c = canoniza_incipit(t)
        if not c:
            break
        out.append(c)
    return ": ".join(out) + ":" if out else ""


# --------------------------------------------------------------------------
# el texto de los tomos
# --------------------------------------------------------------------------
RUIDO = re.compile(r"^[\s\d.,;:'`·•l|!iI\[\]{}()*+\-_~^­]*$")
CITA = re.compile(r"^[\s\d.,;:\-–abcdefgh ]+$")
FIN = re.compile(r"\b(uerbum\s*domini)\b")


def paginas(ruta):
    import fitz
    doc = fitz.open(ruta)
    out = []
    for i in range(len(doc)):
        bruto = re.sub(r"­\s*\n\s*", "", doc[i].get_text())
        out.append((i + 1, [l.rstrip() for l in bruto.split("\n")]))
    doc.close()
    return out


def cabeceras(pags):
    """Los renglones de encabezado que se repiten pagina tras pagina."""
    c = collections.Counter()
    for _, ls in pags:
        for l in ls[:4]:
            s = l.strip()
            if s and not RUIDO.match(s):
                c[s] += 1
    return {s for s, n in c.items() if n >= 4}


def limpia(pags, heads):
    out = []
    for n, ls in pags:
        for i, l in enumerate(ls):
            s = l.strip()
            if not s or (i < 4 and (RUIDO.match(s) or s in heads)):
                continue
            out.append((s, n))
    return out


def _puntua(p, claves):
    mejor, sc = None, 0.0
    for k in claves:
        r = difflib.SequenceMatcher(None, p, k).ratio()
        if r > sc:
            mejor, sc = k, r
    return mejor, sc


def casa_formula(linea, siguiente, tabla, claves):
    """(libro, sigla, score, n_renglones) si el renglon es formula de lectura.

    La formula se parte a veces en dos renglones -'Lectio Epistolae primae
    beati Pauli apostoli / ad Corinthios'-, y entonces el primero solo se
    parece mas a la de Pedro que a la suya. Se prueban las dos.
    """
    p = plano(linea)
    if not (12 <= len(p) <= 80) or "ectio" not in p[:20]:
        return None
    mejor, sc = _puntua(p, claves)
    n = 1
    if siguiente is not None and len(plano(siguiente)) <= 40:
        m2, s2 = _puntua(p + plano(siguiente), claves)
        if s2 > sc:
            mejor, sc, n = m2, s2, 2
    if sc < 0.80:
        return None
    lib, sig = tabla[mejor]
    return lib, sig, round(sc, 3), n


def parse_cita(s, un_capitulo=False):
    """'63, 16 b-17; 64, 1 . 3 b-8' -> [(cap, desde, hasta), ...]

    El margen imprime la cita y el OCR le mete espacios dentro de los numeros
    ('1 1-14') y letras de media linea ('3 b-8'); y hay rangos que saltan de
    capitulo ('3, 12 - 4, 2').
    """
    if not s:
        return []
    s = s.replace("–", "-")
    s = re.sub(r"(?<=\d)\s+(?=\d)", "", s)
    s = re.sub(r"\s*,\s*", ",", s)
    s = re.sub(r"(?<=\d)\s*[a-h]\b", "", s)
    s = re.sub(r"\s*-\s*", "-", s).replace(";", ".")
    segs, cap = [], (1 if un_capitulo else None)
    for it in s.split("."):
        it = it.strip().strip(",").strip()
        if not it or not re.search(r"\d", it):
            continue
        m = re.match(r"^(\d+),(\d+)-(\d+),(\d+)$", it)
        if m:
            c1, v1, c2, v2 = (int(m.group(k)) for k in (1, 2, 3, 4))
            for c in range(c1, c2 + 1):
                segs.append((c, v1 if c == c1 else 1, v2 if c == c2 else 999))
            cap = c2
            continue
        m = re.match(r"^(\d+),(\d+)(?:-(\d+))?$", it)
        if m:
            cap = int(m.group(1))
            d = int(m.group(2))
            segs.append((cap, d, int(m.group(3) or d)))
            continue
        m = re.match(r"^(\d+)(?:-(\d+))?$", it)
        if m and cap is not None:
            d = int(m.group(1))
            segs.append((cap, d, int(m.group(2) or d)))
    return segs


UN_CAP = {"Abdias", "Ad Philemonem", "II Ioannis", "III Ioannis", "Iudae"}


def pericopas(ruta, tomo, tabla, claves):
    pags = paginas(ruta)
    ls = limpia(pags, cabeceras(pags))
    marcas = {}
    for i, (linea, _) in enumerate(ls):
        m = casa_formula(linea, ls[i + 1][0] if i + 1 < len(ls) else None,
                         tabla, claves)
        if m:
            marcas[i] = m
    out = []
    for i0 in sorted(marcas):
        lib, sig, sc, nren = marcas[i0]
        i = i0 + nren - 1
        linea, pag = ls[i0]
        cita, ci = None, None
        for j in list(range(i + 1, min(i + 5, len(ls)))) + [i - 1]:
            s = ls[j][0]
            if CITA.match(s) and re.search(r"\d", s):
                cita, ci = s, j
                break
        ini = (ci + 1) if (ci is not None and ci > i) else (i + 1)
        cuerpo, cerrada = [], False
        for j in range(ini, min(ini + 120, len(ls))):
            if j == ci:
                continue
            s = ls[j][0]
            if FIN.search(plano(s)) or j in marcas:
                cerrada = True
                break
            cuerpo.append(s)
        cuerpo = " ".join(cuerpo)
        segs = parse_cita(cita, lib in UN_CAP)
        out.append({
            "tomo": tomo, "pagina": pag, "libro": lib, "sigla": sig,
            "cita_cruda": cita, "segs": segs, "cerrada": cerrada,
            "formula": FORMULA_1977.get(lib, ""),
            "incipit": incipit_de(cuerpo),
            "n_palabras": len(cuerpo.split()),
        })
    return out


def clave_de(libro, segs):
    return "%s|%s" % (libro, ";".join("%d,%d-%d" % s for s in sorted(segs)))


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tomos", default="1234")
    args = ap.parse_args()

    tabla = formulas()
    claves = list(tabla)
    inf = ["El leccionario latino de 1977 - cosecha de los cuatro tomos", ""]
    todo = []
    for t in args.tomos:
        ruta = os.path.join(TOMOS, PATRON % t)
        if not os.path.exists(ruta):
            inf.append("   FALTA el tomo %s: %s" % (t, ruta))
            continue
        p = pericopas(ruta, t, tabla, claves)
        todo += p
        inf.append("   tomo %s: %4d pericopas  (cerradas %4d, con cita %4d,"
                   " con incipit %4d)"
                   % (t, len(p), sum(x["cerrada"] for x in p),
                      sum(bool(x["segs"]) for x in p),
                      sum(bool(x["incipit"]) for x in p)))

    # el santoral y los comunes salen enteros en los cuatro tomos: se queda
    # la copia con el cuerpo mas largo, que es la menos cortada por el parseo
    porclave = {}
    for x in todo:
        if not x["segs"] or not x["cerrada"]:
            continue
        k = clave_de(x["libro"], x["segs"])
        if k not in porclave or x["n_palabras"] > porclave[k]["n_palabras"]:
            porclave[k] = x
    inf.append("")
    inf.append("   %d pericopas en total -> %d distintas (quitadas %d"
               " repeticiones entre tomos)"
               % (len(todo), len(porclave), len(todo) - len(porclave)))

    porlibro = collections.Counter(x["libro"] for x in porclave.values())
    faltan = sorted({v[0] for v in tabla.values()} - set(porlibro))
    inf.append("   %d libros biblicos representados" % len(porlibro))
    if faltan:
        inf.append("   sin ninguna pericopa: %s" % ", ".join(faltan))

    coni = sum(1 for x in porclave.values() if x["incipit"])
    inf.append("")
    inf.append("   con incipit canonico: %d de %d  (%.1f %%)"
               % (coni, len(porclave), coni * 100.0 / max(1, len(porclave))))
    ci = collections.Counter(x["incipit"] for x in porclave.values()
                             if x["incipit"])
    for k, n in ci.most_common(12):
        inf.append("      %5d  %s" % (n, k))

    salida = sorted(porclave.values(), key=lambda x: (x["libro"], x["segs"]))
    ruta = os.path.join(DATA, "lect1977_pericopas.json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, separators=(",", ":"))
    inf.append("")
    inf.append("escrito data/lect1977_pericopas.json  (%d KB)"
               % (os.path.getsize(ruta) // 1024))

    with open(os.path.join(DATA, "lect1977_qa.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(inf) + "\n")
    print("\n".join(inf))


if __name__ == "__main__":
    main()
