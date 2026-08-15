import duckdb


def build_fct_reconciliacion_bebidas_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    # Cortesias no incluida todavia: la formula del usuario la calcula en DAX
    # a partir de movimientos "interna"+"prod-venta" menos ventas, y no esta
    # confirmada - queda en 0 por ahora, a ajustar cuando se defina bien.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_reconciliacion_bebidas_ancestral AS
        WITH conteos AS (
            SELECT
                producto,
                categoria,
                fecha AS fecha_cierre,
                cantidad AS cierre,
                LAG(fecha) OVER (PARTITION BY producto ORDER BY fecha) AS fecha_inicio,
                LAG(cantidad) OVER (PARTITION BY producto ORDER BY fecha) AS inv_inicial
            FROM gold.fct_inventario_fisico
        ),
        semanas AS (
            SELECT * FROM conteos WHERE fecha_inicio IS NOT NULL
        ),
        compras AS (
            SELECT UPPER(producto) AS producto, fecha, cantidad
            FROM gold.fct_compras_insumos_ancestral
        ),
        ventas_directas AS (
            SELECT UPPER(producto) AS producto, fecha, cantidad
            FROM gold.fct_ventas_items
            WHERE negocio = 'Ancestral'
        ),
        ventas_indirectas AS (
            SELECT UPPER(insumo) AS producto, fecha, cantidad_consumida AS cantidad
            FROM gold.fct_consumo_insumos_ancestral
        ),
        ventas_ext AS (
            SELECT UPPER(producto) AS producto, fecha, cantidad
            FROM gold.fct_pedidosya_items
        ),
        salidas AS (
            SELECT UPPER(producto) AS producto, fecha, porciones AS cantidad
            FROM gold.fct_salidas_mermas_ancestral
        ),
        base AS (
            SELECT
                s.producto,
                s.categoria,
                s.fecha_inicio,
                s.fecha_cierre,
                s.inv_inicial,
                COALESCE((SELECT SUM(cantidad) FROM compras c WHERE c.producto = UPPER(s.producto) AND c.fecha > s.fecha_inicio AND c.fecha <= s.fecha_cierre), 0) AS compras,
                COALESCE((SELECT SUM(cantidad) FROM ventas_directas v WHERE v.producto = UPPER(s.producto) AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0)
                    + COALESCE((SELECT SUM(cantidad) FROM ventas_indirectas v WHERE v.producto = UPPER(s.producto) AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS ventas,
                COALESCE((SELECT SUM(cantidad) FROM ventas_ext v WHERE v.producto = UPPER(s.producto) AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS ventas_ext,
                0 AS cortesias,
                COALESCE((SELECT SUM(cantidad) FROM salidas sa WHERE sa.producto = UPPER(s.producto) AND sa.fecha > s.fecha_inicio AND sa.fecha <= s.fecha_cierre), 0) AS salidas,
                s.cierre
            FROM semanas s
        )
        SELECT
            *,
            ventas + ventas_ext + cortesias AS ventas_totales,
            inv_inicial + compras - (ventas + ventas_ext + cortesias) - salidas AS inv_calculado,
            (inv_inicial + compras - (ventas + ventas_ext + cortesias) - salidas) - cierre AS diferencia
        FROM base
        """
    )
