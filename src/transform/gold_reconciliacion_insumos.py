import duckdb


def build_dim_promedio_peso_porcion_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    # Replica la tabla calculada "PromedioSinOutliers" del Power BI original:
    # para cada insumo, toma las compras de los ultimos 60 dias con Peso Real
    # y Porciones ambos conocidos, calcula peso-por-porcion, y promedia
    # excluyendo outliers (fuera de +-2 desviaciones estandar). Sirve para
    # convertir peso -> porciones cuando una compra o salida no trae el
    # numero de porciones directamente.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.dim_promedio_peso_porcion_ancestral AS
        WITH muestras AS (
            SELECT
                "Producto" AS producto,
                "Peso Real" / "Porciones" AS peso_x_porcion
            FROM raw.compras_insumos_ancestral
            WHERE "Porciones" IS NOT NULL
              AND "Peso Real" IS NOT NULL
              AND "Porciones" != 0
              AND TRY_STRPTIME("Fecha", '%d-%b-%Y')::DATE >= CURRENT_DATE - INTERVAL '60 days'
        ),
        stats AS (
            SELECT
                producto,
                AVG(peso_x_porcion) AS media,
                STDDEV_POP(peso_x_porcion) AS desv
            FROM muestras
            GROUP BY producto
        )
        SELECT
            m.producto,
            AVG(m.peso_x_porcion) AS promedio_peso_x_porcion
        FROM muestras m
        JOIN stats s ON m.producto = s.producto
        WHERE m.peso_x_porcion BETWEEN s.media - 2 * s.desv AND s.media + 2 * s.desv
        GROUP BY m.producto
        """
    )


def build_fct_consumo_insumos_ancestral_todos(con: duckdb.DuckDBPyConnection) -> None:
    # Igual a fct_consumo_insumos_ancestral pero sin exigir Cod Insumo propio
    # (necesaria para el calculo general de Ventas de insumos, replica la
    # medida DAX "Vtas Anc Ins": ventas del producto vendido x factor de
    # receta, sumado para TODOS los insumos de la matriz, no solo los que
    # se controlan como stock individual).
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_consumo_insumos_ancestral_todos AS
        SELECT
            m.fecha,
            r.insumo,
            r.cod_producto,
            r.producto,
            m.cantidad AS cantidad_vendida,
            r.cantidad AS factor_receta,
            m.cantidad * r.cantidad AS cantidad_consumida
        FROM gold.fct_movimiento_inventario m
        JOIN gold.dim_receta_ancestral r ON m.codigo_inventario = r.cod_producto
        """
    )


def build_fct_reconciliacion_insumos_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_reconciliacion_insumos_ancestral AS
        WITH conteos_diarios AS (
            SELECT producto, fecha, AVG(cantidad) AS cantidad
            FROM gold.fct_inventario_unitarios_gs
            GROUP BY producto, fecha
        ),
        conteos AS (
            SELECT
                producto,
                fecha AS fecha_cierre,
                cantidad AS cierre,
                LAG(fecha) OVER (PARTITION BY producto ORDER BY fecha) AS fecha_inicio,
                LAG(cantidad) OVER (PARTITION BY producto ORDER BY fecha) AS inv_inicial
            FROM conteos_diarios
        ),
        ultimo_conteo AS (
            -- Semana en curso: sin cierre todavia, se usa el ultimo conteo
            -- conocido como inicio y avance parcial hasta hoy.
            SELECT producto, fecha + INTERVAL '7 days' AS fecha_cierre, CAST(NULL AS DOUBLE) AS cierre,
                   fecha AS fecha_inicio, cantidad AS inv_inicial
            FROM (
                SELECT producto, fecha, cantidad,
                       ROW_NUMBER() OVER (PARTITION BY producto ORDER BY fecha DESC) AS rn
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
            SELECT
                UPPER(ci."Producto") AS producto,
                TRY_STRPTIME(ci."Fecha", '%d-%b-%Y')::DATE AS fecha,
                COALESCE(ci."Porciones", ROUND(ci."Peso Real" / p.promedio_peso_x_porcion, 0)) AS cantidad
            FROM raw.compras_insumos_ancestral ci
            LEFT JOIN gold.dim_promedio_peso_porcion_ancestral p ON ci."Producto" = p.producto
            WHERE ci."Empresa" = 'Ancestral' AND ci."Fecha" IS NOT NULL AND ci."Fecha" != ''
        ),
        ventas AS (
            SELECT UPPER(insumo) AS producto, fecha, SUM(cantidad_consumida) AS cantidad
            FROM gold.fct_consumo_insumos_ancestral_todos
            GROUP BY UPPER(insumo), fecha
        ),
        salidas AS (
            SELECT
                UPPER(sm.producto) AS producto,
                sm.fecha,
                COALESCE(sm.porciones, sm.peso / p.promedio_peso_x_porcion) AS cantidad
            FROM gold.fct_salidas_mermas_ancestral sm
            LEFT JOIN gold.dim_promedio_peso_porcion_ancestral p ON sm.producto = p.producto
        ),
        base AS (
            SELECT
                s.producto,
                s.fecha_inicio,
                s.fecha_cierre,
                s.inv_inicial,
                COALESCE((SELECT SUM(cantidad) FROM compras c WHERE c.producto = UPPER(s.producto) AND c.fecha > s.fecha_inicio AND c.fecha <= s.fecha_cierre), 0) AS compras,
                COALESCE((SELECT SUM(cantidad) FROM ventas v WHERE v.producto = UPPER(s.producto) AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS ventas,
                COALESCE((SELECT SUM(cantidad) FROM salidas sa WHERE sa.producto = UPPER(s.producto) AND sa.fecha > s.fecha_inicio AND sa.fecha <= s.fecha_cierre), 0) AS salidas,
                s.cierre
            FROM semanas s
        )
        SELECT
            producto,
            strftime(fecha_cierre, '%Y.%m.%d') AS semana,
            fecha_inicio,
            fecha_cierre,
            inv_inicial,
            compras,
            ventas,
            salidas,
            inv_inicial + compras - ventas - salidas AS inv_calculado,
            cierre,
            cierre - (inv_inicial + compras - ventas - salidas) AS diferencia
        FROM base
        """
    )


def build_fct_reconciliacion_insumos_ancestral_diario(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_reconciliacion_insumos_ancestral_diario AS
        WITH semanas AS (
            SELECT producto, semana, fecha_inicio, fecha_cierre, inv_inicial, cierre
            FROM gold.fct_reconciliacion_insumos_ancestral
        ),
        dias AS (
            SELECT
                s.producto, s.semana, s.fecha_inicio, s.fecha_cierre, s.inv_inicial, s.cierre,
                d.fecha::DATE AS fecha
            FROM semanas s, generate_series(s.fecha_inicio + INTERVAL '1 day', LEAST(s.fecha_cierre, CURRENT_DATE), INTERVAL '1 day') AS d(fecha)
        ),
        compras AS (
            SELECT
                UPPER(ci."Producto") AS producto,
                TRY_STRPTIME(ci."Fecha", '%d-%b-%Y')::DATE AS fecha,
                COALESCE(ci."Porciones", ROUND(ci."Peso Real" / p.promedio_peso_x_porcion, 0)) AS cantidad
            FROM raw.compras_insumos_ancestral ci
            LEFT JOIN gold.dim_promedio_peso_porcion_ancestral p ON ci."Producto" = p.producto
            WHERE ci."Empresa" = 'Ancestral' AND ci."Fecha" IS NOT NULL AND ci."Fecha" != ''
        ),
        ventas AS (
            SELECT UPPER(insumo) AS producto, fecha, SUM(cantidad_consumida) AS cantidad
            FROM gold.fct_consumo_insumos_ancestral_todos
            GROUP BY UPPER(insumo), fecha
        ),
        salidas AS (
            SELECT
                UPPER(sm.producto) AS producto,
                sm.fecha,
                COALESCE(sm.porciones, sm.peso / p.promedio_peso_x_porcion) AS cantidad
            FROM gold.fct_salidas_mermas_ancestral sm
            LEFT JOIN gold.dim_promedio_peso_porcion_ancestral p ON sm.producto = p.producto
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
                COALESCE((SELECT SUM(cantidad) FROM compras c WHERE c.producto = UPPER(d.producto) AND c.fecha = d.fecha), 0) AS compras,
                COALESCE((SELECT SUM(cantidad) FROM ventas v WHERE v.producto = UPPER(d.producto) AND v.fecha = d.fecha), 0) AS ventas,
                COALESCE((SELECT SUM(cantidad) FROM salidas sa WHERE sa.producto = UPPER(d.producto) AND sa.fecha = d.fecha), 0) AS salidas
            FROM dias d
        )
        SELECT
            producto,
            semana,
            fecha,
            dia,
            compras,
            ventas,
            salidas,
            inv_inicial
                + SUM(compras - ventas - salidas) OVER (
                    PARTITION BY producto, semana ORDER BY fecha
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS inv_dia_esperado,
            CASE WHEN es_primer_dia THEN inv_inicial WHEN es_ultimo_dia THEN cierre END AS inv_ini_fin,
            CASE WHEN es_ultimo_dia THEN
                cierre - (inv_inicial
                    + SUM(compras - ventas - salidas) OVER (
                        PARTITION BY producto, semana ORDER BY fecha
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ))
            END AS diferencia
        FROM detalle
        ORDER BY producto, fecha
        """
    )
