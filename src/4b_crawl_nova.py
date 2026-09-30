"""Fase 4b (1/2) - Descarga del texto de la NOVA VULGATA desde vatican.va.

La Nova Vulgata (editio typica altera, 1986) es el texto latino que usan los
libros liturgicos actuales: el Ordo lectionum Missae de 1981 sustituyo por ella
la Vulgata que traia la edicion de 1969. La Santa Sede la publica integra en
73 paginas HTML, una por libro, con el texto completo dentro de cada pagina.

Politica de descarga: una peticion cada 2 s, cache en disco (nunca se vuelve a
pedir lo ya guardado), reintentos con retroceso. 73 paginas -> ~3 min.

Salida: cache/nova/<clave>.html  +  cache/nova/crawl.log

Uso:  python src/4b_crawl_nova.py [--pausa 2.0] [--forzar]
"""

import argparse
import os
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "nova")
BASE = "https://www.vatican.va/archive/bible/nova_vulgata/documents/"
UA = "Lectionarium-Latinum/1.0 (proyecto personal de estudio liturgico)"

# clave -> nombre del fichero en vatican.va (sin el prefijo nova-vulgata_ ni
# el sufijo _lt.html). El orden es el canonico, que es el de la propia edicion.
LIBROS = [
    # --- Vetus Testamentum ---
    ("Genesis", "vt_genesis"),
    ("Exodus", "vt_exodus"),
    ("Leviticus", "vt_leviticus"),
    ("Numeri", "vt_numeri"),
    ("Deuteronomium", "vt_deuteronomii"),
    ("Iosue", "vt_iosue"),
    ("Iudicum", "vt_iudicum"),
    ("Ruth", "vt_ruth"),
    ("I Samuelis", "vt_i-samuelis"),
    ("II Samuelis", "vt_ii-samuelis"),
    ("I Regum", "vt_i-regum"),
    ("II Regum", "vt_ii-regum"),
    ("I Paralipomenon", "vt_i-paralipomenon"),
    ("II Paralipomenon", "vt_ii-paralipomenon"),
    ("Esdrae", "vt_esdrae"),
    ("Nehemiae", "vt_nehemiae"),
    ("Thobis", "vt_thobis"),
    ("Iudith", "vt_iudith"),
    ("Esther", "vt_esther"),
    ("Iob", "vt_iob"),
    ("Psalmi", "vt_psalmorum"),
    ("Proverbia", "vt_proverbiorum"),
    ("Ecclesiastes", "vt_ecclesiastes"),
    ("Canticum Canticorum", "vt_canticum-canticorum"),
    ("Sapientia", "vt_sapientiae"),
    ("Ecclesiasticus", "vt_ecclesiasticus"),
    ("Isaias", "vt_isaiae"),
    ("Ieremias", "vt_ieremiae"),
    ("Lamentationes", "vt_lamentationes"),
    ("Baruch", "vt_baruch"),
    ("Ezechiel", "vt_ezechielis"),
    ("Daniel", "vt_danielis"),
    ("Osee", "vt_osee"),
    ("Ioel", "vt_ioel"),
    ("Amos", "vt_amos"),
    ("Abdias", "vt_abdiae"),
    ("Ionas", "vt_ionae"),
    ("Michaeas", "vt_michaeae"),
    ("Nahum", "vt_nahum"),
    ("Habacuc", "vt_habacuc"),
    ("Sophonias", "vt_sophoniae"),
    ("Aggaeus", "vt_aggaei"),
    ("Zacharias", "vt_zachariae"),
    ("Malachias", "vt_malachiae"),
    ("I Maccabaeorum", "vt_i-maccabaeorum"),
    ("II Maccabaeorum", "vt_ii-maccabaeorum"),
    # --- Novum Testamentum ---
    ("Matthaeus", "nt_evang-matthaeum"),
    ("Marcus", "nt_evang-marcum"),
    ("Lucas", "nt_evang-lucam"),
    ("Ioannes", "nt_evang-ioannem"),
    ("Actus Apostolorum", "nt_actus-apostolorum"),
    ("Ad Romanos", "nt_epist-romanos"),
    ("I Ad Corinthios", "nt_epist-i-corinthios"),
    ("II Ad Corinthios", "nt_epist-ii-corinthios"),
    ("Ad Galatas", "nt_epist-galatas"),
    ("Ad Ephesios", "nt_epist-ephesios"),
    ("Ad Philippenses", "nt_epist-philippenses"),
    ("Ad Colossenses", "nt_epist-colossenses"),
    ("I Ad Thessalonicenses", "nt_epist-i-thessalonicenses"),
    ("II Ad Thessalonicenses", "nt_epist-ii-thessalonicenses"),
    ("I Ad Timotheum", "nt_epist-i-timotheum"),
    ("II Ad Timotheum", "nt_epist-ii-timotheum"),
    ("Ad Titum", "nt_epist-titum"),
    ("Ad Philemonem", "nt_epist-philemonem"),
    ("Ad Hebraeos", "nt_epist-hebraeos"),
    ("Iacobi", "nt_epist-iacobi"),
    ("I Petri", "nt_epist-i-petri"),
    ("II Petri", "nt_epist-ii-petri"),
    ("I Ioannis", "nt_epist-i-ioannis"),
    ("II Ioannis", "nt_epist-ii-ioannis"),
    ("III Ioannis", "nt_epist-iii-ioannis"),
    ("Iudae", "nt_epist-iudae"),
    ("Apocalypsis", "nt_epist-apocalypsis"),
]

# la pagina del Apocalipsis no sigue el patron de las demas epistolas
ALIAS = {"nt_epist-apocalypsis": "nt_apocalypsis-ioannis"}


def url_de(slug):
    return BASE + "nova-vulgata_" + ALIAS.get(slug, slug) + "_lt.html"


def descarga(url, intentos=4):
    espera = 5
    for n in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except (urllib.error.URLError, OSError) as e:
            if n == intentos - 1:
                raise
            print("      fallo (%s); reintento en %ds" % (e, espera))
            time.sleep(espera)
            espera *= 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pausa", type=float, default=2.0)
    ap.add_argument("--forzar", action="store_true",
                    help="vuelve a pedir incluso lo que ya esta en cache")
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    log = []
    nuevos = cacheados = fallos = 0

    for i, (nombre, slug) in enumerate(LIBROS, 1):
        destino = os.path.join(CACHE, slug + ".html")
        if os.path.exists(destino) and not args.forzar:
            cacheados += 1
            continue
        url = url_de(slug)
        try:
            datos = descarga(url)
        except Exception as e:                                # noqa: BLE001
            fallos += 1
            log.append("FALLO %-32s %s  %s" % (nombre, url, e))
            print("%3d/%d  FALLO   %-24s %s" % (i, len(LIBROS), nombre, e))
            continue
        with open(destino, "wb") as f:
            f.write(datos)
        nuevos += 1
        log.append("OK    %-32s %7d B  %s" % (nombre, len(datos), url))
        print("%3d/%d  %-24s %7d B" % (i, len(LIBROS), nombre, len(datos)))
        time.sleep(args.pausa)

    resumen = "\nnuevos %d · ya en cache %d · fallos %d · total %d" % (
        nuevos, cacheados, fallos, len(LIBROS))
    print(resumen)
    with open(os.path.join(CACHE, "crawl.log"), "a", encoding="utf-8") as f:
        f.write("\n".join(log) + resumen + "\n")


if __name__ == "__main__":
    main()
