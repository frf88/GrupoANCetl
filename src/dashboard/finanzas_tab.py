from datetime import date

from dash import Input, Output, State, dash_table, dcc, html
from dash.exceptions import PreventUpdate

from src.dashboard.data import NUMBER_FORMAT
from src.transform.gold_estados_resultados import ORDEN_EERR_ROWS

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

# Jerarquia Grupos EERR -> categorias (mismo agrupamiento de la tabla
# Orden EERR del Power BI, ej. "Salarios" agrupa a Salarios Fijos/
# Semanales/Extras/Socios). Los grupos con una sola categoria (Ingresos,
# Compras, Margen Bruto, EBITDA...) se muestran directo, sin flecha de
# expandir - solo los que tienen mas de una categoria son desplegables.
GRUPOS = {}
for _grupo, _orden_grupo, _categoria, _calculos, _orden in ORDEN_EERR_ROWS:
    GRUPOS.setdefault(_grupo, {"orden_grupo": _orden_grupo, "categorias": []})
    GRUPOS[_grupo]["categorias"].append(_categoria)
GRUPOS_ORDENADOS = sorted(GRUPOS.items(), key=lambda kv: kv[1]["orden_grupo"])


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
            dcc.Store(id="finanzas-expandido", data=[]),
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
            html.P(
                "Clic en un grupo (Salarios, Costos, Gastos Fijos) para desplegar el detalle.",
                style={"fontFamily": theme.font_body, "fontSize": "13px", "color": theme.carbon, "opacity": 0.75, "marginTop": 0},
            ),
            dash_table.DataTable(
                id="finanzas-tabla",
                style_header=theme.table_style_header,
                style_cell=theme.table_style_cell,
                # el P&L siempre tiene 13 grupos (o menos, si se excluye
                # Salarios Socios) - a diferencia de otras tablas del
                # dashboard con listas largas de productos, esta no
                # necesita scroll interno: se le quita el maxHeight/
                # overflowY del theme para que se vea completa.
                style_table={
                    **theme.table_style_table,
                    "overflowX": "auto",
                    "overflowY": "visible",
                    "maxHeight": "none",
                    "width": "100%",
                    "minWidth": "100%",
                },
                page_action="none",
            ),
        ],
    )


def _construir_filas(df_anio, meses_presentes, excluir_socios):
    lineas = df_anio[["orden", "categoria", "calculos_eerr"]].drop_duplicates().sort_values("orden")
    month_ids = [_mes_col(m) for m in meses_presentes]

    rows_by_categoria = {}
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
        rows_by_categoria[linea["categoria"]] = row

    if excluir_socios and "Salarios Socios" in rows_by_categoria:
        socios = rows_by_categoria.pop("Salarios Socios")
        for categoria in SUBTOTALES_AFECTADOS:
            if categoria in rows_by_categoria:
                target = rows_by_categoria[categoria]
                for col in month_ids + ["total"]:
                    if target.get(col) is not None:
                        target[col] = round(target[col] - (socios.get(col) or 0))

    return rows_by_categoria, month_ids


def _construir_jerarquia(rows_by_categoria, month_ids, expandido):
    expandido = set(expandido or [])
    display_rows = []
    for grupo, info in GRUPOS_ORDENADOS:
        categorias_grupo = [c for c in info["categorias"] if c in rows_by_categoria]
        if not categorias_grupo:
            continue
        tiene_hijos = len(categorias_grupo) > 1
        calculos_eerr = rows_by_categoria[categorias_grupo[0]]["calculos_eerr"] if not tiene_hijos else 0
        icono = ("▾ " if grupo in expandido else "▸ ") if tiene_hijos else ""
        group_row = {
            "categoria": f"{icono}{grupo}",
            "calculos_eerr": calculos_eerr,
            "_grupo_key": grupo,
            "_tiene_hijos": 1 if tiene_hijos else 0,
            "_indent": 0,
        }
        for col in month_ids + ["total"]:
            valores = [rows_by_categoria[c].get(col) for c in categorias_grupo]
            valores = [v for v in valores if v is not None]
            group_row[col] = round(sum(valores)) if valores else None
        display_rows.append(group_row)

        if tiene_hijos and grupo in expandido:
            for categoria in categorias_grupo:
                hijo = dict(rows_by_categoria[categoria])
                hijo["_grupo_key"] = None
                hijo["_tiene_hijos"] = 0
                hijo["_indent"] = 1
                display_rows.append(hijo)

    return display_rows


def register_callbacks(app, estados_df, theme):
    @app.callback(
        Output("finanzas-expandido", "data"),
        Input("finanzas-tabla", "active_cell"),
        State("finanzas-tabla", "data"),
        State("finanzas-expandido", "data"),
        prevent_initial_call=True,
    )
    def alternar_grupo(active_cell, data, expandido):
        if not active_cell or active_cell.get("column_id") != "categoria":
            raise PreventUpdate
        fila = data[active_cell["row"]]
        if not fila.get("_tiene_hijos"):
            raise PreventUpdate
        grupo = fila["_grupo_key"]
        expandido = set(expandido or [])
        if grupo in expandido:
            expandido.discard(grupo)
        else:
            expandido.add(grupo)
        return list(expandido)

    @app.callback(
        Output("finanzas-tabla", "columns"),
        Output("finanzas-tabla", "data"),
        Output("finanzas-tabla", "style_cell_conditional"),
        Output("finanzas-tabla", "style_data_conditional"),
        Input("finanzas-f-anio", "value"),
        Input("finanzas-f-negocio", "value"),
        Input("finanzas-f-sin-socios", "value"),
        Input("finanzas-expandido", "data"),
    )
    def actualizar(anio, negocio, sin_socios_flags, expandido):
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

        rows_by_categoria, month_ids = _construir_filas(df_anio, meses_presentes, excluir_socios)
        rows = _construir_jerarquia(rows_by_categoria, month_ids, expandido)

        columns = [{"name": "Línea", "id": "categoria"}]
        for m in meses_presentes:
            columns.append(
                {"name": MESES_ABREV[m - 1], "id": _mes_col(m), "type": "numeric", "format": NUMBER_FORMAT}
            )
        columns.append({"name": "Total Año", "id": "total", "type": "numeric", "format": NUMBER_FORMAT})

        # anchos explicitos: "Linea" fija, las columnas de mes+total se
        # reparten el resto del ancho en partes iguales - sin esto la
        # tabla de Dash solo ocupa el ancho minimo de su contenido, no el
        # del contenedor (aunque el contenedor si tenga width:100%).
        categoria_width = "220px"
        n_flex = len(month_ids) + 1
        flex_width = f"calc((100% - {categoria_width}) / {n_flex})"
        # lineas verticales entre columnas: 1px para separar meses, mas
        # marcada (2px) antes de Total Año para distinguirla. style_cell_
        # conditional aplica tanto al header como a las celdas de datos,
        # asi que el encabezado queda alineado igual que su columna
        # (Linea a la izquierda, metricas al centro) sin definirlo aparte.
        style_cell_conditional = [
            {"if": {"column_id": "categoria"}, "textAlign": "left", "width": categoria_width, "minWidth": categoria_width},
        ] + [
            {
                "if": {"column_id": c},
                "textAlign": "center",
                "width": flex_width,
                "minWidth": "70px",
                "borderLeft": f"2px solid {theme.cream_dim}" if c == "total" else f"1px solid {theme.cream_dim}",
            }
            for c in (month_ids + ["total"])
        ]
        style_data_conditional = [
            {"if": {"row_index": "odd"}, "backgroundColor": theme.cream},
            {"if": {"filter_query": "{calculos_eerr} = 1"}, "backgroundColor": theme.cream_dim, "fontWeight": "700"},
            {"if": {"filter_query": "{_tiene_hijos} = 1"}, "fontWeight": "700", "cursor": "pointer"},
            {"if": {"filter_query": "{_indent} = 1", "column_id": "categoria"}, "paddingLeft": "36px", "opacity": 0.85},
            {"if": {"column_id": "total"}, "fontWeight": "700"},
        ]
        for c in month_ids + ["total"]:
            style_data_conditional.append({"if": {"filter_query": f"{{{c}}} < 0", "column_id": c}, "color": NEGATIVO_FG})
            style_data_conditional.append({"if": {"filter_query": f"{{{c}}} > 0", "column_id": c}, "color": POSITIVO_FG})

        return columns, rows, style_cell_conditional, style_data_conditional
