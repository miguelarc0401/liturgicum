# -*- coding: utf-8 -*-
"""Los iconos de la app instalada.

La tapa de un breviario de toda la vida: tafilete rojo y, gofrada en oro,
una cruz florenzada con su ráfaga de rayos y el medallón del IHS en el
crucero. No es un dibujo nuevo —es lo que lleva un siglo en la cubierta de
estos libros—, y por eso se reconoce sin explicarlo.

Un icono de pantalla de inicio se ve a 48 píxeles, así que el detalle se
gradúa: a tamaño grande van el IHS, la orla de puntos y las crucecitas de
los remates; a tamaño de favicon queda lo que aguanta, que es la cruz, los
rayos y el medallón. Se dibuja en grande y se reduce, que es lo que le da
el filo.

    python src/19_iconos.py
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, 'app')

GRANDE = 1024
TAFILETE = (124, 22, 32)           # el rojo de la piel, a la luz
TAFILETE_HONDO = (70, 10, 19)      # y en la sombra
ORO = (212, 175, 100)
ORO_ALTO = (243, 222, 165)
ORO_BAJO = (150, 113, 50)
SERIFAS = ['C:/Windows/Fonts/BOOKOSB.TTF', 'C:/Windows/Fonts/constanb.ttf',
           'C:/Windows/Fonts/georgiab.ttf', 'C:/Windows/Fonts/timesbd.ttf']


def tipo(tam):
    for ruta in SERIFAS:
        if os.path.exists(ruta):
            return ImageFont.truetype(ruta, tam)
    return None


def piel(lado):
    """El tafilete: un rojo que no es plano —se ahonda hacia los bordes— y
    con el grano menudo de la piel, que es lo que le quita el aire de
    plástico."""
    img = Image.new('RGB', (lado, lado), TAFILETE)
    px = img.load()
    rnd = random.Random(7)
    for y in range(lado):
        t = y / (lado - 1)
        base = tuple(round(a + (b - a) * t)
                     for a, b in zip(TAFILETE, TAFILETE_HONDO))
        for x in range(lado):
            d = math.hypot(x - lado / 2, y - lado / 2) / (lado * 0.72)
            v = max(0.0, 1 - d * d * 0.55)
            g = rnd.randint(-9, 9)
            px[x, y] = tuple(max(0, min(255, round(c * v) + g)) for c in base)
    return img.convert('RGBA')


def rayos(d, cx, cy, dentro, fuera, cuantos, color, ancho):
    """La ráfaga del crucero: rayos rectos, uno sí y otro más corto."""
    for i in range(cuantos):
        a = i * 2 * math.pi / cuantos
        largo = fuera if i % 2 == 0 else fuera * 0.76
        d.line([cx + dentro * math.cos(a), cy + dentro * math.sin(a),
                cx + largo * math.cos(a), cy + largo * math.sin(a)],
               fill=color, width=ancho)


def brazo(d, cx, cy, hacia, largo, g, gf, color):
    """Un brazo de la cruz, que se abre hacia la punta."""
    dx, dy = hacia
    px, py = -dy, dx
    def p(t, a):
        return (cx + dx * t + px * a, cy + dy * t + py * a)
    d.polygon([p(0, -g), p(largo, -gf), p(largo, gf), p(0, g)], fill=color)


def remate(d, cx, cy, r, color, detalle):
    """El remate de cada brazo: un disco con su crucecita dentro."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    if not detalle:
        return
    g, b = r * 0.17, r * 0.55
    d.polygon([(cx - g, cy - b), (cx + g, cy - b), (cx + g, cy - g),
               (cx + b, cy - g), (cx + b, cy + g), (cx + g, cy + g),
               (cx + g, cy + b), (cx - g, cy + b), (cx - g, cy + g),
               (cx - b, cy + g), (cx - b, cy - g), (cx - g, cy - g)],
              fill=TAFILETE_HONDO)


def cruz_chica(d, cx, cy, g, b, color):
    d.polygon([(cx - g, cy - b), (cx + g, cy - b), (cx + g, cy - g),
               (cx + b * 0.72, cy - g), (cx + b * 0.72, cy + g),
               (cx + g, cy + g), (cx + g, cy + b), (cx - g, cy + b),
               (cx - g, cy + g), (cx - b * 0.72, cy + g),
               (cx - b * 0.72, cy - g), (cx - g, cy - g)], fill=color)


def medallon(d, cx, cy, rx, ry, detalle):
    """El medallón del crucero, con el IHS."""
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=ORO)
    d.ellipse([cx - rx * 0.90, cy - ry * 0.90, cx + rx * 0.90, cy + ry * 0.90],
              fill=TAFILETE_HONDO)
    if not detalle:
        # a tamaño de favicon el IHS se vuelve una mancha: una cruz dentro
        cruz_chica(d, cx, cy, rx * 0.14, ry * 0.52, ORO)
        return
    for i in range(28):                     # la orla de puntos del gofrado
        a = i * 2 * math.pi / 28
        px = cx + rx * 0.945 * math.cos(a)
        py = cy + ry * 0.945 * math.sin(a)
        o = rx * 0.038
        d.ellipse([px - o, py - o, px + o, py + o], fill=ORO_ALTO)
    f = tipo(int(ry * 0.70))
    caja = d.textbbox((0, 0), 'IHS', font=f)
    d.text((cx - (caja[2] - caja[0]) / 2 - caja[0],
            cy + ry * 0.10 - (caja[3] - caja[1]) / 2 - caja[1]),
           'IHS', font=f, fill=ORO)
    cruz_chica(d, cx, cy - ry * 0.46, rx * 0.05, ry * 0.19, ORO)


def gofrado(lado, detalle):
    """El oro: la cruz entera en su capa, para poder darle el relieve."""
    capa = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    cx = cy = lado / 2
    L, A = lado * 0.370, lado * 0.290       # medio largo y medio ancho
    g, gf = lado * 0.026, lado * 0.038      # grueso al centro y a la punta
    r = lado * 0.062                        # el disco del remate

    rayos(d, cx, cy, lado * 0.098, lado * 0.300, 36, ORO,
          max(1, round(lado * 0.0062)))
    brazos = (((0, -1), L * 0.92), ((0, 1), L * 1.14),
              ((-1, 0), A), ((1, 0), A))
    for hacia, largo in brazos:
        brazo(d, cx, cy, hacia, largo, g, gf, ORO)
    for hacia, largo in brazos:
        remate(d, cx + hacia[0] * largo, cy + hacia[1] * largo, r, ORO, detalle)
    medallon(d, cx, cy, lado * 0.122, lado * 0.150, detalle)
    return capa


def dibuja(tam, sangre):
    """El icono. `sangre` lo lleva a los bordes, para el recorte de Android;
    si no, se le redondean las esquinas."""
    detalle = tam >= 128
    img = piel(GRANDE)
    lado = round(GRANDE * (0.78 if sangre else 0.94))   # zona segura
    oro = gofrado(lado, detalle)
    m = round((GRANDE - lado) / 2)
    if detalle:
        # el gofrado hunde el oro en la piel: una sombra debajo y una luz
        # arriba, un pelo desplazadas
        alfa = oro.split()[3]
        sombra = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
        sombra.paste(ORO_BAJO + (190,), (0, 0), alfa)
        luz = Image.new('RGBA', (lado, lado), (0, 0, 0, 0))
        luz.paste(ORO_ALTO + (140,), (0, 0), alfa)
        off = max(1, round(lado * 0.004))
        img.alpha_composite(sombra, (m + off, m + off))
        img.alpha_composite(luz, (m - off, m - off))
    img.alpha_composite(oro, (m, m))

    if not sangre:
        mascara = Image.new('L', (GRANDE, GRANDE), 0)
        ImageDraw.Draw(mascara).rounded_rectangle(
            [0, 0, GRANDE, GRANDE], radius=GRANDE * 0.22, fill=255)
        img.putalpha(mascara)
    return img.resize((tam, tam), Image.LANCZOS)


def main():
    for nombre, tam, sangre in [('icono-32.png', 32, False),
                                ('icono-180.png', 180, False),
                                ('icono-192.png', 192, False),
                                ('icono-512.png', 512, False),
                                ('icono-maskable-512.png', 512, True)]:
        ruta = os.path.join(APP, nombre)
        dibuja(tam, sangre).save(ruta)
        print(f'{nombre:26s} {tam}x{tam}  {os.path.getsize(ruta) / 1024:.0f} kB')


if __name__ == '__main__':
    main()
