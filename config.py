import os

# --- RUTAS DE ARCHIVOS CENTRALIZADAS ---
# Definimos la ruta a la carpeta de datos
DATA_DIR = "data"

# Aseguramos que el directorio exista
os.makedirs(DATA_DIR, exist_ok=True)

# URL oficial de Pronósticos para el histórico de Melate Retro
HISTORICAL_DATA_URL = "https://www.loterianacional.gob.mx/Home/Historicos?ARHP=TQBlAGwAYQB0AGUALQBSAGUAdAByAG8A"

# Columnas esperadas en el archivo CSV para validación.
EXPECTED_COLUMNS = ['CONCURSO', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'BOLSA', 'FECHA']

# Archivo de la base de datos
DB_FILE = os.path.join(DATA_DIR, "zen_lotto.db")
# Archivo de frecuencias
FREQUENCIES_FILE = os.path.join(DATA_DIR, "frecuencias.json")
# Archivo de estado central
STATE_FILE = os.path.join(DATA_DIR, "system_state.json")
# Archivo de respaldo de registros
REGISTROS_BACKUP_FILE = os.path.join(DATA_DIR, "registros_omega_backup.json")

# Umbrales para la clasificación Omega
UMBRAL_PARES = 421
UMBRAL_TERCIAS = 65
UMBRAL_CUARTETOS = 16

# Habilita/deshabilita las vistas y cálculos avanzados de monitoreo
DEBUG_MODE = True

# --- CONSTANTES DE ESQUEMA DE BASE DE DATOS ---
# Para asegurar consistencia entre escritura y lectura

# Esquema para la tabla umbrales_trayectoria
UMBRALES_TRAYECTORIA_SCHEMA = {
    "ultimo_concurso_usado": "INTEGER PRIMARY KEY",
    "umbral_pares": "INTEGER NOT NULL",
    "umbral_tercias": "INTEGER NOT NULL",
    "umbral_cuartetos": "INTEGER NOT NULL",
    "cobertura_historica": "REAL NOT NULL",
    "cobertura_universal_estimada": "REAL NOT NULL",
    "fecha_calculo": "DATETIME"
}

# Esquema para la tabla frecuencias_trayectoria
FRECUENCIAS_TRAYECTORIA_SCHEMA = {
    "ultimo_concurso_usado": "INTEGER PRIMARY KEY",
    "total_pares_unicos": "INTEGER NOT NULL",
    "suma_freq_pares": "INTEGER NOT NULL",
    "total_tercias_unicos": "INTEGER NOT NULL",
    "suma_freq_tercias": "INTEGER NOT NULL",
    "total_cuartetos_unicos": "INTEGER NOT NULL",
    "suma_freq_cuartetos": "INTEGER NOT NULL",
    "fecha_calculo": "DATETIME"
}

# Esquema para la tabla afinidades_trayectoria
AFINIDADES_TRAYECTORIA_SCHEMA = {
    "ultimo_concurso_usado": "INTEGER PRIMARY KEY",
    "afin_pares_media": "REAL NOT NULL",
    "afin_pares_mediana": "REAL NOT NULL",
    "afin_pares_min": "INTEGER NOT NULL",
    "afin_pares_max": "INTEGER NOT NULL",
    "afin_tercias_media": "REAL NOT NULL",
    "afin_tercias_mediana": "REAL NOT NULL",
    "afin_tercias_min": "INTEGER NOT NULL",
    "afin_tercias_max": "INTEGER NOT NULL",
    "afin_cuartetos_media": "REAL NOT NULL",
    "afin_cuartetos_mediana": "REAL NOT NULL",
    "afin_cuartetos_min": "INTEGER NOT NULL",
    "afin_cuartetos_max": "INTEGER NOT NULL",
    "fecha_calculo": "DATETIME"
}

# Esquema para la tabla freq_dist_trayectoria
FREQ_DIST_TRAYECTORIA_SCHEMA = {
    "ultimo_concurso_usado": "INTEGER PRIMARY KEY",
    "freq_pares_media": "REAL NOT NULL",
    "freq_pares_min": "INTEGER NOT NULL",
    "freq_pares_max": "INTEGER NOT NULL",
    "freq_tercias_media": "REAL NOT NULL",
    "freq_tercias_min": "INTEGER NOT NULL",
    "freq_tercias_max": "INTEGER NOT NULL",
    "freq_cuartetos_media": "REAL NOT NULL",
    "freq_cuartetos_min": "INTEGER NOT NULL",
    "freq_cuartetos_max": "INTEGER NOT NULL",
    "fecha_calculo": "DATETIME"
}