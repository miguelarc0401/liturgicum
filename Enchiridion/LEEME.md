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
   app/datos/horas.json ─┐                   │
   app/datos/ordinario ──┼─4_castellano──▶ datos/castellano.json
   Compendio (4a) ───────┘                   │
                                             └─5_app──▶ app/datos/devocionario.json
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

### 5. La app

Junta todo en `app/datos/devocionario.json` (1,1 MB) y decide lo que se
publica. La app lo carga sólo cuando se abre el devocionario, como las
horas.

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
* **el inglés**, que está bajado y guardado, esperando permiso.
