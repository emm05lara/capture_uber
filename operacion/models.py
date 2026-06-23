from django.db import models
from django.db.models.functions import Upper


class AsignacionVehiculo(models.Model):
    vehiculo = models.ForeignKey(
        "vehiculos.Vehiculo",
        on_delete=models.CASCADE,
        related_name="asignaciones_vehiculo",
        verbose_name="vehículo",
    )
    conductor = models.ForeignKey(
        "actores.Conductor",
        on_delete=models.PROTECT,
        related_name="asignaciones_vehiculo",
        verbose_name="conductor",
    )
    plataforma = models.ForeignKey(
        "actores.PlataformaOperativa",
        on_delete=models.PROTECT,
        related_name="asignaciones_vehiculo",
        null=True,
        blank=True,
        verbose_name="plataforma operativa",
    )
    socio = models.ForeignKey(
        "actores.Socio",
        on_delete=models.PROTECT,
        related_name="asignaciones_vehiculo",
        null=True,
        blank=True,
        verbose_name="socio",
    )
    cuenta = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="cuenta operativa",
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
        verbose_name = "asignación de vehículo"
        verbose_name_plural = "asignaciones de vehículo"
        ordering = ["-fecha_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo"],
                condition=models.Q(fecha_fin__isnull=True),
                name="uq_asignacion_actual_por_vehiculo",
            ),
            models.UniqueConstraint(
                fields=["conductor"],
                condition=models.Q(fecha_fin__isnull=True),
                name="uq_asignacion_actual_por_conductor",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(fecha_fin__isnull=True)
                    | models.Q(fecha_inicio__isnull=True)
                    | models.Q(fecha_fin__gte=models.F("fecha_inicio"))
                ),
                name="chk_asignacion_vehiculo_fechas",
            ),
        ]
        indexes = [
            models.Index(fields=["vehiculo"], name="idx_asignacion_vehiculo"),
            models.Index(fields=["conductor"], name="idx_asignacion_conductor"),
            models.Index(fields=["plataforma"], name="idx_asignacion_plataforma"),
            models.Index(fields=["socio"], name="idx_asignacion_socio"),
            models.Index(Upper("cuenta"), name="idx_asignacion_cuenta"),
        ]

    def __str__(self):
        estado = "activa" if self.es_actual else f"hasta {self.fecha_fin}"
        return f"{self.vehiculo.numero_serie} → {self.conductor} ({estado})"

    @property
    def es_actual(self):
        return self.fecha_fin is None

    @property
    def estatus_asignacion(self):
        return "ACTIVA" if self.fecha_fin is None else "FINALIZADA"


class AsignacionApp(models.Model):
    class Estatus(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        INACTIVA = "INACTIVA", "Inactiva"
        SUSPENDIDA = "SUSPENDIDA", "Suspendida"

    asignacion_vehiculo = models.ForeignKey(
        AsignacionVehiculo,
        on_delete=models.CASCADE,
        related_name="apps_asignadas",
        verbose_name="asignación de vehículo",
    )
    app_transporte = models.ForeignKey(
        "catalogos.AppTransporte",
        on_delete=models.PROTECT,
        related_name="asignaciones_app",
        verbose_name="app de transporte",
    )
    estatus_app_asignada = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVA,
        verbose_name="estatus",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "app asignada"
        verbose_name_plural = "apps asignadas"
        ordering = ["app_transporte__nombre_app"]
        constraints = [
            models.UniqueConstraint(
                fields=["asignacion_vehiculo", "app_transporte"],
                name="uq_asignacion_app",
            ),
            models.CheckConstraint(
                check=models.Q(estatus_app_asignada__in=["ACTIVA", "INACTIVA", "SUSPENDIDA"]),
                name="chk_asignacion_app_estatus",
            ),
        ]

    def __str__(self):
        return f"{self.app_transporte} — {self.asignacion_vehiculo}"
