import json
from collections import Counter
from itertools import combinations
import modules.database as db # Importamos nuestro módulo de base de datos

FREQUENCIES_FILE = "frecuencias.json"

def calculate_and_save_frequencies():
    """
    Orquesta el proceso completo de cálculo de frecuencias:
    1. Lee los datos históricos desde la base de datos.
    2. Extrae las subsecuencias (pares, tercias, cuartetos).
    3. Cuenta la frecuencia de cada subsecuencia.
    4. Guarda los resultados en un archivo JSON.

    Returns:
        tuple: (bool, str) - Un booleano indicando éxito y un mensaje.
    """
    # 1. Leer datos desde la BD
    df_historico = db.read_historico_from_db()
    
    if df_historico is None or df_historico.empty:
        return False, "No se encontraron datos históricos en la base de datos. Por favor, genere el histórico primero."

    # Preparamos las listas para almacenar todas las subsecuencias de todos los sorteos
    all_pairs = []
    all_triplets = []
    all_quartets = []

    # Columnas de los resultados
    result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
    
    # 2. Extraer subsecuencias para cada sorteo (Paso 1 de la metodología)
    for index, row in df_historico.iterrows():
        # Extraemos los 6 números del sorteo actual
        draw = sorted([row[col] for col in result_columns])
        
        # Generamos y añadimos las combinaciones a nuestras listas globales
        all_pairs.extend(list(combinations(draw, 2)))
        all_triplets.extend(list(combinations(draw, 3)))
        all_quartets.extend(list(combinations(draw, 4)))

    # 3. Contar frecuencias (Paso 2 de la metodología)
    # Counter hace el trabajo pesado de contar las ocurrencias de cada tupla
    freq_pairs = Counter(all_pairs)
    freq_triplets = Counter(all_triplets)
    freq_quartets = Counter(all_quartets)

    # 4. Crear mapas de frecuencia y guardar en JSON (Paso 3 de la metodología)
    # Las tuplas no pueden ser claves en JSON, así que las convertimos a string.
    output_data = {
        "FREQ_PARES": {str(k): v for k, v in freq_pairs.items()},
        "FREQ_TERCIAS": {str(k): v for k, v in freq_triplets.items()},
        "FREQ_CUARTETOS": {str(k): v for k, v in freq_quartets.items()}
    }

    try:
        with open(FREQUENCIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        message = (
            f"Cálculo de frecuencias completado. "
            f"Se encontraron {len(freq_pairs)} pares, "
            f"{len(freq_triplets)} tercias y "
            f"{len(freq_quartets)} cuartetos únicos. "
            f"Resultados guardados en '{FREQUENCIES_FILE}'."
        )
        return True, message

    except Exception as e:
        return False, f"Error al guardar el archivo de frecuencias: {e}"