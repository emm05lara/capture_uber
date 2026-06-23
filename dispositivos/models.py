from django.db import models
from django.db.models.functions import Upper


# ---------------------------------------------------------------------------
# GPS
# ---------------------------------------------------------------------------

class DispositivoGps(models.Model):
    class Estatus(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"
        EXTRAVIADO = "EXTRAVIADO", "Extraviado"
        DANADO = "DANADO", "Dañado"
        BAJA = "BAJA", "Baja"

    imei = models.CharField(
        max_length=80,
        unique=True,
        verbose_name="IMEI",
    )
    numero_gps = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        verbose_name="número GPS",
    )
    estatus_gps = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVO,
        verbose_name="estatus",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "dispositivo GPS"
        verbose_name_plural = "dispositivos GPS"
        ordering = ["imei"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_gps__in=["ACTIVO", "INACTIVO", "EXTRAVIADO", "DANADO", "BAJA"]),
                name="chk_gps_estatus",
            ),
        ]
        indexes = [
            models.Index(Upper("imei"), name="idx_gps_imei"),
        ]

    def __str__(self):
        if self.numero_gps:
            return f"{self.imei} ({self.numero_gps})"
        return self.imei


class InstalacionGps(models.Model):
    vehiculo = models.ForeignKey(
        "vehiculos.Vehiculo",
        on_delete=models.CASCADE,
        related_name="instalaciones_gps",
        verbose_name="vehículo",
    )
    gps = models.ForeignKey(
        DispositivoGps,
        on_delete=models.PROTECT,
        related_name="instalaciones",
        verbose_name="dispositivo GPS",
    )
    fecha_instalacion = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha de instalación",
    )
    fecha_retiro = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha de retiro",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "instalación GPS"
        verbose_name_plural = "instalaciones GPS"
        ordering = ["-fecha_instalacion"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo"],
                condition=models.Q(fecha_retiro__isnull=True),
                name="uq_gps_actual_por_vehiculo",
            ),
            models.UniqueConstraint(
                fields=["gps"],
                condition=models.Q(fecha_retiro__isnull=True),
                name="uq_gps_actual_por_dispositivo",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(fecha_retiro__isnull=True)
                    | models.Q(fecha_instalacion__isnull=True)
                    | models.Q(fecha_retiro__gte=models.F("fecha_instalacion"))
                ),
                name="chk_instalacion_gps_fechas",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_instalacion_gps_vehiculo"),
            models.Index(fields=["gps"], name="idx_instalacion_gps_disp"),
        ]

    def __str__(self):
        estado = "instalado" if self.fecha_retiro is None else f"retirado {self.fecha_retiro}"
        return f"{self.gps.imei} → {self.vehiculo.numero_serie} ({estado})"

    @property
    def es_actual(self):
        return self.fecha_retiro is None


# ---------------------------------------------------------------------------
# TAG de telepeaje
# ---------------------------------------------------------------------------

class TagTelepeaje(models.Model):
    class Estatus(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        INACTIVO = "INACTIVO", "Inactivo"
        EXTRAVIADO = "EXTRAVIADO", "Extraviado"
        DANADO = "DANADO", "Dañado"
        BAJA = "BAJA", "Baja"

    codigo_tag = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="código TAG",
    )
    codigo_tag_corto = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="código corto",
    )
    estatus_tag = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVO,
        verbose_name="estatus",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "TAG de telepeaje"
        verbose_name_plural = "TAGs de telepeaje"
        ordering = ["codigo_tag"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_tag__in=["ACTIVO", "INACTIVO", "EXTRAVIADO", "DANADO", "BAJA"]),
                name="chk_tag_estatus",
            ),
        ]
        indexes = [
            models.Index(Upper("codigo_tag"), name="idx_tag_codigo"),
            models.Index(Upper("codigo_tag_corto"), name="idx_tag_codigo_corto"),
        ]

    def __str__(self):
        if self.codigo_tag_corto:
            return f"{self.codigo_tag} / {self.codigo_tag_corto}"
        return self.codigo_tag


class AsignacionTag(models.Model):
    vehiculo = models.ForeignKey(
        "vehiculos.Vehiculo",
        on_delete=models.CASCADE,
        related_name="asignaciones_tag",
        verbose_name="vehículo",
    )
    tag = models.ForeignKey(
        TagTelepeaje,
        on_delete=models.PROTECT,
        related_name="asignaciones",
        verbose_name="TAG",
    )
    fecha_inicio = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha inicio",
    )
    fecha_fin = models.DateField(
        blank=True,
        null=True,
        verbose_name="fecha fin",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "asignación TAG"
        verbose_name_plural = "asignaciones TAG"
        ordering = ["-fecha_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo"],
                condition=models.Q(fecha_fin__isnull=True),
                name="uq_tag_actual_por_vehiculo",
            ),
            models.UniqueConstraint(
                fields=["tag"],
                condition=models.Q(fecha_fin__isnull=True),
                name="uq_tag_actual_por_codigo",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(fecha_fin__isnull=True)
                    | models.Q(fecha_inicio__isnull=True)
                    | models.Q(fecha_fin__gte=models.F("fecha_inicio"))
                ),
                name="chk_asignacion_tag_fechas",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_asignacion_tag_vehiculo"),
            models.Index(fields=["tag"], name="idx_asignacion_tag_tag"),
        ]

    def __str__(self):
        estado = "activo" if self.fecha_fin is None else f"hasta {self.fecha_fin}"
        return f"{self.tag.codigo_tag} → {self.vehiculo.numero_serie} ({estado})"

    @property
    def es_actual(self):
        return self.fecha_fin is None
