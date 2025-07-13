print("--- Ejecutando app.py ---")

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, ctx

print("--- Importando módulos locales ---")
# --- IMPORTACIONES ---
from modules.data_ingestion import run_historical_load
from modules.presentation import create_layout, create_generador_view, create_configuracion_view
from modules.database import save_historico_to_db
from modules.omega_logic import calculate_and_save_frequencies
print("--- Módulos locales importados ---")
# --- INICIALIZACIÓN DE LA APP ---
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.LUX, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True # Corrección para manejar layouts dinámicos
)
server = app.server

# --- LAYOUT DE LA APLICACIÓN ---
app.layout = create_layout()

# --- CALLBACKS ---
print("--- Registrando callbacks ---")

# Callback para actualizar el contenido de la vista principal
@app.callback(
    Output("view-content", "children"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
)
def render_view_content(gen_clicks, conf_clicks):
    triggered_id = ctx.triggered_id or "btn-nav-generador"
    if triggered_id == "btn-nav-configuracion":
        return create_configuracion_view()
    return create_generador_view()

# Callback para gestionar el estilo "active" de los botones de navegación
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
    
    if triggered_id == "btn-nav-generador":
        gen_class += " active"
    elif triggered_id == "btn-nav-configuracion":
        conf_class += " active"
        
    return gen_class, conf_class


# Callback para el botón de carga de histórico
@app.callback(
    Output("config-feedback-message", "children"),
    Input("btn-gen-historico", "n_clicks"),
    prevent_initial_call=True  # Evita que se ejecute al cargar la página
)
def handle_historical_load(n_clicks):
    # 1. Cargar datos desde el CSV
    df, load_message, load_success = run_historical_load()
    
    if not load_success:
        # Si la carga falla, muestra el error y termina
        alert = dbc.Alert(
            [html.I(className="fa-solid fa-triangle-exclamation me-2"), load_message],
            color="danger",
            className="d-flex align-items-center"
        )
        return alert

    # 2. Guardar el DataFrame en la base de datos
    save_success, save_message = save_historico_to_db(df)

    if not save_success:
        # Si el guardado falla, muestra el error
        alert = dbc.Alert(
            [html.I(className="fa-solid fa-triangle-exclamation me-2"), save_message],
            color="danger",
            className="d-flex align-items-center"
        )
        return alert

    # 3. Si todo fue exitoso, muestra un mensaje combinado
    final_message = f"{load_message} {save_message}"
    alert = dbc.Alert(
        [html.I(className="fa-solid fa-check-circle me-2"), final_message],
        color="success",
        className="d-flex align-items-center"
    )
    return alert

@app.callback(
    Output("config-feedback-message", "children", allow_duplicate=True),
    Input("btn-gen-omega", "n_clicks"),
    prevent_initial_call=True
)
def handle_omega_class_generation(n_clicks):
    success, message = calculate_and_save_frequencies()
    
    if success:
        alert = dbc.Alert(
            [html.I(className="fa-solid fa-check-circle me-2"), message],
            color="success",
            className="d-flex align-items-center"
        )
    else:
        alert = dbc.Alert(
            [html.I(className="fa-solid fa-triangle-exclamation me-2"), message],
            color="danger",
            className="d-flex align-items-center"
        )
    
    return alert


print("--- Callbacks registrados ---")
# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    app.run(debug=True)