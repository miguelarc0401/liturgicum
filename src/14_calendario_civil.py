"""Fase 10 - El calendario civil: que dia liturgico le toca a cada fecha.

Hasta aqui el proyecto sabia *que* se lee cada dia del ano liturgico
(data/calendario.json: tiempo > semana > dia), pero no *cuando* cae ese dia en
el calendario de la pared. Para una app que abra por las lecturas de hoy hace
falta justamente eso: fecha civil -> dia del leccionario.

Todo sale de dos fechas que se calculan, no se consultan:

* la **Pascua**, por el computo gregoriano, y de ella cuelgan Ceniza, Cuaresma,
  Semana Santa, el tiempo pascual, Pentecostes y las tres solemnidades del
  Senor que le siguen;
* el **Domingo I de Adviento**, que es el cuarto domingo antes de Navidad, y de
  el cuelgan Adviento, Navidad, Epifania y el Bautismo.

El Tiempo Ordinario no se numera hacia adelante sino **hacia atras**: la semana
34 es siempre la que muere el sabado anterior al Adviento siguiente, y contando
hacia atras desde ahi se sabe en que semana se reanuda el lunes despues de
Pentecostes. Ese es el famoso "salto" (en 2026 se pasa de la 6a a la 8a), y
sale solo de restar; no hay que tabularlo.

Tres cosas dependen del pais y se dejan elegir (`--epifania`, `--ascension`,
`--corpus`). Como cada una afecta a un tramo distinto del ano y los tramos no
se tocan, se emite el calendario base y **tres parches independientes**, en vez
de las ocho combinaciones. Que sean de verdad independientes no se supone: se
comprueba construyendo las ocho y comparandolas (§ comprueba_parches).

Salida:  data/calendario_civil.json   fecha -> dia, con sus parches
         data/calendario_civil_qa.txt  el informe y las comprobaciones

Uso:  python src/14_calendario_civil.py [--desde 2024] [--hasta 2060]
"""

import argparse
import datetime as dt
import json
import os
import re
import unicodedata
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

DIA = dt.timedelta(days=1)
DOW = {"lunes": 1, "martes": 2, "miercoles": 3, "jueves": 4, "viernes": 5,
       "sabado": 6}
NOMBRE_DOW = {v: k for k, v in DOW.items()}
ORD_TEXTO = {"primera": 1, "segunda": 2, "tercera": 3, "cuarta": 4,
             "quinta": 5, "sexta": 6, "septima": 7}
ROMANOS = ["", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
           "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix",
           "xx", "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi", "xxvii",
           "xxviii", "xxix", "xxx", "xxxi", "xxxii", "xxxiii", "xxxiv"]
NUM_ROMANO = {r: i for i, r in enumerate(ROMANOS) if r}

# Las tres opciones que cambian de un pais a otro. El valor por omision es el
# uso mas extendido en Espana y en America Latina: las tres trasladadas al
# domingo (salvo la Epifania en Espana, que es el 6 de enero; de ahi la opcion).
OPCIONES = OrderedDict([
    ("epifania", ("domingo", "6enero")),
    ("ascension", ("domingo", "jueves")),
    ("corpus", ("domingo", "jueves")),
])


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# --------------------------------------------------------------------------
# las dos fechas de las que cuelga todo
# --------------------------------------------------------------------------
def pascua(anio):
    """Domingo de Pascua (computo gregoriano anonimo)."""
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return dt.date(anio, mes, dia + 1)


def adviento1(anio):
    """Domingo I de Adviento del ano civil dado.

    Es el cuarto domingo antes de Navidad. Se ancla en el **domingo anterior a
    la Navidad** (estrictamente anterior: si el 25 cae en domingo, el Domingo
    IV es el 18) y se restan tres semanas.
    """
    nav = dt.date(anio, 12, 25)
    atras = (nav.weekday() + 1) % 7 or 7
    return nav - dt.timedelta(days=atras + 21)


def domingo_ancla(f):
    """El domingo de la semana litúrgica en que cae la fecha (domingo-sábado)."""
    return f - dt.timedelta(days=(f.weekday() + 1) % 7)


def primer_domingo(desde, hasta):
    f = desde
    while f <= hasta:
        if f.weekday() == 6:
            return f
        f += DIA
    return None


def ciclo_de(anio):
    """Ciclo dominical del ano liturgico que TERMINA en ese ano civil."""
    return {1: "A", 2: "B", 0: "C"}[anio % 3]


def ferial_de(anio):
    """Ano ferial (I impares / II pares) del ano liturgico que ahi termina."""
    return "II" if anio % 2 == 0 else "I"


# --------------------------------------------------------------------------
# el ano liturgico, dia a dia
# --------------------------------------------------------------------------
def construye_anio(anio, cfg):
    """{fecha: [clave, ...]} del ano liturgico que termina en el ano civil dado.

    La primera clave de cada fecha es la que manda; las demas son formularios
    alternativos del mismo dia (las cuatro misas de Navidad, la Crismal junto a
    la Cena del Senor, la feria que la solemnidad desplaza).
    """
    y0, y1 = anio - 1, anio
    dias = OrderedDict()

    def pon(fecha, *claves):
        dias.setdefault(fecha, []).extend(claves)

    # ---- Adviento --------------------------------------------------------
    adv1 = adviento1(y0)
    nav = dt.date(y0, 12, 25)
    for n in range(4):
        pon(adv1 + dt.timedelta(days=7 * n), ("adv", "dom", n + 1))
    f = adv1 + DIA
    while f < nav:
        if f.weekday() != 6:
            if f >= dt.date(y0, 12, 17):
                pon(f, ("adv", "dic", f.day))
            else:
                sem = (f - adv1).days // 7 + 1
                pon(f, ("adv", "fer", sem, f.weekday() + 1))
        f += DIA
    pon(dt.date(y0, 12, 24), ("nav", "misa", "vigilia"))

    # ---- Navidad ---------------------------------------------------------
    pon(nav, ("nav", "misa", "dia"), ("nav", "misa", "medianoche"),
        ("nav", "misa", "aurora"))
    # La Sagrada Familia es el domingo dentro de la octava; si no hay domingo
    # entre el 26 y el 31 (pasa cuando la Navidad cae en domingo), el 30.
    sagfam = primer_domingo(dt.date(y0, 12, 26), dt.date(y0, 12, 31)) \
        or dt.date(y0, 12, 30)
    pon(sagfam, ("nav", "sagfam"))
    for k in (29, 30, 31):
        f = dt.date(y0, 12, k)
        if f != sagfam:
            pon(f, ("nav", "dic", k))
    pon(dt.date(y1, 1, 1), ("nav", "mariamadre"))

    if cfg["epifania"] == "6enero":
        epi = dt.date(y1, 1, 6)
    else:
        epi = primer_domingo(dt.date(y1, 1, 2), dt.date(y1, 1, 8))
    dom2 = primer_domingo(dt.date(y1, 1, 2), dt.date(y1, 1, 5))
    if dom2 and dom2 != epi:
        pon(dom2, ("nav", "dom2"))
    f = dt.date(y1, 1, 2)
    while f < epi:
        if f != dom2:
            pon(f, ("nav", "antesepi", f.day))
        f += DIA
    pon(epi, ("nav", "epifania"))
    # Cuando la Epifania se traslada al 7 o al 8, el Bautismo es el lunes
    # siguiente; si no, el domingo siguiente.
    if epi.day >= 7:
        bautismo = epi + DIA
    else:
        bautismo = primer_domingo(epi + DIA, epi + dt.timedelta(days=7))
    f = epi + DIA
    while f < bautismo:
        pon(f, ("nav", "trasepi", (f - epi).days))
        f += DIA
    pon(bautismo, ("nav", "bautismo"))

    # ---- Tiempo Ordinario, primer tramo ----------------------------------
    pas = pascua(y1)
    ceniza = pas - dt.timedelta(days=46)
    ancla_to1 = domingo_ancla(bautismo)
    f = bautismo + DIA
    while f < ceniza:
        sem = (domingo_ancla(f) - ancla_to1).days // 7 + 1
        if f.weekday() == 6:
            pon(f, ("to", "dom", sem))
        else:
            pon(f, ("to", "fer", sem, f.weekday() + 1))
        f += DIA

    # ---- Cuaresma --------------------------------------------------------
    pon(ceniza, ("cua", "ceniza"))
    for n in (1, 2, 3):
        pon(ceniza + dt.timedelta(days=n), ("cua", "trasceniza", n + 3))
    dom1 = pas - dt.timedelta(days=42)
    for sem in range(1, 6):
        dom = dom1 + dt.timedelta(days=7 * (sem - 1))
        pon(dom, ("cua", "dom", sem))
        if sem >= 3:
            pon(dom, ("cua", "libre", sem))
        for dow in range(1, 7):
            pon(dom + dt.timedelta(days=dow), ("cua", "fer", sem, dow))

    # ---- Semana Santa y Triduo ------------------------------------------
    pon(pas - dt.timedelta(days=7), ("san", "ramos"))
    for dow in (1, 2, 3):
        pon(pas - dt.timedelta(days=7 - dow), ("san", "fer", dow))
    pon(pas - dt.timedelta(days=3), ("tri", "cena"), ("san", "crismal"))
    pon(pas - dt.timedelta(days=2), ("tri", "viernes"))
    pon(pas - DIA, ("tri", "vigilia"))
    pon(pas, ("tri", "pascua"))

    # ---- Tiempo pascual --------------------------------------------------
    for dow in range(1, 7):
        pon(pas + dt.timedelta(days=dow), ("pas", "oct", dow))
    asc = pas + dt.timedelta(days=39 if cfg["ascension"] == "jueves" else 42)
    for sem in range(2, 8):
        dom = pas + dt.timedelta(days=7 * (sem - 1))
        if dom == asc:
            pon(dom, ("pas", "ascension"), ("pas", "dom", sem))
        else:
            pon(dom, ("pas", "dom", sem))
        for dow in range(1, 7):
            f = dom + dt.timedelta(days=dow)
            if f == asc:
                pon(f, ("pas", "ascension"), ("pas", "fer", sem, dow))
            else:
                pon(f, ("pas", "fer", sem, dow))
    pent = pas + dt.timedelta(days=49)
    pon(pent, ("pas", "pentecostes"))

    # ---- Tiempo Ordinario, segundo tramo ---------------------------------
    # La numeracion se cuenta hacia atras: la semana 34 muere el sabado
    # anterior al Adviento siguiente.
    adv_sig = adviento1(y1)
    dom34 = adv_sig - dt.timedelta(days=7)
    solemnes = {pent + dt.timedelta(days=7): ("sol", "trinidad"),
                pent + dt.timedelta(days=19): ("sol", "corazon")}
    solemnes[pent + dt.timedelta(
        days=11 if cfg["corpus"] == "jueves" else 14)] = ("sol", "corpus")
    f = pent + DIA
    while f < adv_sig:
        sem = 34 - (dom34 - domingo_ancla(f)).days // 7
        propia = (("to", "dom", sem) if f.weekday() == 6
                  else ("to", "fer", sem, f.weekday() + 1))
        if f in solemnes:
            pon(f, solemnes[f], propia)
        else:
            pon(f, propia)
        f += DIA
    return dias


# --------------------------------------------------------------------------
# el otro lado: que clave le corresponde a cada dia de data/calendario.json
# --------------------------------------------------------------------------
def _dow(p):
    return DOW.get(p)


def clave_de_dia(seccion, grupo, titulo):
    """Lee el nombre de un dia del leccionario y devuelve su clave canonica.

    Las claves son las mismas que emite el calendario; asi las dos mitades se
    encuentran sin que ninguna tenga que conocer los rotulos de la otra.
    """
    s, g, t = norm(seccion), norm(grupo), norm(titulo)
    dias = "lunes|martes|miercoles|jueves|viernes|sabado"

    m = re.match(r"^domingo ([ivx]+) de adviento$", t)
    if m:
        return ("adv", "dom", NUM_ROMANO[m.group(1)])
    m = re.match(r"^(%s) de la (\d+) semana de adviento$" % dias, t)
    if m:
        return ("adv", "fer", int(m.group(2)), _dow(m.group(1)))
    m = re.match(r"^(\d+) de diciembre$", t)
    if m and "adviento" in s:
        return ("adv", "dic", int(m.group(1)))

    if t == "misa de la vigilia":
        return ("nav", "misa", "vigilia")
    if t == "misa de medianoche":
        return ("nav", "misa", "medianoche")
    if t == "misa de la aurora":
        return ("nav", "misa", "aurora")
    if t == "misa del dia":
        return ("nav", "misa", "dia")
    if t.startswith("la sagrada familia"):
        return ("nav", "sagfam")
    m = re.match(r"^(\d+) de diciembre", t)
    if m and "navidad" in s:
        return ("nav", "dic", int(m.group(1)))
    if t.startswith("solemnidad de santa maria"):
        return ("nav", "mariamadre")
    if t == "segundo domingo despues de navidad":
        return ("nav", "dom2")
    if t == "la epifania del senor":
        return ("nav", "epifania")
    m = re.match(r"^(\d+) de enero$", t)
    if m and "antes de la epifania" in g:
        return ("nav", "antesepi", int(m.group(1)))
    m = re.search(r"(%s) despues de epifania$" % dias, t)
    if m and "despues de la epifania" in g:
        return ("nav", "trasepi", _dow(m.group(1)))
    if t == "el bautismo del senor":
        return ("nav", "bautismo")

    if t == "miercoles de ceniza":
        return ("cua", "ceniza")
    m = re.match(r"^(jueves|viernes|sabado) despues de cenizas$", t)
    if m:
        return ("cua", "trasceniza", _dow(m.group(1)))
    m = re.match(r"^domingo ([ivx]+) de cuaresma$", t)
    if m:
        return ("cua", "dom", NUM_ROMANO[m.group(1)])
    m = re.match(r"^(%s) de la (\d+) semana de cuaresma$" % dias, t)
    if m:
        return ("cua", "fer", int(m.group(2)), _dow(m.group(1)))
    if t == "misa de libre eleccion":
        m = re.match(r"^([ivx]+) semana de cuaresma$", g)
        if m:
            return ("cua", "libre", NUM_ROMANO[m.group(1)])

    if t.startswith("domingo de ramos"):
        return ("san", "ramos")
    m = re.match(r"^(lunes|martes|miercoles) santo$", t)
    if m:
        return ("san", "fer", _dow(m.group(1)))
    if "misa crismal" in t:
        return ("san", "crismal")
    if t.startswith("jueves santo de la cena"):
        return ("tri", "cena")
    if t.startswith("viernes santo"):
        return ("tri", "viernes")
    if t.startswith("vigilia pascual"):
        return ("tri", "vigilia")
    if t == "misa del dia de pascua":
        return ("tri", "pascua")

    m = re.match(r"^(%s) de la octava de pascua$" % dias, t)
    if m:
        return ("pas", "oct", _dow(m.group(1)))
    m = re.match(r"^domingo ([ivx]+) de pascua$", t)
    if m:
        return ("pas", "dom", NUM_ROMANO[m.group(1)])
    m = re.match(r"^(%s) de la (\w+) semana de pascua$" % dias, t)
    if m and m.group(2) in ORD_TEXTO:
        return ("pas", "fer", ORD_TEXTO[m.group(2)], _dow(m.group(1)))
    if t == "la ascension del senor":
        return ("pas", "ascension")
    if t == "domingo de pentecostes":
        return ("pas", "pentecostes")

    if "santisima trinidad" in t:
        return ("sol", "trinidad")
    if "cuerpo y sangre" in t:
        return ("sol", "corpus")
    if "sagrado corazon" in t:
        return ("sol", "corazon")

    m = re.match(r"^domingo ([ivx]+) del tiempo ordinario", t)
    if m:
        return ("to", "dom", NUM_ROMANO[m.group(1)])
    m = re.match(r"^(%s) de la (\d+) semana de tiempo ordinario$" % dias, t)
    if m:
        return ("to", "fer", int(m.group(2)), _dow(m.group(1)))
    return None


def indexa_calendario(cal):
    """clave -> dia, leyendo data/calendario.json. Y lo que no se reconoce."""
    por_clave, sin_clave, repetidas = {}, [], []
    for sec in cal["secciones"]:
        for g in sec["grupos"]:
            for d in g["dias"]:
                k = clave_de_dia(sec["titulo"], g.get("titulo") or "",
                                 d["titulo"])
                if k is None:
                    sin_clave.append((sec["titulo"], g.get("titulo"),
                                      d["titulo"]))
                    continue
                if k in por_clave:
                    repetidas.append((k, d["titulo"]))
                    continue
                por_clave[k] = {"slug": d["slug"], "titulo": d["titulo"],
                                "seccion": sec["titulo"],
                                "grupo": g.get("titulo") or "",
                                "bloques": d["bloques"]}
    return por_clave, sin_clave, repetidas


# --------------------------------------------------------------------------
# que formulario de los del dia le toca a este ano
# --------------------------------------------------------------------------
def es_comun(etiqueta):
    return len(re.findall(r"\b[abc]\b", norm(etiqueta))) > 1


def elige_bloque(bloques, ciclo, ferial):
    """Indice del formulario que corresponde al ciclo y al ano feriales dados.

    El orden importa: "Ciclo A" exacto gana a "Ciclos A, B y C", y este a
    "Ciclo A - evangelios alternativos", que es un anadido y no el formulario.
    """
    et = [norm(b["etiqueta"]) for b in bloques]
    for i, e in enumerate(et):
        if e == "ciclo %s" % ciclo.lower():
            return i
    for i, e in enumerate(et):
        if re.match(r"^ano %s\b" % ferial.lower(), e):
            return i
    for i, e in enumerate(et):
        if es_comun(e):
            return i
    for i, e in enumerate(et):
        if e.startswith("ciclo %s" % ciclo.lower()):
            return i
    return 0


# --------------------------------------------------------------------------
# construccion completa, con sus comprobaciones
# --------------------------------------------------------------------------
def fechas_de(anio, cfg, por_clave, faltan):
    """{'YYYY-MM-DD': [[slug, bloque], ...]} de un ano liturgico."""
    ciclo, ferial = ciclo_de(anio), ferial_de(anio)
    salida = OrderedDict()
    for fecha, claves in sorted(construye_anio(anio, cfg).items()):
        entradas = []
        for k in claves:
            dia = por_clave.get(k)
            if dia is None:
                faltan.setdefault(k, []).append(fecha.isoformat())
                continue
            entradas.append([dia["slug"],
                             elige_bloque(dia["bloques"], ciclo, ferial)])
        if entradas:
            salida[fecha.isoformat()] = entradas
    return salida


def variantes(cfg_base):
    """Las tres configuraciones que cambian una sola opcion respecto a la base."""
    for opcion, valores in OPCIONES.items():
        otro = [v for v in valores if v != cfg_base[opcion]][0]
        cfg = dict(cfg_base)
        cfg[opcion] = otro
        yield "%s_%s" % (opcion, otro), opcion, otro, cfg


def comprueba_parches(anios, cfg_base, por_clave):
    """Las tres opciones tocan tramos distintos del ano: hay que demostrarlo.

    Si son de verdad independientes, aplicar los tres parches a la vez tiene
    que dar exactamente el calendario construido con las tres opciones
    cambiadas. Se comprueba sobre los ocho casos y todos los anos.
    """
    fallos = []
    for combo in range(8):
        cfg = dict(cfg_base)
        cambiadas = []
        for bit, (opcion, valores) in enumerate(OPCIONES.items()):
            if combo >> bit & 1:
                cfg[opcion] = [v for v in valores if v != cfg_base[opcion]][0]
                cambiadas.append(opcion)
        for anio in anios:
            basura = {}
            directo = fechas_de(anio, cfg, por_clave, basura)
            montado = dict(fechas_de(anio, cfg_base, por_clave, basura))
            for _, opcion, otro, cfg_v in variantes(cfg_base):
                if opcion not in cambiadas:
                    continue
                v = fechas_de(anio, cfg_v, por_clave, basura)
                base = fechas_de(anio, cfg_base, por_clave, basura)
                for f in set(v) | set(base):
                    if v.get(f) != base.get(f):
                        if f in v:
                            montado[f] = v[f]
                        else:
                            montado.pop(f, None)
            if montado != dict(directo):
                difs = [f for f in set(montado) | set(directo)
                        if montado.get(f) != directo.get(f)]
                fallos.append((anio, "+".join(cambiadas) or "base",
                               sorted(difs)[:5]))
    return fallos


def parche(base, otro):
    """Lo que hay que cambiar en `base` para obtener `otro`. null = quitar."""
    p = OrderedDict()
    for f in sorted(set(base) | set(otro)):
        if base.get(f) != otro.get(f):
            p[f] = otro.get(f)
    return p


# --------------------------------------------------------------------------
# comprobaciones de fechas conocidas
# --------------------------------------------------------------------------
PRUEBAS_PASCUA = {2024: "2024-03-31", 2025: "2025-04-20", 2026: "2026-04-05",
                  2027: "2027-03-28", 2028: "2028-04-16", 2030: "2030-04-21",
                  2033: "2033-04-17", 2038: "2038-04-25"}
PRUEBAS_ADVIENTO = {2022: "2022-11-27", 2023: "2023-12-03", 2024: "2024-12-01",
                    2025: "2025-11-30", 2026: "2026-11-29", 2027: "2027-11-28"}
# dia liturgico esperado en fechas escogidas (con la configuracion por omision)
PRUEBAS_DIA = [
    ("2026-09-28", "Lunes de la 26ª semana de Tiempo Ordinario"),
    ("2026-09-27", "Domingo XXVI del Tiempo Ordinario"),
    ("2025-11-30", "Domingo I de Adviento"),
    ("2025-12-17", "17 de diciembre"),
    ("2025-12-25", "Misa del día"),
    ("2026-01-01", "Solemnidad de Santa María, Madre de Dios"),
    ("2026-02-18", "Miércoles de Ceniza"),
    ("2026-04-05", "Misa del día de Pascua"),
    ("2026-05-24", "Domingo de Pentecostés"),
    ("2026-11-22", "Domingo XXXIV del Tiempo Ordinario: Jesucristo, Rey del universo"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", type=int, default=2024)
    ap.add_argument("--hasta", type=int, default=2060)
    for opcion, valores in OPCIONES.items():
        ap.add_argument("--" + opcion, default=valores[0], choices=valores)
    args = ap.parse_args()
    cfg_base = {o: getattr(args, o) for o in OPCIONES}
    anios = list(range(args.desde, args.hasta + 1))

    cal = json.load(open(os.path.join(DATA, "calendario.json"),
                         encoding="utf-8"))
    por_clave, sin_clave, repetidas = indexa_calendario(cal)

    inf = ["EL CALENDARIO CIVIL: QUE DIA LITURGICO ES CADA FECHA", "",
           "anos liturgicos          : %d-%d (%d)"
           % (anios[0], anios[-1], len(anios)),
           "configuracion base       : %s"
           % ", ".join("%s=%s" % kv for kv in sorted(cfg_base.items())),
           "dias del leccionario     : %d reconocidos, %d sin reconocer"
           % (len(por_clave), len(sin_clave))]
    for s, g, t in sin_clave:
        inf.append("   sin reconocer: %s / %s / %s" % (s, g, t))
    for k, t in repetidas:
        inf.append("   CLAVE REPETIDA: %s -> %s" % (k, t))

    # --- computo ---------------------------------------------------------
    malos = ["%d: %s != %s" % (a, pascua(a).isoformat(), v)
             for a, v in sorted(PRUEBAS_PASCUA.items())
             if pascua(a).isoformat() != v]
    malos += ["%d: %s != %s" % (a, adviento1(a).isoformat(), v)
              for a, v in sorted(PRUEBAS_ADVIENTO.items())
              if adviento1(a).isoformat() != v]
    inf.append("computo (Pascua y Adviento): %s"
               % ("%d comprobaciones, 0 fallos"
                  % (len(PRUEBAS_PASCUA) + len(PRUEBAS_ADVIENTO))
                  if not malos else "FALLOS: " + "; ".join(malos)))

    # --- calendario base y parches ---------------------------------------
    faltan = {}
    base = OrderedDict()
    meta = OrderedDict()
    for anio in anios:
        meta[str(anio)] = {"ciclo": ciclo_de(anio), "ferial": ferial_de(anio),
                           "inicio": adviento1(anio - 1).isoformat(),
                           "pascua": pascua(anio).isoformat()}
        base.update(fechas_de(anio, cfg_base, por_clave, faltan))

    parches = OrderedDict()
    for nombre, opcion, valor, cfg in variantes(cfg_base):
        otro = OrderedDict()
        for anio in anios:
            otro.update(fechas_de(anio, cfg, por_clave, faltan))
        parches[nombre] = {"opcion": opcion, "valor": valor,
                           "fechas": parche(base, otro)}

    inf.append("fechas del calendario base : %d" % len(base))
    for nombre, p in parches.items():
        inf.append("parche %-20s: %d fechas cambian"
                   % (nombre, len(p["fechas"])))

    if faltan:
        inf.append("")
        inf.append("CLAVES QUE EL LECCIONARIO NO TIENE (%d):" % len(faltan))
        for k, fechas in sorted(faltan.items(), key=lambda x: str(x[0])):
            inf.append("   %-34s %d fechas, p.ej. %s"
                       % (str(k), len(fechas), fechas[0]))
    else:
        inf.append("claves sin dia en el leccionario: 0")

    # --- dias del leccionario que ninguna fecha usa -----------------------
    usados = {s for e in base.values() for s, _ in e}
    for p in parches.values():
        usados |= {s for e in p["fechas"].values() if e for s, _ in e}
    ociosos = [d for d in por_clave.values() if d["slug"] not in usados]
    inf.append("dias del leccionario sin ninguna fecha: %d" % len(ociosos))
    for d in ociosos:
        inf.append("   %s" % d["titulo"])

    # --- fechas sin formulario -------------------------------------------
    sin_form = []
    for anio in anios[:3]:
        f = adviento1(anio - 1)
        fin = adviento1(anio)
        while f < fin:
            if f.isoformat() not in base:
                sin_form.append(f.isoformat())
            f += DIA
    inf.append("")
    inf.append("fechas sin formulario en %d-%d: %d (son del propio de los "
               "santos, fuera del alcance de los leccionarios I-IV y VII)"
               % (anios[0], anios[2], len(sin_form)))
    inf.append("   %s" % ", ".join(sin_form[:12]))

    # --- independencia de los parches ------------------------------------
    fallos = comprueba_parches(anios[:6], cfg_base, por_clave)
    inf.append("")
    inf.append("independencia de las tres opciones (8 combinaciones x %d anos):"
               " %s" % (6, "0 fallos" if not fallos
                        else "FALLOS: %r" % fallos[:3]))

    # --- dias conocidos ---------------------------------------------------
    por_slug = {d["slug"]: d for d in por_clave.values()}
    malos = []
    for fecha, esperado in PRUEBAS_DIA:
        e = base.get(fecha)
        obt = por_slug[e[0][0]]["titulo"] if e else "(nada)"
        if obt != esperado:
            malos.append("%s: %s != %s" % (fecha, obt, esperado))
    inf.append("fechas conocidas: %s"
               % ("%d comprobadas, 0 fallos" % len(PRUEBAS_DIA) if not malos
                  else "FALLOS: " + "; ".join(malos)))

    salida = {"config": cfg_base, "opciones": {k: list(v) for k, v
                                               in OPCIONES.items()},
              "rango": [anios[0], anios[-1]], "anios": meta,
              "fechas": base, "parches": parches}
    ruta = os.path.join(DATA, "calendario_civil.json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, separators=(",", ":"))
    inf.append("")
    inf.append("escrito data/calendario_civil.json  (%d KB)"
               % (os.path.getsize(ruta) // 1024))

    with open(os.path.join(DATA, "calendario_civil_qa.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(inf) + "\n")
    print("\n".join(inf))


if __name__ == "__main__":
    main()
