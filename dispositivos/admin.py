from django.contrib import admin
from django.db.models import Prefetch

from .models import AsignacionTag, DispositivoGps, InstalacionGps, TagTelepeaje


class InstalacionGpsInline(admin.TabularInline):
    model = InstalacionGps
    extra = 0
    show_change_link = True
    fields = ["vehiculo", "fecha_instalacion", "fecha_retiro"]
    ordering = ["-fecha_instalacion"]
    autocomplete_fields = ["vehiculo"]


class AsignacionTagInline(admin.TabularInline):
    model = AsignacionTag
    extra = 0
    show_change_link = True
    fields = ["vehiculo", "fecha_inicio", "fecha_fin"]
    ordering = ["-fecha_inicio"]
    autocomplete_fields = ["vehiculo"]


@admin.register(DispositivoGps)
class DispositivoGpsAdmin(admin.ModelAdmin):
    list_display = ["imei", "numero_gps", "estatus_gps", "instalacion_actual_display", "fecha_creacion"]
    list_filter = ["estatus_gps"]
    search_fields = ["imei", "numero_gps"]
    ordering = ["imei"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    inlines = [InstalacionGpsInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            Prefetch(
                "instalaciones",
                queryset=InstalacionGps.objects.filter(
                    fecha_retiro__isnull=True
                ).select_related("vehiculo"),
                to_attr="_instalaciones_actuales",
            )
        )

    @admin.display(description="Vehículo actual")
    def instalacion_actual_display(self, obj):
        insts = getattr(obj, "_instalaciones_actuales", [])
        return insts[0].vehiculo.numero_serie if insts else "—"


@admin.register(InstalacionGps)
class InstalacionGpsAdmin(admin.ModelAdmin):
    list_display = ["gps", "vehiculo", "fecha_instalacion", "fecha_retiro", "es_actual_display"]
    list_filter = ["gps__estatus_gps"]
    list_select_related = ["gps", "vehiculo"]
    search_fields = ["gps__imei", "vehiculo__numero_serie"]
    ordering = ["-fecha_instalacion"]
    date_hierarchy = "fecha_instalacion"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo", "gps"]

    @admin.display(description="¿Actual?", boolean=True)
    def es_actual_display(self, obj):
        return obj.es_actual


@admin.register(TagTelepeaje)
class TagTelepeajeAdmin(admin.ModelAdmin):
    list_display = ["codigo_tag", "codigo_tag_corto", "estatus_tag", "vehiculo_actual_display", "fecha_creacion"]
    list_filter = ["estatus_tag"]
    search_fields = ["codigo_tag", "codigo_tag_corto"]
    ordering = ["codigo_tag"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    inlines = [AsignacionTagInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            Prefetch(
                "asignaciones",
                queryset=AsignacionTag.objects.filter(
                    fecha_fin__isnull=True
                ).select_related("vehiculo"),
                to_attr="_asignaciones_actuales",
            )
        )

    @admin.display(description="Vehículo actual")
    def vehiculo_actual_display(self, obj):
        asigs = getattr(obj, "_asignaciones_actuales", [])
        return asigs[0].vehiculo.numero_serie if asigs else "—"


@admin.register(AsignacionTag)
class AsignacionTagAdmin(admin.ModelAdmin):
    list_display = ["tag", "vehiculo", "fecha_inicio", "fecha_fin", "es_actual_display"]
    list_filter = ["tag__estatus_tag"]
    list_select_related = ["tag", "vehiculo"]
    search_fields = ["tag__codigo_tag", "vehiculo__numero_serie"]
    ordering = ["-fecha_inicio"]
    date_hierarchy = "fecha_inicio"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo", "tag"]

    @admin.display(description="¿Actual?", boolean=True)
    def es_actual_display(self, obj):
        return obj.es_actual
