// Identificación del huésped: RUT y teléfono solo reciben números, y el RUT se valida mientras se escribe.
(() => {
  const rut = document.getElementById('id_rut');
  const tel = document.getElementById('id_telefono');
  const ext = document.getElementById('id_extranjero');   // «Soy extranjero»: documento con letras y números
  if (!rut || !tel) return;

  // RUT chileno (módulo 11): solo se usa para AVISAR si el dígito verificador no coincide; no impide continuar.
  const rutValido = r => {
    if (!/^\d{7,8}[\dK]$/.test(r)) return false;
    let suma = 0, mult = 2;
    for (const d of r.slice(0, -1).split('').reverse()) { suma += +d * mult; mult = mult === 7 ? 2 : mult + 1; }
    const e = 11 - (suma % 11), dv = e === 11 ? '0' : e === 10 ? 'K' : String(e);
    return r.slice(-1) === dv;
  };

  const aviso = document.createElement('div');
  aviso.className = 'text-warning small mt-1 fw-bold';   // aviso, no bloquea
  rut.insertAdjacentElement('afterend', aviso);

  const extranjero = () => !!(ext && ext.checked);
  const filtrarRut = () => {
    let v = rut.value.toUpperCase();
    v = extranjero() ? v.replace(/[^0-9A-Z]/g, '').slice(0, 20) : v.replace(/[^0-9K]/g, '').replace(/K(?=.)/g, '').slice(0, 9);
    if (v !== rut.value) rut.value = v;
  };
  const revisarRut = () => {
    const v = rut.value;
    aviso.textContent = !extranjero() && v.length >= 8 && !rutValido(v) ? 'ℹ️ ' + (window.SITIO_T?.rut || '') : '';
  };

  rut.addEventListener('input', () => { filtrarRut(); aviso.textContent = ''; if (rut.value.length >= 8) revisarRut(); });
  rut.addEventListener('blur', revisarRut);
  if (ext) ext.addEventListener('change', () => { rut.maxLength = extranjero() ? 20 : 9; filtrarRut(); revisarRut(); });
  tel.addEventListener('input', () => { const v = tel.value.replace(/\D/g, '').slice(0, 15); if (v !== tel.value) tel.value = v; });
  rut.maxLength = extranjero() ? 20 : 9;
  filtrarRut(); tel.value = tel.value.replace(/\D/g, '');
})();
