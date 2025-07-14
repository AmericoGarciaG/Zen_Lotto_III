import json
from collections import Counter
from itertools import combinations
import logging
from math import factorial
import pandas as pd
import modules.database as db
import config
from utils import state_manager # <-- Importamos el nuevo gestor de estado

logger = logging.getLogger(__name__)

# --- Funciones de Carga y Cálculo de Afinidad (sin cambios en su lógica interna) ---

_frequencies_cache = None

def get_frequencies():
    """
    Carga las frecuencias desde el archivo JSON. Usa un caché en memoria
    para evitar leer el archivo repetidamente en la misma sesión.
    """
    global _frequencies_cache
    if _frequencies_cache is not None:
        return _frequencies_cache

    try:
        with open(config.FREQUENCIES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Cargando datos desde {config.FREQUENCIES_FILE}...")
        _frequencies_cache = {
            "pares": {eval(k): v for k, v in data.get("FREQ_PARES", {}).items()},
            "tercias": {eval(k): v for k, v in data.get("FREQ_TERCIAS", {}).items()},
            "cuartetos": {eval(k): v for k, v in data.get("FREQ_CUARTETOS", {}).items()}
        }
        logger.info("Caché de frecuencias cargado en memoria.")
        return _frequencies_cache
    except FileNotFoundError:
        logger.error(f"El archivo de frecuencias '{config.FREQUENCIES_FILE}' no se ha generado todavía.")
        return None
    except Exception as e:
        logger.error(f"Error al cargar o procesar el archivo de frecuencias: {e}", exc_info=True)
        return None

def _calculate_subsequence_affinity(combination, freqs, size):
    """Función de ayuda genérica para calcular afinidad."""
    key_map = {2: "pares", 3: "tercias", 4: "cuartetos"}
    if not freqs or key_map[size] not in freqs:
        return 0
    
    total_affinity = 0
    subsequences = combinations(sorted(combination), size)
    freq_map = freqs[key_map[size]]
    
    for sub in subsequences:
        total_affinity += freq_map.get(sub, 0)
        
    return total_affinity

def evaluate_combination(combination, freqs):
    """
    Evalúa una combinación de 6 números según los criterios Omega.
    Siempre devuelve un diccionario.
    """
    if len(set(combination)) != 6:
        return {"error": "La combinación debe tener 6 números únicos."}

    afinidad_pares = _calculate_subsequence_affinity(combination, freqs, 2)
    afinidad_tercias = _calculate_subsequence_affinity(combination, freqs, 3)
    afinidad_cuartetos = _calculate_subsequence_affinity(combination, freqs, 4)

    cumple_pares = afinidad_pares >= config.UMBRAL_PARES
    cumple_tercias = afinidad_tercias >= config.UMBRAL_TERCIAS
    cumple_cuartetos = afinidad_cuartetos >= config.UMBRAL_CUARTETOS
    
    criterios_cumplidos = sum([cumple_pares, cumple_tercias, cumple_cuartetos])
    es_omega = criterios_cumplidos == 3
    
    return {
        "error": None,
        "esOmega": es_omega,
        "combinacion": sorted(combination),
        "afinidadPares": afinidad_pares,
        "afinidadTercias": afinidad_tercias,
        "afinidadCuartetos": afinidad_cuartetos,
        "criterios": {
            "pares": {"cumple": cumple_pares, "score": afinidad_pares, "umbral": config.UMBRAL_PARES},
            "tercias": {"cumple": cumple_tercias, "score": afinidad_tercias, "umbral": config.UMBRAL_TERCIAS},
            "cuartetos": {"cumple": cumple_cuartetos, "score": afinidad_cuartetos, "umbral": config.UMBRAL_CUARTETOS}
        },
        "criteriosCumplidos": criterios_cumplidos
    }

def C(n, k):
    """Calcula el coeficiente binomial 'n choose k'."""
    return factorial(n) // (factorial(k) * factorial(n - k))


# --- Funciones de Lógica de Negocio Refactorizadas ---

def calculate_and_save_frequencies():
    """
    Orquesta el cálculo de frecuencias usando el estado centralizado.
    """
    logger.info("Iniciando el cálculo/actualización de frecuencias.")
    
    state = state_manager.get_state()
    last_processed_concurso = state.get("last_concurso_for_freqs", 0)

    df_historico = db.read_historico_from_db()
    if df_historico is None or df_historico.empty:
        return False, "La base de datos está vacía. Genere el histórico primero."

    df_new_draws = df_historico[df_historico['concurso'] > last_processed_concurso].copy()
    
    if df_new_draws.empty:
        message = "No hay sorteos nuevos para procesar. Las frecuencias están actualizadas."
        logger.info(message)
        return True, message

    # Carga las frecuencias existentes o crea contadores vacíos
    freqs_data = get_frequencies() or {}
    freq_pairs = Counter(freqs_data.get("pares", {}))
    freq_triplets = Counter(freqs_data.get("tercias", {}))
    freq_quartets = Counter(freqs_data.get("cuartetos", {}))
    
    logger.info(f"Se procesarán {len(df_new_draws)} sorteos nuevos.")
    all_new_pairs, all_new_triplets, all_new_quartets = [], [], []
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    
    for _, row in df_new_draws.iterrows():
        draw = sorted([row[col] for col in result_columns])
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

        message = f"Frecuencias actualizadas con {len(df_new_draws)} nuevos sorteos."
        return True, message
    except Exception as e:
        message = f"Error al guardar el archivo de frecuencias actualizado: {e}"
        logger.error(message, exc_info=True)
        return False, message

def pregenerate_omega_class():
    """
    Pre-genera la Clase Omega usando el estado centralizado para verificar si es necesario.
    """
    logger.info("Verificando si la pre-generación de Clase Omega es necesaria...")
    
    state = state_manager.get_state()
    last_concurso_for_freqs = state.get("last_concurso_for_freqs", 0)
    last_concurso_for_omega = state.get("last_concurso_for_omega_class", 0)

    if last_concurso_for_freqs == 0:
        return False, "Las frecuencias no han sido generadas. Por favor, actualícelas primero."
    
    if last_concurso_for_freqs == last_concurso_for_omega:
        message = "La Clase Omega ya está actualizada con las últimas frecuencias. No es necesario re-generar."
        logger.info(message)
        return True, message

    logger.info("Iniciando la pre-generación. Esto puede tardar varios minutos...")
    freqs = get_frequencies()
    if freqs is None:
        return False, "No se pueden generar combinaciones Omega sin un archivo de frecuencias."

    omega_list = []
    total_combinations = C(39, 6)
    logger.info(f"Se evaluarán {total_combinations:,} combinaciones en total.")

    all_possible_combinations = combinations(range(1, 40), 6)

    count = 0
    for combo in all_possible_combinations:
        count += 1
        if count % 200000 == 0:
            logger.info(f"Procesando... {count:,} / {total_combinations:,} combinaciones evaluadas.")

        result = evaluate_combination(list(combo), freqs)
        
        if result.get("esOmega"):
            omega_list.append({
                'c1': combo[0], 'c2': combo[1], 'c3': combo[2],
                'c4': combo[3], 'c5': combo[4], 'c6': combo[5],
                'afinidad_pares': result['afinidadPares'],
                'afinidad_tercias': result['afinidadTercias'],
                'afinidad_cuartetos': result['afinidadCuartetos'],
            })

    logger.info(f"Evaluación completa. Se encontraron {len(omega_list)} combinaciones Omega.")
    if not omega_list:
        return True, "No se encontró ninguna combinación Omega con los criterios actuales."

    omega_df = pd.DataFrame(omega_list)
    success, message = db.save_omega_class(omega_df)
    
    if success:
        # Actualizamos el estado central al finalizar con éxito
        state["last_concurso_for_omega_class"] = last_concurso_for_freqs
        state_manager.save_state(state)
        
    return success, message