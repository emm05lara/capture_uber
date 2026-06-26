# Sistema de Gestión de Flotilla

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-requerido-4169E1?logo=postgresql&logoColor=white)
![Estado](https://img.shields.io/badge/estado-en%20desarrollo-orange)

Aplicación web desarrollada con **Django y PostgreSQL** para centralizar la administración de una flotilla vehicular.

El sistema permite registrar vehículos, conductores, organizaciones, asignaciones operativas, pólizas, verificaciones, tarjetas de circulación, tenencias, adeudos, dispositivos GPS, TAG de telepeaje y observaciones. Además, incluye un dashboard con indicadores y alertas documentales.

> Aunque el repositorio conserva el nombre `capture_uber`, la implementación actual corresponde a un sistema integral de gestión de flotilla.

---

## Características principales

- Autenticación de usuarios mediante Django.
- Usuarios con roles de administrador, operador y auditor.
- Dashboard con resumen general de la flotilla.
- Semáforo documental para identificar unidades:
  - **Verde:** documentación sin alertas.
  - **Amarillo:** documentos próximos a vencer en un periodo de 30 días.
  - **Rojo:** documentos vencidos o adeudos pendientes.
- Consulta de vehículos con:
  - búsqueda por número interno;
  - placas;
  - conductor;
  - VIN o número de serie;
  - modelo;
  - marca.
- Filtros por estatus de la unidad y semáforo documental.
- Paginación de resultados.
- Ficha detallada de cada vehículo.
- Historial de placas y emplacamientos.
- Administración de pólizas de seguro.
- Control de verificaciones vehiculares.
- Control de tarjetas de circulación.
- Registro de tenencias y adeudos.
- Asignación de vehículos a conductores, plataformas y socios.
- Asociación con aplicaciones de transporte.
- Administración de dispositivos GPS.
- Administración de TAG de telepeaje.
- Bitácora de observaciones.
- Panel administrativo de Django para altas, bajas y modificaciones.
- Preparación para despliegue con Gunicorn, WhiteNoise y PostgreSQL.

---

## Estado actual

El proyecto se encuentra en desarrollo.

La interfaz web permite actualmente:

- iniciar y cerrar sesión;
- consultar el dashboard;
- buscar y filtrar vehículos;
- consultar la ficha detallada de una unidad.

La captura y modificación de información se realiza principalmente desde el panel de administración de Django:

```text
/admin/
```

---

## Tecnologías utilizadas

| Tecnología | Uso |
|---|---|
| Python | Lenguaje principal |
| Django 5.2 | Framework web |
| PostgreSQL | Base de datos relacional |
| Bootstrap 5 | Diseño de la interfaz |
| Bootstrap Icons | Iconografía |
| Gunicorn | Servidor WSGI para producción |
| WhiteNoise | Archivos estáticos en producción |
| python-decouple | Variables de entorno |
| dj-database-url | Configuración de PostgreSQL mediante URL |

---

## Arquitectura del proyecto

El sistema está dividido en aplicaciones de Django con responsabilidades específicas:

| Aplicación | Responsabilidad |
|---|---|
| `accounts` | Usuarios personalizados y roles |
| `catalogos` | Marcas, modelos, colores, entidades federativas y aplicaciones de transporte |
| `actores` | Personas, conductores, titulares, socios, plataformas y aseguradoras |
| `vehiculos` | Vehículos, placas, documentos, adeudos, adquisiciones y observaciones |
| `dispositivos` | Dispositivos GPS, instalaciones, TAG y asignaciones |
| `operacion` | Asignaciones de vehículos, conductores, socios, plataformas y apps |
| `config` | Configuración general del proyecto |

Estructura principal:

```text
capture_uber/
├── accounts/
├── actores/
├── catalogos/
├── config/
├── dispositivos/
├── operacion/
├── static/
│   └── css/
├── templates/
│   ├── registration/
│   └── vehiculos/
├── vehiculos/
├── .env.example
├── manage.py
└── requirements.txt
```

---

## Modelo general de información

```mermaid
flowchart TD
    Marca --> ModeloVehiculo
    ModeloVehiculo --> Vehiculo
    Color --> Vehiculo
    EntidadFederativa --> Emplacamiento
    Vehiculo --> Emplacamiento

    Vehiculo --> PolizaSeguro
    Aseguradora --> PolizaSeguro
    TitularPoliza --> PolizaSeguro

    Vehiculo --> VerificacionVehicular
    Vehiculo --> TarjetaCirculacion
    Vehiculo --> Tenencia
    Vehiculo --> AdeudoVehicular
    Vehiculo --> Observacion

    Vehiculo --> AsignacionVehiculo
    Conductor --> AsignacionVehiculo
    PlataformaOperativa --> AsignacionVehiculo
    Socio --> AsignacionVehiculo

    AsignacionVehiculo --> AsignacionApp
    AppTransporte --> AsignacionApp

    Vehiculo --> InstalacionGps
    DispositivoGps --> InstalacionGps

    Vehiculo --> AsignacionTag
    TagTelepeaje --> AsignacionTag
```

---

## Requisitos

Antes de iniciar se necesita:

- Python 3.10 o superior.
- PostgreSQL instalado y en ejecución.
- Git.
- Un entorno virtual de Python.
- Acceso a una terminal PowerShell, CMD, Bash o similar.

---

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/emm05lara/capture_uber.git
cd capture_uber
```

### 2. Crear el entorno virtual

En Windows:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar las dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Crear la base de datos PostgreSQL

Desde `psql` o una herramienta como pgAdmin:

```sql
CREATE USER flotilla_user WITH PASSWORD 'cambia-esta-contrasena';
CREATE DATABASE flotilla_db OWNER flotilla_user;
```

Se recomienda utilizar credenciales distintas en cada entorno.

### 5. Crear el archivo de variables de entorno

En PowerShell:

```powershell
Copy-Item .env.example .env
```

En Linux o macOS:

```bash
cp .env.example .env
```

Editar el archivo `.env`:

```env
SECRET_KEY=coloca-aqui-una-clave-secreta
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=
DATABASE_URL=postgres://flotilla_user:cambia-esta-contrasena@localhost:5432/flotilla_db
```

Para generar una clave secreta de Django:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

No se debe subir el archivo `.env` al repositorio.

### 6. Aplicar las migraciones

```bash
python manage.py migrate
```

Las migraciones crean las tablas y las vistas de PostgreSQL requeridas por el dashboard y las fichas de vehículos.

### 7. Crear un usuario administrador

```bash
python manage.py createsuperuser
```

### 8. Iniciar el servidor

```bash
python manage.py runserver
```

Abrir en el navegador:

```text
http://127.0.0.1:8000/
```

---

## Rutas principales

| Ruta | Descripción |
|---|---|
| `/` | Dashboard |
| `/vehiculos/` | Listado y búsqueda de vehículos |
| `/vehiculos/<id>/` | Ficha detallada del vehículo |
| `/accounts/login/` | Inicio de sesión |
| `/accounts/logout/` | Cierre de sesión |
| `/admin/` | Administración del sistema |

Todas las vistas principales requieren autenticación.

---

## Configuración inicial recomendada

Después de crear el superusuario:

1. Ingresar a `/admin/`.
2. Registrar marcas.
3. Registrar modelos de vehículo.
4. Registrar colores.
5. Registrar entidades federativas.
6. Registrar aplicaciones de transporte.
7. Registrar conductores, plataformas, socios y aseguradoras.
8. Registrar los vehículos.
9. Agregar placas, documentos, dispositivos y asignaciones.
10. Consultar el dashboard y verificar el semáforo documental.

---

## Semáforo documental

El sistema utiliza vistas de PostgreSQL para generar una ficha consolidada de cada vehículo.

Las vistas creadas son:

```text
vw_vehiculo_actual
vw_asignacion_actual
vw_documentacion_actual
vw_ficha_vehiculo
```

El semáforo se determina de la siguiente manera:

### Rojo

Una unidad aparece en rojo cuando:

- tiene uno o más adeudos pendientes;
- la póliza está vencida;
- la verificación está vencida;
- la tarjeta de circulación está vencida.

### Amarillo

Una unidad aparece en amarillo cuando alguno de esos documentos vencerá dentro de los próximos 30 días.

### Verde

Una unidad aparece en verde cuando no existen adeudos pendientes ni vencimientos inmediatos.

---

## Comandos útiles

Verificar la configuración:

```bash
python manage.py check
```

Crear nuevas migraciones:

```bash
python manage.py makemigrations
```

Aplicar migraciones:

```bash
python manage.py migrate
```

Ejecutar pruebas:

```bash
python manage.py test
```

Recolectar archivos estáticos:

```bash
python manage.py collectstatic --noinput
```

Abrir la consola interactiva de Django:

```bash
python manage.py shell
```

---

## Despliegue en Render

El proyecto incluye las dependencias necesarias para ejecutarse con PostgreSQL, Gunicorn y WhiteNoise.

### Servicio web

Configurar un nuevo Web Service conectado al repositorio.

Build Command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Start Command:

```bash
gunicorn config.wsgi:application
```

### Variables de entorno

Configurar como mínimo:

```env
SECRET_KEY=una-clave-segura
DEBUG=False
ALLOWED_HOSTS=nombre-del-servicio.onrender.com
CSRF_TRUSTED_ORIGINS=https://nombre-del-servicio.onrender.com
DATABASE_URL=valor-proporcionado-por-render
```

Después del primer despliegue, ejecutar:

```bash
python manage.py migrate
python manage.py createsuperuser
```

La variable `DATABASE_URL` puede ser proporcionada automáticamente al vincular una base de datos PostgreSQL de Render.

---

## Seguridad

Para producción:

- utilizar una `SECRET_KEY` diferente a la del entorno local;
- mantener `DEBUG=False`;
- restringir `ALLOWED_HOSTS`;
- configurar correctamente `CSRF_TRUSTED_ORIGINS`;
- no versionar `.env`;
- utilizar contraseñas seguras para PostgreSQL;
- realizar respaldos periódicos de la base de datos;
- revisar los permisos de usuarios y roles;
- no utilizar el servidor de desarrollo de Django en producción.

---

## Próximas mejoras

- Formularios web para altas y modificaciones sin depender del panel administrativo.
- Permisos diferenciados por rol.
- Importación de datos desde Excel o CSV.
- Exportación de reportes.
- Carga y almacenamiento de documentos.
- Historial de cambios y auditoría.
- Notificaciones por vencimientos.
- Pruebas automatizadas.
- Integración continua.
- Contenedores Docker.
- API REST.
- Mejoras adicionales en la interfaz.

---

## Contribución

Para desarrollar una nueva funcionalidad:

```bash
git checkout -b feature/nombre-de-la-funcionalidad
```

Después de realizar los cambios:

```bash
git add .
git commit -m "feat: descripción del cambio"
git push origin feature/nombre-de-la-funcionalidad
```

Posteriormente se puede abrir un Pull Request hacia la rama `main`.

---

## Licencia

Este repositorio no incluye actualmente un archivo de licencia. Antes de distribuir o reutilizar el proyecto fuera de su propósito original, se recomienda definir una licencia explícita.
