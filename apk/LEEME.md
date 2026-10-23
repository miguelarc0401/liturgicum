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

## La voz en el APK

Dentro del APK la página corre en el WebView de Android, no en Chrome, y al
WebView le faltan las tres cosas en que se apoya la voz de la web. Las pone
el propio APK, con tres plugins suyos que están en
`android/app/src/main/java/.../liturgicum/` y que `MainActivity.java` apunta
al abrir:

- **La voz del teléfono** (`VozPlugin.java`). El WebView no trae
  `speechSynthesis`; `app/nativo.js` monta uno encima del motor de voz de
  Android, con lo mismo que da Chrome, y así la voz de `app.js` sirve igual
  en los dos sitios. Trae una cosa más que Chrome no tiene, `silencio(ms)`:
  con ella `app.js` le da al motor la hora entera de una vez, con el
  silencio de cada sección dentro, y el motor la dice sin que la página
  tenga que despertarse entre una sección y otra. Las voces son las que
  tenga puestas el teléfono en Ajustes de Android.
- **Los mandos y la pantalla apagada** (`VozServicio.java`). Mientras suena
  la voz hay un servicio en primer plano, con su aviso en la barra de
  notificaciones: Android no duerme la app aunque se apague la pantalla. El
  aviso trae los mandos, que salen también en la pantalla de bloqueo, y la
  sesión de medios recibe el botón del volante y el de los auriculares. Para
  que Android le mande esos botones a esta app y no a la radio, el servicio
  hace sonar un audio que no se oye, como el `<audio>` mudo de la web: la voz
  del sistema suena desde el motor de voz, que es otra app.
- **No apagar la pantalla** (`PantallaPlugin.java`), en vez de `wakeLock`.

Y Piper guarda sus piezas en **archivos de la app** (`ArchivosPlugin.java`,
`files/piper/`), no en la caché del navegador: Android no los borra para
hacer sitio. Las baja el teléfono, porque el worker de `piper.js` no puede
hablar con él, y al worker se le dan las direcciones de los archivos ya
bajados.

Todo esto mira primero si el APK trae el plugin (`conPlugin()` en `app.js`):
un APK viejo puede recibir por el actualizador un `app.js` nuevo, y entonces
esa parte sigue como en la web hasta que se instale el APK nuevo.

Cada compilación lo prueba en el emulador (trabajo «voz», `prueba/voz.mjs`):
pone a rezar Laudes con la voz del teléfono, apaga la pantalla y mira que
sigue, toca los botones de medios que manda el volante (pausa, seguir,
siguiente, parar), mira que sale el aviso y que «No apagar la pantalla»
funciona, y baja la voz ligera de Piper a archivos para hacerla hablar desde
ahí. Si algo de eso falla, el APK no va a la release. Usa el APK de
depuración, que es el único que deja mirar la página desde fuera.

**Lo que falta:** al empezar, la voz pide el audio, así que la música que
estuviera sonando se calla; pero lo que pase después no se atiende todavía.
Pausar al entrar una llamada y seguir al colgar está por hacer, porque el
motor de voz y el WebView también suenan y hay que ver en un teléfono de
verdad que no se pisan entre ellos antes de fiarse de esos avisos.

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
  arranque (`res/values/styles.xml` y los dos `colors.xml`), los iconos, los
  cuatro ficheros de la voz y de Piper (ver arriba), y en
  `AndroidManifest.xml` el servicio, sus permisos y la consulta del motor de
  voz, sin la que desde Android 11 la app no lo ve.
- `prueba/voz.mjs`: la prueba de la voz en el emulador (ver arriba).
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
