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
    
def get_random_omega_combination():
    """
    Selecciona una combinación aleatoria INÉDITA (ha_salido=0) de la tabla 'omega_class'.
    """
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        # --- CONSULTA MODIFICADA ---
        # Añadimos la condición WHERE para filtrar solo las que no han salido
        query = f"SELECT c1, c2, c3, c4, c5, c6 FROM {TABLE_NAME_OMEGA} WHERE ha_salido = 0 ORDER BY RANDOM() LIMIT 1"
        # -------------------------
        cursor = conn.cursor()
        cursor.execute(query)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            logger.info(f"Combinación Omega aleatoria INÉDITA obtenida de la BD: {list(row)}")
            return list(row)
        else:
            logger.warning("No se encontró ninguna combinación Omega INÉDITA disponible.")
            return None

    except sqlite3.OperationalError:
        logger.error(f"La tabla '{TABLE_NAME_OMEGA}' no existe. Debe ser pre-generada primero.", exc_info=True)
        if conn: conn.close()
        return None
    except Exception as e:
        logger.error(f"Error al obtener una combinación Omega aleatoria: {e}", exc_info=True)
        if conn: conn.close()
        return None
    
# modules/database.py

def find_closest_omega(user_combo, match_count):
    """
    Busca en la BD una combinación Omega aleatoria que tenga exactamente
    'match_count' números en común con la combinación del usuario.
    """
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        # SQLite no tiene un 'IN' para tuplas, así que lo formateamos directamente.
        # Es seguro porque sabemos que user_combo es una lista de números.
        user_combo_str = ", ".join(map(str, user_combo))
        
        # Esta consulta cuenta cuántas columnas (c1 a c6) están en la lista de números del usuario.
        query = f"""
            SELECT c1, c2, c3, c4, c5, c6
            FROM {TABLE_NAME_OMEGA}
            WHERE 
                (CASE WHEN c1 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c2 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c3 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c4 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c5 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c6 IN ({user_combo_str}) THEN 1 ELSE 0 END) = ?
            AND ha_salido = 0
            ORDER BY RANDOM()
            LIMIT 1
        """
        cursor = conn.cursor()
        # Pasamos match_count como un parámetro seguro a la consulta
        cursor.execute(query, (match_count,))
        
        row = cursor.fetchone()
        conn.close()
        
        return list(row) if row else None

    except Exception as e:
        logger.error(f"Error al buscar la combinación más cercana: {e}", exc_info=True)
        if conn: conn.close()
        return None