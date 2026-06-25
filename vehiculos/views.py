from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import localdate

from .models import Vehiculo, VwFichaVehiculo


@login_required
def dashboard(request):
    fichas = VwFichaVehiculo.objects.all()
    activos = fichas.filter(estatus_unidad="ACTIVA")

    stats = {
        "total": fichas.count(),
        "activos": activos.count(),
        "verde": activos.filter(semaforo_documental="VERDE").count(),
        "amarillo": activos.filter(semaforo_documental="AMARILLO").count(),
        "rojo": activos.filter(semaforo_documental="ROJO").count(),
    }

    alertas = (
        activos.exclude(semaforo_documental="VERDE")
        .annotate(
            prioridad=Case(
                When(semaforo_documental="ROJO", then=Value(1)),
                When(semaforo_documental="AMARILLO", then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        )
        .order_by("prioridad", "numero_interno")[:20]
    )

    return render(request, "vehiculos/dashboard.html", {
        "stats": stats,
        "alertas": alertas,
        "hoy": localdate(),
    })


@login_required
def lista_vehiculos(request):
    fichas = VwFichaVehiculo.objects.all()

    q = request.GET.get("q", "").strip()
    semaforo = request.GET.get("semaforo", "").strip()
    estatus = request.GET.get("estatus", "").strip()

    if q:
        fichas = fichas.filter(
            Q(numero_interno__icontains=q)
            | Q(placas_actuales__icontains=q)
            | Q(conductor__icontains=q)
            | Q(numero_serie__icontains=q)
            | Q(nombre_modelo_comercial__icontains=q)
            | Q(nombre_marca__icontains=q)
        )
    if semaforo:
        fichas = fichas.filter(semaforo_documental=semaforo)
    if estatus:
        fichas = fichas.filter(estatus_unidad=estatus)

    query_params = {k: v for k, v in {"q": q, "semaforo": semaforo, "estatus": estatus}.items() if v}
    query_string = urlencode(query_params)

    paginator = Paginator(fichas, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "vehiculos/lista.html", {
        "page_obj": page_obj,
        "q": q,
        "semaforo": semaforo,
        "estatus": estatus,
        "query_string": query_string,
        "estatus_choices": Vehiculo.EstatusUnidad.choices,
        "semaforo_choices": ["VERDE", "AMARILLO", "ROJO"],
    })


@login_required
def detalle_vehiculo(request, pk):
    vehiculo = get_object_or_404(
        Vehiculo.objects.select_related("modelo_vehiculo__marca", "color"),
        pk=pk,
    )
    ficha = VwFichaVehiculo.objects.filter(pk=pk).first()

    return render(request, "vehiculos/detalle.html", {
        "vehiculo": vehiculo,
        "ficha": ficha,
        "asignaciones": (
            vehiculo.asignaciones_vehiculo
            .select_related("conductor", "plataforma", "socio")
            .prefetch_related("apps_asignadas__app_transporte")
        ),
        "polizas": vehiculo.polizas.select_related("aseguradora", "titular_poliza"),
        "verificaciones": vehiculo.verificaciones.select_related("emplacamiento"),
        "tarjetas": vehiculo.tarjetas_circulacion.select_related("emplacamiento"),
        "tenencias": vehiculo.tenencias.all(),
        "emplacamientos": vehiculo.emplacamientos.select_related("entidad_federativa"),
        "adeudos": vehiculo.adeudos.all(),
        "adeudos_pendientes_count": vehiculo.adeudos.filter(estatus_adeudo="PENDIENTE").count(),
        "instalaciones_gps": vehiculo.instalaciones_gps.select_related("gps"),
        "asignaciones_tag": vehiculo.asignaciones_tag.select_related("tag"),
        "observaciones": vehiculo.observaciones.select_related("autor_registro")[:20],
        "hoy": localdate(),
    })
