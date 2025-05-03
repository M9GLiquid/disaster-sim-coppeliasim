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
- 🧠 **Event-driven depth dataset collection** Depth images for machine learning, triggered by simulation events
- 🎮 **Interactive control menus** for creating, clearing, restarting scenes

---

## Project Structure

| Folder/File                             | Purpose                                                                                         |
|-----------------------------------------|-------------------------------------------------------------------------------------------------|
| `.gitignore`                            | Specifies files and directories for Git to ignore                                               |
| `README.md`                             | Project overview, setup instructions, and usage guide                                           |
| `main.py`                               | Entry point: initializes sim, menus, controls, and runs the main loop                           |
| `CHANGELOG.md`                          | Tracks all notable changes to the project                                                      |
| `TODO.md`                               | Tracks planned features and improvements                                                        |

**Controls/**

| Folder/File                       | Purpose                                                                                         |
|-----------------------------------|-------------------------------------------------------------------------------------------------|
| `drone_control_manager.py`        | Orchestrates keyboard events into velocity & rotation targets                                   |
| `drone_keyboard_mapper.py`        | Maps WASD/QE/Space/Z keys to `keyboard/move` and `keyboard/rotate` events                       |
| `drone_movement_transformer.py`   | Transforms local forward/side/up + yaw-rate into world-frame velocities and applies them        |
| `target_mover.py`                 | Moves the `/target` dummy with simple inertia toward desired velocities and yaw rates           |

**Core/**

| Folder/File             | Purpose                                                         |
|-------------------------|-----------------------------------------------------------------|
| `event_manager.py`      | Thread-safe `subscribe`/`publish` messaging for decoupled modules|

**Managers/**

| Folder/File                      | Purpose                                                                                                   |
|----------------------------------|-----------------------------------------------------------------------------------------------------------|
| `depth_dataset_collector.py`     | Captures depth frames, poses, actions, and victim-direction vectors into batched `.npz` files            |
| `keyboard_manager.py`            | Low-level, cross-platform raw key capture thread that publishes `keyboard/key_pressed`                    |
| `menu_manager.py`                | Registry and dispatcher for named menus (`main`, `config`, etc.)                                         |
| `menu_system.py`                 | Routes ENTER/ESC to open/close menus, dispatches commands to the active menu                              |
| `scene_core.py`                  | Core functionality for scene generation with floor, trees, rocks                                         |
| `scene_creator_base.py`          | Abstract base class to standardize scene creation approaches                                             |
| `scene_object_creators.py`       | Helper functions for creating scene objects                                                              |
| `scene_pos_sampler.py`           | Samples positions for placing objects in the scene                                                       |
| `scene_progressive.py`           | Handles progressive procedural scene generation with event-driven updates                                |
| `typing_mode_manager.py`         | Gathers typed characters in "chat" mode, emits `typing/command_ready` or `typing/exit`                   |

**Managers/Connections/**

| Folder/File                | Purpose                                                                 |
|----------------------------|-------------------------------------------------------------------------|
| `sim_connection.py`       | Connects to CoppeliaSim via ZMQ, starts/stops simulation, and handles clean shutdown|

**Menus/**

| Folder/File           | Purpose                                                                                           |
|-----------------------|---------------------------------------------------------------------------------------------------|
| `main_menu.py`        | Shows “Create”, “Restart”, “Clear”, “Config”, and “Quit” options; publishes `menu/selected`       |
| `config_menu.py`      | Lists editable config fields (key + description), lets you toggle/update values                   |

**Sensors**

| Folder/File                  | Purpose                                                          |
|------------------------------|------------------------------------------------------------------|
| `rgbd_camera_setup.py`       | Attaches an RGB & depth vision sensor to the drone, sets up floating views |

**Utils**

| Folder/File                   | Purpose                                                                 |
|-------------------------------|-------------------------------------------------------------------------|
| `capture_utils.py`            | Grabs depth images and drone pose from the sim                          |
| `config_utils.py`             | Defines `FIELDS` schema and `get_default_config()` with adjustable parameters |
| `lock_utils.py`               | Provides thread-safe locking mechanisms                                 |
| `save_utils.py`               | Saves batches of depth/pose/actions/victim_dirs in compressed `.npz` files |
| `scene_helpers.py`            | Utility functions for scene creation and event handling                |
| `scene_utils.py`              | Starts/stops simulation if needed, clears `DisasterGroup`, calls `create_scene` |
| `terrain_elements.py`         | Creates floor, trees (fallen/standing), and rocks primitives            |

**Docs/**

| Folder/File                  | Purpose                                                                 |
|------------------------------|-------------------------------------------------------------------------|
| `Docs/en/`                   | Contains API documentation, guides, and references                     |
| `Docs/index/`                | Index files for documentation                                          |
| `Docs/js/`                   | JavaScript files for documentation                                      |
| `Docs/templates/`            | Templates for generating documentation                                 |
| `Docs/wb_img/`               | Images used in documentation                                           |

**Data**

| Folder/File                  | Purpose                                                                 |
|------------------------------|-------------------------------------------------------------------------|
| `data/depth_dataset/`        | Contains training, validation, and test datasets                       |
| `data/depth_dataset/train/`  | Training dataset                                                       |
| `data/depth_dataset/val/`    | Validation dataset                                                     |
| `data/depth_dataset/test/`   | Test dataset                                                           |

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

- Event-driven capture on each published `simulation/frame` event.
- Configurable sampling rate via `dataset_capture_frequency` (frames per capture).
- Real Euclidean distances to victim (replacing dummy values).
- Immediate one-off capture on `victim/detected` when distance < `victim_detection_threshold`.
- Published events:
  - `dataset/capture/complete`: per-frame metadata `{ frame, distance, action, victim_vec }`
  - `dataset/batch/saved` / `dataset/batch/error`: batch save notifications `{ folder, counter }`
  - `victim/detected`: anomaly alert `{ frame, distance }`
- Batching on in-memory buffers of size `batch_size`, saved on background thread.
- All event publishes from background threads are thread-safe.
- On shutdown, unsubscribes from dataset events to clean up callbacks.

Data is saved as compressed `.npz` files in `data/depth_dataset/{train,val,test}/batch_XXXXXX.npz` containing:
  - `depths`: float32 array (N, H, W)
  - `poses`: float32 array (N, 6)
  - `frames`: int32 array (N,)
  - `distances`: float32 array (N,)
  - `actions`: int32 array (N,)
  - `victim_dirs`: float32 array (N, 4)  # (ux,uy,uz,distance)

---

## Future Improvements

- Separate AI module for intelligent navigation (will be hosted in a dedicated repo).  
  *Placeholder: [AI Navigation Repository](https://github.com/your-org/ai-navigation-system)*

- Advanced obstacle avoidance and path planning.
- Dynamic obstacles such as moving objects or agents.
- Expanded disaster scenarios with additional elements.
- Add runtime log system for debugging and analysis.
- General bug fixes and polish.

---

## Contribution

- **Thomas Lundqvist** – Senior Developer  
  Main contributor responsible for core development and system architecture.

- **Jakub Espandr** – Developer & Tester  
  Assisted with development and conducted simulation testing.

- **Hieu Tran** – Documentation & Product Manager  
  Handled planning, documentation, and team coordination.

---

This project was built through close collaboration, shared responsibility, and open communication among all team members.

---

## License

MIT License
