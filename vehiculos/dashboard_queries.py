"""
Consultas del dashboard operativo (Fase 7).

Mantiene la lógica de agregaciones y clasificación de vencimientos separada
de la vista, para que `views.dashboard` no crezca de forma descontrolada.
Todas las funciones reciben `hoy` como parámetro explícito (en vez de leer
`localdate()` internamente) para que las pruebas puedan controlar la fecha
con `unittest.mock.patch` sin depender del día real.
"""
from datetime import timedelta

from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Q, Sum, Value, When
from django.urls import reverse

from actores.models import Conductor, ReferenciaConductor
from dispositivos.models import AsignacionTag, DispositivoGps, InstalacionGps, TagTelepeaje
from operacion.models import AsignacionVehiculo
from .models import AdeudoVehicular, Vehiculo, VwFichaVehiculo

HORIZONTES_VALIDOS = (30, 60, 90)
HORIZONTE_MAXIMO = max(HORIZONTES_VALIDOS)
HORIZONTE_DEFECTO = 30

TIPOS_DOCUMENTO_VALIDOS = {"POLIZA", "VERIFICACION", "TARJETA", "LICENCIA"}
SEVERIDADES_VALIDAS = {"VENCIDO", "30", "60", "90"}


def horizonte_valido(valor):
    """Normaliza el parámetro GET `horizonte`: cualquier valor que no sea
    30/60/90 se ignora silenciosamente y se usa el valor por defecto."""
    try:
        horizonte = int(valor)
    except (TypeError, ValueError):
        return HORIZONTE_DEFECTO
    return horizonte if horizonte in HORIZONTES_VALIDOS else HORIZONTE_DEFECTO


def tipo_valido(valor):
    valor = (valor or "").strip().upper()
    return valor if valor in TIPOS_DOCUMENTO_VALIDOS else ""


def severidad_valida(valor):
    valor = (valor or "").strip().upper()
    return valor if valor in SEVERIDADES_VALIDAS else ""


def estatus_vehiculo_valido(valor):
    valor = (valor or "").strip().upper()
    return valor if valor in Vehiculo.EstatusUnidad.values else ""


def clasificar_dias(dias):
    """A partir de los días restantes (negativo = ya venció), regresa
    (bucket, etiqueta legible, clase css de Bootstrap) para un badge."""
    if dias < 0:
        return "VENCIDO", "Vencido", "bg-danger"
    if dias <= 30:
        return "30", "Vence en 30 días o menos", "bg-danger"
    if dias <= 60:
        return "60", "Vence en 31–60 días", "bg-warning text-dark"
    return "90", "Vence en 61–90 días", "bg-warning-subtle text-warning-emphasis border"


def resumen_vehiculos(hoy):
    """Un solo aggregate con el total de la flota, el desglose de semáforo,
    adeudos y los paneles de 'información faltante', todo sobre vehículos
    ACTIVOS. Se resuelve en 2 consultas (total + aggregate), sin importar
    cuántos vehículos existan."""
    fichas = VwFichaVehiculo.objects.all()
    total = fichas.count()

    instalacion_gps_activa = InstalacionGps.objects.filter(vehiculo_id=OuterRef("pk"), fecha_retiro__isnull=True)
    asignacion_tag_activa = AsignacionTag.objects.filter(vehiculo_id=OuterRef("pk"), fecha_fin__isnull=True)

    activos = fichas.filter(estatus_unidad=Vehiculo.EstatusUnidad.ACTIVA).annotate(
        tiene_gps=Exists(instalacion_gps_activa),
        tiene_tag=Exists(asignacion_tag_activa),
    )

    sin_poliza_vigente = Q(vigencia_poliza__isnull=True) | Q(vigencia_poliza__lt=hoy)
    sin_verificacion_vigente = Q(fecha_limite_verificacion__isnull=True) | Q(fecha_limite_verificacion__lt=hoy)
    sin_tarjeta_vigente = Q(vigencia_tarjeta_circulacion__isnull=True) | Q(vigencia_tarjeta_circulacion__lt=hoy)

    resumen = activos.aggregate(
        activos=Count("pk"),
        verde=Count("pk", filter=Q(semaforo_documental="VERDE")),
        amarillo=Count("pk", filter=Q(semaforo_documental="AMARILLO")),
        rojo=Count("pk", filter=Q(semaforo_documental="ROJO")),
        con_adeudos=Count("pk", filter=Q(cantidad_adeudos_pendientes__gt=0)),
        monto_adeudos=Sum("monto_adeudos_pendientes", filter=Q(cantidad_adeudos_pendientes__gt=0)),
        sin_conductor=Count("pk", filter=Q(conductor__isnull=True)),
        sin_poliza=Count("pk", filter=sin_poliza_vigente),
        sin_verificacion=Count("pk", filter=sin_verificacion_vigente),
        sin_tarjeta=Count("pk", filter=sin_tarjeta_vigente),
        sin_placas=Count("pk", filter=Q(placas_actuales__isnull=True)),
        sin_gps=Count("pk", filter=Q(tiene_gps=False)),
        sin_tag=Count("pk", filter=Q(tiene_tag=False)),
    )
    resumen["total"] = total
    resumen["monto_adeudos"] = resumen["monto_adeudos"] or 0
    return resumen


def alertas_semaforo(limite=10):
    """Vehículos activos con semáforo documental distinto de VERDE, para el
    panel de 'atención' del dashboard (no confundir con la tabla de
    vencimientos: esta usa el semáforo ya calculado por la vista de BD)."""
    fichas = VwFichaVehiculo.objects.filter(estatus_unidad=Vehiculo.EstatusUnidad.ACTIVA)
    return (
        fichas.exclude(semaforo_documental="VERDE")
        .annotate(
            prioridad=Case(
                When(semaforo_documental="ROJO", then=Value(1)),
                When(semaforo_documental="AMARILLO", then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        )
        .order_by("prioridad", "numero_interno")[:limite]
    )


def resumen_conductores(hoy, horizonte=HORIZONTE_DEFECTO):
    """Un aggregate con las métricas de conductores (excluye los dados de
    BAJA, que ya no son operativos)."""
    asignacion_activa = AsignacionVehiculo.objects.filter(conductor_id=OuterRef("pk"), fecha_fin__isnull=True)
    referencia_existente = ReferenciaConductor.objects.filter(conductor_id=OuterRef("pk"))
    limite = hoy + timedelta(days=horizonte)

    conductores = Conductor.objects.exclude(estatus_conductor=Conductor.Estatus.BAJA).annotate(
        tiene_vehiculo=Exists(asignacion_activa),
        tiene_referencias=Exists(referencia_existente),
    )
    return conductores.aggregate(
        activos=Count("pk", filter=Q(estatus_conductor=Conductor.Estatus.ACTIVO)),
        sin_vehiculo=Count(
            "pk", filter=Q(estatus_conductor=Conductor.Estatus.ACTIVO, tiene_vehiculo=False)
        ),
        sin_referencias=Count("pk", filter=Q(tiene_referencias=False)),
        licencias_vencidas=Count(
            "pk", filter=Q(fecha_vencimiento_licencia__isnull=False, fecha_vencimiento_licencia__lt=hoy)
        ),
        licencias_por_vencer=Count(
            "pk",
            filter=Q(
                fecha_vencimiento_licencia__isnull=False,
                fecha_vencimiento_licencia__gte=hoy,
                fecha_vencimiento_licencia__lte=limite,
            ),
        ),
    )


def resumen_dispositivos():
    """Disponibilidad e inactividad de GPS y TAG, dos aggregates (uno por
    catálogo) sin importar cuántos dispositivos existan."""
    gps_instalado_actual = InstalacionGps.objects.filter(gps_id=OuterRef("pk"), fecha_retiro__isnull=True)
    gps = DispositivoGps.objects.annotate(instalado=Exists(gps_instalado_actual)).aggregate(
        disponibles=Count("pk", filter=Q(estatus_gps=DispositivoGps.Estatus.ACTIVO, instalado=False)),
        inactivos=Count("pk", filter=Q(estatus_gps=DispositivoGps.Estatus.INACTIVO)),
    )
    tag_asignado_actual = AsignacionTag.objects.filter(tag_id=OuterRef("pk"), fecha_fin__isnull=True)
    tag = TagTelepeaje.objects.annotate(asignado=Exists(tag_asignado_actual)).aggregate(
        disponibles=Count("pk", filter=Q(estatus_tag=TagTelepeaje.Estatus.ACTIVO, asignado=False)),
        inactivos=Count("pk", filter=Q(estatus_tag=TagTelepeaje.Estatus.INACTIVO)),
    )
    return {
        "gps_disponibles": gps["disponibles"],
        "gps_inactivos": gps["inactivos"],
        "tag_disponibles": tag["disponibles"],
        "tag_inactivos": tag["inactivos"],
    }


def adeudos_destacados(limite=5):
    return (
        AdeudoVehicular.objects.filter(estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE)
        .select_related("vehiculo")
        .order_by("-monto_adeudo", "-fecha_consulta")[:limite]
    )


_DOCUMENTOS = (
    ("POLIZA", "Póliza de seguro", "vigencia_poliza", "bi-file-earmark-text"),
    ("VERIFICACION", "Verificación vehicular", "fecha_limite_verificacion", "bi-clipboard-check"),
    ("TARJETA", "Tarjeta de circulación", "vigencia_tarjeta_circulacion", "bi-card-text"),
)


def obtener_vencimientos(hoy, horizonte=HORIZONTE_DEFECTO, tipo="", severidad="", estatus="", q=""):
    """Combina pólizas, verificaciones, tarjetas y licencias de conductor en
    una sola lista de alertas de vencimiento, clasificadas y ordenadas por
    urgencia. Los documentos de vehículo salen de `vw_ficha_vehiculo` (ya
    trae solo el registro vigente de cada tipo por vehículo, sin necesidad
    de una consulta aparte por vehículo); las licencias vienen de una única
    consulta a Conductor. El filtrado adicional (tipo/severidad/búsqueda) se
    hace en Python sobre esta lista ya acotada por fecha, sin más consultas.
    """
    limite_fecha = hoy + timedelta(days=HORIZONTE_MAXIMO)
    filas = []

    fichas = VwFichaVehiculo.objects.filter(estatus_unidad=estatus or Vehiculo.EstatusUnidad.ACTIVA)
    condiciones_fecha = (
        Q(vigencia_poliza__isnull=False, vigencia_poliza__lte=limite_fecha)
        | Q(fecha_limite_verificacion__isnull=False, fecha_limite_verificacion__lte=limite_fecha)
        | Q(vigencia_tarjeta_circulacion__isnull=False, vigencia_tarjeta_circulacion__lte=limite_fecha)
    )

    for ficha in fichas.filter(condiciones_fecha):
        for tipo_codigo, tipo_label, campo, icono in _DOCUMENTOS:
            fecha = getattr(ficha, campo)
            if fecha is None or fecha > limite_fecha:
                continue
            dias = (fecha - hoy).days
            bucket, severidad_label, css = clasificar_dias(dias)
            filas.append({
                "tipo": tipo_codigo,
                "tipo_label": tipo_label,
                "icono": icono,
                "entidad": ficha.numero_interno or ficha.numero_serie,
                "placas": ficha.placas_actuales,
                "fecha": fecha,
                "dias": dias,
                "dias_abs": abs(dias),
                "bucket": bucket,
                "severidad_label": severidad_label,
                "css": css,
                "url": reverse("vehiculos:detalle", args=[ficha.pk]),
            })

    if not estatus:
        # Las licencias no tienen "estatus de vehículo": solo se incluyen
        # cuando no se filtró explícitamente por ese campo.
        conductores = Conductor.objects.exclude(estatus_conductor=Conductor.Estatus.BAJA).filter(
            fecha_vencimiento_licencia__isnull=False, fecha_vencimiento_licencia__lte=limite_fecha
        )
        for conductor in conductores:
            fecha = conductor.fecha_vencimiento_licencia
            dias = (fecha - hoy).days
            bucket, severidad_label, css = clasificar_dias(dias)
            filas.append({
                "tipo": "LICENCIA",
                "tipo_label": "Licencia de conductor",
                "icono": "bi-person-vcard",
                "entidad": conductor.nombre_completo,
                "placas": None,
                "fecha": fecha,
                "dias": dias,
                "dias_abs": abs(dias),
                "bucket": bucket,
                "severidad_label": severidad_label,
                "css": css,
                "url": reverse("actores:conductor_detalle", args=[conductor.pk]),
            })

    if tipo:
        filas = [f for f in filas if f["tipo"] == tipo]

    if severidad:
        filas = [f for f in filas if f["bucket"] == severidad]
    else:
        filas = [f for f in filas if f["dias"] <= horizonte or f["bucket"] == "VENCIDO"]

    if q:
        q_lower = q.lower()
        filas = [
            f for f in filas
            if q_lower in (f["entidad"] or "").lower() or q_lower in (f["placas"] or "").lower()
        ]

    filas.sort(key=lambda f: f["dias"])
    return filas
