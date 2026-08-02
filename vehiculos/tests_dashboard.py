"""Pruebas de la Fase 7: dashboard operativo de alertas y vencimientos."""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate

from actores.models import Aseguradora, Conductor, ReferenciaConductor
from catalogos.models import Color, Marca, ModeloVehiculo
from dispositivos.models import DispositivoGps, InstalacionGps, TagTelepeaje
from .dashboard_queries import (
    adeudos_destacados,
    clasificar_dias,
    estatus_vehiculo_valido,
    horizonte_valido,
    obtener_vencimientos,
    resumen_conductores,
    resumen_dispositivos,
    resumen_vehiculos,
    severidad_valida,
    tipo_valido,
)
from .models import AdeudoVehicular, PolizaSeguro, VerificacionVehicular, Vehiculo

User = get_user_model()


def crear_vehiculo(numero_serie, estatus=Vehiculo.EstatusUnidad.ACTIVA):
    marca = Marca.objects.create(nombre_marca=f"Marca {numero_serie}")
    modelo = ModeloVehiculo.objects.create(marca=marca, nombre_modelo_comercial="Modelo X")
    color = Color.objects.create(nombre_color=f"Color {numero_serie}")
    return Vehiculo.objects.create(
        numero_serie=numero_serie,
        modelo_vehiculo=modelo,
        color=color,
        anio_modelo=2023,
        estatus_unidad=estatus,
    )


def crear_conductor(nombre, **overrides):
    datos = {
        "nombre_completo": nombre,
        "estatus_conductor": Conductor.Estatus.ACTIVO,
    }
    datos.update(overrides)
    return Conductor.objects.create(**datos)


class ClasificarDiasTests(TestCase):
    def test_dias_negativos_es_vencido(self):
        bucket, _, css = clasificar_dias(-1)
        self.assertEqual(bucket, "VENCIDO")
        self.assertIn("bg-danger", css)

    def test_treinta_dias_es_bucket_30(self):
        bucket, _, _ = clasificar_dias(30)
        self.assertEqual(bucket, "30")

    def test_treinta_y_uno_dias_es_bucket_60(self):
        bucket, _, _ = clasificar_dias(31)
        self.assertEqual(bucket, "60")

    def test_sesenta_dias_es_bucket_60(self):
        bucket, _, _ = clasificar_dias(60)
        self.assertEqual(bucket, "60")

    def test_sesenta_y_uno_dias_es_bucket_90(self):
        bucket, _, _ = clasificar_dias(61)
        self.assertEqual(bucket, "90")

    def test_noventa_dias_es_bucket_90(self):
        bucket, _, _ = clasificar_dias(90)
        self.assertEqual(bucket, "90")

    def test_cero_dias_es_bucket_30(self):
        bucket, _, _ = clasificar_dias(0)
        self.assertEqual(bucket, "30")


class ValidadoresParametrosTests(TestCase):
    def test_horizonte_invalido_regresa_defecto(self):
        self.assertEqual(horizonte_valido("no-es-numero"), 30)
        self.assertEqual(horizonte_valido("45"), 30)
        self.assertEqual(horizonte_valido(None), 30)

    def test_horizonte_valido_se_respeta(self):
        self.assertEqual(horizonte_valido("60"), 60)
        self.assertEqual(horizonte_valido("90"), 90)

    def test_tipo_invalido_regresa_vacio(self):
        self.assertEqual(tipo_valido("no-existe"), "")
        self.assertEqual(tipo_valido("poliza"), "POLIZA")

    def test_severidad_invalida_regresa_vacio(self):
        self.assertEqual(severidad_valida("critico"), "")
        self.assertEqual(severidad_valida("vencido"), "VENCIDO")

    def test_estatus_vehiculo_invalido_regresa_vacio(self):
        self.assertEqual(estatus_vehiculo_valido("NO_EXISTE"), "")
        self.assertEqual(estatus_vehiculo_valido("taller"), "TALLER")


class ResumenVehiculosTests(TestCase):
    """Usa fechas controladas (no `localdate()` real) para que la
    clasificación vencido/30/60/90 no dependa del día en que corra la
    prueba."""

    def setUp(self):
        self.hoy = date(2026, 6, 1)
        self.aseguradora = Aseguradora.objects.create(nombre_organizacion="Aseguradora Dash")

    def test_excluye_vehiculos_inactivos_del_resumen(self):
        crear_vehiculo("VDASH0000000001", estatus=Vehiculo.EstatusUnidad.ACTIVA)
        crear_vehiculo("VDASH0000000002", estatus=Vehiculo.EstatusUnidad.BAJA)
        crear_vehiculo("VDASH0000000003", estatus=Vehiculo.EstatusUnidad.TALLER)

        resumen = resumen_vehiculos(self.hoy)
        self.assertEqual(resumen["activos"], 1)
        self.assertEqual(resumen["total"], 3)

    def test_sin_conductor_cuenta_solo_activos(self):
        crear_vehiculo("VDASH0000000010")
        crear_vehiculo("VDASH0000000011", estatus=Vehiculo.EstatusUnidad.BAJA)

        resumen = resumen_vehiculos(self.hoy)
        # Ambos vehículos carecen de conductor, pero solo el activo cuenta.
        self.assertEqual(resumen["sin_conductor"], 1)

    def test_sin_poliza_vigente_incluye_vencidas_y_sin_registro(self):
        con_poliza_vigente = crear_vehiculo("VDASH0000000020")
        con_poliza_vencida = crear_vehiculo("VDASH0000000021")
        sin_poliza = crear_vehiculo("VDASH0000000022")

        PolizaSeguro.objects.create(
            vehiculo=con_poliza_vigente, aseguradora=self.aseguradora,
            numero_poliza="POL-VIG", fecha_vigencia_fin=self.hoy + timedelta(days=180),
        )
        PolizaSeguro.objects.create(
            vehiculo=con_poliza_vencida, aseguradora=self.aseguradora,
            numero_poliza="POL-VENC", fecha_vigencia_fin=self.hoy - timedelta(days=10),
        )

        resumen = resumen_vehiculos(self.hoy)
        self.assertEqual(resumen["sin_poliza"], 2)  # vencida + sin registro

    def test_sin_gps_y_sin_tag(self):
        con_gps = crear_vehiculo("VDASH0000000030")
        sin_gps = crear_vehiculo("VDASH0000000031")
        gps = DispositivoGps.objects.create(imei="864DASH000000001", estatus_gps="ACTIVO")
        InstalacionGps.objects.create(vehiculo=con_gps, gps=gps, fecha_retiro=None)

        resumen = resumen_vehiculos(self.hoy)
        self.assertEqual(resumen["sin_gps"], 1)
        self.assertEqual(resumen["sin_tag"], 2)  # ninguno tiene TAG

    def test_monto_adeudos_pendientes_usa_agregacion(self):
        v1 = crear_vehiculo("VDASH0000000040")
        v2 = crear_vehiculo("VDASH0000000041")
        AdeudoVehicular.objects.create(
            vehiculo=v1, tipo_adeudo="Multa", estatus_adeudo="PENDIENTE", monto_adeudo=1200,
        )
        AdeudoVehicular.objects.create(
            vehiculo=v2, tipo_adeudo="Tenencia", estatus_adeudo="PENDIENTE", monto_adeudo=300,
        )
        # Un adeudo pagado no debe sumar al total pendiente.
        AdeudoVehicular.objects.create(
            vehiculo=v1, tipo_adeudo="Multa vieja", estatus_adeudo="PAGADO", monto_adeudo=999,
        )

        resumen = resumen_vehiculos(self.hoy)
        self.assertEqual(resumen["con_adeudos"], 2)
        self.assertEqual(resumen["monto_adeudos"], 1500)


class ResumenConductoresTests(TestCase):
    def setUp(self):
        self.hoy = date(2026, 6, 1)

    def test_sin_vehiculo_solo_cuenta_activos(self):
        crear_conductor("Sin Vehículo Activo")
        crear_conductor("Sin Vehículo Baja", estatus_conductor=Conductor.Estatus.BAJA)

        resumen = resumen_conductores(self.hoy)
        self.assertEqual(resumen["sin_vehiculo"], 1)

    def test_sin_referencias(self):
        con_ref = crear_conductor("Con Referencia")
        sin_ref = crear_conductor("Sin Referencia")
        ReferenciaConductor.objects.create(
            conductor=con_ref, nombre="Alguien", domicilio="Calle 1",
            telefono_contacto="555", parentesco="MADRE",
        )
        resumen = resumen_conductores(self.hoy)
        self.assertEqual(resumen["sin_referencias"], 1)

    def test_licencias_vencidas_y_por_vencer(self):
        crear_conductor("Vencida", fecha_vencimiento_licencia=self.hoy - timedelta(days=5))
        crear_conductor("Por vencer", fecha_vencimiento_licencia=self.hoy + timedelta(days=10))
        crear_conductor("Lejana", fecha_vencimiento_licencia=self.hoy + timedelta(days=200))
        crear_conductor("Sin licencia")

        resumen = resumen_conductores(self.hoy, horizonte=30)
        self.assertEqual(resumen["licencias_vencidas"], 1)
        self.assertEqual(resumen["licencias_por_vencer"], 1)

    def test_baja_no_cuenta_en_ninguna_metrica(self):
        crear_conductor(
            "Conductor Baja",
            estatus_conductor=Conductor.Estatus.BAJA,
            fecha_vencimiento_licencia=self.hoy - timedelta(days=5),
        )
        resumen = resumen_conductores(self.hoy)
        self.assertEqual(resumen["licencias_vencidas"], 0)
        self.assertEqual(resumen["activos"], 0)


class ResumenDispositivosTests(TestCase):
    def test_disponibles_e_inactivos(self):
        DispositivoGps.objects.create(imei="864DASH100000001", estatus_gps="ACTIVO")
        gps_instalado = DispositivoGps.objects.create(imei="864DASH100000002", estatus_gps="ACTIVO")
        DispositivoGps.objects.create(imei="864DASH100000003", estatus_gps="INACTIVO")
        v = crear_vehiculo("VDASH0000000050")
        InstalacionGps.objects.create(vehiculo=v, gps=gps_instalado, fecha_retiro=None)

        TagTelepeaje.objects.create(codigo_tag="TAGDASH001", estatus_tag="ACTIVO")
        TagTelepeaje.objects.create(codigo_tag="TAGDASH002", estatus_tag="INACTIVO")

        resumen = resumen_dispositivos()
        self.assertEqual(resumen["gps_disponibles"], 1)
        self.assertEqual(resumen["gps_inactivos"], 1)
        self.assertEqual(resumen["tag_disponibles"], 1)
        self.assertEqual(resumen["tag_inactivos"], 1)


class ObtenerVencimientosTests(TestCase):
    def setUp(self):
        self.hoy = date(2026, 6, 1)
        self.aseguradora = Aseguradora.objects.create(nombre_organizacion="Aseguradora Venc")

    def test_clasifica_poliza_vencida_y_proxima(self):
        vencida = crear_vehiculo("VDASH0000000060")
        proxima = crear_vehiculo("VDASH0000000061")
        PolizaSeguro.objects.create(
            vehiculo=vencida, aseguradora=self.aseguradora, numero_poliza="P1",
            fecha_vigencia_fin=self.hoy - timedelta(days=5),
        )
        PolizaSeguro.objects.create(
            vehiculo=proxima, aseguradora=self.aseguradora, numero_poliza="P2",
            fecha_vigencia_fin=self.hoy + timedelta(days=10),
        )
        filas = obtener_vencimientos(self.hoy)
        buckets = {f["entidad"]: f["bucket"] for f in filas}
        self.assertEqual(buckets[vencida.numero_serie], "VENCIDO")
        self.assertEqual(buckets[proxima.numero_serie], "30")

    def test_fuera_de_horizonte_no_aparece(self):
        lejano = crear_vehiculo("VDASH0000000062")
        PolizaSeguro.objects.create(
            vehiculo=lejano, aseguradora=self.aseguradora, numero_poliza="P3",
            fecha_vigencia_fin=self.hoy + timedelta(days=200),
        )
        filas = obtener_vencimientos(self.hoy)
        self.assertFalse(any(f["entidad"] == lejano.numero_serie for f in filas))

    def test_filtro_por_tipo(self):
        v = crear_vehiculo("VDASH0000000063")
        PolizaSeguro.objects.create(
            vehiculo=v, aseguradora=self.aseguradora, numero_poliza="P4",
            fecha_vigencia_fin=self.hoy + timedelta(days=5),
        )
        VerificacionVehicular.objects.create(
            vehiculo=v, semestre="2026-1", fecha_limite_verificacion=self.hoy + timedelta(days=5),
        )
        solo_polizas = obtener_vencimientos(self.hoy, tipo="POLIZA")
        self.assertTrue(all(f["tipo"] == "POLIZA" for f in solo_polizas))
        self.assertTrue(any(f["tipo"] == "POLIZA" for f in solo_polizas))

    def test_filtro_por_severidad_ignora_horizonte(self):
        v = crear_vehiculo("VDASH0000000064")
        PolizaSeguro.objects.create(
            vehiculo=v, aseguradora=self.aseguradora, numero_poliza="P5",
            fecha_vigencia_fin=self.hoy + timedelta(days=75),
        )
        # horizonte=30 normalmente excluiría este registro de 75 días, pero
        # severidad="90" debe encontrarlo igual (la severidad manda).
        filas = obtener_vencimientos(self.hoy, horizonte=30, severidad="90")
        self.assertTrue(any(f["entidad"] == v.numero_serie for f in filas))

    def test_licencia_de_conductor_incluida(self):
        conductor = crear_conductor("Con Licencia Próxima", fecha_vencimiento_licencia=self.hoy + timedelta(days=5))
        filas = obtener_vencimientos(self.hoy)
        self.assertTrue(any(f["tipo"] == "LICENCIA" and f["entidad"] == conductor.nombre_completo for f in filas))

    def test_estatus_explicito_excluye_licencias(self):
        crear_conductor("Con Licencia Excluida", fecha_vencimiento_licencia=self.hoy + timedelta(days=5))
        filas = obtener_vencimientos(self.hoy, estatus="ACTIVA")
        self.assertFalse(any(f["tipo"] == "LICENCIA" for f in filas))

    def test_busqueda_por_placas_o_entidad(self):
        v1 = crear_vehiculo("VDASHBUSCAME01")
        v2 = crear_vehiculo("VDASHOTROVEHIC")
        PolizaSeguro.objects.create(
            vehiculo=v1, aseguradora=self.aseguradora, numero_poliza="P6",
            fecha_vigencia_fin=self.hoy + timedelta(days=5),
        )
        PolizaSeguro.objects.create(
            vehiculo=v2, aseguradora=self.aseguradora, numero_poliza="P7",
            fecha_vigencia_fin=self.hoy + timedelta(days=5),
        )
        filas = obtener_vencimientos(self.hoy, q="BUSCAME")
        entidades = {f["entidad"] for f in filas}
        self.assertIn(v1.numero_serie, entidades)
        self.assertNotIn(v2.numero_serie, entidades)


class AdeudosDestacadosTests(TestCase):
    def test_ordena_por_monto_descendente(self):
        v = crear_vehiculo("VDASH0000000070")
        AdeudoVehicular.objects.create(vehiculo=v, tipo_adeudo="Chico", estatus_adeudo="PENDIENTE", monto_adeudo=100)
        AdeudoVehicular.objects.create(vehiculo=v, tipo_adeudo="Grande", estatus_adeudo="PENDIENTE", monto_adeudo=5000)
        top = list(adeudos_destacados(limite=5))
        self.assertEqual(top[0].tipo_adeudo, "Grande")


class DashboardVistaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dashuser", password="clave-segura-123")
        self.client.login(username="dashuser", password="clave-segura-123")

    def test_requiere_login(self):
        self.client.logout()
        resp = self.client.get(reverse("vehiculos:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.url)

    def test_dashboard_sin_datos_no_falla(self):
        resp = self.client.get(reverse("vehiculos:dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Dashboard")

    def test_dashboard_ignora_parametros_invalidos(self):
        resp = self.client.get(reverse("vehiculos:dashboard"), {
            "horizonte": "9999", "tipo": "NO_EXISTE", "severidad": "CRITICO",
            "estatus": "NO_EXISTE", "page": "abc",
        })
        self.assertEqual(resp.status_code, 200)

    def test_filtros_se_conservan_en_el_contexto(self):
        resp = self.client.get(reverse("vehiculos:dashboard"), {"horizonte": "60", "tipo": "POLIZA"})
        self.assertEqual(resp.context["horizonte"], 60)
        self.assertEqual(resp.context["tipo"], "POLIZA")

    def test_tarjetas_enlazan_a_vehiculos_filtrados(self):
        resp = self.client.get(reverse("vehiculos:dashboard"))
        self.assertContains(resp, "alerta=sin_conductor")
        self.assertContains(resp, "alerta=sin_poliza")
        self.assertContains(resp, "alerta=adeudos")

    def test_numero_de_consultas_estable_sin_importar_cantidad_de_vehiculos(self):
        """El dashboard no debe hacer una consulta por vehículo (N+1): el
        número de queries con 2 vehículos debe ser igual que con 10."""
        for i in range(2):
            crear_vehiculo(f"VDASHQ0000000{i}")
        queries_pocos = self._contar_queries_dashboard()

        for i in range(2, 10):
            crear_vehiculo(f"VDASHQ0000000{i}")
        queries_muchos = self._contar_queries_dashboard()

        self.assertEqual(queries_pocos, queries_muchos)

    def _contar_queries_dashboard(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(reverse("vehiculos:dashboard"))
        self.assertEqual(resp.status_code, 200)
        return len(ctx.captured_queries)


class ListaVehiculosAlertaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="listauser", password="clave-segura-123")
        self.client.login(username="listauser", password="clave-segura-123")

    def test_alerta_sin_conductor_filtra_correctamente(self):
        crear_vehiculo("VDASHLISTA00001")
        resp = self.client.get(reverse("vehiculos:lista"), {"alerta": "sin_conductor"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "VDASHLISTA00001")

    def test_alerta_invalida_no_produce_error(self):
        resp = self.client.get(reverse("vehiculos:lista"), {"alerta": "no_existe"})
        self.assertEqual(resp.status_code, 200)


class ConductoresListaAlertaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="conduser", password="clave-segura-123")
        self.client.login(username="conduser", password="clave-segura-123")

    def test_alerta_licencia_vencida(self):
        crear_conductor("Vencida Lista", fecha_vencimiento_licencia=localdate() - timedelta(days=1))
        crear_conductor("Vigente Lista", fecha_vencimiento_licencia=localdate() + timedelta(days=200))
        resp = self.client.get(reverse("actores:conductores_lista"), {"alerta": "licencia_vencida"})
        self.assertContains(resp, "Vencida Lista")
        self.assertNotContains(resp, "Vigente Lista")

    def test_alerta_invalida_no_produce_error(self):
        resp = self.client.get(reverse("actores:conductores_lista"), {"alerta": "no_existe"})
        self.assertEqual(resp.status_code, 200)


class SeedDemoDataFase7Tests(TestCase):
    """Verifica que el seed reclasifique fechas relativas a 'hoy' incluso si
    ya existían registros creados en una corrida anterior (simulando otro
    día), y que los casos de la Fase 7 queden demostrables."""

    def test_polizas_y_verificaciones_se_reclasifican_en_otro_dia(self):
        from django.core.management import call_command

        call_command("seed_demo_data")
        otro_dia = localdate() + timedelta(days=20)
        with patch("vehiculos.management.commands.seed_demo_data.localdate", return_value=otro_dia):
            call_command("seed_demo_data")

        poliza_v3 = PolizaSeguro.objects.get(numero_poliza="POL-DEMO-003")
        # "amarillo" se recalcula sobre el nuevo "hoy" en cada corrida.
        self.assertEqual(poliza_v3.fecha_vigencia_fin, otro_dia + timedelta(days=15))

    def test_no_duplica_polizas_ni_verificaciones(self):
        from django.core.management import call_command

        call_command("seed_demo_data")
        primera = PolizaSeguro.objects.filter(vehiculo__numero_serie__startswith="VDEMO").count()
        otro_dia = localdate() + timedelta(days=5)
        with patch("vehiculos.management.commands.seed_demo_data.localdate", return_value=otro_dia):
            call_command("seed_demo_data")
        segunda = PolizaSeguro.objects.filter(vehiculo__numero_serie__startswith="VDEMO").count()
        self.assertEqual(primera, segunda)
