/* Gestión dinámica del formset de referencias personales del conductor.
   Permite agregar filas nuevas y marcar filas para eliminar sin recargar
   la página, respetando el management_form del formset de Django. */
(function () {
    "use strict";

    var container = document.getElementById("referencias-container");
    var addBtn = document.getElementById("btn-agregar-referencia");
    var template = document.getElementById("template-referencia-vacia");
    var prefix = "referencias";
    var totalFormsInput = document.getElementById("id_" + prefix + "-TOTAL_FORMS");

    if (!container || !addBtn || !template || !totalFormsInput) {
        return;
    }

    function filasActivas() {
        var filas = container.querySelectorAll(".referencia-row");
        var total = 0;
        for (var i = 0; i < filas.length; i++) {
            if (filas[i].dataset.eliminada !== "1") {
                total++;
            }
        }
        return total;
    }

    addBtn.addEventListener("click", function () {
        var indice = parseInt(totalFormsInput.value, 10);
        var html = template.innerHTML.split("__prefix__").join(indice);
        var envoltura = document.createElement("div");
        envoltura.innerHTML = html.trim();
        var nuevaFila = envoltura.firstElementChild;
        container.appendChild(nuevaFila);
        totalFormsInput.value = indice + 1;
    });

    container.addEventListener("click", function (event) {
        var boton = event.target.closest(".btn-eliminar-referencia");
        if (!boton) {
            return;
        }
        var fila = boton.closest(".referencia-row");
        if (!fila) {
            return;
        }

        if (filasActivas() <= 1) {
            window.alert("El conductor debe conservar al menos una referencia personal.");
            return;
        }

        var campoId = fila.querySelector('input[name$="-id"]');
        var esExistente = campoId && campoId.value;

        if (esExistente) {
            var checkboxEliminar = fila.querySelector('input[name$="-DELETE"]');
            if (checkboxEliminar) {
                checkboxEliminar.checked = true;
            }
            fila.style.display = "none";
            fila.dataset.eliminada = "1";
        } else {
            fila.remove();
        }
    });
})();
