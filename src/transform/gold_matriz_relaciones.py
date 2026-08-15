import duckdb


def build_dim_receta_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.dim_receta_ancestral AS
        WITH base AS (
            SELECT
                "Cod Producto" AS cod_producto,
                "Producto (izi)" AS producto,
                "Cod Insumo" AS cod_insumo,
                "Insumo" AS insumo,
                "Cantidad usada (kg o u)" AS cantidad_usada,
                CAST(REPLACE("Merma (%)", '%', '') AS DOUBLE) / 100 AS merma_pct,
                COALESCE("Porciones", 1) AS porciones,
                "Stock de porciones" AS stock_porciones,
                "Nuevo Stock" AS nuevo_stock,
                "Rango" AS rango,
                "Dias de compras" AS dias_compras,
                "Dias de llegada estimada" AS dias_llegada_estimada,
                "Dias de produccion" AS dias_produccion
            FROM raw.matriz_relaciones_ancestral
            WHERE "Cod Producto" != ''
        )
        SELECT *, cantidad_usada / (1 - merma_pct) AS cantidad
        FROM base
        WHERE porciones != 0
        """
    )


def build_dim_receta_omuh(con: duckdb.DuckDBPyConnection) -> None:
    # Filtro corregido: la Power Query original decia
    # "[Cantidad usada (kg o u)] = null" (deja solo filas SIN cantidad,
    # vacias); acá se usa "IS NOT NULL" para quedarse con las filas
    # completas - pendiente de confirmar con el usuario.
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.dim_receta_omuh AS
        SELECT
            "Cod Producto" AS cod_producto,
            "Producto (izi)" AS producto,
            "Cod Insumo" AS cod_insumo,
            "Insumo" AS insumo,
            "Categoria" AS categoria,
            "Cantidad usada (kg o u)" AS cantidad_usada,
            CAST(REPLACE("Merma (%)", '%', '') AS DOUBLE) / 100 AS merma_pct,
            "Cantidad usada (kg o u)" / (1 - CAST(REPLACE("Merma (%)", '%', '') AS DOUBLE) / 100) AS cantidad
        FROM raw.matriz_relaciones_omuh
        WHERE "Insumo" != '' AND "Cantidad usada (kg o u)" IS NOT NULL
        """
    )


def build_pesos_platos_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.pesos_platos_ancestral AS
        SELECT cod_producto, cantidad
        FROM (
            SELECT
                "Cod Producto" AS cod_producto,
                "Cantidad usada (kg o u)" / (1 - CAST(REPLACE("Merma (%)", '%', '') AS DOUBLE) / 100) AS cantidad
            FROM raw.matriz_relaciones_ancestral
            WHERE "Cod Producto" != ''
        )
        WHERE cantidad IS NOT NULL
        """
    )


def build_fct_consumo_insumos_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    # Solo insumos con Cod Insumo propio (botellas/insumos que se controlan
    # como stock, ej. HUARI en la Michelada) - se generaliza sola a medida
    # que se agreguen mas filas con Cod Insumo en la matriz (ej. las 3
    # botellas de un Negroni).
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_consumo_insumos_ancestral AS
        SELECT
            m.fecha,
            r.cod_insumo,
            r.insumo,
            r.cod_producto,
            r.producto,
            m.cantidad AS cantidad_vendida,
            r.cantidad AS factor_receta,
            m.cantidad * r.cantidad AS cantidad_consumida
        FROM gold.fct_movimiento_inventario m
        JOIN gold.dim_receta_ancestral r ON m.codigo_inventario = r.cod_producto
        WHERE r.cod_insumo IS NOT NULL AND r.cod_insumo != ''
        """
    )


def build_fct_salidas_mermas_ancestral(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_salidas_mermas_ancestral AS
        SELECT
            strptime("Fecha", '%d-%b-%Y')::DATE AS fecha,
            "Producto" AS producto,
            "Peso" AS peso,
            "Porciones" AS porciones,
            "Comentarios" AS comentarios
        FROM raw.salidas_mermas_ancestral
        """
    )


def build_fct_salidas_mermas_omuh(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_salidas_mermas_omuh AS
        SELECT
            strptime("Fecha", '%d-%b-%Y')::DATE AS fecha,
            "Producto" AS producto,
            "Peso (g / ml)" AS peso,
            "Porciones" AS porciones,
            "Comentarios" AS comentarios
        FROM raw.salidas_mermas_omuh
        """
    )
