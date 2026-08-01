from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Conductor, ReferenciaConductor

User = get_user_model()


def datos_conductor(**overrides):
    """Payload en formato de formulario (POST): los campos opcionales se
    envían como cadena vacía, tal como lo hace un <input> HTML sin llenar.
    El formulario se encarga de normalizarlos a None antes de guardar.
    No usar esta función para crear objetos directamente vía el ORM
    (usar crear_conductor en su lugar): el ORM no pasa por esa limpieza y
    "" no es un valor válido para una fecha ni para un choice con
    restricción CHECK en base de datos.
    """
    datos = {
        "nombre_completo": "Juan Pérez López",
        "telefono": "",
        "correo": "",
        "estatus_conductor": Conductor.Estatus.ACTIVO,
        "numero_licencia": "",
        "tipo_licencia": "",
        "fecha_vencimiento_licencia": "",
        "curp": "",
    }
    datos.update(overrides)
    return datos


def crear_conductor(**overrides):
    """Crea un Conductor directamente vía el ORM, con los campos opcionales
    en None (no ""), que es el valor correcto para saltarse el formulario.
    """
    datos = {
        "nombre_completo": "Juan Pérez López",
        "telefono": None,
        "correo": None,
        "estatus_conductor": Conductor.Estatus.ACTIVO,
        "numero_licencia": None,
        "tipo_licencia": None,
        "fecha_vencimiento_licencia": None,
        "curp": None,
    }
    datos.update(overrides)
    return Conductor.objects.create(**datos)


def datos_formset_referencias(referencias, total_forms=None, initial_forms=0):
    if total_forms is None:
        total_forms = len(referencias)
    datos = {
        "referencias-TOTAL_FORMS": str(total_forms),
        "referencias-INITIAL_FORMS": str(initial_forms),
        "referencias-MIN_NUM_FORMS": "1",
        "referencias-MAX_NUM_FORMS": "1000",
    }
    for i, ref in enumerate(referencias):
        prefix = f"referencias-{i}"
        datos[f"{prefix}-id"] = ref.get("id", "")
        datos[f"{prefix}-nombre"] = ref.get("nombre", "")
        datos[f"{prefix}-domicilio"] = ref.get("domicilio", "")
        datos[f"{prefix}-telefono_contacto"] = ref.get("telefono_contacto", "")
        datos[f"{prefix}-parentesco"] = ref.get("parentesco", "")
        if ref.get("DELETE"):
            datos[f"{prefix}-DELETE"] = "on"
    return datos


class ReferenciaConductorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="operador", password="clave-segura-123")
        self.client.login(username="operador", password="clave-segura-123")

    def test_login_required_en_vistas_de_conductor(self):
        self.client.logout()
        url_lista = reverse("actores:conductores_lista")
        url_nuevo = reverse("actores:conductor_nuevo")

        resp_lista = self.client.get(url_lista)
        resp_nuevo = self.client.get(url_nuevo)

        self.assertEqual(resp_lista.status_code, 302)
        self.assertIn("/login", resp_lista.url)
        self.assertEqual(resp_nuevo.status_code, 302)
        self.assertIn("/login", resp_nuevo.url)

    def test_crear_conductor_con_una_referencia(self):
        url = reverse("actores:conductor_nuevo")
        payload = datos_conductor()
        payload.update(datos_formset_referencias([
            {
                "nombre": "Rosa Gómez Pérez",
                "domicilio": "Calle Falsa 123, Col. Centro",
                "telefono_contacto": "55 1234 5678",
                "parentesco": "MADRE",
            },
        ]))

        resp = self.client.post(url, payload)

        self.assertEqual(Conductor.objects.count(), 1)
        conductor = Conductor.objects.get()
        self.assertEqual(conductor.referencias.count(), 1)
        self.assertRedirects(resp, reverse("actores:conductor_detalle", args=[conductor.pk]))

    def test_rechaza_creacion_de_conductor_sin_referencias(self):
        url = reverse("actores:conductor_nuevo")
        payload = datos_conductor()
        payload.update(datos_formset_referencias([]))

        resp = self.client.post(url, payload)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Conductor.objects.count(), 0)

    def test_crear_conductor_con_varias_referencias(self):
        url = reverse("actores:conductor_nuevo")
        payload = datos_conductor()
        payload.update(datos_formset_referencias([
            {
                "nombre": "Rosa Gómez Pérez",
                "domicilio": "Calle Falsa 123",
                "telefono_contacto": "55 1234 5678",
                "parentesco": "MADRE",
            },
            {
                "nombre": "Pedro Gómez Pérez",
                "domicilio": "Calle Falsa 123",
                "telefono_contacto": "55 8765 4321",
                "parentesco": "HERMANO_A",
            },
        ]))

        self.client.post(url, payload)

        conductor = Conductor.objects.get()
        self.assertEqual(conductor.referencias.count(), 2)

    def test_editar_referencia_existente(self):
        conductor = crear_conductor()
        referencia = ReferenciaConductor.objects.create(
            conductor=conductor,
            nombre="Rosa Gómez Pérez",
            domicilio="Calle Falsa 123",
            telefono_contacto="55 1234 5678",
            parentesco="MADRE",
        )

        url = reverse("actores:conductor_editar", args=[conductor.pk])
        payload = datos_conductor()
        payload.update(datos_formset_referencias(
            [{
                "id": referencia.pk,
                "nombre": "Rosa Gómez Pérez (actualizada)",
                "domicilio": "Nueva dirección 456",
                "telefono_contacto": "55 0000 0000",
                "parentesco": "MADRE",
            }],
            initial_forms=1,
        ))

        self.client.post(url, payload)

        referencia.refresh_from_db()
        self.assertEqual(referencia.nombre, "Rosa Gómez Pérez (actualizada)")
        self.assertEqual(referencia.domicilio, "Nueva dirección 456")

    def test_no_permite_eliminar_la_ultima_referencia(self):
        conductor = crear_conductor()
        referencia = ReferenciaConductor.objects.create(
            conductor=conductor,
            nombre="Rosa Gómez Pérez",
            domicilio="Calle Falsa 123",
            telefono_contacto="55 1234 5678",
            parentesco="MADRE",
        )

        url = reverse("actores:conductor_editar", args=[conductor.pk])
        payload = datos_conductor()
        payload.update(datos_formset_referencias(
            [{
                "id": referencia.pk,
                "nombre": referencia.nombre,
                "domicilio": referencia.domicilio,
                "telefono_contacto": referencia.telefono_contacto,
                "parentesco": referencia.parentesco,
                "DELETE": True,
            }],
            initial_forms=1,
        ))

        resp = self.client.post(url, payload)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(ReferenciaConductor.objects.filter(pk=referencia.pk).exists())

    def test_eliminacion_en_cascada_al_borrar_conductor(self):
        conductor = crear_conductor()
        referencia = ReferenciaConductor.objects.create(
            conductor=conductor,
            nombre="Rosa Gómez Pérez",
            domicilio="Calle Falsa 123",
            telefono_contacto="55 1234 5678",
            parentesco="MADRE",
        )

        conductor.delete()

        self.assertFalse(ReferenciaConductor.objects.filter(pk=referencia.pk).exists())

    def test_no_permite_editar_referencia_de_otro_conductor(self):
        conductor_a = crear_conductor(nombre_completo="Conductor A")
        conductor_b = crear_conductor(nombre_completo="Conductor B")
        referencia_a = ReferenciaConductor.objects.create(
            conductor=conductor_a,
            nombre="Referencia de A",
            domicilio="Domicilio A",
            telefono_contacto="55 1111 1111",
            parentesco="MADRE",
        )
        ReferenciaConductor.objects.create(
            conductor=conductor_b,
            nombre="Referencia de B",
            domicilio="Domicilio B",
            telefono_contacto="55 2222 2222",
            parentesco="PADRE",
        )

        # Intento de editar la página de conductor_b enviando el id de la
        # referencia de conductor_a (manipulación de la URL/datos del formset).
        url = reverse("actores:conductor_editar", args=[conductor_b.pk])
        payload = datos_conductor(nombre_completo=conductor_b.nombre_completo)
        payload.update(datos_formset_referencias(
            [{
                "id": referencia_a.pk,
                "nombre": "Nombre modificado indebidamente",
                "domicilio": "Domicilio A",
                "telefono_contacto": "55 1111 1111",
                "parentesco": "MADRE",
            }],
            initial_forms=1,
        ))

        self.client.post(url, payload)

        referencia_a.refresh_from_db()
        self.assertEqual(referencia_a.nombre, "Referencia de A")
        self.assertEqual(referencia_a.conductor_id, conductor_a.pk)
