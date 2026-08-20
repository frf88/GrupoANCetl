import duckdb


def build_fct_gastos_compilados(con: duckdb.DuckDBPyConnection) -> None:
    # Replica la tabla "Gastos Compilados" del Power BI "Estados de
    # Resultados Ancestralrest S.R.L v2": 14 fuentes (bancos + cash + GS)
    # unificadas a un esquema comun. Cada rama replica el filtro/signo
    # exacto de su Power Query fuente (ver memoria estados-resultados-pnl
    # para el M code completo de cada una) - "bs" siempre queda como
    # magnitud POSITIVA de gasto; el signo negativo se aplica recien al
    # combinar con ingresos en gold_estados_resultados.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_gastos_compilados AS
        WITH bisa_ancestral AS (
            -- "Gastos Bisa Ancestral": Egreso, Importe Formateado * -1
            SELECT
                Fecha::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, "Importe Formateado" * -1 AS bs,
                'Bisa Ancestral' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_bisa_ancestral
            WHERE "Ingreso Egreso" = 'Egreso'
        ),
        bisa_explora AS (
            -- "Gastos Bisa Explora": misma hoja que Ingresos Asesorias
            -- (BisaAsesoria), filtrada al lado Egreso
            SELECT
                "Fecha Ajustada"::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, "Importe Formateado" * -1 AS bs,
                'Bisa Explora' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_bisa_explora
            WHERE "Ingreso Egreso" = 'Egreso'
        ),
        cash_ancestral AS (
            -- "Gastos Cash Ancestral": sin filtro Ingreso Egreso, excluye
            -- Fijo/Semanal/Otros = Cash/Transferencias, sin flip de signo
            SELECT
                Fecha::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, TRY_CAST(Bs AS DOUBLE) AS bs,
                'Cash Ancestral' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_caja_ancestral
            WHERE Empresa IS NOT NULL
              AND "Fijo/Semanal/Otros" NOT IN ('Cash', 'Transferencias')
        ),
        cash_omuh AS (
            -- "Gastos Cash omuh": solo Empresa=omuh y Fijo/Semanal
            SELECT
                Fecha::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, TRY_CAST(Bs AS DOUBLE) AS bs,
                'Cash omuh' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_caja_omuh
            WHERE Empresa = 'omuh'
              AND "Fijo/Semanal/Otros" IN ('Fijo', 'Semanal')
        ),
        bcp_omuh AS (
            -- "Gastos Cuenta BCP omuh": Bs<0 en el extracto (negativo=
            -- egreso), excluye ERROR/Cash, se toma valor absoluto
            SELECT
                Fecha1::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, ABS(Monto) AS bs,
                'BCP omuh' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_bcp_omuh
            WHERE Monto < 0
              AND "Fijo/Semanal/Otros" NOT IN ('ERROR', 'Error', 'Cash')
        ),
        bcp_bodas AS (
            -- "Gastos Cuenta BCP bodas": igual patron que BCP omuh
            SELECT
                Fecha1::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, ABS(Monto) AS bs,
                'BCP catering' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_bcp_bodas
            WHERE Monto < 0
              AND "Fijo/Semanal/Otros" NOT IN ('ERROR', 'Error', 'Cash')
              AND Categoria IS NOT NULL
        ),
        cash_ancestral_gs AS (
            -- "Gastos Cash Ancestral GS": CSV manual, sin flip de signo
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, TRY_CAST(Bs AS DOUBLE) AS bs,
                'Cash Ancestral GS' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_cash_ancestral_gs
            WHERE Empresa IS NOT NULL
        ),
        cash_omuh_gs AS (
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, TRY_CAST(Bs AS DOUBLE) AS bs,
                'Cash omuH GS' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_cash_omuh_gs
            WHERE Empresa IS NOT NULL
        ),
        fortaleza_ancestral_gs AS (
            -- "Gastos Fortaleza Ancestral GS": Egreso, Importe Formateado * -1
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, "Importe Formateado" * -1 AS bs,
                'Fortaleza Ancestral GS' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_fortaleza_ancestral_gs
            WHERE "Ingreso Egreso" = 'Egreso' AND Categoria IS NOT NULL
        ),
        fortaleza_omuh_gs AS (
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, "Importe Formateado" * -1 AS bs,
                'Fortaleza omuh GS' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_fortaleza_omuh_gs
            WHERE "Ingreso Egreso" = 'Egreso' AND Categoria IS NOT NULL
        ),
        bnb_ancestral_gs AS (
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, "Importe Formateado" * -1 AS bs,
                'BNB Ancestral GS' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_bnb_ancestral_gs
            WHERE "Ingreso Egreso" = 'Egreso' AND Categoria IS NOT NULL
        ),
        bnb_omuh_gs AS (
            SELECT
                STRPTIME(Fecha, '%-d-%b-%Y')::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, "Importe Formateado" * -1 AS bs,
                'BNB omuh GS' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_bnb_omuh_gs
            WHERE "Ingreso Egreso" = 'Egreso' AND Categoria IS NOT NULL
        ),
        us_ancestral AS (
            -- "Gastos $us Ancestral" (hoja "Pagos $us" / tabla AncestralDolar):
            -- sin Ingreso Egreso (toda la hoja son egresos), sin flip de signo
            SELECT
                Fecha::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, Bs AS bs,
                '$us Ancestral' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_us_ancestral
            WHERE Empresa IS NOT NULL
        ),
        aproximados AS (
            -- "Gastos Aproximados": ver src/load/raw_gastos_aproximados.py -
            -- solo el primer bloque de la hoja (hoy: solo Ancestral)
            SELECT
                Fecha::DATE AS fecha, Categoria AS categoria,
                "Categoria FC" AS categoria_fc, "Categoria Detalle" AS categoria_detalle,
                Detalle AS detalle, TRY_CAST(Bs AS DOUBLE) AS bs,
                'Gastos Aproximados' AS cuenta, Empresa AS empresa,
                "Fijo/Semanal/Otros" AS fijo_semanal_otros
            FROM raw.gastos_aproximados
        ),
        combinado AS (
            SELECT * FROM bisa_ancestral
            UNION ALL SELECT * FROM bisa_explora
            UNION ALL SELECT * FROM cash_ancestral
            UNION ALL SELECT * FROM cash_omuh
            UNION ALL SELECT * FROM bcp_omuh
            UNION ALL SELECT * FROM bcp_bodas
            UNION ALL SELECT * FROM cash_ancestral_gs
            UNION ALL SELECT * FROM cash_omuh_gs
            UNION ALL SELECT * FROM fortaleza_ancestral_gs
            UNION ALL SELECT * FROM fortaleza_omuh_gs
            UNION ALL SELECT * FROM bnb_ancestral_gs
            UNION ALL SELECT * FROM bnb_omuh_gs
            UNION ALL SELECT * FROM us_ancestral
            UNION ALL SELECT * FROM aproximados
        )
        SELECT * FROM combinado
        WHERE fecha >= DATE '2021-01-01'
        """
    )
