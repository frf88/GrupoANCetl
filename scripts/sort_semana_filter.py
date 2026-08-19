import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

DASHBOARD_ID = 2
DATABASE_ID = 2


def main():
    # 1. Pregunta auxiliar: semanas distintas ordenadas de mas reciente a mas antigua.
    card_payload = {
        "name": "Semanas Bebidas Ancestral (orden)",
        "dataset_query": {
            "database": DATABASE_ID,
            "type": "native",
            "native": {
                "query": (
                    "SELECT DISTINCT semana FROM gold.fct_reconciliacion_bebidas_ancestral "
                    "ORDER BY semana DESC"
                )
            },
        },
        "display": "table",
        "visualization_settings": {},
        "collection_id": None,
    }
    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=card_payload)
    r.raise_for_status()
    helper_card_id = r.json()["id"]
    print(f"Pregunta auxiliar creada: id={helper_card_id}")

    # 2. Apuntar el filtro Semana del dashboard a esta pregunta como fuente de valores.
    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    r.raise_for_status()
    dash = r.json()
    for p in dash["parameters"]:
        if p["id"] == "f1sem4na0001":
            p["values_source_type"] = "card"
            p["values_source_config"] = {
                "card_id": helper_card_id,
                "value_field": ["field", "semana", {"base-type": "type/Text"}],
            }
    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS, json={"parameters": dash["parameters"]})
    r.raise_for_status()
    print("Filtro Semana ahora usa orden descendente (mas reciente primero)")


if __name__ == "__main__":
    main()
