from pathlib import Path

import duckdb
import pandas as pd


def load_raw_xlsx_sheet(con: duckdb.DuckDBPyConnection, table: str, path: Path, sheet_name: str) -> None:
    df = pd.read_excel(path, sheet_name=sheet_name)
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM df")
