/* El corrector de erratas: cualquier texto de la app, corregido desde la
 * app misma, y que siga corregido.
 *
 * Sólo existe con la app servida por Enchiridion/src/editar.py en el
 * ordenador: app.js lo carga cuando miraEditor() encuentra el editor. En el
 * teléfono no se pide nunca, y por eso no está en sw.js ni en la firma de
 * version.js.
 *
 * Se selecciona el texto —una palabra basta, y un doble clic la selecciona—
 * y sale «Corregir» al lado. En la ficha va la tirada entera en que cae lo
 * seleccionado (un versículo, un renglón del himno, la antífona), y se
 * escribe como debe quedar. «Buscar dónde está» le pide al editor los
 * sitios de app/datos/ donde está ese texto con lo mismo alrededor; al
 * guardar, el editor lo cambia allí y lo apunta en data/fe_de_erratas.json,
 * que cada fase vuelve a aplicar al rehacer los datos (src/erratas.py). La
 * página cambia en el acto, y lo cargado en memoria también, para que al
 * volver a la misma pieza salga ya corregida.
 */
'use strict';

(() => {
  const LAPIZ = '<svg viewBox="0 0 24 24" aria-hidden="true">'
    + '<path d="M4 20h4L19 9a2.83 2.83 0 0 0-4-4L4 16v4Z"/>'
    + '<path d="m13.5 6.5 4 4"/></svg>';
  // lo que no es texto del libro: los mandos, y lo que se escribe
  const NO_ES_TEXTO = 'button, input, textarea, select, label, .alterna, '
    + '.devo-chip, .devo-editor, .devo-form, .voz';
  // el renglón: lo que la página enseña alrededor se toma dentro de él
  const RENGLON = '.ln, p, li, h1, h2, h3, h4, h5, h6, td, dd, dt, '
    + 'blockquote, div';

  let sel = null;       // lo que se corrige: {nodo, texto, ini, fin, antes, despues}
  let plan = null;      // dónde lo ha encontrado el editor
  let reloj = null;

  const boton = document.createElement('button');
  boton.type = 'button';
  boton.className = 'errata-boton';
  boton.hidden = true;
  boton.innerHTML = LAPIZ + 'Corregir';
  // que el clic no se lleve la selección antes de leerla
  boton.addEventListener('mousedown', (ev) => ev.preventDefault());
  boton.addEventListener('click', abre);
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

  function cuenta() {
    const n = (E.editor && E.editor.erratas) || 0;
    pildora.innerHTML = LAPIZ + 'Erratas' + (n ? ' <span>' + n + '</span>' : '');
  }

  /** La tirada de texto en que empieza lo seleccionado, si es texto de la
   *  app: un nodo de texto de la página, que es lo que el editor sabe buscar
   *  en los datos. */
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
    const s = seleccion();
    boton.hidden = true;
    if (!s) return;
    // lo que la página enseña alrededor, en el mismo renglón: con eso el
    // editor sabe cuál es, si el mismo texto está en muchos sitios
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
      + 'sólo en este ordenador</p><h2 id="errata-tit" class="errata-tit">'
      + titulo + '</h2>';
  }

  function dondeSeGuarda() {
    return '<code>' + esc((E.editor && E.editor.fe) || 'data/fe_de_erratas.json')
      + '</code>';
  }

  /** El fondo cierra la ficha si se toca fuera —pero no si se suelta fuera
   *  una selección empezada dentro—, Escape también, y Ctrl+Intro hace lo
   *  del botón principal. */
  function abreFondo(html, principal) {
    cierra();
    const fondo = document.createElement('div');
    fondo.className = 'errata-fondo';
    fondo.innerHTML = html;
    document.body.appendChild(fondo);
    let pulsado = null;
    fondo.addEventListener('mousedown', (ev) => { pulsado = ev.target; });
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
      + '<p class="errata-pista">Escríbelo como debe quedar. Se cambia en los '
      + 'datos de la app y se apunta en ' + dondeSeGuarda() + ', que se vuelve '
      + 'a aplicar cada vez que se rehacen; lo verán todos cuando publiques. '
      + 'Ctrl+Intro hace lo del botón.</p>'
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
      plan = (await orden('buscar', c)).plan;
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
        + 'eso lo que quieres cambiar.</p>' : '');
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
      // desde la lista no se sabe qué tirada de la página era: se vuelve a
      // pintar lo que se está viendo, que ya sale de la memoria al día
      const y = window.scrollY;
      await enruta();
      window.scrollTo(0, y);
    }
    cuenta();
    devoAvisa('Deshecho: ' + d.cambio);
    return true;
  }

  /* -------------------------------------------- la lista de las corregidas */
  async function verLista() {
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

  /** El fichero de datos tal como está cargado en memoria, si lo está. */
  function cargado(f) {
    const lect = (x) => (x && 'lecturas_' + x.fuente + '.json' === f ? x : null);
    return { 'horas.json': E.horas, 'horas_dias.json': E.horasDias,
      'misa.json': E.misa, 'misal_latino.json': E.latino,
      'prefacios.json': E.prefacios, 'ordinario.json': E.ordinario,
      'devocionario.json': E.devoTodo, 'indice.json': E.indice,
      'calendario.json': E.cal }[f] || lect(E.lecturas) || lect(E.lecturasEs);
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
