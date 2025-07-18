import pandas as pd
import numpy as np
import multiprocessing as mp
from itertools import combinations, product
import logging
import time
from typing import Tuple, Dict, Any
import warnings
import config
import re

# Suprimir warnings para output limpio en producción
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# --- Funciones Worker y de Ayuda (Internas al Módulo) ---

def _worker_evaluate_scenario(args: Tuple) -> Dict[str, Any]:
    """
    Función worker global sin estado para evaluación paralela.
    Siempre devuelve un diccionario.
    """
    try:
        percentiles, afinidades_data, freqs_data = args
        p_pares, p_tercias, p_cuartetos = percentiles
        
        afinidades_pares = np.array(afinidades_data['pares'])
        afinidades_tercias = np.array(afinidades_data['tercias'])
        afinidades_cuartetos = np.array(afinidades_data['cuartetos'])
        
        umbral_pares = int(np.percentile(afinidades_pares, p_pares * 100))
        umbral_tercias = int(np.percentile(afinidades_tercias, p_tercias * 100))
        umbral_cuartetos = int(np.percentile(afinidades_cuartetos, p_cuartetos * 100))
        
        mask_omega = (
            (afinidades_pares >= umbral_pares) &
            (afinidades_tercias >= umbral_tercias) &
            (afinidades_cuartetos >= umbral_cuartetos)
        )
        cobertura_historica = float(np.mean(mask_omega))
        
        # FILTRO JERÁRQUICO: Si no cumple, devuelve un diccionario vacío
        if cobertura_historica < 0.95:
            return {}
            
        cobertura_universal_estimada = _estimate_cu_monte_carlo(
            umbral_pares, umbral_tercias, umbral_cuartetos, freqs_data
        )
        
        return {
            'umbrales': {'pares': umbral_pares, 'tercias': umbral_tercias, 'cuartetos': umbral_cuartetos},
            'cobertura_historica': cobertura_historica,
            'cobertura_universal_estimada': cobertura_universal_estimada
        }
    except Exception:
        # En caso de cualquier error, devuelve un diccionario vacío
        return {}

def _estimate_cu_monte_carlo(umbral_pares: int, umbral_tercias: int, umbral_cuartetos: int, 
                            freqs_data: dict, sample_size: int = 3000) -> float:
    """
    Estima cobertura universal usando muestreo Monte Carlo.
    """
    try:
        np.random.seed(42)
        omega_count = 0
        for _ in range(sample_size):
            combo = sorted(np.random.choice(range(1, 40), 6, replace=False))
            afinidad_pares = sum(freqs_data['pares'].get(str(tuple(par)), 0) for par in combinations(combo, 2))
            afinidad_tercias = sum(freqs_data['tercias'].get(str(tuple(tercia)), 0) for tercia in combinations(combo, 3))
            afinidad_cuartetos = sum(freqs_data['cuartetos'].get(str(tuple(cuarteto)), 0) for cuarteto in combinations(combo, 4))
            
            if (afinidad_pares >= umbral_pares and 
                afinidad_tercias >= umbral_tercias and 
                afinidad_cuartetos >= umbral_cuartetos):
                omega_count += 1
        return float(omega_count / sample_size)
    except Exception:
        return 1.0 # Devolver un valor alto en caso de error para que no sea elegido

def _update_config_file(new_thresholds: dict) -> bool:
    """
    Actualiza el archivo config.py.
    """
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
    except Exception as e:
        logger.error(f"Error crítico al actualizar config.py: {e}", exc_info=True)
        return False

# --- FUNCIÓN PÚBLICA PRINCIPAL ---

def run_optimization(df_historico: pd.DataFrame, freqs: dict) -> Tuple[bool, str, dict]:
    """
    Función principal de optimización jerárquica de umbrales.
    """
    try:
        # FASE 1: Validación de Inputs
        if df_historico.empty or not freqs: return False, "Datos de entrada inválidos.", {}

        # FASE 2: Cálculo de Afinidades
        from modules.omega_logic import _calculate_subsequence_affinity
        afinidades_pares, afinidades_tercias, afinidades_cuartetos = [], [], []
        for _, row in df_historico.iterrows():
            try:
                combo = sorted([int(row[col]) for col in ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']])
                afinidades_pares.append(_calculate_subsequence_affinity(combo, freqs, 2))
                afinidades_tercias.append(_calculate_subsequence_affinity(combo, freqs, 3))
                afinidades_cuartetos.append(_calculate_subsequence_affinity(combo, freqs, 4))
            except (ValueError, TypeError): continue
        
        if not afinidades_pares: return False, "No se pudieron calcular afinidades.", {}

        # FASE 3: Generación de Escenarios
        percentiles_range = np.arange(0.01, 0.51, 0.03)
        percentile_combinations = list(product(percentiles_range, repeat=3))
        
        # FASE 4: Paralelización
        afinidades_data = {'pares': afinidades_pares, 'tercias': afinidades_tercias, 'cuartetos': afinidades_cuartetos}
        freqs_data = {k: {str(key): val for key, val in v.items()} for k, v in freqs.items()}
        
        n_processes = min(mp.cpu_count(), 8)
        worker_args = [(combo, afinidades_data, freqs_data) for combo in percentile_combinations]
        
        logger.info(f"Iniciando optimización con {len(worker_args)} escenarios en {n_processes} núcleos...")
        with mp.Pool(processes=n_processes) as pool:
            worker_results = pool.map(_worker_evaluate_scenario, worker_args)
        
        valid_candidates = [result for result in worker_results if result]
        
        # FASE 5: Selección del Óptimo
        if not valid_candidates: return False, "No se encontraron candidatos con CH >= 95%", {}
        
        optimal_candidate = min(valid_candidates, key=lambda x: x['cobertura_universal_estimada'])
        
        # FASE 6: Generar Reporte y Actualizar Config
        report = {
            "new_thresholds": optimal_candidate['umbrales'],
            "cobertura_historica": optimal_candidate['cobertura_historica'],
            "cobertura_universal_estimada": optimal_candidate['cobertura_universal_estimada']
        }
        
        if not _update_config_file(report["new_thresholds"]):
            return False, "Falló la actualización del archivo de configuración.", {}
        
        return True, "Optimización exitosa (Ingeniería de Precisión).", report
        
    except Exception as e:
        logger.error(f"Error crítico en optimización: {str(e)}", exc_info=True)
        return False, f"Error crítico: {str(e)}", {}