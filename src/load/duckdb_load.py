import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.environ["DUCKDB_PATH"]


def connect() -> duckdb.DuckDBPyConnection:
    Path(DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute("CREATE SCHEMA IF NOT EXISTS gold")
    return con
