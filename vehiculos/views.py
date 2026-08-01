from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.timezone import localdate
from django.views.decorators.http import require_POST

from operacion.forms import AsignacionVehiculoForm
from operacion.models import AsignacionVehiculo
from .forms import (
    EditarVehiculoForm,
    NuevaPlacaForm,
    NuevoVehiculoForm,
    PolizaSeguroForm,
    TarjetaCirculacionForm,
    VerificacionVehicularForm,
)
from .models import (
    Emplacamiento,
    PolizaSeguro,
    TarjetaCirculacion,
    Vehiculo,
    VerificacionVehicular,
    VwFichaVehiculo,
)


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
def nuevo_vehiculo(request):
    if request.method == "POST":
        form = NuevoVehiculoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    vehiculo = Vehiculo.objects.create(
                        numero_interno=data["numero_interno"],
                        modelo_vehiculo=data["modelo_vehiculo"],
                        anio_modelo=data["anio_modelo"],
                        color=data["color"],
                        numero_serie=data["numero_serie"],
                        estatus_unidad=data["estatus_unidad"],
                    )
                    if data.get("placas"):
                        Emplacamiento.objects.create(
                            vehiculo=vehiculo,
                            placas=data["placas"],
                            entidad_federativa=data["entidad_federativa"],
                            fecha_inicio=localdate(),
                        )
                messages.success(
                    request,
                    f"Vehículo {vehiculo.numero_serie} registrado correctamente.",
                )
                return redirect("vehiculos:detalle", pk=vehiculo.pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo guardar el vehículo. "
                    "El número de serie o las placas ya están registrados.",
                )
    else:
        form = NuevoVehiculoForm()
    return render(request, "vehiculos/nuevo.html", {"form": form})


@login_required
def editar_vehiculo(request, pk):
    vehiculo = get_object_or_404(
        Vehiculo.objects.select_related("modelo_vehiculo__marca", "color"),
        pk=pk,
    )
    if request.method == "POST":
        form = EditarVehiculoForm(request.POST, vehiculo_pk=pk)
        if form.is_valid():
            data = form.cleaned_data
            vehiculo.numero_interno = data["numero_interno"]
            vehiculo.modelo_vehiculo = data["modelo_vehiculo"]
            vehiculo.anio_modelo = data["anio_modelo"]
            vehiculo.color = data["color"]
            vehiculo.estatus_unidad = data["estatus_unidad"]
            try:
                vehiculo.save()
                messages.success(request, "Datos del vehículo actualizados correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo guardar. El número interno ya está en uso por otro vehículo.",
                )
    else:
        form = EditarVehiculoForm(
            vehiculo_pk=pk,
            initial={
                "numero_interno": vehiculo.numero_interno or "",
                "modelo_vehiculo": vehiculo.modelo_vehiculo,
                "anio_modelo": vehiculo.anio_modelo,
                "color": vehiculo.color,
                "estatus_unidad": vehiculo.estatus_unidad,
            },
        )
    return render(request, "vehiculos/editar.html", {
        "form": form,
        "vehiculo": vehiculo,
    })


@login_required
def nueva_placa(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    emplacamiento_actual = vehiculo.emplacamiento_actual

    if request.method == "POST":
        form = NuevaPlacaForm(request.POST, vehiculo=vehiculo)
        if form.is_valid():
            data = form.cleaned_data
            fecha_inicio = data.get("fecha_inicio") or localdate()
            try:
                with transaction.atomic():
                    if emplacamiento_actual:
                        Emplacamiento.objects.filter(
                            vehiculo=vehiculo, fecha_fin__isnull=True
                        ).update(fecha_fin=fecha_inicio)
                    Emplacamiento.objects.create(
                        vehiculo=vehiculo,
                        placas=data["placas"],
                        entidad_federativa=data["entidad_federativa"],
                        fecha_inicio=fecha_inicio,
                    )
                messages.success(
                    request,
                    f"Placas {data['placas']} registradas correctamente.",
                )
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudieron registrar las placas. "
                    "Verifica que no estén asignadas a otro vehículo activo.",
                )
    else:
        form = NuevaPlacaForm(vehiculo=vehiculo)

    return render(request, "vehiculos/nueva_placa.html", {
        "form": form,
        "vehiculo": vehiculo,
        "emplacamiento_actual": emplacamiento_actual,
    })


@login_required
@require_POST
def cambiar_estatus(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    nuevo_estatus = request.POST.get("estatus_unidad", "").strip()
    if nuevo_estatus not in Vehiculo.EstatusUnidad.values:
        messages.error(request, "Estatus no válido.")
    elif nuevo_estatus == vehiculo.estatus_unidad:
        messages.info(request, "El estatus no cambió.")
    else:
        vehiculo.estatus_unidad = nuevo_estatus
        vehiculo.save(update_fields=["estatus_unidad", "fecha_actualizacion"])
        messages.success(
            request,
            f"Estatus cambiado a {vehiculo.get_estatus_unidad_display()}.",
        )
    return redirect("vehiculos:detalle", pk=pk)


@login_required
def detalle_vehiculo(request, pk):
    vehiculo = get_object_or_404(
        Vehiculo.objects.select_related("modelo_vehiculo__marca", "color"),
        pk=pk,
    )
    ficha = VwFichaVehiculo.objects.filter(pk=pk).first()
    asignaciones_vehiculo = (
        vehiculo.asignaciones_vehiculo
        .select_related("conductor", "plataforma", "socio")
        .prefetch_related("apps_asignadas__app_transporte")
    )
    asignacion_actual = next((a for a in asignaciones_vehiculo if a.es_actual), None)

    return render(request, "vehiculos/detalle.html", {
        "vehiculo": vehiculo,
        "ficha": ficha,
        "asignacion_actual": asignacion_actual,
        "asignaciones": asignaciones_vehiculo,
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
        "limite_amarillo": localdate() + timedelta(days=30),
    })


@login_required
def asignar_conductor(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    asignacion_actual = (
        vehiculo.asignaciones_vehiculo
        .filter(fecha_fin__isnull=True)
        .select_related("conductor")
        .first()
    )

    if asignacion_actual:
        messages.info(
            request,
            "Este vehículo ya tiene un conductor asignado. "
            "Finaliza la asignación actual o cambia de conductor.",
        )
        return redirect("vehiculos:detalle", pk=pk)

    if request.method == "POST":
        form = AsignacionVehiculoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    AsignacionVehiculo.objects.create(
                        vehiculo=vehiculo,
                        conductor=data["conductor"],
                        fecha_inicio=data["fecha_inicio"],
                        plataforma=data.get("plataforma"),
                        socio=data.get("socio"),
                        cuenta=data.get("cuenta"),
                    )
                messages.success(
                    request,
                    f"Conductor {data['conductor'].nombre_completo} asignado a este vehículo.",
                )
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo asignar el conductor. Es posible que ya tenga otra "
                    "asignación activa o que el vehículo ya no esté disponible.",
                )
    else:
        form = AsignacionVehiculoForm()

    return render(request, "vehiculos/asignar_conductor.html", {
        "form": form,
        "vehiculo": vehiculo,
    })


@login_required
@require_POST
def finalizar_asignacion(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    asignacion = (
        vehiculo.asignaciones_vehiculo
        .filter(fecha_fin__isnull=True)
        .select_related("conductor")
        .first()
    )
    if not asignacion:
        messages.error(request, "Este vehículo no tiene una asignación activa para finalizar.")
        return redirect("vehiculos:detalle", pk=pk)

    fecha_fin_raw = request.POST.get("fecha_fin", "").strip()
    fecha_fin = parse_date(fecha_fin_raw) if fecha_fin_raw else localdate()
    if fecha_fin is None or (asignacion.fecha_inicio and fecha_fin < asignacion.fecha_inicio):
        messages.error(
            request,
            "La fecha de finalización no es válida: no puede ser anterior a la fecha de inicio.",
        )
        return redirect("vehiculos:detalle", pk=pk)

    try:
        with transaction.atomic():
            asignacion.fecha_fin = fecha_fin
            asignacion.save(update_fields=["fecha_fin", "fecha_actualizacion"])
        messages.success(
            request,
            f"Asignación de {asignacion.conductor.nombre_completo} finalizada correctamente.",
        )
    except IntegrityError:
        messages.error(request, "No se pudo finalizar la asignación. Intenta nuevamente.")

    return redirect("vehiculos:detalle", pk=pk)


@login_required
def cambiar_conductor(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    asignacion_actual = (
        vehiculo.asignaciones_vehiculo
        .filter(fecha_fin__isnull=True)
        .select_related("conductor")
        .first()
    )

    if not asignacion_actual:
        messages.info(
            request,
            "Este vehículo no tiene conductor asignado actualmente. Usa \"Asignar conductor\".",
        )
        return redirect("vehiculos:asignar_conductor", pk=pk)

    if request.method == "POST":
        form = AsignacionVehiculoForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            fecha_cambio = data["fecha_inicio"]
            if asignacion_actual.fecha_inicio and fecha_cambio < asignacion_actual.fecha_inicio:
                form.add_error(
                    "fecha_inicio",
                    "La nueva fecha de inicio no puede ser anterior al inicio de la asignación actual.",
                )
            else:
                try:
                    with transaction.atomic():
                        # Se cierra primero la asignación actual: el vehículo no puede
                        # tener dos asignaciones activas a la vez (ni siquiera un
                        # instante dentro de la misma transacción), por la restricción
                        # de unicidad. Si la creación de la nueva asignación falla más
                        # abajo, transaction.atomic() revierte también este cierre, así
                        # que la asignación anterior nunca queda cerrada sin reemplazo.
                        asignacion_actual.fecha_fin = fecha_cambio
                        asignacion_actual.save(update_fields=["fecha_fin", "fecha_actualizacion"])
                        nueva_asignacion = AsignacionVehiculo.objects.create(
                            vehiculo=vehiculo,
                            conductor=data["conductor"],
                            fecha_inicio=fecha_cambio,
                            plataforma=data.get("plataforma"),
                            socio=data.get("socio"),
                            cuenta=data.get("cuenta"),
                        )
                    messages.success(
                        request,
                        f"Conductor cambiado a {nueva_asignacion.conductor.nombre_completo}.",
                    )
                    return redirect("vehiculos:detalle", pk=pk)
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo cambiar el conductor. Es posible que ya no esté disponible.",
                    )
    else:
        form = AsignacionVehiculoForm()

    return render(request, "vehiculos/cambiar_conductor.html", {
        "form": form,
        "vehiculo": vehiculo,
        "asignacion_actual": asignacion_actual,
    })


# ---------------------------------------------------------------------------
# Pólizas de seguro
# ---------------------------------------------------------------------------

@login_required
def poliza_nueva(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)

    if request.method == "POST":
        form = PolizaSeguroForm(request.POST, vehiculo=vehiculo)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    PolizaSeguro.objects.create(
                        vehiculo=vehiculo,
                        aseguradora=data["aseguradora"],
                        titular_poliza=data.get("titular_poliza"),
                        numero_poliza=data["numero_poliza"],
                        fecha_vigencia_inicio=data.get("fecha_vigencia_inicio"),
                        fecha_vigencia_fin=data["fecha_vigencia_fin"],
                        importe_prima=data.get("importe_prima"),
                    )
                messages.success(
                    request,
                    f"Póliza {data['numero_poliza']} registrada correctamente.",
                )
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo registrar la póliza. Verifica que el número no esté "
                    "duplicado para la misma aseguradora.",
                )
    else:
        form = PolizaSeguroForm(vehiculo=vehiculo)

    return render(request, "vehiculos/poliza_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "es_edicion": False,
    })


@login_required
def poliza_editar(request, pk, poliza_pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    poliza = get_object_or_404(PolizaSeguro, pk=poliza_pk, vehiculo=vehiculo)

    if request.method == "POST":
        form = PolizaSeguroForm(request.POST, vehiculo=vehiculo, poliza_pk=poliza.pk)
        if form.is_valid():
            data = form.cleaned_data
            poliza.aseguradora = data["aseguradora"]
            poliza.titular_poliza = data.get("titular_poliza")
            poliza.numero_poliza = data["numero_poliza"]
            poliza.fecha_vigencia_inicio = data.get("fecha_vigencia_inicio")
            poliza.fecha_vigencia_fin = data["fecha_vigencia_fin"]
            poliza.importe_prima = data.get("importe_prima")
            try:
                with transaction.atomic():
                    poliza.save()
                messages.success(request, "Póliza actualizada correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo actualizar la póliza. Verifica que el número no esté "
                    "duplicado para la misma aseguradora.",
                )
    else:
        form = PolizaSeguroForm(
            vehiculo=vehiculo,
            poliza_pk=poliza.pk,
            initial={
                "aseguradora": poliza.aseguradora_id,
                "titular_poliza": poliza.titular_poliza_id,
                "numero_poliza": poliza.numero_poliza,
                "fecha_vigencia_inicio": poliza.fecha_vigencia_inicio,
                "fecha_vigencia_fin": poliza.fecha_vigencia_fin,
                "importe_prima": poliza.importe_prima,
            },
        )

    return render(request, "vehiculos/poliza_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "poliza": poliza,
        "es_edicion": True,
    })


# ---------------------------------------------------------------------------
# Verificaciones vehiculares
# ---------------------------------------------------------------------------

@login_required
def verificacion_nueva(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)

    if request.method == "POST":
        form = VerificacionVehicularForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    VerificacionVehicular.objects.create(
                        vehiculo=vehiculo,
                        emplacamiento=vehiculo.emplacamiento_actual,
                        semestre=data["semestre"],
                        fecha_ultima_verificacion=data.get("fecha_ultima_verificacion"),
                        fecha_limite_verificacion=data["fecha_limite_verificacion"],
                    )
                messages.success(
                    request,
                    f"Verificación {data['semestre']} registrada correctamente.",
                )
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo registrar la verificación. Verifica que no exista "
                    "ya un registro igual para este vehículo.",
                )
    else:
        form = VerificacionVehicularForm()

    return render(request, "vehiculos/verificacion_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "es_edicion": False,
    })


@login_required
def verificacion_editar(request, pk, verificacion_pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    verificacion = get_object_or_404(VerificacionVehicular, pk=verificacion_pk, vehiculo=vehiculo)

    if request.method == "POST":
        form = VerificacionVehicularForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            verificacion.semestre = data["semestre"]
            verificacion.fecha_ultima_verificacion = data.get("fecha_ultima_verificacion")
            verificacion.fecha_limite_verificacion = data["fecha_limite_verificacion"]
            try:
                with transaction.atomic():
                    verificacion.save()
                messages.success(request, "Verificación actualizada correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo actualizar la verificación. Verifica que no exista "
                    "ya un registro igual para este vehículo.",
                )
    else:
        form = VerificacionVehicularForm(initial={
            "semestre": verificacion.semestre,
            "fecha_ultima_verificacion": verificacion.fecha_ultima_verificacion,
            "fecha_limite_verificacion": verificacion.fecha_limite_verificacion,
        })

    return render(request, "vehiculos/verificacion_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "verificacion": verificacion,
        "es_edicion": True,
    })


# ---------------------------------------------------------------------------
# Tarjetas de circulación
# ---------------------------------------------------------------------------

@login_required
def tarjeta_nueva(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)

    if request.method == "POST":
        form = TarjetaCirculacionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    TarjetaCirculacion.objects.create(
                        vehiculo=vehiculo,
                        emplacamiento=vehiculo.emplacamiento_actual,
                        fecha_emision=data.get("fecha_emision"),
                        fecha_vigencia_fin=data["fecha_vigencia_fin"],
                    )
                messages.success(request, "Tarjeta de circulación registrada correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo registrar la tarjeta de circulación. Intenta nuevamente.",
                )
    else:
        form = TarjetaCirculacionForm()

    return render(request, "vehiculos/tarjeta_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "es_edicion": False,
    })


@login_required
def tarjeta_editar(request, pk, tarjeta_pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    tarjeta = get_object_or_404(TarjetaCirculacion, pk=tarjeta_pk, vehiculo=vehiculo)

    if request.method == "POST":
        form = TarjetaCirculacionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            tarjeta.fecha_emision = data.get("fecha_emision")
            tarjeta.fecha_vigencia_fin = data["fecha_vigencia_fin"]
            try:
                with transaction.atomic():
                    tarjeta.save()
                messages.success(request, "Tarjeta de circulación actualizada correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo actualizar la tarjeta de circulación. Intenta nuevamente.",
                )
    else:
        form = TarjetaCirculacionForm(initial={
            "fecha_emision": tarjeta.fecha_emision,
            "fecha_vigencia_fin": tarjeta.fecha_vigencia_fin,
        })

    return render(request, "vehiculos/tarjeta_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "tarjeta": tarjeta,
        "es_edicion": True,
    })
