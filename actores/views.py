from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import localdate

from operacion.models import AsignacionVehiculo
from .forms import ConductorForm, ReferenciaConductorFormSet
from .models import Conductor, ReferenciaConductor

ALERTAS_CONDUCTOR_VALIDAS = {"sin_vehiculo", "sin_referencias", "licencia_vencida", "licencia_por_vencer"}
HORIZONTES_VALIDOS = (30, 60, 90)


def _horizonte_valido(valor):
    try:
        horizonte = int(valor)
    except (TypeError, ValueError):
        return 30
    return horizonte if horizonte in HORIZONTES_VALIDOS else 30


@login_required
def conductores_lista(request):
    hoy = localdate()

    q = request.GET.get("q", "").strip()
    estatus = request.GET.get("estatus", "").strip()
    alerta = request.GET.get("alerta", "").strip()
    if alerta not in ALERTAS_CONDUCTOR_VALIDAS:
        alerta = ""
    horizonte = _horizonte_valido(request.GET.get("horizonte"))

    conductores = Conductor.objects.prefetch_related(
        Prefetch(
            "asignaciones_vehiculo",
            queryset=AsignacionVehiculo.objects.filter(
                fecha_fin__isnull=True
            ).select_related("vehiculo"),
            to_attr="asignacion_activa",
        )
    )

    if q:
        conductores = conductores.filter(
            Q(nombre_completo__icontains=q)
            | Q(telefono__icontains=q)
            | Q(numero_licencia__icontains=q)
        )
    if estatus:
        conductores = conductores.filter(estatus_conductor=estatus)

    if alerta == "sin_vehiculo":
        asignacion_activa = AsignacionVehiculo.objects.filter(conductor_id=OuterRef("pk"), fecha_fin__isnull=True)
        conductores = conductores.annotate(tiene_vehiculo=Exists(asignacion_activa)).filter(tiene_vehiculo=False)
    elif alerta == "sin_referencias":
        referencia_existente = ReferenciaConductor.objects.filter(conductor_id=OuterRef("pk"))
        conductores = conductores.annotate(tiene_referencias=Exists(referencia_existente)).filter(
            tiene_referencias=False
        )
    elif alerta == "licencia_vencida":
        conductores = conductores.filter(
            fecha_vencimiento_licencia__isnull=False, fecha_vencimiento_licencia__lt=hoy
        )
    elif alerta == "licencia_por_vencer":
        limite = hoy + timedelta(days=horizonte)
        conductores = conductores.filter(
            fecha_vencimiento_licencia__isnull=False,
            fecha_vencimiento_licencia__gte=hoy,
            fecha_vencimiento_licencia__lte=limite,
        )

    conductores = conductores.order_by("nombre_completo")
    paginator = Paginator(conductores, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "actores/conductores_lista.html", {
        "page_obj": page_obj,
        "q": q,
        "estatus": estatus,
        "alerta": alerta,
        "estatus_choices": Conductor.Estatus.choices,
    })


@login_required
def conductor_nuevo(request):
    if request.method == "POST":
        form = ConductorForm(request.POST)
        formset = ReferenciaConductorFormSet(
            request.POST, instance=Conductor(), prefix="referencias",
        )
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                data = form.cleaned_data
                conductor = Conductor.objects.create(
                    nombre_completo=data["nombre_completo"],
                    telefono=data.get("telefono") or None,
                    correo=data.get("correo") or None,
                    estatus_conductor=data["estatus_conductor"],
                    numero_licencia=data.get("numero_licencia") or None,
                    tipo_licencia=data.get("tipo_licencia"),
                    fecha_vencimiento_licencia=data.get("fecha_vencimiento_licencia"),
                    curp=data.get("curp"),
                )
                formset.instance = conductor
                formset.save()
            messages.success(
                request,
                f"Conductor {conductor.nombre_completo} registrado correctamente.",
            )
            return redirect("actores:conductor_detalle", pk=conductor.pk)
    else:
        form = ConductorForm()
        formset = ReferenciaConductorFormSet(instance=Conductor(), prefix="referencias")

    return render(request, "actores/conductor_form.html", {
        "form": form,
        "formset": formset,
        "titulo": "Nuevo conductor",
        "es_nuevo": True,
        "conductor": None,
    })


@login_required
def conductor_detalle(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)
    asignaciones = (
        conductor.asignaciones_vehiculo
        .select_related(
            "vehiculo__modelo_vehiculo__marca",
            "vehiculo__color",
            "plataforma",
            "socio",
        )
        .prefetch_related("apps_asignadas__app_transporte")
        .order_by("-fecha_inicio")
    )
    asignacion_actual = asignaciones.filter(fecha_fin__isnull=True).first()
    referencias = conductor.referencias.all()

    return render(request, "actores/conductor_detalle.html", {
        "conductor": conductor,
        "asignaciones": asignaciones,
        "asignacion_actual": asignacion_actual,
        "referencias": referencias,
    })


@login_required
def conductor_editar(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)

    if request.method == "POST":
        form = ConductorForm(request.POST)
        formset = ReferenciaConductorFormSet(
            request.POST, instance=conductor, prefix="referencias",
        )
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                data = form.cleaned_data
                conductor.nombre_completo = data["nombre_completo"]
                conductor.telefono = data.get("telefono") or None
                conductor.correo = data.get("correo") or None
                conductor.estatus_conductor = data["estatus_conductor"]
                conductor.numero_licencia = data.get("numero_licencia") or None
                conductor.tipo_licencia = data.get("tipo_licencia")
                conductor.fecha_vencimiento_licencia = data.get("fecha_vencimiento_licencia")
                conductor.curp = data.get("curp")
                conductor.save()
                formset.save()
            messages.success(request, "Datos del conductor actualizados correctamente.")
            return redirect("actores:conductor_detalle", pk=pk)
    else:
        form = ConductorForm(initial={
            "nombre_completo": conductor.nombre_completo,
            "telefono": conductor.telefono or "",
            "correo": conductor.correo or "",
            "estatus_conductor": conductor.estatus_conductor,
            "numero_licencia": conductor.numero_licencia or "",
            "tipo_licencia": conductor.tipo_licencia or "",
            "fecha_vencimiento_licencia": conductor.fecha_vencimiento_licencia or "",
            "curp": conductor.curp or "",
        })
        formset = ReferenciaConductorFormSet(instance=conductor, prefix="referencias")

    return render(request, "actores/conductor_form.html", {
        "form": form,
        "formset": formset,
        "titulo": f"Editar — {conductor.nombre_completo}",
        "es_nuevo": False,
        "conductor": conductor,
    })
