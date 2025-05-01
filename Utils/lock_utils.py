from contextlib import contextmanager

@contextmanager
def sim_lock(sim):
    locked = False
    try:
        sim.acquireLock()
        locked = True
    except Exception as e:
        print(f"[LockUtils] Could not acquire simulation lock: {e}")
    try:
        yield locked
    finally:
        if locked:
            try:
                sim.releaseLock()
            except Exception as e:
                print(f"[LockUtils] Could not release simulation lock: {e}")