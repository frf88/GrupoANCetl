from datetime import date

from dash import Input, Output, dash_table, dcc, html

from src.dashboard.data import NUMBER_FORMAT

MESES_ABREV = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# Verde/rojo neutrales, consistentes con la convencion de "diferencia" del
# resto del dashboard (theme.DIFERENCIA_BG/FG) pero aplicados por signo del
# monto en vez de por diferencia de inventario.
NEGATIVO_FG = "#8A4A24"
POSITIVO_FG = "#1F6B3A"

# Subtotales que se ven afectados si se excluye "Salarios Socios" del
# calculo (todo lo que va DESPUES de esa linea en el orden del EERR;
# Margen Bruto queda antes, no se toca).
SUBTOTALES_AFECTADOS = ("EBITDA", "Resultado", "Resultado Total")


def _mes_col(mes):
    return f"m{mes:02d}"


def build_layout(estados_df, theme):
    anios = sorted(estados_df["periodo"].dt.year.unique(), reverse=True)
    anio_actual = date.today().year
    default_anio = anio_actual if anio_actual in anios else (anios[0] if anios else None)

    negocios = sorted(n for n in estados_df["negocio"].unique() if n != "Todos")
    negocio_options = [{"label": "Todos", "value": "Todos"}] + [{"label": n, "value": n} for n in negocios]

    return html.Div(
        style={"width": "100%", "padding": "24px 32px 48px", "boxSizing": "border-box"},
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
                    html.Div(
                        [
                            html.Label("Negocio", className="filtro-label"),
                            dcc.Dropdown(
                                id="finanzas-f-negocio",
                                options=negocio_options,
                                value="Todos",
                                clearable=False,
                                style={"width": "180px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            dcc.Checklist(
                                id="finanzas-f-sin-socios",
                                options=[{"label": " Excluir Salarios Socios del resultado", "value": "excluir"}],
                                value=[],
                                style={"fontFamily": theme.font_body, "fontSize": "13px", "color": theme.carbon},
                            ),
                        ],
                        style={"marginBottom": "2px"},
                    ),
                ],
            ),
            html.H4("Estado de Resultados", style=theme.section_title_style),
            dash_table.DataTable(
                id="finanzas-tabla",
                style_header=theme.table_style_header,
                style_cell=theme.table_style_cell,
                style_table={**theme.table_style_table, "overflowX": "auto", "width": "100%", "minWidth": "100%"},
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
        Input("finanzas-f-negocio", "value"),
        Input("finanzas-f-sin-socios", "value"),
    )
    def actualizar(anio, negocio, sin_socios_flags):
        if anio is None:
            return [], [], [], []
        excluir_socios = "excluir" in (sin_socios_flags or [])

        df_anio = estados_df[(estados_df["periodo"].dt.year == anio) & (estados_df["negocio"] == (negocio or "Todos"))]
        meses_presentes = sorted(df_anio["periodo"].dt.month.unique())
        # no mostrar meses futuros con datos adelantados/parciales (ej. un
        # adelanto de boda cobrado con meses de anticipacion) - solo aplica
        # al anio en curso, los anios pasados muestran todos sus meses
        hoy = date.today()
        if anio == hoy.year:
            meses_presentes = [m for m in meses_presentes if m <= hoy.month]
        lineas = df_anio[["orden", "categoria", "calculos_eerr"]].drop_duplicates().sort_values("orden")

        columns = [{"name": "Línea", "id": "categoria"}]
        for m in meses_presentes:
            columns.append(
                {"name": MESES_ABREV[m - 1], "id": _mes_col(m), "type": "numeric", "format": NUMBER_FORMAT}
            )
        columns.append({"name": "Total Año", "id": "total", "type": "numeric", "format": NUMBER_FORMAT})

        month_ids = [_mes_col(m) for m in meses_presentes]
        rows_by_categoria = {}
        rows = []
        for _, linea in lineas.iterrows():
            sub = df_anio[df_anio["orden"] == linea["orden"]]
            row = {"categoria": linea["categoria"], "calculos_eerr": int(linea["calculos_eerr"])}
            total = 0.0
            for m in meses_presentes:
                valores = sub[sub["periodo"].dt.month == m]["monto"]
                v = round(float(valores.iloc[0])) if len(valores) else None
                row[_mes_col(m)] = v
                total += v or 0
            row["total"] = round(total)
            rows.append(row)
            rows_by_categoria[linea["categoria"]] = row

        if excluir_socios and "Salarios Socios" in rows_by_categoria:
            socios = rows_by_categoria["Salarios Socios"]
            for categoria in SUBTOTALES_AFECTADOS:
                if categoria in rows_by_categoria:
                    target = rows_by_categoria[categoria]
                    for col in month_ids + ["total"]:
                        if target.get(col) is not None:
                            target[col] = round(target[col] - (socios.get(col) or 0))
            rows = [r for r in rows if r["categoria"] != "Salarios Socios"]

        # anchos explicitos: "Linea" fija, las columnas de mes+total se
        # reparten el resto del ancho en partes iguales - sin esto la
        # tabla de Dash solo ocupa el ancho minimo de su contenido, no el
        # del contenedor (aunque el contenedor si tenga width:100%).
        categoria_width = "220px"
        n_flex = len(month_ids) + 1
        flex_width = f"calc((100% - {categoria_width}) / {n_flex})"
        style_cell_conditional = [
            {"if": {"column_id": c}, "textAlign": "right", "width": flex_width, "minWidth": "70px"}
            for c in (month_ids + ["total"])
        ] + [{"if": {"column_id": "categoria"}, "width": categoria_width, "minWidth": categoria_width}]
        style_data_conditional = [
            {"if": {"row_index": "odd"}, "backgroundColor": theme.cream},
            {"if": {"filter_query": "{calculos_eerr} = 1"}, "backgroundColor": theme.cream_dim, "fontWeight": "700"},
            {"if": {"column_id": "total"}, "fontWeight": "700", "borderLeft": f"2px solid {theme.cream_dim}"},
        ]
        for c in month_ids + ["total"]:
            style_data_conditional.append({"if": {"filter_query": f"{{{c}}} < 0", "column_id": c}, "color": NEGATIVO_FG})
            style_data_conditional.append({"if": {"filter_query": f"{{{c}}} > 0", "column_id": c}, "color": POSITIVO_FG})

        return columns, rows, style_cell_conditional, style_data_conditional
