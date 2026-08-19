import pandas as pd
from dash import Input, Output, State, callback_context, dash_table, dcc, html, no_update

from src.dashboard.data import NULL_AS_DASH


def _format_table_df(df, columns):
    out = df[columns].copy()
    for col in columns:
        if col in ("producto", "semana", "dia"):
            continue
        if col == "fecha":
            out[col] = out[col].dt.strftime("%Y-%m-%d")
        elif col in NULL_AS_DASH:
            out[col] = out[col].round(0).apply(lambda v: "–" if pd.isna(v) else str(int(v)))
        else:
            out[col] = out[col].round(0)
    return out


def build_layout(tab_key, weekly_df, daily_df, weekly_titles, daily_titles, theme):
    """Layout de una pestana de reconciliacion (filtros + tabla semanal + tabla diaria + grafico)."""
    weekly_cols = [c for c in weekly_df.columns if c != "fecha_cierre"]
    daily_cols = list(daily_df.columns)
    semana_options = sorted(weekly_df["semana"].unique(), reverse=True)
    ultima_semana_completa = semana_options[0] if semana_options else None
    producto_options = sorted(weekly_df["producto"].unique())

    def cid(name):
        return f"{tab_key}-{name}"

    return html.Div(
        style={"maxWidth": "1700px", "margin": "0 auto", "padding": "24px 32px 48px"},
        children=[
            html.Div(
                style=theme.filter_style,
                children=[
                    html.Div(
                        [
                            html.Label("Semana", className="filtro-label"),
                            dcc.Dropdown(
                                id=cid("f-semana"),
                                options=semana_options,
                                value=ultima_semana_completa,
                                clearable=True,
                                style=theme.dropdown_style,
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Producto", className="filtro-label"),
                            dcc.Dropdown(id=cid("f-producto"), options=producto_options, placeholder="Todos", style=theme.dropdown_style),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Filtro", className="filtro-label"),
                            dcc.Checklist(
                                id=cid("f-dif-toggle"),
                                options=[{"label": " Solo con diferencia", "value": "on"}],
                                value=[],
                                style={"paddingBottom": "8px"},
                            ),
                        ]
                    ),
                    html.Div(
                        "Tip: hacé click en una fila (producto) o en una barra del gráfico (semana) para filtrar todo el tablero.",
                        style={
                            "fontFamily": theme.font_body,
                            "fontSize": "12px",
                            "fontStyle": "italic",
                            "color": theme.carbon,
                            "opacity": 0.65,
                            "paddingBottom": "8px",
                        },
                    ),
                ],
            ),
            html.H4("Reconciliación Semanal", style=theme.section_title_style),
            html.Div(
                dash_table.DataTable(
                    id=cid("tabla-semanal"),
                    columns=[{"name": weekly_titles[c], "id": c} for c in weekly_cols],
                    style_header=theme.table_style_header,
                    style_cell=theme.table_style_cell,
                    style_table=theme.table_style_table,
                    style_data_conditional=theme.row_highlight_style,
                    page_action="none",
                    fixed_rows={"headers": True},
                    sort_action="native",
                    cell_selectable=True,
                ),
                style={"marginBottom": "40px"},
            ),
            html.H4("Detalle Diario", style=theme.section_title_style),
            html.Div(
                dash_table.DataTable(
                    id=cid("tabla-diaria"),
                    columns=[{"name": daily_titles[c], "id": c} for c in daily_cols],
                    style_header=theme.table_style_header,
                    style_cell=theme.table_style_cell,
                    style_table=theme.table_style_table,
                    style_data_conditional=theme.cell_highlight_style,
                    page_action="none",
                    fixed_rows={"headers": True},
                    sort_action="native",
                    cell_selectable=True,
                ),
                style={"marginBottom": "40px"},
            ),
            html.H4("Ventas por Semana (últimas 6 semanas)", style=theme.section_title_style),
            html.Div(
                dcc.Graph(id=cid("grafico-ventas"), config={"displayModeBar": False}),
                style={"background": theme.white, "border": f"1px solid {theme.cream_dim}", "borderRadius": "4px", "padding": "12px"},
            ),
        ],
    )


def register_callbacks(app, tab_key, weekly_df, daily_df, ventas_semana_df, theme):
    weekly_cols = [c for c in weekly_df.columns if c != "fecha_cierre"]
    daily_cols = list(daily_df.columns)

    def cid(name):
        return f"{tab_key}-{name}"

    @app.callback(
        Output(cid("f-producto"), "value"),
        Input(cid("tabla-semanal"), "active_cell"),
        Input(cid("tabla-diaria"), "active_cell"),
        State(cid("tabla-semanal"), "data"),
        State(cid("tabla-diaria"), "data"),
        prevent_initial_call=True,
    )
    def filtrar_por_click_en_tabla(cell_semanal, cell_diaria, data_semanal, data_diaria):
        trigger = callback_context.triggered[0]["prop_id"] if callback_context.triggered else ""
        if trigger.startswith(cid("tabla-semanal")) and cell_semanal:
            return data_semanal[cell_semanal["row"]]["producto"]
        if trigger.startswith(cid("tabla-diaria")) and cell_diaria:
            return data_diaria[cell_diaria["row"]]["producto"]
        return no_update

    @app.callback(
        Output(cid("f-semana"), "value"),
        Input(cid("grafico-ventas"), "clickData"),
        prevent_initial_call=True,
    )
    def filtrar_por_click_en_grafico(click_data):
        if not click_data:
            return no_update
        return click_data["points"][0]["x"]

    @app.callback(
        Output(cid("tabla-semanal"), "data"),
        Output(cid("tabla-diaria"), "data"),
        Output(cid("grafico-ventas"), "figure"),
        Input(cid("f-semana"), "value"),
        Input(cid("f-producto"), "value"),
        Input(cid("f-dif-toggle"), "value"),
    )
    def actualizar(semana, producto, dif_toggle):
        w = weekly_df
        d = daily_df
        v = ventas_semana_df

        if semana:
            w = w[w["semana"] == semana]
            d = d[d["semana"] == semana]
        if producto:
            w = w[w["producto"] == producto]
            d = d[d["producto"] == producto]
            v = v[v["producto"] == producto]
        if "on" in (dif_toggle or []):
            w = w[w["diferencia"] != 0]
            d = d[d["diferencia"] != 0]

        v_agg = v.groupby("semana", as_index=False)["ventas"].sum().sort_values("semana")

        w_display = _format_table_df(w, weekly_cols)
        d_display = _format_table_df(d, daily_cols)

        return w_display.to_dict("records"), d_display.to_dict("records"), theme.bar_chart(v_agg)
