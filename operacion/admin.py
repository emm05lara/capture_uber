from django.contrib import admin
from django.utils import timezone

from .models import AsignacionApp, AsignacionVehiculo


class AsignacionAppInline(admin.TabularInline):
    model = AsignacionApp
    extra = 0
    fields = ["app_transporte", "estatus_app_asignada"]


@admin.register(AsignacionVehiculo)
class AsignacionVehiculoAdmin(admin.ModelAdmin):
    list_display = [
        "vehiculo", "conductor", "plataforma", "socio",
        "cuenta", "fecha_inicio", "fecha_fin", "estatus_display",
    ]
    list_filter = ["plataforma", "socio"]
    list_select_related = ["vehiculo", "conductor", "plataforma", "socio"]
    search_fields = [
        "vehiculo__numero_serie",
        "vehiculo__numero_interno",
        "conductor__nombre_completo",
        "cuenta",
    ]
    ordering = ["-fecha_inicio"]
    date_hierarchy = "fecha_inicio"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo", "conductor"]
    inlines = [AsignacionAppInline]
    actions = ["cerrar_asignaciones"]

    @admin.display(description="Estatus", ordering="fecha_fin")
    def estatus_display(self, obj):
        return obj.estatus_asignacion

    @admin.action(description="Cerrar asignaciones activas (fecha fin = hoy)")
    def cerrar_asignaciones(self, request, queryset):
        activas = queryset.filter(fecha_fin__isnull=True)
        n = activas.update(fecha_fin=timezone.localdate())
        self.message_user(request, f"{n} asignación(es) cerrada(s).")


@admin.register(AsignacionApp)
class AsignacionAppAdmin(admin.ModelAdmin):
    list_display = ["asignacion_vehiculo", "app_transporte", "estatus_app_asignada"]
    list_filter = ["app_transporte", "estatus_app_asignada"]
    list_select_related = [
        "asignacion_vehiculo__vehiculo",
        "asignacion_vehiculo__conductor",
        "app_transporte",
    ]
    search_fields = [
        "asignacion_vehiculo__vehiculo__numero_serie",
        "asignacion_vehiculo__conductor__nombre_completo",
    ]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
