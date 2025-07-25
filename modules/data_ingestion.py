import pandas as pd
import logging
import config
import ssl
import urllib.request

logger = logging.getLogger(__name__)

def run_historical_load(last_concurso=0):
    """
    Descarga, valida y limpia el histórico.
    Aplica una solución global para el problema de certificados SSL en Docker.
    """
    try:
        logger.info(f"Iniciando descarga de datos desde {config.HISTORICAL_DATA_URL}")

        # --- INICIO DE LA SOLUCIÓN SSL GLOBAL ---
        # Creamos un contexto no verificado y lo establecemos como el
        # contexto por defecto para todas las peticiones HTTPS de urllib.
        # Esto soluciona el error [SSL: CERTIFICATE_VERIFY_FAILED] de forma global.
        ssl._create_default_https_context = ssl._create_unverified_context
        # ------------------------------------
        
        # Ahora, la llamada a pd.read_csv es simple, sin parámetros extra.
        df = pd.read_csv(
            config.HISTORICAL_DATA_URL, 
            parse_dates=['FECHA'], 
            dayfirst=True
        )

        logger.info("Descarga completada.")

        if not all(col in df.columns for col in config.EXPECTED_COLUMNS):
            missing = set(config.EXPECTED_COLUMNS) - set(df.columns)
            return None, f"Error: Faltan las columnas {missing}.", False
        
        df = df[config.EXPECTED_COLUMNS]

        column_mapping = {
            'CONCURSO': 'concurso', 'F1': 'r1', 'F2': 'r2', 'F3': 'r3', 
            'F4': 'r4', 'F5': 'r5', 'F6': 'r6', 'BOLSA': 'bolsa', 'FECHA': 'fecha'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        if last_concurso > 0:
            df = df[df['concurso'] > last_concurso].copy()

        result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
        initial_rows = len(df)
        df.dropna(subset=result_columns, inplace=True)
        
        for col in result_columns: df[col] = df[col].astype(int)
            
        df['bolsa'] = pd.to_numeric(df['bolsa'], errors='coerce')
        df.dropna(subset=['bolsa'], inplace=True)
        df['bolsa'] = df['bolsa'].astype(int)

        cleaned_rows = len(df)
        message = f"Carga y procesamiento exitoso. Se procesaron {cleaned_rows} sorteos."
        return df, message, True

    except Exception as e:
        error_message = f"Error crítico durante la ingestión de datos: {e}"
        logger.error(error_message, exc_info=True)
        return None, error_message, False