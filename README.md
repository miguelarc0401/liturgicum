# Lectionarium — el leccionario romano y el oficio divino

Dos libros litúrgicos, hechos con el mismo método y servidos por la misma app:

* el **leccionario** completo en latín (Vulgata Clementina y Nova Vulgata), en
  tres formas: **documentos** (DOCX y PDF maquetados como libro), un **índice
  maestro de citas** y la app; y en la app, además, **la misa entera en
  castellano** —el formulario de arriba abajo, con el Ordinario intercalado y
  lo que las rúbricas dejan elegir—, en la traducción litúrgica que se usa en
  México, cosechada por [`Missale/`](Missale/LEEME.md) del misalito mensual de
  2018 a 2026, con el Misal latino de 2002 al lado;
* la **Liturgia de las Horas** en la traducción litúrgica que se usa en
  México, con sus siete horas, extraída y ordenada por
  [`Breviarium/`](Breviarium/LEEME.md), que es un módulo aparte con su propia
  fuente y su propio proceso;
* el **devocionario**: 461 oraciones latinas del *Thesaurus Precum
  Latinarum*, puestas en la ortografía de los libros litúrgicos —con su
  jota, su ligadura y su acento— por [`Enchiridion/`](Enchiridion/LEEME.md),
  con el castellano de cada una donde se ha podido verificar de dónde sale.

Cómo está hecho y por qué, paso a paso, en [Vision.md](Vision.md); lo del
oficio divino, en [Breviarium/LEEME.md](Breviarium/LEEME.md).

---

## La app

`app/` es una PWA —**Liturgicum**— : una página web que se instala en la
pantalla de inicio y lleva los dos libros dentro, así que abre sin conexión.
Al abrirse pregunta cuál de los dos se quiere, y quien siempre va al mismo lo
dice una vez en Ajustes.

Para verla en el ordenador:

```bash
python -m http.server 8765 --directory app
```

y abrir <http://localhost:8765>.

Para instalarla en el teléfono hay que servirla por `https` una vez. Eso es lo
que hace GitHub Pages, y es de lo que trata el resto de este documento.

---

## Cómo se actualiza el teléfono cuando tocas algo aquí

La cadena es corta y cada eslabón es automático menos el primero:

```
 carpeta del escritorio  ──.\publicar.ps1──▶  GitHub  ──Actions──▶  GitHub Pages
                                                                        │
                    la app instalada pregunta si hay versión nueva ◀─────┘
                    al abrirse y al volver a primer plano, y se recarga
```

En la práctica: **editas, ejecutas `.\publicar.ps1`, y el teléfono se pone al
día solo** en cuanto vuelvas a abrir la app (con conexión; sin ella sigue
funcionando con lo último que tuviera).

### La primera vez

1. **Crear el repositorio en GitHub.** En <https://github.com/new>, con el
   nombre que quieras (aqui, `liturgicum`). *Sin* README, sin
   `.gitignore` y sin licencia: la carpeta ya los trae.

   > GitHub Pages es gratis en repositorios **públicos**. En privados hace
   > falta cuenta de pago. Lo que se publica son textos bíblicos en latín y
   > castellano, ya públicos, y el código de este proyecto.

2. **Enlazar esta carpeta con él.** En PowerShell, dentro de la carpeta:

   ```powershell
   git init -b main
   git config user.name  "Tu nombre"
   git config user.email "tu@correo"
   git add -A
   git commit -m "Primera version"
   git remote add origin https://github.com/TU-USUARIO/liturgicum.git
   git push -u origin main
   ```

3. **Encender GitHub Pages.** En el repositorio: *Settings ▸ Pages ▸ Build and
   deployment ▸ Source* → **GitHub Actions**. No hay que elegir carpeta: lo
   dice el flujo de trabajo [`.github/workflows/publicar-app.yml`](.github/workflows/publicar-app.yml),
   que publica `app/` en cada empujón a `main`.

4. **Instalarla en el teléfono.** Abrir en Chrome
   `https://TU-USUARIO.github.io/liturgicum/` y usar *Añadir a la pantalla de
   inicio*. A partir de ahí no necesita ni servidor ni conexión.

### Cada vez que cambies algo

```powershell
.\publicar.ps1
```

(o doble clic en `publicar.bat`, si PowerShell no deja correr `.ps1`).
Trae antes lo corregido desde el teléfono, rehace el calendario y los datos
de la app, los sube, y GitHub Pages se republica en un par de minutos. Con `-Mensaje "..."` le pones tu propio texto
al commit, y con `-SoloConstruir` rehace los datos sin subir nada.

Si sólo tocas las tablas editables (`data/santoral.csv`, los `*_overrides.csv`)
eso es todo lo que hay que hacer. Si tocas el texto latino o el índice de
citas, hay que rehacer antes las fases que correspondan (ver
[Vision.md](Vision.md), §7.4).

> **Si la publicación sale en rojo, no le des a «Re-run jobs».** Reintentar
> vuelve a subir el artefacto dentro de la misma ejecución, quedan dos con
> el mismo nombre y el despliegue falla sin saber cuál publicar
> (*Multiple artifacts named "github-pages"…*). Para volver a publicar sin
> haber cambiado nada, usa **«Run workflow»** en la pestaña *Actions*, que
> abre una ejecución nueva y limpia. El flujo está partido en dos trabajos
> —*construir* y *publicar*— precisamente para que reintentar el fallido
> reintente sólo el segundo, que no sube nada.
>
> Y si el sitio sigue viéndose bien aunque la ejecución esté en rojo, es que
> el despliegue anterior sigue en pie: no se ha perdido nada.

### Corregir una errata desde la app

Si al leer ves algo mal escrito —una palabra de una lectura, de un himno, de
una oración—, se corrige en la propia app, donde se lee: se selecciona el
texto, sale **Corregir** al lado, se escribe como debe quedar, «Buscar dónde
está» dice en qué sitios de los datos está, y «Guardar la corrección» lo
cambia. La pastilla **Erratas**, abajo a la izquierda, lista las corregidas
y deja deshacerlas. Se puede desde dos sitios:

**Desde el teléfono, sin el ordenador.** Una vez, en el teléfono, se le da a
la app una llave de GitHub (abajo, «La llave del teléfono»). Desde entonces,
en ese teléfono, se deja el dedo sobre la palabra y se toca «Corregir». Lo
corregido se ve al momento en el teléfono, y se manda a GitHub —sin
conexión, se queda esperando y sale sola cuando vuelve—. Allí el proceso
**Erratas del teléfono** (`.github/workflows/erratas.yml`) la aplica a los
datos con el mismo programa que el ordenador y vuelve a publicar la app. La
pastilla «Erratas» dice cómo va cada una: en GitHub, aplicada, o por qué no
se pudo.

**Desde el ordenador.** Doble clic en **`editar.bat`** (o `python
Enchiridion/src/editar.py`). Se abre una ventana negra —es el editor;
mientras esté abierta, la app se puede corregir, y al cerrarla se para— y la
app en el navegador, en `http://127.0.0.1:8780/`. Con un doble clic se
selecciona una palabra. Lo corregido cambia los datos de esta carpeta al
momento, y llega a los demás al publicar.

Cada corrección se apunta en `data/fe_de_erratas/`, una por fichero —el
trozo como estaba, como queda y en qué sitios—, y cada fase que rehace los
datos la vuelve a poner antes de escribir (`src/erratas.py`), así que no se
pierde al rehacer. Si un día la fuente cambia y una errata ya no se
encuentra, la fase lo dice con un AVISO.

#### Cómo llega a los demás

* **Lo corregido en el teléfono, solo.** GitHub la aplica en un minuto y
  pone en marcha «Publicar la app»; en otro par de minutos está en GitHub
  Pages. Los teléfonos de todos —la web instalada y el APK— lo ven la
  próxima vez que abren la app o vuelven a ella, como cualquier otra
  publicación: la firma de los datos ha cambiado y se recargan una vez.
  Nada que hacer en el ordenador.
* **Lo corregido en el ordenador, al publicar:** doble clic en
  **`publicar.bat`** (corre `publicar.ps1` sin pedirle nada a la política de
  ejecución de Windows). Antes de rehacer nada trae de GitHub lo corregido
  desde el teléfono, de modo que lo uno y lo otro no se pisan nunca.

#### La llave del teléfono

Es un «token» de GitHub que sólo deja escribir en este repositorio. Se hace
una vez, desde el teléfono o desde el ordenador:

1. Entra en <https://github.com/settings/personal-access-tokens/new> (GitHub
   › foto › Settings › Developer settings › Personal access tokens ›
   Fine-grained tokens › Generate new token).
2. **Token name:** «Liturgicum, erratas desde el teléfono». **Expiration:**
   la más larga que deje; cuando caduque, se hace otra igual.
3. **Repository access:** *Only select repositories* › `liturgicum`.
4. **Permissions** › *Repository permissions* › **Contents: Read and
   write**. Nada más.
5. **Generate token**, y cópiala (empieza por `github_pat_`; GitHub no la
   vuelve a enseñar).
6. En la app del teléfono: **Ajustes › Editor del libro**, pégala y toca
   «Guardar la llave». La app la prueba con GitHub antes de guardarla.

La llave se queda sólo en ese teléfono, y sin ella la app de los demás no
tiene nada de esto. Si pierdes el teléfono, bórrala en la misma página de
GitHub y deja de servir en el acto.

### Lo que la app hace para enterarse

Un service worker guarda la app entera en caché —es lo que la hace funcionar
sin conexión— y por eso no basta con subir los ficheros nuevos: hay que pedirle
que mire. `app/app.js` lo pide al arrancar, al volver la app a primer plano y
al recuperar la conexión; y `app/datos/version.js` lleva una firma de los
propios datos, de modo que cuando los datos cambian el worker tira la caché
vieja y la vuelve a llenar. Al terminar, la página se recarga una sola vez.

---

## Qué hay en cada carpeta

| | |
|---|---|
| `src/` | el proceso, por fases numeradas (ver Vision.md, §7.4) |
| `data/` | las tablas editables a mano y los informes de control de calidad |
| `app/` | la PWA: lo único que se publica |
| `Breviarium/` | la Liturgia de las Horas: su proceso y el libro ya ordenado |
| `Enchiridion/` | el devocionario latino: su proceso, sus tablas y su castellano |
| `out/` | los documentos compuestos (no va al repositorio: son 500 MB) |
| `cache/` | las páginas descargadas (tampoco va: se vuelven a bajar) |

El volcado del sitio de las horas y su corpus intermedio no están ni en
`cache/`: viven **fuera del proyecto**, porque esta carpeta se sincroniza con
la nube y subir 200 MB en cada pasada multiplica por quince lo que tarda la
extracción. Lo dice `Breviarium/src/breviario.py`.

Los tres PDF de rúbricas (*Tabla de los días litúrgicos*, *Tabla de
celebraciones*, *Calendario de celebraciones*) sí van al repositorio: son la
fuente del santoral y de la precedencia, y conviene poder cotejar contra ellos.
