"""Fase 1b - Rastreo por proxy de lectura (r.jina.ai).

El servidor de origen dejo de aceptar conexiones desde esta red (TCP sin
respuesta, comprobado: curl agota el tiempo en el saludo), y Wayback solo tiene
64 de las ~350 paginas de los leccionarios V, VI, VIII y IX. El sitio, sin
embargo, esta en pie: responde a traves de un proxy de lectura.

Este modulo baja las paginas por ese camino y las deja en cache/texto con la
MISMA codificacion de byte que las 757 que ya habia (cp1252), para que
2_parse_readings.py no note la diferencia.

Uso:  python src/1b_crawl_proxy.py --index 5,6,8,9     (indices + objetivos)
      python src/1b_crawl_proxy.py --fetch             (baja lo que falte)
"""

import argparse
import html as htmlmod
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
DATA = os.path.join(ROOT, "data")
SITE = "https://servicioskoinonia.org/leccionario/"
PROXY = "https://r.jina.ai/"

# los cuatro leccionarios que faltaban y su pagina indice, sacada del frameset
# Libro_0N.html de cada uno
INDICES = {
    "5": "texto/500indice.html",
    "6": "texto/6000indice.html",
    "8": "texto/8000indice.html",
    "9": "texto/9000INDICE.html",
}

UA = "Mozilla/5.0 (compatible; LectionariumLatinum/1.0; research project)"
DELAY = 2.5
TIMEOUT = 120
REINTENTOS = 4


def log(msg):
    print(msg)
    sys.stdout.flush()


def fetch(rel):
    """La pagina rel del sitio, en bytes cp1252 como el resto del cache."""
    url = PROXY + SITE + urllib.parse.quote(rel, safe="/")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "x-return-format": "html",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
    txt = raw.decode("utf-8", errors="replace")
    if "<body" not in txt.lower():
        raise ValueError("respuesta sin cuerpo HTML (%d bytes)" % len(txt))
    # el proxy sirve utf-8; el cache del proyecto es cp1252. Lo que no quepa en
    # cp1252 se guarda como entidad, que strip_tags() deshace despues.
    return txt.encode("cp1252", errors="xmlcharrefreplace")


def cache_path(rel):
    return os.path.join(CACHE, rel.replace("/", os.sep))


def guarda(rel, data):
    p = cache_path(rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def baja(rel, forzar=False):
    """Deja rel en cache. Devuelve True si esta, False si no se pudo."""
    p = cache_path(rel)
    if not forzar and os.path.exists(p) and os.path.getsize(p) > 200:
        return True
    for intento in range(1, REINTENTOS + 1):
        try:
            guarda(rel, fetch(rel))
            return True
        except Exception as e:
            log("    intento %d/%d %s: %s" % (intento, REINTENTOS, rel, e))
            time.sleep(DELAY * intento * 2)
    return False


HREF_RE = re.compile(r'href\s*=\s*"([^"#]+\.html?)"', re.I)


def objetivos_del_indice(libro, rel_indice):
    """Los ficheros de lecturas que enlaza la pagina indice de un leccionario."""
    raw = open(cache_path(rel_indice), "rb").read().decode("cp1252", "replace")
    vistos, fuera = [], set()
    for href in HREF_RE.findall(raw):
        href = htmlmod.unescape(href).strip()
        if href.startswith(("http:", "https:", "mailto:", "javascript:")):
            continue
        nombre = href.split("/")[-1]
        if not nombre or not nombre[0].isdigit():
            continue
        if not nombre.startswith(libro):
            fuera.add(nombre)
            continue
        if nombre not in vistos:
            vistos.append(nombre)
    return vistos, sorted(fuera)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="", help="libros cuyo indice bajar, p.ej. 5,6,8,9")
    ap.add_argument("--fetch", action="store_true", help="bajar los objetivos")
    ap.add_argument("--delay", type=float, default=DELAY)
    args = ap.parse_args()

    globals()["DELAY"] = args.delay

    ruta_t = os.path.join(DATA, "targets_extra.json")
    tabla = {}
    if os.path.exists(ruta_t):
        tabla = json.load(open(ruta_t, encoding="utf-8"))

    if args.index:
        for libro in [x.strip() for x in args.index.split(",") if x.strip()]:
            rel = INDICES[libro]
            log("indice del leccionario %s: %s" % (libro, rel))
            if not baja(rel, forzar=True):
                log("  !! no se pudo bajar el indice")
                continue
            objs, fuera = objetivos_del_indice(libro, rel)
            log("  %d objetivos" % len(objs))
            if fuera:
                log("  enlaces a otros libros (no se bajan aqui): %s"
                    % ", ".join(fuera[:8]))
            tabla[libro] = {"indice": rel, "objetivos": objs, "ajenos": fuera}
            time.sleep(DELAY)
        with open(ruta_t, "w", encoding="utf-8") as f:
            json.dump(tabla, f, ensure_ascii=False, indent=1)
        log("escrito %s" % ruta_t)

    if args.fetch:
        pend = []
        for libro, info in sorted(tabla.items()):
            for nombre in info["objetivos"]:
                rel = "texto/" + nombre
                if not os.path.exists(cache_path(rel)) or \
                        os.path.getsize(cache_path(rel)) <= 200:
                    pend.append(rel)
        log("pendientes: %d" % len(pend))
        fallos = []
        for i, rel in enumerate(pend, 1):
            ok = baja(rel)
            log("  [%d/%d] %s %s" % (i, len(pend), rel, "ok" if ok else "FALLO"))
            if not ok:
                fallos.append(rel)
            time.sleep(DELAY)
        with open(os.path.join(CACHE, "missing_extra.txt"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(fallos))
        log("=== FIN === faltan %d (cache/missing_extra.txt)" % len(fallos))


if __name__ == "__main__":
    main()
