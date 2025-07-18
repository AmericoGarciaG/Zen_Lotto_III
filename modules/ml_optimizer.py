import pandas as pd
import numpy as np
import multiprocessing as mp
from itertools import combinations, product
import logging
import time
import re
import config

logger = logging.getLogger(__name__)

def _update_config_file(new_thresholds):
    # (Esta función la tomamos de nuestra versión anterior, es robusta)
    try:
        with open('config.py', 'r', encoding='utf-8') as f: lines = f.readlines()
        new_lines = []
        for line in lines:
            if line.strip().startswith('UMBRAL_PARES'): new_lines.append(f'UMBRAL_PARES = {new_thresholds["pares"]}\n')
            elif line.strip().startswith('UMBRAL_TERCIAS'): new_lines.append(f'UMBRAL_TERCIAS = {new_thresholds["tercias"]}\n')
            elif line.strip().startswith('UMBRAL_CUARTETOS'): new_lines.append(f'UMBRAL_CUARTETOS = {new_thresholds["cuartetos"]}\n')
            else: new_lines.append(line)
        with open('config.py', 'w', encoding='utf-8') as f: f.writelines(new_lines)
        return True
    except Exception as e: return False

# Función 'worker' global para la paralelización
def _evaluate_scenario_worker(args):
    percentiles, df_aff_values, freqs, min_ch_target = args
    p_p, p_t, p_q = percentiles
    
    try:
        df_aff = pd.DataFrame(df_aff_values)
        umbral_p = int(np.percentile(df_aff['pares'], p_p * 100))
        umbral_t = int(np.percentile(df_aff['tercias'], p_t * 100))
        umbral_q = int(np.percentile(df_aff['cuartetos'], p_q * 100))
        
        mask = ((df_aff['pares'] >= umbral_p) & (df_aff['tercias'] >= umbral_t) & (df_aff['cuartetos'] >= umbral_q))
        cobertura_historica = mask.mean()
        
        if cobertura_historica < min_ch_target:
            return None
            
        cobertura_universal_estimada = (1 - p_p) * (1 - p_t) * (1 - p_q)
        
        return {
            'umbrales': {'pares': umbral_p, 'tercias': umbral_t, 'cuartetos': umbral_q},
            'cobertura_historica': cobertura_historica,
            'cobertura_universal_estimada': cobertura_universal_estimada
        }
    except Exception:
        return None

def optimize_thresholds(df_historico, freqs, min_cobertura_historica=0.95):
    logger.info("INICIANDO OPTIMIZACIÓN JERÁRQUICA FINAL (VERSIÓN MANUS)")
    
    # 1. Calcular afinidades
    affinities = []
    for _, row in df_historico.iterrows():
        try:
            combo = sorted([int(row[col]) for col in ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']])
            afinidad_pares = sum(freqs['pares'].get(tuple(par), 0) for par in combinations(combo, 2))
            afinidad_tercias = sum(freqs['tercias'].get(tuple(tercia), 0) for tercia in combinations(combo, 3))
            afinidad_cuartetos = sum(freqs['cuartetos'].get(tuple(cuarteto), 0) for cuarteto in combinations(combo, 4))
            affinities.append({'pares': afinidad_pares, 'tercias': afinidad_tercias, 'cuartetos': afinidad_cuartetos})
        except (ValueError, TypeError, KeyError):
            continue
    if not affinities:
        return False, "No se pudieron calcular afinidades", {}
    df_affinities = pd.DataFrame(affinities)

    # 2. Generar escenarios
    percentiles_range = np.arange(0.01, 0.71, 0.03)
    percentile_combinations = list(product(percentiles_range, repeat=3))
    logger.info(f"Generados {len(percentile_combinations):,} escenarios de percentiles")
    
    # 3. Ejecutar en paralelo
    n_processes = mp.cpu_count()
    df_aff_values = df_affinities.to_dict('records')
    args_list = [(combo, df_aff_values, freqs, min_cobertura_historica) for combo in percentile_combinations]
    
    start_time = time.time()
    with mp.Pool(processes=n_processes) as pool:
        results = pool.map(_evaluate_scenario_worker, args_list)
    
    valid_results = [r for r in results if r is not None]
    logger.info(f"Evaluación paralela completada en {time.time() - start_time:.2f}s. Candidatos válidos: {len(valid_results)}")
    
    if not valid_results:
        return False, f"No se encontraron candidatos con CH >= {min_cobertura_historica:.0%}", {}
    
    # 4. Seleccionar óptimo
    optimal_candidate = min(valid_results, key=lambda x: x['cobertura_universal_estimada'])
    
    # 5. Generar reporte y actualizar config
    report = {
        "new_thresholds": optimal_candidate['umbrales'],
        "cobertura_historica": optimal_candidate['cobertura_historica'],
        "cobertura_universal_estimada": optimal_candidate['cobertura_universal_estimada']
    }
    
    if not _update_config_file(report["new_thresholds"]):
        return False, "Falló la actualización del archivo de configuración.", {}
        
    return True, "Optimización exitosa (Versión Manus).", report