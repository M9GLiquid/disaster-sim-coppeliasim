# Disaster Simulation with Drone Navigation (CoppeliaSim Project)

## Overview

This project simulates a disaster-struck area filled with fallen trees, rocks, and other obstacles, using CoppeliaSim. 
A quadcopter (drone) equipped with an RGB-D camera navigates the area. 
The system supports manual control, dataset collection for AI training, and dynamic environment generation.

Video showcasing the project:
[Video](https://drive.google.com/file/d/18U5E_Mlqz0zEZYPZGHmw8nj2tE6iEoNk/view?usp=sharing)

---

## Main Features

- 🛩️ **Drone control** (WASD + QE keyboard controls for movement and rotation)
- 📷 **RGB-D Camera setup** (floating view for live RGB images)
- 🌳 **Procedural disaster area generation** (rocks, standing/fallen trees)
- 🛠️ **Configuration menu** to adjust scene parameters at runtime
- 🧠 **Event-driven depth dataset collection** Depth images for machine learning, triggered by simulation events
- 🎮 **Interactive control menus** for creating, clearing, restarting scenes
- 📊 **Status tab with victim detection visualization** including direction indicator, elevation, distance, and signal strength

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

## Victim Detection Visualization

The Status Tab provides comprehensive visualization for victim detection:

- **Direction Indicator**: Radar-like display showing victim's position accurately relative to drone's heading
- **Elevation Indicator**: Displays victim's height difference in meters with color coding
- **Distance Display**: Shows distance to victim with color coding (green=near, orange=medium, red=far)
- **Signal Strength**: Visual indicator that increases as drone gets closer to victim
- **Safety Check**: System ensures victims spawn at least 2m away from the drone's starting position

All visualizations update in real-time through the event subscription system, with coordinate transformations aligned to the drone's orientation.

---

## Future Improvements

- Separate AI module for intelligent navigation (will be hosted in a dedicated repo).  
  *Placeholder: [AI Navigation Repository](https://github.com/your-org/ai-navigation-system)*

- Advanced obstacle avoidance and path planning.
- Dynamic obstacles such as moving objects or agents.
- Expanded disaster scenarios with additional elements.
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

This project is licensed under the “Personal Use Only License.” See [LICENSE](./LICENSE) for details.
