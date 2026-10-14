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
# las comillas latinas salen en cuerpo menor, como los numeros de versiculo,
# y no son ningun signo de la salmodia
COMILLA = re.compile(r"^[«»\"'\u201c\u201d]+$")


def _senas(sp, cuerpo):
    """(cifra al empezar, signo al empezar, signo al acabar) del renglon.

    El libro compone en cuerpo menor dos cosas que no se parecen en nada: el
    **numero de versiculo**, volado en el margen, y los **signos de la
    salmodia** -el ℟ de la respuesta y el ℣ del versiculo-. Del OCR las dos
    salen hechas pure (`11'`, `lji`, `I)!`, `Jli`), de modo que por la letra
    no se reconocen; pero el cuerpo las delata a las dos, y la cifra
    distingue una de la otra: el numero trae digito y el signo no.

    Con eso se sabe donde acaba la respuesta y empieza el salmo, y donde
    acaba cada estrofa, sin leer ni una letra del OCR.
    """
    def chica(s):
        t = s["text"].strip()
        return (bool(t) and len(t) <= 4 and round(s["size"], 1) != cuerpo
                and not COMILLA.match(t))
    ini = sp[0] if chica(sp[0]) else None
    fin = sp[-1] if len(sp) > 1 and chica(sp[-1]) else None
    cifra = bool(ini) and bool(re.search(r"\d", ini["text"]))
    return cifra, bool(ini) and not cifra, bool(fin)


def paginas(ruta):
    """[(n_pagina, [renglon, ...]), ...], y cada renglon con su geometria.

    renglon = (texto, x0, x1, cifra_ini, signo_ini, signo_fin)

    Se lee con `get_text("dict")` y no con `get_text()` para quedarse con la
    caja y el cuerpo de cada trozo: hace falta la caja para distinguir un
    renglon de sentido de uno partido por la medida de la columna, y el
    cuerpo para reconocer los signos de la salmodia. Los renglones que salen
    son los mismos que daba `get_text()` -comprobado pagina por pagina-,
    incluido el guion de renglon, que se junta con el de abajo.
    """
    import fitz
    doc = fitz.open(ruta)
    out = []
    for i in range(len(doc)):
        tam, brutas = collections.Counter(), []
        for b in doc[i].get_text("dict")["blocks"]:
            if b.get("type"):
                continue
            for l in b["lines"]:
                sp = [s for s in l["spans"] if s["text"].strip()]
                if not sp:
                    continue
                for s in sp:
                    tam[round(s["size"], 1)] += len(s["text"].strip())
                t = "".join(s["text"] for s in l["spans"]).rstrip()
                brutas.append((t, sp, l["bbox"]))
        cuerpo = tam.most_common(1)[0][0] if tam else 0.0
        ren = []
        for t, sp, bb in brutas:
            if ren and ren[-1][0].endswith("­"):
                v, s = ren[-1], _senas(sp, cuerpo)
                ren[-1] = (v[0][:-1] + t.lstrip(),) + v[1:5] + (s[2],)
                continue
            ren.append((t, round(bb[0], 1), round(bb[2], 1))
                       + _senas(sp, cuerpo))
        out.append((i + 1, ren))
    doc.close()
    return out


def cabeceras(pags):
    """Los renglones de encabezado que se repiten pagina tras pagina."""
    c = collections.Counter()
    for _, ls in pags:
        for l in ls[:4]:
            s = l[0].strip()
            if s and not RUIDO.match(s):
                c[s] += 1
    return {s for s, n in c.items() if n >= 4}


def limpia(pags, heads):
    """[(texto, pagina, x0, x1, cifra_ini, signo_ini, signo_fin), ...]"""
    out = []
    for n, ls in pags:
        for i, l in enumerate(ls):
            s = l[0].strip()
            if not s or (i < 4 and (RUIDO.match(s) or s in heads)):
                continue
            out.append((s, n) + tuple(l[1:]))
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


# --------------------------------------------------------------------------
# las rubricas del formulario: el salmo y la aclamacion
# --------------------------------------------------------------------------
# El salmo responsorial y la aclamacion antes del evangelio no se presentan
# con una formula -`Lectio libri...`- sino con una rubrica, asi que la
# cosecha de pericopas no los veia. Y son justo las dos piezas que el libro
# imprime **en renglones**, repartidos en estrofas: eso es lo que se viene a
# buscar aqui, porque es formato y no letra, y es lo unico de esta pagina que
# se puede tomar sin copiar el OCR.
ROTULOS = (("salmo", "psalmusresponsorius"),
           ("versus", "versusanteevangelium"),
           ("alleluia", "alleluia"))

# lo que cierra una de esas dos piezas por abajo: la rubrica siguiente
CIERRAN = ("evangelium", "lectioprior", "lectioprima", "lectiosecunda",
           "lectiotertia", "lectioquarta", "epistola", "collecta",
           "superoblata", "postcommunionem", "antadintroitum",
           "antadcommunionem", "ordomissae", "sequentia", "tractus",
           "oratiosuperpopulum", "lectionesutinfra",
           # y el rotulo del dia siguiente, que a veces cae en mitad de la
           # columna y si no se lo tomaria el salmo por un renglon suyo
           "feriasecunda", "feriatertia", "feriaquarta", "feriaquinta",
           "feriasexta", "sabbato", "dominica", "annoprimo", "annosecundo")

# El rotulo del evangelio no cierra nada: es lo que viene **debajo** de la
# aclamacion, y al buscarla hacia arriba hay que pasar por el.
EVANG_ROT = "evangelium"

EVANGELIOS = {"Matthaeus", "Marcus", "Lucas", "Ioannes"}

# cuanto puede faltarle a un renglon para el margen y seguir estando lleno
HOLGURA = 13.0


def rotulo_de(linea, signo=False):
    """"salmo", "alleluia", "versus", o None si el renglon no es rubrica.

    El `Alleluia` de la rubrica y el `R. Alleluia.` que se canta se escriben
    con la misma palabra, y por la letra no hay manera de distinguirlos: lo
    que los separa es que el segundo lleva delante el signo de la respuesta,
    que `paginas()` reconoce por el cuerpo de la letra.
    """
    p = plano(linea)
    if not (5 <= len(p) <= 30):
        return None
    for cual, clave in ROTULOS:
        if difflib.SequenceMatcher(None, p, clave).ratio() >= 0.82:
            return None if (cual == "alleluia" and signo) else cual
    return None


def cierra(linea):
    """Si el renglon es ya la rubrica de la pieza siguiente."""
    p = plano(linea)
    if not (5 <= len(p) <= 30):
        return False
    if FIN.search(p):
        return True
    return any(difflib.SequenceMatcher(None, p, k).ratio() >= 0.85
               for k in CIERRAN)


def _es_signo(tok):
    """Si una palabra suelta tiene pinta de ser el signo de la salmodia.

    El OCR escribe el ℟ de veinte maneras (`11'·`, `lji.`, `I)!.`, `J:!i.`,
    `ê·`, `-`), y todas tienen tres cosas en comun: son cortas, no son
    palabra, y **llevan algo que no es letra ni cifra**. Lo ultimo es lo que
    lo distingue del numero de versiculo, que es solo cifras y en lo demas se
    le parece todo (`11'` contra `11`).
    """
    if not (1 <= len(tok) <= 5) or len(plano(tok)) > 3 or COMILLA.match(tok):
        return False
    return bool(re.search(r"[^0-9A-Za-zÀ-ɏ]", tok))


def signo_al_final(texto):
    """Si el renglon acaba con el signo de la respuesta, visto por la letra.

    El cuerpo de la letra lo dice mejor (`paginas()`), pero no siempre: hay
    paginas donde el signo sale en el mismo cuerpo que el texto. Entonces se
    reconoce por donde esta: **detras del punto final**. Las dos mitades de
    la regla hacen falta: `me.` tiene pinta de signo y no lo es, pero tampoco
    viene detras de ningun punto.
    """
    partes = texto.strip().split()
    if len(partes) < 2 or not _es_signo(partes[-1]):
        return False
    previo = " ".join(partes[:-1]).rstrip()
    return bool(previo) and previo[-1] in ".!?»"


def signo_al_empezar(texto):
    """Si el renglon empieza con el signo de la respuesta."""
    partes = texto.strip().split()
    return bool(partes) and _es_signo(partes[0])


def parece_cita(s):
    """Si el renglon es una cita biblica y nada mas.

    La cita del salmo lleva de propina la referencia de la respuesta -`Ps 88,
    4-5. 16-17. 27 et 29 ( R.: cf. 2 a )`-, de modo que no sirve el `CITA` de
    las pericopas, que no admite letras: aqui se admiten palabras, pero
    cortas y pocas, que es lo que hay en una cita y no en un versiculo.
    """
    s = (s or "").strip()
    if not s or len(s) > 70 or not re.search(r"\d", s):
        return False
    palabras = re.findall(r"[A-Za-zÀ-ɏ]+", s)
    return len(palabras) <= 8 and all(len(w) <= 5 for w in palabras)


def parte_cita_salmo(s):
    """('Ps', 'cf. 2 a', [(cap, desde, hasta), ...]) de la cita del salmo.

    Del parentesis sale la referencia de la respuesta, que este libro da
    siempre y el leccionario del proyecto no siempre. El resto es la cita,
    con dos cosas que `parse_cita` no espera: el `et` con que el libro une
    dos versiculos que no se siguen (`27 et 29`) y las letras de media linea
    de dos en dos (`2 cd-3`).
    """
    s = (s or "").strip()
    resp = ""
    m = re.search(r"\(([^)]*)\)", s)
    if m:
        dentro = m.group(1)
        resp = dentro.split(":", 1)[1].strip() if ":" in dentro else ""
        s = s[:m.start()].strip()
    sig = ""
    m = re.match(r"^\s*((?:[1-4]\s+)?[A-Za-zÀ-ɏ]{1,5})\s+(.*)$", s)
    if m:
        sig, s = re.sub(r"\s+", " ", m.group(1)), m.group(2)
    # Los tramos de la cita son las estrofas del libro, y con eso se
    # comprueba el parseo: `Ps 84, 9 ab-10. 11-12. 13-14` son tres estrofas y
    # tres han de salir. El `et` no abre tramo -`27 et 29` es una estrofa con
    # dos versiculos-, asi que se cuentan antes de deshacerlo.
    tramos = len([x for x in s.split(".") if re.search(r"\d", x)])
    s = re.sub(r"\bet\b", ".", s)
    s = re.sub(r"(?<=\d)\s*[a-h]{2,3}\b", "", s)
    return sig, resp, parse_cita(s), tramos


def parte_rubrica(s):
    """(cita, lo que sigue) cuando los dos van en el mismo renglon.

    Lo corriente es que la cita del salmo ocupe su renglon y la respuesta el
    siguiente, pero no siempre: `Ps 121, 1-2. 3-4 a. 8-9 ( ℟.: cf. 1 ) ℟· In
    domum Domini laetantes ibimus.` va de una sola tirada, y entonces la cita
    no se reconoce porque trae detras un versiculo entero.
    """
    m = re.search(r"\)", s)
    if m and parece_cita(s[:m.end()]):
        return s[:m.end()], s[m.end():].strip()
    return "", s


def margenes(ls):
    """El margen derecho de cada pagina, y el de la mayoria de ellas.

    Hace falta para distinguir un renglon **de sentido** de uno partido por
    la medida: el libro compone el salmo en una columna estrecha, y el
    renglon largo que no le cabe lo pasa abajo con la misma sangria que
    llevaria uno nuevo. Si el de arriba llega al margen, el de abajo es su
    continuacion y no un renglon del salmo.
    """
    por = collections.defaultdict(float)
    for r in ls:
        if len(plano(r[0])) >= 25:
            por[r[1]] = max(por[r[1]], r[3])
    xs = sorted(por.values())
    return por, (xs[len(xs) // 2] if xs else 0.0)


def desenvuelve(trozos, margen):
    """Los renglones de sentido, ya juntos los que la medida habia partido."""
    out = []
    for texto, x1 in trozos:
        if out and out[-1][1] >= margen - HOLGURA:
            out[-1] = (out[-1][0] + " " + texto.lstrip(), x1)
        else:
            out.append((texto, x1))
    return [t for t, _ in out]


def salmo_en(ls, i0, marcas, margen):
    """El salmo responsorial cuya rubrica esta en `i0`.

    Devuelve sus renglones, repartidos en estrofas. Las estrofas las marca el
    propio libro: cada una acaba con el signo de la respuesta. La respuesta
    de arriba se aparta -empieza con ese mismo signo, y lo que va mas
    sangrado debajo es suyo- porque no es parte del salmo, y colarla dentro
    correria un renglon todas las estrofas.
    """
    cita, ci, resto = "", None, ""
    for j in range(i0 + 1, min(i0 + 4, len(ls))):
        s = ls[j][0]
        if parece_cita(s):
            cita, ci = s, j
            break
        c, r = parte_rubrica(s)
        if c:
            cita, ci, resto = c, j, r
            break
    cuerpo = []
    for j in range((ci + 1) if ci is not None else (i0 + 1),
                   min(i0 + 48, len(ls))):
        r = ls[j]
        if j in marcas or rotulo_de(r[0], r[5]) or cierra(r[0]):
            break
        if len(plano(r[0])) < 4:
            continue
        cuerpo.append(r)
    n_resp = 0
    if not resto and cuerpo and (cuerpo[0][5]
                                 or signo_al_empezar(cuerpo[0][0])):
        n_resp = 1
        while n_resp < len(cuerpo) and cuerpo[n_resp][2] > cuerpo[0][2] + 6:
            n_resp += 1
    cuerpo = cuerpo[n_resp:]
    estrofas, actual = [], []
    for r in cuerpo:
        actual.append((r[0], r[3]))
        if r[6] or signo_al_final(r[0]):
            estrofas.append(actual)
            actual = []
    cerrada = not actual
    if actual:
        estrofas.append(actual)
    sig, resp, segs, tramos = parte_cita_salmo(cita)
    return {
        "tomo": None, "tramos": tramos, "pagina": ls[i0][1],
        "cita_cruda": cita, "sigla_cruda": sig, "resp_ref": resp, "segs": segs,
        "n_resp": n_resp + (1 if resto else 0), "cerrada": cerrada,
        "estrofas": [desenvuelve(e, margen) for e in estrofas],
    }


def aclamacion_antes(ls, i_ev, marcas):
    """La aclamacion que el libro imprime delante del evangelio.

    No se busca de arriba abajo sino **desde el evangelio hacia arriba**, que
    es donde esta, y se para en su rubrica. Si la rubrica no aparece no se
    inventa nada: por encima viene el salmo, y tomar sus ultimos renglones
    por el versiculo de la aclamacion seria peor que no traer nada. Por el
    camino se pasa por el rotulo del evangelio y por su titulillo tematico,
    que son de el y no de la aclamacion.

    La forma es lo que de verdad se viene a buscar: en Cuaresma este libro no
    imprime ningun `Alleluia` sino `Versus ante Evangelium`, el versiculo
    solo y sin aclamacion que lo enmarque.
    """
    tramo, forma = [], None
    for j in range(i_ev - 1, max(-1, i_ev - 12), -1):
        r = ls[j]
        if j in marcas or FIN.search(plano(r[0])):
            break
        if difflib.SequenceMatcher(None, plano(r[0]),
                                   EVANG_ROT).ratio() >= 0.85:
            tramo = []          # lo de debajo del rotulo era del evangelio
            continue
        if cierra(r[0]):
            break
        rot = rotulo_de(r[0], r[5])
        if rot in ("alleluia", "versus"):
            forma = rot
            break
        if rot:
            break
        tramo.append(r)
    if forma is None:
        return None
    tramo.reverse()
    cita = ""
    for r in tramo:
        if parece_cita(r[0]):
            cita = r[0]
            break
    sig, _, segs, _n = parte_cita_salmo(cita)
    return {"forma": forma, "cita_cruda": cita, "sigla_cruda": sig,
            "segs": segs, "renglones": len(tramo)}


def pericopas(ruta, tomo, tabla, claves):
    """Lo que el libro decide en un tomo: pericopas y salmos responsoriales.

    La aclamacion no sale por su cuenta: va pegada al evangelio que precede,
    que es lo que la identifica.
    """
    pags = paginas(ruta)
    ls = limpia(pags, cabeceras(pags))
    por_pag, med = margenes(ls)
    marcas = {}
    for i, r in enumerate(ls):
        m = casa_formula(r[0], ls[i + 1][0] if i + 1 < len(ls) else None,
                         tabla, claves)
        if m:
            marcas[i] = m
    out, salmos = [], []
    for i0 in sorted(marcas):
        lib, sig, sc, nren = marcas[i0]
        i = i0 + nren - 1
        pag = ls[i0][1]
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
        x = {
            "tomo": tomo, "pagina": pag, "libro": lib, "sigla": sig,
            "cita_cruda": cita, "segs": segs, "cerrada": cerrada,
            "formula": FORMULA_1977.get(lib, ""),
            "incipit": incipit_de(cuerpo),
            "n_palabras": len(cuerpo.split()),
        }
        if lib in EVANGELIOS:
            acl = aclamacion_antes(ls, i0, marcas)
            if acl:
                x["acl"] = acl
        out.append(x)
    for i0, r in enumerate(ls):
        if rotulo_de(r[0], r[5]) != "salmo":
            continue
        margen = por_pag.get(r[1], med)
        if margen < med - 12:
            margen = med
        s = salmo_en(ls, i0, marcas, margen)
        s["tomo"] = tomo
        salmos.append(s)
    return out, salmos


def clave_de(libro, segs):
    return "%s|%s" % (libro, ";".join("%d,%d-%d" % s for s in sorted(segs)))


def siglas_a_libro():
    """{sigla llana: libro de la Vulgata}, para la cita del salmo.

    La cita de la pericopa no hace falta leerla: el libro ya lo dice la
    formula. La del salmo si, porque el salmo no trae formula, y en esa
    ranura caben tambien los canticos (Is 12, Dan 3, Ex 15, Lc 1).
    """
    out = {}
    with io.open(os.path.join(DATA, "latin_formulas_nova.csv"),
                 encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[plano(r["sigla_lat"])] = r["vulgata"]
    return out


# Lo que el OCR hace con las dos siglas que mas caben en esta ranura: a `Ps`
# le come la s, y la `c` de `Lc` la lee `e`. Son las dos que salen aqui -el
# salmo, y el Magnificat o el Benedictus cuando hacen de salmo-, y por lo
# fuzzy no se recuperan: `p` no se parece a `ps` lo bastante.
ALIAS_SIGLA = {"p": "Psalmi", "le": "Lucas"}


def libro_de_sigla(sig, tabla):
    """El libro de una sigla que ha pasado por el OCR."""
    p = plano(sig)
    if not p:
        return None
    if p in tabla:
        return tabla[p]
    if p in ALIAS_SIGLA:
        return ALIAS_SIGLA[p]
    mejor, sc = None, 0.0
    for k, v in tabla.items():
        r = difflib.SequenceMatcher(None, p, k).ratio()
        if r > sc:
            mejor, sc = v, r
    return mejor if sc >= 0.85 else None


def forma_de(estrofas):
    """La forma de un salmo: cuantos renglones lleva cada estrofa."""
    return tuple(len(e) for e in estrofas)


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tomos", default="1234")
    args = ap.parse_args()

    tabla = formulas()
    claves = list(tabla)
    sig2lib = siglas_a_libro()
    inf = ["El leccionario latino de 1977 - cosecha de los cuatro tomos", ""]
    todo, salmos = [], []
    for t in args.tomos:
        ruta = os.path.join(TOMOS, PATRON % t)
        if not os.path.exists(ruta):
            inf.append("   FALTA el tomo %s: %s" % (t, ruta))
            continue
        p, s = pericopas(ruta, t, tabla, claves)
        todo += p
        salmos += s
        inf.append("   tomo %s: %4d pericopas  (cerradas %4d, con cita %4d,"
                   " con incipit %4d);  %4d salmos,  %4d aclamaciones"
                   % (t, len(p), sum(x["cerrada"] for x in p),
                      sum(bool(x["segs"]) for x in p),
                      sum(bool(x["incipit"]) for x in p), len(s),
                      sum(1 for x in p if x.get("acl"))))

    # el santoral y los comunes salen enteros en los cuatro tomos: se queda
    # la copia con el cuerpo mas largo, que es la menos cortada por el parseo
    porclave, formas = {}, collections.defaultdict(collections.Counter)
    for x in todo:
        if not x["segs"] or not x["cerrada"]:
            continue
        k = clave_de(x["libro"], x["segs"])
        if x.get("acl"):
            formas[k][x["acl"]["forma"]] += 1
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

    # --- la aclamacion: la forma tiene que ser la misma en todas las copias
    # El mismo evangelio se lee en Adviento y en Cuaresma, y entonces la
    # aclamacion que lo precede no es la misma pieza: una trae Alleluia y la
    # otra el Versus ante Evangelium. Al quedarse con una sola copia de cada
    # pericopa se perderia de vista esa diferencia, asi que se mira **antes**
    # de quitar las repeticiones: donde las copias no dicen lo mismo, la
    # aclamacion no se atribuye a nadie.
    con, discorde = 0, 0
    for k, x in porclave.items():
        if not x.get("acl"):
            continue
        if len(formas[k]) > 1:
            del x["acl"]
            discorde += 1
        else:
            con += 1
    inf.append("")
    inf.append("   aclamaciones antes del evangelio: %d pericopas, %d"
               " descartadas porque sus copias no traen la misma forma"
               % (con, discorde))
    cf = collections.Counter(x["acl"]["forma"] for x in porclave.values()
                             if x.get("acl"))
    for k, n in cf.most_common():
        inf.append("      %5d  %s" % (n, k))
    inf.append("      %5d  con cita del versiculo"
               % sum(1 for x in porclave.values()
                     if x.get("acl") and x["acl"]["segs"]))

    # --- el salmo: una sola forma por cita, la que repiten mas copias
    #
    # Lo que decide si un salmo se da por bien leido no es que el parseo no
    # haya protestado, sino que **la cita y las estrofas digan lo mismo**:
    # `Ps 84, 9 ab-10. 11-12. 13-14` son tres estrofas, y si no han salido
    # tres es que algo se ha colado o se ha quedado fuera. Es una
    # comprobacion que se paga sola: donde el OCR pierde un signo o la
    # columna junta dos renglones, la cuenta deja de cuadrar y el salmo se
    # cae, en vez de pasar con una estrofa de mas.
    porsal, fuera = {}, collections.Counter()
    for s in salmos:
        lib = libro_de_sigla(s["sigla_cruda"], sig2lib)
        if not lib or not s["segs"] or not s["tramos"]:
            fuera["sin cita que se pueda leer"] += 1
            continue
        if len(s["estrofas"]) != s["tramos"]:
            fuera["las estrofas no cuadran con la cita"] += 1
            continue
        if signo_al_empezar(s["estrofas"][0][0]):
            fuera["la respuesta se metio en la primera estrofa"] += 1
            continue
        s["libro"] = lib
        porsal.setdefault(clave_de(lib, s["segs"]), []).append(s)
    unicos, dudosos = {}, 0
    for k, xs in porsal.items():
        cuenta = collections.Counter(forma_de(x["estrofas"]) for x in xs)
        buena, n = cuenta.most_common(1)[0]
        uno = next(x for x in xs if forma_de(x["estrofas"]) == buena)
        uno["copias"] = len(xs)
        uno["acuerdo"] = round(n * 1.0 / len(xs), 2)
        if len(cuenta) > 1:
            dudosos += 1
        unicos[k] = uno
    inf.append("")
    inf.append("   %d salmos en total -> %d citas distintas (%d con mas de"
               " una forma entre copias; se queda la de la mayoria)"
               % (len(salmos), len(unicos), dudosos))
    inf.append("      %5d  con la respuesta apartada por su signo"
               % sum(1 for x in unicos.values() if x["n_resp"]))
    inf.append("      %5d  renglones en total, %.2f por estrofa"
               % (sum(sum(forma_de(x["estrofas"])) for x in unicos.values()),
                  sum(sum(forma_de(x["estrofas"])) for x in unicos.values())
                  * 1.0 / max(1, sum(len(x["estrofas"])
                                     for x in unicos.values()))))
    ce = collections.Counter(len(x["estrofas"]) for x in unicos.values())
    inf.append("      estrofas por salmo: %s"
               % ", ".join("%d x%d" % kv for kv in sorted(ce.items())))
    cl = collections.Counter(n for x in unicos.values()
                             for n in forma_de(x["estrofas"]))
    inf.append("      renglones por estrofa: %s"
               % ", ".join("%d x%d" % kv for kv in sorted(cl.items())))
    for k, n in fuera.most_common():
        inf.append("      %5d  descartados: %s" % (n, k))

    salida = {
        "pericopas": sorted(porclave.values(),
                            key=lambda x: (x["libro"], x["segs"])),
        "salmos": sorted(unicos.values(), key=lambda x: (x["libro"],
                                                         x["segs"])),
    }
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
