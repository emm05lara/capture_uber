from django.db import migrations


SQL_VW_VEHICULO_ACTUAL = """
CREATE OR REPLACE VIEW vw_vehiculo_actual AS
SELECT
    v.id                                            AS id_vehiculo,
    v.numero_interno,
    ma.nombre_marca,
    mv.nombre_modelo_comercial,
    mv.version,
    v.anio_modelo,
    c.nombre_color,
    v.numero_serie,
    e.placas                                        AS placas_actuales,
    ef.nombre_entidad                               AS entidad_emplacamiento_actual,
    CASE
        WHEN e.placas IS NULL THEN NULL
        ELSE CONCAT(
            mv.nombre_modelo_comercial, '|',
            v.anio_modelo,             '|',
            UPPER(c.nombre_color),     '|',
            UPPER(e.placas)
        )
    END                                             AS clave_vehiculo,
    v.estatus_unidad,
    v.fecha_creacion,
    v.fecha_actualizacion
FROM vehiculos_vehiculo v
JOIN catalogos_modelovehiculo mv  ON mv.id  = v.modelo_vehiculo_id
JOIN catalogos_marca ma            ON ma.id  = mv.marca_id
JOIN catalogos_color c             ON c.id   = v.color_id
LEFT JOIN vehiculos_emplacamiento e
       ON e.vehiculo_id = v.id AND e.fecha_fin IS NULL
LEFT JOIN catalogos_entidadfederativa ef
       ON ef.id = e.entidad_federativa_id;
"""

SQL_VW_ASIGNACION_ACTUAL = """
CREATE OR REPLACE VIEW vw_asignacion_actual AS
SELECT
    av.id                                           AS id_asignacion_vehiculo,
    av.vehiculo_id                                  AS id_vehiculo,
    av.conductor_id                                 AS id_conductor,
    p.nombre_completo                               AS conductor,
    orgp.nombre_organizacion                        AS plataforma,
    orgs.nombre_organizacion                        AS socio,
    av.cuenta,
    av.fecha_inicio,
    av.fecha_fin,
    CASE
        WHEN av.fecha_fin IS NULL THEN 'ACTIVA'
        ELSE 'FINALIZADA'
    END                                             AS estatus_asignacion
FROM operacion_asignacionvehiculo av
JOIN actores_persona p              ON p.id    = av.conductor_id
LEFT JOIN actores_organizacion orgp ON orgp.id = av.plataforma_id
LEFT JOIN actores_organizacion orgs ON orgs.id = av.socio_id
WHERE av.fecha_fin IS NULL;
"""

SQL_VW_DOCUMENTACION_ACTUAL = """
CREATE OR REPLACE VIEW vw_documentacion_actual AS
WITH ultima_poliza AS (
    SELECT DISTINCT ON (vehiculo_id)
        vehiculo_id,
        id                              AS id_poliza_seguro,
        numero_poliza,
        fecha_vigencia_fin
    FROM vehiculos_polizaseguro
    ORDER BY vehiculo_id, fecha_vigencia_fin DESC, id DESC
),
ultima_verificacion AS (
    SELECT DISTINCT ON (vehiculo_id)
        vehiculo_id,
        id                              AS id_verificacion,
        semestre,
        fecha_ultima_verificacion,
        fecha_limite_verificacion
    FROM vehiculos_verificacionvehicular
    ORDER BY vehiculo_id, fecha_limite_verificacion DESC, id DESC
),
ultima_tarjeta AS (
    SELECT DISTINCT ON (vehiculo_id)
        vehiculo_id,
        id                              AS id_tarjeta_circulacion,
        fecha_vigencia_fin
    FROM vehiculos_tarjetacirculacion
    ORDER BY vehiculo_id, fecha_vigencia_fin DESC, id DESC
),
adeudos_pendientes AS (
    SELECT
        vehiculo_id,
        COUNT(*)                        AS cantidad_adeudos_pendientes,
        COALESCE(SUM(monto_adeudo), 0)  AS monto_adeudos_pendientes
    FROM vehiculos_adeudovehicular
    WHERE estatus_adeudo = 'PENDIENTE'
    GROUP BY vehiculo_id
)
SELECT
    v.id                                AS id_vehiculo,
    up.numero_poliza,
    up.fecha_vigencia_fin               AS vigencia_poliza,
    uv.semestre                         AS semestre_verificacion,
    uv.fecha_ultima_verificacion,
    uv.fecha_limite_verificacion,
    ut.fecha_vigencia_fin               AS vigencia_tarjeta_circulacion,
    COALESCE(ap.cantidad_adeudos_pendientes, 0) AS cantidad_adeudos_pendientes,
    COALESCE(ap.monto_adeudos_pendientes,   0) AS monto_adeudos_pendientes,
    CASE
        WHEN COALESCE(ap.cantidad_adeudos_pendientes, 0) > 0 THEN 'ROJO'
        WHEN up.fecha_vigencia_fin IS NOT NULL
             AND up.fecha_vigencia_fin < CURRENT_DATE THEN 'ROJO'
        WHEN uv.fecha_limite_verificacion IS NOT NULL
             AND uv.fecha_limite_verificacion < CURRENT_DATE THEN 'ROJO'
        WHEN ut.fecha_vigencia_fin IS NOT NULL
             AND ut.fecha_vigencia_fin < CURRENT_DATE THEN 'ROJO'
        WHEN up.fecha_vigencia_fin IS NOT NULL
             AND up.fecha_vigencia_fin <= CURRENT_DATE + INTERVAL '30 days' THEN 'AMARILLO'
        WHEN uv.fecha_limite_verificacion IS NOT NULL
             AND uv.fecha_limite_verificacion <= CURRENT_DATE + INTERVAL '30 days' THEN 'AMARILLO'
        WHEN ut.fecha_vigencia_fin IS NOT NULL
             AND ut.fecha_vigencia_fin <= CURRENT_DATE + INTERVAL '30 days' THEN 'AMARILLO'
        ELSE 'VERDE'
    END                                 AS semaforo_documental
FROM vehiculos_vehiculo v
LEFT JOIN ultima_poliza up        ON up.vehiculo_id = v.id
LEFT JOIN ultima_verificacion uv  ON uv.vehiculo_id = v.id
LEFT JOIN ultima_tarjeta ut       ON ut.vehiculo_id = v.id
LEFT JOIN adeudos_pendientes ap   ON ap.vehiculo_id = v.id;
"""

SQL_VW_FICHA_VEHICULO = """
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
LEFT JOIN vw_asignacion_actual aa    ON aa.id_vehiculo = va.id_vehiculo
LEFT JOIN vw_documentacion_actual da ON da.id_vehiculo = va.id_vehiculo;
"""

REVERSE_SQL = """
DROP VIEW IF EXISTS vw_ficha_vehiculo;
DROP VIEW IF EXISTS vw_documentacion_actual;
DROP VIEW IF EXISTS vw_asignacion_actual;
DROP VIEW IF EXISTS vw_vehiculo_actual;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("vehiculos", "0003_observacion_fk_asignacion_vehiculo"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL_VW_VEHICULO_ACTUAL,      reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=SQL_VW_ASIGNACION_ACTUAL,    reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=SQL_VW_DOCUMENTACION_ACTUAL, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=SQL_VW_FICHA_VEHICULO,       reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=migrations.RunSQL.noop,      reverse_sql=REVERSE_SQL),
    ]
