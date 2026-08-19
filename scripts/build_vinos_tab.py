import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

DASHBOARD_ID = 2
ID_SEMANAL = 106
ID_DIARIO = 107
ID_CHART = 108


def col_key(name):
    return f'["name","{name}"]'


def main():
    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    dash = r.json()
    dashcards = [{k: v for k, v in dc.items() if k != "card"} for dc in dash["dashcards"]]

    tabs = dash["tabs"]
    tab_bebidas_id = next(t["id"] for t in tabs if t["name"] == "Anc. Bebidas")
    tab_vinos_id = next(t["id"] for t in tabs if t["name"] == "Anc. Vinos")
    for dc in dashcards:
        if dc["dashboard_tab_id"] is None:
            dc["dashboard_tab_id"] = tab_bebidas_id

    filtro_semana = "f1sem4na0001"
    filtro_producto = "f1prod0002"

    existing_card_ids = {dc["card_id"] for dc in dashcards}

    if ID_SEMANAL not in existing_card_ids:
        dashcards.append(
            {
                "id": -101,
                "card_id": ID_SEMANAL,
                "dashboard_tab_id": tab_vinos_id,
                "row": 0,
                "col": 0,
                "size_x": 12,
                "size_y": 8,
                "parameter_mappings": [
                    {"parameter_id": filtro_semana, "card_id": ID_SEMANAL, "target": ["variable", ["template-tag", "semana"]]},
                    {"parameter_id": filtro_producto, "card_id": ID_SEMANAL, "target": ["variable", ["template-tag", "producto"]]},
                ],
                "visualization_settings": {
                    "column_settings": {
                        col_key("producto"): {
                            "click_behavior": {
                                "type": "crossfilter",
                                "parameterMapping": {
                                    filtro_producto: {
                                        "id": filtro_producto,
                                        "source": {"type": "column", "id": "producto", "name": "producto"},
                                        "target": {"type": "parameter", "id": filtro_producto},
                                    }
                                },
                            }
                        }
                    }
                },
            }
        )
    if ID_DIARIO not in existing_card_ids:
        dashcards.append(
        {
            "id": -102,
            "card_id": ID_DIARIO,
            "dashboard_tab_id": tab_vinos_id,
            "row": 0,
            "col": 12,
            "size_x": 12,
            "size_y": 8,
            "parameter_mappings": [
                {"parameter_id": filtro_semana, "card_id": ID_DIARIO, "target": ["variable", ["template-tag", "semana"]]},
                {"parameter_id": filtro_producto, "card_id": ID_DIARIO, "target": ["variable", ["template-tag", "producto"]]},
            ],
        }
    )
    if ID_CHART not in existing_card_ids:
        dashcards.append(
            {
                "id": -103,
                "card_id": ID_CHART,
                "dashboard_tab_id": tab_vinos_id,
                "row": 8,
                "col": 0,
                "size_x": 24,
                "size_y": 8,
                "parameter_mappings": [
                    {"parameter_id": filtro_producto, "card_id": ID_CHART, "target": ["variable", ["template-tag", "producto"]]},
                ],
            }
        )

    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards", headers=HEADERS, json={"cards": dashcards, "tabs": tabs})
    r.raise_for_status()
    print("Pestana Anc. Vinos creada con sus 3 tarjetas")


if __name__ == "__main__":
    main()
