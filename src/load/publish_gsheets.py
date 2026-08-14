import duckdb

DASHBOARD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1gGDK_eRYIUFrgyJ-XaO0xvQdG1YPx-hEEPWWtRfsROI/"


def setup(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("INSTALL gsheets FROM community")
    con.execute("LOAD gsheets")
    con.execute(
        """
        CREATE OR REPLACE PERSISTENT SECRET izi_gsheets (
            TYPE gsheet,
            PROVIDER key_file,
            FILEPATH 'credentials/google-service-account.json'
        )
        """
    )


def publish_table(con: duckdb.DuckDBPyConnection, table: str, sheet_name: str) -> None:
    con.execute(
        f"""
        COPY (SELECT * FROM {table})
        TO '{DASHBOARD_SHEET_URL}' (FORMAT gsheet, sheet '{sheet_name}', create_if_not_exists true)
        """
    )
