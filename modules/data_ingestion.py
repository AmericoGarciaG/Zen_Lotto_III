# data_ingestion.py

import pandas as pd
import logging
import ssl
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

def run_historical_load(game_config: Dict[str, Any], last_concurso: int = 0) -> Tuple[Optional[pd.DataFrame], str, bool]:
    """
    Descarga, valida y limpia el histórico para un juego específico.
    """
    data_source_config = game_config['data_source']
    url = data_source_config['url']
    expected_cols = data_source_config['expected_columns']
    col_mapping = data_source_config['column_mapping']
    result_columns = data_source_config['result_columns']

    try:
        logger.info(f"Iniciando descarga de datos para '{game_config['display_name']}' desde {url}")

        ssl._create_default_https_context = ssl._create_unverified_context
        
        # Leemos el CSV, parseamos fechas y eliminamos espacios en blanco de los encabezados
        df = pd.read_csv(url, parse_dates=['FECHA'], dayfirst=True)
        df.columns = df.columns.str.strip()
        
        logger.info("Descarga completada. Validando columnas...")

        if not all(col in df.columns for col in expected_cols):
            missing = set(expected_cols) - set(df.columns)
            return None, f"Error: Faltan las columnas {missing}.", False
        
        df = df[expected_cols]
        df.rename(columns=col_mapping, inplace=True)
        
        # Manejo de la columna 'bolsa' (si no existe, se crea con ceros)
        if 'bolsa' not in df.columns:
            logger.warning("La columna 'bolsa' no existe en los datos de origen. Se creará con valor 0.")
            df['bolsa'] = 0
            
        if last_concurso > 0:
            df = df[df['concurso'] > last_concurso].copy()

        # Limpieza de datos
        initial_rows = len(df)
        df.dropna(subset=result_columns, inplace=True)
        for col in result_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(subset=result_columns, inplace=True)
        for col in result_columns:
            df[col] = df[col].astype(int)

        df['bolsa'] = pd.to_numeric(df['bolsa'], errors='coerce').fillna(0).astype(int)
        
        cleaned_rows = len(df)
        dropped_rows = initial_rows - cleaned_rows
        message = (f"Carga para '{game_config['display_name']}' exitosa. "
                   f"Se procesaron {cleaned_rows} nuevos sorteos (se descartaron {dropped_rows} por datos inválidos).")
        
        return df, message, True

    except Exception as e:
        error_message = f"Error crítico durante la ingestión de datos para '{game_config['display_name']}': {e}"
        logger.error(error_message, exc_info=True)
        return None, error_message, False