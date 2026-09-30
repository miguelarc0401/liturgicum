"""Fase 1 - Rastreo del Leccionario Koinonia.

Descarga a cache/ las paginas de lecturas de los leccionarios I, II, III, IV y
VII. Reanudable: lo ya descargado no se vuelve a pedir.

El servidor de origen rechaza conexiones de forma intermitente (bloqueo por
rafagas), asi que:
  * se vigila su salud y, si se le da por caido, se tira de Wayback Machine;
  * se resondea el origen al empezar cada pasada;
  * se dan pasadas sucesivas, con espera entre ellas, hasta completar.

La lista de objetivos se arma de tres fuentes que se complementan:
  1. las paginas indice del propio sitio (lo ideal);
  2. derivacion de los ciclos B y C a partir del indice del ciclo A, cuyos
     numeros de archivo son paralelos (1014ACUD01 -> 2014BCUD01 / 3014CCUD01);
  3. el inventario de lo ya archivado en Wayback (CDX API).

Uso:  python src/1_crawl.py [--only 1,2,3,4,7] [--delay 1.5]
                            [--passes 8] [--wait 300] [--targets-only]
"""

import argparse
import gzip
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://servicioskoinonia.org/leccionario/"
WAYBACK = "https://web.archive.org/web/2id_/"
CDX = ("https://web.archive.org/cdx/search/cdx?url=servicioskoinonia.org"
       "/leccionario/texto/*&output=text&fl=original&collapse=urlkey&limit=20000")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
DATA = os.path.join(ROOT, "data")

INDEXES = {
    "1": "texto/1000INDICE.html",
    "2": "texto/2000indice.html",
    "3": "texto/3000indice.html",
    "4": "texto/4000indice.html",
    "7": "texto/7000indice.html",
}
CYCLE_LETTER = {"1": "A", "2": "B", "3": "C"}

UA = "Mozilla/5.0 (compatible; LectionariumLatinum/1.0; research project)"
ORIGIN_TIMEOUT = 10
WAYBACK_TIMEOUT = 90
ORIGIN_DOWN_FOR = 600
ORIGIN_FAIL_LIMIT = 3
WAYBACK_DELAY = 6.0        # archive.org limita fuerte: ~10 peticiones/minuto
WAYBACK_COOLDOWN = 45      # espera tras una conexion rechazada
PROBE = "texto/1000INDICE.html"


def log(msg):
    print(msg)
    sys.stdout.flush()


# --------------------------------------------------------------------------
# red
# --------------------------------------------------------------------------
class Origin:
    def __init__(self):
        self.fails = 0
        self.down_until = 0.0

    def usable(self):
        return time.time() >= self.down_until

    def ok(self):
        self.fails = 0
        self.down_until = 0.0

    def failed(self):
        self.fails += 1
        if self.fails >= ORIGIN_FAIL_LIMIT:
            self.down_until = time.time() + ORIGIN_DOWN_FOR
            self.fails = 0
            log("  ~~ origen declarado caido; Wayback durante %d s" % ORIGIN_DOWN_FOR)

    def probe(self):
        """Fuerza un sondeo del origen; devuelve True si responde."""
        self.down_until = 0.0
        self.fails = 0
        try:
            http_get(BASE + PROBE, ORIGIN_TIMEOUT)
            log("  ~~ el origen RESPONDE")
            return True
        except Exception:
            self.down_until = time.time() + ORIGIN_DOWN_FOR
            log("  ~~ el origen sigue sin responder")
            return False


origin = Origin()


def http_get(url, timeout):
    # algunos nombres de fichero del sitio llevan espacios sin codificar
    url = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%~")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if data[:2] == b"\x1f\x8b":          # Wayback sirve gzip aunque no se pida
        data = gzip.decompress(data)
    return data


def cache_path(rel):
    return os.path.join(CACHE, rel.replace("/", os.sep))


def cached(rel):
    p = cache_path(rel)
    return os.path.exists(p) and os.path.getsize(p) > 0


def store(rel, data):
    p = cache_path(rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


def fetch(rel, delay, allow_wayback=True):
    """bytes de BASE+rel usando cache; None si no se pudo por ninguna via."""
    if cached(rel):
        with open(cache_path(rel), "rb") as f:
            return f.read()

    url = BASE + rel
    if origin.usable():
        try:
            data = http_get(url, ORIGIN_TIMEOUT)
            origin.ok()
            store(rel, data)
            time.sleep(delay)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None                  # no existe: no insistir
            origin.failed()
        except Exception:
            origin.failed()

    if allow_wayback:
        for attempt in range(3):
            try:
                data = http_get(WAYBACK + url, WAYBACK_TIMEOUT)
                store(rel, data)
                time.sleep(WAYBACK_DELAY)
                return data
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None          # no archivada: no insistir
                log("    Wayback HTTP %s en %s" % (e.code, rel))
            except Exception:
                pass
            # conexion rechazada = limite de tasa de archive.org: respirar
            time.sleep(WAYBACK_COOLDOWN * (attempt + 1))
        log("    Wayback no responde para %s" % rel)
    return None


# --------------------------------------------------------------------------
# objetivos
# --------------------------------------------------------------------------
LINK_RE = re.compile(rb'href\s*=\s*"([^"]+?\.html?)(?:#[^"]*)?"', re.I)


def links_from_index(data):
    out, seen = [], set()
    for m in LINK_RE.finditer(data):
        href = m.group(1).decode("latin-1")
        if "/" in href or not re.match(r"^\d{3}", href):
            continue
        if href not in seen:
            seen.add(href)
            out.append(href)
    return out


def derive(href, from_lect, to_lect):
    """1014ACUD01.html -> candidatos para el leccionario destino."""
    stem, ext = os.path.splitext(href)
    seq, rest = stem[:4], stem[4:]
    seq = to_lect + seq[1:]
    src, dst = CYCLE_LETTER[from_lect], CYCLE_LETTER[to_lect]
    cands = []
    if rest[:1] == src:
        cands.append(seq + dst + rest[1:] + ext)     # 2014BCUD01
    cands.append(seq + rest + ext)                    # 2022AVIPAS / comunes
    return cands


def cdx_inventory():
    """Nombres de fichero de texto/ archivados en Wayback."""
    path = os.path.join(DATA, "cdx.txt")
    if not os.path.exists(path):
        log("  descargando inventario CDX de Wayback...")
        try:
            data = http_get(CDX, 180)
        except Exception as e:
            log("  CDX fallo: %s" % e)
            return {}
        os.makedirs(DATA, exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
    names = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            u = line.strip().split(" ")[0]
            if not u:
                continue
            n = u.rsplit("/", 1)[-1]
            if re.match(r"^\d{3}", n) and n.lower().endswith((".html", ".htm")):
                names.setdefault(n[0], set()).add(n)
    return names


def build_targets(wanted, delay):
    targets = {}            # lect -> lista ordenada de href
    source = {}             # lect -> como se obtuvo

    for lect in wanted:
        data = fetch(INDEXES[lect], delay)
        if data is not None and links_from_index(data):
            targets[lect] = links_from_index(data)
            source[lect] = "indice del sitio"
            log("  L%s: %d paginas segun su indice" % (lect, len(targets[lect])))
        else:
            targets[lect] = []
            source[lect] = "pendiente"
            log("  L%s: indice inaccesible" % lect)

    # ciclos B y C derivados del ciclo A
    for lect in ("2", "3"):
        if lect in targets and not targets[lect] and targets.get("1"):
            cands = []
            for href in targets["1"]:
                cands += derive(href, "1", lect)
            targets[lect] = cands
            source[lect] = "derivado del ciclo A (candidatos, se probaran)"
            log("  L%s: %d candidatos derivados del ciclo A" % (lect, len(cands)))

    # union con lo archivado en Wayback
    inv = cdx_inventory()
    for lect in wanted:
        extra = sorted(inv.get(lect, set()) - set(targets.get(lect, [])))
        if extra:
            targets[lect] = targets.get(lect, []) + extra
            source[lect] += " + %d de Wayback" % len(extra)
            log("  L%s: +%d paginas conocidas por Wayback" % (lect, len(extra)))

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "targets.json"), "w", encoding="utf-8") as f:
        json.dump({"source": source, "targets": targets}, f,
                  ensure_ascii=False, indent=1)
    return targets


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="1,2,3,4,7")
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--passes", type=int, default=8)
    ap.add_argument("--wait", type=int, default=300)
    ap.add_argument("--targets-only", action="store_true")
    ap.add_argument("--anexos", action="store_true",
                    help="solo las paginas de anexo que aun faltan, tomadas "
                         "del catalogo de 16_parse_anexos.py")
    args = ap.parse_args()

    wanted = [x.strip() for x in args.only.split(",") if x.strip()]

    if args.anexos:
        # Las tres que el origen no ha llegado a servir nunca. Tienen espacios
        # en el nombre, que http_get ya codifica; no es eso lo que falla, sino
        # que el servidor rechaza la conexion (ver §2.7).
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "anexos", os.path.join(ROOT, "src", "16_parse_anexos.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        todo = [("7", "texto/" + h)
                for cat in mod.CATALOGO for h in cat["archivos"]
                if not cached("texto/" + h)]
        log("=== %d paginas de anexo pendientes ===" % len(todo))
        if not todo:
            log("No falta ninguna.")
            return
    else:
        log("=== armando lista de objetivos ===")
        targets = build_targets(wanted, args.delay)
        todo = [(l, "texto/" + h) for l in wanted for h in targets.get(l, [])]
    log("=== %d paginas objetivo ===" % len(todo))
    if args.targets_only:
        return

    dead = set()        # 404 confirmados: no se reintentan
    for p in range(1, args.passes + 1):
        missing = [(l, r) for l, r in todo if not cached(r) and r not in dead]
        if not missing:
            log("\nNada pendiente.")
            break
        log("\n--- pasada %d: %d pendientes ---" % (p, len(missing)))
        if p > 1:
            origin.probe()
        for i, (lect, rel) in enumerate(missing, 1):
            got = fetch(rel, args.delay)
            if got is not None:
                log("  [%3d/%3d] L%s ok %s (%d B)"
                    % (i, len(missing), lect, rel.split("/")[-1], len(got)))
        if p < args.passes:
            time.sleep(args.wait)

    missing = [r for _, r in todo if not cached(r)]
    log("\n=== FIN === en cache: %d / %d   faltan: %d"
        % (len(todo) - len(missing), len(todo), len(missing)))
    with open(os.path.join(CACHE, "missing.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(missing))


if __name__ == "__main__":
    main()
