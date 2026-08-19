import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

DASHBOARD_ID = 2
CARD_SEMANAL = 40
CARD_DIARIO = 104
CARD_CHART = 105


def col_key(name, base_type=None):
    return f'["name","{name}"]'


def main():
    # --- Tabla semanal (card 40): sin categoria/semana, Producto ancho, numeros angostos ---
    sql_semanal = """
SELECT
    producto,
    inv_inicial,
    compras,
    ventas,
    ventas_ext,
    cortesias,
    salidas,
    ventas_totales,
    inv_calculado,
    cierre,
    diferencia
FROM gold.fct_reconciliacion_bebidas_ancestral
WHERE categoria IN ('CERVEZA', 'GASEOSAS', 'AGUAS')
  AND diferencia IS NOT NULL
  [[AND semana = {{semana}}]]
  [[AND producto = {{producto}}]]
ORDER BY producto
""".strip()

    titles_semanal = {
        "producto": "Producto",
        "inv_inicial": "Inv. -7",
        "compras": "Comp.",
        "ventas": "Vtas",
        "ventas_ext": "Vtas Ext",
        "cortesias": "Cort.",
        "salidas": "Sal.",
        "cierre": "Cie.",
        "ventas_totales": "Vtas Tot",
        "inv_calculado": "Inv.",
        "diferencia": "Dif.",
    }
    types_semanal = {
        "producto": "type/Text",
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
    widths_semanal = [130, 55, 55, 50, 50, 50, 50, 55, 55, 50, 50]

    query = {
        "database": 2,
        "type": "native",
        "native": {
            "query": sql_semanal,
            "template-tags": {
                "semana": {"id": "tt-semana-001", "name": "semana", "display-name": "Semana", "type": "text"},
                "producto": {"id": "tt-producto-001", "name": "producto", "display-name": "Producto", "type": "text"},
            },
        },
    }
    viz = {
        "table.column_widths": widths_semanal,
        "column_settings": {
            col_key(name, types_semanal[name]): {"column_title": title} for name, title in titles_semanal.items()
        },
        "table.column_formatting": [
            {"columns": ["diferencia"], "type": "single", "operator": "=", "value": 0, "color": "#E0E0E0", "highlight_row": True},
            {"columns": ["diferencia"], "type": "single", "operator": "!=", "value": 0, "color": "#FFCC80", "highlight_row": True},
        ],
    }
    r = requests.put(f"{BASE}/api/card/{CARD_SEMANAL}", headers=HEADERS, json={"dataset_query": query, "visualization_settings": viz})
    r.raise_for_status()
    print("Tabla semanal actualizada")

    # --- Tabla diaria (card 104): sin dia, Producto ancho, numeros angostos ---
    sql_diario = """
SELECT
    producto,
    strftime(fecha, '%d.%m.%y') AS fecha,
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
  AND producto IN (
      SELECT r.producto FROM gold.fct_reconciliacion_bebidas_ancestral r
      WHERE r.categoria IN ('CERVEZA', 'GASEOSAS', 'AGUAS') AND r.diferencia IS NOT NULL
        [[AND r.semana = {{semana}}]]
  )
  [[AND semana = {{semana}}]]
  [[AND producto = {{producto}}]]
ORDER BY producto, fecha
""".strip()

    titles_diario = {
        "producto": "Producto",
        "fecha": "Fecha",
        "compras": "Comp.",
        "cortesias": "Cort.",
        "ventas": "Vtas",
        "ventas_ext": "Vtas Ext",
        "salidas": "Sal.",
        "inv_dia_esperado": "Inv. Dia Esp.",
        "inv_ini_fin": "Inv. (Ini y Fin)",
        "diferencia": "Dif.",
    }
    types_diario = {
        "producto": "type/Text",
        "fecha": "type/Text",
        "compras": "type/Float",
        "cortesias": "type/Float",
        "ventas": "type/Float",
        "ventas_ext": "type/Float",
        "salidas": "type/Float",
        "inv_dia_esperado": "type/Float",
        "inv_ini_fin": "type/Float",
        "diferencia": "type/Float",
    }
    widths_diario = [130, 70, 50, 50, 50, 50, 50, 55, 55, 50]

    query = {
        "database": 2,
        "type": "native",
        "native": {
            "query": sql_diario,
            "template-tags": {
                "semana": {"id": "tt-semana-diario", "name": "semana", "display-name": "Semana", "type": "text"},
                "producto": {"id": "tt-producto-diario", "name": "producto", "display-name": "Producto", "type": "text"},
            },
        },
    }
    viz = {
        "table.column_widths": widths_diario,
        "column_settings": {
            col_key(name, types_diario[name]): {"column_title": title} for name, title in titles_diario.items()
        },
        "table.column_formatting": [
            {"columns": ["diferencia"], "type": "single", "operator": "=", "value": 0, "color": "#E0E0E0", "highlight_row": False},
            {"columns": ["diferencia"], "type": "single", "operator": "!=", "value": 0, "color": "#FFCC80", "highlight_row": False},
        ],
    }
    r = requests.put(f"{BASE}/api/card/{CARD_DIARIO}", headers=HEADERS, json={"dataset_query": query, "visualization_settings": viz})
    r.raise_for_status()
    print("Tabla diaria actualizada")

    # --- Layout del dashboard: tablas mas bajas, grafico justo debajo ---
    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    dash = r.json()
    dashcards = [{k: v for k, v in dc.items() if k != "card"} for dc in dash["dashcards"]]
    for dc in dashcards:
        if dc["card_id"] in (CARD_SEMANAL, CARD_DIARIO):
            dc["row"] = 0
            dc["size_y"] = 8
        if dc["card_id"] == CARD_CHART:
            dc["row"] = 8
            dc["size_y"] = 8
    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards", headers=HEADERS, json={"cards": dashcards, "tabs": dash["tabs"]})
    r.raise_for_status()
    print("Layout actualizado (tablas mas bajas, grafico debajo)")


if __name__ == "__main__":
    main()
