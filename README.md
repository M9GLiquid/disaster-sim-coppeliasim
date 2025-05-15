<p align="center">
  <a href="https://i.imghippo.com/files/snk6965sI.png">
    <img src="https://i.imghippo.com/files/snk6965sI.png" alt="Disaster Sim Logo" width="250"/>
  </a>
</p>

<h1 align="center">Disaster Simulation with Drone Navigation</h1>
<p align="center"><em>(CoppeliaSim Project)</em></p>

## Overview

This project simulates a disaster-struck area filled with fallen trees, rocks, and other obstacles, using CoppeliaSim. 
A quadcopter (drone) equipped with an RGB-D camera navigates the area. 
The system supports manual control, dataset collection for AI training, and dynamic environment generation.

---

## Quick Start

```bash
# Clone the repository
gh repo clone Jakub-Espandr/disaster-sim-coppeliasim
# Move to directory
cd disaster-sim-coppeliasim
# Install dependencies
pip install -r requirements.txt
# Launch CoppeliaSim with your quadcopter scene
# Then run:
python main.py
```

---

## Main Features

- 🛩️ **Drone control** (WASD + QE keyboard controls for movement and rotation)
- 📷 **RGB-D Camera setup** (floating view for live RGB images)
- 🌳 **Procedural disaster area generation** (rocks, standing/fallen trees)
- 🛠️ **Configuration menu** to adjust scene parameters at runtime
- 🧠 **Event-driven depth dataset collection** Depth images for machine learning, triggered by simulation events
- 🎮 **Interactive control menus** for creating, clearing, restarting scenes
- 📊 **Status tab with victim detection visualization** including direction indicator, elevation, distance, and signal strength
- 🧪 **Tool Suite:** GUI tools for viewing and preprocessing collected depth datasets, and for generating application icons

---

## Setup Instructions

1. Install [CoppeliaSim 4.9.0](https://www.coppeliarobotics.com/downloads.html).
2. Make sure the `zmqRemoteApi` plugin is available (standard in 4.6+).
3. Install required Python packages:

```bash
pip install -r requirements.txt
```

4. Start CoppeliaSim with a quadrotor scene containing:
   - `Quadcopter` model
   - `/target` dummy
   - `/propeller` children properly configured

5. Run the simulation:

```bash
python main.py
```

6. Use the keyboard or RC Joystick to interact:
   - Use `W/A/S/D` + `Q/E` + `Z/SPACE`keys to move and rotate the drone.

---

## Tools

🧰 **Disaster Simulation Tools**  
Includes utility apps like:

- `View_Depth_Image.py` – GUI for batch image viewing and flipping
- `Icon_Creator.py` – Create custom application icons (macOS/Windows friendly)

Run tools using:

```bash
python Tools/View_Depth_Image.py
python Tools/Icon_Creator.py
```

---

## Dataset Collection Behavior

Event-driven and real-time collection, saved in `.npz` format.  
Refer to [dataset format documentation](docs/dataset_format.md) for details.

---

## Victim Detection Visualization

Comprehensive UI with radar indicators, elevation display, and real-time vector updates.

---

## Supported Controls

### 🖥️ Keyboard

| Key     | Action             |
|---------|--------------------|
| `W`     | Move Forward       |
| `S`     | Move Backward      |
| `A`     | Strafe Left        |
| `D`     | Strafe Right       |
| `Q`     | Rotate Left (Yaw)  |
| `E`     | Rotate Right (Yaw) |
| `Space` | Move Up            |
| `Z`     | Move Down          |

### 🎮 USB RC Transmitter (e.g. Jumper T-PRO v2)

| Stick        | Control        |
|--------------|----------------|
| Left Stick   | Throttle / Yaw |
| Right Stick  | Pitch / Roll   |

---

## Contributors

- **Thomas Lundqvist** – System Architect & Developer  
- **Jakub Espandr** – Feature Developer & Testing  
- **Hieu Tran** – Documentation & Management

---

## License

MIT License