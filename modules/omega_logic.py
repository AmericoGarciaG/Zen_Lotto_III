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

# --- (Omitiendo funciones auxiliares que no cambian por brevedad) ---
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
    except FileNotFoundError: return None
    except Exception: return None

def _calculate_subsequence_affinity(combination, freqs, size):
    key_map = {2: "pares", 3: "tercias", 4: "cuartetos"}
    if not freqs or key_map[size] not in freqs: return 0
    total_affinity = 0
    subsequences = combinations(sorted(combination), size)
    freq_map = freqs[key_map[size]]
    for sub in subsequences: total_affinity += freq_map.get(sub, 0)
    return total_affinity

def evaluate_combination(combination, freqs):
    if len(set(combination)) != 6: return {"error": "La combinación debe tener 6 números únicos."}
    afinidad_pares = _calculate_subsequence_affinity(combination, freqs, 2)
    afinidad_tercias = _calculate_subsequence_affinity(combination, freqs, 3)
    afinidad_cuartetos = _calculate_subsequence_affinity(combination, freqs, 4)
    cumple_pares = afinidad_pares >= config.UMBRAL_PARES
    cumple_tercias = afinidad_tercias >= config.UMBRAL_TERCIAS
    cumple_cuartetos = afinidad_cuartetos >= config.UMBRAL_CUARTETOS
    es_omega = sum([cumple_pares, cumple_tercias, cumple_cuartetos]) == 3
    return {
        "error": None, "esOmega": es_omega, "combinacion": sorted(combination),
        "afinidadPares": afinidad_pares, "afinidadTercias": afinidad_tercias, "afinidadCuartetos": afinidad_cuartetos,
        "criterios": {
            "pares": {"cumple": cumple_pares, "score": afinidad_pares, "umbral": config.UMBRAL_PARES},
            "tercias": {"cumple": cumple_tercias, "score": afinidad_tercias, "umbral": config.UMBRAL_TERCIAS},
            "cuartetos": {"cumple": cumple_cuartetos, "score": afinidad_cuartetos, "umbral": config.UMBRAL_CUARTETOS}
        }
    }

def C(n, k): return factorial(n) // (factorial(k) * factorial(n - k))

def calculate_and_save_frequencies():
    """
    Orquesta el cálculo de frecuencias. Su única responsabilidad es
    leer el histórico y generar/actualizar el archivo de frecuencias.
    """
    logger.info("Iniciando el cálculo/actualización de frecuencias.")
    
    state = state_manager.get_state()
    last_processed_concurso = state.get("last_concurso_for_freqs", 0)

    df_historico = db.read_historico_from_db()
    if df_historico.empty:
        return False, "La base de datos está vacía. Ejecute 'Actualizar Histórico' primero."

    df_new_draws = df_historico[df_historico['concurso'] > last_processed_concurso].copy()
    
    if df_new_draws.empty:
        message = "No hay sorteos nuevos para procesar. Las frecuencias ya están actualizadas."
        logger.info(message)
        return True, message

    # Carga las frecuencias existentes o crea contadores vacíos
    freqs_data = get_frequencies() or {}
    freq_pairs = Counter(freqs_data.get("pares", {}))
    freq_triplets = Counter(freqs_data.get("tercias", {}))
    freq_quartets = Counter(freqs_data.get("cuartetos", {}))
    
    logger.info(f"Se procesarán {len(df_new_draws)} sorteos nuevos para calcular frecuencias.")
    all_new_pairs, all_new_triplets, all_new_quartets = [], [], []
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    
    for _, row in df_new_draws.iterrows():
        draw = sorted([int(row[col]) for col in result_columns])
        all_new_pairs.extend(list(combinations(draw, 2)))
        all_new_triplets.extend(list(combinations(draw, 3)))
        all_new_quartets.extend(list(combinations(draw, 4)))

    freq_pairs.update(all_new_pairs)
    freq_triplets.update(all_new_triplets)
    freq_quartets.update(all_new_quartets)
    
    new_last_processed_concurso = int(df_new_draws['concurso'].max())

    # La data para el JSON de frecuencias no cambia
    output_data = {
        "FREQ_PARES": {str(k): v for k, v in freq_pairs.items()},
        "FREQ_TERCIAS": {str(k): v for k, v in freq_triplets.items()},
        "FREQ_CUARTETOS": {str(k): v for k, v in freq_quartets.items()}
    }

    try:
        with open(config.FREQUENCIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        # Actualizamos el estado central y lo guardamos
        state["last_concurso_for_freqs"] = new_last_processed_concurso
        state_manager.save_state(state)

        message = f"Frecuencias actualizadas con éxito usando {len(df_new_draws)} nuevos sorteos."
        logger.info(message)
        return True, message
    except Exception as e:
        message = f"Error al guardar el archivo de frecuencias actualizado: {e}"
        logger.error(message, exc_info=True)
        return False, message

def pregenerate_omega_class():
    logger.info("Verificando si la pre-generación es necesaria...")
    state = state_manager.get_state()
    last_concurso_for_freqs = state.get("last_concurso_for_freqs", 0)
    last_concurso_for_omega = state.get("last_concurso_for_omega_class", 0)
    if last_concurso_for_freqs == 0: return False, "Frecuencias no generadas."
    if last_concurso_for_freqs == last_concurso_for_omega: return True, "La Clase Omega ya está actualizada."
    logger.info("Iniciando la pre-generación...")
    freqs = get_frequencies()
    if freqs is None: return False, "No se puede generar sin archivo de frecuencias."
    df_historico = db.read_historico_from_db()
    if df_historico.empty: return False, "No se pudo leer el histórico."
    historical_draws_set = set(tuple(sorted(row)) for row in df_historico[['r1','r2','r3','r4','r5','r6']].to_numpy())
    omega_list = []
    total_combinations = C(39, 6)
    for count, combo in enumerate(combinations(range(1, 40), 6), 1):
        if count % 200000 == 0: logger.info(f"Procesando... {count:,} / {total_combinations:,}")
        result = evaluate_combination(list(combo), freqs)
        if result.get("esOmega"):
            omega_list.append({'c1': combo[0], 'c2': combo[1], 'c3': combo[2], 'c4': combo[3], 'c5': combo[4], 'c6': combo[5], 'ha_salido': 1 if combo in historical_draws_set else 0, 'afinidad_pares': result['afinidadPares'], 'afinidad_tercias': result['afinidadTercias'], 'afinidad_cuartetos': result['afinidadCuartetos']})
    if not omega_list: return True, "No se encontraron combinaciones Omega."
    omega_df = pd.DataFrame(omega_list)
    success, message = db.save_omega_class(omega_df)
    if success:
        state["last_concurso_for_omega_class"] = last_concurso_for_freqs
        state_manager.save_state(state)
    return success, message

def adjust_to_omega(user_combo):
    logger.info(f"Iniciando ajuste para: {user_combo}")
    for matches in range(5, 2, -1):
        closest_combo = db.find_closest_omega(user_combo, matches)
        if closest_combo: return closest_combo, matches
    return None, 0

# --- FUNCIÓN DE ENRIQUECIMIENTO CON CORRECCIÓN FINAL ---
def enrich_historical_data():
    """
    Calcula todas las métricas, incluyendo el Score Omega universal (positivo/negativo),
    para el histórico completo y las guarda en la BD.
    """
    logger.info("Iniciando el enriquecimiento de datos históricos con Score Omega universal...")
    
    from modules.database import read_historico_from_db, TABLE_NAME_HISTORICO
    import sqlite3

    df_historico = read_historico_from_db()
    freqs = get_frequencies()

    if df_historico.empty or freqs is None:
        return False, "No se puede enriquecer el histórico. Faltan datos base."

    # Forzamos el recálculo para asegurar que los datos estén correctos.
    # if 'omega_score' in df_historico.columns:
    #     return True, "El histórico ya estaba enriquecido."

    resultados_omega = []
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    
    for _, row in df_historico.iterrows():
        try:
            # Aseguramos que los números del sorteo sean enteros
            combination = [int(row[col]) for col in result_columns]
        except (ValueError, TypeError):
            logger.warning(f"Sorteo {row.get('concurso')} con datos inválidos. Omitiendo.")
            continue # Saltamos a la siguiente iteración

        eval_result = evaluate_combination(combination, freqs)
        
        # Inicializamos con valores seguros
        af_q, af_t, af_p = 0, 0, 0
        es_omega_val = 0
        omega_score = 0.0

        # Verificamos que el resultado de la evaluación sea un diccionario válido
        if isinstance(eval_result, dict) and not eval_result.get("error"):
            # Extraemos los valores y los convertimos explícitamente a enteros
            # Esto elimina cualquier ambigüedad para Pylance
            af_q = int(eval_result.get('afinidadCuartetos', 0))
            af_t = int(eval_result.get('afinidadTercias', 0))
            af_p = int(eval_result.get('afinidadPares', 0))
            es_omega_val = 1 if eval_result.get("esOmega") else 0
            
            # Con las variables garantizadas como enteros, el cálculo es seguro
            score_q = ((af_q - config.UMBRAL_CUARTETOS) / config.UMBRAL_CUARTETOS) * 0.5 if config.UMBRAL_CUARTETOS > 0 else 0
            score_t = ((af_t - config.UMBRAL_TERCIAS) / config.UMBRAL_TERCIAS) * 0.3 if config.UMBRAL_TERCIAS > 0 else 0
            score_p = ((af_p - config.UMBRAL_PARES) / config.UMBRAL_PARES) * 0.2 if config.UMBRAL_PARES > 0 else 0
            omega_score = score_q + score_t + score_p
        
        resultados_omega.append({
            'concurso': row['concurso'],
            'es_omega': es_omega_val,
            'omega_score': round(omega_score, 4),
            'afinidad_cuartetos': af_q,
            'afinidad_tercias': af_t,
            'afinidad_pares': af_p
        })

    df_omega_stats = pd.DataFrame(resultados_omega)
    
    df_historico_sorted = df_historico.sort_values(by='concurso')
    df_historico_sorted['bolsa_siguiente'] = df_historico_sorted['bolsa'].shift(-1)
    df_historico_sorted['bolsa_ganada'] = (df_historico_sorted['bolsa_siguiente'] == 5000000).astype(int)
    
    cols_to_drop = [col for col in df_omega_stats.columns if col in df_historico_sorted.columns and col != 'concurso']
    df_historico_to_merge = df_historico_sorted.drop(columns=cols_to_drop)

    df_enriquecido = pd.merge(df_historico_to_merge, df_omega_stats, on='concurso')
    
    try:
        conn = sqlite3.connect(config.DB_FILE)
        df_enriquecido.to_sql(TABLE_NAME_HISTORICO, conn, if_exists='replace', index=False)
        conn.close()
        logger.info("El enriquecimiento de datos históricos ha finalizado con éxito.")
        return True, "Datos históricos enriquecidos y guardados correctamente."
    except Exception as e:
        return False, f"Error al guardar el histórico enriquecido: {e}"