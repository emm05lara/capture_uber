from django.contrib import admin
from django.db.models import OuterRef, Subquery

from dispositivos.models import AsignacionTag, InstalacionGps
from operacion.models import AsignacionVehiculo
from .models import (
    Adquisicion,
    AdeudoVehicular,
    Emplacamiento,
    Observacion,
    PolizaSeguro,
    TarjetaCirculacion,
    Tenencia,
    Vehiculo,
    VerificacionVehicular,
    VwFichaVehiculo,
)


# ---------------------------------------------------------------------------
# Inlines para VehiculoAdmin
# ---------------------------------------------------------------------------

class EmplacamientoInline(admin.TabularInline):
    model = Emplacamiento
    extra = 0
    show_change_link = True
    fields = ["placas", "entidad_federativa", "fecha_inicio", "fecha_fin"]
    ordering = ["-fecha_inicio"]


class AdquisicionInline(admin.TabularInline):
    model = Adquisicion
    extra = 0
    show_change_link = True
    fields = ["tipo_adquisicion", "fecha_adquisicion", "importe_adquisicion"]
    ordering = ["-fecha_adquisicion"]


class PolizaSeguroInline(admin.TabularInline):
    model = PolizaSeguro
    extra = 0
    show_change_link = True
    fields = ["numero_poliza", "aseguradora", "fecha_vigencia_inicio", "fecha_vigencia_fin", "importe_prima"]
    ordering = ["-fecha_vigencia_fin"]


class VerificacionVehicularInline(admin.TabularInline):
    model = VerificacionVehicular
    extra = 0
    show_change_link = True
    fields = ["semestre", "fecha_ultima_verificacion", "fecha_limite_verificacion"]
    ordering = ["-fecha_limite_verificacion"]


class TarjetaCirculacionInline(admin.TabularInline):
    model = TarjetaCirculacion
    extra = 0
    show_change_link = True
    fields = ["fecha_emision", "fecha_vigencia_fin"]
    ordering = ["-fecha_vigencia_fin"]


class TenenciaInline(admin.TabularInline):
    model = Tenencia
    extra = 0
    show_change_link = True
    fields = ["anio_fiscal", "estatus_tenencia", "fecha_pago", "monto_tenencia"]
    ordering = ["-anio_fiscal"]


class AdeudoVehicularInline(admin.TabularInline):
    model = AdeudoVehicular
    extra = 0
    show_change_link = True
    fields = ["tipo_adeudo", "estatus_adeudo", "monto_adeudo", "fecha_consulta"]
    ordering = ["-fecha_consulta"]


class ObservacionInline(admin.TabularInline):
    model = Observacion
    extra = 0
    show_change_link = True
    fields = ["tipo_observacion", "texto_observacion", "fecha_registro", "autor_registro"]
    ordering = ["-fecha_registro"]


class AsignacionVehiculoInline(admin.TabularInline):
    model = AsignacionVehiculo
    extra = 0
    show_change_link = True
    fields = ["conductor", "plataforma", "socio", "cuenta", "fecha_inicio", "fecha_fin"]
    ordering = ["-fecha_inicio"]


class InstalacionGpsVehiculoInline(admin.TabularInline):
    model = InstalacionGps
    extra = 0
    show_change_link = True
    fields = ["gps", "fecha_instalacion", "fecha_retiro"]
    ordering = ["-fecha_instalacion"]


class AsignacionTagVehiculoInline(admin.TabularInline):
    model = AsignacionTag
    extra = 0
    show_change_link = True
    fields = ["tag", "fecha_inicio", "fecha_fin"]
    ordering = ["-fecha_inicio"]


# ---------------------------------------------------------------------------
# VehiculoAdmin
# ---------------------------------------------------------------------------

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = [
        "numero_interno",
        "numero_serie",
        "modelo_vehiculo",
        "anio_modelo",
        "color",
        "placas_display",
        "estatus_unidad",
    ]
    list_filter = ["estatus_unidad", "color", "modelo_vehiculo__marca"]
    list_select_related = ["modelo_vehiculo__marca", "color"]
    search_fields = ["numero_serie", "numero_interno", "modelo_vehiculo__nombre_modelo_comercial"]
    ordering = ["numero_interno", "numero_serie"]
    show_full_result_count = False
    readonly_fields = ["clave_vehiculo_display", "fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["modelo_vehiculo", "color"]
    actions = ["marcar_activa", "marcar_baja", "marcar_taller", "marcar_sin_asignar"]
    inlines = [
        EmplacamientoInline,
        AsignacionVehiculoInline,
        AdquisicionInline,
        PolizaSeguroInline,
        VerificacionVehicularInline,
        TarjetaCirculacionInline,
        TenenciaInline,
        AdeudoVehicularInline,
        InstalacionGpsVehiculoInline,
        AsignacionTagVehiculoInline,
        ObservacionInline,
    ]
    fieldsets = [
        ("Identificación", {
            "fields": ["numero_interno", "numero_serie", "clave_vehiculo_display"],
        }),
        ("Características", {
            "fields": ["modelo_vehiculo", "anio_modelo", "color"],
        }),
        ("Estado", {
            "fields": ["estatus_unidad"],
        }),
        ("Auditoría", {
            "fields": ["fecha_creacion", "fecha_actualizacion"],
            "classes": ["collapse"],
        }),
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("modelo_vehiculo__marca", "color")
        placas_sq = Emplacamiento.objects.filter(
            vehiculo=OuterRef("pk"),
            fecha_fin__isnull=True,
        ).values("placas")[:1]
        return qs.annotate(_placas_actuales=Subquery(placas_sq))

    @admin.display(description="Placas actuales")
    def placas_display(self, obj):
        return getattr(obj, "_placas_actuales", None) or "—"

    @admin.display(description="Clave vehículo")
    def clave_vehiculo_display(self, obj):
        return obj.clave_vehiculo or "—"

    @admin.action(description="Marcar seleccionados como ACTIVA")
    def marcar_activa(self, request, queryset):
        n = queryset.update(estatus_unidad="ACTIVA")
        self.message_user(request, f"{n} vehículo(s) marcados como ACTIVA.")

    @admin.action(description="Marcar seleccionados como BAJA")
    def marcar_baja(self, request, queryset):
        n = queryset.update(estatus_unidad="BAJA")
        self.message_user(request, f"{n} vehículo(s) marcados como BAJA.")

    @admin.action(description="Marcar seleccionados como EN TALLER")
    def marcar_taller(self, request, queryset):
        n = queryset.update(estatus_unidad="TALLER")
        self.message_user(request, f"{n} vehículo(s) marcados como EN TALLER.")

    @admin.action(description="Marcar seleccionados como SIN ASIGNAR")
    def marcar_sin_asignar(self, request, queryset):
        n = queryset.update(estatus_unidad="SIN_ASIGNAR")
        self.message_user(request, f"{n} vehículo(s) marcados como SIN ASIGNAR.")


# ---------------------------------------------------------------------------
# Admins individuales
# ---------------------------------------------------------------------------

@admin.register(Emplacamiento)
class EmplacamientoAdmin(admin.ModelAdmin):
    list_display = ["placas", "vehiculo", "entidad_federativa", "fecha_inicio", "fecha_fin", "es_actual"]
    list_filter = ["entidad_federativa"]
    list_select_related = ["vehiculo", "entidad_federativa"]
    search_fields = ["placas", "vehiculo__numero_serie", "vehiculo__numero_interno"]
    ordering = ["-fecha_inicio"]
    date_hierarchy = "fecha_inicio"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo"]

    @admin.display(description="¿Actual?", boolean=True)
    def es_actual(self, obj):
        return obj.fecha_fin is None


@admin.register(Adquisicion)
class AdquisicionAdmin(admin.ModelAdmin):
    list_display = ["vehiculo", "tipo_adquisicion", "fecha_adquisicion", "importe_adquisicion"]
    list_filter = ["tipo_adquisicion"]
    list_select_related = ["vehiculo"]
    search_fields = ["vehiculo__numero_serie", "vehiculo__numero_interno", "tipo_adquisicion"]
    ordering = ["-fecha_adquisicion"]
    date_hierarchy = "fecha_adquisicion"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo"]


@admin.register(PolizaSeguro)
class PolizaSeguroAdmin(admin.ModelAdmin):
    list_display = ["numero_poliza", "vehiculo", "aseguradora", "fecha_vigencia_fin", "vigente_display"]
    list_filter = ["aseguradora"]
    list_select_related = ["vehiculo", "aseguradora"]
    search_fields = ["numero_poliza", "vehiculo__numero_serie", "vehiculo__numero_interno"]
    ordering = ["-fecha_vigencia_fin"]
    date_hierarchy = "fecha_vigencia_fin"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo"]

    @admin.display(description="¿Vigente?", boolean=True)
    def vigente_display(self, obj):
        return obj.vigente


@admin.register(VerificacionVehicular)
class VerificacionVehicularAdmin(admin.ModelAdmin):
    list_display = ["vehiculo", "semestre", "fecha_ultima_verificacion", "fecha_limite_verificacion", "vencida_display"]
    list_filter = ["semestre"]
    list_select_related = ["vehiculo"]
    search_fields = ["vehiculo__numero_serie", "vehiculo__numero_interno", "semestre"]
    ordering = ["-fecha_limite_verificacion"]
    date_hierarchy = "fecha_limite_verificacion"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo"]

    @admin.display(description="¿Vencida?", boolean=True)
    def vencida_display(self, obj):
        return obj.vencida


@admin.register(TarjetaCirculacion)
class TarjetaCirculacionAdmin(admin.ModelAdmin):
    list_display = ["vehiculo", "fecha_emision", "fecha_vigencia_fin", "vigente_display"]
    list_select_related = ["vehiculo"]
    search_fields = ["vehiculo__numero_serie", "vehiculo__numero_interno"]
    ordering = ["-fecha_vigencia_fin"]
    date_hierarchy = "fecha_vigencia_fin"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo"]

    @admin.display(description="¿Vigente?", boolean=True)
    def vigente_display(self, obj):
        return obj.vigente


@admin.register(Tenencia)
class TenenciaAdmin(admin.ModelAdmin):
    list_display = ["vehiculo", "anio_fiscal", "estatus_tenencia", "fecha_pago", "monto_tenencia"]
    list_filter = ["estatus_tenencia", "anio_fiscal"]
    list_select_related = ["vehiculo"]
    search_fields = ["vehiculo__numero_serie", "vehiculo__numero_interno"]
    ordering = ["-anio_fiscal"]
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo"]


@admin.register(AdeudoVehicular)
class AdeudoVehicularAdmin(admin.ModelAdmin):
    list_display = ["vehiculo", "tipo_adeudo", "estatus_adeudo", "monto_adeudo", "fecha_consulta"]
    list_filter = ["estatus_adeudo"]
    list_select_related = ["vehiculo"]
    search_fields = ["vehiculo__numero_serie", "vehiculo__numero_interno", "tipo_adeudo"]
    ordering = ["-fecha_consulta"]
    date_hierarchy = "fecha_consulta"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo"]
    actions = ["marcar_pagado", "marcar_cancelado"]

    @admin.action(description="Marcar seleccionados como PAGADO")
    def marcar_pagado(self, request, queryset):
        n = queryset.update(estatus_adeudo="PAGADO")
        self.message_user(request, f"{n} adeudo(s) marcados como PAGADO.")

    @admin.action(description="Marcar seleccionados como CANCELADO")
    def marcar_cancelado(self, request, queryset):
        n = queryset.update(estatus_adeudo="CANCELADO")
        self.message_user(request, f"{n} adeudo(s) marcados como CANCELADO.")


@admin.register(Observacion)
class ObservacionAdmin(admin.ModelAdmin):
    list_display = ["vehiculo", "tipo_observacion", "fecha_registro", "autor_registro"]
    list_filter = ["tipo_observacion"]
    list_select_related = ["vehiculo", "autor_registro"]
    search_fields = ["vehiculo__numero_serie", "vehiculo__numero_interno", "texto_observacion"]
    ordering = ["-fecha_registro"]
    date_hierarchy = "fecha_registro"
    readonly_fields = ["fecha_creacion", "fecha_actualizacion"]
    autocomplete_fields = ["vehiculo"]


# ---------------------------------------------------------------------------
# Ficha de vehículo (vista de BD, solo lectura)
# ---------------------------------------------------------------------------

@admin.register(VwFichaVehiculo)
class VwFichaVehiculoAdmin(admin.ModelAdmin):
    list_display = [
        "numero_interno",
        "clave_vehiculo",
        "conductor",
        "plataforma",
        "semaforo_documental_display",
        "estatus_unidad",
    ]
    list_filter = ["estatus_unidad", "semaforo_documental", "nombre_marca"]
    search_fields = [
        "numero_interno",
        "numero_serie",
        "placas_actuales",
        "conductor",
        "clave_vehiculo",
    ]
    ordering = ["numero_interno"]
    readonly_fields = [
        "id_vehiculo",
        "numero_interno",
        "clave_vehiculo",
        "nombre_marca",
        "nombre_modelo_comercial",
        "version",
        "anio_modelo",
        "nombre_color",
        "numero_serie",
        "placas_actuales",
        "entidad_emplacamiento_actual",
        "conductor",
        "plataforma",
        "socio",
        "cuenta",
        "numero_poliza",
        "vigencia_poliza",
        "semestre_verificacion",
        "fecha_ultima_verificacion",
        "fecha_limite_verificacion",
        "vigencia_tarjeta_circulacion",
        "cantidad_adeudos_pendientes",
        "monto_adeudos_pendientes",
        "semaforo_documental",
        "estatus_unidad",
    ]
    fieldsets = [
        ("Identificación", {
            "fields": [
                "id_vehiculo", "numero_interno", "clave_vehiculo", "numero_serie",
                "nombre_marca", "nombre_modelo_comercial", "version",
                "anio_modelo", "nombre_color",
                "placas_actuales", "entidad_emplacamiento_actual",
            ],
        }),
        ("Asignación actual", {
            "fields": ["conductor", "plataforma", "socio", "cuenta"],
        }),
        ("Documentación", {
            "fields": [
                "numero_poliza", "vigencia_poliza",
                "semestre_verificacion", "fecha_ultima_verificacion", "fecha_limite_verificacion",
                "vigencia_tarjeta_circulacion",
                "cantidad_adeudos_pendientes", "monto_adeudos_pendientes",
                "semaforo_documental",
            ],
        }),
        ("Estado operativo", {
            "fields": ["estatus_unidad"],
        }),
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Semáforo")
    def semaforo_documental_display(self, obj):
        colores = {"VERDE": "✅", "AMARILLO": "⚠️", "ROJO": "🔴"}
        return f"{colores.get(obj.semaforo_documental, '')} {obj.semaforo_documental}"
