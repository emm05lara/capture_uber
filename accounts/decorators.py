"""Decoradores y mixins que aplican la matriz de `accounts.permissions`.

Todas las vistas de la aplicación se protegen con estos envoltorios en vez
de comprobar el rol a mano. La validación es siempre de servidor: ocultar
el botón en el template no sustituye a esto.

Comportamiento:

* Usuario **no autenticado** (o cuya cuenta fue desactivada, porque el
  backend de Django deja de reconocer su sesión): redirección al login,
  como en las fases anteriores.
* Usuario **autenticado sin permiso**: `PermissionDenied`, que Django
  convierte en HTTP 403 con la plantilla `403.html`. Nunca un redirect
  silencioso.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .permissions import (
    ACCION_ADMINISTRAR_USUARIOS,
    ACCION_CAPTURAR,
    ACCION_CONSULTAR,
    ACCION_EDITAR,
    ACCION_EJECUTAR_ACCIONES,
    ACCION_EXPORTAR,
    tiene_permiso,
)

MENSAJE_SIN_PERMISO = "Tu rol no tiene permiso para realizar esta operación."


def requiere_permiso(accion):
    """Devuelve un decorador que exige `accion` sobre `request.user`."""

    def decorador(vista):
        @wraps(vista)
        def _envoltura(request, *args, **kwargs):
            if not tiene_permiso(request.user, accion):
                raise PermissionDenied(MENSAJE_SIN_PERMISO)
            return vista(request, *args, **kwargs)

        return login_required(_envoltura)

    return decorador


# Atajos: `requiere_permiso(accion)` ya devuelve el decorador listo.
requiere_consulta = requiere_permiso(ACCION_CONSULTAR)
requiere_exportacion = requiere_permiso(ACCION_EXPORTAR)
requiere_captura = requiere_permiso(ACCION_CAPTURAR)
requiere_edicion = requiere_permiso(ACCION_EDITAR)
requiere_accion_operativa = requiere_permiso(ACCION_EJECUTAR_ACCIONES)
requiere_administracion_usuarios = requiere_permiso(ACCION_ADMINISTRAR_USUARIOS)


class PermisoRequeridoMixin(LoginRequiredMixin):
    """Equivalente de `requiere_permiso` para vistas basadas en clases."""

    accion_requerida = ACCION_CONSULTAR

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not tiene_permiso(
            request.user, self.accion_requerida
        ):
            raise PermissionDenied(MENSAJE_SIN_PERMISO)
        return super().dispatch(request, *args, **kwargs)
