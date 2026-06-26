from django import forms

from catalogos.models import Color, EntidadFederativa, ModeloVehiculo
from .models import Vehiculo


class NuevoVehiculoForm(forms.Form):
    numero_interno = forms.CharField(
        label="Número interno",
        max_length=50,
        required=False,
        help_text="Clave o folio interno de tu empresa. Puedes dejarlo vacío.",
        widget=forms.TextInput(attrs={"placeholder": "Ej. V-011, U-042…"}),
    )
    modelo_vehiculo = forms.ModelChoiceField(
        queryset=ModeloVehiculo.objects.select_related("marca").order_by(
            "marca__nombre_marca", "nombre_modelo_comercial"
        ),
        label="Marca y modelo",
        empty_label="— Selecciona marca y modelo —",
    )
    anio_modelo = forms.IntegerField(
        label="Año modelo",
        min_value=1990,
        max_value=2030,
        widget=forms.NumberInput(attrs={"placeholder": "Ej. 2024"}),
    )
    color = forms.ModelChoiceField(
        queryset=Color.objects.all(),
        label="Color",
        empty_label="— Selecciona color —",
    )
    numero_serie = forms.CharField(
        label="Número de serie / VIN",
        max_length=40,
        help_text="Identificador único del vehículo (generalmente 17 caracteres).",
        widget=forms.TextInput(attrs={"placeholder": "Ej. 3VWFE21C04M000001", "class": "text-uppercase"}),
    )
    estatus_unidad = forms.ChoiceField(
        label="Estatus del vehículo",
        choices=Vehiculo.EstatusUnidad.choices,
        initial=Vehiculo.EstatusUnidad.ACTIVA,
    )
    placas = forms.CharField(
        label="Placas",
        max_length=20,
        required=False,
        help_text="Opcional. Puedes agregarlas después desde el detalle del vehículo.",
        widget=forms.TextInput(attrs={"placeholder": "Ej. ABC-123"}),
    )
    entidad_federativa = forms.ModelChoiceField(
        queryset=EntidadFederativa.objects.all(),
        label="Entidad federativa de las placas",
        empty_label="— Selecciona entidad —",
        required=False,
        help_text="Obligatoria si se capturan placas.",
    )

    def clean_numero_serie(self):
        vin = self.cleaned_data["numero_serie"].upper().strip()
        if Vehiculo.objects.filter(numero_serie=vin).exists():
            raise forms.ValidationError(
                "Ya existe un vehículo registrado con este número de serie."
            )
        return vin

    def clean_numero_interno(self):
        num = self.cleaned_data.get("numero_interno", "").strip() or None
        if num and Vehiculo.objects.filter(numero_interno=num).exists():
            raise forms.ValidationError(
                "Ya existe un vehículo con este número interno. Usa uno diferente."
            )
        return num

    def clean(self):
        cleaned = super().clean()
        placas = (cleaned.get("placas") or "").strip().upper() or None
        entidad = cleaned.get("entidad_federativa")
        if placas and not entidad:
            self.add_error(
                "entidad_federativa",
                "Indica la entidad federativa en la que están registradas estas placas.",
            )
        cleaned["placas"] = placas
        return cleaned
