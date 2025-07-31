# omega_logic.py

import json
from collections import Counter
from itertools import combinations, islice
import logging
from math import factorial
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from functools import partial
import multiprocessing as mp
import os

from utils.parallel_utils import NoDaemonPool
from modules import database as db
from utils import state_manager

logger = logging.getLogger(__name__)

# --- FUNCIONES DE AYUDA (Sin cambios) ---
def get_frequencies(game_config: Dict[str, Any]) -> Optional[Dict[str, Dict[tuple, int]]]:
    freq_file = game_config['paths']['frequencies']
    try:
        with open(freq_file, 'r', encoding='utf-8') as f: data = json.load(f)
        return {"pares": {eval(k): v for k, v in data.get("FREQ_PARES", {}).items()}, "tercias": {eval(k): v for k, v in data.get("FREQ_TERCIAS", {}).items()}, "cuartetos": {eval(k): v for k, v in data.get("FREQ_CUARTETOS", {}).items()}}
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"No se pudo cargar el archivo de frecuencias: {freq_file}"); return None

def get_loaded_thresholds(game_config: Dict[str, Any]) -> Dict[str, int]:
    thresholds_file = game_config['paths']['thresholds']
    try:
        with open(thresholds_file, 'r', encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"No se encontró '{thresholds_file}'. Usando valores por defecto."); return game_config['omega_config']['default_thresholds']

def get_historical_draws_set(game_config: Dict[str, Any]) -> set:
    db_path = game_config['paths']['db']
    df_historico = db.read_historico_from_db(db_path)
    if df_historico.empty: return set()
    result_columns = game_config['data_source']['result_columns']
    valid_columns = [col for col in result_columns if col in df_historico.columns]
    if not valid_columns: return set()
    np_draws = df_historico[valid_columns].to_numpy()
    return {tuple(sorted(row)) for row in np_draws}

def _calculate_subsequence_affinity(combination: List[int], freqs: Dict, size: int) -> int:
    key_map = {2: "pares", 3: "tercias", 4: "cuartetos"}
    if not freqs or key_map[size] not in freqs: return 0
    total_affinity = 0
    freq_map = freqs[key_map[size]]
    for sub in combinations(sorted(combination), size): total_affinity += freq_map.get(sub, 0)
    return total_affinity

def evaluate_combination(combination: List[int], freqs: Dict, game_config: Dict[str, Any], loaded_thresholds: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    n = game_config['n']
    if not isinstance(combination, list) or len(set(combination)) != n: return {"error": f"Entrada inválida. Se esperan {n} números únicos."}
    thresholds = loaded_thresholds if loaded_thresholds is not None else get_loaded_thresholds(game_config)
    weights = game_config['omega_config']['score_weights']
    af_p = _calculate_subsequence_affinity(combination, freqs, 2)
    af_t = _calculate_subsequence_affinity(combination, freqs, 3)
    af_q = _calculate_subsequence_affinity(combination, freqs, 4)
    c_p = af_p >= thresholds.get('pares', 0)
    c_t = af_t >= thresholds.get('tercias', 0)
    c_q = af_q >= thresholds.get('cuartetos', 0)
    es_omega = all([c_p, c_t, c_q])
    s_p = ((af_p - thresholds.get('pares', 0)) / (thresholds.get('pares', 1) or 1)) * weights.get('pares', 0)
    s_t = ((af_t - thresholds.get('tercias', 0)) / (thresholds.get('tercias', 1) or 1)) * weights.get('tercias', 0)
    s_q = ((af_q - thresholds.get('cuartetos', 0)) / (thresholds.get('cuartetos', 1) or 1)) * weights.get('cuartetos', 0)
    omega_score = s_p + s_t + s_q
    historical_set = game_config.get('_historical_set_cache')
    if historical_set is None:
        historical_set = get_historical_draws_set(game_config)
        game_config['_historical_set_cache'] = historical_set
    ha_salido = tuple(sorted(combination)) in historical_set
    return {"error": None, "esOmega": es_omega, "omegaScore": omega_score, "haSalido": ha_salido, "combinacion": sorted(combination), "afinidadPares": af_p, "afinidadTercias": af_t, "afinidadCuartetos": af_q, "criterios": {"pares": {"cumple": c_p, "score": af_p, "umbral": thresholds.get('pares', 0)}, "tercias": {"cumple": c_t, "score": af_t, "umbral": thresholds.get('tercias', 0)}, "cuartetos": {"cumple": c_q, "score": af_q, "umbral": thresholds.get('cuartetos', 0)}}}

def calculate_and_save_frequencies(game_config: Dict[str, Any]) -> Tuple[bool, str]:
    # (sin cambios)
    logger.info(f"Iniciando cálculo de frecuencias para '{game_config['display_name']}'.")
    state_file, freq_file, db_path = game_config['paths']['state'], game_config['paths']['frequencies'], game_config['paths']['db']
    result_columns, affinity_levels = game_config['data_source']['result_columns'], game_config['omega_config']['affinity_levels']
    state = state_manager.get_state(state_file)
    last_processed_concurso = state.get("last_concurso_for_freqs", 0)
    df_historico = db.read_historico_from_db(db_path)
    if df_historico.empty: return False, "La base de datos del juego está vacía."
    df_new_draws = df_historico[df_historico['concurso'] > last_processed_concurso].copy()
    if df_new_draws.empty: return True, "Las frecuencias ya están actualizadas."
    freqs_data = get_frequencies(game_config) or {}
    freq_counters = {2: Counter(freqs_data.get("pares", {})), 3: Counter(freqs_data.get("tercias", {})), 4: Counter(freqs_data.get("cuartetos", {}))}
    for _, row in df_new_draws.iterrows():
        try:
            draw = sorted([int(row[col]) for col in result_columns])
            for level in affinity_levels: freq_counters[level].update(combinations(draw, level))
        except (ValueError, TypeError):
            logger.warning(f"Omitiendo fila con datos inválidos en el histórico: {row.get('concurso')}")
            continue
    new_last_processed_concurso = int(df_new_draws['concurso'].max())
    output_data = {"FREQ_PARES": {str(k): v for k, v in freq_counters[2].items()}, "FREQ_TERCIAS": {str(k): v for k, v in freq_counters[3].items()}, "FREQ_CUARTETOS": {str(k): v for k, v in freq_counters[4].items()}}
    try:
        with open(freq_file, 'w', encoding='utf-8') as f: json.dump(output_data, f, indent=4)
        state["last_concurso_for_freqs"] = new_last_processed_concurso
        state_manager.save_state(state, state_file)
        return True, f"Frecuencias para '{game_config['display_name']}' actualizadas con {len(df_new_draws)} nuevos sorteos."
    except Exception as e: return False, f"Error al guardar archivo de frecuencias para '{game_config['display_name']}': {e}"

# --- SECCIÓN DE ENRIQUECIMIENTO PARALELO (CORREGIDA) ---

def _worker_enrich(df_chunk: pd.DataFrame, freqs: Dict, game_config: Dict[str, Any], loaded_thresholds: Dict[str, int]) -> List[Dict]:
    """Worker para enriquecer un lote del DataFrame histórico."""
    result_columns = game_config['data_source']['result_columns']
    resultados_chunk = []
    
    for _, row in df_chunk.iterrows():
        try:
            combination = [int(row[col]) for col in result_columns] # type: ignore
            eval_result = evaluate_combination(combination, freqs, game_config, loaded_thresholds)
            
            if eval_result.get("error"): continue

            resultados_chunk.append({
                'concurso': row['concurso'],
                'es_omega': 1 if eval_result["esOmega"] else 0,
                'omega_score': round(eval_result["omegaScore"], 4),
                'afinidad_cuartetos': eval_result["afinidadCuartetos"],
                'afinidad_tercias': eval_result["afinidadTercias"],
                'afinidad_pares': eval_result["afinidadPares"],
            })
        except (ValueError, TypeError):
            continue
            
    return resultados_chunk

def enrich_historical_data(game_config: Dict[str, Any], set_progress=None) -> Tuple[bool, str]:
    from dash import no_update
    
    logger.info(f"Iniciando enriquecimiento paralelo para '{game_config['display_name']}'.")
    db_path = game_config['paths']['db']
    
    df_historico = db.read_historico_from_db(db_path)
    freqs = get_frequencies(game_config)
    loaded_thresholds = get_loaded_thresholds(game_config)
    
    if df_historico.empty or freqs is None:
        return False, "No se puede enriquecer. Faltan datos base."
        
    n_processes = mp.cpu_count()
    
    # --- CORRECCIÓN: Dividir los índices del DataFrame en lugar del DataFrame en sí ---
    indices = np.array_split(df_historico.index, n_processes)
    df_chunks = [df_historico.loc[idx] for idx in indices if not idx.empty] # type: ignore
    # --- FIN CORRECCIÓN ---
    
    worker_func = partial(_worker_enrich, freqs=freqs, game_config=game_config, loaded_thresholds=loaded_thresholds)
    
    all_results = []
    processed_count = 0
    total_rows = len(df_historico)
    
    with NoDaemonPool(processes=n_processes) as pool:
        for i, result_chunk in enumerate(pool.imap_unordered(worker_func, df_chunks)):
            all_results.extend(result_chunk)
            processed_count += len(df_chunks[i])
            if set_progress:
                progress = int((processed_count / total_rows) * 100)
                set_progress((progress, f"Enriqueciendo: {processed_count}/{total_rows}", no_update, no_update, no_update, no_update, no_update, no_update))

    df_omega_stats = pd.DataFrame(all_results)
    
    if 'bolsa' in df_historico.columns and df_historico['bolsa'].max() > 5000000:
        df_sorted = df_historico.sort_values(by='concurso', ascending=True)
        df_sorted['bolsa_ganada'] = df_sorted['bolsa'].shift(1).fillna(0)
        df_sorted['es_ganador'] = (df_sorted['bolsa'] == 5000000).astype(int)
        df_final = df_sorted.sort_values(by='concurso', ascending=False)
    else:
        df_historico['es_ganador'], df_historico['bolsa_ganada'] = 0, 0
        df_final = df_historico
        
    cols_to_drop = [c for c in df_omega_stats.columns if c in df_final.columns and c != 'concurso']
    df_to_merge = df_final.drop(columns=cols_to_drop, errors='ignore')
    
    df_enriquecido = pd.merge(df_to_merge, df_omega_stats, on='concurso', how='left') if not df_omega_stats.empty else df_to_merge
        
    success, message = db.save_historico_to_db(df_enriquecido, db_path, mode='replace')
    return success, f"Enriquecimiento para '{game_config['display_name']}' completado. {message}"

# --- SECCIÓN DE PRE-GENERACIÓN DE ALTO RENDIMIENTO (CORREGIDA) ---

def _worker_pregenerate(combo_chunk: List[tuple], freqs: Dict, thresholds: Dict[str, int], historical_set: set) -> List[Dict]:
    pid = os.getpid()
    logger.info(f"[Worker PID: {pid}] Procesando un lote de {len(combo_chunk)} combinaciones.")
    omega_list_chunk = []
    for combo in combo_chunk:
        af_p = sum(freqs['pares'].get(par, 0) for par in combinations(combo, 2))
        if af_p < thresholds['pares']: continue
            
        # --- CORRECCIÓN: Usar 'terc' en lugar de 'ter' ---
        af_t = sum(freqs['tercias'].get(terc, 0) for terc in combinations(combo, 3))
        if af_t < thresholds['tercias']: continue

        af_q = sum(freqs['cuartetos'].get(cuart, 0) for cuart in combinations(combo, 4))
        if af_q < thresholds['cuartetos']: continue
            
        data = {f'c{j+1}': num for j, num in enumerate(combo)}
        data.update({'ha_salido': 1 if combo in historical_set else 0, 'afinidad_pares': af_p, 'afinidad_tercias': af_t, 'afinidad_cuartetos': af_q})
        omega_list_chunk.append(data)
    return omega_list_chunk

# ... (El resto del archivo, pregenerate_omega_class y deconstruct_affinity, se mantiene sin cambios)
def pregenerate_omega_class(game_config: Dict[str, Any], set_progress=None) -> Tuple[bool, str]:
    from dash import no_update
    logger.info(f"Verificando pre-generación para '{game_config['display_name']}'.")
    state = state_manager.get_state(game_config['paths']['state'])
    last_opt, last_omega = state.get("last_concurso_for_optimization", 0), state.get("last_concurso_for_omega_class", -1)
    if last_opt > 0 and last_opt == last_omega: return True, "Pre-generación ya está actualizada."
    freqs = get_frequencies(game_config)
    if freqs is None: return False, "Faltan frecuencias para pre-generar."
    thresholds = get_loaded_thresholds(game_config)
    historical_draws_set = get_historical_draws_set(game_config)
    n, k = game_config['n'], game_config['k']
    total_combinations = factorial(k) // (factorial(n) * factorial(k - n))
    if set_progress: set_progress((5, f"Iniciando pre-generación de {total_combinations:,} combinaciones...", no_update, no_update, no_update, no_update, no_update, no_update))
    all_possible_combinations = combinations(range(1, k + 1), n)
    n_processes = mp.cpu_count()
    chunk_size = (total_combinations + n_processes - 1) // n_processes
    worker_func = partial(_worker_pregenerate, freqs=freqs, thresholds=thresholds, historical_set=historical_draws_set)
    omega_list = []
    processed_count = 0
    with NoDaemonPool(processes=n_processes) as pool:
        def chunk_generator(it, size):
            iterator = iter(it)
            while True:
                chunk = list(islice(iterator, size))
                if not chunk: break
                yield chunk
        for i, result_chunk in enumerate(pool.imap_unordered(worker_func, chunk_generator(all_possible_combinations, chunk_size))):
            omega_list.extend(result_chunk)
            processed_count += chunk_size
            if set_progress:
                progress = 5 + int((min(processed_count, total_combinations) / total_combinations) * 90)
                set_progress((progress, f"Pre-generando: {min(processed_count, total_combinations):,}/{total_combinations:,}", no_update, no_update, no_update, no_update, no_update, no_update))
    if set_progress: set_progress((95, "Guardando resultados...", no_update, no_update, no_update, no_update, no_update, no_update))
    omega_df = pd.DataFrame(omega_list)
    success, message = db.save_omega_class(omega_df, game_config['paths']['db'])
    if success:
        state["last_concurso_for_omega_class"] = state.get("last_concurso_for_optimization", 0)
        state_manager.save_state(state, game_config['paths']['state'])
    return success, f"Pre-generación para '{game_config['display_name']}' completada. {message}"

def deconstruct_affinity(combination: List[int], omega_score: float, game_config: Dict[str, Any]) -> Dict[str, Any]:
    freqs = get_frequencies(game_config)
    if not freqs: return {"error": "Frecuencias no disponibles."}
    loaded_thresholds = get_loaded_thresholds(game_config)
    eval_result = evaluate_combination(combination, freqs, game_config, loaded_thresholds)
    if eval_result.get("error"): return eval_result
    breakdown = {}
    for level, name in [(2, "pares"), (3, "tercias"), (4, "cuartetos")]:
        if level in game_config['omega_config']['affinity_levels']:
            subs = list(combinations(sorted(combination), level))
            freq_map = freqs.get(name, {})
            breakdown_list = [{"subsequence": str(s), "frequency": freq_map.get(s, 0)} for s in subs]
            breakdown[name] = sorted(breakdown_list, key=lambda x: x["frequency"], reverse=True)
    return {"combination": eval_result.get("combinacion"), "omega_score": omega_score, "totals": {"pares": eval_result.get("afinidadPares"), "tercias": eval_result.get("afinidadTercias"), "cuartetos": eval_result.get("afinidadCuartetos")}, "breakdown": breakdown, "error": None}