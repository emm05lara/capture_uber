from django.db import models
from django.db.models.functions import Upper
from django.utils.timezone import localdate


# ---------------------------------------------------------------------------
# Jerarquía PERSONA → CONDUCTOR, TITULAR_POLIZA
# Especialización parcial y con traslape: una persona puede ser conductor,
# titular de póliza, ambos o ninguno.
# ---------------------------------------------------------------------------

class Persona(models.Model):
    nombre_completo = models.CharField(
        max_length=150,
        verbose_name="nombre completo",
    )
    telefono = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="teléfono",
    )
    correo = models.EmailField(
        max_length=120,
        blank=True,
        null=True,
        verbose_name="correo electrónico",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "persona"
        verbose_name_plural = "personas"
        ordering = ["nombre_completo"]
        indexes = [
            models.Index(Upper("nombre_completo"), name="idx_persona_nombre"),
        ]

    def __str__(self):
        return self.nombre_completo


class Conductor(Persona):
    class Estatus(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"
        BLOQUEADO = "BLOQUEADO", "Bloqueado"
        BAJA = "BAJA", "Baja"

    class TipoLicencia(models.TextChoices):
        A = "A", "A — Motocicleta"
        B = "B", "B — Automóvil"
        C = "C", "C — Camión ligero"
        D = "D", "D — Autobús"
        E = "E", "E — Vehículo especial"

    estatus_conductor = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVO,
        verbose_name="estatus",
    )
    numero_licencia = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="número de licencia",
    )
    tipo_licencia = models.CharField(
        max_length=1,
        choices=TipoLicencia.choices,
        blank=True,
        null=True,
        verbose_name="tipo de licencia",
    )
    fecha_vencimiento_licencia = models.DateField(
        blank=True,
        null=True,
        verbose_name="vencimiento de licencia",
    )
    curp = models.CharField(
        max_length=18,
        blank=True,
        null=True,
        verbose_name="CURP",
    )

    class Meta:
        verbose_name = "conductor"
        verbose_name_plural = "conductores"
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_conductor__in=["ACTIVO", "INACTIVO", "BLOQUEADO", "BAJA"]),
                name="chk_conductor_estatus",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(tipo_licencia__isnull=True)
                    | models.Q(tipo_licencia__in=["A", "B", "C", "D", "E"])
                ),
                name="chk_conductor_tipo_licencia",
            ),
        ]
        indexes = [
            models.Index(fields=["numero_licencia"], name="idx_conductor_licencia"),
        ]

    @property
    def licencia_vigente(self):
        if self.fecha_vencimiento_licencia is None:
            return None
        return self.fecha_vencimiento_licencia >= localdate()


class TitularPoliza(Persona):
    class Estatus(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"

    estatus_titular = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVO,
        verbose_name="estatus",
    )

    class Meta:
        verbose_name = "titular de póliza"
        verbose_name_plural = "titulares de póliza"
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_titular__in=["ACTIVO", "INACTIVO"]),
                name="chk_titular_poliza_estatus",
            ),
        ]


# ---------------------------------------------------------------------------
# Jerarquía ORGANIZACION → PLATAFORMA_OPERATIVA, SOCIO, ASEGURADORA
# Especialización parcial y con traslape: una organización puede cumplir
# uno o varios roles simultáneamente.
# ---------------------------------------------------------------------------

class Organizacion(models.Model):
    clave_organizacion = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="clave interna",
    )
    nombre_organizacion = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="nombre o razón social",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "organización"
        verbose_name_plural = "organizaciones"
        ordering = ["nombre_organizacion"]
        indexes = [
            models.Index(Upper("clave_organizacion"), name="idx_org_clave"),
            models.Index(Upper("nombre_organizacion"), name="idx_org_nombre"),
        ]

    def __str__(self):
        if self.clave_organizacion:
            return f"{self.nombre_organizacion} ({self.clave_organizacion})"
        return self.nombre_organizacion


class PlataformaOperativa(Organizacion):
    class Estatus(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        INACTIVA = "INACTIVA", "Inactiva"

    estatus_plataforma = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVA,
        verbose_name="estatus",
    )

    class Meta:
        verbose_name = "plataforma operativa"
        verbose_name_plural = "plataformas operativas"
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_plataforma__in=["ACTIVA", "INACTIVA"]),
                name="chk_plataforma_estatus",
            ),
        ]


class Socio(Organizacion):
    class Estatus(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"

    estatus_socio = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVO,
        verbose_name="estatus",
    )

    class Meta:
        verbose_name = "socio"
        verbose_name_plural = "socios"
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_socio__in=["ACTIVO", "INACTIVO"]),
                name="chk_socio_estatus",
            ),
        ]


class Aseguradora(Organizacion):
    class Estatus(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        INACTIVA = "INACTIVA", "Inactiva"

    estatus_aseguradora = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVA,
        verbose_name="estatus",
    )

    class Meta:
        verbose_name = "aseguradora"
        verbose_name_plural = "aseguradoras"
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_aseguradora__in=["ACTIVA", "INACTIVA"]),
                name="chk_aseguradora_estatus",
            ),
        ]
