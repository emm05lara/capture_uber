from django.urls import path

from . import views

app_name = "vehiculos"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("vehiculos/", views.lista_vehiculos, name="lista"),
    path("vehiculos/nuevo/", views.nuevo_vehiculo, name="nuevo"),
    path("vehiculos/<int:pk>/", views.detalle_vehiculo, name="detalle"),
    path("vehiculos/<int:pk>/editar/", views.editar_vehiculo, name="editar"),
    path("vehiculos/<int:pk>/placas/nueva/", views.nueva_placa, name="nueva_placa"),
    path("vehiculos/<int:pk>/estatus/", views.cambiar_estatus, name="cambiar_estatus"),
]
