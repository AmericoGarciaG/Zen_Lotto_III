import time
import logging
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import importlib
import config
import plotly.express as px
from threading import Timer
import webbrowser
import diskcache
from dash.long_callback import DiskcacheManager

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, ctx, State, no_update

from utils.logger_config import setup_logger
from utils import state_manager
from modules.presentation import create_layout

# --- CONFIGURACIÓN INICIAL (SEGURA PARA IMPORTAR) ---
setup_logger()
logger = logging.getLogger(__name__)

# --- FUNCIONES DE AYUDA (SEGURAS PARA IMPORTAR) ---
def fue_un_clic_real(button_id):
    if not ctx.triggered: return False
    triggered_component_id = ctx.triggered[0]['prop_id'].split('.')[0]
    n_clicks = ctx.triggered[0]['value']
    return triggered_component_id == button_id and isinstance(n_clicks, int) and n_clicks > 0

def create_donut_chart(values, labels, title):
    if not any(values):
        fig = go.Figure()
        fig.update_layout(title_text=f"{title}<br>(No hay datos disponibles)", title_x=0.5, xaxis={"visible": False}, yaxis={"visible": False}, annotations=[{"text": "N/A", "xref": "paper", "yref": "paper", "showarrow": False, "font": {"size": 28}}])
        return fig
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.5, textinfo='label+percent', insidetextorientation='radial', marker_colors=['#3b71ca', '#adb5bd'])])
    fig.update_layout(title_text=title, title_x=0.5, showlegend=False, margin=dict(t=50, b=20, l=20, r=20), height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

# --- PUNTO DE ENTRADA PRINCIPAL ---
# Todo el código de la aplicación ahora reside dentro de este bloque.
if __name__ == "__main__":
    logger.info("="*50)
    logger.info("INICIO DE LA APLICACIÓN ZEN LOTTO (PROCESO PRINCIPAL)")
    logger.info("="*50)

    # 1. INICIALIZAR EL GESTOR DE CALLBACKS LARGOS
    cache = diskcache.Cache("./cache")
    long_callback_manager = DiskcacheManager(cache)

    # 2. INICIALIZAR LA APP DASH
    app = dash.Dash(
        __name__, 
        external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME],
        suppress_callback_exceptions=True,
        long_callback_manager=long_callback_manager
    )
    server = app.server
    
    # 3. ASIGNAR EL LAYOUT
    app.layout = create_layout()

    # 4. DEFINIR TODOS LOS CALLBACKS
    logger.info("Registrando callbacks de la aplicación...")

    # --- Callbacks de Navegación ---
    @app.callback(
        Output("view-content", "children"),
        Input("btn-nav-generador", "n_clicks"),
        Input("btn-nav-graficos", "n_clicks"),
        Input("btn-nav-historicos", "n_clicks"),
        Input("btn-nav-trayectoria", "n_clicks"),
        Input("btn-nav-registros", "n_clicks"),
        Input("btn-nav-configuracion", "n_clicks"),
    )
    def render_view_content(gen, graf, hist, tray, reg, conf):
        from modules.presentation import create_generador_view, create_configuracion_view, create_registros_view, create_historicos_view, create_graficos_view, create_trayectoria_view
        triggered_id = ctx.triggered_id or "btn-nav-generador"
        if triggered_id == "btn-nav-configuracion": return create_configuracion_view()
        elif triggered_id == "btn-nav-registros": return create_registros_view()
        elif triggered_id == "btn-nav-historicos": return create_historicos_view()
        elif triggered_id == "btn-nav-graficos": return create_graficos_view()
        elif triggered_id == "btn-nav-trayectoria": return create_trayectoria_view()
        return create_generador_view()

    @app.callback(
        Output("btn-nav-generador", "className"),
        Output("btn-nav-graficos", "className"),
        Output("btn-nav-historicos", "className"),
        Output("btn-nav-trayectoria", "className"),
        Output("btn-nav-registros", "className"),
        Output("btn-nav-configuracion", "className"),
        Input("btn-nav-generador", "n_clicks"),
        Input("btn-nav-graficos", "n_clicks"),
        Input("btn-nav-historicos", "n_clicks"),
        Input("btn-nav-trayectoria", "n_clicks"),
        Input("btn-nav-registros", "n_clicks"),
        Input("btn-nav-configuracion", "n_clicks"),
    )
    def update_nav_buttons_style(gen, graf, hist, tray, reg, conf):
        triggered_id = ctx.triggered_id or "btn-nav-generador"
        base_class = "nav-button"
        styles = {"generador": base_class, "graficos": base_class, "historicos": base_class, "trayectoria": base_class, "registros": base_class, "configuracion": base_class}
        active_view = triggered_id.replace("btn-nav-", "")
        if active_view in styles: styles[active_view] += " active"
        else: styles['generador'] += " active"
        return tuple(styles.values())

    # --- Callbacks de Configuración ---
    @app.callback(Output("notification-container", "children", allow_duplicate=True), Input("btn-gen-historico", "n_clicks"), prevent_initial_call=True)
    def handle_historical_load(n_clicks):
        if not fue_un_clic_real('btn-gen-historico'): return no_update
        from modules.data_ingestion import run_historical_load
        from modules.database import save_historico_to_db
        state = state_manager.get_state()
        last_concurso = state.get("last_concurso_in_db", 0)
        df_new, _, success = run_historical_load(last_concurso=last_concurso)
        if not success or df_new is None: return dbc.Alert("Error durante la carga.", color="danger")
        save_success, save_msg = save_historico_to_db(df_new, mode='append')
        if not save_success: return dbc.Alert(save_msg, color="danger")
        if save_success and not df_new.empty:
            state["last_concurso_in_db"] = int(df_new['concurso'].max())
            state_manager.save_state(state)
        return dbc.Alert(save_msg, color="success", duration=5000)

    @app.callback(Output("notification-container", "children", allow_duplicate=True), Input("btn-gen-omega", "n_clicks"), prevent_initial_call=True)
    def handle_omega_class_generation(n_clicks):
        if not fue_un_clic_real('btn-gen-omega'): return no_update
        from modules.omega_logic import calculate_and_save_frequencies
        success, message = calculate_and_save_frequencies()
        return dbc.Alert(message, color="success" if success else "danger", duration=8000)

    @app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-optimize-thresholds", "n_clicks"),
    progress=[
        Output("progress-bar", "value"),
        Output("progress-text", "children"),
        Output("progress-container", "style"),
        Output("btn-optimize-thresholds", "disabled"),
        Output("btn-gen-historico", "disabled"),
        Output("btn-gen-omega", "disabled"),
        Output("btn-enrich-pregen", "disabled"),
    ],
    background=True,
    prevent_initial_call=True
    )
    def handle_optimize_thresholds(set_progress, n_clicks):
        if not n_clicks or n_clicks < 1:
            raise dash.exceptions.PreventUpdate
        
        from modules import ml_optimizer, omega_logic, database
        
        state = state_manager.get_state()
        
        # --- CORRECCIÓN DE TIPO CON VALOR POR DEFECTO SEGURO ---
        last_freqs = state.get("last_concurso_for_freqs", 0)
        last_opt = state.get("last_concurso_for_optimization", -1)
        
        if last_freqs == last_opt:
            return dbc.Alert("Los umbrales ya están optimizados con los datos más recientes.", color="info", duration=5000)
            
        # Deshabilitamos botones y mostramos la barra de progreso
        set_progress((0, "Iniciando optimización...", {'display': 'block'}, True, True, True, True))

        df_historico = database.read_historico_from_db()
        freqs = omega_logic.get_frequencies()
        if df_historico.empty or freqs is None:
            set_progress((100, "Error.", {'display': 'none'}, False, False, False, False))
            return dbc.Alert("Se necesita el histórico y las frecuencias para optimizar.", color="warning")

        start = time.time()
        success, message, report = ml_optimizer.run_optimization(df_historico, freqs, set_progress=set_progress)
        total_time = time.time() - start
        
        importlib.reload(config)
        
        if success and isinstance(report, dict):
            new_thr, ch, cu = report.get('new_thresholds', {}), report.get('cobertura_historica', 0), report.get('cobertura_universal_estimada', 0)
            details = f"Nuevos umbrales: P={new_thr.get('pares')}, T={new_thr.get('tercias')}, C={new_thr.get('cuartetos')}. | CH: {ch:.1%} | CU (Est.): {cu:.2%}"
            instruction = " Para aplicar, re-ejecute '4. ENRIQUECER Y PRE-GENERAR'."
            full_message = f"{message} {details}{instruction} (Tiempo: {total_time:.2f}s)"
            
            # Guardamos el estado de que la optimización se hizo con esta versión de las frecuencias
            state["last_concurso_for_optimization"] = state.get("last_concurso_for_freqs", 0)
            state_manager.save_state(state)
        else:
            full_message = f"{message} (Tiempo: {total_time:.2f}s)"

        # Ocultamos la barra de progreso y habilitamos los botones
        set_progress((100, "Completado.", {'display': 'none'}, False, False, False, False))
        return dbc.Alert(full_message, color="success" if success else "danger", duration=25000)
    
    @app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-enrich-pregen", "n_clicks"),
    progress=[
        Output("progress-bar", "value"),
        Output("progress-text", "children"),
        Output("progress-container", "style"),
        Output("btn-enrich-pregen", "disabled"),
        Output("btn-gen-historico", "disabled"),
        Output("btn-gen-omega", "disabled"),
        Output("btn-optimize-thresholds", "disabled"),
    ],
    background=True,
    prevent_initial_call=True
    )
    def handle_enrich_and_pregenerate(set_progress, n_clicks):
        if not n_clicks or n_clicks < 1:
            raise dash.exceptions.PreventUpdate
        
        from modules.omega_logic import enrich_historical_data, pregenerate_omega_class
        
        state = state_manager.get_state()
        
        # --- CORRECCIÓN DE TIPO CON VALOR POR DEFECTO SEGURO ---
        last_opt = state.get("last_concurso_for_optimization", 0)
        last_omega_class = state.get("last_concurso_for_omega_class", -1)

        # Validación: Si la Clase Omega ya fue generada con los últimos umbrales, no hacer nada.
        if last_opt > 0 and last_opt == last_omega_class:
            return dbc.Alert("Los datos ya están enriquecidos y la Clase Omega pre-generada con los últimos umbrales.", color="info", duration=5000)

        importlib.reload(config)
        
        # Mostrar barra de progreso y deshabilitar botones
        set_progress((0, "Iniciando...", {'display': 'block'}, True, True, True, True))
        
        success_enrich, msg_enrich = enrich_historical_data(set_progress)
        if not success_enrich:
            set_progress((100, "Error.", {'display': 'none'}, False, False, False, False))
            return dbc.Alert(f"Falló el enriquecimiento: {msg_enrich}", color="danger")
        
        success_pregen, msg_pregen = pregenerate_omega_class(set_progress)
        if not success_pregen:
            set_progress((100, "Error.", {'display': 'none'}, False, False, False, False))
            return dbc.Alert(f"Falló la pre-generación: {msg_pregen}", color="danger")

        full_message = f"Proceso completado. {msg_enrich} {msg_pregen}"
        
        # Guardamos el estado de que este proceso se completó
        state["last_concurso_for_omega_class"] = state.get("last_concurso_for_optimization", 0)
        state_manager.save_state(state)
        
        # Ocultar barra y habilitar botones
        set_progress((100, "Completado.", {'display': 'none'}, False, False, False, False))
        return dbc.Alert(full_message, color="success", duration=15000)
   
    
        # --- Callbacks del Generador ---
    @app.callback([Output(f"num-input-{i}", "value", allow_duplicate=True) for i in range(6)] + [Output("notification-container", "children", allow_duplicate=True)] + [Output('store-validated-omega', 'data', allow_duplicate=True)], Input("btn-generar", "n_clicks"), [State(f"num-input-{i}", "value") for i in range(6)], prevent_initial_call=True)
    def handle_generate_omega(n_clicks, *num_inputs):
        if not fue_un_clic_real('btn-generar'): return [no_update] * 8
        importlib.reload(config)
        from modules.database import get_random_omega_combination
        from modules.omega_logic import evaluate_combination, adjust_to_omega, get_frequencies
        if all(num is None or num == '' for num in num_inputs):
            combo = get_random_omega_combination()
            if combo: return combo + [None, combo]
            return [no_update] * 6 + [dbc.Alert("Error al generar.", color="warning"), None]
        else:
            try: user_combo = sorted([int(num) for num in num_inputs])
            except (ValueError, TypeError): return [no_update] * 7 + [None]
            if len(set(user_combo)) != 6: return [no_update] * 7 + [None]
            freqs = get_frequencies()
            if freqs is None: return [no_update] * 7 + [None]
            eval_result = evaluate_combination(user_combo, freqs)
            if eval_result.get("esOmega"): return [no_update] * 6 + [dbc.Alert("¡Tu combinación ya es Omega!", color="success"), user_combo]
            adjusted, matches = adjust_to_omega(user_combo)
            if adjusted: return adjusted + [dbc.Alert(f"¡Ajuste exitoso! Se mantuvieron {matches} números.", color="info"), adjusted]
            return [no_update] * 6 + [dbc.Alert("No se encontró un ajuste cercano.", color="danger"), None]

    @app.callback(Output('analysis-result-card', 'style'), Output('analysis-result-card', 'className'), Output('analysis-title', 'children'), Output('analysis-combination-text', 'children'), Output('analysis-score-text', 'children'), Output('analysis-details-list', 'children'), Output('store-validated-omega', 'data', allow_duplicate=True), Output("notification-container", "children", allow_duplicate=True), Input("btn-analizar", "n_clicks"), [State(f"num-input-{i}", "value") for i in range(6)], prevent_initial_call=True)
    def handle_analizar_combinacion(n_clicks, *num_inputs):
        if not fue_un_clic_real('btn-analizar'): return (no_update,) * 8
        importlib.reload(config)
        from modules.omega_logic import get_frequencies, evaluate_combination
        hidden_style = {'display': 'none'}
        default_return = [hidden_style, "", "", "", "", [], None, None]
        try:
            if any(num is None or num == '' for num in num_inputs): raise ValueError("Por favor, ingrese 6 números.")
            combination = sorted([int(num) for num in num_inputs])
            if len(set(combination)) != 6: raise ValueError("Los 6 números deben ser únicos.")
        except (ValueError, TypeError) as e: return default_return[:-1] + [dbc.Alert(str(e), color="warning")]
        freqs = get_frequencies()
        if freqs is None: return default_return[:-1] + [dbc.Alert("Frecuencias no generadas.", color="danger")]
        result = evaluate_combination(combination, freqs)
        if not isinstance(result, dict) or result.get("error"):
            error_msg = result.get("error", "Error.") if isinstance(result, dict) else "Error."
            return default_return[:-1] + [dbc.Alert(error_msg, color="danger")]
        es_omega = result.get("esOmega", False)
        title = "¡CLASE OMEGA! ✅" if es_omega else "COMBINACIÓN NO-OMEGA ❌"
        card_class_base = "mt-4 text-dark p-3"
        card_class_color = "border-success bg-success-subtle" if es_omega else "border-danger bg-danger-subtle"
        combo_text = f"Tu combinación: {result.get('combinacion', [])}"
        omega_score = result.get('omegaScore')
        score_text = f"Omega Score: {omega_score:.4f}" if isinstance(omega_score, (int, float)) else "Omega Score: N/A"
        criterios = result.get("criterios", {})
        if not isinstance(criterios, dict): return default_return[:-1] + [dbc.Alert("Faltan datos de criterios.", color="danger")]
        pares, tercias, cuartetos = criterios.get("pares", {}), criterios.get("tercias", {}), criterios.get("cuartetos", {})
        details_list = [html.Li(f"Pares: {pares.get('score')} / {pares.get('umbral')} {'✅' if pares.get('cumple') else '❌'}"), html.Li(f"Tercias: {tercias.get('score')} / {tercias.get('umbral')} {'✅' if tercias.get('cumple') else '❌'}"), html.Li(f"Cuartetos: {cuartetos.get('score')} / {cuartetos.get('umbral')} {'✅' if cuartetos.get('cumple') else '❌'}")]
        return {'display': 'block'}, f"{card_class_base} {card_class_color}", title, combo_text, score_text, details_list, (combination if es_omega else None), None

    @app.callback([Output(f"num-input-{i}", "value", allow_duplicate=True) for i in range(6)] + [Output('store-validated-omega', 'data', allow_duplicate=True)] + [Output('analysis-result-card', 'style', allow_duplicate=True)], Input("btn-clear-inputs", "n_clicks"), prevent_initial_call=True)
    def handle_clear_inputs(n_clicks):
        if not fue_un_clic_real('btn-clear-inputs'): return [no_update] * 8
        return [None] * 6 + [None, {'display': 'none'}]

    @app.callback(Output('input-nombre', 'disabled'), Output('input-movil', 'disabled'), Output('btn-registrar', 'disabled'), Input('store-validated-omega', 'data'), [Input(f"num-input-{i}", "value") for i in range(6)])
    def control_registration_fields(validated_omega, *current_inputs_tuple):
        try: current_inputs = sorted([int(i) for i in current_inputs_tuple if i is not None and i != ''])
        except (ValueError, TypeError): current_inputs = []
        if validated_omega and len(current_inputs) == 6 and sorted(validated_omega) == current_inputs: return False, False, False
        return True, True, True

    # --- Callbacks de Registro y Gestión ---
    @app.callback(Output("notification-container", "children", allow_duplicate=True), Input("btn-registrar", "n_clicks"), [State('store-validated-omega', 'data'), State('input-nombre', 'value'), State('input-movil', 'value')], prevent_initial_call=True)
    def handle_register_omega(n_clicks, validated_omega, nombre, movil):
        if not fue_un_clic_real('btn-registrar'): return no_update
        from modules.database import register_omega_combination
        if not validated_omega or not nombre or not movil: return dbc.Alert("Todos los campos son obligatorios.", color="warning")
        success, message = register_omega_combination(validated_omega, nombre.strip(), movil.strip())
        return dbc.Alert(message, color="success" if success else "danger", duration=5000)

    @app.callback(Output('table-registros', 'data'), Input('btn-refresh-registros', 'n_clicks'), Input('btn-nav-registros', 'n_clicks'), State('modal-confirm-delete', 'is_open'))
    def populate_registros_table(refresh_clicks, nav_clicks, is_modal_open):
        if ctx.triggered_id in ['btn-refresh-registros', 'btn-nav-registros'] or (ctx.triggered_id == 'modal-confirm-delete' and not is_modal_open):
            from modules.database import get_all_registrations
            df = get_all_registrations()
            if not df.empty: df['acciones'] = '🗑️'
            return df.to_dict('records')
        return no_update

    @app.callback(Output('modal-confirm-delete', 'is_open'), Output('store-record-to-delete', 'data'), Input('table-registros', 'active_cell'), State('table-registros', 'data'), prevent_initial_call=True)
    def open_delete_modal(active_cell, data):
        if active_cell and active_cell['column_id'] == 'acciones': return True, data[active_cell['row']]['combinacion']
        return False, no_update

    @app.callback(Output('modal-confirm-delete', 'is_open', allow_duplicate=True), Output("notification-container", "children", allow_duplicate=True), Input('btn-confirm-delete', 'n_clicks'), State('store-record-to-delete', 'data'), prevent_initial_call=True)
    def confirm_delete_record(n_clicks, combo_to_delete):
        if not fue_un_clic_real('btn-confirm-delete'): return no_update, no_update
        from modules.database import delete_registration
        if not combo_to_delete: return False, dbc.Alert("Error: No hay registro seleccionado.", color="danger")
        success, message = delete_registration(combo_to_delete)
        return False, dbc.Alert(message, color="success" if success else "danger", duration=4000)

    @app.callback(Output('modal-confirm-delete', 'is_open', allow_duplicate=True), Input('btn-cancel-delete', 'n_clicks'), prevent_initial_call=True)
    def cancel_delete(n_clicks):
        if not fue_un_clic_real('btn-cancel-delete'): return no_update
        return False

    @app.callback(Output("notification-container", "children", allow_duplicate=True), Input("btn-export-registros", "n_clicks"), prevent_initial_call=True)
    def handle_export_registros(n_clicks):
        if not fue_un_clic_real('btn-export-registros'): return no_update
        from modules.database import export_registrations_to_json
        success, message = export_registrations_to_json()
        return dbc.Alert(message, color="success" if success else "danger", duration=5000)

    @app.callback(Output("modal-confirm-import", "is_open"), Input("btn-import-registros", "n_clicks"), prevent_initial_call=True)
    def open_import_modal(n_clicks):
        if fue_un_clic_real('btn-import-registros'): return True
        return False

    @app.callback(Output("notification-container", "children", allow_duplicate=True), Output("modal-confirm-import", "is_open", allow_duplicate=True), Input("btn-import-overwrite", "n_clicks"), Input("btn-import-no-overwrite", "n_clicks"), prevent_initial_call=True)
    def handle_import_registros(overwrite_clicks, no_overwrite_clicks):
        from modules.database import import_registrations_from_json
        trigger_id = ctx.triggered_id
        if trigger_id not in ['btn-import-overwrite', 'btn-import-no-overwrite']: return no_update, no_update
        overwrite = trigger_id == 'btn-import-overwrite'
        _, _, _, message = import_registrations_from_json(overwrite=overwrite)
        return dbc.Alert(message, color="success", duration=8000), False

    # --- Callbacks de Visores ---
    @app.callback(
    Output('table-historicos', 'data'), 
    Output('table-historicos', 'style_data_conditional'), 
    Input('btn-refresh-historicos', 'n_clicks'), 
    Input('btn-nav-historicos', 'n_clicks')
    )
    def populate_historicos_table(refresh_clicks, nav_clicks):
        if ctx.triggered_id in ['btn-refresh-historicos', 'btn-nav-historicos']:
            from modules.database import read_historico_from_db
            df = read_historico_from_db()
            if df.empty: return [], []
            df['es_omega_str'] = df['es_omega'].apply(lambda x: 'Sí' if x == 1 else 'No')
            df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%d/%m/%Y')
            
            # --- LÓGICA DE ESTILO CORREGIDA (ORDEN DE PRIORIDAD) ---
            styles = [
                # 1. Regla general: Se aplica a toda la fila ganadora primero.
                {'if': {'filter_query': '{bolsa_ganada} = 1'}, 
                'backgroundColor': '#155724', 'color': 'white', 'fontWeight': 'bold'},
                
                # 2. Reglas específicas: Anulan la regla general SOLO para la columna 'es_omega_str'.
                #    Estas se aplican después y tienen la última palabra.
                {'if': {'column_id': 'es_omega_str', 'filter_query': '{es_omega_str} = "Sí"'}, 
                'backgroundColor': '#d4edda', 'color': '#155724'},
                {'if': {'column_id': 'es_omega_str', 'filter_query': '{es_omega_str} = "No"'}, 
                'backgroundColor': '#f8d7da', 'color': '#721c24'},
            ]
            
            # Para evitar romper el filter_query de la tabla que esperaba 'bolsa_ganada',
            # simplemente renombremos la columna en el DF que se envía a la tabla.
            if 'es_ganador' in df.columns:
                    df.rename(columns={'es_ganador': 'bolsa_ganada'}, inplace=True)

            return df.to_dict('records'), styles
        return no_update, no_update

    @app.callback(
    Output('graph-universo', 'figure'), 
    Output('graph-historico', 'figure'), 
    Output('graph-ganadores', 'figure'), 
    Output('graph-scatter-score-bolsa', 'figure'), 
    Output('notification-container', 'children', allow_duplicate=True), 
    Input('btn-refresh-graficos', 'n_clicks'), 
    prevent_initial_call=True
    )
    def update_all_graphs(n_clicks):
        if not fue_un_clic_real('btn-refresh-graficos'): return no_update, no_update, no_update, no_update, no_update
        from modules.database import read_historico_from_db, count_omega_class
        from modules.omega_logic import C
        empty_fig = go.Figure().update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        total_omega_class = count_omega_class()
        if not isinstance(total_omega_class, (int, float, np.integer)): return empty_fig, empty_fig, empty_fig, empty_fig, dbc.Alert("Error de tipo.", color="danger")
        total_omega_class_int = int(total_omega_class)
        if total_omega_class_int == 0: return empty_fig, empty_fig, empty_fig, empty_fig, dbc.Alert("Clase Omega no generada.", color="warning")
        fig_universo = create_donut_chart([total_omega_class_int, C(39, 6) - total_omega_class_int], ['Clase Omega', 'Otras'], 'Universo')
        df_historico = read_historico_from_db()
        if df_historico.empty: return no_update, empty_fig, empty_fig, empty_fig, dbc.Alert("Histórico vacío.", color="warning")
        
        # --- LÓGICA DE GRÁFICOS CORREGIDA ---
        historico_counts = df_historico['es_omega'].value_counts()
        fig_historico = create_donut_chart([historico_counts.get(1, 0), historico_counts.get(0, 0)], ['Omega', 'No Omega'], 'Sorteos Históricos')
        
        # Filtramos por el nuevo flag 'es_ganador'
        df_ganadores = df_historico[df_historico['es_ganador'] == 1].copy()
        ganadores_counts = df_ganadores['es_omega'].value_counts()
        fig_ganadores = create_donut_chart([ganadores_counts.get(1, 0), ganadores_counts.get(0, 0)], ['Omega', 'No Omega'], 'Sorteos con Premio')
        
        df_scatter = df_ganadores
        if df_scatter.empty: fig_scatter = empty_fig.update_layout(title_text="No hay sorteos con premio mayor")
        else:
            df_scatter['Clase'] = df_scatter['es_omega'].apply(lambda x: 'Omega' if x == 1 else 'No Omega')
            df_scatter['combinacion_str'] = df_scatter[['r1', 'r2', 'r3', 'r4', 'r5', 'r6']].astype(str).agg('-'.join, axis=1)
            
            # Usamos la columna 'bolsa_ganada' para el eje Y, que ahora contiene el monto correcto
            fig_scatter = px.scatter(
                df_scatter, x="omega_score", y="bolsa_ganada", color="Clase",
                color_discrete_map={'Omega': '#3b71ca', 'No Omega': '#dc3545'},
                template="simple_white", title="Comparativa de Sorteos con Premio Mayor",
                labels={"omega_score": "Omega Score", "bolsa_ganada": "Bolsa Ganada (MXN)"},
                hover_data=['concurso', 'fecha', 'combinacion_str']
            )
            fig_scatter.update_layout(title_x=0.5, legend_title_text='', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig_scatter.update_traces(marker=dict(size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')))
        
        return fig_universo, fig_historico, fig_ganadores, fig_scatter, None

    @app.callback(Output('graph-trayectoria-umbrales', 'figure'), Input('btn-refresh-trayectoria', 'n_clicks'), Input('btn-nav-trayectoria', 'n_clicks'))
    def update_trajectory_graph(refresh_clicks, nav_clicks):
        if ctx.triggered_id in ['btn-refresh-trayectoria', 'btn-nav-trayectoria']:
            from modules.database import read_trajectory_data
            df_trajectory = read_trajectory_data()
            if df_trajectory.empty:
                fig = go.Figure()
                fig.update_layout(title_text="No hay datos de trayectoria. Ejecute 'generate_trajectory.py'", title_x=0.5, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                return fig
            fig = px.line(
                df_trajectory, x='ultimo_concurso_usado', y=['umbral_pares', 'umbral_tercias', 'umbral_cuartetos'],
                template='simple_white', labels={'ultimo_concurso_usado': 'Sorteo Histórico', 'value': 'Valor del Umbral'},
                title='Evolución de Umbrales Óptimos'
            )
            fig.update_layout(title_x=0.5, legend_title_text='Afinidad')
            return fig
        return no_update

    # 5. INICIAR EL SERVIDOR
    def open_browser():
        webbrowser.open_new_tab("http://127.0.0.1:8050")

    import os
    if os.environ.get("DOCKER_ENV") is None:
        Timer(1, open_browser).start()
    
    app.run(debug=False, host='0.0.0.0', port='8050')