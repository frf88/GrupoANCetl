import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

CARD_ID = 40

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

VISIBLE_ORDER = list(SHORT_TITLES.keys())

TYPE_MAP = {
    "producto": "type/Text",
    "categoria": "type/Text",
    "semana": "type/Text",
    "inv_inicial": "type/Float",
    "compras": "type/Float",
    "ventas": "type/Float",
    "ventas_ext": "type/Float",
    "cortesias": "type/Float",
    "salidas": "type/Float",
    "cierre": "type/Float",
    "ventas_totales": "type/Float",
    "inv_calculado": "type/Float",
    "diferencia": "type/Float",
}


def field_ref(name):
    return ["field", name, {"base-type": TYPE_MAP[name]}]


def main():
    table_columns = [
        {"name": name, "fieldRef": field_ref(name), "enabled": True} for name in VISIBLE_ORDER
    ]

    column_settings = {}
    for name in VISIBLE_ORDER:
        key = f'["ref",["field","{name}",{{"base-type":"{TYPE_MAP[name]}"}}]]'
        column_settings[key] = {"column_title": SHORT_TITLES[name]}

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
    print("Formato de columnas reaplicado")


if __name__ == "__main__":
    main()
