from django import forms

from .models import Conductor


class ConductorForm(forms.Form):
    nombre_completo = forms.CharField(
        label="Nombre completo",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Ej. Juan García López", "autofocus": True}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej. 55 1234 5678"}),
    )
    correo = forms.EmailField(
        label="Correo electrónico",
        max_length=120,
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "conductor@empresa.com"}),
    )
    estatus_conductor = forms.ChoiceField(
        label="Estatus",
        choices=Conductor.Estatus.choices,
        initial=Conductor.Estatus.ACTIVO,
    )
    numero_licencia = forms.CharField(
        label="Número de licencia",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Ej. CDMX123456789"}),
    )
    tipo_licencia = forms.ChoiceField(
        label="Tipo de licencia",
        choices=[("", "— Sin especificar —")] + Conductor.TipoLicencia.choices,
        required=False,
    )
    fecha_vencimiento_licencia = forms.DateField(
        label="Vencimiento de licencia",
        required=False,
        help_text="Fecha en que vence la licencia de conducir.",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    curp = forms.CharField(
        label="CURP",
        max_length=18,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "Ej. GALA800101HDFRCR01",
            "style": "text-transform: uppercase",
            "maxlength": "18",
        }),
    )

    def clean_tipo_licencia(self):
        return self.cleaned_data.get("tipo_licencia") or None

    def clean_curp(self):
        return (self.cleaned_data.get("curp") or "").upper().strip() or None
