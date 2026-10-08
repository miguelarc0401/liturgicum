# -*- coding: utf-8 -*-
"""Los iconos de la app instalada, sacados de la imagen de la tapa.

La tapa de un breviario de toda la vida: tafilete rojo y, gofrada en oro,
una cruz florenzada con su rafaga de rayos y el medallon del IHS en el
crucero. Antes se dibujaba aqui con geometria; ahora la imagen viene hecha,
en `src/icono-fuente.webp`, y este guion solo la prepara. Si algun dia se
cambia la tapa, se sustituye ese fichero y se vuelve a pasar el guion.

Lo que hay que preparar es poco, pero no es del todo trivial:

  * La imagen no es cuadrada (1188x1324) y los iconos si lo son, asi que la
    piel tiene que seguir hasta el borde del cuadrado. No se estira la
    imagen -deformaria la cruz- ni se pone una banda de color plano -se
    notaria la costura-: se prolonga el borde con su propio grano.
  * La tapa de la imagen va redondeada y biselada sobre un fondo claro, asi
    que trae un marco y cuatro esquinas en blanco que sobran: se recortan el
    bisel y se tapan las esquinas, y el redondeo se vuelve a dar al final
    sobre el cuadrado entero. Asi el icono tiene SUS esquinas, no las de la
    imagen encogida dentro de otro marco.
  * La version `maskable` es la que Android usa de verdad en el cajon de
    aplicaciones: ahi el sistema recorta el icono con la forma que le de la
    gana -circulo en los Pixel- asi que la piel llega al borde y la cruz se
    encoge a la zona segura.

    python src/19_iconos.py
"""

import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, 'app')
FUENTE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'icono-fuente.webp')

GRANDE = 1024          # se compone en grande y se reduce: eso da el filo
# lo que se recorta de cada borde -izquierda, arriba, derecha, abajo-: el
# bisel de la tapa, que no es igual de ancho por los cuatro lados
MARGEN = 0.047, 0.035, 0.047, 0.047
REDONDEO = 0.22        # el radio de las esquinas, como en iOS
ESQUINA = 0.17         # el trozo de esquina que hay que tapar, del alto
BORDE = 10             # cuantas filas se promedian para prolongar la piel
GRANO = 7              # el ruido de la piel, para que la prolongacion no
                       # salga lisa al lado de lo que si tiene grano
SUAVE = 0.05           # cuanto se difumina la linea que se prolonga
HONDO = 0.30           # cuanto sigue oscureciendo la piel hacia el borde
LLENO = 0.96           # lo que ocupa la tapa en el icono normal
ZONA = 0.78            # y en el `maskable`, que es la zona segura


def destapa():
    """La tapa sola: un rectangulo entero de piel, sin marco ni esquinas.

    Primero se recorta el bisel -la tapa de la imagen lleva un reborde mas
    claro con su acanaladura, y si se deja, al prolongar la piel queda un
    marco dentro de otro marco, el del bisel y el del propio icono, que se
    ve enseguida-. Se recorta menos por arriba, porque la cruz sube casi
    hasta el borde y es la poca piel que queda para prolongar, y mas por
    abajo, donde el bisel de la imagen es mas ancho.

    El recorte no llega a las esquinas: el redondeo tiene mucho mas radio
    que el bisel, y en las cuatro esquinas quedan el arco claro y el fondo
    blanco de fuera. Cada una se tapa con el cuadrado de piel que tiene
    justo debajo (o encima), dado la vuelta: a esa altura la piel ya esta
    limpia y el reflejo no deja costura, porque el corte cae donde las dos
    mitades coinciden. A los lados no se puede ir a buscar, que es por
    donde asoman las puntas de la cruz.
    """
    img = Image.open(FUENTE).convert('RGB')
    w, h = img.size
    a, b, c, d = MARGEN
    img = img.crop((round(w * a), round(h * b),
                    w - round(w * c), h - round(h * d)))
    w, h = img.size
    r = round(h * ESQUINA)
    for x in (0, w - r):
        for y, vuelta in ((0, r), (h - r, h - 2 * r)):
            trozo = img.crop((x, vuelta, x + r, vuelta + r))
            img.paste(trozo.transpose(Image.FLIP_TOP_BOTTOM), (x, y))
    return img


def prolonga(img, lado):
    """Centra la tapa en un cuadrado y sigue la piel hasta el borde.

    El relleno sale de promediar las filas (o las columnas) del borde y
    difuminar lo que queda, que deja el degradado de la piel y se lleva el
    relieve; si no se difumina, cada altura se prolonga con su color y el
    borde de la tapa se repite hacia fuera como un eco, que es justo lo que
    delata el apano. El grano se devuelve despues como ruido: una banda
    lisa al lado de una piel con grano se ve, y una banda con grano no.
    """
    w, h = img.size
    izq, arr = (lado - w) // 2, (lado - h) // 2
    lienzo = Image.new('RGB', (lado, lado))
    lienzo.paste(img, (izq, arr))
    for ancho, alto, caja, donde in (
            (izq, h, (0, 0, BORDE, h), (0, arr)),
            (lado - izq - w, h, (w - BORDE, 0, w, h), (izq + w, arr))):
        if ancho > 0:
            linea = img.crop(caja).resize((1, alto), Image.BOX).filter(
                ImageFilter.GaussianBlur(lado * SUAVE))
            lienzo.paste(linea.resize((ancho, alto), Image.NEAREST), donde)
    for ancho, alto, caja, donde in (
            (lado, arr, (0, arr, lado, arr + BORDE), (0, 0)),
            (lado, lado - arr - h,
             (0, arr + h - BORDE, lado, arr + h), (0, arr + h))):
        if alto > 0:
            linea = lienzo.crop(caja).resize((ancho, 1), Image.BOX).filter(
                ImageFilter.GaussianBlur(lado * SUAVE))
            lienzo.paste(linea.resize((ancho, alto), Image.NEAREST), donde)
    lienzo = ImageChops.multiply(lienzo, sombra(lado, izq, w, arr, h))
    grano = ImageChops.add(lienzo, ruido(lado), 1.0, -128)
    mascara = Image.new('L', (lado, lado), 255)      # grano solo en el relleno
    ImageDraw.Draw(mascara).rectangle(
        [izq, arr, izq + w - 1, arr + h - 1], fill=0)
    lienzo.paste(grano, (0, 0), mascara)
    return lienzo


def ruido(lado):
    """El grano, y siempre el mismo. Va sembrado a proposito: si cambiara en
    cada pasada, volver a pasar el guion metería 850 kB nuevos en el
    repositorio sin que el icono se viera distinto."""
    rnd = random.Random(7)
    return Image.frombytes('L', (lado, lado), bytes(
        min(255, max(0, round(rnd.gauss(128, GRANO))))
        for _ in range(lado * lado))).convert('RGB')


def sombra(lado, izq, w, arr, h):
    """Lo que hace que no se vea el recuadro de la tapa dentro del icono.

    La piel de la imagen se va oscureciendo hacia sus bordes, y una banda
    que repita el borde se queda clavada en ese ultimo valor: dentro sigue
    aclarando y fuera no, y el ojo lee ahi un rectangulo aunque no haya
    ningun salto de color. Asi que fuera de la tapa se sigue oscureciendo,
    como si la penumbra continuara, y el recuadro desaparece.
    """
    def eje(largo, desde, cuanto):
        v = bytearray(largo)
        for i in range(largo):
            fuera = max(desde - i, i - (desde + cuanto - 1), 0)
            t = fuera / max(desde, largo - desde - cuanto, 1)
            v[i] = round(255 * (1 - HONDO * t))
        return Image.frombytes('L', (largo, 1), bytes(v))
    x = eje(lado, izq, w).resize((lado, lado), Image.NEAREST)
    y = eje(lado, arr, h).rotate(90, expand=True).resize(
        (lado, lado), Image.NEAREST)
    return ImageChops.multiply(x, y).convert('RGB')


def compone(tapa, tam, sangre):
    """El icono. `sangre` lleva la piel a los bordes y encoge la cruz, para
    que Android pueda recortarla en circulo sin comersela; si no, se le
    redondean las esquinas y la cruz va a su tamano."""
    alto = round(GRANDE * (ZONA if sangre else LLENO))
    ancho = round(tapa.size[0] * alto / tapa.size[1])
    img = prolonga(tapa.resize((ancho, alto), Image.LANCZOS), GRANDE)
    img = img.convert('RGBA')
    if not sangre:
        mascara = Image.new('L', (GRANDE, GRANDE), 0)
        ImageDraw.Draw(mascara).rounded_rectangle(
            [0, 0, GRANDE - 1, GRANDE - 1], radius=GRANDE * REDONDEO, fill=255)
        img.putalpha(mascara)
    img = img.resize((tam, tam), Image.LANCZOS)
    if tam <= 256:                      # lo que se reduce mucho pierde filo
        alfa = img.getchannel('A')      # el filo, al canal de color: darselo
        img = img.filter(ImageFilter.UnsharpMask(1.2, 70))   # al alfa haria
        img.putalpha(alfa)                                   # cerco
    return img


def main():
    tapa = destapa()
    for nombre, tam, sangre in [('icono-32.png', 32, False),
                                ('icono-180.png', 180, False),
                                ('icono-192.png', 192, False),
                                ('icono-512.png', 512, False),
                                ('icono-maskable-512.png', 512, True)]:
        ruta = os.path.join(APP, nombre)
        compone(tapa, tam, sangre).save(ruta, optimize=True)
        print(f'{nombre:26s} {tam}x{tam}  {os.path.getsize(ruta) / 1024:.0f} kB')


if __name__ == '__main__':
    main()
