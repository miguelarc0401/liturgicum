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
* **Clementina, Nova Vulgata y castellano**, con un interruptor en
  Ajustes. El castellano es la traducción litúrgica aprobada para México,
  cosechada por [`Missale/`](../Missale/LEEME.md) del misalito mensual de
  2018 a 2026: dos de cada tres lecturas la tienen, y la que no se
  imprimió ni una vez en los nueve años lo dice en su sitio en vez de
  disimularlo. No se traduce nada: si no está, se dice que no está.
* **Acentuación litúrgica** encendida o apagada, números de versículo,
  tamaño de letra, y aspecto claro / sepia / oscuro.
* **Calendario litúrgico** de cada año (2024–2060): qué se celebra cada día
  y con qué grado —solemnidad, fiesta, memoria, memoria libre, domingo,
  feria de Cuaresma, de Adviento…—, con su color, lo que se puede elegir y
  lo que se omite. Un toque en un día lo abre en la misa o en las horas.
  Arriba, un **buscador de celebraciones** («teresa», «ángeles», «asís»)
  deja sólo los días que las nombran, aunque sea como memoria libre o como
  lo que ese año se omite; y al bajar por el año la cabecera se queda
  arriba, resumida: el año, la tira de los meses con el que se está
  leyendo marcado, y la lupa. Desde él se llega al **índice del
  leccionario**.
* **Buscador** sobre el latín, en el índice del leccionario: ignora acentos y
  desata æ/œ, así que escribiendo `quaesumus` encuentra *quǽsumus*. También
  busca por cita: **«salmo 121»** devuelve los siete lugares donde se canta.
* **Se vuelve a donde se estaba.** Quien sale de Laudes al calendario y
  vuelve, vuelve al mismo renglón; otro día, otra hora u otra celebración
  empiezan arriba, y cerrar la app lo olvida. Cuando se anda por otro día,
  junto a la fecha sale **«Hoy»**, que vuelve a éste.
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
* **La Liturgia de las Horas**, en la traducción litúrgica de México: las
  siete horas —Oficio de Lectura, Laudes, Tercia, Sexta, Nona, Vísperas y
  Completas— con sus rúbricas en rojo, como en el libro. Al entrar propone
  la hora que toca por el reloj. El oficio se arma en cascada: lo propio
  del santo, si no lo de su común, si no lo del tiempo, la salmodia del
  salterio y el ordinario para lo que no cambia. Sale de
  [`Breviarium/`](../Breviarium/LEEME.md), que es un módulo aparte y con
  su propia fuente.
* **Lo que las rúbricas dejan elegir, se ofrece.** Qué se celebra cada día
  lo dice el mismo calendario que la misa, con su precedencia. En las
  memorias, lo que el santo no tiene propio —el invitatorio, el himno y, en
  Laudes y Vísperas, de la lectura breve a las preces— lleva junto a su
  rótulo un selector discreto: *Del día · Doctores* (o *Pastores*, si el
  santo admite los dos comunes). La salmodia, la lectura bíblica del Oficio
  y Completas no lo llevan, porque ahí no se elige. La antífona del
  Benedictus y del Magníficat, en las memorias y fiestas de los santos,
  ofrece también la del día detrás de la del santo. Una
  memoria libre se puede celebrar o dejar, y en Cuaresma y las ferias
  privilegiadas sólo cabe como conmemoración: eso se elige arriba, con los
  chips de la cabecera. En Ajustes se dice qué opción sale marcada.
* **La Hora intermedia**: la salmodia del día sale en Sexta y la
  complementaria (salmos graduales) en Tercia y Nona, y las tres dejan
  cambiar a la otra. En Adviento, Navidad, Cuaresma y Pascua la antífona de
  cada hora se queda aunque cambien los salmos. Los himnos que se ofrecen
  son los del tiempo: en el ordinario, los de las semanas I a XVII o los de
  la XVIII a la XXXIV.
* **La lectura bíblica del Oficio sigue el ciclo de dos años** (año I los
  impares, año II los pares), como la fuente.
* **Reseña, himnos y antífona final.** El Oficio de lectura abre con la
  reseña del santo; donde hay varios himnos posibles (Completas, la Hora
  intermedia, y los días en que el libro da más de uno) y en la antífona
  final de la Virgen, un selector numerado deja escoger.
* **Cómo se lee.** Himnos, salmos y cánticos van por renglones con sangría
  francesa, de modo que al agrandar la letra se ve dónde empieza cada uno;
  lecturas, responsorios, preces y oraciones, justificados. Cuando el salmo
  empieza con las mismas palabras que su antífona (con o sin «aleluya»), una
  † roja al final de la antífona y otra donde se sigue. Lo que no está en la fuente y se tomó
  de los tomos impresos lleva la marca «ed. española» (ver
  [Breviarium/LEEME.md](../Breviarium/LEEME.md)).

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
descarga unos 8 MB; por detrás y sin estorbar se guardan la segunda versión
latina (6 MB) y la liturgia de las horas (unos 25). A partir de ahí abre sin
conexión.

> Si el navegador no ofrece instalarla, casi siempre es que la dirección es
> `http` y no `https`. Es el único requisito.

## Rehacer los datos

```bash
python src/12_calendario.py        # el esqueleto del año (si cambió algo antes)
python src/16_parse_anexos.py      # los apéndices
python src/5_resolve.py --anexos   # y con --fuente nova
python src/18_santoral.py          # santoral + precedencia -> calendario completo
python src/15_app_data.py          # -> app/datos/*.json + los iconos
python Breviarium/src/4_app.py     # -> app/datos/horas*.json (la liturgia de las horas)
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
datos/horas*.json       la liturgia de las horas (la hace Breviarium/src/4_app.py)
```
