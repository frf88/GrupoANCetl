import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

DATABASE_ID = 2
DASHBOARD_ID = 2
FILTRO_SEMANA = "f1sem4na0001"

SQL_ANCESTRAL = """
SELECT 'Bebidas' AS area, producto, diferencia
FROM gold.fct_reconciliacion_bebidas_ancestral
WHERE categoria IN ('CERVEZA', 'GASEOSAS', 'AGUAS') AND diferencia IS NOT NULL AND diferencia <> 0
  [[AND semana = {{semana}}]]
UNION ALL
SELECT 'Vinos' AS area, producto, diferencia
FROM gold.fct_reconciliacion_bebidas_ancestral
WHERE categoria IN ('VINO BLANCO', 'VINO BLANCO ', 'VINO TINTO', 'VINO ROSADO', 'VINO DULCE', 'VINO ESPUMANTE', 'IMPORTADO BLANCO', 'IMPORTADO CAVA', 'IMPORTADO ROSADO', 'IMPORTADO TINTO') AND diferencia IS NOT NULL AND diferencia <> 0
  [[AND semana = {{semana}}]]
UNION ALL
SELECT 'Insumos' AS area, producto, diferencia
FROM gold.fct_reconciliacion_insumos_ancestral
WHERE diferencia IS NOT NULL AND diferencia <> 0
  [[AND semana = {{semana}}]]
ORDER BY area, producto
""".strip()

SQL_OMUH = """
SELECT 'Bebidas' AS area, producto, diferencia
FROM gold.fct_reconciliacion_bebidas_omuh
WHERE diferencia IS NOT NULL AND diferencia <> 0
  [[AND semana = {{semana}}]]
UNION ALL
SELECT 'Insumos' AS area, producto, diferencia
FROM gold.fct_reconciliacion_insumos_omuh
WHERE diferencia IS NOT NULL AND diferencia <> 0
  [[AND semana = {{semana}}]]
ORDER BY area, producto
""".strip()


def native_query(sql):
    return {
        "database": DATABASE_ID,
        "type": "native",
        "native": {
            "query": sql,
            "template-tags": {
                "semana": {"id": "tt-semana-resumen", "name": "semana", "display-name": "Semana", "type": "text"},
            },
        },
    }


def make_card(name, sql):
    return {
        "name": name,
        "dataset_query": native_query(sql),
        "display": "table",
        "visualization_settings": {
            "table.column_widths": [90, 220, 70],
            "column_settings": {
                '["name","area"]': {"column_title": "Area"},
                '["name","producto"]': {"column_title": "Producto"},
                '["name","diferencia"]': {"column_title": "Dif.", "number_style": "decimal", "decimals": 0},
            },
            "table.column_formatting": [
                {"columns": ["diferencia"], "type": "single", "operator": "!=", "value": 0, "color": "#FFCC80", "highlight_row": True},
            ],
        },
        "collection_id": None,
    }


def main():
    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=make_card("Resumen Diferencias - Ancestral", SQL_ANCESTRAL))
    r.raise_for_status()
    id_anc = r.json()["id"]
    print(f"Card Ancestral: id={id_anc}")

    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=make_card("Resumen Diferencias - omuH", SQL_OMUH))
    r.raise_for_status()
    id_om = r.json()["id"]
    print(f"Card omuH: id={id_om}")

    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    dash = r.json()
    KEEP = {"id", "card_id", "dashboard_tab_id", "row", "col", "size_x", "size_y", "parameter_mappings", "visualization_settings", "series"}
    dashcards = [{k: v for k, v in dc.items() if k in KEEP} for dc in dash["dashcards"]]
    tabs = dash["tabs"]

    tab_resumen_id = -10
    new_tabs = [{"id": tab_resumen_id, "name": "Resumen"}] + [{"id": t["id"], "name": t["name"]} for t in tabs]

    dashcards.append(
        {
            "id": -401,
            "card_id": id_anc,
            "dashboard_tab_id": tab_resumen_id,
            "row": 0,
            "col": 0,
            "size_x": 12,
            "size_y": 16,
            "parameter_mappings": [
                {"parameter_id": FILTRO_SEMANA, "card_id": id_anc, "target": ["variable", ["template-tag", "semana"]]},
            ],
        }
    )
    dashcards.append(
        {
            "id": -402,
            "card_id": id_om,
            "dashboard_tab_id": tab_resumen_id,
            "row": 0,
            "col": 12,
            "size_x": 12,
            "size_y": 16,
            "parameter_mappings": [
                {"parameter_id": FILTRO_SEMANA, "card_id": id_om, "target": ["variable", ["template-tag", "semana"]]},
            ],
        }
    )

    r2 = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards", headers=HEADERS, json={"cards": dashcards, "tabs": new_tabs})
    r2.raise_for_status()
    print("Pestana Resumen creada (primera posicion)")


if __name__ == "__main__":
    main()
