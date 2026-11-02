# -*- coding: utf-8 -*-
"""Las erratas que manda el teléfono, aplicadas por GitHub sin el ordenador.

El teléfono de quien edita el libro (app/erratas.js, con su llave de GitHub
puesta en Ajustes) no puede reescribir los datos de la app, que son 55 MB:
deja un pedido pequeño en data/erratas_pendientes/<id>.json, y el proceso de
GitHub (.github/workflows/erratas.yml) corre esto, que con cada pedido hace
lo mismo que el editor del ordenador (src/erratas.py): busca el texto en
app/datos/, lo corrige y lo apunta en data/fe_de_erratas/<id>.json —o lo
deshace—, y luego firma otra vez app/datos/version.js (src/firma.py) para
que los teléfonos se enteren de que hay textos nuevos. El pedido se borra;
si no se ha podido hacer, queda en data/erratas_rechazadas/<id>.json con el
motivo, que el teléfono enseña en su lista de erratas.

    python src/erratas_telefono.py

Escribe en $GITHUB_OUTPUT `hecho=1` si ha cambiado algo que publicar.
"""

import datetime
import io
import json
import os
import sys

import erratas
import firma

PENDIENTES = os.path.join(erratas.RAIZ, 'data', 'erratas_pendientes')
RECHAZADAS = os.path.join(erratas.RAIZ, 'data', 'erratas_rechazadas')


def rechaza(nombre, pedido, motivo):
    os.makedirs(RECHAZADAS, exist_ok=True)
    with io.open(os.path.join(RECHAZADAS, nombre), 'w', encoding='utf-8',
                 newline='\n') as fh:
        json.dump({'id': pedido.get('id'), 'accion': pedido.get('accion'),
                   'errata': pedido.get('errata'),
                   'fecha': datetime.date.today().isoformat(),
                   'motivo': motivo}, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('  rechazada %s: %s' % (nombre, motivo))


def main():
    # la consola de Windows, si se corre a mano
    sys.stdout.reconfigure(errors='replace')
    if not os.path.isdir(PENDIENTES):
        print('No hay pedidos del teléfono.')
        return
    pedidos = []
    for nombre in sorted(os.listdir(PENDIENTES)):
        if not nombre.endswith('.json'):
            continue
        ruta = os.path.join(PENDIENTES, nombre)
        try:
            with io.open(ruta, encoding='utf-8') as fh:
                pedido = json.load(fh)
            if not isinstance(pedido, dict):
                raise ValueError
        except ValueError:
            rechaza(nombre, {}, 'El pedido llegó mal escrito.')
            os.remove(ruta)
            continue
        pedidos.append((nombre, ruta, pedido))
    # en el orden en que se hicieron, no en el de su nombre: corregir y
    # deshacer enseguida llegan juntos, y deshacer ha de ir detrás
    pedidos.sort(key=lambda x: (str(x[2].get('creado') or ''), x[0]))
    pub = erratas.Publicados()
    hechos = 0
    for nombre, ruta, pedido in pedidos:
        print('%s (%s)' % (nombre, pedido.get('accion') or 'corregir'))
        try:
            if pedido.get('accion') == 'deshacer':
                erratas.deshace(pub, str(pedido.get('errata') or ''))
            else:
                eid = pedido.get('id')
                if nombre != '%s.json' % eid:
                    raise erratas.Fallo('El pedido no se llama como su id.')
                erratas.corrige(pub, {k: pedido.get(k) for k in (
                    'texto', 'nuevo', 'antes', 'despues', 'otros')},
                    eid=eid, desde='teléfono')
            hechos += 1
        except erratas.Fallo as e:
            rechaza(nombre, pedido, str(e))
        os.remove(ruta)
    if hechos:
        print('firma de los datos: %s' % firma.escribe())
    salida = os.environ.get('GITHUB_OUTPUT')
    if salida:
        with open(salida, 'a', encoding='utf-8') as fh:
            fh.write('hecho=%d\n' % (1 if pedidos else 0))
    print('%d pedido(s), %d hecho(s).' % (len(pedidos), hechos))


if __name__ == '__main__':
    main()
