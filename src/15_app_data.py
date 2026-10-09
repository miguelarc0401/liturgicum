"""Fase 11 - Los datos de la app: el leccionario empaquetado para el telefono.

La app no vuelve a resolver nada. Todo lo que ensena sale ya hecho de las fases
anteriores, y este modulo se limita a pasarlo de la forma en que se imprime un
libro a la forma en que la lee un programa:

    data/readings_latin*.json     ->  app/datos/lecturas_<fuente>.json
    data/calendario.json          ->  app/datos/indice.json
    data/calendario_completo.json ->  app/datos/calendario.json

Desde la fase 13 entran tambien los leccionarios **V** (propio y comun de los
santos), **VI** (misas por diversas necesidades y votivas) y **VIII** (misas
rituales y de difuntos), con su indice propio; y el calendario ya no es solo el
del tiempo, sino el completo, con el santoral y la precedencia resuelta. El
**IX** (misas con ninos) se deja fuera a proposito: no es un formulario del
ano, y meterlo doblaria las opciones de cada dia sin que nadie lo pida.

Lo importante es de donde sale el texto compuesto. **No se reescribe aqui**:
se importa `8_render.py` y se usan sus propias funciones -la formula latina de
cada libro, la cita con su sigla, la antifona del salmo, la acentuacion
liturgica de la fase 9-, de modo que lo que ensena la app y lo que imprime el
DOCX salen de la misma maquinaria y no pueden divergir.

El texto va acentuado. Quitar el acento es facil (es un agudo que se le puede
retirar a la vocal) y lo hace la propia app cuando se apaga la acentuacion;
ponerlo no lo es. Asi que se empaqueta una sola version, la acentuada.

Los iconos no se tocan aqui. Los hace src/19_iconos.py a partir de la imagen
de la tapa, y se dejaron de dibujar en este guion porque se pisaban: cada
publicacion rehacia la cruz de trazo y borraba la tapa buena. Lo que si entra
aqui es su firma, para que al cambiarlos el telefono se entere.

Uso:  python src/15_app_data.py [--fuente clementina|nova|ambas]
"""

import argparse
import importlib.util
import json
import os
import re
import unicodedata
import zlib
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
APP = os.path.join(ROOT, "app")
DATOS = os.path.join(APP, "datos")
# el codigo de la app, que tambien firma version.js (y Breviarium/src/4_app.py).
# Los iconos entran en la firma aunque no los escriba este guion: si no, se
# cambia la tapa y el telefono sigue ensenando la de antes, porque el service
# worker los tiene cacheados y nada le dice que ha cambiado nada.
CODIGO_APP = ["index.html", "app.js", "estilos.css", "manifest.webmanifest",
              "icono.svg", "icono-32.png", "icono-180.png", "icono-192.png",
              "icono-512.png", "icono-maskable-512.png"]

COLOR_SECCION = [
    (r"adviento|cuaresma", "morado"),
    (r"navidad|pascua|solemnidades", "blanco"),
    (r"ordinario", "verde"),
]

# El color del tiempo no es el de todos sus dias, y cuatro del temporal se
# salen: Pentecostes es rojo dentro del tiempo pascual, el Viernes santo
# tambien, el domingo de Ramos es rojo dentro de la Cuaresma y la Misa
# crismal es blanca dentro de ella. Son estos cuatro y no mas: se miraron
# uno a uno los dias del temporal cuyo nombre delata otro color. (El rosa de
# Gaudete y Laetare no esta: es optativo, el libro deja el morado, y la app
# no tiene ese color.)
COLOR_DIA = [
    (r"\bpentecostes\b", "rojo"),
    (r"\bdomingo de ramos\b", "rojo"),
    (r"\bviernes santo\b", "rojo"),
    (r"\bmisa crismal\b", "blanco"),
]

# Los leccionarios que entran en la app. El IX (misas con ninos) queda fuera.
LECCIONARIOS = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII")

MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
         "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]


def modulo(nombre):
    """Importa un script cuyo nombre empieza por un numero."""
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


def color_de(seccion):
    n = norm(seccion)
    for patron, color in COLOR_SECCION:
        if re.search(patron, n):
            return color
    return "neutro"


def color_del_dia(titulo):
    """El color propio de un dia del temporal, cuando no es el de su tiempo."""
    n = norm(titulo)
    for patron, color in COLOR_DIA:
        if re.search(patron, n):
            return color
    return None


# --------------------------------------------------------------------------
# las lecturas
# --------------------------------------------------------------------------
def tramos_de(r8, e, salmo=False):
    """[[['1', 'Verbum quod...'], ...], ...] — un tramo por corte de la cita."""
    fuera = []
    for tr in e["tramos"]:
        linea = []
        for v in tr:
            t = v["texto"]
            if salmo:
                t = r8.sin_titulo_salmo(t, v["cap"], v["vers"])
                if not t:
                    continue
            linea.append([str(v["vers"]), r8.ac(t)])
        if linea:
            fuera.append(linea)
    return fuera


def lectura_de(r8, e, formulas, siglas, corpus, libros_es=None):
    """Una lectura tal como la ensena la app, ya compuesta."""
    cita = r8.cita_latina(e, siglas)
    if e.get("aprox_cf"):
        cita = "cf. " + cita
    tipo = e["tipo"]
    if tipo == "salmo responsorial":
        clase = "salmo"
    elif tipo in ("aleluya", "secuencia"):
        clase = tipo
    else:
        clase = "lectura"
    out = {"t": r8.titulo_lectura(e), "c": cita, "k": clase,
           "g": tramos_de(r8, e, salmo=(clase == "salmo"))}
    if clase in ("lectura", "salmo"):
        out["f"] = formulas.get(e["libro_vulgata"], "Lectio")
    if clase == "salmo":
        ant = r8.antifona_latina(e, corpus)
        if ant:
            out["r"] = ant
        elif e.get("antifona_ref"):
            out["rr"] = e["antifona_ref"]
    # Texto extra solo para el buscador: la cita como la escribe el leccionario
    # ("Sal 121") y el nombre castellano del libro, para que quien busca
    # "Isaias 2" o "Salmo 121" lo encuentre sin saber la sigla latina.
    extra = [e.get("canonica", "")]
    if libros_es:
        extra.append(libros_es.get(e["libro_vulgata"], ""))
    extra = " ".join(x for x in extra if x and x != cita)
    if extra:
        out["q"] = extra
    return out


def construye_anexos(r8, fuente, siglas, corpus, avisos):
    """Los apendices, con la misma forma que un formulario cualquiera.

    Asi la app no necesita saber que existen: el indice, el lector y el
    buscador los tratan como a un dia mas. Cada anexo es un "dia" con un solo
    formulario, y cada entrada de la lista, una "lectura".
    """
    meta, resueltas, fijo = r8.load_anexos(fuente)
    if not meta:
        return {}, None
    bloques, dias = OrderedDict(), []
    for a in meta["anexos"]:
        if a.get("ausente"):
            continue
        clave = "ANEXO|%s|0" % a["id"]
        lect, tiempo = [], None
        for e in a["entradas"]:
            if e.get("sin_cita"):
                row = fijo.get((a["id"], str(e["n"])))
                if not row:
                    continue
                lect.append({"t": str(e["n"]), "c": "", "k": "aleluya",
                             "g": [[["", r8.texto_fijo(row["latin"])]]]})
                continue
            r = resueltas.get((a["id"], e["orden"]))
            if not r or not r["tramos"]:
                continue
            cita = r8.cita_latina(r, siglas)
            if r.get("aprox_cf"):
                cita = "cf. " + cita
            if r["tipo"] == "salmo responsorial":
                rot = ""
                if e.get("tiempo") and e["tiempo"] != tiempo:
                    tiempo = rot = e["tiempo"]
                item = {"t": rot, "c": cita, "k": "salmo",
                        "g": tramos_de(r8, r, salmo=True)}
                ant = r8.antifona_latina(r, corpus)
                if ant:
                    item["r"] = ant
                elif r.get("antifona_ref"):
                    item["rr"] = r["antifona_ref"]
            else:
                item = {"t": str(e["n"]), "c": cita, "k": "aleluya",
                        "g": tramos_de(r8, r)}
            lect.append(item)
        for resp in a.get("respuestas", []):
            lect.append({"t": resp["tiempo"], "c": "", "k": "aleluya",
                         "g": [[["", resp["es"]]]], "es": True})
        if not lect:
            continue
        bloques[clave] = lect
        dias.append({"s": "anexo_" + a["id"], "t": a["titulo"],
                     "i": a["ambito"],
                     "b": [{"e": a["ambito"], "k": clave}]})
    ausentes = [a["ambito"] for a in meta["anexos"] if a.get("ausente")]
    if ausentes:
        avisos.append("apendices sin pagina descargada: %d (%s)"
                      % (len(ausentes), "; ".join(ausentes)))
    if not dias:
        return {}, None
    return bloques, {"t": "APÉNDICES", "c": "neutro",
                     "g": [{"t": "", "d": dias}]}


def construye_lecturas(fuente, avisos):
    r8 = modulo("8_render")
    cfg = r8.FUENTES[fuente]
    r8.activa_acentos(True)
    r8.TITULI = r8.load_tituli_salmos() if fuente == "nova" else {}
    formulas, siglas = r8.load_formulas(cfg["formulas"])
    corpus = json.load(open(os.path.join(DATA, cfg["corpus"]),
                            encoding="utf-8"))
    entradas = json.load(open(os.path.join(DATA, cfg["lecturas"]),
                              encoding="utf-8"))
    libros_es = {b["vulgata"]: b["es"][0] for b in
                 json.load(open(os.path.join(DATA, "books.json"),
                                encoding="utf-8"))}
    entradas = [e for e in entradas if e["leccionario"] in LECCIONARIOS]
    por_bloque = OrderedDict()
    for e in sorted(entradas, key=lambda x: x["orden"]):
        clave = "%s|%s|%d" % (e["leccionario"], e["archivo"], e.get("cel_n", 0))
        por_bloque.setdefault(clave, []).append(
            lectura_de(r8, e, formulas, siglas, corpus, libros_es))
    faltan = sorted({e["libro_vulgata"] for e in entradas
                     if e["libro_vulgata"] not in formulas})
    if faltan:
        avisos.append("%s: sin formula latina: %s" % (fuente, ", ".join(faltan)))
    anexos, seccion = construye_anexos(r8, fuente, siglas, corpus, avisos)
    por_bloque.update(anexos)
    cierre = r8.ac("Verbum Domini.")
    return ({"fuente": fuente, "titulo": cfg["titulo"],
             "cabecera": re.sub(r"\*|\n$", "", cfg["cabecera"]).strip(),
             "cierre": cierre, "bloques": por_bloque},
            len(entradas), seccion)


# --------------------------------------------------------------------------
# el indice del ano
# --------------------------------------------------------------------------
def construye_indice():
    cal = json.load(open(os.path.join(DATA, "calendario.json"),
                         encoding="utf-8"))
    secciones = []
    n_dias = 0
    for sec in cal["secciones"]:
        grupos = []
        for g in sec["grupos"]:
            dias = []
            for d in g["dias"]:
                # `c` solo cuando el dia se sale del color de su tiempo: sin
                # el, la app toma el de la seccion
                color = color_del_dia(d["titulo"])
                dia = {"s": d["slug"], "t": d["titulo"],
                       "i": d.get("titulo_indice") or d["titulo"],
                       "b": [{"e": b["etiqueta"],
                              "k": "%s|%s|%d" % tuple(b["clave"])}
                             for b in d["bloques"]]}
                if color:
                    dia["c"] = color
                dias.append(dia)
                n_dias += 1
            if dias:
                grupos.append({"t": g.get("titulo") or "", "d": dias})
        if grupos:
            secciones.append({"t": sec["titulo"], "c": color_de(sec["titulo"]),
                              "g": grupos})
    return {"secciones": secciones}, n_dias


# --------------------------------------------------------------------------
# el indice de los leccionarios V, VI y VIII
# --------------------------------------------------------------------------
def dia_santoral(d):
    """Un dia del propio de los santos, tal como lo emite 18_santoral.py."""
    return {"s": d["slug"], "t": d["titulo"],
            "i": d.get("titulo_indice") or d["titulo"],
            "g": d.get("rotulo_grado") or "",
            "c": d.get("color") or "blanco",
            "b": [{"e": b["etiqueta"], "k": "%s|%s|%d" % tuple(b["clave"])}
                  for b in d["bloques"]]}


def seccion_santoral(santoral):
    """PROPIO DE LOS SANTOS, por meses, en el orden del calendario."""
    porder, moviles = OrderedDict(), []
    for d in santoral:
        if d.get("mes"):
            porder.setdefault(d["mes"], []).append(d)
        else:
            moviles.append(d)
    grupos = []
    for mes in sorted(porder):
        dias = sorted(porder[mes], key=lambda d: (d["dia"], d["titulo"]))
        grupos.append({"t": MESES[mes - 1],
                       "d": [dia_santoral(d) for d in dias]})
    if moviles:
        grupos.append({"t": "CELEBRACIONES MÓVILES",
                       "d": [dia_santoral(d) for d in moviles]})
    return {"t": "PROPIO DE LOS SANTOS", "c": "rojo", "g": grupos}


def bloques_de_pagina(readings, leccionario, archivo):
    """Los formularios de una pagina: uno por celebracion, con su rotulo.

    Nueve memorias del leccionario V no traen lecturas: todo su formulario es
    una linea que remite al Comun («Del Comun de pastores»). Si se dejaran con
    su bloque vacio, el indice las ofreceria y la app abriria una pagina en
    blanco; se les ponen los Comunes a los que remiten, que es lo que hay que
    leer ese dia.
    """
    bl = [r for r in readings
          if r["lectionary"] == leccionario and r["source_file"] == archivo]
    bl.sort(key=lambda r: r.get("cel_n", 0))
    fuera = []
    for r in bl:
        if r.get("readings"):
            clave = "%s|%s|%d" % (leccionario, archivo, r.get("cel_n", 0))
            fuera.append({"e": r["celebration"] if len(bl) > 1 else "",
                          "k": clave})
            continue
        for c in (r.get("comunes") or []):
            fuera.append({"e": re.sub(r"^O bien d", "D", c["texto"]),
                          "k": "%s|%s|0" % (leccionario, c["archivo"])})
    return fuera, (bl[0]["celebration"] if bl else None)


def seccion_de_toc(toc, readings, leccionario, titulo, color):
    """Una seccion del indice construida con el arbol del propio sitio."""
    nodos = toc.get(leccionario, {}).get("nodos", [])
    grupos, actual, cabeceras = [], None, {}
    for n in nodos:
        nivel = n.get("nivel", 0)
        if nivel >= 1 and not n.get("archivo"):
            cabeceras[nivel] = n["texto"]
            for k in list(cabeceras):
                if k > nivel:
                    del cabeceras[k]
            actual = None
            continue
        if not n.get("archivo"):
            continue
        b, nombre = bloques_de_pagina(readings, leccionario, n["archivo"])
        if not b:
            continue
        if actual is None:
            actual = {"t": " · ".join(cabeceras[k] for k in sorted(cabeceras)),
                      "d": []}
            grupos.append(actual)
        slug = "l%s_%s" % (leccionario.lower(),
                           re.sub(r"\.html?$", "", n["archivo"]).lower())
        texto = re.sub(r"^\d+[.:]\s*", "", n["texto"]).strip()
        actual["d"].append({"s": slug, "t": nombre or texto, "i": texto,
                            "b": b})
    return {"t": titulo, "c": color, "g": [g for g in grupos if g["d"]]}


def secciones_extra(santoral, avisos):
    """Santoral, comunes, votivas y rituales: lo que la app no tenia."""
    toc = json.load(open(os.path.join(DATA, "toc.json"), encoding="utf-8"))
    readings = json.load(open(os.path.join(DATA, "readings.json"),
                              encoding="utf-8"))
    secs = [seccion_santoral(santoral)]

    # El leccionario V entero. Se parte en dos: los Comunes van a su propia
    # seccion (se usan a diario desde cualquier memoria) y del resto se quita
    # lo que el calendario ya coloca en su fecha, que ahi se alcanza por el
    # dia y repetirlo solo alarga el indice.
    colocados = {b["clave"][1] for d in santoral for b in d["bloques"]}
    sec_v = seccion_de_toc(toc, readings, "V", "", "rojo")
    grupos_com = [g for g in sec_v["g"] if norm(g["t"]) == "comunes"]
    otros = []
    for g in sec_v["g"]:
        if norm(g["t"]) == "comunes":
            continue
        g["d"] = [d for d in g["d"]
                  if not any(b["k"].split("|")[1] in colocados
                             for b in d["b"])]
        if g["d"]:
            otros.append(g)
    if otros:
        secs.append({"t": "OTROS FORMULARIOS DEL PROPIO DE LOS SANTOS",
                     "c": "rojo", "g": otros})
    if grupos_com:
        secs.append({"t": "COMÚN DE LOS SANTOS", "c": "rojo",
                     "g": [{"t": "", "d": grupos_com[0]["d"]}]})
    else:
        avisos.append("no encuentro el grupo COMUNES en el indice del "
                      "leccionario V")

    secs.append(seccion_de_toc(
        toc, readings, "VI",
        "MISAS POR DIVERSAS NECESIDADES Y VOTIVAS · leccionario VI", "neutro"))
    secs.append(seccion_de_toc(
        toc, readings, "VIII",
        "MISAS RITUALES Y DE DIFUNTOS · leccionario VIII", "neutro"))
    secs = [s for s in secs if s["g"]]
    return secs


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuente", default="ambas",
                    choices=["clementina", "nova", "ambas"])
    args = ap.parse_args()
    os.makedirs(DATOS, exist_ok=True)
    avisos, inf = [], []

    def escribe(ruta, obj):
        with open(ruta, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
        kb = os.path.getsize(ruta) // 1024
        inf.append("%-34s %6d KB" % (os.path.basename(ruta), kb))
        return kb

    fuentes = ["clementina", "nova"] if args.fuente == "ambas" \
        else [args.fuente]
    total = 0
    seccion_anexos = None
    for fuente in fuentes:
        datos, n, seccion = construye_lecturas(fuente, avisos)
        seccion_anexos = seccion_anexos or seccion
        total += escribe(os.path.join(DATOS, "lecturas_%s.json" % fuente),
                         datos)
        inf.append("   %s: %d formularios, %d lecturas"
                   % (fuente, len(datos["bloques"]), n))

    ruta_cal = os.path.join(DATA, "calendario_completo.json")
    if not os.path.exists(ruta_cal):
        raise SystemExit("falta data/calendario_completo.json: ejecuta "
                         "python src/14_calendario_civil.py y luego "
                         "python src/18_santoral.py")
    cal = json.load(open(ruta_cal, encoding="utf-8"))
    santoral = cal.pop("santoral", [])

    indice, n_dias = construye_indice()
    extra = secciones_extra(santoral, avisos)
    for s in extra:
        indice["secciones"].append(s)
        n = sum(len(g["d"]) for g in s["g"])
        n_dias += n
        inf.append("   %-58s %4d dias" % (s["t"], n))
    if seccion_anexos:
        indice["secciones"].append(seccion_anexos)
        n_dias += len(seccion_anexos["g"][0]["d"])
        inf.append("   %d apéndices" % len(seccion_anexos["g"][0]["d"]))
    total += escribe(os.path.join(DATOS, "indice.json"), indice)
    inf.append("   %d dias en el indice" % n_dias)

    total += escribe(os.path.join(DATOS, "calendario.json"), cal)
    inf.append("   %d fechas, anos %d-%d"
               % (len(cal["fechas"]), cal["rango"][0], cal["rango"][1]))

    # las claves que el indice declara y las lecturas no traen (o al reves)
    claves_indice = {b["k"] for s in indice["secciones"] for g in s["g"]
                     for d in g["d"] for b in d["b"]}
    for fuente in fuentes:
        ruta = os.path.join(DATOS, "lecturas_%s.json" % fuente)
        bl = set(json.load(open(ruta, encoding="utf-8"))["bloques"])
        huerfanas = sorted(claves_indice - bl)
        if huerfanas:
            avisos.append("%s: %d formularios del indice sin lecturas: %s"
                          % (fuente, len(huerfanas), ", ".join(huerfanas[:5])))
    slugs = {d["s"] for s in indice["secciones"] for g in s["g"]
             for d in g["d"]}
    del_cal = {o[0] for e in cal["fechas"].values() for o in e["c"]}
    for p in cal["parches"].values():
        for e in p["fechas"].values():
            if e:
                del_cal |= {o[0] for o in e["c"]}
    sueltos = sorted(del_cal - slugs)
    if sueltos:
        avisos.append("el calendario apunta a %d dias que el indice no tiene: "
                      "%s" % (len(sueltos), ", ".join(sueltos[:5])))

    # La firma cubre los datos y tambien el codigo de la app: si solo cambia
    # app.js (una vista nueva, un arreglo), el telefono tiene que enterarse
    # igual, y lo que le obliga a tirar la cache es que cambie esta firma.
    version = "%s-%d" % (
        "+".join(fuentes),
        zlib.crc32(b"".join(open(os.path.join(DATOS, f), "rb").read()
                            for f in sorted(os.listdir(DATOS))
                            if f != "version.js")
                   + b"".join(open(os.path.join(APP, f), "rb").read()
                              for f in CODIGO_APP
                              if os.path.exists(os.path.join(APP, f))))
        & 0xffffffff)
    with open(os.path.join(DATOS, "version.js"), "w", encoding="utf-8") as fh:
        fh.write("// lo escribe src/15_app_data.py; cambia con los datos, y al\n"
                 "// cambiar obliga al service worker a rehacer su cache\n"
                 'self.VERSION_DATOS = "%s";\n' % version)

    print("\n".join(inf))
    print("%-34s %6d KB  (lo que ocupa la app sin conexion)" % ("TOTAL", total))
    print("version de datos: %s" % version)
    if avisos:
        print("\nAVISOS:")
        for a in avisos:
            print("  " + a)
    else:
        print("\n0 avisos: el indice, las lecturas y el calendario cuadran.")


if __name__ == "__main__":
    main()
