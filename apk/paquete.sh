#!/usr/bin/env bash
# La huella de la app y el paquete que se baja el APK. Lo corre GitHub
# Actions, no hace falta correrlo a mano (ver apk/LEEME.md).
#
#   apk/paquete.sh          escribe app/paquete-version.json
#   apk/paquete.sh --zip    y además app/paquete.zip y app/paquete.json
#
# La huella sale de todo lo que hay en app/ -datos, app.js, estilos, iconos-,
# así que cambia con cualquier cosa que se publique. El APK lleva dentro la
# suya en paquete-version.json, y la compara con la de paquete.json, que se
# publica en GitHub Pages junto a la web: si no son la misma, se baja
# paquete.zip. Nada de esto entra en git -16 MB por publicación hincharían
# la historia para siempre-: se hace al publicar y se queda en Pages.
set -euo pipefail
cd "$(dirname "$0")/../app"

rm -f paquete.zip paquete.json paquete-version.json

VERSION=$(find . -type f ! -name LEEME.md -print0 | LC_ALL=C sort -z \
  | xargs -0 sha256sum | sha256sum | cut -c1-16)
printf '{"version":"%s"}\n' "$VERSION" > paquete-version.json

if [ "${1:-}" = "--zip" ]; then
  # la raíz del zip es la de la app, con index.html arriba, que es lo que
  # pide el actualizador
  zip -q -r -X -9 paquete.zip . -x LEEME.md -x paquete.zip -x paquete.json
  SUMA=$(sha256sum paquete.zip | cut -d' ' -f1)
  BYTES=$(stat -c %s paquete.zip)
  printf '{"version":"%s","zip":"paquete.zip","sha256":"%s","bytes":%s}\n' \
    "$VERSION" "$SUMA" "$BYTES" > paquete.json
  echo "paquete.zip: $BYTES bytes"
fi
echo "version $VERSION"
