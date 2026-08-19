import duckdb


def build_fct_reconciliacion_bebidas_omuh(con: duckdb.DuckDBPyConnection) -> None:
    # Formulas confirmadas leyendo las medidas DAX reales del modelo Power BI
    # (tabla "03omuh", carpeta "Omuh Beb"): Inv/Inv.-7/Compras/Cierre/Dif, mas
    # el detalle de Ventas Totales = Vtas iZi (con multiplicadores especiales
    # por SKU) + Vtas PedidosYa + Vtas Extras + Vtas iZi Ancestral (SKUs
    # compartidos entre negocios) - Cortesias.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_reconciliacion_bebidas_omuh AS
        WITH conteos_diarios AS (
            SELECT cod_producto, producto, fecha, AVG(cantidad) AS cantidad
            FROM gold.fct_inventario_omuh
            WHERE cod_producto IS NOT NULL AND cod_producto != ''
            GROUP BY cod_producto, producto, fecha
        ),
        conteos AS (
            SELECT
                cod_producto,
                producto,
                fecha AS fecha_cierre,
                cantidad AS cierre,
                LAG(fecha) OVER (PARTITION BY cod_producto ORDER BY fecha) AS fecha_inicio,
                LAG(cantidad) OVER (PARTITION BY cod_producto ORDER BY fecha) AS inv_inicial
            FROM conteos_diarios
        ),
        ultimo_conteo AS (
            -- Semana en curso: sin cierre todavia, se usa el ultimo conteo
            -- conocido como inicio y avance parcial hasta hoy.
            SELECT cod_producto, producto, fecha + INTERVAL '7 days' AS fecha_cierre, CAST(NULL AS DOUBLE) AS cierre,
                   fecha AS fecha_inicio, cantidad AS inv_inicial
            FROM (
                SELECT cod_producto, producto, fecha, cantidad,
                       ROW_NUMBER() OVER (PARTITION BY cod_producto ORDER BY fecha DESC) AS rn
                FROM conteos_diarios
                WHERE cantidad IS NOT NULL
            ) t
            WHERE rn = 1
        ),
        semanas AS (
            SELECT * FROM conteos WHERE fecha_inicio IS NOT NULL AND cierre IS NOT NULL
            UNION ALL
            SELECT * FROM ultimo_conteo
        ),
        compras AS (
            SELECT cod_producto, fecha, cantidad
            FROM gold.fct_compras_insumos_omuh
            WHERE cod_producto IS NOT NULL AND cod_producto != ''
        ),
        vtas_izi AS (
            SELECT
                codigo_inventario AS cod_producto,
                fecha,
                CASE
                    WHEN producto = 'Chop Cerveza' THEN cantidad * 0.75
                    WHEN producto = 'Chop Cerveza 2X1' THEN cantidad * 1.5
                    WHEN codigo_inventario = 'OMU00052' THEN cantidad * 0.5
                    WHEN codigo_inventario = 'OMU00053' THEN cantidad * 0.5
                    WHEN codigo_inventario = 'OMU00071' THEN cantidad * 0.5
                    WHEN codigo_inventario = 'OMU00068' THEN 0
                    ELSE cantidad
                END AS cantidad
            FROM gold.fct_ventas_items
            WHERE negocio = 'omuH'
        ),
        vtas_py AS (
            SELECT cod_producto, fecha, cantidad
            FROM gold.fct_ventas_omuh_pedidosya
            WHERE cod_producto IS NOT NULL
        ),
        vtas_ext AS (
            SELECT COALESCE(d2.cod_producto, e.value) AS cod_producto, e.fecha, e.cantidad
            FROM gold.fct_extras_izi_omuh e
            LEFT JOIN gold.dim_producto_izi d2 ON e.producto2 = d2.producto
        ),
        vtas_anc_izi AS (
            SELECT
                codigo_inventario AS cod_producto,
                fecha,
                CASE
                    WHEN codigo_inventario = 'OMU00052' THEN cantidad * 0.5
                    WHEN codigo_inventario = 'OMU00053' THEN cantidad * 0.5
                    ELSE cantidad
                END AS cantidad
            FROM gold.fct_ventas_items
            WHERE negocio = 'Ancestral'
        ),
        cortesias AS (
            SELECT codigo_inventario AS cod_producto, fecha, cantidad
            FROM gold.fct_mov_inv_omuh_todos
            WHERE tipo_movimiento = 'interna'
        ),
        base AS (
            SELECT
                s.cod_producto,
                s.producto,
                s.fecha_inicio,
                s.fecha_cierre,
                s.inv_inicial,
                COALESCE((SELECT SUM(cantidad) FROM compras c WHERE c.cod_producto = s.cod_producto AND c.fecha > s.fecha_inicio AND c.fecha <= s.fecha_cierre), 0) AS compras,
                COALESCE((SELECT SUM(cantidad) FROM vtas_izi v WHERE v.cod_producto = s.cod_producto AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS vtas_izi,
                COALESCE((SELECT SUM(cantidad) FROM vtas_py v WHERE v.cod_producto = s.cod_producto AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS vtas_py,
                COALESCE((SELECT SUM(cantidad) FROM vtas_ext v WHERE v.cod_producto = s.cod_producto AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS vtas_ext,
                COALESCE((SELECT SUM(cantidad) FROM vtas_anc_izi v WHERE v.cod_producto = s.cod_producto AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS vtas_anc,
                COALESCE((SELECT SUM(cantidad) FROM cortesias c WHERE c.cod_producto = s.cod_producto AND c.fecha > s.fecha_inicio AND c.fecha <= s.fecha_cierre), 0) AS cortesias,
                s.cierre
            FROM semanas s
        )
        SELECT
            producto,
            cod_producto,
            strftime(fecha_cierre, '%Y.%m.%d') AS semana,
            fecha_inicio,
            fecha_cierre,
            inv_inicial,
            compras,
            vtas_izi AS vtas,
            vtas_anc,
            vtas_py,
            vtas_ext,
            cortesias,
            vtas_izi + vtas_anc + vtas_py + vtas_ext AS ventas_totales,
            inv_inicial + compras - (vtas_izi + vtas_anc + vtas_py + vtas_ext) - cortesias AS inv_calculado,
            cierre,
            cierre - (inv_inicial + compras - (vtas_izi + vtas_anc + vtas_py + vtas_ext) - cortesias) AS diferencia
        FROM base
        """
    )


def build_fct_reconciliacion_bebidas_omuh_diario(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_reconciliacion_bebidas_omuh_diario AS
        WITH semanas AS (
            SELECT producto, cod_producto, semana, fecha_inicio, fecha_cierre, inv_inicial, cierre
            FROM gold.fct_reconciliacion_bebidas_omuh
        ),
        dias AS (
            SELECT
                s.producto, s.cod_producto, s.semana, s.fecha_inicio, s.fecha_cierre, s.inv_inicial, s.cierre,
                d.fecha::DATE AS fecha
            FROM semanas s, generate_series(s.fecha_inicio + INTERVAL '1 day', LEAST(s.fecha_cierre, CURRENT_DATE), INTERVAL '1 day') AS d(fecha)
        ),
        compras AS (
            SELECT cod_producto, fecha, cantidad
            FROM gold.fct_compras_insumos_omuh
            WHERE cod_producto IS NOT NULL AND cod_producto != ''
        ),
        vtas_izi AS (
            SELECT
                codigo_inventario AS cod_producto, fecha,
                CASE
                    WHEN producto = 'Chop Cerveza' THEN cantidad * 0.75
                    WHEN producto = 'Chop Cerveza 2X1' THEN cantidad * 1.5
                    WHEN codigo_inventario = 'OMU00052' THEN cantidad * 0.5
                    WHEN codigo_inventario = 'OMU00053' THEN cantidad * 0.5
                    WHEN codigo_inventario = 'OMU00071' THEN cantidad * 0.5
                    WHEN codigo_inventario = 'OMU00068' THEN 0
                    ELSE cantidad
                END AS cantidad
            FROM gold.fct_ventas_items WHERE negocio = 'omuH'
        ),
        vtas_py AS (
            SELECT cod_producto, fecha, cantidad FROM gold.fct_ventas_omuh_pedidosya WHERE cod_producto IS NOT NULL
        ),
        vtas_ext AS (
            SELECT COALESCE(d2.cod_producto, e.value) AS cod_producto, e.fecha, e.cantidad
            FROM gold.fct_extras_izi_omuh e
            LEFT JOIN gold.dim_producto_izi d2 ON e.producto2 = d2.producto
        ),
        vtas_anc_izi AS (
            SELECT
                codigo_inventario AS cod_producto, fecha,
                CASE
                    WHEN codigo_inventario = 'OMU00052' THEN cantidad * 0.5
                    WHEN codigo_inventario = 'OMU00053' THEN cantidad * 0.5
                    ELSE cantidad
                END AS cantidad
            FROM gold.fct_ventas_items WHERE negocio = 'Ancestral'
        ),
        cortesias AS (
            SELECT codigo_inventario AS cod_producto, fecha, cantidad
            FROM gold.fct_mov_inv_omuh_todos WHERE tipo_movimiento = 'interna'
        ),
        detalle AS (
            SELECT
                d.producto,
                d.semana,
                d.fecha,
                strftime(d.fecha, '%a') AS dia,
                d.inv_inicial,
                d.cierre,
                d.fecha = d.fecha_inicio + INTERVAL '1 day' AS es_primer_dia,
                d.fecha = d.fecha_cierre AS es_ultimo_dia,
                COALESCE((SELECT SUM(cantidad) FROM compras c WHERE c.cod_producto = d.cod_producto AND c.fecha = d.fecha), 0) AS compras,
                COALESCE((SELECT SUM(cantidad) FROM vtas_izi v WHERE v.cod_producto = d.cod_producto AND v.fecha = d.fecha), 0) AS vtas,
                COALESCE((SELECT SUM(cantidad) FROM vtas_anc_izi v WHERE v.cod_producto = d.cod_producto AND v.fecha = d.fecha), 0) AS vtas_anc,
                COALESCE((SELECT SUM(cantidad) FROM vtas_py v WHERE v.cod_producto = d.cod_producto AND v.fecha = d.fecha), 0) AS vtas_py,
                COALESCE((SELECT SUM(cantidad) FROM vtas_ext v WHERE v.cod_producto = d.cod_producto AND v.fecha = d.fecha), 0) AS vtas_ext,
                COALESCE((SELECT SUM(cantidad) FROM cortesias c WHERE c.cod_producto = d.cod_producto AND c.fecha = d.fecha), 0) AS cortesias
            FROM dias d
        )
        SELECT
            producto,
            semana,
            fecha,
            dia,
            compras,
            vtas,
            vtas_anc,
            vtas_py,
            vtas_ext,
            cortesias,
            inv_inicial
                + SUM(compras - (vtas + vtas_anc + vtas_py + vtas_ext) - cortesias) OVER (
                    PARTITION BY producto, semana ORDER BY fecha
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS inv_dia_esperado,
            CASE WHEN es_primer_dia THEN inv_inicial WHEN es_ultimo_dia THEN cierre END AS inv_ini_fin,
            CASE WHEN es_ultimo_dia THEN
                cierre - (inv_inicial
                    + SUM(compras - (vtas + vtas_anc + vtas_py + vtas_ext) - cortesias) OVER (
                        PARTITION BY producto, semana ORDER BY fecha
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ))
            END AS diferencia
        FROM detalle
        ORDER BY producto, fecha
        """
    )
