from django.urls import path

from . import views

app_name = "dispositivos"

urlpatterns = [
    path("dispositivos/gps/", views.gps_lista, name="gps_lista"),
    path("dispositivos/gps/nuevo/", views.gps_nuevo, name="gps_nuevo"),
    path("dispositivos/gps/<int:pk>/", views.gps_detalle, name="gps_detalle"),
    path("dispositivos/gps/<int:pk>/editar/", views.gps_editar, name="gps_editar"),
    path("dispositivos/tags/", views.tag_lista, name="tag_lista"),
    path("dispositivos/tags/nuevo/", views.tag_nuevo, name="tag_nuevo"),
    path("dispositivos/tags/<int:pk>/", views.tag_detalle, name="tag_detalle"),
    path("dispositivos/tags/<int:pk>/editar/", views.tag_editar, name="tag_editar"),
]
