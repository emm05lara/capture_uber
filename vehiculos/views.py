from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.utils.timezone import localdate
from django.views.decorators.http import require_POST

from dispositivos.forms import AsignacionTagForm, InstalacionGpsForm
from dispositivos.models import AsignacionTag, DispositivoGps, InstalacionGps, TagTelepeaje
from operacion.forms import AsignacionVehiculoForm
from operacion.models import AsignacionVehiculo
from .dashboard_queries import (
    HORIZONTES_VALIDOS,
    adeudos_destacados,
    alertas_semaforo,
    estatus_vehiculo_valido,
    horizonte_valido,
    obtener_vencimientos,
    resumen_conductores,
    resumen_dispositivos,
    resumen_vehiculos,
    severidad_valida,
    tipo_valido,
)
from .forms import (
    AdeudoVehicularForm,
    EditarVehiculoForm,
    NuevaPlacaForm,
    NuevoVehiculoForm,
    ObservacionForm,
    PolizaSeguroForm,
    TarjetaCirculacionForm,
    TenenciaForm,
    VerificacionVehicularForm,
)
from .models import (
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


@login_required
def dashboard(request):
    hoy = localdate()

    horizonte = horizonte_valido(request.GET.get("horizonte"))
    tipo = tipo_valido(request.GET.get("tipo"))
    severidad = severidad_valida(request.GET.get("severidad"))
    estatus = estatus_vehiculo_valido(request.GET.get("estatus"))
    q = request.GET.get("q", "").strip()

    resumen = resumen_vehiculos(hoy)
    conductores = resumen_conductores(hoy, horizonte)
    dispositivos = resumen_dispositivos()

    vencimientos = obtener_vencimientos(
        hoy, horizonte=horizonte, tipo=tipo, severidad=severidad, estatus=estatus, q=q,
    )
    vencidos = [f for f in vencimientos if f["bucket"] == "VENCIDO"]

    query_params = {
        k: v for k, v in {
            "horizonte": horizonte if horizonte != 30 else "",
            "tipo": tipo,
            "severidad": severidad,
            "estatus": estatus,
            "q": q,
        }.items() if v
    }
    query_string = urlencode(query_params)

    paginator = Paginator(vencimientos, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "vehiculos/dashboard.html", {
        "hoy": hoy,
        "resumen": resumen,
        "conductores": conductores,
        "dispositivos": dispositivos,
        "page_obj": page_obj,
        "vencidos_criticos": vencidos[:5],
        "vencidos_criticos_total": len(vencidos),
        "adeudos_top": adeudos_destacados(5),
        "alertas_semaforo": alertas_semaforo(10),
        "horizonte": horizonte,
        "tipo": tipo,
        "severidad": severidad,
        "estatus": estatus,
        "q": q,
        "query_string": query_string,
        "horizontes": HORIZONTES_VALIDOS,
        "estatus_choices": Vehiculo.EstatusUnidad.choices,
        "tipo_choices": [
            ("POLIZA", "Póliza de seguro"),
            ("VERIFICACION", "Verificación vehicular"),
            ("TARJETA", "Tarjeta de circulación"),
            ("LICENCIA", "Licencia de conductor"),
        ],
    })


ALERTAS_VEHICULO_VALIDAS = {
    "sin_conductor", "sin_poliza", "sin_verificacion", "sin_tarjeta",
    "sin_placas", "sin_gps", "sin_tag", "adeudos",
}


@login_required
def lista_vehiculos(request):
    fichas = VwFichaVehiculo.objects.all()
    hoy = localdate()

    q = request.GET.get("q", "").strip()
    semaforo = request.GET.get("semaforo", "").strip()
    estatus = request.GET.get("estatus", "").strip()
    alerta = request.GET.get("alerta", "").strip()
    if alerta not in ALERTAS_VEHICULO_VALIDAS:
        alerta = ""

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

    if alerta == "sin_conductor":
        fichas = fichas.filter(conductor__isnull=True)
    elif alerta == "sin_poliza":
        fichas = fichas.filter(Q(vigencia_poliza__isnull=True) | Q(vigencia_poliza__lt=hoy))
    elif alerta == "sin_verificacion":
        fichas = fichas.filter(Q(fecha_limite_verificacion__isnull=True) | Q(fecha_limite_verificacion__lt=hoy))
    elif alerta == "sin_tarjeta":
        fichas = fichas.filter(
            Q(vigencia_tarjeta_circulacion__isnull=True) | Q(vigencia_tarjeta_circulacion__lt=hoy)
        )
    elif alerta == "sin_placas":
        fichas = fichas.filter(placas_actuales__isnull=True)
    elif alerta == "adeudos":
        fichas = fichas.filter(cantidad_adeudos_pendientes__gt=0)
    elif alerta == "sin_gps":
        instalacion_activa = InstalacionGps.objects.filter(vehiculo_id=OuterRef("pk"), fecha_retiro__isnull=True)
        fichas = fichas.annotate(tiene_gps=Exists(instalacion_activa)).filter(tiene_gps=False)
    elif alerta == "sin_tag":
        asignacion_activa = AsignacionTag.objects.filter(vehiculo_id=OuterRef("pk"), fecha_fin__isnull=True)
        fichas = fichas.annotate(tiene_tag=Exists(asignacion_activa)).filter(tiene_tag=False)

    query_params = {
        k: v for k, v in {"q": q, "semaforo": semaforo, "estatus": estatus, "alerta": alerta}.items() if v
    }
    query_string = urlencode(query_params)

    paginator = Paginator(fichas, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "vehiculos/lista.html", {
        "page_obj": page_obj,
        "q": q,
        "semaforo": semaforo,
        "estatus": estatus,
        "alerta": alerta,
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

    adeudos_pendientes_qs = vehiculo.adeudos.filter(estatus_adeudo="PENDIENTE")
    monto_pendiente = adeudos_pendientes_qs.aggregate(total=Sum("monto_adeudo"))["total"]

    instalaciones_gps = list(vehiculo.instalaciones_gps.select_related("gps"))
    asignaciones_tag = list(vehiculo.asignaciones_tag.select_related("tag"))
    gps_actual = next((i for i in instalaciones_gps if i.es_actual), None)
    tag_actual = next((a for a in asignaciones_tag if a.es_actual), None)

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
        "adeudos_pendientes_count": adeudos_pendientes_qs.count(),
        "adeudos_pendientes_monto": monto_pendiente or 0,
        "instalaciones_gps": instalaciones_gps,
        "asignaciones_tag": asignaciones_tag,
        "gps_actual": gps_actual,
        "tag_actual": tag_actual,
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


# ---------------------------------------------------------------------------
# Tenencias
# ---------------------------------------------------------------------------

@login_required
def tenencia_nueva(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)

    if request.method == "POST":
        form = TenenciaForm(request.POST, vehiculo=vehiculo)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    Tenencia.objects.create(
                        vehiculo=vehiculo,
                        anio_fiscal=data["anio_fiscal"],
                        estatus_tenencia=data["estatus_tenencia"],
                        monto_tenencia=data.get("monto_tenencia"),
                        fecha_pago=data.get("fecha_pago"),
                    )
                messages.success(
                    request,
                    f"Tenencia {data['anio_fiscal']} registrada correctamente.",
                )
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo registrar la tenencia. Ya existe un registro para "
                    "este vehículo en ese año fiscal.",
                )
    else:
        form = TenenciaForm(vehiculo=vehiculo)

    return render(request, "vehiculos/tenencia_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "es_edicion": False,
    })


@login_required
def tenencia_editar(request, pk, tenencia_pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    tenencia = get_object_or_404(Tenencia, pk=tenencia_pk, vehiculo=vehiculo)

    if request.method == "POST":
        form = TenenciaForm(request.POST, vehiculo=vehiculo, tenencia_pk=tenencia.pk)
        if form.is_valid():
            data = form.cleaned_data
            tenencia.anio_fiscal = data["anio_fiscal"]
            tenencia.estatus_tenencia = data["estatus_tenencia"]
            tenencia.monto_tenencia = data.get("monto_tenencia")
            tenencia.fecha_pago = data.get("fecha_pago")
            try:
                with transaction.atomic():
                    tenencia.save()
                messages.success(request, "Tenencia actualizada correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo actualizar la tenencia. Ya existe un registro para "
                    "este vehículo en ese año fiscal.",
                )
    else:
        form = TenenciaForm(
            vehiculo=vehiculo,
            tenencia_pk=tenencia.pk,
            initial={
                "anio_fiscal": tenencia.anio_fiscal,
                "estatus_tenencia": tenencia.estatus_tenencia,
                "monto_tenencia": tenencia.monto_tenencia,
                "fecha_pago": tenencia.fecha_pago,
            },
        )

    return render(request, "vehiculos/tenencia_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "tenencia": tenencia,
        "es_edicion": True,
    })


# ---------------------------------------------------------------------------
# Adeudos vehiculares
# ---------------------------------------------------------------------------

@login_required
def adeudo_nuevo(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)

    if request.method == "POST":
        form = AdeudoVehicularForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    AdeudoVehicular.objects.create(
                        vehiculo=vehiculo,
                        tipo_adeudo=data["tipo_adeudo"],
                        monto_adeudo=data.get("monto_adeudo"),
                        estatus_adeudo=data["estatus_adeudo"],
                        fecha_consulta=data.get("fecha_consulta"),
                        observacion_adeudo=data.get("observacion_adeudo") or None,
                    )
                messages.success(request, "Adeudo registrado correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(request, "No se pudo registrar el adeudo. Intenta nuevamente.")
    else:
        form = AdeudoVehicularForm(initial={"estatus_adeudo": AdeudoVehicular.EstatusAdeudo.PENDIENTE})

    return render(request, "vehiculos/adeudo_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "es_edicion": False,
    })


@login_required
def adeudo_editar(request, pk, adeudo_pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    adeudo = get_object_or_404(AdeudoVehicular, pk=adeudo_pk, vehiculo=vehiculo)

    if adeudo.estatus_adeudo in (
        AdeudoVehicular.EstatusAdeudo.PAGADO,
        AdeudoVehicular.EstatusAdeudo.CANCELADO,
    ):
        messages.info(
            request,
            "Este adeudo ya está pagado o cancelado y no se puede editar. "
            "El historial se conserva tal como quedó.",
        )
        return redirect("vehiculos:detalle", pk=pk)

    if request.method == "POST":
        form = AdeudoVehicularForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            adeudo.tipo_adeudo = data["tipo_adeudo"]
            adeudo.monto_adeudo = data.get("monto_adeudo")
            adeudo.estatus_adeudo = data["estatus_adeudo"]
            adeudo.fecha_consulta = data.get("fecha_consulta")
            adeudo.observacion_adeudo = data.get("observacion_adeudo") or None
            try:
                with transaction.atomic():
                    adeudo.save()
                messages.success(request, "Adeudo actualizado correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(request, "No se pudo actualizar el adeudo. Intenta nuevamente.")
    else:
        form = AdeudoVehicularForm(initial={
            "tipo_adeudo": adeudo.tipo_adeudo,
            "monto_adeudo": adeudo.monto_adeudo,
            "estatus_adeudo": adeudo.estatus_adeudo,
            "fecha_consulta": adeudo.fecha_consulta,
            "observacion_adeudo": adeudo.observacion_adeudo,
        })

    return render(request, "vehiculos/adeudo_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "adeudo": adeudo,
        "es_edicion": True,
    })


@login_required
@require_POST
def adeudo_pagar(request, pk, adeudo_pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    adeudo = get_object_or_404(AdeudoVehicular, pk=adeudo_pk, vehiculo=vehiculo)

    if adeudo.estatus_adeudo in (
        AdeudoVehicular.EstatusAdeudo.PAGADO,
        AdeudoVehicular.EstatusAdeudo.CANCELADO,
    ):
        messages.error(request, "Este adeudo ya está pagado o cancelado.")
        return redirect("vehiculos:detalle", pk=pk)

    with transaction.atomic():
        adeudo.estatus_adeudo = AdeudoVehicular.EstatusAdeudo.PAGADO
        adeudo.save(update_fields=["estatus_adeudo", "fecha_actualizacion"])
    messages.success(request, f"Adeudo «{adeudo.tipo_adeudo}» marcado como pagado.")
    return redirect("vehiculos:detalle", pk=pk)


@login_required
@require_POST
def adeudo_cancelar(request, pk, adeudo_pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    adeudo = get_object_or_404(AdeudoVehicular, pk=adeudo_pk, vehiculo=vehiculo)

    if adeudo.estatus_adeudo in (
        AdeudoVehicular.EstatusAdeudo.PAGADO,
        AdeudoVehicular.EstatusAdeudo.CANCELADO,
    ):
        messages.error(request, "Este adeudo ya está pagado o cancelado.")
        return redirect("vehiculos:detalle", pk=pk)

    with transaction.atomic():
        adeudo.estatus_adeudo = AdeudoVehicular.EstatusAdeudo.CANCELADO
        adeudo.save(update_fields=["estatus_adeudo", "fecha_actualizacion"])
    messages.success(request, f"Adeudo «{adeudo.tipo_adeudo}» cancelado.")
    return redirect("vehiculos:detalle", pk=pk)


# ---------------------------------------------------------------------------
# Observaciones / bitácora
# ---------------------------------------------------------------------------

@login_required
def observacion_nueva(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)

    if request.method == "POST":
        form = ObservacionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    Observacion.objects.create(
                        vehiculo=vehiculo,
                        tipo_observacion=data["tipo_observacion"],
                        texto_observacion=data["texto_observacion"],
                        autor_registro=request.user,
                    )
                messages.success(request, "Observación registrada correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(request, "No se pudo registrar la observación. Intenta nuevamente.")
    else:
        form = ObservacionForm()

    return render(request, "vehiculos/observacion_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "es_edicion": False,
    })


@login_required
def observacion_editar(request, pk, observacion_pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    observacion = get_object_or_404(Observacion, pk=observacion_pk, vehiculo=vehiculo)

    # Política de edición: solo quien la registró puede editarla. Las
    # observaciones sin autor (datos demo o capturadas antes de esta fase)
    # se consideran de uso común y cualquier persona autenticada puede
    # corregirlas.
    puede_editar = (
        observacion.autor_registro_id is None
        or observacion.autor_registro_id == request.user.id
    )
    if not puede_editar:
        messages.info(request, "Solo quien registró esta observación puede editarla.")
        return redirect("vehiculos:detalle", pk=pk)

    if request.method == "POST":
        form = ObservacionForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            observacion.tipo_observacion = data["tipo_observacion"]
            observacion.texto_observacion = data["texto_observacion"]
            try:
                with transaction.atomic():
                    observacion.save()
                messages.success(request, "Observación actualizada correctamente.")
                return redirect("vehiculos:detalle", pk=pk)
            except IntegrityError:
                messages.error(request, "No se pudo actualizar la observación. Intenta nuevamente.")
    else:
        form = ObservacionForm(initial={
            "tipo_observacion": observacion.tipo_observacion,
            "texto_observacion": observacion.texto_observacion,
        })

    return render(request, "vehiculos/observacion_form.html", {
        "form": form,
        "vehiculo": vehiculo,
        "observacion": observacion,
        "es_edicion": True,
    })


# ---------------------------------------------------------------------------
# GPS
# ---------------------------------------------------------------------------

@login_required
def gps_instalar(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    instalacion_actual = vehiculo.instalaciones_gps.filter(fecha_retiro__isnull=True).select_related("gps").first()

    if instalacion_actual:
        messages.info(
            request,
            "Este vehículo ya tiene un GPS instalado. Usa \"Cambiar GPS\" o retíralo primero.",
        )
        return redirect("vehiculos:detalle", pk=pk)

    if request.method == "POST":
        form = InstalacionGpsForm(request.POST, vehiculo=vehiculo)
        if form.is_valid():
            data = form.cleaned_data
            gps = data["gps"]
            # Revalida disponibilidad en el servidor: el queryset del formulario
            # pudo haberse generado antes de que alguien más ocupara este GPS.
            if InstalacionGps.objects.filter(gps=gps, fecha_retiro__isnull=True).exists():
                form.add_error("gps", "Este GPS ya está instalado en otro vehículo.")
            else:
                try:
                    with transaction.atomic():
                        InstalacionGps.objects.create(
                            vehiculo=vehiculo,
                            gps=gps,
                            fecha_instalacion=data.get("fecha_instalacion") or localdate(),
                        )
                    messages.success(request, f"GPS {gps.imei} instalado correctamente.")
                    return redirect("vehiculos:detalle", pk=pk)
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo instalar el GPS. Verifica que siga disponible.",
                    )
    else:
        form = InstalacionGpsForm(vehiculo=vehiculo, initial={"fecha_instalacion": localdate()})

    return render(request, "vehiculos/gps_instalar.html", {"form": form, "vehiculo": vehiculo})


@login_required
@require_POST
def gps_retirar(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    instalacion = (
        vehiculo.instalaciones_gps.filter(fecha_retiro__isnull=True).select_related("gps").first()
    )
    if not instalacion:
        messages.error(request, "Este vehículo no tiene un GPS instalado para retirar.")
        return redirect("vehiculos:detalle", pk=pk)

    fecha_retiro_raw = request.POST.get("fecha_retiro", "").strip()
    fecha_retiro = parse_date(fecha_retiro_raw) if fecha_retiro_raw else localdate()
    if fecha_retiro is None or (
        instalacion.fecha_instalacion and fecha_retiro < instalacion.fecha_instalacion
    ):
        messages.error(
            request,
            "La fecha de retiro no es válida: no puede ser anterior a la instalación.",
        )
        return redirect("vehiculos:detalle", pk=pk)

    with transaction.atomic():
        instalacion.fecha_retiro = fecha_retiro
        instalacion.save(update_fields=["fecha_retiro", "fecha_actualizacion"])
    messages.success(request, f"GPS {instalacion.gps.imei} retirado correctamente.")
    return redirect("vehiculos:detalle", pk=pk)


@login_required
def gps_cambiar(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    instalacion_actual = (
        vehiculo.instalaciones_gps.filter(fecha_retiro__isnull=True).select_related("gps").first()
    )

    if not instalacion_actual:
        messages.info(
            request,
            "Este vehículo no tiene GPS instalado actualmente. Usa \"Instalar GPS\".",
        )
        return redirect("vehiculos:gps_instalar", pk=pk)

    if request.method == "POST":
        form = InstalacionGpsForm(request.POST, vehiculo=vehiculo)
        if form.is_valid():
            data = form.cleaned_data
            gps_nuevo = data["gps"]
            fecha_cambio = data.get("fecha_instalacion") or localdate()

            if instalacion_actual.fecha_instalacion and fecha_cambio < instalacion_actual.fecha_instalacion:
                form.add_error(
                    "fecha_instalacion",
                    "La nueva fecha no puede ser anterior a la instalación actual.",
                )
            elif InstalacionGps.objects.filter(gps=gps_nuevo, fecha_retiro__isnull=True).exists():
                form.add_error("gps", "Este GPS ya está instalado en otro vehículo.")
            else:
                try:
                    with transaction.atomic():
                        # Se cierra primero la instalación actual: el vehículo no
                        # puede tener dos GPS activos a la vez. Si la instalación
                        # nueva falla más abajo, transaction.atomic() revierte
                        # también este cierre, así que el GPS anterior nunca
                        # queda retirado sin reemplazo.
                        instalacion_actual.fecha_retiro = fecha_cambio
                        instalacion_actual.save(update_fields=["fecha_retiro", "fecha_actualizacion"])
                        InstalacionGps.objects.create(
                            vehiculo=vehiculo,
                            gps=gps_nuevo,
                            fecha_instalacion=fecha_cambio,
                        )
                    messages.success(request, f"GPS cambiado a {gps_nuevo.imei}.")
                    return redirect("vehiculos:detalle", pk=pk)
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo cambiar el GPS. Es posible que ya no esté disponible.",
                    )
    else:
        form = InstalacionGpsForm(vehiculo=vehiculo)

    return render(request, "vehiculos/gps_cambiar.html", {
        "form": form,
        "vehiculo": vehiculo,
        "instalacion_actual": instalacion_actual,
    })


# ---------------------------------------------------------------------------
# TAG de telepeaje
# ---------------------------------------------------------------------------

@login_required
def tag_asignar(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    asignacion_actual = vehiculo.asignaciones_tag.filter(fecha_fin__isnull=True).select_related("tag").first()

    if asignacion_actual:
        messages.info(
            request,
            "Este vehículo ya tiene un TAG asignado. Usa \"Cambiar TAG\" o retíralo primero.",
        )
        return redirect("vehiculos:detalle", pk=pk)

    if request.method == "POST":
        form = AsignacionTagForm(request.POST, vehiculo=vehiculo)
        if form.is_valid():
            data = form.cleaned_data
            tag = data["tag"]
            if AsignacionTag.objects.filter(tag=tag, fecha_fin__isnull=True).exists():
                form.add_error("tag", "Este TAG ya está asignado a otro vehículo.")
            else:
                try:
                    with transaction.atomic():
                        AsignacionTag.objects.create(
                            vehiculo=vehiculo,
                            tag=tag,
                            fecha_inicio=data.get("fecha_inicio") or localdate(),
                        )
                    messages.success(request, f"TAG {tag.codigo_tag} asignado correctamente.")
                    return redirect("vehiculos:detalle", pk=pk)
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo asignar el TAG. Verifica que siga disponible.",
                    )
    else:
        form = AsignacionTagForm(vehiculo=vehiculo)

    return render(request, "vehiculos/tag_asignar.html", {"form": form, "vehiculo": vehiculo})


@login_required
@require_POST
def tag_retirar(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    asignacion = vehiculo.asignaciones_tag.filter(fecha_fin__isnull=True).select_related("tag").first()
    if not asignacion:
        messages.error(request, "Este vehículo no tiene un TAG asignado para retirar.")
        return redirect("vehiculos:detalle", pk=pk)

    fecha_fin_raw = request.POST.get("fecha_fin", "").strip()
    fecha_fin = parse_date(fecha_fin_raw) if fecha_fin_raw else localdate()
    if fecha_fin is None or (asignacion.fecha_inicio and fecha_fin < asignacion.fecha_inicio):
        messages.error(
            request,
            "La fecha de retiro no es válida: no puede ser anterior al inicio de la asignación.",
        )
        return redirect("vehiculos:detalle", pk=pk)

    with transaction.atomic():
        asignacion.fecha_fin = fecha_fin
        asignacion.save(update_fields=["fecha_fin", "fecha_actualizacion"])
    messages.success(request, f"TAG {asignacion.tag.codigo_tag} retirado correctamente.")
    return redirect("vehiculos:detalle", pk=pk)


@login_required
def tag_cambiar(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    asignacion_actual = (
        vehiculo.asignaciones_tag.filter(fecha_fin__isnull=True).select_related("tag").first()
    )

    if not asignacion_actual:
        messages.info(
            request,
            "Este vehículo no tiene TAG asignado actualmente. Usa \"Asignar TAG\".",
        )
        return redirect("vehiculos:tag_asignar", pk=pk)

    if request.method == "POST":
        form = AsignacionTagForm(request.POST, vehiculo=vehiculo)
        if form.is_valid():
            data = form.cleaned_data
            tag_nuevo = data["tag"]
            fecha_cambio = data.get("fecha_inicio") or localdate()

            if asignacion_actual.fecha_inicio and fecha_cambio < asignacion_actual.fecha_inicio:
                form.add_error(
                    "fecha_inicio",
                    "La nueva fecha no puede ser anterior al inicio de la asignación actual.",
                )
            elif AsignacionTag.objects.filter(tag=tag_nuevo, fecha_fin__isnull=True).exists():
                form.add_error("tag", "Este TAG ya está asignado a otro vehículo.")
            else:
                try:
                    with transaction.atomic():
                        # Igual que con el GPS: se cierra la asignación actual
                        # antes de crear la nueva, dentro de la misma
                        # transacción, para que un fallo en la nueva no deje al
                        # vehículo sin TAG.
                        asignacion_actual.fecha_fin = fecha_cambio
                        asignacion_actual.save(update_fields=["fecha_fin", "fecha_actualizacion"])
                        AsignacionTag.objects.create(
                            vehiculo=vehiculo,
                            tag=tag_nuevo,
                            fecha_inicio=fecha_cambio,
                        )
                    messages.success(request, f"TAG cambiado a {tag_nuevo.codigo_tag}.")
                    return redirect("vehiculos:detalle", pk=pk)
                except IntegrityError:
                    messages.error(
                        request,
                        "No se pudo cambiar el TAG. Es posible que ya no esté disponible.",
                    )
    else:
        form = AsignacionTagForm(vehiculo=vehiculo)

    return render(request, "vehiculos/tag_cambiar.html", {
        "form": form,
        "vehiculo": vehiculo,
        "asignacion_actual": asignacion_actual,
    })
