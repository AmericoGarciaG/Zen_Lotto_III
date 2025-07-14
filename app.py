import time
start_total = time.perf_counter()

import logging
from utils.logger_config import setup_logger
from utils import state_manager

setup_logger()
logger = logging.getLogger(__name__)

logger.info("="*50)
logger.info("INICIO DE LA APLICACIÓN ZEN LOTTO (MODO DEPURACIÓN CONTROLADA)")
logger.info("="*50)

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, ctx, State, no_update

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
    if not ctx.triggered: return False
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
    return dbc.Alert(full_message, color=color, duration=10000)

# --- CALLBACK PARA EL BOTÓN "GENERAR OMEGA / AJUSTAR" ---
@app.callback(
    [Output(f"num-input-{i}", "value") for i in range(6)] + 
    [Output("notification-container", "children", allow_duplicate=True)],
    Input("btn-generar", "n_clicks"),
    [State(f"num-input-{i}", "value") for i in range(6)], # Leemos el estado de los inputs
    prevent_initial_call=True
)
def handle_generate_omega(n_clicks, *num_inputs):
    # Primero, la guarda de seguridad para evitar disparos automáticos
    if not fue_un_clic_real('btn-generar'):
        return [no_update] * 7

    # Importaciones perezosas
    from modules.database import get_random_omega_combination
    from modules.omega_logic import evaluate_combination, adjust_to_omega, get_frequencies

    logger.info(f"Callback 'GENERAR/AJUSTAR' disparado. Inputs: {num_inputs}")

    # --- Lógica Condicional Principal ---

    # Escenario 1: Los recuadros están vacíos. Generar una combinación Omega aleatoria.
    if all(num is None or num == '' for num in num_inputs):
        logger.info("Modo: Generación aleatoria (inputs vacíos).")
        omega_combination = get_random_omega_combination()
        if omega_combination:
            return omega_combination + [None] # Combinación + sin mensaje
        else:
            error_msg = dbc.Alert("Error: No se pudo generar una combinación. ¿Falta pre-generar la Clase Omega?", color="warning", duration=5000)
            return [no_update] * 6 + [error_msg]

    # Escenario 2: Los recuadros tienen números. Intentar analizar y ajustar.
    else:
        logger.info("Modo: Análisis y ajuste (inputs con datos).")
        
        # 2.1. Validar la estructura de la combinación del usuario
        if any(num is None or num == '' for num in num_inputs):
            return [no_update] * 6 + [dbc.Alert("Por favor, ingrese 6 números para ajustar.", color="warning", duration=4000)]
        try:
            user_combo = [int(num) for num in num_inputs]
            if len(set(user_combo)) != 6:
                return [no_update] * 6 + [dbc.Alert("Los 6 números deben ser únicos para ajustar.", color="warning", duration=4000)]
        except (ValueError, TypeError):
            return [no_update] * 6 + [dbc.Alert("Por favor, ingrese solo números válidos para ajustar.", color="warning", duration=4000)]

        # 2.2. Evaluar si la combinación ya es Omega
        freqs = get_frequencies()
        if freqs is None:
            return [no_update] * 6 + [dbc.Alert("Error: Frecuencias no generadas. Ve a Configuración.", color="danger")]
            
        eval_result = evaluate_combination(user_combo, freqs)
        if eval_result.get("esOmega"):
            success_msg = dbc.Alert(f"¡Tu combinación {user_combo} ya es de Clase Omega! No necesita ajuste.", color="success", duration=6000)
            return [no_update] * 6 + [success_msg]

        # 2.3. Si no es Omega, buscar el ajuste
        logger.info(f"La combinación {user_combo} no es Omega. Buscando ajuste...")
        adjusted_combo, matches = adjust_to_omega(user_combo)
        
        if adjusted_combo:
            # Creamos un mensaje informativo para el usuario
            changed_numbers = 6 - matches
            ajuste_msg = dbc.Alert(
                f"¡Combinación ajustada! Se mantuvieron {matches} de tus números y se cambiaron {changed_numbers} para que sea Omega.",
                color="info",
                duration=8000
            )
            # Devolvemos la nueva combinación y el mensaje
            return adjusted_combo + [ajuste_msg]
        else:
            # Si no se encontró ningún ajuste razonable
            no_ajuste_msg = dbc.Alert(
                f"No se encontró un ajuste cercano para tu combinación. Intenta con otros números o genera una aleatoria.",
                color="danger",
                duration=8000
            )
            return [no_update] * 6 + [no_ajuste_msg]

# --- BLOQUE REINTRODUCIDO Y CORREGIDO ---
@app.callback(
    Output("notification-container", "children", allow_duplicate=True),
    Input("btn-analizar", "n_clicks"),
    [State(f"num-input-{i}", "value") for i in range(6)], # Pasa 6 argumentos de State
    prevent_initial_call=True
)
def handle_analizar_combinacion(n_clicks, *num_inputs): # Acepta 1 + 6 argumentos
    """Evalúa la combinación ingresada por el usuario."""
    # El asterisco en *num_inputs agrupa los 6 argumentos de State en una sola tupla.
    
    if not fue_un_clic_real('btn-analizar'):
        return no_update

    from modules.omega_logic import get_frequencies, evaluate_combination
    logger.info(f"Callback 'handle_analizar_combinacion' disparado. Inputs: {num_inputs}")
    
    # 1. Validación de la entrada del usuario
    if any(num is None or num == '' for num in num_inputs):
        return dbc.Alert("Por favor, ingrese 6 números para analizar.", color="warning", duration=5000)

    try:
        # num_inputs ya es una tupla, la convertimos a lista de enteros
        combination = [int(num) for num in num_inputs]
        if len(set(combination)) != 6:
            return dbc.Alert("Los 6 números deben ser únicos.", color="warning", duration=5000)
    except (ValueError, TypeError):
        return dbc.Alert("Por favor, ingrese solo números válidos.", color="warning", duration=5000)
    
    # 2. Obtención de datos necesarios
    freqs = get_frequencies()
    if freqs is None:
        return dbc.Alert("Error: Las frecuencias no han sido generadas. Ve a Configuración.", color="danger")
        
    # 3. Evaluación de la combinación
    result = evaluate_combination(combination, freqs)
    
    # 4. Construcción del mensaje de respuesta (a prueba de Pylance)
    # Verificación explícita de que 'result' es un diccionario
    if not isinstance(result, dict):
        return dbc.Alert("Ocurrió un error inesperado durante la evaluación.", color="danger")
    # Verificación de la clave de error
    if result.get("error"):
        return dbc.Alert(result["error"], color="danger")

    # A partir de aquí, Pylance sabe que 'result' es un diccionario de éxito
    es_omega = result.get("esOmega", False)
    title = "¡Combinación de Clase Omega! ✅" if es_omega else "Combinación No-Omega ❌"
    color = "success" if es_omega else "danger"
    combinacion_ordenada = result.get("combinacion", [])
    
    # Verificación explícita para la clave 'criterios'
    criterios = result.get("criterios", {})
    if not isinstance(criterios, dict):
         return dbc.Alert("Faltan datos de criterios en el resultado.", color="danger")

    # Ahora Pylance sabe que 'criterios' es un dict, por lo que .get() es seguro.
    pares = criterios.get("pares", {})
    tercias = criterios.get("tercias", {})
    cuartetos = criterios.get("cuartetos", {})
    
    body_content = [
        html.H4(title, className="alert-heading"),
        html.P(f"Tu combinación: {combinacion_ordenada}"),
        html.Hr(),
        html.P("Detalles de la evaluación:", className="mb-0"),
        html.Ul([
            html.Li(f"Afinidad de Pares: {pares.get('score', 'N/A')} / {pares.get('umbral', 'N/A')} {'✅' if pares.get('cumple') else '❌'}"),
            html.Li(f"Afinidad de Tercias: {tercias.get('score', 'N/A')} / {tercias.get('umbral', 'N/A')} {'✅' if tercias.get('cumple') else '❌'}"),
            html.Li(f"Afinidad de Cuartetos: {cuartetos.get('score', 'N/A')} / {cuartetos.get('umbral', 'N/A')} {'✅' if cuartetos.get('cumple') else '❌'}")
        ])
    ]
    
    # 5. Punto de retorno único
    return dbc.Alert(body_content, color=color, duration=15000)


logger.info("Callbacks registrados.")
end_total = time.perf_counter()
logger.info(f"--- TIEMPO TOTAL DE ARRANQUE DEL SCRIPT: {end_total - start_total:.4f} segundos ---")


if __name__ == "__main__":
    logger.info("Iniciando servidor (Debug OFF).")
    app.run(debug=False, port=8050)