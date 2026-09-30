"""Fase 9a - Las dos fuentes externas de la acentuacion liturgica.

Para acentuar hace falta saber donde cae el acento tonico, y eso no esta en la
Vulgata: ni el PDF de la Clementina ni la Nova Vulgata de vatican.va traen
acentos. Se traen de dos sitios distintos y complementarios:

1. **El uso liturgico impreso.** Divinum Officium publica el Breviario y el
   Misal romanos en latin *ya acentuados*, y con la misma ortografia clasica que
   usa este proyecto ("Isaíæ", "quǽsumus", "ejus"). Son 6069 ficheros de texto
   con la Escritura, los salmos, las antifonas y las oraciones: el acento tal
   como lo imprimen los libros, no como lo deduciria una regla.

   Se descarga con un clon parcial de git (--filter=blob:none --sparse), asi que
   de un repositorio de 210 MB se bajan solo los 12 MB de las carpetas latinas.

2. **Las cantidades vocalicas.** El fichero de macrones de CLTK, generado con
   Morpheus (Perseus): 755 557 analisis morfologicos con la vocal larga marcada
   ("ju_sto_rum" = jūstōrum). Sirve para lo que el uso liturgico no cubre.

Las dos son cache: si ya estan, no se vuelven a pedir.

Salida:  cache/acentos/divinum/            (corpus liturgico acentuado)
         cache/acentos/macrons.txt         (cantidades vocalicas)
         cache/acentos/crawl.log

Uso:  python src/13a_crawl_acentos.py [--forzar]
"""

import argparse
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "acentos")
DIVINUM = os.path.join(CACHE, "divinum")
MACRONS = os.path.join(CACHE, "macrons.txt")
LOG = os.path.join(CACHE, "crawl.log")

REPO = "https://github.com/DivinumOfficium/divinum-officium.git"
SPARSE = ["web/www/horas/Latin", "web/www/missa/Latin"]
URL_MACRONS = ("https://raw.githubusercontent.com/cltk/latin_models_cltk/"
               "master/taggers/macrons/macrons.txt")
UA = "Lectionarium-Latinum/1.0 (proyecto personal de estudio liturgico)"


def log(msg):
    linea = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(linea)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(linea + "\n")


def git(*args, **kw):
    cwd = kw.pop("cwd", None)
    r = subprocess.run(("git",) + args, cwd=cwd, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit("git %s fallo:\n%s%s"
                         % (" ".join(args), r.stdout, r.stderr))
    return r.stdout


def corpus_liturgico(forzar):
    """Clon parcial y disperso: solo las carpetas latinas, solo sus blobs."""
    try:
        git("--version")
    except FileNotFoundError:
        raise SystemExit("hace falta git en el PATH para traer el corpus "
                         "liturgico de Divinum Officium")
    if os.path.isdir(os.path.join(DIVINUM, ".git")) and not forzar:
        git("fetch", "--depth", "1", "origin", cwd=DIVINUM)
        git("checkout", "-f", "origin/master", cwd=DIVINUM)
        log("divinum-officium: actualizado")
    else:
        if os.path.isdir(DIVINUM):
            raise SystemExit("con --forzar, borra antes cache/acentos/divinum")
        log("divinum-officium: clonando (solo las carpetas latinas)")
        git("clone", "--filter=blob:none", "--no-checkout", "--depth", "1",
            REPO, DIVINUM)
        git("sparse-checkout", "init", "--cone", cwd=DIVINUM)
        git("sparse-checkout", "set", *SPARSE, cwd=DIVINUM)
        git("checkout", cwd=DIVINUM)
    n = tam = 0
    for sub in SPARSE:
        for dp, _, fs in os.walk(os.path.join(DIVINUM, *sub.split("/"))):
            for f in fs:
                if f.endswith(".txt"):
                    n += 1
                    tam += os.path.getsize(os.path.join(dp, f))
    log("divinum-officium: %d ficheros de texto, %.1f MB" % (n, tam / 1e6))
    if not n:
        raise SystemExit("el clon no ha traido ningun .txt latino")


def cantidades(forzar):
    if os.path.exists(MACRONS) and not forzar:
        log("macrons.txt: ya estaba (%.1f MB)" % (os.path.getsize(MACRONS) / 1e6))
        return
    log("macrons.txt: descargando de cltk/latin_models_cltk")
    pet = urllib.request.Request(URL_MACRONS, headers={"User-Agent": UA})
    with urllib.request.urlopen(pet, timeout=180) as fh:
        datos = fh.read()
    with open(MACRONS, "wb") as fh:
        fh.write(datos)
    log("macrons.txt: %.1f MB" % (len(datos) / 1e6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a traerlo todo aunque ya este en cache")
    args = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    sys.stdout.reconfigure(encoding="utf-8")
    corpus_liturgico(args.forzar)
    cantidades(args.forzar)
    log("listo: ahora python src/13b_build_acentos.py")


if __name__ == "__main__":
    main()
