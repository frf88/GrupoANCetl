import duckdb

# Tabla estatica "Orden EERR" del Power BI "Estados de Resultados
# Ancestralrest S.R.L v2" (Enter Data manual, no viene de ninguna fuente
# externa). calculos_eerr=1 marca las filas de subtotal acumulado
# (Margen Bruto, EBITDA, Resultado, Resultado Total).
ORDEN_EERR_ROWS = [
    ("Ingresos", 1, "Ingresos", 0, "1.01"),
    ("Compras", 2, "Compras", 0, "1.02"),
    ("Margen Bruto", 3, "Margen Bruto", 1, "1.03"),
    ("Salarios", 4, "Salarios Fijos", 0, "2.01"),
    ("Salarios", 4, "Salarios Semanales", 0, "2.02"),
    ("Salarios", 4, "Salarios Extras", 0, "2.03"),
    ("Salarios", 4, "Salarios Socios", 0, "2.04"),
    ("Costos", 5, "Costos Fijos", 0, "2.05"),
    ("Costos", 5, "Costos Variables", 0, "2.06"),
    ("Gastos Fijos", 6, "Servicios", 0, "2.07"),
    ("Gastos Fijos", 6, "Alquiler", 0, "2.08"),
    ("Gastos Variables", 7, "Gasto", 0, "2.09"),
    ("EBITDA", 8, "EBITDA", 1, "2.10"),
    ("Impuestos", 9, "Impuestos", 0, "3.01"),
    ("Aproximados", 10, "Aproximados", 0, "3.02"),
    ("Resultado", 11, "Resultado", 1, "3.03"),
    ("Inversion", 12, "Inversion", 0, "4.01"),
    ("Resultado Total", 13, "Resultado Total", 1, "4.02"),
]


def build_dim_orden_eerr(con: duckdb.DuckDBPyConnection) -> None:
    values = ", ".join(
        f"('{grupo}', {orden_grupo}, '{categoria}', {calculos}, '{orden}')"
        for grupo, orden_grupo, categoria, calculos, orden in ORDEN_EERR_ROWS
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE gold.dim_orden_eerr AS
        SELECT * FROM (VALUES {values})
            AS t(grupo_eerr, orden_grupo, categoria, calculos_eerr, orden)
        """
    )


def build_fct_estados_resultados(con: duckdb.DuckDBPyConnection) -> None:
    # Replica la medida DAX "Monto EERR": combina gastos (negados) +
    # ingresos (Categoria="Ingresos" fijo, igual que "Ingresos Compilados
    # new"), agrega por mes x categoria x negocio, y aplica el acumulado
    # de subtotal via SUM() OVER (mismo idioma de ventana que
    # gold_reconciliacion.build_fct_reconciliacion_bebidas_ancestral_diario).
    # Se excluye Categoria="Dividendos" igual que "Ingresos y Gastos
    # Compilados" en el Power BI real.
    #
    # "negocio" agrega una dimension que el Power BI original NO tiene
    # como vista separada (el P&L real es uno solo, combinado) pero SI
    # tiene disponible como columna en Gastos/Ingresos Compilados
    # (Empresa/Negocio) - se expone aca para poder filtrar el dashboard
    # por negocio sin inventar una categorizacion nueva. 'Todos' replica
    # exacto el P&L combinado original (ya validado contra Power BI).
    # El valor 'omuh' en la fuente de gastos viene con variantes de
    # mayuscula/espacio ("omuh", "omuh ", "Omuh") por como se cargo a
    # mano en el Google Sheet original - se normaliza SOLO para poder
    # agruparlas como el mismo negocio (TRIM+LOWER), sin tocar ningun
    # monto ni fecha.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_estados_resultados AS
        WITH combinado AS (
            SELECT fecha, categoria, bs * -1 AS bs, empresa AS negocio_raw
            FROM gold.fct_gastos_compilados
            UNION ALL
            SELECT fecha, 'Ingresos' AS categoria, total AS bs, negocio AS negocio_raw
            FROM gold.fct_ingresos_compilados
        ),
        normalizado AS (
            SELECT
                fecha, categoria, bs,
                CASE
                    WHEN LOWER(TRIM(negocio_raw)) = 'omuh' THEN 'omuh'
                    WHEN LOWER(TRIM(negocio_raw)) = 'ancestral' THEN 'Ancestral'
                    ELSE TRIM(negocio_raw)
                END AS negocio
            FROM combinado
            WHERE categoria <> 'Dividendos'
        ),
        con_todos AS (
            SELECT fecha, categoria, bs, negocio FROM normalizado
            UNION ALL
            SELECT fecha, categoria, bs, 'Todos' AS negocio FROM normalizado
        ),
        monthly_categoria AS (
            SELECT
                date_trunc('month', fecha)::DATE AS periodo,
                categoria, negocio,
                SUM(bs) AS monto
            FROM con_todos
            GROUP BY date_trunc('month', fecha)::DATE, categoria, negocio
        ),
        periodos_negocios AS (
            SELECT DISTINCT periodo, negocio FROM monthly_categoria
        ),
        grid AS (
            SELECT pn.periodo, pn.negocio, d.grupo_eerr, d.orden_grupo, d.categoria, d.calculos_eerr, d.orden
            FROM periodos_negocios pn
            CROSS JOIN gold.dim_orden_eerr d
        ),
        con_monto_directo AS (
            SELECT
                g.periodo, g.negocio, g.orden, g.grupo_eerr, g.categoria, g.calculos_eerr,
                COALESCE(m.monto, 0) AS monto_directo
            FROM grid g
            LEFT JOIN monthly_categoria m
                ON m.periodo = g.periodo AND m.categoria = g.categoria AND m.negocio = g.negocio
        )
        SELECT
            periodo, negocio, orden, grupo_eerr, categoria, calculos_eerr,
            CASE
                WHEN calculos_eerr = 0 THEN monto_directo
                ELSE SUM(monto_directo) OVER (
                    PARTITION BY periodo, negocio ORDER BY orden
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
            END AS monto
        FROM con_monto_directo
        ORDER BY periodo, negocio, orden
        """
    )
