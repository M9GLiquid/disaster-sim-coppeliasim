from contextlib import contextmanager
from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

SC = SimConnection.get_instance()
logger = get_logger()

@contextmanager
def sim_lock():
    locked = False
    try:
        SC.sim.acquireLock()
        locked = True
    except Exception as e:
        logger.warning("Lock", f"Could not acquire simulation lock: {e}")
    try:
        yield locked
    finally:
        if locked:
            try:
                SC.sim.releaseLock()
            except Exception as e:
                logger.error("Lock", f"Could not release simulation lock: {e}")