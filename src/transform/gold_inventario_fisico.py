import duckdb
import pandas as pd

ID_COLS = ["Categoria", "Producto", "Cod Producto"]


def _unpivot_wide_inventario(df: pd.DataFrame, solo_vigentes: bool = False) -> pd.DataFrame:
    if solo_vigentes and "Vigente" in df.columns:
        df = df[df["Vigente"] == "Si"]
    id_cols = [c for c in ID_COLS if c in df.columns]
    value_cols = [c for c in df.columns if c not in id_cols and c != "Vigente"]

    long_df = df.melt(id_vars=id_cols, value_vars=value_cols, var_name="fecha_str", value_name="cantidad")
    fecha_4d = pd.to_datetime(long_df["fecha_str"], format="%d/%m/%Y", errors="coerce")
    fecha_2d = pd.to_datetime(long_df["fecha_str"], format="%d/%m/%y", errors="coerce")
    long_df["fecha"] = fecha_4d.fillna(fecha_2d)
    long_df = long_df.dropna(subset=["fecha"])

    long_df["cantidad"] = long_df["cantidad"].astype(str).str.replace("-", "", regex=False)
    long_df["cantidad"] = pd.to_numeric(long_df["cantidad"], errors="coerce")

    keep_cols = ["fecha"] + id_cols + ["cantidad"]
    rename_map = {"Categoria": "categoria", "Producto": "producto", "Cod Producto": "cod_producto"}
    return long_df[keep_cols].rename(columns=rename_map)


def build_fct_inventario_fisico(con: duckdb.DuckDBPyConnection) -> None:
    gs = con.sql("SELECT * FROM raw.inventarios_gs").df()
    bebidas = con.sql("SELECT * FROM raw.inventarios_bebidas").df()

    combined = pd.concat(
        [_unpivot_wide_inventario(gs), _unpivot_wide_inventario(bebidas)],
        ignore_index=True,
    )
    con.execute("CREATE OR REPLACE TABLE gold.fct_inventario_fisico AS SELECT * FROM combined")


def build_fct_inventario_omuh(con: duckdb.DuckDBPyConnection) -> None:
    df = con.sql("SELECT * FROM raw.inventarios_omuh").df()
    result = _unpivot_wide_inventario(df, solo_vigentes=True)
    con.execute("CREATE OR REPLACE TABLE gold.fct_inventario_omuh AS SELECT * FROM result")


def build_fct_inventario_unitarios_omuh(con: duckdb.DuckDBPyConnection) -> None:
    df = con.sql("SELECT * FROM raw.inventarios_unitarios_omuh").df()
    unpivoted = _unpivot_wide_inventario(df).rename(columns={"categoria": "categoria_conteo"})

    con.execute("CREATE OR REPLACE TEMP TABLE _inv_unit_omuh AS SELECT * FROM unpivoted")
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_inventario_unitarios_omuh AS
        SELECT
            i.fecha,
            i.producto,
            i.categoria_conteo,
            i.cantidad,
            r.categoria,
            r.cod_producto
        FROM _inv_unit_omuh i
        LEFT JOIN gold.dim_receta_omuh r ON i.producto = r.insumo
        WHERE i.cantidad IS NOT NULL
        """
    )
    con.execute("DROP TABLE _inv_unit_omuh")


def build_fct_inventario_insumos_gs(con: duckdb.DuckDBPyConnection) -> None:
    df = con.sql("SELECT * FROM raw.inventarios_insumos_gs").df()
    unpivoted = _unpivot_wide_inventario(df).rename(columns={"cantidad": "peso"})

    con.execute("CREATE OR REPLACE TEMP TABLE _inv_insumos_gs AS SELECT * FROM unpivoted")
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_inventario_insumos_gs AS
        SELECT
            i.fecha,
            i.categoria,
            i.producto,
            i.peso,
            r.cod_producto,
            i.peso * 1000 / r.cantidad_usada AS cantidad
        FROM _inv_insumos_gs i
        LEFT JOIN gold.dim_receta_ancestral r ON i.producto = r.insumo
        WHERE i.peso IS NOT NULL
        """
    )
    con.execute("DROP TABLE _inv_insumos_gs")


def build_fct_inventario_unitarios_gs(con: duckdb.DuckDBPyConnection) -> None:
    df = con.sql("SELECT * FROM raw.inventarios_unitarios_gs").df()
    unpivoted = _unpivot_wide_inventario(df)

    con.execute("CREATE OR REPLACE TEMP TABLE _inv_unit_gs AS SELECT * FROM unpivoted")
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_inventario_unitarios_gs AS
        SELECT
            i.fecha,
            i.categoria,
            i.producto,
            i.cantidad,
            r.cod_producto
        FROM _inv_unit_gs i
        LEFT JOIN gold.dim_receta_ancestral r ON i.producto = r.insumo
        WHERE i.cantidad IS NOT NULL
        """
    )
    con.execute("DROP TABLE _inv_unit_gs")


def build_fct_apertura_vinos_copa(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_apertura_vinos_copa AS
        SELECT
            strptime("Fecha", '%d-%b-%Y')::DATE AS fecha,
            "Codigo Producto" AS codigo_producto,
            "Botella" AS botella,
            "#Botellas" AS num_botellas,
            "Comentarios" AS comentarios
        FROM raw.apertura_vinos_copa
        WHERE "Codigo Producto" != ''
        """
    )
