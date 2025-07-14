import time
start_total = time.perf_counter()

import logging
from utils.logger_config import setup_logger
from utils import state_manager

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

# --- Callbacks de Navegación ---
@app.callback(
    Output("view-content", "children"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
    Input("btn-nav-registros", "n_clicks"),
)
def render_view_content(gen_clicks, conf_clicks, reg_clicks):
    from modules.presentation import create_generador_view, create_configuracion_view, create_registros_view
    triggered_id = ctx.triggered_id or "btn-nav-generador"
    if triggered_id == "btn-nav-configuracion":
        return create_configuracion_view()
    elif triggered_id == "btn-nav-registros":
        return create_registros_view()
    return create_generador_view()

@app.callback(
    Output("btn-nav-generador", "className"),
    Output("btn-nav-configuracion", "className"),
    Output("btn-nav-registros", "className"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
    Input("btn-nav-registros", "n_clicks"),
)
def update_nav_buttons_style(gen_clicks, conf_clicks, reg_clicks):
    triggered_id = ctx.triggered_id or "btn-nav-generador"
    base_class = "nav-button"
    gen_class, conf_class, reg_class = base_class, base_class, base_class
    if triggered_id == "btn-nav-generador": gen_class += " active"
    elif triggered_id == "btn-nav-configuracion": conf_class += " active"
    elif triggered_id == "btn-nav-registros": reg_class += " active"
    else: gen_class += " active"
    return gen_class, conf_class, reg_class

# --- Callbacks de Configuración ---
@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-gen-historico", "n_clicks"),
    prevent_initial_call=True
)
def handle_historical_load(n_clicks):
    if not fue_un_clic_real('btn-gen-historico'): return no_update
    from modules.data_ingestion import run_historical_load
    from modules.database import save_historico_to_db
    state = state_manager.get_state()
    last_concurso_in_db = state.get("last_concurso_in_db", 0)
    df_new, _, load_success = run_historical_load(last_concurso=last_concurso_in_db)
    if not load_success or df_new is None: return dbc.Alert("Error durante la carga. Revise logs.", color="danger", duration=5000)
    save_success, save_message = save_historico_to_db(df_new, mode='append')
    if not save_success: return dbc.Alert(save_message, color="danger", duration=5000)
    if save_success and not df_new.empty:
        state["last_concurso_in_db"] = int(df_new['concurso'].max())
        state_manager.save_state(state)
    return dbc.Alert(save_message, color="success", duration=5000)

@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-gen-omega", "n_clicks"),
    prevent_initial_call=True
)
def handle_omega_class_generation(n_clicks):
    if not fue_un_clic_real('btn-gen-omega'): return no_update
    from modules.omega_logic import calculate_and_save_frequencies
    success, message = calculate_and_save_frequencies()
    color = "success" if success else "danger"
    return dbc.Alert(message, color=color, duration=5000)

@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-pregen-omega", "n_clicks"),
    prevent_initial_call=True
)
def handle_pregenerate_omega(n_clicks):
    if not fue_un_clic_real('btn-pregen-omega'): return no_update
    from modules.omega_logic import pregenerate_omega_class
    start_time = time.time()
    success, message = pregenerate_omega_class()
    end_time = time.time()
    total_time = end_time - start_time
    full_message = f"{message} (Tiempo de ejecución: {total_time:.2f} segundos)"
    color = "success" if success else "danger"
    return dbc.Alert(full_message, color=color, duration=10000)

# --- Callbacks del Generador ---
@app.callback(
    [Output(f"num-input-{i}", "value", allow_duplicate=True) for i in range(6)] + 
    [Output("notification-container", "children", allow_duplicate=True)] +
    [Output('store-validated-omega', 'data', allow_duplicate=True)],
    Input("btn-generar", "n_clicks"),
    [State(f"num-input-{i}", "value") for i in range(6)],
    prevent_initial_call=True
)
def handle_generate_omega(n_clicks, *num_inputs):
    if not fue_un_clic_real('btn-generar'): return [no_update] * 8
    from modules.database import get_random_omega_combination
    from modules.omega_logic import evaluate_combination, adjust_to_omega, get_frequencies
    if all(num is None or num == '' for num in num_inputs):
        omega_combination = get_random_omega_combination()
        if omega_combination: return omega_combination + [None, omega_combination]
        else:
            error_msg = dbc.Alert("Error: No se pudo generar una combinación.", color="warning", duration=5000)
            return [no_update] * 6 + [error_msg, None]
    else:
        if any(num is None or num == '' for num in num_inputs): return [no_update] * 7 + [None]
        try:
            user_combo = sorted([int(num) for num in num_inputs])
            if len(set(user_combo)) != 6: return [no_update] * 7 + [None]
        except (ValueError, TypeError): return [no_update] * 7 + [None]
        freqs = get_frequencies()
        if freqs is None: return [no_update] * 7 + [None]
        eval_result = evaluate_combination(user_combo, freqs)
        if eval_result.get("esOmega"):
            msg = dbc.Alert(f"¡Tu combinación {user_combo} ya es de Clase Omega!", color="success", duration=6000)
            return [no_update] * 6 + [msg, user_combo]
        adjusted_combo, matches = adjust_to_omega(user_combo)
        if adjusted_combo:
            msg = dbc.Alert(f"¡Ajuste exitoso! Se mantuvieron {matches} de tus números.", color="info", duration=8000)
            return adjusted_combo + [msg, adjusted_combo]
        else:
            msg = dbc.Alert("No se encontró un ajuste cercano.", color="danger", duration=8000)
            return [no_update] * 6 + [msg, None]

@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Output('store-validated-omega', 'data', allow_duplicate=True),
    Input("btn-analizar", "n_clicks"),
    [State(f"num-input-{i}", "value") for i in range(6)],
    prevent_initial_call=True
)
def handle_analizar_combinacion(n_clicks, *num_inputs):
    if not fue_un_clic_real('btn-analizar'): return no_update, no_update
    from modules.omega_logic import get_frequencies, evaluate_combination
    try:
        if any(num is None or num == '' for num in num_inputs): raise ValueError("Por favor, ingrese 6 números.")
        combination = sorted([int(num) for num in num_inputs])
        if len(set(combination)) != 6: raise ValueError("Los 6 números deben ser únicos.")
    except (ValueError, TypeError) as e: return dbc.Alert(str(e), color="warning", duration=4000), None
    freqs = get_frequencies()
    if freqs is None: return dbc.Alert("Frecuencias no generadas.", color="danger"), None
    result = evaluate_combination(combination, freqs)
    if not isinstance(result, dict) or result.get("error"):
        error_msg = result.get("error") if isinstance(result, dict) else "Error en evaluación."
        return dbc.Alert(error_msg, color="danger"), None
    es_omega = result.get("esOmega", False)
    title = "¡Clase Omega! ✅" if es_omega else "No-Omega ❌"
    color = "success" if es_omega else "danger"
    combinacion_ordenada, criterios = result.get("combinacion", []), result.get("criterios", {})
    if not isinstance(criterios, dict): return dbc.Alert("Faltan datos de criterios.", color="danger"), None
    pares, tercias, cuartetos = criterios.get("pares", {}), criterios.get("tercias", {}), criterios.get("cuartetos", {})
    body_content = [
        html.H4(title, className="alert-heading"), html.P(f"Tu combinación: {combinacion_ordenada}"), html.Hr(),
        html.Ul([
            html.Li(f"Pares: {pares.get('score')} / {pares.get('umbral')} {'✅' if pares.get('cumple') else '❌'}"),
            html.Li(f"Tercias: {tercias.get('score')} / {tercias.get('umbral')} {'✅' if tercias.get('cumple') else '❌'}"),
            html.Li(f"Cuartetos: {cuartetos.get('score')} / {cuartetos.get('umbral')} {'✅' if cuartetos.get('cumple') else '❌'}")
        ])
    ]
    validated_combo_for_store = combination if es_omega else None
    return dbc.Alert(body_content, color=color, duration=10000), validated_combo_for_store

@app.callback(
    [Output(f"num-input-{i}", "value", allow_duplicate=True) for i in range(6)] +
    [Output('store-validated-omega', 'data', allow_duplicate=True)],
    Input("btn-clear-inputs", "n_clicks"),
    prevent_initial_call=True
)
def handle_clear_inputs(n_clicks):
    if not fue_un_clic_real('btn-clear-inputs'): return [no_update] * 7
    return [None] * 6 + [None]

@app.callback(
    Output('input-nombre', 'disabled'),
    Output('input-movil', 'disabled'),
    Output('btn-registrar', 'disabled'),
    Input('store-validated-omega', 'data'),
    [Input(f"num-input-{i}", "value") for i in range(6)]
)
def control_registration_fields(validated_omega, *current_inputs_tuple):
    try: current_inputs = sorted([int(i) for i in current_inputs_tuple if i is not None and i != ''])
    except (ValueError, TypeError): current_inputs = []
    if validated_omega and len(current_inputs) == 6 and sorted(validated_omega) == current_inputs: return False, False, False
    return True, True, True

# --- NUEVOS CALLBACKS PARA REGISTRO ---
@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-registrar", "n_clicks"),
    [State('store-validated-omega', 'data'), State('input-nombre', 'value'), State('input-movil', 'value')],
    prevent_initial_call=True
)
def handle_register_omega(n_clicks, validated_omega, nombre, movil):
    if not fue_un_clic_real('btn-registrar'): return no_update
    from modules.database import register_omega_combination
    if not validated_omega: return dbc.Alert("No hay una combinación Omega válida para registrar.", color="warning", duration=4000)
    if not nombre or not movil: return dbc.Alert("El nombre y el número de móvil son obligatorios.", color="warning", duration=4000)
    success, message = register_omega_combination(validated_omega, nombre.strip(), movil.strip())
    color = "success" if success else "danger"
    return dbc.Alert(message, color=color, duration=5000)

@app.callback(
    Output('table-registros', 'data'),
    Input('btn-refresh-registros', 'n_clicks'),
    Input('btn-nav-registros', 'n_clicks')
)
def populate_registros_table(refresh_clicks, nav_clicks):
    from modules.database import get_all_registrations
    # Solo se ejecuta si el trigger es uno de los botones de entrada
    if ctx.triggered_id in ['btn-refresh-registros', 'btn-nav-registros']:
        logger.info("Poblando/refrescando la tabla de registros Omega.")
        df = get_all_registrations()
        return df.to_dict('records')
    return no_update

if __name__ == "__main__":
    logger.info("Iniciando servidor (Debug OFF).")
    app.run(debug=False, port=8050)