# Depth Dataset Format Documentation
## Overview

This document describes the format and collection methodology for depth datasets captured in the Disaster Simulation environment. The datasets are designed for training machine learning models for drone navigation and victim detection in disaster scenarios.

## Collection Methodology

### Capture Triggers

- **Event-driven capture**: Data is collected on each published `simulation/frame` event
- **Configurable sampling rate**: Controlled via `dataset_capture_frequency` (frames per capture)
- **Special event capture**: Immediate one-off capture occurs on `victim/detected` events when distance < `victim_detection_threshold`

### Published Events

The system publishes several events during dataset collection:

- `dataset/capture/complete`: Emitted per-frame with metadata `{ frame, distance, action, victim_vec }`
- `dataset/batch/saved`: Notification when a batch is successfully saved `{ folder, counter }`
- `dataset/batch/error`: Error notification if batch saving fails `{ folder, counter }`
- `victim/detected`: Anomaly alert with data `{ frame, distance }`

### Processing Pipeline

1. Data is captured based on configured frequency
2. Collected samples are stored in in-memory buffers of size `batch_size`
3. When a buffer is full, data is saved on a background thread
4. All event publishing from background threads is thread-safe
5. On shutdown, the system unsubscribes from dataset events to clean up callbacks

## File Format

### Storage Structure

Datasets are saved as compressed `.npz` files in the following directory structure:
```
data/depth_dataset/
├── train/
│   └── batch_XXXXXX.npz
├── val/
│   └── batch_XXXXXX.npz
└── test/
    └── batch_XXXXXX.npz
```

### Data Arrays

Each `.npz` file contains the following arrays:

| Array | Type | Shape | Description |
|-------|------|-------|-------------|
| `depths` | float32 | (N, H, W) | Depth images from RGB-D camera |
| `poses` | float32 | (N, 6) | Drone pose data (position and orientation) |
| `frames` | int32 | (N,) | Frame indices from the simulation |
| `distances` | float32 | (N,) | Real Euclidean distances to victim |
| `actions` | int32 | (N,) | Control actions taken by the drone |
| `victim_dirs` | float32 | (N, 4) | Victim direction vectors (ux, uy, uz, distance) |

Where:
- N: Number of samples in the batch
- H: Height of the depth image
- W: Width of the depth image

## Usage Recommendations

- For training navigation models, use the `depths` and `actions` arrays
- For victim detection, focus on `depths` and `victim_dirs`
- The `distances` array provides ground truth for distance estimation models
- Split your models between the train, validation, and test datasets for proper evaluation

## Data Preprocessing

For preprocessing the collected depth images, use the provided tool:
```bash
python Tools/View_Depth_Image.py
```

This tool provides a GUI for batch image viewing and flipping, which can be useful for data inspection and preprocessing before training machine learning models. 