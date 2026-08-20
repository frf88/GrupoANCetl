from datetime import date

from dash import Input, Output, dash_table, dcc, html

from src.dashboard.data import NUMBER_FORMAT

MESES_ABREV = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# Verde/rojo neutrales, consistentes con la convencion de "diferencia" del
# resto del dashboard (theme.DIFERENCIA_BG/FG) pero aplicados por signo del
# monto en vez de por diferencia de inventario.
NEGATIVO_FG = "#8A4A24"
POSITIVO_FG = "#1F6B3A"


def _mes_col(mes):
    return f"m{mes:02d}"


def build_layout(estados_df, theme):
    anios = sorted(estados_df["periodo"].dt.year.unique(), reverse=True)
    anio_actual = date.today().year
    default_anio = anio_actual if anio_actual in anios else (anios[0] if anios else None)

    return html.Div(
        style={"maxWidth": "1100px", "margin": "0 auto", "padding": "24px 32px 48px"},
        children=[
            html.Div(
                style=theme.filter_style,
                children=[
                    html.Div(
                        [
                            html.Label("Año", className="filtro-label"),
                            dcc.Dropdown(
                                id="finanzas-f-anio",
                                options=[{"label": str(a), "value": a} for a in anios],
                                value=default_anio,
                                clearable=False,
                                style={"width": "140px"},
                            ),
                        ]
                    ),
                ],
            ),
            html.H4("Estado de Resultados", style=theme.section_title_style),
            dash_table.DataTable(
                id="finanzas-tabla",
                style_header=theme.table_style_header,
                style_cell=theme.table_style_cell,
                style_table=theme.table_style_table,
                page_action="none",
                fixed_rows={"headers": True},
                fixed_columns={"headers": True, "data": 1},
            ),
        ],
    )


def register_callbacks(app, estados_df, theme):
    @app.callback(
        Output("finanzas-tabla", "columns"),
        Output("finanzas-tabla", "data"),
        Output("finanzas-tabla", "style_cell_conditional"),
        Output("finanzas-tabla", "style_data_conditional"),
        Input("finanzas-f-anio", "value"),
    )
    def actualizar(anio):
        if anio is None:
            return [], [], [], []

        df_anio = estados_df[estados_df["periodo"].dt.year == anio]
        meses_presentes = sorted(df_anio["periodo"].dt.month.unique())
        lineas = df_anio[["orden", "categoria", "calculos_eerr"]].drop_duplicates().sort_values("orden")

        columns = [{"name": "Línea", "id": "categoria"}]
        for m in meses_presentes:
            columns.append(
                {"name": MESES_ABREV[m - 1], "id": _mes_col(m), "type": "numeric", "format": NUMBER_FORMAT}
            )
        columns.append({"name": "Total Año", "id": "total", "type": "numeric", "format": NUMBER_FORMAT})

        rows = []
        for _, linea in lineas.iterrows():
            sub = df_anio[df_anio["orden"] == linea["orden"]]
            row = {"categoria": linea["categoria"], "calculos_eerr": int(linea["calculos_eerr"])}
            total = 0.0
            for m in meses_presentes:
                valores = sub[sub["periodo"].dt.month == m]["monto"]
                if len(valores):
                    v = round(float(valores.iloc[0]))
                    row[_mes_col(m)] = v
                    total += v
                else:
                    row[_mes_col(m)] = None
            row["total"] = round(total)
            rows.append(row)

        month_ids = [_mes_col(m) for m in meses_presentes]
        style_cell_conditional = [
            {"if": {"column_id": c}, "textAlign": "right"} for c in (month_ids + ["total"])
        ] + [{"if": {"column_id": "categoria"}, "minWidth": "180px"}]
        style_data_conditional = [
            {"if": {"row_index": "odd"}, "backgroundColor": theme.cream},
            {"if": {"filter_query": "{calculos_eerr} = 1"}, "backgroundColor": theme.cream_dim, "fontWeight": "700"},
            {"if": {"column_id": "total"}, "fontWeight": "700", "borderLeft": f"2px solid {theme.cream_dim}"},
        ]
        for c in month_ids + ["total"]:
            style_data_conditional.append({"if": {"filter_query": f"{{{c}}} < 0", "column_id": c}, "color": NEGATIVO_FG})
            style_data_conditional.append({"if": {"filter_query": f"{{{c}}} > 0", "column_id": c}, "color": POSITIVO_FG})

        return columns, rows, style_cell_conditional, style_data_conditional
