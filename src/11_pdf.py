"""Fase 6d - PDF a partir de los .docx ya generados.

Convierte con LibreOffice en modo consola. La conversion conserva lo que hace
falta para leer el leccionario en pantalla y en papel: los hipervinculos del
indice pasan a enlaces internos del PDF, los estilos de titulo a marcadores
del navegador, y los campos PAGEREF del indice se calculan al abrir, asi que
los numeros de pagina salen ya resueltos.

Cada perfil de maquetacion tiene su carpeta:

    out/carta/*.docx  ->  out/pdf/carta/*.pdf
    out/media/*.docx  ->  out/pdf/media/*.pdf

Usa un perfil de usuario aparte, asi que funciona aunque tengas LibreOffice
abierto.

Uso:  python src/11_pdf.py                     (los dos perfiles, todo)
      python src/11_pdf.py --perfil media
      python src/11_pdf.py --solo Leccionario_I_Domingos_cicloA.docx
      python src/11_pdf.py --soffice "C:/ruta/soffice.exe"
"""

import argparse
import glob
import importlib.util
import os
import re
import subprocess
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
PDF = os.path.join(OUT, "pdf")
PERFILES = ["carta", "media"]

CANDIDATOS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice", "/usr/local/bin/soffice", "soffice",
]


def canonicos(carpeta):
    """Los documentos del proyecto, sin muestras ni restos de otras pasadas."""
    spec = importlib.util.spec_from_file_location(
        "r8", os.path.join(ROOT, "src", "8_render.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    nombres = [mod.ARCHIVO_ANUAL + ".docx"]
    nombres += [mod.ARCHIVO_LECT[l] + ".docx" for l in mod.ORDEN_LECT]
    nombres.append("lectionarium.docx")
    return [os.path.join(carpeta, n) for n in nombres
            if os.path.exists(os.path.join(carpeta, n))]


def busca_soffice(dado=None):
    for c in ([dado] if dado else []) + CANDIDATOS:
        if c and (os.path.exists(c) or c == "soffice"):
            return c
    raise SystemExit("no encuentro LibreOffice; pasalo con --soffice RUTA")


def convierte(soffice, ruta, destino, perfil_lo):
    t0 = time.time()
    os.makedirs(destino, exist_ok=True)
    cmd = [soffice, "-env:UserInstallation=file:///%s"
           % perfil_lo.replace("\\", "/").lstrip("/"),
           "--headless", "--norestore", "--convert-to", "pdf",
           "--outdir", destino, ruta]
    r = subprocess.run(cmd, capture_output=True, text=True)
    salida = os.path.join(destino,
                          re.sub(r"\.docx$", ".pdf", os.path.basename(ruta)))
    if not os.path.exists(salida):
        print("  FALLO %s\n%s%s" % (os.path.basename(ruta), r.stdout, r.stderr))
        return None
    raw = open(salida, "rb").read()
    print("%-62s %6d KB · %4d enlaces internos · %.0fs"
          % (salida[len(OUT) + 1:], len(raw) // 1024, raw.count(b"/Link"),
             time.time() - t0))
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--soffice", default=None)
    ap.add_argument("--perfil", default="ambos",
                    choices=PERFILES + ["ambos"])
    ap.add_argument("--solo", default=None, help="un solo nombre de .docx")
    ap.add_argument("--fuente", default="clementina",
                    choices=["clementina", "nova"],
                    help="convierte los .docx de out/ o los de out/nova/")
    ap.add_argument("--todos", action="store_true",
                    help="cualquier .docx de la carpeta, no solo los del "
                         "proyecto")
    args = ap.parse_args()
    global OUT, PDF
    if args.fuente == "nova":
        OUT = os.path.join(OUT, "nova")
        PDF = os.path.join(OUT, "pdf")

    soffice = busca_soffice(args.soffice)
    claves = PERFILES if args.perfil == "ambos" else [args.perfil]

    with tempfile.TemporaryDirectory(prefix="lo_profile_") as perfil_lo:
        for clave in claves:
            carpeta = os.path.join(OUT, clave)
            if not os.path.isdir(carpeta):
                print("no hay %s; salta" % carpeta[len(ROOT) + 1:])
                continue
            if args.solo:
                rutas = [os.path.join(carpeta, args.solo)]
            elif args.todos:
                rutas = sorted(glob.glob(os.path.join(carpeta, "*.docx")))
            else:
                rutas = canonicos(carpeta)
            rutas = [r for r in rutas
                     if os.path.exists(r)
                     and not os.path.basename(r).startswith("~$")]
            if not rutas:
                print("no hay .docx en %s" % carpeta[len(ROOT) + 1:])
                continue
            for ruta in rutas:
                convierte(soffice, ruta, os.path.join(PDF, clave), perfil_lo)


if __name__ == "__main__":
    main()
