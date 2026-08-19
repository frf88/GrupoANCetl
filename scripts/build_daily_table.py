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
    producto,
    fecha,
    dia,
    compras,
    cortesias,
    ventas,
    ventas_ext,
    salidas,
    inv_dia_esperado,
    inv_ini_fin,
    diferencia
FROM gold.fct_reconciliacion_bebidas_ancestral_diario
WHERE categoria IN ('CERVEZA', 'GASEOSAS', 'AGUAS')
  [[AND semana = {{semana}}]]
  [[AND producto = {{producto}}]]
ORDER BY producto, fecha
""".strip()

TITLES = {
    "producto": "Producto",
    "fecha": "Fecha",
    "dia": "Dia",
    "compras": "Comp.",
    "cortesias": "Cort.",
    "ventas": "Vtas",
    "ventas_ext": "Vtas Ext",
    "salidas": "Sal.",
    "inv_dia_esperado": "Inv.Dia.Esp",
    "inv_ini_fin": "Inv.(Ini/Fin)",
    "diferencia": "Dif.",
}
TYPES = {
    "producto": "type/Text",
    "fecha": "type/Date",
    "dia": "type/Text",
    "compras": "type/Float",
    "cortesias": "type/Float",
    "ventas": "type/Float",
    "ventas_ext": "type/Float",
    "salidas": "type/Float",
    "inv_dia_esperado": "type/Float",
    "inv_ini_fin": "type/Float",
    "diferencia": "type/Float",
}


def main():
    card_payload = {
        "name": "Reconciliacion Bebidas Ancestral - Diario",
        "dataset_query": {
            "database": DATABASE_ID,
            "type": "native",
            "native": {
                "query": SQL,
                "template-tags": {
                    "semana": {"id": "tt-semana-diario", "name": "semana", "display-name": "Semana", "type": "text"},
                    "producto": {
                        "id": "tt-producto-diario",
                        "name": "producto",
                        "display-name": "Producto",
                        "type": "text",
                    },
                },
            },
        },
        "display": "table",
        "visualization_settings": {
            "table.column_widths": [90, 75, 45, 55, 50, 50, 55, 50, 75, 85, 55],
            "column_settings": {
                f'["ref",["field","{name}",{{"base-type":"{TYPES[name]}"}}]]': {"column_title": title}
                for name, title in TITLES.items()
            },
            "table.column_formatting": [
                {
                    "columns": ["diferencia"],
                    "type": "single",
                    "operator": "=",
                    "value": 0,
                    "color": "#E0E0E0",
                    "highlight_row": False,
                },
                {
                    "columns": ["diferencia"],
                    "type": "single",
                    "operator": "!=",
                    "value": 0,
                    "color": "#FFCC80",
                    "highlight_row": False,
                },
            ],
        },
        "collection_id": None,
    }
    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=card_payload)
    r.raise_for_status()
    card_id = r.json()["id"]
    print(f"Card diaria creada: id={card_id}")

    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    r.raise_for_status()
    dash = r.json()

    dashcards = [{k: v for k, v in dc.items() if k != "card"} for dc in dash["dashcards"]]
    # ubicar la nueva tarjeta al lado de la primera (misma fila, mitad de ancho cada una)
    for dc in dashcards:
        if dc["card_id"] == 40:
            dc["size_x"] = 12

    dashcards.append(
        {
            "id": -1,
            "card_id": card_id,
            "row": 0,
            "col": 12,
            "size_x": 12,
            "size_y": 20,
            "parameter_mappings": [
                {"parameter_id": "f1sem4na0001", "card_id": card_id, "target": ["variable", ["template-tag", "semana"]]},
                {"parameter_id": "f1prod0002", "card_id": card_id, "target": ["variable", ["template-tag", "producto"]]},
            ],
        }
    )
    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards", headers=HEADERS, json={"cards": dashcards})
    r.raise_for_status()
    print("Tarjeta diaria agregada al dashboard")


if __name__ == "__main__":
    main()
