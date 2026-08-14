import duckdb


def build_fct_ventas_items(con: duckdb.DuckDBPyConnection) -> None:
    # AN000046 se excluye solo para Ancestral: asi lo definia la Power Query
    # original de ese negocio (no aplica a omuH).
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_ventas_items AS
        SELECT
            (fechaPago - INTERVAL '4 hours')::DATE AS fecha,
            item.articulo AS producto,
            item.cantidad AS cantidad,
            _negocio AS negocio,
            item.codigoInventario AS codigo_inventario,
            item.precioTotal AS precio_total
        FROM raw.izi_facturas, UNNEST(listaItems) AS t(item)
        WHERE anulada = 0
          AND NOT (_negocio = 'Ancestral' AND item.codigoInventario = 'AN000046')
        """
    )


def build_dim_producto(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.dim_producto AS
        SELECT DISTINCT ON (codigo)
            codigo AS codigo_inventario,
            nombre AS producto,
            categoria.nombre AS categoria,
            precioUnitario AS precio_unitario,
            cantidad AS cantidad_stock
        FROM raw.izi_items_inventario
        """
    )
