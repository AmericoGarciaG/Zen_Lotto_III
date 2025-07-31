# generate_omega_score_trajectory.py

import pandas as pd
import logging
import time
import sqlite3
import sys
import numpy as np
from collections import Counter
from itertools import combinations
import importlib
from typing import Dict, Any

import config
from utils.logger_config import setup_logger
from modules import database as db
from modules import ml_optimizer
from modules.omega_logic import _calculate_subsequence_affinity, evaluate_combination

importlib.reload(config)
setup_logger()
logger = logging.getLogger(__name__)

def create_trajectory_table(db_path: str):
    """Crea la nueva tabla para almacenar los resultados."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS omega_score_trajectory")
        cursor.execute("""
            CREATE TABLE omega_score_trajectory (
                concurso INTEGER PRIMARY KEY,
                original_omega_score REAL NOT NULL,
                current_omega_score REAL NOT NULL,
                combinacion TEXT NOT NULL
            );
        """)
        conn.commit()
        logger.info("Tabla 'omega_score_trajectory' creada con éxito.")
    finally:
        if conn: conn.close()

def save_trajectory_batch(db_path: str, data: list):
    """Guarda un lote de resultados en la tabla."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO omega_score_trajectory VALUES (?, ?, ?, ?)",
            data
        )
        conn.commit()
    finally:
        if conn: conn.close()

def main(game_id: str):
    try:
        game_config = config.get_game_config(game_id)
    except ValueError as e:
        logger.error(f"Error: {e}. Juegos disponibles: {list(config.GAME_REGISTRY.keys())}")
        return

    logger.info("=" * 60)
    logger.info(f"INICIANDO CÁLCULO DE TRAYECTORIA DE OMEGA SCORES PARA: {game_config['display_name']}")
    logger.info("=" * 60)

    db_path = game_config['paths']['db']
    result_columns = game_config['data_source']['result_columns']
    
    create_trajectory_table(db_path)
    
    df_full_historico = db.read_historico_from_db(db_path)
    if df_full_historico.empty or 'omega_score' not in df_full_historico.columns:
        logger.error("El histórico está vacío o no está enriquecido. Ejecute la configuración en la app primero.")
        return
        
    df_full_historico = df_full_historico.sort_values(by='concurso').reset_index(drop=True)
    total_sorteos = len(df_full_historico)
    start_point = 50

    original_scores = []
    script_start_time = time.time()
    
    # --- INICIO DE LA CORRECCIÓN ---
    # Definimos un percentil fijo para usar en el cálculo simplificado
    PERCENTIL_FIJO = 20
    # --- FIN DE LA CORRECCIÓN ---

    for i in range(start_point, total_sorteos):
        current_concurso_row = df_full_historico.iloc[i]
        concurso_num = int(current_concurso_row['concurso'])
        
        df_past = df_full_historico.iloc[:i]
        
        logger.info(f"Procesando concurso {concurso_num} ({i+1}/{total_sorteos})...")
        
        # Calcular frecuencias basado en el pasado
        freqs_past_pares = Counter()
        for _, row in df_past.iterrows():
            try:
                draw = sorted([int(row[col]) for col in result_columns]) # type: ignore
                freqs_past_pares.update(combinations(draw, 2))
            except (ValueError, TypeError):
                continue
        
        freqs_for_eval = {'pares': dict(freqs_past_pares)}
        
        if not freqs_for_eval['pares']:
            original_score_value = 0.0
        else:
            # Calcular las afinidades de todos los sorteos pasados
            afinidades_pasadas = [
                _calculate_subsequence_affinity(sorted([int(r[c]) for c in result_columns]), freqs_for_eval, 2)  # type: ignore
                for _, r in df_past.iterrows()
            ]

            # --- INICIO DE LA CORRECCIÓN ---
            # Usamos el percentil fijo (ej. 20) en lugar del valor del umbral
            umbral_pares_past = int(np.percentile(afinidades_pasadas, PERCENTIL_FIJO))
            # --- FIN DE LA CORRECCIÓN ---

            current_combination = sorted([int(current_concurso_row[col]) for col in result_columns]) # type: ignore
            af_p = _calculate_subsequence_affinity(current_combination, freqs_for_eval, 2)
            
            original_score_value = (af_p - umbral_pares_past) / (umbral_pares_past or 1)

        original_scores.append({
            'concurso': concurso_num,
            'original_omega_score': original_score_value,
            'current_omega_score': current_concurso_row['omega_score'],
            'combinacion': "-".join(map(str, sorted([int(current_concurso_row[col]) for col in result_columns]))) # type: ignore
        })

    db_data = [tuple(d.values()) for d in original_scores]
    save_trajectory_batch(db_path, db_data)

    logger.info("=" * 60)
    logger.info(f"CÁLCULO DE TRAYECTORIA COMPLETO. Tiempo total: {(time.time() - script_start_time) / 60:.2f} minutos.")
    logger.info("=" * 60)

if __name__ == "__main__":
    game_id_arg = 'melate_retro'
    if len(sys.argv) > 1:
        game_id_arg = sys.argv[1]
    main(game_id=game_id_arg)