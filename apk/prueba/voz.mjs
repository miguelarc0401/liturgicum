// La prueba de la voz en el emulador de GitHub Actions (workflow «Compilar
// el APK», trabajo «voz»). No corre en el ordenador: necesita el emulador
// arrancado y el APK de depuración, que es el único que deja asomarse a la
// página por el protocolo de depuración de Chrome.
//
// Hace con el APK lo que se haría en el coche y mira la página por dentro:
// pone a rezar Laudes con la voz del teléfono, apaga la pantalla y mira que
// sigue, toca los botones de medios —los mismos que manda el volante— y baja
// la voz ligera de Piper a archivos de la app para hacerla hablar desde ahí.
// Deja voz-informe.json y unas fotos; si algo de lo que importa falla, sale
// con error.

import { execSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const PAQUETE = 'io.github.miguelarc0401.liturgicum';
const informe = { pasos: [], fallos: [] };
const espera = (ms) => new Promise((r) => setTimeout(r, ms));
const adb = (orden) => execSync('adb ' + orden, { encoding: 'utf8' }).trim();

function apunta(paso, datos, bien) {
  informe.pasos.push({ paso, bien, datos });
  if (!bien) informe.fallos.push(paso);
  console.log((bien ? 'OK   ' : 'MAL  ') + paso + '  ' + JSON.stringify(datos));
}

function foto(nombre) {
  execSync('adb exec-out screencap -p > ' + nombre);
}

/* ---------------------------------------------- asomarse a la página */

async function conecta() {
  let socket = '';
  for (let i = 0; i < 30 && !socket; i++) {
    const m = adb('shell cat /proc/net/unix').match(/@(webview_devtools_remote_\d+)/);
    if (m) socket = m[1];
    else await espera(1000);
  }
  if (!socket) throw new Error('el WebView no abre su depurador');
  adb('forward tcp:9222 localabstract:' + socket);
  let pagina = null;
  for (let i = 0; i < 20 && !pagina; i++) {
    try {
      const lista = await (await fetch('http://127.0.0.1:9222/json')).json();
      pagina = lista.find((p) => p.type === 'page' && /localhost/.test(p.url));
    } catch (_) { /* todavía no */ }
    if (!pagina) await espera(1000);
  }
  if (!pagina) throw new Error('no se ve la página de la app');
  const ws = new WebSocket(pagina.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let n = 0;
  const esperan = new Map();
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && esperan.has(m.id)) { esperan.get(m.id)(m); esperan.delete(m.id); }
  };
  return async function evalua(codigo) {
    const id = ++n;
    ws.send(JSON.stringify({ id, method: 'Runtime.evaluate', params: {
      expression: '(async () => {' + codigo + '})()',
      awaitPromise: true, returnByValue: true } }));
    const r = await new Promise((res) => esperan.set(id, res));
    if (r.result && r.result.exceptionDetails) {
      throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 400));
    }
    return r.result && r.result.result ? r.result.result.value : undefined;
  };
}

/* --------------------------------------------------------------- la prueba */

async function prueba() {
  const evalua = await conecta();
  const estado = () => evalua('return { estado: V.estado, i: V.i, '
    + 'sec: V.guion && V.guion[V.i] ? V.guion[V.i].sec : null, '
    + 'n: V.guion ? V.guion.length : 0 };');

  // las voces del teléfono
  const voces = await evalua(`
    for (let k = 0; k < 40 && !speechSynthesis.getVoices().length; k++)
      await new Promise((r) => setTimeout(r, 500));
    return speechSynthesis.getVoices().map((v) => v.voiceURI + ' ' + v.lang);`);
  apunta('el teléfono da voces', { n: voces.length, voces: voces.slice(0, 8) }, voces.length > 0);

  // Laudes, con una española si la hay y si no con la primera
  await evalua(`
    const v = speechSynthesis.getVoices();
    const es = v.find((x) => /^es/i.test(x.lang)) || v[0];
    if (es) E.cfg.voz = es.voiceURI;
    E.cfg.vozMotor = 'sistema';
    location.hash = '#/h/' + hoyISO() + '/laudes';
    await new Promise((r) => setTimeout(r, 4000));
    arrancaVoz(0);`);
  await espera(10000);
  let e = await estado();
  e.motor = await evalua('return { hablando: speechSynthesis.speaking, '
    + 'pendiente: speechSynthesis.pending, voz: E.cfg.voz };');
  apunta('dice Laudes', e, e.estado === 'diciendo' && e.i >= 1);
  foto('voz-1-diciendo.png');

  const sesion = adb('shell dumpsys media_session');
  const nuestra = sesion.split('\n').some((l) => l.includes(PAQUETE));
  apunta('la sesión de medios está puesta', { nuestra }, nuestra);

  adb('shell cmd statusbar expand-notifications');
  await espera(1500);
  foto('voz-2-aviso.png');
  adb('shell cmd statusbar collapse');

  // con la pantalla apagada
  const antes = (await estado()).i;
  adb('shell input keyevent KEYCODE_SLEEP');
  await espera(35000);
  e = await estado();
  apunta('sigue con la pantalla apagada', { antes, despues: e.i, estado: e.estado },
    e.estado === 'diciendo' && e.i > antes);

  // los botones de fuera, con la pantalla todavía apagada. Se mandan como
  // los manda el Bluetooth del coche, por la sesión de medios: con `input
  // keyevent` irían a la ventana, y con la pantalla apagada no hay ninguna
  const boton = (b) => adb('shell cmd media_session dispatch ' + b);
  boton('pause');
  await espera(2500);
  e = await estado();
  apunta('el botón de pausa la pausa', e, e.estado === 'pausada');
  boton('play');
  await espera(2500);
  e = await estado();
  apunta('el de seguir la sigue', e, e.estado === 'diciendo');
  const sec = e.sec;
  boton('next');
  await espera(2500);
  e = await estado();
  apunta('el de siguiente pasa de sección', { antes: sec, ahora: e.sec }, e.sec > sec);
  adb('shell input keyevent KEYCODE_WAKEUP');
  adb('shell wm dismiss-keyguard');
  await espera(1500);
  foto('voz-3-de-vuelta.png');
  boton('stop');
  await espera(2500);
  e = await estado();
  const servicio = adb('shell dumpsys activity services ' + PAQUETE);
  apunta('el de parar la para y quita el servicio', { estado: e.estado,
    servicio: /VozServicio/.test(servicio) }, e.estado === 'parada' && !/VozServicio/.test(servicio));

  // no apagar la pantalla
  await evalua('E.cfg.despierto = true; await velaPantalla();');
  await espera(1000);
  const ventana = adb('shell dumpsys window windows');
  const despierta = /KEEP_SCREEN_ON/.test(ventana);
  apunta('«No apagar la pantalla» la deja encendida', { despierta }, despierta);

  // Piper, la voz ligera, a archivos de la app
  const piper = await evalua(`
    const voz = 'es_MX-ald-x_low';
    const t0 = Date.now();
    await pidePiper({ tipo: 'baja', voz: voz });
    const hay = (await pidePiper({ tipo: 'hay', voz: voz })).hay;
    const t1 = Date.now();
    const r = await pidePiper({ tipo: 'di', voz: voz, hablante: '', vel: 1,
      texto: 'Bendito sea el Señor, Dios de Israel.' });
    const enCache = (await caches.keys()).includes('voz-piper')
      ? (await (await caches.open('voz-piper')).keys()).length : 0;
    return { hay: hay, bajadaEn: Math.round((t1 - t0) / 1000), segundos: r.segundos,
      ms: Math.round(r.ms), enLaCacheDelNavegador: enCache };`);
  apunta('Piper baja a archivos y habla desde ellos', piper,
    piper.hay && piper.segundos > 0 && piper.enLaCacheDelNavegador === 0);
  const archivos = adb('shell run-as ' + PAQUETE + ' ls -l files/piper');
  apunta('los archivos están en files/piper', { archivos: archivos.split('\n') }, /ald-x_low\.onnx/.test(archivos));
}

try {
  await prueba();
} catch (err) {
  apunta('la prueba ha podido correr', { error: String(err && err.message || err) }, false);
}
writeFileSync('voz-informe.json', JSON.stringify(informe, null, 2));
console.log(informe.fallos.length ? 'FALLA: ' + informe.fallos.join(' · ') : 'Todo bien');
process.exit(informe.fallos.length ? 1 : 0);
