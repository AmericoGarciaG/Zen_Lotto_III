# app.py

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ctx

from modules.presentation import create_layout, create_generador_view, create_configuracion_view

# --- INICIALIZACIÓN DE LA APP ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.LITERA])    # opción dbc.themes.LUX
server = app.server

# --- LAYOUT DE LA APLICACIÓN ---
app.layout = create_layout()

# --- CALLBACKS ---

# Callback para actualizar el contenido de la vista principal
@app.callback(
    Output("view-content", "children"),
    Input("btn-nav-generador", "n_clicks"),
    Input("btn-nav-configuracion", "n_clicks"),
)
def render_view_content(gen_clicks, conf_clicks):
    # ctx.triggered_id nos dice qué botón se presionó
    triggered_id = ctx.triggered_id or "btn-nav-generador"

    if triggered_id == "btn-nav-configuracion":
        return create_configuracion_view()
    
    # Por defecto, siempre mostramos el generador
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
    
    # Estilos base
    gen_class = "nav-button"
    conf_class = "nav-button"
    
    # Agregamos la clase 'active' al botón que fue presionado
    if triggered_id == "btn-nav-generador":
        gen_class += " active"
    elif triggered_id == "btn-nav-configuracion":
        conf_class += " active"
        
    return gen_class, conf_class

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    app.run(debug=True)