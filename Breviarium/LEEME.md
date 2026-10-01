# Breviarium — la Liturgia de las Horas en la traducción de México

Las siete horas del oficio divino —Oficio de Lectura, Laudes, Tercia,
Sexta, Nona, Vísperas y Completas— en la traducción castellana que se usa
litúrgicamente en México, extraídas de su única fuente pública y ordenadas
como un libro: por tiempos, por salterio, por santoral y por comunes.

Es el hermano del leccionario: aquél da lo que se lee en la misa, éste lo
que se reza a lo largo del día.

---

## De dónde salen los textos

De <https://liturgiadelashoras.github.io>, que publica el oficio día a día
y guarda lo publicado en su repositorio. No hay detrás ninguna base de
datos ni ninguna API que consultar: **el sitio es el archivo**. En
`sync/AAAA/mes/dd/` hay un HTML por hora y un `index.htm` que dice qué día
litúrgico es. Son unos 29 000 ficheros, de 2019 a hoy.

El HTML es de los años noventa —ni clases ni etiquetas semánticas, sólo
`<FONT COLOR>` y `<BR>`—, pero de una regularidad absoluta, y en esa
regularidad está toda la información que hace falta:

| en el original | quiere decir |
|---|---|
| rojo `#FF0000` | rúbrica: rótulos, «V.», «R.», «Ant.», títulos de salmo |
| negro `#000000` | el texto que se reza |
| pardo `#9E5806` | la celebración del santoral, con su rango |
| `<BR>` | salto de línea |

De ahí que todo el módulo trabaje con *líneas de tiradas*: cada línea es
una lista de tiradas `(rojo, texto)`, y así no se pierde qué parte de un
verso es rúbrica y qué parte es oración.

---

## El problema, y cómo se resuelve

La fuente publica **días ya armados**: el 15 de marzo trae sus Laudes
enteras, con lo que ese día toma del salterio, lo que toma del propio del
tiempo y lo que toma del santo, todo seguido y sin costuras. Un libro de
horas hace el camino contrario: guarda cada pieza **una sola vez**, en su
sitio, y el día se arma al rezarlo.

Deshacer esa costura no se adivina: se **mide**, y en tres pasadas.

**Primera — el ferial.** Los días que no celebran a nadie dan el propio
del tiempo puro. Se agrupan por `(tiempo, semana, día, hora, sección)`, y
la salmodia aparte, por `(tiempo, salterio, día, hora)`. Ocho años de
testigos deciden por mayoría, y lo que no es unánime **no se tira**: se
guarda como variante con los años que la respaldan, porque muchas veces
no es errata sino el ciclo dominical (A, B, C) o el año ferial (I, II)
asomando.

> Que el tiempo tenga que entrar en la clave del salterio no es una
> suposición, es un resultado. Con la clave `(salterio, día, hora)` sola,
> el **0 %** de las casillas tiene un texto único: los salmos vuelven cada
> cuatro semanas, pero sus antífonas no —Adviento, Cuaresma y Pascua
> tienen las suyas—. Añadiendo el tiempo sube al **85 %**, con una cuota
> mayoritaria media de 0.94.

**Segunda — lo propio.** En una memoria casi todo el oficio sigue siendo
ferial: sólo algunas piezas son del santo. Cuál es cuál no hace falta
suponerlo: se **compara**. Cada sección de un día con celebración se
coteja con la del mismo hueco ferial; si dice lo mismo, es del tiempo y
no se toca; si dice otra cosa, es propia.

**Tercera — los comunes.** De lo propio, lo que un día toma «del Común de
los pastores» aparecerá igual en los demás pastores. Así que un texto que
sale con **dos santos distintos del mismo común** es del común; el que
sale con uno solo se queda con ese santo. También aquí la prueba es el
recuento, no la conjetura.

Y lo que no cambia nunca —la invocación inicial, la conclusión, las
antífonas finales de la Virgen— es el **ordinario**, y se guarda aparte.

> Salvo que tampoco el ordinario es del todo invariable, y también eso lo
> dijo la medida antes que la teoría. La primera versión guardaba una sola
> invocación inicial por hora, y en Cuaresma salía un «Amén. **Aleluya**»
> que no debe decirse. Cotejado con la fuente: el 17 de marzo de 2025 no
> lo lleva, y enero, mayo y diciembre sí. Así que el ordinario también se
> guarda por tiempo, con recurso a la forma general cuando un tiempo no
> tiene la suya.
>
> Lo mismo la antífona final de la Virgen, que no es una sino catorce: las
> guarda todas, y «Reina del cielo, alégrate, aleluya» queda donde le toca,
> en Pascua.

---

## La cadena

```
  el sitio  ──1_bajar──▶  TRABAJO/fuente/     29 000 HTML
                              │
                          2_extraer
                              │
                              ▼
                      TRABAJO/dias/AAAA.json  un día armado, ~200 MB
                              │
                          3_ordenar
                              │
                              ▼
                    datos/libro/*.json        el libro: cada pieza, una vez
                              │
   Breviarium/*.pdf ──3b_pdf──┤               lo que la fuente no trae
                              │
                            4_app
                              │
                              ▼
        app/datos/horas.json + horas_dias.json   lo que lee el teléfono
```

```bash
python Breviarium/src/1_bajar.py
python Breviarium/src/2_extraer.py
python Breviarium/src/3_ordenar.py
python Breviarium/src/3b_pdf.py      # sólo si cambian los PDF; necesita pdftotext
python Breviarium/src/4_app.py
```

`TRABAJO` **no está dentro del proyecto**: por omisión es
`%LOCALAPPDATA%\breviarium` (o `~/.cache/breviarium`), y se cambia con la
variable de entorno `BREVIARIUM_TRABAJO`. Ni el volcado ni el corpus se
versionan —se rehacen con una orden— y tenerlos dentro de una carpeta
sincronizada con la nube sale caro: cada pasada dispara una subida de
cientos de megas que compite por el disco con la pasada siguiente. Medido
en esta máquina, **multiplica por quince** lo que tarda la extracción (de
minuto y medio por año a veinticinco).

Cada fase deja su informe al lado de lo que produce (`datos/*_qa.txt`):
qué encontró, qué no supo colocar y dónde los años no se ponen de acuerdo.
Esos informes son el control de calidad del módulo, y conviene mirarlos
antes de fiarse de lo que sale.

---

## Lo que hay en `datos/libro/`

| fichero | qué guarda | clave |
|---|---|---|
| `ordinario.json` | lo invariable de cada hora | `hora/sección` |
| `salterio.json` | la salmodia ferial | `tiempo/salterio/día/hora` |
| `tiempo.json` | el propio del tiempo | `tiempo/semana/día/hora/sección` |
| `santoral.json` | lo propio de cada santo | `mm-dd/santo/hora/sección` |
| `comunes.json` | los comunes | `común/hora/sección` |
| `santoral_indice.json` | qué se celebra cada día del año | `mm-dd` |
| `bienal.json` | la lectura bíblica del Oficio de cada año del ciclo bienal | `tiempo/semana/día/oficio/sección` → `I`, `II` |
| `resenas.json` | la reseña biográfica de cada celebración | `mm-dd/santo` |
| `pdf_santoral.json` | el Propio de los santos de los cuatro tomos en PDF | lista de entradas |

En las claves, *día* es el día de la semana (0 = domingo) y *sección* es
una de `invitatorio`, `himno`, `salmodia`, `lectura1`, `lectura2`,
`responsorio`, `lectura_breve`, `responsorio_breve`, `cantico_evangelico`,
`preces`, `oracion`… Los días sin semana numerada —el Triduo, la Navidad—
usan `tiempo/@/título`.

Cada casilla trae el texto canónico (`lineas`), su rótulo, cuántos
testigos lo avalan y desde cuándo; y, si los años discrepan, la lista de
`variantes` con sus ciclos, sus años feriales y sus fechas.

---

## Qué se celebra cada día, y qué se puede elegir

El libro guarda las piezas; qué día se reza cuál no lo decide este módulo,
sino el **calendario del proyecto**, el mismo de la misa, que ya resolvió
la concurrencia con la Tabla de los días litúrgicos. La fase 4 sólo
aprende en qué casillas del santoral están los textos de cada celebración
de ese calendario: comparando los nombres en las fechas en que la fuente
y el calendario se solapan, y, para lo que no coincidió nunca, por el
nombre a secas. Así un santo no sale en domingo, y las fiestas móviles
—el Sagrado Corazón, Cristo Rey— caen en su día y no en el que cayeron el
año del volcado. Lo que el calendario celebra y la fuente no dio nunca
queda en el informe (`app_qa.txt`), y la app lo dice en vez de callárselo.

Sobre eso la app aplica las rúbricas del *Ordinario de la Liturgia de las
Horas* (están en cada tomo en los PDF de esta carpeta):

| en las memorias | de dónde |
|---|---|
| invitatorio, himno; en Laudes y Vísperas, de la lectura breve a las preces | propio; si no, **a elegir** entre el común y la feria |
| salmodia | del salterio, salvo que sea propia |
| lectura bíblica del Oficio | del propio del tiempo |
| lectura hagiográfica y oración | propio o común |
| Hora intermedia y Completas | de la feria: no mencionan la memoria |

Una memoria libre se puede celebrar o dejar; en las ferias privilegiadas
una memoria sólo cabe como **conmemoración** (lectura hagiográfica y
oración en el Oficio; antífona y oración en Laudes y Vísperas); y el
sábado las vísperas son las primeras del domingo, que en la Tabla están
por encima de cualquier memoria y de las fiestas de los santos.

---

## Aviso sobre los textos

La traducción es la litúrgica aprobada para México, y se reproduce tal
como la publica la fuente. Este módulo no traduce, no corrige y no
compone: sólo ordena. Cuando la fuente trae una errata, la errata llega
hasta aquí —y por eso el canónico se decide por mayoría de años, que es
la única manera de que una errata de un año no se imponga a los otros
siete.

---

## Lo que la fuente no trae: los PDF

La fuente reza la feria en las memorias libres, y por eso de unos noventa
santos —san Bruno, santa Eduviges, san Juan Damasceno…— no publicó nunca
nada. No es que se perdieran: no están en ninguno de sus años ni en la
historia del repositorio, que empieza en 2019.

Los cuatro tomos en PDF de esta carpeta (la edición de la Conferencia
Episcopal Española) sí los traen. La fase `3b_pdf` lee su Propio de los
santos —reseña, grado, común del que se toma lo demás, y cada sección— y
la fase 4 lo usa con un orden de preferencia estricto:

1. **la fuente**, siempre que tenga el texto;
2. **la fuente en otro sitio**: antes de usar un texto del PDF se busca en
   todo el libro (tiempo, santoral, comunes, salterio, con las variantes de
   todos los años), comparando por tripletas de palabras para que dos
   ediciones del mismo texto se reconozcan aunque difieran en alguna
   palabra. Si está, se usa el de la fuente (y si era su forma pascual y el
   santo cae fuera de Pascua, sin el aleluya);
3. **el PDF**, sólo si no está en ninguna parte. Esos textos llevan la marca
   `f: "pdf"`, y la app los señala con un discreto «ed. española».

Todo queda apuntado en `datos/pdf_usado.txt`: qué celebraciones salen del
PDF y con qué común, qué textos se hallaron en la fuente, y un cotejo de
citas, antífonas e himnos entre el PDF y la fuente en los santos que tienen
los dos (ahí no se cambia nada: manda la fuente). Los PDF no se versionan;
`pdf_santoral.json` sí, así que la fase 3b sólo hay que repetirla si
cambian los tomos.

## Lo que más se puede elegir

* **La reseña** del santo o de la fiesta abre el Oficio de lectura, como en
  el libro (`resenas.json`, de la fuente; si no la dio, del PDF).
* **Himnos.** Del himno del día se ofrecen los otros que la fuente dio ese
  mismo día en otros años; en Completas, los del tiempo —y en el ordinario,
  los de su mitad, semanas I-XVII o XVIII-XXXIV, que es el corte de los
  tomos III y IV—, que son dos y se turnan. Van numerados (I, II, III…)
  junto al rótulo.
* **La antífona final de la Virgen**: las cuatro del Ordinario, en su orden
  (I *Dios te salve*, II *Madre del Redentor*, III *Salve, Reina de los
  cielos*, IV *Bajo tu amparo*); en Pascua, *Reina del cielo*. La que se
  elige una noche sale marcada la siguiente.
* **La lectura bíblica del Oficio, por años.** La fuente sigue el ciclo de
  dos años: medido, en 307 de los 350 días del tiempo la primera lectura
  (y su responsorio) es una los años impares y otra los pares, y cada año
  repite siempre la suya. La mayoría de todos los años se quedaba con una
  sola, y salía la del año I en el II. Ahora `3_ordenar` decide por mayoría
  *dentro de cada año*, contando también las memorias, que leen la del
  tiempo, y lo deja en `bienal.json`; la fase 4 lleva a la app sólo el
  texto del año que no coincide con el de `tiempo.json`.
* **La Hora intermedia.** La fuente reza las tres horas y reparte: la
  salmodia del día en una —no siempre la misma— y la complementaria
  (salmos 119-121, 122-124, 125-127) en las otras dos. La fase 4 deja dicho
  dónde está la del día de cada día del salterio y cuál es la
  complementaria de cada hora, y la app ofrece las dos en las tres horas
  (por omisión, la del día en Sexta). Los himnos de Tercia, Sexta y Nona
  se ofrecen por tiempos, y en el ordinario por mitades (semanas I-XVII y
  XVIII-XXXIV, que es el corte de los tomos III y IV), según lo que la
  fuente reza en cada una: lo que asoma un par de veces en la semana de la
  frontera (menos del 5 % de los testigos) no cuenta.
* **El Te Deum** («Himno: Señor, Dios eterno» en la fuente) va tras el
  segundo responsorio, no al final del Oficio.

