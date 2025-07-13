import sqlite3
import pandas as pd
import logging
import config

logger = logging.getLogger(__name__)

TABLE_NAME_HISTORICO = "historico" # Renombramos para claridad
TABLE_NAME_OMEGA = "omega_class"   # Nueva tabla

def save_historico_to_db(df, mode='replace'):
    """
    Guarda un DataFrame en la BD.
    mode: 'replace' (por defecto) o 'append'.
    """
    if df.empty:
        logger.info("El DataFrame está vacío. No se realizarán cambios en la base de datos.")
        return True, "No hay nuevos registros que guardar en la base de datos."

    try:
        conn = sqlite3.connect(config.DB_FILE)
        df.to_sql(TABLE_NAME_HISTORICO, conn, if_exists=mode, index=False)
        conn.close()
        
        action = "guardaron" if mode == 'replace' else "añadieron"
        message = f"Se {action} {len(df)} registros en la base de datos ({config.DB_FILE})."
        logger.info(message)
        return True, message

    except Exception as e:
        logger.error(f"Error al guardar en la base de datos: {e}", exc_info=True)
        return False, f"Error al guardar en la base de datos: {e}"

def read_historico_from_db():
    """
    Lee la tabla 'historico' completa desde la base de datos SQLite y la
    devuelve como un DataFrame de pandas.
    """
    try:
        conn = sqlite3.connect(config.DB_FILE)
        df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME_HISTORICO}", conn, parse_dates=['fecha'])
        conn.close()
        return df
    except sqlite3.OperationalError:
        logger.warning(f"La tabla '{TABLE_NAME_HISTORICO}' no existe en la base de datos. Se retornará None.")
        return None
    except Exception as e:
        logger.error(f"Error al leer desde la base de datos: {e}", exc_info=True)
        return None

def get_last_concurso_from_db():
    """
    Obtiene el número del concurso más reciente almacenado en la base de datos.
    """
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f"SELECT MAX(concurso) FROM {TABLE_NAME_HISTORICO}")
        last_concurso = cursor.fetchone()[0]
        conn.close()
        
        # Si la tabla está vacía, last_concurso será None. Lo convertimos a 0.
        last_concurso = last_concurso if last_concurso is not None else 0
        logger.info(f"Último concurso encontrado en la BD: {last_concurso}")
        return last_concurso
        
    except sqlite3.OperationalError:
        logger.warning(f"La tabla '{TABLE_NAME_HISTORICO}' no existe. Se asume que el último concurso es 0.")
        if conn:
            conn.close()
        return 0
    except Exception as e:
        logger.error(f"Error al obtener el último concurso: {e}", exc_info=True)
        if conn:
            conn.close()
        return 0
    
def save_omega_class(omega_combinations_df):
    """
    Guarda un DataFrame de combinaciones Omega en la base de datos.
    Reemplaza la tabla por completo si ya existe.

    Args:
        omega_combinations_df (pd.DataFrame): DataFrame con las combinaciones Omega.

    Returns:
        tuple: (bool, str) - Éxito y mensaje.
    """
    if omega_combinations_df.empty:
        message = "No se encontraron combinaciones Omega para guardar."
        logger.warning(message)
        return False, message

    try:
        conn = sqlite3.connect(config.DB_FILE)
        # Guardamos el DataFrame en la nueva tabla.
        omega_combinations_df.to_sql(TABLE_NAME_OMEGA, conn, if_exists='replace', index=False)
        conn.close()
        
        message = f"Pre-generación completada. Se guardaron {len(omega_combinations_df)} combinaciones Omega en la tabla '{TABLE_NAME_OMEGA}'."
        logger.info(message)
        return True, message

    except Exception as e:
        message = f"Error al guardar la Clase Omega en la base de datos: {e}"
        logger.error(message, exc_info=True)
        return False, message