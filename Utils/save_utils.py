# Utils/save_utils.py

import numpy as np
import os

def save_batch_npz(folder, counter, batch_data):
    """
    Save a batch dictionary into a compressed .npz file.
    """
    filename = os.path.join(folder, f"batch_{counter:06d}.npz")
    np.savez_compressed(filename,
                        depths=batch_data['depths'],
                        poses=batch_data['poses'],
                        frames=batch_data['frames'],
                        distances=batch_data['distances'],
                        actions=batch_data['actions'])
    print(f"[SaveUtils] Saved batch to {filename}")
