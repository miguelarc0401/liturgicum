# Vision — Lectionarium Latinum

Proyecto: construir un **leccionario completo en latín (Vulgata Clementina)** siguiendo la organización litúrgica del *Leccionario Koinonía*.

Fecha del documento: 2026-09-25

---

## 1. Objetivo

Dos entregables encadenados:

| # | Entregable | Descripción |
|---|------------|-------------|
| **A** | **Índice maestro de citas** | Una tabla/base de datos con *una fila por lectura*: celebración → ciclo/año → tipo de lectura (1ª lectura, salmo, 2ª lectura, aleluya, evangelio…) → **cita bíblica normalizada** (sólo la cita, no el texto). |
| **B** | **Leccionario latino** | El mismo esqueleto, pero con el **texto latino** de la Vulgata resuelto e insertado para cada cita. |

Alcance de leccionarios (según lo pedido):

- **Leccionario I / II / III** → Domingos y fiestas, ciclos A, B, C
- **Leccionario IV** → Ferias del Tiempo Ordinario, Año I (impar) y Año II (par)
- **Leccionario V** → Propio y Común de los Santos
- **Leccionario VI** → Misas por diversas necesidades y votivas
- **Leccionario VII** → Ferias de Adviento, Navidad, Cuaresma y Pascua
- **Leccionario VIII** → Misas rituales y de difuntos
- **Leccionario IX** → Misas con niños

Los cuatro últimos se añadieron después (§12); el alcance inicial eran los
cinco primeros.

---

## 2. Verificación técnica ya realizada

Todo lo de esta sección está **comprobado hoy**, no supuesto.

### 2.1 Estructura del sitio web

El sitio usa *framesets* antiguos. La cadena real es:

```
Index.html                      (frameset)
 └─ menu0.html                  → enlaces a Libro_01.html … Libro_09.html
     └─ Libro_01.html           (frameset)
         ├─ menu1.html          → carga menu/menu1.js (menú DHTML)
         └─ texto/1000INDICE.html   ← ÍNDICE REAL con todos los enlaces
             └─ texto/1001AAVD01.html   ← PÁGINA DE LECTURAS
```

Índices confirmados por leccionario:

| Leccionario | Frameset | Página índice |
|---|---|---|
| I (Dom. ciclo A) | `Libro_01.html` | `texto/1000INDICE.html` |
| II (Dom. ciclo B) | `Libro_02.html` | `texto/2000indice.html` |
| III (Dom. ciclo C) | `Libro_03.html` | `texto/3000indice.html` |
| IV (Ferias T.O.) | `Libro_04.html` | `texto/4000indice.html` |
| VII (Ferias tiempos fuertes) | `Libro_07.html` | `texto/7000indice.html` |

### 2.2 Nomenclatura de archivos (predecible)

`texto/NNNN<CÓDIGO>.html` — el primer dígito es el leccionario.

```
1001AAVD01   Lecc. I  · A · AV = Adviento  · D01 = Domingo 1
1019AFDORA   Lecc. I  · A · Fiesta · DOmingo de RAmos
4009ITOX02   Lecc. IV · I = año Impar · TO · X = miércoles · semana 02
4289PTOL15   Lecc. IV · P = año Par    · TO · L = lunes     · semana 15
7001TAVL01   Lecc. VII · AV = Adviento · L = lunes · semana 01
```

Días: **L**unes, **M**artes, **X** miércoles, **J**ueves, **V**iernes, **S**ábado.
Tiempos: **AV** Adviento, **TN** Navidad, **CU** Cuaresma, **PA**/**TFP** Pascua, **TO** Ordinario.

### 2.3 Estructura interna de una página de lecturas — el hallazgo clave

El HTML está marcado con clases CSS **perfectamente regulares**, así que la extracción es determinista (no hace falta heurística de texto ni IA):

| Clase CSS | Contenido |
|---|---|
| `p.Santo` | Nombre de la celebración — *"Domingo 1º de Adviento"* |
| `p.tiempo` | Ciclo o año — *"Ciclo A"*, *"Años impares"* |
| `p.centrorojo` | Cabecera de sección — `PRIMERA LECTURA`, `SEGUNDA LECTURA`, `EVANGELIO` |
| `p.resumen` | Frase-resumen de la lectura |
| **`p.cita`** | **La cita** — *"Lectura del libro de Isaías 2, 1-5"* ← **esto es lo que queremos** |
| `p.cita` (variante) | Salmo — *"**Salmo responsorial**: Salmo 121, 1-2. 4-5. 6-7. 8-9 (R.: Cf.1)"* |
| `p.aleluya` | Aleluya + su cita — *"Aleluya Sal 84,8"* |
| `p.versosang` / `p.salmo` / `p.pnormal` | Cuerpo del texto (lo ignoramos) |
| `p.palabra` | *"Palabra de Dios." / "Palabra del Señor."* — marca fin de lectura |
| `a name="LE1".."LE4"` | Anclas que numeran las lecturas |

Prueba real (Domingo I de Adviento, ciclo A → `1001AAVD01.html`):

```
Santo      | Domingo 1º de Adviento
tiempo     | Ciclo A
centrorojo | PRIMERA LECTURA
cita       | Lectura del libro de Isaías  2, 1-5
cita       | Salmo responsorial: Salmo 121, 1-2. 4-5. 6-7. 8-9 (R.: Cf.1)
centrorojo | SEGUNDA LECTURA
cita       | Lectura de la carta del apóstol San Pablo a los Romanos 13, 11-14a
aleluya    | Aleluya Sal 84,8
centrorojo | EVANGELIO
cita       | Lectura del santo Evangelio según San Mateo 24, 37-44
```

Y una feria (Lecc. IV, `4009ITOX02.html`) sale igual de limpia:

```
Santo      | Miércoles de la 2ª semana de Tiempo Ordinario
tiempo     | Años impares
cita       | Lectura de la carta a los Hebreos 7, 1-3. 15-17
cita       | Salmo responsorial: Salmo 109, 1. 2. 3. 4 (R.: 4bc)
aleluya    | Aleluya Cf. Mt 4, 23
cita       | Lectura del santo evangelio según san Marcos 3, 1-6
```

**Conclusión: la Fase A (índice de citas) es un problema resuelto en cuanto tengamos los HTML.**

### 2.4 `vulgate.pdf` — también totalmente parseable

- 1522 páginas · *Biblia Sacra juxta Vulgatam Clementinam*, ed. Michael Tweedale (proyecto VulSearch).
- Marcadores PDF con **73 libros**, y sus nombres coinciden *exactamente* con la columna "Nombre del libro en la Vulgata" de tu `Siglas.docx`.
- **Firma tipográfica que permite parsear con precisión quirúrgica:**

| Tamaño | Fuente | Significado |
|---|---|---|
| 24.2 pt | URWPalladioL-Roma | **número de capítulo** |
| ~6.0 pt | URWPalladioL-Roma | **número de versículo** (volado) |
| 10 pt | URWPalladioL-Roma | texto bíblico |
| 10 pt | TeXPalladioL-**SC** (versalitas) | encabezado corrido (nombre del libro) — descartar |

**Prototipo ya ejecutado** sobre Isaías (pp. 839–936): detectó **66 capítulos y 1288 versículos**, con recuentos correctos (Is 1 = 31 vv., Is 2 = 22, Is 4 = 6, Is 12 = 6) y devolvió:

> **Isaias 2, 1-5** — *"Verbum quod vidit Isaias, filius Amos, super Juda et Jerusalem… Domus Jacob, venite, et ambulemus in lumine Domini."*

que corresponde exactamente a la primera lectura del Domingo I de Adviento A. **Prueba de concepto superada.**

Normalizaciones necesarias detectadas: ligaduras `ﬁ`/`ﬂ`, diéresis descompuesta (`Isra¨el`), espaciado francés antes de `: ; ? !`, y decisión sobre conservar o no `æ`/`œ`.

### 2.5 `Siglas.docx` — puente completo

Tabla de 3 columnas con **73 filas**: `Abreviatura | Nombre en los leccionarios | Nombre en la Vulgata`. Resuelve por sí sola los casos trampa:

- `1 y 2 S` → **Regum I / Regum II**
- `1 y 2 R` → **Regum III / Regum IV** ← desplazamiento clásico
- `1 y 2 Cro` → Paralipomenon I / II · `Hch` → Actus Apostolorum · `Ap` → Apocalypsis
- `Ne` → Nehemiæ · `Eclo` → Ecclesiasticus · `Ecl/Qo` → Ecclesiastes

### 2.6 Numeración de los Salmos — buena noticia

El leccionario español usa numeración **griega/Vulgata**, no hebrea. Verificado en 3 casos:

| Cita del leccionario | Texto español | Vulgata |
|---|---|---|
| Sal 121 | *"Qué alegría cuando me dijeron…"* | Ps 121 *Lætatus sum* ✔ |
| Sal 84, 8 | *"Muéstranos, Señor, tu misericordia"* | Ps 84,8 *Ostende nobis* ✔ |
| Sal 109 | *"Tú eres sacerdote eterno…"* | Ps 109 *Dixit Dominus* ✔ |

⇒ Los números de salmo mapean **1:1** contra el PDF. Aun así, la Fase 4 incluirá una verificación automática de los ~200 salmos usados (ver §5.2).

### 2.7 Bloqueo actual: acceso al sitio

⚠️ `servicioskoinonia.org` (91.226.177.137) **no acepta conexiones desde esta máquina ahora mismo**: las dos primeras peticiones funcionaron y a partir de la tercera todo da *timeout* de conexión TCP a los 21 s, tanto por `curl` como por el navegador integrado. Otros dominios (google, archive.org) responden con normalidad ⇒ es **límite de tasa / bloqueo de IP del servidor**, no un problema de red local.

Mitigaciones previstas (§4.1): rastreo lento con pausas, reanudable, caché en disco, y **Wayback Machine como fuente secundaria** (ya funciona; el CDX API devuelve 361 URLs archivadas bajo `/leccionario/texto/`, cobertura parcial: Lecc. I ~72, VII ~128, IV sólo 5).

---

## 3. Arquitectura del pipeline

```
 ┌─ FASE 1 ─────────┐   ┌─ FASE 2 ────────┐   ┌─ FASE 3 ──────────┐
 │ Rastreo del sitio│──▶│ Parseo HTML     │──▶│ Normalización de  │
 │ → cache/*.html   │   │ → readings.json │   │ citas → refs      │
 └──────────────────┘   └─────────────────┘   └─────────┬─────────┘
                                                        │  ENTREGABLE A
                                                        ▼  (índice maestro)
 ┌─ FASE 4 ─────────┐   ┌─ FASE 5 ────────┐   ┌─ FASE 6 ──────────┐
 │ vulgate.pdf      │──▶│ Resolución      │──▶│ Composición       │
 │ → vulgata.json   │   │ ref → texto lat.│   │ → DOCX/PDF/HTML   │
 └──────────────────┘   └─────────────────┘   └───────────────────┘
                                                        ENTREGABLE B
```

Cada fase escribe su salida en disco ⇒ **reanudable, auditable y re-ejecutable** sin repetir las anteriores.

### Estructura de carpetas propuesta

```
Lectionarium/
├─ Vision.md                  (este documento)
├─ vulgate.pdf                (fuente, ya presente)
├─ Siglas.docx                (fuente, ya presente)
├─ src/
│   ├─ 1_crawl.py             rastreo + caché
│   ├─ 2_parse_readings.py    HTML → readings.json
│   ├─ 3_normalize_refs.py    citas → referencias canónicas
│   ├─ 4_build_vulgate.py     PDF → vulgata.json
│   ├─ 5_resolve.py           referencias → texto latino
│   ├─ 6_render.py            salida final
│   └─ lib/books.py           tabla de siglas (de Siglas.docx)
├─ cache/                     HTML crudo descargado (no se vuelve a pedir)
├─ data/
│   ├─ readings.json          crudo parseado
│   ├─ index_master.csv|json  ◀ ENTREGABLE A
│   ├─ vulgata.json           Biblia indexada libro/cap/vers
│   └─ unresolved.csv         casos que exigen decisión humana
└─ out/
    ├─ lectionarium.md / .docx / .pdf   ◀ ENTREGABLE B
```

---

## 4. Fases en detalle

### Fase 1 — Rastreo (`1_crawl.py`)

1. Descargar los 5 índices (`1000INDICE`, `2000indice`, `3000indice`, `4000indice`, `7000indice`).
2. Extraer de cada uno todos los `<a href="NNNN*.html">` junto con su texto visible (el texto del enlace ya da el nombre de la celebración) y las cabeceras `p.centrorojo` que los agrupan por tiempo litúrgico.
3. Descargar cada página de lecturas.

**Política anti-bloqueo** (obligatoria, visto §2.7):

- 1 petición cada 3–5 s, un solo hilo, `User-Agent` identificable.
- Reintentos con retroceso exponencial; si hay ≥5 fallos seguidos, pausa larga y reanudación.
- Caché en `cache/`: nunca se re-descarga lo ya guardado ⇒ el rastreo puede correr en varias sesiones.
- *Fallback* automático a `https://web.archive.org/web/2id_/<url>` cuando el origen falle.
- Guardar el byte-stream tal cual; el sitio es **ISO-8859-1**, se decodifica al parsear.

**Volumen estimado:** ≈ 70 + 70 + 70 + ~290 + ~150 ≈ **650–900 páginas** → 1–1.5 h de rastreo educado. (El número exacto de Lecc. IV se confirma al leer `4000indice.html`; el archivo `4289PTOL15` observado sugiere ~290.)

### Fase 2 — Parseo de lecturas (`2_parse_readings.py`)

Recorrer el `<body>` en orden y construir una máquina de estados sobre las clases CSS de §2.3. Cada `p.cita` abre una lectura; `p.centrorojo` fija el *tipo*; `p.tiempo` fija ciclo/año.

Salida `readings.json`:

```json
{
  "id": "1001AAVD01",
  "lectionary": "I",
  "cycle": "A",
  "season": "Adviento",
  "celebration": "Domingo 1º de Adviento",
  "source_url": "https://servicioskoinonia.org/leccionario/texto/1001AAVD01.html",
  "readings": [
    {"slot": 1, "type": "primera_lectura",
     "raw_cita": "Lectura del libro de Isaías 2, 1-5",
     "summary": "El Señor reúne a todas las naciones en la paz eterna del Reino de Dios"},
    {"slot": 2, "type": "salmo",
     "raw_cita": "Salmo 121, 1-2. 4-5. 6-7. 8-9 (R.: Cf.1)",
     "response": "Vamos alegres a la casa del Señor"},
    {"slot": 3, "type": "segunda_lectura",
     "raw_cita": "Lectura de la carta del apóstol San Pablo a los Romanos 13, 11-14a"},
    {"slot": 4, "type": "aleluya", "raw_cita": "Sal 84, 8"},
    {"slot": 5, "type": "evangelio",
     "raw_cita": "Lectura del santo Evangelio según San Mateo 24, 37-44"}
  ]
}
```

### Fase 3 — Normalización de citas (`3_normalize_refs.py`) → ENTREGABLE A

Convierte `raw_cita` en una referencia canónica y verificable.

1. **Separar libro y cita**: quitar el prefijo (`Lectura del libro de`, `Lectura de la carta del apóstol San Pablo a los`, `Lectura del santo Evangelio según san`, `Salmo responsorial:`…) por normalización (minúsculas, sin tildes) y coincidencia con la columna 2 de `Siglas.docx`, tomando **el nombre más largo que coincida** para evitar ambigüedades (`Juan` vs `1 Juan`).
2. **Mapear** a sigla + nombre Vulgata (columnas 1 y 3 de `Siglas.docx`).
3. **Parsear el rango** con una gramática explícita que cubra: `2, 1-5` · `7, 1-3. 15-17` · `13, 11-14a` · `24, 37-44` · `121, 1-2. 4-5. 6-7. 8-9` · `109, 1. 2. 3. 4` · `Cf. Mt 4, 23` · `7, 10-14; 8, 10` (salto de capítulo) · `Sal 88, 2-3. 4-5. 27 y 29` · `1, 1-4; 2, 1-2`.
4. Emitir una estructura de **segmentos** `[{book, chapter, from_v, to_v, letters}]`.

Salida `index_master.csv` (una fila por lectura) — **esto es exactamente lo que pediste primero**:

| lect | ciclo | tiempo | celebración | orden | tipo | libro (es) | sigla | libro (Vulgata) | cita_cruda | cita_normalizada |
|---|---|---|---|---|---|---|---|---|---|---|
| I | A | Adviento | Domingo 1º de Adviento | 1 | primera lectura | Isaías | Is | Isaias | Lectura del libro de Isaías 2, 1-5 | Is 2,1-5 |
| I | A | Adviento | Domingo 1º de Adviento | 2 | salmo | Salmos | Sal | Psalmi | Salmo 121, 1-2. 4-5… | Ps 121,1-2.4-5.6-7.8-9 |
| I | A | Adviento | Domingo 1º de Adviento | 3 | segunda lectura | Romanos | Rm | Ad Romanos | …a los Romanos 13, 11-14a | Rom 13,11-14a |
| I | A | Adviento | Domingo 1º de Adviento | 4 | aleluya | Salmos | Sal | Psalmi | Aleluya Sal 84,8 | Ps 84,8 |
| I | A | Adviento | Domingo 1º de Adviento | 5 | evangelio | Mateo | Mt | Matthæus | …según San Mateo 24, 37-44 | Mt 24,37-44 |

Se entrega también en JSON y, si lo prefieres, en XLSX.

### Fase 4 — Corpus de la Vulgata (`4_build_vulgate.py`)

Aplicar el parser ya prototipado (§2.4) a las 1522 páginas:

- Recorrer los marcadores del PDF para delimitar cada libro.
- Dentro de cada libro: span de 24.2 pt = nuevo capítulo (v. 1 implícito); span de ~6 pt = nuevo versículo; spans de 10 pt = texto; descartar versalitas y el número de página al pie.
- Normalizar ligaduras y diéresis; conservar los saltos de verso del PDF como metadato (útil para maquetar poesía: Salmos, Isaías, Proverbios).

Salida `vulgata.json`: `{ "Isaias": { "2": { "1": "Verbum quod vidit…", … } } }`

**Control de calidad automático:** comparar el recuento de capítulos y versículos por libro contra una tabla de referencia de la Vulgata Clementina; cualquier desviación se reporta antes de continuar.

### Fase 5 — Resolución (`5_resolve.py`)

Para cada segmento del índice maestro, extraer los versículos del corpus.

- Sufijos `a`/`b`/`c` (`13, 11-14a`): la Vulgata no tiene subdivisiones ⇒ **se toma el versículo completo** y se anota la marca en el aparato (`14a`). Decisión configurable.
- `Cf.` (cita libre): se resuelve igual, marcando `cf.` en el aparato.
- Versículos ausentes ⇒ fila en `unresolved.csv` para revisión manual. Objetivo: **0 sorpresas silenciosas**.

### Fase 6 — Composición (`6_render.py`) → ENTREGABLE B

Genera el leccionario latino con la estructura litúrgica tradicional:

```
DOMINICA I ADVENTUS · Anno A

LECTIO PRIMA
Lectio libri Isaiæ prophetæ                                    Is 2, 1-5
    Verbum quod vidit Isaias, filius Amos, super Juda et Jerusalem…
    Verbum Domini.

PSALMUS RESPONSORIUS                              Ps 121, 1-2. 4-5. 6-7. 8-9
    ℟. Lætatus sum in his quæ dicta sunt mihi…

LECTIO SECUNDA
Lectio Epistolæ beati Pauli apostoli ad Romanos              Rom 13, 11-14a
    …

EVANGELIUM
Lectio sancti Evangelii secundum Matthæum                     Mt 24, 37-44
    …
```

Plantillas de fórmulas latinas (`Lectio libri…`, `Verbum Domini`, `Lectio sancti Evangelii secundum…`) generadas a partir del nombre Vulgata de cada libro, con su declinación correcta (tabla fija de 73 entradas, escrita a mano una sola vez).

Formatos de salida: **Markdown** (siempre, como fuente de verdad) → **DOCX** y **PDF** (maquetado a dos columnas o a una, tipografía litúrgica).

---

## 5. Riesgos y casos difíciles

### 5.1 Riesgos de proceso

| Riesgo | Impacto | Mitigación |
|---|---|---|
| **Bloqueo del sitio** (§2.7) | Alto — bloquea la Fase 1 | Rastreo lento reanudable + caché + Wayback; si persiste, el rastreo puede correr en varios días sin perder trabajo |
| Wayback incompleto para Lecc. IV (5/290) | Medio | Sólo es *fallback*; el origen sigue siendo la fuente principal |
| Páginas con estructura irregular | Medio | El parser marca como "sospechosa" cualquier página sin `p.Santo` o sin evangelio, y se revisa a mano |

### 5.2 Casos litúrgico-textuales que exigen decisión

1. **Clementina vs. Nova Vulgata.** El *Ordo Lectionum Missæ* oficial latino usa la **Nova Vulgata** (1979), no la Clementina. Tú aportaste la Clementina, así que ese es el plan por defecto — pero conviene saberlo: la Nova Vulgata numera los Salmos con doble numeración y difiere en algunos versículos. *(Decisión pendiente, §6.)*
2. **Numeración de Salmos.** Verificada 1:1 en 3 muestras (§2.6). Se añadirá un chequeo automático de los ~200 salmos usados comparando el *incipit* español con el latino.
3. **Versículos de los Salmos.** La Clementina cuenta el título (*"Canticum graduum"*, *"In finem, psalmus David"*) **como parte del versículo 1**; los leccionarios modernos a veces lo omiten ⇒ posible desfase de 1 en algunos salmos. Se detecta con el chequeo anterior.
4. **Cánticos no salmódicos** usados como salmo responsorial (Is 12; Dn 3; 1 Sam 2; Ex 15; Lc 1 *Magnificat* / *Benedictus*). Se resuelven como cualquier otra cita, salvo **Dn 3**, cuyo cántico griego (vv. 52–90) sí está en la Vulgata Clementina — a verificar.
5. **Ester y Daniel** tienen secciones deuterocanónicas con numeración propia en la Clementina (Est 10,4–16,24). Cualquier cita del leccionario a esas partes irá a `unresolved.csv`.
6. **Lecturas alternativas** (*"o bien:"*, formas breves *"forma breve: 1-4. 14-16"*, las 7 lecturas de la Vigilia Pascual). El modelo de datos ya soporta varias lecturas por *slot*; hay que decidir si se incluyen todas o sólo la principal.
7. **Secuencias** (*Victimæ paschali*, *Veni Sancte Spiritus*, *Lauda Sion*, *Stabat Mater*): no son citas bíblicas; se insertan desde una tabla fija de textos latinos.
8. **Pasiones** (Domingo de Ramos, Viernes Santo) — lecturas muy largas con partes dialogadas (✠, C, S). Se extraen como texto continuo salvo que quieras las marcas de personaje.
9. **`1 y 2 R` → `Regum III / IV`** y `1 y 2 S` → `Regum I / II`: la tabla de siglas lo resuelve, pero es la fuente de error más probable ⇒ test unitario dedicado.

---

## 6. Decisiones que necesito de ti

| # | Pregunta | Recomendación |
|---|---|---|
| 1 | ¿**Clementina** (tu PDF) o **Nova Vulgata** (la del leccionario oficial)? | Clementina, como planeado — es lo que aportaste y el parser ya funciona |
	Respuesta: Clementina
| 2 | ¿Bilingüe latín-español o **sólo latín**? | Sólo latín en la salida principal; el español queda en el índice maestro por si lo quieres después |
	-Respuesta: seguimos la recomendación
| 3 | ¿Incluir **lecturas alternativas** y formas breves? | Sí, marcadas como *"Vel:"* — no cuesta más y el leccionario queda completo |
	-Respuesta: Seguimos tú Recomendación
| 4 | ¿Incluir el **versículo del Aleluya** y la **antífona del salmo (℟.)**? | Sí, ambos |
	-Respuesta: Seguimos tu Recomendación
| 5 | Formato final: ¿**Markdown**, **DOCX**, **PDF** maquetado, los tres? | Markdown siempre + DOCX; PDF al final |
	-Respuesta: seguimos tu recomendación
| 6 | ¿Texto latino con ortografía **clásica** (`Isaiæ`, `cæli`, `ejus`) o modernizada (`Isaiae`, `caeli`, `eius`)? | Conservar la del PDF (clásica con `æ`/`œ` y `j`) |
	-Respuesta: Seguimos tu Recomendación
| 7 | ¿Incluir **acentuación litúrgica** (`Léctio`, `Dómini`) para canto? | Es un trabajo aparte y grande; **no** en la v1, se puede añadir después |
	-Respuesta: Agrega acentuación (si no implica muchísimo esfuerzo extra)
| 8 | ¿Añadir también **Leccionario V, VI, VIII, IX** (santos, misas rituales…)? | No en la v1; la arquitectura los admite sin cambios |
	-Respuesta: Seguimos tu propuesta, y mejor después lo agregamos.

### 6.bis Acentuación litúrgica (decisión 7): medido, no estimado a ojo

Pediste añadirla «si no implica muchísimo esfuerzo extra». Lo medí sobre el
corpus real en vez de suponerlo.

La acentuación litúrgica marca el acento tónico de las palabras de 3+ sílabas.
La regla es: **penúltima si es larga, antepenúltima si es breve** — y la
longitud de una penúltima abierta no se deduce de la ortografía, es léxica
(`Dóminus` vs `amícus` se escriben igual de ambiguos).

Cobertura alcanzable, medida sobre las 232 211 apariciones de palabras de 3+
sílabas de la Vulgata:

| Método | Apariciones resueltas |
|---|---|
| Diptongo en la penúltima | 0.9 % |
| Penúltima trabada por 2+ consonantes (posición) | 16.9 % |
| Terminaciones de penúltima larga (`-órum`, `-ávit`, `-tátis`…) | 15.8 % |
| Terminaciones de penúltima breve (`-ibus`, `-inis`, `-ium`, `-itur`…) | 21.6 % |
| **Automático total** | **55.2 %** |
| + 500 formas curadas a mano | 76.5 % |
| + 2000 formas curadas a mano | 86.2 % |

Para un libro litúrgico impreso haría falta ~99.5 %, y eso exige un léxico de
cantidades vocálicas completo (decenas de miles de formas). CLTK trae la lógica
pero **no** los datos, que descarga aparte y sin validar para este uso.

**Conclusión y plan:** sí se hace, pero **como Fase 7, al final y acotada**. La
clave que lo vuelve tratable: no hay que acentuar la Vulgata entera, sólo los
versículos que realmente entran en el leccionario — una fracción pequeña del
texto. Sobre ese subconjunto la lista de formas ambiguas a curar baja muchísimo.
Entregables de esa fase: el texto acentuado, un informe de cobertura y un
`acentos_excepciones.csv` revisable, para que corrijas a mano lo que haga falta
sin tocar código. **No bloquea ni retrasa nada de lo anterior.**

> **Hecho, y mejor de lo que decía esta estimación** (§9). La cuenta de arriba
> daba por supuesto que el acento había que *deducirlo*. No hacía falta: los
> libros litúrgicos lo imprimen, y hay un corpus de Breviario y Misal en latín
> ya acentuado y con esta misma ortografía. Con él, más las cantidades vocálicas
> de Morpheus para el resto, se resuelve el **99,65 %** (Clementina) y el
> **99,50 %** (Nova Vulgata), medido, y con una validación por retención sobre
> el Salterio que da **99,57 %** de coincidencia con el libro impreso.

### 6.ter Registro de decisiones

Todas cerradas: Clementina · sólo latín · con lecturas alternativas · con
aleluya y antífona · Markdown + DOCX (PDF al final) · ortografía clásica del PDF
· **acentuación sí, como Fase 7 acotada** · leccionarios V/VI/VIII/IX más
adelante.

Fuera de alcance por petición tuya: la versión con la **Nova Vulgata**, que será
un proyecto aparte y posterior (ver nota al final del documento). La
arquitectura ya lo admite: sólo cambia la Fase 4 (otro corpus) y la tabla de
numeración de Salmos.

---

## 7. Orden de trabajo propuesto

| Etapa | Contenido | Resultado visible | Estado |
|---|---|---|---|
| **0** | Andamiaje del repo | `src/`, `data/`, `cache/`, `out/` | ✅ hecho |
| **1** | `4_build_vulgate.py` — no depende de la red | `data/vulgata.json` | ✅ **hecho y validado**: 73 libros, 1334 capítulos, **35 811 versículos**, 0 fallos de control de calidad |
| **2** | `1_crawl.py` — los 5 índices reales del sitio | **758 páginas objetivo** | ✅ **754 descargadas**; faltan 4 apéndices de aleluyas (§7.7) |
| **3** | `2_parse_readings.py` + `3_normalize_refs.py` | **`data/index_master.csv`** | ✅ **3347 citas, 3290 normalizadas, 0 fallos** |
| **4** | *Checkpoint contigo*: validas el formato del índice | luz verde | ⏳ **te toca** |
| **5** | Completar el rastreo de IV y VII y re-ejecutar | **ENTREGABLE A completo** | ✅ hecho |
| **6** | `5_resolve.py` + `6_crosscheck.py` + `7_offset_scan.py` | cobertura latina medida y **verificada** | ✅ **100 % resuelto, 0 versículos ausentes** |
| **7** | `8_render.py` con el Domingo I de Adviento A como muestra | `out/muestra_adviento1A.md` | ✅ hecho |
| **8** | Render completo | **`out/lectionarium.md`** | ✅ **3290 lecturas, 21 562 versículos** |
| **8b** | Exportación a DOCX (`9_docx.py`) | `out/lectionarium.docx` | ✅ hecho |
| **8c** | **Un documento por leccionario con índice navegable** (`10_toc.py`) | `out/Leccionario_*.md` / `.docx` | ✅ **hecho** (§7.6) |
| **8d** | PDF (`11_pdf.py`, LibreOffice en consola) | `out/pdf/*.pdf` | ✅ hecho, con enlaces internos y marcadores |
| **8e** | **Un solo leccionario en el orden del año** (`12_calendario.py`) | `out/Leccionario_ano_liturgico_completo.*` | ✅ **hecho** (§7.8) |
| **8f** | **Maquetación de libro en dos tamaños** (`9_docx.py --perfil`) | `out/carta/*` y `out/media/*` + sus PDF | ✅ **hecho** (§7.9) |
| **8g** | Titulillo de la Vulgata colado en el texto | corpus limpio, cadena rehecha | ✅ **corregido** (§7.7 bis) |
| **9** | **Acentuación litúrgica en las dos versiones** (`13_acentos.py`) | texto acentuado + informes + excepciones revisables | ✅ **hecho** (§9): **99,65 %** de las palabras de 3+ sílabas resueltas con fundamento en la Clementina, **99,50 %** en la Nova Vulgata |
| **10** | Apéndices de aleluyas y textos comunes (§7.7) | secciones finales de cada leccionario | ✅ **hecho** (§11): 105 citas, **105 resueltas**, + el índice de textos |
| **11** | **Calendario civil**: qué día litúrgico es cada fecha (`14_calendario_civil.py`) | `data/calendario_civil.json` | ✅ **hecho** (§10.1): 13 415 fechas, 2024-2060, **0 días sin pareja** |
| **12** | **La app para el teléfono** (`15_app_data.py` + `app/`) | PWA instalable, sin conexión | ✅ **hecho** (§10) |

### 7.6 Los cinco leccionarios como documentos independientes, con índice navegable

Pediste poder abrir cada leccionario y saltar con un clic al domingo o la feria
que buscas. El esqueleto para eso no se ha inventado: se ha extraído del propio
sitio.

`10_toc.py` lee las cinco páginas índice que ya estaban en caché y reconstruye
su árbol tal como lo publica Koinonía: tiempos litúrgicos, subgrupos y entradas.
La jerarquía no está en las clases CSS, sino en la **sangría** (`blockquote`,
`ol`): así se sabe que las cuatro misas de Navidad dependen de «Natividad del
Señor» y que «La Sagrada Familia», que viene después, ya no. Sin seguir la
sangría, media Navidad colgaba de la cabecera equivocada.

Resultado: `data/toc.json`, que gobierna **dos cosas a la vez** — el índice del
principio y el orden del cuerpo del documento, de modo que no pueden discrepar.

Lo que se genera ahora (`--separados` en `8_render.py` y `9_docx.py`):

| Documento | Celebraciones | DOCX |
|---|---|---|
| Leccionario I · Domingos, ciclo A | 69 | 170 KB |
| Leccionario II · Domingos, ciclo B | 73 | 180 KB |
| Leccionario III · Domingos, ciclo C | 73 | 187 KB |
| Leccionario IV · Ferias del T.O., años I y II | 408 | 577 KB |
| Leccionario VII · Ferias de Adviento, Navidad, Cuaresma y Pascua | 124 | 204 KB |
| `lectionarium` · los cinco juntos | 747 | 1175 KB |

Cómo se navega, en los tres formatos:

* **DOCX** — el índice usa **marcadores e hipervínculos internos de Word**, no
  un campo `TOC`: funcionan al abrir el documento, sin pulsar F9 ni actualizar
  nada. Además, tiempos litúrgicos, subgrupos y celebraciones llevan estilos de
  título (Heading 1/2/3), así que el **Panel de navegación** de Word muestra el
  leccionario entero como un árbol. Cada celebración tiene un «↑ Índice» para
  volver. Comprobado sobre el XML generado: 752 marcadores, 1506 enlaces,
  **0 enlaces rotos**.
* **Markdown** — anclas HTML explícitas (`<a id="c1001AAVD01_0">`) y enlaces
  `[Domingo I de Adviento](#c1001AAVD01_0)`; funcionan en GitHub, en Obsidian y
  al convertir a HTML con pandoc.
* **PDF** — `11_pdf.py` convierte con LibreOffice en modo consola; la conversión
  conserva los enlaces del índice como enlaces internos del PDF (282 en el
  leccionario I) y los estilos de título como marcadores del navegador.

El índice aprieta en una sola línea los grupos de entradas cortas («*Semana I*:
Lunes · Martes · Miércoles…»), que es lo que hace manejable el índice del
Leccionario IV: 68 semanas en 68 líneas en vez de 408.

### 7.7 Dos huecos encontrados al montar el índice (y qué se hizo)

Cotejar el índice del sitio contra lo ya parseado hizo aparecer dos cosas que
ninguna comprobación anterior podía ver, porque las dos eran **silenciosas**:

1. **Una página perdida entera: `4371PTOV28.html`** (viernes de la 28ª semana
   del T.O., año par). El parser exigía `<p class="cita">` con comillas, y esa
   página, exportada desde Word, escribe `<p class=cita>`. Sin comillas no
   casaba **ni un solo párrafo**, así que la página no daba ningún aviso: salía
   del pipeline como si no existiera. Corregido en `2_parse_readings.py`
   (el atributo se acepta con y sin comillas) y comprobado que es la **única**
   página del sitio afectada. El leccionario IV pasa de 407 a **408** ferias.
2. **Una errata del índice del sitio.** En «LECTURAS PARA DESPUÉS DE LA
   EPIFANÍA», la entrada «7 de enero o bien lunes después del domingo de
   Epifanía» enlaza otra vez `7034TF07EN.html` (la del 7 de enero *antes* de la
   Epifanía) y deja huérfana `7035TFLDEP.html`, que es la del lunes después de
   Epifanía y sí existe. Corregido en `data/toc_overrides.csv`, editable sin
   tocar código.

**Lo que sigue faltando, acotado y a la vista:** los apéndices del sitio que no
son formularios de un día, sino listas (los «Versículos alternativos para el
Aleluya» de cada tiempo, los «Textos comunes para el canto del salmo
responsorial» y el «Índice de textos»). No los descarta ningún error: tienen
otra estructura (`p.encabazul` + lista numerada, sin `p.Santo`), así que el
parser de celebraciones no los reconoce. Son 13 páginas en total, de las cuales
4 ni se descargaron porque su nombre lleva espacios. Cada documento lo declara
al final de su índice, en vez de callarlo. Es la etapa 10 del plan.

### 7.7 bis El encabezado corrido de la Vulgata, metido dentro del versículo

Lo encontraste leyendo, que es como se encuentran estas cosas:

> 32 Venit enim ad vos Joannes in via justitiæ, et non credidistis **Matthæus**
> ei: publicani autem et meretrices crediderunt ei…

`Matthæus` es el **titulillo** que `vulgate.pdf` imprime arriba de cada página.
`4_build_vulgate.py` ya lo descartaba… o eso parecía: la regla era «si *todos*
los fragmentos de la línea van en versalitas, es titulillo». Pero el PDF compone
la cabecera con la inicial en redonda y el resto en versalitas —dos fragmentos,
`M` + `atthæus`—, así que la condición **no se cumplía nunca** y la línea entera
entraba como texto bíblico, justo en el versículo que cruzaba el salto de
página. En 1511 páginas de libros bíblicos había 1521 titulillos: se colaron
todos.

Lo que lo delata sin ambigüedad no es la fuente, sino **dónde cae la línea**:
medido sobre el PDF entero, ninguna línea de texto corrido empieza por encima
del **14.85 %** del alto de la página, y las 1521 cabeceras están todas en el
**10.4 %**. La regla nueva descarta una línea si lleva algún fragmento en
versalitas **y** cae en el 13 % superior.

**Alcance del destrozo y de la reparación**, medido comparando el corpus viejo
con el nuevo versículo a versículo: **1438 versículos corregidos** de 35 811.
Comprobado que los 1438 cambios son exactamente la retirada de un titulillo, ni
uno más. Los casos peores eran los que partían una palabra a caballo de la
página: `quæ man`+`Genesis`+`di possunt` → `quæ mandi possunt`.

En el leccionario: **820 versículos sucios, en 801 lecturas de 518
celebraciones**. Por eso hubo que rehacer la cadena entera desde la fase 4.

Por qué no lo vio ningún control anterior: el control de calidad de la fase 4
cuenta capítulos y versículos, y el recuento salía perfecto —el titulillo no
añade ni quita versículos, se mete *dentro* de uno—; y el cotejo de la fase 5b
compara nombres propios, y `Matthæus` en medio de Mateo no baja ninguna
puntuación. Era un error silencioso de los que este proyecto se toma en serio.
Queda como aviso: **los recuentos cuadrando no son prueba de que el texto esté
limpio.**

### 7.8 Un solo leccionario en el orden del año

Los cinco libros son la organización del *sitio*, no la del año. Lo que pediste
—y es como se lee de verdad— es recorrer el calendario: cada domingo con sus
tres ciclos y, detrás, las ferias de su semana.

    Domingo I de Adviento ....... Ciclo A · Ciclo B · Ciclo C
    Lunes de la 1ª semana ....... Ciclos A, B y C
    ... hasta el sábado
    Domingo II de Adviento ...... Ciclo A · Ciclo B · Ciclo C
    ...
    Lunes de la 1ª semana del T.O. ... Año I · Año II

`12_calendario.py` construye ese espinazo y `data/calendario.json` lo guarda.
Tres cosas lo hacen fiable:

1. **Alinear los tres ciclos.** No se adivina por el nombre del fichero (que
   tiene excepciones: `1022AVIPAS` es `3022AVIPAS` en el ciclo C, no
   `3022CVIPAS`), sino por la **posición en el índice del sitio**: los índices
   de I, II y III llevan las mismas 69 entradas, con el mismo texto y en el
   mismo orden — comprobado entrada por entrada.
2. **Situar las ferias.** El código del fichero es sistemático (`7045TCUL01` =
   Cuaresma, lunes, semana 1). En el leccionario IV el año lo manda la sección
   del índice (AÑO I / AÑO II), no la página: `4249PTOX08` está en la serie del
   año par y su propia página dice «Años impares». El informe lo deja anotado.
3. **No repetir lo que es un solo formulario.** Navidad, Epifanía, el Triduo o
   el Domingo de Pascua son comunes a los tres ciclos: las tres páginas dicen
   «Ciclos A, B y C». Se imprime **una vez**, quedándose con la copia más
   completa. Cuando las tres copias no son idénticas —pasa en 4 días, por
   erratas del sitio: falta la aclamación en una, el salmo empieza en el
   versículo 2 en otra— se toma la más completa y **queda anotado en el
   informe**, no oculto.

Además se descartan 5 bloques que el sitio repite dentro de otra página y que ya
están completos en su propio formulario (el Domingo VII de Pascua aparece
pegado al Domingo VI y a la Ascensión). Uno de ellos, `3029CFASCE`, traía la
aclamación como «Jn 4,18» donde el formulario propio dice «Jn 14,18»: al
quedarnos con el propio, se queda la correcta.

**Cuadre del reparto** (es la comprobación que importa): 747 bloques en los
datos, 5 descartados por duplicar, **742 colocados, 0 sin colocar, 0 colocados
dos veces**, repartidos en **395 días** y 722 formularios.

Cómo queda el índice — una línea por semana, que es lo que lo hace legible:

    TIEMPO DE ADVIENTO
      I semana de Adviento: Domingo I de Adviento · Lunes · Martes · …
      …
    TIEMPO ORDINARIO
      Semana II del Tiempo Ordinario: Domingo II del Tiempo Ordinario · Lunes · …

En el DOCX la navegación tiene cuatro niveles de título (tiempo litúrgico →
semana → día → ciclo/año), así que el Panel de navegación de Word y los
marcadores del PDF muestran el año entero como un árbol. Comprobado: 396
marcadores, 790 enlaces internos, **0 roto**.

Se genera con `--anual`, y conviven los dos formatos: los cinco leccionarios
por separado (§7.6) y este único en orden del año.

### 7.9 La maquetación: dos tamaños, compuestos como libro

Hasta aquí el DOCX era un volcado correcto pero plano: una columna ancha a 11
pt, sin folios, sin cabeceras y sin partición de palabras, que en justificado
abría ríos de blanco. Ahora `9_docx.py` compone el mismo contenido como libro,
en **dos perfiles de página** que se eligen con `--perfil`:

| | carta | media carta |
|---|---|---|
| Página | 21.59 × 27.94 cm | 13.97 × 21.59 cm |
| Caja | dos columnas, 8.6 cm cada una | una columna de 10.8 cm |
| Texto | 10 pt / 1.06 | 10 pt / 1.10 |
| Renglón | ~58 caracteres | ~66 caracteres |

Las dos llevan **márgenes simétricos** (interior más ancho que exterior) y
**folio al corte**: el número de página cae siempre en el borde exterior, con
el titulillo al lado —el leccionario en las páginas pares, el tiempo litúrgico
en las impares— separado por un filete fino. La página que abre cada tiempo va
limpia, sin folio, como en cualquier libro.

Decisiones que no son de adorno:

* **Tres fuentes, cada una por un motivo.** *Constantia* para el texto: sus
  cifras elzevirianas dejan pasar los versículos volados sin hacer ruido.
  *Palatino Linotype* para títulos y rúbricas. Y *Cambria* **solo** para `℟` y
  `✠`: medido sobre los propios ficheros de fuente, son los únicos dos glifos
  que Constantia y Palatino no traen, y sin esto el PDF los sustituía por su
  cuenta con una fuente cualquiera.
* **Partición de palabras con silabeo español.** Es el más cercano al latino, y
  es el que LibreOffice tiene instalado (no hay diccionario italiano ni latino).
  El estilo base va marcado como español y con la revisión ortográfica
  desactivada, para que Word no subraye en rojo todo el latín.
* **Los títulos de tiempo litúrgico van a todo lo ancho de la caja**, no
  encajonados en media columna: cada uno abre con un salto de sección de una
  columna y el cuerpo sigue en dos.
* **El `℟` cierra la estrofa del salmo en el mismo renglón** en vez de gastar
  una línea entera. Con ~790 salmos, eso solo ya son decenas de páginas.
* **El índice lleva número de página real**, no solo el hipervínculo: campos
  `PAGEREF` con puntos guía. LibreOffice los resuelve al exportar el PDF y
  Word al abrir el documento (`w:updateFields`), así que sirve igual en
  pantalla que en papel.

**Lo que cuesta y lo que ahorra**, en páginas:

| Documento | carta (antes: 1 col.) | carta | media carta |
|---|---|---|---|
| Leccionario I · Ciclo A | 130 | **75** | 165 |
| Leccionario II · Ciclo B | 138 | **79** | 172 |
| Leccionario III · Ciclo C | 145 | **82** | 180 |
| Leccionario IV · Ferias del T.O. | 516 | **276** | 629 |
| Leccionario VII · Tiempos fuertes | 163 | **89** | 199 |
| El año litúrgico completo | 1038 | **559** | 1272 |
| `lectionarium` · los cinco juntos | 1093 | **602** | 1346 |

Los catorce documentos salen a `out/carta/` y `out/media/`, y sus PDF a
`out/pdf/carta/` y `out/pdf/media/`. Comprobado sobre los PDF finales: tamaño
de página correcto en los catorce y los enlaces internos del índice intactos
(2306 en el tomo completo en carta).

### 7.5 El problema de fondo: la versificación, y cómo se ha resuelto

Un desfase entre la numeración moderna del leccionario y la de la Clementina
**no da ningún error**: da el texto equivocado en silencio. Era el riesgo real
del proyecto, y por eso se atacó con tres comprobaciones independientes.

**1. Recuento exacto.** Se comparan los versículos que pide la cita con los que
se extrajeron. Es exacta y no necesita datos externos: delata cualquier sitio
donde la Vulgata funda o parta versículos. Resultado actual: **32 descuadres,
los 32 explicados por una regla documentada, 0 sin explicar.**

**2. Cotejo latín–castellano** (`6_crosscheck.py`). Se comparan las raíces de
las palabras del castellano de la propia página con las del latín extraído,
neutralizando las diferencias gráficas constantes (ae/oe→e, j/i, v/u, ph/f,
qu/c, h muda). *El propio verificador se validó antes de usarlo*: en
emparejamientos correctos la coincidencia mediana es **0.14**, y en
emparejamientos al azar **0.024**; el correcto gana al azar en el **94.4 %** de
los casos. Sirve para **ordenar sospechas, no para dictaminar**: en poesía
(salmos) da muchos falsos positivos, comprobado a mano (Sal 26 y Sal 138 marcan
0.0 y son correctos).

**3. Buscador automático de desfases** (`7_offset_scan.py`). Para cada lectura
prueba desplazamientos de −3 a +3 y propone el que mejor casa con el
castellano. Alinear libro por libro a mano no escala; esto sí. **Encontró dos
divergencias reales que no se habrían detectado de otro modo** (Oseas 2 y
Eclesiástico 24).

#### Las 27 reglas de versificación (`data/versification_map.csv`)

Cada una está **verificada contra el castellano de la propia página**, no
supuesta, y el fichero es editable sin tocar código:

| Caso | Divergencia |
|---|---|
| **Ps 115, Ps 147** | Números de salmo de la Vulgata con versificación hebrea (Ps 115 = Heb 116,10-19) |
| **Ps 113A / 113B** | El Ps 113 de la Vulgata se cita partido; 113B lleva +8 |
| **Jn 6,51** | La Clementina **parte** el versículo en dos; de 6,52 en adelante va +1 |
| **Mc 9** | Mc 9,1 moderno es Mc 8,39 en la Vulgata; el resto del capítulo, −1 |
| **Ml 3,19-24** | = Ml 4,1-6 en la Vulgata, que conserva el cuarto capítulo |
| **Jl 4** | La Vulgata solo tiene 3 capítulos en Joel |
| **Os 2** | −2 (Os 2,1-2 moderno = Os 1,10-11) |
| **Za 2** | −4 (Za 2,1-4 moderno = Za 1,18-21) |
| **Ex 40, Gn 50, Mt 17, Hch 7, Hch 14, Mc 4, Ps 15, Ps 55, Ps 95** | Versículos fundidos por la Clementina |
| **Eclo 3 y 24** | El libro más divergente: desfases de +1, +2 y +4 dentro del mismo capítulo |

Cuando la Clementina funde dos versículos modernos, los dos apuntan al mismo
texto: la resolución **deduplica**, de modo que no se repite nada. Cuando los
parte (Jn 6,51), la regla lleva `expandir=1` y se traen los dos.

#### Lo que queda en pie como riesgo

Un desfase de ±1 en una cita **corta** (un versículo de aleluya) no lo detecta
ninguna de las tres comprobaciones: el recuento cuadra y el texto es demasiado
breve para el cotejo. Es un residuo conocido y acotado; la forma definitiva de
cerrarlo sería contrastar contra una versificación moderna de referencia, que
es justamente lo que aportaría el proyecto de la Nova Vulgata.

Las erratas del propio sitio encontradas por el camino (`My 2, 2`, `Jn 8,2b` por
`8,12b`, `Is 33,32` por `33,22`, números partidos por un espacio como `10-1 1`)
están en `data/citation_overrides.csv`, también editable.

### 7.1 Resultado de la Etapa 1 (corpus de la Vulgata)

El parser tipográfico funciona. Dos fallos encontrados y corregidos en el
camino, ambos verificados con el control de calidad automático:

1. Los números del índice del PDF **ya son índices base 0**, así que cada libro
   salía desplazado una página (el Génesis perdía el cap. 50 y se lo quedaba el
   Éxodo). 27 libros afectados.
2. Los libros de **un solo capítulo** (Abdías, Filemón, 2 y 3 Jn, Judas) no
   llevan numeral de capítulo impreso, así que salían vacíos.

Comprobaciones de texto superadas: palabras partidas por el guión de fin de
renglón reunidas (`prædesti-/natus` → `prædestinatus`), ligaduras resueltas
(`conflabunt`, `sanctificationis`), diéresis recompuestas, 0 guiones sospechosos
residuales. Confirmado también el riesgo §5.2.3: `Ps 121,1` incluye el título
*«Canticum graduum»* dentro del versículo 1.

### 7.2 Cómo se resolvió la enumeración de páginas sin los índices del sitio

El origen sólo dejó descargar el índice del Leccionario I. Para los demás:

- **Ciclos B y C derivados del A**: los números de archivo son paralelos
  (`1014ACUD01` → `2014BCUD01` / `3014CCUD01`). Verificado contra las 34 + 44
  páginas que sí están archivadas. Los comunes a los tres ciclos conservan su
  código (`TNSMDM`, `TFJUSA`…) y hay excepciones sueltas (`3022AVIPAS` mantiene
  la A), así que el rastreador prueba **ambas variantes** y se queda con la que
  responda.
- **Inventario CDX de Wayback** (`data/cdx.txt`, 361 páginas archivadas) como
  fuente adicional, sobre todo para el Leccionario VII (129 páginas).
- El **Leccionario IV sigue dependiendo del origen**: sólo 6 de sus ~290
  páginas están archivadas. Es el único punto que puede quedar incompleto.

**Desenlace:** el origen volvió a responder y entregó **los cinco índices
reales**, así que no hizo falta adivinar nada. Cifras confirmadas: Lecc. I = 70
páginas, II = 71, III = 71, **IV = 410** (Año I + Año II, como estimaba el
plan), VII = 131. **758 páginas objetivo.** La derivación de los ciclos B y C
queda en el código como red de seguridad por si el origen vuelve a caerse.

### 7.3 Resultado de las Etapas 2 y 3 (índice maestro)

Sobre las páginas ya descargadas: **1315 citas, 1292 normalizadas (98.3 %),
0 fallos**. Las 23 restantes no son errores: son «Aleluya» sin versículo,
«Secuencia:» y aleluyas dados como texto libre sin referencia bíblica.

Comprobaciones superadas en la salida:

| Caso | Resultado |
|---|---|
| El ejemplo que diste (Dom. I Adviento A) | `Is 2,1-5` · `Sal 121,1-2.4-5.6-7.8-9` · `Rm 13,11-14a` · `Mt 24,37-44` ✔ |
| Salto de capítulo (guion largo) | `Is 8, 23b—9, 3` → `Is 8,23b—9,3` ✔ |
| Pasión entera | `Jn 18, 1—19, 42` ✔ |
| Libro de un solo capítulo | `Filemón 9b-10. 12-17` → `Flm 1,9b-10.12-17` ✔ |
| **Desplazamiento de Reyes/Samuel** | `1 R`→Regum III, `2 R`→Regum IV, `1 S`→Regum I, `2 S`→Regum II ✔ |
| Lecturas alternativas | 71 «o bien» + 47 formas breves, marcadas ✔ |

Erratas del propio sitio detectadas y corregidas en `data/citation_overrides.csv`
(fichero editable, sin tocar código): `My 2, 2`→`Mt 2, 2`; `Juan 3,1 6-18`;
`segunda cara`→`carta`; `Hebreo`→`Hebreos`; `san Luca`→`san Lucas`;
`Mc 11 9b-10a`→`Mc 11, 9b-10a`.

### 7.4 Ficheros que ya existen

```
src/0_build_books.py      Siglas.docx -> data/books.json (73 libros validados)
src/1_crawl.py            rastreo reanudable con respaldo en Wayback
src/2_parse_readings.py   HTML -> data/readings.json
src/3_normalize_refs.py   citas -> data/index_master.csv/.json   <- ENTREGABLE A
src/4_build_vulgate.py    vulgate.pdf -> data/vulgata.json (35 811 versículos)
src/5_resolve.py          referencias -> data/readings_latin.json
src/6_crosscheck.py       cotejo latin/castellano -> data/crosscheck.csv
src/7_offset_scan.py      propone desfases -> data/offset_proposals.csv
src/8_render.py           -> out/lectionarium.md                 <- ENTREGABLE B
src/9_docx.py             -> out/carta/*.docx y out/media/*.docx
                          (maquetado de libro; indice con hipervinculos y
                           numero de pagina)
src/10_toc.py             indices del sitio -> data/toc.json (esqueleto + orden)
src/11_pdf.py             out/<perfil>/*.docx -> out/pdf/<perfil>/*.pdf
                          (LibreOffice)
src/12_calendario.py      los 5 leccionarios -> data/calendario.json
                          (el ano liturgico de corrido)

data/toc.json                 arbol de los cinco indices del sitio
data/toc_overrides.csv        erratas de los enlaces del indice, editables
data/toc_qa.txt               cotejo indice <-> celebraciones parseadas
data/calendario.json          el ano liturgico: seccion > semana > dia
data/calendario_qa.txt        el ano entero en una lista + el cuadre
data/versification_map.csv    las 27 reglas de versificacion, editables
data/citation_overrides.csv   erratas del sitio, editables
data/latin_formulas.csv       "Lectio libri Isaiae prophetae" + siglas latinas
data/vulgata_qa.txt           control de calidad del corpus
data/unparsed_citations.txt   citas no entendidas (vacio)
data/unresolved.csv           versiculos ausentes (vacio)
```

Orden de ejecución: `0 → 4 → 1 → 2 → 3 → 5 → 6 → 7 → 10 → 8 → 9 → 11`.
Para la app, además: `12 → 16 → 17 → 18 → 15` (el 18 es el santoral y la
precedencia, §13; el 14 sigue existiendo y lo importa el 18 como biblioteca).
Los cinco documentos separados: `python src/8_render.py --separados` y
`python src/9_docx.py --separados`.
El leccionario unico en orden del ano: `python src/12_calendario.py` y
luego `python src/8_render.py --anual` y `python src/9_docx.py --anual`.
Las fases 6 y 7 no producen el leccionario: lo auditan.

`9_docx.py` y `11_pdf.py` trabajan por defecto en los **dos tamaños** (§7.9).
Para uno solo: `--perfil carta` o `--perfil media`.

Nota: `Siglas.docx` estaba bloqueado (abierto en Word), así que
`0_build_books.py` acepta `--docx RUTA` para trabajar sobre una copia.

OBSERVACIÓN EXTRA: Quiero que después hagamos lo mismo pero con la traducción de la Nova Vulgata en otro proyecto, tal vez más adelante. No quiero que lo empieces ahora.
---

## 8. Segunda edición: la **Nova Vulgata**, el latín litúrgico vigente

Fecha: 2026-09-27.

### 8.1 Qué versión es la litúrgica, y por qué

La pregunta era cuál es «la versión litúrgica en latín actual». La respuesta es
la **Nova Vulgata Bibliorum Sacrorum editio**: preparada por la comisión que
creó Pablo VI en 1965, promulgada por Juan Pablo II con la constitución
apostólica *Scripturarum thesaurus* del 25 de abril de 1979, y reeditada como
*editio typica altera* en 1986.

No es una deducción: lo dice el propio **Ordo lectionum Missae**, editio typica
altera de 1981, cuyos *praenotanda* se han leído para este trabajo. Dos frases
zanjan el asunto:

> «*adhibita est Bibliorum sacrorum editio Nova Vulgata*»
>
> «*Indicatio textus (id est capituli et versuum) datur semper secundum Novam
> Vulgatam editionem exceptis Psalmis*»

Es decir: el leccionario latino de 1981 **cambió** la Vulgata que traía la
edición de 1969 por la Nova Vulgata, y además da las citas según la Nova
Vulgata — **salvo los salmos**, que sigue citando por la numeración griega (la
de la Vulgata) según el *Liber Psalmorum* de 1969 de la propia comisión.

Eso tiene una consecuencia práctica grande: las citas del leccionario español de
Koinonía **ya están en la versificación de la Nova Vulgata**. Por eso esta
segunda edición resuelve mejor que la primera, y con muchas menos reglas.

### 8.2 De dónde sale el texto

De la Santa Sede, que lo publica íntegro y en abierto: 73 páginas HTML, una por
libro, bajo `vatican.va/archive/bible/nova_vulgata/`. Se bajan con
`4b_crawl_nova.py` (una petición cada 2 s, caché en disco) y se parsean con
`4c_build_nova.py`.

El marcado del sitio es sorprendentemente regular y el parseo sale determinista:

| Marca | Significado |
|---|---|
| `<a name="7">7</a>` | número de capítulo |
| `<a name="PSALMUS 23">…</a> (22)` | salmo, **con su número griego al lado** |
| `<br />12 texto…` | número de versículo + texto |
| `<br /> texto…` | renglón de poesía: sigue el versículo |
| `(21) 22 texto…` | el 21 **no existe** en la Nova Vulgata |
| `<i>Magistro chori. PSALMUS. David.</i>` | epígrafe del salmo, no texto |

Resultado: **73 libros · 1328 capítulos · 35 729 versículos**, con el control de
calidad en cero problemas y cero cifras sueltas dentro del texto.

Tres cosas se guardan que en la Clementina no había:

1. **La estiquiometría.** La Nova Vulgata imprime la poesía en renglones y se
   conservan en `nova_vulgata_stichos.json`, por si algún día se maqueta como
   verso.
2. **La doble numeración de los salmos.** La propia edición da el número griego
   entre paréntesis, así que la tabla de equivalencias **sale de la fuente** y no
   de una suposición (`psalmi_nova.csv`, 152 filas).
3. **Los versículos omitidos.** La edición marca «(21)» los 32 versículos que no
   trae por faltar en el texto crítico (`nova_omissiones.csv`). Sin esa lista, un
   hueco legítimo y un fallo de parseo serían indistinguibles.

Ocho fallos del parser encontrados y corregidos por el camino, todos con su
prueba: el numeral puede ir en mitad del renglón (Gn 14,19; Lv 19,36; Hch 3,18),
pegado a la palabra siguiente (`1Cum`) o a la comilla (`2“ Fili hominis`); las
letras de versículo llegan a ser dos (Est 4,17aa–17kk); Daniel 3 lleva doble
numeración, la griega y la aramea, una detrás de otra; cinco libros de un solo
capítulo no llevan numeral impreso; y en Jue 19 y Ba 6 hay un encabezamiento sin
numerar delante del versículo 1 (se guarda con la clave `"0"`), mientras que en
Nm 1 el que va sin numeral es el versículo 1 mismo — lo que distingue los dos
casos es el numeral que venga después, así que se decide al encontrarlo y no
antes.

#### Las erratas de vatican.va

El HTML de la Santa Sede trae **91 defectos tipográficos**, todos recogidos en
`nova_errata.csv`, que es editable y cuyo uso se cuenta: si alguna regla deja de
aplicarse, el control de calidad avisa en vez de callarse.

De ellos, **85 son palabras partidas por un espacio** (`qui ob viavit` por
`obviavit`, `bo num` por `bonum`, `Chri sto` por `Christo`, `man data` por
`mandata`…). Se concentran en el **versículo 1 de cada capítulo**, que es donde
la edición impresa lleva la capitular, así que el defecto viene de ahí.

No se han cazado a ojo. El detector usa **el propio corpus como diccionario**:
para cada par de palabras contiguas mira si el pegado existe y es frecuente en
los 35 729 versículos, y si la primera mitad, en cambio, es un *hapax*. Eso
saca 31 casos sin un solo falso positivo. Una segunda pasada, más laxa (el
fragmento puede ser una palabra latina de verdad: `ob`, `in`, `pro`, `de`),
propone otros 60, que **sí** hay que juzgar uno a uno: `se ipsum`, `de vita`,
`nec non`, `quam vis`, `in habitantibus` o `bene dicimus` son buen latín y se
han dejado como están. Tras las correcciones el detector devuelve cero.

Las seis restantes: `0 Hira Iethraeus` por `40` (1 Par 11,40), `insu7per` por
`insuper` (Prv 19,7), un paréntesis que se abre y no se cierra (Eclo 1,20),
`mi sit` por `misit` (Ba 6), un `non` duplicado (1 Co 7,1: «*mulierem non non
tangere*») y un `super` de más en Gal 6,17.

Ese último merece una nota, porque se resolvió con el testigo de más autoridad
que hay a mano: vatican.va publica «*stigmata Iesu **in super** corpore meo
porto*», y el Ordo lectionum Missae de 1981 —que es el leccionario hecho con
esta misma Nova Vulgata— titula esa lectura «*Stigmata Iesu in corpore meo
porto*». El libro litúrgico corrige a la página web.

Dos erratas cruzan el salto de línea de la fuente (Ps 119,93 `man data`;
Jr 9,1 `de relinquam`), de modo que las reglas se aplican dos veces: sobre el
renglón —hacen falta ahí para las que afectan al numeral del versículo— y sobre
el versículo ya montado.

### 8.3 Lo único que divergía de verdad: los salmos

La Nova Vulgata numera los salmos **por el hebreo** (`PSALMUS 23 (22)`), y el
leccionario los cita **por el griego**. La tabla `psalmi_lect_nova.csv` traduce
de una numeración a otra, y su aritmética queda comprobada contra el recuento de
versículos del propio corpus:

| Cita del leccionario | Nova Vulgata | Comprobación |
|---|---|---|
| Sal 1–8 | igual | — |
| Sal 9,1-21 | Ps 9 | el Ps 9 de la NV tiene 21 vv. ✔ |
| Sal 9,22-39 | Ps 10, −21 | el Ps 10 de la NV tiene 18 vv. = 39−22+1 ✔ |
| Sal 10–112 | +1 | — |
| Sal 113,1-8 | Ps 114 | el Ps 114 de la NV tiene 8 vv. ✔ |
| Sal 113,9-26 | Ps 115, −8 | el Ps 115 de la NV tiene 18 vv. ✔ |
| Sal 114 y Sal 115,10-19 | Ps 116 | 9 + 10 = los 19 vv. del Ps 116 ✔ |
| Sal 116–145 | +1 | — |
| Sal 146 y Sal 147,12-20 | Ps 147 | 11 + 9 = los 20 vv. del Ps 147 ✔ |
| Sal 148–150 | igual | — |

El leccionario escribe *Salmo 113A* y *113B*, y `3_normalize_refs.py` ya lo pasa
a la numeración corrida del griego; y en el Sal 115 y el Sal 147 cita ya con los
versículos del hebreo, así que ahí no hay desplazamiento. Las dos reglas del caso
contrario están escritas en la tabla, con su nota, para el día en que aparezca
una cita que las necesite.

En la cita impresa se conserva **el número litúrgico** (el que dan el OLM y el
leccionario) y se añade entre corchetes dónde está el texto:
`Ps 121,1-2. 4-5. 6-7. 8-9 [Ps 122]`.

### 8.4 Resto de la versificación: prácticamente nada

Frente a las **27 reglas** que necesitó la Clementina, la Nova Vulgata necesita
**dos**, y las dos en los salmos:

- `Ps 95,14` → la NV cierra el Ps 96 en el v. 13 y el leccionario parte ese
  versículo en 13 y 14;
- `Ps 150,6` → la NV cierra el Ps 150 en el v. 5, que abarca los vv. 5 y 6.

Y **un** caso que no se arregla con aritmética: las adiciones griegas de Ester,
que la Vulgata pone como capítulos 13–16 y la Nova Vulgata dentro del capítulo 4
con versículos en letras. Los dos textos latinos no se corresponden versículo a
versículo, porque Jerónimo tradujo otra recensión griega — comprobado midiendo la
coincidencia léxica: solo `Est 14,1` empareja con fuerza (0.90 con `Est 4,17n`) y
el resto se queda por debajo de 0.2. La equivalencia se toma por tanto del propio
OLM de 1981, que para el jueves de la 1ª semana de Cuaresma cita
`Est 4, 17n. p-r. aa-bb. gg-hh` (`nova_overrides.csv`).

Todo lo demás —Eclo 3 y 24, Ml 3,19-24, Jl 4, Os 2, Za 2, Mc 9, Jn 6,51, Ex 40,
Hch 7 y 14, 1-2 Samuel / 1-2 Reyes— **cuadra solo**, porque es la versificación
moderna. Ejemplo comprobado a mano: Eclo 3,2 = «Indicium patris audite, filii»,
que es justamente el comienzo de la lectura de la Sagrada Familia y que en la
Clementina estaba en 3,3.

### 8.5 Cómo ha quedado el control de calidad

| | Clementina | Nova Vulgata |
|---|---|---|
| Reglas de versificación | 27 | 2 |
| Lecturas resueltas del todo | 3290 / 3290 | 3290 / 3290 |
| Versículos latinos extraídos | 21 562 | 21 540 |
| Descuadres de recuento sin explicar | 0 | 0 |
| Coincidencia mediana latín–castellano | 0.14 | 0.14 |
| Lecturas con coincidencia < 7 % (a revisar) | 379 | **334** |

Los 22 versículos de diferencia son los que la Nova Vulgata declara que no trae
(Mc 7,16; 9,44; 9,46; 11,26; 15,28; Lc 17,36; 23,17; Jn 5,4; Hch 8,37; Mt 23,14;
Rom 16,24; Eclo 35,3), y el cotejo los cuenta ya como explicados. Que las
lecturas sospechosas bajen de 379 a 334 con el **mismo** verificador es una señal
independiente de que este texto casa mejor con el castellano del leccionario, que
es lo que cabía esperar de un texto y una traducción hechos los dos sobre los
originales.

### 8.6 Las fórmulas, tomadas del Ordo lectionum Missae

Las fórmulas de introducción no se han inventado ni se han heredado de la edición
anterior: salen de las normas del propio OLM de 1981 y de su *index siglorum*,
leídos en el ejemplar digitalizado en Internet Archive
(`archive.org/details/OLM1981`):

- siempre «*Lectio libri…*», «*Lectio Epistolae…*», nunca «Initium» ni
  «Sequentia»;
- dos libros del mismo nombre → «*liber primus*» / «*liber secundus*»,
  «*Epistola prima*» / «*Epistola secunda*»;
- nombres modernos: **1 y 2 Samuelis**, **1 y 2 Regum**, **1 y 2 Chronicorum**,
  **Esdrae** y **Nehemiae**;
- sapienciales: *Iob, Proverbiorum, Ecclesiastes vel Qohelet, Canticum
  Canticorum, Sapientiae, Ecclesiasticus vel Siracidis*;
- profetas: «*Lectio libri Isaiae, Ieremiae, Baruch*», pero «*Lectio Prophetiae
  Ezechielis, Danielis, Osee… Malachiae*»;
- «*Lamentationes*» y «*Epistola ad Hebraeos*» **sin** mencionar a Jeremías ni a
  Pablo.

Las siglas son también las del OLM (`Gen, Ex, Lev, Num, Deut, Ios, Iudic, Rut,
1 Sam, 1 Reg, 1 Chr, Esd, Neh, Tob, Iudt, Est, Iob, Ps, Prov, Qoh, Cant, Sap,
Sir, Is, Ier, Lam, Bar, Ez, Dan, Os…, Mt, Mc, Lc, Io, Act, Rom, 1 Cor…, Phm,
Hebr, Iac, 1 Petr, 1 Io, Iudae, Ap`), y la ortografía es la de la Nova Vulgata:
`ae`/`oe` en vez de `æ`/`œ`, e `i` en vez de `j` (*Iosue, Iob, Ioel, Ioannes,
Iacobi, Iudae*).

Y una mejora que la Clementina no permitía: el **epígrafe del salmo**
(«*Magistro chori. PSALMUS. David.*») se quita del salmo responsorial, porque los
libros litúrgicos no lo imprimen. Se puede hacer sin adivinar porque la edición
lo marca en cursiva, y de ahí salen los 133 epígrafes de
`nova_psalmi_tituli.csv`.

### 8.7 Ficheros nuevos y cómo se ejecuta

```
src/4b_crawl_nova.py      vatican.va -> cache/nova/*.html (73 libros)
src/4c_build_nova.py      cache/nova -> data/nova_vulgata.json
                          + nova_vulgata_stichos.json (poesía en renglones)
                          + psalmi_nova.csv (doble numeración, de la fuente)
                          + nova_omissiones.csv (los 32 versículos ausentes)
                          + nova_psalmi_tituli.csv (133 epígrafes)
                          + nova_qa.txt

data/books_nova.csv              Clementina -> Nova Vulgata, los 73 nombres
data/psalmi_lect_nova.csv        leccionario (griego) -> Nova Vulgata (hebreo)
data/versification_map_nova.csv  las DOS reglas que quedan
data/nova_overrides.csv          las adiciones griegas de Ester
data/nova_errata.csv             las cuatro erratas de vatican.va
data/latin_formulas_nova.csv     fórmulas y siglas del OLM 1981
data/readings_latin_nova.json    referencias resueltas
data/unresolved_nova.csv         versículos ausentes (vacío)
data/resolve_qa_nova.txt         informe de resolución
data/crosscheck_nova.csv         cotejo latín-castellano
```

Las fases 5, 6, 8, 9 y 11 aceptan ahora `--fuente clementina|nova` (por omisión,
`clementina`, así que nada de lo anterior cambia). La Nova Vulgata escribe en
`out/nova/`:

```bash
python src/4b_crawl_nova.py
python src/4c_build_nova.py
python src/5_resolve.py     --fuente nova
python src/6_crosscheck.py  --fuente nova
python src/8_render.py      --fuente nova [--separados|--anual]
python src/9_docx.py        --fuente nova [--separados|--anual]
python src/11_pdf.py        --fuente nova
```

### 8.8 Lo que queda abierto

- **El OLM de 1981 como tercer verificador.** Al buscar las fórmulas se descubrió
  que su texto digitalizado trae el índice de perícopas entero, y que para el
  Domingo I de Adviento A da exactamente lo mismo que el índice sacado de
  Koinonía (Is 2,1-5 · Ps 121,1-2.4-5.6-7.8-9 · Rom 13,11-14a · Ps 84,8 ·
  Mt 24,37-44). Cotejar el índice maestro completo contra él cerraría el único
  riesgo que sigue en pie desde la primera edición: un desfase de ±1 en una cita
  corta, que ninguna de las comprobaciones actuales detecta. El OCR es ruidoso
  (`Ps 121, r-2` por `1-2`), así que habría que tolerar erratas, pero para
  detectar desfases de capítulo y de versículo serviría de sobra.
- **Los títulos latinos de las celebraciones.** El mismo documento los trae
  (*DOMINICA PRIMA ADVENTUS*), de modo que el leccionario podría ir entero en
  latín, rúbricas incluidas, y no solo las lecturas.
- **La poesía como verso.** La estiquiometría ya está guardada; falta usarla en
  la maquetación de salmos y profetas.

---

## 9. La acentuación litúrgica, en las dos versiones (decisión 7, fase 9)

Los libros litúrgicos marcan con acento agudo la sílaba tónica de toda palabra
de tres sílabas o más — *Dóminus*, *Léctio*, *quǽsumus* — para que el texto se
pueda leer en voz alta y cantar sin saber latín. La §6.bis midió que con reglas
de posición y unas miles de formas curadas a mano se llegaba al 86 %, y que el
99,5 % que pide un libro impreso exigía un léxico completo de cantidades
vocálicas que no estaba a mano.

Lo que ha cambiado el cálculo no es un método mejor: es una fuente que no se
había buscado.

### 9.1 El acento no hay que deducirlo: está impreso

**Divinum Officium** publica el Breviario y el Misal romanos en latín **ya
acentuados**, y —esto es lo decisivo— con la misma ortografía clásica que usa
este proyecto: *Isaíæ*, *quǽsumus*, *ejus*, *pestiléntiæ*. Son **6062 ficheros**
de texto con la Escritura, los salmos, las antífonas y las oraciones: el acento
**tal como lo imprimen los libros**, no como lo deduciría una regla.

De ahí salen **51 999 formas latinas** con su acento medido, cosechadas de
80 834 renglones. La cosecha no se cree lo que no puede comprobar:

- descarta las palabras con w o k, que en ese corpus son apellidos checos de los
  propios de Bohemia, donde el agudo marca cantidad y no tónica;
- descarta el acento que caiga en la última sílaba, porque el latín no la
  acentúa nunca: si sale ahí, o la palabra está mal silabeada o no es latina;
- exige que una forma con varias apariciones coincida consigo misma en el 80 %
  de ellas; las **209** que no lo cumplen se quedan sin decidir.

Para lo que el uso litúrgico no cubre hay una segunda fuente, complementaria:
las **cantidades vocálicas de Morpheus** (Perseus, vía CLTK), 755 557 análisis
morfológicos con la vocal larga marcada (`ju_sto_rum` = *jūstōrum*). De ellos,
32 364 formas pertenecen al vocabulario de este proyecto y **31 512** dan un
acento único.

Traerlo cuesta una orden y no se repite: el corpus litúrgico viene con un clon
parcial de git (`--filter=blob:none --sparse`), así que de un repositorio de
210 MB se bajan sólo los 12 MB de las carpetas latinas.

### 9.2 El orden de decisión, y por qué es ése

Cada palabra se resuelve por orden de autoridad, y el módulo deja escrito de
dónde salió cada decisión (`data/acentos_cobertura_*.txt`):

| # | Paso | Clementina | Nova Vulgata |
|---|------|-----------:|-------------:|
| 1 | decisión a mano (`acentos_overrides.csv`) | 0,24 % | 0,29 % |
| 2 | **posición**: diptongo o penúltima trabada → penúltima | 17,62 % | 17,70 % |
| 3 | **el uso litúrgico impreso** | 78,98 % | 77,84 % |
| 4 | el uso, con la grafía `ae`/`oe` de la otra edición | 0,01 % | 0,02 % |
| 5 | nombre propio que el uso deja desnudo | 0,76 % | 0,77 % |
| 6 | **hiato**: vocal ante vocal → penúltima breve | 0,37 % | 0,56 % |
| 7 | cantidades vocálicas | 1,24 % | 1,72 % |
| 8 | la palabra sin su prefijo (*extollite* ← *tóllite*) | 0,05 % | 0,10 % |
| 9 | terminaciones aprendidas del propio uso | 0,23 % | 0,35 % |
| 10 | cantidad ambigua → antepenúltima | 0,14 % | 0,15 % |
| 11 | por omisión, penúltima | 0,35 % | 0,50 % |

**Resueltas con fundamento: 99,65 % en la Clementina y 99,50 % en la Nova
Vulgata**, sobre 121 322 y 119 853 apariciones de palabras de tres sílabas o
más. Lo que queda —430 y 605 apariciones— lleva el acento en la penúltima, que
es lo que hacen el 62 % de las formas de penúltima abierta del corpus, y está
listado en `data/acentos_excepciones_*.csv` para revisarlo a mano.

Tres pasos merecen explicación, porque no son arbitrarios:

- **La posición va antes que el uso** porque la posición no falla. Contrastada
  con las 51 999 formas acentuadas del corpus, sólo discrepa en **38**, y todas
  son erratas del propio corpus (`intelligeendi`, `aeteerna`, `ieruraslem`,
  `icitbus`): letras dobladas o traspuestas al teclear.
- **El uso va antes que el hiato** porque el hiato falla justo donde el
  leccionario tiene más nombres propios. La regla «vocal ante vocal es breve»
  daría *Mária*, *Élias*, *íllius*, *díei*; los libros imprimen **María**,
  **Elías**, **illíus**, **diéi**, con la i larga del griego y de los genitivos
  pronominales. Son 74 formas, y el uso acierta en todas.
- **Las terminaciones no se han inventado: se aprenden.** De las formas de
  penúltima abierta que el uso ya decide se sacan las terminaciones que mandan
  siempre — `-átur`, `-ébat`, `-órum`, `-íbus`, `-ítur`… — y sólo entran las
  **371** que tienen 25 casos o más y un acuerdo del 99,5 % entre ellos. Así el
  leccionario acentúa bien palabras que ningún libro litúrgico trae, como
  *ascensiónum* o *Thyatirenórum*.

Cuando el uso se apoya en menos de cuatro apariciones y la cantidad clásica dice
otra cosa, manda la cantidad: es la única forma de no heredar las erratas del
corpus (*arbóri* por **árbori**, *Ephési* por **Éphesi**). Pero no en hiato: ahí
Morpheus no marca la i larga de *María* ni la de *intróeas*, y el uso acierta
aunque tenga un solo testigo.

### 9.3 Las dos ediciones se prestan lo que cada una no escribe

La acentuación planteó un problema que las fases anteriores no tenían: para
saber dónde cae el acento hay que saber cuántas sílabas tiene la palabra, y eso
depende de la ortografía de cada edición.

- La Clementina escribe **Israël**, **introëas**, **Noëmi**: la diéresis avisa
  de que ahí `ae`/`oe` **no** es diptongo. La Nova Vulgata escribe *Israel*,
  *introeas*, *Noemi*, y sin ese aviso se leerían con una sílaba menos.
- La Clementina escribe **ejus**, **major**, **allelúja**: la j avisa de que ahí
  la i **no** es vocal. La Nova Vulgata escribe *eius*, *maior*, *alleluia*, y
  sin ese aviso *eius* saldría con tres sílabas y con acento.

Las dos informaciones se extraen del propio corpus de la Clementina y se le
prestan a la Nova Vulgata por la clave común a las dos ortografías: **110**
formas con hiato y **1322** con i consonántica. No hay que adivinar nada: lo que
una edición no escribe, la otra sí.

La misma clave arregla un tercer caso: la Nova Vulgata escribe *paenitemini*
donde la Clementina escribe *pœnitemini*. Es la misma palabra y el mismo acento,
así que **Pœnitémini** y **Paenitémini** salen las dos del mismo testigo.

Y una decisión tipográfica, tomada contando y no de memoria: el agudo va en la
**primera** vocal del diptongo (*exáudi*, *gáudium*: 2712 apariciones en el
corpus) y **en la ligadura** cuando la hay (*quǽsumus*: 5925 apariciones). Si
cae en una vocal con diéresis, el agudo **la sustituye**, porque los libros
imprimen *Israélis* y *Michaélis*, no *Israë́lis*. Comprobado además que
Constantia —la tipografía del libro— trae ǽ (U+01FD) y ǿ (U+01FF), así que el
DOCX y el PDF no caen en una sustitución de fuente.

### 9.4 Cuatro comprobaciones, no una impresión

1. **Posición contra uso**: 38 discrepancias sobre 51 999 formas, todas erratas
   del corpus litúrgico. No afectan al resultado, porque la posición se aplica
   antes que el uso.
2. **Uso contra cantidades clásicas**: 119 formas discrepan, 74 de ellas en
   hiato. Fuera del hiato el uso bien atestiguado acierta —*Paráclitus*,
   *ázymos*, *dedúcis*, *alicúius*, *venúmdari* son suyos— y donde tiene uno o
   dos testigos manda la cantidad. Las 119 quedan en
   `data/acentos_discrepancias.csv` con la elegida y el motivo.
3. **Validación por retención**, que es la que de verdad mide. Se construye el
   léxico **sin el Salterio**, se acentúa con él el Salterio de nuestra
   Clementina y se compara palabra por palabra con el Salterio acentuado de los
   libros litúrgicos:

   | | |
   |---|---:|
   | versículos del Salterio comparados | 2613 |
   | palabras de 3+ sílabas comparadas | 8376 |
   | **coinciden con el libro impreso** | **8340 (99,57 %)** |
   | no coinciden | 36 (0,43 %) |

   Las 36 son formas homógrafas que sólo el contexto resuelve (*invenímus*
   presente / *invénimus* perfecto, *irascéris* futuro / *irásceris* presente) y
   tercera conjugación que la penúltima por omisión lee larga (*extóllite*,
   *compungímini*). Dos de las decisiones a mano salieron de esta misma
   comparación, así que el número es ligeramente optimista; en la pasada de
   verdad el Salterio sí está en el léxico y sale clavado.

4. **El mismo Salterio, con el léxico completo**, donde ya no falta ningún
   dato: ahí una discrepancia no es falta de información, es un fallo de la
   maquinaria. Salen **8370 de 8377 (99,92 %)**, y las siete restantes son
   homógrafas que sólo el contexto resuelve (*irascéris* futuro / *irásceris*
   presente, *maria* «los mares» frente a *María*). Esta prueba es la que cazó
   dos fallos de verdad mientras se montaba: una caché que confundía *æra* con
   *aëra* porque compartían clave, y un «eu-» que se daba por diptongo y
   convertía *e-úntibus* en *éuntibus*.

   Se comprueba además, sobre las 121 376 apariciones, que acentuar **no le
   cambia ni una letra a ninguna palabra**: 0 fallos en las dos fuentes. Y la
   Nova Vulgata de vatican.va trae una palabra que ya venía acentuada
   (*commoratío*, Hch 1,20): no se toca, y se avisa en el informe.

### 9.5 Lo que el uso litúrgico deja desnudo

Hay nombres hebreos que los libros **no acentúan nunca**, y el corpus lo dice
con números: *Israël* aparece desnudo 953 veces y acentuado 2. Se respeta, y por
eso el leccionario imprime **Israel**, **Isaac**, **Aaron**, **Isai**,
**Absalom**, **Amalec** y **Elcana** sin marca, igual que el Salterio impreso.

No se respeta, en cambio, cuando la desnudez viene de las rúbricas y de los
encabezamientos del Martirologio y no de la Escritura: *Áctuum*, *Éxodi*,
*Ángelo*, *Ásia*, *Áfricam*, *Árabum* llevan su acento, apuntado en
`acentos_overrides.csv` con el motivo. Y **Ábraham** lo lleva porque el Salterio
—que es Escritura, como nuestro texto— lo imprime acentuado nueve veces, aunque
los propios de los santos lo dejen desnudo 144.

La lista completa está en los informes de cobertura, y cambiar cualquiera de
estas decisiones es una línea en `acentos_overrides.csv`, sin tocar código.

### 9.6 Ficheros nuevos y cómo se ejecuta

```
src/13a_crawl_acentos.py   corpus liturgico acentuado + cantidades -> cache/acentos/
src/13b_build_acentos.py   cache/acentos/ -> las seis tablas de data/
src/13_acentos.py          el motor; lo importan 8_render.py y 9_docx.py

data/acentos_liturgico.csv      el acento que imprimen los libros liturgicos
data/acentos_cantidades.csv     el acento que se deduce de las cantidades
data/acentos_terminaciones.csv  terminaciones aprendidas del uso, con su acuerdo
data/acentos_hiato.csv          donde 'ae'/'oe' no es diptongo
data/acentos_jota.csv           donde la i es consonante
data/acentos_discrepancias.csv  uso contra cantidades, con la elegida y el motivo
data/acentos_overrides.csv      las decisiones a mano (editable; "-" = sin marca)
data/acentos_qa.txt             el informe de construccion y las tres pruebas
data/acentos_cobertura_*.txt    de donde sale cada acento, por fuente
data/acentos_excepciones_*.csv  lo que queda sin fundamento, para revisar
```

```bash
python src/13a_crawl_acentos.py          # una sola vez
python src/13b_build_acentos.py          # construye los lexicos y los valida
python src/13_acentos.py --fuente nova   # informe de cobertura
python src/13_acentos.py --muestra "Lectio libri Isaiae prophetae"
```

La acentuación está **encendida por omisión** en `8_render.py` y `9_docx.py`, en
las dos fuentes; `--sin-acentos` devuelve el texto desnudo de antes.

### 9.7 Lo que sigue abierto aquí

- **Los homógrafos.** *María* / *mária* (los mares del salmo), *cónvenit* /
  *convénit*, *invénimus* / *invenímus*: el acento depende del contexto y el
  motor no lo mira. Son pocos y el uso litúrgico acierta con el más frecuente.
- **Las 430 y 605 apariciones sin fundamento**, casi todas nombres propios raros
  (*Meriba*, *Joakim*, *Raphidim*) que ningún libro litúrgico trae. Están en las
  dos `acentos_excepciones_*.csv`, con la propuesta y su número de apariciones,
  ordenadas por frecuencia: revisar las cincuenta primeras cubre la mitad.
- **Las rúbricas van en versales y sin acento** (`LECTIO PRIMA`), como en los
  libros impresos; si algún día se quieren en minúscula, el acento ya está
  disponible.

---

## 10. La app: el leccionario en el teléfono (fases 10 y 11)

Fecha: 2026-09-28.

Pediste poder leerlo en el móvil. La forma elegida es una **PWA**: una app web
que se instala en la pantalla de inicio desde Chrome, abre a pantalla completa
con su icono y **funciona sin conexión**, porque lleva el leccionario entero
dentro (6,2 MB). No hace falta SDK de Android, ni firma, ni Play Store; y la
misma carpeta se puede envolver en un `.apk` más adelante sin tocar una línea.

Lo que no se ha hecho —y es deliberado— es **volver a componer el texto**. La
app importa `8_render.py` y usa sus propias funciones para la fórmula latina de
cada libro, la cita con su sigla, la antífona del salmo y la acentuación de la
fase 9. Lo que enseña la app y lo que imprime el DOCX salen de la misma
maquinaria, así que no pueden divergir.

El texto se empaqueta **acentuado** y la app le quita el acento cuando se apaga
la acentuación: descomponer en NFD y borrar el `U+0301` respeta la diéresis
(`Israël`) y la ligadura (`æ`), que no son acento. Quitarlo es trivial; ponerlo
costó una fase entera.

### 10.1 La pieza nueva: qué día litúrgico es cada fecha

Hasta aquí el proyecto sabía *qué* se lee cada día del año litúrgico
(`calendario.json`: tiempo → semana → día), pero no *cuándo* cae ese día en el
calendario de la pared. Eso es `14_calendario_civil.py`, y sale entero de dos
fechas que se calculan:

* la **Pascua**, por el cómputo gregoriano, de la que cuelgan Ceniza, Cuaresma,
  Semana Santa, el tiempo pascual, Pentecostés y las tres solemnidades que le
  siguen;
* el **Domingo I de Adviento**, cuarto domingo antes de Navidad, del que cuelgan
  Adviento, Navidad, Epifanía y el Bautismo.

El Tiempo Ordinario no se numera hacia adelante sino **hacia atrás**: la semana
34 es siempre la que muere el sábado anterior al Adviento siguiente, y contando
desde ahí sale sola la semana en que se reanuda el lunes después de Pentecostés
—el famoso «salto», que en 2026 va de la 6ª a la 8ª—. No hay nada tabulado.

Las dos mitades se encuentran por una **clave canónica**: el calendario emite
`('to','fer',26,1)` y el nombre del día del leccionario («Lunes de la 26ª semana
de Tiempo Ordinario») se lee hasta dar en la misma clave. Ninguna mitad conoce
los rótulos de la otra, y lo que no casa se reporta en vez de perderse.

Comprobaciones, todas en `data/calendario_civil_qa.txt`:

| | |
|---|---:|
| años cubiertos | 2024–2060 |
| fechas colocadas | 13 415 |
| Pascua y Adviento contra fechas conocidas | 14 comprobaciones, **0 fallos** |
| días del leccionario que ninguna fecha usa | **0** |
| claves del calendario que el leccionario no tiene | **0** |
| días litúrgicos concretos comprobados a mano | 10, **0 fallos** |

### 10.2 Las tres opciones que cambian de un país a otro

Epifanía (6 de enero o el domingo entre el 2 y el 8), Ascensión (jueves o
domingo) y Corpus (jueves o domingo) se eligen en Ajustes. Emitir las ocho
combinaciones costaría ocho calendarios; en vez de eso se emite **el base y tres
parches**, porque cada opción toca un tramo distinto del año.

Que sean de verdad independientes **no se supone**: se construyen las ocho
combinaciones y se comprueba que aplicar los parches da exactamente lo mismo que
construir directamente. **0 fallos.** Los parches ocupan 188, 74 y 74 fechas
frente a las 13 415 del base.

### 10.3 Un título roto que apareció al montar el calendario

Cotejar las claves del calendario contra los días del leccionario dejó una sola
sin pareja: el **lunes de la 16ª semana del Tiempo Ordinario**. La página
`4091ITOL16.html` no lleva `<p class="Santo">`, así que el parser cayó en el
`<title>` del HTML, que en las páginas exportadas desde Word es *«Documento sin
título»* — y ese era el nombre del día en `calendario.json`, en el DOCX y en el
PDF.

Ningún control anterior podía verlo: las cuatro lecturas estaban completas y
correctas (Ex 14,5-18 · Ex 15 · Mt 12,38-42, que son las del lunes de la 16ª
semana, año I), así que todos los recuentos cuadraban. Es el mismo tipo de fallo
silencioso que el titulillo de §7.7 bis, y la misma lección: **los recuentos
cuadrando no son prueba de que los datos estén bien.**

Arreglado con `data/celebracion_overrides.csv`, editable sin tocar código, y con
aviso en el informe si alguna corrección deja de aplicarse. Los documentos
impresos heredan el arreglo al regenerarlos.

### 10.4 Qué hace la app

Lecturas de hoy al abrir · flechas de día y salto a cualquier fecha ·
Clementina o Nova Vulgata · acentuación, números de versículo y tamaño de letra
· claro, sepia u oscuro · índice del año entero · buscador sobre el latín que
ignora acentos y desata `æ`/`œ` (escribiendo `quaesumus` encuentra *quǽsumus*)
· el color litúrgico del tiempo en la cabecera.

**Lo que no trae, dicho a las claras** (superado en §13: desde entonces la app
trae V, VI y VIII, y el santoral puesto en el calendario): los leccionarios V,
VI, VIII y IX, que existen como documento (§12) pero no en la app: esta va por el calendario, y el
santoral pide uno de fechas fijas y precedencias que no está hecho. En la fiesta
de un santo enseña la feria o el domingo que toca, y el 26, 27 y 28 de diciembre
lo declara en pantalla en vez de callarlo.

### 10.5 Ficheros nuevos y cómo se ejecuta

```
src/14_calendario_civil.py   fecha civil -> dia liturgico, con sus tres parches
src/15_app_data.py           data/ -> app/datos/*.json + los iconos (sin PIL)

data/celebracion_overrides.csv  nombres de celebracion corregidos, editables
data/calendario_civil.json      13 415 fechas (391 KB)
data/calendario_civil_qa.txt    el informe y las comprobaciones

app/index.html · app/app.js · app/estilos.css · app/sw.js
app/manifest.webmanifest · app/icono-*.png · app/LEEME.md
app/datos/                      lo generado (6,2 MB)
```

```bash
python src/14_calendario_civil.py
python src/15_app_data.py
python -m http.server 8765 --directory app     # probarla en el ordenador
```

Para instalarla en el teléfono hay que servir `app/` **una vez** por `https`
(Netlify Drop o GitHub Pages, los dos gratis) y usar «Añadir a la pantalla de
inicio» en Chrome. A partir de ahí no necesita ni servidor ni conexión. Está
contado en `app/LEEME.md`.

### 10.6 Lo que queda abierto aquí

- **El propio de los santos.** Es lo único que le falta a la app para ser el
  libro completo, y es exactamente la etapa que quedó fuera en §6.8. La
  arquitectura lo admite: un leccionario más y unas cuantas claves de fecha
  fija. → **hecho en §13**.
- **Los apéndices** (§7.7): aleluyas alternativas y textos comunes del salmo
  responsorial, que tampoco están en los documentos impresos.
- **Marcadores y notas** del lector. No hay nada, y en una app de lectura diaria
  se acaba echando de menos.

---

## 11. Los anexos del leccionario (etapa 10, la que quedaba)

Fecha: 2026-09-28.

Era la única etapa del §7 que seguía pendiente, y lo único del sitio que el
proyecto declaraba y no traía. Son **tres anexos distintos**, no uno, y cada
uno pide un trato diferente:

| | Qué es | Cómo se resuelve |
|---|---|---|
| **Versículos alternativos para el Aleluya** | Una lista numerada por cada tiempo litúrgico | Son citas: al latín como cualquier lectura |
| **Textos comunes para el canto del salmo responsorial** | Salmos enteros que pueden cantarse en lugar del propio del día, y las respuestas por tiempo | Los salmos son citas; las respuestas, no |
| **Índice de textos** | Para cada pasaje bíblico, dónde se lee | No es texto que añadir: es el índice inverso |

Lo que hacía invisibles a los dos primeros ya estaba diagnosticado en §7.7: **no
llevan `<p class="Santo">`**, así que el parser de celebraciones no los
reconocía. El tercero ni siquiera es un formulario: es una tabla.

### 11.1 Lo que sirve de ancla, y lo que no

Las clases CSS, que en el resto del sitio son de una regularidad ejemplar
(§2.3), aquí no sirven: el mismo número aparece como `centrorojonum`, como
`centrorojo` y como `pnormal` según la página. Lo que manda es **la forma del
párrafo**: un número suelto es un número, venga con la clase que venga; y la
cita es siempre el párrafo que empieza por «Aleluya».

Eso deja dos clases de entrada:

* **con cita** — 105 en total, que pasan por el mismo `5_resolve.py` que las
  lecturas: mismas reglas de versificación, mismos overrides, misma
  renumeración de salmos en la Nova Vulgata. **105 de 105 resueltas, 0
  versículos ausentes**, en las dos fuentes.
* **sin cita** — 15: las siete antífonas «O» del 17 al 24 de diciembre y las
  ocho aclamaciones de Cuaresma. No son Escritura, así que su latín no puede
  salir de la Vulgata.

### 11.2 Las quince que no salen de ningún corpus

Es lo único de todo el proyecto que **no está medido**, y conviene que se sepa.
Están en `data/anexos_latin_fijo.csv`, editable, con columna `fuente` y columna
`confianza`:

* las **siete antífonas «O»** (*O Sapiéntia, O Adonái, O Radix Jesse…*) son
  texto del Breviario y del Misal romanos, inalterado desde el siglo VIII, y se
  marcan `alta`;
* las **seis aclamaciones** de Cuaresma (*Glória et laus tibi, Christe*…) van
  marcadas `media`, con un **REVISAR** explícito: la correspondencia
  castellano-latín se ha tomado del uso del *Ordo lectionum Missae*, pero no se
  ha podido cotejar contra un ejemplar;
* las **dos últimas** (*Magna et mirabília ópera tua* y *Salus et glória et
  virtus*) son Ap 15,3b y Ap 19,1, así que además se contrastan con la Vulgata.

Se buscó en el corpus de Divinum Officium, que ya se usa para la acentuación
(§9.1), pero no trae las antífonas «O» en el subconjunto clonado y su Misal es
anterior a 1962, así que tampoco cubre las aclamaciones. Queda apuntado como lo
primero que revisar de este capítulo.

### 11.3 Elegir copia: contando lo que importa

Varias páginas repiten el mismo anexo una vez por ciclo, y **no son idénticas**.
La primera versión se quedaba con la que más párrafos traía, que es fácil de
contar y no dice nada. La regla buena es **cuántas citas normaliza**:

    aclamaciones de Cuaresma   70705AleluyaCuaresma 16/17 · 1017AclamCU 15/17 ·
                               2019AclamCU 15/17 · 30171AclamCU 0/0
    aleluya del T.O.           400aleluyaTO 45/45 · 3068 44/45 · 1068 44/45 ·
                               2068 44/45

Tres de las cuatro copias de Cuaresma escriben «Am 5,» sin el versículo, y la
del leccionario VII escribe «Am 5, 14». Contando párrafos ganaba una copia con
la errata; contando citas que se entienden, gana la buena.

### 11.4 El índice de textos, y por qué vale más como testigo

Se construye **de `index_master.json`**, no de la tabla del sitio: la tabla
existe en cuatro de los cinco leccionarios y la nuestra cubre las 3290 lecturas
ya auditadas. **1949 pasajes en 2670 lugares**, en orden canónico —el de los
marcadores del PDF de la Vulgata, no el alfabético de `Siglas.docx`— y con
enlace y número de página a cada celebración.

Eso deja la tabla del sitio libre para lo que de verdad vale: **ser un testigo
independiente**. La tabla y las páginas de cada día son dos listados distintos
del mismo libro, escritos por separado, así que cotejarlos encuentra lo que
ninguno de los dos declara.

| | |
|---|---:|
| citas de las tablas del sitio | 2210 |
| casan con nuestro índice | **2148 (97,2 %)** |
| la cita de la tabla no se entiende | 19 |
| discrepan | 42 |

Las 42 son casi todas erratas de la propia tabla, del mismo tipo que ya
conocíamos (§7.5): cifras partidas o comidas —`1 R 3,5.7-1` por `3,5.7-12`,
`Mc 8,11-1.3` por `8,11-13`, `Sal 16,1.56.8ab.15` por `1.5-6.8ab.15`—. Están
listadas una a una en `data/indice_textos_qa.txt`.

Dos detalles de lectura que valieron 33 discrepancias falsas: la tabla escribe
el salto de capítulo con **dos guiones** (`Éxodo 14, 15--15, 1`) donde el
formulario usa raya, y usa **nombres cortos** (`Romanos`) que ningún formulario
usa. Lo segundo se resuelve añadiendo alias, pero **sólo cuando la última
palabra del nombre identifica un único libro**: «reyes» vale para cuatro, así
que queda fuera y su cita se declara no entendida en vez de adjudicársela a uno
al azar. Y se hace en `17_indice_textos.py`, no en `3_normalize_refs.py`:
aflojar el emparejamiento del leccionario para que le sirva a una tabla es
cambiar por comodidad lo que ya está comprobado.

### 11.5 Tres errores nuestros que el cotejo sacó, y el control que los cierra

Pero tres no eran de la tabla. Eran **nuestros**, y los tres silenciosos:

1. **`2024BPAD02.html` — el peor.** El sitio escribe «Lectura de la primera
   carta **de** apóstol san Juan 5, 1-6», sin la *l*. Ese nombre no casa con
   ningún alias, así que el emparejamiento por el nombre más largo se quedó con
   **«Juan»** —el evangelio— y el leccionario imprimía **Jn 5,1-6**, la piscina
   de Betesda, donde toca **1 Jn 5,1-6**. En el Domingo II de Pascua del ciclo
   B. Un domingo. Ni un fallo, ni un recuento descuadrado, ni un versículo
   ausente: el texto equivocado, en silencio.
2. **`4081ITOX14.html`** — «42, 5-7.**1 7**-24a», con el 17 partido por un
   espacio: salían el versículo 1 y los 7-24a en vez de los 17-24a.
3. **`4147ITOX25.html`** — «Tobías 13, 2. 4. 6. 7. 8 **(R.:)1a**», con el
   paréntesis mal cerrado, que se comía el versículo 8.

Los tres, corregidos en `data/citation_overrides.csv`, que ya existía para esto.

Y lo que importa más que las tres correcciones: **el primero ya no puede volver
a pasar callando**. `3_normalize_refs.py` lleva un control nuevo, de una línea
de lógica y mucho alcance: *una cita que dice «carta» no puede resolverse en un
evangelio*. Comprobado sobre las 3347 citas: el de `2024BPAD02` era el único.

### 11.6 Un cuarto hallazgo, de codificación

Al leer los anexos apareció que **5 de las 757 páginas declaran `iso-8859-1` y
traen bytes cp1252**: 0x97 y 0x96, las rayas de diálogo de «—dice el Señor—».
En iso-8859-1 esos bytes son caracteres de control invisibles, así que la raya
**desaparecía sin dar ningún error**. Son 17 apariciones y afectaban sólo al
castellano —el latín viene del PDF—, pero el arreglo es una palabra: cp1252
coincide con iso-8859-1 en todo lo demás, de modo que las otras 752 páginas se
leen exactamente igual. Corregido en `2_parse_readings.py` y en el parser nuevo.

### 11.7 Lo que sigue faltando, acotado

**Tres páginas que el origen no ha llegado a servir nunca**: los versículos del
Aleluya de las ferias de Navidad después de la Epifanía y los de las ferias
pascuales antes y después de la Ascensión. No es el problema de los espacios en
el nombre que suponía §7.7 —`7003Aleluya_Navidad_antes de Epifania.html`, que
también los lleva, sí está—: es el bloqueo del origen de §2.7, que hoy rechaza
incluso páginas que ya tenemos en caché. Tampoco están en Wayback.

Se reintentan con una orden, y **cada documento lo declara al final de sus
apéndices** en vez de callarlo:

```bash
python src/1_crawl.py --anexos
```

Lo demás que queda abierto aquí:

- **Las seis aclamaciones marcadas `media`** (§11.2): lo primero que revisar.
- **`2019BFDORA.html`**: la tabla del sitio da `Jn 12,12-16` como evangelio
  alternativo de la procesión del Domingo de Ramos del ciclo B, y la página no
  lo trae. No se ha inventado; queda anotado.
- **`1031TFDOPE` y `2031TFDOPE`**: la tabla cita el salmo de la Vigilia de
  Pentecostés con `35c` y la página lo omite. Aquí manda la página, y la
  divergencia queda en el informe.
- **La secuencia** *Victimæ paschali laudes*: las tres entradas de «Secuencia:»
  del Domingo de Pascua siguen sin texto, porque no es cita bíblica. Con la
  tabla fija que ahora existe, añadirla es una fila.

### 11.8 Ficheros nuevos y cómo se ejecuta

```
src/16_parse_anexos.py    cache -> data/anexos.json + anexos_index.json
src/17_indice_textos.py   index_master -> data/indice_textos.json + el cotejo

data/anexos.json                  los anexos tal como se leen
data/anexos_index.json            una fila por cita, en el formato de index_master
data/anexos_latin_fijo.csv        los 15 textos que no son Escritura (editable)
data/anexos_readings_latin*.json  el latin resuelto, por fuente
data/anexos_qa.txt                el informe de los anexos
data/indice_textos.json           1949 pasajes, 2670 lugares
data/indice_textos_qa.txt         el cotejo contra las tablas del sitio
```

```bash
python src/16_parse_anexos.py
python src/5_resolve.py --anexos                  # y --fuente nova
python src/17_indice_textos.py
python src/8_render.py --anual                    # los apendices ya entran
python src/9_docx.py  --anual
python src/15_app_data.py
```

`8_render.py` y `9_docx.py` los incorporan **por omisión** al final de cada
documento, con su entrada en el índice y su número de página; `--sin-anexos` y
`--sin-indice-textos` los quitan. En la app son una sección más —«APÉNDICES»—,
de modo que el índice, el lector y el buscador los tratan como a cualquier día,
sin que la app tenga que saber que existen.

Y el buscador de la app gana de paso el índice de textos sin interfaz nueva:
cada lectura lleva ahora su cita como la escribe el leccionario y el nombre
castellano del libro, y la búsqueda casa por palabras cuando la frase entera no
aparece. Escribir **«salmo 121»** devuelve los siete lugares donde se canta.

---

## 12. Los leccionarios que faltaban: V, VI, VIII y IX

La decisión 8 del §6 los dejaba «para después». Esto es ese después. El sitio de
Koinonía publica **nueve** leccionarios, no cinco: `menu/menu0.js` los enumera y
el frameset de cada uno declara su página índice (`texto/500indice.html`,
`6000indice.html`, `8000indice.html`, `9000INDICE.html`).

| | Contenido | Formularios | Lecturas | Versículos |
|---|---|---|---|---|
| **V** | Propio y Común de los Santos | 230 | 1251 | 6896 |
| **VI** | Misas por diversas necesidades y votivas | 67 | 1129 | 6926 |
| **VIII** | Misas rituales y de difuntos | 35 | 891 | 5594 |
| **IX** | Misas con niños | 53 | 368 | 2378 |

El leccionario entero queda en **6929 lecturas y 43 347 versículos latinos**,
frente a las 3347 lecturas de los cinco primeros.

### 12.1 El origen dejó de responder, y el sitio seguía en pie

Al empezar, `servicioskoinonia.org` ya no aceptaba conexiones desde esta red:
no es un 403 ni un 500, es que **el saludo TCP no obtiene respuesta** (`curl`
agota el tiempo; comprobado también con `http`, con `www.` y con otro
User-Agent). Wayback Machine tiene de esos cuatro leccionarios **64 páginas de
367** — la CDX API sobre `/leccionario/` devuelve 405 URLs en total—, y ni
`menu5.js` ni `texto/500indice.html` están archivados. Con eso no se hace un
leccionario.

El sitio, en cambio, **sí estaba en pie**: responde a través de un proxy de
lectura. De ahí `src/1b_crawl_proxy.py`, que baja las páginas por ese camino y
las deja en `cache/texto` **con la misma codificación de byte** (cp1252) que las
757 que ya había, de modo que `2_parse_readings.py` no distingue unas de otras.
367 de 367, sin un fallo.

### 12.2 Lo que estos cuatro tienen y los cinco primeros no

**El día del mes y el grado.** El santoral va ordenado por fechas, y la fecha
(`p.fecha`) y el grado (*Solemnidad*, *Fiesta*, *Memoria*, *Memoria libre*) son
parte del encabezamiento, no un adorno. Ahora se recogen y se imprimen bajo el
nombre de la celebración. De paso aparecen también donde ya estaban en los
leccionarios I–III y se perdían: Epifanía, Corpus, el Sagrado Corazón.

**La remisión al Común.** Casi todas las memorias llevan una línea —«Del Común
de pastores»— junto a sus lecturas propias, y **nueve de ellas no tienen otra
cosa**: esa línea es todo su formulario. Como no dan ninguna lectura, no
generaban ninguna fila en el índice maestro y se habrían caído del documento,
dejando nueve días del año en blanco sin decir por qué. `2_parse_readings.py`
las escribe en `data/remisiones.json` y la composición les da su entrada de
índice y su rúbrica.

**Los repertorios.** En los Comunes y en las misas rituales, votivas y por
diversas necesidades el libro no dice «primera lectura»: ofrece un repertorio
agrupado por Testamento —«LECTURAS DEL ANTIGUO TESTAMENTO», «SALMOS
RESPONSORIALES», «EVANGELIOS»— y numerado, y quien celebra elige. Sin reconocer
esas cabeceras, **2000 citas de los leccionarios VI y VIII quedaban sin tipo**, y
—peor— la sección anterior se quedaba pegada: 498 evangelios salían rotulados
«salmo responsorial». Con ellas reconocidas, los tipos nuevos son
`LECTIO VETERIS TESTAMENTI` y `LECTIO NOVI TESTAMENTI`, y cada opción lleva su
número, que es como la cita el libro (`EVANGELIUM 3`).

**Un índice escrito de otra manera.** El del leccionario V mete el mes entero en
un solo `<p>`, una celebración por línea separada por `<br>`; tomando solo el
primer enlace de cada párrafo se perdían diecisiete de cada dieciocho. El VIII
usa la misma clase CSS para sus dos niveles de cabecera y los distingue solo por
la sangría. El IX mete la cabecera dentro de un `<span>`. Y un enlace del V
apunta a un `.htm`, no a un `.html`. Los cinco índices antiguos se siguen
reconstruyendo exactamente igual: 70 / 71 / 70 / 410 / 132 entradas.

### 12.3 Catorce erratas del sitio, corregidas a mano

Quedaron catorce citas que ninguna regla podía resolver, todas erratas del
propio sitio, y están en `data/citation_overrides.csv` con su razón:

* `Mi 16, 18` por `Mt 16, 18` (4 veces): es «Tú eres Pedro», el aleluya de los
  papas, y Miqueas no tiene capítulo 16.
* `1 Jn 13, 34` por `Jn 13, 34`: la primera de Juan tiene cinco capítulos, y el
  versículo impreso es «Un mandamiento nuevo os doy».
* `Salmo 84` por `Salmo 48`: el texto impreso es «Oíd esto, todas las naciones»
  (*Audite hæc, omnes gentes*), y el 84 no llega al versículo 17.
* `Sal 84, 15` por `Sal 84, 13`: el 84 tiene catorce versículos, y el impreso
  («El Señor nos dará la lluvia») es el 13.
* «Lectura del santo evangelio según san 16, 24-27», sin evangelista: el texto
  es «El que quiera venirse conmigo», que es Mateo.
* `Aleluya Col 3,` truncada: el versículo impreso es Col 3, 15.
* `Mateo 16, 13-19´` con un acento pegado (2 veces).
* `4, 13-16` a secas: continúa la 1ª de Pedro del párrafo anterior.
* `Salmo 116, 1. 2 (R.: Mc 16, 15` sin cerrar: la antífona se colaba como
  versículos del salmo.
* `Sirácida Cf. 44—49`: un florilegio de seis capítulos. Se reconstruyó párrafo
  por párrafo (Abrahán, Isaac, Moisés, Josué, David, los reyes, Jeremías, los
  doce profetas). Es la única de las catorce que es una **reconstrucción** y no
  una corrección evidente; queda anotada como tal.

Además, dieciocho citas aparecen en páginas que ofrecen un repertorio numerado
sin decir de qué —el Sábado santo del leccionario IX y tres casos sueltos— y el
tipo se deduce de la fórmula que imprime el sitio: «Lectura del santo evangelio
según…» es un evangelio y lo demás es una lectura. Antes salían rotuladas
`DESCONOCIDO`, y eso incluía dos de los leccionarios III y VII que llevaban ahí
desde el principio.

**Resultado: 6929 citas, el 100 % resueltas**, en Clementina y en Nova Vulgata,
con `data/unresolved.csv` vacío en las dos.

### 12.4 Ficheros nuevos y cómo se ejecuta

```
src/1b_crawl_proxy.py        las paginas de los libros 5, 6, 8 y 9
data/targets_extra.json      sus objetivos, sacados de cada pagina indice
data/remisiones.json         las nueve memorias que solo remiten al Comun
```

```bash
python src/1b_crawl_proxy.py --index 5,6,8,9     # los cuatro indices
python src/1b_crawl_proxy.py --fetch             # las 367 paginas
python src/2_parse_readings.py
python src/3_normalize_refs.py
python src/5_resolve.py                          # y --fuente nova
python src/10_toc.py
python src/8_render.py --separados               # y --fuente nova
python src/9_docx.py  --separados --perfil ambos # y --fuente nova
python src/11_pdf.py
```

Nada de esto cambia el documento anual (`--anual`), que va por el calendario y
sigue siendo el de los cinco leccionarios del tiempo: el santoral necesitaría su
propio calendario de fechas fijas y precedencias, y eso es otro trabajo. La app
tampoco los trae, por lo mismo.

> Ese «otro trabajo» es el §13, y ya está hecho: el santoral tiene su calendario
> de fechas fijas y su tabla de precedencias, y la app trae V, VI y VIII. El
> documento anual sigue siendo el de los leccionarios del tiempo.

---

## 13. El santoral y la precedencia: qué se lee **cada fecha**

Fecha: 2026-09-29.

Hasta aquí el proyecto sabía qué se lee cada día del año **litúrgico** y qué
fecha civil le toca a cada uno (§10.1), pero el calendario iba sólo por el
tiempo. Los leccionarios V, VI y VIII existían como documento (§12) y no
entraban en la app, y el §10.6 lo declaraba como lo único que le faltaba para
ser el libro completo. Esta fase lo cierra.

Las tres rúbricas que aportaste hacen tres trabajos distintos, y conviene no
confundirlos:

| Fuente | Qué aporta | Dónde acaba |
|---|---|---|
| **Calendario de celebraciones** (*Calendario general romano y latinoamericano*) | qué se celebra cada día del año y con qué grado | `data/santoral.csv` |
| **Tabla de los días litúrgicos** (Normas universales, n. 59) | los trece rangos de precedencia | `data/tabla_dias_liturgicos.csv` y el motor |
| **Tabla de celebraciones movibles** | Ceniza, Pascua, Ascensión, Pentecostés, Corpus y Adviento, año por año | **no** se usa como dato: se usa como **verificación** |

Lo tercero merece explicación. El proyecto ya calcula esas fechas desde §10.1,
así que copiarlas sería cambiar un cómputo comprobado por un teclear. Lo que sí
vale es **cotejar**, y por eso la tabla se transcribe entera —erratas incluidas—
a `data/tabla_celebraciones_movibles.csv` y se usa de testigo.

**Doce años (2016–2027) × once datos = 132 cotejos, de los que cuadran 126.**
Los seis que no están **todos en el último bloque de la tabla impresa**, y son
erratas suyas:

* **La Ceniza de 2024.** La tabla imprime el 13 de febrero. La Pascua de 2024
  es el 31 de marzo, la misma que la de 2013, y 2013 sí tuvo la Ceniza el 13;
  pero 2024 es bisiesto, y restar 46 días cae en el **14**. La fila está
  copiada de la de 2013 sin contar el 29 de febrero. De ahí salen otras dos
  diferencias de esa misma fila: el último día y la última semana del tiempo
  ordinario antes de Cuaresma.
* **Los ciclos de 2024 y 2025, cambiados entre sí** (imprime C-A donde toca
  B-C, y B-C donde toca C-A), y el de **2027 impreso «C-D»**, cuando no existe
  un ciclo dominical D. La serie es regular y correcta en los ocho años
  anteriores y en 2026.

Es un buen resultado en los dos sentidos: confirma el cómputo donde el impreso
está bien, y lo encuentra donde el impreso está mal. Y confirma de paso lo más
delicado del §10.1, el **salto del tiempo ordinario**: la tabla dice que en 2026
se va de la semana 6 a la 8, que es exactamente lo que sale de contar hacia
atrás.

### 13.1 Dos páginas que faltaban, y de dónde salieron

El PDF del calendario trae diez páginas y **doce meses no caben en diez**: el
escaneo se saltó las páginas XXVI y XXVII, es decir **agosto y septiembre
enteros**. No se han inventado ni se han copiado de otro calendario: están en el
propio PDF, en el **calco del reverso**.

El papel es fino y la tinta de la página de atrás se transparenta, invertida,
sobre la que sí está escaneada. Espejando horizontalmente la página de julio se
lee agosto, y espejando la de octubre se lee septiembre. Con un estirado del
rango claro (los grises entre 150 y 232) el calco queda legible entero.

Las 43 celebraciones que salen de ahí van marcadas `fuente=calco` en
`data/santoral.csv`, y además se cotejan una a una contra el leccionario V, que
las trae todas. **Están señaladas, no escondidas**, por si quieres verificarlas
contra un ejemplar en papel.

### 13.2 El emparejamiento con el leccionario V

Cada celebración del calendario necesita sus lecturas, y salen del leccionario V
(propio y común de los santos), que ya estaba parseado y resuelto al latín
(§12). El emparejamiento va por fecha y, dentro de la fecha, por las palabras
significativas del nombre; se admite un día de diferencia, y no por capricho:

- el leccionario pone a **san Pedro Claver** el 8 de septiembre y el Calendario
  latinoamericano el 9;
- **san Isidoro** es memoria libre el 4 de abril en el Calendario general y
  fiesta el 26 en el propio de España, que es el que publica Koinonía.

Resultado: **194 de 195 celebraciones de fecha fija emparejadas con su propio.**
La única que se queda sin él es **Nuestra Señora de Guadalupe**, que no está en
el leccionario español; toma el Común de santa María Virgen, y queda anotado.

Tres emparejamientos que el nombre no resuelve están en
`data/santoral_enlaces.csv`, editable: *Isidoro* (fechas distintas), *Primeros
mártires de la Iglesia de Roma* (el leccionario los titula «Protomártires») y
*Eduviges* (el leccionario escribe «Eduvigis»).

**Un bloque repetido, cazado sin heurística.** El sitio pega san Simón y san
Judas dentro del formulario de san Felipe y Santiago, y ya tienen el suyo
propio. Se detecta con lo que el propio nombre del fichero dice: `5058TA0503`
codifica el 3 de mayo, y ese bloque dice «28 de octubre». Si el bloque y el
fichero no dicen la misma fecha, el bloque no es de esa página.

### 13.3 Los grados: quién manda cuando las dos fuentes discrepan

El leccionario V de Koinonía es el **de España** y el calendario que aportaste
es el **general romano y latinoamericano**. Discrepan en el grado de **15 de las
194** celebraciones emparejadas: Santiago es solemnidad en España y fiesta en el
Calendario general; santa Rosa de Lima es fiesta en América y memoria libre en
España; santa Teresa de Jesús, san Benito y santa Catalina de Siena son fiesta
en España y memoria en el general.

**Manda el calendario que aportaste**, porque es el que fija qué se celebra, y
las quince discrepancias están listadas una a una en `data/santoral_qa.txt`. El
leccionario sólo pone las lecturas.

Quedan además **19 formularios del leccionario V con fecha que este calendario
no trae** (san Fructuoso, san Ildefonso, san Isidro labrador, san Fernando, el
Pilar, santa Eulalia de Mérida…, casi todos del propio de España). No se
colocan en ninguna fecha —sería meter el santoral español en un calendario
latinoamericano— pero **siguen accesibles por el índice**, en una sección
aparte.

### 13.4 La concurrencia, que es lo que de verdad pedía la Tabla

Las trece líneas de la Tabla de los días litúrgicos se traducen a un rango por
celebración, y con eso cada fecha se resuelve sola:

1. de las que concurren se celebra **la de rango superior**;
2. la **solemnidad impedida se traslada** a la fecha más cercana sin ninguna
   celebración de los números 1 al 8, y **las demás se omiten aquel año**;
3. las **memorias libres pueden celebrarse también** en los días del número 9
   (ferias del 17 al 24 de diciembre, octava de Navidad, ferias de Cuaresma);
4. las **memorias obligatorias que caen en feria de Cuaresma se rebajan** a
   memorias libres.

Sobre 2024–2060: **13 510 fechas**, **0 días sin celebración**, y **24
solemnidades trasladadas**. Los traslados son la comprobación que más dice,
porque son verificables uno a uno contra cualquier ordo:

| | |
|---|---|
| 2024-03-25 → 2024-04-08 | la Anunciación cae en Lunes santo; va al lunes siguiente a la octava de Pascua |
| 2024-12-08 → 2024-12-09 | la Inmaculada cae en Domingo II de Adviento |
| 2027-03-25 → 2027-04-05 | la Anunciación cae en Jueves santo |
| 2028-03-19 → 2028-03-20 | san José cae en Domingo III de Cuaresma |

Y el reparto de la concurrencia, que es lo que se ve al usar la app: **7693 días
con una sola celebración, 5268 con dos, 516 con tres y 33 con cuatro.**

Dos decisiones que no son obvias y conviene dejar escritas:

* **El formulario del tiempo nunca se esconde.** Aunque un año no se celebre
  —el Domingo XXXI cuando cae Todos los Santos, la feria bajo una solemnidad—,
  su lectura es la del ciclo, y enseñarla es para lo que existe este proyecto.
  Va el último y **marcado «no se celebra»**, que es distinto de ofrecerlo como
  si tocara. Lo que sí se omite de verdad es lo del santoral, porque así lo
  manda la Tabla: la Visitación desaparece el año en que el 31 de mayo es la
  Santísima Trinidad, y la app lo dice.
* **La Misa crismal no compite con la Cena del Señor.** Es la misa de la mañana
  del mismo Jueves santo, así que comparte su rango en vez de salir «impedida».

### 13.5 La memoria y la feria: la única preferencia que es del lector

Aquí hay una tensión real entre dos libros, y no se resuelve sola:

* la **Tabla de los días litúrgicos** pone la memoria (n. 10–12) por encima de
  la feria del tiempo ordinario (n. 13);
* el ***Ordo lectionum Missae*** (n. 82) manda seguir la **lectura continua de
  la feria** salvo que el santo tenga lecturas propias de verdad.

Las dos cosas son ciertas: la primera habla de qué se celebra y la segunda de
qué se lee. Como el leccionario de Koinonía no marca cuáles de sus lecturas son
«propias de verdad», no hay forma de decidirlo por los datos. Así que **las dos
opciones se ofrecen siempre** y lo que cambia es cuál sale primero: un ajuste de
la app, con la Tabla por omisión. Está explicado dentro de la propia app, no
sólo aquí.

### 13.6 Lo que ha cambiado en la app

* Entran los leccionarios **V, VI y VIII** —1077 formularios frente a 754— con
  su índice: propio de los santos por meses, otros formularios del propio,
  común de los santos, misas por diversas necesidades y votivas, y misas
  rituales y de difuntos. **El IX (misas con niños) se deja fuera** a propósito:
  no es un formulario del año y doblaría las opciones de cada día sin que nadie
  lo pida.
* La cabecera tiene ahora **dos filas de opciones**: arriba las celebraciones
  del día en orden de precedencia, con su grado debajo del nombre y en trazo
  discontinuo lo que no se celebra; abajo los formularios de la elegida (el
  propio, sus comunes, o los tres ciclos de un domingo).
* Una línea de nota dice lo que no cabe en un botón: de dónde se trasladó una
  solemnidad, por qué una memoria obligatoria va como libre en Cuaresma, y qué
  se omite ese año.
* El **color litúrgico** ya no es sólo el del tiempo: el santoral trae el suyo
  (rojo en los mártires, los apóstoles, los evangelistas y la Santa Cruz).
* Los días **26, 27 y 28 de diciembre** ya no están en blanco: son san Esteban,
  san Juan y los santos Inocentes, que es lo que el §10.4 declaraba como hueco.

La app pasa de 6,2 a **13,4 MB**. El service worker guarda primero lo
imprescindible y la segunda versión latina por detrás, para que instalarla no
dependa de bajar el doble de golpe con mala conexión.

### 13.7 Del escritorio al teléfono, sin pasos manuales

La app estaba hecha pero no publicada: había que subirla a mano cada vez. Ahora
la cadena es una orden:

```
 carpeta del escritorio  ──.\publicar.ps1──▶  GitHub  ──Actions──▶  GitHub Pages
                                                                        │
                    la app instalada pregunta si hay versión nueva ◀─────┘
                    al abrirse y al volver a primer plano, y se recarga
```

`publicar.ps1` rehace el calendario y los datos de la app y los sube;
`.github/workflows/publicar-app.yml` republica `app/` en cada empujón a `main`;
y `app.js` pregunta por la versión nueva al arrancar, al volver la app a primer
plano y al recuperar la conexión, de modo que el teléfono se pone al día solo.
Los pasos de la primera vez (crear el repositorio, encender Pages, instalar la
app) están en `README.md`.

El `.gitignore` deja fuera `cache/` (60 MB), `out/` (520 MB) y los JSON grandes
que se regeneran con una orden, no por el tamaño en sí, sino porque cambian
enteros cada vez y git guarda cada versión completa. La primera subida son
**28,8 MB**.

### 13.8 Ficheros nuevos y cómo se ejecuta

```
src/18_santoral.py            santoral + Tabla de precedencia -> el calendario
                              completo, con sus parches regionales

data/santoral.csv             el Calendario general romano y latinoamericano
                              (editable; 196 celebraciones)
data/santoral_rango.csv       los rangos que el grado no da (las fiestas del
                              Senor, que son n. 5 y no n. 7)
data/santoral_enlaces.csv     los emparejamientos que el nombre no resuelve
data/tabla_dias_liturgicos.csv  las trece lineas de la Tabla, para consulta
data/tabla_celebraciones_movibles.csv  la tabla del misal transcrita, de
                              testigo (no es fuente de datos)
data/calendario_completo.json fecha -> celebraciones ordenadas (2,1 MB)
data/santoral_qa.txt          el informe y las comprobaciones

.github/workflows/publicar-app.yml  publica app/ en GitHub Pages
publicar.ps1                  rehacer los datos y subirlos, en una orden
README.md                     como se monta la cadena escritorio -> telefono
.gitignore                    lo que no va al repositorio, y por que
```

```bash
python src/18_santoral.py       # y luego
python src/15_app_data.py
```

### 13.9 Lo que queda abierto

- **Agosto y septiembre vienen del calco** (§13.1). Están marcados y cotejados
  contra el leccionario, pero conviene verificarlos contra el papel.
- **El calendario es el de esta edición**, anterior a 2000: el Inmaculado
  Corazón de María todavía es memoria libre (hoy es obligatoria), santa María
  Magdalena es memoria (hoy fiesta) y el 29 de julio es sólo santa Marta (hoy
  Marta, María y Lázaro). Cambiarlo es editar tres líneas de
  `data/santoral.csv`.
- **Las solemnidades y fiestas propias** (números 4 y 8 de la Tabla: el patrono
  del lugar, la dedicación de la iglesia propia, el titular) no están, porque
  dependen de la diócesis y de la parroquia. La arquitectura las admite: son
  filas más en `santoral.csv` con su rango.
- **Las lecturas «propias de verdad»** (§13.5): si algún día se coteja el
  leccionario contra el *Ordo lectionum Missae* de 1981, se sabría cuáles lo
  son y la preferencia dejaría de ser un ajuste para ser un dato.
