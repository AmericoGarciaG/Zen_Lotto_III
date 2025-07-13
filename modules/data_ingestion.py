import pandas as pd
import config

def run_historical_load():
    """
    Descarga el archivo CSV con el histórico de sorteos, lo valida,
    lo limpia y lo devuelve en un formato estandarizado.
    """
    try:
        # Usamos parse_dates para que pandas intente convertir la columna 'FECHA' a datetime
        # y dayfirst=True para que interprete formatos como 'dd/mm/yyyy' correctamente.
        df = pd.read_csv(config.HISTORICAL_DATA_URL, parse_dates=['FECHA'], dayfirst=True)

        # 1. Validación: Verificar que las columnas que necesitamos existan.
        if not all(col in df.columns for col in config.EXPECTED_COLUMNS):
            missing = set(config.EXPECTED_COLUMNS) - set(df.columns)
            return (
                None, 
                f"Error de validación: Faltan las columnas {missing} en el archivo CSV.",
                False
            )
        
        # 2. Selección de columnas: Nos quedamos solo con las que nos interesan.
        df = df[config.EXPECTED_COLUMNS]

        # 3. Mapeo/Renombrado de columnas: Estandarizamos los nombres.
        column_mapping = {
            'CONCURSO': 'concurso',
            'F1': 'r1', 'F2': 'r2', 'F3': 'r3', 
            'F4': 'r4', 'F5': 'r5', 'F6': 'r6',
            'BOLSA': 'bolsa',
            'FECHA': 'fecha'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # 4. Limpieza y conversión de tipos.
        result_columns = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']
        initial_rows = len(df)
        
        # Eliminamos filas con nulos en las columnas de resultados
        df.dropna(subset=result_columns, inplace=True)
        
        # Convertimos columnas de resultados a enteros
        for col in result_columns:
            df[col] = df[col].astype(int)
            
        # Convertimos la bolsa a numérico, manejando errores (si algo no es un número)
        # 'coerce' convertirá los valores no numéricos en NaT (Not a Time), que luego podemos manejar.
        df['bolsa'] = pd.to_numeric(df['bolsa'], errors='coerce')
        df.dropna(subset=['bolsa'], inplace=True) # Eliminamos filas donde la bolsa no era un número
        df['bolsa'] = df['bolsa'].astype(int)


        cleaned_rows = len(df)
        message = (
            f"Carga exitosa. Se han procesado y validado {cleaned_rows} sorteos. "
            f"({initial_rows - cleaned_rows} filas con datos incompletos fueron descartadas)."
        )
        return df, message, True

    except Exception as e:
        error_message = f"Error al descargar o procesar el histórico: {e}"
        return None, error_message, False