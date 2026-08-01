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
    path("vehiculos/<int:pk>/tenencias/nueva/", views.tenencia_nueva, name="tenencia_nueva"),
    path(
        "vehiculos/<int:pk>/tenencias/<int:tenencia_pk>/editar/",
        views.tenencia_editar,
        name="tenencia_editar",
    ),
    path("vehiculos/<int:pk>/adeudos/nuevo/", views.adeudo_nuevo, name="adeudo_nuevo"),
    path("vehiculos/<int:pk>/adeudos/<int:adeudo_pk>/editar/", views.adeudo_editar, name="adeudo_editar"),
    path("vehiculos/<int:pk>/adeudos/<int:adeudo_pk>/pagar/", views.adeudo_pagar, name="adeudo_pagar"),
    path("vehiculos/<int:pk>/adeudos/<int:adeudo_pk>/cancelar/", views.adeudo_cancelar, name="adeudo_cancelar"),
    path("vehiculos/<int:pk>/observaciones/nueva/", views.observacion_nueva, name="observacion_nueva"),
    path(
        "vehiculos/<int:pk>/observaciones/<int:observacion_pk>/editar/",
        views.observacion_editar,
        name="observacion_editar",
    ),
    path("vehiculos/<int:pk>/gps/instalar/", views.gps_instalar, name="gps_instalar"),
    path("vehiculos/<int:pk>/gps/retirar/", views.gps_retirar, name="gps_retirar"),
    path("vehiculos/<int:pk>/gps/cambiar/", views.gps_cambiar, name="gps_cambiar"),
    path("vehiculos/<int:pk>/tag/asignar/", views.tag_asignar, name="tag_asignar"),
    path("vehiculos/<int:pk>/tag/retirar/", views.tag_retirar, name="tag_retirar"),
    path("vehiculos/<int:pk>/tag/cambiar/", views.tag_cambiar, name="tag_cambiar"),
]
