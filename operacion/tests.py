from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate

from actores.models import Conductor, ReferenciaConductor
from catalogos.models import Color, ModeloVehiculo, Marca
from vehiculos.models import Vehiculo

from .models import AsignacionVehiculo

User = get_user_model()


def crear_conductor(nombre, estatus=Conductor.Estatus.ACTIVO, con_referencia=True):
    conductor = Conductor.objects.create(
        nombre_completo=nombre,
        estatus_conductor=estatus,
    )
    if con_referencia:
        ReferenciaConductor.objects.create(
            conductor=conductor,
            nombre=f"Referencia de {nombre}",
            domicilio="Calle Falsa 123",
            telefono_contacto="55 0000 0000",
            parentesco="MADRE",
        )
    return conductor


def crear_vehiculo(numero_serie):
    marca = Marca.objects.create(nombre_marca=f"Marca {numero_serie}")
    modelo = ModeloVehiculo.objects.create(marca=marca, nombre_modelo_comercial="Modelo X")
    color = Color.objects.create(nombre_color=f"Color {numero_serie}")
    return Vehiculo.objects.create(
        numero_serie=numero_serie,
        modelo_vehiculo=modelo,
        color=color,
        anio_modelo=2023,
        estatus_unidad=Vehiculo.EstatusUnidad.ACTIVA,
    )


class AsignacionVehiculoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador", password="clave-segura-123")
        self.client.login(username="operador", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000001")
        self.conductor = crear_conductor("Conductor Disponible")

    def _payload(self, conductor, **overrides):
        datos = {
            "conductor": conductor.pk,
            "fecha_inicio": localdate().isoformat(),
            "plataforma": "",
            "socio": "",
            "cuenta": "",
        }
        datos.update(overrides)
        return datos

    # ── Alta de asignación ──────────────────────────────────────────────

    def test_asignar_conductor_disponible_a_vehiculo_libre(self):
        url = reverse("vehiculos:asignar_conductor", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(self.conductor))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(
            AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo, fecha_fin__isnull=True).count(),
            1,
        )

    def test_impide_asignar_conductor_ya_ocupado(self):
        otro_vehiculo = crear_vehiculo("VIN0000000000002")
        AsignacionVehiculo.objects.create(
            vehiculo=otro_vehiculo, conductor=self.conductor, fecha_inicio=localdate(),
        )
        # El formulario no debe ofrecer al conductor ya ocupado como opción.
        url = reverse("vehiculos:asignar_conductor", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(self.conductor))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo, fecha_fin__isnull=True).exists()
        )

    def test_impide_asignar_a_vehiculo_ya_ocupado(self):
        AsignacionVehiculo.objects.create(
            vehiculo=self.vehiculo, conductor=self.conductor, fecha_inicio=localdate(),
        )
        otro_conductor = crear_conductor("Otro Disponible")
        url = reverse("vehiculos:asignar_conductor", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(otro_conductor))
        # La vista redirige de inmediato sin mostrar el formulario porque ya hay asignación activa.
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(
            AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo, fecha_fin__isnull=True).count(),
            1,
        )
        activa = AsignacionVehiculo.objects.get(vehiculo=self.vehiculo, fecha_fin__isnull=True)
        self.assertEqual(activa.conductor_id, self.conductor.pk)

    def test_impide_asignar_conductor_inactivo(self):
        inactivo = crear_conductor("Conductor Inactivo", estatus=Conductor.Estatus.INACTIVO)
        url = reverse("vehiculos:asignar_conductor", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(inactivo))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo).exists()
        )

    def test_impide_asignar_conductor_sin_referencias(self):
        sin_ref = crear_conductor("Sin Referencias", con_referencia=False)
        url = reverse("vehiculos:asignar_conductor", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(sin_ref))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo).exists()
        )

    # ── Finalizar asignación ────────────────────────────────────────────

    def test_finalizar_asignacion(self):
        asignacion = AsignacionVehiculo.objects.create(
            vehiculo=self.vehiculo, conductor=self.conductor, fecha_inicio=localdate(),
        )
        url = reverse("vehiculos:finalizar_asignacion", args=[self.vehiculo.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        asignacion.refresh_from_db()
        self.assertIsNotNone(asignacion.fecha_fin)
        self.assertTrue(AsignacionVehiculo.objects.filter(pk=asignacion.pk).exists())

    def test_finalizar_asignacion_inexistente_no_falla(self):
        url = reverse("vehiculos:finalizar_asignacion", args=[self.vehiculo.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))

    def test_finalizar_asignacion_rechaza_get(self):
        AsignacionVehiculo.objects.create(
            vehiculo=self.vehiculo, conductor=self.conductor, fecha_inicio=localdate(),
        )
        url = reverse("vehiculos:finalizar_asignacion", args=[self.vehiculo.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

    def test_conserva_historial_al_finalizar(self):
        asignacion = AsignacionVehiculo.objects.create(
            vehiculo=self.vehiculo, conductor=self.conductor, fecha_inicio=localdate(),
        )
        url = reverse("vehiculos:finalizar_asignacion", args=[self.vehiculo.pk])
        self.client.post(url)
        self.assertEqual(AsignacionVehiculo.objects.filter(pk=asignacion.pk).count(), 1)
        self.assertEqual(AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo).count(), 1)

    # ── Cambiar conductor ────────────────────────────────────────────────

    def test_cambiar_conductor_de_forma_atomica(self):
        actual = AsignacionVehiculo.objects.create(
            vehiculo=self.vehiculo, conductor=self.conductor, fecha_inicio=localdate(),
        )
        nuevo_conductor = crear_conductor("Nuevo Conductor")
        url = reverse("vehiculos:cambiar_conductor", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(nuevo_conductor))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))

        actual.refresh_from_db()
        self.assertIsNotNone(actual.fecha_fin)

        nueva_activa = AsignacionVehiculo.objects.get(vehiculo=self.vehiculo, fecha_fin__isnull=True)
        self.assertEqual(nueva_activa.conductor_id, nuevo_conductor.pk)
        self.assertEqual(AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo).count(), 2)

    def test_no_cierra_asignacion_actual_si_falla_la_nueva(self):
        actual = AsignacionVehiculo.objects.create(
            vehiculo=self.vehiculo, conductor=self.conductor, fecha_inicio=localdate(),
        )
        ocupado_en_otro_vehiculo = crear_conductor("Ocupado En Otro")
        otro_vehiculo = crear_vehiculo("VIN0000000000003")
        AsignacionVehiculo.objects.create(
            vehiculo=otro_vehiculo, conductor=ocupado_en_otro_vehiculo, fecha_inicio=localdate(),
        )

        # Se fuerza el intento de asignar un conductor que ya tiene otra
        # asignación activa directamente contra el modelo (simulando una
        # condición de carrera que el formulario normalmente evita), para
        # comprobar que si la nueva asignación falla, la anterior sigue activa.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AsignacionVehiculo.objects.create(
                    vehiculo=self.vehiculo, conductor=ocupado_en_otro_vehiculo, fecha_inicio=localdate(),
                )
                actual.fecha_fin = localdate()
                actual.save(update_fields=["fecha_fin"])

        actual.refresh_from_db()
        self.assertIsNone(actual.fecha_fin)

    def test_get_a_cambiar_conductor_no_modifica_nada(self):
        AsignacionVehiculo.objects.create(
            vehiculo=self.vehiculo, conductor=self.conductor, fecha_inicio=localdate(),
        )
        url = reverse("vehiculos:cambiar_conductor", args=[self.vehiculo.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo).count(), 1)

    # ── Seguridad ────────────────────────────────────────────────────────

    def test_vistas_protegidas_requieren_login(self):
        self.client.logout()
        urls = [
            reverse("vehiculos:asignar_conductor", args=[self.vehiculo.pk]),
            reverse("vehiculos:cambiar_conductor", args=[self.vehiculo.pk]),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/login", resp.url)

        resp = self.client.post(reverse("vehiculos:finalizar_asignacion", args=[self.vehiculo.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)
