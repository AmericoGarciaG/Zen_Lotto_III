import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import plotly.graph_objects as go

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
                        dbc.Button("GRÁFICOS Y ESTADÍSTICAS", id="btn-nav-graficos", className="nav-button"),
                        dbc.Button("VISOR DE HISTÓRICOS", id="btn-nav-historicos", className="nav-button"),
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
        dbc.Row(number_inputs + [clear_button], justify="center", align="center", className="mb-5 g-2"),
        dbc.Row([
            dbc.Col(dbc.Button("ANALIZAR COMBINACIÓN", id="btn-analizar", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("GENERAR OMEGA / AJUSTAR", id="btn-generar", color="dark", className="action-button"), width="auto"),
        ], justify="center", align="center", className="g-3 mb-4"),
        html.Div([
            dbc.Row(dbc.Col(dcc.Input(id="input-nombre", placeholder="Nombre Completo", className="form-control", disabled=True), width=8, md=6, lg=5, xl=4), justify="center", className="mb-3"),
            dbc.Row(dbc.Col(dcc.Input(id="input-movil", placeholder="Número de Móvil", type="tel", className="form-control", disabled=True), width=8, md=6, lg=5, xl=4), justify="center", className="mb-4"),
            dbc.Row(dbc.Col(dbc.Button("REGISTRAR OMEGA", id="btn-registrar", color="dark", outline=True, className="action-button", disabled=True), width="auto"), justify="center"),
        ], className="mt-5 pt-3")
    ])

def create_configuracion_view():
    return html.Div([
        html.H3("Configuración y Mantenimiento", className="text-center text-dark mb-4"),
        dbc.Row([
            dbc.Col(dbc.Button("1. ACTUALIZAR HISTÓRICO", id="btn-gen-historico", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("2. ACTUALIZAR FRECUENCIAS", id="btn-gen-omega", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("3. OPTIMIZAR UMBRALES (ML)", id="btn-optimize-thresholds", color="primary", className="action-button"), width="auto"),
            # --- BOTÓN COMBINADO ---
            dbc.Col(dbc.Button("4. ENRIQUECER Y PRE-GENERAR", id="btn-enrich-pregen", color="dark", className="action-button"), width="auto"),
        ], justify="center", className="g-3")
    ])

def create_registros_view():
    confirmation_modal = dbc.Modal([
        dbc.ModalHeader("Confirmar Eliminación"), dbc.ModalBody("¿Estás seguro?"),
        dbc.ModalFooter([dbc.Button("Cancelar", id="btn-cancel-delete"), dbc.Button("Confirmar", id="btn-confirm-delete", color="danger")]),
    ], id="modal-confirm-delete", is_open=False)

    # --- NUEVO MODAL PARA LA IMPORTACIÓN ---
    import_modal = dbc.Modal([
        dbc.ModalHeader("Confirmar Importación"),
        dbc.ModalBody("Se han encontrado registros existentes. ¿Deseas sobrescribirlos con los datos del archivo de respaldo?"),
        dbc.ModalFooter([
            dbc.Button("No Sobrescribir (Solo añadir nuevos)", id="btn-import-no-overwrite", color="secondary"),
            dbc.Button("Sí, Sobrescribir", id="btn-import-overwrite", color="primary"),
        ]),
    ], id="modal-confirm-import", is_open=False)

    return html.Div([
        dcc.Store(id='store-record-to-delete', data=None), confirmation_modal, import_modal, # <-- Añadir nuevo modal
        html.H3("Registro de Combinaciones Omega", className="text-center text-dark mb-4"),
        
        # --- NUEVOS BOTONES DE GESTIÓN ---
        dbc.Row([
            dbc.Col(dbc.Button("Exportar a JSON", id="btn-export-registros", color="success", outline=True), width="auto"),
            dbc.Col(dbc.Button("Importar desde JSON", id="btn-import-registros", color="info", outline=True), width="auto"),
            dbc.Col(dbc.Button("Refrescar Datos", id="btn-refresh-registros", className="ms-auto", color="primary", outline=True)),
        ], className="mb-3"),
        # -----------------------------
        
        dash_table.DataTable(id='table-registros',
            # ... (resto de la tabla sin cambios) ...
        )
    ])

def create_historicos_view():
    return html.Div([
        html.H3("Melate Retro - Registros Históricos", className="text-center text-dark mb-4"),
        dbc.Row(dbc.Col(dbc.Button("Refrescar Datos", id="btn-refresh-historicos", className="mb-3", color="primary", outline=True)), justify="end"),
        dash_table.DataTable(id='table-historicos',
            columns=[
                {'name': 'Concurso', 'id': 'concurso'}, {'name': 'Fecha', 'id': 'fecha'},
                {'name': 'R1', 'id': 'r1'}, {'name': 'R2', 'id': 'r2'}, {'name': 'R3', 'id': 'r3'},
                {'name': 'R4', 'id': 'r4'}, {'name': 'R5', 'id': 'r5'}, {'name': 'R6', 'id': 'r6'},
                {'name': 'Bolsa', 'id': 'bolsa', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                {'name': 'Clase Omega', 'id': 'es_omega_str'},
                {'name': 'Omega Score', 'id': 'omega_score', 'type': 'numeric', 'format': {'specifier': '.4f'}},
                {'name': 'Af. Cuartetos', 'id': 'afinidad_cuartetos'},
                {'name': 'Af. Tercias', 'id': 'afinidad_tercias'}, {'name': 'Af. Pares', 'id': 'afinidad_pares'},
            ],
            data=[], page_size=20, sort_action='native', filter_action='native',
            style_cell={'textAlign': 'center', 'minWidth': '80px'},
            style_header={'fontWeight': 'bold', 'backgroundColor': 'rgb(230, 230, 230)'},
            style_table={'overflowX': 'auto'}, style_data_conditional=[]
        )
    ])

def create_graficos_view():
    """Crea el layout para la pestaña de Gráficos y Estadísticas."""
    def create_graph_card(graph_id, title):
        return dbc.Card([
            dbc.CardHeader(html.H5(title, className="mb-0")),
            dbc.CardBody(dcc.Graph(id=graph_id)),
        ], className="mb-4")

    return html.Div([
        html.H3("Gráficos y Estadísticas", className="text-center text-dark mb-4"),
        dbc.Row(dbc.Col(
            dbc.Button("Generar/Refrescar Gráficos", id="btn-refresh-graficos", className="mb-3", color="primary")
        ), justify="end"),
        
        # Fila de los gráficos de dona
        dbc.Row([
            dbc.Col(create_graph_card('graph-universo', 'Clase Omega vs. Universo Total'), md=4),
            dbc.Col(create_graph_card('graph-historico', 'Clase Omega en Sorteos Históricos'), md=4),
            dbc.Col(create_graph_card('graph-ganadores', 'Clase Omega en Sorteos con Premio'), md=4),
        ]),

        # --- NUEVA FILA PARA EL GRÁFICO DE DISPERSIÓN ---
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader(html.H5("Omega Score vs. Bolsa Acumulada (Sorteos Ganadores)", className="mb-0")),
                    dbc.CardBody(dcc.Graph(id='graph-scatter-score-bolsa')),
                ]),
                width=12 # Ocupa todo el ancho
            )
        ])
    ])

def create_layout():
    return dbc.Container(
        [
            create_header(),
            create_navigation(),
            html.Div(id="view-content"),
            html.Div(id="notification-container", className="mt-4")
        ],
        fluid=False,
        className="main-container",
    )