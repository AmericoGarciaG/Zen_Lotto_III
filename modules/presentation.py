import dash_bootstrap_components as dbc
from dash import html, dcc

def create_header():
    return html.Div(
        [
            html.H1("Zen Lotto", className="text-center text-dark mb-2"),
            html.P("Plataforma de Análisis para Lotería Melate Retro", className="text-center text-muted"),
        ],
        className="mb-5",
    )

def create_navigation():
    return dbc.Row(
        dbc.Col(
            html.Div(
                dbc.ButtonGroup(
                    [
                        dbc.Button("GENERADOR OMEGA", id="btn-nav-generador", className="nav-button"),
                        dbc.Button("GRÁFICOS", id="btn-nav-graficos", className="nav-button", disabled=True),
                        dbc.Button("VISOR DE HISTÓRICOS", id="btn-nav-historicos", className="nav-button", disabled=True),
                        dbc.Button("CONFIGURACIÓN", id="btn-nav-configuracion", className="nav-button"),
                    ],
                    id="navigation-group",
                ),
                className="nav-pill-container"
            ),
            width="auto"
        ),
        justify="center",
        className="mb-5"
    )

def create_generador_view():
    number_inputs = [
        dbc.Col(dcc.Input(id=f"num-input-{i}", type="number", className="number-box"), width="auto")
        for i in range(6)
    ]
    return html.Div([
        dbc.Row(number_inputs, justify="center", className="mb-5 g-2"),
        
        # --- BLOQUE DE BOTONES HOMOLOGADO ---
        dbc.Row([
            dbc.Col(
                # Cambiado a color="dark" y sin outline
                dbc.Button("ANALIZAR COMBINACIÓN", id="btn-analizar", color="dark", className="action-button"), 
                width="auto"
            ),
            dbc.Col(
                dbc.Button("GENERAR OMEGA", id="btn-generar", color="dark", className="action-button"), 
                width="auto"
            ),
        ], justify="center", align="center", className="g-3 mb-4"),
        # ------------------------------------

        dbc.Row(
            dbc.Col(dcc.Input(id="input-nombre", placeholder="Nombre Completo", className="form-control"), width=8, md=6, lg=5, xl=4),
            justify="center",
            className="mb-4"
        ),
        dbc.Row(
            # Este mantiene el estilo "outline" como botón secundario
            dbc.Col(dbc.Button("REGISTRAR OMEGA", id="btn-registrar", color="dark", outline=True, className="action-button", disabled=True), width="auto"),
            justify="center"
        ),
    ])

def create_configuracion_view():
    return html.Div([
        html.H3("Configuración", className="text-center text-dark mb-4"),
        
        # --- BLOQUE DE BOTONES HOMOLOGADO ---
        dbc.Row([
            dbc.Col(
                # Cambiado a color="dark" y sin outline
                dbc.Button("ACTUALIZAR HISTÓRICO", id="btn-gen-historico", color="dark", className="action-button"), 
                width="auto"
            ),
            dbc.Col(
                # Cambiado a color="dark" y sin outline
                dbc.Button("ACTUALIZAR FRECUENCIAS", id="btn-gen-omega", color="dark", className="action-button"), 
                width="auto"
            ),
            dbc.Col(
                dbc.Button("PRE-GENERAR CLASE OMEGA", id="btn-pregen-omega", color="dark", className="action-button"), 
                width="auto"
            ),
        ], justify="center", className="g-3")
        # ------------------------------------
    ])

def create_layout():
    return dbc.Container(
        [
            create_header(),
            create_navigation(),
            html.Div(id="view-content", className="pt-4"),
            html.Div(id="notification-container", className="mt-4")
        ],
        fluid=False,
        className="main-container",
    )