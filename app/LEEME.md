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
* **Clementina, Nova Vulgata, castellano y bilingüe**, con un interruptor en
  Ajustes. El castellano es la traducción litúrgica aprobada para México,
  cosechada por [`Missale/`](../Missale/LEEME.md) del misalito mensual de
  2018 a 2026: tres de cada cuatro lecturas la tienen, y la que no se
  imprimió ni una vez en los nueve años lo dice en su sitio en vez de
  disimularlo. La cita del leccionario y la que el misalito imprime no
  siempre son la misma, y la perícopa se busca por tres caminos: la cita,
  los versículos que abarca y el día del calendario en que se imprimió;
  cuando el leccionario de México canta otros versículos del mismo salmo,
  se enseñan las dos citas. No se traduce nada: si no está, se dice que no está. El
  bilingüe enfrenta las dos lenguas —en el teléfono, una debajo de otra; en
  una pantalla ancha, a dos columnas— y el latín que pone es el último que
  se eligió, de modo que quien lee la Nova la sigue teniendo.
* **La misa entera, no sólo las lecturas.** El formulario de arriba abajo:
  la reseña, la antífona de entrada, la colecta, las lecturas, la oración
  sobre las ofrendas, el prefacio, la plegaria eucarística, la antífona de
  comunión y la oración de después, con el **Ordinario de la misa**
  intercalado donde va —las 146 rúbricas del Ordo, en las dos lenguas y
  alineadas por su número—. El Ordinario viene **plegado**, porque no se lee
  cada día, pero cuando se busca se busca ahí: un toque en su rótulo lo
  abre, y lo que se deja abierto se queda abierto mientras dure la sesión.
  En Ajustes puede venir abierto, o no salir.
* **Lo que se enseña del formulario, se dice en Ajustes.** «Qué se enseña de
  la misa» da tres modos. *Todo*, que es el formulario entero. *Lo breve*,
  que es lo que cambia cada día y se dice: antífona de entrada, el Gloria
  los días que lo lleva, la colecta, las lecturas con su salmo y su
  aclamación, la oración de los fieles, la oración sobre las ofrendas, la
  antífona de comunión y la oración después de la comunión. Y *lo que yo
  elija*, que es la misma lista de veintidós piezas con una casilla cada
  una, en el orden de la misa; empieza por lo que se estuviera viendo. En
  los dos últimos modos las piezas pedidas vienen abiertas, y el ajuste del
  Ordinario —que sólo dice si viene plegado— no se ofrece, porque allí lo
  que entra ya está decidido pieza por pieza.
* **Lo que la misa deja elegir, se elige.** El saludo (tres fórmulas), la
  invitación al acto penitencial (cuatro) y su fórmula (I, II y III), el
  símbolo —niceno o de los apóstoles—, el «Oren, hermanos», el prefacio
  (los sesenta y siete castellanos, los veintiocho propios cosechados del
  misalito y los treinta y nueve que sólo existen en latín), la plegaria
  eucarística (las cuatro del Ordinario y, en latín, las de la
  reconciliación y las de diversas necesidades), el Misterio de la fe, la
  invitación al padrenuestro y a la paz, la oración antes de comulgar, la
  bendición final —las veinte solemnes y las veintiocho oraciones sobre el
  pueblo del apéndice del Misal— y la despedida. Lo que el día **manda** no
  se pregunta: el Gloria y el Credo los pone o los calla el formulario, y el
  prefacio que el día marca viene elegido. Con una enmienda: el formulario
  no siempre es del día —las ferias del tiempo ordinario toman el del
  domingo de su semana, y con él se traían su Gloria y su Credo—, así que
  una feria los calla. Qué es feria lo dice el calendario del proyecto con
  su rango de la Tabla de los días litúrgicos, y se miran las del rango 13;
  los días de la octava de Navidad, que son del 9 y sí los dicen, los
  acierta el formulario porque es suyo. Donde el Misal no marca ninguno
  —los domingos del tiempo ordinario, por ejemplo— se dice que la elección
  es libre y se ofrece el juego del tiempo.
* **Las otras misas del mismo día.** Las que el leccionario numera —las tres
  de Navidad— salen en la tira de formularios de la cabecera; las que no
  numera —la vespertina de la vigilia de san Juan Bautista y de los
  Apóstoles, la segunda y la tercera de Difuntos— se eligen dentro, en «La
  misa»: cambian los propios y no las lecturas.
* **De dónde sale cada texto castellano**, cuando no salió del sitio obvio:
  bajo la pieza, en pequeño, «del día» o «del común», con el porqué y los
  testigos en el título. Lo que el misalito no imprimió en nueve años lo dice
  en su sitio.
* **Acentuación litúrgica** encendida o apagada, números de versículo,
  tamaño de letra, y aspecto claro / sepia / oscuro.
* **El formato del texto, una vez para todo o sección por sección.** La
  alineación, el interlineado y la partición de palabras se dicen una vez y
  valen para toda la app, que es lo que basta casi siempre; y quien quiera
  más apaga «un solo formato para todo» y entonces cada clase de texto
  —lecturas, salmos y cánticos, himnos, antífonas, oraciones, preces y
  responsorios, y el Ordinario de la misa— lleva el suyo, con una muestra
  al lado que no es un dibujo sino el mismo texto con las mismas reglas. Lo
  que una sección no diga lo sigue diciendo el general. Las secciones se
  agrupan por lo que son y no por el libro en que salen: la primera lectura
  de la misa y la lectura breve de Vísperas son la misma clase de texto.
* **Siete tipos de letra**, de libro y de pantalla, y **el color de la app**
  fijo si se quiere: en vez del litúrgico del día, el que se elija. En el
  calendario el color sigue siendo el de cada día, porque allí el color es
  lo que se lee y no un adorno. Ninguna letra se descarga —la app abre sin
  conexión desde el primer día—, así que lo que se elige es un aire y lo
  sirve la fuente que el teléfono ya tenga.
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
* **Primeras o segundas vísperas.** Un domingo y una solemnidad tienen dos
  vísperas, y la app dice cuáles enseña: la tarde del sábado, «Primeras
  vísperas», con el nombre y el color del domingo que entra —también si ese
  domingo lo gana una solemnidad: se ha medido que el sábado de la semana
  VII de Pascua trae el himno y la antífona de las primeras vísperas de
  Pentecostés—; y el día mismo, «Segundas vísperas». De las solemnidades
  que caen en día de semana no se anuncian las primeras: la fuente no las
  dio —en la víspera imprime las del día que acaba, y el 24 de diciembre
  trae las de Adviento y no las de Navidad—, y poner el rótulo sobre un
  texto que no es el suyo sería mentir.
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
  lecturas, responsorios, preces y oraciones, justificados —y todo eso se
  puede cambiar en Ajustes, junto o sección por sección—. Cuando el salmo
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
python src/15_app_data.py          # -> app/datos/*.json
python Breviarium/src/4_app.py     # -> app/datos/horas*.json (la liturgia de las horas)
```

Las dos últimas son las que hay que repetir cuando se toca `data/santoral.csv`
o cualquiera de las tablas editables, y es justo lo que hace `.\publicar.ps1`.

El icono va aparte, porque no depende de los datos y casi nunca cambia:

```bash
python src/19_iconos.py            # src/icono-fuente.webp -> app/icono-*.png
```

Sale todo de una sola imagen, la tapa del breviario. Para cambiarlo se
sustituye `src/icono-fuente.webp` y se vuelve a pasar el guion; de ahí salen
el del navegador, el de iOS y los dos de Android —el normal y el `maskable`,
que es el que el sistema recorta con la forma que tenga el teléfono—.

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
icono-*.png             los saca src/19_iconos.py de src/icono-fuente.webp
datos/                  lo generado; no se edita a mano
datos/horas*.json       la liturgia de las horas (la hace Breviarium/src/4_app.py)
datos/misa.json         el formulario de cada misa, con sus propios
datos/misal_latino.json el Misal de 2002, una vez y por su propio nombre
datos/prefacios.json    los dos juegos de prefacios, emparejados
datos/ordinario.json    el Ordo Missæ bilingüe, por número de rúbrica
                        (los cuatro los hace Missale/src/6_app.py)
```

Los cuatro ficheros de la misa son 3,8 MB y **no** se guardan al instalar la
app: serían 3,8 MB inútiles en el teléfono de quien sólo lee las lecturas. Se
piden la primera vez que se abre una misa —ahí hace falta conexión— y de ahí
en adelante quedan guardados como todo lo demás.
