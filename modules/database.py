import sqlite3
import pandas as pd
import logging
import config
import json

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
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS umbrales_trayectoria (
                ultimo_concurso_usado INTEGER PRIMARY KEY,
                umbral_pares INTEGER NOT NULL,
                umbral_tercias INTEGER NOT NULL,
                umbral_cuartetos INTEGER NOT NULL,
                cobertura_historica REAL NOT NULL,
                cobertura_universal_estimada REAL NOT NULL,
                fecha_calculo DATETIME
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS frecuencias_trayectoria (
                ultimo_concurso_usado INTEGER PRIMARY KEY,
                total_pares_unicos INTEGER NOT NULL,
                suma_freq_pares INTEGER NOT NULL,
                total_tercias_unicas INTEGER NOT NULL,
                suma_freq_tercias INTEGER NOT NULL,
                total_cuartetos_unicos INTEGER NOT NULL,
                suma_freq_cuartetos INTEGER NOT NULL,
                fecha_calculo DATETIME
            );
        """)
        logger.info("Asegurada la existencia de la tabla 'frecuencias_trayectoria'.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS afinidades_trayectoria (
                ultimo_concurso_usado INTEGER PRIMARY KEY,
                afin_pares_media REAL NOT NULL,
                afin_pares_mediana REAL NOT NULL,
                afin_pares_min INTEGER NOT NULL,
                afin_pares_max INTEGER NOT NULL,
                afin_tercias_media REAL NOT NULL,
                afin_tercias_mediana REAL NOT NULL,
                afin_tercias_min INTEGER NOT NULL,
                afin_tercias_max INTEGER NOT NULL,
                afin_cuartetos_media REAL NOT NULL,
                afin_cuartetos_mediana REAL NOT NULL,
                afin_cuartetos_min INTEGER NOT NULL,
                afin_cuartetos_max INTEGER NOT NULL,
                fecha_calculo DATETIME
            );
        """)
        logger.info("Asegurada la existencia de la tabla 'afinidades_trayectoria'.")
        
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

def count_omega_class():
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

def export_registrations_to_json():
    try:
        df = get_all_registrations()
        if df.empty:
            return False, "No hay registros para exportar."
        
        if 'fecha_registro' in df.columns:
            df['fecha_registro'] = df['fecha_registro'].astype(str)

        df.to_json(config.REGISTROS_BACKUP_FILE, orient='records', indent=4)
        logger.info(f"Se han exportado {len(df)} registros a '{config.REGISTROS_BACKUP_FILE}'")
        return True, f"Se han exportado {len(df)} registros con éxito."
    except Exception as e:
        logger.error(f"Error al exportar registros: {e}", exc_info=True)
        return False, "Ocurrió un error durante la exportación."

def import_registrations_from_json(overwrite=False):
    try:
        with open(config.REGISTROS_BACKUP_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return 0, 0, 0, f"No se encontró el archivo de respaldo '{config.REGISTROS_BACKUP_FILE}'."
    
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()
    
    added_count = 0
    updated_count = 0
    
    for record in data:
        combo_str = record.get('combinacion')
        nombre = record.get('nombre_completo')
        movil = record.get('movil')
        fecha = record.get('fecha_registro')

        if not all([combo_str, nombre, movil]):
            continue

        try:
            query = f"INSERT INTO {TABLE_NAME_REGISTROS} (combinacion, nombre_completo, movil, fecha_registro) VALUES (?, ?, ?, ?)"
            cursor.execute(query, (combo_str, nombre, movil, fecha))
            added_count += 1
        except sqlite3.IntegrityError:
            if overwrite:
                update_query = f"UPDATE {TABLE_NAME_REGISTROS} SET nombre_completo = ?, movil = ? WHERE combinacion = ?"
                cursor.execute(update_query, (nombre, movil, combo_str))
                updated_count += 1

    conn.commit()
    conn.close()
    
    message = f"Importación finalizada. {added_count} registros añadidos, {updated_count} actualizados."
    logger.info(message)
    return added_count, updated_count, len(data), message

def read_trajectory_data():
    try:
        conn = sqlite3.connect(config.DB_FILE)
        query = f"SELECT * FROM umbrales_trayectoria ORDER BY ultimo_concurso_usado ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        logger.info(f"DB READ: 'read_trajectory_data' success. Found {len(df)} rows.")
        if not df.empty:
            for col in df.columns:
                if col != 'fecha_calculo':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except (pd.errors.DatabaseError, Exception) as e:
        logger.error(f"Error en 'read_trajectory_data': {e}", exc_info=True)
        return pd.DataFrame()

def read_freq_trajectory_data():
    try:
        conn = sqlite3.connect(config.DB_FILE)
        query = "SELECT * FROM frecuencias_trayectoria ORDER BY ultimo_concurso_usado ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        logger.info(f"DB READ: 'read_freq_trajectory_data' success. Found {len(df)} rows.")
        if not df.empty:
            for col in df.columns:
                if col != 'fecha_calculo':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except (pd.errors.DatabaseError, Exception) as e:
        logger.error(f"Error en 'read_freq_trajectory_data': {e}", exc_info=True)
        return pd.DataFrame()

def read_affinity_trajectory_data():
    try:
        conn = sqlite3.connect(config.DB_FILE)
        query = "SELECT * FROM afinidades_trayectoria ORDER BY ultimo_concurso_usado ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        logger.info(f"DB READ: 'read_affinity_trajectory_data' success. Found {len(df)} rows.")
        if not df.empty:
            for col in df.columns:
                if col != 'fecha_calculo':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except (pd.errors.DatabaseError, Exception) as e:
        logger.error(f"Error en 'read_affinity_trajectory_data': {e}", exc_info=True)
        return pd.DataFrame()