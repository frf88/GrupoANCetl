from dash import Dash

from src.dashboard import ventas_tab
from src.dashboard.auth import require_basic_auth
from src.dashboard.data import load_all

data = load_all()
ventas_df = data["ventas"]

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "Grupo ANC — Ventas"

require_basic_auth(server)

app.layout = ventas_tab.build_layout(ventas_df)
ventas_tab.register_callbacks(app, ventas_df)


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, port=8051)
