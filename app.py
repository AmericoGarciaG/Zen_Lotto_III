# app.py

import time
import logging
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import config
import plotly.express as px
from threading import Timer
import webbrowser
import diskcache
from dash import DiskcacheManager, Dash, dcc, html, Input, Output, State, ctx, no_update, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import os
import json

from utils.logger_config import setup_logger
from modules.presentation import create_layout

# --- CONFIGURACIÓN INICIAL ---
setup_logger()
logger = logging.getLogger(__name__)

# --- FUNCIONES DE AYUDA ---
def fue_un_clic_real(button_id: str) -> bool:
    if not ctx.triggered: return False
    triggered_info = ctx.triggered[0]
    prop_id_str = triggered_info['prop_id']
    component_id_str = prop_id_str.split('.')[0]
    if component_id_str.startswith('{'): return False
    if component_id_str != button_id: return False
    value = triggered_info.get('value')
    return isinstance(value, int) and value > 0

def create_donut_chart(values, labels, title, game_name):
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5, textinfo='label+percent', insidetextorientation='radial', marker_colors=['#3b71ca', '#adb5bd'])])
    fig.update_layout(title_text=f"{title}<br>({game_name})", title_x=0.5, title_y=0.95, title_yanchor='top', showlegend=False, margin=dict(t=80, b=20, l=20, r=20), height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    if not any(v > 0 for v in values):
        fig.update_layout(annotations=[{"text": "N/A", "xref": "paper", "yref": "paper", "showarrow": False, "font": {"size": 28}}])
    return fig

# --- PUNTO DE ENTRADA PRINCIPAL ---
if __name__ == "__main__":
    logger.info("=" * 50); logger.info("INICIO DE LA APLICACIÓN ZEN LOTTO"); logger.info("=" * 50)

    cache = diskcache.Cache("./cache")
    long_callback_manager = DiskcacheManager(cache)
    app = Dash(__name__, external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME], suppress_callback_exceptions=True, background_callback_manager=long_callback_manager)
    server = app.server
    app.layout = create_layout()

    # --- CALLBACKS DE GESTIÓN DE JUEGO Y UI DINÁMICA ---
    @app.callback(
        Output('store-active-game', 'data'),
        Output('game-selector-display', 'label'),
        Input({'type': 'game-selector', 'index': ALL}, 'n_clicks'),
        State('store-active-game', 'data')
    )
    def update_active_game(n_clicks, game_id_on_load):
        triggered_id = ctx.triggered_id
        if triggered_id is None:
            game_id = game_id_on_load or 'melate_retro'
            game_name = config.GAME_REGISTRY[game_id]['display_name']
            return game_id, game_name
        if isinstance(triggered_id, dict) and triggered_id.get('type') == 'game-selector':
            if not any(n_clicks): return no_update, no_update
            game_id = triggered_id['index']
            game_name = config.GAME_REGISTRY[game_id]['display_name']
            return game_id, game_name
        return no_update, no_update

    @app.callback(
        Output('generador-inputs-container', 'children'),
        Input('store-active-game', 'data')
    )
    def update_generator_inputs(game_id):
        game_config = config.get_game_config(game_id or 'melate_retro')
        n = game_config['n']
        inputs = [dbc.Col(dcc.Input(id={'type': 'num-input', 'index': i}, type='number', className='number-box', min=1, max=game_config['k']), width='auto') for i in range(n)]
        clear_button = dbc.Col(dbc.Button(html.I(className="fas fa-trash-alt"), id="btn-clear-inputs", color="secondary", outline=True, className="ms-2"), width="auto", className="d-flex align-items-center")
        return dbc.Row(inputs + [clear_button], justify="center", align="center", className="g-2")

    @app.callback(
        Output({'type': 'num-input', 'index': ALL}, 'value'),
        Output('store-validated-omega', 'data', allow_duplicate=True),
        Output('analysis-result-card', 'style', allow_duplicate=True),
        Input('btn-clear-inputs', 'n_clicks'),
        State({'type': 'num-input', 'index': ALL}, 'value'),
        prevent_initial_call=True
    )
    def handle_clear_inputs(n_clicks, current_values):
        if not fue_un_clic_real('btn-clear-inputs'):
            return [no_update] * len(current_values), no_update, no_update
        return [None] * len(current_values), None, {'display': 'none'}
    
    @app.callback(
        Output('config-game-indicator', 'children'),
        Output('registros-title', 'children'),
        Output('historicos-title', 'children'),
        Input('store-active-game', 'data'),
        Input('view-content', 'children')
    )
    def update_view_titles(game_id, _):
        game_name = config.get_game_config(game_id or 'melate_retro')['display_name']
        return f"Ejecutando acciones para: {game_name}", f"Registro de Combinaciones Omega ({game_name})", f"Registros Históricos ({game_name})"

    # --- CALLBACKS DE NAVEGACIÓN ---
    @app.callback(
        Output("view-content", "children"),
        [Input(f"btn-nav-{view}", "n_clicks") for view in ["generador", "graficos", "historicos"] + (["monitoreo"] if config.DEBUG_MODE else []) + ["omega-cero", "registros", "configuracion"]]
    )
    def render_view_content(*args):
        from modules import presentation
        triggered_id = ctx.triggered_id or "btn-nav-generador"
        view_map = {
            "btn-nav-configuracion": presentation.create_configuracion_view,
            "btn-nav-registros": presentation.create_registros_view,
            "btn-nav-omega-cero": presentation.create_omega_cero_view,
            "btn-nav-monitoreo": presentation.create_monitoring_view,
            "btn-nav-historicos": presentation.create_historicos_view,
            "btn-nav-graficos": presentation.create_graficos_view,
        }
        return view_map.get(triggered_id, presentation.create_generador_view)()
    
    @app.callback(
        [Output(f"btn-nav-{view}", "className") for view in ["generador", "graficos", "historicos"] + (["monitoreo"] if config.DEBUG_MODE else []) + ["omega-cero", "registros", "configuracion"]],
        [Input(f"btn-nav-{view}", "n_clicks") for view in ["generador", "graficos", "historicos"] + (["monitoreo"] if config.DEBUG_MODE else []) + ["omega-cero", "registros", "configuracion"]]
    )
    def update_nav_buttons_style(*args):
        triggered_id = ctx.triggered_id or "btn-nav-generador"
        views = ["generador", "graficos", "historicos"] + (["monitoreo"] if config.DEBUG_MODE else []) + ["omega-cero", "registros", "configuracion"]
        styles = {view: "nav-button" for view in views}
        active_view = triggered_id.replace("btn-nav-", "")
        if active_view in styles: styles[active_view] += " active"
        else: styles["generador"] += " active"
        return list(styles.values())

    # --- CALLBACKS DE CONFIGURACIÓN ---
    @app.callback(
        Output("notification-container", "children", allow_duplicate=True),
        Input("btn-gen-historico", "n_clicks"),
        State('store-active-game', 'data'),
        prevent_initial_call=True
    )
    def handle_historical_load(n_clicks, game_id):
        if not fue_un_clic_real("btn-gen-historico"): return no_update
        from modules import data_ingestion, database; from utils import state_manager
        game_config = config.get_game_config(game_id); state = state_manager.get_state(game_config['paths']['state'])
        last_concurso = state.get("last_concurso_in_db", 0)
        df_new, message, success = data_ingestion.run_historical_load(game_config, last_concurso)
        if not success or df_new is None: return dbc.Alert(message, color="danger")
        save_success, save_msg = database.save_historico_to_db(df_new, game_config['paths']['db'], mode="append")
        if not save_success: return dbc.Alert(save_msg, color="danger")
        if not df_new.empty:
            state["last_concurso_in_db"] = int(df_new["concurso"].max())
            state_manager.save_state(state, game_config['paths']['state'])
        return dbc.Alert(message, color="success", duration=8000)

    @app.callback(
        Output("notification-container", "children", allow_duplicate=True),
        Input("btn-gen-omega", "n_clicks"), State('store-active-game', 'data'), prevent_initial_call=True
    )
    def handle_freq_generation(n_clicks, game_id):
        if not fue_un_clic_real("btn-gen-omega"): return no_update
        from modules import omega_logic
        game_config = config.get_game_config(game_id)
        success, message = omega_logic.calculate_and_save_frequencies(game_config)
        return dbc.Alert(message, color="success" if success else "danger", duration=8000)

    @app.callback(
        Output("notification-container", "children", allow_duplicate=True),
        Input("btn-optimize-thresholds", "n_clicks"), State('store-active-game', 'data'),
        progress=[Output("progress-bar", "value"), Output("progress-text", "children"), Output("progress-container", "style"), Output("btn-optimize-thresholds", "disabled"), Output("btn-gen-historico", "disabled"), Output("btn-gen-omega", "disabled"), Output("btn-enrich", "disabled"), Output("btn-pregen", "disabled")],
        background=True, prevent_initial_call=True
    )
    def handle_optimize_thresholds(set_progress, n_clicks, game_id):
        if not n_clicks or n_clicks < 1: raise PreventUpdate
        from modules import ml_optimizer, omega_logic, database; from utils import state_manager
        game_config = config.get_game_config(game_id); state_path = game_config['paths']['state']
        state = state_manager.get_state(state_path)
        set_progress((0, "Iniciando...", {"display": "block"}, True, True, True, True, True))
        df_historico = database.read_historico_from_db(game_config['paths']['db'])
        freqs = omega_logic.get_frequencies(game_config)
        if df_historico.empty or not freqs:
            set_progress((100, "Error.", {"display": "none"}, False, False, False, False, False))
            return dbc.Alert("Se necesita el histórico y las frecuencias para optimizar.", color="warning")
        success, message, report = ml_optimizer.run_optimization(game_config, df_historico, freqs, set_progress=set_progress)
        if success:
            state["last_concurso_for_optimization"] = state.get("last_concurso_for_freqs", 0)
            state_manager.save_state(state, state_path)
        set_progress((100, "Completado.", {"display": "none"}, False, False, False, False, False))
        return dbc.Alert(message, color="success" if success else "danger", duration=20000)
    
    @app.callback(
        Output("notification-container", "children", allow_duplicate=True),
        Input("btn-enrich", "n_clicks"), State('store-active-game', 'data'),
        progress=[Output("progress-bar", "value"), Output("progress-text", "children"), Output("progress-container", "style"), Output("btn-enrich", "disabled"), Output("btn-gen-historico", "disabled"), Output("btn-gen-omega", "disabled"), Output("btn-optimize-thresholds", "disabled"), Output("btn-pregen", "disabled")],
        background=True, prevent_initial_call=True
    )
    def handle_enrich(set_progress, n_clicks, game_id):
        if not n_clicks or n_clicks < 1: raise PreventUpdate
        from modules import omega_logic
        game_config = config.get_game_config(game_id)
        set_progress((0, "Iniciando enriquecimiento...", {"display": "block"}, True, True, True, True, True))
        success, message = omega_logic.enrich_historical_data(game_config, set_progress)
        set_progress((100, "Completado.", {"display": "none"}, False, False, False, False, False))
        return dbc.Alert(message, color="success" if success else "danger", duration=15000)

    @app.callback(
        Output("notification-container", "children", allow_duplicate=True),
        Input("btn-pregen", "n_clicks"), State('store-active-game', 'data'),
        progress=[Output("progress-bar", "value"), Output("progress-text", "children"), Output("progress-container", "style"), Output("btn-pregen", "disabled"), Output("btn-gen-historico", "disabled"), Output("btn-gen-omega", "disabled"), Output("btn-optimize-thresholds", "disabled"), Output("btn-enrich", "disabled")],
        background=True, prevent_initial_call=True
    )
    def handle_pregenerate(set_progress, n_clicks, game_id):
        if not n_clicks or n_clicks < 1: raise PreventUpdate
        from modules import omega_logic
        game_config = config.get_game_config(game_id)
        set_progress((0, "Iniciando pre-generación...", {"display": "block"}, True, True, True, True, True))
        success, message = omega_logic.pregenerate_omega_class(game_config, set_progress)
        set_progress((100, "Completado.", {"display": "none"}, False, False, False, False, False))
        return dbc.Alert(message, color="success" if success else "danger", duration=15000)
    
    # --- CALLBACKS DEL GENERADOR ---
    @app.callback(
        Output({'type': 'num-input', 'index': ALL}, 'value', allow_duplicate=True),
        Output("notification-container", "children", allow_duplicate=True),
        Output("store-validated-omega", "data", allow_duplicate=True),
        Input("btn-generar", "n_clicks"), State('store-active-game', 'data'), State({'type': 'num-input', 'index': ALL}, 'value'),
        prevent_initial_call=True,
    )
    def handle_generate_omega(n_clicks, game_id, num_inputs):
        num_outputs = len(num_inputs); no_update_list = [no_update] * num_outputs
        if not fue_un_clic_real("btn-generar"): return no_update_list, no_update, no_update
        from modules import omega_logic, database
        game_config = config.get_game_config(game_id); db_path = game_config['paths']['db']
        if all(num is None or num == "" for num in num_inputs):
            combo = database.get_random_omega_combination(db_path, game_config)
            if combo: return combo, None, combo
            return no_update_list, dbc.Alert("Error al generar.", color="warning"), None
        else:
            try: user_combo = sorted([int(num) for num in num_inputs])
            except (ValueError, TypeError): return no_update_list, dbc.Alert("Ingrese una combinación válida.", color="warning"), None
            if len(set(user_combo)) != game_config['n']: return no_update_list, dbc.Alert(f"Se requieren {game_config['n']} números únicos.", color="warning"), None
            freqs = omega_logic.get_frequencies(game_config)
            if freqs is None: return no_update_list, dbc.Alert("Frecuencias no generadas.", color="danger"), None
            loaded_thresholds = omega_logic.get_loaded_thresholds(game_config)
            eval_result = omega_logic.evaluate_combination(user_combo, freqs, game_config, loaded_thresholds)
            if eval_result.get("esOmega"): return no_update_list, dbc.Alert("¡Tu combinación ya es Omega!", color="success"), user_combo
            for matches in range(game_config['n'] - 1, 2, -1):
                adjusted = database.find_closest_omega(user_combo, matches, db_path, game_config)
                if adjusted: return adjusted, dbc.Alert(f"¡Ajuste exitoso! Se mantuvieron {matches} números.", color="info"), adjusted
            return no_update_list, dbc.Alert("No se encontró un ajuste cercano.", color="danger"), None

    @app.callback(
        Output("analysis-result-card", "style"), Output("analysis-result-card", "className"), Output("analysis-title", "children"),
        Output("analysis-combination-text", "children"), Output("analysis-score-text", "children"), Output("analysis-details-list", "children"),
        Output("store-validated-omega", "data", allow_duplicate=True), Output("notification-container", "children", allow_duplicate=True),
        Input("btn-analizar", "n_clicks"), State('store-active-game', 'data'), State({'type': 'num-input', 'index': ALL}, 'value'),
        prevent_initial_call=True,
    )
    def handle_analizar_combinacion(n_clicks, game_id, num_inputs):
        if not fue_un_clic_real("btn-analizar"): return (no_update,) * 8
        from modules import omega_logic
        game_config = config.get_game_config(game_id); n = game_config['n']
        try:
            if any(num is None or num == "" for num in num_inputs): raise ValueError(f"Por favor, ingrese {n} números.")
            combination = sorted([int(num) for num in num_inputs])
            if len(set(combination)) != n: raise ValueError(f"Los {n} números deben ser únicos.")
        except (ValueError, TypeError) as e: return {'display': 'none'}, "", "", "", "", [], None, dbc.Alert(str(e), color="warning")
        freqs = omega_logic.get_frequencies(game_config)
        if freqs is None: return {'display': 'none'}, "", "", "", "", [], None, dbc.Alert("Frecuencias no generadas.", color="danger")
        loaded_thresholds = omega_logic.get_loaded_thresholds(game_config)
        result = omega_logic.evaluate_combination(combination, freqs, game_config, loaded_thresholds)
        es_omega = result.get("esOmega", False)
        title = "¡CLASE OMEGA! ✅" if es_omega else "COMBINACIÓN NO-OMEGA ❌"
        card_class = f"mt-4 text-dark p-3 {'border-success bg-success-subtle' if es_omega else 'border-danger bg-danger-subtle'}"
        score_text = f"Omega Score: {result.get('omegaScore', 0):.4f}"
        criterios = result.get("criterios", {})
        details_list = [html.Li(f"{key.capitalize()}: {val.get('score')} / {val.get('umbral')} {'✅' if val.get('cumple') else '❌'}") for key, val in criterios.items()]
        if result.get("haSalido"): details_list.extend([html.Li(html.Hr(), style={"listStyleType": "none"}), html.Li("Ya ha salido en el histórico ❌")])
        return {'display': 'block'}, card_class, title, f"Tu combinación: {result.get('combinacion', [])}", score_text, details_list, (combination if es_omega else None), None

    @app.callback(
        Output("input-nombre", "disabled"), Output("input-movil", "disabled"), Output("btn-registrar", "disabled"),
        Input("store-validated-omega", "data"), Input({'type': 'num-input', 'index': ALL}, 'value')
    )
    def control_registration_fields(validated_omega, current_inputs_tuple):
        try: current_inputs = sorted([int(i) for i in current_inputs_tuple if i is not None and i != ""])
        except (ValueError, TypeError): current_inputs = []
        if (validated_omega and len(current_inputs) == len(validated_omega) and sorted(validated_omega) == current_inputs): return False, False, False
        return True, True, True
     
    # --- CALLBACKS DE REGISTRO Y GESTIÓN ---
    @app.callback(
        Output("notification-container", "children", allow_duplicate=True),
        Input("btn-registrar", "n_clicks"), State('store-active-game', 'data'), State("store-validated-omega", "data"), State("input-nombre", "value"), State("input-movil", "value"),
        prevent_initial_call=True
    )
    def handle_register_omega(n_clicks, game_id, validated_omega, nombre, movil):
        if not fue_un_clic_real("btn-registrar"): return no_update
        from modules import database
        game_config = config.get_game_config(game_id)
        if not validated_omega or not nombre or not movil: return dbc.Alert("Todos los campos son obligatorios.", color="warning")
        success, message = database.register_omega_combination(validated_omega, nombre.strip(), movil.strip(), game_config['paths']['db'])
        return dbc.Alert(message, color="success" if success else "danger", duration=5000)
    
    @app.callback(
        Output('table-registros', 'data'),
        Input('btn-refresh-registros', 'n_clicks'), Input('view-content', 'children'),
        State('store-active-game', 'data'), State('btn-nav-registros', 'n_clicks')
    )
    def populate_registros_table(refresh_clicks, _, game_id, nav_clicks):
        if (ctx.triggered_id != 'btn-refresh-registros' and ctx.triggered_id != 'view-content') or not nav_clicks: return no_update
        from modules import database
        game_config = config.get_game_config(game_id)
        df = database.get_all_registrations(game_config['paths']['db'])
        if not df.empty: df['acciones'] = "🗑️"
        return df.to_dict('records')

    @app.callback(
        Output("modal-confirm-delete", "is_open"), Output("store-record-to-delete", "data"),
        Input("table-registros", "active_cell"), State("table-registros", "data"),
        prevent_initial_call=True,
    )
    def open_delete_modal(active_cell, data):
        if active_cell and data and active_cell["column_id"] == "acciones": return True, data[active_cell["row"]]["combinacion"]
        return False, no_update
        
    @app.callback(
        Output("modal-confirm-delete", "is_open", allow_duplicate=True), Output("notification-container", "children", allow_duplicate=True), Output("btn-refresh-registros", "n_clicks"),
        Input("btn-confirm-delete", "n_clicks"), State("store-record-to-delete", "data"), State('store-active-game', 'data'),
        prevent_initial_call=True,
    )
    def confirm_delete_record(n_clicks, combo_to_delete, game_id):
        refresh_trigger = ctx.inputs['btn-confirm-delete.n_clicks']
        if not fue_un_clic_real("btn-confirm-delete"): return no_update, no_update, no_update
        from modules import database
        game_config = config.get_game_config(game_id)
        if not combo_to_delete: return False, dbc.Alert("Error: No hay registro seleccionado.", color="danger"), no_update
        success, message = database.delete_registration(combo_to_delete, game_config['paths']['db'])
        return False, dbc.Alert(message, color="success" if success else "danger", duration=4000), refresh_trigger

    @app.callback(
        Output("modal-confirm-delete", "is_open", allow_duplicate=True),
        Input("btn-cancel-delete", "n_clicks"), prevent_initial_call=True,
    )
    def cancel_delete(n_clicks):
        return False if n_clicks else no_update

    @app.callback(
        Output("notification-container", "children", allow_duplicate=True),
        Input("btn-export-registros", "n_clicks"), State('store-active-game', 'data'),
        prevent_initial_call=True,
    )
    def handle_export_registros(n_clicks, game_id):
        if not fue_un_clic_real("btn-export-registros"): return no_update
        from modules import database
        game_config = config.get_game_config(game_id)
        success, message = database.export_registrations_to_json(game_config['paths']['db'], game_config['paths']['backup'])
        return dbc.Alert(message, color="success" if success else "danger", duration=5000)

    @app.callback(
        Output("modal-confirm-import", "is_open"),
        Input("btn-import-registros", "n_clicks"), prevent_initial_call=True,
    )
    def open_import_modal(n_clicks):
        return True if n_clicks else False

    @app.callback(
        Output("notification-container", "children", allow_duplicate=True), Output("modal-confirm-import", "is_open", allow_duplicate=True), Output("btn-refresh-registros", "n_clicks", allow_duplicate=True),
        Input("btn-import-overwrite", "n_clicks"), Input("btn-import-no-overwrite", "n_clicks"), State('store-active-game', 'data'),
        prevent_initial_call=True,
    )
    def handle_import_registros(overwrite_clicks, no_overwrite_clicks, game_id):
        from modules import database
        trigger_id = ctx.triggered_id
        if trigger_id not in ["btn-import-overwrite", "btn-import-no-overwrite"]: return no_update, no_update, no_update
        game_config = config.get_game_config(game_id)
        overwrite = trigger_id == "btn-import-overwrite"
        _, _, _, message = database.import_registrations_from_json(game_config['paths']['db'], game_config['paths']['backup'], overwrite=overwrite)
        refresh_trigger = (overwrite_clicks or 0) + (no_overwrite_clicks or 0)
        return dbc.Alert(message, color="success", duration=8000), False, refresh_trigger

    # --- CALLBACKS DE VISORES Y GRÁFICOS ---
    @app.callback(
        Output('table-historicos', 'columns'), Output('table-historicos', 'data'), Output('table-historicos', 'style_data_conditional'),
        Input('btn-refresh-historicos', 'n_clicks'), Input('view-content', 'children'),
        State('store-active-game', 'data'), State('btn-nav-historicos', 'n_clicks')
    )
    def populate_historicos_table(refresh_clicks, _, game_id, nav_clicks):
        if (ctx.triggered_id != 'btn-refresh-historicos' and ctx.triggered_id != 'view-content') or not nav_clicks:
            return no_update, no_update, no_update
        from modules import database
        game_config = config.get_game_config(game_id)
        df = database.read_historico_from_db(game_config['paths']['db'])
        if df.empty: return [], [], []
        result_cols = [{'name': f'R{i}', 'id': f'r{i}'} for i in range(1, game_config['n'] + 1)]
        base_cols = [{'name': 'Concurso', 'id': 'concurso'}, {'name': 'Fecha', 'id': 'fecha'}]
        bolsa_cols = [{'name': 'Bolsa', 'id': 'bolsa', 'type': 'numeric', 'format': {'specifier': '$,.0f'}}] if 'bolsa' in df.columns and df['bolsa'].sum() > 0 else []
        omega_cols = [{'name': 'Clase Omega', 'id': 'es_omega_str'}, {'name': 'Omega Score', 'id': 'omega_score', 'type': 'numeric', 'format': {'specifier': '.4f'}}, {'name': 'Af. Cuartetos', 'id': 'afinidad_cuartetos'}, {'name': 'Af. Tercias', 'id': 'afinidad_tercias'}, {'name': 'Af. Pares', 'id': 'afinidad_pares'}, {'name': 'Analizar', 'id': 'analizar', 'presentation': 'markdown'}]
        columns = base_cols + result_cols + bolsa_cols + omega_cols
        df['es_omega_str'] = df.get('es_omega', pd.Series(0)).apply(lambda x: "Sí" if x == 1 else "No")
        df['fecha'] = pd.to_datetime(df['fecha']).dt.strftime('%d/%m/%Y')
        df['analizar'] = "[🔍]"
        df['id'] = df['concurso']
        styles = [{'if': {'column_id': 'es_omega_str', 'filter_query': '{es_omega_str} = "Sí"'}, 'backgroundColor': '#d4edda', 'color': '#155724'}, {'if': {'column_id': 'es_omega_str', 'filter_query': '{es_omega_str} = "No"'}, 'backgroundColor': '#f8d7da', 'color': '#721c24'}]
        if 'es_ganador' in df.columns: styles.append({'if': {'filter_query': '{es_ganador} = 1'}, 'backgroundColor': '#155724', 'color': 'white', 'fontWeight': 'bold'})
        return columns, df.to_dict('records'), styles

    # --- CALLBACKS DEL DECONSTRUCTOR DE AFINIDAD (RESTAURADOS Y CORREGIDOS) ---
    @app.callback(
        Output("modal-deconstructor", "is_open"),
        Output("modal-deconstructor-body", "children"),
        Input("table-historicos", "active_cell"),
        State("table-historicos", "data"),
        State('store-active-game', 'data'),
        prevent_initial_call=True,
    )
    def open_and_populate_deconstructor_modal(active_cell, table_data, game_id):
        if not active_cell or active_cell.get("column_id") != "analizar" or not table_data:
            return no_update, no_update

        from modules import omega_logic
        from dash import dash_table
        game_config = config.get_game_config(game_id)
        result_columns = game_config['data_source']['result_columns']

        # En Dash, cuando los datos se pasan a un componente, el 'id' se convierte en 'row_id'
        row_data = table_data[active_cell['row']]
        
        try:
            combination = [int(row_data[col]) for col in result_columns]
            omega_score = float(row_data.get("omega_score", 0.0))
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error al extraer datos de la fila para el deconstructor: {e}")
            return no_update, no_update
        
        data = omega_logic.deconstruct_affinity(combination, omega_score, game_config)

        if data.get("error"):
            body = dbc.Alert(data["error"], color="danger")
            return True, body

        header = f"Combinación: {data['combination']} | Omega Score: {data['omega_score']:.4f}"
        
        summary_q = f"Af. Cuartetos: {data['totals']['cuartetos']}"
        summary_t = f"Af. Tercias: {data['totals']['tercias']}"
        summary_p = f"Af. Pares: {data['totals']['pares']}"

        body_content = [
            html.H5(header),
            html.Hr(),
            dbc.Row([
                dbc.Col(html.P(summary_q), width=4),
                dbc.Col(html.P(summary_t), width=4),
                dbc.Col(html.P(summary_p), width=4),
            ], className="text-center mb-3"),
            dbc.Tabs([
                dbc.Tab(
                    dash_table.DataTable(
                        data=data["breakdown"].get("cuartetos", []),
                        columns=[{'name': 'Subsecuencia', 'id': 'subsequence'}, {'name': 'Frecuencia', 'id': 'frequency'}],
                        style_cell={'textAlign': 'center'}, style_header={'fontWeight': 'bold'}, page_size=15
                    ), label=f"Cuartetos ({len(data['breakdown'].get('cuartetos', []))})"
                ),
                dbc.Tab(
                    dash_table.DataTable(
                        data=data["breakdown"].get("tercias", []),
                        columns=[{'name': 'Subsecuencia', 'id': 'subsequence'}, {'name': 'Frecuencia', 'id': 'frequency'}],
                        style_cell={'textAlign': 'center'}, style_header={'fontWeight': 'bold'}, page_size=20
                    ), label=f"Tercias ({len(data['breakdown'].get('tercias', []))})"
                ),
                dbc.Tab(
                    dash_table.DataTable(
                        data=data["breakdown"].get("pares", []),
                        columns=[{'name': 'Subsecuencia', 'id': 'subsequence'}, {'name': 'Frecuencia', 'id': 'frequency'}],
                        style_cell={'textAlign': 'center'}, style_header={'fontWeight': 'bold'}, page_size=15
                    ), label=f"Pares ({len(data['breakdown'].get('pares', []))})"
                ),
            ])
        ]
        return True, body_content

    @app.callback(
        Output("modal-deconstructor", "is_open", allow_duplicate=True),
        Input("btn-close-modal", "n_clicks"),
        prevent_initial_call=True,
    )
    def close_deconstructor_modal(n_clicks):
        if n_clicks and n_clicks > 0:
            return False
        return no_update

    @app.callback(
        Output('graph-universo', 'figure'), Output('graph-historico', 'figure'), Output('graph-ganadores', 'figure'),
        Output('graph-scatter-score-bolsa', 'figure'), Output('graph-score-historico-dist', 'figure'), Output('graph-score-omega-class-dist', 'figure'),
        Output('graph-omega-score-trajectory', 'figure'),
        Input('btn-refresh-graficos', 'n_clicks'), State('store-active-game', 'data'),
        prevent_initial_call=True
    )
    def update_all_graphs(n_clicks, game_id):
        if not fue_un_clic_real('btn-refresh-graficos'): return (no_update,) * 7
        from modules import database, omega_logic
        game_config = config.get_game_config(game_id)
        
        # --- INICIO DE LA MODIFICACIÓN ---
        df_trajectory = database.read_omega_score_trajectory(game_config['paths']['db'])
        fig_trajectory = go.Figure()
        if not df_trajectory.empty:
            # --- INICIO DE LA CORRECCIÓN VISUAL ---
            # Mantenemos las líneas de los ganadores
            fig_trajectory.add_trace(go.Scatter(
                x=df_trajectory['concurso'], y=df_trajectory['original_omega_score'],
                mode='lines', name='Score Original (Ganador)', line=dict(color='rgba(231, 76, 60, 0.7)') # Rojo más visible
            ))
            fig_trajectory.add_trace(go.Scatter(
                x=df_trajectory['concurso'], y=df_trajectory['current_omega_score'],
                mode='lines', name='Score Actual (Ganador)', line=dict(color='rgba(52, 152, 219, 0.8)') # Azul más visible
            ))
            
            # Cambiamos la línea aleatoria a una línea sólida y de otro color
            if 'random_omega_score' in df_trajectory.columns:
                fig_trajectory.add_trace(go.Scatter(
                    x=df_trajectory['concurso'], y=df_trajectory['random_omega_score'],
                    mode='lines', name='Score Original (Aleatorio)', 
                    line=dict(color='rgba(46, 204, 113, 0.6)', width=1.5) # Verde sólido
                ))
            
            fig_trajectory.update_layout(
                title_x=0.5, template='simple_white', xaxis_title='Sorteo', yaxis_title='Omega Score',
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                shapes=[dict(type='line', y0=0, y1=0, x0=df_trajectory['concurso'].min(), x1=df_trajectory['concurso'].max(), line=dict(color='Black', width=1, dash='dot'))]
            )
        else:
            fig_trajectory.update_layout(title_text=f"Trayectoria de Scores<br>({game_config['display_name']})<br>(No generada)", title_x=0.5)
        # --- FIN DE LA MODIFICACIÓN ---
        
        # El resto de la función para los otros 6 gráficos no cambia
        # ...
        empty_fig = go.Figure().update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        total_omega = database.count_omega_class(game_config['paths']['db'])
        fig_universo = create_donut_chart([total_omega, game_config['total_combinations'] - total_omega], ["Omega", "Otras"], "Universo", game_config['display_name'])
        df_historico = database.read_historico_from_db(game_config['paths']['db'])
        if df_historico.empty: return fig_universo, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, fig_trajectory
        historico_counts = df_historico.get('es_omega', pd.Series(dtype=int)).value_counts()
        fig_historico = create_donut_chart([historico_counts.get(1, 0), historico_counts.get(0, 0)],["Omega", "No Omega"],"Históricos", game_config['display_name'])
        fig_ganadores, fig_scatter = go.Figure(), go.Figure()
        if 'es_ganador' in df_historico.columns and df_historico['es_ganador'].sum() > 0:
             df_ganadores = df_historico[df_historico["es_ganador"] == 1].copy()
             ganadores_counts = df_ganadores["es_omega"].value_counts()
             fig_ganadores = create_donut_chart([ganadores_counts.get(1, 0), ganadores_counts.get(0, 0)],["Omega", "No Omega"],"Sorteos con Premio", game_config['display_name'])
             df_ganadores["combinacion_str"] = (df_ganadores[game_config['data_source']['result_columns']].astype(str).agg("-".join, axis=1))
             fig_scatter = px.scatter(df_ganadores, x="omega_score", y="bolsa_ganada", color="omega_score", template="simple_white", title="Omega Score vs. Bolsa Ganada", labels={"omega_score": "Omega Score", "bolsa_ganada": "Bolsa Ganada (MXN)", "color": "Omega Score"}, hover_data=["concurso", "fecha", "combinacion_str"], color_continuous_scale=px.colors.sequential.Viridis)
             fig_scatter.update_layout(title_x=0.5)
        else:
             fig_ganadores.update_layout(title_text=f"Sorteos con Premio<br>({game_config['display_name']})<br>(No aplicable)", title_x=0.5)
             fig_scatter.update_layout(title_text=f"Omega Score vs. Bolsa<br>({game_config['display_name']})<br>(No aplicable)", title_x=0.5)
        df_historico['es_omega_str'] = df_historico.get('es_omega', pd.Series(0)).apply(lambda x: "Sí" if x == 1 else "No")
        fig_score_historico = px.histogram(df_historico, x="omega_score", color="es_omega_str", template='simple_white', title='Distribución Omega Score (Histórico)')
        df_omega_class = database.get_omega_class_scores(game_config['paths']['db'])
        fig_score_omega_class = go.Figure()
        if not df_omega_class.empty:
            loaded_thresholds = omega_logic.get_loaded_thresholds(game_config)
            weights, thresholds = game_config['omega_config']['score_weights'], loaded_thresholds
            s_q = ((df_omega_class['afinidad_cuartetos'] - thresholds.get('cuartetos',0)) / (thresholds.get('cuartetos',1) or 1)) * weights.get('cuartetos',0)
            s_t = ((df_omega_class['afinidad_tercias'] - thresholds.get('tercias',0)) / (thresholds.get('tercias',1) or 1)) * weights.get('tercias',0)
            s_p = ((df_omega_class['afinidad_pares'] - thresholds.get('pares',0)) / (thresholds.get('pares',1) or 1)) * weights.get('pares',0)
            df_omega_class['omega_score'] = s_q + s_t + s_p
            fig_score_omega_class = px.histogram(df_omega_class, x="omega_score", template='simple_white', title='Distribución Omega Score (Clase Omega)')
        else:
            fig_score_omega_class.update_layout(title_text=f"Distribución Score (Clase Omega)<br>({game_config['display_name']})<br>(No generada)", title_x=0.5)
            
        return fig_universo, fig_historico, fig_ganadores, fig_scatter, fig_score_historico, fig_score_omega_class, fig_trajectory

    # --- CALLBACK DE LA PESTAÑA DE OMEGA CERO ---
    @app.callback(
        Output("kpi-banda", "children"), Output("kpi-ciclo", "children"), Output("kpi-estabilidad", "children"),
        Output("kpi-candidatas", "children"), Output("table-omega-cero-candidatas", "data"), Output("table-omega-cero-candidatas", "columns"),
        Output("graph-omega-cero-dist", "figure"),
        Input("btn-calc-omega-cero", "n_clicks"),
        State('store-active-game', 'data'),
        prevent_initial_call=True
    )
    def update_omega_cero_dashboard(n_clicks, game_id):
        if not fue_un_clic_real('btn-calc-omega-cero'):
            return (no_update,) * 7

        from modules import omega_cero_logic
        game_config = config.get_game_config(game_id)
        
        df_candidatas, metrics = omega_cero_logic.get_omega_cero_candidates(game_config)

        if not metrics:
            alert = dbc.Alert("Datos de métricas no encontrados. Ejecute el script 'generate_omega_score_trajectory.py' primero.", color="warning")
            return alert, alert, alert, alert, [], [], go.Figure()

        banda = f"[{metrics.get('banda_normal_inferior', 0):.2f}, {metrics.get('banda_normal_superior', 0):.2f}]"
        ciclo = f"{metrics.get('periodo_medio_ciclo', 0):.1f} sorteos"
        estabilidad = f"{metrics.get('periodo_medio_estabilidad', 0):.1f} sorteos"
        num_candidatas = f"{metrics.get('numero_candidatas', 0):,}"
        columns = [{"name": i.replace('_', ' ').title(), "id": i} for i in df_candidatas.columns]
        data = df_candidatas.to_dict('records')
        
        fig = go.Figure()
        if not df_candidatas.empty:
            fig = px.histogram(df_candidatas, x="simulated_original_score", nbins=50, title="Distribución de Scores Simulados (Candidatas)")
            fig.add_vline(x=metrics['banda_normal_inferior'], line_width=2, line_dash="dash", line_color="green")
            fig.add_vline(x=metrics['banda_normal_superior'], line_width=2, line_dash="dash", line_color="green")
            fig.update_layout(template='simple_white', xaxis_title="Score Original Simulado")
        else:
            fig.update_layout(title_text="No se encontraron candidatas", title_x=0.5)

        return banda, ciclo, estabilidad, num_candidatas, data, columns, fig
    
    # --- CALLBACK DE LA PESTAÑA DE MONITOREO ---
    @app.callback(
        Output("collapse-dist-panel", "is_open"),
        Input("btn-collapse-dist", "n_clicks"), State("collapse-dist-panel", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_collapse_dist_panel(n, is_open):
        if n: return not is_open
        return is_open    

    @app.callback(
        Output("graph-freq-dist-trajectory", "figure"), Output("graph-affinity-trajectory", "figure"),
        Output("graph-freq-trajectory", "figure"), Output("graph-threshold-trajectory", "figure"),
        Output("graph-freq-histogram", "figure"), Output("graph-affinity-histogram", "figure"),
        Input("btn-refresh-monitoring", "n_clicks"), State('store-active-game', 'data'),
        prevent_initial_call=True,
    )
    def update_monitoring_graphs(n_clicks, game_id):
        if not fue_un_clic_real('btn-refresh-monitoring'): return (no_update,) * 6
        from modules import database, omega_logic; from plotly.subplots import make_subplots
        game_config = config.get_game_config(game_id); db_path = game_config['paths']['db']
        df_freq_dist = database.read_trajectory_data(db_path, 'freq_dist_trayectoria')
        df_affinity = database.read_trajectory_data(db_path, 'afinidades_trayectoria')
        df_freq_count = database.read_trajectory_data(db_path, 'frecuencias_trayectoria')
        df_threshold = database.read_trajectory_data(db_path, 'umbrales_trayectoria')
        empty_fig = go.Figure().update_layout(title_text="No hay datos. Ejecute 'generate_trajectory.py'", title_x=0.5, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        fig_freq_dist = empty_fig
        if not df_freq_dist.empty:
            fig_freq_dist = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Cuartetos", "Tercias", "Pares"))
            for i, level in enumerate(['cuartetos', 'tercias', 'pares']):
                row = i + 1
                fig_freq_dist.add_trace(go.Scatter(x=df_freq_dist["ultimo_concurso_usado"], y=df_freq_dist[f"freq_{level}_max"], mode='lines', line=dict(width=0), showlegend=False), row=row, col=1)
                fig_freq_dist.add_trace(go.Scatter(x=df_freq_dist["ultimo_concurso_usado"], y=df_freq_dist[f"freq_{level}_min"], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(214,39,40,0.2)'), row=row, col=1)
                fig_freq_dist.add_trace(go.Scatter(x=df_freq_dist["ultimo_concurso_usado"], y=df_freq_dist[f"freq_{level}_media"], mode='lines', line=dict(color='#d62728', width=2), name='Media'), row=row, col=1)
            fig_freq_dist.update_layout(height=700, template="simple_white", showlegend=False)
        fig_affinity = empty_fig
        if not df_affinity.empty:
            fig_affinity = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Cuartetos", "Tercias", "Pares"))
            for i, level in enumerate(['cuartetos', 'tercias', 'pares']):
                row = i + 1
                fig_affinity.add_trace(go.Scatter(x=df_affinity["ultimo_concurso_usado"], y=df_affinity[f"afin_{level}_max"], mode='lines', line=dict(width=0), showlegend=False), row=row, col=1)
                fig_affinity.add_trace(go.Scatter(x=df_affinity["ultimo_concurso_usado"], y=df_affinity[f"afin_{level}_min"], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(31,119,180,0.2)'), row=row, col=1)
                fig_affinity.add_trace(go.Scatter(x=df_affinity["ultimo_concurso_usado"], y=df_affinity[f"afin_{level}_media"], mode='lines', line=dict(color='#1f77b4', width=2)), row=row, col=1)
            fig_affinity.update_layout(height=700, template="simple_white", showlegend=False)
        fig_freq_growth = empty_fig
        if not df_freq_count.empty:
            fig_freq_growth = px.line(df_freq_count, x="ultimo_concurso_usado", y=["total_pares_unicos", "total_tercias_unicas", "total_cuartetos_unicos"], template="simple_white", labels={"value": "Conteo Único", "ultimo_concurso_usado": "Sorteo Histórico"})
            fig_freq_growth.update_layout(legend_title_text='Nivel')
        fig_threshold = empty_fig
        if not df_threshold.empty:
            fig_threshold = px.line(df_threshold, x="ultimo_concurso_usado", y=["umbral_pares", "umbral_tercias", "umbral_cuartetos"], template="simple_white", labels={"value": "Valor del Umbral", "ultimo_concurso_usado": "Sorteo Histórico"})
            fig_threshold.update_layout(legend_title_text='Afinidad')
        fig_freq_hist, fig_affinity_hist = empty_fig, empty_fig
        final_freqs = omega_logic.get_frequencies(game_config)
        if final_freqs:
            hist_data = [{"Frecuencia": v, "Nivel": l.capitalize()} for l in ["pares", "tercias", "cuartetos"] if final_freqs.get(l) for v in final_freqs[l].values()]
            if hist_data: df_hist = pd.DataFrame(hist_data); fig_freq_hist = px.histogram(df_hist, x="Frecuencia", color="Nivel", barmode="overlay", histnorm="percent", template="simple_white"); fig_freq_hist.update_traces(opacity=0.75)
        df_historico = database.read_historico_from_db(db_path)
        if not df_historico.empty and 'afinidad_pares' in df_historico.columns:
            affinity_data = [{"Afinidad": v, "Nivel": l.capitalize()} for l in ["pares", "tercias", "cuartetos"] for v in df_historico[f"afinidad_{l}"]]
            df_aff_hist = pd.DataFrame(affinity_data); fig_affinity_hist = px.histogram(df_aff_hist, x="Afinidad", color="Nivel", barmode="overlay", histnorm="percent", template="simple_white"); fig_affinity_hist.update_traces(opacity=0.75)
        return fig_freq_dist, fig_affinity, fig_freq_growth, fig_threshold, fig_freq_hist, fig_affinity_hist
    
    # --- INICIAR SERVIDOR ---
    def open_browser(): webbrowser.open_new_tab("http://127.0.0.1:8050")
    if os.environ.get("DOCKER_ENV") is None: Timer(2, open_browser).start()
    app.run(debug=False, host="0.0.0.0", port="8050")