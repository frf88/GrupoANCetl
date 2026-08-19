import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

DATABASE_ID = 2
DASHBOARD_ID = 2

SQL = """
SELECT
    semana,
    SUM(ventas) AS ventas
FROM gold.fct_reconciliacion_bebidas_ancestral
WHERE categoria IN ('CERVEZA', 'GASEOSAS', 'AGUAS')
  AND fecha_cierre > (SELECT MAX(fecha_cierre) FROM gold.fct_reconciliacion_bebidas_ancestral) - INTERVAL '6 weeks'
  [[AND producto = {{producto}}]]
GROUP BY semana
ORDER BY semana
""".strip()


def main():
    card_payload = {
        "name": "Ventas por Semana - Bebidas Ancestral",
        "dataset_query": {
            "database": DATABASE_ID,
            "type": "native",
            "native": {
                "query": SQL,
                "template-tags": {
                    "producto": {
                        "id": "tt-producto-chart",
                        "name": "producto",
                        "display-name": "Producto",
                        "type": "text",
                    }
                },
            },
        },
        "display": "bar",
        "visualization_settings": {
            "graph.dimensions": ["semana"],
            "graph.metrics": ["ventas"],
            "graph.x_axis.title_text": "Semana",
            "graph.y_axis.title_text": "Ventas",
        },
        "collection_id": None,
    }
    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=card_payload)
    r.raise_for_status()
    card_id = r.json()["id"]
    print(f"Grafico de barras creado: id={card_id}")

    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    r.raise_for_status()
    dash = r.json()
    dashcards = [{k: v for k, v in dc.items() if k != "card"} for dc in dash["dashcards"]]
    dashcards.append(
        {
            "id": -1,
            "card_id": card_id,
            "row": 20,
            "col": 0,
            "size_x": 24,
            "size_y": 8,
            "parameter_mappings": [
                {"parameter_id": "f1prod0002", "card_id": card_id, "target": ["variable", ["template-tag", "producto"]]},
            ],
        }
    )
    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards", headers=HEADERS, json={"cards": dashcards})
    r.raise_for_status()
    print("Grafico agregado al dashboard")


if __name__ == "__main__":
    main()
