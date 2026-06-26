/* tema.js — selector claro/oscuro para Bootstrap 5.3
   Persiste en localStorage bajo la clave 'flotilla-tema'.
   Se carga después del bundle de Bootstrap para poder usar
   el atributo data-bs-theme del estándar BS 5.3. */
(function () {
    'use strict';

    var KEY = 'flotilla-tema';

    function aplicar(tema) {
        document.documentElement.setAttribute('data-bs-theme', tema);
        localStorage.setItem(KEY, tema);
        actualizarBoton(tema);
    }

    function actualizarBoton(tema) {
        var btn   = document.getElementById('btn-toggle-tema');
        if (!btn) return;
        var icono = btn.querySelector('i');
        var texto = btn.querySelector('span');
        if (tema === 'dark') {
            if (icono) icono.className = 'bi bi-sun-fill me-1';
            if (texto) texto.textContent = 'Cambiar a tema claro';
        } else {
            if (icono) icono.className = 'bi bi-moon-stars-fill me-1';
            if (texto) texto.textContent = 'Cambiar a tema oscuro';
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        /* Sincroniza el botón con el tema ya activo (puede haber sido
           aplicado por el script anti-parpadeo del <head>). */
        var actual = document.documentElement.getAttribute('data-bs-theme') || 'light';
        actualizarBoton(actual);

        var btn = document.getElementById('btn-toggle-tema');
        if (btn) {
            btn.addEventListener('click', function () {
                var ahora = document.documentElement.getAttribute('data-bs-theme') || 'light';
                aplicar(ahora === 'dark' ? 'light' : 'dark');
            });
        }
    });
})();
