"""Formularios de administración de usuarios.

Se apoyan en los formularios nativos de Django (`UserCreationForm`,
`AdminPasswordChangeForm`) adaptados al `CustomUser` del proyecto, de modo
que el hasheo y la validación de contraseñas siguen siendo los estándar.

Decisiones de seguridad de esta interfaz:

* `is_superuser` **no** se expone: nadie puede autootorgarse superusuario
  desde la GUI. Solo se concede desde Django Admin o `createsuperuser`.
* `is_staff` tampoco se expone: el acceso a Django Admin se sigue
  administrando fuera de esta pantalla, así el rol ADMIN de la aplicación
  no se convierte en una vía para entrar al Admin.
* Nunca se muestra el hash de la contraseña ni la contraseña actual.
"""

from django import forms
from django.contrib.auth.forms import AdminPasswordChangeForm, UserCreationForm

from .models import CustomUser
from .permissions import ROL_ADMIN, es_ultimo_administrador

CAMPOS_DATOS = ("username", "first_name", "last_name", "email", "rol")


def _aplicar_estilo_bootstrap(form):
    for nombre, campo in form.fields.items():
        if isinstance(campo.widget, forms.CheckboxInput):
            campo.widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(campo.widget, forms.Select):
            campo.widget.attrs.setdefault("class", "form-select")
        else:
            campo.widget.attrs.setdefault("class", "form-control")


class UsuarioCreacionForm(UserCreationForm):
    """Alta de usuario: pide contraseña y confirmación, y asigna rol."""

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = CAMPOS_DATOS
        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre(s)",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "rol": "Rol en el sistema",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rol"].required = True
        _aplicar_estilo_bootstrap(self)

    def save(self, commit=True):
        usuario = super().save(commit=False)
        # Blindaje explícito: el alta desde la GUI nunca crea cuentas
        # privilegiadas de Django, sea cual sea el rol de aplicación.
        usuario.is_superuser = False
        usuario.is_staff = False
        usuario.is_active = True
        if commit:
            usuario.save()
        return usuario


class UsuarioEdicionForm(forms.ModelForm):
    """Edición de datos, rol y estado. No toca la contraseña."""

    class Meta:
        model = CustomUser
        fields = CAMPOS_DATOS + ("is_active",)
        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre(s)",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "rol": "Rol en el sistema",
            "is_active": "Cuenta activa",
        }

    def __init__(self, *args, usuario_actual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario_actual = usuario_actual
        _aplicar_estilo_bootstrap(self)

    def _es_su_propia_cuenta(self):
        return (
            self.usuario_actual is not None
            and self.instance.pk == self.usuario_actual.pk
        )

    def clean(self):
        datos = super().clean()
        activo = datos.get("is_active", True)
        rol_nuevo = datos.get("rol")

        if self._es_su_propia_cuenta():
            if not activo:
                self.add_error(
                    "is_active",
                    "No puedes desactivar tu propia cuenta.",
                )
            if (
                rol_nuevo != ROL_ADMIN
                and not self.instance.is_superuser
            ):
                self.add_error(
                    "rol",
                    "No puedes quitarte a ti mismo el rol de administrador. "
                    "Pide a otro administrador que haga el cambio.",
                )

        # Si esta cuenta es la última con acceso administrativo, no se le
        # puede quitar ni el rol ni el estado activo: el sistema quedaría
        # sin nadie capaz de administrar usuarios.
        pierde_admin = (not activo) or (
            rol_nuevo != ROL_ADMIN and not self.instance.is_superuser
        )
        if pierde_admin and self.instance.pk and es_ultimo_administrador(self.instance):
            self.add_error(
                None,
                "Esta es la última cuenta con permisos de administrador. "
                "Asigna el rol de administrador a otro usuario antes de "
                "desactivarla o cambiarle el rol.",
            )

        return datos


class UsuarioPasswordForm(AdminPasswordChangeForm):
    """Un ADMIN establece una contraseña temporal para otro usuario.

    Se desactiva la opción nativa de "contraseña inutilizable": desde esta
    pantalla siempre se asigna una contraseña real, hasheada por Django.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("usable_password", None)
        self.fields["password1"].required = True
        self.fields["password2"].required = True
        _aplicar_estilo_bootstrap(self)
