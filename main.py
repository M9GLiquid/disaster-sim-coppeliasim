# main.py

import time

from disaster_area import create_disaster_area
from dynamic_objects import create_all_dynamic

from Utils.scene_utils import start_sim_if_needed, clear_disaster_area, restart_disaster_area
from Utils.config_utils import get_default_config, modify_config

from Controls.drone_control import manual_drone_control
from Controls.waypoint_navigation import prepare_waypoint, activate_waypoint_follow
from Controls.camera_setup import setup_drone_camera
from Controls.camera_view import CameraView
from Controls.keyboard_manager import KeyboardManager

import threading

def show_menu():
    print("\n[Main Menu]")
    print("  1 - Create disaster area")
    print("  2 - Add dynamic flying objects (birds & junk)")
    print("  3 - Restart disaster area")
    print("  4 - Clear disaster area")
    print("  9 - Modify configuration")
    print("  q - Quit\n")

def main():
    sim = start_sim_if_needed()
    print("[Main] Simulation started.")

    sim.setStepping(True)

    config = get_default_config()

    camera_handle, target_handle = setup_drone_camera(sim, config)

    camera_view = CameraView(sim, camera_handle)
    camera_view.start()

    keyboard_manager = KeyboardManager(sim, target_handle)
    try:
        while True:
            keyboard_manager.process_keys()

            if keyboard_manager.in_typing_mode():
                show_menu()
                sim.setStepping(False)
                command = input(">> ").strip().lower()
                sim.setStepping(True) 
                keyboard_manager.finish_typing(command)

            command = keyboard_manager.get_command()
            if command:
                sim.acquireLock()
                if command == '1':
                    create_disaster_area(sim, config)
                elif command == '2':
                    create_all_dynamic(sim, config['area_size'], num_birds=1, num_junk=3)
                elif command == '3':
                    restart_disaster_area(sim, config)
                elif command == '4':
                    clear_disaster_area(sim)

                elif command == '9':
                    modify_config(config)

                elif command == 'q':
                    print("[Main] Quit requested.")
                    break
                else:
                    print("[Main] Unknown command.")
                sim.releaseLock()

            camera_view.update()

            for _ in range(3):
                sim.step()

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n[Main] Exiting on Ctrl-C.")

    keyboard_manager.stop()
    camera_view.close()

    # Graceful shutdown
    try:
        sim.disconnect()
    except Exception:
        pass  # Sometimes sim already closed

    print("[Main] Simulation stopped.")

if __name__ == '__main__':
    main()
