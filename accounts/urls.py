from django.urls import path

from . import views

app_name = "accounts"

# Este módulo se monta en la raíz (`path("", include("accounts.urls"))`)
# para que la gestión de usuarios viva en `/usuarios/…`. La ruta de logout
# conserva su prefijo original `/accounts/logout/` para no cambiar una URL
# que ya estaba en uso.
urlpatterns = [
    path("accounts/logout/", views.cerrar_sesion, name="logout"),
    path("usuarios/", views.usuarios_lista, name="usuarios_lista"),
    path("usuarios/nuevo/", views.usuario_nuevo, name="usuario_nuevo"),
    path("usuarios/<int:pk>/editar/", views.usuario_editar, name="usuario_editar"),
    path("usuarios/<int:pk>/activar/", views.usuario_activar, name="usuario_activar"),
    path("usuarios/<int:pk>/desactivar/", views.usuario_desactivar, name="usuario_desactivar"),
    path("usuarios/<int:pk>/contrasena/", views.usuario_password, name="usuario_password"),
]
