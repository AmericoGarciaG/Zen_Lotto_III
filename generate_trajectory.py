# generate_trajectory.py

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

# --- CONFIGURACIÓN INICIAL ---
import config
from utils.logger_config import setup_logger
from modules import database as db
from modules import ml_optimizer
from modules.omega_logic import _calculate_subsequence_affinity

importlib.reload(config)
setup_logger()
logger = logging.getLogger(__name__)

# --- FUNCIONES DE AYUDA REFACTORIZADAS ---

def prepare_database_for_trajectory(db_path: str):
    logger.info("=" * 30)
    logger.info(f"FASE PREPARATORIA: Reconstruyendo Tablas de Trayectoria en '{db_path}'")
    logger.info("=" * 30)
    
    schemas = {
        'umbrales_trayectoria': config.UMBRALES_TRAYECTORIA_SCHEMA,
        'frecuencias_trayectoria': config.FRECUENCIAS_TRAYECTORIA_SCHEMA,
        'afinidades_trayectoria': config.AFINIDADES_TRAYECTORIA_SCHEMA,
        'freq_dist_trayectoria': config.FREQ_DIST_TRAYECTORIA_SCHEMA
    }
    
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        for table_name in schemas.keys():
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.commit()

        for table_name, schema_dict in schemas.items():
            columns_def = ", ".join([f"{col_name} {col_type}" for col_name, col_type in schema_dict.items()])
            create_query = f"CREATE TABLE {table_name} ({columns_def});"
            cursor.execute(create_query)
            
        conn.commit()
        logger.info("PREPARACIÓN DE BASE DE DATOS COMPLETADA.")
    except Exception as e:
        logger.error(f"FALLO CRÍTICO al preparar la base de datos: {e}", exc_info=True)
        raise
    finally:
        if conn: conn.close()

def save_trajectory_data(db_path: str, table_name: str, schema_dict: Dict, data_dict: Dict):
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cols = [col for col in schema_dict.keys() if col != 'fecha_calculo']
        placeholders = ", ".join(["?"] * len(cols))
        
        query = f"INSERT OR REPLACE INTO {table_name} ({', '.join(cols)}, fecha_calculo) VALUES ({placeholders}, datetime('now', 'localtime'))"
        params = tuple(data_dict[col] for col in cols)

        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"Error guardando datos en '{table_name}': {e}", exc_info=True)
        raise
    finally:
        if conn: conn.close()

# --- FUNCIÓN PRINCIPAL REFACTORIZADA ---

def main(game_id: str, block_size: int = 100):
    try:
        game_config = config.get_game_config(game_id)
    except ValueError as e:
        logger.error(f"Error: {e}. Juegos disponibles: {list(config.GAME_REGISTRY.keys())}")
        return

    logger.info("=" * 60)
    logger.info(f"INICIANDO GENERACIÓN DE TRAYECTORIA PARA: {game_config['display_name']}")
    logger.info(f"Tamaño de bloque configurado: {block_size} sorteos")
    logger.info("=" * 60)
    
    db_path = game_config['paths']['db']
    result_columns = game_config['data_source']['result_columns']
    
    prepare_database_for_trajectory(db_path)
    
    df_full_historico = db.read_historico_from_db(db_path)
    if df_full_historico.empty:
        logger.error("El histórico está vacío. Ejecute la configuración en la app primero.")
        return
        
    df_full_historico = df_full_historico.sort_values(by='concurso').reset_index(drop=True)
    total_sorteos = len(df_full_historico)
    
    start_point = 50 
    if total_sorteos <= start_point:
        logger.error(f"No hay suficientes sorteos ({total_sorteos}) para iniciar el análisis (mínimo {start_point}).")
        return

    analysis_points = list(range(start_point, total_sorteos, block_size))
    if total_sorteos not in analysis_points:
        analysis_points.append(total_sorteos)

    logger.info(f"Se analizarán {len(analysis_points)} puntos de la trayectoria.")
    script_start_time = time.time()
    
    master_frequencies = {'pares': Counter(), 'tercias': Counter(), 'cuartetos': Counter()}
    last_processed_index = 0
    
    for i, end_index in enumerate(analysis_points):
        iter_start_time = time.time()
        
        df_subset = df_full_historico.head(end_index)
        df_slice = df_full_historico.iloc[last_processed_index:end_index]
        last_processed_index = end_index
        ultimo_concurso = int(df_subset.iloc[-1]['concurso'])
        
        logger.info(f"--- Procesando Bloque {i+1}/{len(analysis_points)} (hasta concurso {ultimo_concurso}) ---")
        
        # 1. Actualizar frecuencias incrementalmente
        for _, row in df_slice.iterrows():
            try:
                draw = sorted([int(row[col]) for col in result_columns]) # type: ignore
                master_frequencies['pares'].update(combinations(draw, 2))
                master_frequencies['tercias'].update(combinations(draw, 3))
                master_frequencies['cuartetos'].update(combinations(draw, 4))
            except (ValueError, TypeError): continue
        
        # **INICIO DEL CÓDIGO RESTAURADO**
        # 2. Guardar métricas de CONTEO de frecuencias
        freq_count_metrics = {
            "ultimo_concurso_usado": ultimo_concurso,
            "total_pares_unicos": len(master_frequencies['pares']),
            "suma_freq_pares": sum(master_frequencies['pares'].values()),
            "total_tercias_unicas": len(master_frequencies['tercias']),
            "suma_freq_tercias": sum(master_frequencies['tercias'].values()),
            "total_cuartetos_unicos": len(master_frequencies['cuartetos']),
            "suma_freq_cuartetos": sum(master_frequencies['cuartetos'].values()),
        }
        save_trajectory_data(db_path, 'frecuencias_trayectoria', config.FRECUENCIAS_TRAYECTORIA_SCHEMA, freq_count_metrics)

        # 3. Guardar métricas de DISTRIBUCIÓN de valores de frecuencias
        freq_dist_metrics: Dict[str, Any] = {"ultimo_concurso_usado": ultimo_concurso}
        for level in ['pares', 'tercias', 'cuartetos']:
            values = list(master_frequencies[level].values()) if master_frequencies[level] else [0]
            freq_dist_metrics[f'freq_{level}_media'] = float(np.mean(values))
            freq_dist_metrics[f'freq_{level}_min'] = int(np.min(values))
            freq_dist_metrics[f'freq_{level}_max'] = int(np.max(values))
        save_trajectory_data(db_path, 'freq_dist_trayectoria', config.FREQ_DIST_TRAYECTORIA_SCHEMA, freq_dist_metrics)

        # 4. Guardar métricas de AFINIDADES
        afin_p, afin_t, afin_q = [], [], []
        for _, row in df_subset.iterrows():
            combo = sorted([int(row[col]) for col in result_columns]) # type: ignore
            afin_p.append(_calculate_subsequence_affinity(combo, master_frequencies, 2))
            afin_t.append(_calculate_subsequence_affinity(combo, master_frequencies, 3))
            afin_q.append(_calculate_subsequence_affinity(combo, master_frequencies, 4))
        
        # Forzamos la conversión a tipos nativos de Python ANTES de guardar
        affinity_metrics = {
            "ultimo_concurso_usado": ultimo_concurso,
            "afin_pares_media": float(np.mean(afin_p)), 
            "afin_pares_mediana": float(np.median(afin_p)), 
            "afin_pares_min": int(np.min(afin_p)), 
            "afin_pares_max": int(np.max(afin_p)),
            "afin_tercias_media": float(np.mean(afin_t)), 
            "afin_tercias_mediana": float(np.median(afin_t)), 
            "afin_tercias_min": int(np.min(afin_t)), 
            "afin_tercias_max": int(np.max(afin_t)),
            "afin_cuartetos_media": float(np.mean(afin_q)), 
            "afin_cuartetos_mediana": float(np.median(afin_q)), 
            "afin_cuartetos_min": int(np.min(afin_q)), 
            "afin_cuartetos_max": int(np.max(afin_q))
        }
        save_trajectory_data(db_path, 'afinidades_trayectoria', config.AFINIDADES_TRAYECTORIA_SCHEMA, affinity_metrics)

        # 5. Optimizar y guardar UMBRALES
        freqs_for_optimizer = {k: dict(v) for k, v in master_frequencies.items()}
        success, _, report = ml_optimizer.run_optimization(game_config, df_subset, freqs_for_optimizer)
        if success and 'new_thresholds' in report:
            thresholds = report['new_thresholds']
            umbrales_metrics = {"ultimo_concurso_usado": ultimo_concurso, "umbral_pares": thresholds.get('pares', 0), "umbral_tercias": thresholds.get('tercias', 0), "umbral_cuartetos": thresholds.get('cuartetos', 0), "cobertura_historica": report.get('cobertura_historica', 0.0), "cobertura_universal_estimada": report.get('cobertura_universal_estimada', 0.0)}
            save_trajectory_data(db_path, 'umbrales_trayectoria', config.UMBRALES_TRAYECTORIA_SCHEMA, umbrales_metrics)
        else:
            logging.error(f"La optimización falló para el bloque hasta el sorteo {ultimo_concurso}.")
        
        logger.info(f"Bloque completado en {time.time() - iter_start_time:.2f} segundos.")

    logger.info("=" * 60)
    logger.info(f"GENERACIÓN DE TRAYECTORIA COMPLETA. Tiempo total: {(time.time() - script_start_time) / 60:.2f} minutos.")
    logger.info("=" * 60)

if __name__ == "__main__":
    game_id_arg = 'melate_retro'
    block_size_arg = 100

    if len(sys.argv) > 1:
        game_id_arg = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            block_size_arg = int(sys.argv[2])
        except ValueError:
            print("Error: El tamaño del bloque (segundo argumento) debe ser un número entero.")
            sys.exit(1)

    main(game_id=game_id_arg, block_size=block_size_arg)