import time
start_total = time.perf_counter()

import logging
from utils.logger_config import setup_logger
from utils import state_manager
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import importlib
import config

setup_logger()
logger = logging.getLogger(__name__)

logger.info("="*50)
logger.info("INICIO DE LA APLICACIÓN ZEN LOTTO")
logger.info("="*50)

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, ctx, State, no_update

app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True
)
server = app.server

from modules.presentation import create_layout
app.layout = create_layout()

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

# --- Callbacks de Navegación ---
@app.callback(
    Output("view-content", "children"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-graficos", "n_clicks"),
    Input("btn-nav-historicos", "n_clicks"),
    Input("btn-nav-registros", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
)
def render_view_content(gen_clicks, graf_clicks, hist_clicks, reg_clicks, conf_clicks):
    from modules.presentation import create_generador_view, create_configuracion_view, create_registros_view, create_historicos_view, create_graficos_view
    triggered_id = ctx.triggered_id or "btn-nav-generador"
    if triggered_id == "btn-nav-configuracion": return create_configuracion_view()
    elif triggered_id == "btn-nav-registros": return create_registros_view()
    elif triggered_id == "btn-nav-historicos": return create_historicos_view()
    elif triggered_id == "btn-nav-graficos": return create_graficos_view()
    return create_generador_view()

@app.callback(
    Output("btn-nav-generador", "className"),
    Output("btn-nav-graficos", "className"),
    Output("btn-nav-historicos", "className"),
    Output("btn-nav-registros", "className"),
    Output("btn-nav-configuracion", "className"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-graficos", "n_clicks"),
    Input("btn-nav-historicos", "n_clicks"),
    Input("btn-nav-registros", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
)
def update_nav_buttons_style(gen_clicks, graf_clicks, hist_clicks, reg_clicks, conf_clicks):
    triggered_id = ctx.triggered_id or "btn-nav-generador"
    base_class = "nav-button"
    styles = {"generador": base_class, "graficos": base_class, "historicos": base_class, "registros": base_class, "configuracion": base_class}
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
    prevent_initial_call=True
)
def handle_optimize_thresholds(n_clicks):
    if not fue_un_clic_real('btn-optimize-thresholds'): return no_update
    
    from modules import ml_optimizer, omega_logic, database
    
    logger.info("Callback 'handle_optimize_thresholds' (Versión Manus) disparado.")
    df_historico = database.read_historico_from_db()
    freqs = omega_logic.get_frequencies()
    
    if df_historico.empty or freqs is None:
        return dbc.Alert("Se necesita el histórico y las frecuencias para optimizar.", color="warning")
    
    start = time.time()
    success, message, report = ml_optimizer.optimize_thresholds(df_historico, freqs)
    total_time = time.time() - start
    
    importlib.reload(config)
    
    if success and isinstance(report, dict):
        new_thr = report.get('new_thresholds', {})
        ch = report.get('cobertura_historica', 0)
        cu = report.get('cobertura_universal_estimada', 0)
        
        details = (
            f"Nuevos umbrales: P={new_thr.get('pares')}, T={new_thr.get('tercias')}, C={new_thr.get('cuartetos')}. | "
            f"CH: {ch:.1%} | CU (Estimada): {cu:.2%}"
        )
        
        instruction = "Para aplicar, re-ejecute '4. ENRIQUECER Y PRE-GENERAR'."
        full_message = f"{message} {details} {instruction} (Tiempo: {total_time:.2f}s)"
    else:
        full_message = f"{message} (Tiempo: {total_time:.2f}s)"
        
    return dbc.Alert(full_message, color="success" if success else "danger", duration=25000)

@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-enrich-pregen", "n_clicks"),
    prevent_initial_call=True
)
def handle_enrich_and_pregenerate(n_clicks):
    if not fue_un_clic_real('btn-enrich-pregen'): return no_update
    from modules.omega_logic import enrich_historical_data, pregenerate_omega_class
    importlib.reload(config)
    
    logger.info("Iniciando Fase 1: Enriquecimiento de datos históricos.")
    start_enrich = time.time()
    success_enrich, msg_enrich = enrich_historical_data()
    time_enrich = time.time() - start_enrich
    
    if not success_enrich:
        return dbc.Alert(f"Falló el enriquecimiento de datos: {msg_enrich}", color="danger")
    
    logger.info("Iniciando Fase 2: Pre-generación de Clase Omega.")
    start_pregen = time.time()
    success_pregen, msg_pregen = pregenerate_omega_class()
    time_pregen = time.time() - start_pregen
    
    if not success_pregen:
        return dbc.Alert(f"Falló la pre-generación: {msg_pregen}", color="danger")

    total_time = time_enrich + time_pregen
    full_message = f"Proceso completado en {total_time:.2f}s. {msg_enrich} {msg_pregen}"
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
    if isinstance(omega_score, (int, float)): score_text = f"Omega Score: {omega_score:.4f}"
    else: score_text = "Omega Score: N/A"
    criterios = result.get("criterios", {})
    if not isinstance(criterios, dict): return default_return[:-1] + [dbc.Alert("Faltan datos de criterios.", color="danger")]
    pares, tercias, cuartetos = criterios.get("pares", {}), criterios.get("tercias", {}), criterios.get("cuartetos", {})
    details_list = [html.Li(f"Afinidad de Pares: {pares.get('score')} / {pares.get('umbral')} {'✅' if pares.get('cumple') else '❌'}"), html.Li(f"Afinidad de Tercias: {tercias.get('score')} / {tercias.get('umbral')} {'✅' if tercias.get('cumple') else '❌'}"), html.Li(f"Afinidad de Cuartetos: {cuartetos.get('score')} / {cuartetos.get('umbral')} {'✅' if cuartetos.get('cumple') else '❌'}")]
    validated_combo_for_store = combination if es_omega else None
    return {'display': 'block'}, f"{card_class_base} {card_class_color}", title, combo_text, score_text, details_list, validated_combo_for_store, None

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

@app.callback(Output("notification-container", "children", allow_duplicate=True), Input("btn-registrar", "n_clicks"), [State('store-validated-omega', 'data'), State('input-nombre', 'value'), State('input-movil', 'value')], prevent_initial_call=True)
def handle_register_omega(n_clicks, validated_omega, nombre, movil):
    if not fue_un_clic_real('btn-registrar'): return no_update
    from modules.database import register_omega_combination
    if not validated_omega or not nombre or not movil: return dbc.Alert("Todos los campos son obligatorios.", color="warning")
    success, message = register_omega_combination(validated_omega, nombre.strip(), movil.strip())
    return dbc.Alert(message, color="success" if success else "danger", duration=5000)

# --- CALLBACKS QUE FALTABAN ---
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

@app.callback(Output('table-historicos', 'data'), Output('table-historicos', 'style_data_conditional'), Input('btn-refresh-historicos', 'n_clicks'), Input('btn-nav-historicos', 'n_clicks'))
def populate_historicos_table(refresh_clicks, nav_clicks):
    if ctx.triggered_id in ['btn-refresh-historicos', 'btn-nav-historicos']:
        from modules.database import read_historico_from_db
        df = read_historico_from_db()
        if df.empty: return [], []
        df['es_omega_str'] = df['es_omega'].apply(lambda x: 'Sí' if x == 1 else 'No')
        df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%d/%m/%Y')
        styles = [
            {'if': {'column_id': 'es_omega_str', 'filter_query': '{es_omega_str} = "Sí"'}, 'backgroundColor': '#d4edda', 'color': '#155724'},
            {'if': {'column_id': 'es_omega_str', 'filter_query': '{es_omega_str} = "No"'}, 'backgroundColor': '#f8d7da', 'color': '#721c24'},
            {'if': {'column_id': 'bolsa', 'filter_query': '{bolsa_ganada} = 1'}, 'backgroundColor': '#155724', 'color': 'white', 'fontWeight': 'bold'}
        ]
        return df.to_dict('records'), styles
    return no_update, no_update

@app.callback(
    Output('graph-universo', 'figure'), Output('graph-historico', 'figure'),
    Output('graph-ganadores', 'figure'), Output('graph-scatter-score-bolsa', 'figure'),
    Output('notification-container', 'children', allow_duplicate=True),
    Input('btn-refresh-graficos', 'n_clicks'),
    prevent_initial_call=True
)
def update_all_graphs(n_clicks):
    if not fue_un_clic_real('btn-refresh-graficos'):
        return no_update, no_update, no_update, no_update, no_update
    from modules.database import read_historico_from_db, count_omega_class
    from modules.omega_logic import C
    empty_fig = go.Figure().update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    total_omega_class = count_omega_class()
    if not isinstance(total_omega_class, (int, float, np.integer)):
        return empty_fig, empty_fig, empty_fig, empty_fig, dbc.Alert("Error de tipo en datos.", color="danger")
    total_omega_class_int = int(total_omega_class)
    if total_omega_class_int == 0:
        return empty_fig, empty_fig, empty_fig, empty_fig, dbc.Alert("Clase Omega no generada.", color="warning")
    fig_universo = create_donut_chart([total_omega_class_int, C(39, 6) - total_omega_class_int], ['Clase Omega', 'Otras'], 'Universo')
    df_historico = read_historico_from_db()
    if df_historico.empty: return no_update, empty_fig, empty_fig, empty_fig, dbc.Alert("Histórico vacío.", color="warning")
    historico_counts = df_historico['es_omega'].value_counts()
    fig_historico = create_donut_chart([historico_counts.get(1, 0), historico_counts.get(0, 0)], ['Omega', 'No Omega'], 'Sorteos Históricos')
    df_ganadores = df_historico[df_historico['bolsa_ganada'] == 1]
    ganadores_counts = df_ganadores['es_omega'].value_counts()
    fig_ganadores = create_donut_chart([ganadores_counts.get(1, 0), ganadores_counts.get(0, 0)], ['Omega', 'No Omega'], 'Sorteos con Premio')
    df_scatter = df_ganadores.copy()
    if df_scatter.empty: fig_scatter = empty_fig.update_layout(title_text="No hay sorteos con premio mayor")
    else:
        df_scatter['Clase'] = df_scatter['es_omega'].apply(lambda x: 'Omega' if x == 1 else 'No Omega')
        df_scatter['combinacion_str'] = df_scatter[['r1', 'r2', 'r3', 'r4', 'r5', 'r6']].astype(str).agg('-'.join, axis=1)
        fig_scatter = px.scatter(
            df_scatter, x="omega_score", y="bolsa", color="Clase",
            color_discrete_map={'Omega': '#3b71ca', 'No Omega': '#dc3545'},
            template="simple_white", title="Comparativa de Sorteos con Premio Mayor",
            labels={"omega_score": "Omega Score", "bolsa": "Bolsa Acumulada (MXN)"},
            hover_data=['concurso', 'fecha', 'combinacion_str']
        )
        fig_scatter.update_layout(title_x=0.5, legend_title_text='', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig_scatter.update_traces(marker=dict(size=10, opacity=0.7, line=dict(width=1, color='DarkSlateGrey')))
    return fig_universo, fig_historico, fig_ganadores, fig_scatter, None

# --- CALLBACKS PARA IMPORTACIÓN/EXPORTACIÓN DE REGISTROS ---

@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-export-registros", "n_clicks"),
    prevent_initial_call=True
)
def handle_export_registros(n_clicks):
    if not fue_un_clic_real('btn-export-registros'):
        return no_update
    
    from modules.database import export_registrations_to_json
    logger.info("Iniciando exportación de registros.")
    success, message = export_registrations_to_json()
    color = "success" if success else "danger"
    
    return dbc.Alert(message, color=color, duration=5000)

@app.callback(
    Output("modal-confirm-import", "is_open"),
    Input("btn-import-registros", "n_clicks"),
    prevent_initial_call=True
)
def open_import_modal(n_clicks):
    if fue_un_clic_real('btn-import-registros'):
        return True
    return False

@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Output("modal-confirm-import", "is_open", allow_duplicate=True),
    Input("btn-import-overwrite", "n_clicks"),
    Input("btn-import-no-overwrite", "n_clicks"),
    prevent_initial_call=True
)
def handle_import_registros(overwrite_clicks, no_overwrite_clicks):
    from modules.database import import_registrations_from_json
    
    # Determinamos si el usuario quiere sobrescribir basándonos en qué botón se presionó
    overwrite = ctx.triggered_id == 'btn-import-overwrite'
    
    logger.info(f"Iniciando importación de registros con overwrite={overwrite}")
    added, updated, total, message = import_registrations_from_json(overwrite=overwrite)
    
    # Cerramos el modal y mostramos el resultado
    return dbc.Alert(message, color="success", duration=8000), False

if __name__ == "__main__":
    logger.info("Iniciando servidor (Debug OFF).")
    app.run(debug=False, port=8050) # type: ignore