/*
===============================================================================
 SCRIPT SQL - MODELO RELACIONAL PARA SISTEMA DE FLOTA VEHICULAR
 Base: PostgreSQL
 Objetivo: convertir el MER/EER definido en una estructura relacional normalizada.

 Principios del modelo:
 - VEHICULO representa solo la unidad física.
 - No se usa una tabla gigante tipo Excel.
 - La llave concatenada no es PK; se calcula en una vista.
 - Placas, pólizas, GPS, TAG, verificaciones, tenencias, adeudos y observaciones
   se modelan como entidades históricas o asociativas.
 - Supertipos/subtipos:
     PERSONA -> CONDUCTOR, TITULAR_POLIZA
     ORGANIZACION -> PLATAFORMA_OPERATIVA, SOCIO, ASEGURADORA
 - Las especializaciones son parciales y con traslape, salvo que el negocio
   decida volverlas totales.
===============================================================================
*/

-- Si quieres recrear todo desde cero, descomenta esta línea:
-- DROP SCHEMA IF EXISTS flotilla CASCADE;

CREATE SCHEMA IF NOT EXISTS flotilla;
SET search_path TO flotilla, public;

/*=============================================================================
  1. FUNCIONES GENERALES
=============================================================================*/

CREATE OR REPLACE FUNCTION flotilla.fn_set_fecha_actualizacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

/*=============================================================================
  2. CATÁLOGOS BASE DEL VEHÍCULO
=============================================================================*/

CREATE TABLE marca (
    id_marca BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_marca VARCHAR(80) NOT NULL UNIQUE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE marca IS 'Entidad fuerte / catálogo. Representa la marca comercial del vehículo.';
COMMENT ON COLUMN marca.nombre_marca IS 'Obligatorio. Ejemplos: BMW, CHEVROLET, NISSAN, VOLKSWAGEN.';

CREATE TABLE modelo_vehiculo (
    id_modelo_vehiculo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_marca BIGINT NOT NULL REFERENCES marca(id_marca) ON UPDATE CASCADE ON DELETE RESTRICT,
    nombre_modelo_comercial VARCHAR(100) NOT NULL,
    version VARCHAR(100),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_modelo_vehiculo UNIQUE (id_marca, nombre_modelo_comercial, version)
);

COMMENT ON TABLE modelo_vehiculo IS 'Entidad fuerte / catálogo. Línea o modelo comercial del vehículo.';
COMMENT ON COLUMN modelo_vehiculo.nombre_modelo_comercial IS 'Obligatorio. Ejemplos: X7, AVEO, VENTO, MARCH, VERSA.';
COMMENT ON COLUMN modelo_vehiculo.version IS 'Opcional. Versión comercial si se maneja: LT, Sense, Advance, etc.';

CREATE TABLE color (
    id_color BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_color VARCHAR(50) NOT NULL UNIQUE,
    abreviatura_color VARCHAR(20),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE color IS 'Entidad fuerte / catálogo. Color normalizado del vehículo.';
COMMENT ON COLUMN color.nombre_color IS 'Obligatorio. Ejemplos: NEGRO, BLANCO, GRIS, AZUL.';
COMMENT ON COLUMN color.abreviatura_color IS 'Opcional. Abreviatura usada internamente si aplica.';

CREATE TABLE entidad_federativa (
    id_entidad_federativa BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_entidad VARCHAR(80) NOT NULL UNIQUE,
    abreviatura_entidad VARCHAR(20),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE entidad_federativa IS 'Entidad fuerte / catálogo. Entidad donde se emplaca el vehículo.';
COMMENT ON COLUMN entidad_federativa.nombre_entidad IS 'Obligatorio. Ejemplos: CDMX, ESTADO DE MEXICO, JALISCO.';
COMMENT ON COLUMN entidad_federativa.abreviatura_entidad IS 'Opcional. Abreviatura institucional.';

/*=============================================================================
  3. ENTIDAD PRINCIPAL: VEHÍCULO
=============================================================================*/

CREATE TABLE vehiculo (
    id_vehiculo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    numero_interno VARCHAR(50),
    id_modelo_vehiculo BIGINT NOT NULL REFERENCES modelo_vehiculo(id_modelo_vehiculo) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_color BIGINT NOT NULL REFERENCES color(id_color) ON UPDATE CASCADE ON DELETE RESTRICT,
    anio_modelo SMALLINT NOT NULL CHECK (anio_modelo BETWEEN 1900 AND 2100),
    numero_serie VARCHAR(40) NOT NULL UNIQUE,
    estatus_unidad VARCHAR(30) NOT NULL DEFAULT 'ACTIVA',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_vehiculo_estatus CHECK (
        estatus_unidad IN ('ACTIVA', 'BAJA', 'TALLER', 'SIN_ASIGNAR', 'SINIESTRADA', 'VENDIDA')
    )
);

COMMENT ON TABLE vehiculo IS 'Entidad fuerte. Representa únicamente la unidad física, no su operación, póliza, GPS, TAG, adeudos ni conductor.';
COMMENT ON COLUMN vehiculo.id_vehiculo IS 'Obligatorio. PK artificial recomendada.';
COMMENT ON COLUMN vehiculo.numero_interno IS 'Opcional. Consecutivo o folio interno proveniente del Excel.';
COMMENT ON COLUMN vehiculo.numero_serie IS 'Obligatorio. Número de serie/VIN. Llave candidata única.';
COMMENT ON COLUMN vehiculo.anio_modelo IS 'Obligatorio. Año modelo del vehículo.';
COMMENT ON COLUMN vehiculo.estatus_unidad IS 'Obligatorio. Estado operativo general de la unidad.';

CREATE INDEX idx_vehiculo_numero_serie ON vehiculo(numero_serie);
CREATE INDEX idx_vehiculo_estatus_unidad ON vehiculo(estatus_unidad);
CREATE INDEX idx_vehiculo_modelo_color_anio ON vehiculo(id_modelo_vehiculo, id_color, anio_modelo);

/*=============================================================================
  4. EMPLACAMIENTO - HISTORIAL DE PLACAS
=============================================================================*/

CREATE TABLE emplacamiento (
    id_emplacamiento BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    placas VARCHAR(20) NOT NULL,
    id_entidad_federativa BIGINT NOT NULL REFERENCES entidad_federativa(id_entidad_federativa) ON UPDATE CASCADE ON DELETE RESTRICT,
    fecha_inicio DATE,
    fecha_fin DATE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_emplacamiento_fechas CHECK (
        fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio
    )
);

COMMENT ON TABLE emplacamiento IS 'Entidad dependiente / histórica. Guarda el historial de placas de cada vehículo.';
COMMENT ON COLUMN emplacamiento.placas IS 'Obligatorio. Placas asignadas en un periodo.';
COMMENT ON COLUMN emplacamiento.fecha_inicio IS 'Opcional. Inicio de vigencia del emplacamiento.';
COMMENT ON COLUMN emplacamiento.fecha_fin IS 'Opcional. Fin de vigencia. Si es NULL, se considera emplacamiento actual.';

-- Evita que un vehículo tenga dos placas actuales al mismo tiempo.
CREATE UNIQUE INDEX uq_emplacamiento_actual_por_vehiculo
ON emplacamiento(id_vehiculo)
WHERE fecha_fin IS NULL;

-- Evita que una misma placa esté activa en dos vehículos al mismo tiempo.
CREATE UNIQUE INDEX uq_emplacamiento_placa_actual
ON emplacamiento(UPPER(placas))
WHERE fecha_fin IS NULL;

CREATE INDEX idx_emplacamiento_placas ON emplacamiento(UPPER(placas));
CREATE INDEX idx_emplacamiento_vehiculo ON emplacamiento(id_vehiculo);

/*=============================================================================
  5. ADQUISICIÓN / COMPRA
=============================================================================*/

CREATE TABLE adquisicion (
    id_adquisicion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    tipo_adquisicion VARCHAR(80) NOT NULL,
    fecha_adquisicion DATE,
    importe_adquisicion NUMERIC(14,2),
    observacion_adquisicion TEXT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_adquisicion_importe CHECK (importe_adquisicion IS NULL OR importe_adquisicion >= 0)
);

COMMENT ON TABLE adquisicion IS 'Entidad dependiente de VEHICULO. Registra compra, recuperación, siniestro, regularización u otra forma de adquisición.';
COMMENT ON COLUMN adquisicion.tipo_adquisicion IS 'Obligatorio. Ejemplos: COMPRA, RECUPERACION, SINIESTRO, ROBO, INUNDACION.';
COMMENT ON COLUMN adquisicion.fecha_adquisicion IS 'Opcional. Fecha de compra o adquisición.';
COMMENT ON COLUMN adquisicion.importe_adquisicion IS 'Opcional. Importe de adquisición. Corresponde al primer IMPORTE del Excel.';

CREATE INDEX idx_adquisicion_vehiculo ON adquisicion(id_vehiculo);
CREATE INDEX idx_adquisicion_fecha ON adquisicion(fecha_adquisicion);

/*=============================================================================
  6. PERSONAS Y SUBTIPOS
     Especialización: parcial y con traslape.
=============================================================================*/

CREATE TABLE persona (
    id_persona BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_completo VARCHAR(150) NOT NULL,
    telefono VARCHAR(30),
    correo VARCHAR(120),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE persona IS 'Supertipo. Representa personas físicas relacionadas con el sistema.';
COMMENT ON COLUMN persona.nombre_completo IS 'Obligatorio. No se usa atributo compuesto para nombre y apellidos.';
COMMENT ON COLUMN persona.telefono IS 'Opcional.';
COMMENT ON COLUMN persona.correo IS 'Opcional.';

CREATE TABLE conductor (
    id_persona BIGINT PRIMARY KEY REFERENCES persona(id_persona) ON UPDATE CASCADE ON DELETE CASCADE,
    estatus_conductor VARCHAR(30) NOT NULL DEFAULT 'ACTIVO',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_conductor_estatus CHECK (
        estatus_conductor IN ('ACTIVO', 'INACTIVO', 'BLOQUEADO', 'BAJA')
    )
);

COMMENT ON TABLE conductor IS 'Subtipo de PERSONA. Especialización parcial y con traslape.';
COMMENT ON COLUMN conductor.estatus_conductor IS 'Obligatorio. Estado operativo del conductor.';

CREATE TABLE titular_poliza (
    id_persona BIGINT PRIMARY KEY REFERENCES persona(id_persona) ON UPDATE CASCADE ON DELETE CASCADE,
    estatus_titular VARCHAR(30) NOT NULL DEFAULT 'ACTIVO',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_titular_estatus CHECK (
        estatus_titular IN ('ACTIVO', 'INACTIVO')
    )
);

COMMENT ON TABLE titular_poliza IS 'Subtipo de PERSONA. Una persona puede ser titular de póliza, conductor o ambos.';
COMMENT ON COLUMN titular_poliza.estatus_titular IS 'Obligatorio. Estado del titular de póliza.';

CREATE INDEX idx_persona_nombre ON persona(UPPER(nombre_completo));

/*=============================================================================
  7. ORGANIZACIONES Y SUBTIPOS
     Especialización: parcial y con traslape.
=============================================================================*/

CREATE TABLE organizacion (
    id_organizacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    clave_organizacion VARCHAR(50),
    nombre_organizacion VARCHAR(150) NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_organizacion_nombre UNIQUE(nombre_organizacion)
);

COMMENT ON TABLE organizacion IS 'Supertipo. Representa organizaciones: plataforma, socio, aseguradora u otros roles futuros.';
COMMENT ON COLUMN organizacion.clave_organizacion IS 'Opcional. Clave interna como ASHC, BYER, AXA, etc.';
COMMENT ON COLUMN organizacion.nombre_organizacion IS 'Obligatorio. Nombre o razón social.';

CREATE TABLE plataforma_operativa (
    id_organizacion BIGINT PRIMARY KEY REFERENCES organizacion(id_organizacion) ON UPDATE CASCADE ON DELETE CASCADE,
    estatus_plataforma VARCHAR(30) NOT NULL DEFAULT 'ACTIVA',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_plataforma_estatus CHECK (
        estatus_plataforma IN ('ACTIVA', 'INACTIVA')
    )
);

COMMENT ON TABLE plataforma_operativa IS 'Subtipo de ORGANIZACION. Representa plataformas operativas internas o externas.';

CREATE TABLE socio (
    id_organizacion BIGINT PRIMARY KEY REFERENCES organizacion(id_organizacion) ON UPDATE CASCADE ON DELETE CASCADE,
    estatus_socio VARCHAR(30) NOT NULL DEFAULT 'ACTIVO',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_socio_estatus CHECK (
        estatus_socio IN ('ACTIVO', 'INACTIVO')
    )
);

COMMENT ON TABLE socio IS 'Subtipo de ORGANIZACION. Representa socio asociado a la operación o asignación.';

CREATE TABLE aseguradora (
    id_organizacion BIGINT PRIMARY KEY REFERENCES organizacion(id_organizacion) ON UPDATE CASCADE ON DELETE CASCADE,
    estatus_aseguradora VARCHAR(30) NOT NULL DEFAULT 'ACTIVA',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_aseguradora_estatus CHECK (
        estatus_aseguradora IN ('ACTIVA', 'INACTIVA')
    )
);

COMMENT ON TABLE aseguradora IS 'Subtipo de ORGANIZACION. Representa aseguradoras emisoras de pólizas.';

CREATE INDEX idx_organizacion_clave ON organizacion(UPPER(clave_organizacion));
CREATE INDEX idx_organizacion_nombre ON organizacion(UPPER(nombre_organizacion));

/*=============================================================================
  8. ASIGNACIÓN VEHÍCULO - CONDUCTOR
     Entidad asociativa / histórica. Resuelve N:M entre VEHICULO y CONDUCTOR.
=============================================================================*/

CREATE TABLE asignacion_vehiculo (
    id_asignacion_vehiculo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    id_conductor BIGINT NOT NULL REFERENCES conductor(id_persona) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_plataforma BIGINT REFERENCES plataforma_operativa(id_organizacion) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_socio BIGINT REFERENCES socio(id_organizacion) ON UPDATE CASCADE ON DELETE RESTRICT,
    cuenta VARCHAR(100),
    fecha_inicio DATE,
    fecha_fin DATE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_asignacion_fechas CHECK (
        fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio
    )
);

COMMENT ON TABLE asignacion_vehiculo IS 'Entidad asociativa e histórica. Representa la relación operativa entre vehículo y conductor.';
COMMENT ON COLUMN asignacion_vehiculo.cuenta IS 'Opcional. Cuenta o identificador operativo asociado a la asignación.';
COMMENT ON COLUMN asignacion_vehiculo.fecha_fin IS 'Opcional. Si es NULL, la asignación se considera vigente.';

-- Un vehículo no debe tener dos asignaciones vigentes simultáneas.
CREATE UNIQUE INDEX uq_asignacion_actual_por_vehiculo
ON asignacion_vehiculo(id_vehiculo)
WHERE fecha_fin IS NULL;

-- Si el negocio permite que un conductor tenga varios vehículos simultáneos, elimina este índice.
CREATE UNIQUE INDEX uq_asignacion_actual_por_conductor
ON asignacion_vehiculo(id_conductor)
WHERE fecha_fin IS NULL;

CREATE INDEX idx_asignacion_vehiculo ON asignacion_vehiculo(id_vehiculo);
CREATE INDEX idx_asignacion_conductor ON asignacion_vehiculo(id_conductor);
CREATE INDEX idx_asignacion_plataforma ON asignacion_vehiculo(id_plataforma);
CREATE INDEX idx_asignacion_socio ON asignacion_vehiculo(id_socio);
CREATE INDEX idx_asignacion_cuenta ON asignacion_vehiculo(UPPER(cuenta));

/*=============================================================================
  9. APLICACIONES DE TRANSPORTE
     APP es multivaluado: UBER, DIDI, ambos, etc. Se normaliza.
=============================================================================*/

CREATE TABLE app_transporte (
    id_app_transporte BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_app VARCHAR(80) NOT NULL UNIQUE,
    estatus_app VARCHAR(30) NOT NULL DEFAULT 'ACTIVA',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_app_estatus CHECK (
        estatus_app IN ('ACTIVA', 'INACTIVA')
    )
);

COMMENT ON TABLE app_transporte IS 'Entidad fuerte / catálogo. Reemplaza valores multivaluados como UBER, DIDI o AMBOS.';

CREATE TABLE asignacion_app (
    id_asignacion_vehiculo BIGINT NOT NULL REFERENCES asignacion_vehiculo(id_asignacion_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    id_app_transporte BIGINT NOT NULL REFERENCES app_transporte(id_app_transporte) ON UPDATE CASCADE ON DELETE RESTRICT,
    estatus_app_asignada VARCHAR(30) NOT NULL DEFAULT 'ACTIVA',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id_asignacion_vehiculo, id_app_transporte),
    CONSTRAINT chk_asignacion_app_estatus CHECK (
        estatus_app_asignada IN ('ACTIVA', 'INACTIVA', 'SUSPENDIDA')
    )
);

COMMENT ON TABLE asignacion_app IS 'Entidad asociativa. Relaciona una asignación vehículo-conductor con una o más apps.';

/*=============================================================================
  10. SEGUROS / PÓLIZAS
=============================================================================*/

CREATE TABLE poliza_seguro (
    id_poliza_seguro BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    id_aseguradora BIGINT NOT NULL REFERENCES aseguradora(id_organizacion) ON UPDATE CASCADE ON DELETE RESTRICT,
    id_titular_poliza BIGINT REFERENCES titular_poliza(id_persona) ON UPDATE CASCADE ON DELETE RESTRICT,
    numero_poliza VARCHAR(100) NOT NULL,
    fecha_vigencia_inicio DATE,
    fecha_vigencia_fin DATE NOT NULL,
    importe_prima NUMERIC(14,2),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_poliza_fechas CHECK (
        fecha_vigencia_inicio IS NULL OR fecha_vigencia_fin >= fecha_vigencia_inicio
    ),
    CONSTRAINT chk_poliza_importe CHECK (importe_prima IS NULL OR importe_prima >= 0),
    CONSTRAINT uq_poliza_por_aseguradora UNIQUE (id_aseguradora, numero_poliza)
);

COMMENT ON TABLE poliza_seguro IS 'Entidad dependiente / histórica. Registra pólizas de seguro asociadas a vehículos.';
COMMENT ON COLUMN poliza_seguro.numero_poliza IS 'Obligatorio. Número de póliza.';
COMMENT ON COLUMN poliza_seguro.fecha_vigencia_fin IS 'Obligatorio. Fecha de vencimiento de la póliza.';
COMMENT ON COLUMN poliza_seguro.importe_prima IS 'Opcional. Corresponde al segundo IMPORTE del Excel.';

CREATE INDEX idx_poliza_vehiculo ON poliza_seguro(id_vehiculo);
CREATE INDEX idx_poliza_numero ON poliza_seguro(UPPER(numero_poliza));
CREATE INDEX idx_poliza_vigencia_fin ON poliza_seguro(fecha_vigencia_fin);

/*=============================================================================
  11. GPS
=============================================================================*/

CREATE TABLE dispositivo_gps (
    id_gps BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    imei VARCHAR(80) NOT NULL UNIQUE,
    numero_gps VARCHAR(80),
    estatus_gps VARCHAR(30) NOT NULL DEFAULT 'ACTIVO',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_gps_estatus CHECK (
        estatus_gps IN ('ACTIVO', 'INACTIVO', 'EXTRAVIADO', 'DANADO', 'BAJA')
    )
);

COMMENT ON TABLE dispositivo_gps IS 'Entidad fuerte. Dispositivo GPS físico. Puede ser instalado en distintos vehículos a lo largo del tiempo.';
COMMENT ON COLUMN dispositivo_gps.imei IS 'Obligatorio. Llave candidata única del dispositivo GPS.';
COMMENT ON COLUMN dispositivo_gps.numero_gps IS 'Opcional. Número interno o identificador alterno del GPS.';

CREATE TABLE instalacion_gps (
    id_instalacion_gps BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    id_gps BIGINT NOT NULL REFERENCES dispositivo_gps(id_gps) ON UPDATE CASCADE ON DELETE RESTRICT,
    fecha_instalacion DATE,
    fecha_retiro DATE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_instalacion_gps_fechas CHECK (
        fecha_retiro IS NULL OR fecha_instalacion IS NULL OR fecha_retiro >= fecha_instalacion
    )
);

COMMENT ON TABLE instalacion_gps IS 'Entidad asociativa / histórica. Resuelve la relación N:M entre vehículos y GPS.';
COMMENT ON COLUMN instalacion_gps.fecha_retiro IS 'Opcional. Si es NULL, la instalación se considera vigente.';

CREATE UNIQUE INDEX uq_gps_actual_por_vehiculo
ON instalacion_gps(id_vehiculo)
WHERE fecha_retiro IS NULL;

CREATE UNIQUE INDEX uq_gps_actual_por_dispositivo
ON instalacion_gps(id_gps)
WHERE fecha_retiro IS NULL;

CREATE INDEX idx_gps_imei ON dispositivo_gps(UPPER(imei));
CREATE INDEX idx_instalacion_gps_vehiculo ON instalacion_gps(id_vehiculo);
CREATE INDEX idx_instalacion_gps_dispositivo ON instalacion_gps(id_gps);

/*=============================================================================
  12. TAG DE TELEPEAJE
=============================================================================*/

CREATE TABLE tag_telepeaje (
    id_tag BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_tag VARCHAR(100) NOT NULL UNIQUE,
    codigo_tag_corto VARCHAR(100),
    estatus_tag VARCHAR(30) NOT NULL DEFAULT 'ACTIVO',
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tag_estatus CHECK (
        estatus_tag IN ('ACTIVO', 'INACTIVO', 'EXTRAVIADO', 'DANADO', 'BAJA')
    )
);

COMMENT ON TABLE tag_telepeaje IS 'Entidad fuerte. TAG físico o cuenta de telepeaje.';
COMMENT ON COLUMN tag_telepeaje.codigo_tag IS 'Obligatorio. Código principal del TAG.';
COMMENT ON COLUMN tag_telepeaje.codigo_tag_corto IS 'Opcional. Código corto, equivalente a TAG2 del Excel si aplica.';

CREATE TABLE asignacion_tag (
    id_asignacion_tag BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    id_tag BIGINT NOT NULL REFERENCES tag_telepeaje(id_tag) ON UPDATE CASCADE ON DELETE RESTRICT,
    fecha_inicio DATE,
    fecha_fin DATE,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_asignacion_tag_fechas CHECK (
        fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio
    )
);

COMMENT ON TABLE asignacion_tag IS 'Entidad asociativa / histórica. Guarda la relación entre vehículo y TAG a lo largo del tiempo.';

-- Si el negocio permite varios TAG activos por vehículo, elimina este índice.
CREATE UNIQUE INDEX uq_tag_actual_por_vehiculo
ON asignacion_tag(id_vehiculo)
WHERE fecha_fin IS NULL;

CREATE UNIQUE INDEX uq_tag_actual_por_codigo
ON asignacion_tag(id_tag)
WHERE fecha_fin IS NULL;

CREATE INDEX idx_tag_codigo ON tag_telepeaje(UPPER(codigo_tag));
CREATE INDEX idx_tag_codigo_corto ON tag_telepeaje(UPPER(codigo_tag_corto));
CREATE INDEX idx_asignacion_tag_vehiculo ON asignacion_tag(id_vehiculo);
CREATE INDEX idx_asignacion_tag_tag ON asignacion_tag(id_tag);

/*=============================================================================
  13. VERIFICACIÓN VEHICULAR
=============================================================================*/

CREATE TABLE verificacion_vehicular (
    id_verificacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    id_emplacamiento BIGINT REFERENCES emplacamiento(id_emplacamiento) ON UPDATE CASCADE ON DELETE SET NULL,
    semestre VARCHAR(20) NOT NULL,
    fecha_ultima_verificacion DATE,
    fecha_limite_verificacion DATE NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE verificacion_vehicular IS 'Entidad dependiente / histórica. Registra fechas de verificación vehicular.';
COMMENT ON COLUMN verificacion_vehicular.semestre IS 'Obligatorio. Semestre de verificación.';
COMMENT ON COLUMN verificacion_vehicular.fecha_ultima_verificacion IS 'Opcional. Fecha en que se realizó la última verificación.';
COMMENT ON COLUMN verificacion_vehicular.fecha_limite_verificacion IS 'Obligatorio. Fecha límite de verificación.';
COMMENT ON COLUMN verificacion_vehicular.id_emplacamiento IS 'Opcional. Permite ligar la verificación al emplacamiento correspondiente.';

CREATE INDEX idx_verificacion_vehiculo ON verificacion_vehicular(id_vehiculo);
CREATE INDEX idx_verificacion_limite ON verificacion_vehicular(fecha_limite_verificacion);
CREATE INDEX idx_verificacion_semestre ON verificacion_vehicular(semestre);

/*=============================================================================
  14. TARJETA DE CIRCULACIÓN
=============================================================================*/

CREATE TABLE tarjeta_circulacion (
    id_tarjeta_circulacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    id_emplacamiento BIGINT REFERENCES emplacamiento(id_emplacamiento) ON UPDATE CASCADE ON DELETE SET NULL,
    fecha_emision DATE,
    fecha_vigencia_fin DATE NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tarjeta_fechas CHECK (
        fecha_emision IS NULL OR fecha_vigencia_fin >= fecha_emision
    )
);

COMMENT ON TABLE tarjeta_circulacion IS 'Entidad dependiente / histórica. Registra vigencias de tarjeta de circulación.';
COMMENT ON COLUMN tarjeta_circulacion.fecha_vigencia_fin IS 'Obligatorio. Fecha de vencimiento.';

CREATE INDEX idx_tarjeta_vehiculo ON tarjeta_circulacion(id_vehiculo);
CREATE INDEX idx_tarjeta_vigencia ON tarjeta_circulacion(fecha_vigencia_fin);

/*=============================================================================
  15. TENENCIA
=============================================================================*/

CREATE TABLE tenencia (
    id_tenencia BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    anio_fiscal SMALLINT NOT NULL CHECK (anio_fiscal BETWEEN 1900 AND 2100),
    estatus_tenencia VARCHAR(30) NOT NULL,
    fecha_pago DATE,
    monto_tenencia NUMERIC(14,2),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tenencia_estatus CHECK (
        estatus_tenencia IN ('PAGADA', 'PENDIENTE', 'NO_APLICA', 'DESCONOCIDA')
    ),
    CONSTRAINT chk_tenencia_monto CHECK (monto_tenencia IS NULL OR monto_tenencia >= 0),
    CONSTRAINT uq_tenencia_vehiculo_anio UNIQUE (id_vehiculo, anio_fiscal)
);

COMMENT ON TABLE tenencia IS 'Entidad dependiente / histórica. Registra el estado de tenencia por vehículo y año fiscal.';
COMMENT ON COLUMN tenencia.estatus_tenencia IS 'Obligatorio. PAGADA, PENDIENTE, NO_APLICA o DESCONOCIDA.';

CREATE INDEX idx_tenencia_vehiculo ON tenencia(id_vehiculo);
CREATE INDEX idx_tenencia_anio ON tenencia(anio_fiscal);
CREATE INDEX idx_tenencia_estatus ON tenencia(estatus_tenencia);

/*=============================================================================
  16. ADEUDOS VEHICULARES
=============================================================================*/

CREATE TABLE adeudo_vehicular (
    id_adeudo BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    tipo_adeudo VARCHAR(80) NOT NULL,
    monto_adeudo NUMERIC(14,2),
    estatus_adeudo VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
    fecha_consulta DATE,
    observacion_adeudo TEXT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_adeudo_monto CHECK (monto_adeudo IS NULL OR monto_adeudo >= 0),
    CONSTRAINT chk_adeudo_estatus CHECK (
        estatus_adeudo IN ('SIN_ADEUDO', 'PENDIENTE', 'PAGADO', 'CANCELADO', 'DESCONOCIDO')
    )
);

COMMENT ON TABLE adeudo_vehicular IS 'Entidad dependiente / histórica. Registra adeudos, multas, pagos pendientes u obligaciones vehiculares.';
COMMENT ON COLUMN adeudo_vehicular.tipo_adeudo IS 'Obligatorio. Ejemplos: MULTA, TENENCIA, VERIFICACION, PLACAS, OTRO.';
COMMENT ON COLUMN adeudo_vehicular.monto_adeudo IS 'Opcional. Monto detectado.';
COMMENT ON COLUMN adeudo_vehicular.fecha_consulta IS 'Opcional. Fecha en que se consultó o detectó el adeudo.';

CREATE INDEX idx_adeudo_vehiculo ON adeudo_vehicular(id_vehiculo);
CREATE INDEX idx_adeudo_estatus ON adeudo_vehicular(estatus_adeudo);
CREATE INDEX idx_adeudo_tipo ON adeudo_vehicular(UPPER(tipo_adeudo));

/*=============================================================================
  17. OBSERVACIONES / BITÁCORA
=============================================================================*/

CREATE TABLE observacion (
    id_observacion BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo BIGINT NOT NULL REFERENCES vehiculo(id_vehiculo) ON UPDATE CASCADE ON DELETE CASCADE,
    id_asignacion_vehiculo BIGINT REFERENCES asignacion_vehiculo(id_asignacion_vehiculo) ON UPDATE CASCADE ON DELETE SET NULL,
    id_poliza_seguro BIGINT REFERENCES poliza_seguro(id_poliza_seguro) ON UPDATE CASCADE ON DELETE SET NULL,
    id_instalacion_gps BIGINT REFERENCES instalacion_gps(id_instalacion_gps) ON UPDATE CASCADE ON DELETE SET NULL,
    tipo_observacion VARCHAR(50) NOT NULL,
    texto_observacion TEXT NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT NOW(),
    autor_registro VARCHAR(120),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_observacion_tipo CHECK (
        tipo_observacion IN ('GENERAL', 'OPERATIVA', 'MECANICA', 'SEGURO', 'GPS', 'ADEUDO', 'SINIESTRO', 'DOCUMENTO')
    )
);

COMMENT ON TABLE observacion IS 'Entidad dependiente / histórica. Reemplaza columnas de comentarios del Excel y permite bitácora.';
COMMENT ON COLUMN observacion.tipo_observacion IS 'Obligatorio. Clasifica el comentario.';
COMMENT ON COLUMN observacion.texto_observacion IS 'Obligatorio. Texto de la observación.';
COMMENT ON COLUMN observacion.autor_registro IS 'Opcional. Usuario o persona que registró la observación.';

CREATE INDEX idx_observacion_vehiculo ON observacion(id_vehiculo);
CREATE INDEX idx_observacion_tipo ON observacion(tipo_observacion);
CREATE INDEX idx_observacion_fecha ON observacion(fecha_registro);

/*=============================================================================
  18. VISTAS PARA ATRIBUTOS DERIVADOS
=============================================================================*/

CREATE OR REPLACE VIEW vw_vehiculo_actual AS
SELECT
    v.id_vehiculo,
    v.numero_interno,
    ma.nombre_marca,
    mv.nombre_modelo_comercial,
    mv.version,
    v.anio_modelo,
    c.nombre_color,
    v.numero_serie,
    e.placas AS placas_actuales,
    ef.nombre_entidad AS entidad_emplacamiento_actual,
    CASE
        WHEN e.placas IS NULL THEN NULL
        ELSE CONCAT(
            mv.nombre_modelo_comercial,
            '|',
            v.anio_modelo,
            '|',
            UPPER(c.nombre_color),
            '|',
            UPPER(e.placas)
        )
    END AS clave_vehiculo,
    v.estatus_unidad,
    v.fecha_creacion,
    v.fecha_actualizacion
FROM vehiculo v
JOIN modelo_vehiculo mv ON mv.id_modelo_vehiculo = v.id_modelo_vehiculo
JOIN marca ma ON ma.id_marca = mv.id_marca
JOIN color c ON c.id_color = v.id_color
LEFT JOIN emplacamiento e ON e.id_vehiculo = v.id_vehiculo AND e.fecha_fin IS NULL
LEFT JOIN entidad_federativa ef ON ef.id_entidad_federativa = e.id_entidad_federativa;

COMMENT ON VIEW vw_vehiculo_actual IS 'Vista con datos actuales del vehículo. Incluye placas actuales y clave_vehiculo derivada.';

CREATE OR REPLACE VIEW vw_asignacion_actual AS
SELECT
    av.id_asignacion_vehiculo,
    av.id_vehiculo,
    p.id_persona AS id_conductor,
    p.nombre_completo AS conductor,
    orgp.nombre_organizacion AS plataforma,
    orgs.nombre_organizacion AS socio,
    av.cuenta,
    av.fecha_inicio,
    av.fecha_fin,
    CASE WHEN av.fecha_fin IS NULL THEN 'ACTIVA' ELSE 'FINALIZADA' END AS estatus_asignacion
FROM asignacion_vehiculo av
JOIN conductor co ON co.id_persona = av.id_conductor
JOIN persona p ON p.id_persona = co.id_persona
LEFT JOIN plataforma_operativa po ON po.id_organizacion = av.id_plataforma
LEFT JOIN organizacion orgp ON orgp.id_organizacion = po.id_organizacion
LEFT JOIN socio s ON s.id_organizacion = av.id_socio
LEFT JOIN organizacion orgs ON orgs.id_organizacion = s.id_organizacion
WHERE av.fecha_fin IS NULL;

COMMENT ON VIEW vw_asignacion_actual IS 'Vista derivada con asignación vigente de vehículo-conductor.';

CREATE OR REPLACE VIEW vw_documentacion_actual AS
WITH ultima_poliza AS (
    SELECT DISTINCT ON (id_vehiculo)
        id_vehiculo,
        id_poliza_seguro,
        numero_poliza,
        fecha_vigencia_fin
    FROM poliza_seguro
    ORDER BY id_vehiculo, fecha_vigencia_fin DESC, id_poliza_seguro DESC
),
ultima_verificacion AS (
    SELECT DISTINCT ON (id_vehiculo)
        id_vehiculo,
        id_verificacion,
        semestre,
        fecha_ultima_verificacion,
        fecha_limite_verificacion
    FROM verificacion_vehicular
    ORDER BY id_vehiculo, fecha_limite_verificacion DESC, id_verificacion DESC
),
ultima_tarjeta AS (
    SELECT DISTINCT ON (id_vehiculo)
        id_vehiculo,
        id_tarjeta_circulacion,
        fecha_vigencia_fin
    FROM tarjeta_circulacion
    ORDER BY id_vehiculo, fecha_vigencia_fin DESC, id_tarjeta_circulacion DESC
),
adeudos_pendientes AS (
    SELECT
        id_vehiculo,
        COUNT(*) AS cantidad_adeudos_pendientes,
        COALESCE(SUM(monto_adeudo), 0) AS monto_adeudos_pendientes
    FROM adeudo_vehicular
    WHERE estatus_adeudo = 'PENDIENTE'
    GROUP BY id_vehiculo
)
SELECT
    v.id_vehiculo,
    up.numero_poliza,
    up.fecha_vigencia_fin AS vigencia_poliza,
    uv.semestre AS semestre_verificacion,
    uv.fecha_ultima_verificacion,
    uv.fecha_limite_verificacion,
    ut.fecha_vigencia_fin AS vigencia_tarjeta_circulacion,
    COALESCE(ap.cantidad_adeudos_pendientes, 0) AS cantidad_adeudos_pendientes,
    COALESCE(ap.monto_adeudos_pendientes, 0) AS monto_adeudos_pendientes,
    CASE
        WHEN COALESCE(ap.cantidad_adeudos_pendientes, 0) > 0 THEN 'ROJO'
        WHEN up.fecha_vigencia_fin IS NOT NULL AND up.fecha_vigencia_fin < CURRENT_DATE THEN 'ROJO'
        WHEN uv.fecha_limite_verificacion IS NOT NULL AND uv.fecha_limite_verificacion < CURRENT_DATE THEN 'ROJO'
        WHEN ut.fecha_vigencia_fin IS NOT NULL AND ut.fecha_vigencia_fin < CURRENT_DATE THEN 'ROJO'
        WHEN up.fecha_vigencia_fin IS NOT NULL AND up.fecha_vigencia_fin <= CURRENT_DATE + INTERVAL '30 days' THEN 'AMARILLO'
        WHEN uv.fecha_limite_verificacion IS NOT NULL AND uv.fecha_limite_verificacion <= CURRENT_DATE + INTERVAL '30 days' THEN 'AMARILLO'
        WHEN ut.fecha_vigencia_fin IS NOT NULL AND ut.fecha_vigencia_fin <= CURRENT_DATE + INTERVAL '30 days' THEN 'AMARILLO'
        ELSE 'VERDE'
    END AS semaforo_documental
FROM vehiculo v
LEFT JOIN ultima_poliza up ON up.id_vehiculo = v.id_vehiculo
LEFT JOIN ultima_verificacion uv ON uv.id_vehiculo = v.id_vehiculo
LEFT JOIN ultima_tarjeta ut ON ut.id_vehiculo = v.id_vehiculo
LEFT JOIN adeudos_pendientes ap ON ap.id_vehiculo = v.id_vehiculo;

COMMENT ON VIEW vw_documentacion_actual IS 'Vista derivada con vencimientos, adeudos y semáforo documental de cada vehículo.';

CREATE OR REPLACE VIEW vw_ficha_vehiculo AS
SELECT
    va.id_vehiculo,
    va.numero_interno,
    va.clave_vehiculo,
    va.nombre_marca,
    va.nombre_modelo_comercial,
    va.version,
    va.anio_modelo,
    va.nombre_color,
    va.numero_serie,
    va.placas_actuales,
    va.entidad_emplacamiento_actual,
    aa.conductor,
    aa.plataforma,
    aa.socio,
    aa.cuenta,
    da.numero_poliza,
    da.vigencia_poliza,
    da.semestre_verificacion,
    da.fecha_ultima_verificacion,
    da.fecha_limite_verificacion,
    da.vigencia_tarjeta_circulacion,
    da.cantidad_adeudos_pendientes,
    da.monto_adeudos_pendientes,
    da.semaforo_documental,
    va.estatus_unidad
FROM vw_vehiculo_actual va
LEFT JOIN vw_asignacion_actual aa ON aa.id_vehiculo = va.id_vehiculo
LEFT JOIN vw_documentacion_actual da ON da.id_vehiculo = va.id_vehiculo;

COMMENT ON VIEW vw_ficha_vehiculo IS 'Vista integral para consulta. No sustituye a las tablas normalizadas.';

/*=============================================================================
  19. TRIGGERS DE ACTUALIZACIÓN
=============================================================================*/

CREATE TRIGGER trg_marca_fecha_actualizacion
BEFORE UPDATE ON marca
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_modelo_vehiculo_fecha_actualizacion
BEFORE UPDATE ON modelo_vehiculo
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_color_fecha_actualizacion
BEFORE UPDATE ON color
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_entidad_federativa_fecha_actualizacion
BEFORE UPDATE ON entidad_federativa
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_vehiculo_fecha_actualizacion
BEFORE UPDATE ON vehiculo
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_emplacamiento_fecha_actualizacion
BEFORE UPDATE ON emplacamiento
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_adquisicion_fecha_actualizacion
BEFORE UPDATE ON adquisicion
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_persona_fecha_actualizacion
BEFORE UPDATE ON persona
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_conductor_fecha_actualizacion
BEFORE UPDATE ON conductor
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_titular_poliza_fecha_actualizacion
BEFORE UPDATE ON titular_poliza
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_organizacion_fecha_actualizacion
BEFORE UPDATE ON organizacion
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_plataforma_operativa_fecha_actualizacion
BEFORE UPDATE ON plataforma_operativa
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_socio_fecha_actualizacion
BEFORE UPDATE ON socio
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_aseguradora_fecha_actualizacion
BEFORE UPDATE ON aseguradora
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_asignacion_vehiculo_fecha_actualizacion
BEFORE UPDATE ON asignacion_vehiculo
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_app_transporte_fecha_actualizacion
BEFORE UPDATE ON app_transporte
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_asignacion_app_fecha_actualizacion
BEFORE UPDATE ON asignacion_app
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_poliza_seguro_fecha_actualizacion
BEFORE UPDATE ON poliza_seguro
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_dispositivo_gps_fecha_actualizacion
BEFORE UPDATE ON dispositivo_gps
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_instalacion_gps_fecha_actualizacion
BEFORE UPDATE ON instalacion_gps
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_tag_telepeaje_fecha_actualizacion
BEFORE UPDATE ON tag_telepeaje
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_asignacion_tag_fecha_actualizacion
BEFORE UPDATE ON asignacion_tag
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_verificacion_vehicular_fecha_actualizacion
BEFORE UPDATE ON verificacion_vehicular
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_tarjeta_circulacion_fecha_actualizacion
BEFORE UPDATE ON tarjeta_circulacion
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_tenencia_fecha_actualizacion
BEFORE UPDATE ON tenencia
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_adeudo_vehicular_fecha_actualizacion
BEFORE UPDATE ON adeudo_vehicular
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

CREATE TRIGGER trg_observacion_fecha_actualizacion
BEFORE UPDATE ON observacion
FOR EACH ROW EXECUTE FUNCTION flotilla.fn_set_fecha_actualizacion();

/*=============================================================================
  20. DATOS BASE OPCIONALES
=============================================================================*/

INSERT INTO app_transporte (nombre_app)
VALUES ('UBER'), ('DIDI')
ON CONFLICT (nombre_app) DO NOTHING;

INSERT INTO color (nombre_color)
VALUES ('NEGRO'), ('BLANCO'), ('GRIS'), ('PLATA'), ('AZUL'), ('ROJO')
ON CONFLICT (nombre_color) DO NOTHING;

/*=============================================================================
  21. CONSULTAS DE PRUEBA SUGERIDAS
===============================================================================

-- Ficha integral de vehículos:
-- SELECT * FROM flotilla.vw_ficha_vehiculo;

-- Buscar por placas actuales:
-- SELECT *
-- FROM flotilla.vw_ficha_vehiculo
-- WHERE UPPER(placas_actuales) = UPPER('D40BKD');

-- Buscar por número de serie:
-- SELECT *
-- FROM flotilla.vw_ficha_vehiculo
-- WHERE numero_serie = 'NUMERO_SERIE_AQUI';

-- Vehículos con semáforo documental en rojo:
-- SELECT *
-- FROM flotilla.vw_ficha_vehiculo
-- WHERE semaforo_documental = 'ROJO';

=============================================================================*/
