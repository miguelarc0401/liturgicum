# El *Missale Romanum cum lectionibus* de 1977

Cuatro tomos, 7 793 páginas, el leccionario entero en latín dentro del Misal:

| tomo | qué trae | páginas |
|---|---|---|
| I | Adviento, Navidad, tiempo ordinario antes de Cuaresma | 1 985 |
| II | Cuaresma y Pascua | 1 936 |
| III | tiempo ordinario, semanas VI-XXI | 2 036 |
| IV | tiempo ordinario, semanas XXII-XXXIV | 1 836 |

Cada tomo lleva, además de su parte del temporal, **el santoral y los comunes
enteros**, para que sirva solo. Eso significa que lo que no es del tiempo
aparece hasta cuatro veces, y hay que deduplicarlo: de 4 575 perícopas
localizadas quedan **1 618 distintas**, más **1 296 salmos responsoriales**.

---

## 1. La capa de texto no se puede publicar

Los cuatro PDF llevan capa de texto y no hace falta pasarlos otra vez por OCR
para *leerlos*. Pero esa capa **es un OCR malo de una página buena**, y eso
cambia para qué sirven.

La página impresa está acentuada entera y limpia. La capa de texto no:

| lo que hay en la página | lo que sale en la capa de texto |
|---|---|
| `Ad te levávi ánimam meam` | `Ad te levavi animam meam` |
| `Da, quǽsumus, omnípotens Deus` | `Da, qmésumus, omnipotens Deus` |
| `eius déxteræ sociáti … cæléste` | `eius déxterre sodati … creléste` |
| `in lúmine Dómini` | `in lamine Domini` |
| `quam cum credídimus` | `quam curo credidimus` |
| `inimíci mei` | `inimki mei` |

No es impresión: está contado sobre los 9,7 MB de texto de los cuatro tomos.

| carácter | veces en la capa de texto |
|---|---|
| `é` | 97 261 |
| `á` | 15 |
| `í` | 7 |
| `ó` | 5 |
| `ú` | 2 |
| `æ` | 7 |
| `œ` | 8 |

El acento agudo **sólo sobrevive sobre la `e`**. Sobre las demás vocales se
pierde, y en el caso de la `o` se convierte en el dígito `6` —12 100 veces
dentro de palabra: `p6pulum`, `Babyl6nis`, `generati6nis`—. La `æ` se lee casi
siempre como `re` (9 481 `rre`: `prophétre`, `srecula`, `creléste`), y la `í`
como `ì` (4 222 veces). A eso se suma el ruido suelto que ninguna regla
arregla: `cum`→`curo`, `sociáti`→`sodati`, `lúmine`→`lamine`,
`Matthan`→`Mattban`, `Eléazar`→`Ele:lzar`.

Se recuperan bien sólo dos cosas: el guion blando de fin de renglón (19 564) y
las comillas angulares (9 847 `«` frente a 11 070 `»` —ni eso cuadra—).

**Conclusión: de estos PDF no puede salir ni una letra que se publique.** Lo
que sí puede salir de ellos es la *decisión*: qué texto es, qué versículos se
leen, y qué pone el libro donde ningún corpus llega.

---

## 2. Qué texto latino es éste

Ésta es la pregunta que el cotejo sí contesta, y la contesta limpiamente.

El método: `plano()` deshace la ortografía —tildes, `j/i`, `u/v`, `æ/œ`—, así
que una diferencia que sobrevive a `plano` es **diferencia de palabra**, no de
grafía. Se buscan los puntos donde la Clementina y la Nova Vulgata difieren
**entre sí** en una palabra entera, y se mira cuál de las dos lleva el libro
de 1977. En esos puntos las dos candidatas no se parecen, así que el ruido del
OCR no puede decidir mal.

**5 484 puntos de divergencia, sin repeticiones:**

| | puntos | sigue la Nova | sigue la Clementina | indeciso | ninguna |
|---|---|---|---|---|---|
| Nuevo Testamento | 2 873 | **70,6 %** | 5,2 % | 22,8 % | 1,4 % |
| Antiguo Testamento | 2 611 | 1,9 % | **82,5 %** | 13,7 % | 2,0 % |

Y el corte es por libro, no una media que esconda mezcla:

| libro | puntos | Nova | Clementina |
|---|---|---|---|
| Ad Hebræos | 164 | 83 % | 2 % |
| Apocalypsis | 152 | 70 % | 4 % |
| I Ad Corinthios | 164 | 78 % | 0 % |
| Actus Apostolorum | 292 | 77 % | 4 % |
| Ad Romanos | 203 | 70 % | 5 % |
| Matthæus | 212 | 69 % | 4 % |
| Marcus | 322 | 65 % | 3 % |
| Lucas | 323 | 63 % | 7 % |
| Ioannes | 301 | 58 % | 12 % |
| II Machabæorum | 98 | 0 % | 95 % |
| Isaias | 453 | 1 % | 87 % |
| Ecclesiasticus | 142 | 1 % | 85 % |
| Exodus | 114 | 2 % | 82 % |
| Genesis | 332 | 3 % | 79 % |
| Ezechiel | 119 | 3 % | 76 % |

**Los salmos** —800 distintos, cotejados renglón a renglón contra el salmo
entero de cada corpus, porque el libro escoge estrofas sueltas— van con la
Nova: 510 a 22, con 268 empates.

### Lo que esto quiere decir

El Misal de 1977 **no es un tercer texto caprichoso: es el estado en que
estaba la revisión de la Vulgata en 1977**, y por eso es mixto.

* La Nova Vulgata del **Nuevo Testamento** se publicó en 1971, antes que este
  Misal, y el Misal ya la usa.
* El **salterio** nuevo —el de la *Liturgia Horarum* de 1971, que es el que
  pasó a la Nova Vulgata— también estaba hecho, y el Misal lo usa, pero
  **numerando a la griega**: lo que el libro llama Ps 121 es el 122 de la Nova.
* El **Antiguo Testamento** de la Nova Vulgata no se completó hasta 1979, dos
  años después. Para el Antiguo Testamento el Misal sigue usando la
  **Clementina**.

### Comprobado a ojo, no sólo por el OCR

Toda la conclusión descansa sobre una capa de texto estropeada, así que
conviene verla en la página impresa. Tomo I, página 232, Núm 24, 2-7. 15-17a:

| el libro impreso | Clementina | Nova Vulgata |
|---|---|---|
| cuius **obturátus** est óculus | obturatus | apertus |
| ut valles **nemorósæ** | nemorosæ | dilatantur |
| ut tabernácula, **quæ fixit Dóminus** | tabernacula quæ fixit | aloe quam plantavit |
| de **sítula** eius … in **aquas multas** | situla … aquas multas | situlis … aquis multis |
| **Tollétur** propter Agag … **auferétur** regnum | Tolletur … auferetur | Extolletur … elevabitur |
| percútiet **duces** Moab, **vastabítque** omnes fílios | duces … vastabitque | tempora … et verticem |

Seis de seis, la Clementina. Y en Rom 13, 11-14 (tomo I, p. 170), seis de seis
la Nova: `iam vos de somno súrgere`, `nobis salus`, `indúite`,
`in concupiscéntiis`.

---

## 3. Lo que este libro da y no da ningún corpus

Aquí está el valor que no se puede sacar ni de la Clementina ni de la Nova,
porque no es texto bíblico sino **leccionario**:

* **El íncipit litúrgico.** 1 098 `In illo témpore`, 622 `In diébus illis`,
  1 493 `Fratres`, 303 `Caríssimi`. Y no es sólo un rótulo pegado delante: en
  Núm 24 el libro escribe `In diébus illis: Bálaam élevans óculos`, donde la
  Clementina dice `et elevans oculos` —la perícopa sustituye el pronombre por
  el sujeto para que se entienda suelta—.
* **La selección exacta de versículos**, con sus medias líneas (`16 b-17`,
  `8 abcd`), que es lo que el corpus no sabe.
* **El salmo responsorial entero**: la respuesta (`℟. Sémitas tuas, Dómine,
  édoce me.`), de qué versículo sale (`℟.: 4 b`), y el reparto en estrofas.
* **El título temático** en cursiva sobre cada lectura (`Orietur stella ex
  Iacob.`, `Congregat Dominus omnes nationes in pacem æternam Regni Dei.`).
* **La acentuación** de toda la perícopa —que es justo lo que al proyecto le
  costó una fase entera—, aunque el OCR sólo deje leer la de la `e`.

---

## 4. Cuánto del leccionario del proyecto alcanza

De las 4 107 ranuras de lectura y evangelio de `data/index_master.json`:

| | ranuras | |
|---|---|---|
| cita idéntica en el Misal de 1977 | 3 328 | 81,0 % |
| mismo libro y mismo versículo inicial | 433 | 10,5 % |
| sin correspondencia | 344 | 8,4 % |

**91,5 % enganchado por la cita.** Lo que falta se explica: este Misal sigue el
*Ordo lectionum Missæ* de 1969, y el leccionario mexicano del proyecto sigue
el de 1981, que cambió perícopas; y parte de lo que falta son cánticos
(1 S 2, Is 12, Jdt 13) que el libro imprime como salmo responsorial y no como
lectura, de modo que los recupera el otro parseo.

---

## 5. El residuo: 90 puntos que no son de ninguna de las dos

**90 puntos** en los que el libro no sigue ni a la Clementina ni a la Nova.
Mirados en la página impresa —no en el OCR— resultan ser dos cosas, y ninguna
de las dos es ruido:

**Lectura mezclada.** Col 3, 12 (tomo II, p. 1437) imprime
`víscera misericórdiæ, benignitátem, humilitátem, mansuetúdinem, patiéntiam`:
toma `mansuetúdinem` de la Nova —la Clementina dice `modestiam`— y
`patiéntiam` de la Clementina —la Nova dice `longanimitatem`—. Una palabra de
cada una en la misma frase.

**Corte de perícopa.** Rom 5, 1 empieza `Fratres: Iustificáti ex fide, pacem
habémus`, sin el `ergo` de la Clementina ni el `igitur` de la Nova: la
conjunción se cae porque la lectura arranca ahí y no puede empezar por «así
pues». Es adaptación del leccionario, no variante de texto.

Están listados en `datos/cotejo_1977_residuo.csv`, con tomo y página para ir
directo a comprobarlos.

El cotejo entero —5 484 puntos, con qué dice cada corpus y cuál sigue el
libro— está en `datos/cotejo_1977_divergencias.csv`.

---

## 6. Lo que esto significa para la app

El encargo era «usar esta traducción en lugar de la Nova Vulgata». Medido, lo
que sale es distinto de eso:

* En el **Nuevo Testamento y en los salmos**, el texto que la app ya sirve
  —la Nova Vulgata— **ya es, en lo sustancial, el de este Misal**. Cambiarlo
  no cambiaría casi nada.
* En el **Antiguo Testamento**, el Misal sigue la **Clementina**, que el
  proyecto también tiene ya, limpia y completa. Ahí el cambio sí se nota, y
  consiste en elegir el corpus que ya está, no en traer texto nuevo.
* Lo que de verdad falta en la app y sólo este libro da son los **íncipits,
  las respuestas de los salmos, los títulos temáticos y la selección fina de
  versículos**.

De modo que el camino no es volcar el OCR, sino usar el libro como **árbitro**:
que decida qué corpus y qué versículos, y que las letras salgan de los corpus
limpios que el proyecto ya tiene. Así no se publica ni una letra de OCR, y el
residuo queda señalado en vez de disimulado.
