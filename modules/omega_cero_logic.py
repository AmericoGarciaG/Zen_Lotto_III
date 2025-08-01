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
    Función principal para aplicar el filtro dinámico y encontrar las candidatas de Omega Cero.
    """
    logger.info(f"Iniciando cálculo de candidatas Omega Cero para '{game_config['display_name']}'...")
    db_path = game_config['paths']['db']
    result_columns = game_config['data_source']['result_columns']

    metrics = get_omega_cero_metrics(db_path)
    if not metrics:
        logger.warning("No se encontraron métricas de Omega Cero. Ejecute primero 'generate_omega_score_trajectory.py'.")
        return pd.DataFrame(), {}

    # Usamos el histórico enriquecido, ya que contiene todas las combinaciones Omega que han salido
    df_omega_class = db.read_historico_from_db(db_path)
    if df_omega_class.empty:
        logger.warning("El histórico enriquecido está vacío. Ejecute la configuración primero.")
        return pd.DataFrame(), metrics
    
    # Nos quedamos solo con las que son de la Clase Omega para tener nuestra base de candidatas
    df_omega_class = df_omega_class[df_omega_class['es_omega'] == 1].copy()

    freqs = ol.get_frequencies(game_config)
    if not freqs:
        logger.warning("No se encontraron frecuencias."); return pd.DataFrame(), metrics

    # Calcular el modelo "actual" (simplificado)
    df_full_historico = db.read_historico_from_db(db_path)
    afinidades_actuales = [
        ol._calculate_subsequence_affinity(sorted([int(r[c]) for c in result_columns]), freqs, 2) # type: ignore
        for _, r in df_full_historico.iterrows()
    ]
    umbral_pares_actual = int(np.percentile(afinidades_actuales, 20))

    candidatas = []
    total_candidatas = len(df_omega_class)
    logger.info(f"Simulando 'Score al nacer' para {total_candidatas} combinaciones Omega...")
    
    for i, row in df_omega_class.iterrows():
        try:
            combination = [int(row[col]) for col in result_columns] # type: ignore
            af_p = ol._calculate_subsequence_affinity(combination, freqs, 2)
            
            # --- INICIO DE LA CORRECCIÓN ---
            # Calculamos la afinidad de cuartetos para incluirla en el resultado
            af_q = ol._calculate_subsequence_affinity(combination, freqs, 4)
            # --- FIN DE LA CORRECCIÓN ---

            simulated_original_score = (af_p - umbral_pares_actual) / (umbral_pares_actual or 1)
            
            if metrics['banda_normal_inferior'] <= simulated_original_score <= metrics['banda_normal_superior']:
                candidatas.append({
                    'combinacion': "-".join(map(str, combination)),
                    'simulated_original_score': simulated_original_score,
                    'current_omega_score': row['omega_score'],
                    # --- CORRECCIÓN: Se añade la afinidad de cuartetos ---
                    'afinidad_cuartetos': af_q
                })
        except (ValueError, TypeError):
            continue

    logger.info(f"Filtro completado. Se encontraron {len(candidatas)} candidatas de Omega Cero.")
    df_candidatas = pd.DataFrame(candidatas)
    
    metrics['numero_candidatas'] = len(df_candidatas)
    
    return df_candidatas, metrics