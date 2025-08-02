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
from modules import omega_logic as ol

import config
from utils.logger_config import setup_logger
from modules import database as db
from modules.omega_logic import _calculate_subsequence_affinity

importlib.reload(config)
setup_logger()
logger = logging.getLogger(__name__)

def prepare_database_for_cero(db_path: str):
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
                random_omega_score REAL NOT NULL, -- <-- NUEVA COLUMNA
                combinacion TEXT NOT NULL
            );
        """)
        cursor.execute("DROP TABLE IF EXISTS omega_cero_metrics")
        cursor.execute("CREATE TABLE omega_cero_metrics (metric_name TEXT PRIMARY KEY, value REAL NOT NULL);")
        conn.commit()
        logger.info("Tablas de trayectoria para Omega Cero creadas/recreadas.")
    finally:
        if conn: conn.close()

def save_data(db_path: str, trajectory_data: list, metrics_data: dict):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.executemany("INSERT INTO omega_score_trajectory VALUES (?, ?, ?, ?, ?)", trajectory_data) # <-- 5 placeholders
        metrics_list = list(metrics_data.items())
        cursor.executemany("INSERT INTO omega_cero_metrics VALUES (?, ?)", metrics_list)
        conn.commit()
    finally:
        if conn: conn.close()

def main(game_id: str):
    try:
        game_config = config.get_game_config(game_id)
    except ValueError as e:
        logger.error(f"Error: {e}. Juegos disponibles: {list(config.GAME_REGISTRY.keys())}")
        return

    logger.info("="*60); logger.info(f"INICIANDO ANÁLISIS DE OMEGA CERO PARA: {game_config['display_name']}"); logger.info("="*60)

    db_path = game_config['paths']['db']
    result_columns = game_config['data_source']['result_columns']
    n, k = game_config['n'], game_config['k']
    
    prepare_database_for_cero(db_path)
    
    df_full_historico = db.read_historico_from_db(db_path)
    if df_full_historico.empty or 'omega_score' not in df_full_historico.columns:
        logger.error("El histórico está vacío o no está enriquecido."); return
        
    df_full_historico = df_full_historico.sort_values(by='concurso').reset_index(drop=True)
    total_sorteos = len(df_full_historico)
    start_point = 50

    trajectory_results = []
    script_start_time = time.time()
    PERCENTIL_FIJO = 20

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
            except (ValueError, TypeError): continue
        
        freqs_for_eval = {'pares': dict(freqs_past_pares)}
        
        original_score_value = 0.0
        random_score_value = 0.0
        
        if freqs_for_eval['pares']:
            afinidades_pasadas = [ol._calculate_subsequence_affinity(sorted([int(r[c]) for c in result_columns]), freqs_for_eval, 2) for _, r in df_past.iterrows() if all(c in r for c in result_columns)] # type: ignore
            
            if afinidades_pasadas:
                umbral_pares_past = int(np.percentile(afinidades_pasadas, PERCENTIL_FIJO))
                
                # Calcular score para el ganador REAL
                try:
                    current_combination = sorted([int(current_concurso_row[col]) for col in result_columns]) # type: ignore
                    af_p_real = _calculate_subsequence_affinity(current_combination, freqs_for_eval, 2)
                    original_score_value = (af_p_real - umbral_pares_past) / (umbral_pares_past or 1)
                except (ValueError, TypeError): combo_str = "Error en datos"

                # --- NUEVO: Calcular score para una combinación ALEATORIA ---
                random_combination = sorted(np.random.choice(range(1, k + 1), n, replace=False))
                af_p_random = _calculate_subsequence_affinity(random_combination, freqs_for_eval, 2)
                random_score_value = (af_p_random - umbral_pares_past) / (umbral_pares_past or 1)
        
        try: combo_str = "-".join(map(str, current_combination)) # type: ignore
        except: combo_str = "Error"

        trajectory_results.append((
            concurso_num,
            original_score_value,
            current_concurso_row['omega_score'],
            random_score_value, # <-- DATO NUEVO
            combo_str
        ))
    
    # ... (cálculo de métricas y guardado)
    df_trajectory = pd.DataFrame(trajectory_results, columns=['concurso', 'original_omega_score', 'current_omega_score', 'random_omega_score', 'combinacion'])
    df_intervalo = df_trajectory[df_trajectory['concurso'] >= 600].copy().reset_index(drop=True)
    
    # (El resto de la lógica de métricas se mantiene igual, ya que se basa en 'original_omega_score')
    media = df_intervalo['original_omega_score'].mean(); std_dev = df_intervalo['original_omega_score'].std()
    limite_superior = media + std_dev; limite_inferior = media - std_dev
    signs = np.sign(df_intervalo['original_omega_score']); indices_de_cruce = np.where(np.diff(signs) != 0)[0]
    periodo_ciclo = np.mean(np.diff(indices_de_cruce)) if len(indices_de_cruce) > 1 else 0
    en_banda = (df_intervalo['original_omega_score'] >= limite_inferior) & (df_intervalo['original_omega_score'] <= limite_superior)
    cambios_de_estado = en_banda.ne(en_banda.shift()).cumsum(); duraciones = cambios_de_estado.value_counts().sort_index()
    indices_en_banda = cambios_de_estado[en_banda].unique()
    periodo_estabilidad = duraciones[indices_en_banda].mean() if len(indices_en_banda) > 0 else 0
    
    metrics = {"media_score_original": media, "std_dev_score_original": std_dev, "banda_normal_superior": limite_superior, "banda_normal_inferior": limite_inferior, "periodo_medio_ciclo": periodo_ciclo, "periodo_medio_estabilidad": periodo_estabilidad}
    
    save_data(db_path, trajectory_results, metrics)
    logger.info("=" * 60); logger.info(f"ANÁLISIS OMEGA CERO COMPLETO. Tiempo total: {(time.time() - script_start_time) / 60:.2f} minutos."); logger.info("=" * 60)

if __name__ == "__main__":
    game_id_arg = 'melate_retro'
    if len(sys.argv) > 1:
        game_id_arg = sys.argv[1]
    main(game_id=game_id_arg)