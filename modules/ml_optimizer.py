# ml_optimizer.py

import pandas as pd
import numpy as np
import multiprocessing as mp
from itertools import combinations, product
import logging
import time
import json
from typing import Tuple, Dict, Any, Optional
import warnings

# Se importa solo la función de ayuda de omega_logic
from modules.omega_logic import _calculate_subsequence_affinity

warnings.filterwarnings('ignore') # Se mantiene para suprimir advertencias de numpy/pandas

logger = logging.getLogger(__name__)

def _save_thresholds_to_json(new_thresholds: Dict[str, int], game_config: Dict[str, Any]) -> bool:
    """Guarda los nuevos umbrales en un archivo JSON específico del juego."""
    thresholds_file = game_config['paths']['thresholds']
    try:
        with open(thresholds_file, 'w', encoding='utf-8') as f:
            json.dump(new_thresholds, f, indent=4)
        logger.info(f"Nuevos umbrales para '{game_config['display_name']}' guardados en '{thresholds_file}'.")
        return True
    except Exception as e:
        logger.error(f"Error crítico al guardar umbrales en '{thresholds_file}': {e}", exc_info=True)
        return False

def _estimate_cu_monte_carlo(
    thresholds: Dict[str, int], 
    freqs_data: Dict[str, Dict[tuple, int]], 
    game_config: Dict[str, Any],
    sample_size: int = 3000
) -> float:
    """Estima la Cobertura Universal para un juego específico mediante Monte Carlo."""
    try:
        np.random.seed(42)
        omega_count = 0
        n, k = game_config['n'], game_config['k']
        
        freq_pares = freqs_data.get('pares', {})
        freq_tercias = freqs_data.get('tercias', {})
        freq_cuartetos = freqs_data.get('cuartetos', {})
        
        for _ in range(sample_size):
            combo = tuple(sorted(np.random.choice(range(1, k + 1), n, replace=False)))
            
            afinidad_pares = sum(freq_pares.get(par, 0) for par in combinations(combo, 2))
            afinidad_tercias = sum(freq_tercias.get(tercia, 0) for tercia in combinations(combo, 3))
            afinidad_cuartetos = sum(freq_cuartetos.get(cuarteto, 0) for cuarteto in combinations(combo, 4))
            
            if (afinidad_pares >= thresholds['pares'] and 
                afinidad_tercias >= thresholds['tercias'] and 
                afinidad_cuartetos >= thresholds['cuartetos']):
                omega_count += 1
        return float(omega_count / sample_size)
    except Exception:
        return 1.0 # Devuelve el peor caso si falla

def _worker_evaluate_scenario(args: Tuple) -> Optional[Dict[str, Any]]:
    """Función de trabajo para un proceso del pool de multiprocessing."""
    try:
        percentiles, afinidades_hist, freqs_tuple_keys, game_config = args
        p_pares, p_tercias, p_cuartetos = percentiles
        
        # Calcula los umbrales para este escenario
        umbral_pares = int(np.percentile(afinidades_hist['pares'], p_pares * 100))
        umbral_tercias = int(np.percentile(afinidades_hist['tercias'], p_tercias * 100))
        umbral_cuartetos = int(np.percentile(afinidades_hist['cuartetos'], p_cuartetos * 100))
        
        thresholds_scenario = {'pares': umbral_pares, 'tercias': umbral_tercias, 'cuartetos': umbral_cuartetos}

        # Calcula la Cobertura Histórica
        mask_omega = (
            (np.array(afinidades_hist['pares']) >= umbral_pares) &
            (np.array(afinidades_hist['tercias']) >= umbral_tercias) &
            (np.array(afinidades_hist['cuartetos']) >= umbral_cuartetos)
        )
        cobertura_historica = float(np.mean(mask_omega))
        
        # Filtro no negociable: si no cubre al menos el 95% del histórico, se descarta
        if cobertura_historica < 0.95:
            return None
            
        # Estima la Cobertura Universal
        cobertura_universal_estimada = _estimate_cu_monte_carlo(
            thresholds_scenario, freqs_tuple_keys, game_config
        )
        
        return {
            'umbrales': thresholds_scenario,
            'cobertura_historica': cobertura_historica,
            'cobertura_universal_estimada': cobertura_universal_estimada
        }
    except Exception:
        return None
# ml_optimizer.py

# ... (otros imports y funciones)

def run_optimization(
    game_config: Dict[str, Any], 
    df_historico: pd.DataFrame, 
    freqs: Dict[str, Dict[tuple, int]], 
    set_progress=None
) -> Tuple[bool, str, Dict]:
    from dash import no_update
    
    try:
        if df_historico.empty or not freqs:
            return False, "Datos de entrada (histórico o frecuencias) inválidos.", {}
        
        logger.info(f"Iniciando optimización para '{game_config['display_name']}'.")
        result_columns = game_config['data_source']['result_columns']

        afinidades_pares, afinidades_tercias, afinidades_cuartetos = [], [], []
        for _, row in df_historico.iterrows():
            try:
                combo = sorted([int(row[col]) for col in result_columns]) #type: ignore
                afinidades_pares.append(_calculate_subsequence_affinity(combo, freqs, 2))
                afinidades_tercias.append(_calculate_subsequence_affinity(combo, freqs, 3))
                afinidades_cuartetos.append(_calculate_subsequence_affinity(combo, freqs, 4))
            except (ValueError, TypeError):
                continue
        
        if not afinidades_pares:
            return False, "No se pudieron calcular afinidades para el histórico.", {}

        afinidades_hist_data = {'pares': afinidades_pares, 'tercias': afinidades_tercias, 'cuartetos': afinidades_cuartetos}

        percentiles_range = np.arange(0.01, 0.51, 0.03)
        percentile_combinations = list(product(percentiles_range, repeat=3))
        
        worker_args = [(p_combo, afinidades_hist_data, freqs, game_config) for p_combo in percentile_combinations]
        
        n_processes = min(mp.cpu_count(), 8)
        logger.info(f"Optimizando {len(worker_args)} escenarios en {n_processes} núcleos...")
        
        # --- INICIO DE LA CORRECCIÓN DE PROGRESO (ROBUSTA) ---
        if set_progress:
            set_progress((5, f"Iniciando optimización de {len(worker_args)} escenarios...", no_update, no_update, no_update, no_update, no_update, no_update))
        # --- FIN DE LA CORRECCIÓN DE PROGRESO ---
        
        with mp.Pool(processes=n_processes) as pool:
            async_result = pool.map_async(_worker_evaluate_scenario, worker_args)
            
            if set_progress:
                # Bucle de progreso "ficticio" que avanza mientras espera
                progress = 5
                while not async_result.ready():
                    time.sleep(1) # Espera un segundo
                    progress = min(progress + 5, 90) # Incrementa el progreso, con un tope de 90%
                    set_progress((
                        progress, f"Procesando escenarios...",
                        no_update, no_update, no_update, no_update, no_update, no_update
                    ))
            
            worker_results = async_result.get() # Espera a que todo termine
        
        if set_progress:
            set_progress((95, "Recopilando resultados...", no_update, no_update, no_update, no_update, no_update, no_update))

        valid_candidates = [result for result in worker_results if result is not None]
        
        if not valid_candidates:
            return False, "No se encontraron candidatos con Cobertura Histórica >= 95%", {}
        
        optimal_candidate = min(valid_candidates, key=lambda x: x['cobertura_universal_estimada'])
        
        if not _save_thresholds_to_json(optimal_candidate['umbrales'], game_config):
            return False, "Falló la actualización del archivo de umbrales.", {}
        
        report = {
            "new_thresholds": optimal_candidate['umbrales'], 
            "cobertura_historica": optimal_candidate['cobertura_historica'], 
            "cobertura_universal_estimada": optimal_candidate['cobertura_universal_estimada']
        }
        
        return True, f"Optimización para '{game_config['display_name']}' exitosa.", report
        
    except Exception as e:
        logger.error(f"Error crítico en optimización: {str(e)}", exc_info=True)
        return False, f"Error crítico: {str(e)}", {}