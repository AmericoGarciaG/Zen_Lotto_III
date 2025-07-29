import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import plotly.graph_objects as go
import config

def create_header():
    return html.Div(
        [
            html.H1("Zen Lotto", className="text-center text-dark mb-2"),
            html.P("Plataforma de Análisis para Lotería Melate Retro", className="text-center text-muted"),
        ],
        className="mb-5",
    )

def create_navigation():
    buttons = [
        dbc.Button("GENERADOR OMEGA", id="btn-nav-generador", className="nav-button"),
        dbc.Button("GRÁFICOS", id="btn-nav-graficos", className="nav-button"),
        dbc.Button("VISOR HISTÓRICOS", id="btn-nav-historicos", className="nav-button"),
        dbc.Button("REGISTRO DE OMEGAS", id="btn-nav-registros", className="nav-button"),
        dbc.Button("CONFIGURACIÓN", id="btn-nav-configuracion", className="nav-button"),
    ]

    if config.DEBUG_MODE:
        buttons.insert(3, dbc.Button("MONITOREO", id="btn-nav-monitoreo", className="nav-button"))

    return dbc.Row(
        dbc.Col(
            html.Div(
                dbc.ButtonGroup(buttons, id="navigation-group"),
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

    analysis_result_card = dbc.Card(
        dbc.CardBody([
            html.H4(id='analysis-title', className="card-title"),
            html.P(id='analysis-combination-text'),
            html.Hr(),
            html.P(id='analysis-score-text'),
            html.Ul(id='analysis-details-list', className='list-unstyled')
        ]),
        id='analysis-result-card',
        className="mt-4", 
        style={'display': 'none'}
    )

    return html.Div([
        dcc.Store(id='store-validated-omega', data=None),
        dbc.Row(number_inputs + [clear_button], justify="center", align="center", className="mb-5 g-2"),
        dbc.Row([
            dbc.Col(dbc.Button("ANALIZAR COMBINACIÓN", id="btn-analizar", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("GENERAR OMEGA / AJUSTAR", id="btn-generar", color="dark", className="action-button"), width="auto"),
        ], justify="center", align="center", className="g-3 mb-4"),
        dbc.Row(dbc.Col(analysis_result_card, width=12, md=8, lg=6), justify="center"),
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
            dbc.Col(dbc.Button("4. ENRIQUECER Y PRE-GENERAR", id="btn-enrich-pregen", color="dark", className="action-button"), width="auto"),
        ], justify="center", className="g-3"),
        
        html.Div(
            [
                html.P("Procesando, por favor espere...", id="progress-text", className="mt-4 mb-2 text-muted"),
                dbc.Progress(id="progress-bar", value=0, striped=True, animated=True, style={"height": "20px"}),
            ],
            id="progress-container",
            style={'display': 'none'}
        )
    ])

def create_registros_view():
    confirmation_modal = dbc.Modal([
        dbc.ModalHeader("Confirmar Eliminación"), dbc.ModalBody("¿Estás seguro?"),
        dbc.ModalFooter([dbc.Button("Cancelar", id="btn-cancel-delete"), dbc.Button("Confirmar", id="btn-confirm-delete", color="danger")]),
    ], id="modal-confirm-delete", is_open=False)

    import_modal = dbc.Modal([
        dbc.ModalHeader("Confirmar Importación"),
        dbc.ModalBody("Se han encontrado registros existentes. ¿Deseas sobrescribirlos con los datos del archivo de respaldo?"),
        dbc.ModalFooter([
            dbc.Button("No Sobrescribir (Solo añadir nuevos)", id="btn-import-no-overwrite", color="secondary"),
            dbc.Button("Sí, Sobrescribir", id="btn-import-overwrite", color="primary"),
        ]),
    ], id="modal-confirm-import", is_open=False)

    return html.Div([
        dcc.Store(id='store-record-to-delete', data=None), confirmation_modal, import_modal,
        html.H3("Registro de Combinaciones Omega", className="text-center text-dark mb-4"),
        
        dbc.Row([
            dbc.Col(dbc.Button("Exportar a JSON", id="btn-export-registros", color="success", outline=True), width="auto"),
            dbc.Col(dbc.Button("Importar desde JSON", id="btn-import-registros", color="info", outline=True), width="auto"),
            dbc.Col(dbc.Button("Refrescar Datos", id="btn-refresh-registros", className="ms-auto", color="primary", outline=True)),
        ], className="mb-3"),
        
        dash_table.DataTable(id='table-registros')
    ])

def create_historicos_view():
    modal_deconstructor = dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Deconstructor de Afinidad")),
            dbc.ModalBody([
                html.H5(id="modal-deconstructor-header"),
                html.Hr(),
                dbc.Row([
                    dbc.Col(html.P(id="summary-cuartetos"), width=4),
                    dbc.Col(html.P(id="summary-tercias"), width=4),
                    dbc.Col(html.P(id="summary-pares"), width=4),
                ], className="text-center mb-3"),
                dbc.Tabs(
                    [
                        dbc.Tab(
                            dash_table.DataTable(
                                id='table-cuartetos',
                                columns=[{'name': 'Subsecuencia', 'id': 'subsequence'}, {'name': 'Frecuencia (Aporte)', 'id': 'frequency'}],
                                style_cell={'textAlign': 'center'}, style_header={'fontWeight': 'bold'}, page_size=15
                            ),
                            label="Cuartetos (15)",
                        ),
                        dbc.Tab(
                            dash_table.DataTable(
                                id='table-tercias',
                                columns=[{'name': 'Subsecuencia', 'id': 'subsequence'}, {'name': 'Frecuencia (Aporte)', 'id': 'frequency'}],
                                style_cell={'textAlign': 'center'}, style_header={'fontWeight': 'bold'}, page_size=20
                            ),
                            label="Tercias (20)",
                        ),
                        dbc.Tab(
                            dash_table.DataTable(
                                id='table-pares',
                                columns=[{'name': 'Subsecuencia', 'id': 'subsequence'}, {'name': 'Frecuencia (Aporte)', 'id': 'frequency'}],
                                style_cell={'textAlign': 'center'}, style_header={'fontWeight': 'bold'}, page_size=15
                            ),
                            label="Pares (15)",
                        ),
                    ]
                ),
            ]),
            dbc.ModalFooter(dbc.Button("Cerrar", id="btn-close-modal", className="ms-auto")),
        ],
        id="modal-deconstructor",
        size="lg",
        is_open=False,
    )

    # --- ARQUITECTURA CORREGIDA: La vista ahora gestiona su propio contenedor ---
    return dbc.Container(
        [
            modal_deconstructor,
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
                    {'name': 'Af. Tercias', 'id': 'afinidad_tercias'}, 
                    {'name': 'Af. Pares', 'id': 'afinidad_pares'},
                    {'name': 'Analizar', 'id': 'analizar', 'presentation': 'markdown'},
                ],
                data=[], page_size=20, sort_action='native', filter_action='native',
                style_cell={
                    'textAlign': 'center', 'whiteSpace': 'normal',
                },
                style_header={'fontWeight': 'bold', 'backgroundColor': 'rgb(230, 230, 230)'},
                style_table={'overflowX': 'auto'},
                style_data_conditional=[]
            )
        ],
        fluid=True # <-- Esta es la clave. Este contenedor ocupa todo el ancho de la ventana.
    )

# ... (otras funciones sin cambios) ...

def create_graficos_view():
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
        
        # --- FILA 1: Donuts de Proporción (sin cambios) ---
        dbc.Row([
            dbc.Col(create_graph_card('graph-universo', 'Clase Omega vs. Universo Total'), md=4),
            dbc.Col(create_graph_card('graph-historico', 'Clase Omega en Sorteos Históricos'), md=4),
            dbc.Col(create_graph_card('graph-ganadores', 'Clase Omega en Sorteos con Premio'), md=4),
        ]),

        # --- FILA 2: Scatter Plot (sin cambios) ---
        dbc.Row([
            dbc.Col(create_graph_card(
                'graph-scatter-score-bolsa', 
                "Omega Score vs. Bolsa Acumulada (Sorteos con Premio Mayor)"
            ), width=12)
        ]),

        # --- FILA 3 (NUEVA): Histogramas de Distribución de Omega Score ---
        dbc.Row([
            dbc.Col(create_graph_card(
                'graph-score-historico-dist', 
                "Distribución del Omega Score en TODO el Histórico"
            ), md=6),
            dbc.Col(create_graph_card(
                'graph-score-omega-class-dist', 
                "Distribución del Omega Score en TODA la Clase Omega Teórica"
            ), md=6),
        ])
    ])

def create_monitoring_view():
    """Crea el layout para la nueva pestaña de Monitoreo Estadístico."""
    def create_graph_card(graph_id, title, subtitle):
        return dbc.Card(
            dbc.CardBody([
                html.H5(title, className="card-title"),
                html.H6(subtitle, className="card-subtitle text-muted mb-3"),
                dcc.Graph(id=graph_id)
            ]),
            className="mb-4"
        )

    return html.Div([
        html.H3("Panel de Control de Salud y Monitoreo Estadístico", className="text-center text-dark mb-4"),
        html.P("Esta sección permite vigilar la consistencia del modelo a lo largo del tiempo.", className="text-center text-muted"),
        dbc.Row(dbc.Col(
            dbc.Button("Generar/Refrescar Gráficos de Monitoreo", id="btn-refresh-monitoring", className="mb-4", color="primary", style={'width': '100%'})
        )),
        
        dbc.Row([
            dbc.Col(create_graph_card(
                'graph-freq-dist-trajectory', 
                "Evolución de la Distribución de Frecuencias",
                "Muestra la media (línea sólida) y el rango (mín/máx) de los valores de las frecuencias en cada punto."
            ), width=12),
        ]),
        
        dbc.Row([
            dbc.Col(create_graph_card(
                'graph-affinity-trajectory', 
                "Evolución de la Distribución de Afinidades",
                "Muestra la media (línea sólida) y el rango (mín/máx) de las afinidades para todos los sorteos históricos en cada punto."
            ), width=12),
        ]),
        
        dbc.Row([
            dbc.Col(create_graph_card(
                'graph-freq-trajectory', 
                "Crecimiento de Frecuencias Base",
                "Curvas de crecimiento del modelo estadístico (conteos de combinaciones únicas)."
            ), md=6),
            dbc.Col(create_graph_card(
                'graph-threshold-trajectory', 
                "Evolución de Umbrales Óptimos",
                "Resultado de la optimización de ML en cada punto de la trayectoria."
            ), md=6),
        ]),
        
        html.Hr(className="my-4"),
        dbc.Button(
            "Mostrar/Ocultar Análisis de Distribución Detallado",
            id="btn-collapse-dist",
            className="mb-3",
            color="secondary",
            outline=True,
            style={'width': '100%'}
        ),
        dbc.Collapse(
            dbc.Card(dbc.CardBody([
                dbc.Row([
                    dbc.Col(create_graph_card(
                        'graph-freq-histogram',
                        "Histograma de Frecuencias (Estado Final)",
                        "Muestra la 'rareza': qué % de combinaciones ha aparecido X veces."
                    ), md=6),
                    dbc.Col(create_graph_card(
                        'graph-affinity-histogram',
                        "Histograma de Afinidades (Sorteos Históricos)",
                        "Muestra la distribución de la 'potencia' de los ganadores."
                    ), md=6),
                ])
            ])),
            id="collapse-dist-panel",
            is_open=False,
        ),
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