# Disaster Simulation with Drone Navigation (CoppeliaSim Project)

## Overview

This project simulates a disaster-struck area filled with fallen trees, rocks, and other obstacles, using CoppeliaSim. 
A quadcopter (drone) equipped with an RGB-D camera navigates the area. 
The system supports manual control, dataset collection for AI training, and dynamic environment generation.

---

## Main Features

- 🛩️ **Drone control** (WASD + QE keyboard controls for movement and rotation)
- 📷 **RGB-D Camera setup** (floating view for live RGB images)
- 🌳 **Procedural disaster area generation** (rocks, standing/fallen trees)
- 🛠️ **Configuration menu** to adjust scene parameters at runtime
- 🧠 **Depth dataset collection** Depth images for machine learning
- 🎮 **Interactive control menus** for creating, clearing, restarting scenes

---

## Project Structure

| Folder/File                                      | Purpose                                                                                         |
|--------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `.gitignore`                                     | Specifies files and directories for Git to ignore                                               |
| `README.md`                                      | Project overview, setup instructions, and usage guide                                           |
| `main.py`                                        | Entry point: initializes sim, menus, controls, and runs the main loop                           |
| **Controls/**                                    | Mapping from high-level commands to drone movements                                             |
| `Controls/drone_control_manager.py`               | Orchestrates keyboard events into velocity & rotation targets                                   |
| `Controls/drone_keyboard_mapper.py`               | Maps WASD/QE/Space/Z keys to `keyboard/move` and `keyboard/rotate` events                       |
| `Controls/drone_movement_transformer.py`          | Transforms local forward/side/up + yaw-rate into world-frame velocities and applies them        |
| `Controls/target_mover.py`                        | Moves the `/target` dummy with simple inertia toward desired velocities and yaw rates           |
| **Core/**                                        | Publish/subscribe event dispatch system                                                         |
| `Core/event_manager.py`                          | Thread-safe `subscribe`/`publish` messaging for decoupled modules                               |
| **Managers/Connections/**                         | CoppeliaSim connection and shutdown helpers                                                     |
| `Managers/Connections/sim_connection.py`         | Connects to CoppeliaSim via ZMQ, starts/stops simulation, and handles clean shutdown            |
| **Managers/**                                     | High-level orchestration: input, menus, scene creation, data collection                         |
| `Managers/keyboard_manager.py`                    | Low-level, cross-platform raw key capture thread that publishes `keyboard/key_pressed`          |
| `Managers/typing_mode_manager.py`                 | Gathers typed characters when in “chat” mode, emits `typing/command_ready` or `typing/exit`    |
| `Managers/menu_interface.py`                      | Abstract base class defining `on_open`, `on_command`, and `on_exit` hooks for menus            |
| `Managers/menu_manager.py`                        | Registry and dispatcher for named menus (`main`, `config`, etc.)                                |
| `Managers/menu_system.py`                         | Routes ENTER/ESC to open/close menus, dispatches commands to the active menu                    |
| `Managers/scene_manager.py`                       | Procedurally generates floor, trees, rocks; teleports drone & target; places the victim        |
| `Managers/depth_dataset_collector.py`             | Captures depth frames, poses, actions, and victim-direction vectors into batched `.npz` files   |
| **Menus/**                                       | Concrete menu implementations conforming to `MenuInterface`                                      |
| `Menus/main_menu.py`                              | Shows “Create”, “Restart”, “Clear”, “Config”, and “Quit” options; publishes `menu/selected`     |
| `Menus/config_menu.py`                            | Lists editable config fields (key + description), lets you toggle/update values                 |
| **Sensors/**                                     | Camera setup utilities                                                                          |
| `Sensors/rgbd_camera_setup.py`                    | Attaches an RGB & depth vision sensor to the drone, sets up floating views                      |
| **Utils/**                                       | Standalone helpers: configuration, scene clearing, terrain, saving & capture functions          |
| `Utils/config_utils.py`                           | Defines `FIELDS` schema and `get_default_config()` with all adjustable parameters               |
| `Utils/scene_utils.py`                            | Starts/stops simulation if needed, clears `DisasterGroup`, calls `create_scene` under the hood  |
| `Utils/terrain_elements.py`                       | Creates floor, trees (fallen/standing), and rocks primitives                                    |
| `Utils/capture_utils.py`                          | Grabs depth images and drone pose from the sim                                                  |
| `Utils/save_utils.py`                             | Saves batches of depth/pose/actions/victim_dirs in compressed `.npz` files                      |


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

---

## Authors

- Core Developer: Thomas Lundqvist
- Simulation based on CoppeliaSim API v4.9

---

## License

MIT License
