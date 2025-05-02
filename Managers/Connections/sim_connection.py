# sim_connection.py

from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import time

__all__ = ['connect_to_simulation', 'shutdown_simulation']

def connect_to_simulation(timeout_sec=2.5):
    """
    Connect to CoppeliaSim's remote API server and return (client, sim).

    If the simulation is stopped, start it and wait until running.
    """
    print("[Connection] Connecting to CoppeliaSim...")
    client = RemoteAPIClient()
    sim = client.require('sim')

    sim_state = sim.getSimulationState()
    if sim_state == sim.simulation_advancing_running:
        print("[Connection] Simulation already running.")
    elif sim_state == sim.simulation_stopped:
        print("[Connection] Simulation stopped. Starting...")
        sim.startSimulation()
        _wait_until_running(sim, timeout_sec)
    else:
        print(f"[Connection] Unexpected simulation state: {sim_state}")

    return sim

def _wait_until_running(sim, timeout_sec=2.5):
    """
    Wait until simulation state is 'running' or until timeout.
    """
    start_time = time.time()
    while True:
        state = sim.getSimulationState()
        if state == sim.simulation_advancing_running:
            print("[Connection] Simulation is running.")
            return
        if time.time() - start_time > timeout_sec:
            print("[Connection] Timeout while waiting for simulation to start.")
            return
        time.sleep(0.05)

def shutdown_simulation(keyboard_manager, depth_collector, floating_view_rgb, sim):
    """
    Cleanly shutdown keyboard control, camera viewer, disconnect from simulation.
    """
    print("[Connection] Shutting down KeyboardManager...")
    try:
        keyboard_manager.stop()
    except Exception as e:
        print(f"[Connection] Error stopping KeyboardManager: {e}")

    # Remove camera floating view
    print("[Connection] Removing Camera View...")
    try:
        sim.floatingViewRemove(floating_view_rgb)
    except Exception as e:
        print(f"[Connection] Error removing Camera View: {e}")

    # Shutdown depth dataset collector
    print("[Connection] Shutting down DepthDatasetCollector...")
    try:
        depth_collector.shutdown()
    except Exception as e:
        print(f"[Connection] Error shutting down DepthDatasetCollector: {e}")

    print("[Connection] Disconnecting Remote API client...")
    try:
        sim.stopSimulation()
        print("[Connection] Simulation stopped.")
    except Exception as e:
        print(f"[Connection] Error during simulation stop: {e}")
