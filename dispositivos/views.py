from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DispositivoGpsForm, TagTelepeajeForm
from .models import AsignacionTag, DispositivoGps, InstalacionGps, TagTelepeaje


# ---------------------------------------------------------------------------
# Catálogo de GPS
# ---------------------------------------------------------------------------

def _gps_queryset_anotado():
    instalacion_activa = InstalacionGps.objects.filter(gps=OuterRef("pk"), fecha_retiro__isnull=True)
    return (
        DispositivoGps.objects.annotate(tiene_instalacion_activa=Exists(instalacion_activa))
        .prefetch_related(
            Prefetch(
                "instalaciones",
                queryset=InstalacionGps.objects.filter(fecha_retiro__isnull=True).select_related("vehiculo"),
                to_attr="instalacion_actual_list",
            )
        )
    )


@login_required
def gps_lista(request):
    gpss = _gps_queryset_anotado()

    q = request.GET.get("q", "").strip()
    estatus = request.GET.get("estatus", "").strip()
    disponibilidad = request.GET.get("disponibilidad", "").strip()

    if q:
        gpss = gpss.filter(Q(imei__icontains=q) | Q(numero_gps__icontains=q))
    if estatus:
        gpss = gpss.filter(estatus_gps=estatus)
    if disponibilidad == "DISPONIBLE":
        gpss = gpss.filter(estatus_gps=DispositivoGps.Estatus.ACTIVO, tiene_instalacion_activa=False)
    elif disponibilidad == "INSTALADO":
        gpss = gpss.filter(tiene_instalacion_activa=True)

    query_params = {k: v for k, v in {"q": q, "estatus": estatus, "disponibilidad": disponibilidad}.items() if v}
    query_string = urlencode(query_params)

    paginator = Paginator(gpss, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "dispositivos/gps_lista.html", {
        "page_obj": page_obj,
        "q": q,
        "estatus": estatus,
        "disponibilidad": disponibilidad,
        "query_string": query_string,
        "estatus_choices": DispositivoGps.Estatus.choices,
    })


@login_required
def gps_nuevo(request):
    if request.method == "POST":
        form = DispositivoGpsForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    gps = DispositivoGps.objects.create(
                        imei=data["imei"],
                        numero_gps=data.get("numero_gps"),
                        estatus_gps=data["estatus_gps"],
                    )
                messages.success(request, f"Dispositivo GPS {gps.imei} registrado correctamente.")
                return redirect("dispositivos:gps_detalle", pk=gps.pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo registrar el GPS. Verifica que el IMEI no esté duplicado.",
                )
    else:
        form = DispositivoGpsForm()

    return render(request, "dispositivos/gps_form.html", {"form": form, "es_edicion": False})


@login_required
def gps_editar(request, pk):
    gps = get_object_or_404(DispositivoGps, pk=pk)

    if request.method == "POST":
        form = DispositivoGpsForm(request.POST, gps_pk=gps.pk)
        if form.is_valid():
            data = form.cleaned_data
            gps.imei = data["imei"]
            gps.numero_gps = data.get("numero_gps")
            gps.estatus_gps = data["estatus_gps"]
            try:
                with transaction.atomic():
                    gps.save()
                messages.success(request, "Dispositivo GPS actualizado correctamente.")
                return redirect("dispositivos:gps_detalle", pk=gps.pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo actualizar el GPS. Verifica que el IMEI no esté duplicado.",
                )
    else:
        form = DispositivoGpsForm(gps_pk=gps.pk, initial={
            "imei": gps.imei,
            "numero_gps": gps.numero_gps,
            "estatus_gps": gps.estatus_gps,
        })

    return render(request, "dispositivos/gps_form.html", {"form": form, "gps": gps, "es_edicion": True})


@login_required
def gps_detalle(request, pk):
    gps = get_object_or_404(DispositivoGps, pk=pk)
    instalaciones = list(gps.instalaciones.select_related("vehiculo").order_by("-fecha_instalacion"))
    instalacion_actual = next((i for i in instalaciones if i.es_actual), None)

    return render(request, "dispositivos/gps_detalle.html", {
        "gps": gps,
        "instalaciones": instalaciones,
        "instalacion_actual": instalacion_actual,
    })


# ---------------------------------------------------------------------------
# Catálogo de TAG de telepeaje
# ---------------------------------------------------------------------------

def _tag_queryset_anotado():
    asignacion_activa = AsignacionTag.objects.filter(tag=OuterRef("pk"), fecha_fin__isnull=True)
    return (
        TagTelepeaje.objects.annotate(tiene_asignacion_activa=Exists(asignacion_activa))
        .prefetch_related(
            Prefetch(
                "asignaciones",
                queryset=AsignacionTag.objects.filter(fecha_fin__isnull=True).select_related("vehiculo"),
                to_attr="asignacion_actual_list",
            )
        )
    )


@login_required
def tag_lista(request):
    tags = _tag_queryset_anotado()

    q = request.GET.get("q", "").strip()
    estatus = request.GET.get("estatus", "").strip()
    disponibilidad = request.GET.get("disponibilidad", "").strip()

    if q:
        tags = tags.filter(Q(codigo_tag__icontains=q) | Q(codigo_tag_corto__icontains=q))
    if estatus:
        tags = tags.filter(estatus_tag=estatus)
    if disponibilidad == "DISPONIBLE":
        tags = tags.filter(estatus_tag=TagTelepeaje.Estatus.ACTIVO, tiene_asignacion_activa=False)
    elif disponibilidad == "ASIGNADO":
        tags = tags.filter(tiene_asignacion_activa=True)

    query_params = {k: v for k, v in {"q": q, "estatus": estatus, "disponibilidad": disponibilidad}.items() if v}
    query_string = urlencode(query_params)

    paginator = Paginator(tags, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "dispositivos/tag_lista.html", {
        "page_obj": page_obj,
        "q": q,
        "estatus": estatus,
        "disponibilidad": disponibilidad,
        "query_string": query_string,
        "estatus_choices": TagTelepeaje.Estatus.choices,
    })


@login_required
def tag_nuevo(request):
    if request.method == "POST":
        form = TagTelepeajeForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    tag = TagTelepeaje.objects.create(
                        codigo_tag=data["codigo_tag"],
                        codigo_tag_corto=data.get("codigo_tag_corto"),
                        estatus_tag=data["estatus_tag"],
                    )
                messages.success(request, f"TAG {tag.codigo_tag} registrado correctamente.")
                return redirect("dispositivos:tag_detalle", pk=tag.pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo registrar el TAG. Verifica que el código no esté duplicado.",
                )
    else:
        form = TagTelepeajeForm()

    return render(request, "dispositivos/tag_form.html", {"form": form, "es_edicion": False})


@login_required
def tag_editar(request, pk):
    tag = get_object_or_404(TagTelepeaje, pk=pk)

    if request.method == "POST":
        form = TagTelepeajeForm(request.POST, tag_pk=tag.pk)
        if form.is_valid():
            data = form.cleaned_data
            tag.codigo_tag = data["codigo_tag"]
            tag.codigo_tag_corto = data.get("codigo_tag_corto")
            tag.estatus_tag = data["estatus_tag"]
            try:
                with transaction.atomic():
                    tag.save()
                messages.success(request, "TAG actualizado correctamente.")
                return redirect("dispositivos:tag_detalle", pk=tag.pk)
            except IntegrityError:
                messages.error(
                    request,
                    "No se pudo actualizar el TAG. Verifica que el código no esté duplicado.",
                )
    else:
        form = TagTelepeajeForm(tag_pk=tag.pk, initial={
            "codigo_tag": tag.codigo_tag,
            "codigo_tag_corto": tag.codigo_tag_corto,
            "estatus_tag": tag.estatus_tag,
        })

    return render(request, "dispositivos/tag_form.html", {"form": form, "tag": tag, "es_edicion": True})


@login_required
def tag_detalle(request, pk):
    tag = get_object_or_404(TagTelepeaje, pk=pk)
    asignaciones = list(tag.asignaciones.select_related("vehiculo").order_by("-fecha_inicio"))
    asignacion_actual = next((a for a in asignaciones if a.es_actual), None)

    return render(request, "dispositivos/tag_detalle.html", {
        "tag": tag,
        "asignaciones": asignaciones,
        "asignacion_actual": asignacion_actual,
    })
