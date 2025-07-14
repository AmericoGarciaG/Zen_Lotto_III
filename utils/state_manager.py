import json
import logging
import config

logger = logging.getLogger(__name__)

def get_state():
    """Lee el archivo de estado y devuelve su contenido como un diccionario."""
    try:
        with open(config.STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si no existe o está corrupto, devuelve un estado por defecto
        return {
            "last_concurso_in_db": 0,
            "last_concurso_for_freqs": 0,
            "last_concurso_for_omega_class": 0
        }

def save_state(new_state):
    """Guarda un diccionario de estado actualizado en el archivo JSON."""
    try:
        with open(config.STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_state, f, indent=4)
        logger.info(f"Estado del sistema actualizado en '{config.STATE_FILE}'.")
    except Exception as e:
        logger.error(f"Error crítico al guardar el estado del sistema: {e}", exc_info=True)