# config.py

import os
from math import comb
from typing import Dict, Any

# --- CONFIGURACIONES GLOBALES DE LA APLICACIÓN ---

# Directorio de datos principal
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Habilita/deshabilita las vistas y cálculos avanzados de monitoreo
DEBUG_MODE = True


# --- REGISTRO CENTRAL DE JUEGOS ---
# Esta es la nueva "única fuente de verdad". Cada juego soportado por la
# aplicación se define como una entrada en este diccionario.

GAME_REGISTRY: Dict[str, Dict[str, Any]] = {
    
    'melate_retro': {
        'id': 'melate_retro',
        'display_name': 'Melate Retro',
        'n': 6,  # Números a elegir en una combinación
        'k': 39,  # Universo total de números disponibles
        
        'data_source': {
            'url': 'https://www.loterianacional.gob.mx/Home/Historicos?ARHP=TQBlAGwAYQB0AGUALQBSAGUAdAByAG8A',
            'expected_columns': ['CONCURSO', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'BOLSA', 'FECHA'],
            'column_mapping': {
                'CONCURSO': 'concurso', 'F1': 'r1', 'F2': 'r2', 'F3': 'r3',
                'F4': 'r4', 'F5': 'r5', 'F6': 'r6', 'BOLSA': 'bolsa', 'FECHA': 'fecha'
            },
            'result_columns': [f'r{i}' for i in range(1, 7)]
        },
        
        'omega_config': {
            'affinity_levels': [2, 3, 4],
            'score_weights': {'pares': 0.2, 'tercias': 0.3, 'cuartetos': 0.5},
            'default_thresholds': {'pares': 421, 'tercias': 65, 'cuartetos': 16}
        }
    },
    
    'chispazo': {
        'id': 'chispazo',
        'display_name': 'Chispazo',
        'n': 5,
        'k': 28,
        
        'data_source': {
            'url': 'https://www.loterianacional.gob.mx/Home/Historicos?ARHP=QwBoAGkAcwBwAGEAegBvAA==',
            # Columnas exactas del archivo CSV oficial
            'expected_columns': ['CONCURSO', 'R1', 'R2', 'R3', 'R4', 'R5', 'FECHA'], 
            # Mapeo corregido para coincidir con las columnas reales (sin espacios)
            'column_mapping': {
                'CONCURSO': 'concurso', 'R1': 'r1', 'R2': 'r2', 'R3': 'r3',
                'R4': 'r4', 'R5': 'r5', 'FECHA': 'fecha'
            },
            'result_columns': [f'r{i}' for i in range(1, 6)]
        },
        
        'omega_config': {
            'affinity_levels': [2, 3, 4],
            # Mantenemos los mismos pesos para el experimento
            'score_weights': {'pares': 0.2, 'tercias': 0.3, 'cuartetos': 0.5},
            # Umbrales iniciales conservadores (se optimizarán con el ML)
            'default_thresholds': {'pares': 1, 'tercias': 1, 'cuartetos': 1}
        }
    }
}


# --- FUNCIONES DE AYUDA PARA GESTIONAR LA CONFIGURACIÓN ---

def get_game_paths(game_id: str) -> Dict[str, str]:
    if game_id not in GAME_REGISTRY:
        raise ValueError(f"Juego no reconocido: {game_id}")
    
    return {
        'db': os.path.join(DATA_DIR, f"{game_id}.db"),
        'frequencies': os.path.join(DATA_DIR, f"{game_id}_frecuencias.json"),
        'state': os.path.join(DATA_DIR, f"{game_id}_system_state.json"),
        'thresholds': os.path.join(DATA_DIR, f"{game_id}_thresholds.json"),
        'backup': os.path.join(DATA_DIR, f"{game_id}_registros_backup.json")
    }

def get_game_config(game_id: str) -> Dict[str, Any]:
    if game_id not in GAME_REGISTRY:
        raise ValueError(f"Juego no reconocido: {game_id}")
    
    config = GAME_REGISTRY[game_id].copy()
    config['paths'] = get_game_paths(game_id)
    config['total_combinations'] = comb(config['k'], config['n'])
    
    return config


# --- ESQUEMAS DE TABLAS DE TRAYECTORIA (COMUNES) ---

UMBRALES_TRAYECTORIA_SCHEMA = {
    "ultimo_concurso_usado": "INTEGER PRIMARY KEY", "umbral_pares": "INTEGER NOT NULL",
    "umbral_tercias": "INTEGER NOT NULL", "umbral_cuartetos": "INTEGER NOT NULL",
    "cobertura_historica": "REAL NOT NULL", "cobertura_universal_estimada": "REAL NOT NULL",
    "fecha_calculo": "DATETIME"
}

FRECUENCIAS_TRAYECTORIA_SCHEMA = {
    "ultimo_concurso_usado": "INTEGER PRIMARY KEY", "total_pares_unicos": "INTEGER NOT NULL",
    "suma_freq_pares": "INTEGER NOT NULL", "total_tercias_unicas": "INTEGER NOT NULL",
    "suma_freq_tercias": "INTEGER NOT NULL", "total_cuartetos_unicos": "INTEGER NOT NULL",
    "suma_freq_cuartetos": "INTEGER NOT NULL", "fecha_calculo": "DATETIME"
}

AFINIDADES_TRAYECTORIA_SCHEMA = {
    "ultimo_concurso_usado": "INTEGER PRIMARY KEY", "afin_pares_media": "REAL NOT NULL",
    "afin_pares_mediana": "REAL NOT NULL", "afin_pares_min": "INTEGER NOT NULL",
    "afin_pares_max": "INTEGER NOT NULL", "afin_tercias_media": "REAL NOT NULL",
    "afin_tercias_mediana": "REAL NOT NULL", "afin_tercias_min": "INTEGER NOT NULL",
    "afin_tercias_max": "INTEGER NOT NULL", "afin_cuartetos_media": "REAL NOT NULL",
    "afin_cuartetos_mediana": "REAL NOT NULL", "afin_cuartetos_min": "INTEGER NOT NULL",
    "afin_cuartetos_max": "INTEGER NOT NULL", "fecha_calculo": "DATETIME"
}

FREQ_DIST_TRAYECTORIA_SCHEMA = {
    "ultimo_concurso_usado": "INTEGER PRIMARY KEY", "freq_pares_media": "REAL NOT NULL",
    "freq_pares_min": "INTEGER NOT NULL", "freq_pares_max": "INTEGER NOT NULL",
    "freq_tercias_media": "REAL NOT NULL", "freq_tercias_min": "INTEGER NOT NULL",
    "freq_tercias_max": "INTEGER NOT NULL", "freq_cuartetos_media": "REAL NOT NULL",
    "freq_cuartetos_min": "INTEGER NOT NULL", "freq_cuartetos_max": "INTEGER NOT NULL",
    "fecha_calculo": "DATETIME"
}