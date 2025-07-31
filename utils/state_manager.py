# state_manager.py

import json
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_state(state_file_path: str) -> Dict[str, Any]:
    """
    Lee un archivo de estado específico y devuelve su contenido como un diccionario.
    """
    try:
        with open(state_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si no existe o está corrupto, devuelve un estado por defecto.
        # Este estado es genérico para cualquier juego.
        logger.warning(f"No se encontró o no se pudo leer el archivo de estado '{os.path.basename(state_file_path)}'. Se devuelve un estado por defecto.")
        return {
            "last_concurso_in_db": 0,
            "last_concurso_for_freqs": 0,
            "last_concurso_for_optimization": 0,
            "last_concurso_for_omega_class": 0
        }

def save_state(new_state: Dict[str, Any], state_file_path: str):
    """
    Guarda un diccionario de estado actualizado en un archivo JSON específico.
    """
    try:
        with open(state_file_path, 'w', encoding='utf-8') as f:
            json.dump(new_state, f, indent=4)
        logger.info(f"Estado del sistema actualizado en '{os.path.basename(state_file_path)}'.")
    except Exception as e:
        logger.error(f"Error crítico al guardar el estado del sistema en '{state_file_path}': {e}", exc_info=True)