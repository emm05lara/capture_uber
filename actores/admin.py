from django.contrib import admin

from .models import (
    Aseguradora,
    Conductor,
    Organizacion,
    Persona,
    PlataformaOperativa,
    Socio,
    TitularPoliza,
)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = [
        "nombre_completo", "telefono", "correo",
        "es_conductor", "es_titular_poliza", "fecha_creacion",
    ]
    search_fields = ["nombre_completo", "telefono", "correo"]
    ordering = ["nombre_completo"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("conductor", "titularpoliza")

    @admin.display(description="¿Conductor?", boolean=True)
    def es_conductor(self, obj):
        return hasattr(obj, "conductor")

    @admin.display(description="¿Titular póliza?", boolean=True)
    def es_titular_poliza(self, obj):
        return hasattr(obj, "titularpoliza")


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = [
        "nombre_completo", "telefono", "correo",
        "estatus_conductor", "numero_licencia", "tipo_licencia",
        "fecha_vencimiento_licencia", "licencia_vigente_display",
    ]
    list_filter = ["estatus_conductor", "tipo_licencia"]
    search_fields = ["nombre_completo", "telefono", "correo", "numero_licencia", "curp"]
    ordering = ["nombre_completo"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion", "licencia_vigente_display"]
    actions = ["marcar_activo", "marcar_inactivo", "marcar_bloqueado", "marcar_baja"]
    fieldsets = (
        ("Datos personales", {
            "fields": ("nombre_completo", "telefono", "correo", "estatus_conductor"),
        }),
        ("Licencia de conducir", {
            "fields": (
                "numero_licencia", "tipo_licencia",
                "fecha_vencimiento_licencia", "licencia_vigente_display",
            ),
        }),
        ("Identificación", {
            "fields": ("curp",),
        }),
        ("Auditoría", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Licencia vigente", boolean=True)
    def licencia_vigente_display(self, obj):
        return obj.licencia_vigente

    @admin.action(description="Marcar seleccionados como ACTIVO")
    def marcar_activo(self, request, queryset):
        n = queryset.update(estatus_conductor="ACTIVO")
        self.message_user(request, f"{n} conductor(es) marcados como ACTIVO.")

    @admin.action(description="Marcar seleccionados como INACTIVO")
    def marcar_inactivo(self, request, queryset):
        n = queryset.update(estatus_conductor="INACTIVO")
        self.message_user(request, f"{n} conductor(es) marcados como INACTIVO.")

    @admin.action(description="Marcar seleccionados como BLOQUEADO")
    def marcar_bloqueado(self, request, queryset):
        n = queryset.update(estatus_conductor="BLOQUEADO")
        self.message_user(request, f"{n} conductor(es) marcados como BLOQUEADO.")

    @admin.action(description="Marcar seleccionados como BAJA")
    def marcar_baja(self, request, queryset):
        n = queryset.update(estatus_conductor="BAJA")
        self.message_user(request, f"{n} conductor(es) dados de baja.")


@admin.register(TitularPoliza)
class TitularPolizaAdmin(admin.ModelAdmin):
    list_display = ["nombre_completo", "telefono", "correo", "estatus_titular", "fecha_creacion"]
    list_filter = ["estatus_titular"]
    search_fields = ["nombre_completo", "telefono", "correo"]
    ordering = ["nombre_completo"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    actions = ["marcar_activo", "marcar_inactivo"]

    @admin.action(description="Marcar seleccionados como ACTIVO")
    def marcar_activo(self, request, queryset):
        n = queryset.update(estatus_titular="ACTIVO")
        self.message_user(request, f"{n} titular(es) marcados como ACTIVO.")

    @admin.action(description="Marcar seleccionados como INACTIVO")
    def marcar_inactivo(self, request, queryset):
        n = queryset.update(estatus_titular="INACTIVO")
        self.message_user(request, f"{n} titular(es) marcados como INACTIVO.")


@admin.register(Organizacion)
class OrganizacionAdmin(admin.ModelAdmin):
    list_display = ["nombre_organizacion", "clave_organizacion", "fecha_creacion"]
    search_fields = ["nombre_organizacion", "clave_organizacion"]
    ordering = ["nombre_organizacion"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]


@admin.register(PlataformaOperativa)
class PlataformaOperativaAdmin(admin.ModelAdmin):
    list_display = ["nombre_organizacion", "clave_organizacion", "estatus_plataforma", "fecha_creacion"]
    list_filter = ["estatus_plataforma"]
    search_fields = ["nombre_organizacion", "clave_organizacion"]
    ordering = ["nombre_organizacion"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ["nombre_organizacion", "clave_organizacion", "estatus_socio", "fecha_creacion"]
    list_filter = ["estatus_socio"]
    search_fields = ["nombre_organizacion", "clave_organizacion"]
    ordering = ["nombre_organizacion"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]


@admin.register(Aseguradora)
class AseguradoraAdmin(admin.ModelAdmin):
    list_display = ["nombre_organizacion", "clave_organizacion", "estatus_aseguradora", "fecha_creacion"]
    list_filter = ["estatus_aseguradora"]
    search_fields = ["nombre_organizacion", "clave_organizacion"]
    ordering = ["nombre_organizacion"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
