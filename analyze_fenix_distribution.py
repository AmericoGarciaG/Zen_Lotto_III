# analyze_fenix_distribution.py

import pandas as pd
import numpy as np
import logging
import sys
import json
import os

import config
from utils.logger_config import setup_logger
from modules import database as db

setup_logger()
logger = logging.getLogger(__name__)

def main(game_id: str):
    try:
        game_config = config.get_game_config(game_id)
    except ValueError as e:
        logger.error(f"Error: {e}."); return

    logger.info("="*60); logger.info(f"PROYECTO FÉNIX (EL VEREDICTO): Analizando distribución de Scores para: {game_config['display_name']}"); logger.info("="*60)

    db_path = game_config['paths']['db']
    
    # 1. Leer la clase omega completa con los Fenix Scores ya calculados
    df_omega = db.read_full_omega_class(db_path)

    if df_omega.empty or 'fenix_score' not in df_omega.columns or df_omega['fenix_score'].isnull().all():
        logger.error("No se encontraron Scores Fénix en la base de datos. Ejecute 'calculate_fenix_score.py' primero.")
        return

    # 2. Dividir en los dos grupos de estudio
    df_ganadores = df_omega[df_omega['ha_salido'] == 1].copy()
    df_virgenes = df_omega[df_omega['ha_salido'] == 0].copy()

    if df_ganadores.empty:
        logger.warning("No se encontraron ganadores históricos en la Clase Omega para realizar el análisis.")
        return

    logger.info(f"Análisis sobre {len(df_ganadores)} ganadores y {len(df_virgenes)} candidatas vírgenes.")

    # 3. Preparar datos para la visualización
    data_to_save = {
        'ganadores_scores': df_ganadores['fenix_score'].dropna().tolist(),
        'virgenes_scores': df_virgenes['fenix_score'].dropna().tolist(),
        'stats': {
            'ganadores_mean': df_ganadores['fenix_score'].mean(),
            'ganadores_median': df_ganadores['fenix_score'].median(),
            'ganadores_std': df_ganadores['fenix_score'].std(),
            'virgenes_mean': df_virgenes['fenix_score'].mean(),
            'virgenes_median': df_virgenes['fenix_score'].median(),
            'virgenes_std': df_virgenes['fenix_score'].std(),
        }
    }
    
    # 4. Guardar los resultados en un archivo JSON
    output_path = os.path.join(config.DATA_DIR, f"{game_id}_fenix_analysis.json")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4)
        logger.info(f"Análisis de distribución Fénix guardado en '{output_path}'")
    except Exception as e:
        logger.error(f"Error al guardar el archivo de análisis: {e}")

    logger.info("="*60); logger.info("VEREDICTO COMPLETADO."); logger.info("="*60)


if __name__ == "__main__":
    main('melate_retro')