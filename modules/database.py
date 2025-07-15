import sqlite3
import pandas as pd
import logging
import config

logger = logging.getLogger(__name__)

TABLE_NAME_HISTORICO = "historico"
TABLE_NAME_OMEGA = "omega_class"
TABLE_NAME_REGISTROS = "registros_omega"

def save_historico_to_db(df, mode='replace'):
    """
    Guarda un DataFrame en la BD. También se asegura de que las otras tablas existan.
    """
    if df.empty and mode == 'append':
        return True, "No hay nuevos registros que guardar."

    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_REGISTROS} (
                combinacion TEXT PRIMARY KEY, nombre_completo TEXT NOT NULL,
                movil TEXT NOT NULL, fecha_registro DATETIME
            );
        """)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME_OMEGA} (
                c1 INTEGER, c2 INTEGER, c3 INTEGER, c4 INTEGER, c5 INTEGER, c6 INTEGER,
                ha_salido INTEGER, afinidad_pares INTEGER, afinidad_tercias INTEGER,
                afinidad_cuartetos INTEGER,
                PRIMARY KEY (c1, c2, c3, c4, c5, c6)
            );
        """)
        
        df.to_sql(TABLE_NAME_HISTORICO, conn, if_exists=mode, index=False)
        conn.commit()
        conn.close()
        
        action = "guardaron" if mode == 'replace' else "añadieron"
        message = f"Se {action} {len(df)} registros en la base de datos."
        return True, message

    except Exception as e:
        return False, f"Error al guardar en la base de datos: {e}"

def read_historico_from_db():
    """
    Lee la tabla 'historico' completa, ordenada por el concurso más reciente.
    """
    try:
        conn = sqlite3.connect(config.DB_FILE)
        query = f"SELECT * FROM {TABLE_NAME_HISTORICO} ORDER BY concurso DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except pd.errors.DatabaseError:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def save_omega_class(omega_combinations_df):
    if omega_combinations_df.empty:
        return False, "No se encontraron combinaciones Omega para guardar."
    try:
        conn = sqlite3.connect(config.DB_FILE)
        omega_combinations_df.to_sql(TABLE_NAME_OMEGA, conn, if_exists='replace', index=False)
        conn.close()
        return True, f"Pre-generación completada. Se guardaron {len(omega_combinations_df)} combinaciones Omega."
    except Exception as e:
        return False, f"Error al guardar la Clase Omega: {e}"
    
def get_random_omega_combination():
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        query = f"SELECT c1, c2, c3, c4, c5, c6 FROM {TABLE_NAME_OMEGA} WHERE ha_salido = 0 ORDER BY RANDOM() LIMIT 1"
        row = pd.read_sql_query(query, conn).iloc[0].tolist()
        conn.close()
        return row
    except (pd.errors.DatabaseError, IndexError, Exception):
        if conn: conn.close()
        return None

def find_closest_omega(user_combo, match_count):
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        user_combo_str = ", ".join(map(str, user_combo))
        query = f"""
            SELECT c1, c2, c3, c4, c5, c6 FROM {TABLE_NAME_OMEGA}
            WHERE (
                (CASE WHEN c1 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c2 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c3 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c4 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c5 IN ({user_combo_str}) THEN 1 ELSE 0 END +
                 CASE WHEN c6 IN ({user_combo_str}) THEN 1 ELSE 0 END) = ?
            ) AND ha_salido = 0
            ORDER BY RANDOM() LIMIT 1
        """
        df = pd.read_sql_query(query, conn, params=(match_count,))
        conn.close()
        return df.iloc[0].tolist() if not df.empty else None
    except Exception:
        if conn: conn.close()
        return None

def register_omega_combination(combinacion, nombre, movil):
    combo_str = "-".join(map(str, sorted(combinacion)))
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        query = f"INSERT INTO {TABLE_NAME_REGISTROS} (combinacion, nombre_completo, movil, fecha_registro) VALUES (?, ?, ?, datetime('now', 'localtime'))"
        cursor.execute(query, (combo_str, nombre, movil))
        conn.commit()
        return True, "¡Combinación registrada con éxito!"
    except sqlite3.IntegrityError:
        return False, "Esta combinación ya ha sido registrada."
    except Exception:
        return False, "Ocurrió un error inesperado al registrar."
    finally:
        if conn: conn.close()

def get_all_registrations():
    try:
        conn = sqlite3.connect(config.DB_FILE)
        df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME_REGISTROS}", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame(columns=['combinacion', 'nombre_completo', 'movil', 'fecha_registro'])

def delete_registration(combinacion_str):
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        query = f"DELETE FROM {TABLE_NAME_REGISTROS} WHERE combinacion = ?"
        cursor.execute(query, (combinacion_str,))
        conn.commit()
        if cursor.rowcount > 0: return True, "Registro eliminado con éxito."
        else: return False, "El registro no fue encontrado."
    except Exception:
        return False, "Ocurrió un error inesperado al eliminar."
    finally:
        if conn: conn.close()

# --- NUEVA FUNCIÓN PARA LOS GRÁFICOS ---
def count_omega_class():
    """Cuenta el número total de combinaciones en la tabla omega_class."""
    conn = None
    try:
        conn = sqlite3.connect(config.DB_FILE)
        query = f"SELECT COUNT(*) FROM {TABLE_NAME_OMEGA}"
        count = pd.read_sql_query(query, conn).iloc[0, 0]
        conn.close()
        return count
    except (pd.errors.DatabaseError, IndexError, Exception):
        if conn: conn.close()
        return 0