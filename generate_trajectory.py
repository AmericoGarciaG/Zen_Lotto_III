import pandas as pd
import logging
import time
import sqlite3
import sys
import numpy as np
from collections import Counter
from itertools import combinations
from utils.logger_config import setup_logger
from modules import database as db
from modules import ml_optimizer
from modules.omega_logic import _calculate_subsequence_affinity
import config
import importlib
from typing import Dict, Any

# Forzar la re-lectura del archivo de configuración para evitar problemas de caché
importlib.reload(config)

setup_logger()
logger = logging.getLogger(__name__)


def prepare_database_for_trajectory():
    """
    BORRA y RECREA dinámicamente las tablas de trayectoria usando los esquemas de config.py.
    """
    logger.info("=" * 30)
    logger.info("FASE PREPARATORIA: Reconstruyendo Tablas de Trayectoria")
    logger.info("=" * 30)
    
    schemas = {
        'umbrales_trayectoria': config.UMBRALES_TRAYECTORIA_SCHEMA,
        'frecuencias_trayectoria': config.FRECUENCIAS_TRAYECTORIA_SCHEMA,
        'afinidades_trayectoria': config.AFINIDADES_TRAYECTORIA_SCHEMA,
        'freq_dist_trayectoria': config.FREQ_DIST_TRAYECTORIA_SCHEMA
    }
    
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE, timeout=10.0)
        cursor = conn.cursor()
        
        logger.info("Paso 1: Borrando tablas antiguas...")
        for table_name in schemas.keys():
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            logger.info(f"-> Comando DROP para '{table_name}' ejecutado.")
        
        conn.commit()

        logger.info("Paso 2: Recreando esquemas de tabla dinámicamente desde config.py...")
        for table_name, schema_dict in schemas.items():
            columns_def = ", ".join([f"{col_name} {col_type}" for col_name, col_type in schema_dict.items()])
            create_query = f"CREATE TABLE {table_name} ({columns_def});"
            cursor.execute(create_query)
            logger.info(f"-> Tabla '{table_name}' creada con éxito.")
            
        conn.commit()
        logger.info("PREPARACIÓN DE BASE DE DATOS COMPLETADA CON ÉXITO.")
        
    except Exception as e:
        logger.error(f"FALLO CRÍTICO al preparar la base de datos: {e}", exc_info=True)
        raise
    finally:
        if conn:
            conn.close()


def save_trajectory_data(table_name, schema_dict, data_dict):
    """
    Función genérica y dinámica para guardar datos en cualquier tabla de trayectoria.
    Utiliza el schema de config.py como única fuente de verdad.
    """
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE, timeout=10.0)
        cursor = conn.cursor()
        
        cols_to_insert = [col for col in schema_dict.keys() if col != 'fecha_calculo']
        
        column_names_sql = ", ".join(cols_to_insert) + ", fecha_calculo"
        placeholders_sql = ", ".join(["?"] * len(cols_to_insert)) + ", datetime('now', 'localtime')"

        query = f"INSERT OR REPLACE INTO {table_name} ({column_names_sql}) VALUES ({placeholders_sql})"
        
        # Construir la tupla de parámetros en el orden exacto definido por el schema
        params_tuple = tuple(data_dict[col] for col in cols_to_insert)

        cursor.execute(query, params_tuple)
        conn.commit()
    except KeyError as e:
        logger.error(f"KeyError guardando en '{table_name}'. Clave faltante: {e}. Diccionario: {data_dict.keys()}")
        raise
    except Exception as e:
        logger.error(f"Error guardando datos en '{table_name}': {e}")
    finally:
        if conn: conn.close()


def update_frequencies_incrementally(df_slice, master_freqs):
    freq_pairs, freq_triplets, freq_quartets = Counter(), Counter(), Counter()
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    for _, row in df_slice.iterrows():
        try:
            draw = sorted([int(row[col]) for col in result_columns])
            freq_pairs.update(combinations(draw, 2))
            freq_triplets.update(combinations(draw, 3))
            freq_quartets.update(combinations(draw, 4))
        except (ValueError, TypeError):
            continue
    master_freqs['pares'].update(freq_pairs)
    master_freqs['tercias'].update(freq_triplets)
    master_freqs['cuartetos'].update(freq_quartets)
    return master_freqs

def main(block_size=100):
    logger.info("=" * 60)
    logger.info("INICIANDO SCRIPT DE GENERACIÓN DE TRAYECTORIA (ARQUITECTURA DINÁMICA)")
    logger.info(f"Tamaño de bloque configurado: {block_size} sorteos")
    logger.info("=" * 60)
    
    prepare_database_for_trajectory()
    
    df_full_historico = db.read_historico_from_db()
    if df_full_historico.empty:
        logger.error("El histórico está vacío. Ejecute la configuración en la app primero.")
        return
        
    df_full_historico = df_full_historico.sort_values(by='concurso').reset_index(drop=True)
    total_sorteos = len(df_full_historico)
    
    start_point = 50 
    analysis_points = list(range(start_point, total_sorteos, block_size))
    if total_sorteos not in analysis_points:
        analysis_points.append(total_sorteos)

    logger.info(f"Se analizarán {len(analysis_points)} puntos de la trayectoria: {analysis_points}")
    
    script_start_time = time.time()
    
    master_frequencies = {'pares': Counter(), 'tercias': Counter(), 'cuartetos': Counter()}
    last_processed_index = 0
    
    for i, end_index in enumerate(analysis_points):
        iter_start_time = time.time()
        
        df_subset = df_full_historico.head(end_index)
        df_slice = df_full_historico.iloc[last_processed_index:end_index]
        last_processed_index = end_index
        
        ultimo_concurso = int(df_subset.iloc[-1]['concurso'])
        
        logger.info(f"--- Procesando Bloque {i+1}/{len(analysis_points)} (hasta concurso {ultimo_concurso}, {len(df_slice)} nuevos sorteos) ---")
        
        master_frequencies = update_frequencies_incrementally(df_slice, master_frequencies)
        
        # 1. Guardar métricas de CONTEO de frecuencias
        freq_count_metrics = {
            "ultimo_concurso_usado": ultimo_concurso,
            "total_pares_unicos": len(master_frequencies['pares']),
            "suma_freq_pares": sum(master_frequencies['pares'].values()),
            "total_tercias_unicos": len(master_frequencies['tercias']),
            "suma_freq_tercias": sum(master_frequencies['tercias'].values()),
            "total_cuartetos_unicos": len(master_frequencies['cuartetos']),
            "suma_freq_cuartetos": sum(master_frequencies['cuartetos'].values()),
        }
        save_trajectory_data('frecuencias_trayectoria', config.FRECUENCIAS_TRAYECTORIA_SCHEMA, freq_count_metrics)

        # 2. Guardar métricas de DISTRIBUCIÓN de valores de frecuencias
        # --- CORRECCIÓN CLAVE: Tipado explícito del diccionario ---
        freq_dist_metrics: Dict[str, Any] = {"ultimo_concurso_usado": ultimo_concurso}
        for level in ['pares', 'tercias', 'cuartetos']:
            values = list(master_frequencies[level].values())
            if not values: values = [0]
            freq_dist_metrics[f'freq_{level}_media'] = float(np.mean(values))
            freq_dist_metrics[f'freq_{level}_min'] = int(np.min(values))
            freq_dist_metrics[f'freq_{level}_max'] = int(np.max(values))
        save_trajectory_data('freq_dist_trayectoria', config.FREQ_DIST_TRAYECTORIA_SCHEMA, freq_dist_metrics)

        # 3. Guardar métricas de AFINIDADES
        afin_p, afin_t, afin_q = [], [], []
        for _, row in df_subset.iterrows():
            combo = sorted([int(row[col]) for col in ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']])
            afin_p.append(_calculate_subsequence_affinity(combo, master_frequencies, 2))
            afin_t.append(_calculate_subsequence_affinity(combo, master_frequencies, 3))
            afin_q.append(_calculate_subsequence_affinity(combo, master_frequencies, 4))
        
        affinity_metrics: Dict[str, Any] = {
            "ultimo_concurso_usado": ultimo_concurso,
            "afin_pares_media": float(np.mean(afin_p)), "afin_pares_mediana": float(np.median(afin_p)),
            "afin_pares_min": int(np.min(afin_p)), "afin_pares_max": int(np.max(afin_p)),
            "afin_tercias_media": float(np.mean(afin_t)), "afin_tercias_mediana": float(np.median(afin_t)),
            "afin_tercias_min": int(np.min(afin_t)), "afin_tercias_max": int(np.max(afin_t)),
            "afin_cuartetos_media": float(np.mean(afin_q)), "afin_cuartetos_mediana": float(np.median(afin_q)),
            "afin_cuartetos_min": int(np.min(afin_q)), "afin_cuartetos_max": int(np.max(afin_q)),
        }
        save_trajectory_data('afinidades_trayectoria', config.AFINIDADES_TRAYECTORIA_SCHEMA, affinity_metrics)

        # 4. Guardar UMBRALES
        freqs_for_optimizer = {k: dict(v) for k, v in master_frequencies.items()}
        success, _, report = ml_optimizer.run_optimization(df_subset, freqs_for_optimizer)
        if success and isinstance(report, dict) and 'new_thresholds' in report:
            thresholds = report['new_thresholds']
            umbrales_metrics: Dict[str, Any] = {
                "ultimo_concurso_usado": ultimo_concurso,
                "umbral_pares": int(thresholds.get('pares', 0)),
                "umbral_tercias": int(thresholds.get('tercias', 0)),
                "umbral_cuartetos": int(thresholds.get('cuartetos', 0)),
                "cobertura_historica": float(report.get('cobertura_historica', 0.0)),
                "cobertura_universal_estimada": float(report.get('cobertura_universal_estimada', 0.0)),
            }
            save_trajectory_data('umbrales_trayectoria', config.UMBRALES_TRAYECTORIA_SCHEMA, umbrales_metrics)
        else:
            logging.error(f"La optimización de umbrales falló para el bloque hasta el sorteo {ultimo_concurso}.")
        
        iter_time = time.time() - iter_start_time
        logger.info(f"Bloque completado en {iter_time:.2f} segundos.")

    script_total_time = time.time() - script_start_time
    logger.info("=" * 60)
    logger.info(f"GENERACIÓN DE TRAYECTORIA COMPLETA. Tiempo total: {script_total_time / 60:.2f} minutos.")
    logger.info("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            block_size_arg = int(sys.argv[1])
            main(block_size=block_size_arg)
        except ValueError:
            print("Error: El tamaño del bloque debe ser un número entero.")
            print("Uso: python generate_trajectory.py [tamaño_del_bloque]")
    else:
        main()