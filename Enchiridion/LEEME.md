# Enchiridion — el devocionario latino

Las oraciones de la Iglesia en latín, puestas en la ortografía de los libros
litúrgicos y con su traducción castellana donde se ha podido verificar de
dónde sale. Son **461 piezas**: el Padre nuestro y el Ave María, los himnos
de santo Tomás y de Prudencio, las letanías, los oficios parvos, los salmos
penitenciales, las oraciones antes y después de la misa, y un montón de
oraciones medievales que no están en ningún otro sitio.

Es el tercer libro de la app, y el único que no va por fechas: el
leccionario da lo que se lee en la misa, el Breviarium lo que se reza a lo
largo del día, y éste lo que se reza cuando se quiere.

---

## De dónde salen los textos

Del **Thesaurus Precum Latinarum** de Michael Martin,
<https://www.preces-latinae.org>, que lleva publicándose desde 1998 y es la
colección de oraciones latinas más completa que hay en internet. Como el
sitio del Breviarium, **el sitio es el libro**: no hay base de datos ni API,
hay 568 páginas de HTML escrito a mano, y en su regularidad está toda la
información.

| en el original | quiere decir |
|---|---|
| tabla con `cellpadding="10"` | la oración (las de `2` son el comentario) |
| dos celdas al 48 % | latín a la izquierda, inglés a la derecha |
| `<font size="+3\|+2\|+1" color="#AF0000">` | la versalita con que abre la oración |
| `<font size="-1" color="#AF0000">` | la rúbrica, que también es rúbrica en latín |
| `<b>V.</b>` `<b>R.</b>` | el versículo y su respuesta |
| `<i>…</i>` | lo que se dice sólo en ciertos casos |
| `<center><b>…</b></center>` | un titular dentro de la oración |
| `<sup>` | nota al pie del autor, que no es texto |

Una recopilación anterior intentó bajar el sitio con un navegador y se quedó
en 178 de 495 páginas, porque el cliente bloqueaba el resto. Con una
petición normal responde sin problema, y de ahí salen las 568. De los 19
enlaces que no contestan, los 19 están rotos en el propio sitio: la página a
la que apuntan existe en otra carpeta y está bajada.

---

## Las fases

```
   el sitio ──1_bajar──▶ TRABAJO/fuente/        568 HTML tal cual
                         │
                         ├─2_piezas──▶ TRABAJO/piezas.json      532 piezas
                         │                                      (65 duplicadas)
   data/acentos_*.csv ───┤
   cache/acentos/ ───3a_acentos──▶ datos/acentos_*.csv, jota_uso.csv…
                         │
                         └─3_eclesiastico──▶ TRABAJO/piezas_ecl.json
                                             │
   app/datos/horas.json ─┐                   ├─4c_formas──▶ datos/formas.csv
   app/datos/ordinario ──┼─4_castellano──┐   │
   Compendio (4a) ───────┘               │   ├─4d_himnario──▶ datos/himnario.csv
                                         │   │   (del Breviario de cache/acentos)
                                         └───┴─5_app──▶ app/datos/devocionario.json
```

La carpeta de trabajo **no está dentro del proyecto** —por omisión
`%LOCALAPPDATA%\enchiridion`, y se le puede decir otra con
`ENCHIRIDION_TRABAJO`—: el volcado se rehace con una orden y no se versiona.
Lo que sí entra en el repositorio es lo que no se puede rehacer sin
investigar: las tablas de la fase 3a, el castellano de la fase 4 y los
informes de cada fase.

### 1. Bajar

Recorre el sitio entero desde el índice siguiendo cuanto enlace salga. No
parte de una lista: la cadena «Next» con que el sitio encadena cada oración
con la siguiente garantiza que no se queda ninguna fuera por no estar en
ningún índice.

### 2. Piezas

Una página no es una oración: puede llevar varias (los tres actos de fe,
esperanza y caridad viven en una). Se parte por los títulos centrados y por
las líneas de procedencia —«By Pietro Cardinal Gasparri, Catechismus
Catholicus, (1931)»—, que es lo único que distingue dos versiones de la
misma oración.

El comentario histórico de cada página **no se guarda**: es de Martin, y
además no es la oración. De la línea de procedencia sólo pasa el año.

La trampa de esta fase es la versalita. El HTML dice
`<font +3>A</font><font +1>DORO</font> te devote`, que en texto llano sería
«ADORO te devote», y lo que hay que escribir es «Adoro te devote». Se baja a
minúscula, y los nombres propios se levantan otra vez con el vocabulario del
propio proyecto —el Misal latino y el Ordinario, que traen sus mayúsculas
puestas—; así «AVE MARIA» sale «Ave María» y no «Ave maria». Las 73
versalitas de más de una palabra están listadas en `datos/piezas_qa.txt`.

### 3. Del latín clásico al eclesiástico

El sitio imprime «iustitia», «eius», «caelis», y sin un solo acento. Los
libros litúrgicos imprimen «justítia», «ejus», «cælis». Son tres cambios, y
ninguno es de adorno: son los que permiten leer y cantar el texto sin saber
latín, y son los que ya usa el resto de la app (la Vulgata Clementina del
leccionario se sirve así).

**La jota.** La i que suena como consonante se escribe j. No se deduce de la
ortografía: es léxica. Se resuelve por orden de autoridad, y cada palabra
deja constancia de por qué:

| | decide | casos |
|---|---|---|
| 1 | `datos/jota_mano.csv` | decisión a mano |
| 2 | el testigo impreso | 290 |
| 3 | tres reglas (i inicial, prefijo + raíz, entre vocales) | 46 |
| | se queda en i porque un testigo la escribe así | 4 421 |

El testigo son la Vulgata Clementina del leccionario —que escribe «ejus»
donde la Nova Vulgata escribe «eius», verso a verso— y el Breviario de
Divinum Officium. Valen por lo que no dicen tanto como por lo que dicen:
«Isaíæ» y «iisdem» prueban que ahí la i **no** es consonante, que es la
mitad que las reglas no sabrían.

**La ligadura.** `ae`→`æ` y `oe`→`œ`, salvo donde el diptongo no lo es y
entonces lleva diéresis: «Israël», «Michaëlis», «Saül». 1 056 ligaduras y 18
diéresis.

**El acento.** Lo pone el acentuador del leccionario (`src/13_acentos.py`),
que resuelve cada palabra por el uso impreso, la posición, las cantidades
vocálicas y las terminaciones aprendidas. Pero sus léxicos van recortados al
vocabulario de la Vulgata, y el devocionario trae 14 464 claves latinas, con
vocativos y latín medieval que la Vulgata no usa. Así que la **fase 3a**
vuelve a cosechar las dos fuentes externas que ya estaban bajadas —el
Breviario acentuado de Divinum Officium y las cantidades de Morpheus— para
este vocabulario, y saca 2 948 cantidades vocálicas, 51 jotas y 4 hiatos que
el leccionario no tenía.

Con eso, de dónde sale cada acento:

| uso impreso | 8 107 | posición | 2 878 | cantidad | 840 |
|---|---|---|---|---|---|
| **terminación** | 245 | **analogía de tema** | 210 | **a mano** | 29 |
| **hiato** | 317 | **prefijo** | 61 | **por omisión** | 169 |

La **analogía de tema** es lo único que este módulo añade al método del
leccionario, y es para lo que ninguna autoridad resuelve: la cantidad de una
sílaba es del tema y no de la desinencia, así que si «ángelus», «ángeli» y
«ángelo» llevan el acento en la antepenúltima, «ángele» lo lleva donde
ellas. Medido dejando fuera cada forma y preguntando a las 52 000 del uso,
acierta el **95,9 %** cuando una respuesta dobla a la otra; lo que no dobla
no se decide. Las 210 decisiones están listadas una por una en
`datos/eclesiastico_qa.txt`, y las 169 que se quedan sin resolver también.

Los trece salmos de la Nova Vulgata no se tocan más que en el acento: esa
edición escribe «iustus» y «caeli» a propósito, igual que en el leccionario.
La ortografía es de la edición; el acento es de quien reza.

### 4. El castellano

El sitio no tiene castellano. Hay que buscarlo oración por oración, y no
todas lo tienen. El orden es éste, y cada pieza guarda por cuál de los
cuatro pasos llegó:

1. la traducción oficial mexicana;
2. **la que ya está dentro de esta app**, cuando la pieza es literalmente la
   misma —la Liturgia de las Horas y el Misal en la traducción que se usa en
   México están en `app/datos/`—;
3. la Santa Sede u otro episcopado, diciendo de qué país es;
4. una versión tradicional castellana de fuente eclesiástica verificable,
   marcada como no oficial.

De momento, **55 de 461**:

| de dónde | cuántas |
|---|---|
| el salterio de la Liturgia de las Horas (los 13 salmos, en sus dos ediciones latinas) | 26 |
| el apéndice bilingüe del Compendio del Catecismo | 15 |
| la Liturgia de las Horas: antífonas finales y cánticos evangélicos | 8 |
| el Ordinario de la misa | 6 |

Con el Ordinario y con el Compendio el emparejamiento no se supone: los dos
libros imprimen el latín al lado del castellano, así que la pieza latina del
devocionario se busca **en el latín del libro** y la traducción viene con
él. Se exige un parecido del 93 %; el Confíteor tridentino, que nombra a san
Miguel y a los apóstoles, se queda en 0,25 contra el del Misal y por eso no
se empareja: no es la misma oración.

`null` no significa que no exista traducción: significa que aquí no se ha
verificado cuál es ni de dónde sale. Las 406 pendientes están listadas en
`datos/castellano_qa.txt`.

### 4c. Qué es cada pieza

Un devocionario no se hojea sólo por *a quién* se reza: también por *qué es*
lo que se va a rezar. No es lo mismo abrir una letanía de seis minutos que
una jaculatoria de nueve palabras, y en la lista las dos ocupan la misma
fila. Esta fase le pone a cada pieza su forma —son **veintiocho**— y escribe
en `datos/formas_qa.txt` por qué señal se decidió cada una.

**La forma no se adivina por el título: se lee en la hechura del texto.** Un
título puede faltar o mentir —hay cuatro piezas que se llaman «Dómine Jesu
Christe»—, pero la hechura no: una letanía tiene el Kýrie y una respuesta
que vuelve veinte veces; una colecta es prosa y acaba en «Per Christum
Dóminum nostrum»; un himno son renglones cortos y parejos; una conmemoración
es antífona, versículo y oración, en ese orden.

| | |
|---|---|
| de la Escritura | salmo · cántico · salterio |
| del canto | himno · secuencia · antífona · aclamación · pregón |
| del rezo en coro | letanía · preces · conmemoración · responsorio |
| de la devoción | oficio parvo · novena · rosario · vía crucis · ejercicio · rito |
| de la liturgia | oración (la colecta) · bendición |
| del alma | jaculatoria · súplica · acto · ofrecimiento · consagración · acción de gracias |
| de la doctrina | credo · fórmula |
| y de varias | colección, que es una pieza con un juego de oraciones dentro |

Salen 132 oraciones, 108 himnos, 43 letanías, 18 conmemoraciones, 15
súplicas, 12 oficios parvos, 11 novenas, 11 jaculatorias, 9 colecciones y el
resto en grupos pequeños. Donde la hechura engaña hay **una tabla a mano**,
como en los acentos: `datos/formas_mano.csv`, veinte piezas con su razón
escrita —el *Te Deum* acaba en versículos y no por eso deja de ser el himno
ambrosiano; el *Ánima Christi* está en verso y nadie lo llama himno; *Si
quæris mirácula* es el responsorio de san Antonio—.

### 4d. A qué hora se canta cada himno

En el sitio, 32 himnos están en una carpeta llamada «Tiempo ordinario» y no
son de ningún tiempo: son **el himnario del día**. *Jam lucis orto sídere* es
de Prima, *Te lucis ante términum* de Completas, y la serie de Vísperas
—*Lucis Creátor óptime*, *Imménse cæli Cónditor*, *Tellúris ingens
Cónditor*— es la de Gregorio Magno, un himno para cada día de la semana
siguiendo los días de la creación. Por orden alfabético, todo eso se pierde.

La hora no hay que deducirla: **el Breviario la dice**. El volcado de Divinum
Officium que la fase 3a ya usa para los acentos no es una lista de palabras,
es el libro entero, y sus ficheros rotulan cada himno con su hora, su día y
su tiempo: `[Hymnus Prima]`, `[Hymnus Day1 Laudes]` (Day0 es el domingo),
`[Hymnus Adv Vespera]`, `[Day3 Hymnus]` en Maitines, y
`@:Hymnus Day5 Vespera:s/un verso/otro/` para el que se canta cambiando dos
versos. Se cotejan por el íncipit —las cuatro primeras palabras, sin
acentos, sin ligaduras y con la i y la j confundidas— y el cotejo es exacto:
o casa el verso o no casa.

**64 piezas se quedan con su hora**: 17 de Maitines, 18 de Laudes, 19 de
Vísperas, una por cada hora menor, y seis de Completas —el *Te lucis ante
términum*, el *Nunc dimíttis* y las cuatro antífonas finales de la Virgen,
que están en otro fichero del Breviario y por tiempos—. Los tres cánticos del Evangelio son lo único que se pone a mano
aquí, porque el Breviario los guarda con los salmos y no con las horas. Lo
que no casa sale en el devocionario bajo «sin hora en el Breviario», que es
la verdad y no un hueco.

### 5. La app

Junta todo en `app/datos/devocionario.json` (1,1 MB), decide lo que se
publica y **lo ordena**. La app lo carga sólo cuando se abre el devocionario,
como las horas.

El orden cambió el 2026-10-14. Antes eran las carpetas del sitio
renombradas —veintiún grupos—, y las carpetas del sitio **mezclan tres
criterios en el mismo nivel**: a quién se reza (Trinidad, Virgen, san José),
qué es la pieza (himnos, salmos, credos) y cuándo se reza (antes de la misa,
los tiempos del año). De ahí salían dos estorbos: el año litúrgico vivía en
dos sitios —«Los tiempos del año», tres piezas, y cuarenta y tres himnos de
tiempo en otra carpeta—, y el himnario del día quedaba escondido en una
lista alfabética.

Ahora son **once capítulos, por cuándo y a quién**, con una regla sola:

> una pieza vive en un solo sitio —cuándo o a quién—, y lo que la pieza es
> no es una carpeta: es una señal en la fila y un filtro que atraviesa el
> libro entero.

| capítulo | piezas | por dentro |
|---|---|---|
| Las oraciones comunes | 17 | lo que se reza de memoria |
| El día | 8 | la mañana, la mesa, la noche |
| La misa | 30 | antes, después, la comunión |
| La confesión | 8 | |
| El año litúrgico | 46 | los nueve tiempos, con sus himnos |
| Las horas del día | 33 | el himnario, por la hora del Breviario |
| A Dios | 92 | Trinidad, Padre, Hijo, Espíritu, Eucaristía |
| A la Virgen y a los santos | 153 | veinte secciones |
| En cada necesidad | 22 | la paz, el Papa, el viaje, los difuntos |
| La Escritura | 30 | salmos y cánticos |
| Para saber de memoria | 22 | credos y fórmulas |

Y tres cosas más que el orden necesitaba:

* **las colecciones.** Hay piezas que no son oraciones sueltas sino partes
  de una devoción —las nueve novenas de letanías a san Benito, los siete
  días de su semana, los trece salmos en sus dos ediciones—, y ocupaban
  veintiséis filas indistinguibles. Van plegadas en una fila que se abre: la
  sección de san Benito pasa de 26 filas a 10;
* **la marca del Compendio.** Las veintidós del apéndice del Compendio del
  Catecismo llevan su marca donde vivan, y sólo una por oración: cuando hay
  tres «Veni, Sancte Spíritus», la marca va a la que el Compendio emparejó
  de verdad en la fase 4, no a las tres;
* **lo que distingue dos piezas del mismo nombre.** Antes era el año o
  «versión 2»; ahora, cuando no hay año, es el primer renglón, que es lo que
  de verdad las separa.

---

## Los derechos

El aviso del sitio —<https://www.preces-latinae.org/Copyright_Notice.html>—
permite, y anima, el uso personal y de estudio sin ánimo de lucro, que es el
de esta app; y prohíbe la reproducción fuera de eso sin permiso del autor.
La app, además, está publicada en GitHub Pages y el repositorio es público.
De ahí tres decisiones:

* **el latín se publica.** Son textos tradicionales, impresos desde hace
  siglos; lo que el sitio aporta es la transcripción, y se le atribuye en
  cada oración;
* **el inglés no.** La traducción inglesa es obra de Michael Martin. Se baja
  y se guarda en la carpeta de trabajo —por si algún día hay permiso— y no
  entra ni en el repositorio ni en la app;
* **el comentario tampoco.** La historia de cada oración y la nota de la
  indulgencia son suyas, y además no son la oración. De la línea de
  procedencia sólo pasa el año, que es un dato.

Del castellano, cada oración dice en la app de dónde sale, con qué autoridad
y para qué territorio, y si es traducción aprobada o no.

---

## Cómo se rehace

```bash
python Enchiridion/src/1_bajar.py          # el volcado del sitio (568 HTML)
python Enchiridion/src/2_piezas.py         # las piezas
python Enchiridion/src/3a_acentos.py       # las tablas de este vocabulario
python Enchiridion/src/3_eclesiastico.py   # jota, ligadura y acento
python Enchiridion/src/4a_compendio.py     # el apéndice del Compendio
python Enchiridion/src/4_castellano.py     # el castellano y su procedencia
python Enchiridion/src/4c_formas.py        # qué es cada pieza
python Enchiridion/src/4d_himnario.py      # la hora de cada himno
python Enchiridion/src/5_app.py            # app/datos/devocionario.json
```

La 3a necesita `cache/acentos/`, que baja `python src/13a_crawl_acentos.py`.
Después, `.\publicar.ps1` firma los datos y los sube.

---

## Lo que falta

* **el castellano de 406 piezas.** Las que tienen traducción oficial
  mexicana o de la Santa Sede se van resolviendo por fuentes bilingües, que
  es lo que permite emparejar sin suponer; las letanías medievales y los
  oficios parvos probablemente no la tengan, y ésas se quedarán en latín con
  su ficha diciendo por qué;
* **los títulos castellanos.** Cuando una pieza tiene traducción pero no
  título propio, la lista enseña su primer renglón;
* **169 acentos por omisión**, listados en el informe, que son palabras que
  no usan ni la Vulgata ni el Breviario;
* **trece títulos heredados de la fase 2**: diez que se quedaron en
  versalita entera (`DOMINICA`, `FERIA QUARTA`, `I. LITANIÆ`) y tres que
  están en inglés y acentuados como si fueran latín («Práyers of St.
  Bridget», «The Chord of St. Joseph», «Subjects for Daíly Meditátion»). Se
  arreglan en la fase 2 y se notan en cualquier orden, porque la fila es el
  título;
* **52 himnos sin hora** —de 108, y sólo 7 de ellos en el capítulo de las
  horas—, que son los que el Breviario canta con otro texto
  —*Cónditor alme síderum* frente a *Creátor alme síderum*, que es la
  revisión de 1632— o que no están en él;
* **el inglés**, que está bajado y guardado, esperando permiso.
