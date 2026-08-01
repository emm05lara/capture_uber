from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AsignacionTag, DispositivoGps, InstalacionGps, TagTelepeaje

User = get_user_model()


class DispositivoGpsCatalogoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="disp1", password="clave-segura-123")
        self.client.login(username="disp1", password="clave-segura-123")

    def _payload(self, **overrides):
        datos = {
            "imei": "864111111111111",
            "numero_gps": "GPS-T01",
            "estatus_gps": DispositivoGps.Estatus.ACTIVO,
        }
        datos.update(overrides)
        return datos

    def test_crear_gps(self):
        url = reverse("dispositivos:gps_nuevo")
        resp = self.client.post(url, self._payload())
        gps = DispositivoGps.objects.get(imei="864111111111111")
        self.assertRedirects(resp, reverse("dispositivos:gps_detalle", args=[gps.pk]))

    def test_editar_gps(self):
        gps = DispositivoGps.objects.create(imei="864222222222222", estatus_gps=DispositivoGps.Estatus.ACTIVO)
        url = reverse("dispositivos:gps_editar", args=[gps.pk])
        resp = self.client.post(url, self._payload(imei="864222222222222", numero_gps="GPS-EDITADO"))
        self.assertRedirects(resp, reverse("dispositivos:gps_detalle", args=[gps.pk]))
        gps.refresh_from_db()
        self.assertEqual(gps.numero_gps, "GPS-EDITADO")

    def test_rechaza_imei_duplicado(self):
        DispositivoGps.objects.create(imei="864333333333333", estatus_gps=DispositivoGps.Estatus.ACTIVO)
        url = reverse("dispositivos:gps_nuevo")
        resp = self.client.post(url, self._payload(imei="864333333333333"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(DispositivoGps.objects.filter(imei="864333333333333").count(), 1)

    def test_lista_muestra_vehiculo_actual(self):
        from catalogos.models import Color, Marca, ModeloVehiculo
        from vehiculos.models import Vehiculo

        marca = Marca.objects.create(nombre_marca="Marca GPS")
        modelo = ModeloVehiculo.objects.create(marca=marca, nombre_modelo_comercial="Modelo GPS")
        color = Color.objects.create(nombre_color="Color GPS")
        vehiculo = Vehiculo.objects.create(
            numero_serie="VINGPS0000000001", modelo_vehiculo=modelo, color=color, anio_modelo=2023,
        )
        gps = DispositivoGps.objects.create(imei="864444444444444", estatus_gps=DispositivoGps.Estatus.ACTIVO)
        InstalacionGps.objects.create(vehiculo=vehiculo, gps=gps, fecha_retiro=None)

        resp = self.client.get(reverse("dispositivos:gps_lista"))
        self.assertContains(resp, "864444444444444")
        self.assertContains(resp, vehiculo.numero_serie)

    def test_detalle_maneja_gps_sin_historial(self):
        gps = DispositivoGps.objects.create(imei="864555555555555", estatus_gps=DispositivoGps.Estatus.ACTIVO)
        url = reverse("dispositivos:gps_detalle", args=[gps.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_requiere_login(self):
        self.client.logout()
        resp = self.client.get(reverse("dispositivos:gps_lista"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)


class TagTelepeajeCatalogoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="disp2", password="clave-segura-123")
        self.client.login(username="disp2", password="clave-segura-123")

    def _payload(self, **overrides):
        datos = {
            "codigo_tag": "TAG-T00001",
            "codigo_tag_corto": "T001",
            "estatus_tag": TagTelepeaje.Estatus.ACTIVO,
        }
        datos.update(overrides)
        return datos

    def test_crear_tag(self):
        url = reverse("dispositivos:tag_nuevo")
        resp = self.client.post(url, self._payload())
        tag = TagTelepeaje.objects.get(codigo_tag="TAG-T00001")
        self.assertRedirects(resp, reverse("dispositivos:tag_detalle", args=[tag.pk]))

    def test_editar_tag(self):
        tag = TagTelepeaje.objects.create(codigo_tag="TAG-T00002", estatus_tag=TagTelepeaje.Estatus.ACTIVO)
        url = reverse("dispositivos:tag_editar", args=[tag.pk])
        resp = self.client.post(url, self._payload(codigo_tag="TAG-T00002", codigo_tag_corto="EDITADO"))
        self.assertRedirects(resp, reverse("dispositivos:tag_detalle", args=[tag.pk]))
        tag.refresh_from_db()
        self.assertEqual(tag.codigo_tag_corto, "EDITADO")

    def test_rechaza_codigo_duplicado(self):
        TagTelepeaje.objects.create(codigo_tag="TAG-T00003", estatus_tag=TagTelepeaje.Estatus.ACTIVO)
        url = reverse("dispositivos:tag_nuevo")
        resp = self.client.post(url, self._payload(codigo_tag="TAG-T00003"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(TagTelepeaje.objects.filter(codigo_tag="TAG-T00003").count(), 1)

    def test_detalle_maneja_tag_sin_historial(self):
        tag = TagTelepeaje.objects.create(codigo_tag="TAG-T00004", estatus_tag=TagTelepeaje.Estatus.ACTIVO)
        url = reverse("dispositivos:tag_detalle", args=[tag.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_requiere_login(self):
        self.client.logout()
        resp = self.client.get(reverse("dispositivos:tag_lista"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)
