# URL oficial de Pronósticos para el histórico de Melate Retro
HISTORICAL_DATA_URL = "https://www.loterianacional.gob.mx/Home/Historicos?ARHP=TQBlAGwAYQB0AGUALQBSAGUAdAByAG8A"

# Columnas esperadas en el archivo CSV para validación.
# Ahora incluimos Bolsa y Fecha.
EXPECTED_COLUMNS = ['CONCURSO', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'BOLSA', 'FECHA']

# Archivo de la base de datos
DB_FILE = "zen_lotto.db"
# Archivo de frecuencias
FREQUENCIES_FILE = "frecuencias.json"