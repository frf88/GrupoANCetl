import duckdb


def build_dim_relacion_copa_vino(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.dim_relacion_copa_vino AS
        SELECT
            "Categoria" AS categoria,
            "Cod. Producto" AS cod_producto,
            "Producto" AS producto,
            "Botella" AS botella,
            "Cod Botella" AS cod_botella
        FROM raw.relacion_copa_vino
        WHERE "Cod Botella" != ''
        """
    )


def build_fct_copas_vino_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_copas_vino_ancestral AS
        SELECT
            v.fecha,
            v.producto,
            v.cantidad,
            v.codigo_inventario,
            r.cod_botella
        FROM gold.fct_ventas_items v
        JOIN gold.dim_relacion_copa_vino r ON v.codigo_inventario = r.cod_producto
        WHERE v.negocio = 'Ancestral'
        """
    )
