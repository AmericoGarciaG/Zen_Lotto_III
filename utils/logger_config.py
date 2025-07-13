import logging
import sys

def setup_logger():
    """Configura el logger global para el proyecto."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s",
        stream=sys.stdout,
        force=True, # Asegura que la configuración se aplique incluso si ya fue llamada
    )