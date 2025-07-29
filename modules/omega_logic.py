import json
from collections import Counter
from itertools import combinations
import logging
from math import factorial
import pandas as pd
import modules.database as db
import config
from utils import state_manager

logger = logging.getLogger(__name__)

_historical_draws_set_cache = None

def _get_historical_draws_set():
    """
    Carga y cachea el set de combinaciones históricas para una comprobación rápida.
    """
    global _historical_draws_set_cache
    if _historical_draws_set_cache is not None:
        return _historical_draws_set_cache
    
    logger.info("Caching historical draws set for the first time...")
    df_historico = db.read_historico_from_db()
    if df_historico.empty:
        _historical_draws_set_cache = set()
    else:
        result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
        # Convertimos a numpy para velocidad, ordenamos y convertimos a tupla para el set
        np_draws = df_historico[result_columns].to_numpy()
        _historical_draws_set_cache = {tuple(sorted(row)) for row in np_draws}
    
    logger.info(f"Cached {len(_historical_draws_set_cache)} historical draws.")
    return _historical_draws_set_cache

_frequencies_cache = None
def get_frequencies():
    global _frequencies_cache
    if _frequencies_cache is not None: return _frequencies_cache
    try:
        with open(config.FREQUENCIES_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        _frequencies_cache = {
            "pares": {eval(k): v for k, v in data.get("FREQ_PARES", {}).items()},
            "tercias": {eval(k): v for k, v in data.get("FREQ_TERCIAS", {}).items()},
            "cuartetos": {eval(k): v for k, v in data.get("FREQ_CUARTETOS", {}).items()}
        }
        return _frequencies_cache
    except (FileNotFoundError, json.JSONDecodeError): return None

def _calculate_subsequence_affinity(combination, freqs, size):
    key_map = {2: "pares", 3: "tercias", 4: "cuartetos"}
    if not freqs or key_map[size] not in freqs: return 0
    total_affinity = 0
    subsequences = combinations(sorted(combination), size)
    freq_map = freqs[key_map[size]]
    for sub in subsequences: total_affinity += freq_map.get(sub, 0)
    return total_affinity

def evaluate_combination(combination, freqs):
    """
    Evalúa una combinación y también comprueba si ha salido históricamente.
    """
    if not isinstance(combination, list) or len(set(combination)) != 6: return {"error": "Entrada inválida."}
    af_p = _calculate_subsequence_affinity(combination, freqs, 2)
    af_t = _calculate_subsequence_affinity(combination, freqs, 3)
    af_q = _calculate_subsequence_affinity(combination, freqs, 4)
    c_p = af_p >= config.UMBRAL_PARES
    c_t = af_t >= config.UMBRAL_TERCIAS
    c_q = af_q >= config.UMBRAL_CUARTETOS
    es_omega = sum([c_p, c_t, c_q]) == 3
    s_q = ((af_q - config.UMBRAL_CUARTETOS) / config.UMBRAL_CUARTETOS) * 0.5 if config.UMBRAL_CUARTETOS > 0 else 0
    s_t = ((af_t - config.UMBRAL_TERCIAS) / config.UMBRAL_TERCIAS) * 0.3 if config.UMBRAL_TERCIAS > 0 else 0
    s_p = ((af_p - config.UMBRAL_PARES) / config.UMBRAL_PARES) * 0.2 if config.UMBRAL_PARES > 0 else 0

    historical_set = _get_historical_draws_set()
    ha_salido = tuple(sorted(combination)) in historical_set

    return {
        "error": None, "esOmega": es_omega, "omegaScore": s_q + s_t + s_p, "haSalido": ha_salido,
        "combinacion": sorted(combination), "afinidadPares": af_p, "afinidadTercias": af_t, "afinidadCuartetos": af_q,
        "criterios": {"pares": {"cumple": c_p, "score": af_p, "umbral": config.UMBRAL_PARES},
                      "tercias": {"cumple": c_t, "score": af_t, "umbral": config.UMBRAL_TERCIAS},
                      "cuartetos": {"cumple": c_q, "score": af_q, "umbral": config.UMBRAL_CUARTETOS}}
    }

def C(n, k): return factorial(n) // (factorial(k) * factorial(n - k))

# --- FUNCIÓN CORREGIDA ---
def calculate_and_save_frequencies():
    logger.info("Iniciando el cálculo/actualización de frecuencias.")
    state = state_manager.get_state()
    last_processed_concurso = state.get("last_concurso_for_freqs", 0)
    df_historico = db.read_historico_from_db()
    if df_historico.empty: return False, "La base de datos está vacía."
    df_new_draws = df_historico[df_historico['concurso'] > last_processed_concurso].copy()
    if df_new_draws.empty: return True, "Las frecuencias ya están actualizadas."
    freqs_data = get_frequencies() or {}
    freq_pairs, freq_triplets, freq_quartets = Counter(freqs_data.get("pares", {})), Counter(freqs_data.get("tercias", {})), Counter(freqs_data.get("cuartetos", {}))
    all_new_pairs, all_new_triplets, all_new_quartets = [], [], []
    for _, row in df_new_draws.iterrows():
        draw = sorted([int(row[col]) for col in ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']])
        all_new_pairs.extend(list(combinations(draw, 2)))
        all_new_triplets.extend(list(combinations(draw, 3)))
        all_new_quartets.extend(list(combinations(draw, 4)))
    freq_pairs.update(all_new_pairs); freq_triplets.update(all_new_triplets); freq_quartets.update(all_new_quartets)
    new_last_processed_concurso = int(df_new_draws['concurso'].max())
    output_data = {"FREQ_PARES": {str(k): v for k, v in freq_pairs.items()}, "FREQ_TERCIAS": {str(k): v for k, v in freq_triplets.items()}, "FREQ_CUARTETOS": {str(k): v for k, v in freq_quartets.items()}}
    try:
        with open(config.FREQUENCIES_FILE, 'w', encoding='utf-8') as f: json.dump(output_data, f, indent=4)
        state["last_concurso_for_freqs"] = new_last_processed_concurso
        state_manager.save_state(state)
        return True, f"Frecuencias actualizadas con éxito usando {len(df_new_draws)} nuevos sorteos."
    except Exception as e: return False, f"Error al guardar archivo de frecuencias: {e}"

def enrich_historical_data(set_progress=None):
    """
    Calcula todas las métricas para el histórico y las guarda en la BD,
    reportando el progreso si se proporciona una función de callback.
    """
    # Importar no_update dentro de la función para mantener los módulos desacoplados
    from dash import no_update
    from modules.database import read_historico_from_db, TABLE_NAME_HISTORICO
    import sqlite3

    logger.info("Iniciando el enriquecimiento de datos históricos...")
    
    df_historico = read_historico_from_db()
    freqs = get_frequencies()

    if df_historico.empty or freqs is None:
        return False, "No se puede enriquecer. Faltan datos base."

    resultados_omega = []
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    total_rows = len(df_historico)
    
    for i, (_, row) in enumerate(df_historico.iterrows()):
        try:
            combination = [int(row[col]) for col in result_columns]
        except (ValueError, TypeError):
            continue

        eval_result = evaluate_combination(combination, freqs)
        
        af_q, af_t, af_p, es_omega_val = 0, 0, 0, 0
        omega_score = 0.0

        if isinstance(eval_result, dict) and not eval_result.get("error"):
            try:
                af_q = int(eval_result.get('afinidadCuartetos', 0))
                af_t = int(eval_result.get('afinidadTercias', 0))
                af_p = int(eval_result.get('afinidadPares', 0))
                es_omega_val = 1 if eval_result.get("esOmega") else 0
                
                score_q = ((af_q - config.UMBRAL_CUARTETOS) / config.UMBRAL_CUARTETOS) * 0.5 if config.UMBRAL_CUARTETOS > 0 else 0
                score_t = ((af_t - config.UMBRAL_TERCIAS) / config.UMBRAL_TERCIAS) * 0.3 if config.UMBRAL_TERCIAS > 0 else 0
                score_p = ((af_p - config.UMBRAL_PARES) / config.UMBRAL_PARES) * 0.2 if config.UMBRAL_PARES > 0 else 0
                omega_score = score_q + score_t + score_p
            except (TypeError, ValueError):
                pass
        
        resultados_omega.append({
            'concurso': row['concurso'], 'es_omega': es_omega_val,
            'omega_score': round(omega_score, 4), 'afinidad_cuartetos': af_q,
            'afinidad_tercias': af_t, 'afinidad_pares': af_p
        })
        
        # Llama a set_progress con la tupla completa de 7 elementos
        if set_progress and (i + 1) % 100 == 0:
            progress = int(((i + 1) / total_rows) * 50)
            set_progress((
                progress, f"Enriqueciendo: {i+1}/{total_rows}", 
                no_update, no_update, no_update, no_update, no_update
            ))
            
    df_omega_stats = pd.DataFrame(resultados_omega)

    # --- INICIO DE LA LÓGICA DE CORRECCIÓN DE DATOS ---
    # 1. Ordenamos por concurso ASCENDENTE para que shift() funcione correctamente
    df_historico_sorted = df_historico.sort_values(by='concurso', ascending=True)
    
    # 2. Creamos la columna 'bolsa_ganada' que contiene el MONTO que se ganó.
    # La bolsa que se gana es la del concurso ANTERIOR.
    df_historico_sorted['bolsa_ganada'] = df_historico_sorted['bolsa'].shift(1)
    
    # 3. Creamos el flag 'es_ganador'. Un sorteo es el ganador si SU bolsa es 5M.
    df_historico_sorted['es_ganador'] = (df_historico_sorted['bolsa'] == 5000000).astype(int)
    
    # Rellenamos el primer NaN que crea el shift
    df_historico_sorted['bolsa_ganada'].fillna(0, inplace=True)
    
    # Ahora volvemos a ordenar DESC para la visualización en la tabla
    df_historico_final = df_historico_sorted.sort_values(by='concurso', ascending=False)
    # --- FIN DE LA LÓGICA DE CORRECCIÓN DE DATOS ---
    
    cols_to_drop = [col for col in df_omega_stats.columns if col in df_historico_final.columns and col != 'concurso']
    df_historico_to_merge = df_historico_final.drop(columns=cols_to_drop)
    df_enriquecido = pd.merge(df_historico_to_merge, df_omega_stats, on='concurso')
    
    try:
        conn = sqlite3.connect(config.DB_FILE)
        df_enriquecido.to_sql(TABLE_NAME_HISTORICO, conn, if_exists='replace', index=False)
        conn.close()
        return True, "Datos históricos enriquecidos."
    except Exception as e:
        return False, f"Error al guardar histórico enriquecido: {e}"

def pregenerate_omega_class(set_progress=None):
    """
    Pre-genera la Clase Omega, reportando el progreso si se proporciona
    una función de callback.
    """
    # Importar no_update dentro de la función
    from dash import no_update

    logger.info("Verificando si la pre-generación es necesaria...")
    state = state_manager.get_state()
    last_concurso_for_freqs = state.get("last_concurso_for_freqs", 0)
    last_concurso_for_omega = state.get("last_concurso_for_omega_class", 0)
    
    if last_concurso_for_freqs > 0 and last_concurso_for_freqs == last_concurso_for_omega:
        return True, "Pre-generación ya está actualizada."

    logger.info("Iniciando la pre-generación de Clase Omega...")
    freqs = get_frequencies()
    if freqs is None: return False, "Faltan frecuencias para pre-generar."
    
    df_historico = db.read_historico_from_db()
    if df_historico.empty: return False, "Falta histórico para pre-generar."
    
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    historical_draws_set = set(tuple(sorted(row)) for row in df_historico[result_columns].to_numpy())
    
    omega_list = []
    total_combinations = C(39, 6)
    all_possible_combinations = combinations(range(1, 40), 6)
    
    for count, combo in enumerate(all_possible_combinations, 1):
        # Llama a set_progress con la tupla completa de 7 elementos
        if set_progress and count % 100000 == 0:
            progress = 50 + int((count / total_combinations) * 50)
            set_progress((
                progress, f"Pre-generando: {count:,}/{total_combinations:,}",
                no_update, no_update, no_update, no_update, no_update
            ))
        
        result = evaluate_combination(list(combo), freqs)
        if isinstance(result, dict) and result.get("esOmega"):
            ha_salido = 1 if combo in historical_draws_set else 0
            omega_list.append({
                'c1': combo[0], 'c2': combo[1], 'c3': combo[2],
                'c4': combo[3], 'c5': combo[4], 'c6': combo[5],
                'ha_salido': ha_salido, 'afinidad_pares': result['afinidadPares'],
                'afinidad_tercias': result['afinidadTercias'],
                'afinidad_cuartetos': result['afinidadCuartetos'],
            })

    omega_df = pd.DataFrame(omega_list)
    success, message = db.save_omega_class(omega_df)
    
    if success:
        state["last_concurso_for_omega_class"] = last_concurso_for_freqs
        state_manager.save_state(state)
        message = "Pre-generación completada."
    
    return success, message

def adjust_to_omega(user_combo):
    logger.info(f"Iniciando ajuste para: {user_combo}")
    for matches in range(5, 2, -1):
        closest_combo = db.find_closest_omega(user_combo, matches)
        if closest_combo: return closest_combo, matches
    return None, 0

def deconstruct_affinity(combination: list, omega_score: float) -> dict:
    """
    Deconstruye las afinidades de una combinación y sus frecuencias.
    """
    freqs = get_frequencies()
    if not freqs:
        return {"error": "Frecuencias no disponibles."}

    eval_result = evaluate_combination(combination, freqs)
    if eval_result.get("error"):
        return eval_result

    # Generar subsecuencias
    pares = list(combinations(sorted(combination), 2))
    tercias = list(combinations(sorted(combination), 3))
    cuartetos = list(combinations(sorted(combination), 4))

    # Get frequency maps
    freq_map_pares = freqs.get("pares", {})
    freq_map_tercias = freqs.get("tercias", {})
    freq_map_cuartetos = freqs.get("cuartetos", {})

    # Build breakdown lists
    breakdown_pares = [{"subsequence": str(p), "frequency": freq_map_pares.get(p, 0)} for p in pares]
    breakdown_tercias = [{"subsequence": str(t), "frequency": freq_map_tercias.get(t, 0)} for t in tercias]
    breakdown_cuartetos = [{"subsequence": str(c), "frequency": freq_map_cuartetos.get(c, 0)} for c in cuartetos]

    # Sort by frequency
    breakdown_pares.sort(key=lambda x: x["frequency"], reverse=True)
    breakdown_tercias.sort(key=lambda x: x["frequency"], reverse=True)
    breakdown_cuartetos.sort(key=lambda x: x["frequency"], reverse=True)

    deconstructed_data = {
        "combination": eval_result.get("combinacion"),
        "omega_score": omega_score, # Usar el score de la tabla para consistencia
        "totals": {
            "pares": eval_result.get("afinidadPares"),
            "tercias": eval_result.get("afinidadTercias"),
            "cuartetos": eval_result.get("afinidadCuartetos"),
        },
        "breakdown": {
            "pares": breakdown_pares,
            "tercias": breakdown_tercias,
            "cuartetos": breakdown_cuartetos,
        },
        "error": None
    }
    return deconstructed_data