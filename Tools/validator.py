#!/usr/bin/env python3
"""
Validator: preview one sample .npz, show depths image and metadata side by side in Tkinter;
allow Accept or Flip Left–Right or Flip Up–Down; if flip selected, auto-run flip tool on entire dataset.

Usage:
    python validator.py --dir <dataset_dir> --out <output_dir> [--file <sample_npz>]
Requires: numpy, pillow
"""
import argparse
import os
import sys
import random
import subprocess
import numpy as np
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk


def parse_args():
    parser = argparse.ArgumentParser(description='Orientation Validator')
    parser.add_argument('--dir', required=True, help='Directory containing .npz files')
    parser.add_argument('--out', required=True, help='Output directory for flipped files')
    parser.add_argument('--file', default=None, help='Optional specific .npz file to preview')
    return parser.parse_args()


def select_sample(npz_dir, sample_file):
    if sample_file:
        if not os.path.isfile(sample_file):
            print(f"Sample file {sample_file} not found", file=sys.stderr)
            sys.exit(1)
        return sample_file
    files = []
    for root, _, names in os.walk(npz_dir):
        for name in names:
            if name.lower().endswith('.npz'):
                files.append(os.path.join(root, name))
    if not files:
        print(f"No .npz files found in {npz_dir}", file=sys.stderr)
        sys.exit(1)
    return random.choice(files)


def load_npz(path):
    return np.load(path, allow_pickle=True)


def prepare_image(arr):
    # scale to uint8 and convert to PIL Image
    if arr.ndim == 2:
        a = arr
    elif arr.ndim == 3 and arr.shape[2] in (1,3,4):
        a = arr
    else:
        a = arr.squeeze()
    if a.dtype != np.uint8:
        minv, maxv = np.nanmin(a), np.nanmax(a)
        if maxv > minv:
            a = ((a - minv) / (maxv - minv) * 255).astype(np.uint8)
        else:
            a = np.zeros_like(a, dtype=np.uint8)
    if a.ndim == 2:
        img = Image.fromarray(a, mode='L')
    else:
        if a.shape[2] == 1:
            img = Image.fromarray(a[:,:,0], mode='L')
        else:
            img = Image.fromarray(a, mode='RGB')
    return img


class ValidatorApp:
    def __init__(self, root, pil_img, metadata_str, dataset_dir, out_dir, sample_file):
        self.root = root
        self.choice = 'none'
        self.dataset_dir = dataset_dir
        self.out_dir = out_dir
        self.sample_file = sample_file
        self.pil_img = pil_img
        self.photo = ImageTk.PhotoImage(self.pil_img)
        # image on left
        self.label = tk.Label(root, image=self.photo)
        self.label.pack(side=tk.LEFT, padx=5, pady=5)
        # metadata on right
        self.text = ScrolledText(root, width=40, height=20)
        self.text.insert(tk.END, metadata_str)
        self.text.config(state='disabled')
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        # buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Button(btn_frame, text='Accept', command=self.accept).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(btn_frame, text='Flip Left–Right', command=self.flip_lr).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(btn_frame, text='Flip Up–Down', command=self.flip_ud).pack(side=tk.LEFT, padx=5, pady=5)

    def accept(self):
        self.root.destroy()

    def flip_lr(self):
        self.choice = 'fliplr'
        self.pil_img = self.pil_img.transpose(Image.FLIP_LEFT_RIGHT)
        self.photo = ImageTk.PhotoImage(self.pil_img)
        self.label.config(image=self.photo)

    def flip_ud(self):
        self.choice = 'flipud'
        self.pil_img = self.pil_img.transpose(Image.FLIP_TOP_BOTTOM)
        self.photo = ImageTk.PhotoImage(self.pil_img)
        self.label.config(image=self.photo)


def main():
    args = parse_args()
    sample = select_sample(args.dir, args.file)
    data = load_npz(sample)
    if 'depths' not in data:
        print(f"Key 'depths' not found in {sample}. Available: {list(data.keys())}", file=sys.stderr)
        sys.exit(1)
    arr = data['depths']
    if arr.ndim == 3:
        arr = arr[0]  # Show the first image in the batch
    metadata_lines = [f"{k}: shape={v.shape}, dtype={v.dtype}" for k, v in data.items()]
    metadata = 'Metadata:\n' + '\n'.join(metadata_lines)
    pil_img = prepare_image(arr)
    root = tk.Tk()
    root.title('Orientation Validator')
    app = ValidatorApp(root, pil_img, metadata, args.dir, args.out, sample)
    root.mainloop()
    # after window closes, if flip selected, run flip tool
    if app.choice in ('fliplr', 'flipud'):
        script = os.path.join(os.path.dirname(__file__), 'flip.py')
        subprocess.run([sys.executable, script,
                        '--dir', args.dir,
                        '--flip', app.choice,
                        '--out', args.out], check=True)
    sys.exit(0)


if __name__ == '__main__':
    main() 