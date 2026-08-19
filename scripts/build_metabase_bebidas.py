import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

DATABASE_ID = 2
TABLE_ID = 32

FIELD_IDS = {
    "producto": 217,
    "categoria": 218,
    "fecha_inicio": 219,
    "fecha_cierre": 220,
    "inv_inicial": 221,
    "compras": 222,
    "ventas": 223,
    "ventas_ext": 224,
    "cortesias": 225,
    "salidas": 226,
    "cierre": 227,
    "ventas_totales": 228,
    "inv_calculado": 229,
    "diferencia": 230,
}


def field_ref(name):
    return ["field", FIELD_IDS[name], None]


def main():
    # 1. Crear la pregunta (Card)
    card_payload = {
        "name": "Reconciliacion Bebidas Ancestral",
        "dataset_query": {
            "database": DATABASE_ID,
            "type": "query",
            "query": {"source-table": TABLE_ID},
        },
        "display": "table",
        "visualization_settings": {
            "table.column_formatting": [
                {
                    "columns": ["diferencia"],
                    "type": "single",
                    "operator": "=",
                    "value": 0,
                    "color": "#E0E0E0",
                    "highlight_row": True,
                },
                {
                    "columns": ["diferencia"],
                    "type": "single",
                    "operator": "!=",
                    "value": 0,
                    "color": "#FFCC80",
                    "highlight_row": True,
                },
            ]
        },
        "collection_id": None,
    }
    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=card_payload)
    r.raise_for_status()
    card = r.json()
    card_id = card["id"]
    print(f"Card creada: id={card_id}")

    # 2. Crear el dashboard
    dash_payload = {"name": "Control Inventario: Bebidas Ancestral"}
    r = requests.post(f"{BASE}/api/dashboard", headers=HEADERS, json=dash_payload)
    r.raise_for_status()
    dashboard = r.json()
    dashboard_id = dashboard["id"]
    print(f"Dashboard creado: id={dashboard_id}")

    # 3. Definir filtros del dashboard (semana / fecha_cierre y producto)
    filter_semana = {
        "id": "f1sem4na0001",
        "name": "Semana (cierre)",
        "slug": "semana_cierre",
        "type": "date/all-options",
        "sectionId": "date",
    }
    filter_producto = {
        "id": "f1prod0002",
        "name": "Producto",
        "slug": "producto",
        "type": "string/=",
        "sectionId": "string",
    }

    # 4. Agregar la tarjeta al dashboard, con tamano y mapeo de filtros
    dashcard_payload = {
        "dashcards": [
            {
                "id": -1,
                "card_id": card_id,
                "row": 0,
                "col": 0,
                "size_x": 18,
                "size_y": 10,
                "parameter_mappings": [
                    {
                        "parameter_id": filter_semana["id"],
                        "card_id": card_id,
                        "target": ["dimension", field_ref("fecha_cierre")],
                    },
                    {
                        "parameter_id": filter_producto["id"],
                        "card_id": card_id,
                        "target": ["dimension", field_ref("producto")],
                    },
                ],
            }
        ]
    }

    r = requests.put(
        f"{BASE}/api/dashboard/{dashboard_id}",
        headers=HEADERS,
        json={"parameters": [filter_semana, filter_producto]},
    )
    r.raise_for_status()
    print("Filtros agregados al dashboard")

    r = requests.put(
        f"{BASE}/api/dashboard/{dashboard_id}/cards",
        headers=HEADERS,
        json=dashcard_payload,
    )
    r.raise_for_status()
    print("Tarjeta agregada al dashboard")

    print(f"\nListo: {BASE}/dashboard/{dashboard_id}")


if __name__ == "__main__":
    main()
