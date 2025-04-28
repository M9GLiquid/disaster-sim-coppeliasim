# Disaster Simulation with Drone Navigation (CoppeliaSim Project)

## Overview

This project simulates a disaster-struck area filled with fallen trees, rocks, and other obstacles, using CoppeliaSim. 
A quadcopter (drone) equipped with an RGB-D camera navigates the area. 
The system supports manual control, dataset collection for AI training, and dynamic environment generation.

---

## Main Features

- 🛩️ **Drone control** (WASD + QE keyboard controls for movement and rotation)
- 📷 **RGB-D Camera setup** (floating views for live RGB and depth images)
- 🌳 **Procedural disaster area generation** (rocks, standing/fallen trees)
- 🛠️ **Configuration menu** to adjust scene parameters at runtime
- 🧠 **Depth dataset collection** for future machine learning projects
- 🎮 **Interactive control menus** for creating, clearing, restarting scenes

---

## Project Structure

| Folder/File                  | Purpose |
|--------------------------------|---------|
| `main.py`                     | Entry point to start simulation and control loop |
| `Managers/keyboard_manager.py` | Low-level keyboard input handling |
| `Managers/menu_system.py`      | Menu display and input mode switching |
| `Managers/movement_manager.py` | Queue-based movement command system |
| `Managers/depth_dataset_collector.py` | Captures depth data and drone pose for datasets |
| `Core/event_manager.py`        | Publish/Subscribe messaging system |
| `Controls/drone_keyboard_mapper.py` | Maps keypresses to movement/rotation commands |
| `Utils/config_utils.py`        | Default configuration and editing system |
| `Utils/scene_utils.py`         | Utility functions for resetting disaster areas |
| `Sensors/rgbd_camera_setup.py` | Initializes RGB + Depth cameras on drone |
| `disaster_area.py`             | Creates procedural rocks and trees |
| `Utils/save_utils.py`          | Saves collected datasets into compressed files |
| `Utils/capture_utils.py`       | Depth image and pose capture functions |
| `sim_connection.py`            | CoppeliaSim connection and shutdown helpers |

---

## Setup Instructions

1. Install [CoppeliaSim 4.9.0](https://www.coppeliarobotics.com/downloads.html).
2. Make sure the `zmqRemoteApi` plugin is available (standard in 4.6+).
3. Install required Python packages:

```bash
pip install coppeliasim-zmqremoteapi-client numpy
```

4. Start CoppeliaSim with a quadrotor scene containing:
   - `Quadcopter` model
   - `/target` dummy
   - `/propeller` children properly configured

5. Run the simulation from `main.py`:

```bash
python main.py
```

6. Use the keyboard to interact:
   - Use `W/A/S/D` + `Q/E` keys to move and rotate the drone.
   - Press `Enter` to open the menu.
---

## Controls

| Key  | Action |
|------|-------|
| `W`  | Move Forward |
| `S`  | Move Backward |
| `A`  | Strafe Left |
| `D`  | Strafe Right |
| `Q`  | Rotate Left (Yaw) |
| `E`  | Rotate Right (Yaw) |
| `Space` | Move Up |
| `Z`  | Move Down |

---

## Dataset Collection Behavior

- Depth images and drone poses are captured every N simulation frames.
- Each saved batch contains:
  - `depths`: Depth images
  - `poses`: Drone positions and orientations `[x, y, z, roll, pitch, yaw]`
  - `frames`: Frame numbers
  - `distances`: Placeholder distances (currently always `-1.0`)
  - `actions`: Discrete movement/rotation labels
- Data is saved automatically in compressed `.npz` files.
- Dataset is split into `train/`, `val/`, and `test/` folders based on the configured ratio.

---

## Future Improvements

- Advanced obstacle avoidance AI (planned).
- Dynamic obstacles (moving targets).
- Expand the disaster scenario with additional elements.
- Refactored menu system

---

## Authors

- Core Developer: Thomas Lundqvist
- Simulation based on CoppeliaSim API v4.9

---

## License

MIT License
