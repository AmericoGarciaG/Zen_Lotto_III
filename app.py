import time
start_total = time.perf_counter()

import logging
from utils.logger_config import setup_logger
from utils import state_manager # Importamos el gestor de estado

setup_logger()
logger = logging.getLogger(__name__)

logger.info("="*50)
logger.info("INICIO DE LA APLICACIÓN ZEN LOTTO (MODO LAZY-IMPORT)")
logger.info("="*50)

start_imports = time.perf_counter()
logger.info("Importando librerías esenciales (Dash)...")
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, ctx, State, no_update
end_imports = time.perf_counter()
logger.info(f"--- TIEMPO DE IMPORTS ESENCIALES: {end_imports - start_imports:.4f} segundos ---")

logger.info("Inicializando la aplicación Dash...")
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True
)
server = app.server
logger.info("Aplicación Dash inicializada.")

from modules.presentation import create_layout
logger.info("Creando el layout de la aplicación...")
app.layout = create_layout()
logger.info("Layout creado.")

logger.info("Registrando callbacks de la aplicación...")

# --- Función de Ayuda para Callbacks ---
def fue_un_clic_real(button_id):
    """Verifica si un callback fue disparado por un clic real del usuario."""
    if not ctx.triggered:
        return False
    triggered_component_id = ctx.triggered[0]['prop_id'].split('.')[0]
    n_clicks = ctx.triggered[0]['value']
    return triggered_component_id == button_id and isinstance(n_clicks, int) and n_clicks > 0

# --- Callbacks de Navegación ---
@app.callback(
    Output("view-content", "children"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
)
def render_view_content(gen_clicks, conf_clicks):
    from modules.presentation import create_generador_view, create_configuracion_view
    triggered_id = ctx.triggered_id or "btn-nav-generador"
    if triggered_id == "btn-nav-configuracion":
        return create_configuracion_view()
    return create_generador_view()

@app.callback(
    Output("btn-nav-generador", "className"),
    Output("btn-nav-configuracion", "className"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
)
def update_nav_buttons_style(gen_clicks, conf_clicks):
    triggered_id = ctx.triggered_id or "btn-nav-generador"
    base_class = "nav-button"
    gen_class = base_class
    conf_class = base_class
    if triggered_id == "btn-nav-generador": gen_class += " active"
    elif triggered_id == "btn-nav-configuracion": conf_class += " active"
    else: gen_class += " active"
    return gen_class, conf_class

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

    logger.info("Callback 'handle_historical_load' disparado por clic real.")
    
    state = state_manager.get_state()
    last_concurso_in_db = state.get("last_concurso_in_db", 0)
    
    df_new, _, load_success = run_historical_load(last_concurso=last_concurso_in_db)
    
    # --- INICIO DE LA CORRECCIÓN ---
    # Comprobamos explícitamente si la carga falló O si el DataFrame es None
    if not load_success or df_new is None:
        return dbc.Alert("Error durante la carga o DataFrame nulo. Revise logs.", color="danger", duration=5000)
    
    save_success, save_message = save_historico_to_db(df_new, mode='append')
    
    if not save_success:
        return dbc.Alert(save_message, color="danger", duration=5000)
    
    # Ahora, esta comprobación es 100% segura
    if save_success and not df_new.empty:
        state["last_concurso_in_db"] = int(df_new['concurso'].max())
        state_manager.save_state(state)
        
    return dbc.Alert(save_message, color="success", duration=5000)
    # --- FIN DE LA CORRECCIÓN ---

@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-gen-omega", "n_clicks"),
    prevent_initial_call=True
)
def handle_omega_class_generation(n_clicks):
    if not fue_un_clic_real('btn-gen-omega'): return no_update
    from modules.omega_logic import calculate_and_save_frequencies
    logger.info("Callback 'handle_omega_class_generation' disparado por clic real.")
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
    logger.info("Callback 'handle_pregenerate_omega' disparado por clic real.")
    start_time = time.time()
    success, message = pregenerate_omega_class()
    end_time = time.time()
    total_time = end_time - start_time
    full_message = f"{message} (Tiempo de ejecución: {total_time:.2f} segundos)"
    color = "success" if success else "danger"
    return dbc.Alert(full_message, color=color)

# --- Callbacks del Generador ---
@app.callback(
    [Output(f"num-input-{i}", "value") for i in range(6)] + 
    [Output("notification-container", "children", allow_duplicate=True)],
    Input("btn-generar", "n_clicks"),
    prevent_initial_call=True
)
def handle_generate_omega(n_clicks):
    if not fue_un_clic_real('btn-generar'): return [no_update] * 7
    from modules.database import get_random_omega_combination
    logger.info("Callback 'handle_generate_omega' disparado por clic real.")
    omega_combination = get_random_omega_combination()
    if omega_combination:
        return omega_combination + [None]
    else:
        logger.warning("No se pudo generar combinación. ¿Falta pre-generar Clase Omega?")
        error_message = dbc.Alert("Error: La Clase Omega no ha sido generada. Ve a Configuración y ejecútala.", color="warning", duration=5000)
        return [no_update] * 6 + [error_message]


logger.info("Callbacks registrados.")
end_total = time.perf_counter()
logger.info(f"--- TIEMPO TOTAL DE ARRANQUE DEL SCRIPT: {end_total - start_total:.4f} segundos ---")

if __name__ == "__main__":
    logger.info("Iniciando servidor (Debug OFF).")
    app.run(debug=False, port=8050)