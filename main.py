# main.py

import time

from Managers.depth_dataset_collector    import DepthDatasetCollector
from Utils.scene_utils                   import clear_disaster_area, restart_disaster_area
from Utils.config_utils                  import get_default_config

from Sensors.rgbd_camera_setup           import setup_rgbd_camera
from Controls.drone_keyboard_mapper      import register_drone_keyboard_mapper

from Core.event_manager                  import EventManager

from Managers.scene_manager              import create_scene
from Managers.keyboard_manager           import KeyboardManager
from Managers.menu_system                import MenuSystem
from Managers.Connections.sim_connection import connect_to_simulation, shutdown_simulation

from Controls.drone_control_manager      import DroneControlManager

def main():
    event_manager = EventManager()
    sim = connect_to_simulation()
    print("[Main] Simulation connected.")

    sim.setStepping(True)
    config = get_default_config()

    cam_rgb, floating_view_rgb, = setup_rgbd_camera(sim, config)

    depth_collector = DepthDatasetCollector(
        sim,
        cam_rgb,
        base_folder="data/depth_dataset",
        batch_size=100,
        save_every_n_frames=10,
        split_ratio=(0.98, 0.01, 0.01),
        event_manager=event_manager
    )

    keyboard_manager = KeyboardManager(event_manager)
    menu_system = MenuSystem(event_manager, keyboard_manager, config)
    register_drone_keyboard_mapper(event_manager, keyboard_manager, config)

    # Create full drone control chain
    drone_control_manager = DroneControlManager(event_manager, sim)

    # Menu command handler
    current_command = None
    def on_menu_selected(cmd):
        nonlocal current_command
        current_command = cmd
    event_manager.subscribe('menu/selected', on_menu_selected)

    timestep = 0.05  # 50 ms steps

    try:
        while True:
            if current_command:
                sim.acquireLock()
                try:
                    if current_command == '1':
                        create_scene(sim, config)
                    elif current_command == '3':
                        restart_disaster_area(sim, config)
                    elif current_command == '4':
                        clear_disaster_area(sim)
                    elif current_command == 'q':
                        print("[Main] Quit requested.")
                        break
                    else:
                        print("[Main] Unknown command.")
                finally:
                    sim.releaseLock()

                if current_command != 'q':
                    menu_system.open_chat()
                current_command = None

            # update drone controls
            drone_control_manager.update(timestep)

            # Vision Sensors
            sim.acquireLock()
            try:
                sim.handleVisionSensor(cam_rgb)
                depth_collector.capture()
            finally:
                sim.releaseLock()

            sim.step()
            time.sleep(timestep)

    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt received. Exiting...")

    finally:
        shutdown_simulation(keyboard_manager, depth_collector, floating_view_rgb, sim)
        print("[Main] Shutdown complete.")

if __name__ == '__main__':
    main()
