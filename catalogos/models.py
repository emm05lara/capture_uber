from django.db import models


class Marca(models.Model):
    nombre_marca = models.CharField(
        max_length=80,
        unique=True,
        verbose_name="nombre de marca",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "marca"
        verbose_name_plural = "marcas"
        ordering = ["nombre_marca"]

    def __str__(self):
        return self.nombre_marca


class ModeloVehiculo(models.Model):
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        related_name="modelos",
        verbose_name="marca",
    )
    nombre_modelo_comercial = models.CharField(
        max_length=100,
        verbose_name="modelo comercial",
    )
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="versión",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "modelo de vehículo"
        verbose_name_plural = "modelos de vehículo"
        ordering = ["marca__nombre_marca", "nombre_modelo_comercial", "version"]
        constraints = [
            # nulls_distinct=False: dos filas (misma_marca, mismo_modelo, NULL) se consideran
            # duplicadas. Evita registrar "BMW X7 sin versión" dos veces.
            models.UniqueConstraint(
                fields=["marca", "nombre_modelo_comercial", "version"],
                name="uq_modelo_vehiculo",
                nulls_distinct=False,
            ),
        ]

    def __str__(self):
        if self.version:
            return f"{self.marca} {self.nombre_modelo_comercial} {self.version}"
        return f"{self.marca} {self.nombre_modelo_comercial}"


class Color(models.Model):
    nombre_color = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="color",
    )
    abreviatura_color = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="abreviatura",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "color"
        verbose_name_plural = "colores"
        ordering = ["nombre_color"]

    def __str__(self):
        return self.nombre_color


class EntidadFederativa(models.Model):
    nombre_entidad = models.CharField(
        max_length=80,
        unique=True,
        verbose_name="nombre de entidad",
    )
    abreviatura_entidad = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="abreviatura",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "entidad federativa"
        verbose_name_plural = "entidades federativas"
        ordering = ["nombre_entidad"]

    def __str__(self):
        if self.abreviatura_entidad:
            return f"{self.nombre_entidad} ({self.abreviatura_entidad})"
        return self.nombre_entidad


class AppTransporte(models.Model):
    class Estatus(models.TextChoices):
        ACTIVA = "ACTIVA", "Activa"
        INACTIVA = "INACTIVA", "Inactiva"

    nombre_app = models.CharField(
        max_length=80,
        unique=True,
        verbose_name="nombre de la app",
    )
    estatus_app = models.CharField(
        max_length=30,
        choices=Estatus.choices,
        default=Estatus.ACTIVA,
        verbose_name="estatus",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "aplicación de transporte"
        verbose_name_plural = "aplicaciones de transporte"
        ordering = ["nombre_app"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(estatus_app__in=["ACTIVA", "INACTIVA"]),
                name="chk_app_transporte_estatus",
            ),
        ]

    def __str__(self):
        return self.nombre_app
