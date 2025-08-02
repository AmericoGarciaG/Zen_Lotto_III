# modules/omega_cero_logic.py

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from collections import Counter
from itertools import combinations

from . import database as db
from . import omega_logic as ol # Reutilizamos funciones de omega_logic

logger = logging.getLogger(__name__)

def get_omega_cero_metrics(db_path: str) -> Dict[str, Any]:
    """
    Lee las métricas pre-calculadas de la tabla omega_cero_metrics.
    Devuelve un diccionario con las métricas o un diccionario vacío si no se encuentran.
    """
    try:
        # --- CORRECCIÓN: Llamar a la nueva función de base de datos ---
        df_metrics = db.read_omega_cero_metrics(db_path)
        # --- FIN DE LA CORRECCIÓN ---

        if df_metrics.empty:
            return {}
        # Convertir el DataFrame de dos columnas (metric_name, value) a un diccionario
        return pd.Series(df_metrics.value.values, index=df_metrics.metric_name).to_dict()
    except Exception as e:
        logger.error(f"Error al leer las métricas de Omega Cero: {e}")
        return {}

def get_omega_cero_candidates(game_config: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Aplica el filtro dinámico y encuentra las candidatas de Omega Cero que NO han salido.
    """
    logger.info(f"Iniciando cálculo de candidatas Omega Cero para '{game_config['display_name']}'...")
    db_path = game_config['paths']['db']
    result_columns = game_config['data_source']['result_columns']

    metrics = get_omega_cero_metrics(db_path)
    if not metrics:
        logger.warning("No se encontraron métricas de Omega Cero. Ejecute 'generate_omega_score_trajectory.py' primero.")
        return pd.DataFrame(), {}

    # 1. Cargar TODA la Clase Omega pre-generada usando la nueva función de DB.
    df_omega_class = db.read_full_omega_class(db_path)
    if df_omega_class.empty:
        logger.warning("La tabla de la Clase Omega está vacía. Ejecute el paso 5 de configuración.")
        return pd.DataFrame(), metrics
    
    # 2. Filtrar las combinaciones que YA HAN SALIDO.
    logger.info(f"Clase Omega total: {len(df_omega_class)} combinaciones. Filtrando las que ya han salido...")
    df_omega_candidates = df_omega_class[df_omega_class['ha_salido'] == 0].copy()
    logger.info(f"Quedan {len(df_omega_candidates)} combinaciones Omega vírgenes como base de candidatas.")

    freqs = ol.get_frequencies(game_config)
    if not freqs:
        logger.warning("No se encontraron frecuencias."); return pd.DataFrame(), metrics

    # 3. Calcular el modelo "actual" (simplificado)
    df_full_historico = db.read_historico_from_db(db_path)
    if df_full_historico.empty:
        logger.warning("El histórico está vacío para calcular el umbral actual."); return pd.DataFrame(), metrics

    afinidades_actuales = [
        ol._calculate_subsequence_affinity(sorted([int(r[c]) for c in result_columns]), freqs, 2) # type: ignore
        for _, r in df_full_historico.iterrows()
    ]
    umbral_pares_actual = int(np.percentile(afinidades_actuales, 20))

    # 4. Simular el "Score al nacer" para cada candidata
    candidatas_finales = []
    num_cols = [f'c{i}' for i in range(1, game_config['n'] + 1)]
    loaded_thresholds = ol.get_loaded_thresholds(game_config)
    weights = game_config['omega_config']['score_weights']

    for _, row in df_omega_candidates.iterrows():
        try:
            combination = [int(row[col]) for col in num_cols]
            af_p = row['afinidad_pares']
            af_q = row['afinidad_cuartetos']
            simulated_original_score = (af_p - umbral_pares_actual) / (umbral_pares_actual or 1)
            
            # 5. Aplicar el Filtro Dinámico de "Banda de Normalidad"
            if metrics['banda_normal_inferior'] <= simulated_original_score <= metrics['banda_normal_superior']:
                # Calcular el 'current_omega_score' on-the-fly para esta candidata
                s_q = ((af_q - loaded_thresholds.get('cuartetos',0)) / (loaded_thresholds.get('cuartetos',1) or 1)) * weights.get('cuartetos',0)
                s_t = ((row['afinidad_tercias'] - loaded_thresholds.get('tercias',0)) / (loaded_thresholds.get('tercias',1) or 1)) * weights.get('tercias',0)
                s_p = ((af_p - loaded_thresholds.get('pares',0)) / (loaded_thresholds.get('pares',1) or 1)) * weights.get('pares',0)
                current_omega_score = s_q + s_t + s_p

                candidatas_finales.append({
                    'combinacion': "-".join(map(str, combination)),
                    'simulated_original_score': simulated_original_score,
                    'current_omega_score': current_omega_score,
                    'afinidad_cuartetos': af_q
                })
        except (ValueError, TypeError, KeyError):
            continue

    logger.info(f"Filtro completado. Se encontraron {len(candidatas_finales)} candidatas de Omega Cero.")
    df_candidatas = pd.DataFrame(candidatas_finales)
    
    metrics['numero_candidatas'] = len(df_candidatas)
    
    return df_candidatas, metrics