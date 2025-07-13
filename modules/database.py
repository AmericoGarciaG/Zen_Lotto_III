import sqlite3
import pandas as pd

DB_FILE = "zen_lotto.db"
TABLE_NAME = "historico"

def save_historico_to_db(df):
    """
    Guarda un DataFrame en la tabla 'historico' de la base de datos SQLite.
    La tabla se reemplazará por completo si ya existe.

    Args:
        df (pd.DataFrame): El DataFrame limpio con los datos históricos.

    Returns:
        tuple: (bool, str) - Un booleano indicando éxito y un mensaje.
    """
    try:
        # Establece la conexión con la base de datos (crea el archivo si no existe)
        conn = sqlite3.connect(DB_FILE)
        
        # Usa la función to_sql de pandas para guardar el DataFrame
        # if_exists='replace' borrará la tabla actual y la creará de nuevo.
        # Esto es ideal para la carga completa del histórico.
        df.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)
        
        # Cierra la conexión
        conn.close()
        
        return True, f"Se guardaron {len(df)} registros en la base de datos ({DB_FILE})."

    except Exception as e:
        return False, f"Error al guardar en la base de datos: {e}"