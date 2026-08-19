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
    "semana": 993,  # nueva columna de texto (agregada en el gold layer)
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

SHORT_TITLES = {
    "producto": "Producto",
    "categoria": "Categoria",
    "semana": "Semana",
    "inv_inicial": "Inv.Ini",
    "compras": "Compras",
    "ventas": "Ventas",
    "ventas_ext": "V.Ext",
    "cortesias": "Cort.",
    "salidas": "Salidas",
    "cierre": "Cierre",
    "ventas_totales": "V.Tot",
    "inv_calculado": "Inv.Calc",
    "diferencia": "Dif.",
}

VISIBLE_ORDER = [
    "producto",
    "categoria",
    "semana",
    "inv_inicial",
    "compras",
    "ventas",
    "ventas_ext",
    "cortesias",
    "salidas",
    "cierre",
    "ventas_totales",
    "inv_calculado",
    "diferencia",
]


def main():
    table_columns = []
    for name, fid in FIELD_IDS.items():
        table_columns.append(
            {
                "name": name,
                "fieldRef": ["field", fid, None],
                "enabled": name in VISIBLE_ORDER,
            }
        )
    # reordenar: primero las visibles en el orden deseado, luego las ocultas
    table_columns.sort(key=lambda c: VISIBLE_ORDER.index(c["name"]) if c["name"] in VISIBLE_ORDER else 999)

    column_settings = {}
    for name in VISIBLE_ORDER:
        fid = FIELD_IDS[name]
        column_settings[f'["ref",["field",{fid},null]]'] = {"column_title": SHORT_TITLES[name]}

    viz_settings = {
        "table.columns": table_columns,
        "table.column_widths": [70, 90, 90, 65, 65, 65, 60, 55, 60, 60, 65, 70, 60],
        "column_settings": column_settings,
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
    r = requests.put(f"{BASE}/api/card/{CARD_ID}", headers=HEADERS, json={"visualization_settings": viz_settings})
    r.raise_for_status()
    print("Columnas achicadas y reordenadas")


if __name__ == "__main__":
    main()
