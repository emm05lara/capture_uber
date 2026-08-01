from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localdate, timedelta

from actores.models import Aseguradora, TitularPoliza
from catalogos.models import Color, Marca, ModeloVehiculo
from dispositivos.models import AsignacionTag, DispositivoGps, InstalacionGps, TagTelepeaje
from .models import (
    AdeudoVehicular,
    Observacion,
    PolizaSeguro,
    TarjetaCirculacion,
    Tenencia,
    Vehiculo,
    VerificacionVehicular,
)

User = get_user_model()


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


def crear_aseguradora(nombre="Aseguradora Demo"):
    return Aseguradora.objects.create(nombre_organizacion=nombre)


class PolizaSeguroTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador", password="clave-segura-123")
        self.client.login(username="operador", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000010")
        self.otro_vehiculo = crear_vehiculo("VIN0000000000011")
        self.aseguradora = crear_aseguradora()

    def _payload(self, **overrides):
        datos = {
            "aseguradora": self.aseguradora.pk,
            "titular_poliza": "",
            "numero_poliza": "POL-001",
            "fecha_vigencia_inicio": "",
            "fecha_vigencia_fin": (localdate() + timedelta(days=180)).isoformat(),
            "importe_prima": "",
        }
        datos.update(overrides)
        return datos

    def test_crear_poliza_para_un_vehiculo(self):
        url = reverse("vehiculos:poliza_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload())
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(PolizaSeguro.objects.filter(vehiculo=self.vehiculo).count(), 1)

    def test_editar_poliza(self):
        poliza = PolizaSeguro.objects.create(
            vehiculo=self.vehiculo,
            aseguradora=self.aseguradora,
            numero_poliza="POL-001",
            fecha_vigencia_fin=localdate() + timedelta(days=30),
        )
        url = reverse("vehiculos:poliza_editar", args=[self.vehiculo.pk, poliza.pk])
        nueva_fecha = (localdate() + timedelta(days=365)).isoformat()
        resp = self.client.post(url, self._payload(fecha_vigencia_fin=nueva_fecha))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        poliza.refresh_from_db()
        self.assertEqual(poliza.fecha_vigencia_fin.isoformat(), nueva_fecha)

    def test_impide_editar_poliza_de_otro_vehiculo(self):
        poliza_ajena = PolizaSeguro.objects.create(
            vehiculo=self.otro_vehiculo,
            aseguradora=self.aseguradora,
            numero_poliza="POL-AJENA",
            fecha_vigencia_fin=localdate() + timedelta(days=30),
        )
        url = reverse("vehiculos:poliza_editar", args=[self.vehiculo.pk, poliza_ajena.pk])
        resp = self.client.post(url, self._payload(numero_poliza="POL-AJENA"))
        self.assertEqual(resp.status_code, 404)

    def test_impide_numero_poliza_duplicado_en_misma_aseguradora(self):
        PolizaSeguro.objects.create(
            vehiculo=self.otro_vehiculo,
            aseguradora=self.aseguradora,
            numero_poliza="POL-DUP",
            fecha_vigencia_fin=localdate() + timedelta(days=30),
        )
        url = reverse("vehiculos:poliza_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(numero_poliza="POL-DUP"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(
            PolizaSeguro.objects.filter(vehiculo=self.vehiculo, numero_poliza="POL-DUP").exists()
        )

    def test_conserva_polizas_anteriores_al_registrar_una_nueva(self):
        PolizaSeguro.objects.create(
            vehiculo=self.vehiculo,
            aseguradora=self.aseguradora,
            numero_poliza="POL-ANTERIOR",
            fecha_vigencia_fin=localdate() - timedelta(days=10),
        )
        url = reverse("vehiculos:poliza_nueva", args=[self.vehiculo.pk])
        self.client.post(url, self._payload(numero_poliza="POL-NUEVA"))
        self.assertEqual(PolizaSeguro.objects.filter(vehiculo=self.vehiculo).count(), 2)
        self.assertTrue(
            PolizaSeguro.objects.filter(vehiculo=self.vehiculo, numero_poliza="POL-ANTERIOR").exists()
        )


class VerificacionVehicularTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador2", password="clave-segura-123")
        self.client.login(username="operador2", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000020")
        self.otro_vehiculo = crear_vehiculo("VIN0000000000021")

    def _payload(self, **overrides):
        datos = {
            "semestre": "2026-1",
            "fecha_ultima_verificacion": "",
            "fecha_limite_verificacion": (localdate() + timedelta(days=90)).isoformat(),
        }
        datos.update(overrides)
        return datos

    def test_crear_verificacion(self):
        url = reverse("vehiculos:verificacion_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload())
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(VerificacionVehicular.objects.filter(vehiculo=self.vehiculo).count(), 1)

    def test_editar_verificacion(self):
        verificacion = VerificacionVehicular.objects.create(
            vehiculo=self.vehiculo,
            semestre="2026-1",
            fecha_limite_verificacion=localdate() + timedelta(days=90),
        )
        url = reverse("vehiculos:verificacion_editar", args=[self.vehiculo.pk, verificacion.pk])
        resp = self.client.post(url, self._payload(semestre="2026-2"))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        verificacion.refresh_from_db()
        self.assertEqual(verificacion.semestre, "2026-2")

    def test_fecha_verificacion_incoherente_no_guarda(self):
        url = reverse("vehiculos:verificacion_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(
            fecha_ultima_verificacion=(localdate() + timedelta(days=200)).isoformat(),
            fecha_limite_verificacion=(localdate() + timedelta(days=90)).isoformat(),
        ))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(VerificacionVehicular.objects.filter(vehiculo=self.vehiculo).exists())

    def test_estatus_derivado_vencida(self):
        verificacion = VerificacionVehicular.objects.create(
            vehiculo=self.vehiculo,
            semestre="2025-2",
            fecha_limite_verificacion=localdate() - timedelta(days=5),
        )
        self.assertTrue(verificacion.vencida)

    def test_estatus_derivado_a_tiempo(self):
        verificacion = VerificacionVehicular.objects.create(
            vehiculo=self.vehiculo,
            semestre="2026-1",
            fecha_limite_verificacion=localdate() + timedelta(days=90),
        )
        self.assertFalse(verificacion.vencida)

    def test_impide_acceso_cruzado(self):
        verificacion_ajena = VerificacionVehicular.objects.create(
            vehiculo=self.otro_vehiculo,
            semestre="2026-1",
            fecha_limite_verificacion=localdate() + timedelta(days=90),
        )
        url = reverse("vehiculos:verificacion_editar", args=[self.vehiculo.pk, verificacion_ajena.pk])
        resp = self.client.post(url, self._payload())
        self.assertEqual(resp.status_code, 404)


class TarjetaCirculacionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador3", password="clave-segura-123")
        self.client.login(username="operador3", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000030")
        self.otro_vehiculo = crear_vehiculo("VIN0000000000031")

    def _payload(self, **overrides):
        datos = {
            "fecha_emision": "",
            "fecha_vigencia_fin": (localdate() + timedelta(days=365)).isoformat(),
        }
        datos.update(overrides)
        return datos

    def test_crear_tarjeta(self):
        url = reverse("vehiculos:tarjeta_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload())
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(TarjetaCirculacion.objects.filter(vehiculo=self.vehiculo).count(), 1)

    def test_editar_tarjeta(self):
        tarjeta = TarjetaCirculacion.objects.create(
            vehiculo=self.vehiculo,
            fecha_vigencia_fin=localdate() + timedelta(days=30),
        )
        url = reverse("vehiculos:tarjeta_editar", args=[self.vehiculo.pk, tarjeta.pk])
        nueva_fecha = (localdate() + timedelta(days=400)).isoformat()
        resp = self.client.post(url, self._payload(fecha_vigencia_fin=nueva_fecha))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        tarjeta.refresh_from_db()
        self.assertEqual(tarjeta.fecha_vigencia_fin.isoformat(), nueva_fecha)

    def test_identifica_la_vigente(self):
        vigente = TarjetaCirculacion.objects.create(
            vehiculo=self.vehiculo,
            fecha_vigencia_fin=localdate() + timedelta(days=30),
        )
        vencida = TarjetaCirculacion.objects.create(
            vehiculo=self.vehiculo,
            fecha_vigencia_fin=localdate() - timedelta(days=30),
        )
        self.assertTrue(vigente.vigente)
        self.assertFalse(vencida.vigente)

    def test_conserva_historial(self):
        TarjetaCirculacion.objects.create(
            vehiculo=self.vehiculo,
            fecha_vigencia_fin=localdate() - timedelta(days=100),
        )
        url = reverse("vehiculos:tarjeta_nueva", args=[self.vehiculo.pk])
        self.client.post(url, self._payload())
        self.assertEqual(TarjetaCirculacion.objects.filter(vehiculo=self.vehiculo).count(), 2)

    def test_impide_acceso_cruzado(self):
        tarjeta_ajena = TarjetaCirculacion.objects.create(
            vehiculo=self.otro_vehiculo,
            fecha_vigencia_fin=localdate() + timedelta(days=30),
        )
        url = reverse("vehiculos:tarjeta_editar", args=[self.vehiculo.pk, tarjeta_ajena.pk])
        resp = self.client.post(url, self._payload())
        self.assertEqual(resp.status_code, 404)


class DocumentacionSeguridadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador4", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000040")

    def test_requiere_login(self):
        urls = [
            reverse("vehiculos:poliza_nueva", args=[self.vehiculo.pk]),
            reverse("vehiculos:verificacion_nueva", args=[self.vehiculo.pk]),
            reverse("vehiculos:tarjeta_nueva", args=[self.vehiculo.pk]),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/login", resp.url)

    def test_incluye_csrf_token_en_formularios(self):
        self.client.login(username="operador4", password="clave-segura-123")
        url = reverse("vehiculos:poliza_nueva", args=[self.vehiculo.pk])
        resp = self.client.get(url)
        self.assertContains(resp, "csrfmiddlewaretoken")

    def test_rechaza_metodo_no_permitido_en_cambiar_estatus(self):
        self.client.login(username="operador4", password="clave-segura-123")
        url = reverse("vehiculos:cambiar_estatus", args=[self.vehiculo.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)


class TenenciaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador5", password="clave-segura-123")
        self.client.login(username="operador5", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000050")
        self.otro_vehiculo = crear_vehiculo("VIN0000000000051")

    def _payload(self, **overrides):
        datos = {
            "anio_fiscal": 2026,
            "estatus_tenencia": Tenencia.EstatusTenencia.PENDIENTE,
            "monto_tenencia": "2500.00",
            "fecha_pago": "",
        }
        datos.update(overrides)
        return datos

    def test_crear_tenencia(self):
        url = reverse("vehiculos:tenencia_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload())
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(Tenencia.objects.filter(vehiculo=self.vehiculo).count(), 1)

    def test_editar_tenencia(self):
        tenencia = Tenencia.objects.create(
            vehiculo=self.vehiculo,
            anio_fiscal=2026,
            estatus_tenencia=Tenencia.EstatusTenencia.PENDIENTE,
        )
        url = reverse("vehiculos:tenencia_editar", args=[self.vehiculo.pk, tenencia.pk])
        resp = self.client.post(url, self._payload(
            estatus_tenencia=Tenencia.EstatusTenencia.PAGADA,
            fecha_pago="2026-01-15",
        ))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        tenencia.refresh_from_db()
        self.assertEqual(tenencia.estatus_tenencia, Tenencia.EstatusTenencia.PAGADA)

    def test_rechaza_duplicado_por_vehiculo_y_anio(self):
        Tenencia.objects.create(
            vehiculo=self.vehiculo,
            anio_fiscal=2026,
            estatus_tenencia=Tenencia.EstatusTenencia.PAGADA,
        )
        url = reverse("vehiculos:tenencia_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Tenencia.objects.filter(vehiculo=self.vehiculo, anio_fiscal=2026).count(), 1)

    def test_pagada_requiere_fecha_de_pago(self):
        url = reverse("vehiculos:tenencia_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(estatus_tenencia=Tenencia.EstatusTenencia.PAGADA))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Tenencia.objects.filter(vehiculo=self.vehiculo).exists())

    def test_impide_acceso_cruzado(self):
        tenencia_ajena = Tenencia.objects.create(
            vehiculo=self.otro_vehiculo,
            anio_fiscal=2026,
            estatus_tenencia=Tenencia.EstatusTenencia.PENDIENTE,
        )
        url = reverse("vehiculos:tenencia_editar", args=[self.vehiculo.pk, tenencia_ajena.pk])
        resp = self.client.post(url, self._payload())
        self.assertEqual(resp.status_code, 404)

    def test_conserva_historial_al_registrar_otro_anio(self):
        Tenencia.objects.create(
            vehiculo=self.vehiculo,
            anio_fiscal=2025,
            estatus_tenencia=Tenencia.EstatusTenencia.PAGADA,
        )
        url = reverse("vehiculos:tenencia_nueva", args=[self.vehiculo.pk])
        self.client.post(url, self._payload(anio_fiscal=2026))
        self.assertEqual(Tenencia.objects.filter(vehiculo=self.vehiculo).count(), 2)


class AdeudoVehicularTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador6", password="clave-segura-123")
        self.client.login(username="operador6", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000060")
        self.otro_vehiculo = crear_vehiculo("VIN0000000000061")

    def _payload(self, **overrides):
        datos = {
            "tipo_adeudo": "Multa de tránsito",
            "monto_adeudo": "1200.00",
            "estatus_adeudo": AdeudoVehicular.EstatusAdeudo.PENDIENTE,
            "fecha_consulta": "",
            "observacion_adeudo": "",
        }
        datos.update(overrides)
        return datos

    def test_crear_adeudo(self):
        url = reverse("vehiculos:adeudo_nuevo", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload())
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(AdeudoVehicular.objects.filter(vehiculo=self.vehiculo).count(), 1)

    def test_editar_adeudo(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )
        url = reverse("vehiculos:adeudo_editar", args=[self.vehiculo.pk, adeudo.pk])
        resp = self.client.post(url, self._payload(tipo_adeudo="Multa actualizada"))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        adeudo.refresh_from_db()
        self.assertEqual(adeudo.tipo_adeudo, "Multa actualizada")

    def test_marcar_como_pagado(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )
        url = reverse("vehiculos:adeudo_pagar", args=[self.vehiculo.pk, adeudo.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        adeudo.refresh_from_db()
        self.assertEqual(adeudo.estatus_adeudo, AdeudoVehicular.EstatusAdeudo.PAGADO)
        self.assertEqual(AdeudoVehicular.objects.filter(vehiculo=self.vehiculo).count(), 1)

    def test_cancelar_adeudo(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )
        url = reverse("vehiculos:adeudo_cancelar", args=[self.vehiculo.pk, adeudo.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        adeudo.refresh_from_db()
        self.assertEqual(adeudo.estatus_adeudo, AdeudoVehicular.EstatusAdeudo.CANCELADO)

    def test_impide_pagar_adeudo_ya_pagado(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PAGADO,
        )
        url = reverse("vehiculos:adeudo_pagar", args=[self.vehiculo.pk, adeudo.pk])
        self.client.post(url)
        adeudo.refresh_from_db()
        self.assertEqual(adeudo.estatus_adeudo, AdeudoVehicular.EstatusAdeudo.PAGADO)

    def test_impide_cancelar_adeudo_ya_cancelado(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.CANCELADO,
        )
        url = reverse("vehiculos:adeudo_cancelar", args=[self.vehiculo.pk, adeudo.pk])
        self.client.post(url)
        adeudo.refresh_from_db()
        self.assertEqual(adeudo.estatus_adeudo, AdeudoVehicular.EstatusAdeudo.CANCELADO)

    def test_impide_editar_adeudo_pagado(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PAGADO,
        )
        url = reverse("vehiculos:adeudo_editar", args=[self.vehiculo.pk, adeudo.pk])
        resp = self.client.post(url, self._payload(tipo_adeudo="Intento de edición"))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        adeudo.refresh_from_db()
        self.assertEqual(adeudo.tipo_adeudo, "Multa de tránsito")

    def test_rechaza_monto_negativo(self):
        url = reverse("vehiculos:adeudo_nuevo", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(monto_adeudo="-100"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AdeudoVehicular.objects.filter(vehiculo=self.vehiculo).exists())

    def test_conserva_historial_al_pagar(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )
        url = reverse("vehiculos:adeudo_pagar", args=[self.vehiculo.pk, adeudo.pk])
        self.client.post(url)
        self.assertTrue(AdeudoVehicular.objects.filter(pk=adeudo.pk).exists())

    def test_total_pendiente_suma_montos(self):
        AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa 1",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
            monto_adeudo=1200,
        )
        AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa 2",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
            monto_adeudo=300,
        )
        url = reverse("vehiculos:detalle", args=[self.vehiculo.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.context["adeudos_pendientes_monto"], 1500)
        self.assertEqual(resp.context["adeudos_pendientes_count"], 2)

    def test_impide_acceso_cruzado(self):
        adeudo_ajeno = AdeudoVehicular.objects.create(
            vehiculo=self.otro_vehiculo,
            tipo_adeudo="Multa ajena",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )
        url = reverse("vehiculos:adeudo_editar", args=[self.vehiculo.pk, adeudo_ajeno.pk])
        resp = self.client.post(url, self._payload())
        self.assertEqual(resp.status_code, 404)

        url_pagar = reverse("vehiculos:adeudo_pagar", args=[self.vehiculo.pk, adeudo_ajeno.pk])
        resp = self.client.post(url_pagar)
        self.assertEqual(resp.status_code, 404)

    def test_pagar_requiere_post(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )
        url = reverse("vehiculos:adeudo_pagar", args=[self.vehiculo.pk, adeudo.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

    def test_cancelar_requiere_post(self):
        adeudo = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )
        url = reverse("vehiculos:adeudo_cancelar", args=[self.vehiculo.pk, adeudo.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)


class ObservacionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador7", password="clave-segura-123")
        self.otro_user = User.objects.create_user(username="operador8", password="clave-segura-123")
        self.client.login(username="operador7", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000070")
        self.otro_vehiculo = crear_vehiculo("VIN0000000000071")

    def _payload(self, **overrides):
        datos = {
            "tipo_observacion": Observacion.TipoObservacion.GENERAL,
            "texto_observacion": "Unidad revisada sin novedades.",
        }
        datos.update(overrides)
        return datos

    def test_crear_observacion_asigna_autor_automaticamente(self):
        url = reverse("vehiculos:observacion_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload())
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        observacion = Observacion.objects.get(vehiculo=self.vehiculo)
        self.assertEqual(observacion.autor_registro, self.user)

    def test_editar_observacion_propia(self):
        observacion = Observacion.objects.create(
            vehiculo=self.vehiculo,
            tipo_observacion=Observacion.TipoObservacion.GENERAL,
            texto_observacion="Texto original",
            autor_registro=self.user,
        )
        url = reverse("vehiculos:observacion_editar", args=[self.vehiculo.pk, observacion.pk])
        resp = self.client.post(url, self._payload(texto_observacion="Texto corregido"))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        observacion.refresh_from_db()
        self.assertEqual(observacion.texto_observacion, "Texto corregido")

    def test_rechaza_texto_vacio(self):
        url = reverse("vehiculos:observacion_nueva", args=[self.vehiculo.pk])
        resp = self.client.post(url, self._payload(texto_observacion="   "))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Observacion.objects.filter(vehiculo=self.vehiculo).exists())

    def test_impide_editar_observacion_de_otro_usuario(self):
        observacion = Observacion.objects.create(
            vehiculo=self.vehiculo,
            tipo_observacion=Observacion.TipoObservacion.GENERAL,
            texto_observacion="Texto original",
            autor_registro=self.otro_user,
        )
        url = reverse("vehiculos:observacion_editar", args=[self.vehiculo.pk, observacion.pk])
        resp = self.client.post(url, self._payload(texto_observacion="Intento de edición ajena"))
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        observacion.refresh_from_db()
        self.assertEqual(observacion.texto_observacion, "Texto original")

    def test_impide_acceso_cruzado(self):
        observacion_ajena = Observacion.objects.create(
            vehiculo=self.otro_vehiculo,
            tipo_observacion=Observacion.TipoObservacion.GENERAL,
            texto_observacion="Observación de otro vehículo",
        )
        url = reverse("vehiculos:observacion_editar", args=[self.vehiculo.pk, observacion_ajena.pk])
        resp = self.client.post(url, self._payload())
        self.assertEqual(resp.status_code, 404)

    def test_orden_cronologico_mas_reciente_primero(self):
        ahora = timezone.now()
        antigua = Observacion.objects.create(
            vehiculo=self.vehiculo,
            tipo_observacion=Observacion.TipoObservacion.GENERAL,
            texto_observacion="Observación antigua",
            fecha_registro=ahora - timedelta(days=10),
        )
        reciente = Observacion.objects.create(
            vehiculo=self.vehiculo,
            tipo_observacion=Observacion.TipoObservacion.GENERAL,
            texto_observacion="Observación reciente",
            fecha_registro=ahora,
        )
        observaciones = list(self.vehiculo.observaciones.all())
        self.assertEqual(observaciones[0], reciente)
        self.assertEqual(observaciones[1], antigua)


class Fase5SeguridadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador9", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VIN0000000000080")

    def test_requiere_login(self):
        urls = [
            reverse("vehiculos:tenencia_nueva", args=[self.vehiculo.pk]),
            reverse("vehiculos:adeudo_nuevo", args=[self.vehiculo.pk]),
            reverse("vehiculos:observacion_nueva", args=[self.vehiculo.pk]),
        ]
        for url in urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertIn("/login", resp.url)

    def test_incluye_csrf_token_en_formularios(self):
        self.client.login(username="operador9", password="clave-segura-123")
        for name in ("tenencia_nueva", "adeudo_nuevo", "observacion_nueva"):
            url = reverse(f"vehiculos:{name}", args=[self.vehiculo.pk])
            resp = self.client.get(url)
            self.assertContains(resp, "csrfmiddlewaretoken")


class GpsVehiculoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gpsop1", password="clave-segura-123")
        self.client.login(username="gpsop1", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VINGPSVEH000001")
        self.otro_vehiculo = crear_vehiculo("VINGPSVEH000002")
        self.gps_libre = DispositivoGps.objects.create(imei="864VEH000000001", estatus_gps=DispositivoGps.Estatus.ACTIVO)
        self.gps_libre2 = DispositivoGps.objects.create(imei="864VEH000000002", estatus_gps=DispositivoGps.Estatus.ACTIVO)

    def test_instalar_gps_en_vehiculo_libre(self):
        url = reverse("vehiculos:gps_instalar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"gps": self.gps_libre.pk, "fecha_instalacion": ""})
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertTrue(
            InstalacionGps.objects.filter(vehiculo=self.vehiculo, gps=self.gps_libre, fecha_retiro__isnull=True).exists()
        )

    def test_impide_instalar_gps_ocupado(self):
        InstalacionGps.objects.create(vehiculo=self.otro_vehiculo, gps=self.gps_libre, fecha_retiro=None)
        url = reverse("vehiculos:gps_instalar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"gps": self.gps_libre.pk, "fecha_instalacion": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(InstalacionGps.objects.filter(vehiculo=self.vehiculo).exists())

    def test_impide_segundo_gps_activo_en_mismo_vehiculo(self):
        InstalacionGps.objects.create(vehiculo=self.vehiculo, gps=self.gps_libre, fecha_retiro=None)
        url = reverse("vehiculos:gps_instalar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"gps": self.gps_libre2.pk, "fecha_instalacion": ""})
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(InstalacionGps.objects.filter(vehiculo=self.vehiculo, fecha_retiro__isnull=True).count(), 1)

    def test_retirar_gps(self):
        instalacion = InstalacionGps.objects.create(
            vehiculo=self.vehiculo, gps=self.gps_libre, fecha_instalacion=localdate() - timedelta(days=10), fecha_retiro=None
        )
        url = reverse("vehiculos:gps_retirar", args=[self.vehiculo.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        instalacion.refresh_from_db()
        self.assertIsNotNone(instalacion.fecha_retiro)

    def test_retirar_conserva_historial(self):
        instalacion = InstalacionGps.objects.create(vehiculo=self.vehiculo, gps=self.gps_libre, fecha_retiro=None)
        url = reverse("vehiculos:gps_retirar", args=[self.vehiculo.pk])
        self.client.post(url)
        self.assertTrue(InstalacionGps.objects.filter(pk=instalacion.pk).exists())

    def test_impide_retirar_sin_instalacion_activa(self):
        url = reverse("vehiculos:gps_retirar", args=[self.vehiculo.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))

    def test_retirar_requiere_post(self):
        InstalacionGps.objects.create(vehiculo=self.vehiculo, gps=self.gps_libre, fecha_retiro=None)
        url = reverse("vehiculos:gps_retirar", args=[self.vehiculo.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

    def test_cambiar_gps_de_forma_atomica(self):
        instalacion = InstalacionGps.objects.create(vehiculo=self.vehiculo, gps=self.gps_libre, fecha_retiro=None)
        url = reverse("vehiculos:gps_cambiar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"gps": self.gps_libre2.pk, "fecha_instalacion": ""})
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        instalacion.refresh_from_db()
        self.assertIsNotNone(instalacion.fecha_retiro)
        self.assertTrue(
            InstalacionGps.objects.filter(vehiculo=self.vehiculo, gps=self.gps_libre2, fecha_retiro__isnull=True).exists()
        )

    def test_cambiar_gps_no_cierra_anterior_si_falla_nueva(self):
        instalacion = InstalacionGps.objects.create(vehiculo=self.vehiculo, gps=self.gps_libre, fecha_retiro=None)
        # El GPS "nuevo" ya está ocupado en otro vehículo: la operación debe fallar
        # sin cerrar la instalación actual.
        InstalacionGps.objects.create(vehiculo=self.otro_vehiculo, gps=self.gps_libre2, fecha_retiro=None)
        url = reverse("vehiculos:gps_cambiar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"gps": self.gps_libre2.pk, "fecha_instalacion": ""})
        self.assertEqual(resp.status_code, 200)
        instalacion.refresh_from_db()
        self.assertIsNone(instalacion.fecha_retiro)

    def test_impide_acceso_cruzado(self):
        instalacion_ajena = InstalacionGps.objects.create(vehiculo=self.otro_vehiculo, gps=self.gps_libre, fecha_retiro=None)
        # gps_retirar y gps_cambiar resuelven la instalación desde el propio vehículo
        # de la URL, así que "retirar" en self.vehiculo no debe afectar la ajena.
        url = reverse("vehiculos:gps_retirar", args=[self.vehiculo.pk])
        self.client.post(url)
        instalacion_ajena.refresh_from_db()
        self.assertIsNone(instalacion_ajena.fecha_retiro)

    def test_requiere_login(self):
        self.client.logout()
        resp = self.client.get(reverse("vehiculos:gps_instalar", args=[self.vehiculo.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)


class TagVehiculoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tagop1", password="clave-segura-123")
        self.client.login(username="tagop1", password="clave-segura-123")
        self.vehiculo = crear_vehiculo("VINTAGVEH000001")
        self.otro_vehiculo = crear_vehiculo("VINTAGVEH000002")
        self.tag_libre = TagTelepeaje.objects.create(codigo_tag="TAG-VEH-001", estatus_tag=TagTelepeaje.Estatus.ACTIVO)
        self.tag_libre2 = TagTelepeaje.objects.create(codigo_tag="TAG-VEH-002", estatus_tag=TagTelepeaje.Estatus.ACTIVO)

    def test_asignar_tag_a_vehiculo_libre(self):
        url = reverse("vehiculos:tag_asignar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"tag": self.tag_libre.pk, "fecha_inicio": ""})
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertTrue(
            AsignacionTag.objects.filter(vehiculo=self.vehiculo, tag=self.tag_libre, fecha_fin__isnull=True).exists()
        )

    def test_impide_asignar_tag_ocupado(self):
        AsignacionTag.objects.create(vehiculo=self.otro_vehiculo, tag=self.tag_libre, fecha_fin=None)
        url = reverse("vehiculos:tag_asignar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"tag": self.tag_libre.pk, "fecha_inicio": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(AsignacionTag.objects.filter(vehiculo=self.vehiculo).exists())

    def test_impide_segundo_tag_activo_en_mismo_vehiculo(self):
        AsignacionTag.objects.create(vehiculo=self.vehiculo, tag=self.tag_libre, fecha_fin=None)
        url = reverse("vehiculos:tag_asignar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"tag": self.tag_libre2.pk, "fecha_inicio": ""})
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        self.assertEqual(AsignacionTag.objects.filter(vehiculo=self.vehiculo, fecha_fin__isnull=True).count(), 1)

    def test_retirar_tag(self):
        asignacion = AsignacionTag.objects.create(
            vehiculo=self.vehiculo, tag=self.tag_libre, fecha_inicio=localdate() - timedelta(days=10), fecha_fin=None
        )
        url = reverse("vehiculos:tag_retirar", args=[self.vehiculo.pk])
        resp = self.client.post(url)
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        asignacion.refresh_from_db()
        self.assertIsNotNone(asignacion.fecha_fin)

    def test_retirar_conserva_historial(self):
        asignacion = AsignacionTag.objects.create(vehiculo=self.vehiculo, tag=self.tag_libre, fecha_fin=None)
        url = reverse("vehiculos:tag_retirar", args=[self.vehiculo.pk])
        self.client.post(url)
        self.assertTrue(AsignacionTag.objects.filter(pk=asignacion.pk).exists())

    def test_retirar_requiere_post(self):
        AsignacionTag.objects.create(vehiculo=self.vehiculo, tag=self.tag_libre, fecha_fin=None)
        url = reverse("vehiculos:tag_retirar", args=[self.vehiculo.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

    def test_cambiar_tag_de_forma_atomica(self):
        asignacion = AsignacionTag.objects.create(vehiculo=self.vehiculo, tag=self.tag_libre, fecha_fin=None)
        url = reverse("vehiculos:tag_cambiar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"tag": self.tag_libre2.pk, "fecha_inicio": ""})
        self.assertRedirects(resp, reverse("vehiculos:detalle", args=[self.vehiculo.pk]))
        asignacion.refresh_from_db()
        self.assertIsNotNone(asignacion.fecha_fin)
        self.assertTrue(
            AsignacionTag.objects.filter(vehiculo=self.vehiculo, tag=self.tag_libre2, fecha_fin__isnull=True).exists()
        )

    def test_cambiar_tag_no_cierra_anterior_si_falla_nueva(self):
        asignacion = AsignacionTag.objects.create(vehiculo=self.vehiculo, tag=self.tag_libre, fecha_fin=None)
        AsignacionTag.objects.create(vehiculo=self.otro_vehiculo, tag=self.tag_libre2, fecha_fin=None)
        url = reverse("vehiculos:tag_cambiar", args=[self.vehiculo.pk])
        resp = self.client.post(url, {"tag": self.tag_libre2.pk, "fecha_inicio": ""})
        self.assertEqual(resp.status_code, 200)
        asignacion.refresh_from_db()
        self.assertIsNone(asignacion.fecha_fin)

    def test_impide_acceso_cruzado(self):
        asignacion_ajena = AsignacionTag.objects.create(vehiculo=self.otro_vehiculo, tag=self.tag_libre, fecha_fin=None)
        url = reverse("vehiculos:tag_retirar", args=[self.vehiculo.pk])
        self.client.post(url)
        asignacion_ajena.refresh_from_db()
        self.assertIsNone(asignacion_ajena.fecha_fin)

    def test_requiere_login(self):
        self.client.logout()
        resp = self.client.get(reverse("vehiculos:tag_asignar", args=[self.vehiculo.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)


class SeedDemoDataIdempotenciaTests(TestCase):
    """El comando debe poder ejecutarse muchas veces (incluso en días
    distintos) sin ir acumulando registros demo duplicados."""

    def _conteos_demo(self):
        demo = {"vehiculo__numero_serie__startswith": "VDEMO"}
        return {
            "polizas": PolizaSeguro.objects.filter(**demo).count(),
            "verificaciones": VerificacionVehicular.objects.filter(**demo).count(),
            "tarjetas": TarjetaCirculacion.objects.filter(**demo).count(),
            "tenencias": Tenencia.objects.filter(**demo).count(),
            "adeudos": AdeudoVehicular.objects.filter(**demo).count(),
            "observaciones": Observacion.objects.filter(**demo).count(),
            "instalaciones_gps": InstalacionGps.objects.filter(**demo).count(),
            "asignaciones_tag": AsignacionTag.objects.filter(**demo).count(),
            "gps_demo": DispositivoGps.objects.filter(imei__startswith="864DEMO").count(),
            "tags_demo": TagTelepeaje.objects.filter(codigo_tag__startswith="TAG-DEMO").count(),
        }

    def test_ejecutar_el_seed_varios_dias_no_duplica_tarjetas(self):
        call_command("seed_demo_data")
        primera_corrida = self._conteos_demo()
        self.assertGreater(primera_corrida["tarjetas"], 0)
        self.assertGreater(primera_corrida["tenencias"], 0)
        self.assertGreater(primera_corrida["adeudos"], 0)
        self.assertGreater(primera_corrida["observaciones"], 0)
        self.assertGreater(primera_corrida["instalaciones_gps"], 0)
        self.assertGreater(primera_corrida["asignaciones_tag"], 0)
        self.assertGreater(primera_corrida["gps_demo"], 0)
        self.assertGreater(primera_corrida["tags_demo"], 0)

        # Simula que el comando se vuelve a ejecutar 10 días después: las
        # fechas relativas a "hoy" cambian, pero la identidad de cada
        # registro demo (vehículo, número de póliza+aseguradora, semestre)
        # debe seguir siendo la misma.
        otro_dia = localdate() + timedelta(days=10)
        with patch("vehiculos.management.commands.seed_demo_data.localdate", return_value=otro_dia):
            call_command("seed_demo_data")
            call_command("seed_demo_data")

        segunda_corrida = self._conteos_demo()
        self.assertEqual(primera_corrida, segunda_corrida)

        # Y que las fechas sí se hayan actualizado con la nueva "hoy"
        # (no se ignoró la ejecución: se actualizó vía defaults).
        tarjeta_v001 = TarjetaCirculacion.objects.get(vehiculo__numero_serie="VDEMO1A2B3C4D5E6F7")
        self.assertEqual(tarjeta_v001.fecha_vigencia_fin, otro_dia + timedelta(days=180))
