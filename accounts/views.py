from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decorators import requiere_administracion_usuarios
from .forms import UsuarioCreacionForm, UsuarioEdicionForm, UsuarioPasswordForm
from .models import CustomUser
from .permissions import ROLES_VALIDOS, es_ultimo_administrador


@require_POST
def cerrar_sesion(request):
    logout(request)
    return redirect("login")


# ---------------------------------------------------------------------------
# Gestión de usuarios (solo ADMIN)
# ---------------------------------------------------------------------------

def _obtener_gestionable(request, pk):
    """Devuelve el usuario a gestionar, o 403 si está fuera de alcance.

    Un ADMIN de aplicación no puede tocar cuentas de superusuario: si
    pudiera cambiarles la contraseña o desactivarlas, tendría de facto el
    control de la cuenta más privilegiada del sistema. Solo un superusuario
    administra a otro superusuario.
    """
    usuario = get_object_or_404(CustomUser, pk=pk)
    if usuario.is_superuser and not request.user.is_superuser:
        raise PermissionDenied(
            "Las cuentas de superusuario solo las administra otro superusuario."
        )
    return usuario


@requiere_administracion_usuarios
def usuarios_lista(request):
    q = request.GET.get("q", "").strip()
    rol = request.GET.get("rol", "").strip()
    if rol not in ROLES_VALIDOS:
        rol = ""

    usuarios = CustomUser.objects.all()
    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    if rol:
        usuarios = usuarios.filter(rol=rol)
    usuarios = usuarios.order_by("username")

    paginator = Paginator(usuarios, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_string = urlencode({k: v for k, v in {"q": q, "rol": rol}.items() if v})

    return render(request, "accounts/usuarios_lista.html", {
        "page_obj": page_obj,
        "q": q,
        "rol": rol,
        "query_string": query_string,
        "rol_choices": CustomUser.Rol.choices,
    })


@requiere_administracion_usuarios
def usuario_nuevo(request):
    if request.method == "POST":
        form = UsuarioCreacionForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request,
                f"Usuario {usuario.username} creado correctamente "
                f"con rol {usuario.get_rol_display()}.",
            )
            return redirect("accounts:usuarios_lista")
    else:
        form = UsuarioCreacionForm()

    return render(request, "accounts/usuario_form.html", {
        "form": form,
        "titulo": "Nuevo usuario",
        "es_nuevo": True,
        "usuario_editado": None,
    })


@requiere_administracion_usuarios
def usuario_editar(request, pk):
    usuario = _obtener_gestionable(request, pk)

    if request.method == "POST":
        form = UsuarioEdicionForm(
            request.POST, instance=usuario, usuario_actual=request.user
        )
        if form.is_valid():
            form.save()
            messages.success(request, f"Usuario {usuario.username} actualizado correctamente.")
            return redirect("accounts:usuarios_lista")
    else:
        form = UsuarioEdicionForm(instance=usuario, usuario_actual=request.user)

    return render(request, "accounts/usuario_form.html", {
        "form": form,
        "titulo": f"Editar — {usuario.username}",
        "es_nuevo": False,
        "usuario_editado": usuario,
    })


@requiere_administracion_usuarios
@require_POST
def usuario_activar(request, pk):
    usuario = _obtener_gestionable(request, pk)
    if usuario.is_active:
        messages.info(request, f"La cuenta de {usuario.username} ya estaba activa.")
    else:
        usuario.is_active = True
        usuario.save(update_fields=["is_active"])
        messages.success(request, f"Cuenta de {usuario.username} activada.")
    return redirect("accounts:usuarios_lista")


@requiere_administracion_usuarios
@require_POST
def usuario_desactivar(request, pk):
    usuario = _obtener_gestionable(request, pk)

    if usuario.pk == request.user.pk:
        messages.error(request, "No puedes desactivar tu propia cuenta.")
    elif not usuario.is_active:
        messages.info(request, f"La cuenta de {usuario.username} ya estaba inactiva.")
    elif es_ultimo_administrador(usuario):
        messages.error(
            request,
            "No se puede desactivar la última cuenta con permisos de "
            "administrador. Asigna ese rol a otro usuario primero.",
        )
    else:
        # Se conserva el registro y todo su historial vinculado: nunca se
        # elimina físicamente un usuario desde esta interfaz.
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        messages.success(request, f"Cuenta de {usuario.username} desactivada.")

    return redirect("accounts:usuarios_lista")


@requiere_administracion_usuarios
def usuario_password(request, pk):
    """Un ADMIN establece una contraseña temporal para otro usuario."""
    usuario = _obtener_gestionable(request, pk)

    if request.method == "POST":
        form = UsuarioPasswordForm(usuario, request.POST)
        if form.is_valid():
            form.save()
            if usuario.pk == request.user.pk:
                # Cambiar la propia contraseña invalida la sesión actual si
                # no se refresca el hash de sesión.
                update_session_auth_hash(request, usuario)
            messages.success(
                request,
                f"Contraseña de {usuario.username} actualizada. "
                "Pídele que la cambie en su primer acceso.",
            )
            return redirect("accounts:usuarios_lista")
    else:
        form = UsuarioPasswordForm(usuario)

    return render(request, "accounts/usuario_password.html", {
        "form": form,
        "usuario_editado": usuario,
    })
