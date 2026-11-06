# -*- coding: utf-8 -*-
"""La firma de los datos de la app: app/datos/version.js.

El service worker del teléfono guarda la app entera en caché, y lo que le
obliga a tirarla y bajar la nueva es que cambie esta firma. Sale de todo lo
que hay en app/datos/ y del código de la app, así que cambia con cualquier
cosa que se publique. La escribe src/15_app_data.py al final de cada pasada,
y src/erratas_telefono.py cuando GitHub aplica una errata que manda el
teléfono: si no, el texto corregido llegaría a la web y el teléfono seguiría
rezando con el de antes.
"""

import os
import zlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, 'app')
DATOS = os.path.join(APP, 'datos')

# El código de la app, que también entra en la firma (Breviarium/src/4_app.py
# y Missale/src/6_app.py llevan su propia lista). Los iconos entran aunque no
# los escriba nadie: si no, se cambia la tapa y el teléfono sigue enseñando
# la de antes, porque el service worker los tiene cacheados y nada le dice
# que ha cambiado nada.
CODIGO_APP = ['index.html', 'app.js', 'piper.js', 'estilos.css',
              'devo-vistas.js', 'devo-vistas.css', 'recorrido.js',
              'recorrido.css', 'parvo.js', 'parvo.css', 'erratas.js',
              'erratas.css', 'manifest.webmanifest',
              'icono.svg', 'icono-32.png', 'icono-180.png', 'icono-192.png',
              'icono-512.png', 'icono-maskable-512.png']


def escribe(fuentes=('clementina', 'nova')):
    """Escribe app/datos/version.js y devuelve la firma. El rótulo nombra
    las versiones latinas que la app sirve —las que tienen su
    lecturas_*.json—, no sólo las que escribió quien firma."""
    latinas = sorted(f[len('lecturas_'):-len('.json')]
                     for f in os.listdir(DATOS)
                     if f.startswith('lecturas_') and f.endswith('.json')
                     and f != 'lecturas_es.json')
    version = '%s-%d' % (
        '+'.join(latinas or fuentes),
        zlib.crc32(b''.join(open(os.path.join(DATOS, f), 'rb').read()
                            for f in sorted(os.listdir(DATOS))
                            if f != 'version.js')
                   + b''.join(open(os.path.join(APP, f), 'rb').read()
                              for f in CODIGO_APP
                              if os.path.exists(os.path.join(APP, f))))
        & 0xffffffff)
    with open(os.path.join(DATOS, 'version.js'), 'w', encoding='utf-8') as fh:
        fh.write('// lo escribe src/15_app_data.py; cambia con los datos, y al\n'
                 '// cambiar obliga al service worker a rehacer su cache\n'
                 'self.VERSION_DATOS = "%s";\n' % version)
    return version
