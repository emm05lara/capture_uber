from django.urls import path

from . import views

app_name = "actores"

urlpatterns = [
    path("conductores/", views.conductores_lista, name="conductores_lista"),
    path("conductores/nuevo/", views.conductor_nuevo, name="conductor_nuevo"),
    path("conductores/<int:pk>/", views.conductor_detalle, name="conductor_detalle"),
    path("conductores/<int:pk>/editar/", views.conductor_editar, name="conductor_editar"),
]
