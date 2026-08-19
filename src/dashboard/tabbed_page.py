from dash import Input, Output, dcc, html


def build(app, page_key, header_title, header_subtitle, tabs, theme):
    """Arma una pagina con header de marca + dcc.Tabs, reusable para Ancestral y omuH.

    `tabs` es una lista de (label, value, layout) — cada layout ya construido
    (por ejemplo via reconciliacion_tab.build_layout o resumen_tab.build_layout).
    Todas las pestanas quedan montadas en el DOM (display:none las inactivas)
    para no perder el estado de filtros al navegar entre ellas.
    """
    tab_style = {
        "fontFamily": theme.font_display,
        "letterSpacing": "1px",
        "fontSize": "15px",
        "padding": "12px 20px",
        "borderTop": "3px solid transparent",
        "borderLeft": "none",
        "borderRight": "none",
        "borderBottom": "none",
        "background": theme.dark,
        "color": theme.cream_dim,
    }
    tab_selected_style = {
        "fontFamily": theme.font_display,
        "letterSpacing": "1px",
        "fontSize": "15px",
        "padding": "12px 20px",
        "borderTop": f"3px solid {theme.primary}",
        "borderLeft": "none",
        "borderRight": "none",
        "borderBottom": "none",
        "background": theme.cream,
        "color": theme.dark,
    }

    tabs_id = f"{page_key}-tabs"
    resize_id = f"{page_key}-resize-noop"
    default_value = tabs[0][1]

    panels = [
        html.Div(id=f"{page_key}-panel-{value}", children=layout, style={} if value == default_value else {"display": "none"})
        for _, value, layout in tabs
    ]

    layout = html.Div(
        style={"background": theme.cream, "minHeight": "100vh"},
        children=[
            html.Div(
                style={"background": theme.dark, "padding": "22px 32px", "display": "flex", "alignItems": "center", "gap": "16px"},
                children=[
                    *([html.Img(src=app.get_asset_url(theme.logo_asset), style={"height": "48px"})] if theme.logo_asset else []),
                    html.Div(
                        [
                            html.H1(header_title, style={"color": theme.white, "fontSize": "30px", "margin": 0, "lineHeight": 1}),
                            html.Span(
                                header_subtitle,
                                style={"color": theme.primary, "fontFamily": theme.font_display, "letterSpacing": "2px", "fontSize": "14px"},
                            ),
                        ]
                    ),
                ],
            ),
            dcc.Tabs(
                id=tabs_id,
                value=default_value,
                children=[dcc.Tab(label=label, value=value, style=tab_style, selected_style=tab_selected_style) for label, value, _ in tabs],
            ),
            html.Div(panels),
            html.Div(id=resize_id, style={"display": "none"}),
        ],
    )

    values = [value for _, value, _ in tabs]

    @app.callback(
        [Output(f"{page_key}-panel-{value}", "style") for value in values],
        Input(tabs_id, "value"),
    )
    def mostrar_pestana(selected):
        return [{} if v == selected else {"display": "none"} for v in values]

    app.clientside_callback(
        """
        function(tab) {
            setTimeout(function() {
                document.querySelectorAll('.js-plotly-plot').forEach(function(gd) {
                    if (window.Plotly) { window.Plotly.Plots.resize(gd); }
                });
            }, 50);
            return "";
        }
        """,
        Output(resize_id, "title"),
        Input(tabs_id, "value"),
    )

    return layout
