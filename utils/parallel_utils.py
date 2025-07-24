# utils/parallel_utils.py
import multiprocessing
import multiprocessing.pool
from typing import Any, Callable, Iterable, Optional

# --- CORRECCIÓN 1: Solución para "Incompatible Variable Override" ---
# En lugar de sobrescribir la propiedad 'daemon', que confunde a Pylance,
# sobrescribimos el método 'start()'. Dentro de 'start()', forzamos
# que el proceso NO sea daemonic JUSTO ANTES de que se inicie.
# Esta es una técnica limpia que logra el mismo resultado.

class NoDaemonProcess(multiprocessing.Process):
    """
    Una clase de proceso que se asegura de que la propiedad 'daemon' siempre sea False
    al momento de iniciar, permitiendo que cree procesos hijos.
    """
    def start(self):
        self.daemon = False
        super().start()

# --- El resto de la lógica se mantiene igual, pero ahora se basa en un NoDaemonProcess robusto ---

class NoDaemonContext(type(multiprocessing.get_context())):
    """
    Un contexto de multiprocessing personalizado que utiliza nuestro NoDaemonProcess.
    """
    Process = NoDaemonProcess

class NoDaemonPool(multiprocessing.pool.Pool):
    """
    Un Pool de procesos que utiliza un contexto NoDaemon, permitiendo así
    la creación de pools anidados.
    """
    def __init__(self, 
                 processes: Optional[int] = None, 
                 initializer: Optional[Callable[..., Any]] = None, 
                 initargs: Iterable[Any] = (), 
                 maxtasksperchild: Optional[int] = None):
        
        # Creamos nuestro contexto personalizado que usa NoDaemonProcess
        custom_context = NoDaemonContext() # type: ignore
        
        # --- CORRECCIÓN 2: Solución para "Argument missing for parameter 'context'" ---
        # Llamamos al __init__ de la clase padre explícitamente, pasando
        # nuestro contexto personalizado. Esto es claro, explícito y satisface a Pylance.
        super(NoDaemonPool, self).__init__(
            processes=processes, 
            initializer=initializer, 
            initargs=initargs, 
            maxtasksperchild=maxtasksperchild, 
            context=custom_context
        )