import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ["METABASE_URL"]
HEADERS = {"x-api-key": os.environ["METABASE_API_KEY"], "Content-Type": "application/json"}

DASHBOARD_ID = 2
FILTRO_DIF_ID = "f1difx0003"

CARD_SQLS = {
    40: """
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
  [[AND diferencia <> 0 AND {{dif_toggle}} = {{dif_toggle}}]]
ORDER BY producto
""".strip(),
    106: """
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
WHERE categoria IN ('VINO BLANCO', 'VINO BLANCO ', 'VINO TINTO', 'VINO ROSADO', 'VINO DULCE', 'VINO ESPUMANTE', 'IMPORTADO BLANCO', 'IMPORTADO CAVA', 'IMPORTADO ROSADO', 'IMPORTADO TINTO')
  AND diferencia IS NOT NULL
  [[AND semana = {{semana}}]]
  [[AND producto = {{producto}}]]
  [[AND diferencia <> 0 AND {{dif_toggle}} = {{dif_toggle}}]]
ORDER BY producto
""".strip(),
    136: """
SELECT
    producto,
    inv_inicial,
    compras,
    ventas,
    salidas,
    inv_calculado,
    cierre,
    diferencia
FROM gold.fct_reconciliacion_insumos_ancestral
WHERE diferencia IS NOT NULL
  [[AND semana = {{semana}}]]
  [[AND producto = {{producto}}]]
  [[AND diferencia <> 0 AND {{dif_toggle}} = {{dif_toggle}}]]
ORDER BY producto
""".strip(),
    168: """
SELECT
    producto,
    inv_inicial,
    compras,
    vtas,
    vtas_anc,
    vtas_py,
    vtas_ext,
    cortesias,
    ventas_totales,
    inv_calculado,
    cierre,
    diferencia
FROM gold.fct_reconciliacion_bebidas_omuh
WHERE diferencia IS NOT NULL
  [[AND semana = {{semana}}]]
  [[AND producto = {{producto}}]]
  [[AND diferencia <> 0 AND {{dif_toggle}} = {{dif_toggle}}]]
ORDER BY producto
""".strip(),
    200: """
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
  [[AND diferencia <> 0 AND {{dif_toggle}} = {{dif_toggle}}]]
ORDER BY producto
""".strip(),
}


def native_query(sql):
    return {
        "database": 2,
        "type": "native",
        "native": {
            "query": sql,
            "template-tags": {
                "semana": {"id": "tt-semana-shared", "name": "semana", "display-name": "Semana", "type": "text"},
                "producto": {"id": "tt-producto-shared", "name": "producto", "display-name": "Producto", "type": "text"},
                "dif_toggle": {
                    "id": "tt-dif-toggle",
                    "name": "dif_toggle",
                    "display-name": "Solo con diferencia",
                    "type": "text",
                },
            },
        },
    }


def main():
    for card_id, sql in CARD_SQLS.items():
        r = requests.put(f"{BASE}/api/card/{card_id}", headers=HEADERS, json={"dataset_query": native_query(sql)})
        r.raise_for_status()
        print(f"Card {card_id} actualizada con filtro de diferencia")

    r = requests.get(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS)
    dash = r.json()

    parametro_dif = {
        "id": FILTRO_DIF_ID,
        "name": "Solo con diferencia",
        "slug": "solo_con_diferencia",
        "type": "string/=",
        "sectionId": "string",
        "values_source_type": "static-list",
        "values_source_config": {"values": ["Solo con diferencia"]},
    }
    parameters = dash["parameters"] + [parametro_dif]
    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}", headers=HEADERS, json={"parameters": parameters})
    r.raise_for_status()
    print("Filtro 'Solo con diferencia' agregado al dashboard")

    dashcards = [{k: v for k, v in dc.items() if k != "card"} for dc in dash["dashcards"]]
    for dc in dashcards:
        if dc["card_id"] in CARD_SQLS:
            mappings = [m for m in dc["parameter_mappings"] if m["parameter_id"] != FILTRO_DIF_ID]
            mappings.append(
                {
                    "parameter_id": FILTRO_DIF_ID,
                    "card_id": dc["card_id"],
                    "target": ["variable", ["template-tag", "dif_toggle"]],
                }
            )
            dc["parameter_mappings"] = mappings

    tabs = [{k: v for k, v in t.items() if k in ("id", "name")} for t in dash["tabs"]]
    r = requests.put(f"{BASE}/api/dashboard/{DASHBOARD_ID}/cards", headers=HEADERS, json={"cards": dashcards, "tabs": tabs})
    r.raise_for_status()
    print("Filtro mapeado a las 5 tarjetas semanales")


if __name__ == "__main__":
    main()
