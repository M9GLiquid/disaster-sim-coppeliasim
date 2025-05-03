# Utils/scene_utils.py

"""
Utility functions for scene management operations like clearing and restarting scenes.
These functions operate on a higher level than individual object creators.
"""

from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import time
from Managers.scene_core import create_scene
from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager

EM = EventManager.get_instance()
SC = SimConnection.get_instance()

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
    Starts the simulation if it is stopped.
    Returns the sim handle.
    """
    # Get sim from singleton
    sim_state = SC.sim.getSimulationState()

    if sim_state == SIMULATION_ADVANCING_RUNNING:
        print("[Scene] Simulation already running.")
        return 

    if sim_state == SIMULATION_STOPPED:
        print("[Scene] Starting simulation...")
        SC.sim.startSimulation()
        start_time = time.time()
        while True:
            try:
                if SC.sim.getSimulationState() == SIMULATION_ADVANCING_RUNNING:
                    print("[Scene] Simulation started (confirmed running).")
                    return 
            except Exception:
                pass
            if time.time() - start_time > timeout_sec:
                current = SC.sim.getSimulationState()
                if current == SIMULATION_STOPPED:
                    print("[Scene] Warning: Start timeout. Still stopped, assuming running.")
                else:
                    print(f"[Scene] Warning: Start timeout. State={current}. Proceeding anyway.")
                return 
            time.sleep(0.05)
    else:
        print(f"[Scene] Unexpected state {sim_state}. Continuing.")

def clear_disaster_area():
    """
    Clear all objects in the disaster scene area.
    """
    # Get sim from singleton
    
    try:
        # Find the disaster group
        group = SC.sim.getObject('/DisasterGroup')
        
        # Remove the whole group directly
        # Using a direct removeObject call with parameters that ensure proper cleanup
        SC.sim.removeObject(group) 
        print("[SceneUtils] Disaster area cleared")
        
        # Publish event that scene has been cleared
        EM.publish('scene/cleared', None)
            
        return True
    except Exception as e:
        print(f"[SceneUtils] Error clearing disaster area: {e}")
        return False

def restart_disaster_area(config=None):
    """
    Clear and recreate the disaster scene area.
    
    Args:
        config: Configuration dictionary
    """
    # First clear current scene
    clear_disaster_area()
    
    # Then create a new scene
    if config is None:
        from Utils.config_utils import get_default_config
        config = get_default_config()
        
    # Use synchronous scene creation
    create_scene(config)
    
    print("[SceneUtils] Disaster area restarted")
    
    return True

# Setup listeners to handle scene events
def setup_scene_event_handlers():
    """
    Set up event handlers for scene-related events.
    """
    # Get EventManager singleton instance
    
    def handle_scene_clear(_):
        clear_disaster_area()
    
    def handle_scene_restart(config):
        restart_disaster_area(config)
    
    # Register event handlers
    EM.subscribe('scene/clear', handle_scene_clear)
    EM.subscribe('scene/restart', handle_scene_restart)
    
    print("[SceneUtils] Scene event handlers registered")
