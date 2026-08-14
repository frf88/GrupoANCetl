from pathlib import Path

import duckdb

MAX_JSON_OBJECT_SIZE = 300_000_000

# sucursal -> nombre de negocio (mismo contribuyente, 79818, para ambos)
NEGOCIOS_POR_SUCURSAL = {
    79344: "Ancestral",
    81761: "omuH",
}


def _to_sql_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def load_raw_facturas(con: duckdb.DuckDBPyConnection, files: dict[str, Path]) -> None:
    file_list = ", ".join(f"'{_to_sql_path(p)}'" for p in files.values())
    negocio_case = " ".join(
        f"WHEN {sucursal} THEN '{negocio}'" for sucursal, negocio in NEGOCIOS_POR_SUCURSAL.items()
    )
    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw.izi_facturas AS
        SELECT
            f.*,
            CASE f.sucursal {negocio_case} END AS _negocio,
            now() AS _extraido_en
        FROM (
            SELECT UNNEST(facturas) AS f
            FROM read_json_auto(
                [{file_list}],
                maximum_object_size={MAX_JSON_OBJECT_SIZE},
                union_by_name=true
            )
        )
        """
    )


def load_raw_items_inventario(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw.izi_items_inventario AS
        SELECT *, now() AS _extraido_en
        FROM read_json_auto('{_to_sql_path(path)}', maximum_object_size={MAX_JSON_OBJECT_SIZE})
        """
    )
