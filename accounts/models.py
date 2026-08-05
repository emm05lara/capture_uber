from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Rol(models.TextChoices):
        # Los tres valores existían desde la primera migración. Se conservan
        # tal cual en la base de datos; solo se ajustaron las etiquetas para
        # que coincidan con el vocabulario operativo del sistema:
        #   ADMINISTRADOR -> rol ADMIN     (acceso completo)
        #   OPERADOR      -> rol OPERADOR  (captura y acciones operativas)
        #   AUDITOR       -> rol CONSULTA  (solo lectura)
        # La matriz de permisos vive en `accounts.permissions`.
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        OPERADOR = "OPERADOR", "Operador"
        AUDITOR = "AUDITOR", "Consulta (solo lectura)"

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.ADMINISTRADOR,
        verbose_name="rol",
    )

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.CheckConstraint(
                check=models.Q(rol__in=["ADMINISTRADOR", "OPERADOR", "AUDITOR"]),
                name="chk_customuser_rol",
            ),
        ]

    def __str__(self):
        return self.get_full_name() or self.username
