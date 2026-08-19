import duckdb


def build_fct_reconciliacion_bebidas_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    # Formula de Cortesias confirmada leyendo la medida DAX real del modelo
    # Power BI ("Cortesias Anc Beb"): movimientos interna+prod-venta menos
    # ventas directas (misma fuente que "Vtas Anc Beb": fac_ventas_Ancestral_iZi).
    # La resta solo aplica si el producto tuvo movimientos ese periodo (ej.
    # vinos nunca los tienen) - sin este resguardo, productos sin movimientos
    # quedaban con Cortesias = -Ventas en vez de 0 (bug detectado en Vinos).
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
        ultimo_conteo AS (
            -- Semana en curso: todavia no hay conteo de cierre (se hace los
            -- domingos), asi que se arma con el ultimo conteo conocido como
            -- inicio, avance parcial hasta hoy, y cierre en blanco.
            SELECT producto, categoria, fecha + INTERVAL '7 days' AS fecha_cierre, CAST(NULL AS DOUBLE) AS cierre,
                   fecha AS fecha_inicio, cantidad AS inv_inicial
            FROM (
                SELECT producto, categoria, fecha, cantidad,
                       ROW_NUMBER() OVER (PARTITION BY producto ORDER BY fecha DESC) AS rn
                FROM gold.fct_inventario_fisico
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
        movimientos_cortesia AS (
            SELECT UPPER(dp.producto) AS producto, m.fecha, m.cantidad
            FROM gold.fct_mov_inv_omuh_todos m
            JOIN gold.dim_producto dp ON dp.codigo_inventario = m.codigo_inventario
            WHERE m.tipo_movimiento IN ('interna', 'prod-venta')
        ),
        salidas AS (
            -- "Salidas" en Bebidas/Vinos = medida DAX "Ap Copas/Bajas" =
            -- SUM('Apertura Vinos por Copa'[#Botellas]), NO fct_salidas_mermas
            -- (esa tabla es para Insumos). Union via Cod Producto, no nombre.
            SELECT UPPER(dp.producto) AS producto, a.fecha, a.num_botellas AS cantidad
            FROM gold.fct_apertura_vinos_copa a
            JOIN gold.dim_producto_izi dp ON a.codigo_producto = dp.cod_producto
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
                CASE WHEN EXISTS (SELECT 1 FROM movimientos_cortesia mc WHERE mc.producto = UPPER(s.producto) AND mc.fecha > s.fecha_inicio AND mc.fecha <= s.fecha_cierre)
                    THEN COALESCE((SELECT SUM(cantidad) FROM movimientos_cortesia mc WHERE mc.producto = UPPER(s.producto) AND mc.fecha > s.fecha_inicio AND mc.fecha <= s.fecha_cierre), 0)
                        - COALESCE((SELECT SUM(cantidad) FROM ventas_directas v WHERE v.producto = UPPER(s.producto) AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0)
                    ELSE 0
                END AS cortesias,
                COALESCE((SELECT SUM(cantidad) FROM salidas sa WHERE sa.producto = UPPER(s.producto) AND sa.fecha > s.fecha_inicio AND sa.fecha <= s.fecha_cierre), 0) AS salidas,
                s.cierre
            FROM semanas s
        )
        SELECT
            producto,
            categoria,
            strftime(fecha_cierre, '%Y.%m.%d') AS semana,
            fecha_inicio,
            fecha_cierre,
            inv_inicial,
            compras,
            ventas,
            ventas_ext,
            cortesias,
            salidas,
            cierre,
            ventas + ventas_ext + cortesias AS ventas_totales,
            inv_inicial + compras - (ventas + ventas_ext + cortesias) - salidas AS inv_calculado,
            cierre - (inv_inicial + compras - (ventas + ventas_ext + cortesias) - salidas) AS diferencia
        FROM base
        """
    )


def build_fct_reconciliacion_bebidas_ancestral_diario(con: duckdb.DuckDBPyConnection) -> None:
    # Desglose dia a dia dentro de cada semana ya calculada en
    # fct_reconciliacion_bebidas_ancestral, con el inventario esperado
    # corriendo (Inv Dia Esp = saldo acumulado dia a dia desde el inv inicial).
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_reconciliacion_bebidas_ancestral_diario AS
        WITH semanas AS (
            SELECT producto, categoria, semana, fecha_inicio, fecha_cierre, inv_inicial, cierre
            FROM gold.fct_reconciliacion_bebidas_ancestral
        ),
        dias AS (
            SELECT
                s.producto,
                s.categoria,
                s.semana,
                s.fecha_inicio,
                s.fecha_cierre,
                s.inv_inicial,
                s.cierre,
                d.fecha::DATE AS fecha
            FROM semanas s, generate_series(s.fecha_inicio + INTERVAL '1 day', LEAST(s.fecha_cierre, CURRENT_DATE), INTERVAL '1 day') AS d(fecha)
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
        movimientos_cortesia AS (
            SELECT UPPER(dp.producto) AS producto, m.fecha, m.cantidad
            FROM gold.fct_mov_inv_omuh_todos m
            JOIN gold.dim_producto dp ON dp.codigo_inventario = m.codigo_inventario
            WHERE m.tipo_movimiento IN ('interna', 'prod-venta')
        ),
        salidas AS (
            -- "Salidas" en Bebidas/Vinos = medida DAX "Ap Copas/Bajas" =
            -- SUM('Apertura Vinos por Copa'[#Botellas]), NO fct_salidas_mermas
            -- (esa tabla es para Insumos). Union via Cod Producto, no nombre.
            SELECT UPPER(dp.producto) AS producto, a.fecha, a.num_botellas AS cantidad
            FROM gold.fct_apertura_vinos_copa a
            JOIN gold.dim_producto_izi dp ON a.codigo_producto = dp.cod_producto
        ),
        detalle AS (
            SELECT
                d.producto,
                d.categoria,
                d.semana,
                d.fecha,
                strftime(d.fecha, '%a') AS dia,
                d.inv_inicial,
                d.cierre,
                d.fecha = d.fecha_inicio + INTERVAL '1 day' AS es_primer_dia,
                d.fecha = d.fecha_cierre AS es_ultimo_dia,
                COALESCE((SELECT SUM(cantidad) FROM compras c WHERE c.producto = UPPER(d.producto) AND c.fecha = d.fecha), 0) AS compras,
                COALESCE((SELECT SUM(cantidad) FROM ventas_directas v WHERE v.producto = UPPER(d.producto) AND v.fecha = d.fecha), 0)
                    + COALESCE((SELECT SUM(cantidad) FROM ventas_indirectas v WHERE v.producto = UPPER(d.producto) AND v.fecha = d.fecha), 0) AS ventas,
                COALESCE((SELECT SUM(cantidad) FROM ventas_ext v WHERE v.producto = UPPER(d.producto) AND v.fecha = d.fecha), 0) AS ventas_ext,
                CASE WHEN EXISTS (SELECT 1 FROM movimientos_cortesia mc WHERE mc.producto = UPPER(d.producto) AND mc.fecha = d.fecha)
                    THEN COALESCE((SELECT SUM(cantidad) FROM movimientos_cortesia mc WHERE mc.producto = UPPER(d.producto) AND mc.fecha = d.fecha), 0)
                        - COALESCE((SELECT SUM(cantidad) FROM ventas_directas v WHERE v.producto = UPPER(d.producto) AND v.fecha = d.fecha), 0)
                    ELSE 0
                END AS cortesias,
                COALESCE((SELECT SUM(cantidad) FROM salidas sa WHERE sa.producto = UPPER(d.producto) AND sa.fecha = d.fecha), 0) AS salidas
            FROM dias d
        )
        SELECT
            producto,
            categoria,
            semana,
            fecha,
            dia,
            compras,
            cortesias,
            ventas,
            ventas_ext,
            salidas,
            inv_inicial
                + SUM(compras - ventas - ventas_ext - cortesias - salidas) OVER (
                    PARTITION BY producto, semana ORDER BY fecha
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS inv_dia_esperado,
            CASE WHEN es_primer_dia THEN inv_inicial WHEN es_ultimo_dia THEN cierre END AS inv_ini_fin,
            CASE WHEN es_ultimo_dia THEN
                cierre - (inv_inicial
                    + SUM(compras - ventas - ventas_ext - cortesias - salidas) OVER (
                        PARTITION BY producto, semana ORDER BY fecha
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ))
            END AS diferencia
        FROM detalle
        ORDER BY producto, fecha
        """
    )
