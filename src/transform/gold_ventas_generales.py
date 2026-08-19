import duckdb


def build_fct_pedidosya_pedidos(con: duckdb.DuckDBPyConnection) -> None:
    # Replica la medida DAX "Total Bs" de la tabla "Pedidos Ya": ingreso neto
    # de PedidosYa despues de descontar su comision (18% hasta 24-sep-2024,
    # 22% hasta 24-oct-2024, 25% despues), formula: (Total-Descuento) * (1 - Fee/0.87)
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_pedidosya_pedidos AS
        WITH base AS (
            SELECT
                "Fecha del pedido"::DATE AS fecha,
                TRY_CAST(REPLACE("Total del pedido", ',', '.') AS DOUBLE) AS total_pedido,
                COALESCE(TRY_CAST(REPLACE("Descuento total", ',', '.') AS DOUBLE), 0) AS descuento_total
            FROM raw.pedidosya_ventas
            WHERE "Estado del pedido" = 'Entregado'
        )
        SELECT
            fecha,
            (total_pedido - descuento_total) AS total_inicial_bs,
            (total_pedido - descuento_total) * (
                1 - (
                    CASE
                        WHEN fecha < DATE '2024-09-24' THEN 0.18
                        WHEN fecha <= DATE '2024-10-24' THEN 0.22
                        ELSE 0.25
                    END
                ) / 0.87
            ) AS total_bs
        FROM base
        WHERE fecha IS NOT NULL AND total_pedido IS NOT NULL
        """
    )


def build_fct_ventas_diarias_negocio(con: duckdb.DuckDBPyConnection) -> None:
    # "Vtas Bs" del Dashboard General: ventas iZi (Ancestral+omuH) + PedidosYa
    # (omuH), a nivel dia x negocio - insumo para el pivot de Ventas.
    # Usa raw.izi_facturas directo (no gold.fct_ventas_items) porque esa
    # tabla excluye AN000046 - regla valida para inventario pero no para el
    # total de ventas reportado (medida DAX "Vtas Bs" no excluye nada).
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_ventas_diarias_negocio AS
        WITH izi AS (
            SELECT
                (fechaPago - INTERVAL '4 hours')::DATE AS fecha,
                _negocio AS negocio,
                SUM(item.precioTotal) AS vtas_bs
            FROM raw.izi_facturas, UNNEST(listaItems) AS t(item)
            WHERE anulada = 0
            GROUP BY (fechaPago - INTERVAL '4 hours')::DATE, _negocio
        ),
        pedidosya AS (
            SELECT fecha, 'omuH' AS negocio, SUM(total_bs) AS vtas_bs
            FROM gold.fct_pedidosya_pedidos
            GROUP BY fecha
        ),
        combinado AS (
            SELECT fecha, negocio, vtas_bs FROM izi
            UNION ALL
            SELECT fecha, negocio, vtas_bs FROM pedidosya
        )
        SELECT
            fecha,
            negocio,
            strftime(fecha, '%G%V') AS semana_ano,
            SUM(vtas_bs) AS vtas_bs
        FROM combinado
        GROUP BY fecha, negocio, strftime(fecha, '%G%V')
        """
    )
