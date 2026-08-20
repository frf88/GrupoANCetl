from datetime import date

import pandas as pd
from dash import Input, Output, dash_table, dcc, html

from src.dashboard.data import NUMBER_FORMAT

TITLES = {"categoria": "Línea", "monto": "Monto (Bs)"}

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

# Verde/rojo neutrales, consistentes con la convencion de "diferencia" del
# resto del dashboard (theme.DIFERENCIA_BG/FG) pero aplicados por signo del
# monto en vez de por diferencia de inventario.
NEGATIVO_FG = "#8A4A24"
POSITIVO_FG = "#1F6B3A"


def _periodo_label(periodo):
    return f"{MESES[periodo.month - 1]} {periodo.year}"


def build_layout(estados_df, theme):
    periodos = sorted(estados_df["periodo"].unique(), reverse=True)
    periodo_options = [{"label": _periodo_label(p), "value": p.isoformat()} for p in periodos]
    # default: el mes actual o anterior mas reciente - evita arrancar en un
    # mes futuro con datos incompletos (ej. un adelanto de boda cobrado con
    # meses de anticipacion, que igual queda disponible en el dropdown)
    mes_actual = pd.Timestamp(date.today().replace(day=1))
    pasados = [p for p in periodos if p <= mes_actual]
    default_periodo = (pasados[0] if pasados else periodos[0]).isoformat() if periodos else None

    style_data_conditional = [
        {"if": {"row_index": "odd"}, "backgroundColor": theme.cream},
        {"if": {"filter_query": "{calculos_eerr} = 1"}, "backgroundColor": theme.cream_dim, "fontWeight": "700"},
        {"if": {"filter_query": "{monto} < 0", "column_id": "monto"}, "color": NEGATIVO_FG},
        {"if": {"filter_query": "{monto} > 0", "column_id": "monto"}, "color": POSITIVO_FG},
    ]

    return html.Div(
        style={"maxWidth": "760px", "margin": "0 auto", "padding": "24px 32px 48px"},
        children=[
            html.Div(
                style=theme.filter_style,
                children=[
                    html.Div(
                        [
                            html.Label("Mes", className="filtro-label"),
                            dcc.Dropdown(
                                id="finanzas-f-periodo",
                                options=periodo_options,
                                value=default_periodo,
                                clearable=False,
                                style=theme.dropdown_style,
                            ),
                        ]
                    ),
                ],
            ),
            html.H4("Estado de Resultados", style=theme.section_title_style),
            dash_table.DataTable(
                id="finanzas-tabla",
                columns=[
                    {"name": TITLES["categoria"], "id": "categoria"},
                    {"name": TITLES["monto"], "id": "monto", "type": "numeric", "format": NUMBER_FORMAT},
                ],
                style_header=theme.table_style_header,
                style_cell=theme.table_style_cell,
                style_table=theme.table_style_table,
                style_cell_conditional=[{"if": {"column_id": "monto"}, "textAlign": "right"}],
                style_data_conditional=style_data_conditional,
                page_action="none",
                fixed_rows={"headers": True},
            ),
        ],
    )


def register_callbacks(app, estados_df):
    @app.callback(
        Output("finanzas-tabla", "data"),
        Input("finanzas-f-periodo", "value"),
    )
    def actualizar(periodo):
        df = estados_df
        if periodo:
            df = df[df["periodo"] == pd.Timestamp(periodo)]
        out = df.sort_values("orden")[["categoria", "monto", "calculos_eerr"]].copy()
        out["monto"] = out["monto"].round(0)
        return out.to_dict("records")
