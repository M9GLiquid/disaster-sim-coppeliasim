import numpy as np
import os
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

logger = get_logger()

def save_batch_npz(filepath, batch_data):
    """
    Save a batch dictionary into a compressed .npz file,
    with detailed logging and error handling.
    
    Args:
        filepath: Full path to the target NPZ file
        batch_data: Dictionary with data to save
    
    Returns:
        bool: Success status
    """
    try:
        # Verify all required data is present
        required_keys = ['depths', 'poses', 'frames', 'distances', 'actions', 'victim_dirs']
        missing_keys = [key for key in required_keys if key not in batch_data]
        
        if missing_keys:
            logger.error("SaveUtils", f"Missing data keys: {missing_keys}")
            return False
            
        # Save the data
        np.savez_compressed(
            filepath,
            depths      = batch_data['depths'],
            poses       = batch_data['poses'],
            frames      = batch_data['frames'],
            distances   = batch_data['distances'],
            actions     = batch_data['actions'],
            victim_dirs = batch_data['victim_dirs'],
            split       = batch_data.get('split', 'train'),  # Include split information
        )
        
        # Log summary statistics
        logger.debug_at_level(DEBUG_L1, "SaveUtils", f"Saved batch to {filepath}")
        logger.debug_at_level(DEBUG_L2, "SaveUtils", f"- Depths shape: {batch_data['depths'].shape}")
        logger.debug_at_level(DEBUG_L2, "SaveUtils", f"- Poses shape: {batch_data['poses'].shape}")
        logger.debug_at_level(DEBUG_L2, "SaveUtils", f"- Frames count: {len(batch_data['frames'])}")
        logger.debug_at_level(DEBUG_L2, "SaveUtils", f"- Actions count: {len(batch_data['actions'])}")
        logger.debug_at_level(DEBUG_L2, "SaveUtils", f"- Victim dirs shape: {batch_data['victim_dirs'].shape}")
        
        return True
        
    except Exception as e:
        logger.error("SaveUtils", f"Error saving batch to {filepath}: {e}")
        # More detailed error diagnostics
        for key, value in batch_data.items():
            try:
                shape_or_len = value.shape if hasattr(value, 'shape') else len(value)
                logger.debug_at_level(DEBUG_L1, "SaveUtils", f"- {key}: type={type(value)}, shape/len={shape_or_len}")
            except:
                logger.debug_at_level(DEBUG_L1, "SaveUtils", f"- {key}: Error getting shape/length")
        return False
