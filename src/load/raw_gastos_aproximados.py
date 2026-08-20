from pathlib import Path

import duckdb
import pandas as pd


def load_raw_gastos_aproximados(con: duckdb.DuckDBPyConnection, table: str, path: Path) -> None:
    """Carga la hoja "Gastos Aproximados": en el Google Sheet original hay
    varios bloques de datos apilados (sueldos Ancestral, sueldos omuh,
    gastos fijos omuh...) separados por filas completamente en blanco. El
    Power Query del Power BI real solo toma el PRIMER bloque
    (Table.Group + seleccionar Rows{0}) - los bloques siguientes (hoy:
    sueldos y gastos fijos de omuh) quedan fuera del P&L actual. Se
    replica ese mismo comportamiento aqui a proposito, no se "corrige".
    """
    raw = pd.read_excel(path, sheet_name="Gastos Aproximados", header=None)
    header_idx = raw.index[raw.iloc[:, 0] == "Empresa"][0]
    header = raw.iloc[header_idx].tolist()
    body = raw.iloc[header_idx + 1 :].reset_index(drop=True)
    body.columns = header

    blank_mask = body.isna().all(axis=1)
    first_blank = blank_mask.idxmax() if blank_mask.any() else len(body)
    block = body.iloc[:first_blank]
    block = block[block["Fecha"].notna()]
    block = block[
        [
            "Empresa",
            "Fecha",
            "Fijo/Semanal/Otros",
            "Categoria",
            "Categoria FC",
            "Categoria Detalle",
            "Detalle",
            "Bs",
            "Week",
        ]
    ].copy()
    block["Cuenta"] = "Gastos Aproximados"

    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM block")
