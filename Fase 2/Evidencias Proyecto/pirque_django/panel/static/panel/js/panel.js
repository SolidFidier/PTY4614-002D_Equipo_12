const csrf = document.querySelector('meta[name=csrf]')?.content;
const post = async (url, body) => {
  let r;
  try { r = await fetch(url, {method: 'POST', body, headers: {'X-CSRFToken': csrf}}); }
  catch { return {ok: false, error: 'Sin conexión con el servidor.'}; }
  try { return await r.json(); }
  catch { return {ok: false, error: `El servidor respondió con un error (${r.status}). Revisa la terminal de runserver.`}; }
};
// Avisos grandes y visibles (en lugar de ventanas emergentes); se recuerdan al recargar la página
const mostrarAviso = (msg, tipo = 'success') => {
  const c = document.getElementById('avisos'); if (!c) return alert(msg);
  const d = document.createElement('div');
  d.className = `alert alert-${tipo} alert-dismissible fs-5 shadow`; d.setAttribute('role', 'alert');
  d.innerHTML = `<i class="bi ${tipo === 'danger' ? 'bi-exclamation-octagon' : 'bi-check-circle'} me-2"></i><span></span><button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Cerrar"></button>`;
  d.querySelector('span').textContent = msg; c.appendChild(d);
  // No se borra sola (WCAG 2.2.1): se cierra con la ×, así hay tiempo de leerla con calma
};
const listo = r => { if (r.aviso) sessionStorage.setItem('panelAviso', r.aviso); location.reload(); };
document.addEventListener('DOMContentLoaded', () => { const a = sessionStorage.getItem('panelAviso'); if (a) { sessionStorage.removeItem('panelAviso'); mostrarAviso(a); } });
document.addEventListener('click', async e => {
  const ed = e.target.closest('[data-edit]');            // abre modal rellenando campos por nombre
  if (ed) {
    const m = document.querySelector(ed.dataset.edit), f = m.querySelector('form');
    if (f) { f.reset(); if (ed.dataset.url) f.action = ed.dataset.url;
      [...f.elements].forEach(i => { if (i.name && i.type !== 'file' && ed.dataset[i.name] !== undefined) i.value = ed.dataset[i.name]; });
      f.querySelector('.form-error')?.classList.add('d-none'); }
    m.querySelectorAll('[data-fill]').forEach(n => n.textContent = ed.dataset[n.dataset.fill] || '—');
    m.querySelectorAll('[data-post-attr]').forEach(n => n.dataset.post = ed.dataset[n.dataset.postAttr]);
    // Partes que se muestran solo si el botón trae (o no trae) cierto dato; p. ej. el historial de cambios de una reserva
    m.querySelectorAll('[data-show-if]').forEach(n => n.classList.toggle('d-none', !ed.dataset[n.dataset.showIf]));
    m.querySelectorAll('[data-show-if-not]').forEach(n => n.classList.toggle('d-none', !!ed.dataset[n.dataset.showIfNot]));
    m.querySelectorAll('[data-url-attr]').forEach(n => n.dataset.url = ed.dataset[n.dataset.urlAttr] || '');
    m.querySelectorAll('.originales').forEach(n => { n.classList.add('d-none'); n.replaceChildren(); });
    m.querySelectorAll('[data-ver-originales]').forEach(b => { b.setAttribute('aria-expanded', 'false'); b.querySelector('span').textContent = 'Ver datos originales'; });
    if (ed.dataset.vistaUrl) {                       // la reserva fue revisada: deja de destacarse como «Nueva»
      post(ed.dataset.vistaUrl);
      const fila = ed.closest('tr'); fila?.classList.remove('fila-nueva'); fila?.querySelector('.etq-nueva')?.remove();
      delete ed.dataset.vistaUrl;
    }
    bootstrap.Modal.getOrCreateInstance(m).show();
  }
  const vo = e.target.closest('[data-ver-originales]');   // reserva: comparar los datos originales con los actuales
  if (vo) {
    const caja = vo.closest('.modal').querySelector('.originales'), etq = vo.querySelector('span');
    if (!caja.classList.contains('d-none')) {
      caja.classList.add('d-none'); etq.textContent = 'Ver datos originales'; vo.setAttribute('aria-expanded', 'false'); return;
    }
    let j;
    try { j = await (await fetch(vo.dataset.url, {headers: {'X-Requested-With': 'fetch'}})).json(); }
    catch { j = {ok: false, error: 'No se pudieron cargar los datos originales. Revisa la conexión e inténtalo de nuevo.'}; }
    if (!j.ok) return mostrarAviso(j.error, 'danger');
    caja.replaceChildren(tablaOriginales(j));
    caja.classList.remove('d-none'); etq.textContent = 'Ocultar datos originales'; vo.setAttribute('aria-expanded', 'true');
    return;
  }
  const del = e.target.closest('[data-delete]');
  if (del && confirm(del.dataset.msg || '¿Eliminar este registro?')) {
    const r = await post(del.dataset.delete); r.ok ? listo(r) : mostrarAviso(r.error, 'danger');
  }
  const cp = e.target.closest('[data-copiar]');   // copiar el enlace personal de una reseña
  if (cp) {
    try { await navigator.clipboard.writeText(cp.dataset.copiar); mostrarAviso('Enlace copiado. Ya puedes pegarlo en WhatsApp o en un correo.'); }
    catch { window.prompt('Copia este enlace (Ctrl+C):', cp.dataset.copiar); }
  }
  const p = e.target.closest('[data-post]');
  if (p && (!p.dataset.msg || confirm(p.dataset.msg))) { const r = await post(p.dataset.post); r.ok ? listo(r) : mostrarAviso(r.error, 'danger'); }
});
// Tabla «Dato · Original · Actual» de una reserva; los datos que cambiaron se marcan en amarillo.
// Se arma con textContent (nunca innerHTML) para que ningún dato pueda ejecutar código.
function tablaOriginales(j) {
  const frag = document.createDocumentFragment(), el = (tag, txt, cls) => { const n = document.createElement(tag); if (txt !== undefined) n.textContent = txt; if (cls) n.className = cls; return n; };
  if (!j.modificada) { frag.append(el('p', j.aviso, 'mb-0')); return frag; }
  frag.append(el('p', `Datos que tenía la reserva antes del primer cambio. Cambiaron ${j.cambios} dato(s), marcados en amarillo.`, 'mb-2'));
  const tabla = el('table', undefined, 'table table-sm tabla-originales mb-0'), cab = el('tr');
  ['Dato', 'Original', 'Actual'].forEach(t => cab.append(el('th', t)));
  tabla.append(el('thead')); tabla.tHead.append(cab);
  const cuerpo = el('tbody');
  j.filas.forEach(f => { const tr = el('tr', undefined, f.cambio ? 'dato-cambiado' : ''); tr.append(el('td', f.dato), el('td', f.original), el('td', f.actual)); cuerpo.append(tr); });
  tabla.append(cuerpo);
  const envoltura = el('div', undefined, 'table-responsive'); envoltura.append(tabla); frag.append(envoltura);
  return frag;
}
document.addEventListener('submit', async e => {         // formularios AJAX de las modales
  const f = e.target.closest('form[data-ajax]'); if (!f) return;
  e.preventDefault();
  const r = await post(f.action, new FormData(f));
  if (r.ok) return listo(r);
  const b = f.querySelector('.form-error'); b.textContent = r.error; b.classList.remove('d-none');
});

// Burbujas del menú (mensajes sin gestionar y reservas pendientes): se actualizan solas cada 20 segundos
// y desaparecen cuando llegan a cero.
(() => {
  const bm = document.getElementById('badgeMensajes'), br = document.getElementById('badgeReservas'), bg = document.getElementById('badgeReservasGrupo'), bmov = document.getElementById('badgeMovil');
  if (!bm) return;
  const pintar = (b, n) => { if (b) { b.textContent = n; b.classList.toggle('d-none', !n); } };
  const actualizar = async () => {
    try {
      const j = await (await fetch(bm.dataset.url, {headers: {'X-Requested-With': 'fetch'}})).json();
      pintar(bm, j.pendientes); pintar(br, j.reservas); pintar(bg, j.reservas); pintar(bmov, j.reservas);
    } catch {}
  };
  setInterval(actualizar, 20000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) actualizar(); });
})();

// Filtros de reservas de la barra lateral: se pueden colapsar/expandir y se recuerda la elección.
// (Si estás dentro de Reservas, el grupo se abre solo.)
(() => {
  const sub = document.getElementById('subReservas'); if (!sub) return;
  const guardado = localStorage.getItem('panelSubReservas');
  const enReservas = sub.classList.contains('show');
  if (!enReservas && guardado === 'abierto') bootstrap.Collapse.getOrCreateInstance(sub, {toggle: false}).show();
  sub.addEventListener('shown.bs.collapse', () => localStorage.setItem('panelSubReservas', 'abierto'));
  sub.addEventListener('hidden.bs.collapse', () => localStorage.setItem('panelSubReservas', 'cerrado'));
})();

// Lista de reservas: botón «Actualizar» y actualización automática cada 30 s (sin recargar la página ni perder los filtros).
// No se actualiza mientras hay una ventana de edición abierta, para no perder lo que se está escribiendo.
(() => {
  const btn = document.getElementById('btnActualizar'); if (!btn) return;
  const sello = document.getElementById('ultimaActualizacion');
  const auto = document.getElementById('chkAutoActualizar');   // se puede pausar la actualización automática (WCAG 2.2.2)
  if (auto) {
    auto.checked = localStorage.getItem('panelAutoActualizar') !== 'no';
    auto.addEventListener('change', () => localStorage.setItem('panelAutoActualizar', auto.checked ? 'si' : 'no'));
  }
  const refrescar = async (manual) => {
    if (!manual && (document.querySelector('.modal.show') || (auto && !auto.checked))) return;
    btn.classList.add('girando');
    try {
      const html = await (await fetch(location.href, {headers: {'X-Requested-With': 'fetch'}})).text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      ['pillsReservas', 'listaReservas'].forEach(id => { const nuevo = doc.getElementById(id), actual = document.getElementById(id); if (nuevo && actual) actual.replaceWith(nuevo); });
      sello.textContent = 'Actualizado ' + new Date().toLocaleTimeString('es-CL');
    } catch { sello.textContent = 'No se pudo actualizar'; }
    btn.classList.remove('girando');
  };
  btn.addEventListener('click', () => refrescar(true));
  setInterval(() => { if (!document.hidden) refrescar(false); }, 30000);
  sello.textContent = 'Actualizado ' + new Date().toLocaleTimeString('es-CL');
})();

// Calendario de las ventanas de reserva: muestra en ROJO las fechas ocupadas (reservas aceptadas).
// Se sincroniza con los campos de fecha en ambos sentidos.
document.addEventListener('shown.bs.modal', async e => {
  const cont = e.target.querySelector('.cal-reserva');
  if (!cont || typeof flatpickr === 'undefined') return;
  const f = e.target.querySelector('form'), ent = f.elements.fecha_entrada, sal = f.elements.fecha_salida;
  const aviso = e.target.querySelector('.aviso-ocupado');
  const id = (f.action.match(/reservas\/(\d+)\/editar/) || [])[1] || '';
  let ocupadas = [];
  try { ocupadas = (await (await fetch(`${cont.dataset.url}?excluir=${id}`)).json()).ocupadas; } catch {}
  const dia = s => new Date(s + 'T00:00:00');
  const quien = d => ocupadas.find(o => d >= dia(o.from) && d <= dia(o.to));
  const iso = d => flatpickr.formatDate(d, 'Y-m-d');
  const choca = (a, b) => { for (let d = new Date(a); d < b; d.setDate(d.getDate() + 1)) if (quien(d)) return true; return false; };
  const revisar = (a, b) => aviso.classList.toggle('d-none', !(a && b && choca(a, b)));
  cont._fp?.destroy();
  cont._fp = flatpickr(cont, {
    inline: true, mode: 'range', locale: 'es', showMonths: window.innerWidth >= 992 ? 2 : 1,
    defaultDate: ent.value && sal.value ? [ent.value, sal.value] : null,
    onDayCreate: (_, __, ___, el) => { const o = quien(el.dateObj); if (o) { el.classList.add('dia-ocupado'); el.title = 'Ocupado: ' + o.quien; } },
    onChange: sel => { if (sel.length === 2) { ent.value = iso(sel[0]); sal.value = iso(sel[1]); } revisar(sel[0], sel[1]); }
  });
  if (ent.value && sal.value) revisar(dia(ent.value), dia(sal.value));
  const desdeCampos = () => {
    if (ent.value && sal.value && sal.value > ent.value) { cont._fp.setDate([ent.value, sal.value], false); revisar(dia(ent.value), dia(sal.value)); }
  };
  ent.onchange = sal.onchange = desdeCampos;
});
