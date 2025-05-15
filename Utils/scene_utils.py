# Utils/scene_utils.py

"""
Utility functions for scene management that work with the event-driven system.
"""
from Managers.scene_manager import (
    restart_scene, clear_scene, 
    SCENE_CLEARED, SCENE_CREATION_COMPLETED
)
from Core.event_manager import EventManager
from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

# Get singleton instances
SC = SimConnection.get_instance()
EM = EventManager.get_instance()
logger = get_logger()

def restart_disaster_area(config=None):
    """
    Restart the disaster area with the given configuration.
    
    Args:
        config: Scene configuration dict. If None, uses default configuration.
        
    Returns:
        True - the request was submitted via the event system
    """
    # Just delegate to the scene_manager's restart_scene function
    restart_scene(config)
    return True

def setup_scene_event_handlers():
    """
    Set up additional event handlers for scene-related events.
    
    The core scene events are already handled by SceneManager,
    but you can register additional handlers here.
    """
    # Initialize the SceneManager singleton to ensure event handlers are registered
    
    def on_scene_cleared(_):
        """Handle scene cleared event"""
        logger.info("SceneUtils", "Scene cleared")
    
    def on_scene_completed(objects):
        """Handle scene creation completed event"""
        logger.info("SceneUtils", f"Scene creation completed with {len(objects)} objects")
    
    # Subscribe to events
    EM.subscribe(SCENE_CLEARED, on_scene_cleared)
    EM.subscribe(SCENE_CREATION_COMPLETED, on_scene_completed)
    
    logger.info("SceneUtils", "Scene event handlers registered")
