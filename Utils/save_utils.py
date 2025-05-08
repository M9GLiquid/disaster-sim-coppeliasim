import numpy as np
import os

from Utils.config_utils import get_default_config

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
            print(f"[SaveUtils] ERROR: Missing data keys: {missing_keys}")
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
        
        # Print summary statistics for debugging
        if verbose:
            print(f"[SaveUtils] Saved batch to {filename}")
            print(f"[SaveUtils] - Depths shape: {batch_data['depths'].shape}")
            print(f"[SaveUtils] - Poses shape: {batch_data['poses'].shape}")
            print(f"[SaveUtils] - Frames count: {len(batch_data['frames'])}")
            print(f"[SaveUtils] - Actions count: {len(batch_data['actions'])}")
            print(f"[SaveUtils] - Victim dirs shape: {batch_data['victim_dirs'].shape}")
        
        return True
        
    except Exception as e:
        print(f"[SaveUtils] Error saving batch to {filename}: {e}")
        # More detailed error diagnostics
        for key, value in batch_data.items():
            try:
                shape_or_len = value.shape if hasattr(value, 'shape') else len(value)
                if verbose:
                    print(f"[SaveUtils] - {key}: type={type(value)}, shape/len={shape_or_len}")
            except:
                print(f"[SaveUtils] - {key}: Error getting shape/length")
        return False
