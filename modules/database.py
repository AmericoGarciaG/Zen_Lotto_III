import sqlite3
import pandas as pd

DB_FILE = "zen_lotto.db"
TABLE_NAME = "historico"

def save_historico_to_db(df):
    """
    Guarda un DataFrame en la tabla 'historico' de la base de datos SQLite.
    La tabla se reemplazará por completo si ya existe.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        df.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)
        conn.close()
        return True, f"Se guardaron {len(df)} registros en la base de datos ({DB_FILE})."
    except Exception as e:
        return False, f"Error al guardar en la base de datos: {e}"

# --- NUEVA FUNCIÓN ---
def read_historico_from_db():
    """
    Lee la tabla 'historico' completa desde la base de datos SQLite y la
    devuelve como un DataFrame de pandas.

    Returns:
        pd.DataFrame: DataFrame con los datos históricos, o None si hay un error.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        # Lee los datos de la tabla, convirtiendo la columna 'fecha' a datetime
        df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn, parse_dates=['fecha'])
        conn.close()
        return df
    except sqlite3.OperationalError:
        # Esto sucede si la tabla o la BD aún no existen
        return None
    except Exception as e:
        print(f"Error al leer desde la base de datos: {e}")
        return None