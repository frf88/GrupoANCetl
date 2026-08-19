import duckdb

# Mapeo real leido de la columna calculada "Categoria Carnes" en Dim_Producto_iZi
# (Power BI): asigna cada codigo de producto vendido a su insumo. No usa la
# matriz de recetas (esa tabla esta practicamente vacia para omuH).
_INSUMO_POR_CODIGO = {
    # Nombres en mayusculas: se comparan con UPPER(producto) del conteo
    # fisico (gold.fct_inventario_unitarios_omuh), no con el nombre "bonito"
    # de la columna calculada de Power BI.
    "CARNE MOLIDA": [
        "OMU00011", "OMU00010", "OMU00009", "OMU00008", "OMU00058", "OMU00007",
        "OMU00006", "OMU00049", "OMU00005", "OMU00066", "OMU00072", "OMU00061",
        "OMU00054", "OMU00055", "OMU00064", "ANC00066", "OMU00052", "OMU00071",
        "OMU00065", "OMU00063", "OMU00062", "OMU00082",
    ],
    "PECHUGA DE POLLO": [
        "OMU00031", "OMU00057", "OMU00030", "OMU00029", "OMU00028", "OMU00027",
        "OMU00026", "OMU00051", "OMU00078", "OMU00079", "OMU00085",
    ],
    "PESCA AMAZONICA": ["OMU00059"],
    "QUESO": ["OMU00068"],
}


def build_dim_insumo_omuh(con: duckdb.DuckDBPyConnection) -> None:
    rows = [
        (codigo, insumo) for insumo, codigos in _INSUMO_POR_CODIGO.items() for codigo in codigos
    ]
    con.execute("CREATE OR REPLACE TABLE gold.dim_insumo_omuh (cod_producto VARCHAR, insumo VARCHAR)")
    con.executemany("INSERT INTO gold.dim_insumo_omuh VALUES (?, ?)", rows)


def build_fct_reconciliacion_insumos_omuh(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_reconciliacion_insumos_omuh AS
        WITH conteos_diarios AS (
            SELECT UPPER(producto) AS producto, fecha, AVG(cantidad) AS cantidad
            FROM gold.fct_inventario_unitarios_omuh
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
            SELECT UPPER("Producto") AS producto, TRY_STRPTIME("Fecha", '%d-%b-%Y')::DATE AS fecha, "Porciones" AS cantidad
            FROM raw.compras_insumos_omuh
        ),
        salidas AS (
            SELECT UPPER(producto) AS producto, fecha, porciones AS cantidad
            FROM gold.fct_salidas_mermas_omuh
        ),
        vtas_izi AS (
            SELECT
                d.insumo AS producto,
                v.fecha,
                CASE
                    WHEN v.producto = 'Chop Cerveza' THEN v.cantidad * 0.75
                    WHEN v.producto = 'Chop Cerveza 2X1' THEN v.cantidad * 1.5
                    WHEN v.codigo_inventario IN ('OMU00052', 'OMU00053', 'OMU00071') THEN v.cantidad * 0.5
                    WHEN v.codigo_inventario = 'OMU00068' THEN 0
                    ELSE v.cantidad
                END AS cantidad
            FROM gold.fct_ventas_items v
            JOIN gold.dim_insumo_omuh d ON v.codigo_inventario = d.cod_producto
            WHERE v.negocio = 'omuH'
        ),
        vtas_py AS (
            SELECT
                d.insumo AS producto,
                p.fecha,
                CASE
                    WHEN p.producto IN ('Super Smash Burger', 'Carne Extra Super Smash Burger') THEN p.cantidad * 0.5
                    ELSE p.cantidad
                END AS cantidad
            FROM gold.fct_ventas_omuh_pedidosya p
            JOIN gold.dim_insumo_omuh d ON p.cod_producto = d.cod_producto
        ),
        vtas_anc_izi AS (
            SELECT
                d.insumo AS producto,
                v.fecha,
                CASE WHEN v.codigo_inventario IN ('OMU00052', 'OMU00053') THEN v.cantidad * 0.5 ELSE v.cantidad END AS cantidad
            FROM gold.fct_ventas_items v
            JOIN gold.dim_insumo_omuh d ON v.codigo_inventario = d.cod_producto
            WHERE v.negocio = 'Ancestral'
        ),
        cortesias AS (
            SELECT d.insumo AS producto, m.fecha, m.cantidad
            FROM gold.fct_mov_inv_omuh_todos m
            JOIN gold.dim_insumo_omuh d ON m.codigo_inventario = d.cod_producto
            WHERE m.tipo_movimiento = 'interna'
        ),
        base AS (
            SELECT
                s.producto,
                s.fecha_inicio,
                s.fecha_cierre,
                s.inv_inicial,
                COALESCE((SELECT SUM(cantidad) FROM compras c WHERE c.producto = UPPER(s.producto) AND c.fecha > s.fecha_inicio AND c.fecha <= s.fecha_cierre), 0) AS compras,
                COALESCE((SELECT SUM(cantidad) FROM vtas_izi v WHERE v.producto = s.producto AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS vtas,
                COALESCE((SELECT SUM(cantidad) FROM vtas_py v WHERE v.producto = s.producto AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS vtas_py,
                COALESCE((SELECT SUM(cantidad) FROM vtas_anc_izi v WHERE v.producto = s.producto AND v.fecha > s.fecha_inicio AND v.fecha <= s.fecha_cierre), 0) AS vtas_anc,
                COALESCE((SELECT SUM(cantidad) FROM cortesias c WHERE c.producto = s.producto AND c.fecha > s.fecha_inicio AND c.fecha <= s.fecha_cierre), 0) AS cortesias,
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
            vtas,
            vtas_anc,
            vtas_py,
            cortesias,
            salidas,
            vtas + vtas_anc + vtas_py + cortesias + salidas AS ventas_totales,
            inv_inicial + compras - (vtas + vtas_anc + vtas_py + cortesias + salidas) AS inv_calculado,
            cierre,
            cierre - (inv_inicial + compras - (vtas + vtas_anc + vtas_py + cortesias + salidas)) AS diferencia
        FROM base
        """
    )


def build_fct_reconciliacion_insumos_omuh_diario(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_reconciliacion_insumos_omuh_diario AS
        WITH semanas AS (
            SELECT producto, semana, fecha_inicio, fecha_cierre, inv_inicial, cierre
            FROM gold.fct_reconciliacion_insumos_omuh
        ),
        dias AS (
            SELECT
                s.producto, s.semana, s.fecha_inicio, s.fecha_cierre, s.inv_inicial, s.cierre,
                d.fecha::DATE AS fecha
            FROM semanas s, generate_series(s.fecha_inicio + INTERVAL '1 day', LEAST(s.fecha_cierre, CURRENT_DATE), INTERVAL '1 day') AS d(fecha)
        ),
        compras AS (
            SELECT UPPER("Producto") AS producto, TRY_STRPTIME("Fecha", '%d-%b-%Y')::DATE AS fecha, "Porciones" AS cantidad
            FROM raw.compras_insumos_omuh
        ),
        salidas AS (
            SELECT UPPER(producto) AS producto, fecha, porciones AS cantidad
            FROM gold.fct_salidas_mermas_omuh
        ),
        vtas_izi AS (
            SELECT
                d.insumo AS producto, v.fecha,
                CASE
                    WHEN v.producto = 'Chop Cerveza' THEN v.cantidad * 0.75
                    WHEN v.producto = 'Chop Cerveza 2X1' THEN v.cantidad * 1.5
                    WHEN v.codigo_inventario IN ('OMU00052', 'OMU00053', 'OMU00071') THEN v.cantidad * 0.5
                    WHEN v.codigo_inventario = 'OMU00068' THEN 0
                    ELSE v.cantidad
                END AS cantidad
            FROM gold.fct_ventas_items v
            JOIN gold.dim_insumo_omuh d ON v.codigo_inventario = d.cod_producto
            WHERE v.negocio = 'omuH'
        ),
        vtas_py AS (
            SELECT
                d.insumo AS producto, p.fecha,
                CASE
                    WHEN p.producto IN ('Super Smash Burger', 'Carne Extra Super Smash Burger') THEN p.cantidad * 0.5
                    ELSE p.cantidad
                END AS cantidad
            FROM gold.fct_ventas_omuh_pedidosya p
            JOIN gold.dim_insumo_omuh d ON p.cod_producto = d.cod_producto
        ),
        vtas_anc_izi AS (
            SELECT
                d.insumo AS producto, v.fecha,
                CASE WHEN v.codigo_inventario IN ('OMU00052', 'OMU00053') THEN v.cantidad * 0.5 ELSE v.cantidad END AS cantidad
            FROM gold.fct_ventas_items v
            JOIN gold.dim_insumo_omuh d ON v.codigo_inventario = d.cod_producto
            WHERE v.negocio = 'Ancestral'
        ),
        cortesias AS (
            SELECT d.insumo AS producto, m.fecha, m.cantidad
            FROM gold.fct_mov_inv_omuh_todos m
            JOIN gold.dim_insumo_omuh d ON m.codigo_inventario = d.cod_producto
            WHERE m.tipo_movimiento = 'interna'
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
                COALESCE((SELECT SUM(cantidad) FROM vtas_izi v WHERE v.producto = d.producto AND v.fecha = d.fecha), 0) AS vtas,
                COALESCE((SELECT SUM(cantidad) FROM vtas_py v WHERE v.producto = d.producto AND v.fecha = d.fecha), 0) AS vtas_py,
                COALESCE((SELECT SUM(cantidad) FROM vtas_anc_izi v WHERE v.producto = d.producto AND v.fecha = d.fecha), 0) AS vtas_anc,
                COALESCE((SELECT SUM(cantidad) FROM cortesias c WHERE c.producto = d.producto AND c.fecha = d.fecha), 0) AS cortesias,
                COALESCE((SELECT SUM(cantidad) FROM salidas sa WHERE sa.producto = UPPER(d.producto) AND sa.fecha = d.fecha), 0) AS salidas
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
            cortesias,
            salidas,
            inv_inicial
                + SUM(compras - (vtas + vtas_anc + vtas_py + cortesias + salidas)) OVER (
                    PARTITION BY producto, semana ORDER BY fecha
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS inv_dia_esperado,
            CASE WHEN es_primer_dia THEN inv_inicial WHEN es_ultimo_dia THEN cierre END AS inv_ini_fin,
            CASE WHEN es_ultimo_dia THEN
                cierre - (inv_inicial
                    + SUM(compras - (vtas + vtas_anc + vtas_py + cortesias + salidas)) OVER (
                        PARTITION BY producto, semana ORDER BY fecha
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ))
            END AS diferencia
        FROM detalle
        ORDER BY producto, fecha
        """
    )
