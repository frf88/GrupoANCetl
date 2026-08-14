import json
from datetime import date
from pathlib import Path

from src.extract.izi import fetch_facturas, fetch_items_inventario, login
from src.load.duckdb_load import connect
from src.load.publish_gsheets import publish_table, setup as setup_gsheets
from src.load.raw_izi import load_raw_facturas, load_raw_items_inventario
from src.transform.gold_izi import build_dim_producto, build_fct_ventas_items

CONTRIBUYENTE = "79818"
NEGOCIOS = {
    "Ancestral": {"sucursal": "79344"},
    "omuH": {"sucursal": "81761"},
}
DESDE = "2025-06-01"
HASTA = date.today().isoformat()

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

if __name__ == "__main__":
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    token = login()

    factura_files = {}
    for negocio, params in NEGOCIOS.items():
        raw = fetch_facturas(
            token,
            contribuyente=CONTRIBUYENTE,
            sucursal=params["sucursal"],
            desde=DESDE,
            hasta=HASTA,
        )
        path = RAW_DIR / f"izi_facturas_{negocio.lower()}.json"
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        factura_files[negocio] = path
        print(f"{negocio}: {len(raw['facturas'])} facturas extraidas")

    items = fetch_items_inventario(token, contribuyente=CONTRIBUYENTE)
    items_path = RAW_DIR / "izi_items_inventario.json"
    items_path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    print(f"items-inventarios: {len(items)} productos extraidos")

    con = connect()
    load_raw_facturas(con, factura_files)
    load_raw_items_inventario(con, items_path)
    print("Capa raw cargada: raw.izi_facturas, raw.izi_items_inventario")

    build_fct_ventas_items(con)
    build_dim_producto(con)
    print("Capa gold construida: gold.fct_ventas_items, gold.dim_producto")

    setup_gsheets(con)
    publish_table(con, "gold.fct_ventas_items", "ventas_items")
    publish_table(con, "gold.dim_producto", "dim_producto")
    print("Dashboard publicado en Google Sheets")

    con.close()
