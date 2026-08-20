from datetime import date

import pandas as pd
from dash import Input, Output, dash_table, dcc, html

from src.dashboard.data import NUMBER_FORMAT
from src.dashboard.theme import GENERAL as theme

# Dimensiones disponibles para filas/columnas. Turno y Canal existen en el
# Power BI original pero sus fuentes (Ocupacion, Pedidos Ya) todavia no estan
# migradas a DuckDB, asi que no aparecen aca todavia.
DIM_COLUMNS = {
    "Año": "anio",
    "Mes": "mes",
    "Semana Año": "semana_anio",
    "Día Semana": "dia_semana",
    "Fecha": "dia",
    "Negocio": "negocio",
    "Categoría": "categoria",
    "Producto": "producto",
    "Cod Prod": "cod_prod",
}
# orden de anidado cuando se combinan varias dimensiones de fila (de mas
# gruesa a mas fina) - Power BI respeta el orden de click, aca se aproxima
# con una jerarquia fija razonable.
DIM_HIERARCHY_ORDER = ["anio", "mes", "semana_anio", "dia_semana", "dia", "negocio", "categoria", "producto", "cod_prod"]

METRICS = {
    "Ventas Bs": ("ventas_bs", "sum"),
    "Cantidad": ("cantidad", "sum"),
    "Ventas x Día": ("ventas_bs", "avg_per_day"),
}
NEGOCIOS = ["Ancestral", "omuH"]
DIA_SEMANA_ORDEN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
# columnas de valor corto (semana, año, dia de la semana) - no necesitan
# tanto ancho como producto/categoria
NARROW_COLS = {"semana_anio", "anio", "dia_semana", "dia"}


def _order_dims(dims):
    return [d for d in DIM_HIERARCHY_ORDER if d in dims]


def _pivot(df, row_dims, col_dim, metric_label):
    col, agg = METRICS[metric_label]
    row_dims = _order_dims(row_dims) or ["anio"]

    if "dia_semana" in row_dims:
        df = df.copy()
        df["dia_semana"] = pd.Categorical(df["dia_semana"], categories=DIA_SEMANA_ORDEN, ordered=True)

    if agg == "avg_per_day":
        daily = df.groupby(row_dims + [col_dim, "dia"], as_index=False)[col].sum()
        base = daily.groupby(row_dims + [col_dim], as_index=False).agg(value=(col, "sum"), ndias=("dia", "nunique"))
        base["value"] = base["value"] / base["ndias"]
        base = base.drop(columns="ndias")
    else:
        base = df.groupby(row_dims + [col_dim], as_index=False)[col].sum().rename(columns={col: "value"})

    pivot = base.pivot_table(index=row_dims, columns=col_dim, values="value", aggfunc="sum", fill_value=0)
    if pivot.shape[1] > 1:
        pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.round(0).reset_index()
    pivot.columns = [str(c) for c in pivot.columns]
    return pivot, row_dims


def build_layout(ventas_df):
    fecha_min = ventas_df["fecha"].min()
    hoy = date.today()
    categoria_options = sorted(ventas_df["categoria"].unique())
    producto_options = sorted(ventas_df["producto"].unique())
    semana_options = sorted(ventas_df["semana_anio"].unique())

    dim_row_options = [{"label": f" {k}", "value": k} for k in DIM_COLUMNS]
    metric_options = [{"label": f" {k}", "value": k} for k in METRICS]

    return html.Div(
        style={"maxWidth": "1700px", "margin": "0 auto", "padding": "24px 32px 48px", "display": "flex", "gap": "24px"},
        children=[
            html.Div(
                style={"width": "220px", "flexShrink": 0},
                children=[
                    html.Label("Rango de fechas", className="filtro-label"),
                    dcc.DatePickerRange(
                        id="ventas-f-fechas",
                        min_date_allowed=fecha_min,
                        max_date_allowed=hoy,
                        start_date=fecha_min,
                        end_date=hoy,
                        display_format="D/M/YYYY",
                        style={"marginBottom": "16px"},
                    ),
                    html.Label("Categoría", className="filtro-label"),
                    dcc.Dropdown(id="ventas-f-categoria", options=categoria_options, multi=True, placeholder="Todas", style={"marginBottom": "16px"}),
                    html.Label("Producto", className="filtro-label"),
                    dcc.Dropdown(id="ventas-f-producto", options=producto_options, multi=True, placeholder="Todos", style={"marginBottom": "16px"}),
                    html.Label("Semana Año", className="filtro-label"),
                    dcc.Dropdown(id="ventas-f-semana", options=semana_options, multi=True, placeholder="Todas", style={"marginBottom": "16px"}),
                    html.Label("Negocio", className="filtro-label"),
                    dcc.Checklist(
                        id="ventas-f-negocio",
                        options=[{"label": f" {n}", "value": n} for n in NEGOCIOS],
                        value=list(NEGOCIOS),
                        labelStyle={"display": "block", "marginBottom": "4px"},
                        style={"marginBottom": "16px", "fontFamily": theme.font_body, "fontSize": "13px"},
                    ),
                    html.Label("Métrica", className="filtro-label"),
                    dcc.RadioItems(
                        id="ventas-f-metrica",
                        options=metric_options,
                        value="Ventas Bs",
                        labelStyle={"display": "block", "marginBottom": "4px"},
                        style={"fontFamily": theme.font_body, "fontSize": "13px", "marginBottom": "16px"},
                    ),
                    html.Label("Filas (podés combinar varias)", className="filtro-label"),
                    dcc.Checklist(
                        id="ventas-row-dims",
                        options=dim_row_options,
                        value=["Semana Año"],
                        labelStyle={"display": "block", "marginBottom": "4px"},
                        style={"fontFamily": theme.font_body, "fontSize": "13px"},
                    ),
                    html.P(
                        "Turno, Canal, Pax, Ocupación, Ticket Promedio y Stock del dashboard original todavía no están migrados a este stack.",
                        style={"fontSize": "11px", "color": theme.carbon, "opacity": 0.6, "marginTop": "20px", "fontFamily": theme.font_body},
                    ),
                ],
            ),
            html.Div(
                style={"flex": 1, "minWidth": 0},
                children=[
                    html.H4(id="ventas-titulo", style=theme.section_title_style),
                    dash_table.DataTable(
                        id="ventas-tabla",
                        style_header={**theme.table_style_header, "borderRight": f"1px solid {theme.cream}"},
                        style_cell={**theme.table_style_cell, "borderRight": f"1px solid {theme.cream_dim}"},
                        style_table=theme.table_style_table,
                        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": theme.cream}],
                        page_action="none",
                        fixed_rows={"headers": True},
                        sort_action="native",
                    ),
                ],
            ),
        ],
    )


def register_callbacks(app, ventas_df):
    @app.callback(
        Output("ventas-tabla", "data"),
        Output("ventas-tabla", "columns"),
        Output("ventas-tabla", "style_cell_conditional"),
        Output("ventas-tabla", "style_header_conditional"),
        Output("ventas-titulo", "children"),
        Input("ventas-f-fechas", "start_date"),
        Input("ventas-f-fechas", "end_date"),
        Input("ventas-f-categoria", "value"),
        Input("ventas-f-producto", "value"),
        Input("ventas-f-semana", "value"),
        Input("ventas-f-negocio", "value"),
        Input("ventas-f-metrica", "value"),
        Input("ventas-row-dims", "value"),
    )
    def actualizar(start_date, end_date, categorias, productos, semanas, negocios, metrica, row_dim_labels):
        df = ventas_df
        if start_date:
            df = df[df["fecha"] >= pd.Timestamp(start_date)]
        if end_date:
            df = df[df["fecha"] <= pd.Timestamp(end_date)]
        if categorias:
            df = df[df["categoria"].isin(categorias)]
        if productos:
            df = df[df["producto"].isin(productos)]
        if semanas:
            df = df[df["semana_anio"].isin(semanas)]
        if negocios:
            df = df[df["negocio"].isin(negocios)]
        else:
            df = df.iloc[0:0]

        row_dims = [DIM_COLUMNS[label] for label in (row_dim_labels or ["Año"])]
        col_dim = DIM_COLUMNS["Negocio"]

        if df.empty:
            return [], [], [], [], f"{metrica} — sin datos para este filtro"

        pivot, ordered_dims = _pivot(df, row_dims, col_dim, metrica)
        row_labels = [k for k, v in DIM_COLUMNS.items() if v in ordered_dims]
        titulo = f"{metrica} según {', '.join(row_labels)}"

        columns = [
            {"name": c, "id": c, "type": "numeric", "format": NUMBER_FORMAT}
            if pd.api.types.is_numeric_dtype(pivot[c])
            else {"name": c, "id": c}
            for c in pivot.columns
        ]
        style_cell_conditional = [
            {
                "if": {"column_id": c},
                "textAlign": "left" if c in ordered_dims else "center",
                **({"width": "70px"} if c in NARROW_COLS else {}),
            }
            for c in pivot.columns
        ]
        style_header_conditional = [
            {"if": {"column_id": c}, "textAlign": "left" if c in ordered_dims else "center"} for c in pivot.columns
        ]
        return pivot.to_dict("records"), columns, style_cell_conditional, style_header_conditional, titulo
