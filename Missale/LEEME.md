# Missale — el misalito diario en castellano

El tercer libro. El leccionario da en latín lo que se lee en la misa; el
*Breviarium*, en castellano lo que se reza a lo largo del día. Falta la misa
entera en castellano: **las lecturas y los propios** —antífonas, colecta,
oración sobre las ofrendas, prefacio, oración después de la comunión—, con lo
que el Misal deja a elegir.

Tres fuentes, y cada una da lo que las otras no:

| fuente | qué da | lengua | cobertura |
|---|---|---|---|
| `latin_missal2002_organized.pdf` | el Misal Romano entero: propios, prefacios, Ordo Missæ, plegarias eucarísticas | latín | **completa** |
| `Ordinario de la Misa México (1).pdf` | el Ordinario con sus rúbricas numeradas, los 67 prefacios y las plegarias eucarísticas I-IV | castellano de México | **completa**, de lo que es ordinario |
| `Misalitos/` (100 PDF mensuales, 2018-2026) | lo que se celebró cada día: lecturas y propios | castellano de México | **lo celebrado**, no el libro |

Con la tercera fuente —que llegó después de la primera versión de este
documento— la mitad fija de la misa deja de ser una cosecha y pasa a ser una
traducción oficial: no hay que reconstruir el Ordinario a partir de lo que cada
mes imprimía al principio. Lo que sigue dependiendo de los misalitos es lo que
cambia cada día.

---

## Lo que ya está comprobado

Nada de lo que sigue es estimación: está medido sobre los ficheros de esta
carpeta.

### Las tres fuentes tienen capa de texto

Ninguna hace falta pasar por OCR. Los cien misalitos dan entre 1 500 y 2 500
caracteres por página; el Ordinario castellano, 127 páginas a 977; y el Misal
latino 828 páginas con el latín **ya acentuado**, que es justo lo que al
leccionario le costó una fase entera.

### El Misal latino está rotulado, no maquetado

Las etiquetas del libro son literales y se cuentan:

| rótulo | veces |
|---|---|
| `Collecta` | 616 |
| `Post communionem` | 478 |
| `Super oblata` | 477 |
| `Ant. ad introitum` | 442 |
| `Ant. ad communionem` | 438 |
| `Oratio super populum` | 44 |
| `PRÆFATIO …` (los del cuerpo de prefacios) | 50 |
| `PREX EUCHARISTICA …` | 14 |
| `Die N mensis` (santoral) | 202 |
| `ORDO MISSÆ` | 1 |

Son unos 600 formularios completos. Se parsea como se parseó la Vulgata: por
rótulo, no por posición.

El Ordo Missæ latino está dentro, desde la página 303, con sus rúbricas
numeradas (`1. Populo congregato…`, `83. V. Dóminus vobíscum`), las *Preces
eucharisticæ* —el Canon Romano, II, III, IV, las de la reconciliación y la de
diversas necesidades—, los tonos cantados y el *Ordo Missæ cuius unus tantum
minister participat*.

### Los dos Ordinarios comparten la numeración del Misal

Esto es el hallazgo del Ordinario castellano, y vale una fase entera. El
castellano numera **1-146** y el latino **1-146**, y el número dice lo mismo en
los dos:

| n. | castellano | latín |
|---|---|---|
| 1 | Reunido el pueblo, el sacerdote con los ministros va al altar… | Populo congregato, sacerdos cum ministris ad altare accedit… |
| 19 | Para utilidad de los fieles, en lugar del símbolo niceno-constantinopolitano… | Loco symboli nicæno-constantinopolitani, præsertim tempore… |
| 83 | V/. El Señor esté con ustedes. | V. Dóminus vobíscum. |
| 132 | El sacerdote hace genuflexión, toma el pan consagrado… | Sacerdos genuflectit, accipit hostiam, eamque aliquantulum… |

Comprobados 1, 2, 4, 15, 19, 31, 83, 89, 124, 132 y 142: todos cuadran. El
Ordinario bilingüe, por tanto, **no hay que alinearlo a mano**: se alinea por
el número de rúbrica, y si algún número no cuadrara el informe lo dice en vez
de inventar la correspondencia.

### El Ordinario castellano trae las alternativas, que es lo que permite elegir

No es un texto corrido: es el libro con sus opciones abiertas. Los tres saludos
iniciales (y el del obispo), las cuatro invitaciones al acto penitencial con
sus fórmulas I, II y III, los dos símbolos —niceno-constantinopolitano y el de
los apóstoles, éste «especialmente en el tiempo de Cuaresma y en la Cincuentena
pascual»—, las tres fórmulas del *Misterio de la fe*, las invitaciones al
padrenuestro y a la paz, las cinco despedidas, y en las plegarias eucarísticas
el *Reunidos en comunión* propio, las *Intercesiones particulares* y los
insertos propios (el del bautismo de niños, entre otros).

Esa es exactamente la materia de lo que pediste poder escoger, y viene marcada
en la fuente con «O bien:», que es un rótulo tan bueno como los demás.

### Lo que el Ordinario castellano no trae

Las **plegarias eucarísticas de la reconciliación** (I y II) y las de
**diversas necesidades**, y las **bendiciones solemnes** y **oraciones sobre el
pueblo**, que sólo menciona en los números 142 y 143 («puede darse una de las
bendiciones solemnes o de las oraciones sobre el pueblo»). En latín están todas
en el Misal. En castellano, las oraciones sobre el pueblo de la Cuaresma sí las
imprimen los misalitos —es el rótulo `ORACIÓN SOBRE EL PUEBLO`, presente en los
20 ficheros cuaresmales—; las bendiciones solemnes y las dos plegarias de la
reconciliación, no: los misalitos las citan por página y no las copian. Es un
hueco pequeño y conocido.

### Los misalitos son regulares, en dos publicaciones —no en tres familias

*Corregido por la fase 3, que lo midió sobre los cien ficheros.* Lo que sigue
en este apartado se escribió mirando tres meses; al mirar los cien, la
división por años no se sostiene. Hay **dos publicaciones**:

| publicación | ficheros | de dónde |
|---|---|---|
| *La Santa Misa — Misal Diario* | **97** | Guadalajara |
| *Misal Diario — Palabra Viva* | **3** (enero, febrero y diciembre de 2021) | Mérida, Yucatán |

Los otros nueve meses de 2021 son *La Santa Misa* como los demás. Y el ancla
del pie no falta en tres ficheros: está en los cien, sólo que *Palabra Viva*
la escribe sin año («Viernes 1 de Enero») y *La Santa Misa* con él («viernes
1° de enero de 2026»).

Lo que de verdad cambia de una publicación a otra es la **cabecera** del
formulario: *La Santa Misa* titula «2 viernes / Blanco / Memoria, / SANTOS
BASILIO MAGNO…», y *Palabra Viva* «2 de Enero / SÁBADO / SANTOS BASILIO
MAGNO… / MR. pp. 685-686 (675-676) / Memoria - Blanco», con el grado y el
color en un mismo renglón.

### Los misalitos son regulares, en tres familias

Los diez rótulos del formulario —`ANTÍFONA DE ENTRADA`, `ORACIÓN COLECTA`,
`PRIMERA LECTURA`, `SALMO RESPONSORIAL`, `SEGUNDA LECTURA`, `ACLAMACIÓN ANTES
DEL EVANGELIO`, `EVANGELIO`, `ORACIÓN SOBRE LAS OFRENDAS`, `ANTÍFONA DE LA
COMUNIÓN`, `ORACIÓN DESPUÉS DE LA COMUNIÓN`— aparecen en **los cien
ficheros**. `ORACIÓN SOBRE EL PUEBLO` falta en 80, y es correcto: sólo la trae
la Cuaresma.

Cada página lleva al pie el día entero —«martes 13 de enero de 2026»—, y eso
es el ancla que parte el mes en días sin adivinar nada. Está en **97 de 100**.
Los tres que no (`misalEnero2021`, `misalFebrero2021`, `misalDiciembre2021`)
son otra familia de maqueta: titulan «1 de Enero», y además traen las
respuestas del diálogo («R/. Te alabamos, Señor») y las indicaciones de la
Liturgia de las Horas, que los demás no. Hay, pues, tres familias de maqueta
—2018-2020, 2021 y 2022-2026— y el parseo necesita las tres, no una con
remiendos.

El encabezado de cada día da, además: día y día de la semana, color («Verde /
Blanco»), grado, título, reseña histórica y una referencia doble —`MR p. 663
[678] / Lecc. I p. 487`—. Las páginas del *MR* son de las ediciones
castellanas (Buena Prensa y BAC), no del PDF latino: sirven para cotejar con el
libro impreso, no para enlazar fases.

### Los salmos no hay que renumerar

En 84 comparaciones de tres meses, el número de salmo del misalito coincide con
el del formulario latino **80 veces**, y las cuatro restantes son días en que el
misalito eligió otro formulario, no un desfase. Desplazamientos de uno:
**cero**. El leccionario mexicano numera los salmos como la Clementina, y eso
ahorra aquí el trabajo que en la Nova Vulgata ocupó la §8.3 de `Vision.md`.

### El misalito reza la feria en las memorias

El 13 de enero de 2026 el calendario del proyecto pone primero a san Hilario;
el misalito imprime **la colecta del santo y la lectura continua de la feria**
(1 Sam 1, 9-20 y Mc 1, 21b-28). Es lo que prescribe el *Ordo lectionum Missae*
n. 82, y es exactamente la opción `memorias: 'feria'` que la app ya ofrece.

Consecuencia de diseño, no detalle: al emparejar hay que mirar **todas** las
celebraciones de la fecha, no la primera. En enero de 2026, mirando sólo la
primera, 16 días de 31 no cuadraban, y todos eran este caso.

### En las ferias no reza la feria: reza lo que el editor eligió ese año

*Hallazgo de la fase 4, y es lo que obliga a atribuir antes de contar.* Lo de
arriba se queda corto. El mismo **miércoles de la 11ª semana del tiempo
ordinario** trae, en los nueve años que el corpus lo alcanza, nueve cosas
distintas:

| año | lo que imprime | lo que dice la cabecera |
|---|---|---|
| 2018 | misa por la santificación del trabajo humano «B» | `o Misa por la santificación…` |
| 2019 | san Romualdo, abad (memoria libre) | `o SAN ROMUALDO, Abad` |
| 2020 | la misma del trabajo humano | `o Misa por la santificación…` |
| 2021 | misa del Espíritu Santo «A» | `Feria o / Misa del Espíritu Santo` |
| 2022 | misa por los laicos | `Feria o / Misa por los laicos` |
| 2023 | san Luis Gonzaga (memoria) | el título del día |
| 2024 | san Romualdo otra vez | `o SAN ROMUALDO, Abad` |
| 2026 | misa por los laicos otra vez | `Feria o / Misa por los laicos` |

Y sólo **un** año de los nueve imprimió la oración de la feria. De ahí dos
cosas:

1. **La mayoría de testigos no se puede tomar por fecha.** Agrupar por «el
   miércoles de la 11ª semana» y votar daría una colecta elegida entre nueve
   formularios que no son el mismo. Hay que atribuir cada texto a la
   celebración que de verdad explica los días en que aparece —la que está
   presente en **todos** ellos— y sólo entonces contar. Eso es lo que hace
   `atribuye()`, y el informe dice por qué camino se decidió cada texto: por
   lo que nombra la fuente (731), por lo que titula el día (984), por la
   fecha del año (408), por el común que comparten (27) o por el calendario
   (522).
2. **No hay que inventar la lista de opciones: la fuente la nombra.** Pero la
   nombra en tres campos distintos según cómo caiga la maqueta, y la fase 3
   los separaba sin saber que eran lo mismo: `alterna` cuando parte «Feria o»
   y el nombre en dos renglones (508 veces), `resena` cuando va en un solo
   renglón empezando por «o » (484) y `subtitulo` cuando la alternativa es un
   santo (58). Son 1 050 formularios, y de ellos **542 los tenía la fase 3
   fuera de `alterna`**. La fase 4 vuelve a leerlos del campo `crudo` y los
   unifica.

### El propio de México: 48 celebraciones que el calendario no trae

También de la fase 4. Los 245 avisos del informe son todos de lo mismo: el
misalito ofrece santos que el calendario del proyecto no tiene, porque el
calendario se armó con el general y éstos son los de México —san José María
Robles Hurtado, el beato Miguel Agustín Pro, los mártires cristeros, la
Virgen de Fátima, san Pascual Bailón, santa Rita—. Sus textos entran con
identificador `san_…` y `md_…`, y están nombrados uno a uno.

Para que entren hizo falta un candidato más, y conviene no volver a
derivarlo: **la fecha del año**. Un texto que sólo aparece los 17 de mayo es
de una celebración del 17 de mayo, se llame como se llame; sin ese candidato
se quedaba sin ninguna celebración que lo explicara y se iba fuera.

### Los comunes no se pueden atribuir a un común

Lo primero que se intenta —atribuir cada texto suelto al común que más de sus
días ofrezcan— **lo desmiente el propio reparto**, y por eso no se hace. La
antífona «El que quiera venir conmigo, que renuncie a sí mismo» se imprime en
**72 días**, y el común que más cubre, el de santos y santas, llega a 37:

| común | días de los 72 |
|---|---|
| santos y santas | 37 |
| mártires | 27 |
| pastores | 22 |
| doctores | 7 |
| santa María Virgen | 5 |
| vírgenes | 4 |

Porque la antífona está en varios comunes a la vez. Así que los 356 textos de
este tipo van a `sueltos_es.json` con ese reparto ya medido, común por común,
y los colocará la fase 5 contra los comunes del Misal latino, que los trae
enteros. Los que sí son de un solo común —el que ofrecen todos sus días, sin
una excepción— entran en `propios_es.json`.

### Una excepción, y nombrada: la fuente también traslada

La regla de «la celebración que está en **todos** los días» se rompe por un
solo día, y hay que admitirlo con cuentagotas. El 24 de junio de 2022 fue el
Sagrado Corazón, así que el misalito pasó la Natividad de san Juan Bautista
al 23 y lo dijo en un corchete —«[Anticipada del día 24]»— **que no vuelve a
usar en los cien ficheros**, de modo que no da para una regla. Con ese único
día desviado, la intersección de las nueve se quedaba vacía y las cinco
piezas de la solemnidad se iban con los textos sueltos.

Por eso se admite **una** excepción, y sólo cuando el texto tiene cuatro días
o más: son 108 textos, y cada excepción va nombrada con su día en el informe.
La regla sigue siendo conservadora donde importa: «El que quiera venir
conmigo» tiene 72 días y su mejor común cubre 37, muy lejos de 71, así que
sigue suelta.

### El renglón partido, que parecía cosmético y decidía el texto

El PDF corta la palabra al final del renglón y deja el guión: «…divino poder
dispon-» / «gas nuestros corazones…». Son **7 233 palabras** en el corpus, y
no es cosmético: sin juntarlas, los ocho testigos de una misma oración se
parten en dos grupos, la mayoría decide sobre un reparto falso y el texto
canónico sale con «dispon- gas» dentro. Al juntarlas, `pericopas_es.json`
pasó de 6,1 MB a 4,2 MB —eran variantes falsas— y las piezas con variantes
bajaron de 1 028 a 532.

### Cuánto del leccionario alcanzan ocho años de misalitos

El leccionario tiene **1 077 formularios** con texto.

| | formularios | |
|---|---|---|
| alcanzables desde alguna fecha (calendario 2024-2060) | 906 | 84 % |
| alcanzables en los 34 meses que hoy tienen misalito **y** calendario | 875 | 81 % |

La diferencia son 27 formularios del tiempo ordinario, 3 de Adviento y 1 de
Navidad, y los cubren los otros 66 misalitos en cuanto el calendario llegue a
2018. Los 100 ficheros van de junio de 2018 a septiembre de 2026: los tres
ciclos dominicales dos o tres veces cada uno, los dos años feriales cuatro, y
cada día del año civil ocho veces. Es la misma redundancia con la que el
*Breviarium* decide por mayoría de testigos, y aquí sirve para lo mismo.

Los **171 formularios que ninguna fecha alcanza nunca** son los que no se
celebran por calendario:

| sección | formularios |
|---|---|
| misas por diversas necesidades y votivas (lecc. VI) | 67 |
| misas rituales y de difuntos (lecc. VIII) | 35 |
| sin sección asignada en el índice | 26 |
| otros formularios del propio de los santos | 19 |
| apéndices | 7 |
| resto (Cuaresma, santos, Pascua, común, Navidad, sueltos) | 17 |

De ésos el castellano **no va a salir de los misalitos**. Sus propios sí salen
del Misal latino, completos. Es el hueco grande, y hay que decirlo, no taparlo.

### Los prefacios: los dos juegos no se corresponden

Los del tiempo y los comunes están **completos en castellano**: 67 en el
Ordinario, cada uno con su título y su epígrafe («PREFACIO III DE SANTA MARÍA
VIRGEN / MARÍA, MODELO Y MADRE DE LA IGLESIA»). Eso cierra de golpe el hueco
que la primera versión de este documento daba por abierto, cuando lo único que
había eran los 73 títulos que los misalitos imprimen sueltos.

Pero el juego castellano y el latino **no son el mismo juego**, y esto no es un
detalle de presentación:

| | castellano | latín 2002 |
|---|---|---|
| Adviento | **I-IV** | I-II |
| Navidad | I-III | I-III |
| Epifanía | 1 | 1 |
| Cuaresma | **I-V** | I-IV |
| Pasión del Señor | I-II | I-II |
| Pascual | I-V | I-V |
| Ascensión | I-II **+ «para después de la Ascensión»** | I-II |
| Domingos del tiempo ordinario | **I-X** | I-VIII |
| Bautismo, Confirmación, Penitencia, Unción | **4** | — (van en los rituales) |
| Santísima Eucaristía | **I-III** | I-II |
| Santa María Virgen | **I-V** | I-II |
| Apóstoles · Santos · Mártires | I-II cada uno | I-II cada uno |
| Pastores · Vírgenes y religiosos | 1 + 1 | 1 + 1 |
| Comunes | **I-IX** | I-VI |
| Difuntos | I-V | I-V |
| **total** | **67** | **50** |

De ahí que los misalitos citen «Prefacio I o III de Adviento» y «II o IV de
Adviento» (catorce veces cada uno): sólo tiene sentido con cuatro. Consecuencia
de diseño: `prefacios.json` lleva **su propio identificador**, y la
correspondencia latín↔castellano va en una tabla explícita, con los diecisiete
castellanos que no tienen pareja en el juego común latino marcados como tales
—varios de ellos sí están en el Misal latino, pero dentro de las misas rituales,
y hay que ir a buscarlos ahí—. Las referencias de los misalitos se resuelven
contra el juego **castellano**, nunca contra el latino.

Faltan los **prefacios propios**, que no están en ninguno de los dos juegos
comunes porque viven dentro de su formulario: Pentecostés, la Trinidad, el
Corpus, el Sagrado Corazón, Cristo Rey, la Transfiguración, la Santa Cruz, la
Dedicación, la Asunción, santa María Magdalena… En latín salen del formulario,
donde el Misal los imprime. En castellano salen de los misalitos, que al
principio de cada mes imprimen los del mes —ahí están los 73 títulos ya
contados, con «PREFACIO DE LA EPIFANÍA» y «PREFACIO María Magdalena:
‹Apóstola› de los Apóstoles» entre ellos—. Cuántos propios quedan sin cosechar
lo dirá el informe de la fase 4, cotejando los dos juegos contra las
referencias que los días citan.

---

## La idea: no parsear días, deshacer el libro

Un misalito publica **días ya armados**, igual que la fuente de las horas: el
13 de enero trae su colecta del santo, su lectura de la feria y su salmo, todo
seguido. Un misal hace el camino contrario: guarda cada pieza una vez, en su
sitio, y el día se arma al celebrarlo.

Deshacer la costura tiene aquí una ventaja que en las horas no había: **la
pieza viene con su cita**. «Del primer libro de Samuel 1, 9-20» dice qué es, y
el formulario latino dice `1 Rg 1,9-20`. El emparejamiento, por tanto, no se
adivina: se comprueba por dos caminos independientes, y se guarda el resultado
cuando los dos dicen lo mismo.

```
fecha del misalito ──▶ calendario del proyecto ──▶ celebraciones ──▶ claves
                                                                       │
     cita de la pieza castellana ──▶ cita del formulario latino ───────┘
                               (libro + capítulo + versículos)
```

Lo que cuadra por los dos caminos entra. Lo que cuadra por uno entra marcado.
Lo que no cuadra por ninguno va al informe y no entra. Y como cada pieza
aparece ocho veces, el texto canónico se decide **por mayoría de testigos**, y
las discrepancias se guardan como variantes con los años que las respaldan,
que es lo que impide que una errata de un año se imponga a los otros siete.

Las lecturas, además, se guardan **dos veces**: por formulario y por cita. Una
perícopa que el misalito nunca imprimió en el día de un santo puede estar
impresa en otro día que use la misma perícopa, y así se recupera. Las
adaptaciones de incipit («Hermanos:», «En aquel tiempo,») hacen que dos usos de
la misma perícopa no sean idénticos, así que el corpus por cita guarda
testigos, no un texto único.

### Lo que no se toma del misalito

Las **moniciones**, la **reflexión** y la **oración de los fieles** son obra
del editor, no del Misal ni del leccionario: no son traducción litúrgica
aprobada, y las escribe cada mes quien hace la revista. No entran. Lo que entra
es el texto litúrgico, que es traducción aprobada y es el mismo todos los años
—y por eso la mayoría de testigos funciona con él y con lo otro no.

---

## Las fases

Módulo aparte, con su proceso y su carpeta, como `Breviarium/`.

| fase | fichero | de qué a qué |
|---|---|---|
| 0 ✓ | — | `python src/18_santoral.py` : el calendario desde 2018, que ya es **el valor por defecto** del guion —estaba en 2024, y como `publicar.ps1` lo llama sin argumentos, cada publicación deshacía esta fase sin que nadie lo notara—. **Hecha.** La Pascua, la Ceniza y los dos ciclos de 2018-2023 cuadran con las fechas conocidas en las 28 comprobaciones, el calendario va ahora del 3 de diciembre de 2017 al 27 de noviembre de 2060 sin un día vacío, y los tres traslados de esos seis años son los que de verdad ocurrieron: la Anunciación de 2018 al 9 de abril, la Inmaculada de 2019 al 9 de diciembre y san José de 2023 al 20 de marzo, los tres de domingo a lunes |
| 1 | `Missale/src/1_latino.py` | el PDF del Misal 2002 → `datos/misal_latino.json`: formularios con sus cinco o seis piezas, prefacios comunes y propios, Ordo Missæ numerado, plegarias eucarísticas (con las de la reconciliación y diversas necesidades), bendiciones solemnes |
| 2 | `Missale/src/2_ordinario.py` | el PDF del Ordinario de México → `datos/ordinario_es.json` y `datos/prefacios_es.json`: las 146 rúbricas con sus alternativas («O bien:»), los dos símbolos, las plegarias I-IV con sus propios, y los 67 prefacios con título y epígrafe. **Alinea con el latino por número de rúbrica**, y lo que no cuadre va al informe |
| 3 ✓ | `Missale/src/3_extraer.py` | los 100 misalitos → `datos/misalitos/AAAA-MM.json`. **Hecha.** 3 290 formularios en los 3 044 días de los cien meses, sin un hueco: cada uno con su cabecera (día, color, grado, título, reseña y la referencia doble al Misal), sus piezas rotuladas con su cita, las rúbricas que el propio Misal imprime (Gloria, Credo, prefacio, plegaria, bendición solemne) y, marcado aparte, lo editorial |
| 4 ✓ | `Missale/src/4_piezas.py` | los días en bruto → `datos/libro/`. **Hecha.** 598 celebraciones con propios, 2 642 perícopas por cita, 28 prefacios propios cosechados enteros, 54 celebraciones con oración sobre el pueblo y 356 textos de los comunes que ninguna celebración explica, aparte y con su reparto medido. Canónico por mayoría de testigos, variantes con los días que las respaldan, y la construcción es byte a byte la misma en dos pasadas |
| 5 | `Missale/src/5_resolver.py` | las piezas + el Ordinario + el calendario + el índice del leccionario → `datos/libro/misa.json`, y `datos/resolver_qa.txt` con todo lo que no cuadró |
| 6 | `Missale/src/6_app.py` | → `app/datos/misa.json`, `lecturas_es.json`, `misal_latino.json`, `prefacios.json`, `ordinario.json` |

Las fases 1 y 2 no dependen de nada: ni del calendario de 2018, ni de los
misalitos, ni una de otra salvo para el cotejo final de la 2. Son el sitio por
donde empezar.

Después, `src/15_app_data.py` firma lo nuevo —como ya firma las horas— para que
el *service worker* del teléfono tire su caché, y `publicar.ps1` gana un paso.

El orden de preferencia de las fuentes, estricto y en este orden, como el del
*Breviarium* con sus PDF:

1. **el Ordinario de México**, para todo lo que es ordinario: el Ordo Missæ,
   los prefacios del tiempo y comunes, las plegarias I-IV. Es traducción
   oficial y completa, y no se discute con una cosecha;
2. **el misalito**, para lo que cambia cada día, siempre que tenga el texto de
   esa pieza;
3. **el misalito en otro sitio**: antes de dar algo por ausente se busca la
   pieza en todo el corpus (por cita, para las lecturas; por tripletas de
   palabras, para las oraciones, que es como se reconocen dos impresiones del
   mismo texto aunque difieran en una palabra);
4. **el Misal latino**, que no traduce nada: da el texto en latín, marcado, y
   la app dice que de castellano no hay.

Nunca se traduce. Si el castellano no está, se dice que no está.

---

## El modelo de datos

```
app/datos/misa.json          { formularios: { clave: {
                                 entrada: {t, c}, colecta, ofrendas,
                                 comunion: {t, c}, poscomunion, pueblo,
                                 gloria: bool, credo: bool,
                                 prefacio: [ref, …], f: 'misalito'|'latino',
                                 testigos: n, variantes: [ … ] } } }
app/datos/lecturas_es.json   como lecturas_clementina.json: bloques por clave
app/datos/misal_latino.json  lo mismo, en latín, para los 600 formularios
app/datos/prefacios.json     { id: {titulo_es, epigrafe_es, texto_es,
                                   la: <id latino | null>, titulo_la, texto_la,
                                   juego: 'tiempo'|'comun'|'propio',
                                   cuando: [ … ] } }
app/datos/ordinario.json     { rubricas: [ {n, es: [ … ], la: [ … ],
                                   alternativas: [ … ] } ],
                               plegarias: { … } }
```

El Ordinario va **por número de rúbrica**, que es lo que hace que el bilingüe
no necesite costura: cada entrada lleva su número, el castellano, el latín y
sus alternativas. Las rúbricas en que uno de los dos no tenga texto llevan la
marca y la app lo dice.

Las claves son **las del leccionario** (`I|1001AAVD01.html|0`), las mismas que
ya usan `indice.json` y `calendario.json`. Así la app no aprende un segundo
sistema de nombres, y la misa castellana es otra «fuente» al lado de la
Clementina y la Nova, no otra app.

Sobre el tamaño: `app/datos/` pesa hoy 38 MB, de los que 22 son las horas. Lo
nuevo son unos 14 MB, y se cargan sólo cuando se elige el castellano, como ya
pasa con `lecturas_clementina.json` y `lecturas_nova.json`. No hace falta
partir nada.

---

## La app: qué cambia

Hoy la sección «Misa» muestra lecturas. Ha de mostrar **la misa**: el
formulario de arriba abajo, con los propios en su sitio y las lecturas dentro.

* **La lengua**, en Ajustes, junto a Clementina y Nova: *castellano* y
  *bilingüe* (latín y castellano enfrentados, que es como está maquetado el
  leccionario impreso del proyecto).
* **El ordinario**, plegable, intercalado donde va: no se lee cada día, pero
  cuando se busca se busca ahí. Y como viene numerado y alineado en las dos
  lenguas, el bilingüe se puede dar rúbrica a rúbrica.

Lo que queda a elegir, que es la otra mitad de lo pedido. Unas ya existen y
otras son nuevas:

| se elige | de dónde | estado |
|---|---|---|
| la celebración del día, cuando concurren | calendario, ya resuelto por precedencia | **existe** |
| el formulario (ciclo A/B/C, o varios propios) | `indice.json` | **existe** |
| lecturas de la feria o del santo, en las memorias | ajuste `memorias` | **existe** |
| **misa vespertina de la vigilia**, de la aurora, del día | Misal latino y misalitos (la familia 2021 las imprime aparte) | nuevo |
| **el prefacio**: el que marca el día, y los que el Misal permite | `prefacios.json`: los 67 del Ordinario en castellano, los propios cosechados, todos en latín | nuevo |
| **la plegaria eucarística**: I-IV con sus partes propias y sus embolismos; en latín además las de la reconciliación y de diversas necesidades | `ordinario.json` | nuevo |
| **el saludo inicial** (tres, más el del obispo), **la invitación al acto penitencial** (cuatro) y **su fórmula** (I, II, III) | Ordinario, rúbricas 2 y 4 | nuevo |
| **el símbolo**: niceno-constantinopolitano o de los apóstoles | Ordinario, rúbrica 19 | nuevo |
| **el *Misterio de la fe*** (tres), la invitación al padrenuestro y a la paz, y la **despedida** (cinco) | Ordinario | nuevo |
| **misas por diversas necesidades, votivas, rituales y de difuntos** | Misal latino completo; castellano, lo cosechado | nuevo |
| la bendición solemne y la oración sobre el pueblo | Misal latino; misalitos en Cuaresma | nuevo |

El `Gloria` y el `Credo` no se eligen: los dice el día, y el misalito los
imprime («Se dice Gloria», «Se dice Credo»), así que entran como dos banderas
del formulario y la app los pone o los calla sin preguntar.

---

## Control de calidad

Un informe por fase, en `Missale/datos/`, con la misma regla que el resto del
proyecto: **lo que no se pudo resolver se escribe, no se calla, y la app lo
dice en vez de disimularlo**.

* `latino_qa.txt` — formularios del Misal con piezas incompletas; prefacios
  propios dentro de formularios; lo que el parseo no supo clasificar.
* `ordinario_qa.txt` — el cotejo de las 146 rúbricas entre las dos lenguas:
  cuáles cuadran, cuáles no y por qué; la tabla de correspondencia de los 67
  prefacios castellanos con los 50 latinos, con los diecisiete sin pareja
  nombrados uno a uno; y las alternativas detectadas en cada rúbrica, contadas,
  para que se vea si falta alguna.
* `extraer_qa.txt` — **hecho**. Días no hallados: **0 de 3 044**. Además: las
  dos publicaciones con sus ficheros; las 31 formas en que la fuente escribe
  mal un rótulo («ORACIÓN COLETA», «ACLAMACIÓN ATES DEL EVANGELIO»,
  «SALMORESPONSORIA», «ORACIÓN SOBRE EL PUELO»), una por una, con las veces
  que aparece; los pies de página que se contradicen y cómo se resolvió cada
  uno; los 155 formularios sin lecturas, nombrados (son los que las remiten a
  otro sitio, no un fallo del parseo); y lo que el día **deja elegir**, que no
  hay que inventar porque el misalito lo imprime: los nueve rótulos de misa
  propia de un mismo día (la vespertina de la vigilia, la de Noche Buena, la
  de la aurora, la del día, las tres de los Difuntos) y las 116 misas votivas
  distintas que las ferias permiten, con sus 531 apariciones.
* `piezas_qa.txt` — **hecho**. El riesgo 3 medido y puesto primero; lo que la
  fuente nombra al lado de la cabecera y que la fase 3 repartía en tres
  campos; el cotejo de las 2 642 citas contra el índice del leccionario, con
  las cinco que no cuadran ni por el capítulo nombradas; las reparaciones con
  su prueba (7 233 palabras partidas por el renglón, los salmos partidos con
  letra, las erratas); las piezas por número de testigos, las 532 con
  variantes, los empates y las de un solo testigo; los 108 textos atribuidos
  con una excepción, con el día de cada una; los 356 textos de los comunes
  con el reparto medido; los 28 prefacios propios cosechados y
  los que ningún día cita; las oraciones sobre el pueblo; y las 48
  celebraciones del propio de México que el calendario del proyecto no trae.
* `resolver_qa.txt` — el informe que importa: por cada uno de los 1 077
  formularios, si tiene castellano, por qué camino se emparejó (fecha, cita, o
  los dos), cuántos testigos, y, si no lo tiene, por qué. Más el cotejo de
  citas entre el leccionario latino y el misalito, que es la prueba de que el
  emparejamiento no es una coincidencia de calendario.

---

## Riesgos, y lo que de verdad puede salir mal

1. ~~**El calendario de 2018 a 2023.**~~ **Cerrado por la fase 0.** Sale
   bien: Pascua, Ceniza, ciclo dominical y ciclo ferial de 2018 a 2023 cuadran
   con las fechas conocidas, no hay un solo día sin celebración en 2018-2020,
   y los tres traslados por concurrencia de esos seis años son los que de
   verdad ocurrieron. El riesgo era que no saliera; salió.

   Tiene una consecuencia que conviene saber: `data/calendario_completo.json`
   va ahora de 2018 a 2060 en vez de 2024 a 2060, de modo que la próxima
   pasada de `src/15_app_data.py` llevará esos seis años también a la app.
   Para volver atrás basta `python src/18_santoral.py` sin el flag.
2. ~~**Tres familias de maqueta, no una.**~~ **Cerrado por la fase 3, y no era
   eso.** No son tres familias por años: son dos publicaciones, *La Santa
   Misa* (97 ficheros) y *Palabra Viva* (3). El trabajo gordo estuvo en otro
   sitio, y en dos cosas que una muestra de tres meses no podía mostrar:

   - **ninguna de las dos anclas basta sola.** El pie nombra el día en los
     cien ficheros, pero una página puede llevar el final de un formulario y
     el principio del siguiente —nombra el día que *empieza* en ella—, y en
     trece páginas la fuente se contradice a sí misma: unas veces estropea la
     palabra («miécoles», «viérnes», «marte», «sábados») y otras el número
     (julio de 2023, dos veces, con el día de la semana bueno). La cabecera
     del formulario sí es de fiar: su día de la semana cuadra con el
     calendario en las 3 031 veces que aparece, sin una excepción. Así que se
     parte por la cabecera y el pie queda para cotejar, y lo que se
     contradice lo decide la secuencia —las páginas van en orden y el día no
     retrocede—, con cada decisión escrita en el informe;
   - **dónde acaba un formulario no lo dice la maqueta, lo dice el Misal.** La
     oración después de la comunión es la última pieza propia, y tras ella
     sólo caben la oración sobre el pueblo y las rúbricas. Hace falta saberlo
     porque el misalito imprime la reseña y las moniciones del día siguiente
     *antes* de la cabecera de ese día: sin esa regla cada formulario se
     tragaba el aparato editorial del que viene —32 488 párrafos—, y las
     moniciones rotulan sus párrafos con el nombre de la pieza que comentan
     («EVANGELIO: [Mc 2, 23—3, 6] En franca oposición…»), que es como se
     cuelan 650 evangelios que no existen.
3. ~~**Las lecturas propias de las memorias libres.**~~ **Medido por la fase
   4, y es la mitad de malo de lo que parecía.** De las 194 celebraciones del
   santoral con formulario propio en el leccionario, con 443 lecturas propias
   entre todas:

   | | lecturas | |
   |---|---|---|
   | impresas en un día del propio santo | 83 | 19 % |
   | impresas en otro día del corpus, y de ahí las recupera el corpus por cita | 171 | 39 % |
   | no impresas ni una vez en los cien misalitos | 189 | 43 % |

   El agujero existe, y está donde se esperaba: en las memorias (69 de 145) y
   en las memorias libres (100 de 196); las solemnidades y las fiestas lo
   tienen casi todo. Pero **sólo 39 celebraciones se quedan sin ni una**
   lectura propia, y están nombradas una por una en `piezas_qa.txt`. El
   corpus por cita era la mitigación prevista y funciona: recupera 171.

   Para esas 39 el castellano saldrá del común —la fase 4 cosechó 470 textos
   de los comunes— o del latín marcado, que es lo que decidiste en la
   pregunta 6.
4. **Los dos juegos de prefacios.** 67 castellanos y 50 latinos, con la
   numeración divergente que está en la tabla de arriba. Si la correspondencia
   se hiciera por número —«Prefacio III de Adviento» con el tercero del juego
   latino, que no existe— saldrían textos cruzados, y cruzados de una manera
   difícil de notar, porque los dos serían prefacios de Adviento y los dos
   sonarían bien. Por eso va en tabla explícita y por eso el informe la imprime
   entera: es el error más fácil de cometer aquí y el más difícil de ver.
5. **Las siglas de los libros.** La Clementina numera `1-4 Regum` lo que el
   castellano llama 1-2 Samuel y 1-2 Reyes; `Io`/`Jo` es Juan y 1 Jn a la vez
   según el contexto. Hace falta una tabla de puente, y ya existe media en
   `Siglas.docx` y en `data/books.json`.
6. **Los derechos.** La traducción es la litúrgica aprobada para México, y es
   obra protegida, igual que la de las horas que el proyecto ya publica en
   GitHub Pages. Dejar fuera la parte de autoría del editor —moniciones,
   reflexión, oración de los fieles— reduce la cuestión a los textos
   litúrgicos, pero no la elimina. Es decisión tuya, y conviene tomarla antes
   de la fase 6, que es la que publica.
7. **Los 364 MB de esta carpeta, y `publicar.ps1`.** *Resuelto, y con una
   línea más: la fase 3 escribe 25 MB de días en bruto en
   `Missale/datos/misalitos/`, que también quedan fuera del repositorio. Son
   doce veces lo que el Misal latino y el Ordinario juntos —que sí entran,
   porque son el libro ya estructurado— y se rehacen con una orden; lo que de
   ellos hace falta para cotejar está en `extraer_qa.txt`, que entra. Si los
   quieres dentro, se borra la línea de `.gitignore`.* `Missale/` está hoy sin
   versionar, y `publicar.ps1` hace `git add -A`: la próxima vez que publiques,
   los cien misalitos, el Misal latino y el Ordinario entran al repositorio y se quedan
   dentro para siempre. La convención del proyecto ya resuelve esto —
   `.gitignore` deja fuera `Breviarium/*.pdf` porque de ellos sólo hace falta
   lo que generan—, y aquí pide dos líneas:

   ```
   Missale/Misalitos/
   Missale/*.pdf
   ```

   Con los tres PDF de rúbricas se decidió lo contrario, versionarlos, porque
   son la fuente del santoral y conviene cotejar. Aquí el cotejo lo hacen los
   informes de calidad, así que la decisión parece clara, pero es tuya.

---

## Decisiones que hacen falta antes de empezar

1. **¿Un libro o dos?** La misa castellana como tercera «fuente» de la sección
   Misa (recomendado: la app ya tiene el conmutador y las claves son las
   mismas), o una cuarta tarjeta en la portada, al lado del leccionario y las
   horas.
   -RESPUESTA: la primera opción.
2. **¿Bilingüe cómo?** Latín y castellano en columnas enfrentadas, o
   intercalados por párrafo, o un conmutador por pieza.
   -RESPUESTA:Quiero que haya la opción de elegir, si en español solo, si en latín solo, o ambas al mismo tiempo. No sé cómo se vería mejor en el caso de que fueran ambos al mismo tiempo. Decide tú.
3. **¿El ordinario entero, o sólo lo que cambia?** Entero cabe —son 127
   páginas, y ahora están en traducción oficial— y es lo que hace que esto sea
   un misalito; abulta la vista del día. Lo razonable: entero, plegado, abierto
   por donde el día lo necesita. 
   -RESPUESTA: Decide lo más práctico para seguir la Misa de un día normal.
4. **¿Cuántas alternativas se eligen, y cuántas se dan por supuestas?** El
   Ordinario abre tres saludos, cuatro invitaciones penitenciales con tres
   fórmulas, dos símbolos, tres *Misterio de la fe* y cinco despedidas. Todas
   se pueden ofrecer, o se puede ofrecer la primera y guardar las demás detrás
   de un «O bien». Para quien reza, lo segundo; para quien prepara una misa, lo
   primero. 
   -Respuesta: lo segundo.
5. **La parte editorial.** Confirmar que las moniciones, la reflexión y la
   oración de los fieles quedan fuera. (Si las quieres dentro, van en otro
   fichero y marcadas, nunca mezcladas con el texto litúrgico.)
   -Respuesta: las quiero fuera. Solo agrega la breve reseña histórica de la celebración o santo si es que viene.
6. **El castellano que falte.** Para los 171 formularios que ninguna fecha
   alcanza —votivas, rituales, difuntos—: mostrar el latín con el aviso
   (recomendado), u ocultarlos de la vista castellana.
   -Respuesta: muestra solo la opción en latín, y la opción castellana que diga "no disponible"
