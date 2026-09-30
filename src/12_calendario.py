"""Fase 6e - El espinazo del ano liturgico: los cinco leccionarios en uno.

Los leccionarios del sitio estan organizados por libro (I, II, III = domingos
de cada ciclo; IV = ferias del Tiempo Ordinario; VII = ferias de los tiempos
fuertes). Para leer el ano de corrido hace falta lo contrario: recorrer el
calendario y, en cada dia, poner juntos todos sus formularios.

    Domingo I de Adviento .... ciclo A, ciclo B, ciclo C
    Lunes de la 1a semana .... ferias (comun a los tres ciclos)
    ...
    Lunes de la 1a semana del T.O. .... ano I, ano II

Como se construye:

* Los **domingos y fiestas** se alinean por su posicion en el indice del sitio.
  Comprobado en `10_toc.py`: los indices de I, II y III llevan las mismas 69
  entradas, con el mismo texto y en el mismo orden, asi que la posicion es una
  clave fiable para saber que tres paginas son el mismo dia.
* Las **ferias** se localizan por el codigo de su fichero, que es sistematico
  (`7045TCUL01` = Cuaresma, lunes, semana 1; `4001ITOL01` = T.O., ano I, lunes,
  semana 1). En el leccionario IV el ano lo manda la seccion del indice
  (ANO I / ANO II), no la pagina: hay una pagina con el ano mal puesto.
* Los dias cuyo formulario es **comun a los tres ciclos** (Navidad, Epifania,
  Triduo, Pascua...) no se imprimen tres veces. Se detectan porque las tres
  paginas lo declaran ("Ciclos A, B y C") y se queda la mas completa; las
  diferencias entre las tres copias se anotan en el informe, no se ocultan.

Salida: data/calendario.json  +  data/calendario_qa.txt (el ano entero en una
lista, para revisarlo de un vistazo, con el recuento de lo colocado).

Uso:  python src/12_calendario.py
"""

import csv
import json
import os
import re
import unicodedata
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

DIAS = OrderedDict([("L", "Lunes"), ("M", "Martes"), ("X", "Miércoles"),
                    ("J", "Jueves"), ("V", "Viernes"), ("S", "Sábado")])
CICLO_DE_LECT = {"I": "A", "II": "B", "III": "C"}
ROMANOS = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
           "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX",
           "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII",
           "XXVIII", "XXIX", "XXX", "XXXI", "XXXII", "XXXIII", "XXXIV"]

# Bloques secundarios que el sitio repite dentro de otra pagina y que ya estan
# completos en su propio formulario: se descartan para no duplicar el dia.
DUPLICADOS = {
    ("1028APAD06.html", 1): "1030APAD07.html",
    ("2028BPAD06.html", 1): "2030BPAD07.html",
    ("3028CPAD06.html", 1): "3030CPAD07.html",
    ("2029BFASCE.html", 1): "2030BPAD07.html",
    ("3029CFASCE.html", 1): "3030CPAD07.html",
}

# Bloques secundarios que si aportan algo, con el rotulo que les corresponde.
ROTULO_SECUNDARIO = {
    ("1023APAD01.html", 1): "Ciclo A · evangelios alternativos",
    ("2023BPAD01.html", 1): "Ciclo B · evangelios alternativos",
    ("3023CPAD01.html", 1): "Ciclo C · evangelios alternativos",
}


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def es_comun(ciclo):
    """"Ciclos A, B y C" (con sus variantes) frente a "Ciclo A"."""
    return len(re.findall(r"\b[abc]\b", norm(ciclo))) > 1


def carga_overrides():
    """Nombres de celebracion corregidos a mano, editables sin tocar codigo.

    Hay paginas del sitio sin <p class=Santo>: el parser cae entonces en el
    <title> del HTML, que en las exportadas desde Word es "Documento sin
    titulo". El recuento no se entera, porque las lecturas estan completas; lo
    unico que sale mal es el nombre del dia.
    """
    ruta = os.path.join(DATA, "celebracion_overrides.csv")
    if not os.path.exists(ruta):
        return {}
    with open(ruta, encoding="utf-8", newline="") as fh:
        return {r["archivo"].strip(): r["titulo"].strip()
                for r in csv.DictReader(fh) if r.get("archivo")}


OVERRIDES = carga_overrides()
OVERRIDES_USADOS = set()


def limpia_titulo(nombre, archivo=None):
    """El nombre del dia tal como lo trae la pagina, presentable."""
    if archivo and archivo in OVERRIDES:
        OVERRIDES_USADOS.add(archivo)
        return OVERRIDES[archivo]
    t = (nombre or "").strip().rstrip(".")
    t = re.sub(r"^Feria de Adviento\.?\s*[—–-]\s*", "", t)
    t = re.sub(r"^Día\s+", "", t)
    t = re.sub(r"^(\d+)\s+DE\s+([A-ZÁÉÍÓÚÑ]+)",
               lambda m: "%s de %s" % (m.group(1), m.group(2).lower()), t)
    return re.sub(r"\s+", " ", t).strip()


# --------------------------------------------------------------------------
# carga
# --------------------------------------------------------------------------
def carga():
    entradas = json.load(open(os.path.join(DATA, "readings_latin.json"),
                              encoding="utf-8"))
    toc = json.load(open(os.path.join(DATA, "toc.json"), encoding="utf-8"))
    bloques = OrderedDict()
    for e in entradas:
        bloques.setdefault((e["leccionario"], e["archivo"],
                            e.get("cel_n", 0)), []).append(e)
    for v in bloques.values():
        v.sort(key=lambda x: x["orden"])
    return bloques, toc


def slots_dominicales(toc):
    """Alinea I, II y III por la posicion de su entrada en el indice."""
    listas = {l: [n for n in toc[l]["nodos"] if n["nivel"] == 0]
              for l in ("I", "II", "III") if l in toc}
    slots = []
    for i in range(min(len(v) for v in listas.values())):
        etiquetas = {l: listas[l][i]["texto"] for l in listas}
        if len({norm(t) for t in etiquetas.values()}) != 1:
            break                      # los indices dejaron de ir en paralelo
        slots.append({"etiqueta": etiquetas["I"],
                      "archivos": {l: listas[l][i]["archivo"] for l in listas}})
    return slots


def ferias_iv(toc):
    """(semana, dia) -> {ano: archivo}. El ano lo manda la seccion del indice."""
    salida, avisos, seccion = {}, [], None
    for nodo in toc.get("IV", {}).get("nodos", []):
        if nodo["nivel"] == 1:
            # ojo: "impares" contiene "pares", asi que el impar va primero
            t = norm(nodo["texto"])
            if "impar" in t or re.search(r"\bano i\b", t):
                seccion = "I"
            elif "par" in t or re.search(r"\bano ii\b", t):
                seccion = "II"
            else:
                seccion = None
            continue
        if nodo["nivel"] != 0:
            continue
        m = re.search(r"TO([LMXJVS])(\d\d)", nodo["archivo"])
        if not m or seccion is None:
            continue
        letra = re.match(r"^\d+([IP])TO", nodo["archivo"])
        if letra and ("I" if letra.group(1) == "I" else "II") != seccion:
            avisos.append("%s: el codigo dice ano %s y el indice, ano %s"
                          % (nodo["archivo"],
                             "I" if letra.group(1) == "I" else "II", seccion))
        salida.setdefault((int(m.group(2)), m.group(1)), {})[seccion] = \
            nodo["archivo"]
    return salida, avisos


# --------------------------------------------------------------------------
# espinazo
# --------------------------------------------------------------------------
def construye(bloques, toc):
    slots = slots_dominicales(toc)
    if len(slots) < 69:
        raise SystemExit("los indices de I/II/III solo se alinean en %d "
                         "entradas; revisa data/toc.json" % len(slots))
    iv, avisos_iv = ferias_iv(toc)
    ano_de = {arch: ano for dias in iv.values() for ano, arch in dias.items()}
    vii = sorted(a for (l, a, c) in bloques if l == "VII" and c == 0)

    def dominical(i, titulo=None):
        """Un dia con los formularios de los tres ciclos."""
        s = slots[i]
        bl = []
        for lect in ("I", "II", "III"):
            arch = s["archivos"].get(lect)
            bl += [(lect, arch, c) for c in
                   sorted(c for (l, a, c) in bloques
                          if l == lect and a == arch)]
        return {"titulo": titulo or s["etiqueta"],
                "titulo_indice": titulo or s["etiqueta"], "bloques": bl}

    def dia_vii(archivo, titulo=None):
        clave = ("VII", archivo, 0)
        if clave not in bloques:
            return None
        largo = limpia_titulo(bloques[clave][0]["celebracion"], archivo)
        return {"titulo": titulo or largo, "titulo_indice": titulo or largo,
                "bloques": [clave]}

    def serie_vii(patron, titulos=None):
        """Los ficheros del leccionario VII que casan, en orden de fichero."""
        rx = re.compile(r"^\d+(?:%s)\.html$" % patron)
        salida = []
        for a in vii:
            if rx.match(a):
                d = dia_vii(a)
                if d:
                    if titulos:
                        d["titulo"] = titulos(a, d["titulo"])
                    salida.append(d)
        return salida

    def semana_vii(tiempo, semana):
        """Las ferias de una semana, rotuladas con el nombre del dia."""
        salida = []
        for letra, nombre in DIAS.items():
            d = serie_vii("T%s%s%02d" % (tiempo, letra, semana))
            if d:
                d[0]["titulo_indice"] = nombre     # en el indice basta el dia
                salida.append(d[0])
        return salida

    def semana_iv(semana):
        """Las ferias de una semana del T.O., cada dia con sus dos anos."""
        salida = []
        for letra, nombre in DIAS.items():
            archivos = iv.get((semana, letra), {})
            bl = [("IV", archivos[a], 0) for a in ("I", "II")
                  if a in archivos and ("IV", archivos[a], 0) in bloques]
            if bl:
                salida.append({"titulo": limpia_titulo(
                    bloques[bl[0]][0]["celebracion"], bl[0][1]),
                    "titulo_indice": nombre, "bloques": bl})
        return salida

    def grupo(titulo, dias):
        return {"titulo": titulo, "dias": [d for d in dias if d]}

    secciones = []

    # ---- Adviento -------------------------------------------------------
    grupos = [grupo("%s semana de Adviento" % ROMANOS[s],
                    [dominical(s - 1)] + semana_vii("AV", s))
              for s in (1, 2, 3)]
    grupos.append(grupo("IV semana de Adviento", [dominical(3)]))
    grupos.append(grupo("Ferias del 17 al 24 de diciembre",
                        serie_vii(r"TFPD\d\d")))
    secciones.append({"titulo": "TIEMPO DE ADVIENTO", "grupos": grupos})

    # ---- Navidad --------------------------------------------------------
    grupos = [grupo("Natividad del Señor",
                    [dominical(i) for i in (4, 5, 6, 7)]),
              grupo("Octava de Navidad",
                    [dominical(8)] + serie_vii(r"TON\d{3}") + [dominical(9)]),
              grupo("", [dominical(10)]),
              grupo("Ferias antes de la Epifanía", serie_vii(r"TF0\dEN")),
              grupo("", [dominical(11)]),
              grupo("Ferias después de la Epifanía",
                    serie_vii(r"TF[LMXJVS]DEP")),
              grupo("", [dominical(12)])]
    secciones.append({"titulo": "TIEMPO DE NAVIDAD", "grupos": grupos})

    # ---- Cuaresma -------------------------------------------------------
    grupos = [grupo("Miércoles de Ceniza y ferias siguientes",
                    serie_vii(r"TFMICE|TFJUDC|TFVIDC|TFSACE"))]
    for s in range(1, 6):
        dias = [dominical(12 + s)]
        libre = serie_vii(r"MLCU0%d" % s)
        for d in libre:
            d["titulo"] = d["titulo_indice"] = "Misa de libre elección"
        grupos.append(grupo("%s semana de Cuaresma" % ROMANOS[s],
                            dias + libre + semana_vii("CU", s)))
    grupos.append(grupo("Semana Santa",
                        [dominical(18, "Domingo de Ramos en la Pasión "
                                       "del Señor")]
                        + serie_vii(r"T[LMX]SESA|JUSAMC")))
    secciones.append({"titulo": "TIEMPO DE CUARESMA", "grupos": grupos})

    # ---- Triduo y Pascua ------------------------------------------------
    grupos = [grupo("Triduo pascual", [dominical(i) for i in (20, 21, 22, 23)]),
              grupo("Octava de Pascua", serie_vii(r"TOCPA[LMXJVS]"))]
    for s in range(2, 7):
        grupos.append(grupo("%s semana de Pascua" % ROMANOS[s],
                            [dominical(22 + s)] + semana_vii("PA", s)))
    grupos.append(grupo("", [dominical(29)]))                  # Ascension
    grupos.append(grupo("VII semana de Pascua",
                        [dominical(30)] + semana_vii("PA", 7)))
    grupos.append(grupo("", [dominical(31, "Domingo de Pentecostés")]))
    secciones.append({"titulo": "TRIDUO PASCUAL Y TIEMPO DE PASCUA",
                      "grupos": grupos})

    # ---- Solemnidades del Señor -----------------------------------------
    secciones.append({"titulo": "SOLEMNIDADES DEL SEÑOR EN EL TIEMPO "
                                "ORDINARIO",
                      "grupos": [grupo("", [dominical(i)
                                            for i in (33, 34, 35)])]})

    # ---- Tiempo Ordinario ------------------------------------------------
    # las ferias de la semana I siguen al Bautismo del Señor; de ahi en
    # adelante, cada domingo abre su semana
    grupos = [grupo("Semana I del Tiempo Ordinario", semana_iv(1))]
    for s in range(2, 35):
        grupos.append(grupo("Semana %s del Tiempo Ordinario" % ROMANOS[s],
                            [dominical(34 + s)] + semana_iv(s)))
    secciones.append({"titulo": "TIEMPO ORDINARIO", "grupos": grupos})

    # ---- lo que no entra en el calendario -------------------------------
    usados = {b for sec in secciones for g in sec["grupos"]
              for d in g["dias"] for b in d["bloques"]}
    sueltos = [k for k in bloques if k not in usados and (k[1], k[2])
               not in DUPLICADOS]
    if sueltos:
        # No se llama "APENDICE" a secas para no confundirse con los anexos
        # de la fase 12 (§11), que son otra cosa: esto es lo que queda suelto
        # del propio leccionario, no las listas que van detras de el.
        secciones.append(
            {"titulo": "FORMULARIOS SUELTOS",
             "grupos": [grupo("", [{"titulo": limpia_titulo(
                 bloques[k][0]["celebracion"]),
                 "titulo_indice": limpia_titulo(
                     bloques[k][0]["celebracion"]),
                 "bloques": [k]} for k in sueltos])]})
    return secciones, avisos_iv, ano_de


# --------------------------------------------------------------------------
# rotulos y fusion de los dias comunes a los tres ciclos
# --------------------------------------------------------------------------
def huella(lecturas):
    """Identifica un formulario por sus citas, para detectar los repetidos."""
    return tuple((e["tipo"], e["canonica"], e.get("variante", ""))
                 for e in lecturas)


def nombre_ciclos(lects):
    cic = [CICLO_DE_LECT[l] for l in ("I", "II", "III") if l in lects]
    if len(cic) == 1:
        return "Ciclo %s" % cic[0]
    return "Ciclos %s y %s" % (", ".join(cic[:-1]), cic[-1])


def rotula(dia, bloques, ano_de, notas):
    """Pasa de claves a bloques rotulados, fundiendo lo que es el mismo dia."""
    principales = [k for k in dia["bloques"]
                   if k[0] in ("I", "II", "III") and k[2] == 0]
    comunes = [k for k in principales if es_comun(bloques[k][0].get("ciclo"))]

    fundir = {}                        # clave que se queda -> claves fundidas
    descartar = set()
    if len(comunes) > 1 and len(comunes) == len(principales):
        # el propio sitio dice que el formulario es comun: se queda el mas
        # completo y se anota si las copias no eran idenicas
        elegida = max(comunes, key=lambda k: (len(bloques[k]),
                                              -["I", "II", "III"].index(k[0])))
        fundir[elegida] = [k for k in comunes if k != elegida]
        descartar.update(fundir[elegida])
        distintas = {k: huella(bloques[k]) for k in comunes}
        if len(set(distintas.values())) > 1:
            notas.append("%s: las paginas de los tres ciclos no son idénticas; "
                         "se toma %s (%d lecturas) — %s"
                         % (dia["titulo"], elegida[1], len(bloques[elegida]),
                            ", ".join("%s:%d" % (k[0], len(bloques[k]))
                                      for k in comunes)))
    else:
        # fuera de eso, solo se funde lo que es literalmente igual
        por_huella = OrderedDict()
        for k in principales:
            por_huella.setdefault(huella(bloques[k]), []).append(k)
        for grupo in por_huella.values():
            if len(grupo) > 1:
                fundir[grupo[0]] = grupo[1:]
                descartar.update(grupo[1:])

    salida = []
    for clave in dia["bloques"]:
        lect, arch, cel = clave
        if (arch, cel) in DUPLICADOS or clave in descartar:
            continue
        if clave in fundir and fundir[clave]:
            etiqueta = nombre_ciclos([lect] + [k[0] for k in fundir[clave]])
        elif (arch, cel) in ROTULO_SECUNDARIO:
            etiqueta = ROTULO_SECUNDARIO[(arch, cel)]
        elif lect == "IV":
            etiqueta = "Año I (años impares)" if ano_de.get(arch, "I") == "I" \
                else "Año II (años pares)"
        elif lect == "VII":
            etiqueta = "Ciclos A, B y C"
        elif cel > 0:
            propio = bloques[clave][0].get("ciclo", "")
            padre = "Ciclo %s" % CICLO_DE_LECT[lect]
            if propio and norm(propio) != norm(padre):
                etiqueta = "%s · lecturas del %s" % (padre, propio[0].lower()
                                                     + propio[1:])
            else:
                etiqueta = "%s · otro formulario" % padre
        else:
            etiqueta = "Ciclo %s" % CICLO_DE_LECT[lect]
        salida.append({"etiqueta": etiqueta, "clave": list(clave),
                       "fundidos": [list(k) for k in fundir.get(clave, [])]})
    return salida


def main():
    bloques, toc = carga()
    secciones, avisos_iv, ano_de = construye(bloques, toc)

    notas = []
    colocados, repetidos, n_dias = set(), [], 0
    for si, sec in enumerate(secciones):
        for gi, g in enumerate(sec["grupos"]):
            for di, dia in enumerate(g["dias"]):
                dia.setdefault("titulo_indice", dia["titulo"])
                # en el indice, "Lunes de la 1a semana de Adviento" se queda en
                # "Lunes" porque la cabecera del grupo ya dice de que semana es;
                # "Lunes santo" o "Jueves Santo - Misa Crismal" se quedan como
                # estan, porque ahi el resto del nombre si dice algo
                m = re.match(r"^(Domingo|Lunes|Martes|Miércoles|Jueves"
                             r"|Viernes|Sábado)\b(.*)$", dia["titulo_indice"])
                if m and "semana" in norm(m.group(2)):
                    dia["titulo_indice"] = m.group(1)
                dia["slug"] = "d%d_%d_%d" % (si, gi, di)
                dia["bloques"] = rotula(dia, bloques, ano_de, notas)
                n_dias += 1
                for b in dia["bloques"]:
                    for k in [tuple(b["clave"])] + \
                            [tuple(f) for f in b["fundidos"]]:
                        if k in colocados:
                            repetidos.append(k)
                        colocados.add(k)

    faltan = [k for k in bloques
              if k not in colocados and (k[1], k[2]) not in DUPLICADOS]

    with open(os.path.join(DATA, "calendario.json"), "w",
              encoding="utf-8") as f:
        json.dump({"secciones": secciones}, f, ensure_ascii=False, indent=1)

    qa = ["EL ANO LITURGICO EN UN SOLO LECCIONARIO", ""]
    qa.append("bloques de lectura en los datos : %d" % len(bloques))
    qa.append("descartados por duplicar otro   : %d" % len(DUPLICADOS))
    qa.append("colocados en el calendario      : %d" % len(colocados))
    qa.append("SIN COLOCAR                     : %d" % len(faltan))
    qa.append("colocados dos veces             : %d" % len(repetidos))
    qa.append("dias del calendario             : %d" % n_dias)
    qa.append("nombres corregidos a mano       : %d de %d"
              % (len(OVERRIDES_USADOS), len(OVERRIDES)))
    for a in sorted(set(OVERRIDES) - OVERRIDES_USADOS):
        qa.append("   SIN APLICAR: %s (revisa celebracion_overrides.csv)" % a)
    for titulo, lista in (("sin colocar", ["%s %s cel%d  %s"
                                           % (k[0], k[1], k[2],
                                              bloques[k][0]["celebracion"])
                                           for k in faltan]),
                          ("colocados dos veces", [str(k) for k in repetidos]),
                          ("erratas de ano en el leccionario IV "
                           "(manda el indice)", avisos_iv),
                          ("dias comunes cuyas tres paginas difieren", notas)):
        if lista:
            qa += ["", titulo + ":"] + ["   " + x for x in lista]
    qa += ["", "--- el ano entero ---"]
    for sec in secciones:
        qa += ["", "== %s" % sec["titulo"]]
        for g in sec["grupos"]:
            if g["titulo"]:
                qa.append("  -- %s" % g["titulo"])
            for dia in g["dias"]:
                qa.append("     %-46s %s"
                          % (dia["titulo"][:46],
                             " | ".join(b["etiqueta"] for b in dia["bloques"])))
    salida = os.path.join(DATA, "calendario_qa.txt")
    open(salida, "w", encoding="utf-8").write("\n".join(qa) + "\n")
    print("\n".join(qa[:8]))
    if notas:
        print("\ndias comunes con paginas distintas: %d (ver el informe)"
              % len(notas))
    print("-> data/calendario.json  ·  %s" % salida)


if __name__ == "__main__":
    main()
