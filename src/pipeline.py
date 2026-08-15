import json
from datetime import date
from pathlib import Path

from dateutil.relativedelta import relativedelta

from src.extract.gsheet_csv import fetch_csv
from src.extract.http import fetch_bytes
from src.extract.izi import fetch_facturas, fetch_items_inventario, fetch_movimientos, login
from src.load.duckdb_load import connect
from src.load.raw_csv import load_raw_csv
from src.load.raw_izi import load_raw_facturas, load_raw_items_inventario, load_raw_json_list
from src.load.raw_xlsx import load_raw_xlsx_sheet
from src.transform.gold_izi import (
    build_dim_producto,
    build_fct_mov_inv_omuh,
    build_fct_mov_inv_omuh_todos,
    build_fct_movimiento_inventario,
    build_fct_ventas_items,
)
from src.transform.gold_matriz_relaciones import (
    build_dim_receta_ancestral,
    build_dim_receta_omuh,
    build_fct_consumo_insumos_ancestral,
    build_fct_salidas_mermas_ancestral,
    build_fct_salidas_mermas_omuh,
    build_pesos_platos_ancestral,
)
from src.transform.gold_compras import (
    build_dim_compras_precios_ancestral,
    build_dim_producto_izi,
    build_fct_compras_insumos_ancestral,
    build_fct_compras_insumos_omuh,
    build_fct_compras_totales_ancestral,
)
from src.transform.gold_copas_vino import build_dim_relacion_copa_vino, build_fct_copas_vino_ancestral
from src.transform.gold_inventario_fisico import (
    build_fct_apertura_vinos_copa,
    build_fct_inventario_fisico,
    build_fct_inventario_insumos_gs,
    build_fct_inventario_omuh,
    build_fct_inventario_unitarios_gs,
    build_fct_inventario_unitarios_omuh,
)
from src.transform.gold_min_max import build_dim_min_max_porciones
from src.transform.gold_pedidosya import (
    build_fct_extras_izi_omuh,
    build_fct_pedidosya_items,
    build_fct_ventas_omuh_pedidosya,
)
from src.load.publish_gsheets import publish_table, setup as setup_gsheets
from src.transform.gold_reconciliacion import build_fct_reconciliacion_bebidas_ancestral

CONTRIBUYENTE = "79818"
NEGOCIOS = {
    "Ancestral": {"sucursal": "79344"},
    "omuH": {"sucursal": "81761"},
}
DESDE = "2025-06-01"
HASTA = date.today().isoformat()

MATRIZ_RELACIONES_ANCESTRAL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ75zxBFs61BR1asMscyYFYKIblAKmz1QXyIaOMPFophgCXeG22j-iy8GgU6Fl2tIxKkZM1YkDEj21l/pub?gid=178005519&single=true&output=csv"
SALIDAS_MERMAS_ANCESTRAL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ75zxBFs61BR1asMscyYFYKIblAKmz1QXyIaOMPFophgCXeG22j-iy8GgU6Fl2tIxKkZM1YkDEj21l/pub?gid=1579941617&single=true&output=csv"
PEDIDOSYA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSC58DTA6f4kAYJHQCCKQz0OHBDOtjD6eek0uYcyaQFmWmEoXKgEtaaKStQMtidWy-6XaABEW1xJPJK/pub?output=xlsx"
COMPRAS_INSUMOS_ANCESTRAL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ75zxBFs61BR1asMscyYFYKIblAKmz1QXyIaOMPFophgCXeG22j-iy8GgU6Fl2tIxKkZM1YkDEj21l/pub?gid=1477437632&single=true&output=csv"
COMPRAS_INSUMOS_OMUH_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSbk4txiHVLCOPicpvOX9kHQO-VfGLEUSfLwCTe91rvlyUo-NdBKURpRd1JvCFeyhtKWh0vPQFWBJRh/pub?gid=1479238698&single=true&output=csv"
INVENTARIOS_GS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxSq2o86st5D9pK6lzNuXRS5IitoiPU5739PRf8hL-lPWtFu9ypphWVP867sRfRSnSyUb8oAlUYPR_/pub?gid=0&single=true&output=csv"
INVENTARIOS_BEBIDAS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxSq2o86st5D9pK6lzNuXRS5IitoiPU5739PRf8hL-lPWtFu9ypphWVP867sRfRSnSyUb8oAlUYPR_/pub?gid=809483540&single=true&output=csv"
MATRIZ_RELACIONES_OMUH_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSbk4txiHVLCOPicpvOX9kHQO-VfGLEUSfLwCTe91rvlyUo-NdBKURpRd1JvCFeyhtKWh0vPQFWBJRh/pub?gid=904210502&single=true&output=csv"
INVENTARIOS_OMUH_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSbk4txiHVLCOPicpvOX9kHQO-VfGLEUSfLwCTe91rvlyUo-NdBKURpRd1JvCFeyhtKWh0vPQFWBJRh/pub?gid=1483260326&single=true&output=csv"
INVENTARIOS_UNITARIOS_OMUH_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSbk4txiHVLCOPicpvOX9kHQO-VfGLEUSfLwCTe91rvlyUo-NdBKURpRd1JvCFeyhtKWh0vPQFWBJRh/pub?gid=831896933&single=true&output=csv"
APERTURA_VINOS_COPA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxSq2o86st5D9pK6lzNuXRS5IitoiPU5739PRf8hL-lPWtFu9ypphWVP867sRfRSnSyUb8oAlUYPR_/pub?gid=451366995&single=true&output=csv"
SALIDAS_MERMAS_OMUH_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSbk4txiHVLCOPicpvOX9kHQO-VfGLEUSfLwCTe91rvlyUo-NdBKURpRd1JvCFeyhtKWh0vPQFWBJRh/pub?gid=1579941617&single=true&output=csv"
INVENTARIOS_INSUMOS_GS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ75zxBFs61BR1asMscyYFYKIblAKmz1QXyIaOMPFophgCXeG22j-iy8GgU6Fl2tIxKkZM1YkDEj21l/pub?gid=635693128&single=true&output=csv"
INVENTARIOS_UNITARIOS_GS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ75zxBFs61BR1asMscyYFYKIblAKmz1QXyIaOMPFophgCXeG22j-iy8GgU6Fl2tIxKkZM1YkDEj21l/pub?gid=614318944&single=true&output=csv"
RELACION_COPA_VINO_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRxSq2o86st5D9pK6lzNuXRS5IitoiPU5739PRf8hL-lPWtFu9ypphWVP867sRfRSnSyUb8oAlUYPR_/pub?gid=1445544935&single=true&output=csv"

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

    matriz_path = RAW_DIR / "matriz_relaciones_ancestral.csv"
    matriz_path.write_bytes(fetch_csv(MATRIZ_RELACIONES_ANCESTRAL_URL))
    print("matriz_relaciones_ancestral: extraida")

    salidas_path = RAW_DIR / "salidas_mermas_ancestral.csv"
    salidas_path.write_bytes(fetch_csv(SALIDAS_MERMAS_ANCESTRAL_URL))
    print("salidas_mermas_ancestral: extraida")

    pedidosya_path = RAW_DIR / "pedidosya_ancestral.xlsx"
    pedidosya_path.write_bytes(fetch_bytes(PEDIDOSYA_URL))
    print("pedidosya: extraida")

    compras_path = RAW_DIR / "compras_insumos_ancestral.csv"
    compras_path.write_bytes(fetch_csv(COMPRAS_INSUMOS_ANCESTRAL_URL))
    print("compras_insumos_ancestral: extraida")

    compras_omuh_path = RAW_DIR / "compras_insumos_omuh.csv"
    compras_omuh_path.write_bytes(fetch_csv(COMPRAS_INSUMOS_OMUH_URL))
    print("compras_insumos_omuh: extraida")

    inv_gs_path = RAW_DIR / "inventarios_gs.csv"
    inv_gs_path.write_bytes(fetch_csv(INVENTARIOS_GS_URL))
    print("inventarios_gs: extraida")

    inv_bebidas_path = RAW_DIR / "inventarios_bebidas.csv"
    inv_bebidas_path.write_bytes(fetch_csv(INVENTARIOS_BEBIDAS_URL))
    print("inventarios_bebidas: extraida")

    matriz_omuh_path = RAW_DIR / "matriz_relaciones_omuh.csv"
    matriz_omuh_path.write_bytes(fetch_csv(MATRIZ_RELACIONES_OMUH_URL))
    print("matriz_relaciones_omuh: extraida")

    inv_omuh_path = RAW_DIR / "inventarios_omuh.csv"
    inv_omuh_path.write_bytes(fetch_csv(INVENTARIOS_OMUH_URL))
    print("inventarios_omuh: extraida")

    inv_unit_omuh_path = RAW_DIR / "inventarios_unitarios_omuh.csv"
    inv_unit_omuh_path.write_bytes(fetch_csv(INVENTARIOS_UNITARIOS_OMUH_URL))
    print("inventarios_unitarios_omuh: extraida")

    apertura_path = RAW_DIR / "apertura_vinos_copa.csv"
    apertura_path.write_bytes(fetch_csv(APERTURA_VINOS_COPA_URL))
    print("apertura_vinos_copa: extraida")

    salidas_omuh_path = RAW_DIR / "salidas_mermas_omuh.csv"
    salidas_omuh_path.write_bytes(fetch_csv(SALIDAS_MERMAS_OMUH_URL))
    print("salidas_mermas_omuh: extraida")

    hoy = date.today()
    desde_movimientos = hoy - relativedelta(months=1)
    movimientos = fetch_movimientos(
        token,
        contribuyente=CONTRIBUYENTE,
        desde=f"{desde_movimientos.isoformat()}T00:00:00.000Z",
        hasta=f"{hoy.isoformat()}T23:59:59.000Z",
    )
    movimientos_path = RAW_DIR / "izi_movimientos.json"
    movimientos_path.write_text(json.dumps(movimientos, ensure_ascii=False), encoding="utf-8")
    print(f"izi_movimientos: {len(movimientos)} movimientos extraidos")

    inv_insumos_gs_path = RAW_DIR / "inventarios_insumos_gs.csv"
    inv_insumos_gs_path.write_bytes(fetch_csv(INVENTARIOS_INSUMOS_GS_URL))
    print("inventarios_insumos_gs: extraida")

    inv_unit_gs_path = RAW_DIR / "inventarios_unitarios_gs.csv"
    inv_unit_gs_path.write_bytes(fetch_csv(INVENTARIOS_UNITARIOS_GS_URL))
    print("inventarios_unitarios_gs: extraida")

    relacion_copa_path = RAW_DIR / "relacion_copa_vino.csv"
    relacion_copa_path.write_bytes(fetch_csv(RELACION_COPA_VINO_URL))
    print("relacion_copa_vino: extraida")

    con = connect()
    load_raw_facturas(con, factura_files)
    load_raw_items_inventario(con, items_path)
    load_raw_csv(con, "raw.matriz_relaciones_ancestral", matriz_path)
    load_raw_csv(con, "raw.salidas_mermas_ancestral", salidas_path)
    load_raw_xlsx_sheet(con, "raw.pedidosya_ventas", pedidosya_path, "Ventas Pedidos Ya")
    load_raw_csv(con, "raw.compras_insumos_ancestral", compras_path)
    load_raw_csv(con, "raw.compras_insumos_omuh", compras_omuh_path)
    load_raw_csv(con, "raw.inventarios_gs", inv_gs_path)
    load_raw_csv(con, "raw.inventarios_bebidas", inv_bebidas_path)
    load_raw_csv(con, "raw.matriz_relaciones_omuh", matriz_omuh_path)
    load_raw_csv(con, "raw.inventarios_omuh", inv_omuh_path)
    load_raw_csv(con, "raw.inventarios_unitarios_omuh", inv_unit_omuh_path)
    load_raw_csv(con, "raw.apertura_vinos_copa", apertura_path)
    load_raw_csv(con, "raw.salidas_mermas_omuh", salidas_omuh_path)
    load_raw_json_list(con, "raw.izi_movimientos", movimientos_path)
    load_raw_xlsx_sheet(con, "raw.pedidosya_ventas_extras", pedidosya_path, "Ventas Extras iZi")
    load_raw_csv(con, "raw.inventarios_insumos_gs", inv_insumos_gs_path)
    load_raw_csv(con, "raw.inventarios_unitarios_gs", inv_unit_gs_path)
    load_raw_csv(con, "raw.relacion_copa_vino", relacion_copa_path, skip=1)
    print(
        "Capa raw cargada: raw.izi_facturas, raw.izi_items_inventario, "
        "raw.matriz_relaciones_ancestral, raw.salidas_mermas_ancestral, "
        "raw.pedidosya_ventas, raw.compras_insumos_ancestral, "
        "raw.compras_insumos_omuh, raw.inventarios_gs, raw.inventarios_bebidas, "
        "raw.matriz_relaciones_omuh, raw.inventarios_omuh, "
        "raw.inventarios_unitarios_omuh, raw.apertura_vinos_copa, "
        "raw.salidas_mermas_omuh, raw.izi_movimientos, raw.pedidosya_ventas_extras, "
        "raw.inventarios_insumos_gs, raw.inventarios_unitarios_gs, "
        "raw.relacion_copa_vino"
    )

    build_fct_ventas_items(con)
    build_dim_producto(con)
    build_fct_movimiento_inventario(con)
    build_dim_receta_ancestral(con)
    build_fct_consumo_insumos_ancestral(con)
    build_fct_salidas_mermas_ancestral(con)
    build_fct_pedidosya_items(con)
    build_fct_compras_insumos_ancestral(con)
    build_fct_compras_insumos_omuh(con)
    build_dim_compras_precios_ancestral(con)
    build_dim_producto_izi(con)
    build_fct_ventas_omuh_pedidosya(con)
    build_fct_inventario_fisico(con)
    build_dim_receta_omuh(con)
    build_fct_inventario_omuh(con)
    build_fct_inventario_unitarios_omuh(con)
    build_fct_apertura_vinos_copa(con)
    build_pesos_platos_ancestral(con)
    build_fct_compras_totales_ancestral(con)
    build_fct_salidas_mermas_omuh(con)
    build_dim_min_max_porciones(con)
    build_fct_mov_inv_omuh(con)
    build_fct_mov_inv_omuh_todos(con)
    build_fct_extras_izi_omuh(con)
    build_fct_inventario_insumos_gs(con)
    build_fct_inventario_unitarios_gs(con)
    build_dim_relacion_copa_vino(con)
    build_fct_copas_vino_ancestral(con)
    build_fct_reconciliacion_bebidas_ancestral(con)
    print(
        "Capa gold construida: gold.fct_ventas_items, gold.dim_producto, "
        "gold.fct_movimiento_inventario, gold.dim_receta_ancestral, "
        "gold.fct_consumo_insumos_ancestral, gold.fct_salidas_mermas_ancestral, "
        "gold.fct_pedidosya_items, gold.fct_compras_insumos_ancestral, "
        "gold.fct_compras_insumos_omuh, gold.dim_compras_precios_ancestral, "
        "gold.dim_producto_izi, gold.fct_ventas_omuh_pedidosya, "
        "gold.fct_inventario_fisico, gold.dim_receta_omuh, "
        "gold.fct_inventario_omuh, gold.fct_inventario_unitarios_omuh, "
        "gold.fct_apertura_vinos_copa, gold.pesos_platos_ancestral, "
        "gold.fct_compras_totales_ancestral, gold.fct_salidas_mermas_omuh, "
        "gold.dim_min_max_porciones, gold.fct_mov_inv_omuh, "
        "gold.fct_mov_inv_omuh_todos, gold.fct_extras_izi_omuh, "
        "gold.fct_inventario_insumos_gs, gold.fct_inventario_unitarios_gs, "
        "gold.dim_relacion_copa_vino, gold.fct_copas_vino_ancestral, "
        "gold.fct_reconciliacion_bebidas_ancestral"
    )

    # Publicacion a Google Sheets pausada para el resto de las tablas mientras
    # se define el modelo final; reactivada solo para la primera tabla de
    # reconciliacion, ya validada contra el dashboard real.
    setup_gsheets(con)
    publish_table(con, "gold.fct_reconciliacion_bebidas_ancestral", "reconciliacion_bebidas_ancestral")
    print("Publicado en Google Sheets: reconciliacion_bebidas_ancestral")

    con.close()
