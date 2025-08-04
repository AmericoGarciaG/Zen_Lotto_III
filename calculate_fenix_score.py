# calculate_fenix_score.py

import pandas as pd
import numpy as np
import logging
import time
import sys
import importlib
from itertools import combinations
from functools import partial
import multiprocessing as mp
from typing import List, Dict, Any, Tuple
from collections import Counter

import config
from utils.logger_config import setup_logger
from utils.parallel_utils import NoDaemonPool
from modules import database as db
from modules import omega_logic as ol

importlib.reload(config)
setup_logger()
logger = logging.getLogger(__name__)

# _worker_calculate_fenix no necesita cambios
def _worker_calculate_fenix(combo_chunk: List[Tuple[int, ...]], trajectory_data: List[Tuple[Dict[str, Any], float]]) -> List[Dict[str, Any]]:
    fenix_results = []
    for combo in combo_chunk:
        historical_scores: List[float] = []
        for freqs_past, umbral_past in trajectory_data:
            af_p = ol._calculate_subsequence_affinity(list(combo), freqs_past, 2)
            score_at_t = (af_p - umbral_past) / (umbral_past or 1)
            historical_scores.append(score_at_t)
        
        fenix_score = np.std(historical_scores) if len(historical_scores) > 1 else 0.0
        result_row = {'combination': list(combo), 'fenix_score': float(fenix_score)}
        fenix_results.append(result_row)
    return fenix_results


def main(game_id: str):
    try:
        game_config = config.get_game_config(game_id)
    except ValueError as e:
        logger.error(f"Error: {e}."); return

    logger.info("="*60); logger.info(f"PROYECTO FÉNIX (MOTOR INCREMENTAL): Calculando Scores para: {game_config['display_name']}"); logger.info("="*60)

    db_path = game_config['paths']['db']
    n = game_config['n']
    db.add_fenix_score_column(db_path)

    logger.info("Construyendo motor de viaje en el tiempo (Incremental)...")
    df_historico_full = db.read_historico_from_db(db_path).sort_values(by='concurso').reset_index(drop=True)
    result_cols = game_config['data_source']['result_columns']
    
    # --- INICIO DE LA CORRECCIÓN ESTRUCTURAL ---
    START_POINT_ANALYSIS = 600
    df_base_hist = df_historico_full[df_historico_full['concurso'] < START_POINT_ANALYSIS]
    df_analysis_hist = df_historico_full[df_historico_full['concurso'] >= START_POINT_ANALYSIS].copy()
    
    # 1. Calcular el estado inicial una sola vez, ANTES del bucle.
    logger.info("Calculando estado base inicial (hasta sorteo 600)...")
    current_freqs = Counter(c for _, row in df_base_hist.iterrows() for c in combinations(sorted(row[result_cols]), 2))
    afinidades_list = [ol._calculate_subsequence_affinity(list(sorted(row[result_cols])), {'pares': current_freqs}, 2) for _, row in df_base_hist.iterrows()]
    
    trajectory_points: List[Tuple[Dict[str, Any], float]] = []
    total_points = len(df_analysis_hist)
    
    # 2. Bucle incremental que ahora funciona correctamente.
    logger.info(f"Iniciando construcción incremental de {total_points} puntos de trayectoria...")
    start_time_loop = time.time()

    for i, analysis_row in enumerate(df_analysis_hist.itertuples(index=False)):
        # Calcular el umbral basado en el estado *anterior*
        umbral_pares_past = float(np.percentile(afinidades_list, 20)) if afinidades_list else 0.0
        trajectory_points.append(({'pares': dict(current_freqs)}, umbral_pares_past))

        # Actualizar el estado con la información del sorteo actual
        current_combo = sorted([int(getattr(analysis_row, col)) for col in result_cols])
        current_freqs.update(combinations(current_combo, 2))
        afinidades_list.append(ol._calculate_subsequence_affinity(current_combo, {'pares': current_freqs}, 2))

        if (i + 1) % 50 == 0 or (i + 1) == total_points:
            logger.info(f"  -> Motor: Procesado punto {i + 1}/{total_points}...")

    end_time_loop = time.time()
    logger.info(f"Motor de viaje en el tiempo construido en {end_time_loop - start_time_loop:.2f} segundos con {len(trajectory_points)} puntos.")
    # --- FIN DE LA CORRECCIÓN ESTRUCTURAL ---

    # El resto del script ya es eficiente y utiliza el paralelismo
    logger.info("Cargando combinaciones de la Clase Omega para evaluar...")
    df_omega_class = db.read_full_omega_class(db_path)
    combinations_to_eval = [tuple(row) for row in df_omega_class[[f'c{i}' for i in range(1, n + 1)]].values]

    n_processes = mp.cpu_count()
    chunk_size = (len(combinations_to_eval) + n_processes - 1) // n_processes
    chunks: List[List[Tuple[int, ...]]] = [combinations_to_eval[i:i + chunk_size] for i in range(0, len(combinations_to_eval), chunk_size)]
    worker_func = partial(_worker_calculate_fenix, trajectory_data=trajectory_points)

    logger.info(f"Iniciando cálculo paralelo de {len(combinations_to_eval)} Fenix Scores en {n_processes} procesos...")
    script_start_time = time.time()
    all_results: List[Dict[str, Any]] = []
    
    with NoDaemonPool(processes=n_processes) as pool:
        for i, result_chunk in enumerate(pool.imap(worker_func, chunks)):
            all_results.extend(result_chunk)
            logger.info(f"  -> Paralelo: Procesado lote {i + 1}/{len(chunks)}...")

    df_fenix_scores = pd.DataFrame(all_results)
    logger.info("Cálculo paralelo completado. Guardando resultados...")
    db.update_fenix_scores_in_db(db_path, df_fenix_scores, game_config)
    
    logger.info("="*60); logger.info(f"PROYECTO FÉNIX COMPLETO. Tiempo total: {(time.time() - start_time_loop) / 60:.2f} minutos."); logger.info("="*60)

if __name__ == "__main__":
    main('melate_retro')