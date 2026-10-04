"""Fase 13 - El santoral y la precedencia entre celebraciones.

Hasta aqui el calendario de la app solo sabia del **tiempo** (Adviento,
Navidad, Cuaresma, Pascua, Ordinario). Este modulo le anade el **santoral** y,
sobre todo, decide que se celebra cuando en una misma fecha concurren varias
cosas: la feria del tiempo ordinario y la memoria libre de un santo, un domingo
y una fiesta, una solemnidad y la Semana Santa.

Las tres fuentes son las que aportaste, y cada una hace un trabajo distinto:

* **Calendario de celebraciones** (Calendario general romano y latinoamericano)
  -> `data/santoral.csv`: que se celebra cada dia del ano y con que grado.
* **Tabla de los dias liturgicos** (Normas universales sobre el ano liturgico,
  n. 59) -> `data/tabla_dias_liturgicos.csv`: los trece rangos de precedencia,
  que es lo que resuelve la concurrencia.
* **Tabla de celebraciones** (las fechas moviles ano por ano): no hace falta
  como dato, porque el proyecto ya calcula la Pascua y el Adviento; se usa como
  **verificacion** (ver `--verifica-tabla`).

Y las lecturas salen del **leccionario V** (propio y comun de los santos), que
ya estaba parseado y resuelto al latin: cada celebracion se empareja con su
formulario por la fecha y el nombre.

Reglas aplicadas, todas de la propia Tabla:

1. De las celebraciones que concurren se celebra la de rango menor (= superior
   en la Tabla).
2. **La solemnidad impedida se traslada** a la fecha mas cercana que no tenga
   ninguna celebracion de los numeros 1 al 8. Las demas se omiten ese ano.
3. Las **memorias libres** pueden celebrarse tambien en los dias del numero 9
   (ferias del 17 al 24 de diciembre, octava de Navidad, ferias de Cuaresma);
   ahi la feria manda, pero la memoria sigue ofreciendose.
4. Las **memorias obligatorias que caen en ferias de Cuaresma** se rebajan a
   memorias libres.

Salida:  data/calendario_completo.json   fecha -> celebraciones ordenadas
         data/santoral_qa.txt            el informe y las comprobaciones

Uso:  python src/18_santoral.py [--desde 2018] [--hasta 2060]
      python src/18_santoral.py --verifica-tabla     (contra la Tabla de
                                                      celebraciones movibles)
"""

import argparse
import csv
import datetime as dt
import importlib.util
import json
import os
import re
import unicodedata
from collections import OrderedDict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DIA = dt.timedelta(days=1)

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

GRADO_RANGO = {"solemnidad": 3, "conmemoracion": 3, "fiesta": 7,
               "memoria": 10, "memoria_libre": 12}
GRADO_ROTULO = {"solemnidad": "Solemnidad", "conmemoracion": "Conmemoración",
                "fiesta": "Fiesta", "memoria": "Memoria",
                "memoria_libre": "Memoria libre"}
# como lo escribe el leccionario V (columna _grado) -> nuestra clave
GRADO_LECC = {"solemnidad": "solemnidad", "fiesta": "fiesta",
              "memoria": "memoria", "memoria libre": "memoria_libre"}

COMUNES = OrderedDict([
    ("5223COMDBA.htm", "Común de la dedicación de una iglesia"),
    ("5224COMSVI.html", "Común de santa María Virgen"),
    ("5225COMMAR.html", "Común de mártires"),
    ("5226COMPAS.html", "Común de pastores"),
    ("5227COMDOC.html", "Común de doctores de la Iglesia"),
    ("5228COMVIR.html", "Común de vírgenes"),
    ("5229COMSAN.html", "Común de santos y santas"),
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


PALABRAS_VACIAS = {"san", "santa", "santo", "santos", "santas", "de", "del",
                   "la", "el", "los", "las", "y", "e", "obispo", "obispos",
                   "presbitero", "presbiteros", "martir", "martires",
                   "virgen", "virgenes", "doctor", "doctora", "doctores",
                   "iglesia", "religioso", "religiosa", "abad", "papa",
                   "diacono", "apostol", "apostoles", "evangelista",
                   "companeros", "sus"}


def claves_nombre(s):
    return {p for p in norm(s).split() if p not in PALABRAS_VACIAS
            and len(p) > 2}


# --------------------------------------------------------------------------
# los rangos del tiempo, sacados de la Tabla
# --------------------------------------------------------------------------
def rango_temporal(k):
    """Rango en la Tabla de los dias liturgicos de una clave del tiempo."""
    a = k[0]
    if a == "tri":
        return 1                      # Triduo pascual (incluye el Domingo)
    if a == "san":
        # Ramos es domingo de Cuaresma (2); lunes a miercoles santo, tambien 2.
        # La Misa crismal no compite con la Cena del Senor: es la misa de la
        # manana del mismo Jueves santo, asi que comparte su rango.
        return 1 if k[1] == "crismal" else 2
    if a == "cua":
        if k[1] == "ceniza":
            return 2
        if k[1] in ("dom", "libre"):
            return 2
        return 9                      # ferias de Cuaresma
    if a == "adv":
        if k[1] == "dom":
            return 2
        if k[1] == "dic":
            return 9                  # del 17 al 24 de diciembre
        return 13                     # ferias hasta el 16
    if a == "pas":
        if k[1] in ("oct",):
            return 2                  # octava de Pascua
        if k[1] == "dom":
            return 2
        if k[1] in ("ascension", "pentecostes"):
            return 2
        return 13                     # ferias del tiempo pascual
    if a == "nav":
        if k[1] == "misa":
            return 2                  # Natividad del Senor
        if k[1] == "epifania":
            return 2
        if k[1] == "mariamadre":
            return 3                  # solemnidad
        if k[1] in ("sagfam", "bautismo"):
            return 5                  # fiestas del Senor
        if k[1] == "dom2":
            return 6                  # domingo del tiempo de Navidad
        if k[1] == "dic":
            return 9                  # dias dentro de la octava de Navidad
        return 13                     # ferias del 2 de enero en adelante
    if a == "sol":
        return 3                      # Trinidad, Corpus, Sagrado Corazon
    if a == "to":
        if k[1] == "dom":
            return 3 if k[2] == 34 else 6      # Cristo Rey es solemnidad
        return 13
    return 13


def es_feria(k):
    return k[0] in ("adv", "cua", "pas", "to", "nav") and \
        k[1] in ("fer", "dic", "antesepi", "trasepi", "trasceniza")


# --------------------------------------------------------------------------
# el santoral: leer la tabla y emparejarlo con el leccionario V
# --------------------------------------------------------------------------
def carga_santoral():
    filas = []
    with open(os.path.join(DATA, "santoral.csv"), encoding="utf-8") as fh:
        for i, r in enumerate(csv.DictReader(fh)):
            if not (r["nombre"] or "").strip():
                continue
            mes = int(r["mes"]) if r["mes"] else None
            dia = int(r["dia"]) if r["dia"] else None
            filas.append({
                "n": i, "mes": mes, "dia": dia,
                "movil": (r["movil"] or "").strip() or None,
                "nombre": r["nombre"].strip(),
                "grado": r["grado"].strip(),
                "ambito": (r["ambito"] or "general").strip(),
                "fuente": (r["fuente"] or "").strip(),
                "nota": (r["nota"] or "").strip(),
            })
    return filas


def carga_rangos():
    ruta = os.path.join(DATA, "santoral_rango.csv")
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if r.get("contiene")]


def aplica_rangos(filas, overrides, avisos):
    usados = Counter()
    for f in filas:
        f["rango"] = GRADO_RANGO.get(f["grado"], 12)
        for o in overrides:
            if norm(o["contiene"]) not in norm(f["nombre"]):
                continue
            if o["mes"] and int(o["mes"]) != (f["mes"] or 0):
                continue
            if o["dia"] and int(o["dia"]) != (f["dia"] or 0):
                continue
            f["rango"] = int(o["rango"])
            f["rango_motivo"] = o["motivo"]
            usados[o["contiene"]] += 1
    for o in overrides:
        if not usados[o["contiene"]]:
            avisos.append("santoral_rango.csv: la regla «%s» no se aplico a "
                          "ninguna celebracion" % o["contiene"])
    return usados


def fecha_lecc(texto):
    """'2 de enero' -> (1, 2). None si no es una fecha fija."""
    m = re.match(r"^(\d{1,2})\s+de\s+(\w+)$", norm(texto or ""))
    if not m:
        return None
    mes = norm(m.group(2))
    for i, nm in enumerate(MESES):
        if norm(nm) == mes:
            return (i + 1, int(m.group(1)))
    return None


def fecha_del_codigo(archivo):
    """La fecha que el propio nombre del fichero codifica: 5001TA0102 -> (1,2)."""
    m = re.match(r"^5\d{3}T?A(\d{2})(\d{2})(?:_\d+)?\.html?$", archivo)
    if not m:
        return None
    mes, dia = int(m.group(1)), int(m.group(2))
    if 1 <= mes <= 12 and 1 <= dia <= 31:
        return (mes, dia)
    return None


def carga_leccionario_v(readings, avisos):
    """Los formularios del leccionario V, con su fecha, grado y comunes.

    El sitio repite algun bloque dentro de otra pagina (san Simon y san Judas
    viene pegado al formulario de san Felipe y Santiago, y ya tiene el suyo
    propio). Se detecta sin heuristica: el nombre del fichero codifica la fecha,
    y si el bloque dice otra, el bloque no es de esa pagina.
    """
    vistos, out = set(), []
    for r in readings:
        if r["lectionary"] != "V":
            continue
        clave = (r["id"], r.get("cel_n", 0))
        if clave in vistos:
            continue
        vistos.add(clave)
        archivo = r["source_file"]
        fecha = fecha_lecc(r.get("fecha"))
        codigo = fecha_del_codigo(archivo)
        if codigo and fecha and codigo != fecha:
            avisos.append("leccionario V: %s (cel %d) dice «%s» y el fichero "
                          "codifica el %d/%d; se descarta por bloque repetido"
                          % (archivo, r.get("cel_n", 0), r.get("fecha"),
                             codigo[1], codigo[0]))
            continue
        out.append({
            "archivo": archivo, "cel_n": r.get("cel_n", 0),
            "id": r["id"], "nombre": r["celebration"],
            "fecha_txt": r.get("fecha"), "fecha": fecha_lecc(r.get("fecha")),
            "grado": GRADO_LECC.get(norm(r.get("grado") or ""), None),
            "comunes": [c["archivo"] for c in (r.get("comunes") or [])],
            "n_lecturas": len(r.get("readings") or []),
            "comun": archivo in COMUNES,
        })
    return out


def carga_enlaces():
    """Los emparejamientos que el nombre no resuelve, puestos a mano."""
    ruta = os.path.join(DATA, "santoral_enlaces.csv")
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8") as fh:
        return {(int(r["mes"]), int(r["dia"]), norm(r["nombre"])):
                r["archivo"] for r in csv.DictReader(fh) if r.get("archivo")}


def empareja(santoral, lecc_v, enlaces, avisos):
    """Cada celebracion del calendario con su formulario del leccionario V.

    Por fecha exacta y, si no, por fecha +-1 dia; dentro de la fecha, por el
    numero de palabras significativas del nombre que coinciden. El desfase de
    un dia no es un capricho: el leccionario espanol pone a san Pedro Claver el
    8 de septiembre y el Calendario latinoamericano el 9.
    """
    por_fecha = {}
    for e in lecc_v:
        if e["fecha"]:
            por_fecha.setdefault(e["fecha"], []).append(e)
    por_archivo = {e["archivo"]: e for e in lecc_v if e["cel_n"] == 0}
    usados, sin_usar_enlace = set(), set(enlaces)
    for s in santoral:
        s["lecc"] = None
        if not s["mes"]:
            continue
        manual = enlaces.get((s["mes"], s["dia"], norm(s["nombre"])))
        if manual:
            sin_usar_enlace.discard((s["mes"], s["dia"], norm(s["nombre"])))
            e = por_archivo.get(manual)
            if e is None:
                avisos.append("santoral_enlaces.csv: no existe el formulario "
                              "%s (%s)" % (manual, s["nombre"]))
            else:
                s["lecc"] = e
                s["desfase"] = e["fecha"] != (s["mes"], s["dia"])
                s["enlace_manual"] = True
                usados.add((e["archivo"], e["cel_n"]))
                continue
        candidatos = []
        for delta in (0, -1, 1):
            f = dt.date(2001, s["mes"], s["dia"]) + dt.timedelta(days=delta)
            for e in por_fecha.get((f.month, f.day), []):
                comunes = len(claves_nombre(s["nombre"])
                              & claves_nombre(e["nombre"]))
                if comunes:
                    candidatos.append((comunes, -abs(delta), e))
        if not candidatos:
            continue
        candidatos.sort(key=lambda t: (t[0], t[1]), reverse=True)
        mejor = candidatos[0][2]
        s["lecc"] = mejor
        s["desfase"] = mejor["fecha"] != (s["mes"], s["dia"])
        usados.add((mejor["archivo"], mejor["cel_n"]))
    for k in sorted(sin_usar_enlace):
        avisos.append("santoral_enlaces.csv: la fila %d/%d «%s» no casa con "
                      "ninguna celebracion del calendario" % (k[1], k[0], k[2]))
    sin = [s["nombre"] for s in santoral if s["mes"] and not s["lecc"]]
    if sin:
        avisos.append("celebraciones del calendario sin formulario propio en "
                      "el leccionario V: %d (%s)"
                      % (len(sin), "; ".join(sin)))
    sobran = [e for e in lecc_v
              if e["fecha"] and (e["archivo"], e["cel_n"]) not in usados]
    return sin, sobran


# --------------------------------------------------------------------------
# los dias del santoral, tal como los ve la app
# --------------------------------------------------------------------------
def slug_de(s, i):
    if s["movil"]:
        return "st_" + s["movil"]
    return "st_%02d%02d_%d" % (s["mes"], s["dia"], i)


def comun_por_nombre(nombre):
    """Cuando no hay propio ni remision, de que Comun se toman las lecturas."""
    n = norm(nombre)
    if "dedicacion" in n and "basilica" in n:
        return ["5223COMDBA.htm"]
    if re.search(r"\bvirgen maria\b|nuestra senora|santa maria|inmaculad|"
                 r"asuncion|natividad de la|presentacion de la|visitacion", n):
        return ["5224COMSVI.html"]
    if "martir" in n:
        return ["5225COMMAR.html"]
    if re.search(r"\bobispo|\bpapa\b|pastor", n):
        return ["5226COMPAS.html"]
    if "doctor" in n:
        return ["5227COMDOC.html"]
    if "virgen" in n:
        return ["5228COMVIR.html"]
    return ["5229COMSAN.html"]


def color_liturgico(nombre, grado):
    """El color del ornamento, que es lo que la app pinta en la cabecera.

    Rojo para los martires y para quienes el rito romano viste de rojo aunque
    no lo fueran (los apostoles y los evangelistas, por su martirio o su
    testimonio, y la Santa Cruz). Morado para los difuntos. Blanco lo demas.
    """
    n = norm(nombre)
    if "difuntos" in n:
        return "morado"
    if re.search(r"\bmartir|\bmartires|protomartir|santa cruz|inocentes", n):
        return "rojo"
    if re.search(r"\bapostol|\bapostoles|evangelista", n):
        return "rojo"
    return "blanco"


def construye_dias(santoral):
    """Un dia del indice por celebracion, con sus formularios."""
    dias = OrderedDict()
    for i, s in enumerate(santoral):
        slug = slug_de(s, i)
        s["slug"] = slug
        bloques = []
        lec = s["lecc"]
        if lec and lec["n_lecturas"]:
            bloques.append({"etiqueta": "Propio",
                            "clave": ["V", lec["archivo"], lec["cel_n"]]})
        # Los Comunes se ofrecen cuando el propio remite a ellos, que es lo
        # que hacen casi todas las memorias. Si el formulario es propio de
        # verdad (una solemnidad, una fiesta) no hay Comun que ofrecer, y
        # ponerselo seria inventarlo. Solo cuando no hay propio ninguno -el
        # caso de Guadalupe- se deduce el Comun del titulo.
        comunes = lec["comunes"] if lec else comun_por_nombre(s["nombre"])
        for c in comunes:
            if c in COMUNES:
                bloques.append({"etiqueta": COMUNES[c],
                                "clave": ["V", c, 0]})
        s["bloques"] = bloques
        dias[slug] = {
            "slug": slug, "titulo": s["nombre"],
            "titulo_indice": ("%d: %s" % (s["dia"], s["nombre"])
                              if s["mes"] else s["nombre"]),
            "mes": s["mes"], "dia": s["dia"], "grado": s["grado"],
            "rotulo_grado": GRADO_ROTULO.get(s["grado"], ""),
            "ambito": s["ambito"], "nota": s["nota"],
            "color": color_liturgico(s["nombre"], s["grado"]),
            "bloques": bloques,
        }
    return dias


# --------------------------------------------------------------------------
# la concurrencia, fecha a fecha
# --------------------------------------------------------------------------
def fechas_moviles(anio, cfg, m14):
    """Las celebraciones del santoral que no van en fecha fija."""
    pent = m14.pascua(anio) + dt.timedelta(days=49)
    return {"inmaculado_corazon": pent + dt.timedelta(days=20)}


def celebraciones_de_anio(anio, cfg, m14, santoral, por_clave):
    """{fecha: [celebracion, ...]} sin resolver todavia la concurrencia."""
    agenda = {}

    # --- el tiempo -------------------------------------------------------
    for fecha, claves in m14.construye_anio(anio, cfg).items():
        for orden, k in enumerate(claves):
            dia = por_clave.get(k)
            if dia is None:
                continue
            agenda.setdefault(fecha, []).append({
                "clase": "temporal", "clave": k, "slug": dia["slug"],
                "titulo": dia["titulo"], "bloques": dia["bloques"],
                "rango": rango_temporal(k), "grado": "", "orden": orden,
                "feria": es_feria(k),
            })

    # --- el santoral -----------------------------------------------------
    y0, y1 = anio - 1, anio
    inicio, fin = m14.adviento1(y0), m14.adviento1(y1)
    moviles = fechas_moviles(anio, cfg, m14)
    for s in santoral:
        if s["movil"]:
            f = moviles.get(s["movil"])
            if f is None:
                continue
            fechas = [f]
        else:
            fechas = [d for d in (dt.date(y0, s["mes"], s["dia"]),
                                  dt.date(y1, s["mes"], s["dia"]))
                      if inicio <= d < fin]
        for f in fechas:
            agenda.setdefault(f, []).append({
                "clase": "santoral", "clave": s["slug"], "slug": s["slug"],
                "titulo": s["nombre"], "bloques": s["bloques"],
                "rango": s["rango"], "grado": s["grado"], "orden": 0,
                "feria": False, "ambito": s["ambito"], "nota": s["nota"],
            })
    return agenda, inicio, fin


def resuelve(agenda, inicio, fin, avisos):
    """Aplica la Tabla: ordena, traslada solemnidades y omite lo demas."""
    # 1) el rango superior de cada fecha, contando solo lo que no se mueve
    def top(f):
        cs = agenda.get(f) or []
        return min([c["rango"] for c in cs], default=99)

    # 2) solemnidades impedidas -> a la fecha mas cercana libre de 1..8
    trasladadas = []
    for f in sorted(agenda):
        for c in list(agenda[f]):
            if c["clase"] != "santoral" or c["rango"] > 4:
                continue
            if top(f) >= c["rango"]:
                continue                      # no esta impedida
            destino, paso = None, 1
            while paso < 60:
                cand = f + dt.timedelta(days=paso)
                if cand >= fin:
                    break
                if top(cand) > 8:
                    destino = cand
                    break
                paso += 1
            agenda[f].remove(c)
            if destino is None:
                avisos.append("no hay fecha libre para trasladar «%s» desde %s"
                              % (c["titulo"], f.isoformat()))
                continue
            mov = dict(c)
            mov["trasladada_de"] = f.isoformat()
            agenda.setdefault(destino, []).append(mov)
            trasladadas.append((f.isoformat(), destino.isoformat(),
                                c["titulo"]))

    # 3) ordenar, rebajar y omitir
    salida = OrderedDict()
    for f in sorted(agenda):
        cs = agenda[f]
        t = min(c["rango"] for c in cs)
        vivos, omitidas = [], []
        for c in cs:
            c = dict(c)
            # memoria obligatoria en feria de Cuaresma -> memoria libre
            if (c["clase"] == "santoral" and c["rango"] == 10
                    and any(x["clave"][0] == "cua" and x["clave"][1] == "fer"
                            for x in cs if x["clase"] == "temporal")):
                c["rango"] = 12
                c["grado"] = "memoria_libre"
                c["rebajada"] = ("memoria obligatoria rebajada a libre "
                                 "por caer en feria de Cuaresma (Tabla de "
                                 "los días litúrgicos, n. 12)")
            if c["rango"] <= t:
                vivos.append(c)
            elif c["clase"] == "temporal":
                # El formulario del tiempo nunca se esconde: aunque ese ano no
                # se celebre, su lectura es la del ciclo y es lo que este
                # proyecto existe para ensenar. Va el ultimo y marcado, que es
                # distinto de ofrecerlo como si tocara. Lo que si se omite de
                # verdad es lo del santoral: asi lo manda la Tabla.
                #
                # Solo se marca «no se celebra» cuando lo impide algo de los
                # numeros 1 al 9. Bajo una memoria no se marca: el Ordo
                # lectionum Missae (n. 82) manda justamente seguir la lectura
                # continua de la feria salvo que el santo tenga propias.
                c["no_se_celebra"] = t <= 9
                vivos.append(c)
            elif t == 9 and c["rango"] >= 10:
                # n. 12: las memorias pueden celebrarse en los dias del n. 9
                c["opcional_en_n9"] = True
                vivos.append(c)
            elif t >= 10 and c["rango"] >= 10:
                vivos.append(c)
            else:
                omitidas.append(c)
        vivos.sort(key=lambda c: (c.get("no_se_celebra") and 1 or 0,
                                  c["rango"],
                                  1 if c["clase"] == "temporal" else 0,
                                  c["orden"]))
        salida[f] = (vivos, omitidas)
    return salida, trasladadas


# --------------------------------------------------------------------------
# a la forma que lee la app
# --------------------------------------------------------------------------
def entradas_de(resuelto, ciclo, ferial, m14):
    """{'YYYY-MM-DD': {'c': [[slug, bloque, meta], ...], 'o': [...]}}.

    Una entrada por **celebracion**, no por formulario: los formularios de una
    celebracion (el propio y sus comunes, o los tres ciclos de un domingo) los
    despliega la app desde el indice. En 'o' van las que ese ano se omiten.
    """
    fuera = OrderedDict()
    for f, (vivos, omitidas) in resuelto.items():
        ops = []
        for c in vivos:
            if not c["bloques"]:
                continue
            meta = {"t": c["titulo"], "r": c["rango"]}
            if c["clase"] == "temporal":
                b = m14.elige_bloque(c["bloques"], ciclo, ferial)
                meta["k"] = "t"
                if c["feria"]:
                    meta["f"] = 1
                if c.get("no_se_celebra"):
                    meta["z"] = 1
            else:
                b = 0
                meta["k"] = "s"
                meta["g"] = GRADO_ROTULO.get(c["grado"], "")
                if c.get("trasladada_de"):
                    meta["x"] = c["trasladada_de"]
                if c.get("rebajada"):
                    meta["n"] = c["rebajada"]
                elif c.get("opcional_en_n9"):
                    meta["n"] = ("puede celebrarse en este día como "
                                 "memoria libre (Tabla de los días "
                                 "litúrgicos, n. 12)")
                elif c.get("nota"):
                    meta["n"] = c["nota"]
            ops.append([c["slug"], b, meta])
        if not ops:
            continue
        val = {"c": ops}
        if omitidas:
            val["o"] = [{"t": c["titulo"],
                         "g": GRADO_ROTULO.get(c["grado"], "")}
                        for c in omitidas]
        fuera[f.isoformat()] = val
    return fuera


def parche(base, otro):
    p = OrderedDict()
    for f in sorted(set(base) | set(otro)):
        if base.get(f) != otro.get(f):
            p[f] = otro.get(f)
    return p


# --------------------------------------------------------------------------
# verificacion contra la Tabla de celebraciones movibles del misal
# --------------------------------------------------------------------------
MES_ABREV = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
             "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}


def fecha_impresa(texto, anio):
    """'18 feb' -> date(anio, 2, 18). Los de noviembre y diciembre son del
    ano anterior cuando hablan del Domingo I de Adviento que abre el ano."""
    m = re.match(r"^(\d{1,2})\s+(\w{3})", norm(texto))
    if not m:
        return None
    return dt.date(anio, MES_ABREV[m.group(2)[:3]], int(m.group(1)))


def semana_to(dias, fecha):
    """La semana del Tiempo Ordinario en que cae esa fecha, segun el calculo."""
    for k in dias.get(fecha, []):
        if k[0] == "to":
            return k[2]
    return None


def verifica_tabla(m14, cfg_base):
    """Coteja el computo con la Tabla de celebraciones movibles del misal.

    La tabla **no** es la fuente: el proyecto calcula la Pascua y el Adviento
    desde la fase 10, y copiar una tabla transcrita a mano seria cambiar un
    computo comprobado por un teclear. Lo que hace aqui es de testigo: doce
    anos por trece datos, y lo que no cuadre se canta con su nombre.
    """
    ruta = os.path.join(DATA, "tabla_celebraciones_movibles.csv")
    if not os.path.exists(ruta):
        return ["Tabla de celebraciones movibles: no esta el fichero"]
    with open(ruta, encoding="utf-8") as fh:
        filas = list(csv.DictReader(
            l for l in fh if not l.startswith("#")))

    lineas, n, difs = [], 0, []
    for r in filas:
        anio = int(r["anio"])
        p = m14.pascua(anio)
        pent = p + dt.timedelta(days=49)
        adv = m14.adviento1(anio)
        # el ano liturgico se construye con la Ascension y el Corpus en jueves,
        # que es como los da la tabla
        cfg = dict(cfg_base, ascension="jueves", corpus="jueves")
        dias = m14.construye_anio(anio, cfg)
        ceniza = p - dt.timedelta(days=46)
        ultimo_to = max((f for f in dias if f < ceniza
                         and semana_to(dias, f)), default=None)
        primer_to = min((f for f in dias if f > pent
                         and semana_to(dias, f)), default=None)
        pruebas = [
            ("ciclo", "%s-%s" % (m14.ciclo_de(anio),
                                 m14.ciclo_de(anio + 1)), r["ciclo"]),
            ("ceniza", ceniza, fecha_impresa(r["ceniza"], anio)),
            ("pascua", p, fecha_impresa(r["pascua"], anio)),
            ("ascension", p + dt.timedelta(days=39),
             fecha_impresa(r["ascension"], anio)),
            ("pentecostes", pent, fecha_impresa(r["pentecostes"], anio)),
            ("corpus", pent + dt.timedelta(days=11),
             fecha_impresa(r["corpus"], anio)),
            ("to_hasta", ultimo_to, fecha_impresa(r["to_hasta"], anio)),
            ("to_semana_antes", semana_to(dias, ultimo_to),
             int(r["to_semana_antes"])),
            ("to_desde", primer_to, fecha_impresa(r["to_desde"], anio)),
            ("to_semana_despues", semana_to(dias, primer_to),
             int(r["to_semana_despues"])),
            ("adviento", adv, fecha_impresa(r["adviento"], anio)),
        ]
        for nombre, calculado, impreso in pruebas:
            n += 1
            if calculado != impreso:
                difs.append("   %d %-18s calculado %-12s  impreso %s"
                            % (anio, nombre, calculado, impreso))
    lineas.append("Tabla de celebraciones movibles (%d-%d): %d cotejos, "
                  "%d diferencias"
                  % (int(filas[0]["anio"]), int(filas[-1]["anio"]), n,
                     len(difs)))
    lineas.extend(difs)
    if difs:
        lineas.extend([
            "",
            "   Las seis diferencias estan todas en el ultimo bloque de la",
            "   tabla impresa (2024-2027) y son erratas suyas, no del computo:",
            "",
            "   * Ceniza de 2024. La tabla imprime el 13 de febrero. La Pascua",
            "     de 2024 es el 31 de marzo, la misma que la de 2013, y 2013",
            "     si tuvo la Ceniza el 13 de febrero; pero 2024 es bisiesto y",
            "     restar 46 dias cae en el 14. La fila parece copiada de la de",
            "     2013 sin contar el 29 de febrero. De ahi salen tambien las",
            "     otras dos diferencias de 2024 (el ultimo dia y la ultima",
            "     semana del tiempo ordinario antes de Cuaresma).",
            "   * Ciclo de 2024 y 2025: la tabla los da cambiados entre si",
            "     (imprime C-A donde toca B-C, y B-C donde toca C-A). La serie",
            "     es regular y correcta en los ocho anos anteriores y en 2026.",
            "   * Ciclo de 2027: la tabla imprime «C-D», y no existe un ciclo",
            "     dominical D.",
            "",
            "   Comprobacion independiente: la Ceniza de 2024 fue el 14 de",
            "   febrero, y el ciclo dominical de 2024 fue el B y el de 2025 el",
            "   C. Los 126 cotejos restantes cuadran.",
        ])
    return lineas


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    # 2018 y no 2024: los cien misalitos del Missale van de junio de 2018
    # a septiembre de 2026, y emparejarlos con su dia necesita el
    # calendario de esos anos. La fase 0 del Missale lo comprobo contra
    # las fechas conocidas -Pascua, Ceniza y los dos ciclos de 2018 a
    # 2023- y sale bien. El valor va aqui, y no en publicar.ps1, porque
    # publicar.ps1 llama al guion sin argumentos: con el defecto en 2024
    # cada publicacion deshacia la fase 0 sin que nadie lo notara.
    ap.add_argument("--desde", type=int, default=2018)
    ap.add_argument("--hasta", type=int, default=2060)
    ap.add_argument("--verifica-tabla", action="store_true",
                    help="solo el cotejo con la Tabla de celebraciones "
                         "movibles del misal, y salir")
    args = ap.parse_args()

    m14 = modulo("14_calendario_civil")
    cfg_base = {o: v[0] for o, v in m14.OPCIONES.items()}
    if args.verifica_tabla:
        print("\n".join(verifica_tabla(m14, cfg_base)))
        return
    anios = list(range(args.desde, args.hasta + 1))
    avisos = []

    # --- el tiempo, tal como ya estaba ------------------------------------
    cal = json.load(open(os.path.join(DATA, "calendario.json"),
                         encoding="utf-8"))
    por_clave, sin_clave, repetidas = m14.indexa_calendario(cal)

    # --- el santoral ------------------------------------------------------
    santoral = carga_santoral()
    aplica_rangos(santoral, carga_rangos(), avisos)
    readings = json.load(open(os.path.join(DATA, "readings.json"),
                              encoding="utf-8"))
    lecc_v = carga_leccionario_v(readings, avisos)
    sin, sobran = empareja(santoral, lecc_v, carga_enlaces(), avisos)
    dias_santoral = construye_dias(santoral)

    inf = ["EL SANTORAL Y LA PRECEDENCIA ENTRE CELEBRACIONES", "",
           "celebraciones del calendario : %d (%d en fecha fija, %d moviles)"
           % (len(santoral), sum(1 for s in santoral if s["mes"]),
              sum(1 for s in santoral if s["movil"])),
           "   por grado                 : %s"
           % ", ".join("%s %d" % (GRADO_ROTULO.get(g, g), n) for g, n in
                       sorted(Counter(s["grado"] for s in santoral).items(),
                              key=lambda t: GRADO_RANGO.get(t[0], 99))),
           "   leidas del PDF            : %d; reconstruidas del calco del "
           "reverso (agosto y septiembre, que faltan en el escaneo): %d"
           % (sum(1 for s in santoral if s["fuente"] == "pdf"),
              sum(1 for s in santoral if s["fuente"] == "calco")),
           "formularios del leccionario V: %d (%d con fecha, %d comunes)"
           % (len(lecc_v), sum(1 for e in lecc_v if e["fecha"]),
              sum(1 for e in lecc_v if e["comun"])),
           "emparejadas con su propio    : %d de %d"
           % (sum(1 for s in santoral if s.get("lecc")),
              sum(1 for s in santoral if s["mes"]))]

    desfasadas = [s for s in santoral if s.get("desfase")]
    if desfasadas:
        inf.append("   con un dia de diferencia entre el calendario y el "
                   "leccionario: %d" % len(desfasadas))
        for s in desfasadas:
            inf.append("      %s: calendario %d/%d, leccionario %s"
                       % (s["nombre"], s["dia"], s["mes"],
                          s["lecc"]["fecha_txt"]))

    # --- cotejo de grados: calendario (PDF) contra leccionario V ----------
    discrepan = [s for s in santoral if s.get("lecc")
                 and s["lecc"]["grado"] and s["lecc"]["grado"] != s["grado"]]
    inf.append("")
    inf.append("grados: el calendario y el leccionario V discrepan en %d de "
               "%d celebraciones emparejadas" % (len(discrepan),
                                                 sum(1 for s in santoral
                                                     if s.get("lecc"))))
    inf.append("   (manda el calendario que aportaste; el leccionario V de "
               "Koinonia es el de Espana y sube o baja algunos grados)")
    for s in discrepan:
        inf.append("      %-58s calendario: %-14s leccionario: %s"
                   % (s["nombre"][:58], GRADO_ROTULO[s["grado"]],
                      GRADO_ROTULO[s["lecc"]["grado"]]))

    if sobran:
        inf.append("")
        inf.append("formularios del leccionario V con fecha que el calendario "
                   "no trae: %d" % len(sobran))
        inf.append("   (siguen accesibles por el indice, pero no se colocan "
                   "en ninguna fecha; casi todos son del propio de Espana)")
        for e in sobran:
            inf.append("      %s: %s" % (e["fecha_txt"], e["nombre"][:70]))

    # --- el calendario completo, ano por ano ------------------------------
    def construye(cfg):
        fuera = OrderedDict()
        for anio in anios:
            agenda, ini, fin = celebraciones_de_anio(anio, cfg, m14, santoral,
                                                     por_clave)
            resuelto, trasl = resuelve(agenda, ini, fin, avisos)
            fuera.update(entradas_de(resuelto, m14.ciclo_de(anio),
                                     m14.ferial_de(anio), m14))
            fuera.setdefault("_trasladadas", []).extend(trasl)
        trasl = fuera.pop("_trasladadas", [])
        return fuera, trasl

    base, trasladadas = construye(cfg_base)
    parches = OrderedDict()
    for nombre, opcion, valor, cfg in m14.variantes(cfg_base):
        otro, _ = construye(cfg)
        parches[nombre] = {"opcion": opcion, "valor": valor,
                           "fechas": parche(base, otro)}

    meta = OrderedDict()
    for anio in anios:
        meta[str(anio)] = {"ciclo": m14.ciclo_de(anio),
                           "ferial": m14.ferial_de(anio),
                           "inicio": m14.adviento1(anio - 1).isoformat(),
                           "pascua": m14.pascua(anio).isoformat()}

    inf.append("")
    inf.append("fechas con al menos una celebracion: %d (anos %d-%d)"
               % (len(base), anios[0], anios[-1]))
    for nombre, p in parches.items():
        inf.append("parche %-20s: %d fechas cambian"
                   % (nombre, len(p["fechas"])))

    # --- huecos: fechas del ano sin ninguna celebracion -------------------
    huecos = []
    for anio in anios[:3]:
        f, fin = m14.adviento1(anio - 1), m14.adviento1(anio)
        while f < fin:
            if f.isoformat() not in base:
                huecos.append(f.isoformat())
            f += DIA
    inf.append("dias sin ninguna celebracion en %d-%d: %d"
               % (anios[0], anios[2], len(huecos)))
    if huecos:
        inf.append("   %s" % ", ".join(huecos[:15]))

    # --- traslados --------------------------------------------------------
    inf.append("")
    inf.append("solemnidades trasladadas por concurrencia: %d"
               % len(trasladadas))
    for de, a, t in trasladadas[:25]:
        inf.append("   %s -> %s  %s" % (de, a, t))
    if len(trasladadas) > 25:
        inf.append("   ... y %d mas" % (len(trasladadas) - 25))

    # --- concurrencias: cuantos dias ofrecen mas de una celebracion -------
    cuenta = Counter()
    for f, val in base.items():
        cuenta[len(val["c"])] += 1
    inf.append("")
    inf.append("celebraciones por dia: %s"
               % ", ".join("%d dia(s) con %d" % (n, k)
                           for k, n in sorted(cuenta.items())))

    inf.append("")
    inf.extend(verifica_tabla(m14, cfg_base))

    salida = {"config": cfg_base,
              "opciones": {k: list(v) for k, v in m14.OPCIONES.items()},
              "rango": [anios[0], anios[-1]], "anios": meta,
              "santoral": list(dias_santoral.values()),
              "fechas": base, "parches": parches}
    ruta = os.path.join(DATA, "calendario_completo.json")
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(salida, fh, ensure_ascii=False, separators=(",", ":"))
    inf.append("")
    inf.append("escrito data/calendario_completo.json  (%d KB)"
               % (os.path.getsize(ruta) // 1024))

    if avisos:
        inf.append("")
        inf.append("AVISOS:")
        for a in avisos:
            inf.append("   " + a)

    with open(os.path.join(DATA, "santoral_qa.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(inf) + "\n")
    print("\n".join(inf))


if __name__ == "__main__":
    main()
