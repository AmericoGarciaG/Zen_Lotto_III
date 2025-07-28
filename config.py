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
UMBRAL_PARES = 20
UMBRAL_TERCIAS = 20
UMBRAL_CUARTETOS = 15

# Habilita/deshabilita las vistas y cálculos avanzados de monitoreo
DEBUG_MODE = True