"""
Management command: seed_demo_data
Carga datos de prueba ficticios para validar dashboard, listado y detalle.

Uso:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --reset   # elimina datos demo antes de recrear

Es idempotente: usa get_or_create con claves estables.
No crea contraseñas ni usuarios sensibles.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import localdate

from actores.models import Aseguradora, Conductor, PlataformaOperativa, Socio, TitularPoliza
from catalogos.models import AppTransporte, Color, EntidadFederativa, Marca, ModeloVehiculo
from dispositivos.models import AsignacionTag, DispositivoGps, InstalacionGps, TagTelepeaje
from operacion.models import AsignacionApp, AsignacionVehiculo
from vehiculos.models import (
    AdeudoVehicular,
    Emplacamiento,
    Observacion,
    PolizaSeguro,
    Tenencia,
    TarjetaCirculacion,
    VerificacionVehicular,
    Vehiculo,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Carga datos de prueba ficticios para el sistema de flotilla"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina los datos demo antes de volver a crearlos",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        hoy = localdate()
        verde = hoy + timedelta(days=180)    # documentos vigentes → semáforo VERDE
        amarillo = hoy + timedelta(days=15)  # vencen en 15 días → semáforo AMARILLO
        rojo = hoy - timedelta(days=30)      # ya vencidos → semáforo ROJO

        with transaction.atomic():
            self._paso("Catálogos")
            marcas = self._marcas()
            colores = self._colores()
            entidades = self._entidades()
            apps = self._apps()

            self._paso("Organizaciones")
            plataformas = self._plataformas()
            socios = self._socios()
            aseguradoras = self._aseguradoras()

            self._paso("Conductores")
            conductores = self._conductores()

            self._paso("Vehículos")
            vehiculos = self._vehiculos(marcas, colores)

            self._paso("Emplacamientos")
            emplacamientos = self._emplacamientos(vehiculos, entidades)

            self._paso("Asignaciones")
            asignaciones = self._asignaciones(vehiculos, conductores, plataformas, socios, apps)

            self._paso("Documentación")
            titular = self._titular_poliza()
            self._polizas(vehiculos, aseguradoras, titular, verde, amarillo, rojo)
            self._verificaciones(vehiculos, emplacamientos, verde, amarillo)
            self._tarjetas(vehiculos, emplacamientos, verde, rojo)
            self._tenencias(vehiculos, hoy)

            self._paso("Adeudos")
            self._adeudos(vehiculos)

            self._paso("GPS y TAG")
            self._gps_y_tag(vehiculos, hoy)

            self._paso("Observaciones")
            self._observaciones(vehiculos, asignaciones)

        self.stdout.write(self.style.SUCCESS(
            "\n¡Datos demo cargados exitosamente! "
            "Inicia sesión y verifica dashboard, listado y detalle de vehículos."
        ))

    # ─── Helpers internos ────────────────────────────────────────────────────

    def _paso(self, nombre):
        self.stdout.write(f"  → {nombre}...")

    def _goc(self, model, defaults=None, **kwargs):
        """get_or_create con salida."""
        obj, created = model.objects.get_or_create(defaults=defaults or {}, **kwargs)
        return obj

    def _reset(self):
        self.stdout.write(self.style.WARNING("  Eliminando datos demo previos..."))
        # Elimina por numero_serie prefijado con V-DEMO-
        Vehiculo.objects.filter(numero_serie__startswith="VDEMO").delete()
        # Catálogos demo
        Marca.objects.filter(nombre_marca__in=[
            "Toyota Demo", "Honda Demo", "Chevrolet Demo",
            "Nissan Demo", "Volkswagen Demo", "Hyundai Demo",
        ]).delete()

    # ─── Catálogos ───────────────────────────────────────────────────────────

    def _marcas(self):
        datos = [
            ("Toyota Demo",     "Toyota"),
            ("Honda Demo",      "Honda"),
            ("Chevrolet Demo",  "Chevrolet"),
            ("Nissan Demo",     "Nissan"),
            ("Volkswagen Demo", "Volkswagen"),
            ("Hyundai Demo",    "Hyundai"),
        ]
        marcas = {}
        for nombre, clave in datos:
            m = self._goc(Marca, nombre_marca=nombre)
            marcas[clave] = m
        # Modelos
        modelos_data = [
            ("Toyota",     "Camry",   None),
            ("Toyota",     "RAV4",    None),
            ("Honda",      "CR-V",    None),
            ("Honda",      "Civic",   None),
            ("Chevrolet",  "Tracker", None),
            ("Chevrolet",  "Aveo",    None),
            ("Nissan",     "Versa",   None),
            ("Nissan",     "Sentra",  None),
            ("Volkswagen", "Jetta",   None),
            ("Volkswagen", "Virtus",  None),
            ("Hyundai",    "Tucson",  None),
            ("Hyundai",    "Elantra", None),
        ]
        modelos = {}
        for marca_clave, nombre_modelo, version in modelos_data:
            m = self._goc(
                ModeloVehiculo,
                marca=marcas[marca_clave],
                nombre_modelo_comercial=nombre_modelo,
                version=version,
            )
            modelos[f"{marca_clave}-{nombre_modelo}"] = m
        return {"marcas": marcas, "modelos": modelos}

    def _colores(self):
        datos = [
            ("Blanco",  "BL"),
            ("Negro",   "NG"),
            ("Plata",   "PL"),
            ("Gris",    "GR"),
            ("Rojo",    "RO"),
            ("Azul",    "AZ"),
            ("Beige",   "BE"),
            ("Verde",   "VE"),
        ]
        colores = {}
        for nombre, abr in datos:
            c = self._goc(Color, defaults={"abreviatura_color": abr}, nombre_color=nombre)
            colores[nombre] = c
        return colores

    def _entidades(self):
        datos = [
            ("Ciudad de México",  "CDMX"),
            ("Estado de México",  "EDOMEX"),
            ("Jalisco",           "JAL"),
            ("Nuevo León",        "NL"),
            ("Guanajuato",        "GTO"),
            ("Puebla",            "PUE"),
            ("Querétaro",         "QRO"),
            ("Veracruz",          "VER"),
            ("Aguascalientes",    "AGS"),
            ("Hidalgo",           "HGO"),
        ]
        entidades = {}
        for nombre, abr in datos:
            e = self._goc(
                EntidadFederativa,
                defaults={"abreviatura_entidad": abr},
                nombre_entidad=nombre,
            )
            entidades[abr] = e
        return entidades

    def _apps(self):
        datos = ["Uber", "DiDi", "Cabify"]
        apps = {}
        for nombre in datos:
            a = self._goc(AppTransporte, nombre_app=nombre)
            apps[nombre] = a
        return apps

    # ─── Organizaciones ──────────────────────────────────────────────────────

    def _plataformas(self):
        datos = [
            ("Operadora Flotilla Norte S.A.", "OFN"),
            ("Flotilla Sur S. de R.L.",       "FSR"),
        ]
        result = {}
        for nombre, clave in datos:
            p = self._goc(PlataformaOperativa, defaults={"clave_organizacion": clave}, nombre_organizacion=nombre)
            result[clave] = p
        return result

    def _socios(self):
        datos = [
            ("Arrendadora Movil ABC S.A.",  "ARABC"),
            ("Inversiones Viales XYZ S.A.", "IVXYZ"),
        ]
        result = {}
        for nombre, clave in datos:
            s = self._goc(Socio, defaults={"clave_organizacion": clave}, nombre_organizacion=nombre)
            result[clave] = s
        return result

    def _aseguradoras(self):
        datos = [
            ("AXA Seguros Demo",     "AXA"),
            ("Qualitas Seguros Demo","QUA"),
        ]
        result = {}
        for nombre, clave in datos:
            a = self._goc(Aseguradora, defaults={"clave_organizacion": clave}, nombre_organizacion=nombre)
            result[clave] = a
        return result

    def _titular_poliza(self):
        return self._goc(
            TitularPoliza,
            nombre_completo="Flotilla Demo S.A. de C.V.",
            defaults={"telefono": "55-0000-0000"},
        )

    # ─── Conductores ─────────────────────────────────────────────────────────

    def _conductores(self):
        datos = [
            ("Carlos Mendoza Ruiz",       "ACTIVO",   "B", "55-1111-0001"),
            ("María López Hernández",     "ACTIVO",   "B", "55-1111-0002"),
            ("Roberto García Torres",     "ACTIVO",   "B", "55-1111-0003"),
            ("Ana Martínez Silva",        "ACTIVO",   "B", "55-1111-0004"),
            ("Luis Ramírez Flores",       "ACTIVO",   "B", "55-1111-0005"),
            ("Patricia Sánchez Cruz",     "ACTIVO",   "B", "55-1111-0006"),
            ("Elena Castro Juárez",       "ACTIVO",   "B", "55-1111-0007"),
            ("Diego Morales Vega",        "INACTIVO", "B", "55-1111-0008"),
        ]
        conductores = {}
        for nombre, estatus, tipo_lic, tel in datos:
            c = self._goc(
                Conductor,
                nombre_completo=nombre,
                defaults={
                    "estatus_conductor": estatus,
                    "tipo_licencia": tipo_lic,
                    "telefono": tel,
                },
            )
            conductores[nombre.split()[0]] = c  # índice por primer nombre
        return conductores

    # ─── Vehículos ───────────────────────────────────────────────────────────

    def _vehiculos(self, marcas, colores):
        modelos = marcas["modelos"]
        col = colores
        datos = [
            # (num_interno, VIN,          modelo_key,           anio, color,   estatus)
            ("V-001", "VDEMO1A2B3C4D5E6F7", "Toyota-Camry",     2023, "Blanco",  "ACTIVA"),
            ("V-002", "VDEMO2B3C4D5E6F7A8", "Honda-CR-V",       2024, "Plata",   "ACTIVA"),
            ("V-003", "VDEMO3C4D5E6F7A8B9", "Nissan-Versa",     2023, "Negro",   "ACTIVA"),
            ("V-004", "VDEMO4D5E6F7A8B9C0", "Chevrolet-Tracker", 2024, "Rojo",   "ACTIVA"),
            ("V-005", "VDEMO5E6F7A8B9C0D1", "Volkswagen-Jetta", 2023, "Gris",    "ACTIVA"),
            ("V-006", "VDEMO6F7A8B9C0D1E2", "Hyundai-Tucson",   2023, "Azul",    "ACTIVA"),
            ("V-007", "VDEMO7A8B9C0D1E2F3", "Toyota-RAV4",      2024, "Blanco",  "ACTIVA"),
            ("V-008", "VDEMO8B9C0D1E2F3G4", "Honda-Civic",      2022, "Plata",   "ACTIVA"),
            ("V-009", "VDEMO9C0D1E2F3G4H5", "Nissan-Sentra",    2022, "Beige",   "TALLER"),
            ("V-010", "VDEMO0D1E2F3G4H5I6", "Chevrolet-Aveo",   2023, "Negro",   "SIN_ASIGNAR"),
        ]
        vehiculos = {}
        for num_int, vin, mod_key, anio, color_nom, estatus in datos:
            v, created = Vehiculo.objects.get_or_create(
                numero_serie=vin,
                defaults={
                    "numero_interno": num_int,
                    "modelo_vehiculo": modelos[mod_key],
                    "anio_modelo": anio,
                    "color": col[color_nom],
                    "estatus_unidad": estatus,
                },
            )
            vehiculos[num_int] = v
        return vehiculos

    # ─── Emplacamientos ──────────────────────────────────────────────────────

    def _emplacamientos(self, vehiculos, entidades):
        datos = [
            # (num_int_veh, placas,      entidad_abr)
            ("V-001", "AAA-000-A",  "CDMX"),
            ("V-002", "BBB-111-B",  "EDOMEX"),
            ("V-003", "CCC-222-C",  "CDMX"),
            ("V-004", "DDD-333-D",  "JAL"),
            ("V-005", "EEE-444-E",  "NL"),
            ("V-006", "FFF-555-F",  "QRO"),
            ("V-007", "GGG-666-G",  "CDMX"),
            ("V-008", "HHH-777-H",  "GTO"),
            ("V-009", "III-888-I",  "CDMX"),
            # V-010 sin placas
        ]
        emplacamientos = {}
        for num_int, placas, ent_abr in datos:
            v = vehiculos[num_int]
            emp, _ = Emplacamiento.objects.get_or_create(
                vehiculo=v,
                placas=placas,
                defaults={
                    "entidad_federativa": entidades[ent_abr],
                    "fecha_inicio": localdate() - timedelta(days=365),
                    "fecha_fin": None,
                },
            )
            emplacamientos[num_int] = emp
        return emplacamientos

    # ─── Asignaciones ────────────────────────────────────────────────────────

    def _asignaciones(self, vehiculos, conductores, plataformas, socios, apps):
        plat = list(plataformas.values())
        soc = list(socios.values())
        uber = apps["Uber"]
        didi = apps["DiDi"]
        cabify = apps["Cabify"]

        # (num_int, conductor_primer_nombre, plataforma_idx, socio_idx, apps_list)
        datos = [
            ("V-001", "Carlos",   0, 0, [uber, didi]),
            ("V-002", "María",    0, 1, [uber]),
            ("V-003", "Roberto",  1, 0, [didi]),
            ("V-004", "Ana",      0, 0, [uber, cabify]),
            ("V-005", "Luis",     1, 1, [uber]),
            ("V-006", "Patricia", 0, 0, [didi]),
            ("V-008", "Elena",    1, 1, [uber, didi, cabify]),
        ]
        asignaciones = {}
        for num_int, cond_nombre, plat_idx, soc_idx, apps_list in datos:
            v = vehiculos[num_int]
            c = conductores[cond_nombre]
            asig, created = AsignacionVehiculo.objects.get_or_create(
                vehiculo=v,
                conductor=c,
                fecha_fin=None,
                defaults={
                    "plataforma": plat[plat_idx],
                    "socio": soc[soc_idx],
                    "fecha_inicio": localdate() - timedelta(days=90),
                },
            )
            for app in apps_list:
                AsignacionApp.objects.get_or_create(
                    asignacion_vehiculo=asig,
                    app_transporte=app,
                )
            asignaciones[num_int] = asig
        return asignaciones

    # ─── Pólizas ─────────────────────────────────────────────────────────────

    def _polizas(self, vehiculos, aseguradoras, titular, verde, amarillo, rojo):
        axa = aseguradoras["AXA"]
        qua = aseguradoras["QUA"]
        hoy = localdate()

        datos = [
            # (num_int, aseguradora, num_poliza,       inicio,        fin)
            ("V-001", axa, "POL-DEMO-001", hoy - timedelta(days=180), verde),     # vigente VERDE
            ("V-002", qua, "POL-DEMO-002", hoy - timedelta(days=90),  verde),     # vigente VERDE
            ("V-003", axa, "POL-DEMO-003", hoy - timedelta(days=180), amarillo),  # vence pronto AMARILLO
            ("V-004", qua, "POL-DEMO-004", hoy - timedelta(days=90),  verde),     # vigente VERDE (verif será AMARILLO)
            ("V-005", axa, "POL-DEMO-005", hoy - timedelta(days=365), rojo),      # vencida ROJO
            ("V-006", qua, "POL-DEMO-006", hoy - timedelta(days=180), verde),     # vigente (adeudo dará ROJO)
            ("V-007", axa, "POL-DEMO-007", hoy - timedelta(days=180), verde),     # vigente (tarjeta dará ROJO)
            ("V-008", qua, "POL-DEMO-008", hoy - timedelta(days=180), verde),     # vigente VERDE
        ]
        for num_int, aseg, num_pol, inicio, fin in datos:
            v = vehiculos[num_int]
            PolizaSeguro.objects.get_or_create(
                aseguradora=aseg,
                numero_poliza=num_pol,
                defaults={
                    "vehiculo": v,
                    "titular_poliza": titular,
                    "fecha_vigencia_inicio": inicio,
                    "fecha_vigencia_fin": fin,
                    "importe_prima": Decimal("8500.00"),
                },
            )

    # ─── Verificaciones ──────────────────────────────────────────────────────

    def _verificaciones(self, vehiculos, emplacamientos, verde, amarillo):
        hoy = localdate()
        datos = [
            # (num_int, semestre, ultima_verif, limite)
            ("V-001", "2026-1", hoy - timedelta(days=60), verde),
            ("V-002", "2026-1", hoy - timedelta(days=45), verde),
            ("V-003", "2026-1", hoy - timedelta(days=60), verde),         # poliza da AMARILLO, verif ok
            ("V-004", "2026-1", hoy - timedelta(days=30), amarillo),      # verif da AMARILLO
            ("V-006", "2026-1", hoy - timedelta(days=60), verde),         # adeudo da ROJO, verif ok
            ("V-008", "2026-1", hoy - timedelta(days=60), verde),
        ]
        for num_int, semestre, ultima, limite in datos:
            v = vehiculos[num_int]
            emp = emplacamientos.get(num_int)
            VerificacionVehicular.objects.get_or_create(
                vehiculo=v,
                semestre=semestre,
                defaults={
                    "emplacamiento": emp,
                    "fecha_ultima_verificacion": ultima,
                    "fecha_limite_verificacion": limite,
                },
            )

    # ─── Tarjetas de circulación ─────────────────────────────────────────────

    def _tarjetas(self, vehiculos, emplacamientos, verde, rojo):
        hoy = localdate()
        datos = [
            ("V-001", hoy - timedelta(days=365), verde),
            ("V-002", hoy - timedelta(days=365), verde),
            ("V-003", hoy - timedelta(days=180), verde),
            ("V-004", hoy - timedelta(days=365), verde),
            ("V-006", hoy - timedelta(days=365), verde),
            ("V-007", hoy - timedelta(days=365), rojo),   # tarjeta vencida → ROJO
            ("V-008", hoy - timedelta(days=365), verde),
        ]
        for num_int, emision, vigencia_fin in datos:
            v = vehiculos[num_int]
            emp = emplacamientos.get(num_int)
            TarjetaCirculacion.objects.get_or_create(
                vehiculo=v,
                fecha_vigencia_fin=vigencia_fin,
                defaults={
                    "emplacamiento": emp,
                    "fecha_emision": emision,
                },
            )

    # ─── Tenencias ───────────────────────────────────────────────────────────

    def _tenencias(self, vehiculos, hoy):
        anio = hoy.year
        for num_int, v in vehiculos.items():
            Tenencia.objects.get_or_create(
                vehiculo=v,
                anio_fiscal=anio,
                defaults={
                    "estatus_tenencia": "PAGADA" if num_int not in ("V-005", "V-006") else "PENDIENTE",
                    "monto_tenencia": Decimal("2500.00"),
                    "fecha_pago": hoy - timedelta(days=30) if num_int not in ("V-005", "V-006") else None,
                },
            )

    # ─── Adeudos ─────────────────────────────────────────────────────────────

    def _adeudos(self, vehiculos):
        hoy = localdate()
        # V-006 tendrá adeudo pendiente → semáforo ROJO
        v6 = vehiculos["V-006"]
        AdeudoVehicular.objects.get_or_create(
            vehiculo=v6,
            tipo_adeudo="Multa de tránsito",
            estatus_adeudo="PENDIENTE",
            defaults={
                "monto_adeudo": Decimal("1200.00"),
                "fecha_consulta": hoy - timedelta(days=10),
                "observacion_adeudo": "Infracción por exceso de velocidad.",
            },
        )
        # V-005 también tendrá adeudo además de póliza vencida
        v5 = vehiculos["V-005"]
        AdeudoVehicular.objects.get_or_create(
            vehiculo=v5,
            tipo_adeudo="Tenencia no pagada",
            estatus_adeudo="PENDIENTE",
            defaults={
                "monto_adeudo": Decimal("3500.00"),
                "fecha_consulta": hoy - timedelta(days=5),
            },
        )
        # Adeudo ya pagado en V-001 (histórico, no afecta semáforo)
        v1 = vehiculos["V-001"]
        AdeudoVehicular.objects.get_or_create(
            vehiculo=v1,
            tipo_adeudo="Tenencia 2025",
            estatus_adeudo="PAGADO",
            defaults={
                "monto_adeudo": Decimal("2500.00"),
                "fecha_consulta": hoy - timedelta(days=180),
            },
        )

    # ─── GPS y TAG ───────────────────────────────────────────────────────────

    def _gps_y_tag(self, vehiculos, hoy):
        gps_datos = [
            ("864DEMO000000001", "GPS-D01", "V-001"),
            ("864DEMO000000002", "GPS-D02", "V-002"),
            ("864DEMO000000003", "GPS-D03", "V-003"),
            ("864DEMO000000004", "GPS-D04", "V-004"),
            ("864DEMO000000005", "GPS-D05", "V-008"),
        ]
        for imei, num_gps, num_int in gps_datos:
            gps, _ = DispositivoGps.objects.get_or_create(
                imei=imei,
                defaults={"numero_gps": num_gps, "estatus_gps": "ACTIVO"},
            )
            v = vehiculos[num_int]
            InstalacionGps.objects.get_or_create(
                vehiculo=v,
                gps=gps,
                fecha_retiro=None,
                defaults={"fecha_instalacion": hoy - timedelta(days=90)},
            )

        tag_datos = [
            ("TAG-DEMO-001", "T001", "V-001"),
            ("TAG-DEMO-002", "T002", "V-002"),
            ("TAG-DEMO-003", "T003", "V-004"),
            ("TAG-DEMO-004", "T004", "V-008"),
        ]
        for codigo, corto, num_int in tag_datos:
            tag, _ = TagTelepeaje.objects.get_or_create(
                codigo_tag=codigo,
                defaults={"codigo_tag_corto": corto, "estatus_tag": "ACTIVO"},
            )
            v = vehiculos[num_int]
            AsignacionTag.objects.get_or_create(
                vehiculo=v,
                tag=tag,
                fecha_fin=None,
                defaults={"fecha_inicio": hoy - timedelta(days=90)},
            )

    # ─── Observaciones ───────────────────────────────────────────────────────

    def _observaciones(self, vehiculos, asignaciones):
        hoy = localdate()
        datos = [
            ("V-001", "GENERAL",  "Vehículo incorporado a la flotilla demo. Documentación al corriente."),
            ("V-003", "DOCUMENTO","Póliza de seguro próxima a vencer. Renovar a la brevedad."),
            ("V-004", "DOCUMENTO","Verificación vehicular próxima a vencer. Programar cita."),
            ("V-005", "DOCUMENTO","Póliza de seguro vencida. Vehículo no debe operar hasta renovar."),
            ("V-006", "ADEUDO",   "Se detectó multa de tránsito pendiente de pago. Tramitar liquidación."),
            ("V-007", "DOCUMENTO","Tarjeta de circulación vencida. Tramitar reposición."),
            ("V-009", "MECANICA", "Vehículo ingresado a taller por revisión de frenos."),
            ("V-010", "GENERAL",  "Unidad en espera de asignación a conductor."),
        ]
        for num_int, tipo, texto in datos:
            v = vehiculos[num_int]
            Observacion.objects.get_or_create(
                vehiculo=v,
                tipo_observacion=tipo,
                texto_observacion=texto,
                defaults={"fecha_registro": hoy},
            )
