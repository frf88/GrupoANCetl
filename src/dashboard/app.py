from dash import Dash, Input, Output, dcc, html

from src.dashboard import reconciliacion_tab, resumen_tab, tabbed_page, ventas_tab
from src.dashboard.data import (
    BEBIDAS_DAILY_TITLES,
    BEBIDAS_WEEKLY_TITLES,
    INSUMOS_DAILY_TITLES,
    INSUMOS_WEEKLY_TITLES,
    OMUH_DAILY_TITLES,
    OMUH_WEEKLY_TITLES,
    load_all,
)
from src.dashboard.theme import ANCESTRAL, OMUH

data = load_all()
bebidas_weekly, bebidas_daily, bebidas_ventas = data["bebidas"]
vinos_weekly, vinos_daily, vinos_ventas = data["vinos"]
insumos_weekly, insumos_daily, insumos_ventas = data["insumos"]
resumen_df = data["resumen"]
om_bebidas_weekly, om_bebidas_daily, om_bebidas_ventas = data["omuh_bebidas"]
om_insumos_weekly, om_insumos_daily, om_insumos_ventas = data["omuh_insumos"]
ventas_df = data["ventas"]

# la ultima semana con cierre real (diferencia IS NOT NULL) de Bebidas marca
# el ritmo de conteo fisico de todas las areas de cada negocio por igual
semanas_bebidas = sorted(bebidas_weekly["semana"].unique())
ULTIMA_SEMANA_COMPLETA_ANCESTRAL = semanas_bebidas[-1] if semanas_bebidas else None

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "Grupo ANC — Control de Inventario"

NAV_STYLE = {"background": "#111111", "padding": "10px 32px", "display": "flex", "gap": "24px"}
NAV_LINK_STYLE = {
    "fontFamily": "'Jost', sans-serif",
    "fontSize": "13px",
    "letterSpacing": "1px",
    "textTransform": "uppercase",
    "color": "#B8B8B8",
    "textDecoration": "none",
    "padding": "6px 0",
}
NAV_LINK_ACTIVE_STYLE = {**NAV_LINK_STYLE, "color": "#FFFFFF", "borderBottom": "2px solid #CF7E55"}

ancestral_layout = tabbed_page.build(
    app,
    "ancestral",
    "Ancestral",
    "Control de Inventario",
    [
        ("Bebidas", "bebidas", reconciliacion_tab.build_layout("bebidas", bebidas_weekly, bebidas_daily, BEBIDAS_WEEKLY_TITLES, BEBIDAS_DAILY_TITLES, ANCESTRAL)),
        ("Vinos", "vinos", reconciliacion_tab.build_layout("vinos", vinos_weekly, vinos_daily, BEBIDAS_WEEKLY_TITLES, BEBIDAS_DAILY_TITLES, ANCESTRAL)),
        ("Insumos", "insumos", reconciliacion_tab.build_layout("insumos", insumos_weekly, insumos_daily, INSUMOS_WEEKLY_TITLES, INSUMOS_DAILY_TITLES, ANCESTRAL)),
        ("Resumen", "resumen", resumen_tab.build_layout(resumen_df, ULTIMA_SEMANA_COMPLETA_ANCESTRAL, ANCESTRAL)),
    ],
    ANCESTRAL,
)
reconciliacion_tab.register_callbacks(app, "bebidas", bebidas_weekly, bebidas_daily, bebidas_ventas, ANCESTRAL)
reconciliacion_tab.register_callbacks(app, "vinos", vinos_weekly, vinos_daily, vinos_ventas, ANCESTRAL)
reconciliacion_tab.register_callbacks(app, "insumos", insumos_weekly, insumos_daily, insumos_ventas, ANCESTRAL)
resumen_tab.register_callbacks(app, resumen_df)

omuh_layout = tabbed_page.build(
    app,
    "omuh",
    "omuH",
    "Control de Inventario",
    [
        (
            "Bebidas",
            "om-bebidas",
            reconciliacion_tab.build_layout("ombebidas", om_bebidas_weekly, om_bebidas_daily, OMUH_WEEKLY_TITLES, OMUH_DAILY_TITLES, OMUH),
        ),
        (
            "Insumos",
            "om-insumos",
            reconciliacion_tab.build_layout("ominsumos", om_insumos_weekly, om_insumos_daily, OMUH_WEEKLY_TITLES, OMUH_DAILY_TITLES, OMUH),
        ),
    ],
    OMUH,
)
reconciliacion_tab.register_callbacks(app, "ombebidas", om_bebidas_weekly, om_bebidas_daily, om_bebidas_ventas, OMUH)
reconciliacion_tab.register_callbacks(app, "ominsumos", om_insumos_weekly, om_insumos_daily, om_insumos_ventas, OMUH)

ventas_layout = ventas_tab.build_layout(ventas_df)
ventas_tab.register_callbacks(app, ventas_df)

# path, id-suffix, nav label, layout
PAGES = [
    ("/", "ancestral", "Ancestral", ancestral_layout),
    ("/omuh", "omuh", "omuH", omuh_layout),
    ("/ventas", "ventas", "Ventas", ventas_layout),
]

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(
            style=NAV_STYLE,
            children=[dcc.Link(label, href=path, id=f"nav-{key}", style=NAV_LINK_ACTIVE_STYLE if path == "/" else NAV_LINK_STYLE) for path, key, label, _ in PAGES],
        ),
        *[html.Div(id=f"page-{key}", children=layout, style={} if path == "/" else {"display": "none"}) for path, key, _, layout in PAGES],
        html.Div(id="page-resize-noop", style={"display": "none"}),
    ]
)


_PAGE_OUTPUTS = [Output(f"page-{key}", "style") for _, key, _, _ in PAGES]
_NAV_OUTPUTS = [Output(f"nav-{key}", "style") for _, key, _, _ in PAGES]


@app.callback(*(_PAGE_OUTPUTS + _NAV_OUTPUTS), Input("url", "pathname"))
def enrutar(pathname):
    active_path = pathname if pathname in {p for p, _, _, _ in PAGES} else "/"
    page_styles = [{} if path == active_path else {"display": "none"} for path, _, _, _ in PAGES]
    nav_styles = [NAV_LINK_ACTIVE_STYLE if path == active_path else NAV_LINK_STYLE for path, _, _, _ in PAGES]
    return (*page_styles, *nav_styles)


app.clientside_callback(
    """
    function(pathname) {
        setTimeout(function() {
            document.querySelectorAll('.js-plotly-plot').forEach(function(gd) {
                if (window.Plotly) { window.Plotly.Plots.resize(gd); }
            });
        }, 50);
        return "";
    }
    """,
    Output("page-resize-noop", "title"),
    Input("url", "pathname"),
)


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, port=8050)
