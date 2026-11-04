#!/usr/bin/env bash
# La huella de la app y el paquete que se baja el APK. Lo corre GitHub
# Actions, no hace falta correrlo a mano (ver apk/LEEME.md).
#
#   apk/paquete.sh          escribe app/paquete-version.json
#   apk/paquete.sh --zip    y además app/paquete.zip, app/paquete.json y los
#                           .br de los ficheros grandes
#
# La huella sale de todo lo que hay en app/ -datos, app.js, estilos, iconos-,
# así que cambia con cualquier cosa que se publique. El APK lleva dentro la
# suya en paquete-version.json, y la compara con la de paquete.json, que se
# publica en GitHub Pages junto a la web: si no son la misma, se pone al día.
# Nada de esto entra en git -16 MB por publicación hincharían la historia
# para siempre-: se hace al publicar y se queda en Pages.
set -euo pipefail
cd "$(dirname "$0")/../app"

rm -f paquete.zip paquete.json paquete-version.json
# los .br de otra vez no son de la app: se rehacen abajo
find . -type f -name '*.br' -delete

VERSION=$(find . -type f ! -name LEEME.md -print0 | LC_ALL=C sort -z \
  | xargs -0 sha256sum | sha256sum | cut -c1-16)
printf '{"version":"%s"}\n' "$VERSION" > paquete-version.json

if [ "${1:-}" = "--zip" ]; then
  # la raíz del zip es la de la app, con index.html arriba, que es lo que
  # pide el actualizador. Lo bajan los APK con un app.js de antes de la
  # lista de ficheros (2026-11-03), que no saben pedir otra cosa.
  zip -q -r -X -9 paquete.zip . -x LEEME.md -x paquete.zip -x paquete.json
  SUMA=$(sha256sum paquete.zip | cut -d' ' -f1)
  BYTES=$(stat -c %s paquete.zip)

  # La lista de ficheros, cada uno con su huella: con ella el actualizador
  # pone lo que ya tiene -lo que trae el APK, lo bajado otras veces- y baja
  # sólo lo que ha cambiado, que en una publicación de las de cada día es
  # app.js y poco más. Los de texto grandes van también en brotli: el
  # actualizador los descomprime y los comprueba contra la huella del
  # fichero ya descomprimido (horas.json pasa de 23 MB a 1,7), y si la
  # descarga se corta sigue por donde iba, sobre lo comprimido. El ?v= es
  # para que la caché de GitHub Pages no dé un fichero de la vez anterior.
  BROTLI=$(command -v brotli || true)
  ENTRADAS=()
  while IFS= read -r -d '' f; do
    f=${f#./}
    h=$(sha256sum "$f" | cut -c1-64)
    nombre=$f
    case "$f" in
      *.json|*.js|*.css|*.html|*.svg|*.webmanifest|*.txt)
        if [ -n "$BROTLI" ] && [ "$(stat -c %s "$f")" -ge 32768 ]; then
          brotli -q 9 -f -o "$f.br" "$f"
          nombre=$f.br
        fi ;;
    esac
    ENTRADAS+=("{\"file_name\":\"$nombre\",\"file_hash\":\"$h\",\"download_url\":\"$nombre?v=${h:0:16}\"}")
  done < <(find . -type f ! -name LEEME.md ! -name paquete.zip ! -name '*.br' \
             -print0 | LC_ALL=C sort -z)
  FICHEROS=$(IFS=,; echo "${ENTRADAS[*]}")

  printf '{"version":"%s","zip":"paquete.zip","sha256":"%s","bytes":%s,"ficheros":[%s]}\n' \
    "$VERSION" "$SUMA" "$BYTES" "$FICHEROS" > paquete.json
  echo "paquete.zip: $BYTES bytes; ${#ENTRADAS[@]} ficheros en la lista" \
    "${BROTLI:+(los grandes, también en brotli)}"
fi
echo "version $VERSION"
