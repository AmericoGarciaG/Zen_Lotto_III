# generate_golden_trajectory.py

import pandas as pd
import numpy as np
import logging
import time
import sys
import sqlite3
import importlib
from typing import List, Dict, Any, Tuple
from collections import Counter
from itertools import combinations

import config
from utils.logger_config import setup_logger
from modules import database as db
from modules import omega_logic as ol

importlib.reload(config)
setup_logger()
logger = logging.getLogger(__name__)

def prepare_database(db_path: str):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS golden_trajectory")
        cursor.execute("""
            CREATE TABLE golden_trajectory (
                concurso INTEGER PRIMARY KEY,
                elite_score_original_mean REAL NOT NULL
            );
        """)
        conn.commit()
    except Exception as e:
        logger.error(f"Error preparando la BD para la Línea Dorada: {e}")
    finally:
        if conn: conn.close()

def main(game_id: str, elite_percentile: float = 95.0):
    try:
        game_config = config.get_game_config(game_id)
    except ValueError as e:
        logger.error(f"Error: {e}."); return

    logger.info("="*60); logger.info(f"GENERANDO LÍNEA DORADA (ALTA RESOLUCIÓN) PARA: {game_config['display_name']}"); logger.info("="*60)
    db_path = game_config['paths']['db']

    df_candidates = db.read_omega_class_with_fenix(db_path, only_unplayed=True)
    if df_candidates.empty or 'fenix_score' not in df_candidates.columns or df_candidates['fenix_score'].isnull().all():
        logger.error("No se encontraron Scores Fénix. Ejecute 'calculate_fenix_score.py' primero."); return

    threshold_fenix = np.percentile(df_candidates['fenix_score'].dropna(), elite_percentile)
    df_elite = df_candidates[df_candidates['fenix_score'] >= threshold_fenix]
    logger.info(f"Umbral de Fenix Score (percentil {elite_percentile}): {threshold_fenix:.4f}. Élite Reactiva: {len(df_elite)} combinaciones.")
    
    combo_cols = [f'c{i}' for i in range(1, game_config['n'] + 1)]
    elite_combinations = [list(map(int, row)) for row in df_elite[combo_cols].values]

    df_full_historico = db.read_historico_from_db(db_path).sort_values(by='concurso').reset_index(drop=True)
    result_cols = game_config['data_source']['result_columns']
    
    # --- INICIO DE LA CORRECCIÓN ESTRUCTURAL ---
    START_POINT_ANALYSIS = 600
    df_base_hist = df_full_historico[df_full_historico['concurso'] < START_POINT_ANALYSIS]
    df_analysis_hist = df_full_historico[df_full_historico['concurso'] >= START_POINT_ANALYSIS].copy()
    
    # 1. Calcular el estado inicial una sola vez, ANTES del bucle.
    logger.info("Calculando estado base inicial (hasta sorteo 600)...")
    current_freqs = Counter(c for _, row in df_base_hist.iterrows() for c in combinations(sorted(row[result_cols]), 2))
    afinidades_list = [ol._calculate_subsequence_affinity(list(sorted(row[result_cols])), {'pares': current_freqs}, 2) for _, row in df_base_hist.iterrows()]
    
    golden_trajectory_data: List[Tuple[int, float]] = []
    total_points = len(df_analysis_hist)

    logger.info(f"Iniciando generación de la Línea Dorada sobre {total_points} puntos...")

    # 2. Bucle incremental que ahora funciona correctamente.
    for i, analysis_row in enumerate(df_analysis_hist.itertuples(index=False)):
        current_concurso_num = int(analysis_row.concurso) # type: ignore

        umbral_pares_past = float(np.percentile(afinidades_list, 20)) if afinidades_list else 0.0
        freqs_past_dict = {'pares': dict(current_freqs)}
        
        elite_scores_at_t: List[float] = [
            float((ol._calculate_subsequence_affinity(combo, freqs_past_dict, 2) - umbral_pares_past) / (umbral_pares_past or 1))
            for combo in elite_combinations
        ]
        
        mean_score = float(np.mean(elite_scores_at_t)) if elite_scores_at_t else 0.0
        golden_trajectory_data.append((current_concurso_num, mean_score))

        # Actualizar el estado para la siguiente iteración
        current_combo = sorted([int(getattr(analysis_row, col)) for col in result_cols])
        current_freqs.update(combinations(current_combo, 2))
        afinidades_list.append(ol._calculate_subsequence_affinity(current_combo, {'pares': current_freqs}, 2))
        
        if (i + 1) % 100 == 0 or (i + 1) == total_points:
            logger.info(f"  -> Línea Dorada: Procesado punto {i + 1}/{total_points} (Concurso: {current_concurso_num})")
    # --- FIN DE LA CORRECCIÓN ESTRUCTURAL ---

    prepare_database(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.executemany("INSERT INTO golden_trajectory VALUES (?, ?)", golden_trajectory_data)
        conn.commit()
    finally:
        conn.close()
    
    logger.info(f"Línea Dorada generada con {len(golden_trajectory_data)} puntos y guardada.")

if __name__ == "__main__":
    main('melate_retro')