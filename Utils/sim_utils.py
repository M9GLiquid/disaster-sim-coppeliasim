import time

def safe_step(sim):
    try:
        sim.step()
    except Exception as e:
        print(f"[Main] safe_step: sim.step() exception: {e}")