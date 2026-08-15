import re

import duckdb
import pandas as pd

ITEM_RE = re.compile(r"^\s*(\d+)\s+(.*)$")


def _parse_items(articulos: str) -> list[tuple[int, str]]:
    if not isinstance(articulos, str) or not articulos.strip():
        return []
    items = []
    for part in articulos.split(","):
        before_bracket = part.split("[")[0].strip()
        match = ITEM_RE.match(before_bracket)
        if not match:
            continue
        cantidad = int(match.group(1))
        producto = match.group(2).strip().lower()
        items.append((cantidad, producto))
    return items


def build_fct_pedidosya_items(con: duckdb.DuckDBPyConnection) -> None:
    raw = con.sql(
        """
        SELECT "Fecha del pedido" AS fecha, "Estado del pedido" AS estado, "Artículos" AS articulos
        FROM raw.pedidosya_ventas
        """
    ).df()
    entregados = raw[raw["estado"] == "Entregado"]

    rows = []
    for _, row in entregados.iterrows():
        fecha = pd.to_datetime(row["fecha"]).date()
        for cantidad, producto in _parse_items(row["articulos"]):
            rows.append({"fecha": fecha, "cantidad": cantidad, "producto": producto, "canal": "PedidosYa"})

    df = pd.DataFrame(rows, columns=["fecha", "cantidad", "producto", "canal"])
    con.execute("CREATE OR REPLACE TABLE gold.fct_pedidosya_items AS SELECT * FROM df")


def _limpiar_producto(txt: str) -> str:
    s = txt.lower()
    s = s.replace("]", "")
    s = s.replace(" 600 ml", "")
    s = s.replace(" 500 ml", "")
    s = s.replace(" 500ml", "")
    s = s.replace("-", " ")
    s = s.replace("sin azucar", "zero")
    s = s.replace("coca cola zero", "coca zero")
    s = s.replace("á", "a")
    s = s.replace("gaseosa ", "")
    return s.strip().title()


def _categoria(producto_limpio: str) -> str:
    p = producto_limpio.lower()
    if p.startswith("burger") or p.startswith("cheeseb"):
        return "1. Burgers"
    if p.startswith("sando"):
        return "2. Sandos"
    return "3. Otros"


def build_fct_ventas_omuh_pedidosya(con: duckdb.DuckDBPyConnection) -> None:
    df = con.sql("SELECT fecha, cantidad, producto, canal FROM gold.fct_pedidosya_items").df()
    df["producto"] = df["producto"].apply(_limpiar_producto)
    df["categoria"] = df["producto"].apply(_categoria)

    con.execute("CREATE OR REPLACE TEMP TABLE _pedidosya_limpio AS SELECT * FROM df")
    con.execute(
        """
        CREATE OR REPLACE TABLE gold.fct_ventas_omuh_pedidosya AS
        SELECT
            t.fecha,
            t.cantidad,
            t.producto,
            t.categoria,
            t.canal,
            d.cod_producto
        FROM _pedidosya_limpio t
        LEFT JOIN gold.dim_producto_izi d ON t.producto = d.producto_
        """
    )
    con.execute("DROP TABLE _pedidosya_limpio")


def _split_comma_2(val: str | None) -> tuple[str | None, str | None]:
    if not isinstance(val, str):
        return None, None
    parts = [p.strip() for p in val.split(",")]
    while len(parts) < 2:
        parts.append(None)
    return parts[0], parts[1]


def _extras_cantidad(row: pd.Series) -> float:
    notas = row["notas"]
    if isinstance(notas, str) and "veg" in notas.lower():
        v1 = row["variable1"]
        v2 = row["variable2"]
        v1_extra = isinstance(v1, str) and "carne extra" in v1.lower()
        v2_extra = isinstance(v2, str) and "carne extra" in v2.lower()
        if v1_extra or v2_extra:
            return row["cantidad1"] * -1
    return row["cantidad1"]


def _build_extras_branch(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.sql(
        """
        SELECT "Fecha" AS fecha, "Variable 1" AS variable1, "Variable 2" AS variable2,
               "Cantidad" AS cantidad1, "Notas" AS notas
        FROM raw.pedidosya_ventas_extras
        """
    ).df()
    df = df.dropna(subset=["fecha"])
    df["fecha"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce").dt.date
    df = df.dropna(subset=["fecha"])
    df["cantidad"] = df.apply(_extras_cantidad, axis=1)

    df["Variable 1.1"], df["Variable 1.2"] = zip(*df["variable1"].map(_split_comma_2))
    df["Variable 2.1"], df["Variable 2.2"] = zip(*df["variable2"].map(_split_comma_2))

    long_df = df.melt(
        id_vars=["fecha", "cantidad"],
        value_vars=["Variable 1.1", "Variable 1.2", "Variable 2.1", "Variable 2.2"],
        var_name="attribute",
        value_name="value",
    )
    long_df = long_df[long_df["value"].notna() & (long_df["value"] != "-")]
    long_df["value"] = long_df["value"].str.strip()
    return long_df[["fecha", "cantidad", "value"]]


def _build_vegetarianas_branch(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.sql(
        """
        SELECT r."Fecha" AS fecha, r."Cantidad" AS cantidad1, r."Notas" AS notas,
               d.categoria, d.cod_producto AS value
        FROM raw.pedidosya_ventas_extras r
        LEFT JOIN gold.dim_producto_izi d ON r."Producto" = d.producto
        """
    ).df()
    df["fecha"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce").dt.date
    df = df[df["categoria"].isin(["1. Burgers", "2. Sandos"])].copy()
    df["cantidad"] = df.apply(
        lambda row: row["cantidad1"] * -1
        if isinstance(row["notas"], str) and "veg" in row["notas"].lower()
        else row["cantidad1"],
        axis=1,
    )
    df = df[df["cantidad"].isin([-1, -2, -3])]
    return df[["fecha", "cantidad", "value"]]


def build_fct_extras_izi_omuh(con: duckdb.DuckDBPyConnection) -> None:
    extras = _build_extras_branch(con)
    con.execute("CREATE OR REPLACE TEMP TABLE _extras AS SELECT * FROM extras")
    con.execute(
        """
        CREATE OR REPLACE TEMP TABLE _extras_joined AS
        SELECT e.fecha, e.cantidad, e.value, d.producto AS producto2
        FROM _extras e
        LEFT JOIN gold.dim_producto_izi d ON e.value = d.producto
        """
    )
    extras_joined = con.sql("SELECT * FROM _extras_joined").df()
    con.execute("DROP TABLE _extras")
    con.execute("DROP TABLE _extras_joined")

    vegetarianas = _build_vegetarianas_branch(con)
    vegetarianas["producto2"] = None

    combined = pd.concat([extras_joined, vegetarianas], ignore_index=True)
    con.execute("CREATE OR REPLACE TABLE gold.fct_extras_izi_omuh AS SELECT * FROM combined")
