import numpy as np
import os

from Utils.config_utils import get_default_config
from Utils.log_utils import get_logger

logger = get_logger()

def save_batch_npz(folder, counter, batch_data):
    """
    Save a batch dictionary into a compressed .npz file,
    with detailed logging and error handling.
    """
    filename = os.path.join(folder, f"batch_{counter:06d}.npz")
    verbose = get_default_config().get('verbose', False)
    try:
        # Verify all required data is present
        required_keys = ['depths', 'poses', 'frames', 'distances', 'actions', 'victim_dirs']
        missing_keys = [key for key in required_keys if key not in batch_data]
        
        if missing_keys:
            logger.error("SaveUtils", f"Missing data keys: {missing_keys}")
            return False
            
        # Save the data
        np.savez_compressed(
            filename,
            depths      = batch_data['depths'],
            poses       = batch_data['poses'],
            frames      = batch_data['frames'],
            distances   = batch_data['distances'],
            actions     = batch_data['actions'],
            victim_dirs = batch_data['victim_dirs'],
        )
        
        # Log summary statistics
        logger.info("SaveUtils", f"Saved batch to {filename}")
        
        # Print detailed statistics in verbose mode
        if verbose:
            logger.debug_at_level(1, "SaveUtils", f"Depths shape: {batch_data['depths'].shape}")
            logger.debug_at_level(1, "SaveUtils", f"Poses shape: {batch_data['poses'].shape}")
            logger.debug_at_level(1, "SaveUtils", f"Frames count: {len(batch_data['frames'])}")
            logger.debug_at_level(1, "SaveUtils", f"Actions count: {len(batch_data['actions'])}")
            logger.debug_at_level(1, "SaveUtils", f"Victim dirs shape: {batch_data['victim_dirs'].shape}")
        
        return True
        
    except Exception as e:
        logger.error("SaveUtils", f"Error saving batch to {filename}: {e}")
        # More detailed error diagnostics
        for key, value in batch_data.items():
            try:
                shape_or_len = value.shape if hasattr(value, 'shape') else len(value)
                if verbose:
                    logger.debug_at_level(1, "SaveUtils", f"{key}: type={type(value)}, shape/len={shape_or_len}")
            except Exception as detail_error:
                logger.error("SaveUtils", f"Error getting shape/length for {key}: {detail_error}")
        return False
