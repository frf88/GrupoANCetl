from dash import Input, Output, dash_table, dcc, html

from src.dashboard.theme import DIFERENCIA_BG, DIFERENCIA_FG

TITLES = {"area": "Área", "producto": "Producto", "semana": "Semana", "diferencia": "Diferencia"}


def build_layout(resumen_df, ultima_semana_completa, theme):
    semana_options = sorted(resumen_df["semana"].unique(), reverse=True)
    if ultima_semana_completa and ultima_semana_completa not in semana_options:
        semana_options = sorted(set(semana_options) | {ultima_semana_completa}, reverse=True)

    style_data_conditional = [
        {"if": {"row_index": "odd"}, "backgroundColor": theme.cream},
        {"if": {"filter_query": "{diferencia} != 0"}, "backgroundColor": DIFERENCIA_BG, "color": DIFERENCIA_FG, "fontWeight": "600"},
    ]

    return html.Div(
        style={"maxWidth": "1000px", "margin": "0 auto", "padding": "24px 32px 48px"},
        children=[
            html.Div(
                style=theme.filter_style,
                children=[
                    html.Div(
                        [
                            html.Label("Semana", className="filtro-label"),
                            dcc.Dropdown(
                                id="resumen-f-semana",
                                options=semana_options,
                                value=ultima_semana_completa,
                                clearable=True,
                                style=theme.dropdown_style,
                            ),
                        ]
                    ),
                ],
            ),
            html.H4("Productos con Diferencia", style=theme.section_title_style),
            html.P(
                "Solo se listan los productos donde el inventario calculado no coincide con el conteo físico.",
                style={"fontFamily": theme.font_body, "fontSize": "13px", "color": theme.carbon, "opacity": 0.75, "marginTop": 0},
            ),
            dash_table.DataTable(
                id="resumen-tabla",
                columns=[{"name": TITLES[c], "id": c} for c in ("area", "producto", "semana", "diferencia")],
                style_header=theme.table_style_header,
                style_cell=theme.table_style_cell,
                style_table=theme.table_style_table,
                style_data_conditional=style_data_conditional,
                page_action="none",
                fixed_rows={"headers": True},
                sort_action="native",
            ),
        ],
    )


def register_callbacks(app, resumen_df):
    @app.callback(
        Output("resumen-tabla", "data"),
        Input("resumen-f-semana", "value"),
    )
    def actualizar(semana):
        df = resumen_df
        if semana:
            df = df[df["semana"] == semana]
        out = df.copy()
        out["diferencia"] = out["diferencia"].round(0)
        return out.to_dict("records")
