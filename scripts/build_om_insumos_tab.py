import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

DATABASE_ID = 2
DASHBOARD_ID = 2

SQL_SEMANAL = """
SELECT
    producto,
    inv_inicial,
    compras,
    vtas,
    vtas_anc,
    vtas_py,
    cortesias,
    salidas,
    ventas_totales,
    inv_calculado,
    cierre,
    diferencia
FROM gold.fct_reconciliacion_insumos_omuh
WHERE diferencia IS NOT NULL
  [[AND semana = {{semana}}]]
  [[AND producto = {{producto}}]]
ORDER BY producto
""".strip()

SQL_DIARIO = """
SELECT
    producto,
    strftime(fecha, '%d.%m.%y') AS fecha,
    compras,
    vtas,
    vtas_anc,
    vtas_py,
    cortesias,
    salidas,
    inv_dia_esperado,
    inv_ini_fin,
    diferencia
FROM gold.fct_reconciliacion_insumos_omuh_diario
WHERE producto IN (
    SELECT r.producto FROM gold.fct_reconciliacion_insumos_omuh r
    WHERE r.diferencia IS NOT NULL
      [[AND r.semana = {{semana}}]]
)
  [[AND semana = {{semana}}]]
  [[AND producto = {{producto}}]]
ORDER BY producto, fecha
""".strip()

SQL_CHART = """
SELECT
    semana,
    SUM(ventas_totales) AS ventas
FROM gold.fct_reconciliacion_insumos_omuh
WHERE fecha_cierre > (SELECT MAX(fecha_cierre) FROM gold.fct_reconciliacion_insumos_omuh) - INTERVAL '6 weeks'
  [[AND producto = {{producto}}]]
GROUP BY semana
ORDER BY semana
""".strip()

TITLES_SEMANAL = {
    "producto": "Insumo",
    "inv_inicial": "Inv. -7",
    "compras": "Comp.",
    "vtas": "Vtas",
    "vtas_anc": "Vtas Anc",
    "vtas_py": "Vtas PY",
    "cortesias": "Cort.",
    "salidas": "Sal.",
    "ventas_totales": "Vtas Tot",
    "inv_calculado": "Inv.",
    "cierre": "Cie.",
    "diferencia": "Dif.",
}
TITLES_DIARIO = {
    "producto": "Insumo",
    "fecha": "Fecha",
    "compras": "Comp.",
    "vtas": "Vtas",
    "vtas_anc": "Vtas Anc",
    "vtas_py": "Vtas PY",
    "cortesias": "Cort.",
    "salidas": "Sal.",
    "inv_dia_esperado": "Inv. Dia Esp.",
    "inv_ini_fin": "Inv. (Ini y Fin)",
    "diferencia": "Dif.",
}


def col_key(name):
    return f'["name","{name}"]'


def native_query(sql, tags):
    return {
        "database": DATABASE_ID,
        "type": "native",
        "native": {
            "query": sql,
            "template-tags": {
                name: {"id": f"tt-{name}-omins", "name": name, "display-name": name.capitalize(), "type": "text"}
                for name in tags
            },
        },
    }


def main():
    card_semanal = {
        "name": "Reconciliacion Insumos omuH",
        "dataset_query": native_query(SQL_SEMANAL, ["semana", "producto"]),
        "display": "table",
        "visualization_settings": {
            "table.column_widths": [130, 55, 55, 50, 55, 55, 50, 50, 55, 50, 50, 50],
            "column_settings": {col_key(n): {"column_title": t} for n, t in TITLES_SEMANAL.items()},
            "table.column_formatting": [
                {"columns": ["diferencia"], "type": "single", "operator": "=", "value": 0, "color": "#E0E0E0", "highlight_row": True},
                {"columns": ["diferencia"], "type": "single", "operator": "!=", "value": 0, "color": "#FFCC80", "highlight_row": True},
            ],
        },
        "collection_id": None,
    }
    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=card_semanal)
    r.raise_for_status()
    id_semanal = r.json()["id"]
    print(f"Card semanal om.insumos: id={id_semanal}")

    card_diario = {
        "name": "Reconciliacion Insumos omuH - Diario",
        "dataset_query": native_query(SQL_DIARIO, ["semana", "producto"]),
        "display": "table",
        "visualization_settings": {
            "table.column_widths": [130, 70, 50, 50, 55, 55, 50, 50, 55, 60, 50],
            "column_settings": {col_key(n): {"column_title": t} for n, t in TITLES_DIARIO.items()},
            "table.column_formatting": [
                {"columns": ["diferencia"], "type": "single", "operator": "=", "value": 0, "color": "#E0E0E0", "highlight_row": False},
                {"columns": ["diferencia"], "type": "single", "operator": "!=", "value": 0, "color": "#FFCC80", "highlight_row": False},
            ],
        },
        "collection_id": None,
    }
    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=card_diario)
    r.raise_for_status()
    id_diario = r.json()["id"]
    print(f"Card diario om.insumos: id={id_diario}")

    card_chart = {
        "name": "Ventas por Semana - omuH Insumos",
        "dataset_query": native_query(SQL_CHART, ["producto"]),
        "display": "bar",
        "visualization_settings": {
            "graph.dimensions": ["semana"],
            "graph.metrics": ["ventas"],
            "graph.x_axis.title_text": "Semana",
            "graph.y_axis.title_text": "Ventas",
        },
        "collection_id": None,
    }
    r = requests.post(f"{BASE}/api/card", headers=HEADERS, json=card_chart)
    r.raise_for_status()
    id_chart = r.json()["id"]
    print(f"Card grafico om.insumos: id={id_chart}")

    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    dash = r.json()
    dashcards = [{k: v for k, v in dc.items() if k != "card"} for dc in dash["dashcards"]]
    tabs = dash["tabs"]
    tab_bebidas_id = next(t["id"] for t in tabs if t["name"] == "Anc. Bebidas")
    for dc in dashcards:
        if dc["dashboard_tab_id"] is None:
            dc["dashboard_tab_id"] = tab_bebidas_id

    tab_ominsumos_id = -5
    tabs = tabs + [{"id": tab_ominsumos_id, "name": "Om. Insumos"}]

    filtro_semana = "f1sem4na0001"
    filtro_producto = "f1prod0002"

    dashcards.append(
        {
            "id": -401,
            "card_id": id_semanal,
            "dashboard_tab_id": tab_ominsumos_id,
            "row": 0,
            "col": 0,
            "size_x": 12,
            "size_y": 8,
            "parameter_mappings": [
                {"parameter_id": filtro_semana, "card_id": id_semanal, "target": ["variable", ["template-tag", "semana"]]},
                {"parameter_id": filtro_producto, "card_id": id_semanal, "target": ["variable", ["template-tag", "producto"]]},
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
    dashcards.append(
        {
            "id": -402,
            "card_id": id_diario,
            "dashboard_tab_id": tab_ominsumos_id,
            "row": 0,
            "col": 12,
            "size_x": 12,
            "size_y": 8,
            "parameter_mappings": [
                {"parameter_id": filtro_semana, "card_id": id_diario, "target": ["variable", ["template-tag", "semana"]]},
                {"parameter_id": filtro_producto, "card_id": id_diario, "target": ["variable", ["template-tag", "producto"]]},
            ],
        }
    )
    dashcards.append(
        {
            "id": -403,
            "card_id": id_chart,
            "dashboard_tab_id": tab_ominsumos_id,
            "row": 8,
            "col": 0,
            "size_x": 24,
            "size_y": 8,
            "parameter_mappings": [
                {"parameter_id": filtro_producto, "card_id": id_chart, "target": ["variable", ["template-tag", "producto"]]},
            ],
        }
    )

    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards", headers=HEADERS, json={"cards": dashcards, "tabs": tabs})
    r.raise_for_status()
    print("Pestana Om. Insumos creada con sus 3 tarjetas")


if __name__ == "__main__":
    main()
