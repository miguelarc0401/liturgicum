# Lectionarium — el leccionario romano en latín

El leccionario completo en latín (Vulgata Clementina y Nova Vulgata), en tres
formas: **documentos** (DOCX y PDF maquetados como libro), un **índice maestro
de citas** y una **app para el teléfono** que funciona sin conexión.

Cómo está hecho y por qué, paso a paso, en [Vision.md](Vision.md).

---

## La app

`app/` es una PWA: una página web que se instala en la pantalla de inicio y
lleva el leccionario entero dentro, así que abre sin conexión.

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
   nombre que quieras (por ejemplo `lectionarium`). *Sin* README, sin
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
   git remote add origin https://github.com/USUARIO/lectionarium.git
   git push -u origin main
   ```

3. **Encender GitHub Pages.** En el repositorio: *Settings ▸ Pages ▸ Build and
   deployment ▸ Source* → **GitHub Actions**. No hay que elegir carpeta: lo
   dice el flujo de trabajo [`.github/workflows/publicar-app.yml`](.github/workflows/publicar-app.yml),
   que publica `app/` en cada empujón a `main`.

4. **Instalarla en el teléfono.** Abrir en Chrome
   `https://USUARIO.github.io/lectionarium/` y usar *Añadir a la pantalla de
   inicio*. A partir de ahí no necesita ni servidor ni conexión.

### Cada vez que cambies algo

```powershell
.\publicar.ps1
```

Rehace el calendario y los datos de la app, los sube, y GitHub Pages se
republica en un par de minutos. Con `-Mensaje "..."` le pones tu propio texto
al commit, y con `-SoloConstruir` rehace los datos sin subir nada.

Si sólo tocas las tablas editables (`data/santoral.csv`, los `*_overrides.csv`)
eso es todo lo que hay que hacer. Si tocas el texto latino o el índice de
citas, hay que rehacer antes las fases que correspondan (ver
[Vision.md](Vision.md), §7.4).

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
| `out/` | los documentos compuestos (no va al repositorio: son 500 MB) |
| `cache/` | las páginas descargadas (tampoco va: se vuelven a bajar) |

Los tres PDF de rúbricas (*Tabla de los días litúrgicos*, *Tabla de
celebraciones*, *Calendario de celebraciones*) sí van al repositorio: son la
fuente del santoral y de la precedencia, y conviene poder cotejar contra ellos.
