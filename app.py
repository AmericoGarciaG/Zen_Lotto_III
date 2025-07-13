import time
start_total = time.perf_counter()

import logging
from utils.logger_config import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

logger.info("="*50)
logger.info("INICIO DE LA APLICACIÓN ZEN LOTTO (MODO LAZY-IMPORT)")
logger.info("="*50)

start_imports = time.perf_counter()
logger.info("Importando librerías esenciales (Dash)...")
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, ctx
# ¡NOTA! Ya no importamos nuestros módulos aquí.
end_imports = time.perf_counter()
logger.info(f"--- TIEMPO DE IMPORTS ESENCIALES: {end_imports - start_imports:.4f} segundos ---")

# --- INICIALIZACIÓN DE LA APP ---
logger.info("Inicializando la aplicación Dash...")
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True
)
server = app.server
logger.info("Aplicación Dash inicializada.")

# --- LAYOUT ---
# Necesitamos importar solo el módulo de presentación aquí.
# Esto debería ser rápido, ya que presentation.py no importa pandas.
from modules.presentation import create_layout
logger.info("Creando el layout de la aplicación...")
app.layout = create_layout()
logger.info("Layout creado.")

# --- CALLBACKS ---
logger.info("Registrando callbacks de la aplicación...")

@app.callback(
    Output("view-content", "children"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
)
def render_view_content(gen_clicks, conf_clicks):
    from modules.presentation import create_generador_view, create_configuracion_view
    
    triggered_id = ctx.triggered_id or "btn-nav-generador"
    logger.info(f"Callback 'render_view_content' disparado por: {triggered_id}")
    if triggered_id == "btn-nav-configuracion":
        return create_configuracion_view()
    return create_generador_view()

# ... (El callback de los estilos de navegación no cambia) ...
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
    return gen_class, conf_class


@app.callback(
    Output("config-feedback-message", "children"),
    Input("btn-gen-historico", "n_clicks"),
    prevent_initial_call=True
)
def handle_historical_load(n_clicks):
    # --- IMPORTACIONES PEREZOSAS ---
    from modules.data_ingestion import run_historical_load
    from modules.database import save_historico_to_db, get_last_concurso_from_db
    # -----------------------------
    
    logger.info("Callback 'handle_historical_load' disparado.")
    last_concurso_in_db = get_last_concurso_from_db()
    df_new, _, load_success = run_historical_load(last_concurso=last_concurso_in_db)
    
    if not load_success:
        return dbc.Alert("Error durante la carga de datos. Revise los logs.", color="danger")

    save_mode = 'append'
    save_success, save_message = save_historico_to_db(df_new, mode=save_mode)

    if not save_success:
        return dbc.Alert(save_message, color="danger")
    
    return dbc.Alert(save_message, color="success")

@app.callback(
    Output("config-feedback-message", "children", allow_duplicate=True),
    Input("btn-gen-omega", "n_clicks"),
    prevent_initial_call=True
)
def handle_omega_class_generation(n_clicks):
    # --- IMPORTACIÓN PEREZOSA ---
    from modules.omega_logic import calculate_and_save_frequencies
    # --------------------------

    logger.info("Callback 'handle_omega_class_generation' disparado.")
    success, message = calculate_and_save_frequencies()
    color = "success" if success else "danger"
    return dbc.Alert(message, color=color)

logger.info("Callbacks registrados.")
end_total = time.perf_counter()
logger.info(f"--- TIEMPO TOTAL DE ARRANQUE DEL SCRIPT: {end_total - start_total:.4f} segundos ---")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    logger.info("Iniciando servidor de desarrollo de Dash.")
    # Intenta deshabilitar el reloader para confirmar la teoría
    app.run(debug=True, port=8050, use_reloader=False)