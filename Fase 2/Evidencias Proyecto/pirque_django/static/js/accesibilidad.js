// Menú «Accesibilidad» (WCAG 2.2 AA) para el sitio y el panel.
// Las preferencias se guardan en este navegador (localStorage «pirque_a11y») y se aplican antes de dibujar la página
// con el pequeño script del <head> (ver plantillas base), para que no haya parpadeos.
(() => {
  const CLAVE = 'pirque_a11y';
  const OPCIONES = ['contraste', 'subrayar', 'espaciado', 'legible', 'sin-animaciones'];
  const html = document.documentElement;
  const leer = () => { try { return JSON.parse(localStorage.getItem(CLAVE)) || {}; } catch { return {}; } };
  const guardar = p => { try { localStorage.setItem(CLAVE, JSON.stringify(p)); } catch {} };
  let pref = leer();

  const aplicar = () => {
    for (let n = 1; n <= 3; n++) html.classList.toggle(`a11y-texto-${n}`, pref.texto === n);
    OPCIONES.forEach(o => html.classList.toggle(`a11y-${o}`, !!pref[o]));
    document.querySelectorAll('[data-a11y-opcion]').forEach(b => b.setAttribute('aria-pressed', String(!!pref[b.dataset.a11yOpcion])));
    document.querySelectorAll('[data-a11y-texto]').forEach(b => b.setAttribute('aria-pressed', String((pref.texto || 0) === +b.dataset.a11yTexto)));
    if (pref['sin-animaciones']) document.querySelectorAll('.carousel').forEach(pausarCarrusel);
  };

  // ---------- Carrusel: botón Pausar / Reanudar y sin movimiento automático si la persona lo pidió ----------
  const sinMovimiento = () => pref['sin-animaciones'] || matchMedia('(prefers-reduced-motion: reduce)').matches;
  function pausarCarrusel(c) {
    if (!window.bootstrap) return;
    bootstrap.Carousel.getOrCreateInstance(c).pause();
    c.dataset.pausado = '1';
    const b = c.querySelector('.carrusel-pausa');
    if (b) b.querySelector('span').textContent = b.dataset.reanudar;
  }
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.carousel').forEach(c => {
      const b = c.querySelector('.carrusel-pausa');
      if (b) b.querySelector('span').textContent = b.dataset.pausar;
      if (sinMovimiento()) pausarCarrusel(c);
      if (!b) return;
      b.addEventListener('click', () => {
        const inst = bootstrap.Carousel.getOrCreateInstance(c);
        if (c.dataset.pausado === '1') {
          c.dataset.pausado = ''; inst.cycle(); b.querySelector('span').textContent = b.dataset.pausar;
        } else pausarCarrusel(c);
      });
      // Mientras el carrusel tiene el foco del teclado no cambia solo (2.2.2)
      c.addEventListener('focusin', () => bootstrap.Carousel.getOrCreateInstance(c).pause());
      c.addEventListener('focusout', () => { if (c.dataset.pausado !== '1' && !sinMovimiento()) bootstrap.Carousel.getOrCreateInstance(c).cycle(); });
    });
  });

  // ---------- Menú ----------
  document.addEventListener('DOMContentLoaded', () => {
    const boton = document.getElementById('a11yBoton'), menu = document.getElementById('a11yMenu');
    aplicar();
    if (!boton || !menu) return;
    const abrir = si => {
      menu.hidden = !si; boton.setAttribute('aria-expanded', String(si));
      if (si) menu.querySelector('button')?.focus(); else boton.focus();
    };
    boton.addEventListener('click', () => abrir(menu.hidden));
    menu.addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); abrir(false); } });
    document.addEventListener('click', e => { if (!menu.hidden && !menu.contains(e.target) && !boton.contains(e.target)) { menu.hidden = true; boton.setAttribute('aria-expanded', 'false'); } });
    const avisar = texto => { const v = document.getElementById('a11yEstado'); if (v) { v.textContent = ''; setTimeout(() => { v.textContent = texto; }, 50); } };
    menu.addEventListener('click', e => {
      const t = e.target.closest('button'); if (!t) return;
      if (t.classList.contains('cerrar')) return abrir(false);
      if (t.dataset.a11yTexto !== undefined) pref.texto = +t.dataset.a11yTexto || 0;
      else if (t.dataset.a11yOpcion) pref[t.dataset.a11yOpcion] = !pref[t.dataset.a11yOpcion];
      else if (t.classList.contains('restablecer')) pref = {};
      else return;
      guardar(pref); aplicar(); avisar(menu.dataset.guardado || 'Listo');
    });
  });
})();
