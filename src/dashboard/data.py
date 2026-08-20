import os

import duckdb
from dash.dash_table.Format import Format, Group, Scheme
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.environ["DUCKDB_PATH"]

CATEGORIAS_BEBIDAS = ("CERVEZA", "GASEOSAS", "AGUAS")
CATEGORIAS_VINOS = (
    "VINO BLANCO",
    "VINO BLANCO ",
    "VINO TINTO",
    "VINO ROSADO",
    "VINO DULCE",
    "VINO ESPUMANTE",
    "IMPORTADO BLANCO",
    "IMPORTADO CAVA",
    "IMPORTADO ROSADO",
    "IMPORTADO TINTO",
)

BEBIDAS_WEEKLY_COLUMNS = [
    "producto",
    "semana",
    "fecha_cierre",
    "inv_inicial",
    "compras",
    "ventas",
    "ventas_ext",
    "cortesias",
    "salidas",
    "ventas_totales",
    "inv_calculado",
    "cierre",
    "diferencia",
]
BEBIDAS_DAILY_COLUMNS = [
    "producto",
    "semana",
    "fecha",
    "dia",
    "compras",
    "cortesias",
    "ventas",
    "ventas_ext",
    "salidas",
    "inv_dia_esperado",
    "inv_ini_fin",
    "diferencia",
]
INSUMOS_WEEKLY_COLUMNS = [
    "producto",
    "semana",
    "fecha_cierre",
    "inv_inicial",
    "compras",
    "ventas",
    "salidas",
    "inv_calculado",
    "cierre",
    "diferencia",
]
INSUMOS_DAILY_COLUMNS = [
    "producto",
    "semana",
    "fecha",
    "dia",
    "compras",
    "ventas",
    "salidas",
    "inv_dia_esperado",
    "inv_ini_fin",
    "diferencia",
]

OMUH_BEBIDAS_WEEKLY_COLUMNS = [
    "producto",
    "semana",
    "fecha_cierre",
    "inv_inicial",
    "compras",
    "vtas",
    "vtas_anc",
    "vtas_py",
    "vtas_ext",
    "cortesias",
    "ventas_totales",
    "inv_calculado",
    "cierre",
    "diferencia",
]
OMUH_BEBIDAS_DAILY_COLUMNS = [
    "producto",
    "semana",
    "fecha",
    "dia",
    "compras",
    "vtas",
    "vtas_anc",
    "vtas_py",
    "vtas_ext",
    "cortesias",
    "inv_dia_esperado",
    "inv_ini_fin",
    "diferencia",
]
OMUH_INSUMOS_WEEKLY_COLUMNS = [
    "producto",
    "semana",
    "fecha_cierre",
    "inv_inicial",
    "compras",
    "vtas",
    "vtas_anc",
    "vtas_py",
    "cortesias",
    "salidas",
    "ventas_totales",
    "inv_calculado",
    "cierre",
    "diferencia",
]
OMUH_INSUMOS_DAILY_COLUMNS = [
    "producto",
    "semana",
    "fecha",
    "dia",
    "compras",
    "vtas",
    "vtas_anc",
    "vtas_py",
    "cortesias",
    "salidas",
    "inv_dia_esperado",
    "inv_ini_fin",
    "diferencia",
]

BEBIDAS_WEEKLY_TITLES = {
    "producto": "Producto",
    "semana": "Semana",
    "inv_inicial": "Inv. Inicial",
    "compras": "Compras",
    "ventas": "Ventas",
    "ventas_ext": "Ventas Ext.",
    "cortesias": "Cortesías",
    "salidas": "Salidas",
    "ventas_totales": "Ventas Tot.",
    "inv_calculado": "Inv. Calc.",
    "cierre": "Cierre",
    "diferencia": "Diferencia",
}
BEBIDAS_DAILY_TITLES = {
    "producto": "Producto",
    "semana": "Semana",
    "fecha": "Fecha",
    "dia": "Día",
    "compras": "Comp.",
    "cortesias": "Cort.",
    "ventas": "Vtas",
    "ventas_ext": "Vtas Ext",
    "salidas": "Sal.",
    "inv_dia_esperado": "Inv.Día.Esp",
    "inv_ini_fin": "Inv.(Ini/Fin)",
    "diferencia": "Dif.",
}
INSUMOS_WEEKLY_TITLES = BEBIDAS_WEEKLY_TITLES
INSUMOS_DAILY_TITLES = BEBIDAS_DAILY_TITLES
OMUH_WEEKLY_TITLES = {
    "producto": "Producto",
    "semana": "Semana",
    "inv_inicial": "Inv. -7",
    "compras": "Compras",
    "vtas": "Ventas",
    "vtas_anc": "Ventas Anc.",
    "vtas_py": "Ventas PY",
    "vtas_ext": "Ventas Ext.",
    "cortesias": "Cortesías",
    "salidas": "Salidas",
    "ventas_totales": "Ventas Tot.",
    "inv_calculado": "Inv. Calc.",
    "cierre": "Cierre",
    "diferencia": "Diferencia",
}
OMUH_DAILY_TITLES = {
    "producto": "Producto",
    "semana": "Semana",
    "fecha": "Fecha",
    "dia": "Día",
    "compras": "Comp.",
    "vtas": "Vtas",
    "vtas_anc": "Vtas Anc.",
    "vtas_py": "Vtas PY",
    "vtas_ext": "Vtas Ext",
    "cortesias": "Cort.",
    "salidas": "Sal.",
    "inv_dia_esperado": "Inv.Día.Esp",
    "inv_ini_fin": "Inv.(Ini/Fin)",
    "diferencia": "Dif.",
}

# columnas que en la vista semanal se muestran como texto con guion cuando
# son NULL (la semana en curso, que aun no tiene cierre)
NULL_AS_DASH = ("cierre", "inv_calculado")

# formato compartido para toda columna numerica de metricas en las tablas:
# separador de miles "," y decimales con "." (default de dash_table.Format)
NUMBER_FORMAT = Format(scheme=Scheme.fixed, precision=0, group=Group.yes)


def _connect():
    # read_only=True: la app solo lee, y permite convivir con el pipeline
    # nocturno (que si necesita escritura exclusiva sobre el mismo archivo).
    return duckdb.connect(DUCKDB_PATH, read_only=True)


def _load_bebidas_like(con, tabla_semanal, tabla_diaria, categorias, weekly_columns, daily_columns):
    categorias_sql = ", ".join(f"'{c}'" for c in categorias)
    weekly = con.execute(
        f"""
        SELECT {", ".join(weekly_columns)}
        FROM gold.{tabla_semanal}
        WHERE categoria IN ({categorias_sql}) AND diferencia IS NOT NULL
        ORDER BY producto, semana
        """
    ).df()
    daily = con.execute(
        f"""
        SELECT {", ".join(daily_columns)}
        FROM gold.{tabla_diaria}
        WHERE categoria IN ({categorias_sql})
        ORDER BY producto, fecha
        """
    ).df()
    ventas_semana = con.execute(
        f"""
        SELECT producto, semana, SUM(ventas) AS ventas
        FROM gold.{tabla_semanal}
        WHERE categoria IN ({categorias_sql})
          AND fecha_cierre > (SELECT MAX(fecha_cierre) FROM gold.{tabla_semanal}) - INTERVAL '6 weeks'
        GROUP BY producto, semana
        ORDER BY semana
        """
    ).df()
    return weekly, daily, ventas_semana


def load_bebidas(con):
    return _load_bebidas_like(
        con,
        "fct_reconciliacion_bebidas_ancestral",
        "fct_reconciliacion_bebidas_ancestral_diario",
        CATEGORIAS_BEBIDAS,
        BEBIDAS_WEEKLY_COLUMNS,
        BEBIDAS_DAILY_COLUMNS,
    )


def load_vinos(con):
    return _load_bebidas_like(
        con,
        "fct_reconciliacion_bebidas_ancestral",
        "fct_reconciliacion_bebidas_ancestral_diario",
        CATEGORIAS_VINOS,
        BEBIDAS_WEEKLY_COLUMNS,
        BEBIDAS_DAILY_COLUMNS,
    )


def load_insumos(con):
    weekly = con.execute(
        f"""
        SELECT {", ".join(INSUMOS_WEEKLY_COLUMNS)}
        FROM gold.fct_reconciliacion_insumos_ancestral
        WHERE diferencia IS NOT NULL
        ORDER BY producto, semana
        """
    ).df()
    daily = con.execute(
        f"""
        SELECT {", ".join(INSUMOS_DAILY_COLUMNS)}
        FROM gold.fct_reconciliacion_insumos_ancestral_diario
        ORDER BY producto, fecha
        """
    ).df()
    ventas_semana = con.execute(
        """
        SELECT producto, semana, SUM(ventas) AS ventas
        FROM gold.fct_reconciliacion_insumos_ancestral
        WHERE fecha_cierre > (SELECT MAX(fecha_cierre) FROM gold.fct_reconciliacion_insumos_ancestral) - INTERVAL '6 weeks'
        GROUP BY producto, semana
        ORDER BY semana
        """
    ).df()
    return weekly, daily, ventas_semana


def load_omuh_bebidas(con):
    weekly = con.execute(
        f"""
        SELECT {", ".join(OMUH_BEBIDAS_WEEKLY_COLUMNS)}
        FROM gold.fct_reconciliacion_bebidas_omuh
        WHERE diferencia IS NOT NULL
        ORDER BY producto, semana
        """
    ).df()
    daily = con.execute(
        f"""
        SELECT {", ".join(OMUH_BEBIDAS_DAILY_COLUMNS)}
        FROM gold.fct_reconciliacion_bebidas_omuh_diario
        ORDER BY producto, fecha
        """
    ).df()
    ventas_semana = con.execute(
        """
        SELECT producto, semana, SUM(ventas_totales) AS ventas
        FROM gold.fct_reconciliacion_bebidas_omuh
        WHERE fecha_cierre > (SELECT MAX(fecha_cierre) FROM gold.fct_reconciliacion_bebidas_omuh) - INTERVAL '6 weeks'
        GROUP BY producto, semana
        ORDER BY semana
        """
    ).df()
    return weekly, daily, ventas_semana


def load_omuh_insumos(con):
    weekly = con.execute(
        f"""
        SELECT {", ".join(OMUH_INSUMOS_WEEKLY_COLUMNS)}
        FROM gold.fct_reconciliacion_insumos_omuh
        WHERE diferencia IS NOT NULL
        ORDER BY producto, semana
        """
    ).df()
    daily = con.execute(
        f"""
        SELECT {", ".join(OMUH_INSUMOS_DAILY_COLUMNS)}
        FROM gold.fct_reconciliacion_insumos_omuh_diario
        ORDER BY producto, fecha
        """
    ).df()
    ventas_semana = con.execute(
        """
        SELECT producto, semana, SUM(ventas_totales) AS ventas
        FROM gold.fct_reconciliacion_insumos_omuh
        WHERE fecha_cierre > (SELECT MAX(fecha_cierre) FROM gold.fct_reconciliacion_insumos_omuh) - INTERVAL '6 weeks'
        GROUP BY producto, semana
        ORDER BY semana
        """
    ).df()
    return weekly, daily, ventas_semana


def load_resumen(con):
    # Replica el "Resumen Diferencias - Ancestral" de Metabase: todos los
    # productos con diferencia != 0 en la ultima reconciliacion, por area.
    categorias_beb = ", ".join(f"'{c}'" for c in CATEGORIAS_BEBIDAS)
    categorias_vin = ", ".join(f"'{c}'" for c in CATEGORIAS_VINOS)
    return con.execute(
        f"""
        SELECT 'Bebidas' AS area, producto, semana, diferencia
        FROM gold.fct_reconciliacion_bebidas_ancestral
        WHERE categoria IN ({categorias_beb}) AND diferencia IS NOT NULL AND diferencia <> 0
        UNION ALL
        SELECT 'Vinos' AS area, producto, semana, diferencia
        FROM gold.fct_reconciliacion_bebidas_ancestral
        WHERE categoria IN ({categorias_vin}) AND diferencia IS NOT NULL AND diferencia <> 0
        UNION ALL
        SELECT 'Insumos' AS area, producto, semana, diferencia
        FROM gold.fct_reconciliacion_insumos_ancestral
        WHERE diferencia IS NOT NULL AND diferencia <> 0
        ORDER BY area, producto
        """
    ).df()


def load_ventas(con):
    # Fuente de la "Tabla Dinamica" del Dashboard General v2 de Power BI:
    # fac_ventas_izi + Dim_Producto_iZi -> gold.fct_ventas_items + gold.dim_producto.
    # Turno/Canal/Pax/Ocupacion/Ticket Promedio/Stock del PBI original vienen de
    # fuentes que todavia no se migraron a DuckDB (Ocupacion, Ticket Promedio,
    # Pedidos Ya) - quedan pendientes para cuando se migren esas tablas.
    return con.execute(
        """
        SELECT
            v.fecha,
            v.producto,
            v.negocio,
            v.codigo_inventario AS cod_prod,
            COALESCE(d.categoria, 'Sin categoria') AS categoria,
            v.cantidad,
            v.precio_total AS ventas_bs,
            EXTRACT(YEAR FROM v.fecha) AS anio,
            strftime(v.fecha, '%Y-%m') AS mes,
            v.fecha::VARCHAR AS dia,
            strftime(v.fecha, '%G%V')::INTEGER AS semana_anio,
            strftime(v.fecha, '%a') AS dia_semana
        FROM gold.fct_ventas_items v
        LEFT JOIN gold.dim_producto d ON v.codigo_inventario = d.codigo_inventario
        """
    ).df()


def load_estados_resultados(con):
    # gold.fct_estados_resultados: el P&L mensual replicado del Power BI
    # "Estados de Resultados Ancestralrest S.R.L v2" (ver memoria
    # estados-resultados-pnl). "monto" ya trae el acumulado aplicado en
    # las filas de subtotal (calculos_eerr=1).
    return con.execute(
        """
        SELECT periodo, orden, grupo_eerr, categoria, calculos_eerr, monto
        FROM gold.fct_estados_resultados
        ORDER BY periodo, orden
        """
    ).df()


def load_all():
    con = _connect()
    try:
        return {
            "bebidas": load_bebidas(con),
            "vinos": load_vinos(con),
            "insumos": load_insumos(con),
            "resumen": load_resumen(con),
            "omuh_bebidas": load_omuh_bebidas(con),
            "omuh_insumos": load_omuh_insumos(con),
            "ventas": load_ventas(con),
        }
    finally:
        con.close()


def load_finanzas():
    con = _connect()
    try:
        return {"estados_resultados": load_estados_resultados(con)}
    finally:
        con.close()
