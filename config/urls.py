from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Vista propia de logout va antes para tener prioridad sobre django.contrib.auth.urls
    path("accounts/", include("accounts.urls")),
    # Login, reset de contraseña y demás vistas built-in de autenticación
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("vehiculos.urls")),
]
