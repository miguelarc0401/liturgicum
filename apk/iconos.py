"""Los iconos del APK, sacados de los de la web.

    python apk/iconos.py

Android quiere el icono en cinco densidades y en dos formas: el de siempre
(cuadrado, para Android 7) y el adaptable de Android 8 en adelante, que son
dos capas de 108 dp de las que el lanzador sólo enseña el centro -72 dp, y
con la máscara redonda, 66-. El icono maskable de la web ya trae la tapa a
sangre, pero su zona segura es el 80 %: puesto tal cual en las 108 dp, la
cruz se saldría de las 66 y el lanzador le cortaría los remates. Por eso va
encogido al 75 % de la capa; lo que sobra alrededor no se ve nunca, porque
cae fuera de las 72, y se rellena con el color del borde de la tapa para que
tampoco se note en los lanzadores que enseñan un poco más.

Sólo hace falta volver a correrlo si cambia el icono de la web.
"""

from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / 'app'
RES = RAIZ / 'apk' / 'android' / 'app' / 'src' / 'main' / 'res'

# densidad -> pixeles por dp
DENSIDADES = {'mdpi': 1, 'hdpi': 1.5, 'xhdpi': 2, 'xxhdpi': 3, 'xxxhdpi': 4}
ESCALA_CAPA = 0.75


def color_del_borde(img):
    """La media de un marco de 8 px alrededor: el fondo de la tapa."""
    rgb = img.convert('RGB')
    w, h = rgb.size
    px = []
    for x in range(w):
        for y in list(range(8)) + list(range(h - 8, h)):
            px.append(rgb.getpixel((x, y)))
    for y in range(8, h - 8):
        for x in list(range(8)) + list(range(w - 8, w)):
            px.append(rgb.getpixel((x, y)))
    n = len(px)
    return tuple(round(sum(p[i] for p in px) / n) for i in range(3))


def capa_delantera(maskable, lado, fondo):
    capa = Image.new('RGB', (lado, lado), fondo)
    dentro = round(lado * ESCALA_CAPA)
    tapa = maskable.convert('RGB').resize((dentro, dentro), Image.LANCZOS)
    capa.paste(tapa, ((lado - dentro) // 2, (lado - dentro) // 2))
    return capa


def redondo(maskable, lado):
    # el centro de la zona segura, recortado en círculo
    w = maskable.width
    m = round(w * 0.10)
    centro = maskable.convert('RGBA').crop((m, m, w - m, w - m))
    centro = centro.resize((lado, lado), Image.LANCZOS)
    mascara = Image.new('L', (lado * 4, lado * 4), 0)
    ImageDraw.Draw(mascara).ellipse((0, 0, lado * 4 - 1, lado * 4 - 1), fill=255)
    centro.putalpha(mascara.resize((lado, lado), Image.LANCZOS))
    return centro


def main():
    maskable = Image.open(WEB / 'icono-maskable-512.png')
    cuadrado = Image.open(WEB / 'icono-512.png').convert('RGBA')
    fondo = color_del_borde(maskable)

    for nombre, k in DENSIDADES.items():
        carpeta = RES / ('mipmap-' + nombre)
        carpeta.mkdir(parents=True, exist_ok=True)
        capa_delantera(maskable, round(108 * k), fondo).save(
            carpeta / 'ic_launcher_foreground.png', optimize=True)
        cuadrado.resize((round(48 * k),) * 2, Image.LANCZOS).save(
            carpeta / 'ic_launcher.png', optimize=True)
        redondo(maskable, round(48 * k)).save(
            carpeta / 'ic_launcher_round.png', optimize=True)

    hexa = '#%02X%02X%02X' % fondo
    (RES / 'values' / 'ic_launcher_background.xml').write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        f'    <color name="ic_launcher_background">{hexa}</color>\n'
        '</resources>\n', encoding='utf-8')
    print('iconos hechos; fondo', hexa)


if __name__ == '__main__':
    main()
