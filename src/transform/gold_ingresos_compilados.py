import duckdb


def build_fct_ingresos_compilados(con: duckdb.DuckDBPyConnection) -> None:
    # Replica "Ingresos Compilados" del Power BI "Estados de Resultados
    # Ancestralrest S.R.L v2": ~9 sub-fuentes unificadas a
    # (fecha, total, negocio, canal, canal2_bodas). Ver memoria
    # estados-resultados-pnl para el M code completo de cada una.
    #
    # OJO - 2 hallazgos del modelo real, replicados a proposito (no
    # "corregidos") para que los totales calcen con el Power BI vigente:
    #   1. "Ventas GS Delivery" no aporta nada al total: su Power Query
    #      produce una columna "Bs" pero "Ingresos GS Total Restaurante"
    #      selecciona solo la columna "Total" al combinar, así que el
    #      ingreso de Delivery queda en null/0 en el modelo actual.
    #   2. Fuente iZi de omuH usa el monto de FACTURA (montoTotal), no la
    #      suma de items via UNNEST - distinto del patron de
    #      gold_ventas_generales.build_fct_ventas_diarias_negocio.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_ingresos_compilados AS
        WITH ventas_gs_salon AS (
            -- "Ventas GS Salon" = Actual (Fecha > 2025-01-01) + Pasadas (sin filtro)
            SELECT fecha, SUM(total) AS total
            FROM (
                SELECT
                    STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha,
                    TRY_CAST(REPLACE(Total, ',', '') AS DOUBLE) AS total
                FROM raw.registro_mesas_ancestral
                WHERE STRPTIME(Fecha, '%-d-%b-%Y')::DATE > DATE '2025-01-01'
                UNION ALL
                SELECT
                    STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha,
                    TRY_CAST(REPLACE(Total, ',', '') AS DOUBLE) AS total
                FROM raw.registro_mesas_ancestral_historico
            ) t
            GROUP BY fecha
        ),
        ventas_gs_eventos AS (
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha,
                TRY_CAST(REPLACE(CAST(Total AS VARCHAR), ',', '') AS DOUBLE) AS total
            FROM raw.ingresos_ventas_gs_eventos
            WHERE Fecha IS NOT NULL
        ),
        ventas_gs_delivery AS (
            -- Ver nota arriba: no aporta al total real (columna "Bs" se
            -- descarta al combinar) - se deja la fecha con total=0 para
            -- no perder trazabilidad de la fuente.
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha,
                0.0 AS total
            FROM raw.ingresos_ventas_gs_delivery
            WHERE Fecha IS NOT NULL
        ),
        gs_total_restaurante AS (
            SELECT fecha, SUM(total) AS total, 'Ancestral' AS negocio, 'Ancestral GS Total Restaurante' AS canal, CAST(NULL AS VARCHAR) AS canal2_bodas
            FROM (
                SELECT * FROM ventas_gs_salon
                UNION ALL SELECT * FROM ventas_gs_eventos
                UNION ALL SELECT * FROM ventas_gs_delivery
            ) t
            GROUP BY fecha
        ),
        eventos_bodas AS (
            -- "Ingresos Eventos Bodas": Negocio=Catering, Canal=Catering,
            -- Canal2 Bodas = Nombre del evento
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha,
                TRY_CAST(REPLACE(CAST(Bs AS VARCHAR), ',', '') AS DOUBLE) AS total,
                'Catering' AS negocio, 'Catering' AS canal, Nombre AS canal2_bodas
            FROM raw.ingresos_eventos_bodas
            WHERE Fecha IS NOT NULL
        ),
        odoo_omuh AS (
            SELECT date_order::DATE AS fecha, SUM("Total Bs") AS total, 'omuh' AS negocio, 'omuH Odoo' AS canal, CAST(NULL AS VARCHAR) AS canal2_bodas
            FROM raw.ingresos_fac_ventas_omuh_odoo
            GROUP BY date_order
        ),
        pedidosya_omuh AS (
            SELECT fecha, SUM(total_bs) AS total, 'omuh' AS negocio, 'omuH PedidosYa' AS canal, CAST(NULL AS VARCHAR) AS canal2_bodas
            FROM gold.fct_pedidosya_pedidos
            GROUP BY fecha
        ),
        eventos_omuh AS (
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha,
                SUM(TRY_CAST(REPLACE(CAST(Total AS VARCHAR), ',', '') AS DOUBLE)) AS total,
                'omuh' AS negocio, 'omuH Eventos' AS canal, CAST(NULL AS VARCHAR) AS canal2_bodas
            FROM raw.ingresos_ventas_omuh_eventos
            WHERE Fecha IS NOT NULL
            GROUP BY STRPTIME(Fecha, '%-d-%b-%Y')::DATE
        ),
        izi_omuh AS (
            -- "fuente_iZi_omuH": monto de factura (montoTotal), no suma
            -- de items - se usa raw.izi_facturas en vez del login
            -- hardcodeado que tiene el Power Query original
            SELECT
                (fechaPago - INTERVAL '4 hours')::DATE AS fecha,
                SUM(montoTotal) AS total, 'omuh' AS negocio, 'omuh iZi' AS canal, CAST(NULL AS VARCHAR) AS canal2_bodas
            FROM raw.izi_facturas
            WHERE anulada = 0 AND _negocio = 'omuH'
            GROUP BY (fechaPago - INTERVAL '4 hours')::DATE
        ),
        asesorias AS (
            -- "Ingresos Asesorias": misma hoja que Bisa Explora
            -- (BisaAsesoria), lado Ingreso, solo EXPLORA 1/23/26
            SELECT
                "Fecha Ajustada"::DATE AS fecha,
                "Importe Formateado" AS total,
                'Asesoria' AS negocio, 'Asesoria' AS canal, CAST(NULL AS VARCHAR) AS canal2_bodas
            FROM raw.gastos_bisa_explora
            WHERE "Ingreso Egreso" = 'Ingreso'
              AND "Fijo/Semanal/Otros" IN ('EXPLORA 1', 'EXPLORA 23', 'EXPLORA 26')
        ),
        combinado AS (
            SELECT * FROM gs_total_restaurante
            UNION ALL SELECT * FROM eventos_bodas
            UNION ALL SELECT * FROM odoo_omuh
            UNION ALL SELECT * FROM pedidosya_omuh
            UNION ALL SELECT * FROM eventos_omuh
            UNION ALL SELECT * FROM izi_omuh
            UNION ALL SELECT * FROM asesorias
        )
        SELECT * FROM combinado
        WHERE fecha >= DATE '2021-01-01'
        """
    )
