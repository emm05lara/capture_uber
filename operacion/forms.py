from django import forms
from django.utils.timezone import localdate

from actores.models import Conductor, PlataformaOperativa, Socio
from .models import AsignacionVehiculo


def conductores_disponibles():
    """Conductores activos, con al menos una referencia y sin asignación vigente."""
    ocupados = AsignacionVehiculo.objects.filter(fecha_fin__isnull=True).values("conductor_id")
    return (
        Conductor.objects
        .filter(estatus_conductor=Conductor.Estatus.ACTIVO)
        .filter(referencias__isnull=False)
        .exclude(pk__in=ocupados)
        .distinct()
        .order_by("nombre_completo")
    )


class AsignacionVehiculoForm(forms.Form):
    conductor = forms.ModelChoiceField(
        queryset=Conductor.objects.none(),
        label="Conductor",
        empty_label="— Selecciona un conductor —",
    )
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        initial=localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    plataforma = forms.ModelChoiceField(
        queryset=PlataformaOperativa.objects.all(),
        label="Plataforma operativa",
        required=False,
        empty_label="— Sin especificar —",
    )
    socio = forms.ModelChoiceField(
        queryset=Socio.objects.all(),
        label="Socio",
        required=False,
        empty_label="— Sin especificar —",
    )
    cuenta = forms.CharField(
        label="Cuenta operativa",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej. cuenta-uber-01"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["conductor"].queryset = conductores_disponibles()

    def clean_cuenta(self):
        return (self.cleaned_data.get("cuenta") or "").strip() or None
