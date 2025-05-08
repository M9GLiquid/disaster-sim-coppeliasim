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


def parse_args():
    parser = argparse.ArgumentParser(description='Dataset Flipper')
    parser.add_argument('--dir', required=True, help='Directory containing .npz files')
    parser.add_argument('--flip', required=True, choices=['none','fliplr','flipud'], help='Flip mode')
    parser.add_argument('--out', required=True, help='Output directory for flipped files')
    return parser.parse_args()


def batch_flip(npz_dir, out_dir, flip_type):
    if flip_type == 'none':
        print('No flip requested; exiting.')
        sys.exit(0)
    files = []
    for root, _, names in os.walk(npz_dir):
        for name in names:
            if name.lower().endswith('.npz'):
                files.append(os.path.join(root, name))
    total = len(files)
    print(f"Found {total} .npz files. Applying {flip_type}...")
    axis = 1 if flip_type == 'fliplr' else 0
    for idx, fpath in enumerate(files, 1):
        rel = os.path.relpath(fpath, npz_dir)
        out_path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        data = np.load(fpath, allow_pickle=True)
        flipped = {}
        for k, v in data.items():
            if isinstance(v, np.ndarray) and v.ndim >= 2:
                flipped[k] = np.flip(v, axis=axis)
            else:
                flipped[k] = v
        np.savez_compressed(out_path, **flipped)
        print(f"[{idx}/{total}] {rel}")
    print('Batch flipping complete.')


def main():
    args = parse_args()
    batch_flip(args.dir, args.out, args.flip)


if __name__ == '__main__':
    main() 