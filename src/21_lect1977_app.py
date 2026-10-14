"""Fase 21 - `app/datos/lecturas_lect1977.json`: el leccionario de 1977.

La fase 20 cosecho de los cuatro tomos lo que el libro **decide**; esta lo
arma para la app. No trae ni una letra del OCR: cada pieza se copia entera de
`lecturas_clementina.json` o de `lecturas_nova.json` -que el proyecto ya tiene
limpias y acentuadas-, y lo unico que se le anade de la cosecha es el incipit
liturgico y la redaccion de la formula, que no son texto biblico. Del incipit
se recorta lo que el texto ya diga, porque el libro a veces no lo anade sino
que reescribe con el el arranque de la pericopa (ver `recorta_incipit`).

**La regla, que es el hallazgo.** Medidos 5 484 puntos donde la Clementina y
la Nova difieren entre si en una palabra entera, el Misal de 1977 sigue:

    Nuevo Testamento ... la Nova Vulgata   (70,6 % contra 5,2 %)
    Salmos ............ el salterio de la Nova, numerado a la griega
                        (510 salmos contra 22)
    Antiguo Testamento  la Clementina      (82,5 % contra 1,9 %)

No es capricho: la Nova del Nuevo Testamento se publico en 1971 y el salterio
tambien, antes que este Misal; el Antiguo Testamento de la Nova no se cerro
hasta 1979, dos anos despues. De ahi que el libro sea mixto.

La regla se comprobo contra el voto pericopa a pericopa en las 768 pericopas
con dos o mas puntos decisivos: **coincide en el 99,5 %**. Las cuatro que
votan al reves lo hacen por un margen de un punto, dentro del ruido del OCR,
asi que no se les hace caso aparte.

**Lo que esto no es.** No es una transcripcion del libro de 1977: es una
reconstruccion por la regla, y donde el libro trae lectura propia -71 puntos
que no son ni de una ni de otra, como Col 3,12 `mansuetudinem, patientiam`,
una palabra de cada corpus- esta version dira lo que diga el corpus elegido.
Esos puntos estan listados en `Missale/datos/cotejo_1977_residuo.csv`. La
cabecera del fichero lo dice, para que no se tome por lo que no es.

Salida:  app/datos/lecturas_lect1977.json
         data/lect1977_app_qa.txt

Uso:  python src/21_lect1977_app.py
"""

import argparse
import collections
import csv
import difflib
import importlib.util
import io
import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
DATA = os.path.join(RAIZ, "data")
DATOS = os.path.join(RAIZ, "app", "datos")


def modulo(nombre):
    """Importa un script cuyo nombre empieza por un numero."""
    spec = importlib.util.spec_from_file_location(
        "m" + re.sub(r"\W", "", nombre), os.path.join(AQUI, nombre + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FASE20 = modulo("20_lect1977")

NUEVO_TESTAMENTO = {
    "Matthaeus", "Marcus", "Lucas", "Ioannes", "Actus Apostolorum",
    "Ad Romanos", "I Ad Corinthios", "II Ad Corinthios", "Ad Galatas",
    "Ad Ephesios", "Ad Philippenses", "Ad Colossenses",
    "I Ad Thessalonicenses", "II Ad Thessalonicenses", "I Ad Timotheum",
    "II Ad Timotheum", "Ad Titum", "Ad Philemonem", "Ad Hebraeos", "Iacobi",
    "I Petri", "II Petri", "I Ioannis", "II Ioannis", "III Ioannis", "Iudae",
    "Apocalypsis",
}

# La aclamacion, y el rotulo que el libro le pone en Cuaresma. Son dos
# palabras del libro de 1977 y no del OCR: se escriben aqui, como los
# incipits, porque lo que el OCR dice es **cual** de las dos es, no como se
# escribe. El `Alleluia` sin acento del libro se acentua a la manera de la
# app, que es la del resto de la pagina.
ACLAMACION = "Allelúia."
ROTULO_VERSUS = "VERSUS ANTE EVANGELIUM"

TITULO = "Lectionarium Latinum · Missale cum lectionibus, 1977"
CABECERA = (
    "Texto: reconstruido del Missale Romanum cum lectionibus "
    "(Libreria Editrice Vaticana, 1977).\n"
    "El libro de 1977 no se copia: se usa como árbitro. Él decide, "
    "perícopa por perícopa, qué texto latino se lee y cómo empieza; "
    "las letras las ponen la Vulgata Clementina y la Nova Vulgata, que es "
    "de donde el propio Misal las tomaba —la Nova en el Nuevo Testamento "
    "y en los salmos, la Clementina en el Antiguo—. Medido sobre 5 484 "
    "puntos de divergencia entre las dos versiones.\n"
    "Íncipits litúrgicos y fórmulas: del propio Misal de 1977. Donde "
    "el libro no añade el íncipit sino que reescribe con él el arranque "
    "de la perícopa, se recorta lo que el texto ya dice.\n"
    "Salmo responsorial: en renglones y estrofas, como lo imprime el "
    "libro. Los renglones son los del salterio de la Nova Vulgata, que es "
    "el que el Misal compone; cotejados con los suyos perícopa por "
    "perícopa.\n"
    "Aclamación antes del Evangelio: la del propio Misal. En Cuaresma este "
    "libro no imprime ningún Allelúia, sino el versículo solo bajo el "
    "rótulo «Versus ante Evangelium»; fuera de ella, el Allelúia que lo "
    "enmarca. El versículo que se lee es el del leccionario de México, que "
    "es el que tiene al lado su castellano.\n"
    "Estructura: Leccionario de Servicios Koinonía."
)


def siglas_a_libro():
    m = {}
    with io.open(os.path.join(DATA, "latin_formulas_nova.csv"),
                 encoding="utf-8") as f:
        for r in csv.DictReader(f):
            m[r["sigla_lat"]] = r["vulgata"]
    return m


def parte_cita(c):
    """'cf. Ps 121,1-2.4-5 [Ps 122]' -> ('Ps', [(121,1,2),(121,4,5)])"""
    if not c:
        return None, []
    c = re.sub(r"\s*\[[^\]]*\]\s*$", "", c)
    c = re.sub(r"^\s*cf\.\s*", "", c)
    m = re.match(r"^([1-3]\s)?([A-Za-zÀ-ɏ]+)\s*(.*)$", c)
    if not m:
        return None, []
    sigla = ((m.group(1) or "").strip() + " " + m.group(2)).strip()
    return sigla, FASE20.parse_cita(m.group(3))


# Los dos leccionarios del proyecto no escriben el latin igual: la Clementina
# usa `j` y las ligaduras (`Juda`, `ejus`, `caeli` con ae ligada, `quaesumus`
# con ae ligada y acentuada), y la Nova no usa ninguna de las dos (`Iuda`,
# `eius`, `Mattha'eum`). Como cinco de cada seis piezas de esta version salen
# de la Nova, las que salen de la Clementina se pasan a su manera, para que no
# convivan dos ortografias en la misma pagina. El Misal de 1977 escribe `I`
# como la Nova, y la ligadura como la Clementina; se elige la uniformidad.
#
# La `ae` acentuada va con el acento sobre la **a** (`Mattha'eum`), que es
# como la escribe la Nova; no se inventa, se copia de ella.
ORTOGRAFIA = {
    ord("j"): "i", ord("J"): "I",
    0x01FD: "áe", 0x01FC: "Áe",      # ae ligada acentuada
    0x00E6: "ae", 0x00C6: "Ae",                # ae ligada
    0x01FF: "óe",                          # oe ligada acentuada
    0x0153: "oe", 0x0152: "Oe",                # oe ligada
}


def a_la_nova(x):
    """Pasa una pieza de la Clementina a la ortografia de la Nova."""
    if isinstance(x, str):
        return x.translate(ORTOGRAFIA)
    if isinstance(x, list):
        return [a_la_nova(y) for y in x]
    if isinstance(x, dict):
        return {k: a_la_nova(v) for k, v in x.items()}
    return x


# --------------------------------------------------------------------------
# los renglones del salmo
# --------------------------------------------------------------------------
# El Misal de 1977 no imprime el salmo responsorial de corrido sino en
# **renglones**, repartidos en estrofas, como se canta. Las estrofas ya las
# tiene la app, que son los tramos de la cita; los renglones no los tenia.
#
# Y no hacen falta las letras del OCR para ponerlos, porque el renglon del
# salmo no es cosa de este libro: es la esticometria del **salterio de la
# Nova Vulgata**, que es el que este Misal compone (de ahi que los salmos
# vayan con la Nova y no con la Clementina, ver la regla de arriba). El
# proyecto lo tiene ya en `data/nova_vulgata_stichos.json`, con sus
# renglones, de modo que el corte se copia de ahi, letra por letra, y el
# libro de 1977 dice si son los suyos: eso es lo que coteja `main`.
def stichos():
    """El corpus de la Nova Vulgata con sus renglones."""
    return json.load(io.open(os.path.join(DATA, "nova_vulgata_stichos.json"),
                             encoding="utf-8"))


def cap_corpus(c, segs):
    """El capitulo con que el corpus guarda esta pieza.

    El leccionario cita los salmos por el griego y la Nova los imprime por el
    hebreo, asi que el `Ps 121` de la cita es el 122 del corpus; la cita de
    la app ya lo dice entre corchetes, que para eso se puso. Donde el salmo
    griego se parte en dos hebreos -`[Ps 9/10]`- no hay un capitulo solo y no
    se toca nada.
    """
    m = re.search(r"\[([^\]]*)\]", c or "")
    if m:
        nums = re.findall(r"\d+", m.group(1))
        return int(nums[0]) if len(nums) == 1 else None
    return segs[0][0] if segs else None


def en_renglones(sti, libro, cap, vers, texto):
    """El versiculo con los renglones del salterio, o None si no cuadran.

    No se calcula donde cortar: se copia. El texto de la pieza y el del
    salterio son **el mismo** -los dos salen de la Nova Vulgata, uno en un
    parrafo y el otro en sus renglones-, de modo que basta contar letras:
    donde el salterio parte, se parte aqui. Si la cuenta no cuadra no se
    parte nada, que es lo que pasa cuando el versiculo no es el mismo.

    Del versiculo 1 la fase 15 ya ha quitado el epigrafe (`Canticum
    ascensionum.`), que en el salterio es el primer renglon; por eso se le
    quitan renglones por delante hasta que las dos letras coinciden.
    """
    s = (sti.get(libro, {}).get(str(cap), {}) or {}).get(str(vers))
    if not s or "\n" not in s:
        return None
    pa = FASE20.plano(texto)
    trozos = s.split("\n")
    while trozos and FASE20.plano("".join(trozos)) != pa:
        trozos.pop(0)
    if len(trozos) < 2:
        return None
    cortes, n = [], 0
    for t in trozos[:-1]:
        n += len(FASE20.plano(t))
        cortes.append(n)
    lineas, actual, cuenta, i = [], [], 0, 0
    for w in texto.split():
        actual.append(w)
        cuenta += len(FASE20.plano(w))
        if i < len(cortes) and cuenta >= cortes[i]:
            if cuenta > cortes[i]:
                return None        # el corte caeria dentro de una palabra
            lineas.append(" ".join(actual))
            actual, i = [], i + 1
    if actual:
        lineas.append(" ".join(actual))
    return "\n".join(lineas) if len(lineas) == len(trozos) else None


def parecido(a, b):
    """Lo que se parecen dos tiradas de letras, de 0 a 1.

    `autojunk` apagado a proposito: pasadas las 200 letras, difflib da por
    basura las que se repiten mucho -y en latin eso son la e, la i y la t- y
    entonces dos parrafos iguales salen distintos. Aqui se cotejan parrafos
    enteros de salmo, que pasan de las 400 letras.
    """
    return difflib.SequenceMatcher(None, FASE20.plano(a), FASE20.plano(b),
                                   autojunk=False).ratio()


def pela(t):
    """El renglon del libro sin el numero de versiculo ni el signo.

    Los dos van dentro del renglon -el numero volado al empezar, el ℟ de la
    respuesta al acabar la estrofa- y no son texto del salmo: dejarlos
    cotejando hace que un renglon igual parezca distinto.

    El signo se quita con la regla entera de la fase 20, la de las dos
    mitades, y no solo por la pinta: `manus ems.` -que es como el OCR deja
    `manus eius`- tiene toda la pinta de acabar en signo, y lo que acaba es
    el versiculo.
    """
    partes = t.split()
    if len(partes) > 1 and FASE20.signo_al_final(t):
        partes.pop()
    while partes and (not FASE20.plano(partes[0])
                      or re.search(r"\d", partes[0])):
        partes.pop(0)
    return " ".join(partes)


def cortes_de(lineas):
    """Donde corta cada renglon, en letras contadas desde el principio."""
    out, n = [], 0
    for x in lineas[:-1]:
        n += len(x)
        out.append(n)
    return out


def coteja(lineas, salmo77):
    """Que dice el libro de 1977 de los renglones que vamos a publicar.

    No decide nada: los renglones que se publican son los del salterio en
    todo caso, porque son los unicos que estan bien escritos. Lo que aqui se
    mide es si son los que el libro imprime, y la medida es **el corte**: se
    pegan los renglones de los dos lados en una tirada de letras, se casan
    las dos tiradas con lo que se parecen (que no es poco: el OCR cambia
    letras, pero no las quita a puñados), y se mira si donde el salterio
    corta corta tambien el libro.

    De esa cuenta salen tres cosas distintas, que conviene no confundir:

    * **cortes que el libro no hace**: ahi los dos reparten de otro modo, y
      es la unica discrepancia de verdad.
    * **cortes que hace el libro de mas**: su columna tiene 250 puntos de
      medida y el renglon que no le cabe lo pasa abajo, de modo que un verso
      largo le sale en dos. Eso no es otro reparto; en la app, que se lee en
      un telefono, lo vuelve a partir la pantalla.
    * **otros versiculos**: un hueco de mas de doce letras seguidas no lo
      hace el OCR, lo hace el libro al leer medio versiculo donde el
      leccionario de Mexico lee el versiculo entero (`17-18 a`).
    """
    a = [x for x in (FASE20.plano(y) for y in lineas) if x]
    b = [x for x in (FASE20.plano(pela(r)) for e in salmo77["estrofas"]
                     for r in e) if x]
    if not a or not b:
        return "sin renglones que cotejar", 0, 0, 0
    sm = difflib.SequenceMatcher(None, "".join(a), "".join(b), autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal" and max(i2 - i1, j2 - j1) > 12:
            return "el libro escoge otros versiculos", 0, 0, 0
    mapa = {}
    for i, j, n in sm.get_matching_blocks():
        for k in range(n + 1):
            mapa[i + k] = j + k
    ca, cb = cortes_de(a), set(cortes_de(b))
    faltan = 0
    for p in ca:
        q = mapa.get(p)
        if q is None or not any(abs(q - x) <= 2 for x in cb):
            faltan += 1
    sobran = max(0, len(cb) - (len(ca) - faltan))
    if faltan:
        return "el libro corta en otro sitio", len(ca), faltan, sobran
    return (("los mismos renglones" if not sobran
             else "los mismos, con alguno partido por la medida"),
            len(ca), 0, sobran)


# --------------------------------------------------------------------------
# la aclamacion: cual de las dos formas
# --------------------------------------------------------------------------
# El Misal de 1977 imprime la aclamacion de dos maneras, y no son dos modos de
# decir lo mismo: fuera de Cuaresma, el versiculo enmarcado en `Alleluia`; y
# **en Cuaresma ningun Alleluia**, sino el versiculo solo bajo el rotulo
# `Versus ante Evangelium`. La cosecha lo confirma -31 versus, todos en
# formularios de Cuaresma, contra 386 alleluias- y es ademas la regla del
# rito: el Alleluia calla desde el miercoles de Ceniza hasta la Vigilia.
#
# Cual toca lo dice **el tiempo**, no la pericopa, y por eso no basta con lo
# que traiga enganchado el evangelio: el mismo evangelio se lee en dos dias
# de distinto tiempo -Mt 6, 1-6. 16-18 es el miercoles de Ceniza en el libro
# de 1977 y el miercoles de la 11.ª semana del tiempo ordinario en el
# leccionario de Mexico-, y la aclamacion que lo acompaña alli no es la que
# toca aqui. Asi que manda la seccion del indice, que es la del proyecto, y
# el libro queda de testigo donde el indice no decide: los apendices, que no
# son el formulario de un dia sino el repertorio de versiculos del año, y los
# leccionarios VI y VIII, que no son de ningun tiempo -y ahi si acierta el
# libro, que trae el Versus de los escrutinios y de las entregas-.
CUARESMAL = re.compile(r"cuaresma|escrutinio|jueves santo|viernes santo",
                       re.I)

# Los tiempos en que el Alleluia es seguro. El santoral entra: el libro
# imprime `Alleluia` en el propio de los santos aunque la fiesta caiga en
# Cuaresma, porque el santoral es otra seccion y la rubrica de Cuaresma no se
# repite alli.
SIN_CUARESMA = ("TIEMPO DE ADVIENTO", "TIEMPO DE NAVIDAD", "TIEMPO ORDINARIO",
                "SOLEMNIDADES DEL SEÑOR EN EL TIEMPO ORDINARIO",
                "PROPIO DE LOS SANTOS", "COMÚN DE LOS SANTOS",
                "OTROS FORMULARIOS DEL PROPIO DE LOS SANTOS",
                "FORMULARIOS SUELTOS",
                "TRIDUO PASCUAL Y TIEMPO DE PASCUA")


def tiempos():
    """{clave del bloque: "cuaresma" | "alleluia" | None}, segun el indice.

    `None` es «el indice no lo dice», y entonces decide el libro. El indice
    lo acaba de escribir la fase 15, que es quien llama a esta: lo que se lee
    aqui es el mismo que va a ir en la app.
    """
    ruta = os.path.join(DATOS, "indice.json")
    if not os.path.exists(ruta):
        return {}
    ind = json.load(io.open(ruta, encoding="utf-8"))
    out = {}
    for sec in ind["secciones"]:
        for g in sec["g"]:
            for dia in g["d"]:
                rotulo = " · ".join([sec["t"], g.get("t") or "",
                                     dia.get("t") or ""])
                cual = ("cuaresma" if CUARESMAL.search(rotulo)
                        else ("alleluia" if sec["t"] in SIN_CUARESMA
                              else None))
                for b in dia["b"]:
                    out[b["k"]] = cual
    return out


def forma_aclamacion(tiempo, acl):
    """"alleluia", "versus" o None: que aclamacion lleva esta pieza."""
    if tiempo == "cuaresma":
        return "versus"
    if acl:
        # el libro dice Versus en un tiempo que no lo tiene: la pericopa se
        # le ha enganchado por el dia de Cuaresma en que el tambien la lee
        if acl["forma"] == "versus" and tiempo == "alleluia":
            return "alleluia"
        return acl["forma"]
    return "alleluia" if tiempo else None


def rotulo_versus(t):
    """El rotulo de la aclamacion al modo de 1977: en Cuaresma no es Alleluia.

    El rotulo del proyecto trae a veces el numero con que el leccionario
    ordena las opciones (`ALLELUIA 2`) y la marca de la alternativa
    (`ALLELUIA · Vel:`): eso es suyo y se queda, que es lo que distingue una
    opcion de otra. Lo que cambia es la palabra.
    """
    if not t or not re.search(r"alleluia", t, flags=re.I):
        return ROTULO_VERSUS
    return re.sub(r"ALLELUIA", ROTULO_VERSUS, t, flags=re.I)


# --------------------------------------------------------------------------
# el incipit que el texto ya dice
# --------------------------------------------------------------------------
# El Misal de 1977 no siempre *anade* el incipit: a veces **reescribe** con el
# el arranque de la pericopa, para que se entienda suelta. Num 6, 22 dice en
# la Clementina `Locutusque est Dominus ad Moysen, dicens` y el libro lo
# imprime `Locutus est Dominus ad Moysen dicens`; Mt 16, 24 dice `Tunc Iesus
# dixit discipulis suis` y el libro `Dixit Iesus discipulis suis`. Pegar el
# incipit delante de ese texto lo dice dos veces seguidas.
#
# Asi que se le quita al incipit, por el final, el tramo que el texto ya dice.
# Por el final porque el incipit viene en tramos -`In diebus illis: Dixit
# Dominus ad Abram:`- y el que se repite es el ultimo: el marco generico se
# queda.
#
# El umbral esta medido, no elegido. Los tramos que de verdad se repiten
# llegan a 0,70 o mas -39 pasan de 0,85, uno queda en 0,81 y catorce en 0,70:
# `Dixit Iesus discipulis suis` contra `Tunc Iesus dixit discipulis suis`-; el
# primero que *no* se repite esta en 0,62 (`In illo tempore` contra `Ab initio
# autem creaturae masculum et feminam fecit eos`). Entre 0,62 y 0,70 no cae
# ningun caso, y el umbral se pone en ese hueco.
#
# Se recorta el incipit y nunca el texto: cortarle el versiculo seria editar
# la Escritura, que es lo unico que aqui no se toca. Donde el libro reescribe
# sin repetir -`Dixit Iesus discipulis suis` por `Respondit Iesus et dixit
# ei`- se quedan los dos, porque ninguno de los dos es falso.
PARECIDO = 0.68


def recorta_incipit(inc, tramos):
    """El incipit sin los tramos del final que el texto ya dice.

    Devuelve (incipit, cuantos tramos se han ido).
    """
    if not tramos or not tramos[0]:
        return inc, 0
    segs = [x for x in inc.rstrip(":").split(": ") if x]
    texto = FASE20.plano(" ".join(t for _, t in tramos[0]))
    fuera = 0
    while segs:
        p = FASE20.plano(segs[-1])
        if not p:
            segs.pop()
            continue
        hueco = max(3, len(p) // 4)
        r = difflib.SequenceMatcher(None, p, texto[:len(p) + hueco]).ratio()
        if r < PARECIDO:
            break
        segs.pop()
        fuera += 1
    return (": ".join(segs) + ":" if segs else ""), fuera


def formula_1977(libro, base):
    """La formula al modo del libro de 1977, sobre la ya acentuada del proyecto.

    A los profetas el proyecto los presenta `Lectio Prophetiae Ezechielis` o
    `Lectio libri Isaiae`, y el Misal de 1977 `Lectio libri <genitivo>
    prophetae`. El genitivo se toma **acentuado** de la formula del proyecto
    -ultima palabra-, en vez de reescribirlo aqui: asi el acento lo sigue
    poniendo la fase 13 y no se inventa ninguno.
    """
    regla = FASE20.FORMULA_1977.get(libro)
    if not regla:
        return base
    if regla != "profeta":
        return regla
    if not base:
        return base
    gen = base.split()[-1]
    return "Léctio libri %s prophétae" % gen


def main(argv=None):
    # `argv` para que la fase 15 pueda llamarla sin que le lleguen los suyos
    ap = argparse.ArgumentParser()
    ap.parse_args(argv)
    inf = ["El leccionario de 1977 para la app", ""]

    clem = json.load(io.open(os.path.join(DATOS, "lecturas_clementina.json"),
                             encoding="utf-8"))
    nova = json.load(io.open(os.path.join(DATOS, "lecturas_nova.json"),
                             encoding="utf-8"))
    bc, bn = clem["bloques"], nova["bloques"]
    if set(bc) != set(bn):
        inf.append("   AVISO: los dos leccionarios no traen las mismas claves")

    cos = json.load(io.open(os.path.join(DATA, "lect1977_pericopas.json"),
                            encoding="utf-8"))
    exacta, floja = {}, {}
    for p in cos["pericopas"]:
        segs = [tuple(s) for s in p["segs"]]
        exacta[FASE20.clave_de(p["libro"], segs)] = p
        s0 = sorted(segs)[0]
        floja.setdefault((p["libro"], s0[0], s0[1]), p)
    # el salmo se engancha por su propia cita, que es la misma en los dos
    # libros -los dos citan por el griego-, y no por el dia: los renglones
    # son de la seleccion de versiculos, no de la fiesta
    s77 = {FASE20.clave_de(p["libro"], [tuple(s) for s in p["segs"]]): p
           for p in cos["salmos"]}
    sti = stichos()
    tiempo_de = tiempos()
    if not tiempo_de:
        inf.append("   AVISO: sin app/datos/indice.json, la aclamacion se"
                   " queda con lo que diga el libro y nada mas")

    s2l = siglas_a_libro()
    salida = collections.OrderedDict()
    cuenta = collections.Counter()
    veredicto = collections.Counter()
    sin_libro = collections.Counter()
    for clave in bn:
        piezas, p77s = [], []
        for i, pz_n in enumerate(bn[clave]):
            lista_c = bc.get(clave, [])
            pz_c = lista_c[i] if i < len(lista_c) else pz_n
            sigla, segs = parte_cita(pz_n.get("c"))
            libro = s2l.get(sigla)
            if libro is None:
                sin_libro[sigla or "?"] += 1
            if libro == "Psalmi" or libro in NUEVO_TESTAMENTO or libro is None:
                fuente, pz = "nova", dict(pz_n)
            else:
                fuente, pz = "clementina", a_la_nova(dict(pz_c))
                # el rotulo y la cita los pone siempre el mismo lado, para que
                # no se mezclen dos maneras de citar en la misma pagina
                pz["t"], pz["c"] = pz_n["t"], pz_n["c"]
                if "q" in pz_n:
                    pz["q"] = pz_n["q"]
                elif "q" in pz:
                    del pz["q"]
            cuenta[fuente] += 1
            if libro and "f" in pz_n:
                f = formula_1977(libro, pz_n.get("f"))
                if f:
                    pz["f"] = f
                    if f != pz_n.get("f"):
                        cuenta["formula al modo de 1977"] += 1
            p77 = None
            if libro and segs:
                p77 = exacta.get(FASE20.clave_de(libro, segs))
                if p77 is None:
                    s0 = sorted(segs)[0]
                    p77 = floja.get((libro, s0[0], s0[1]))
            if p77 is not None:
                cuenta["enganchada con el libro de 1977"] += 1
                if p77["incipit"] and pz.get("k") == "lectura":
                    inc, fuera = recorta_incipit(p77["incipit"], pz.get("g"))
                    if inc:
                        pz["i"] = inc
                        cuenta["con incipit"] += 1
                    cuenta["tramos de incipit que el texto ya decia"] += fuera
            # --- el salmo, en renglones
            if pz.get("k") == "salmo" and libro:
                pz["g"] = [[list(v) for v in tr] for tr in pz["g"]]
                cap = cap_corpus(pz.get("c"), segs)
                puestos = 0
                for tr in (pz["g"] if cap else []):
                    for v in tr:
                        r = en_renglones(sti, libro, cap, v[0], v[1])
                        if r:
                            v[1] = r
                            puestos += 1
                if puestos:
                    cuenta["versiculos del salmo en renglones"] += puestos
                    cuenta["salmos en renglones"] += 1
                    s = s77.get(FASE20.clave_de(libro, segs))
                    if s:
                        v77, todos, faltan, sobran = coteja(
                            [x for tr in pz["g"] for v in tr
                             for x in v[1].split("\n")], s)
                        veredicto[v77] += 1
                        cuenta["cortes del salterio cotejados"] += todos
                        cuenta["cortes que el libro no hace"] += faltan
                        cuenta["cortes que el libro hace de mas"] += sobran
                    else:
                        veredicto["no esta en el libro de 1977"] += 1
                elif cap:
                    cuenta["salmos que se quedan de corrido"] += 1
            piezas.append(pz)
            p77s.append(p77)
        # --- la aclamacion antes del evangelio
        #
        # La aclamacion no se engancha por su cita -muchas no la llevan, y el
        # Alleluia de este libro y el del leccionario de Mexico no siempre
        # cantan el mismo versiculo- sino **por el evangelio que viene
        # detras**, que es lo que la identifica: la forma de la aclamacion es
        # del dia, y el dia lo dice el evangelio. Por eso se recorre otra vez
        # el formulario, ya armado: hace falta mirar hacia delante.
        for i, pz in enumerate(piezas):
            if pz.get("k") != "aleluya":
                continue
            acl = None
            for j in range(i + 1, len(piezas)):
                if piezas[j].get("k") == "lectura":
                    acl = (p77s[j] or {}).get("acl")
                    break
            forma = forma_aclamacion(tiempo_de.get(clave), acl)
            if acl:
                cuenta["aclamaciones que el libro dice"] += 1
                if acl["forma"] == forma:
                    cuenta["y el tiempo dice lo mismo"] += 1
            if forma == "alleluia":
                pz["r"] = ACLAMACION
                cuenta["aclamaciones con el Alleluia"] += 1
            elif forma == "versus":
                pz["t"] = rotulo_versus(pz.get("t"))
                pz.pop("r", None)
                cuenta["aclamaciones con el Versus ante Evangelium"] += 1
            else:
                cuenta["aclamaciones sin forma (nadie la dice)"] += 1
        salida[clave] = piezas

    total = sum(len(v) for v in salida.values())
    inf.append("   %d bloques, %d piezas" % (len(salida), total))
    for k in ("clementina", "nova", "enganchada con el libro de 1977",
              "con incipit", "tramos de incipit que el texto ya decia",
              "formula al modo de 1977", "salmos en renglones",
              "versiculos del salmo en renglones",
              "salmos que se quedan de corrido",
              "aclamaciones con el Alleluia",
              "aclamaciones con el Versus ante Evangelium",
              "aclamaciones sin forma (nadie la dice)",
              "aclamaciones que el libro dice",
              "y el tiempo dice lo mismo"):
        inf.append("      %5d  %s" % (cuenta[k], k))
    inf.append("      %5d  piezas enganchadas, de %d  (%.1f %%)"
               % (cuenta["enganchada con el libro de 1977"], total,
                  cuenta["enganchada con el libro de 1977"] * 100.0 / total))
    inf.append("")
    inf.append("   los renglones del salmo, cotejados con el libro de 1977:")
    for k, n in veredicto.most_common():
        inf.append("      %5d  %s" % (n, k))
    enel = sum(n for k, n in veredicto.items()
               if k != "no esta en el libro de 1977")
    igual = (veredicto["los mismos renglones"]
             + veredicto["los mismos, con alguno partido por la medida"])
    if enel:
        inf.append("      el reparto del libro en el %.1f %% de los salmos"
                   " que el libro trae (%d de %d)"
                   % (igual * 100.0 / enel, igual, enel))
    tot, nhace = (cuenta["cortes del salterio cotejados"],
                  cuenta["cortes que el libro no hace"])
    inf.append("      %5d  cortes del salterio cotejados, y el libro hace"
               " %d: el %.1f %%"
               % (tot, tot - nhace, (tot - nhace) * 100.0 / max(1, tot)))
    inf.append("      %5d  cortes que el libro no hace"
               % cuenta["cortes que el libro no hace"])
    inf.append("      %5d  cortes que el libro hace de mas, por la medida"
               % cuenta["cortes que el libro hace de mas"])
    if sin_libro:
        inf.append("   siglas sin libro (se quedan con la Nova): %s"
                   % ", ".join("%s x%d" % kv for kv in sin_libro.most_common(8)))

    obj = {"fuente": "lect1977", "titulo": TITULO,
           "cabecera": CABECERA, "cierre": nova["cierre"], "bloques": salida}
    ruta = os.path.join(DATOS, "lecturas_lect1977.json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
    inf.append("")
    inf.append("escrito app/datos/lecturas_lect1977.json  (%d KB)"
               % (os.path.getsize(ruta) // 1024))

    with open(os.path.join(DATA, "lect1977_app_qa.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(inf) + "\n")
    print("\n".join(inf))


if __name__ == "__main__":
    main()
