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
    path("vehiculos/<int:pk>/asignar-conductor/", views.asignar_conductor, name="asignar_conductor"),
    path("vehiculos/<int:pk>/cambiar-conductor/", views.cambiar_conductor, name="cambiar_conductor"),
    path("vehiculos/<int:pk>/asignacion/finalizar/", views.finalizar_asignacion, name="finalizar_asignacion"),
    path("vehiculos/<int:pk>/polizas/nueva/", views.poliza_nueva, name="poliza_nueva"),
    path("vehiculos/<int:pk>/polizas/<int:poliza_pk>/editar/", views.poliza_editar, name="poliza_editar"),
    path("vehiculos/<int:pk>/verificaciones/nueva/", views.verificacion_nueva, name="verificacion_nueva"),
    path(
        "vehiculos/<int:pk>/verificaciones/<int:verificacion_pk>/editar/",
        views.verificacion_editar,
        name="verificacion_editar",
    ),
    path("vehiculos/<int:pk>/tarjetas/nueva/", views.tarjeta_nueva, name="tarjeta_nueva"),
    path("vehiculos/<int:pk>/tarjetas/<int:tarjeta_pk>/editar/", views.tarjeta_editar, name="tarjeta_editar"),
]
