from dash import Dash, html

from src.dashboard.auth import require_basic_auth
from src.dashboard.theme import GENERAL as theme

app = Dash(__name__)
server = app.server
app.title = "Grupo ANC — Finanzas"

require_basic_auth(server)

app.layout = html.Div(
    style={"background": theme.dark, "minHeight": "100vh", "display": "flex", "alignItems": "center", "justifyContent": "center"},
    children=[
        html.Div(
            style={"textAlign": "center", "fontFamily": theme.font_body, "color": theme.white},
            children=[
                html.H1(
                    "Estados de Resultados",
                    style={"fontFamily": theme.font_display, "color": theme.white, "letterSpacing": "2px", "marginBottom": "8px"},
                ),
                html.P(
                    "En construcción.",
                    style={"color": theme.primary, "fontSize": "16px"},
                ),
            ],
        )
    ],
)


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, port=8052)
