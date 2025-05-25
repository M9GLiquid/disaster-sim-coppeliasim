
import os
import numpy as np
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3
from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager
from Utils.capture_utils import capture_distance_to_victim

# Get singleton instances
SC = SimConnection.get_instance()
EM = EventManager.get_instance()
logger = get_logger()

# Episode-related events
EPISODE_START = 'episode/start'
EPISODE_END = 'episode/end'
EPISODE_SAVE_COMPLETED = 'episode/save/completed'
EPISODE_SAVE_ERROR = 'episode/save/error'

def check_episode_end_condition(threshold=0.5):
    """
    Check if the drone is within the threshold distance of the victim.
    
    Args:
        threshold: Maximum distance in meters to consider the episode ended
        
    Returns:
        bool: True if episode should end, False otherwise
    """
    try:
        distance = capture_distance_to_victim()
        if distance <= threshold and distance > 0:
            logger.info("EpisodeUtils", f"Drone within threshold ({threshold}m) of victim: {distance:.2f}m")
            return True
        return False
    except Exception as e:
        logger.error("EpisodeUtils", f"Error checking episode end condition: {e}")
        return False

def save_episode_data(episode_data, episode_number):
    """
    Save episode data to a .npz file.
    
    Args:
        episode_data: Dictionary containing episode data
        episode_number: Current episode number
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    # Create data directory if it doesn't exist
    data_dir = os.path.join("data", "episodes")
    os.makedirs(data_dir, exist_ok=True)
    
    # Create filename with padded episode number
    filename = os.path.join(data_dir, f"episode_{episode_number:05d}.npz")
    
    try:
        # Verify all required data is present
        required_keys = ['depths', 'poses', 'frames', 'distances', 'actions', 'victim_dirs']
        missing_keys = [key for key in required_keys if key not in episode_data]
        
        if missing_keys:
            logger.error("EpisodeUtils", f"Missing data keys: {missing_keys}")
            return False
            
        # Save the data
        np.savez_compressed(
            filename,
            depths      = episode_data['depths'],
            poses       = episode_data['poses'],
            frames      = episode_data['frames'],
            distances   = episode_data['distances'],
            actions     = episode_data['actions'],
            victim_dirs = episode_data['victim_dirs'],
        )
        
        # Log summary statistics
        logger.info("EpisodeUtils", f"Saved episode to {filename}")
        logger.debug_at_level(DEBUG_L1, "EpisodeUtils", f"Episode statistics:")
        logger.debug_at_level(DEBUG_L1, "EpisodeUtils", f"  Frames: {len(episode_data['frames'])}")
        logger.debug_at_level(DEBUG_L1, "EpisodeUtils", f"  Depths shape: {episode_data['depths'].shape}")
        logger.debug_at_level(DEBUG_L1, "EpisodeUtils", f"  Final distance to victim: {episode_data['distances'][-1]:.2f}m")
        
        return True
        
    except Exception as e:
        logger.error("EpisodeUtils", f"Error saving episode to {filename}: {e}")
        # More detailed error diagnostics
        for key, value in episode_data.items():
            try:
                shape_or_len = value.shape if hasattr(value, 'shape') else len(value)
                logger.debug_at_level(DEBUG_L1, "EpisodeUtils", f"{key}: type={type(value)}, shape/len={shape_or_len}")
            except Exception as detail_error:
                logger.error("EpisodeUtils", f"Error getting shape/length for {key}: {detail_error}")
        return False
