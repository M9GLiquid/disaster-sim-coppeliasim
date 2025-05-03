from contextlib import contextmanager
from Managers.Connections.sim_connection import SimConnection

SC = SimConnection.get_instance()

@contextmanager
def sim_lock():
    locked = False
    try:
        SC.sim.acquireLock()
        locked = True
    except Exception as e:
        print(f"[Lock] Could not acquire simulation lock: {e}")
    try:
        yield locked
    finally:
        if locked:
            try:
                SC.sim.releaseLock()
            except Exception as e:
                print(f"[Lock] Could not release simulation lock: {e}")