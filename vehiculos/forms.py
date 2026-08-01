from django import forms

from actores.models import Aseguradora, TitularPoliza
from catalogos.models import Color, EntidadFederativa, ModeloVehiculo
from .models import Emplacamiento, PolizaSeguro, TarjetaCirculacion, Vehiculo, VerificacionVehicular


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


# ---------------------------------------------------------------------------
# Editar datos básicos de un vehículo existente (VIN es inmutable, no aparece)
# ---------------------------------------------------------------------------

class EditarVehiculoForm(forms.Form):
    def __init__(self, *args, vehiculo_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehiculo_pk = vehiculo_pk

    numero_interno = forms.CharField(
        label="Número interno",
        max_length=50,
        required=False,
        help_text="Clave o folio interno de tu empresa. Deja vacío si no aplica.",
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
    estatus_unidad = forms.ChoiceField(
        label="Estatus del vehículo",
        choices=Vehiculo.EstatusUnidad.choices,
    )

    def clean_numero_interno(self):
        num = (self.cleaned_data.get("numero_interno") or "").strip() or None
        if num:
            qs = Vehiculo.objects.filter(numero_interno=num)
            if self.vehiculo_pk:
                qs = qs.exclude(pk=self.vehiculo_pk)
            if qs.exists():
                raise forms.ValidationError(
                    "Ya existe un vehículo con este número interno. Usa uno diferente."
                )
        return num


# ---------------------------------------------------------------------------
# Registrar nueva placa (cierra la placa activa anterior en la vista)
# ---------------------------------------------------------------------------

class NuevaPlacaForm(forms.Form):
    def __init__(self, *args, vehiculo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehiculo = vehiculo

    placas = forms.CharField(
        label="Placas",
        max_length=20,
        widget=forms.TextInput(attrs={
            "placeholder": "Ej. ABC-123-D",
            "style": "text-transform: uppercase",
            "autofocus": True,
        }),
    )
    entidad_federativa = forms.ModelChoiceField(
        queryset=EntidadFederativa.objects.all(),
        label="Entidad federativa",
        empty_label="— Selecciona entidad —",
        help_text="Estado en el que están registradas estas placas.",
    )
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        required=False,
        help_text="Deja vacío para usar la fecha de hoy.",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_placas(self):
        placas = self.cleaned_data["placas"].upper().strip()
        qs = Emplacamiento.objects.filter(placas__iexact=placas, fecha_fin__isnull=True)
        if self.vehiculo:
            qs = qs.exclude(vehiculo=self.vehiculo)
        if qs.exists():
            raise forms.ValidationError(
                "Estas placas ya están asignadas como activas en otro vehículo."
            )
        return placas


# ---------------------------------------------------------------------------
# Póliza de seguro (alta y edición, siempre ligada a un vehículo)
# ---------------------------------------------------------------------------

class PolizaSeguroForm(forms.Form):
    def __init__(self, *args, vehiculo=None, poliza_pk=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehiculo = vehiculo
        self.poliza_pk = poliza_pk
        self.fields["aseguradora"].queryset = Aseguradora.objects.filter(
            estatus_aseguradora=Aseguradora.Estatus.ACTIVA
        ).order_by("nombre_organizacion")
        self.fields["titular_poliza"].queryset = TitularPoliza.objects.filter(
            estatus_titular=TitularPoliza.Estatus.ACTIVO
        ).order_by("nombre_completo")

    aseguradora = forms.ModelChoiceField(
        queryset=Aseguradora.objects.none(),
        label="Aseguradora",
        empty_label="— Selecciona aseguradora —",
    )
    titular_poliza = forms.ModelChoiceField(
        queryset=TitularPoliza.objects.none(),
        label="Titular de la póliza",
        required=False,
        empty_label="— Sin especificar —",
    )
    numero_poliza = forms.CharField(
        label="Número de póliza",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Ej. POL-2026-0001"}),
    )
    fecha_vigencia_inicio = forms.DateField(
        label="Inicio de vigencia",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_vigencia_fin = forms.DateField(
        label="Fin de vigencia",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    importe_prima = forms.DecimalField(
        label="Importe de prima",
        max_digits=14,
        decimal_places=2,
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"placeholder": "Ej. 8500.00", "step": "0.01"}),
    )

    def clean_numero_poliza(self):
        return self.cleaned_data["numero_poliza"].strip()

    def clean(self):
        cleaned = super().clean()
        aseguradora = cleaned.get("aseguradora")
        numero_poliza = cleaned.get("numero_poliza")
        inicio = cleaned.get("fecha_vigencia_inicio")
        fin = cleaned.get("fecha_vigencia_fin")

        if aseguradora and numero_poliza:
            qs = PolizaSeguro.objects.filter(aseguradora=aseguradora, numero_poliza=numero_poliza)
            if self.poliza_pk:
                qs = qs.exclude(pk=self.poliza_pk)
            if qs.exists():
                self.add_error(
                    "numero_poliza",
                    "Ya existe una póliza con este número para la aseguradora seleccionada.",
                )

        if inicio and fin and fin < inicio:
            self.add_error(
                "fecha_vigencia_fin",
                "La fecha de fin de vigencia no puede ser anterior al inicio.",
            )
        return cleaned


# ---------------------------------------------------------------------------
# Verificación vehicular (alta y edición, siempre ligada a un vehículo)
# ---------------------------------------------------------------------------

class VerificacionVehicularForm(forms.Form):
    semestre = forms.CharField(
        label="Semestre",
        max_length=20,
        help_text="Ejemplo: 2026-1, 2026-2",
        widget=forms.TextInput(attrs={"placeholder": "Ej. 2026-1"}),
    )
    fecha_ultima_verificacion = forms.DateField(
        label="Fecha de última verificación",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_limite_verificacion = forms.DateField(
        label="Fecha límite de verificación",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_semestre(self):
        return self.cleaned_data["semestre"].strip()

    def clean(self):
        cleaned = super().clean()
        ultima = cleaned.get("fecha_ultima_verificacion")
        limite = cleaned.get("fecha_limite_verificacion")
        if ultima and limite and ultima > limite:
            self.add_error(
                "fecha_ultima_verificacion",
                "La fecha de verificación no puede ser posterior a la fecha límite.",
            )
        return cleaned


# ---------------------------------------------------------------------------
# Tarjeta de circulación (alta y edición, siempre ligada a un vehículo)
# ---------------------------------------------------------------------------

class TarjetaCirculacionForm(forms.Form):
    fecha_emision = forms.DateField(
        label="Fecha de emisión",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_vigencia_fin = forms.DateField(
        label="Vigencia hasta",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean(self):
        cleaned = super().clean()
        emision = cleaned.get("fecha_emision")
        fin = cleaned.get("fecha_vigencia_fin")
        if emision and fin and fin < emision:
            self.add_error(
                "fecha_vigencia_fin",
                "La vigencia no puede ser anterior a la fecha de emisión.",
            )
        return cleaned
