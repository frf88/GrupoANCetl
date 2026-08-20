from dash import Dash

from src.dashboard import finanzas_tab
from src.dashboard.auth import require_basic_auth
from src.dashboard.data import load_finanzas
from src.dashboard.theme import GENERAL as theme

data = load_finanzas()
estados_df = data["estados_resultados"]

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "Grupo ANC — Finanzas"

require_basic_auth(server)

app.layout = finanzas_tab.build_layout(estados_df, theme)
finanzas_tab.register_callbacks(app, estados_df)


if __name__ == "__main__":
    app.run(debug=False, use_reloader=False, port=8052)
