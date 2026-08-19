import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

TEXT_COLS = {"producto", "fecha", "dia", "semana"}

# columnas que en la tabla semanal se vuelven texto con guion cuando son NULL
# (la semana en curso, que aun no tiene cierre)
DASH_COLS = {"cierre", "inv_calculado"}

SEMANAL_CARDS = [40, 106, 136, 168, 200]
DIARIO_CARDS = [104, 107, 137, 169, 201]


def col_key(name):
    return f'["name","{name}"]'


def wrap_dash(sql: str, col: str) -> str:
    # reemplaza "col," o "col\n" (limite de columna en el SELECT) por la version con COALESCE a '-'
    old = f",\n    {col},\n" if f",\n    {col},\n" in sql else None
    # las consultas usan distintos formatos de indentacion; hacemos un reemplazo
    # simple de "<coma/espacios>col<coma/salto>" buscando el nombre exacto de columna
    import re

    pattern = re.compile(rf"(?<![A-Za-z_]){col}(?![A-Za-z_])")
    return pattern.sub(f"COALESCE(CAST(ROUND({col}, 0) AS VARCHAR), '–')", sql, count=1)


def main():
    for cid in SEMANAL_CARDS + DIARIO_CARDS:
        r = requests.get(f"{BASE}/api/card/{cid}", headers=HEADERS)
        d = r.json()
        sql = d["dataset_query"]["stages"][0]["native"]
        tags = d["dataset_query"]["stages"][0].get("template-tags", [])
        viz = d["visualization_settings"]
        col_settings = viz.get("column_settings", {})

        # columnas numericas = todas las que aparecen en column_settings menos las de texto
        numeric_cols = [
            name
            for name in (eval(k)[1] for k in col_settings.keys())
            if name not in TEXT_COLS
        ]

        if cid in SEMANAL_CARDS:
            for col in DASH_COLS:
                if col in numeric_cols:
                    sql = wrap_dash(sql, col)
                    numeric_cols.remove(col)

        for col in numeric_cols:
            key = col_key(col)
            col_settings.setdefault(key, {})
            col_settings[key]["number_style"] = "decimal"
            col_settings[key]["decimals"] = 0

        viz["column_settings"] = col_settings

        query = {
            "database": 2,
            "type": "native",
            "native": {
                "query": sql,
                "template-tags": {t["name"]: t for t in tags},
            },
        }
        r2 = requests.put(f"{BASE}/api/card/{cid}", headers=HEADERS, json={"dataset_query": query, "visualization_settings": viz})
        r2.raise_for_status()
        print(f"card {cid} actualizada")


if __name__ == "__main__":
    main()
