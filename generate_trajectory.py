import pandas as pd
import logging
import time
import sqlite3
import sys # Para leer argumentos de línea de comandos

# --- Importar nuestros módulos ---
from utils.logger_config import setup_logger
setup_logger()

from modules import database as db
from modules import ml_optimizer
import config

logger = logging.getLogger(__name__)

# --- (Las funciones de ayuda calculate_frequencies_for_subset y save_trajectory_point no cambian) ---
def calculate_frequencies_for_subset(df_subset):
    from collections import Counter
    from itertools import combinations
    freq_pairs, freq_triplets, freq_quartets = Counter(), Counter(), Counter()
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    for _, row in df_subset.iterrows():
        try:
            draw = sorted([int(row[col]) for col in result_columns])
            freq_pairs.update(combinations(draw, 2))
            freq_triplets.update(combinations(draw, 3))
            freq_quartets.update(combinations(draw, 4))
        except (ValueError, TypeError): continue
    return {"pares": freq_pairs, "tercias": freq_triplets, "cuartetos": freq_quartets}

def save_trajectory_point(concurso_num, report):
    """Guarda un único resultado de optimización en la BD, asegurando los tipos de datos."""
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        query = """
            INSERT OR REPLACE INTO umbrales_trayectoria 
            (ultimo_concurso_usado, umbral_pares, umbral_tercias, umbral_cuartetos, 
             cobertura_historica, cobertura_universal_estimada, fecha_calculo)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        """
        
        # --- INICIO DE LA CORRECCIÓN DE TIPOS ---
        thresholds = report['new_thresholds']
        params = (
            int(concurso_num), # Convertimos explícitamente a int de Python
            int(thresholds.get('pares', 0)),
            int(thresholds.get('tercias', 0)),
            int(thresholds.get('cuartetos', 0)),
            float(report.get('cobertura_historica', 0.0)), # Convertimos a float
            float(report.get('cobertura_universal_estimada', 0.0))
        )
        # --- FIN DE LA CORRECCIÓN ---

        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        logger.error(f"Error guardando punto de trayectoria para {concurso_num}: {e}")
    finally:
        if conn:
            conn.close()

# --- Función Principal del Script Modificada ---
def main(block_size=100):
    """
    Ejecuta el análisis de Walk-Forward por bloques para generar la trayectoria.
    Args:
        block_size (int): El número de sorteos a añadir en cada iteración.
    """
    logger.info("="*60)
    logger.info("INICIANDO SCRIPT DE GENERACIÓN DE TRAYECTORIA (POR BLOQUES)")
    logger.info(f"Tamaño de bloque configurado: {block_size} sorteos")
    logger.info("="*60)
    
    df_full_historico = db.read_historico_from_db()
    if df_full_historico.empty:
        logger.error("El histórico está vacío. Ejecute la configuración en la app primero.")
        return
        
    df_full_historico = df_full_historico.sort_values(by='concurso').reset_index(drop=True)
    total_sorteos = len(df_full_historico)
    
    start_point = 50 # Base estadística mínima
    
    # Creamos los puntos de corte para el análisis por bloques
    analysis_points = list(range(start_point, total_sorteos, block_size))
    # Nos aseguramos de que el último sorteo siempre se incluya
    if total_sorteos not in analysis_points:
        analysis_points.append(total_sorteos)

    logger.info(f"Se analizarán {len(analysis_points)} puntos de la trayectoria: {analysis_points}")
    
    script_start_time = time.time()
    
    for i, end_index in enumerate(analysis_points):
        iter_start_time = time.time()
        
        # Obtenemos el subconjunto de datos para esta iteración (hasta el punto de corte)
        df_subset = df_full_historico.head(end_index)
        ultimo_concurso = df_subset.iloc[-1]['concurso']
        
        logger.info(f"--- Procesando Bloque {i+1}/{len(analysis_points)} (hasta concurso {ultimo_concurso}, {end_index} sorteos) ---")
        
        freqs_subset = calculate_frequencies_for_subset(df_subset)
        success, _, report = ml_optimizer.run_optimization(df_subset, freqs_subset)
        
        if success and isinstance(report, dict) and 'new_thresholds' in report:
            save_trajectory_point(ultimo_concurso, report)
            ch = report.get('cobertura_historica', 0)
            cu = report.get('cobertura_universal_estimada', 0)
            logger.info(f"Punto de trayectoria guardado. CH: {ch:.1%}, CU: {cu:.2%}")
        else:
            logger.error(f"La optimización falló para el bloque hasta el sorteo {ultimo_concurso}.")
        
        iter_time = time.time() - iter_start_time
        logger.info(f"Bloque completado en {iter_time:.2f} segundos.")

    script_total_time = time.time() - script_start_time
    logger.info("="*60)
    logger.info(f"GENERACIÓN DE TRAYECTORIA COMPLETA. Tiempo total: {script_total_time / 60:.2f} minutos.")
    logger.info("="*60)

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    
    # Leemos el tamaño del bloque desde la línea de comandos
    # Si no se proporciona, usamos 100 por defecto.
    if len(sys.argv) > 1:
        try:
            block_size_arg = int(sys.argv[1])
            main(block_size=block_size_arg)
        except ValueError:
            print("Error: El tamaño del bloque debe ser un número entero.")
            print("Uso: python generate_trajectory.py [tamaño_del_bloque]")
    else:
        main() # Llama a main con el valor por defecto de 100