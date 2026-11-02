/* El corrector de erratas: cualquier texto de la app, corregido desde la
 * app misma, y que siga corregido.
 *
 * No existe para todos: app.js lo carga sólo en dos casos.
 *
 *  · En el ordenador, con la app servida por Enchiridion/src/editar.py
 *    (editar.bat): busca y guarda el editor, que cambia app/datos/ al
 *    momento y lo apunta en data/fe_de_erratas/. Lo ven todos al publicar.
 *  · En el teléfono de quien edita el libro, con su llave de GitHub puesta
 *    en Ajustes › Editor del libro: busca el propio teléfono, en lo que
 *    tiene cargado, y la corrección va a GitHub como un pedido pequeño
 *    (data/erratas_pendientes/<id>.json). Allí la aplica el mismo programa
 *    que en el ordenador y la app se vuelve a publicar
 *    (.github/workflows/erratas.yml): la ven todos en un par de minutos. Sin
 *    conexión, el pedido espera en el teléfono y sale cuando vuelve la red.
 *
 * Se selecciona el texto —una palabra basta: doble clic en el ordenador,
 * dedo encima en el teléfono— y sale «Corregir» al lado. En la ficha va la
 * tirada entera en que cae lo seleccionado (un versículo, un renglón del
 * himno, la antífona), y se escribe como debe quedar. «Buscar dónde está»
 * dice en qué sitios de los datos está ese texto con lo mismo alrededor. Al
 * guardar, la página cambia en el acto, y lo cargado en memoria también,
 * para que al volver a la misma pieza salga ya corregida.
 */
'use strict';

(() => {
  // la llave se puede poner con la app abierta, y entonces se carga otra vez
  if (window.Erratas) return;
  window.Erratas = true;

  const ORDENADOR = !!E.editor;
  const LAPIZ = '<svg viewBox="0 0 24 24" aria-hidden="true">'
    + '<path d="M4 20h4L19 9a2.83 2.83 0 0 0-4-4L4 16v4Z"/>'
    + '<path d="m13.5 6.5 4 4"/></svg>';
  // lo que no es texto del libro: los mandos, y lo que se escribe
  const NO_ES_TEXTO = 'button, input, textarea, select, label, .alterna, '
    + '.devo-chip, .devo-editor, .devo-form, .voz, .ajustes-sec';
  // el renglón: lo que la página enseña alrededor se toma dentro de él
  const RENGLON = '.ln, p, li, h1, h2, h3, h4, h5, h6, td, dd, dt, '
    + 'blockquote, div';

  let sel = null;       // lo que se corrige: {nodo, texto, ini, fin, antes, despues}
  let plan = null;      // dónde se ha encontrado
  let ultima = null;    // la última selección buena, por si el toque la borra
  let reloj = null;

  const boton = document.createElement('button');
  boton.type = 'button';
  boton.className = 'errata-boton';
  boton.hidden = true;
  boton.innerHTML = LAPIZ + 'Corregir';
  // que el toque no se lleve la selección antes de leerla; en el teléfono
  // se la lleva igual antes del clic, así que allí se abre ya al tocar
  boton.addEventListener('pointerdown', (ev) => {
    ev.preventDefault();
    if (ev.pointerType !== 'mouse') abre();
  });
  boton.addEventListener('click', () => {
    if (!document.querySelector('.errata-fondo')) abre();
  });
  document.body.appendChild(boton);

  const pildora = document.createElement('button');
  pildora.type = 'button';
  pildora.className = 'erratas-pildora';
  pildora.title = 'Las erratas corregidas. Para corregir otra, selecciona '
    + 'el texto.';
  pildora.addEventListener('click', verLista);
  document.body.appendChild(pildora);
  cuenta();

  document.addEventListener('selectionchange', () => {
    clearTimeout(reloj);
    reloj = setTimeout(coloca, 150);
  });
  window.addEventListener('scroll', () => {
    if (!boton.hidden) coloca();
  }, { passive: true });
  window.addEventListener('resize', () => {
    if (!boton.hidden) coloca();
  });
  // lo que se corrigió sin conexión sale en cuanto vuelve
  if (!ORDENADOR) {
    window.addEventListener('online', () => mandaPendientes());
    setTimeout(mandaPendientes, 3000);
  }

  function cuenta() {
    const n = ORDENADOR ? ((E.editor && E.editor.erratas) || 0)
      : apuntadas().filter((x) => x.estado !== 'deshecha').length;
    pildora.innerHTML = LAPIZ + 'Erratas' + (n ? ' <span>' + n + '</span>' : '');
  }

  /** La tirada de texto en que empieza lo seleccionado, si es texto de la
   *  app: un nodo de texto de la página, que es lo que se sabe buscar en
   *  los datos. */
  function seleccion() {
    const s = window.getSelection();
    if (!s || s.isCollapsed || !s.rangeCount) return null;
    const r = s.getRangeAt(0);
    let nodo = r.startContainer, ini = r.startOffset;
    if (nodo.nodeType !== Node.TEXT_NODE || ini >= nodo.data.length) {
      // empieza entre dos elementos, o al final de la tirada de antes (un
      // triple clic): la primera tirada con letra que cae dentro
      const de = nodo;
      const raiz = r.commonAncestorContainer.nodeType === Node.TEXT_NODE
        ? r.commonAncestorContainer.parentNode : r.commonAncestorContainer;
      const w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT, {
        acceptNode: (n) => n !== de && r.intersectsNode(n) && n.data.trim()
          ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP });
      nodo = w.nextNode();
      ini = 0;
    }
    if (!nodo || !nodo.data.trim()) return null;
    const el = nodo.parentElement;
    if (!el || !(vista.contains(el) || $('#cabecera').contains(el))) return null;
    if (el.closest(NO_ES_TEXTO)) return null;
    const fin = r.endContainer === nodo ? r.endOffset : nodo.data.length;
    return { nodo: nodo, ini: ini, fin: Math.max(ini, fin),
      rect: r.getBoundingClientRect() };
  }

  /** El botón, debajo de lo seleccionado; encima si abajo no cabe. */
  function coloca() {
    const s = document.querySelector('.errata-fondo') ? null : seleccion();
    if (!s) { boton.hidden = true; return; }
    ultima = s;
    boton.hidden = false;
    const w = boton.offsetWidth, h = boton.offsetHeight;
    let top = s.rect.bottom + 8;
    if (top + h > innerHeight - 90) top = s.rect.top - h - 8;
    const left = Math.min(Math.max(8, s.rect.left + s.rect.width / 2 - w / 2),
      innerWidth - w - 8);
    boton.style.top = Math.round(top) + 'px';
    boton.style.left = Math.round(left) + 'px';
  }

  function abre() {
    let s = seleccion();
    if (!s && ultima && ultima.nodo.isConnected) s = ultima;
    boton.hidden = true;
    ultima = null;
    if (!s) return;
    // lo que la página enseña alrededor, en el mismo renglón: con eso se
    // sabe cuál es, si el mismo texto está en muchos sitios
    const renglon = s.nodo.parentElement.closest(RENGLON) || s.nodo.parentElement;
    const r = document.createRange();
    r.selectNodeContents(renglon);
    r.setEndBefore(s.nodo);
    const antes = r.toString().slice(-160);
    r.selectNodeContents(renglon);
    r.setStartAfter(s.nodo);
    const despues = r.toString().slice(0, 160);
    // el doble clic de Windows se lleva el espacio de detrás, y lo que se
    // escribe encima se comía la separación: se marca la palabra sola
    const t = s.nodo.data;
    let ini = s.ini, fin = s.fin;
    while (fin > ini && /\s/.test(t[fin - 1])) fin--;
    while (ini < fin && /\s/.test(t[ini])) ini++;
    sel = { nodo: s.nodo, texto: t, ini: ini, fin: fin,
      antes: antes, despues: despues };
    window.getSelection().removeAllRanges();
    ficha();
  }

  /* ------------------------------------------------------------ la ficha */
  function cabeza(titulo) {
    return '<div class="errata-ficha" role="dialog" aria-modal="true" '
      + 'aria-labelledby="errata-tit"><p class="errata-ojo">Fe de erratas · '
      + (ORDENADOR ? 'sólo en este ordenador' : 'el editor, en el teléfono')
      + '</p><h2 id="errata-tit" class="errata-tit">' + titulo + '</h2>';
  }

  function dondeSeGuarda() {
    return '<code>' + esc((E.editor && E.editor.fe) || 'data/fe_de_erratas/')
      + '</code>';
  }

  /** El fondo cierra la ficha si se toca fuera —pero no si se suelta fuera
   *  una selección empezada dentro, ni con el toque que la abrió—, Escape
   *  también, y Ctrl+Intro hace lo del botón principal. */
  function abreFondo(html, principal) {
    cierra();
    const fondo = document.createElement('div');
    fondo.className = 'errata-fondo';
    fondo.innerHTML = html;
    document.body.appendChild(fondo);
    let pulsado = null;
    fondo.addEventListener('pointerdown', (ev) => { pulsado = ev.target; });
    fondo.addEventListener('click', (ev) => {
      if (ev.target === fondo && pulsado === fondo) { cierra(); return; }
      const b = ev.target.closest('[data-errata]');
      if (b && !b.disabled) ({ busca: busca, guarda: guarda, cierra: cierra })[b.dataset.errata](fondo);
    });
    fondo.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape') {
        ev.preventDefault();
        cierra();
      } else if (ev.key === 'Enter' && (ev.ctrlKey || ev.metaKey) && principal) {
        ev.preventDefault();
        principal(fondo);
      }
    });
    return fondo;
  }

  function ficha() {
    plan = null;
    const fondo = abreFondo(cabeza('Corregir el texto')
      + '<textarea class="campo" spellcheck="true" aria-label="El texto, '
      + 'como debe quedar"></textarea>'
      + '<p class="errata-pista">Escríbelo como debe quedar. '
      + (ORDENADOR
        ? 'Se cambia en los datos de la app y se apunta en ' + dondeSeGuarda()
          + ', que se vuelve a aplicar cada vez que se rehacen; lo verán todos '
          + 'cuando publiques. Ctrl+Intro hace lo del botón.'
        : 'Se corrige en este teléfono al momento y se manda a GitHub, que lo '
          + 'aplica a los datos y vuelve a publicar la app: lo verán todos en '
          + 'un par de minutos.')
      + '</p>'
      + '<div class="errata-res" hidden></div>'
      + '<p class="errata-error" role="alert" hidden></p>'
      + '<div class="errata-botones"><button type="button" class="devo-chip '
      + 'activo" data-errata="busca">Buscar dónde está</button>'
      + '<button type="button" class="devo-chip" data-errata="cierra">'
      + 'Cancelar</button></div></div>', (f) => (plan ? guarda : busca)(f));
    const ta = fondo.querySelector('textarea');
    ta.value = sel.texto;
    ta.rows = Math.min(14, Math.max(3, Math.ceil(sel.texto.length / 55) + 1));
    ta.focus();
    ta.setSelectionRange(sel.ini, sel.fin);
    // lo encontrado vale para lo que se buscó: si se sigue escribiendo, hay
    // que volver a buscar
    ta.addEventListener('input', () => {
      if (!plan) return;
      plan = null;
      pinta(fondo);
    });
  }

  function cuerpo(fondo) {
    return { texto: sel.texto, nuevo: fondo.querySelector('textarea').value,
      antes: sel.antes, despues: sel.despues };
  }

  async function busca(fondo) {
    const c = cuerpo(fondo);
    if (c.nuevo === c.texto) { error(fondo, 'No has cambiado nada.'); return; }
    espera(fondo, true);
    try {
      if (ORDENADOR) {
        plan = (await orden('buscar', c)).plan;
      } else {
        // que se vea que está buscando: en el teléfono tarda un momento
        await new Promise((r) => setTimeout(r, 30));
        plan = buscaAqui(c);
      }
      error(fondo, '');
    } catch (err) {
      plan = null;
      error(fondo, err.message);
    }
    espera(fondo, false);
    pinta(fondo);
  }

  function flecha(de, a) {
    return '<del>' + esc(de) + '</del><span class="errata-flecha"> → </span>'
      + '<ins>' + esc(a) + '</ins>';
  }

  function lista(xs, n) {
    return '<ul class="errata-sitios">' + xs.map((x) => '<li>' + esc(x)
      + '</li>').join('') + (n > xs.length ? '<li class="errata-mas">y '
      + (n - xs.length) + ' más</li>' : '') + '</ul>';
  }

  /** Lo encontrado: el cambio, los sitios seguros —el texto y lo de
   *  alrededor casan con la página— y, aparte y sin marcar, los que tienen
   *  el mismo texto con otra cosa alrededor, que pueden ser otra pieza. */
  function pinta(fondo) {
    const res = fondo.querySelector('.errata-res');
    const b = fondo.querySelector('.errata-botones [data-errata]');
    if (!plan) {
      res.hidden = true;
      res.innerHTML = '';
      b.dataset.errata = 'busca';
      b.textContent = 'Buscar dónde está';
      return;
    }
    const p = plan;
    res.innerHTML = '<p class="errata-cambio">' + flecha(p.cambio.de, p.cambio.a)
      + '</p>'
      + (p.n ? '<p class="errata-n">' + (p.n === 1
        ? 'Está en un sitio de los datos:'
        : 'Está en ' + p.n + ' sitios de los datos, con el mismo texto '
          + 'alrededor:') + '</p>' + lista(p.sitios, p.n)
        : '<p class="errata-n">No lo encuentro con lo que tiene alrededor en '
          + 'la página.</p>')
      + (p.n_otros ? '<label class="errata-otros"><input type="checkbox">'
        + '<span>' + (p.n ? 'Corregir también ' : 'Corregir ')
        + (p.n_otros === 1 ? 'el sitio' : 'los ' + p.n_otros + ' sitios')
        + ' donde sale igual pero con otro texto alrededor</span></label>'
        + '<details class="errata-det"><summary>Cuáles son</summary>'
        + lista(p.otros, p.n_otros) + '</details>' : '')
      + (p.n > 50 ? '<p class="errata-aviso">Son muchos sitios: mira que sea '
        + 'eso lo que quieres cambiar.</p>' : '')
      + (ORDENADOR ? '' : '<p class="errata-pista">Lo busco en lo que este '
        + 'teléfono tiene abierto. GitHub lo busca en todos los libros, y si '
        + 'el mismo pasaje está en otro (la Nova y el Misal de 1977), lo '
        + 'corrige también.</p>');
    res.hidden = false;
    b.dataset.errata = 'guarda';
    b.textContent = 'Guardar la corrección';
  }

  async function guarda(fondo) {
    const marca = fondo.querySelector('.errata-otros input');
    const otros = !!(marca && marca.checked);
    const cuantos = plan.n + (otros ? plan.n_otros : 0);
    if (!cuantos) { error(fondo, 'Marca dónde corregirlo.'); return; }
    const c = Object.assign(cuerpo(fondo), { otros: otros, cuantos: cuantos });
    if (!ORDENADOR) { guardaAqui(fondo, c); return; }
    espera(fondo, true);
    let d;
    try {
      d = await orden('corregir', c);
    } catch (err) {
      espera(fondo, false);
      error(fondo, err.message);
      return;
    }
    ponCambios(d.cambios);
    const nodos = enPagina(c.texto, c.nuevo);
    cierra();
    cuenta();
    devoAvisa('Corregido ' + (d.n === 1 ? 'en un sitio' : 'en ' + d.n
      + ' sitios') + ': ' + d.cambio, 'Deshacer',
    () => deshaz(d.id, nodos, c.texto));
  }

  async function deshaz(id, nodos, viejo) {
    let d;
    try {
      d = await orden('deshacer', { id: id });
    } catch (err) {
      devoAvisa('No se ha deshecho: ' + err.message);
      return false;
    }
    ponCambios(d.cambios);
    if (nodos) {
      for (const n of nodos) n.data = viejo;
    } else {
      await repinta();
    }
    cuenta();
    devoAvisa('Deshecho: ' + d.cambio);
    return true;
  }

  /** Desde la lista no se sabe qué tirada de la página era: se vuelve a
   *  pintar lo que se está viendo, que ya sale de la memoria al día. */
  async function repinta() {
    const y = window.scrollY;
    await enruta();
    window.scrollTo(0, y);
  }

  /* ------------------------------------------ la lista de las corregidas */
  async function verLista() {
    if (!ORDENADOR) { verListaTelefono(); return; }
    let d;
    try {
      d = await orden('erratas');
    } catch (err) {
      devoAvisa('El editor no contesta: ' + err.message);
      return;
    }
    cuenta();
    const xs = d.erratas;
    const fondo = abreFondo(cabeza('Erratas corregidas')
      + '<p class="errata-pista">Para corregir otra, selecciona el texto en la '
      + 'página —con un doble clic basta para una palabra— y pulsa '
      + '«Corregir». Están apuntadas en ' + dondeSeGuarda() + ', y las verán '
      + 'todos cuando publiques.</p>'
      + (xs.length ? '<ul class="errata-lista">' + xs.map((x) => {
        const [de, a] = x.cambio.split(' → ');
        return '<li><p class="errata-cambio">' + flecha(de, a || '') + '</p>'
          + '<span class="errata-meta">' + esc(x.fecha) + ' · '
          + (x.n === 1 ? 'un sitio' : x.n + ' sitios') + '</span>'
          + '<button type="button" class="devo-chip" data-deshaz="'
          + esc(x.id) + '">Deshacer</button></li>';
      }).join('') + '</ul>'
        : '<p class="errata-n">Todavía no has corregido ninguna.</p>')
      + '<div class="errata-botones"><button type="button" class="devo-chip '
      + 'activo" data-errata="cierra">Cerrar</button></div></div>');
    fondo.addEventListener('click', async (ev) => {
      const b = ev.target.closest('[data-deshaz]');
      if (!b || b.disabled) return;
      b.disabled = true;
      if (await deshaz(b.dataset.deshaz, null, null)) b.closest('li').remove();
      else b.disabled = false;
    });
    fondo.querySelector('[data-errata="cierra"]').focus();
  }

  /* ================================================== en el teléfono */
  /* Lo corregido desde aquí, con cómo va cada una: «por enviar» (sin
   * conexión todavía), «enviada» (GitHub la tiene y la está aplicando),
   * «aplicada», «rechazada» (con el motivo), «deshaciendo» y «deshecha».
   * Se guarda en el teléfono; lo que de verdad manda es lo que haya en
   * GitHub, y la lista se pone al día con él cada vez que se abre. */
  const CLAVE = 'erratasTelefono';

  function apuntadas() {
    try {
      return JSON.parse(localStorage.getItem(CLAVE) || '[]');
    } catch (_) {
      return [];
    }
  }

  function guardaApuntadas(xs) {
    try {
      localStorage.setItem(CLAVE, JSON.stringify(xs.slice(0, 200)));
    } catch (_) {}
  }

  function cambiaApuntada(id, cambia) {
    const xs = apuntadas();
    const x = xs.find((y) => y.id === id);
    if (x) {
      cambia(x);
      guardaApuntadas(xs);
    }
    return x;
  }

  function nuevoId() {
    const d = new Date();
    const dos = (n) => String(n).padStart(2, '0');
    const b = crypto.getRandomValues(new Uint8Array(3));
    return 'e_' + d.getFullYear() + dos(d.getMonth() + 1) + dos(d.getDate())
      + '_' + Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
  }

  function guardaAqui(fondo, c) {
    const id = nuevoId();
    const ahora = new Date();
    const pedido = { id: id, accion: 'corregir', creado: ahora.toISOString(),
      texto: c.texto, nuevo: c.nuevo, antes: c.antes, despues: c.despues,
      otros: c.otros };
    const cambios = aplicaAqui(plan.local, c.otros);
    ponCambios(cambios);
    const nodos = enPagina(c.texto, c.nuevo);
    const item = { id: id, cambio: plan.cambio.de + ' → ' + plan.cambio.a,
      fecha: hoyISO(), estado: 'por enviar', pedido: pedido };
    guardaApuntadas([item].concat(apuntadas()));
    cierra();
    cuenta();
    manda(item.id).then((ok) => {
      devoAvisa(ok ? 'Corregido aquí; GitHub lo publica en un par de minutos.'
        : 'Corregido en este teléfono; se manda en cuanto haya conexión.',
      'Deshacer', () => deshazAqui(id, cambios, nodos, c.texto));
    });
  }

  /** El «Deshacer» del aviso, recién guardada: lo de la página y la
   *  memoria vuelve en el acto, y GitHub la deshace después (o ni se
   *  entera, si no había salido del teléfono). */
  async function deshazAqui(id, cambios, nodos, viejo) {
    ponCambios(cambios.map((c) => ({ f: c.f, r: c.r, viejo: c.nuevo,
      nuevo: c.viejo })));
    for (const n of nodos) n.data = viejo;
    const x = apuntadas().find((y) => y.id === id);
    if (x && x.estado === 'por enviar') {
      guardaApuntadas(apuntadas().filter((y) => y.id !== id));
      cuenta();
      devoAvisa('Deshecho: no había salido del teléfono.');
      return;
    }
    await pideDeshacer(id);
    devoAvisa('Deshecho aquí; GitHub lo deshace en un par de minutos.');
  }

  async function pideDeshacer(id) {
    cambiaApuntada(id, (x) => {
      x.estado = 'deshaciendo';
      x.motivo = '';
      x.deshaz = { id: nuevoId(), estado: 'por enviar',
        creado: new Date().toISOString() };
    });
    cuenta();
    return manda(id);
  }

  /* ---------------------------------------------------------- GitHub */
  const API = 'https://api.github.com/repos/' + REPO + '/contents/';

  function gh(ruta, opciones) {
    return fetch(API + ruta, Object.assign({ cache: 'no-store',
      headers: { Authorization: 'Bearer ' + llaveEditor(),
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28' } }, opciones));
  }

  function motivoGitHub(estado) {
    if (estado === 401) return 'GitHub ya no reconoce la llave: pon otra en '
      + 'Ajustes › Editor del libro.';
    if (estado === 403 || estado === 404) return 'La llave no deja escribir en '
      + 'el repositorio: tiene que llevar el permiso «Contents: Read and write».';
    return 'GitHub contesta ' + estado + '.';
  }

  function aBase64(t) {
    const b = new TextEncoder().encode(t);
    let s = '';
    for (let i = 0; i < b.length; i += 0x8000) {
      s += String.fromCharCode.apply(null, b.subarray(i, i + 0x8000));
    }
    return btoa(s);
  }

  function deBase64(t) {
    const s = atob(t.replace(/\s/g, ''));
    return new TextDecoder().decode(Uint8Array.from(s, (ch) => ch.charCodeAt(0)));
  }

  /** Un fichero nuevo en el repositorio. Si ya estaba (se mandó dos veces
   *  y la primera sí llegó), GitHub contesta 422, y vale. */
  async function sube(ruta, objeto, mensaje) {
    const r = await gh(ruta, { method: 'PUT', body: JSON.stringify({
      message: mensaje, branch: 'main',
      content: aBase64(JSON.stringify(objeto, null, 1) + '\n') }) });
    if (!r.ok && r.status !== 422) throw new Error(motivoGitHub(r.status));
  }

  /** Lo que hay en una ruta del repositorio, o null si no hay nada. */
  async function lee(ruta) {
    const r = await gh(ruta + '?ref=main');
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(motivoGitHub(r.status));
    const d = await r.json();
    try {
      return JSON.parse(deBase64(d.content || ''));
    } catch (_) {
      return {};
    }
  }

  const sinRed = (err) => err instanceof TypeError;

  /** Manda lo que de una corregida esté por enviar: la corrección, o el
   *  deshacerla. Devuelve si ha salido. */
  async function manda(id) {
    const x = apuntadas().find((y) => y.id === id);
    if (!x) return false;
    try {
      if (x.estado === 'por enviar' && x.pedido) {
        await sube('data/erratas_pendientes/' + x.id + '.json', x.pedido,
          'Errata desde el teléfono: ' + x.cambio);
        cambiaApuntada(id, (y) => {
          y.estado = 'enviada';
          y.motivo = '';
          delete y.pedido;
        });
      }
      if (x.deshaz && x.deshaz.estado === 'por enviar') {
        await sube('data/erratas_pendientes/' + x.deshaz.id + '.json',
          { id: x.deshaz.id, accion: 'deshacer', errata: x.id,
            creado: x.deshaz.creado },
          'Deshago desde el teléfono: ' + x.cambio);
        cambiaApuntada(id, (y) => { y.deshaz.estado = 'enviada'; });
      }
      return true;
    } catch (err) {
      cambiaApuntada(id, (y) => {
        y.motivo = sinRed(err) ? '' : err.message;
      });
      return false;
    }
  }

  async function mandaPendientes() {
    if (!navigator.onLine) return;
    for (const x of apuntadas()) {
      if (x.estado === 'por enviar' || (x.deshaz && x.deshaz.estado === 'por enviar')) {
        await manda(x.id);
      }
    }
  }

  /** Cómo va en GitHub: si ya está apuntada en la fe de erratas, si la
   *  rechazó (y por qué), si ya se deshizo. */
  async function alDia(x) {
    if (x.estado === 'enviada') {
      if (await lee('data/fe_de_erratas/' + x.id + '.json')) {
        cambiaApuntada(x.id, (y) => { y.estado = 'aplicada'; });
        return;
      }
      const no = await lee('data/erratas_rechazadas/' + x.id + '.json');
      if (no) {
        cambiaApuntada(x.id, (y) => {
          y.estado = 'rechazada';
          y.motivo = no.motivo || '';
        });
      }
    } else if (x.estado === 'deshaciendo' && x.deshaz
        && x.deshaz.estado === 'enviada') {
      const no = await lee('data/erratas_rechazadas/' + x.deshaz.id + '.json');
      if (no) {
        cambiaApuntada(x.id, (y) => {
          y.estado = 'aplicada';
          y.motivo = 'No se pudo deshacer: ' + (no.motivo || '');
          delete y.deshaz;
        });
      } else if (!(await lee('data/erratas_pendientes/' + x.deshaz.id + '.json'))
          && !(await lee('data/fe_de_erratas/' + x.id + '.json'))) {
        cambiaApuntada(x.id, (y) => { y.estado = 'deshecha'; });
      }
    }
  }

  const ESTADO = {
    'por enviar': 'sin enviar todavía: sale en cuanto haya conexión',
    enviada: 'en GitHub, aplicándose',
    aplicada: 'aplicada y publicada',
    rechazada: 'no se pudo aplicar',
    deshaciendo: 'deshaciéndose en GitHub',
    deshecha: 'deshecha'
  };

  function filaTelefono(x) {
    const [de, a] = x.cambio.split(' → ');
    const accion = x.estado === 'aplicada' ? ['deshacer', 'Deshacer']
      : x.estado === 'por enviar' ? ['manda', 'Enviar']
        : (x.estado === 'rechazada' || x.estado === 'deshecha')
          ? ['olvida', 'Quitar'] : null;
    return '<li><p class="errata-cambio">' + flecha(de, a || '') + '</p>'
      + '<span class="errata-meta">' + esc(x.fecha) + ' · '
      + '<span class="errata-estado estado-' + x.estado.replace(' ', '-') + '">'
      + ESTADO[x.estado] + '</span>'
      + (x.motivo ? '<span class="errata-motivo">' + esc(x.motivo) + '</span>' : '')
      + '</span>'
      + (accion ? '<button type="button" class="devo-chip" data-tel="'
        + accion[0] + '" data-id="' + esc(x.id) + '">' + accion[1] + '</button>'
        : '') + '</li>';
  }

  function pintaListaTelefono(fondo, nota) {
    const xs = apuntadas();
    fondo.querySelector('.errata-cuerpo').innerHTML = (nota
      ? '<p class="errata-pista">' + nota + '</p>' : '')
      + (xs.length ? '<ul class="errata-lista">' + xs.map(filaTelefono).join('')
        + '</ul>' : '<p class="errata-n">Todavía no has corregido ninguna '
        + 'desde este teléfono.</p>');
  }

  async function verListaTelefono() {
    const fondo = abreFondo(cabeza('Erratas corregidas')
      + '<p class="errata-pista">Las que has corregido desde este teléfono. '
      + 'Para corregir otra, deja el dedo sobre la palabra y toca «Corregir». '
      + 'GitHub las aplica y vuelve a publicar la app: llegan a todos en un '
      + 'par de minutos.</p><div class="errata-cuerpo"></div>'
      + '<div class="errata-botones"><button type="button" class="devo-chip '
      + 'activo" data-errata="cierra">Cerrar</button></div></div>');
    fondo.addEventListener('click', async (ev) => {
      const b = ev.target.closest('[data-tel]');
      if (!b || b.disabled) return;
      b.disabled = true;
      const id = b.dataset.id;
      if (b.dataset.tel === 'olvida') {
        guardaApuntadas(apuntadas().filter((y) => y.id !== id));
      } else if (b.dataset.tel === 'manda') {
        await manda(id);
      } else {
        await pideDeshacer(id);
      }
      cuenta();
      pintaListaTelefono(fondo);
    });
    const vivas = apuntadas().filter((x) => x.estado === 'enviada'
      || x.estado === 'deshaciendo');
    pintaListaTelefono(fondo, vivas.length ? 'Mirando en GitHub cómo van…' : '');
    let nota = '';
    try {
      await mandaPendientes();
      for (const x of vivas) await alDia(x);
    } catch (err) {
      nota = sinRed(err) ? 'Sin conexión: no puedo mirar en GitHub cómo van.'
        : err.message;
    }
    if (document.body.contains(fondo)) pintaListaTelefono(fondo, nota);
    cuenta();
  }

  /* ------------------------------------------- buscar en el teléfono
   * Lo mismo que src/erratas.py, pero en lo que el teléfono tiene cargado
   * —que es de donde sale lo que la página enseña—: primero la tirada
   * entera, luego trozos más cortos alrededor de lo cambiado; letra a
   * letra, y si no, en plano() (el latín con los acentos apagados, un
   * rótulo en otra caja). El que manda es el de GitHub, que lo vuelve a
   * buscar en todos los ficheros antes de cambiar nada. */
  const CONTEXTOS = [[null, null], [60, 60], [30, 30], [60, 0], [0, 60],
    [15, 15], [30, 0], [0, 30], [0, 0]];
  const esLetra = (ch) => /[\p{L}\p{N}]/u.test(ch || '');
  const esBlanco = (ch) => /\s/.test(ch || '');

  /** El fichero de datos tal como está cargado en memoria, si lo está. */
  function cargado(f) {
    const lect = (x) => (x && 'lecturas_' + x.fuente + '.json' === f ? x : null);
    return { 'horas.json': E.horas, 'horas_dias.json': E.horasDias,
      'misa.json': E.misa, 'misal_latino.json': E.latino,
      'prefacios.json': E.prefacios, 'ordinario.json': E.ordinario,
      'devocionario.json': E.devoTodo, 'indice.json': E.indice,
      'calendario.json': E.cal }[f] || lect(E.lecturas) || lect(E.lecturasEs);
  }

  function cargados() {
    const xs = [];
    for (const f of ['horas.json', 'horas_dias.json', 'misa.json',
      'misal_latino.json', 'prefacios.json', 'ordinario.json',
      'devocionario.json', 'indice.json', 'calendario.json']) {
      const o = cargado(f);
      if (o) xs.push([f, o]);
    }
    for (const l of [E.lecturas, E.lecturasEs]) {
      if (l && l.fuente && !xs.some(([, o]) => o === l)) {
        xs.push(['lecturas_' + l.fuente + '.json', l]);
      }
    }
    return xs;
  }

  /** Las cadenas de un fichero —los valores, no las llaves— que pasan la
   *  prueba, con su ruta. */
  function cadenas(obj, prueba) {
    const salen = [];
    const ruta = [];
    const anda = (x) => {
      if (typeof x === 'string') {
        if (prueba(x)) salen.push([ruta.slice(), x]);
      } else if (Array.isArray(x)) {
        for (let i = 0; i < x.length; i++) { ruta.push(i); anda(x[i]); ruta.pop(); }
      } else if (x && typeof x === 'object') {
        for (const k of Object.keys(x)) { ruta.push(k); anda(x[k]); ruta.pop(); }
      }
    };
    anda(obj);
    return salen;
  }

  function palabra(t, a, b) {
    if (a === b) {
      while (a > 0 && !esLetra(t[a - 1])) a--;
      while (b < t.length && !esLetra(t[b])) b++;
    }
    while (a > 0 && esLetra(t[a - 1])) a--;
    while (b < t.length && esLetra(t[b])) b++;
    return [a, b];
  }

  function desde(t, a, k, ini) {
    if (k === null) return ini;
    let i = Math.max(ini, a - k);
    if (i > ini && esLetra(t[i - 1])) while (i < a && esLetra(t[i])) i++;
    while (i < a && esBlanco(t[i])) i++;
    return i;
  }

  function hasta(t, b, k, fin) {
    if (k === null) return fin;
    let i = Math.min(fin, b + k);
    if (i < fin && esLetra(t[i])) while (i > b && esLetra(t[i - 1])) i--;
    while (i > b && esBlanco(t[i - 1])) i--;
    return i;
  }

  function casaDelante(dato, pagina) {
    dato = dato.slice(dato.lastIndexOf('\n') + 1);
    if (!dato) return true;
    if (!pagina) return false;
    const n = Math.min(dato.length, pagina.length);
    return dato.slice(-n) === pagina.slice(-n);
  }

  function casaDetras(dato, pagina) {
    const i = dato.indexOf('\n');
    if (i >= 0) dato = dato.slice(0, i);
    if (!dato) return true;
    if (!pagina) return false;
    const n = Math.min(dato.length, pagina.length);
    return dato.slice(0, n) === pagina.slice(0, n);
  }

  function halla(trozo, exacto) {
    const hay = [];
    const llano = exacto ? trozo : plano(trozo);
    if (!llano.trim()) return hay;
    for (const [f, obj] of cargados()) {
      const prueba = exacto ? (s) => s.length >= trozo.length && s.includes(trozo)
        : (s) => s.length >= llano.length / 2 && plano(s).includes(llano);
      for (const [r, s] of cadenas(obj, prueba)) {
        const donde = exacto ? s : plano(s);
        for (let i = donde.indexOf(llano); i >= 0;
          i = donde.indexOf(llano, i + llano.length)) {
          hay.push({ f: f, r: r, s: s, i: i, exacto: exacto });
        }
      }
    }
    return hay;
  }

  /** Dónde está, dicho para quien lee: el libro, la clave y el rótulo. */
  const NOMBRES = { 'horas.json': 'Liturgia de las Horas',
    'horas_dias.json': 'Horas, días', 'lecturas_es.json': 'Lecturas en castellano',
    'lecturas_clementina.json': 'Lecturas, Clementina',
    'lecturas_nova.json': 'Lecturas, Nova Vulgata',
    'lecturas_lect1977.json': 'Lecturas, Misal de 1977', 'misa.json': 'Misa',
    'misal_latino.json': 'Misal latino', 'ordinario.json': 'Ordinario de la misa',
    'prefacios.json': 'Prefacios', 'devocionario.json': 'Devocionario',
    'calendario.json': 'Calendario', 'indice.json': 'Índice' };

  function donde(h) {
    let x = cargado(h.f);
    const claves = [];
    let rotulo = '';
    for (const k of h.r.slice(0, -1)) {
      x = x[k];
      if (typeof k === 'string' && k.length > 2) claves.push(k);
      if (x && typeof x === 'object' && !Array.isArray(x)) {
        const t = x.tes || x.tla || x.t || x.r;
        if (typeof t === 'string' && t.trim()) {
          rotulo = t.trim() + (typeof x.c === 'string' ? ' ' + x.c : '');
        }
      }
    }
    const partes = [NOMBRES[h.f] || h.f].concat(claves.slice(-2));
    if (rotulo && claves.indexOf(rotulo) < 0) partes.push(rotulo);
    const d = partes.join(' · ');
    return d.length <= 160 ? d : d.slice(0, 157) + '…';
  }

  function buscaAqui(c) {
    const texto = c.texto, nuevo = c.nuevo;
    if (nuevo.indexOf('\n') >= 0 && texto.indexOf('\n') < 0) {
      throw new Error('Un salto de renglón no se puede añadir aquí: se corrige '
        + 'el texto, no la maquetación.');
    }
    const n = texto.length, m = nuevo.length;
    let p = 0;
    while (p < Math.min(n, m) && texto[p] === nuevo[p]) p++;
    let q = 0;
    while (q < Math.min(n, m) - p && texto[n - 1 - q] === nuevo[m - 1 - q]) q++;
    const e = n - q, e2 = m - q;
    const ini = n - texto.trimStart().length, fin = texto.trimEnd().length;
    let [a, b] = palabra(texto, p, e);
    a = Math.max(a, ini);
    b = Math.min(b, fin);
    if (a >= b || p < a || e > b) {
      throw new Error('El cambio cae en los espacios del principio o del '
        + 'final, que no son del texto.');
    }
    const cambio = { de: texto.slice(a, b), a: nuevo.slice(a, b + e2 - e) };
    const izq = plano(c.antes || ''), der = plano(c.despues || '');
    const vistos = new Set();
    for (const [kl, kr] of CONTEXTOS) {
      const lo = desde(texto, a, kl, ini), hi = hasta(texto, b, kr, fin);
      if (vistos.has(lo + ':' + hi) || lo >= hi) continue;
      vistos.add(lo + ':' + hi);
      const trozo = texto.slice(lo, hi);
      for (const exacto of [true, false]) {
        const hay = halla(trozo, exacto);
        if (!hay.length) continue;
        const delante = izq + plano(texto.slice(0, lo));
        const detras = plano(texto.slice(hi)) + der;
        const largo = exacto ? trozo.length : plano(trozo).length;
        for (const h of hay) {
          const s = exacto ? h.s : plano(h.s);
          const ant = s.slice(0, h.i), des = s.slice(h.i + largo);
          h.fuerte = casaDelante(exacto ? plano(ant) : ant, delante)
            && casaDetras(exacto ? plano(des) : des, detras);
        }
        const fuertes = hay.filter((h) => h.fuerte);
        const otros = hay.filter((h) => !h.fuerte);
        return { cambio: cambio, n: fuertes.length,
          sitios: fuertes.slice(0, 40).map(donde),
          n_otros: otros.length, otros: otros.slice(0, 40).map(donde),
          local: { texto: texto, nuevo: nuevo, p: p, e: e, e2: e2, lo: lo,
            trozo: trozo, fuertes: fuertes, otros: otros } };
      }
    }
    throw new Error('No encuentro este texto en los datos de la app. Puede que '
      + 'la app lo componga (un rótulo, una fecha, un número) y no esté '
      + 'escrito así en ningún fichero.');
  }

  /** Dónde cae el cambio dentro de la cadena del hallazgo. */
  function enElDato(pl, h) {
    let pon = pl.nuevo.slice(pl.p, pl.e2);
    if (h.exacto) return [h.i + pl.p - pl.lo, h.i + pl.e - pl.lo, pon];
    const mt = planoConMapa(pl.trozo)[1], ms = planoConMapa(h.s)[1];
    const k = (j) => { let i = 0; while (mt[i] < j) i++; return i; };
    const x = ms[h.i + k(pl.p - pl.lo)], y = ms[h.i + k(pl.e - pl.lo)];
    // lo que la app enseña en su caja y los datos traen en mayúsculas (un
    // rótulo) se escribe en mayúsculas, como lo de alrededor
    const junto = x < y ? h.s.slice(x, y) : h.s.slice(Math.max(0, x - 1), x + 1);
    const letras = Array.from(junto).filter((ch) => /\p{L}/u.test(ch));
    if (letras.length && letras.every((ch) => ch !== ch.toLowerCase())) {
      pon = pon.toUpperCase();
    }
    return [x, y, pon];
  }

  /** Lo que la corrección cambia en lo cargado: cadena por cadena, de atrás
   *  adelante, como lo hará GitHub. */
  function aplicaAqui(pl, otros) {
    const elegidos = pl.fuertes.concat(otros ? pl.otros : []);
    const porCadena = new Map();
    for (const h of elegidos) {
      const clave = h.f + '\u0000' + JSON.stringify(h.r);
      if (!porCadena.has(clave)) porCadena.set(clave, []);
      porCadena.get(clave).push(h);
    }
    const cambios = [];
    for (const hs of porCadena.values()) {
      const s = hs[0].s;
      let nuevo = s, tope = s.length + 1;
      for (const h of hs.sort((u, v) => v.i - u.i)) {
        const [x, y, pon] = enElDato(pl, h);
        if (y > tope) continue;
        nuevo = nuevo.slice(0, x) + pon + nuevo.slice(y);
        tope = x;
      }
      if (nuevo !== s) cambios.push({ f: hs[0].f, r: hs[0].r, viejo: s, nuevo: nuevo });
    }
    return cambios;
  }

  /* --------------------------------------------------------- utilidades */
  function cierra() {
    const f = document.querySelector('.errata-fondo');
    if (f) f.remove();
    plan = null;
  }

  function espera(fondo, si) {
    fondo.querySelectorAll('.errata-botones button').forEach((b) => {
      b.disabled = si;
    });
    fondo.querySelector('.errata-ficha').setAttribute('aria-busy', String(si));
  }

  function error(fondo, texto) {
    const e = fondo.querySelector('.errata-error');
    e.textContent = texto;
    e.hidden = !texto;
  }

  /** Una orden al editor del ordenador. */
  async function orden(o, c) {
    const r = await fetch('/__editor/' + o, { method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(c || {}) });
    let d = {};
    try { d = await r.json(); } catch (_) {}
    if (!r.ok || !d.ok) throw new Error(d.error || ('el editor contesta ' + r.status));
    if (d.estado) E.editor = d.estado;
    return d;
  }

  /** Lo cargado en memoria, al día: lo que se vuelva a pintar sale ya como
   *  quedó, sin recargar. Sólo donde la cadena sigue siendo la que era. */
  function ponCambios(cambios) {
    for (const c of cambios || []) {
      let x = cargado(c.f);
      for (const k of c.r.slice(0, -1)) x = x == null ? x : x[k];
      const k = c.r[c.r.length - 1];
      if (x != null && x[k] === c.viejo) x[k] = c.nuevo;
    }
    E.busqueda = null;
  }

  /** Lo corregido, cambiado en la página en el acto: la tirada que se
   *  corrigió y las que dicen lo mismo (la antífona repetida tras el
   *  salmo). Devuelve cuáles, para deshacerlo. */
  function enPagina(viejo, nuevo) {
    const nodos = [];
    for (const raiz of [vista, $('#cabecera')]) {
      const w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) {
        if (n.data === viejo) {
          n.data = nuevo;
          nodos.push(n);
        }
      }
    }
    return nodos;
  }
})();
