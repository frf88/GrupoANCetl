import duckdb


def build_fct_compras_insumos_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_compras_insumos_ancestral AS
        SELECT
            COALESCE(
                TRY_STRPTIME(NULLIF("Fecha Porcion", ''), '%d-%b-%Y')::DATE,
                STRPTIME("Fecha", '%d-%b-%Y')::DATE
            ) AS fecha,
            "Cod Producto" AS cod_producto,
            "Categoria" AS categoria,
            "Producto" AS producto,
            "Medida" AS medida,
            "Porciones" AS porciones,
            "Peso Real" AS peso_real,
            "Cantidad Compra" AS cantidad,
            "Precio Unitario" AS precio_unitario,
            "Precio Total" AS precio_total,
            "Empresa" AS empresa,
            "Comentario" AS comentario
        FROM raw.compras_insumos_ancestral
        WHERE "Fecha" IS NOT NULL AND "Fecha" != ''
        """
    )


def build_fct_compras_insumos_omuh(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_compras_insumos_omuh AS
        SELECT
            COALESCE(
                TRY_STRPTIME(NULLIF("Fecha Porcion", ''), '%d-%b-%Y')::DATE,
                STRPTIME("Fecha", '%d-%b-%Y')::DATE
            ) AS fecha,
            "Cod Producto" AS cod_producto,
            "Categoria" AS categoria,
            "Producto" AS producto,
            "Medida" AS medida,
            "Porciones" AS porciones,
            "Peso Real" AS peso_real,
            "Peso Porcion" AS peso_porcion,
            "Cantidad Compra" AS cantidad,
            "Precio Unitario" AS precio_unitario,
            "Precio Total" AS precio_total,
            "Comentario" AS comentario
        FROM raw.compras_insumos_omuh
        WHERE "Fecha" IS NOT NULL AND "Fecha" != ''
        """
    )


def build_fct_compras_totales_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_compras_totales_ancestral AS
        SELECT
            c.*,
            p.cantidad AS cantidad_plato
        FROM gold.fct_compras_insumos_ancestral c
        LEFT JOIN gold.pesos_platos_ancestral p ON c.cod_producto = p.cod_producto
        """
    )


def build_dim_compras_precios_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    # Precio Compra = promedio ponderado de los ultimos 120 dias. Nota: la
    # Power Query original eliminaba esta columna junto con la intermedia
    # "Precio" en el mismo paso (bug de tipeo) - acá se conserva, ya que
    # Dim_Producto_iZi depende de ella para el join.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.dim_compras_precios_ancestral AS
        SELECT
            cod_producto,
            SUM(cantidad) AS cantidad,
            SUM(precio_total) / SUM(cantidad) AS precio_compra
        FROM gold.fct_compras_insumos_ancestral
        WHERE cod_producto IS NOT NULL AND cod_producto != ''
          AND fecha >= CURRENT_DATE - INTERVAL '120 days'
        GROUP BY cod_producto
        """
    )


def build_dim_producto_izi(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.dim_producto_izi AS
        WITH base AS (
            SELECT DISTINCT ON (codigo)
                TRIM(codigo) AS cod_producto,
                nombre AS producto,
                categoria.nombre AS categoria
            FROM raw.izi_items_inventario
        ),
        filtrado AS (
            SELECT * FROM base
            WHERE NOT starts_with(cod_producto, 'i')
              AND NOT starts_with(cod_producto, 'I')
              AND cod_producto NOT IN ('0003698', '002628', '15185151', '6666')
        )
        SELECT
            f.cod_producto,
            f.producto,
            f.categoria,
            c.precio_compra
        FROM filtrado f
        LEFT JOIN gold.dim_compras_precios_ancestral c ON f.cod_producto = c.cod_producto
        """
    )
    df = con.sql("SELECT * FROM gold.dim_producto_izi").df()
    df["producto_"] = df["producto"].str.title()
    con.execute("CREATE OR REPLACE TABLE gold.dim_producto_izi AS SELECT * FROM df")
