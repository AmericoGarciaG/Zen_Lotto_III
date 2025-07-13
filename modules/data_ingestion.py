import pandas as pd
import logging
import config

logger = logging.getLogger(__name__)

def run_historical_load(last_concurso=0):
    """
    Descarga, valida y limpia el histórico. Si se provee last_concurso,
    filtra para devolver solo los sorteos más nuevos.
    """
    try:
        logger.info(f"Iniciando descarga de datos desde {config.HISTORICAL_DATA_URL}")
        df = pd.read_csv(config.HISTORICAL_DATA_URL, parse_dates=['FECHA'], dayfirst=True)
        logger.info("Descarga completada.")

        if not all(col in df.columns for col in config.EXPECTED_COLUMNS):
            missing = set(config.EXPECTED_COLUMNS) - set(df.columns)
            message = f"Error de validación: Faltan las columnas {missing} en el archivo CSV."
            logger.error(message)
            return None, message, False
        
        df = df[config.EXPECTED_COLUMNS]

        column_mapping = {
            'CONCURSO': 'concurso',
            'F1': 'r1', 'F2': 'r2', 'F3': 'r3', 
            'F4': 'r4', 'F5': 'r5', 'F6': 'r6',
            'BOLSA': 'bolsa',
            'FECHA': 'fecha'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        if last_concurso > 0:
            df = df[df['concurso'] > last_concurso].copy()
            logger.info(f"Filtrado aplicado. Se encontraron {len(df)} sorteos nuevos desde el concurso {last_concurso}.")

        result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
        initial_rows = len(df)
        
        df.dropna(subset=result_columns, inplace=True)
        
        for col in result_columns:
            df[col] = df[col].astype(int)
            
        df['bolsa'] = pd.to_numeric(df['bolsa'], errors='coerce')
        df.dropna(subset=['bolsa'], inplace=True)
        df['bolsa'] = df['bolsa'].astype(int)

        cleaned_rows = len(df)
        message = (
            f"Carga y procesamiento exitoso. Se procesaron {cleaned_rows} sorteos. "
            f"({initial_rows - cleaned_rows} filas con datos incompletos fueron descartadas)."
        )
        logger.info(message)
        return df, message, True

    except Exception as e:
        error_message = f"Error crítico durante la ingestión de datos: {e}"
        logger.error(error_message, exc_info=True)
        return None, error_message, False