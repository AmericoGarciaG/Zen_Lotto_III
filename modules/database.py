# database.py

import sqlite3
import pandas as pd
import logging
import config
import json
import os
from typing import Dict, Any, List, Tuple, Optional, Literal

logger = logging.getLogger(__name__)

TABLE_NAME_HISTORICO = "historico"
TABLE_NAME_OMEGA = "omega_class"
TABLE_NAME_REGISTROS = "registros_omega"

def _create_tables_if_not_exist(db_path: str):
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cursor = conn.cursor()
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME_REGISTROS} (combinacion TEXT PRIMARY KEY, nombre_completo TEXT NOT NULL, movil TEXT NOT NULL, fecha_registro DATETIME);")
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME_OMEGA} (c1 INTEGER, c2 INTEGER, c3 INTEGER, c4 INTEGER, c5 INTEGER, c6 INTEGER, c7 INTEGER, c8 INTEGER, ha_salido INTEGER, afinidad_pares INTEGER, afinidad_tercias INTEGER, afinidad_cuartetos INTEGER, PRIMARY KEY (c1, c2, c3, c4, c5, c6, c7, c8));")
        schemas = {'umbrales_trayectoria': config.UMBRALES_TRAYECTORIA_SCHEMA, 'frecuencias_trayectoria': config.FRECUENCIAS_TRAYECTORIA_SCHEMA, 'afinidades_trayectoria': config.AFINIDADES_TRAYECTORIA_SCHEMA, 'freq_dist_trayectoria': config.FREQ_DIST_TRAYECTORIA_SCHEMA}
        for table_name, schema_dict in schemas.items():
            columns_def = ", ".join([f"{col_name} {col_type}" for col_name, col_type in schema_dict.items()])
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def});")
        conn.commit()
    except Exception as e:
        logger.error(f"Error creando tablas en '{db_path}': {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

def save_historico_to_db(df: pd.DataFrame, db_path: str, mode: Literal['replace', 'append'] = 'replace') -> Tuple[bool, str]:
    if df.empty and mode == 'append': return True, "No hay nuevos registros que guardar."
    conn: Optional[sqlite3.Connection] = None
    try:
        _create_tables_if_not_exist(db_path)
        conn = sqlite3.connect(db_path)
        df.to_sql(TABLE_NAME_HISTORICO, conn, if_exists=mode, index=False)
        action = "guardaron" if mode == 'replace' else "añadieron"
        return True, f"Se {action} {len(df)} registros en la base de datos."
    except Exception as e:
        logger.error(f"Error al guardar en '{os.path.basename(db_path)}': {e}", exc_info=True)
        return False, f"Error al guardar en '{os.path.basename(db_path)}': {e}"
    finally:
        if conn: conn.close()

def save_omega_class(omega_combinations_df: pd.DataFrame, db_path: str) -> Tuple[bool, str]:
    if omega_combinations_df.empty: return False, "No se encontraron combinaciones Omega para guardar."
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(db_path)
        for i in range(1, 9):
            if f'c{i}' not in omega_combinations_df.columns: omega_combinations_df[f'c{i}'] = None
        cols = [f'c{i}' for i in range(1, 9)] + ['ha_salido', 'afinidad_pares', 'afinidad_tercias', 'afinidad_cuartetos']
        omega_combinations_df = omega_combinations_df[cols]
        omega_combinations_df.to_sql(TABLE_NAME_OMEGA, conn, if_exists='replace', index=False)
        return True, f"Pre-generación completada. Se guardaron {len(omega_combinations_df)} combinaciones Omega."
    except Exception as e:
        logger.error(f"Error al guardar la Clase Omega en '{os.path.basename(db_path)}': {e}", exc_info=True)
        return False, f"Error al guardar la Clase Omega en '{os.path.basename(db_path)}': {e}"
    finally:
        if conn: conn.close()

def register_omega_combination(combinacion: list, nombre: str, movil: str, db_path: str) -> Tuple[bool, str]:
    combo_str = "-".join(map(str, sorted(combinacion)))
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = f"INSERT INTO {TABLE_NAME_REGISTROS} (combinacion, nombre_completo, movil, fecha_registro) VALUES (?, ?, ?, datetime('now', 'localtime'))"
        cursor.execute(query, (combo_str, nombre, movil))
        conn.commit()
        return True, "¡Combinación registrada con éxito!"
    except sqlite3.IntegrityError:
        return False, "Esta combinación ya ha sido registrada."
    except Exception as e:
        logger.error(f"Error inesperado al registrar: {e}", exc_info=True)
        return False, f"Ocurrió un error inesperado al registrar: {e}"
    finally:
        if conn: conn.close()

def delete_registration(combinacion_str: str, db_path: str) -> Tuple[bool, str]:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        query = f"DELETE FROM {TABLE_NAME_REGISTROS} WHERE combinacion = ?"
        cursor.execute(query, (combinacion_str,))
        conn.commit()
        return (True, "Registro eliminado con éxito.") if cursor.rowcount > 0 else (False, "El registro no fue encontrado.")
    except Exception as e:
        logger.error(f"Error inesperado al eliminar: {e}", exc_info=True)
        return False, f"Ocurrió un error inesperado al eliminar."
    finally:
        if conn: conn.close()

def import_registrations_from_json(db_path: str, backup_file_path: str, overwrite: bool = False) -> Tuple[int, int, int, str]:
    try:
        with open(backup_file_path, 'r', encoding='utf-8') as f: data = json.load(f)
    except FileNotFoundError:
        return 0, 0, 0, f"No se encontró el archivo de respaldo '{os.path.basename(backup_file_path)}'."
    conn: Optional[sqlite3.Connection] = None
    added_count, updated_count = 0, 0
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for record in data:
            if not all(k in record for k in ['combinacion', 'nombre_completo', 'movil']): continue
            try:
                query = f"INSERT INTO {TABLE_NAME_REGISTROS} (combinacion, nombre_completo, movil, fecha_registro) VALUES (?, ?, ?, ?)"
                cursor.execute(query, (record['combinacion'], record['nombre_completo'], record['movil'], record.get('fecha_registro')))
                added_count += 1
            except sqlite3.IntegrityError:
                if overwrite:
                    update_query = f"UPDATE {TABLE_NAME_REGISTROS} SET nombre_completo = ?, movil = ? WHERE combinacion = ?"
                    cursor.execute(update_query, (record['nombre_completo'], record['movil'], record['combinacion']))
                    updated_count += 1
        conn.commit()
    except Exception as e:
        logger.error(f"Error durante la importación desde JSON: {e}", exc_info=True)
    finally:
        if conn: conn.close()
    message = f"Importación finalizada. {added_count} registros añadidos, {updated_count} actualizados."
    return added_count, updated_count, len(data), message

def _read_df_from_db(query: str, db_path: str, params: tuple = ()) -> pd.DataFrame:
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = sqlite3.connect(db_path)
        return pd.read_sql_query(query, conn, params=params)
    except (pd.errors.DatabaseError, sqlite3.Error) as e:
        logger.warning(f"No se pudo leer de '{os.path.basename(db_path)}'. Error: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def read_historico_from_db(db_path: str) -> pd.DataFrame:
    return _read_df_from_db(f"SELECT * FROM {TABLE_NAME_HISTORICO} ORDER BY concurso DESC", db_path)

def get_all_registrations(db_path: str) -> pd.DataFrame:
    return _read_df_from_db(f"SELECT * FROM {TABLE_NAME_REGISTROS}", db_path)

def get_random_omega_combination(db_path: str, game_config: Dict[str, Any]) -> Optional[List[int]]:
    n = game_config['n']
    cols_str = ", ".join([f'c{i}' for i in range(1, n + 1)])
    df = _read_df_from_db(f"SELECT {cols_str} FROM {TABLE_NAME_OMEGA} WHERE ha_salido = 0 ORDER BY RANDOM() LIMIT 1", db_path)
    if not df.empty:
        row_items = df.iloc[0].tolist()
        return [int(item) for item in row_items if pd.notna(item)]
    return None

def find_closest_omega(user_combo: list, match_count: int, db_path: str, game_config: Dict[str, Any]) -> Optional[List[int]]:
    n = game_config['n']
    cols = [f'c{i}' for i in range(1, n + 1)]
    user_combo_str = ", ".join(map(str, user_combo))
    case_statements = [f"CASE WHEN {col} IN ({user_combo_str}) THEN 1 ELSE 0 END" for col in cols]
    where_condition = f"({' + '.join(case_statements)}) = ?"
    query = f"SELECT {', '.join(cols)} FROM {TABLE_NAME_OMEGA} WHERE {where_condition} AND ha_salido = 0 ORDER BY RANDOM() LIMIT 1"
    df = _read_df_from_db(query, db_path, params=(match_count,))
    if not df.empty:
        row_items = df.iloc[0].tolist()
        return [int(item) for item in row_items if pd.notna(item)]
    return None

def count_omega_class(db_path: str) -> int:
    df = _read_df_from_db(f"SELECT COUNT(*) FROM {TABLE_NAME_OMEGA}", db_path)
    if df.empty:
        return 0
    
    # **CORRECCIÓN DEFINITIVA USANDO TRY-EXCEPT**
    try:
        count_value = df.iloc[0, 0]
        # Primero nos aseguramos que no sea un valor nulo de pandas
        if pd.isna(count_value):
            return 0
        # Ahora intentamos la conversión a entero, que es lo que podría fallar
        return int(count_value) # type: ignore 
    except (ValueError, TypeError):
        # Si la conversión falla, registramos el problema y devolvemos 0
        logger.warning(f"No se pudo convertir el resultado de COUNT(*) a entero en '{os.path.basename(db_path)}'. Se recibió: {df.iloc[0, 0]}. Se devuelve 0.")
        return 0

def get_omega_class_scores(db_path: str) -> pd.DataFrame:
    return _read_df_from_db("SELECT afinidad_pares, afinidad_tercias, afinidad_cuartetos FROM omega_class", db_path)

def read_trajectory_data(db_path: str, table_name: str) -> pd.DataFrame:
    df = _read_df_from_db(f"SELECT * FROM {table_name} ORDER BY ultimo_concurso_usado ASC", db_path)
    if not df.empty:
        for col in df.columns:
            if col != 'fecha_calculo':
                df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

def export_registrations_to_json(db_path: str, backup_file_path: str) -> Tuple[bool, str]:
    try:
        df = get_all_registrations(db_path)
        if df.empty: return False, "No hay registros para exportar."
        if 'fecha_registro' in df.columns: df['fecha_registro'] = df['fecha_registro'].astype(str)
        df.to_json(backup_file_path, orient='records', indent=4)
        logger.info(f"Se han exportado {len(df)} registros a '{os.path.basename(backup_file_path)}'")
        return True, f"Se han exportado {len(df)} registros con éxito."
    except Exception as e:
        logger.error(f"Error al exportar registros: {e}", exc_info=True)
        return False, "Ocurrió un error durante la exportación."
    

def read_omega_score_trajectory(db_path: str) -> pd.DataFrame:
    """Lee la tabla con la trayectoria de los Omega Scores."""
    return _read_df_from_db("SELECT * FROM omega_score_trajectory ORDER BY concurso ASC", db_path)