from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("vehiculos.urls")),
    path("", include("actores.urls")),
    path("", include("dispositivos.urls")),
]

# Acceso denegado: usuario autenticado sin permiso para la operación.
# Renderiza `templates/403.html` con HTTP 403 real (no un redirect).
handler403 = "django.views.defaults.permission_denied"
