# Leccionario latino — la app

El mismo leccionario de `out/`, pero para leerlo en el teléfono: abre por las
lecturas de hoy, funciona **sin conexión** y se instala en la pantalla de
inicio con su icono, como cualquier otra app.

No es un desarrollo aparte: los textos, las fórmulas latinas y la acentuación
salen de los mismos ficheros de `data/` que componen los DOCX y los PDF, y los
genera `src/15_app_data.py` importando el propio `8_render.py`. Si mañana se
corrige un versículo en el corpus, se regenera y la app lo trae.

## Qué trae

* **Las lecturas de hoy** al abrir, con la fecha litúrgica calculada (Pascua,
  Adviento, ciclo A/B/C y año ferial I/II). Flechas para pasar de día y un
  toque en la fecha para saltar a cualquier otra.
* **Clementina y Nova Vulgata**, con un interruptor en Ajustes.
* **Acentuación litúrgica** encendida o apagada, números de versículo,
  tamaño de letra, y aspecto claro / sepia / oscuro.
* **Índice del año entero** y **buscador** sobre el latín: ignora acentos y
  desata æ/œ, así que escribiendo `quaesumus` encuentra *quǽsumus*. También
  busca por cita: **«salmo 121»** devuelve los siete lugares donde se canta.
* **Los apéndices**: los versículos que pueden sustituir al del día antes del
  Evangelio en cada tiempo litúrgico (las antífonas «O» del 17 al 24 de
  diciembre, las aclamaciones de Cuaresma…) y los salmos comunes del
  responsorial. Están en el índice, al final.
* **El propio y el común de los santos** (leccionario V), las **misas por
  diversas necesidades y votivas** (VI) y las **rituales y de difuntos**
  (VIII), con su índice propio.
* **El santoral puesto en el calendario**, con el *Calendario general romano y
  latinoamericano*: cada fecha enseña la celebración que toca, con su grado
  (solemnidad, fiesta, memoria, memoria libre).
* **La concurrencia resuelta con la Tabla de los días litúrgicos**: cuando en
  una fecha coinciden varias celebraciones, salen en fila ordenadas por
  precedencia y la primera es la que se celebra. Las solemnidades impedidas se
  trasladan solas, y lo que se omite ese año se dice en vez de callarse.
* El **color litúrgico** tiñe la cabecera: el del tiempo, y el del santo cuando
  lo hay (rojo en los mártires, los apóstoles y la Santa Cruz).
* Epifanía, Ascensión y Corpus se pueden poner en su fecha o trasladados al
  domingo, según el uso del país; y en las memorias se puede preferir la
  lectura del santo o la continua de la feria.

**Lo que no trae:** el leccionario IX (misas con niños), que sí está en `out/`,
en Word y en PDF.

## Probarla en el ordenador

La app **no funciona abriendo `index.html` con doble clic**: el navegador no
deja que una página `file://` lea sus propios datos. Hay que servir la carpeta,
aunque sea desde el propio ordenador:

```bash
python -m http.server 8765 --directory app
```

y abrir <http://localhost:8765>.

## Ponerla en el teléfono

Para instalarla hace falta servirla **una vez** por `https`. Después ya no
necesita ni servidor ni conexión: todo queda guardado en el teléfono.

### Opción 1 — Netlify Drop (lo más rápido, sin cuenta ni git)

1. Entra en <https://app.netlify.com/drop>.
2. Arrastra la carpeta `app/` entera a la página.
3. Te da una dirección `https://algo.netlify.app`.

### Opción 2 — GitHub Pages (si quieres que sea tuya, estable y que se actualice sola)

Es la que está montada: hay un flujo de trabajo en
`.github/workflows/publicar-app.yml` que publica `app/` en cada empujón, y un
`publicar.ps1` que rehace los datos y los sube en una orden. Los pasos de la
primera vez están en el [README](../README.md) de la raíz.

### Instalar en Android

Abre esa dirección en **Chrome**, toca los tres puntos y elige **«Añadir a la
pantalla de inicio»** o **«Instalar aplicación»**. Aparece el icono, y al
abrirla va a pantalla completa, sin barra del navegador. La primera vez
descarga unos 8 MB (y otros 6 por detrás, la segunda versión latina); a partir
de ahí abre sin conexión.

> Si el navegador no ofrece instalarla, casi siempre es que la dirección es
> `http` y no `https`. Es el único requisito.

## Rehacer los datos

```bash
python src/12_calendario.py        # el esqueleto del año (si cambió algo antes)
python src/16_parse_anexos.py      # los apéndices
python src/5_resolve.py --anexos   # y con --fuente nova
python src/18_santoral.py          # santoral + precedencia -> calendario completo
python src/15_app_data.py          # -> app/datos/*.json + los iconos
```

Las dos últimas son las que hay que repetir cuando se toca `data/santoral.csv`
o cualquiera de las tablas editables, y es justo lo que hace `.\publicar.ps1`.

`15_app_data.py` deja en `app/datos/version.js` una firma de los datos. El
service worker la usa como nombre de su caché, así que al cambiar los datos
tira la caché vieja sola: no hay que desinstalar nada en el teléfono. Y
`app.js` pregunta si hay versión nueva al arrancar, al volver la app a primer
plano y al recuperar la conexión, de modo que el teléfono se pone al día solo.

## ¿Y un `.apk` de verdad?

Esta misma carpeta se envuelve en un APK instalable con
[Capacitor](https://capacitorjs.com/) (`npx cap add android`, `webDir: "app"`),
o se publica en Play Store con [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap)
como *Trusted Web Activity*. Las dos exigen instalar JDK y el SDK de Android
(~3 GB) en el ordenador, y no aportan nada que la app instalada no haga ya:
por eso no está hecho.

## Los ficheros

```
index.html              la página
estilos.css             la hoja de estilo (colores litúrgicos, temas)
app.js                  toda la app: rutas, calendario, maquetación, buscador
sw.js                   el service worker: lo que la hace funcionar sin conexión
manifest.webmanifest    nombre, iconos y modo pantalla completa
icono-*.png             los dibuja src/15_app_data.py
datos/                  lo generado; no se edita a mano
```
