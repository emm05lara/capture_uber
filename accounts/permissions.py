"""Matriz central de permisos por rol.

Este módulo es la única fuente de verdad sobre qué puede hacer cada rol.
Las vistas, los decoradores y los templates consultan estos helpers en
lugar de comparar `user.rol == "..."` por su cuenta.

Correspondencia entre los roles operativos pedidos y los valores que ya
existían en la base de datos (`accounts.CustomUser.Rol`):

    ADMIN     -> "ADMINISTRADOR"
    OPERADOR  -> "OPERADOR"
    CONSULTA  -> "AUDITOR"   (solo lectura)

Relación entre el rol de aplicación y los flags nativos de Django:

* `rol` controla lo que el usuario puede hacer **dentro de la aplicación**.
* `is_staff` controla el acceso a **Django Admin** y es independiente del
  rol: tener rol ADMIN no otorga `is_staff` ni `is_superuser`.
* `is_superuser` es el escape de emergencia: siempre tiene acceso total,
  cualquiera que sea su rol.

Ninguna función de este módulo consulta la base de datos: todo se resuelve
con los atributos que ya vienen cargados en `request.user`, de modo que
evaluar permisos por fila en un template no genera consultas extra.
"""

ROL_ADMIN = "ADMINISTRADOR"
ROL_OPERADOR = "OPERADOR"
ROL_CONSULTA = "AUDITOR"

ROLES_VALIDOS = (ROL_ADMIN, ROL_OPERADOR, ROL_CONSULTA)

# Etiquetas legibles, independientes del valor almacenado.
ROLES_LEGIBLES = {
    ROL_ADMIN: "Administrador",
    ROL_OPERADOR: "Operador",
    ROL_CONSULTA: "Consulta (solo lectura)",
}

# --- Acciones controladas -------------------------------------------------
ACCION_CONSULTAR = "puede_consultar"
ACCION_EXPORTAR = "puede_exportar"
ACCION_CAPTURAR = "puede_capturar"
ACCION_EDITAR = "puede_editar"
ACCION_EJECUTAR_ACCIONES = "puede_ejecutar_acciones"
ACCION_ADMINISTRAR_USUARIOS = "puede_administrar_usuarios"
# `puede_acceder_admin` no depende del rol: se resuelve con `is_staff`.
ACCION_ACCEDER_ADMIN = "puede_acceder_admin"

# --- Matriz ---------------------------------------------------------------
# Política de exportaciones: los tres roles pueden exportar información
# operativa de lectura. La administración de usuarios nunca se exporta.
MATRIZ_PERMISOS = {
    ROL_ADMIN: frozenset({
        ACCION_CONSULTAR,
        ACCION_EXPORTAR,
        ACCION_CAPTURAR,
        ACCION_EDITAR,
        ACCION_EJECUTAR_ACCIONES,
        ACCION_ADMINISTRAR_USUARIOS,
    }),
    ROL_OPERADOR: frozenset({
        ACCION_CONSULTAR,
        ACCION_EXPORTAR,
        ACCION_CAPTURAR,
        ACCION_EDITAR,
        ACCION_EJECUTAR_ACCIONES,
    }),
    ROL_CONSULTA: frozenset({
        ACCION_CONSULTAR,
        ACCION_EXPORTAR,
    }),
}

_SIN_PERMISOS = frozenset()


def _usuario_operativo(user):
    """True si hay un usuario autenticado y activo detrás de la petición."""
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", False)
    )


def rol_de(user):
    """Rol de aplicación del usuario, o cadena vacía si no aplica."""
    if not _usuario_operativo(user):
        return ""
    rol = getattr(user, "rol", "")
    return rol if rol in ROLES_VALIDOS else ""


def rol_legible(user):
    """Etiqueta del rol para mostrar en la interfaz."""
    if not _usuario_operativo(user):
        return ""
    if getattr(user, "is_superuser", False):
        return "Superusuario"
    return ROLES_LEGIBLES.get(rol_de(user), "Sin rol asignado")


def tiene_permiso(user, accion):
    """Punto único de decisión: ¿este usuario puede ejecutar `accion`?"""
    if not _usuario_operativo(user):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if accion == ACCION_ACCEDER_ADMIN:
        return bool(getattr(user, "is_staff", False))
    return accion in MATRIZ_PERMISOS.get(rol_de(user), _SIN_PERMISOS)


# --- Atajos legibles ------------------------------------------------------

def puede_consultar(user):
    return tiene_permiso(user, ACCION_CONSULTAR)


def puede_exportar(user):
    return tiene_permiso(user, ACCION_EXPORTAR)


def puede_capturar(user):
    return tiene_permiso(user, ACCION_CAPTURAR)


def puede_editar(user):
    return tiene_permiso(user, ACCION_EDITAR)


def puede_ejecutar_acciones(user):
    return tiene_permiso(user, ACCION_EJECUTAR_ACCIONES)


def puede_administrar_usuarios(user):
    return tiene_permiso(user, ACCION_ADMINISTRAR_USUARIOS)


def puede_acceder_admin(user):
    """Acceso a Django Admin: lo sigue determinando `is_staff`."""
    return tiene_permiso(user, ACCION_ACCEDER_ADMIN)


def puede_escribir(user):
    """Atajo para templates: ¿puede modificar algo (capturar/editar/actuar)?"""
    return (
        puede_capturar(user)
        or puede_editar(user)
        or puede_ejecutar_acciones(user)
    )


# --- Reglas de negocio sobre la propia administración de usuarios ---------

def es_administrador_operativo(usuario):
    """True si este usuario cuenta como ADMIN para el sistema.

    Un superusuario cuenta siempre, aunque su rol de aplicación sea otro.
    """
    return bool(
        usuario.is_active
        and (usuario.is_superuser or usuario.rol == ROL_ADMIN)
    )


def es_ultimo_administrador(usuario):
    """True si desactivar o degradar a `usuario` dejaría al sistema sin ADMIN."""
    from django.db.models import Q

    if not es_administrador_operativo(usuario):
        return False
    otros = (
        type(usuario)
        .objects.filter(is_active=True)
        .filter(Q(rol=ROL_ADMIN) | Q(is_superuser=True))
        .exclude(pk=usuario.pk)
    )
    return not otros.exists()
