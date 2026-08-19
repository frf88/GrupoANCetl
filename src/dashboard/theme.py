import plotly.graph_objects as go

# Colores de alerta para "diferencia" != 0: intencionalmente neutrales al
# branding (mismo semaforo en ambas marcas, para que el ojo lo reconozca
# igual sin importar la pagina).
DIFERENCIA_BG = "#F0D3BE"
DIFERENCIA_FG = "#8A4A24"


class Theme:
    def __init__(self, primary, dark, cream, cream_dim, white, carbon, font_display, font_body, logo_asset):
        self.primary = primary
        self.dark = dark
        self.cream = cream
        self.cream_dim = cream_dim
        self.white = white
        self.carbon = carbon
        self.font_display = font_display
        self.font_body = font_body
        self.logo_asset = logo_asset

        self.table_style_header = {
            "backgroundColor": dark,
            "color": white,
            "fontFamily": font_display,
            "letterSpacing": "1px",
            "textTransform": "uppercase",
            "fontSize": "13px",
            "border": "none",
        }
        self.table_style_cell = {
            "fontFamily": font_body,
            "fontSize": "13px",
            "padding": "8px 10px",
            "border": "none",
            "borderBottom": f"1px solid {cream_dim}",
        }
        self.table_style_table = {
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "520px",
            "border": f"1px solid {cream_dim}",
            "borderRadius": "4px",
        }
        active_cell_style = {"if": {"state": "active"}, "backgroundColor": f"{primary}2E", "border": f"1px solid {primary}"}
        self.row_highlight_style = [
            {"if": {"row_index": "odd"}, "backgroundColor": cream},
            {"if": {"filter_query": "{diferencia} = 0"}, "backgroundColor": cream_dim},
            {"if": {"filter_query": "{diferencia} != 0"}, "backgroundColor": DIFERENCIA_BG, "color": DIFERENCIA_FG, "fontWeight": "600"},
            active_cell_style,
        ]
        self.cell_highlight_style = [
            {"if": {"row_index": "odd"}, "backgroundColor": cream},
            {"if": {"filter_query": "{diferencia} = 0", "column_id": "diferencia"}, "backgroundColor": cream_dim},
            {
                "if": {"filter_query": "{diferencia} != 0", "column_id": "diferencia"},
                "backgroundColor": DIFERENCIA_BG,
                "color": DIFERENCIA_FG,
                "fontWeight": "600",
            },
            active_cell_style,
        ]
        self.filter_style = {"display": "flex", "gap": "32px", "alignItems": "flex-end", "margin": "20px 0 28px"}
        self.dropdown_style = {"width": "220px"}
        self.section_title_style = {"borderLeft": f"4px solid {primary}", "paddingLeft": "10px", "marginBottom": "12px"}

    def bar_chart(self, v_agg, x="semana", y="ventas"):
        fig = go.Figure(
            go.Bar(
                x=v_agg[x],
                y=v_agg[y],
                marker_color=self.primary,
                hovertemplate="Semana %{x}<br>Ventas: %{y}<extra></extra>",
            )
        )
        fig.update_layout(
            font_family=self.font_body,
            font_color=self.carbon,
            plot_bgcolor=self.cream,
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, l=40, r=20, b=40),
            xaxis=dict(title="Semana", showgrid=False, tickfont=dict(size=11)),
            yaxis=dict(title="Ventas", gridcolor=self.cream_dim, zeroline=False),
            bargap=0.3,
        )
        return fig


# Paleta oficial Ancestral (Ancestral-LineaGrafica.pdf, seccion "Paleta de colores")
ANCESTRAL = Theme(
    primary="#CF7E55",
    dark="#282E3C",
    cream="#FAF6F1",
    cream_dim="#F1EAE1",
    white="#FFFFFF",
    carbon="#3F3F3F",
    font_display="'Bebas Neue', sans-serif",
    font_body="'Jost', sans-serif",
    logo_asset="ancestral-logo.png",
)

# Paleta oficial omuH (OMUH MANUAL.pdf, seccion "Color": verde 009F6E,
# negro, blanco, durazno F3DFD5). Chalkboard SE (fuente de cuerpo del manual)
# es una fuente de sistema de Apple sin licencia web; se sustituye por Baloo 2
# (Google Fonts), que mantiene el mismo caracter redondeado y amigable.
OMUH = Theme(
    primary="#009F6E",
    dark="#111111",
    cream="#F3DFD5",
    cream_dim="#E9CFC2",
    white="#FFFFFF",
    carbon="#111111",
    font_display="'Schoolbell', cursive",
    font_body="'Baloo 2', sans-serif",
    logo_asset="omuh-logo.png",
)

# Tema neutral para vistas que cruzan ambos negocios (ej. Ventas / Tabla
# Dinamica) - no pertenece a la identidad de ninguna de las dos marcas.
GENERAL = Theme(
    primary="#4A6FA5",
    dark="#1F2733",
    cream="#F5F5F3",
    cream_dim="#E9E9E6",
    white="#FFFFFF",
    carbon="#333333",
    font_display="'Bebas Neue', sans-serif",
    font_body="'Jost', sans-serif",
    logo_asset=None,
)
