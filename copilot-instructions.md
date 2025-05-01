# CoppeliaSim V4.6–V4.9 Understanding and Programming Guidance

This project is focused on building a **simulation-based dataset generator** using **CoppeliaSim V4.9+**, intended for future use in drone navigation via machine learning. The AI component is not being developed at this stage — the priority is to create clean, modular tools for simulation, data collection, and environmental setup.

Provide guidance for programming in **CoppeliaSim V4.9**, with strict reference to the **manual and API documentation stored in the `docs/` directory**. Follow clean modular practices, including the **Single Responsibility Principle (SRP)** and the **Golden Principle**, and utilize the files provided under **Project Files**.

---

## 🔷 Project Overview

This simulator replicates a drone hovering above an H-shaped platform with dynamic and static obstacles. The goal is to create a labeled dataset using RGBD data from a simulated onboard camera for future use in AI training.

### 🗂️ File Structure Snapshot
```
project/
├── main.py                          # Entry point: initializes sim, menus, controls, and runs the main loop
├── README.md                        # Project overview, setup instructions, and usage guide
├── Controls/
│   ├── drone_control_manager.py     # Orchestrates keyboard events into velocity & rotation targets
│   ├── drone_keyboard_mapper.py     # Maps WASD/QE/Space/Z keys to keyboard/move and keyboard/rotate events
│   ├── drone_movement_transformer.py # Transforms local velocities into world-frame velocities
│   └── target_mover.py              # Moves the /target dummy with inertia toward velocities and yaw rates
├── Core/
│   └── event_manager.py             # Thread-safe subscribe/publish messaging for decoupled modules
├── data/
│   └── depth_dataset/               # Output folder for collected simulation data
│       ├── train/                   # Training data storage
│       ├── val/                     # Validation data storage
│       └── test/                    # Test data storage
├── Docs/                            # Contains CoppeliaSim 4.9+ documentation
├── Interfaces/
│   └── menu_interface.py            # Abstract base class defining menu hooks
├── Managers/
│   ├── depth_dataset_collector.py   # Captures depth frames, poses, actions, and victim-direction vectors
│   ├── keyboard_manager.py          # Low-level, cross-platform raw key capture thread
│   ├── menu_manager.py              # Registry and dispatcher for named menus
│   ├── menu_system.py               # Routes ENTER/ESC to open/close menus, dispatches commands
│   ├── scene_manager.py             # Procedurally generates floor, trees, rocks; places the victim
│   ├── typing_mode_manager.py       # Gathers typed characters in "chat" mode
│   └── Connections/
│       └── sim_connection.py        # Connects to CoppeliaSim via ZMQ
├── Menus/
│   ├── config_menu.py               # Lists editable config fields, lets you toggle/update values
│   └── main_menu.py                 # Shows "Create", "Restart", "Clear", "Config", and "Quit" options
├── Sensors/
│   └── rgbd_camera_setup.py         # Attaches RGB & depth vision sensor to the drone
└── Utils/
    ├── capture_utils.py             # Grabs depth images and drone pose from the sim
    ├── config_utils.py              # Defines FIELDS schema and get_default_config()
    ├── save_utils.py                # Saves batches of depth/pose/actions/victim_dirs in .npz files
    ├── scene_utils.py               # Starts/stops simulation, clears DisasterGroup, calls create_scene
    └── terrain_elements.py          # Creates floor, trees (fallen/standing), and rocks primitives
```

---

## Main Version Changes

- **V 4.6.0**:
  - Integrated direct Python integration and Remote API access.
  - Improved modular plugin structure.

- **V 4.7.0**:
  - Renamed Child Scripts → Simulation Scripts.
  - Various bug fixes and performance optimizations.

- **V 4.8.0**:
  - Implemented Unified Property System: standardized all object properties.
  - Launched Property Explorer Add-on.
  - Integrated TOPPRA for better path timing optimization.

- **V 4.9.0**:
  - Integrated MuJoCo 3.2.6 for faster physics simulation.
  - Added adhesion support (MuJoCo-specific).
  - Deprecated composite types (rope, cube, etc.).
  - Introduced stack-based string/buffer handling (Lua/Python APIs).

---

## Key Documentation Resources (Mandatory Usage)

📂 You **must use the official documentation files stored locally in the `docs/` folder**. Do not rely on outdated, external or inferred behavior.

The `docs/` folder contains:

- API Function Reference (HTML or PDF)
- Unified Property System Overview
- Properties Reference List
- Version History Overview

If any information is missing, ask the project maintainer before making assumptions.

---

## Steps to Follow

1. **Reference Check**  
   Always verify functions, constants, and object properties against the local manual in `docs/`.

2. **Documentation Review**  
   Understand and adapt deprecated or modified features across versions.

3. **Property Usage**  
   Only modify/read properties listed in the official documentation in `docs/`.

4. **Code Snippet Inclusion**  
   When providing code:
   - Preceding Line
   - New or Modified Line
   - Following Line

5. **Utilization of Project Files**  
   Leverage and extend the shared Project Files (`event_manager.py`, `main.py`, `scene_manager.py`, etc.)  
   - Maintain a modular structure  
   - Respect file boundaries and separation of concerns  

---

## 📀 Code Design & Structure Guidelines

### 1. **Single Responsibility Principle (SRP)**
Each **module**, **class**, and **function** must perform **only one well-defined task**.

- Avoid mixing concerns (e.g., sensor logic and control logic in the same module).
- If a unit begins handling unrelated tasks, **refactor and isolate functionality**.
- Split large modules into smaller, testable components when boundaries blur.

> ✅ *Example*: `rgbd_camera_setup.py` should handle only camera setup and configuration.  
> ❌ *Anti-example*: A controller that also processes images and logs telemetry.

### 2. **Golden Principle – Simplicity & Modularity**
Keep code **simple, readable, and easy to modify**:

- Use short, purpose-specific functions.
- Minimize deep inheritance and avoid overengineering.
- Prefer composition and separation of concerns.

> ✅ *Example*: A separate `DroneControlManager` that receives discrete commands.  
> ❌ *Anti-example*: One class that controls, senses, logs, and reacts.

### 3. **Commenting Policy**
Use **comments only when they add meaningful value**. Unnecessary comments should be avoided.

- Favor **self-explanatory code** over explaining what is already obvious.
- Add comments for:
  - **Non-trivial logic or optimizations**
  - **Workarounds or known limitations**
  - **High-level documentation blocks at module/function entry points**

> ✅ *Good*:  
> ```python
> # Normalize depth map to range [0, 1] before feeding to model
> normalized_depth = depth_map / max_val
> ```
>
> ❌ *Bad*:  
> ```python
> # Add 1 to i
> i += 1
> ```

---

## Mandatory Compliance Rules

- ✅ Only use functions and properties described in the **`docs/` manual**.
- ✅ Do not reference undocumented or deprecated features unless they are explicitly noted.
- ✅ Stay within the architectural conventions provided in this guidance.

- ❌ Forbidden to use undocumented APIs, internal-only extensions, or Lua server-only commands.
- ❌ Forbidden to guess or introduce undefined behavior.

---

## Notes and Expectations

- Use the **Version History (in `docs/`)** when updating scripts or features across CoppeliaSim versions.
- Carefully refactor deprecated calls using the official guidelines.
- Code must be:
  - **Context-aware**
  - **Modular**
  - **Readable**
- Favor many small, purposeful files over large, cluttered modules.
- Follow these practices:
  - Consistent naming
  - Minimal viable complexity
  - Clear function responsibilities
- **Always build upon and cleanly update the Project Files.**
