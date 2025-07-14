import dash_bootstrap_components as dbc
from dash import html, dcc

def create_header():
    return html.Div([
        html.H1("Zen Lotto", className="text-center text-dark mb-2"),
        html.P("Plataforma de Análisis para Lotería Melate Retro", className="text-center text-muted"),
    ], className="mb-5")

def create_navigation():
    return dbc.Row(dbc.Col(html.Div(
        dbc.ButtonGroup([
            # Empezamos con el generador activo y el resto deshabilitado
            dbc.Button("GENERADOR OMEGA", id="btn-nav-generador", className="nav-button active"),
            dbc.Button("CONFIGURACIÓN", id="btn-nav-configuracion", className="nav-button"),
        ]),
        className="nav-pill-container"
    ), width="auto"), justify="center", className="mb-5")

def create_generador_view():
    number_inputs = [
        dbc.Col(dcc.Input(id=f"num-input-{i}", type="number", className="number-box", disabled=True), width="auto")
        for i in range(6)
    ]
    return html.Div([
        dbc.Row(number_inputs, justify="center", className="mb-5 g-2"),
        dbc.Row([
            # Todos los botones deshabilitados al inicio
            dbc.Col(dbc.Button("ANALIZAR COMBINACIÓN", id="btn-analizar", color="secondary", className="action-button", disabled=True), width="auto"),
            dbc.Col(dbc.Button("GENERAR OMEGA", id="btn-generar", color="dark", className="action-button", disabled=True), width="auto"),
        ], justify="center", align="center", className="g-3 mb-4"),
    ])

def create_configuracion_view():
    return html.Div([
        html.H3("Configuración", className="text-center text-dark mb-4"),
        dbc.Row([
            dbc.Col(dbc.Button("ACTUALIZAR HISTÓRICO", id="btn-gen-historico", color="secondary", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("ACTUALIZAR FRECUENCIAS", id="btn-gen-omega", color="secondary", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("PRE-GENERAR CLASE OMEGA", id="btn-pregen-omega", color="dark", className="action-button"), width="auto"),
        ], justify="center", className="g-3")
    ])

def create_layout():
    return dbc.Container([
        create_header(),
        create_navigation(),
        html.Div(id="view-content"),
        html.Div(id="notification-container", className="mt-4")
    ], fluid=False, className="main-container")