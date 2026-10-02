# -*- coding: utf-8 -*-
"""Los iconos de la app instalada.

Un icono de pantalla de inicio se ve a 48 píxeles y entre otros cuarenta:
o se reconoce de un vistazo o no sirve. Así que aquí no hay dibujo, hay
marca: el campo rojo del leccionario, una cruz de oro con los brazos
ligeramente abiertos —la de los cantorales, no la de palos rectos— y, al
pie, la cinta del breviario, que es lo que distingue a este libro de
cualquier otro.

Se dibuja en grande y se reduce, que es lo que le da el filo.

    python src/19_iconos.py
"""

import os

from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, 'app')

GRANDE = 1024                      # se dibuja aquí y se reduce
CAMPO = (107, 18, 32)              # el rojo de la app (--acento)
CAMPO_HONDO = (74, 10, 21)         # el mismo, al fondo del degradado
ORO = (218, 182, 106)
ORO_CLARO = (238, 212, 150)
CINTA = (198, 150, 84)


def degradado(tam, arriba, abajo):
    """El campo, de un rojo a otro: plano se ve muerto."""
    img = Image.new('RGB', (1, tam))
    px = img.load()
    for y in range(tam):
        t = y / (tam - 1)
        px[0, y] = tuple(round(a + (b - a) * t) for a, b in zip(arriba, abajo))
    return img.resize((tam, tam))


def cruz(d, tam, color, cx, cy):
    """Una cruz de brazos apenas abiertos hacia las puntas, como la de los
    cantorales: recta de lejos, viva de cerca."""
    g, G = tam * 0.030, tam * 0.040        # medio grueso, al centro y al fin
    alto, ancho = tam * 0.225, tam * 0.195  # medio alto y medio ancho
    y = cy - tam * 0.022                    # el travesano, algo por encima
    d.polygon([(cx - ancho, y - G), (cx - g, y - g), (cx + g, y - g),
               (cx + ancho, y - G), (cx + ancho, y + G), (cx + g, y + g),
               (cx - g, y + g), (cx - ancho, y + G)], fill=color)
    d.polygon([(cx - G, cy - alto), (cx + G, cy - alto),
               (cx + g, y), (cx + G, cy + alto * 1.3),
               (cx - G, cy + alto * 1.3), (cx - g, y)], fill=color)


def cinta(d, tam, color):
    """La cinta del breviario, saliendo de la tapa con su corte en pico."""
    x = tam * 0.705
    an = tam * 0.025
    arriba, abajo = tam * 0.58, tam * 0.955
    d.polygon([(x - an, arriba), (x + an, arriba), (x + an, abajo),
               (x, abajo - an * 1.6), (x - an, abajo)], fill=color)


def dibuja(tam, sangre):
    """El icono. `sangre` lo lleva a los bordes, para el recorte de Android;
    si no, se le redondean las esquinas.

    La tapa es el filete de oro; de ella sale la cinta, y dentro va la cruz:
    el que lo mire vera una cruz, y el que lo mire dos veces, un libro."""
    img = degradado(GRANDE, CAMPO, CAMPO_HONDO).convert('RGBA')
    escala = 1.0 if sangre else 0.88           # la zona segura del maskable
    lado = GRANDE * escala
    capa = Image.new('RGBA', (GRANDE, GRANDE), (0, 0, 0, 0))
    dc = ImageDraw.Draw(capa)
    # la tapa
    m = lado * 0.085
    dc.rounded_rectangle([m, m, lado - m, lado - m],
                         radius=lado * 0.055, outline=ORO, width=round(lado * 0.011))
    # la cinta sale de dentro y cruza la tapa: se dibuja encima del filete
    cinta(dc, lado, CINTA)
    cruz(dc, lado, ORO, lado * 0.5, lado * 0.47)
    off = int((GRANDE - lado) / 2)
    img.alpha_composite(capa, (off, off))

    if not sangre:
        mascara = Image.new('L', (GRANDE, GRANDE), 0)
        ImageDraw.Draw(mascara).rounded_rectangle(
            [0, 0, GRANDE, GRANDE], radius=GRANDE * 0.22, fill=255)
        img.putalpha(mascara)
    return img.resize((tam, tam), Image.LANCZOS)


def main():
    salidas = [('icono-192.png', 192, False),
               ('icono-512.png', 512, False),
               ('icono-maskable-512.png', 512, True)]
    for nombre, tam, sangre in salidas:
        ruta = os.path.join(APP, nombre)
        dibuja(tam, sangre).save(ruta)
        print(f'{nombre:26s} {tam}x{tam}  {os.path.getsize(ruta) / 1024:.0f} kB')


if __name__ == '__main__':
    main()
