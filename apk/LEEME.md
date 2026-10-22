# El APK de Android

La misma app de `app/`, envuelta con [Capacitor](https://capacitorjs.com) para
instalarla en el teléfono como una app de verdad. No es otra copia: el APK
lleva dentro la carpeta `app/` tal cual, y lo poco que tiene que hacer
distinto va en `app.js`, detrás de `enElApk()`. En Chrome esa parte no corre,
y la web de GitHub Pages sigue como estaba.

## Bajarlo e instalarlo

<https://github.com/miguelarc0401/liturgicum/releases/download/apk/liturgicum.apk>

Se abre ese enlace en el teléfono, se baja y se toca. La primera vez Android
pide permiso para instalar apps del navegador («orígenes desconocidos»): se
da para ese navegador y ya. Convive con la app instalada desde Chrome; son
dos apps distintas, cada una con sus ajustes.

## Cómo se pone al día

Hay dos cosas que pueden cambiar, y van por caminos distintos.

**Lo de `app/` —los textos, `app.js`, los estilos—** llega solo, sin volver a
instalar nada. `publicar.ps1` no cambia: al subir a main, el workflow de
GitHub Pages corre `apk/paquete.sh --zip`, que saca una huella de todo
`app/` y arma con ello `paquete.zip` y `paquete.json`, y los publica junto a
la web. El APK pregunta por `paquete.json` al abrirse y al volver a primer
plano; si la huella no es la suya, se baja el zip (unos 16 MB) en segundo
plano con el actualizador de Capgo, y la versión nueva se estrena la próxima
vez que la app arranca o vuelve tras más de un minuto fuera —nunca a media
lectura, ni con la voz sonando—. Si la versión nueva no llegara a arrancar,
el actualizador vuelve solo a la anterior, y esa no se vuelve a bajar hasta
que se publique otra. Todo está en `app.js`, sección «dentro del APK».

**Lo nativo —lo que hay en esta carpeta: Capacitor, los plugins, el icono,
el nombre—** pide un APK nuevo. Al subir un cambio de `apk/`, el workflow
«Compilar el APK» lo compila, lo prueba en un emulador y lo deja en la
release `apk` (el enlace de arriba no cambia). Se baja y se instala encima;
los ajustes y lo bajado se conservan. Al instalar un APK nuevo, el
actualizador tira las versiones que había bajado y arranca con la que trae
el APK, que se pone al día enseguida si hace falta.

El zip no entra en git: 16 MB por publicación se quedarían en la historia
para siempre. Se arma en GitHub Actions y vive sólo en GitHub Pages.

## Lo que todavía no va en el APK

Esta es la primera fase: el esqueleto que abre la app y se actualiza solo.
Dentro del APK la página corre en el WebView de Android, no en Chrome, y al
WebView le faltan tres cosas que la app usa para la voz:

- **la voz del teléfono** (`speechSynthesis`): hay que pasarla al motor de
  voz de Android con un plugin;
- **el botón del volante y los mandos de la pantalla bloqueada**
  (MediaSession): hace falta una pieza nativa, con su notificación;
- **mantener la pantalla encendida** (`wakeLock`): con un plugin.

Piper debería funcionar como en Chrome, pero sigue guardando las voces en la
caché del navegador; la fase siguiente las pasa a archivos de la app, que
Android no borra.

## La llave de firma

Android sólo instala un APK encima de otro si los dos van firmados con la
misma llave. Está en `Llave del APK de Liturgicum`, junto a esta carpeta del
escritorio y **fuera del repositorio** —`publicar.ps1` hace `git add -A` y
se colaría—, con un `LEEME.txt` que dice la clave. OneDrive le hace la
copia. GitHub Actions la tiene en los secretos `APK_LLAVE_BASE64`,
`APK_LLAVE_CLAVE` y `APK_LLAVE_ALIAS`. Si se perdiera, habría que
desinstalar la app y volver a instalarla.

## Lo que hay aquí

- `capacitor.config.json`: el nombre, el identificador
  (`io.github.miguelarc0401.liturgicum`, que no se puede cambiar sin que
  Android lo tome por otra app) y la configuración del actualizador.
  `statsUrl`, `updateUrl` y `channelUrl` van vacíos a propósito: por
  omisión el plugin manda estadísticas y errores a los servidores de Capgo,
  y así no sale nada del teléfono más que la pregunta a GitHub Pages.
- `android/`: el proyecto de Android que genera Capacitor. Lo tocado a mano:
  la firma y el número de versión en `app/build.gradle`, la pantalla de
  arranque (`res/values/styles.xml` y los dos `colors.xml`) y los iconos.
- `iconos.py`: rehace los iconos de Android a partir de los de `app/`. Sólo
  hace falta si cambia el icono.
- `paquete.sh`: la huella y el zip (ver arriba).
- `package.json`: las versiones de Capacitor y de los plugins, fijadas. Las
  dependencias se instalan en GitHub Actions; en el ordenador no hace falta
  ni Node ni el SDK de Android.

Para probar que se baja y estrena una versión publicada, el workflow
«Compilar el APK» tiene, a mano, la opción *probar_actualizacion*: compila
el APK con una huella falsa y mira en el emulador que se baja la de Pages y
que, al volver a abrir, la estrena. Ese APK no va a la release.
