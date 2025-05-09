from contextlib import contextmanager
from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger

SC = SimConnection.get_instance()
logger = get_logger()

@contextmanager
def sim_lock():
    locked = False
    try:
        SC.sim.acquireLock()
        locked = True
        logger.debug_at_level(2, "Lock", "Simulation lock acquired")
    except Exception as e:
        logger.error("Lock", f"Could not acquire simulation lock: {e}")
    try:
        yield locked
    finally:
        if locked:
            try:
                SC.sim.releaseLock()
                logger.debug_at_level(2, "Lock", "Simulation lock released")
            except Exception as e:
                logger.error("Lock", f"Could not release simulation lock: {e}")