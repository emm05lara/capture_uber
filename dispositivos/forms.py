from django import forms
from django.db.models import Exists, OuterRef

from .models import AsignacionTag, DispositivoGps, InstalacionGps, TagTelepeaje


def gps_disponibles_qs():
    """GPS activos y sin una instalación vigente en ningún vehículo."""
    instalacion_activa = InstalacionGps.objects.filter(gps=OuterRef("pk"), fecha_retiro__isnull=True)
    return (
        DispositivoGps.objects.filter(estatus_gps=DispositivoGps.Estatus.ACTIVO)
        .annotate(tiene_instalacion_activa=Exists(instalacion_activa))
        .filter(tiene_instalacion_activa=False)
        .order_by("imei")
    )


def tag_disponibles_qs():
    """TAG activos y sin una asignación vigente en ningún vehículo."""
    asignacion_activa = AsignacionTag.objects.filter(tag=OuterRef("pk"), fecha_fin__isnull=True)
    return (
        TagTelepeaje.objects.filter(estatus_tag=TagTelepeaje.Estatus.ACTIVO)
        .annotate(tiene_asignacion_activa=Exists(asignacion_activa))
        .filter(tiene_asignacion_activa=False)
        .order_by("codigo_tag")
    )


# ---------------------------------------------------------------------------
# Catálogo de dispositivos GPS
# ---------------------------------------------------------------------------

class DispositivoGpsForm(forms.Form):
    def __init__(self, *args, gps_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.gps_pk = gps_pk

    imei = forms.CharField(
        label="IMEI",
        max_length=80,
        widget=forms.TextInput(attrs={"placeholder": "Ej. 864000000000001"}),
    )
    numero_gps = forms.CharField(
        label="Número o identificador interno",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej. GPS-014"}),
    )
    estatus_gps = forms.ChoiceField(
        label="Estatus",
        choices=DispositivoGps.Estatus.choices,
    )

    def clean_imei(self):
        imei = self.cleaned_data["imei"].strip()
        qs = DispositivoGps.objects.filter(imei__iexact=imei)
        if self.gps_pk:
            qs = qs.exclude(pk=self.gps_pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un dispositivo GPS registrado con este IMEI.")
        return imei

    def clean_numero_gps(self):
        return self.cleaned_data.get("numero_gps", "").strip() or None


# ---------------------------------------------------------------------------
# Instalación de GPS en un vehículo (alta y cambio)
# ---------------------------------------------------------------------------

class InstalacionGpsForm(forms.Form):
    def __init__(self, *args, vehiculo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehiculo = vehiculo
        self.fields["gps"].queryset = gps_disponibles_qs()

    gps = forms.ModelChoiceField(
        queryset=DispositivoGps.objects.none(),
        label="Dispositivo GPS",
        empty_label="— Selecciona un GPS disponible —",
    )
    fecha_instalacion = forms.DateField(
        label="Fecha de instalación",
        required=False,
        help_text="Deja vacío para usar la fecha de hoy.",
        widget=forms.DateInput(attrs={"type": "date"}),
    )


# ---------------------------------------------------------------------------
# Catálogo de TAG de telepeaje
# ---------------------------------------------------------------------------

class TagTelepeajeForm(forms.Form):
    def __init__(self, *args, tag_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tag_pk = tag_pk

    codigo_tag = forms.CharField(
        label="Código TAG",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Ej. TAG-000123"}),
    )
    codigo_tag_corto = forms.CharField(
        label="Código corto",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej. T123"}),
    )
    estatus_tag = forms.ChoiceField(
        label="Estatus",
        choices=TagTelepeaje.Estatus.choices,
    )

    def clean_codigo_tag(self):
        codigo = self.cleaned_data["codigo_tag"].strip()
        qs = TagTelepeaje.objects.filter(codigo_tag__iexact=codigo)
        if self.tag_pk:
            qs = qs.exclude(pk=self.tag_pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un TAG registrado con este código.")
        return codigo

    def clean_codigo_tag_corto(self):
        return self.cleaned_data.get("codigo_tag_corto", "").strip() or None


# ---------------------------------------------------------------------------
# Asignación de TAG a un vehículo (alta y cambio)
# ---------------------------------------------------------------------------

class AsignacionTagForm(forms.Form):
    def __init__(self, *args, vehiculo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehiculo = vehiculo
        self.fields["tag"].queryset = tag_disponibles_qs()

    tag = forms.ModelChoiceField(
        queryset=TagTelepeaje.objects.none(),
        label="TAG de telepeaje",
        empty_label="— Selecciona un TAG disponible —",
    )
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        required=False,
        help_text="Deja vacío para usar la fecha de hoy.",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
