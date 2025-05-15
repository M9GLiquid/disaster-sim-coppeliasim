#!/usr/bin/env python3
"""
Batch flipper: apply flip to all .npz files under a directory.

Usage:
    python flip.py --dir <dataset_dir> --flip <none|fliplr|flipud> --out <output_dir>
Requires: numpy
"""
import argparse
import os
import sys
import numpy as np
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

# Initialize logger
logger = get_logger()

def parse_args():
    parser = argparse.ArgumentParser(description='Dataset Flipper')
    parser.add_argument('--dir', required=True, help='Directory containing .npz files')
    parser.add_argument('--flip', required=True, choices=['none','fliplr','flipud'], help='Flip mode')
    parser.add_argument('--out', required=True, help='Output directory for flipped files')
    return parser.parse_args()


def batch_flip(npz_dir, out_dir, flip_type):
    logger.info("Flipper", f"Starting batch flip operation: {flip_type}")
    if flip_type == 'none':
        logger.info("Flipper", "No flip requested; exiting.")
        print('No flip requested; exiting.')
        sys.exit(0)
    
    files = []
    for root, _, names in os.walk(npz_dir):
        for name in names:
            if name.lower().endswith('.npz'):
                files.append(os.path.join(root, name))
    
    total = len(files)
    logger.info("Flipper", f"Found {total} .npz files. Applying {flip_type}...")
    print(f"Found {total} .npz files. Applying {flip_type}...")
    
    axis = 2 if flip_type == 'fliplr' else 1
    logger.debug_at_level(DEBUG_L1, "Flipper", f"Flipping along axis: {axis}")
    
    for idx, fpath in enumerate(files, 1):
        rel = os.path.relpath(fpath, npz_dir)
        out_path = os.path.join(out_dir, rel)
        
        logger.debug_at_level(DEBUG_L2, "Flipper", f"Processing file {idx}/{total}: {rel}")
        logger.debug_at_level(DEBUG_L2, "Flipper", f"Output path: {out_path}")
        
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        try:
            data = np.load(fpath, allow_pickle=True)
            logger.debug_at_level(DEBUG_L3, "Flipper", f"Loaded file with keys: {list(data.keys())}")
            
            flipped = {}
            for k, v in data.items():
                if isinstance(v, np.ndarray) and v.ndim >= 2:
                    logger.debug_at_level(DEBUG_L3, "Flipper", f"Flipping array: {k} with shape {v.shape}")
                    
                    # Check dimensions and use appropriate axis
                    ndim = v.ndim
                    if flip_type == 'fliplr':
                        # For left-right flip, use last dimension (width)
                        flip_axis = min(2, ndim - 1)  # Use axis 2 for 3D+ arrays, axis 1 for 2D arrays
                    else:  # flipud
                        # For up-down flip, use second-to-last dimension (height)
                        flip_axis = min(1, ndim - 2)  # Use axis 1 for 3D+ arrays, axis 0 for 2D arrays
                        if ndim < 2:
                            flip_axis = 0  # Fallback for 1D arrays
                            
                    logger.debug_at_level(DEBUG_L3, "Flipper", f"Using flip_axis={flip_axis} for {ndim}D array")
                    flipped[k] = np.flip(v, axis=flip_axis)
                else:
                    flipped[k] = v
            
            np.savez_compressed(out_path, **flipped)
            logger.debug_at_level(DEBUG_L1, "Flipper", f"[{idx}/{total}] Processed: {rel}")
            print(f"[{idx}/{total}] {rel}")
            
        except Exception as e:
            logger.error("Flipper", f"Error processing file {fpath}: {e}")
            print(f"Error processing {rel}: {e}", file=sys.stderr)
    
    logger.info("Flipper", "Batch flipping complete.")
    print('Batch flipping complete.')


def main():
    logger.info("Flipper", "Starting Flipper tool")
    args = parse_args()
    logger.debug_at_level(DEBUG_L1, "Flipper", f"Arguments: dir={args.dir}, flip={args.flip}, out={args.out}")
    batch_flip(args.dir, args.out, args.flip)
    logger.info("Flipper", "Flipper tool completed")


if __name__ == '__main__':
    main() 