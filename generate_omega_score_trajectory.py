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
from modules.omega_logic import _calculate_subsequence_affinity

importlib.reload(config)
setup_logger()
logger = logging.getLogger(__name__)

def prepare_database_for_cero(db_path: str):
    """Borra y recrea las dos tablas de trayectoria necesarias."""
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
        cursor.execute("DROP TABLE IF EXISTS omega_cero_metrics")
        cursor.execute("""
            CREATE TABLE omega_cero_metrics (
                metric_name TEXT PRIMARY KEY,
                value REAL NOT NULL
            );
        """)
        conn.commit()
        logger.info("Tablas 'omega_score_trajectory' y 'omega_cero_metrics' creadas con éxito.")
    finally:
        if conn: conn.close()

def save_data(db_path: str, trajectory_data: list, metrics_data: dict):
    """Guarda los datos de trayectoria y las métricas finales."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Guardar trayectoria
        cursor.executemany("INSERT INTO omega_score_trajectory VALUES (?, ?, ?, ?)", trajectory_data)
        # Guardar métricas
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

    logger.info("=" * 60)
    logger.info(f"INICIANDO ANÁLISIS DE OMEGA CERO PARA: {game_config['display_name']}")
    logger.info("=" * 60)

    db_path = game_config['paths']['db']
    result_columns = game_config['data_source']['result_columns']
    
    prepare_database_for_cero(db_path)
    
    df_full_historico = db.read_historico_from_db(db_path)
    if df_full_historico.empty or 'omega_score' not in df_full_historico.columns:
        logger.error("El histórico está vacío o no está enriquecido. Ejecute la configuración en la app primero.")
        return
        
    df_full_historico = df_full_historico.sort_values(by='concurso').reset_index(drop=True)
    total_sorteos = len(df_full_historico)
    start_point = 50

    original_scores_data = []
    script_start_time = time.time()
    
    PERCENTIL_FIJO = 20

    for i in range(start_point, total_sorteos):
        # ... (bucle de cálculo de scores sin cambios)
        current_concurso_row = df_full_historico.iloc[i]
        concurso_num = int(current_concurso_row['concurso'])
        df_past = df_full_historico.iloc[:i]
        
        logger.info(f"Procesando concurso {concurso_num} ({i+1}/{total_sorteos})...")
        
        freqs_past_pares = Counter()
        for _, row in df_past.iterrows():
            try:
                draw = sorted([int(row[col]) for col in result_columns]) # type: ignore
                freqs_past_pares.update(combinations(draw, 2))
            except (ValueError, TypeError): continue
        
        freqs_for_eval = {'pares': dict(freqs_past_pares)}
        
        original_score_value = 0.0
        if freqs_for_eval['pares']:
            afinidades_pasadas = []
            for _, r in df_past.iterrows():
                try:
                    combo = sorted([int(r[c]) for c in result_columns]) # type: ignore
                    afinidades_pasadas.append(_calculate_subsequence_affinity(combo, freqs_for_eval, 2))
                except (ValueError, TypeError): continue
            
            if afinidades_pasadas:
                umbral_pares_past = int(np.percentile(afinidades_pasadas, PERCENTIL_FIJO))
                try:
                    current_combination = sorted([int(current_concurso_row[col]) for col in result_columns]) # type: ignore
                    af_p = _calculate_subsequence_affinity(current_combination, freqs_for_eval, 2)
                    original_score_value = (af_p - umbral_pares_past) / (umbral_pares_past or 1)
                except (ValueError, TypeError):
                    logger.warning(f"Datos inválidos en el concurso actual {concurso_num}, score original será 0.")
        try:
            combo_str = "-".join(map(str, sorted([int(current_concurso_row[col]) for col in result_columns]))) # type: ignore
        except (ValueError, TypeError):
            combo_str = "Error en datos"
        original_scores_data.append({'concurso': concurso_num, 'original_omega_score': original_score_value, 'current_omega_score': current_concurso_row['omega_score'], 'combinacion': combo_str})

    logger.info("Cálculo de scores originales completo. Analizando la serie temporal...")
    df_trajectory = pd.DataFrame(original_scores_data)
    
    # --- INICIO DE LA CORRECCIÓN ---
    # Asegurarse de que el intervalo existe antes de proceder
    if 600 in df_trajectory['concurso'].values:
        df_intervalo = df_trajectory[df_trajectory['concurso'] >= 600].copy().reset_index(drop=True)
    else:
        df_intervalo = df_trajectory.copy().reset_index(drop=True)

    media = df_intervalo['original_omega_score'].mean()
    std_dev = df_intervalo['original_omega_score'].std()
    limite_superior = media + std_dev
    limite_inferior = media - std_dev
    
    # Corrección para el cálculo de cruces por cero
    signs = np.sign(df_intervalo['original_omega_score'])
    # Encontramos los índices DONDE ocurre un cambio de signo
    indices_de_cruce = np.where(np.diff(signs) != 0)[0]
    periodo_ciclo = np.mean(np.diff(indices_de_cruce)) if len(indices_de_cruce) > 1 else 0

    # Corrección para el cálculo de estabilidad en la banda
    en_banda = (df_intervalo['original_omega_score'] >= limite_inferior) & (df_intervalo['original_omega_score'] <= limite_superior)
    # Identificamos bloques consecutivos de True/False
    cambios_de_estado = en_banda.ne(en_banda.shift()).cumsum()
    # Calculamos la duración de cada bloque
    duraciones = cambios_de_estado.value_counts().sort_index()
    # Nos quedamos solo con la duración de los bloques que estaban "en banda" (True)
    indices_en_banda = cambios_de_estado[en_banda].unique()
    periodo_estabilidad = duraciones[indices_en_banda].mean() if len(indices_en_banda) > 0 else 0
    # --- FIN DE LA CORRECCIÓN ---
    
    metrics = {
        "media_score_original": media,
        "std_dev_score_original": std_dev,
        "banda_normal_superior": limite_superior,
        "banda_normal_inferior": limite_inferior,
        "periodo_medio_ciclo": periodo_ciclo,
        "periodo_medio_estabilidad": periodo_estabilidad
    }
    logger.info(f"Métricas calculadas: {metrics}")
    
    db_trajectory_data = [tuple(d.values()) for d in original_scores_data]
    save_data(db_path, db_trajectory_data, metrics)

    logger.info("=" * 60)
    logger.info(f"ANÁLISIS OMEGA CERO COMPLETO. Tiempo total: {(time.time() - script_start_time) / 60:.2f} minutos.")
    logger.info("=" * 60)
    
if __name__ == "__main__":
    game_id_arg = 'melate_retro'
    if len(sys.argv) > 1:
        game_id_arg = sys.argv[1]
    main(game_id=game_id_arg)