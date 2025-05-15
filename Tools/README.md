# Disaster Simulation Tools

This directory contains utility tools for working with the Disaster Simulation CoppeliaSim project.

## Available Tools

### View_Depth_Image.py

A GUI application for viewing and manipulating depth image datasets collected by the simulation.

#### Features

- Browse all `.npz` depth image files in the dataset directory.
- View multiple depth images from each batch file in a grid layout.
- Flip images left-right or up-down in batches with a single click.
- Visual indicators for flipped vs. original images.
- Automatically save changes when moving between files.
- Auto-advance through files with continuous flipping (Space to start, ESC to stop).
- Preview flip operations before applying them to the dataset.
- Validate image orientation before processing to ensure correct display.
- Quick flip preview buttons for immediate feedback on flip types.
- Full-depth data image preview to view individual images in detail.
- 3D visualization of depth data for enhanced analysis.
- User-friendly interface designed for ease of use.
- Help tab providing detailed information on operations and usage.

#### Usage

```bash
python Tools/View_Depth_Image.py
```

#### Keyboard Shortcuts

- **Left/Right Arrows**: Navigate between files
- **Space**: Flip all images up-down (hold to auto-advance)
- **Enter**: Flip all images left-right
- **Escape**: Stop auto-advance

#### Requirements

- Python 3.x
- NumPy
- PIL (Pillow)
- Tkinter

## Installation

The tools are designed to work with the main simulation project. No additional installation is required beyond the dependencies of the main project.

## Dataset Structure

hese tools expect dataset files in the `data/depth_dataset` directory, organized in train/val/test subdirectories with `.npz` files containing depth images and metadata. The dataset is automatically loaded from this directory on the local drive, but users can change the directory as needed.

The default structure is:
```
data/
├── depth_dataset/
│   ├── train/
│   │   ├── batch_000001.npz
│   │   ├── batch_000002.npz
│   │   └── ...
│   ├── val/
│   │   ├── batch_000001.npz
│   │   └── ...
│   └── test/
│       ├── batch_000001.npz
│       └── ...
```