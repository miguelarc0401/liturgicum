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
                            4_app
                              │
                              ▼
        app/datos/horas.json + horas_dias.json   lo que lee el teléfono
```

```bash
python Breviarium/src/1_bajar.py
python Breviarium/src/2_extraer.py
python Breviarium/src/3_ordenar.py
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
Horas* (están al final de cada tomo en los PDF de esta carpeta, que sólo
se consultan por sus rúbricas: los textos son siempre los de la fuente):

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
