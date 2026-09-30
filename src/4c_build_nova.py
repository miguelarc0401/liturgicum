"""Fase 4b (2/2) - Corpus de la NOVA VULGATA a partir de cache/nova/*.html.

Las paginas de vatican.va estan marcadas de una forma sorprendentemente
regular, asi que el parseo es determinista:

    <a name="7">7</a>                  -> numero de capitulo
    <a name="PSALMUS 23">...</a> (22)  -> salmo, con su numero de la Vulgata
    <br />12 texto...                  -> numero de versiculo + texto
    <br /> texto...                    -> renglon de poesia, sigue el versiculo
    (21) 22 texto...                   -> el 21 no existe en la Nova Vulgata

Tres cosas se guardan que no estaban en la Clementina:

  * la *estiquiometria*: la Nova Vulgata imprime la poesia (salmos, profetas,
    sapienciales) en renglones, y se conservan en nova_vulgata_stichos.json
    para poder maquetarla algun dia como verso;
  * la *doble numeracion de los salmos*: la propia edicion da entre parentesis
    el numero griego (el de la Vulgata y el del leccionario espanol), asi que
    la tabla de equivalencias sale de la fuente y no de una suposicion;
  * los *versiculos omitidos*: la edicion marca "(21)" los que no trae porque
    faltan en el texto critico. Sin esa lista, un hueco legitimo y un fallo de
    parseo serian indistinguibles.

Salidas:
    data/nova_vulgata.json          {libro: {cap: {vers: texto}}}
    data/nova_vulgata_stichos.json  igual, con los renglones separados
    data/psalmi_nova.csv            griego (leccionario) - hebreo (Nova Vulgata)
    data/nova_omissiones.csv        versiculos que la edicion declara ausentes
    data/nova_qa.txt                control de calidad

Uso:  python src/4c_build_nova.py
"""

import csv
import html
import importlib.util
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "nova")
DATA = os.path.join(ROOT, "data")

_spec = importlib.util.spec_from_file_location(
    "crawl_nova", os.path.join(ROOT, "src", "4b_crawl_nova.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
LIBROS = _mod.LIBROS

NBSP = chr(0xa0)
SHY = chr(0xad)          # guion opcional, aqui usado como raya de inciso
RAYA = chr(0x2014)       # em dash
CUR_A, CUR_B = chr(1), chr(2)     # marcas internas de apertura/cierre de cursiva

# Capitulos esperados (numeracion moderna, la que usa la Nova Vulgata).
EXPECTED = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numeri": 36,
    "Deuteronomium": 34, "Iosue": 24, "Iudicum": 21, "Ruth": 4,
    "I Samuelis": 31, "II Samuelis": 24, "I Regum": 22, "II Regum": 25,
    "I Paralipomenon": 29, "II Paralipomenon": 36, "Esdrae": 10,
    "Nehemiae": 13, "Thobis": 14, "Iudith": 16, "Esther": 10,
    "Iob": 42, "Psalmi": 150, "Proverbia": 31, "Ecclesiastes": 12,
    "Canticum Canticorum": 8, "Sapientia": 19, "Ecclesiasticus": 51,
    "Isaias": 66, "Ieremias": 52, "Lamentationes": 5, "Baruch": 6,
    "Ezechiel": 48, "Daniel": 14, "Osee": 14, "Ioel": 4, "Amos": 9,
    "Abdias": 1, "Ionas": 4, "Michaeas": 7, "Nahum": 3, "Habacuc": 3,
    "Sophonias": 3, "Aggaeus": 2, "Zacharias": 14, "Malachias": 3,
    "I Maccabaeorum": 16, "II Maccabaeorum": 15,
    "Matthaeus": 28, "Marcus": 16, "Lucas": 24, "Ioannes": 21,
    "Actus Apostolorum": 28, "Ad Romanos": 16, "I Ad Corinthios": 16,
    "II Ad Corinthios": 13, "Ad Galatas": 6, "Ad Ephesios": 6,
    "Ad Philippenses": 4, "Ad Colossenses": 4, "I Ad Thessalonicenses": 5,
    "II Ad Thessalonicenses": 3, "I Ad Timotheum": 6, "II Ad Timotheum": 4,
    "Ad Titum": 3, "Ad Philemonem": 1, "Ad Hebraeos": 13, "Iacobi": 5,
    "I Petri": 5, "II Petri": 3, "I Ioannis": 5, "II Ioannis": 1,
    "III Ioannis": 1, "Iudae": 1, "Apocalypsis": 22,
}

# cabecera de salmo:  "PSALMUS 23 (22)" / "PSALMUS 10 (Vg 9, 22-39)"
PSALMO_RE = re.compile(r"^PSALMUS\s+(\d+)\s*(?:\((.*?)\))?\s*$")
# numeral de versiculo. Las letras llegan a ser dos (Est 4, 17aa - 17kk) y el
# numeral puede ir pegado a la palabra siguiente ("1Cum autem") o a la comilla
# de apertura ("2" Fili hominis").
NUMERAL_RE = re.compile(r"(?<![\w-])(\d{1,3})([a-z]{0,2})(?=[\s" + chr(0x201c)
                        + r"A-Z]|$)")
# los versiculos que la edicion no trae:  "(21)" / "(10. 11)"
OMITIDO_RE = re.compile(r"\((\d{1,3}(?:[.,]?\s*\d{1,3})*)\)")
# notas de san Jeronimo en Daniel: aparato, no texto biblico
NOTA_RE = re.compile(r"^\((?!\s*\d)[^)]*\)\.?$")


def lineas(slug):
    """El HTML de un libro, convertido en renglones con sus anclas marcadas."""
    with open(os.path.join(CACHE, slug + ".html"), "rb") as f:
        crudo = f.read()
    # la pagina se declara iso-8859-1 pero trae comillas de cp1252 (0x93/0x94)
    txt = crudo.decode("cp1252", errors="replace")
    i = txt.find("FINE TESTO")
    if i > 0:
        txt = txt[i:]
    txt = re.sub(r'<a\s+name="([^"]*)"[^>]*>',
                 lambda m: "\n@@A:" + m.group(1) + "@@ ", txt, flags=re.I)
    # la cursiva marca los titulos de los salmos ("Magistro chori. PSALMUS.
    # David."), que son epigrafe y no texto del salmo: se conserva la marca
    txt = re.sub(r"<i\b[^>]*>", CUR_A, txt, flags=re.I)
    txt = re.sub(r"</i>", CUR_B, txt, flags=re.I)
    # el titulo del libro y la tira de enlaces a los capitulos viven en su
    # propio <p>: sin cortar ahi se pegarian al versiculo 1
    txt = re.sub(r"</?(?:br|p|div|td|tr|table)\b[^>]*>", "\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html.unescape(txt)
    txt = txt.replace(NBSP, " ")
    # el guion opcional sale 36 veces en los 73 ficheros, siempre como raya de
    # inciso rodeada de espacios y nunca partiendo una palabra: comprobado
    txt = txt.replace(SHY, RAYA)
    return [re.sub(r"[ \t]+", " ", l).strip() for l in txt.split("\n")]


def quita_cursiva(t):
    t = t.replace(CUR_A, "").replace(CUR_B, "")
    return re.sub(r"[ 	]+", " ", t).strip()


def trocea(linea, actual):
    """Parte un renglon en [((num, letra), texto)] por sus numerales.

    La Nova Vulgata no siempre empieza renglon con el numero de versiculo: en
    Gn 14, 19, en Lv 19, 36 o en Hch 3, 18 el numeral va en mitad de la linea,
    asi que no basta con mirar el principio. Para no confundir un numeral con
    una cifra del texto se exige que continue la serie; la edicion escribe
    todos los numeros con letra ("septuaginta", nunca "70"), asi que el riesgo
    es remoto, y el control de calidad avisa de cualquier cifra que se quede
    dentro del texto.

    'actual' es una lista de un elemento que hace de cursor: entra con el
    ultimo versiculo abierto y sale con el ultimo que se haya encontrado.
    """
    def es_numeral(n, letra):
        if actual[0] is None:
            return n <= 2                      # arranque de capitulo
        an, al = actual[0]
        if (n, letra) == (an, al):
            return False
        # en Ez 40 la edicion imprime el 43a antes del 42b: de ahi el -1
        return an - 1 <= n <= an + 5

    piezas, resto = [], linea
    while True:
        m = NUMERAL_RE.search(resto)
        if not m or not es_numeral(int(m.group(1)), m.group(2)):
            break
        antes = resto[:m.start()].strip()
        if antes:
            piezas.append((actual[0], antes))
        actual[0] = (int(m.group(1)), m.group(2))
        piezas.append((actual[0], ""))
        resto = resto[m.end():].strip()
        # Daniel 3 lleva doble numeracion, la griega y la aramea, una detras de
        # otra ("91 24 Tunc Nabuchodonosor..."): la segunda es aparato
        m2 = NUMERAL_RE.match(resto)
        if m2 and not es_numeral(int(m2.group(1)), m2.group(2)):
            resto = resto[m2.end():].strip()
    if resto:
        if piezas:
            piezas[-1] = (piezas[-1][0],
                          (piezas[-1][1] + " " + resto).strip())
        else:
            piezas.append((actual[0], resto))
    return piezas


def load_errata():
    """Erratas de la fuente, en data/nova_errata.csv.

    Se aplican dos veces: sobre el renglon, porque algunas afectan al numeral
    del versiculo, y sobre el versiculo ya montado, porque otras veces la
    errata cruza el salto de linea de la fuente (Ps 119,93 'man data',
    Jr 9,1 'de relinquam'). El patron tolera cualquier espacio en blanco, asi
    que vale igual en las dos pasadas.
    """
    ruta = os.path.join(DATA, "nova_errata.csv")
    reglas = []
    if not os.path.exists(ruta):
        return reglas
    with open(ruta, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            patron = re.compile(r"\s+".join(
                re.escape(x) for x in row["buscar"].split()))
            reglas.append({"libro": row["libro"].strip(),
                           "buscar": row["buscar"], "patron": patron,
                           "reemplazar": row["reemplazar"],
                           "nota": row.get("nota", ""), "usos": 0})
    return reglas


def aplica_errata(texto, libro, errata):
    for r in errata:
        if r["libro"] not in ("", libro):
            continue
        texto, n = r["patron"].subn(r["reemplazar"].replace("\\", "\\\\"),
                                   texto)
        r["usos"] += n
    return texto


def parse_libro(slug, es_salmos, libro="", errata=()):
    """-> (capitulos, salmos_dobles, omitidos, notas)

    capitulos: cap -> {vers -> [renglones]}, en el orden de la edicion
    salmos_dobles: [(hebreo, "griego tal y como lo imprime la edicion")]
    omitidos: [(cap, vers)] de los que la edicion declara que no trae
    notas: [(cap, texto)] del aparato que se ha dejado fuera del texto

    El texto sin numerar que va delante del versiculo 1 se guarda con la clave
    "0": en Jue 19 y en Ba 6 la edicion imprime un encabezamiento antes del
    numeral 1, y en Nm 1 en cambio el propio versiculo 1 va sin numeral. Lo que
    distingue los dos casos es el numeral que venga despues, asi que se decide
    al encontrarlo y no antes.
    """
    ls = lineas(slug)
    # los cinco libros de un solo capitulo (Abdias, Filemon, 2-3 Jn, Judas) no
    # llevan numeral impreso, asi que tampoco ancla de capitulo
    tiene_anclas = es_salmos or any(re.match(r"^@@A:\d+@@", l) for l in ls)

    caps, dobles, omitidos, notas = {}, [], [], []
    cap, vers = None, [None]
    previo = []                 # renglones sin numerar al principio del cap.

    def marca_omitido(mo):
        for n in re.split(r"[.,\s]+", mo.group(1)):
            omitidos.append((cap if cap is not None else 1, n))
        return " "

    def cierra_previo(primer_numeral):
        """Coloca el texto sin numerar: encabezamiento ("0") o versiculo 1."""
        if not previo:
            return
        clave = "0" if primer_numeral == 1 else "1"
        caps[cap].setdefault(clave, [])
        caps[cap][clave] += previo
        del previo[:]

    for l in ls:
        if not l:
            continue
        l = aplica_errata(l, libro, errata)
        m = re.match(r"^@@A:([^@]*)@@\s*(.*)$", l)
        if m:
            ancla, resto = m.group(1).strip(), m.group(2).strip()
            nuevo = None
            if es_salmos:
                mp = PSALMO_RE.match(ancla)
                if mp:
                    nuevo = int(mp.group(1))
                    # el numero griego va FUERA del ancla, de modo que el
                    # renglon queda asi:  "PSALMUS 23" + "PSALMUS 23 (22)"
                    mg = re.match(r"^(?:PSALMUS\s+\d+\s*)?\((.*)\)\s*$", resto)
                    # sin parentesis las dos numeraciones coinciden
                    dobles.append((nuevo, mg.group(1).strip() if mg
                                   else str(nuevo)))
                    resto = ""
            elif ancla.isdigit():
                nuevo = int(ancla)
                # el numeral se repite como texto tras el ancla, y en Jn 8 va
                # ademas en cursiva, asi que hay que quitarle las marcas
                if quita_cursiva(resto).rstrip(".") == ancla:
                    resto = ""
            if nuevo is None:
                continue                       # ancla de indice, no de capitulo
            if cap is not None:
                cierra_previo(2)               # lo que quedo suelto es el v. 1
            cap, vers = nuevo, [None]
            caps.setdefault(cap, {})
            l = resto
            if not l:
                continue
        if re.match(r"^[\d\s]+$", l):
            continue                           # tira de enlaces a capitulos
        if es_salmos and PSALMO_RE.match(l):
            continue                           # la cabecera repetida como texto
        if NOTA_RE.match(l):
            notas.append((cap, l))             # las notas de Jeronimo en Daniel
            continue
        if cap is not None:
            l = OMITIDO_RE.sub(marca_omitido, l).strip()
        # en Eclo 1, 20 la edicion abre un parentesis que no cierra nunca y el
        # numeral se queda pegado a el: hay que soltarlo
        l = re.sub(r"^\((\d{1,3}[a-z]?\s)", r"\1", l)
        if not l:
            continue
        if cap is None:
            if tiene_anclas or not re.match(r"^\d{1,3}[a-z]?\s", l):
                continue                       # titulo, cabecera o aparato
            cap, vers = 1, [None]
            caps.setdefault(cap, {})
        for v, txt in trocea(l, vers):
            if v is None:
                if txt:
                    previo.append(txt)         # aun no se sabe de quien es
                continue
            cierra_previo(v[0])
            clave = "%d%s" % v
            caps[cap].setdefault(clave, [])
            if txt:
                caps[cap][clave].append(txt)
    if cap is not None:
        cierra_previo(2)
    return caps, dobles, omitidos, notas


def psalmi_map(dobles):
    """Griego (leccionario) -> hebreo (Nova Vulgata), sacado de la fuente.

    Los parentesis de la edicion dicen, por ejemplo:
        PSALMUS 23 (22)              -> el 22 griego es el 23 hebreo
        PSALMUS 116 (114, 1-9; 115)  -> el 116 hebreo funde 114 y 115 griegos
        PSALMUS 10 (Vg 9, 22-39)     -> el 10 hebreo es la cola del 9 griego
        PSALMUS 114 (113 A)          -> el 113 griego se parte en 114 y 115
    """
    filas = []
    for heb, griego in dobles:
        g = griego.replace("Vg", "").strip()
        for trozo in g.split(";"):
            trozo = trozo.strip()
            if not trozo:
                continue
            m = re.match(r"^(\d+)\s*([AB])?\s*(?:,\s*([\d-]+))?$", trozo)
            if not m:
                filas.append({"griego": trozo, "sufijo": "", "hebreo": heb,
                              "vers_griegos": "", "nota": "SIN PARSEAR"})
                continue
            filas.append({"griego": m.group(1), "sufijo": m.group(2) or "",
                          "hebreo": heb, "vers_griegos": m.group(3) or "",
                          "nota": ""})
    return filas


def main():
    corpus, stichos, dobles_tot, qa = {}, {}, [], []
    omis_filas, cifras_sueltas, notas_tot, tituli = [], [], [], []
    errata = load_errata()
    for nombre, slug in LIBROS:
        es_salmos = (nombre == "Psalmi")
        caps, dobles, omitidos, notas = parse_libro(slug, es_salmos, nombre,
                                                    errata)
        dobles_tot += dobles
        notas_tot += [(nombre, c, t) for c, t in notas]
        for c, v in omitidos:
            omis_filas.append({"libro": nombre, "cap": c, "vers": v})
        omit_set = {(c, v) for c, v in omitidos}

        plano, verso = {}, {}
        for c in sorted(caps):
            pv, vv = {}, {}
            # se conserva el ORDEN DE LA EDICION, que en Ez 40, 42-43 y en
            # 1 Par 4, 18 no es el orden numerico
            for v in caps[c]:
                renglones = [r for r in caps[c][v] if r]
                plana = re.sub(r"\s+", " ", " ".join(renglones)).strip()
                # segunda pasada: las erratas que cruzan el salto de linea
                plana = aplica_errata(plana, nombre, errata)
                # el epigrafe del salmo va en cursiva al principio del v. 1
                mt = re.match(r"^%s\s*(.*?)\s*%s[.,]?\s*" % (CUR_A, CUR_B),
                              plana)
                if es_salmos and mt and mt.group(1):
                    tit = mt.group(1).strip().rstrip(".,") + "."
                    tituli.append({"salmo": c, "vers": v, "titulo": tit})
                pv[v] = quita_cursiva(plana)
                vv[v] = aplica_errata(quita_cursiva("\n".join(renglones)),
                                      nombre, errata)
            plano[str(c)] = pv
            verso[str(c)] = vv
        corpus[nombre] = plano
        stichos[nombre] = verso

        # --- control de calidad ---
        nums = sorted(int(c) for c in plano)
        problemas = []
        esp = EXPECTED.get(nombre)
        if esp is not None and len(nums) != esp:
            problemas.append("capitulos %d, esperados %d" % (len(nums), esp))
        if nums and nums != list(range(1, len(nums) + 1)):
            falta = sorted(set(range(1, max(nums) + 1)) - set(nums))
            problemas.append("capitulos no contiguos, faltan %s" % falta[:10])
        vacios = 0
        for c in plano:
            enteros = sorted(int(v) for v in plano[c] if re.match(r"^\d+$", v))
            if not plano[c]:
                problemas.append("cap %s vacio" % c)
            elif enteros and enteros != list(range(1, len(enteros) + 1)):
                # no es hueco lo que la edicion declara omitido, ni el numero
                # que solo existe partido en letras (1 Par 4, 18a-18b)
                con_letra = {int(re.match(r"\d+", v).group())
                             for v in plano[c] if not v.isdigit()}
                hueco = sorted(v for v in
                               set(range(1, max(enteros) + 1)) - set(enteros)
                               if (int(c), str(v)) not in omit_set
                               and v not in con_letra)
                if hueco:
                    problemas.append("cap %s huecos %s" % (c, hueco[:8]))
            vacios += sum(1 for v in plano[c] if not plano[c][v])
            # una cifra dentro del texto es, casi siempre, un numeral colado
            for v, t in plano[c].items():
                for mm in re.finditer(r"\d+", t):
                    cifras_sueltas.append("%s %s,%s: ...%s..." % (
                        nombre, c, v,
                        t[max(0, mm.start() - 40):mm.end() + 40]))
        if vacios:
            problemas.append("%d versiculos sin texto" % vacios)
        nv = sum(len(x) for x in plano.values())
        letras = sum(1 for c in plano for v in plano[c]
                     if not re.match(r"^\d+$", v))
        linea = "%-24s cap=%3d vers=%5d%s %s" % (
            nombre, len(nums), nv,
            (" letr=%3d" % letras) if letras else "         ",
            ("  <-- " + " | ".join(problemas)) if problemas else "ok")
        qa.append(linea)
        print(linea)

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "nova_vulgata.json"), "w",
              encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=0)
    with open(os.path.join(DATA, "nova_vulgata_stichos.json"), "w",
              encoding="utf-8") as f:
        json.dump(stichos, f, ensure_ascii=False, indent=0)
    with open(os.path.join(DATA, "nova_omissiones.csv"), "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=["libro", "cap", "vers"])
        w.writeheader()
        w.writerows(omis_filas)

    with open(os.path.join(DATA, "nova_psalmi_tituli.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["salmo", "vers", "titulo"])
        w.writeheader()
        w.writerows(tituli)

    filas = psalmi_map(dobles_tot)
    with open(os.path.join(DATA, "psalmi_nova.csv"), "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=["griego", "sufijo", "hebreo",
                                          "vers_griegos", "nota"])
        w.writeheader()
        w.writerows(filas)

    tot_v = sum(len(ch) for b in corpus.values() for ch in b.values())
    resumen = ("\nTOTAL: %d libros, %d capitulos, %d versiculos"
               "\nsalmos con doble numeracion: %d filas en psalmi_nova.csv"
               "\nversiculos que la edicion declara omitidos: %d"
               "\ncifras sueltas dentro del texto: %d"
               "\nepigrafes de salmo recogidos: %d"
               % (len(corpus), sum(len(b) for b in corpus.values()), tot_v,
                  len(filas), len(omis_filas), len(cifras_sueltas),
                  len(tituli)))
    print(resumen)
    sin_usar = [r for r in errata if not r["usos"]]
    if sin_usar:
        print("ERRATAS QUE YA NO SE APLICAN: %s"
              % ", ".join(r["buscar"] for r in sin_usar))
    with open(os.path.join(DATA, "nova_qa.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(qa) + resumen + "\n")
        f.write("\nerratas de la fuente aplicadas:\n")
        for r in errata:
            f.write("   %-18s %-22s -> %-22s x%d  %s\n"
                    % (r["libro"], r["buscar"], r["reemplazar"], r["usos"],
                       r["nota"]))
        f.write("\nnotas del aparato dejadas fuera del texto (%d):\n"
                % len(notas_tot))
        for b, c, t in notas_tot:
            f.write("   %s %s: %s\n" % (b, c, t))
        if cifras_sueltas:
            f.write("\n\nCIFRAS SUELTAS (revisar):\n")
            f.write("\n".join(cifras_sueltas[:200]) + "\n")


if __name__ == "__main__":
    main()
