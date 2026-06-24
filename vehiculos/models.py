from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Upper
from django.utils import timezone


class VehiculoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(estatus_unidad="ACTIVA")

    def en_taller(self):
        return self.filter(estatus_unidad="TALLER")

    def con_adeudos_pendientes(self):
        return self.filter(adeudos__estatus_adeudo="PENDIENTE").distinct()


# ---------------------------------------------------------------------------
# Entidad principal: VEHÍCULO
# Representa únicamente la unidad física.
# ---------------------------------------------------------------------------

class Vehiculo(models.Model):
    class EstatusUnidad(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        BAJA = "BAJA", "Baja"
        TALLER = "TALLER", "En taller"
        SIN_ASIGNAR = "SIN_ASIGNAR", "Sin asignar"
        SINIESTRADA = "SINIESTRADA", "Siniestrada"
        VENDIDA = "VENDIDA", "Vendida"

    numero_interno = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="número interno",
    )
    modelo_vehiculo = models.ForeignKey(
        "catalogos.ModeloVehiculo",
        on_delete=models.PROTECT,
        related_name="vehiculos",
        verbose_name="modelo",
    )
    color = models.ForeignKey(
        "catalogos.Color",
        on_delete=models.PROTECT,
        related_name="vehiculos",
        verbose_name="color",
    )
    anio_modelo = models.SmallIntegerField(
        verbose_name="año modelo",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
    )
    numero_serie = models.CharField(
        max_length=40,
        unique=True,
        verbose_name="número de serie / VIN",
    )
    estatus_unidad = models.CharField(
        max_length=30,
        choices=EstatusUnidad.choices,
        default=EstatusUnidad.ACTIVA,
        verbose_name="estatus",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    objects = VehiculoQuerySet.as_manager()

    class Meta:
        verbose_name = "vehículo"
        verbose_name_plural = "vehículos"
        ordering = ["numero_interno", "numero_serie"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_unidad__in=[
                    "ACTIVA", "BAJA", "TALLER", "SIN_ASIGNAR", "SINIESTRADA", "VENDIDA",
                ]),
                name="chk_vehiculo_estatus",
            ),
            models.CheckConstraint(
                check=models.Q(anio_modelo__gte=1900) & models.Q(anio_modelo__lte=2100),
                name="chk_vehiculo_anio_modelo",
            ),
        ]
        indexes = [
            models.Index(fields=["estatus_unidad"], name="idx_vehiculo_estatus"),
            models.Index(
                fields=["modelo_vehiculo", "color", "anio_modelo"],
                name="idx_vehiculo_modelo_color_anio",
            ),
        ]

    def __str__(self):
        return f"{self.numero_serie} ({self.modelo_vehiculo})"

    @property
    def emplacamiento_actual(self):
        return self.emplacamientos.filter(fecha_fin__isnull=True).first()

    @property
    def placas_actuales(self):
        emp = self.emplacamiento_actual
        return emp.placas if emp else None

    @property
    def clave_vehiculo(self):
        emp = self.emplacamiento_actual
        if emp is None:
            return None
        modelo = self.modelo_vehiculo.nombre_modelo_comercial
        color = self.color.nombre_color.upper()
        placas = emp.placas.upper()
        return f"{modelo}|{self.anio_modelo}|{color}|{placas}"


# ---------------------------------------------------------------------------
# Historial de placas
# ---------------------------------------------------------------------------

class Emplacamiento(models.Model):
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="emplacamientos",
        verbose_name="vehículo",
    )
    placas = models.CharField(
        max_length=20,
        verbose_name="placas",
    )
    entidad_federativa = models.ForeignKey(
        "catalogos.EntidadFederativa",
        on_delete=models.PROTECT,
        related_name="emplacamientos",
        verbose_name="entidad federativa",
    )
    fecha_inicio = models.DateField(blank=True, null=True, verbose_name="fecha inicio")
    fecha_fin = models.DateField(blank=True, null=True, verbose_name="fecha fin")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "emplacamiento"
        verbose_name_plural = "emplacamientos"
        ordering = ["-fecha_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo"],
                condition=models.Q(fecha_fin__isnull=True),
                name="uq_emplacamiento_actual_por_vehiculo",
            ),
            models.UniqueConstraint(
                Upper("placas"),
                condition=models.Q(fecha_fin__isnull=True),
                name="uq_emplacamiento_placa_actual",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(fecha_fin__isnull=True)
                    | models.Q(fecha_inicio__isnull=True)
                    | models.Q(fecha_fin__gte=models.F("fecha_inicio"))
                ),
                name="chk_emplacamiento_fechas",
            ),
        ]
        indexes = [
            models.Index(Upper("placas"), name="idx_emplacamiento_placas"),
            models.Index(fields=["vehiculo"], name="idx_emplacamiento_vehiculo"),
        ]

    def __str__(self):
        estado = "actual" if self.fecha_fin is None else str(self.fecha_fin)
        return f"{self.placas} — {self.vehiculo.numero_serie} ({estado})"

    @property
    def es_actual(self):
        return self.fecha_fin is None


# ---------------------------------------------------------------------------
# Adquisición / compra
# ---------------------------------------------------------------------------

class Adquisicion(models.Model):
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="adquisiciones",
        verbose_name="vehículo",
    )
    tipo_adquisicion = models.CharField(
        max_length=80,
        verbose_name="tipo de adquisición",
    )
    fecha_adquisicion = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha de adquisición",
    )
    importe_adquisicion = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="importe",
        validators=[MinValueValidator(0)],
    )
    observacion_adquisicion = models.TextField(
        blank=True,
        null=True,
        verbose_name="observación",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "adquisición"
        verbose_name_plural = "adquisiciones"
        ordering = ["-fecha_adquisicion"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(importe_adquisicion__isnull=True)
                    | models.Q(importe_adquisicion__gte=0)
                ),
                name="chk_adquisicion_importe",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_adquisicion_vehiculo"),
            models.Index(fields=["fecha_adquisicion"], name="idx_adquisicion_fecha"),
        ]

    def __str__(self):
        fecha = self.fecha_adquisicion or "sin fecha"
        return f"{self.tipo_adquisicion} — {self.vehiculo.numero_serie} ({fecha})"


# ---------------------------------------------------------------------------
# Póliza de seguro
# ---------------------------------------------------------------------------

class PolizaSeguro(models.Model):
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="polizas",
        verbose_name="vehículo",
    )
    aseguradora = models.ForeignKey(
        "actores.Aseguradora",
        on_delete=models.PROTECT,
        related_name="polizas",
        verbose_name="aseguradora",
    )
    titular_poliza = models.ForeignKey(
        "actores.TitularPoliza",
        on_delete=models.PROTECT,
        related_name="polizas",
        null=True,
        blank=True,
        verbose_name="titular",
    )
    numero_poliza = models.CharField(
        max_length=100,
        verbose_name="número de póliza",
    )
    fecha_vigencia_inicio = models.DateField(
        blank=True,
        null=True,
        verbose_name="inicio de vigencia",
    )
    fecha_vigencia_fin = models.DateField(verbose_name="fin de vigencia")
    importe_prima = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="importe de prima",
        validators=[MinValueValidator(0)],
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "póliza de seguro"
        verbose_name_plural = "pólizas de seguro"
        ordering = ["-fecha_vigencia_fin"]
        constraints = [
            models.UniqueConstraint(
                fields=["aseguradora", "numero_poliza"],
                name="uq_poliza_por_aseguradora",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(fecha_vigencia_inicio__isnull=True)
                    | models.Q(fecha_vigencia_fin__gte=models.F("fecha_vigencia_inicio"))
                ),
                name="chk_poliza_fechas",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(importe_prima__isnull=True)
                    | models.Q(importe_prima__gte=0)
                ),
                name="chk_poliza_importe",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_poliza_vehiculo"),
            models.Index(Upper("numero_poliza"), name="idx_poliza_numero"),
            models.Index(fields=["fecha_vigencia_fin"], name="idx_poliza_vigencia_fin"),
        ]

    def __str__(self):
        return f"{self.numero_poliza} — {self.aseguradora}"

    @property
    def vigente(self):
        return self.fecha_vigencia_fin >= timezone.localdate()


# ---------------------------------------------------------------------------
# Verificación vehicular
# ---------------------------------------------------------------------------

class VerificacionVehicular(models.Model):
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="verificaciones",
        verbose_name="vehículo",
    )
    emplacamiento = models.ForeignKey(
        Emplacamiento,
        on_delete=models.SET_NULL,
        related_name="verificaciones",
        null=True,
        blank=True,
        verbose_name="emplacamiento relacionado",
    )
    semestre = models.CharField(
        max_length=20,
        verbose_name="semestre",
        help_text="Ejemplo: 2024-1, 2024-2",
    )
    fecha_ultima_verificacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha de última verificación",
    )
    fecha_limite_verificacion = models.DateField(
        verbose_name="fecha límite de verificación",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "verificación vehicular"
        verbose_name_plural = "verificaciones vehiculares"
        ordering = ["-fecha_limite_verificacion"]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_verificacion_vehiculo"),
            models.Index(fields=["fecha_limite_verificacion"], name="idx_verificacion_limite"),
            models.Index(fields=["semestre"], name="idx_verificacion_semestre"),
        ]

    def __str__(self):
        return f"Verificación {self.semestre} — {self.vehiculo.numero_serie}"

    @property
    def vencida(self):
        return self.fecha_limite_verificacion < timezone.localdate()


# ---------------------------------------------------------------------------
# Tarjeta de circulación
# ---------------------------------------------------------------------------

class TarjetaCirculacion(models.Model):
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="tarjetas_circulacion",
        verbose_name="vehículo",
    )
    emplacamiento = models.ForeignKey(
        Emplacamiento,
        on_delete=models.SET_NULL,
        related_name="tarjetas_circulacion",
        null=True,
        blank=True,
        verbose_name="emplacamiento relacionado",
    )
    fecha_emision = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha de emisión",
    )
    fecha_vigencia_fin = models.DateField(verbose_name="vigencia hasta")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "tarjeta de circulación"
        verbose_name_plural = "tarjetas de circulación"
        ordering = ["-fecha_vigencia_fin"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(fecha_emision__isnull=True)
                    | models.Q(fecha_vigencia_fin__gte=models.F("fecha_emision"))
                ),
                name="chk_tarjeta_fechas",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_tarjeta_vehiculo"),
            models.Index(fields=["fecha_vigencia_fin"], name="idx_tarjeta_vigencia"),
        ]

    def __str__(self):
        return f"Tarjeta circulación — {self.vehiculo.numero_serie} (vence {self.fecha_vigencia_fin})"

    @property
    def vigente(self):
        return self.fecha_vigencia_fin >= timezone.localdate()


# ---------------------------------------------------------------------------
# Tenencia
# ---------------------------------------------------------------------------

class Tenencia(models.Model):
    class EstatusTenencia(models.TextChoices):
        PAGADA = "PAGADA", "Pagada"
        PENDIENTE = "PENDIENTE", "Pendiente"
        NO_APLICA = "NO_APLICA", "No aplica"
        DESCONOCIDA = "DESCONOCIDA", "Desconocida"

    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="tenencias",
        verbose_name="vehículo",
    )
    anio_fiscal = models.SmallIntegerField(
        verbose_name="año fiscal",
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
    )
    estatus_tenencia = models.CharField(
        max_length=30,
        choices=EstatusTenencia.choices,
        verbose_name="estatus",
    )
    fecha_pago = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha de pago",
    )
    monto_tenencia = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="monto",
        validators=[MinValueValidator(0)],
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "tenencia"
        verbose_name_plural = "tenencias"
        ordering = ["-anio_fiscal"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo", "anio_fiscal"],
                name="uq_tenencia_vehiculo_anio",
            ),
            models.CheckConstraint(
                check=models.Q(estatus_tenencia__in=[
                    "PAGADA", "PENDIENTE", "NO_APLICA", "DESCONOCIDA",
                ]),
                name="chk_tenencia_estatus",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(monto_tenencia__isnull=True)
                    | models.Q(monto_tenencia__gte=0)
                ),
                name="chk_tenencia_monto",
            ),
            models.CheckConstraint(
                check=models.Q(anio_fiscal__gte=1900) & models.Q(anio_fiscal__lte=2100),
                name="chk_tenencia_anio_fiscal",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_tenencia_vehiculo"),
            models.Index(fields=["anio_fiscal"], name="idx_tenencia_anio"),
            models.Index(fields=["estatus_tenencia"], name="idx_tenencia_estatus"),
        ]

    def __str__(self):
        return f"Tenencia {self.anio_fiscal} — {self.vehiculo.numero_serie} ({self.estatus_tenencia})"


# ---------------------------------------------------------------------------
# Adeudo vehicular
# ---------------------------------------------------------------------------

class AdeudoVehicular(models.Model):
    class EstatusAdeudo(models.TextChoices):
        SIN_ADEUDO = "SIN_ADEUDO", "Sin adeudo"
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        CANCELADO = "CANCELADO", "Cancelado"
        DESCONOCIDO = "DESCONOCIDO", "Desconocido"

    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="adeudos",
        verbose_name="vehículo",
    )
    tipo_adeudo = models.CharField(
        max_length=80,
        verbose_name="tipo de adeudo",
    )
    monto_adeudo = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="monto",
        validators=[MinValueValidator(0)],
    )
    estatus_adeudo = models.CharField(
        max_length=30,
        choices=EstatusAdeudo.choices,
        default=EstatusAdeudo.PENDIENTE,
        verbose_name="estatus",
    )
    fecha_consulta = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha de consulta",
    )
    observacion_adeudo = models.TextField(
        blank=True,
        null=True,
        verbose_name="observación",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "adeudo vehicular"
        verbose_name_plural = "adeudos vehiculares"
        ordering = ["-fecha_consulta"]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(monto_adeudo__isnull=True)
                    | models.Q(monto_adeudo__gte=0)
                ),
                name="chk_adeudo_monto",
            ),
            models.CheckConstraint(
                check=models.Q(estatus_adeudo__in=[
                    "SIN_ADEUDO", "PENDIENTE", "PAGADO", "CANCELADO", "DESCONOCIDO",
                ]),
                name="chk_adeudo_estatus",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_adeudo_vehiculo"),
            models.Index(fields=["estatus_adeudo"], name="idx_adeudo_estatus"),
            models.Index(Upper("tipo_adeudo"), name="idx_adeudo_tipo"),
        ]

    def __str__(self):
        return f"{self.tipo_adeudo} — {self.vehiculo.numero_serie} ({self.estatus_adeudo})"


# ---------------------------------------------------------------------------
# Observaciones / bitácora
# ---------------------------------------------------------------------------

class Observacion(models.Model):
    class TipoObservacion(models.TextChoices):
        GENERAL = "GENERAL", "General"
        OPERATIVA = "OPERATIVA", "Operativa"
        MECANICA = "MECANICA", "Mecánica"
        SEGURO = "SEGURO", "Seguro"
        GPS = "GPS", "GPS"
        ADEUDO = "ADEUDO", "Adeudo"
        SINIESTRO = "SINIESTRO", "Siniestro"
        DOCUMENTO = "DOCUMENTO", "Documento"

    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="observaciones",
        verbose_name="vehículo",
    )
    poliza_seguro = models.ForeignKey(
        PolizaSeguro,
        on_delete=models.SET_NULL,
        related_name="observaciones",
        null=True,
        blank=True,
        verbose_name="póliza relacionada",
    )
    instalacion_gps = models.ForeignKey(
        "dispositivos.InstalacionGps",
        on_delete=models.SET_NULL,
        related_name="observaciones",
        null=True,
        blank=True,
        verbose_name="instalación GPS relacionada",
    )
    asignacion_vehiculo = models.ForeignKey(
        "operacion.AsignacionVehiculo",
        on_delete=models.SET_NULL,
        related_name="observaciones",
        null=True,
        blank=True,
        verbose_name="asignación relacionada",
    )
    tipo_observacion = models.CharField(
        max_length=50,
        choices=TipoObservacion.choices,
        verbose_name="tipo",
    )
    texto_observacion = models.TextField(verbose_name="observación")
    fecha_registro = models.DateTimeField(
        default=timezone.now,
        verbose_name="fecha de registro",
    )
    autor_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="observaciones_flotilla",
        null=True,
        blank=True,
        verbose_name="registrado por",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "observación"
        verbose_name_plural = "observaciones"
        ordering = ["-fecha_registro"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(tipo_observacion__in=[
                    "GENERAL", "OPERATIVA", "MECANICA", "SEGURO",
                    "GPS", "ADEUDO", "SINIESTRO", "DOCUMENTO",
                ]),
                name="chk_observacion_tipo",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_observacion_vehiculo"),
            models.Index(fields=["tipo_observacion"], name="idx_observacion_tipo"),
            models.Index(fields=["fecha_registro"], name="idx_observacion_fecha"),
        ]

    def clean(self):
        errores = {}
        if self.tipo_observacion == self.TipoObservacion.GPS and not self.instalacion_gps_id:
            errores["instalacion_gps"] = (
                "Una observación de tipo GPS debe referenciar una instalación GPS."
            )
        if self.tipo_observacion == self.TipoObservacion.SEGURO and not self.poliza_seguro_id:
            errores["poliza_seguro"] = (
                "Una observación de tipo SEGURO debe referenciar una póliza de seguro."
            )
        if self.tipo_observacion == self.TipoObservacion.OPERATIVA and not self.asignacion_vehiculo_id:
            errores["asignacion_vehiculo"] = (
                "Una observación de tipo OPERATIVA debe referenciar una asignación de vehículo."
            )
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f"[{self.tipo_observacion}] {self.vehiculo.numero_serie} — {self.fecha_registro:%Y-%m-%d}"


# ---------------------------------------------------------------------------
# Vista de BD: ficha resumen por vehículo (managed=False → no crea tabla)
# ---------------------------------------------------------------------------

class VwFichaVehiculo(models.Model):
    id_vehiculo = models.BigIntegerField(primary_key=True)
    numero_interno = models.CharField(max_length=50, blank=True, null=True)
    clave_vehiculo = models.TextField(blank=True, null=True)
    nombre_marca = models.CharField(max_length=80)
    nombre_modelo_comercial = models.CharField(max_length=120)
    version = models.CharField(max_length=80, blank=True, null=True)
    anio_modelo = models.SmallIntegerField()
    nombre_color = models.CharField(max_length=50)
    numero_serie = models.CharField(max_length=40)
    placas_actuales = models.CharField(max_length=20, blank=True, null=True)
    entidad_emplacamiento_actual = models.CharField(max_length=80, blank=True, null=True)
    conductor = models.CharField(max_length=255, blank=True, null=True)
    plataforma = models.CharField(max_length=255, blank=True, null=True)
    socio = models.CharField(max_length=255, blank=True, null=True)
    cuenta = models.CharField(max_length=120, blank=True, null=True)
    numero_poliza = models.CharField(max_length=100, blank=True, null=True)
    vigencia_poliza = models.DateField(blank=True, null=True)
    semestre_verificacion = models.CharField(max_length=20, blank=True, null=True)
    fecha_ultima_verificacion = models.DateField(blank=True, null=True)
    fecha_limite_verificacion = models.DateField(blank=True, null=True)
    vigencia_tarjeta_circulacion = models.DateField(blank=True, null=True)
    cantidad_adeudos_pendientes = models.IntegerField(default=0)
    monto_adeudos_pendientes = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    semaforo_documental = models.CharField(max_length=10)
    estatus_unidad = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = "vw_ficha_vehiculo"
        verbose_name = "ficha de vehículo"
        verbose_name_plural = "fichas de vehículos"
        ordering = ["numero_interno", "numero_serie"]

    def __str__(self):
        return self.clave_vehiculo or self.numero_serie
