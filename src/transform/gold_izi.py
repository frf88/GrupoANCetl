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


def build_fct_movimiento_inventario(con: duckdb.DuckDBPyConnection) -> None:
    # Mismo dato que fct_ventas_items (misma fuente, mismos filtros) pero solo
    # las columnas que necesita el dashboard de Inventarios. Es una vista, no
    # una copia, para que nunca se desincronice de fct_ventas_items.
    con.execute(
        """
        CREATE OR REPLACE VIEW gold.fct_movimiento_inventario AS
        SELECT fecha, producto, cantidad, codigo_inventario
        FROM gold.fct_ventas_items
        """
    )


def build_fct_mov_inv_omuh(con: duckdb.DuckDBPyConnection) -> None:
    # El endpoint /movimientos se llama solo con izi-contribuyente (sin
    # izi-sucursal), asi que trae movimientos a nivel contribuyente, no
    # exclusivos de omuH - se mantiene el nombre tal como lo tenia el usuario.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_mov_inv_omuh AS
        SELECT
            fecha::DATE AS fecha,
            cantidad,
            tipoMovimiento AS tipo_movimiento,
            codigoInventario AS codigo_inventario
        FROM raw.izi_movimientos
        WHERE tipoMovimiento = 'interna'
        """
    )


def build_fct_mov_inv_omuh_todos(con: duckdb.DuckDBPyConnection) -> None:
    # Igual a fct_mov_inv_omuh pero sin filtrar tipoMovimiento (equivalente a
    # "Mov Inv omuh (5)") - la necesita la medida DAX "Cortesias Anc Beb"
    # (interna + prod-venta menos ventas).
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_mov_inv_omuh_todos AS
        SELECT
            fecha::DATE AS fecha,
            cantidad,
            tipoMovimiento AS tipo_movimiento,
            codigoInventario AS codigo_inventario
        FROM raw.izi_movimientos
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
