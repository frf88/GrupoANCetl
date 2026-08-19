import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

CARD_ID = 40
DASHBOARD_ID = 2

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


def main():
    # 1. Ocultar fecha_inicio y fecha_cierre como columnas visibles (siguen
    # disponibles como dimension para el filtro de dashboard).
    table_columns = []
    for name, fid in FIELD_IDS.items():
        table_columns.append(
            {
                "name": name,
                "fieldRef": ["field", fid, None],
                "enabled": name not in ("fecha_inicio", "fecha_cierre"),
            }
        )

    viz_settings = {
        "table.columns": table_columns,
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
        ],
    }
    r = requests.put(
        f"{BASE}/api/card/{CARD_ID}",
        headers=HEADERS,
        json={"visualization_settings": viz_settings},
    )
    r.raise_for_status()
    print("Columnas fecha_inicio/fecha_cierre ocultadas")

    # 2. Cambiar el filtro Semana de rango a fecha exacta (una sola semana).
    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    r.raise_for_status()
    dash = r.json()
    parameters = dash["parameters"]
    for p in parameters:
        if p["id"] == "f1sem4na0001":
            p["type"] = "date/single"
    r = requests.put(
        f"{BASE}/api/dashboard/{DASHBOARD_ID}",
        headers=HEADERS,
        json={"parameters": parameters},
    )
    r.raise_for_status()
    print("Filtro Semana cambiado a fecha exacta (una semana)")

    # 3. Agrandar la tarjeta para ocupar mas de la pagina.
    dashcards = dash["dashcards"]
    for dc in dashcards:
        if dc["card_id"] == CARD_ID:
            dc["size_x"] = 24
            dc["size_y"] = 20
    r = requests.put(
        f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards",
        headers=HEADERS,
        json={"cards": [{k: v for k, v in dc.items() if k not in ("card",)} for dc in dashcards]},
    )
    r.raise_for_status()
    print("Tarjeta agrandada")


if __name__ == "__main__":
    main()
