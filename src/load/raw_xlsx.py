from pathlib import Path

import duckdb
import pandas as pd


def load_raw_xlsx_sheet(con: duckdb.DuckDBPyConnection, table: str, path: Path, sheet_name: str) -> None:
    df = pd.read_excel(path, sheet_name=sheet_name)
    # Columnas con tipos mezclados en el Excel origen (ej. celdas con formato
    # de hora e int en la misma columna) rompen la inferencia de DuckDB;
    # se guardan como texto para preservar el dato tal cual viene.
    for col in df.columns[df.dtypes == "object"]:
        if df[col].map(type).nunique() > 1:
            df[col] = df[col].astype(str).where(df[col].notna(), None)
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM df")
