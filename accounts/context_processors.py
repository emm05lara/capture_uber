"""Expone la matriz de permisos a los templates.

Evita repetir en cada plantilla comparaciones del tipo
`{% if user.rol == "ADMINISTRADOR" %}`. Se resuelve en memoria a partir de
`request.user`, sin consultas adicionales a la base de datos.
"""

from . import permissions


def permisos(request):
    user = getattr(request, "user", None)
    return {
        "puede_consultar": permissions.puede_consultar(user),
        "puede_exportar": permissions.puede_exportar(user),
        "puede_capturar": permissions.puede_capturar(user),
        "puede_editar": permissions.puede_editar(user),
        "puede_ejecutar_acciones": permissions.puede_ejecutar_acciones(user),
        "puede_administrar_usuarios": permissions.puede_administrar_usuarios(user),
        "puede_acceder_admin": permissions.puede_acceder_admin(user),
        "puede_escribir": permissions.puede_escribir(user),
        "rol_legible": permissions.rol_legible(user),
    }
