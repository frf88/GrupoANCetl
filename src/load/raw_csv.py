from pathlib import Path

import duckdb


def load_raw_csv(con: duckdb.DuckDBPyConnection, table: str, path: Path, skip: int = 0) -> None:
    p = str(path).replace("\\", "/")
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto('{p}', skip={skip})")
