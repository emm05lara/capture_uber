from django.urls import path

from . import views

app_name = "vehiculos"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("vehiculos/", views.lista_vehiculos, name="lista"),
    path("vehiculos/nuevo/", views.nuevo_vehiculo, name="nuevo"),   # debe ir antes de <pk>
    path("vehiculos/<int:pk>/", views.detalle_vehiculo, name="detalle"),
]
