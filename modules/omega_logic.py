import json
from collections import Counter
from itertools import combinations
import logging
import modules.database as db
import config

logger = logging.getLogger(__name__)

def calculate_and_save_frequencies():
    """
    Orquesta el proceso de cálculo de frecuencias de forma inteligente e incremental.
    1. Carga las frecuencias y el último concurso procesado desde el archivo JSON.
    2. Obtiene los sorteos nuevos de la base de datos.
    3. Si hay sorteos nuevos, los procesa y actualiza los contadores de frecuencia.
    4. Guarda el estado actualizado en el archivo JSON.
    """
    logger.info("Iniciando el cálculo/actualización de frecuencias.")

    # 1. Cargar estado anterior (frecuencias y último concurso)
    try:
        with open(config.FREQUENCIES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertimos las claves de string "(1, 2)" a tuplas (1, 2)
        freq_pairs = Counter({eval(k): v for k, v in data.get("FREQ_PARES", {}).items()})
        freq_triplets = Counter({eval(k): v for k, v in data.get("FREQ_TERCIAS", {}).items()})
        freq_quartets = Counter({eval(k): v for k, v in data.get("FREQ_CUARTETOS", {}).items()})
        
        last_processed_concurso = data.get("last_processed_concurso", 0)
        logger.info(f"Frecuencias existentes cargadas. Último concurso procesado: {last_processed_concurso}")

    except (FileNotFoundError, json.JSONDecodeError):
        # Si el archivo no existe o está corrupto, empezamos de cero.
        logger.warning(f"No se encontró el archivo '{config.FREQUENCIES_FILE}' o está corrupto. Se creará uno nuevo.")
        freq_pairs, freq_triplets, freq_quartets = Counter(), Counter(), Counter()
        last_processed_concurso = 0

    # 2. Obtener sorteos nuevos de la base de datos
    df_historico = db.read_historico_from_db()
    if df_historico is None or df_historico.empty:
        return False, "La base de datos está vacía. Genere el histórico primero."

    # Filtramos para quedarnos solo con los sorteos que no han sido procesados
    df_new_draws = df_historico[df_historico['concurso'] > last_processed_concurso].copy()

    if df_new_draws.empty:
        message = "No hay sorteos nuevos para procesar. Las frecuencias están actualizadas."
        logger.info(message)
        return True, message

    logger.info(f"Se procesarán {len(df_new_draws)} sorteos nuevos.")
    
    # 3. Procesar solo los sorteos nuevos y actualizar los contadores
    all_new_pairs, all_new_triplets, all_new_quartets = [], [], []
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']

    for index, row in df_new_draws.iterrows():
        draw = sorted([row[col] for col in result_columns])
        all_new_pairs.extend(list(combinations(draw, 2)))
        all_new_triplets.extend(list(combinations(draw, 3)))
        all_new_quartets.extend(list(combinations(draw, 4)))

    # Usamos .update() para añadir los nuevos conteos a los existentes
    freq_pairs.update(all_new_pairs)
    freq_triplets.update(all_new_triplets)
    freq_quartets.update(all_new_quartets)
    
    # Actualizamos el número del último concurso que hemos procesado
    new_last_processed_concurso = df_new_draws['concurso'].max()

    # 4. Guardar el estado actualizado en el archivo JSON
    output_data = {
        "last_processed_concurso": int(new_last_processed_concurso),
        "FREQ_PARES": {str(k): v for k, v in freq_pairs.items()},
        "FREQ_TERCIAS": {str(k): v for k, v in freq_triplets.items()},
        "FREQ_CUARTETOS": {str(k): v for k, v in freq_quartets.items()}
    }

    try:
        with open(config.FREQUENCIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        message = f"Frecuencias actualizadas con {len(df_new_draws)} nuevos sorteos. Resultados guardados."
        logger.info(message)
        return True, message

    except Exception as e:
        message = f"Error al guardar el archivo de frecuencias actualizado: {e}"
        logger.error(message, exc_info=True)
        return False, message