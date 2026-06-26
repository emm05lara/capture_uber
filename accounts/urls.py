from django.urls import path

from . import views

urlpatterns = [
    path("logout/", views.cerrar_sesion, name="logout"),
]
