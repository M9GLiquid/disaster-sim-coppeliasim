# Utils/scene_utils.py

from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import time

# Simulation state constants
SIMULATION_STOPPED                 = 0
SIMULATION_PAUSED                  = 1
SIMULATION_ADVANCING_FIRSTAFTERSTOP = 2
SIMULATION_ADVANCING_RUNNING        = 3
SIMULATION_ADVANCING_LASTBEFOREPAUSE = 4
SIMULATION_ADVANCING_FIRSTAFTERPAUSE = 5
SIMULATION_ADVANCING_ABOUTTOSTOP     = 6
SIMULATION_ADVANCING_LASTBEFORESTOP  = 7

def start_sim_if_needed(timeout_sec=2.5):
    """
    Connects to CoppeliaSim and starts the simulation if it is stopped.
    Returns the sim handle.
    """
    client = RemoteAPIClient()
    sim    = client.require('sim')
    sim_state = sim.getSimulationState()

    if sim_state == SIMULATION_ADVANCING_RUNNING:
        print("[SceneUtils] Simulation already running.")
        return sim

    if sim_state == SIMULATION_STOPPED:
        print("[SceneUtils] Starting simulation...")
        sim.startSimulation()
        start_time = time.time()
        while True:
            try:
                if sim.getSimulationState() == SIMULATION_ADVANCING_RUNNING:
                    print("[SceneUtils] Simulation started (confirmed running).")
                    return sim
            except Exception:
                pass
            if time.time() - start_time > timeout_sec:
                current = sim.getSimulationState()
                if current == SIMULATION_STOPPED:
                    print("[SceneUtils] Warning: Start timeout. Still stopped, assuming running.")
                else:
                    print(f"[SceneUtils] Warning: Start timeout. State={current}. Proceeding anyway.")
                return sim
            time.sleep(0.05)
    else:
        print(f"[SceneUtils] Unexpected state {sim_state}. Continuing.")
        return sim

def clear_disaster_area(sim):
    """
    Deletes all objects under DisasterGroup, then deletes the group dummy itself.
    """
    try:
        disaster_group_handle = sim.getObject('/DisasterGroup')
        if disaster_group_handle != -1:
            # Get all children (recursive), but not the group dummy itself
            child_handles = sim.getObjectsInTree(disaster_group_handle, sim.handle_all, 0)
            child_handles = [h for h in child_handles if h != disaster_group_handle]

            # Remove all children first
            sim.removeObjects(child_handles)

            # Then remove the group dummy
            try:
                sim.removeObject(disaster_group_handle)
            except Exception:
                pass

            print("[SceneUtils] DisasterGroup and all contents cleared.")
        else:
            print("[SceneUtils] No DisasterGroup found.")
    except Exception as e:
        print(f"[SceneUtils] Error clearing DisasterGroup: {e}")

def restart_disaster_area(sim, config):
    """
    Clears the DisasterGroup, then rebuilds the scene (including drone teleport).
    """
    from Managers.scene_manager import create_scene

    print("[SceneUtils] Restarting disaster area (no sim stop).")

    clear_disaster_area(sim)
    create_scene(sim, config)
    print("[SceneUtils] New disaster created.")
    # create_scene already does the teleport for the drone & target
