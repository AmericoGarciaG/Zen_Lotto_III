# modules/ml_optimizer.py
import logging
import re
import pandas as pd
import numpy as np
import config

logger = logging.getLogger(__name__)

def _update_config_file(new_thresholds):
    """
    Actualiza de forma segura el archivo config.py con los nuevos umbrales,
    leyendo y reescribiendo el archivo línea por línea para máxima robustez.
    """
    try:
        with open('config.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            # Comprobamos si la línea define uno de nuestros umbrales
            if line.strip().startswith('UMBRAL_PARES'):
                new_lines.append(f'UMBRAL_PARES = {new_thresholds["pares"]}\n')
            elif line.strip().startswith('UMBRAL_TERCIAS'):
                new_lines.append(f'UMBRAL_TERCIAS = {new_thresholds["tercias"]}\n')
            elif line.strip().startswith('UMBRAL_CUARTETOS'):
                new_lines.append(f'UMBRAL_CUARTETOS = {new_thresholds["cuartetos"]}\n')
            else:
                # Si no es una línea de umbral, la mantenemos como está
                new_lines.append(line)

        with open('config.py', 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
        logger.info(f"Archivo config.py actualizado con umbrales: {new_thresholds}")
        return True
    except Exception as e:
        logger.error(f"Error crítico al actualizar config.py: {e}", exc_info=True)
        return False

def optimize_thresholds(df_historico, freqs, coverage_target=0.60):
    """
    Función principal que optimiza los umbrales.
    Recibe el histórico y las frecuencias como DataFrames.
    """
    from modules.omega_logic import _calculate_subsequence_affinity

    logger.info(f"Iniciando optimización de umbrales con objetivo de cobertura: {coverage_target:.0%}")
    
    # 1. Calcular afinidades para todo el histórico
    affinities = []
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    for _, row in df_historico.iterrows():
        try:
            combo = [int(row[col]) for col in result_columns]
            affinities.append({
                'pares': _calculate_subsequence_affinity(combo, freqs, 2),
                'tercias': _calculate_subsequence_affinity(combo, freqs, 3),
                'cuartetos': _calculate_subsequence_affinity(combo, freqs, 4)
            })
        except (ValueError, TypeError):
            continue # Ignora filas con datos no numéricos

    if not affinities:
        return False, "No se pudieron calcular afinidades. Revise los datos del histórico.", {}

    df_affinities = pd.DataFrame(affinities)

    # 2. Búsqueda de umbrales óptimos por percentiles
    best_coverage_diff = float('inf')
    best_thresholds = None
    percentiles_to_test = np.arange(0.1, 1.0, 0.05) # Testeamos en incrementos de 5%

    for p_p in percentiles_to_test:
        for p_t in percentiles_to_test:
            for p_q in percentiles_to_test:
                umbral_p = int(np.percentile(df_affinities['pares'], p_p))
                umbral_t = int(np.percentile(df_affinities['tercias'], p_t))
                umbral_q = int(np.percentile(df_affinities['cuartetos'], p_q))
                
                mask = ((df_affinities['pares'] >= umbral_p) &
                        (df_affinities['tercias'] >= umbral_t) &
                        (df_affinities['cuartetos'] >= umbral_q))
                
                coverage = mask.mean()
                
                # Buscamos la cobertura más cercana al objetivo
                current_diff = abs(coverage - coverage_target)
                if current_diff < best_coverage_diff:
                    best_coverage_diff = current_diff
                    best_thresholds = {'pares': umbral_p, 'tercias': umbral_t, 'cuartetos': umbral_q}
                    
    if best_thresholds is None:
        return False, "No se encontraron umbrales óptimos.", {}

    # 3. Actualizar el archivo de configuración
    if not _update_config_file(best_thresholds):
        return False, "Falló la actualización del archivo de configuración.", {}

    final_coverage = abs(best_coverage_diff - coverage_target)
    report = {
        "new_thresholds": best_thresholds,
        "coverage": final_coverage
    }
    
    return True, "Umbrales optimizados y actualizados con éxito.", report