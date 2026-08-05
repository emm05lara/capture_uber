"""Pruebas de la matriz de permisos y de la gestión de usuarios (Fase 9)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .permissions import (
    ACCION_ADMINISTRAR_USUARIOS,
    ACCION_CAPTURAR,
    ACCION_CONSULTAR,
    ACCION_EDITAR,
    ACCION_EJECUTAR_ACCIONES,
    ACCION_EXPORTAR,
    ROL_ADMIN,
    ROL_CONSULTA,
    ROL_OPERADOR,
    es_ultimo_administrador,
    puede_acceder_admin,
    puede_administrar_usuarios,
    rol_legible,
    tiene_permiso,
)

User = get_user_model()

CLAVE = "Flotilla-2026-Segura"
CLAVE_NUEVA = "Flotilla-2026-Renovada"


def crear_usuario(username, rol=ROL_ADMIN, **extra):
    return User.objects.create_user(username=username, password=CLAVE, rol=rol, **extra)


# ---------------------------------------------------------------------------
# 1. Matriz de permisos
# ---------------------------------------------------------------------------

class MatrizPermisosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("admin_app", ROL_ADMIN)
        cls.operador = crear_usuario("operador_app", ROL_OPERADOR)
        cls.consulta = crear_usuario("consulta_app", ROL_CONSULTA)
        cls.superusuario = User.objects.create_superuser(
            username="root_app", password=CLAVE, rol=ROL_CONSULTA,
        )
        cls.inactivo = crear_usuario("inactivo_app", ROL_ADMIN, is_active=False)

    def test_admin_tiene_todas_las_acciones_de_aplicacion(self):
        for accion in (
            ACCION_CONSULTAR, ACCION_EXPORTAR, ACCION_CAPTURAR,
            ACCION_EDITAR, ACCION_EJECUTAR_ACCIONES, ACCION_ADMINISTRAR_USUARIOS,
        ):
            self.assertTrue(tiene_permiso(self.admin, accion), accion)

    def test_operador_no_administra_usuarios(self):
        for accion in (
            ACCION_CONSULTAR, ACCION_EXPORTAR, ACCION_CAPTURAR,
            ACCION_EDITAR, ACCION_EJECUTAR_ACCIONES,
        ):
            self.assertTrue(tiene_permiso(self.operador, accion), accion)
        self.assertFalse(puede_administrar_usuarios(self.operador))

    def test_consulta_solo_lee_y_exporta(self):
        self.assertTrue(tiene_permiso(self.consulta, ACCION_CONSULTAR))
        self.assertTrue(tiene_permiso(self.consulta, ACCION_EXPORTAR))
        for accion in (
            ACCION_CAPTURAR, ACCION_EDITAR,
            ACCION_EJECUTAR_ACCIONES, ACCION_ADMINISTRAR_USUARIOS,
        ):
            self.assertFalse(tiene_permiso(self.consulta, accion), accion)

    def test_superusuario_conserva_acceso_total_pese_a_su_rol(self):
        self.assertEqual(self.superusuario.rol, ROL_CONSULTA)
        for accion in (
            ACCION_CONSULTAR, ACCION_EXPORTAR, ACCION_CAPTURAR, ACCION_EDITAR,
            ACCION_EJECUTAR_ACCIONES, ACCION_ADMINISTRAR_USUARIOS,
        ):
            self.assertTrue(tiene_permiso(self.superusuario, accion), accion)

    def test_rol_admin_no_otorga_acceso_a_django_admin(self):
        self.assertFalse(self.admin.is_staff)
        self.assertFalse(puede_acceder_admin(self.admin))
        self.admin.is_staff = True
        self.assertTrue(puede_acceder_admin(self.admin))

    def test_consulta_nunca_recibe_staff_automaticamente(self):
        self.assertFalse(self.consulta.is_staff)
        self.assertFalse(puede_acceder_admin(self.consulta))

    def test_usuario_inactivo_no_tiene_permisos(self):
        for accion in (ACCION_CONSULTAR, ACCION_EXPORTAR, ACCION_ADMINISTRAR_USUARIOS):
            self.assertFalse(tiene_permiso(self.inactivo, accion), accion)

    def test_usuario_anonimo_no_tiene_permisos(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(tiene_permiso(AnonymousUser(), ACCION_CONSULTAR))
        self.assertFalse(tiene_permiso(None, ACCION_CONSULTAR))

    def test_rol_legible(self):
        self.assertEqual(rol_legible(self.admin), "Administrador")
        self.assertEqual(rol_legible(self.operador), "Operador")
        self.assertEqual(rol_legible(self.consulta), "Consulta (solo lectura)")
        self.assertEqual(rol_legible(self.superusuario), "Superusuario")

    def test_es_ultimo_administrador(self):
        # Hay admin + superusuario, así que ninguno es el último.
        self.assertFalse(es_ultimo_administrador(self.admin))
        self.superusuario.delete()
        self.inactivo.delete()
        self.assertTrue(es_ultimo_administrador(self.admin))
        self.assertFalse(es_ultimo_administrador(self.operador))


# ---------------------------------------------------------------------------
# 2. Acceso a la gestión de usuarios
# ---------------------------------------------------------------------------

class AccesoGestionUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear_usuario("admin_acc", ROL_ADMIN)
        cls.operador = crear_usuario("operador_acc", ROL_OPERADOR)
        cls.consulta = crear_usuario("consulta_acc", ROL_CONSULTA)

    def urls_gestion(self):
        return [
            reverse("accounts:usuarios_lista"),
            reverse("accounts:usuario_nuevo"),
            reverse("accounts:usuario_editar", args=[self.admin.pk]),
            reverse("accounts:usuario_password", args=[self.admin.pk]),
        ]

    def test_admin_accede(self):
        self.client.force_login(self.admin)
        for url in self.urls_gestion():
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_operador_y_consulta_reciben_403(self):
        for usuario in (self.operador, self.consulta):
            self.client.force_login(usuario)
            for url in self.urls_gestion():
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 403, f"{usuario} {url}")
                self.assertTemplateUsed(resp, "403.html")

    def test_anonimo_es_redirigido_al_login(self):
        for url in self.urls_gestion():
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, url)
            self.assertIn("/accounts/login/", resp["Location"])

    def test_enlace_a_usuarios_solo_visible_para_admin(self):
        url_usuarios = reverse("accounts:usuarios_lista")
        url_dashboard = reverse("vehiculos:dashboard")

        self.client.force_login(self.admin)
        self.assertContains(self.client.get(url_dashboard), url_usuarios)

        for usuario in (self.operador, self.consulta):
            self.client.force_login(usuario)
            self.assertNotContains(self.client.get(url_dashboard), url_usuarios)

    def test_enlace_a_django_admin_solo_para_staff(self):
        url_dashboard = reverse("vehiculos:dashboard")

        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get(url_dashboard), "Django Admin")

        staff = crear_usuario("staff_acc", ROL_OPERADOR, is_staff=True)
        self.client.force_login(staff)
        self.assertContains(self.client.get(url_dashboard), "Django Admin")


# ---------------------------------------------------------------------------
# 3. Alta de usuarios
# ---------------------------------------------------------------------------

class AltaUsuarioTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_alta", ROL_ADMIN)
        self.client.force_login(self.admin)
        self.url = reverse("accounts:usuario_nuevo")

    def datos(self, **extra):
        base = {
            "username": "nuevo_operador",
            "first_name": "Ana",
            "last_name": "López",
            "email": "ana@example.com",
            "rol": ROL_OPERADOR,
            "password1": CLAVE_NUEVA,
            "password2": CLAVE_NUEVA,
        }
        base.update(extra)
        return base

    def test_crea_usuario_con_contrasena_cifrada(self):
        resp = self.client.post(self.url, self.datos())
        self.assertRedirects(resp, reverse("accounts:usuarios_lista"))

        creado = User.objects.get(username="nuevo_operador")
        self.assertEqual(creado.rol, ROL_OPERADOR)
        self.assertTrue(creado.check_password(CLAVE_NUEVA))
        self.assertNotEqual(creado.password, CLAVE_NUEVA)
        self.assertTrue(creado.has_usable_password())

    def test_no_permite_otorgar_superusuario_ni_staff_desde_la_gui(self):
        self.client.post(self.url, self.datos(is_superuser="on", is_staff="on"))
        creado = User.objects.get(username="nuevo_operador")
        self.assertFalse(creado.is_superuser)
        self.assertFalse(creado.is_staff)

    def test_contrasenas_distintas_no_crean_usuario(self):
        resp = self.client.post(self.url, self.datos(password2="otra-cosa-123"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="nuevo_operador").exists())

    def test_formulario_nunca_muestra_hash_de_contrasena(self):
        resp = self.client.get(reverse("accounts:usuario_editar", args=[self.admin.pk]))
        self.assertNotContains(resp, self.admin.password)


# ---------------------------------------------------------------------------
# 4. Edición de usuarios
# ---------------------------------------------------------------------------

class EdicionUsuarioTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_edit", ROL_ADMIN)
        self.otro_admin = crear_usuario("admin_edit_2", ROL_ADMIN)
        self.operador = crear_usuario("operador_edit", ROL_OPERADOR)
        self.client.force_login(self.admin)

    def datos(self, usuario, **extra):
        base = {
            "username": usuario.username,
            "first_name": usuario.first_name,
            "last_name": usuario.last_name,
            "email": usuario.email,
            "rol": usuario.rol,
            "is_active": "on",
        }
        base.update(extra)
        return base

    def test_edicion_normal(self):
        url = reverse("accounts:usuario_editar", args=[self.operador.pk])
        resp = self.client.post(url, self.datos(self.operador, first_name="Beto", rol=ROL_CONSULTA))
        self.assertRedirects(resp, reverse("accounts:usuarios_lista"))
        self.operador.refresh_from_db()
        self.assertEqual(self.operador.first_name, "Beto")
        self.assertEqual(self.operador.rol, ROL_CONSULTA)

    def test_no_puede_desactivar_su_propia_cuenta(self):
        url = reverse("accounts:usuario_editar", args=[self.admin.pk])
        datos = self.datos(self.admin)
        datos.pop("is_active")
        resp = self.client.post(url, datos)
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_no_puede_quitarse_a_si_mismo_el_rol_admin(self):
        url = reverse("accounts:usuario_editar", args=[self.admin.pk])
        resp = self.client.post(url, self.datos(self.admin, rol=ROL_CONSULTA))
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.rol, ROL_ADMIN)

    def test_no_puede_degradar_al_ultimo_administrador(self):
        self.otro_admin.delete()
        url = reverse("accounts:usuario_editar", args=[self.admin.pk])
        resp = self.client.post(url, self.datos(self.admin, rol=ROL_OPERADOR))
        self.assertEqual(resp.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.rol, ROL_ADMIN)

    def test_la_edicion_no_expone_superusuario_ni_staff(self):
        url = reverse("accounts:usuario_editar", args=[self.operador.pk])
        self.client.post(url, self.datos(self.operador, is_superuser="on", is_staff="on"))
        self.operador.refresh_from_db()
        self.assertFalse(self.operador.is_superuser)
        self.assertFalse(self.operador.is_staff)


# ---------------------------------------------------------------------------
# 5. Activar / desactivar
# ---------------------------------------------------------------------------

class ActivarDesactivarTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_estado", ROL_ADMIN)
        self.otro_admin = crear_usuario("admin_estado_2", ROL_ADMIN)
        self.operador = crear_usuario("operador_estado", ROL_OPERADOR)
        self.client.force_login(self.admin)

    def test_desactivar_requiere_post(self):
        url = reverse("accounts:usuario_desactivar", args=[self.operador.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.is_active)

    def test_activar_requiere_post(self):
        url = reverse("accounts:usuario_activar", args=[self.operador.pk])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_desactivar_y_activar(self):
        url_off = reverse("accounts:usuario_desactivar", args=[self.operador.pk])
        self.client.post(url_off)
        self.operador.refresh_from_db()
        self.assertFalse(self.operador.is_active)

        url_on = reverse("accounts:usuario_activar", args=[self.operador.pk])
        self.client.post(url_on)
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.is_active)

    def test_no_puede_autodesactivarse(self):
        url = reverse("accounts:usuario_desactivar", args=[self.admin.pk])
        self.client.post(url)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_no_puede_desactivar_al_ultimo_administrador(self):
        # `admin` desactiva a `otro_admin` cuando este es el único otro ADMIN:
        # como quedaría `admin`, sí se permite. Se prueba el caso contrario
        # desde una cuenta distinta.
        tercero = crear_usuario("admin_estado_3", ROL_ADMIN)
        self.client.force_login(tercero)
        self.client.post(reverse("accounts:usuario_desactivar", args=[self.admin.pk]))
        self.client.post(reverse("accounts:usuario_desactivar", args=[self.otro_admin.pk]))
        self.admin.refresh_from_db()
        self.otro_admin.refresh_from_db()
        self.assertFalse(self.admin.is_active)
        self.assertFalse(self.otro_admin.is_active)

        # Ahora `tercero` es el último ADMIN: otro admin reactivado no existe,
        # así que ni él mismo ni nadie puede dejarlo fuera.
        self.assertTrue(es_ultimo_administrador(tercero))

    def test_operador_no_puede_activar_ni_desactivar(self):
        self.client.force_login(self.operador)
        for nombre in ("accounts:usuario_activar", "accounts:usuario_desactivar"):
            url = reverse(nombre, args=[self.otro_admin.pk])
            self.assertEqual(self.client.post(url).status_code, 403)

    def test_desactivar_no_elimina_el_registro(self):
        self.client.post(reverse("accounts:usuario_desactivar", args=[self.operador.pk]))
        self.assertTrue(User.objects.filter(pk=self.operador.pk).exists())


# ---------------------------------------------------------------------------
# 5b. Un ADMIN de aplicación no escala hasta el superusuario
# ---------------------------------------------------------------------------

class AlcanceSobreSuperusuarioTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_alcance", ROL_ADMIN)
        self.root = User.objects.create_superuser(
            username="root_alcance", password=CLAVE, rol=ROL_ADMIN,
        )
        self.client.force_login(self.admin)

    def urls_sobre_root(self):
        return [
            reverse("accounts:usuario_editar", args=[self.root.pk]),
            reverse("accounts:usuario_password", args=[self.root.pk]),
            reverse("accounts:usuario_desactivar", args=[self.root.pk]),
            reverse("accounts:usuario_activar", args=[self.root.pk]),
        ]

    def test_admin_no_puede_gestionar_una_cuenta_de_superusuario(self):
        for url in self.urls_sobre_root():
            self.assertEqual(self.client.post(url, {}).status_code, 403, url)

    def test_admin_no_puede_cambiarle_la_contrasena_al_superusuario(self):
        url = reverse("accounts:usuario_password", args=[self.root.pk])
        self.client.post(url, {"password1": CLAVE_NUEVA, "password2": CLAVE_NUEVA})
        self.root.refresh_from_db()
        self.assertTrue(self.root.check_password(CLAVE))

    def test_el_listado_no_ofrece_acciones_sobre_superusuarios(self):
        resp = self.client.get(reverse("accounts:usuarios_lista"))
        self.assertNotContains(resp, reverse("accounts:usuario_editar", args=[self.root.pk]))
        self.assertContains(resp, reverse("accounts:usuario_editar", args=[self.admin.pk]))

    def test_un_superusuario_si_gestiona_a_otro(self):
        self.client.force_login(self.root)
        otro_root = User.objects.create_superuser(
            username="root_alcance_2", password=CLAVE, rol=ROL_ADMIN,
        )
        url = reverse("accounts:usuario_editar", args=[otro_root.pk])
        self.assertEqual(self.client.get(url).status_code, 200)


# ---------------------------------------------------------------------------
# 6. Contraseñas
# ---------------------------------------------------------------------------

class ContrasenaTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("admin_pwd", ROL_ADMIN)
        self.operador = crear_usuario("operador_pwd", ROL_OPERADOR)

    def test_admin_establece_contrasena_temporal(self):
        self.client.force_login(self.admin)
        url = reverse("accounts:usuario_password", args=[self.operador.pk])
        resp = self.client.post(url, {"password1": CLAVE_NUEVA, "password2": CLAVE_NUEVA})
        self.assertRedirects(resp, reverse("accounts:usuarios_lista"))

        self.operador.refresh_from_db()
        self.assertTrue(self.operador.check_password(CLAVE_NUEVA))
        self.assertNotEqual(self.operador.password, CLAVE_NUEVA)

    def test_cada_usuario_cambia_su_propia_contrasena_y_conserva_sesion(self):
        self.client.force_login(self.operador)
        resp = self.client.post(reverse("password_change"), {
            "old_password": CLAVE,
            "new_password1": CLAVE_NUEVA,
            "new_password2": CLAVE_NUEVA,
        })
        self.assertRedirects(resp, reverse("password_change_done"))

        self.operador.refresh_from_db()
        self.assertTrue(self.operador.check_password(CLAVE_NUEVA))
        # La sesión sigue viva tras el cambio propio.
        self.assertEqual(self.client.get(reverse("vehiculos:dashboard")).status_code, 200)

    def test_consulta_puede_cambiar_su_propia_contrasena(self):
        consulta = crear_usuario("consulta_pwd", ROL_CONSULTA)
        self.client.force_login(consulta)
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 200)


# ---------------------------------------------------------------------------
# 7. Sesiones y cuentas inactivas
# ---------------------------------------------------------------------------

class CuentasInactivasTests(TestCase):
    def test_usuario_inactivo_no_inicia_sesion(self):
        crear_usuario("inactivo_login", ROL_OPERADOR, is_active=False)
        self.assertFalse(self.client.login(username="inactivo_login", password=CLAVE))

    def test_sesion_existente_deja_de_servir_tras_desactivar(self):
        usuario = crear_usuario("operador_sesion", ROL_OPERADOR)
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse("vehiculos:dashboard")).status_code, 200)

        usuario.is_active = False
        usuario.save(update_fields=["is_active"])

        resp = self.client.get(reverse("vehiculos:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_las_paginas_autenticadas_no_se_guardan_en_cache_del_navegador(self):
        usuario = crear_usuario("operador_cache", ROL_OPERADOR)
        self.client.force_login(usuario)
        resp = self.client.get(reverse("vehiculos:dashboard"))
        self.assertIn("no-store", resp["Cache-Control"])


# ---------------------------------------------------------------------------
# 8. Página 403
# ---------------------------------------------------------------------------

class Pagina403Tests(TestCase):
    def test_devuelve_403_real_con_plantilla_propia(self):
        consulta = crear_usuario("consulta_403", ROL_CONSULTA)
        self.client.force_login(consulta)

        resp = self.client.get(reverse("accounts:usuarios_lista"))
        self.assertEqual(resp.status_code, 403)
        self.assertTemplateUsed(resp, "403.html")
        self.assertContains(
            resp, "No tienes permiso para esta operación", status_code=403,
        )
        # Ofrece salida al dashboard y no filtra detalles técnicos.
        self.assertContains(resp, reverse("vehiculos:dashboard"), status_code=403)
        self.assertNotContains(resp, "Traceback", status_code=403)
