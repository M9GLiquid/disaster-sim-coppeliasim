# sim_connection.py

from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import time

__all__ = ['connect_to_simulation', 'shutdown_simulation']

def connect_to_simulation(timeout_sec=2.5):
    """
    Connect to CoppeliaSim's remote API server and return (client, sim).

    If the simulation is stopped, start it and wait until running.
    """
    print("[SimConnection] Connecting to CoppeliaSim...")
    client = RemoteAPIClient()
    sim = client.require('sim')

    sim_state = sim.getSimulationState()
    if sim_state == sim.simulation_advancing_running:
        print("[SimConnection] Simulation already running.")
    elif sim_state == sim.simulation_stopped:
        print("[SimConnection] Simulation stopped. Starting...")
        sim.startSimulation()
        _wait_until_running(sim, timeout_sec)
    else:
        print(f"[SimConnection] Unexpected simulation state: {sim_state}")

    return sim

def _wait_until_running(sim, timeout_sec=2.5):
    """
    Wait until simulation state is 'running' or until timeout.
    """
    start_time = time.time()
    while True:
        state = sim.getSimulationState()
        if state == sim.simulation_advancing_running:
            print("[SimConnection] Simulation is running.")
            return
        if time.time() - start_time > timeout_sec:
            print("[SimConnection] Timeout while waiting for simulation to start.")
            return
        time.sleep(0.05)

def shutdown_simulation(keyboard_manager, camera_view, sim):
    """
    Cleanly shutdown keyboard control, camera viewer, and disconnect from simulation.
    """
    print("[SimConnection] Shutting down KeyboardManager...")
    try:
        keyboard_manager.stop()
    except Exception as e:
        print(f"[SimConnection] Error stopping KeyboardManager: {e}")

    print("[SimConnection] Closing CameraView...")
    try:
        camera_view.close()
    except Exception as e:
        print(f"[SimConnection] Error closing CameraView: {e}")

    print("[SimConnection] Disconnecting Remote API client...")
    try:
        sim.stopSimulation()
        print("[SimConnection] Client disconnected.")
    except Exception as e:
        print(f"[SimConnection] Error during client disconnect: {e}")

    print("[SimConnection] Shutdown complete.")
