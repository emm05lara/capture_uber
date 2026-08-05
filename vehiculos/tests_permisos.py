"""Pruebas de roles y permisos aplicados a las vistas de todas las apps (Fase 9).

Cubren las tres capas que pide la fase:

* lectura: los tres roles autenticados pueden consultar;
* escritura y acciones operativas: CONSULTA recibe 403 aunque escriba la
  URL directamente, ADMIN y OPERADOR sí pueden;
* interfaz: los botones de escritura no se pintan para CONSULTA (pero eso
  nunca sustituye a la validación de servidor, que se prueba aparte).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate

from accounts.permissions import ROL_ADMIN, ROL_CONSULTA, ROL_OPERADOR
from actores.models import Aseguradora, Conductor, ReferenciaConductor
from catalogos.models import Color, EntidadFederativa, Marca, ModeloVehiculo
from dispositivos.models import DispositivoGps, TagTelepeaje
from operacion.models import AsignacionVehiculo
from .models import AdeudoVehicular, Emplacamiento, Vehiculo

User = get_user_model()

CLAVE = "Flotilla-2026-Segura"


def crear_vehiculo(numero_serie, numero_interno=None):
    marca = Marca.objects.create(nombre_marca=f"Marca {numero_serie}")
    modelo = ModeloVehiculo.objects.create(marca=marca, nombre_modelo_comercial="Modelo X")
    color = Color.objects.create(nombre_color=f"Color {numero_serie}")
    return Vehiculo.objects.create(
        numero_serie=numero_serie,
        numero_interno=numero_interno,
        modelo_vehiculo=modelo,
        color=color,
        anio_modelo=2023,
        estatus_unidad=Vehiculo.EstatusUnidad.ACTIVA,
    )


class BasePermisosTests(TestCase):
    """Fixture común: un usuario por rol y datos suficientes para que todas
    las URLs de escritura existan."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("perm_admin", password=CLAVE, rol=ROL_ADMIN)
        cls.operador = User.objects.create_user("perm_operador", password=CLAVE, rol=ROL_OPERADOR)
        cls.consulta = User.objects.create_user("perm_consulta", password=CLAVE, rol=ROL_CONSULTA)
        cls.superusuario = User.objects.create_superuser(
            "perm_root", password=CLAVE, rol=ROL_CONSULTA,
        )

        cls.vehiculo = crear_vehiculo("VINPERMISOS000001", numero_interno="P-001")
        cls.entidad = EntidadFederativa.objects.create(nombre_entidad="Estado Permisos")
        cls.conductor = Conductor.objects.create(
            nombre_completo="Conductor de Permisos",
            estatus_conductor=Conductor.Estatus.ACTIVO,
        )
        # Un conductor solo es asignable si tiene al menos una referencia.
        ReferenciaConductor.objects.create(
            conductor=cls.conductor,
            nombre="Referencia de Permisos",
            domicilio="Calle Falsa 123",
            telefono_contacto="55 0000 0000",
            parentesco="MADRE",
        )
        cls.aseguradora = Aseguradora.objects.create(nombre_organizacion="Aseguradora Permisos")
        cls.gps = DispositivoGps.objects.create(imei="356789100000001")
        cls.tag = TagTelepeaje.objects.create(codigo_tag="TAGPERMISOS0001")
        cls.adeudo = AdeudoVehicular.objects.create(
            vehiculo=cls.vehiculo,
            tipo_adeudo="Multa de prueba",
            monto_adeudo="500.00",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )

    # -- Catálogos de URLs -------------------------------------------------

    def urls_lectura(self):
        return [
            reverse("vehiculos:dashboard"),
            reverse("vehiculos:lista"),
            reverse("vehiculos:detalle", args=[self.vehiculo.pk]),
            reverse("actores:conductores_lista"),
            reverse("actores:conductor_detalle", args=[self.conductor.pk]),
            reverse("dispositivos:gps_lista"),
            reverse("dispositivos:gps_detalle", args=[self.gps.pk]),
            reverse("dispositivos:tag_lista"),
            reverse("dispositivos:tag_detalle", args=[self.tag.pk]),
        ]

    def urls_exportacion(self):
        return [
            reverse("vehiculos:exportar_lista"),
            reverse("vehiculos:exportar_detalle", args=[self.vehiculo.pk]),
            reverse("vehiculos:dashboard_exportar"),
            reverse("actores:conductores_exportar"),
        ]

    def urls_escritura_get(self):
        """Vistas de escritura que se abren con GET (formularios)."""
        v = self.vehiculo.pk
        return [
            reverse("vehiculos:nuevo"),
            reverse("vehiculos:editar", args=[v]),
            reverse("vehiculos:nueva_placa", args=[v]),
            reverse("vehiculos:asignar_conductor", args=[v]),
            reverse("vehiculos:poliza_nueva", args=[v]),
            reverse("vehiculos:verificacion_nueva", args=[v]),
            reverse("vehiculos:tarjeta_nueva", args=[v]),
            reverse("vehiculos:tenencia_nueva", args=[v]),
            reverse("vehiculos:adeudo_nuevo", args=[v]),
            reverse("vehiculos:adeudo_editar", args=[v, self.adeudo.pk]),
            reverse("vehiculos:observacion_nueva", args=[v]),
            reverse("vehiculos:gps_instalar", args=[v]),
            reverse("vehiculos:tag_asignar", args=[v]),
            reverse("actores:conductor_nuevo"),
            reverse("actores:conductor_editar", args=[self.conductor.pk]),
            reverse("dispositivos:gps_nuevo"),
            reverse("dispositivos:gps_editar", args=[self.gps.pk]),
            reverse("dispositivos:tag_nuevo"),
            reverse("dispositivos:tag_editar", args=[self.tag.pk]),
        ]

    def urls_escritura_condicionadas(self):
        """Vistas de escritura que, sin conductor/dispositivo vigente,
        redirigen por regla de negocio: solo se comprueba el 403."""
        v = self.vehiculo.pk
        return [
            reverse("vehiculos:cambiar_conductor", args=[v]),
            reverse("vehiculos:gps_cambiar", args=[v]),
            reverse("vehiculos:tag_cambiar", args=[v]),
        ]

    def urls_acciones_post(self):
        """Acciones que solo aceptan POST."""
        v = self.vehiculo.pk
        return [
            reverse("vehiculos:cambiar_estatus", args=[v]),
            reverse("vehiculos:finalizar_asignacion", args=[v]),
            reverse("vehiculos:adeudo_pagar", args=[v, self.adeudo.pk]),
            reverse("vehiculos:adeudo_cancelar", args=[v, self.adeudo.pk]),
            reverse("vehiculos:gps_retirar", args=[v]),
            reverse("vehiculos:tag_retirar", args=[v]),
        ]


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

class LecturaPorRolTests(BasePermisosTests):
    def test_los_tres_roles_pueden_consultar(self):
        for usuario in (self.admin, self.operador, self.consulta):
            self.client.force_login(usuario)
            for url in self.urls_lectura():
                self.assertEqual(
                    self.client.get(url).status_code, 200, f"{usuario.rol} {url}",
                )

    def test_usuario_no_autenticado_va_al_login(self):
        for url in self.urls_lectura():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, url)
            self.assertIn("/accounts/login/", resp["Location"])


# ---------------------------------------------------------------------------
# Escritura: la validación es de servidor
# ---------------------------------------------------------------------------

class EscrituraPorRolTests(BasePermisosTests):
    def test_consulta_recibe_403_en_formularios_de_escritura(self):
        self.client.force_login(self.consulta)
        for url in self.urls_escritura_get() + self.urls_escritura_condicionadas():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 403, url)
            self.assertTemplateUsed(resp, "403.html")

    def test_consulta_recibe_403_aunque_envie_post_directo(self):
        """Ocultar el botón no basta: el POST manipulado también se rechaza."""
        self.client.force_login(self.consulta)
        urls = (
            self.urls_escritura_get()
            + self.urls_escritura_condicionadas()
            + self.urls_acciones_post()
        )
        for url in urls:
            self.assertEqual(self.client.post(url, {}).status_code, 403, url)

    def test_admin_y_operador_abren_los_formularios(self):
        for usuario in (self.admin, self.operador):
            self.client.force_login(usuario)
            for url in self.urls_escritura_get():
                self.assertEqual(
                    self.client.get(url).status_code, 200, f"{usuario.rol} {url}",
                )

    def test_superusuario_conserva_acceso_total_pese_a_rol_consulta(self):
        self.client.force_login(self.superusuario)
        for url in self.urls_escritura_get():
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_usuario_no_autenticado_va_al_login_en_escritura(self):
        for url in self.urls_escritura_get():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, url)
            self.assertIn("/accounts/login/", resp["Location"])


# ---------------------------------------------------------------------------
# Acciones operativas concretas
# ---------------------------------------------------------------------------

class AccionesOperativasPorRolTests(BasePermisosTests):
    def test_operador_puede_crear_vehiculo_y_consulta_no(self):
        datos = {
            "numero_interno": "P-999",
            "modelo_vehiculo": self.vehiculo.modelo_vehiculo.pk,
            "anio_modelo": 2024,
            "color": self.vehiculo.color.pk,
            "numero_serie": "VINPERMISOS000999",
            "estatus_unidad": Vehiculo.EstatusUnidad.ACTIVA,
            "placas": "",
            "entidad_federativa": "",
        }
        url = reverse("vehiculos:nuevo")

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(Vehiculo.objects.filter(numero_serie="VINPERMISOS000999").exists())

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.assertTrue(Vehiculo.objects.filter(numero_serie="VINPERMISOS000999").exists())

    def test_cambio_de_estatus(self):
        url = reverse("vehiculos:cambiar_estatus", args=[self.vehiculo.pk])
        datos = {"estatus_unidad": Vehiculo.EstatusUnidad.TALLER}

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estatus_unidad, Vehiculo.EstatusUnidad.ACTIVA)

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estatus_unidad, Vehiculo.EstatusUnidad.TALLER)

    def test_cambio_de_placas(self):
        url = reverse("vehiculos:nueva_placa", args=[self.vehiculo.pk])
        datos = {
            "placas": "PERM-01",
            "entidad_federativa": self.entidad.pk,
            "fecha_inicio": localdate().isoformat(),
        }

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(Emplacamiento.objects.filter(placas="PERM-01").exists())

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.assertTrue(Emplacamiento.objects.filter(placas="PERM-01").exists())

    def test_asignacion_de_conductor(self):
        url = reverse("vehiculos:asignar_conductor", args=[self.vehiculo.pk])
        datos = {
            "conductor": self.conductor.pk,
            "fecha_inicio": localdate().isoformat(),
            "plataforma": "",
            "socio": "",
            "cuenta": "",
        }

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo).exists())

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.assertTrue(
            AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo, fecha_fin__isnull=True).exists()
        )

        # Y finalizarla también es una acción operativa.
        url_fin = reverse("vehiculos:finalizar_asignacion", args=[self.vehiculo.pk])
        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url_fin, {}).status_code, 403)

        self.client.force_login(self.admin)
        self.client.post(url_fin, {})
        self.assertFalse(
            AsignacionVehiculo.objects.filter(vehiculo=self.vehiculo, fecha_fin__isnull=True).exists()
        )

    def test_pagar_y_cancelar_adeudos(self):
        url_pagar = reverse("vehiculos:adeudo_pagar", args=[self.vehiculo.pk, self.adeudo.pk])

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url_pagar).status_code, 403)
        self.adeudo.refresh_from_db()
        self.assertEqual(self.adeudo.estatus_adeudo, AdeudoVehicular.EstatusAdeudo.PENDIENTE)

        self.client.force_login(self.operador)
        self.client.post(url_pagar)
        self.adeudo.refresh_from_db()
        self.assertEqual(self.adeudo.estatus_adeudo, AdeudoVehicular.EstatusAdeudo.PAGADO)

        otro = AdeudoVehicular.objects.create(
            vehiculo=self.vehiculo,
            tipo_adeudo="Otra multa",
            estatus_adeudo=AdeudoVehicular.EstatusAdeudo.PENDIENTE,
        )
        url_cancelar = reverse("vehiculos:adeudo_cancelar", args=[self.vehiculo.pk, otro.pk])
        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url_cancelar).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(url_cancelar)
        otro.refresh_from_db()
        self.assertEqual(otro.estatus_adeudo, AdeudoVehicular.EstatusAdeudo.CANCELADO)

    def test_documentos_poliza(self):
        url = reverse("vehiculos:poliza_nueva", args=[self.vehiculo.pk])
        datos = {
            "aseguradora": self.aseguradora.pk,
            "titular_poliza": "",
            "numero_poliza": "POL-PERM-1",
            "fecha_vigencia_inicio": "",
            "fecha_vigencia_fin": (localdate().replace(year=localdate().year + 1)).isoformat(),
            "importe_prima": "",
        }

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(self.vehiculo.polizas.filter(numero_poliza="POL-PERM-1").exists())

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.assertTrue(self.vehiculo.polizas.filter(numero_poliza="POL-PERM-1").exists())

    def test_instalar_y_retirar_gps(self):
        url = reverse("vehiculos:gps_instalar", args=[self.vehiculo.pk])
        datos = {"gps": self.gps.pk, "fecha_instalacion": ""}

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(self.vehiculo.instalaciones_gps.exists())

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.assertTrue(self.vehiculo.instalaciones_gps.filter(fecha_retiro__isnull=True).exists())

        url_retirar = reverse("vehiculos:gps_retirar", args=[self.vehiculo.pk])
        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url_retirar).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(url_retirar)
        self.assertFalse(self.vehiculo.instalaciones_gps.filter(fecha_retiro__isnull=True).exists())

    def test_asignar_y_retirar_tag(self):
        url = reverse("vehiculos:tag_asignar", args=[self.vehiculo.pk])
        datos = {"tag": self.tag.pk, "fecha_inicio": ""}

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(self.vehiculo.asignaciones_tag.exists())

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.assertTrue(self.vehiculo.asignaciones_tag.filter(fecha_fin__isnull=True).exists())

        url_retirar = reverse("vehiculos:tag_retirar", args=[self.vehiculo.pk])
        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url_retirar).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(url_retirar)
        self.assertFalse(self.vehiculo.asignaciones_tag.filter(fecha_fin__isnull=True).exists())

    def test_alta_de_conductor(self):
        url = reverse("actores:conductor_nuevo")
        datos = {
            "nombre_completo": "Conductor Nuevo Permisos",
            "telefono": "",
            "correo": "",
            "estatus_conductor": Conductor.Estatus.ACTIVO,
            "numero_licencia": "",
            "tipo_licencia": "",
            "fecha_vencimiento_licencia": "",
            "curp": "",
            "referencias-TOTAL_FORMS": "1",
            "referencias-INITIAL_FORMS": "0",
            "referencias-MIN_NUM_FORMS": "1",
            "referencias-MAX_NUM_FORMS": "1000",
            "referencias-0-nombre": "Referencia Alta",
            "referencias-0-domicilio": "Calle Falsa 456",
            "referencias-0-telefono_contacto": "55 1111 2222",
            "referencias-0-parentesco": "MADRE",
        }

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(Conductor.objects.filter(nombre_completo="Conductor Nuevo Permisos").exists())

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.assertTrue(Conductor.objects.filter(nombre_completo="Conductor Nuevo Permisos").exists())

    def test_alta_de_dispositivos(self):
        url = reverse("dispositivos:gps_nuevo")
        datos = {"imei": "356789100000999", "numero_gps": "", "estatus_gps": DispositivoGps.Estatus.ACTIVO}

        self.client.force_login(self.consulta)
        self.assertEqual(self.client.post(url, datos).status_code, 403)
        self.assertFalse(DispositivoGps.objects.filter(imei="356789100000999").exists())

        self.client.force_login(self.operador)
        self.client.post(url, datos)
        self.assertTrue(DispositivoGps.objects.filter(imei="356789100000999").exists())


# ---------------------------------------------------------------------------
# Exportaciones
# ---------------------------------------------------------------------------

class ExportacionPorRolTests(BasePermisosTests):
    def test_los_tres_roles_pueden_exportar(self):
        """Política de la fase: exportar es una operación de lectura."""
        for usuario in (self.admin, self.operador, self.consulta):
            self.client.force_login(usuario)
            for url in self.urls_exportacion():
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f"{usuario.rol} {url}")
                self.assertIn("spreadsheetml", resp["Content-Type"])

    def test_exportar_requiere_sesion(self):
        for url in self.urls_exportacion():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, url)
            self.assertIn("/accounts/login/", resp["Location"])


# ---------------------------------------------------------------------------
# Interfaz según rol
# ---------------------------------------------------------------------------

class BotonesSegunRolTests(BasePermisosTests):
    def test_consulta_no_ve_botones_de_escritura_en_el_listado(self):
        url = reverse("vehiculos:lista")
        url_nuevo = reverse("vehiculos:nuevo")

        self.client.force_login(self.consulta)
        resp = self.client.get(url)
        self.assertNotContains(resp, url_nuevo)
        # Exportar sí lo ve: la política lo permite.
        self.assertContains(resp, reverse("vehiculos:exportar_lista"))

        for usuario in (self.admin, self.operador):
            self.client.force_login(usuario)
            self.assertContains(self.client.get(url), url_nuevo)

    def test_consulta_no_ve_acciones_en_la_ficha_del_vehiculo(self):
        url = reverse("vehiculos:detalle", args=[self.vehiculo.pk])
        acciones = [
            reverse("vehiculos:editar", args=[self.vehiculo.pk]),
            reverse("vehiculos:nueva_placa", args=[self.vehiculo.pk]),
            reverse("vehiculos:asignar_conductor", args=[self.vehiculo.pk]),
            reverse("vehiculos:poliza_nueva", args=[self.vehiculo.pk]),
            reverse("vehiculos:adeudo_nuevo", args=[self.vehiculo.pk]),
            reverse("vehiculos:observacion_nueva", args=[self.vehiculo.pk]),
            reverse("vehiculos:gps_instalar", args=[self.vehiculo.pk]),
            reverse("vehiculos:tag_asignar", args=[self.vehiculo.pk]),
            reverse("vehiculos:cambiar_estatus", args=[self.vehiculo.pk]),
            reverse("vehiculos:adeudo_pagar", args=[self.vehiculo.pk, self.adeudo.pk]),
        ]

        self.client.force_login(self.consulta)
        resp = self.client.get(url)
        for accion in acciones:
            self.assertNotContains(resp, accion)

        self.client.force_login(self.operador)
        resp = self.client.get(url)
        for accion in acciones:
            self.assertContains(resp, accion)

    def test_consulta_no_ve_botones_en_conductores_ni_dispositivos(self):
        self.client.force_login(self.consulta)

        resp = self.client.get(reverse("actores:conductores_lista"))
        self.assertNotContains(resp, reverse("actores:conductor_nuevo"))
        self.assertNotContains(resp, reverse("actores:conductor_editar", args=[self.conductor.pk]))

        resp = self.client.get(reverse("dispositivos:gps_lista"))
        self.assertNotContains(resp, reverse("dispositivos:gps_nuevo"))

        resp = self.client.get(reverse("dispositivos:tag_detalle", args=[self.tag.pk]))
        self.assertNotContains(resp, reverse("dispositivos:tag_editar", args=[self.tag.pk]))

    def test_rol_legible_visible_en_el_menu_de_usuario(self):
        url = reverse("vehiculos:dashboard")
        for usuario, etiqueta in (
            (self.admin, "Administrador"),
            (self.operador, "Operador"),
            (self.consulta, "Consulta (solo lectura)"),
        ):
            self.client.force_login(usuario)
            self.assertContains(self.client.get(url), etiqueta)
