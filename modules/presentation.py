# modules/presentation.py

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_header():
    """Crea el encabezado de la aplicación."""
    return html.Div(
        [
            html.H1("Zen Lotto", className="text-center text-dark mb-2"),
            html.P(
                "Plataforma de Análisis para Lotería Melate Retro",
                className="text-center text-muted",
            ),
        ],
        className="mb-5",
    )

def create_navigation():
    """Crea la barra de navegación con estilo de píldora."""
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
    """Crea la vista de 'Generador Omega' con el diseño final y homologado."""
    number_inputs = [
        dbc.Col(dcc.Input(id=f"num-input-{i}", type="number", className="number-box"), width="auto")
        for i in range(6)
    ]

    return html.Div([
        dbc.Row(number_inputs, justify="center", className="mb-5 g-2"),
        dbc.Row([
            dbc.Col(html.P("ANALIZAR", className="analizar-text"), width="auto"),
            dbc.Col(
                dbc.Button("GENERAR OMEGA", id="btn-generar", color="dark", className="action-button"),
                width="auto"
            ),
        ], justify="center", align="center", className="g-3 mb-4"),
        dbc.Row(
            dbc.Col(
                dcc.Input(id="input-nombre", placeholder="Nombre Completo", className="form-control"),
                width=8, md=6, lg=5, xl=4 # Ajuste para centrar y limitar ancho
            ),
            justify="center",
            className="mb-4"
        ),
        dbc.Row(
            dbc.Col(
                dbc.Button("REGISTRAR OMEGA", id="btn-registrar", color="dark", outline=True, className="action-button"),
                width="auto"
            ),
            justify="center"
        ),
    ])

def create_configuracion_view():
    """Crea la vista de la pestaña 'Configuración'."""
    return html.Div([
        html.H3("Configuración", className="text-center text-dark mb-4"),
        
        # --- LÍNEA FALTANTE AÑADIDA AQUÍ ---
        # Este es el contenedor donde se mostrará el mensaje de éxito o error.
        html.Div(id="config-feedback-message", className="text-center mb-4"),
        # ------------------------------------

        dbc.Row([
            # He envuelto cada botón en su propio dbc.Col como estaba en el diseño original,
            # lo que ayuda con la alineación y el espaciado.
            dbc.Col(
                dbc.Button("Generar Histórico", id="btn-gen-historico", color="secondary", className="action-button"), 
                width="auto"
            ),
            dbc.Col(
                dbc.Button("Generar Clase Omega", id="btn-gen-omega", color="secondary", className="action-button"), 
                width="auto"
            ),
        ], justify="center", className="g-2")
    ])

def create_layout():
    """Crea el layout principal de la aplicación."""
    return dbc.Container(
        [
            create_header(),
            create_navigation(),
            html.Div(id="view-content", className="pt-4"),
        ],
        fluid=False,
        className="main-container",
    )