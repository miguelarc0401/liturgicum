/* Lo que la app necesita del teléfono cuando corre dentro del APK de
 * Android (apk/LEEME.md), y que el WebView no trae.
 *
 * En Chrome este fichero no hace nada: se sale en la primera línea. Dentro
 * del APK deja dos cosas:
 *
 *  · window.NATIVO, para hablar con los plugins de la propia app (la voz,
 *    la pantalla, los archivos de Piper) sin cargar @capacitor/core: el
 *    puente de Capacitor ya trae nativePromise y addListener.
 *
 *  · speechSynthesis y SpeechSynthesisUtterance, montados encima del motor
 *    de voz de Android (VozPlugin.java). El WebView no trae la voz del
 *    sistema, y en vez de escribir otro reproductor para el APK se le da a
 *    app.js lo mismo que le da Chrome: así «la voz del sistema» de app.js
 *    sirve igual en los dos sitios. Trae además una cosa que Chrome no
 *    tiene, silencio(ms): el motor de Android sabe callar dentro de su
 *    cola, y con eso app.js le da la hora entera de una vez, con el
 *    silencio de cada sección dentro (ver encolaHastaElFinDeLaSeccion).
 *
 * Va antes que app.js en index.html, para que app.js ya lo encuentre puesto.
 */
(function () {
  const C = window.Capacitor;
  if (!C || !C.isNativePlatform || !C.isNativePlatform()) return;

  const llama = (plugin, metodo, opciones) =>
    C.nativePromise(plugin, metodo, opciones || {});
  const oye = (plugin, evento, f) => C.addListener(plugin, evento, f);
  // Los plugins que trae este APK, según el propio puente. Un APK viejo puede
  // recibir por el actualizador un app.js nuevo que pide plugins que él no
  // tiene, y entonces cada cosa sigue como en la web.
  const tiene = (nombre) =>
    (C.PluginHeaders || []).some((p) => p && p.name === nombre);

  window.NATIVO = {
    llama: llama,
    oye: oye,
    tiene: tiene,
    /** La dirección con que la página puede leer un archivo de la app. */
    archivo: (uri) => C.convertFileSrc(uri)
  };

  if (!tiene('Voz')) return;

  /* ------------------------------------------------- la voz del sistema */

  const cola = new Map();     // id -> { u: la locución (nada si es silencio), empezada }
  let n = 0;
  let voces = [];
  let oyentes = [];

  function Locucion(texto) {
    this.text = texto || '';
    this.lang = '';
    this.voice = null;
    this.rate = 1;
    this.pitch = 1;
    this.volume = 1;
    this.onstart = null;
    this.onend = null;
    this.onerror = null;
    this.onboundary = null;
  }

  function acaba(id, como) {
    const t = cola.get(id);
    if (!t) return;
    cola.delete(id);
    if (!t.u) return;
    if (como === 'acaba') {
      if (t.u.onend) t.u.onend({});
    } else if (t.u.onerror) {
      // «interrupted» es lo que dice Chrome al callarla a propósito, y app.js
      // ya sabe no atenderlo
      t.u.onerror({ error: como === 'callada' ? 'interrupted' : 'synthesis-failed' });
    }
  }

  const sintesis = {
    onvoiceschanged: null,
    get speaking() {
      for (const t of cola.values()) if (t.empezada) return true;
      return false;
    },
    get pending() { return cola.size > 0; },
    get paused() { return false; },
    getVoices: () => voces.slice(),
    speak(u) {
      const id = 'u' + (++n);
      cola.set(id, { u: u, empezada: false });
      llama('Voz', 'di', {
        id: id,
        texto: u.text,
        voz: u.voice ? u.voice.voiceURI : null,
        lengua: u.lang || 'es-ES',
        vel: u.rate || 1
      }).catch(() => acaba(id, 'error'));
    },
    silencio(ms) {
      const id = 's' + (++n);
      cola.set(id, { u: null, empezada: false });
      llama('Voz', 'silencio', { id: id, ms: Math.round(ms) })
        .catch(() => cola.delete(id));
    },
    cancel() {
      cola.clear();
      llama('Voz', 'calla').catch(() => {});
    },
    pause() {},
    resume() {},
    addEventListener(tipo, f) {
      if (tipo === 'voiceschanged') oyentes.push(f);
    },
    removeEventListener(tipo, f) {
      oyentes = oyentes.filter((x) => x !== f);
    }
  };

  oye('Voz', 'trozo', (d) => {
    const t = d && cola.get(d.id);
    if (!t) return;
    if (d.que === 'empieza') {
      t.empezada = true;
      if (t.u && t.u.onstart) t.u.onstart({});
    } else if (d.que === 'palabra') {
      if (t.u && t.u.onboundary) {
        t.u.onboundary({ name: 'word', charIndex: d.inicio || 0 });
      }
    } else {
      acaba(d.id, d.que);
    }
  });

  // El motor puede dar la lista vacía nada más arrancar —la va cargando—: se
  // le vuelve a preguntar unas cuantas veces antes de creérselo
  function pideLasVoces(veces) {
    llama('Voz', 'voces').then((r) => {
      if (!(r.voces || []).length && veces > 0) {
        setTimeout(() => pideLasVoces(veces - 1), 3000);
        return;
      }
      voces = (r.voces || []).map((v) => ({
        voiceURI: v.id, name: v.nombre, lang: v.lengua,
        localService: !v.red, default: !!v.porOmision
      }));
      oyentes.forEach((f) => { try { f({}); } catch (_) { /* uno que falla */ } });
      if (sintesis.onvoiceschanged) sintesis.onvoiceschanged({});
    }).catch(() => { /* sin motor de voz: la lista se queda vacía y Ajustes lo dice */ });
  }
  pideLasVoces(10);

  Object.defineProperty(window, 'speechSynthesis',
    { value: sintesis, configurable: true, writable: true });
  window.SpeechSynthesisUtterance = Locucion;
})();
