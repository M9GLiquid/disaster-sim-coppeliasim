# main.py

import time

from disaster_area import create_disaster_area
from dynamic_objects import create_all_dynamic

from Utils.scene_utils import clear_disaster_area, restart_disaster_area
from Utils.config_utils import get_default_config, modify_config

from Controls.camera_setup import setup_drone_camera
from Controls.camera_view import CameraView

from Core.event_manager import EventManager
from Managers.keyboard_manager import KeyboardManager
from Controls.drone_keyboard_mapper import register_drone_keyboard_mapper
from Controls.typing_mode_handler import register_typing_mode_handler
from Controls.keyboard_handlers import register_keyboard_handlers

from Managers.Connections.sim_connection import connect_to_simulation, shutdown_simulation

def show_menu():
    print("\n[Main Menu]")
    print("  1 - Create disaster area")
    print("  2 - Add dynamic flying objects (birds & junk)")
    print("  3 - Restart disaster area")
    print("  4 - Clear disaster area")
    print("  9 - Modify configuration")
    print("  q - Quit\n")

def main():
    event_manager = EventManager()
    sim = connect_to_simulation()
    print("[Main] Simulation connected.")

    sim.setStepping(True)

    config = get_default_config()

    camera_handle, target_handle = setup_drone_camera(sim, config)
    camera_view = CameraView(sim, camera_handle)
    camera_view.start()

    keyboard_manager = KeyboardManager(event_manager)
    register_drone_keyboard_mapper(event_manager)
    register_typing_mode_handler(event_manager, keyboard_manager)
    register_keyboard_handlers(event_manager, sim, target_handle)

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
                try:
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
                finally:
                    sim.releaseLock()

            camera_view.update()

            for _ in range(3):
                sim.step()

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt received. Exiting...")

    finally:
        shutdown_simulation(keyboard_manager, camera_view, sim)
        print("[Main] Shutdown complete.")

if __name__ == '__main__':
    main()
