# presentation.py

import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import config

def create_header():
    game_items = [dbc.DropdownMenuItem(game_data['display_name'], id={'type': 'game-selector', 'index': game_id}) for game_id, game_data in config.GAME_REGISTRY.items()]
    return html.Div([
        html.H1("Zen Lotto", className="text-center text-dark mb-2"),
        html.P("Observatorio de Comportamiento de Sistemas de Sorteo", className="text-center text-muted"),
        dbc.Row(dbc.Col(dbc.DropdownMenu(id='game-selector-display', children=game_items, label="Seleccionar Juego", color="secondary", className="mt-3"), width="auto"), justify="center", className="mb-4")
    ])

def create_navigation():
    """Crea la barra de navegación principal, AÑADIENDO EL NUEVO BOTÓN."""
    buttons = [
        dbc.Button("GENERADOR OMEGA", id="btn-nav-generador", className="nav-button"),
        dbc.Button("GRÁFICOS", id="btn-nav-graficos", className="nav-button"),
        dbc.Button("VISOR HISTÓRICOS", id="btn-nav-historicos", className="nav-button"),
        dbc.Button("MONITOREO", id="btn-nav-monitoreo", className="nav-button") if config.DEBUG_MODE else None,
        # --- NUEVO BOTÓN AÑADIDO ---
        dbc.Button("OMEGA CERO", id="btn-nav-omega-cero", className="nav-button"),
        dbc.Button("FÉNIX", id="btn-nav-fenix", className="nav-button"), # NUEVO BOTÓN
        dbc.Button("REGISTRO DE OMEGAS", id="btn-nav-registros", className="nav-button"),
        dbc.Button("CONFIGURACIÓN", id="btn-nav-configuracion", className="nav-button"),
    ]
    # Filtra los botones nulos (si DEBUG_MODE es False)
    buttons = [b for b in buttons if b is not None]
    return dbc.Row(dbc.Col(html.Div(dbc.ButtonGroup(buttons, id="navigation-group"), className="nav-pill-container"), width="auto"), justify="center", className="mb-5")

def create_fenix_view():
    """Crea la vista para el Veredicto del Proyecto Fénix."""
    return html.Div([
        html.H3("Veredicto Fénix: ¿Es la Reactividad un Predictor?", className="text-center text-dark mb-4"),
        dbc.Row(dbc.Col(dbc.Button("Realizar Análisis de Distribución", id="btn-run-fenix-analysis", color="primary", className="mb-4 w-100")), justify="center"),
        dbc.Alert("Ejecute 'calculate_fenix_score.py' primero si los gráficos aparecen vacíos.", color="info"),
        dbc.Row([
            dbc.Col(dcc.Loading(dcc.Graph(id="graph-fenix-histogram")), md=6),
            dbc.Col(dcc.Loading(dcc.Graph(id="graph-fenix-boxplot")), md=6),
        ]),
        dbc.Row(dbc.Col(html.Div(id="fenix-stats-summary"), className="mt-4"))
    ])

def create_omega_cero_view():
    """Crea el layout para el nuevo tablero de análisis Omega Cero."""
    
    def create_kpi_card(title, value_id, tooltip_text):
        return dbc.Card([
            dbc.CardHeader(title, className="kpi-title"),
            dbc.CardBody([
                html.H4("-", id=value_id, className="card-title"),
                dbc.Tooltip(tooltip_text, target=value_id, placement="bottom")
            ])
        ], className="text-center")

    return html.Div([
        html.H3("Tablero de Filtro Dinámico: Clase Omega Cero", className="text-center text-dark mb-4"),
        dbc.Row(dbc.Col(dbc.Button("Calcular Candidatas para el Próximo Sorteo", id="btn-calc-omega-cero", color="primary", className="mb-4 w-100")), justify="center"),
        
        dbc.Row([
            dbc.Col(create_kpi_card("Banda de Normalidad", "kpi-banda", "Intervalo [μ-σ, μ+σ] donde se espera que caiga el 'Score Original' de la próxima combinación ganadora."), md=3),
            dbc.Col(create_kpi_card("Ciclo (Cruce por Cero)", "kpi-ciclo", "Número promedio de sorteos que tarda el 'Score Original' en cruzar el eje cero."), md=3),
            dbc.Col(create_kpi_card("Estabilidad (En Banda)", "kpi-estabilidad", "Número promedio de sorteos consecutivos que el 'Score Original' permanece dentro de la Banda de Normalidad."), md=3),
            dbc.Col(create_kpi_card("# Candidatas", "kpi-candidatas", "Número de combinaciones de la Clase Omega que cumplen el criterio del filtro dinámico."), md=3),
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col(dcc.Loading(dcc.Graph(id="graph-omega-cero-dist")), width=12)
        ], className="mb-4"),
        
        dbc.Row([
            dbc.Col(dcc.Loading(dash_table.DataTable(
                id="table-omega-cero-candidatas",
                page_size=15,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'center'},
                style_header={'fontWeight': 'bold'},
                # --- INICIO DE LA CORRECCIÓN ---
                sort_action='native'  # Habilita la ordenación nativa en el frontend
                # --- FIN DE LA CORRECCIÓN ---
            )), width=12)
        ])
    ])

# ... (El resto de las funciones: create_generador_view, create_historicos_view, etc., no cambian)
def create_generador_view():
    return html.Div([
        dcc.Store(id='store-validated-omega', data=None),
        html.Div(id='generador-inputs-container', className="mb-5"),
        dbc.Row([
            dbc.Col(dbc.Button("ANALIZAR COMBINACIÓN", id="btn-analizar", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("GENERAR OMEGA / AJUSTAR", id="btn-generar", color="dark", className="action-button"), width="auto"),
        ], justify="center", align="center", className="g-3 mb-4"),
        dbc.Row(dbc.Col(dbc.Card(dbc.CardBody([html.H4(id='analysis-title', className="card-title"), html.P(id='analysis-combination-text'), html.Hr(), html.P(id='analysis-score-text'), html.Ul(id='analysis-details-list', className='list-unstyled')]), id='analysis-result-card', className="mt-4", style={'display': 'none'}), width=12, md=8, lg=6), justify="center"),
        html.Div([
            dbc.Row(dbc.Col(dcc.Input(id="input-nombre", placeholder="Nombre Completo", className="form-control", disabled=True), width=8, md=6, lg=5, xl=4), justify="center", className="mb-3"),
            dbc.Row(dbc.Col(dcc.Input(id="input-movil", placeholder="Número de Móvil", type="tel", className="form-control", disabled=True), width=8, md=6, lg=5, xl=4), justify="center", className="mb-4"),
            dbc.Row(dbc.Col(dbc.Button("REGISTRAR OMEGA", id="btn-registrar", color="dark", outline=True, className="action-button", disabled=True), width="auto"), justify="center"),
        ], className="mt-5 pt-3")
    ])

def create_historicos_view():
    return dbc.Container([
        dbc.Modal(id="modal-deconstructor", size="lg", is_open=False, children=[
            dbc.ModalHeader(dbc.ModalTitle("Deconstructor de Afinidad")),
            dbc.ModalBody(id="modal-deconstructor-body"),
            dbc.ModalFooter(dbc.Button("Cerrar", id="btn-close-modal", className="ms-auto")),
        ]),
        html.H3(id="historicos-title", className="text-center text-dark mb-4"),
        dbc.Row(dbc.Col(dbc.Button("Refrescar Datos", id="btn-refresh-historicos", className="mb-3", color="primary", outline=True)), justify="end"),
        dash_table.DataTable(id='table-historicos', data=[], page_size=20, sort_action='native', filter_action='native', style_cell={'textAlign': 'center', 'whiteSpace': 'normal'}, style_header={'fontWeight': 'bold', 'backgroundColor': 'rgb(230, 230, 230)'}, style_table={'overflowX': 'auto'})
    ], fluid=True)

def create_configuracion_view():
    return html.Div([
        html.H3("Configuración y Mantenimiento", className="text-center text-dark mb-4"),
        html.P(id="config-game-indicator", className="text-center text-muted small mb-4"),
        dbc.Row([
            dbc.Col(dbc.Button("1. ACTUALIZAR HISTÓRICO", id="btn-gen-historico", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("2. ACTUALIZAR FRECUENCIAS", id="btn-gen-omega", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("3. OPTIMIZAR UMBRALES (ML)", id="btn-optimize-thresholds", color="primary", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("4. ENRIQUECER HISTÓRICO", id="btn-enrich", color="dark", className="action-button"), width="auto"),
            dbc.Col(dbc.Button("5. PRE-GENERAR CLASE OMEGA", id="btn-pregen", color="danger", className="action-button"), width="auto"),
        ], justify="center", className="g-3"),
        html.Div([
            html.P("Procesando, por favor espere...", id="progress-text", className="mt-4 mb-2 text-muted"),
            dbc.Progress(id="progress-bar", value=0, striped=True, animated=True, style={"height": "20px"}),
        ], id="progress-container", style={'display': 'none'})
    ])

def create_registros_view():
    return html.Div([
        dcc.Store(id='store-record-to-delete', data=None),
        dbc.Modal([dbc.ModalHeader("Confirmar Eliminación"), dbc.ModalBody("¿Estás seguro?"), dbc.ModalFooter([dbc.Button("Cancelar", id="btn-cancel-delete"), dbc.Button("Confirmar", id="btn-confirm-delete", color="danger")])], id="modal-confirm-delete", is_open=False),
        dbc.Modal([dbc.ModalHeader("Confirmar Importación"), dbc.ModalBody("Se han encontrado registros existentes. ¿Deseas sobrescribirlos?"), dbc.ModalFooter([dbc.Button("No Sobrescribir", id="btn-import-no-overwrite", color="secondary"), dbc.Button("Sí, Sobrescribir", id="btn-import-overwrite", color="primary")])], id="modal-confirm-import", is_open=False),
        html.H3(id="registros-title", className="text-center text-dark mb-4"),
        dbc.Row([
            dbc.Col(dbc.Button("Exportar a JSON", id="btn-export-registros", color="success", outline=True), width="auto"),
            dbc.Col(dbc.Button("Importar desde JSON", id="btn-import-registros", color="info", outline=True), width="auto"),
            dbc.Col(dbc.Button("Refrescar Datos", id="btn-refresh-registros", className="ms-auto", color="primary", outline=True)),
        ], className="mb-3"),
        dash_table.DataTable(id='table-registros')
    ])

def create_graficos_view():
    def create_graph_card(graph_id, title):
        return dbc.Card([dbc.CardHeader(html.H5(title, className="mb-0")), dbc.CardBody(dcc.Graph(id=graph_id))], className="mb-4")
    return html.Div([
        html.H3("Gráficos y Estadísticas", className="text-center text-dark mb-4"),
        dbc.Row(dbc.Col(dbc.Button("Generar/Refrescar Gráficos", id="btn-refresh-graficos", className="mb-3", color="primary")), justify="end"),
        dbc.Row([dbc.Col(create_graph_card('graph-omega-score-trajectory', "Trayectoria de Omega Scores (Original vs. Actual)"), width=12)]),
        dbc.Row([
            dbc.Col(create_graph_card('graph-universo', 'Clase Omega vs. Universo Total'), md=4),
            dbc.Col(create_graph_card('graph-historico', 'Clase Omega en Sorteos Históricos'), md=4),
            dbc.Col(create_graph_card('graph-ganadores', 'Clase Omega en Sorteos con Premio'), md=4),
        ]),
        dbc.Row([dbc.Col(create_graph_card('graph-scatter-score-bolsa', "Omega Score vs. Bolsa (Sorteos con Premio)"), width=12)]),
        dbc.Row([
            dbc.Col(create_graph_card('graph-score-historico-dist', "Distribución del Omega Score en el Histórico"), md=6),
            dbc.Col(create_graph_card('graph-score-omega-class-dist', "Distribución del Omega Score en la Clase Omega"), md=6),
        ])
    ])

def create_monitoring_view():
    def create_graph_card(graph_id, title, subtitle):
        return dbc.Card(dbc.CardBody([html.H5(title, className="card-title"), html.H6(subtitle, className="card-subtitle text-muted mb-3"), dcc.Graph(id=graph_id)]), className="mb-4")
    return html.Div([
        html.H3("Panel de Monitoreo Estadístico", className="text-center text-dark mb-4"),
        dbc.Row(dbc.Col(dbc.Button("Generar/Refrescar Gráficos de Monitoreo", id="btn-refresh-monitoring", className="mb-4", color="primary")), justify="end"),
        dbc.Row([dbc.Col(create_graph_card('graph-freq-dist-trajectory', "Evolución de la Distribución de Frecuencias", "Muestra la media (línea sólida) y el rango (mín/máx) de los valores de las frecuencias en cada punto."), width=12)]),
        dbc.Row([dbc.Col(create_graph_card('graph-affinity-trajectory', "Evolución de la Distribución de Afinidades", "Muestra la media (línea sólida) y el rango (mín/máx) de las afinidades para todos los sorteos históricos en cada punto."), width=12)]),
        dbc.Row([
            dbc.Col(create_graph_card('graph-freq-trajectory', "Crecimiento de Frecuencias Base", "Curvas de crecimiento del modelo (conteos de subsecuencias únicas)."), md=6),
            dbc.Col(create_graph_card('graph-threshold-trajectory', "Evolución de Umbrales Óptimos", "Resultado de la optimización de ML en cada punto de la trayectoria."), md=6),
        ]),
        html.Hr(className="my-4"),
        dbc.Button("Mostrar/Ocultar Análisis de Distribución Detallado", id="btn-collapse-dist", className="mb-3 w-100", color="secondary", outline=True),
        dbc.Collapse(dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col(create_graph_card('graph-freq-histogram', "Histograma de Frecuencias (Estado Final)", "Muestra la 'rareza': qué % de subsecuencias ha aparecido X veces."), md=6),
                dbc.Col(create_graph_card('graph-affinity-histogram', "Histograma de Afinidades (Sorteos Históricos)", "Muestra la distribución de la 'potencia' de los ganadores históricos."), md=6),
            ])
        ])), id="collapse-dist-panel", is_open=False),
    ])

def create_layout():
    return dbc.Container([
        dcc.Store(id='store-active-game', storage_type='session', data='melate_retro'),
        create_header(),
        create_navigation(),
        html.Div(id="view-content"),
        html.Div(id="notification-container", className="mt-4")
    ], fluid=False, className="main-container")