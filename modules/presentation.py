import dash_bootstrap_components as dbc
from dash import html, dcc
from dash import html, dcc, dash_table

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
                        dbc.Button("REGISTRO DE OMEGAS", id="btn-nav-registros", className="nav-button"), 
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
    clear_button = dbc.Col(
        dbc.Button(html.I(className="fas fa-trash-alt"), id="btn-clear-inputs", color="secondary", outline=True, className="ms-2"),
        width="auto", className="d-flex align-items-center"
    )

    return html.Div([
        dcc.Store(id='store-validated-omega', data=None),
        
        dbc.Row(
            number_inputs + [clear_button],
            justify="center", align="center", className="mb-5 g-2"
        ),
        
        dbc.Row([
            dbc.Col(dbc.Button("ANALIZAR COMBINACIÓN", id="btn-analizar", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("GENERAR OMEGA / AJUSTAR", id="btn-generar", color="dark", className="action-button"), width="auto"),
        ], justify="center", align="center", className="g-3 mb-4"),
        
        # --- BLOQUE DE REGISTRO MODIFICADO ---
        html.Div([
            dbc.Row(
                dbc.Col(dcc.Input(id="input-nombre", placeholder="Nombre Completo", className="form-control", disabled=True), width=8, md=6, lg=5, xl=4),
                justify="center",
                className="mb-3" # Reducimos margen inferior aquí
            ),
            # --- NUEVO CAMPO PARA MÓVIL ---
            dbc.Row(
                dbc.Col(dcc.Input(id="input-movil", placeholder="Número de Móvil", type="tel", className="form-control", disabled=True), width=8, md=6, lg=5, xl=4),
                justify="center",
                className="mb-4" # Aumentamos margen inferior aquí para separar del botón
            ),
            # ---------------------------
            dbc.Row(
                dbc.Col(dbc.Button("REGISTRAR OMEGA", id="btn-registrar", color="dark", outline=True, className="action-button", disabled=True), width="auto"),
                justify="center"
            ),
        ], className="mt-5 pt-3") # Margen superior y padding superior para bajar todo el bloque
        # -----------------------------------
    ])

def create_configuracion_view():
    return html.Div([
        html.H3("Configuración", className="text-center text-dark mb-4"),
        dbc.Row([
            dbc.Col(dbc.Button("ACTUALIZAR HISTÓRICO", id="btn-gen-historico", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("ACTUALIZAR FRECUENCIAS", id="btn-gen-omega", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("PRE-GENERAR CLASE OMEGA", id="btn-pregen-omega", color="dark", className="action-button"), width="auto"),
        ], justify="center", className="g-3")
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

def create_registros_view():
    return html.Div([
        html.H3("Registro de Combinaciones Omega", className="text-center text-dark mb-4"),
        dbc.Row(dbc.Col(
            dbc.Button("Refrescar Datos", id="btn-refresh-registros", className="mb-3", color="primary", outline=True)
        ), justify="end"),
        
        dash_table.DataTable(
            id='table-registros',
            columns=[
                {'name': 'Combinación', 'id': 'combinacion', 'editable': False},
                {'name': 'Nombre Completo', 'id': 'nombre_completo', 'editable': True},
                {'name': 'Móvil', 'id': 'movil', 'editable': True},
                {'name': 'Fecha de Registro', 'id': 'fecha_registro', 'editable': False},
            ],
            data=[], # Se poblará con un callback
            page_size=15,
            style_cell={'textAlign': 'center', 'fontFamily': 'sans-serif'},
            style_header={'fontWeight': 'bold'},
            style_table={'overflowX': 'auto'}
        )
    ])