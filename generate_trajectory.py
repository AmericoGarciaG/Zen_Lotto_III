import pandas as pd
import logging
import time
import sqlite3
import sys
import numpy as np
import multiprocessing as mp
from utils.logger_config import setup_logger
from utils.parallel_utils import NoDaemonPool
from modules import database as db
from modules import ml_optimizer
from modules.omega_logic import _calculate_subsequence_affinity
import config

setup_logger()
logger = logging.getLogger(__name__)

def calculate_frequencies_for_subset(df_subset):
    from collections import Counter
    from itertools import combinations
    freq_pairs, freq_triplets, freq_quartets = Counter(), Counter(), Counter()
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    for _, row in df_subset.iterrows():
        try:
            draw = sorted([int(row[col]) for col in result_columns])
            freq_pairs.update(combinations(draw, 2))
            freq_triplets.update(combinations(draw, 3))
            freq_quartets.update(combinations(draw, 4))
        except (ValueError, TypeError): continue
    return {
        "pares": dict(freq_pairs),
        "tercias": dict(freq_triplets),
        "cuartetos": dict(freq_quartets)
    }

def save_trajectory_point(concurso_num, report):
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        query = """
            INSERT OR REPLACE INTO umbrales_trayectoria 
            (ultimo_concurso_usado, umbral_pares, umbral_tercias, umbral_cuartetos, 
             cobertura_historica, cobertura_universal_estimada, fecha_calculo)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """
        thresholds = report['new_thresholds']
        params = (
            int(concurso_num), int(thresholds.get('pares', 0)),
            int(thresholds.get('tercias', 0)), int(thresholds.get('cuartetos', 0)),
            float(report.get('cobertura_historica', 0.0)),
            float(report.get('cobertura_universal_estimada', 0.0))
        )
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"Error guardando punto de trayectoria de umbrales para {concurso_num}: {e}")
    finally:
        if conn: conn.close()

def save_frequency_trajectory_point(concurso_num, metrics):
    """Guarda las métricas de CONTEO de frecuencias en la BD."""
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        query = """
            INSERT OR REPLACE INTO frecuencias_trayectoria 
            (ultimo_concurso_usado, total_pares_unicos, suma_freq_pares, 
             total_tercias_unicas, suma_freq_tercias, total_cuartetos_unicos, 
             suma_freq_cuartetos, fecha_calculo)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """
        params = (
            int(concurso_num),
            metrics['total_pares_unicos'], metrics['suma_freq_pares'],
            metrics['total_tercias_unicas'], metrics['suma_freq_tercias'],
            metrics['total_cuartetos_unicos'], metrics['suma_freq_cuartetos']
        )
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"Error guardando punto de trayectoria de frecuencias para {concurso_num}: {e}")
    finally:
        if conn: conn.close()

def save_affinity_trajectory_point(concurso_num, stats):
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        query = """
            INSERT OR REPLACE INTO afinidades_trayectoria 
            (ultimo_concurso_usado, afin_pares_media, afin_pares_mediana, afin_pares_min, afin_pares_max, 
             afin_tercias_media, afin_tercias_mediana, afin_tercias_min, afin_tercias_max, 
             afin_cuartetos_media, afin_cuartetos_mediana, afin_cuartetos_min, afin_cuartetos_max, fecha_calculo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """
        params = (
            int(concurso_num),
            stats['pares']['media'], stats['pares']['mediana'], stats['pares']['min'], stats['pares']['max'],
            stats['tercias']['media'], stats['tercias']['mediana'], stats['tercias']['min'], stats['tercias']['max'],
            stats['cuartetos']['media'], stats['cuartetos']['mediana'], stats['cuartetos']['min'], stats['cuartetos']['max']
        )
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"Error guardando punto de trayectoria de afinidades para {concurso_num}: {e}")
    finally:
        if conn: conn.close()

def save_freq_dist_trajectory_point(concurso_num, stats):
    """Guarda las estadísticas de la distribución de valores de frecuencias en la BD."""
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        query = """
            INSERT OR REPLACE INTO freq_dist_trayectoria 
            (ultimo_concurso_usado, freq_pares_media, freq_pares_min, freq_pares_max, 
             freq_tercias_media, freq_tercias_min, freq_tercias_max, 
             freq_cuartetos_media, freq_cuartetos_min, freq_cuartetos_max, fecha_calculo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """
        params = (
            int(concurso_num),
            stats['pares']['media'], stats['pares']['min'], stats['pares']['max'],
            stats['tercias']['media'], stats['tercias']['min'], stats['tercias']['max'],
            stats['cuartetos']['media'], stats['cuartetos']['min'], stats['cuartetos']['max']
        )
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"Error guardando punto de trayectoria de dist. de freqs para {concurso_num}: {e}")
    finally:
        if conn: conn.close()

def process_trajectory_block(args):
    """Función trabajadora que procesa un único bloque de la trayectoria."""
    end_index, df_full_historico = args
    iter_start_time = time.time()
    df_subset = df_full_historico.head(end_index)
    ultimo_concurso = int(df_subset.iloc[-1]['concurso'])
    
    logging.info(f"--- [Worker] Iniciando bloque hasta concurso {ultimo_concurso} ({end_index} sorteos) ---")
    
    # 1. CÁLCULO DE FRECUENCIAS
    freqs_subset = calculate_frequencies_for_subset(df_subset)
    
    # 1A. Guardar métricas de CONTEO de frecuencias
    freq_count_metrics = {
        'total_pares_unicos': len(freqs_subset['pares']), 'suma_freq_pares': sum(freqs_subset['pares'].values()),
        'total_tercias_unicas': len(freqs_subset['tercias']), 'suma_freq_tercias': sum(freqs_subset['tercias'].values()),
        'total_cuartetos_unicos': len(freqs_subset['cuartetos']), 'suma_freq_cuartetos': sum(freqs_subset['cuartetos'].values())
    }
    save_frequency_trajectory_point(ultimo_concurso, freq_count_metrics)

    # 1B. Guardar métricas de DISTRIBUCIÓN de valores de frecuencias
    freq_dist_stats = {}
    for level in ['pares', 'tercias', 'cuartetos']:
        values = list(freqs_subset[level].values())
        if not values:
            values = [0]
        freq_dist_stats[level] = {
            'media': float(np.mean(values)),
            'min': int(np.min(values)),
            'max': int(np.max(values))
        }
    save_freq_dist_trajectory_point(ultimo_concurso, freq_dist_stats)
    
    # 2. CÁLCULO DE AFINIDADES
    afin_p, afin_t, afin_q = [], [], []
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    for _, row in df_subset.iterrows():
        combo = sorted([int(row[col]) for col in result_columns])
        afin_p.append(_calculate_subsequence_affinity(combo, freqs_subset, 2))
        afin_t.append(_calculate_subsequence_affinity(combo, freqs_subset, 3))
        afin_q.append(_calculate_subsequence_affinity(combo, freqs_subset, 4))
    
    affinity_stats = {
        'pares': {'media': float(np.mean(afin_p)), 'mediana': float(np.median(afin_p)), 'min': int(np.min(afin_p)), 'max': int(np.max(afin_p))},
        'tercias': {'media': float(np.mean(afin_t)), 'mediana': float(np.median(afin_t)), 'min': int(np.min(afin_t)), 'max': int(np.max(afin_t))},
        'cuartetos': {'media': float(np.mean(afin_q)), 'mediana': float(np.median(afin_q)), 'min': int(np.min(afin_q)), 'max': int(np.max(afin_q))}
    }
    save_affinity_trajectory_point(ultimo_concurso, affinity_stats)
    
    # 3. CÁLCULO DE UMBRALES
    success, _, report = ml_optimizer.run_optimization(df_subset, freqs_subset)
    if success and isinstance(report, dict) and 'new_thresholds' in report:
        save_trajectory_point(ultimo_concurso, report)
    else:
        logging.error(f"La optimización de umbrales falló para el bloque hasta el sorteo {ultimo_concurso}.")
    
    iter_time = time.time() - iter_start_time
    logging.info(f"--- [Worker] Bloque hasta concurso {ultimo_concurso} completado en {iter_time:.2f} segundos. ---")
    return True

def main(block_size=100):
    logger.info("="*60)
    logger.info("INICIANDO SCRIPT DE GENERACIÓN DE TRAYECTORIA (ARQUITECTURA ANIDADA)")
    logger.info(f"Tamaño de bloque configurado: {block_size} sorteos")
    logger.info("="*60)
    
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

    logger.info(f"Se analizarán {len(analysis_points)} puntos de la trayectoria en paralelo.")
    
    worker_args = [(point, df_full_historico) for point in analysis_points]
    
    script_start_time = time.time()
    
    n_processes = min(mp.cpu_count(), 16)
    logger.info(f"Creando un Pool NoDaemon con {n_processes} procesos...")
    
    with NoDaemonPool(processes=n_processes) as pool:
        results = pool.map(process_trajectory_block, worker_args)

    if all(results):
        logger.info("Todos los bloques de la trayectoria se procesaron con éxito.")
    else:
        logger.warning("Algunos bloques de la trayectoria pudieron haber fallado. Revise los logs.")

    script_total_time = time.time() - script_start_time
    logger.info("="*60)
    logger.info(f"GENERACIÓN DE TRAYECTORIA COMPLETA. Tiempo total: {script_total_time / 60:.2f} minutos.")
    logger.info("="*60)

if __name__ == "__main__":
    mp.freeze_support()
    
    if len(sys.argv) > 1:
        try:
            block_size_arg = int(sys.argv[1])
            main(block_size=block_size_arg)
        except ValueError:
            print("Error: El tamaño del bloque debe ser un número entero.")
            print("Uso: python generate_trajectory.py [tamaño_del_bloque]")
    else:
        main()