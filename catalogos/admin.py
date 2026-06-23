from django.contrib import admin

from .models import AppTransporte, Color, EntidadFederativa, Marca, ModeloVehiculo


class ModeloVehiculoInline(admin.TabularInline):
    model = ModeloVehiculo
    extra = 0
    fields = ["nombre_modelo_comercial", "version"]
    show_change_link = True


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ["nombre_marca", "fecha_creacion", "fecha_actualizacion"]
    search_fields = ["nombre_marca"]
    ordering = ["nombre_marca"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    inlines = [ModeloVehiculoInline]


@admin.register(ModeloVehiculo)
class ModeloVehiculoAdmin(admin.ModelAdmin):
    list_display = ["__str__", "marca", "nombre_modelo_comercial", "version", "fecha_creacion"]
    list_filter = ["marca"]
    list_select_related = ["marca"]
    search_fields = ["nombre_modelo_comercial", "version", "marca__nombre_marca"]
    ordering = ["marca__nombre_marca", "nombre_modelo_comercial", "version"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["marca"]


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ["nombre_color", "abreviatura_color", "fecha_creacion"]
    search_fields = ["nombre_color", "abreviatura_color"]
    ordering = ["nombre_color"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]


@admin.register(EntidadFederativa)
class EntidadFederativaAdmin(admin.ModelAdmin):
    list_display = ["nombre_entidad", "abreviatura_entidad", "fecha_creacion"]
    search_fields = ["nombre_entidad", "abreviatura_entidad"]
    ordering = ["nombre_entidad"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]


@admin.register(AppTransporte)
class AppTransporteAdmin(admin.ModelAdmin):
    list_display = ["nombre_app", "estatus_app", "fecha_creacion"]
    list_filter = ["estatus_app"]
    search_fields = ["nombre_app"]
    ordering = ["nombre_app"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
