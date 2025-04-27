# main.py

import time

from disaster_area                     import create_disaster_area
from Utils.scene_utils                 import clear_disaster_area, restart_disaster_area
from Utils.config_utils                import get_default_config    # ← still build your dict

from Controls.camera_setup             import setup_drone_camera
from Controls.camera_view              import CameraView
from Managers.movement_manager         import MovementManager

from Core.event_manager                import EventManager
from Controls.drone_keyboard_mapper    import register_drone_keyboard_mapper

from Managers.keyboard_manager         import KeyboardManager
from Managers.menu_system              import MenuSystem

from Managers.Connections.sim_connection import connect_to_simulation, shutdown_simulation


def main():
    event_manager    = EventManager()
    sim              = connect_to_simulation()
    print("[Main] Simulation connected.")

    sim.setStepping(True)

    # build your config dict once
    config = get_default_config()

    # camera
    cam_handle, target_handle = setup_drone_camera(sim, config)
    camera_view               = CameraView(sim, cam_handle)
    camera_view.start()

    # input systems
    keyboard_manager = KeyboardManager(event_manager)
    menu_system      = MenuSystem(event_manager, keyboard_manager, config)
    movement_manager = MovementManager(event_manager)

    register_drone_keyboard_mapper(event_manager, keyboard_manager)

    #  ─── main menu → command dispatcher
    current_command = None
    def on_menu_selected(cmd):
        nonlocal current_command
        current_command = cmd
    event_manager.subscribe('menu/selected', on_menu_selected)

    try:
        while True:
            # ─── if user picked 1/3/4/q, handle here
            if current_command:
                sim.acquireLock()
                try:
                    if current_command == '1':
                        create_disaster_area(sim, config)
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

                current_command = None

            # ─── drone movement from WASD/QE
            moves = movement_manager.get_moves()
            rots  = movement_manager.get_rotates()
            if moves or rots:
                sim.acquireLock()
                try:
                    for dx, dy, dz in moves:
                        pos = sim.getObjectPosition(target_handle, -1)
                        sim.setObjectPosition(
                            target_handle, -1,
                            [pos[0] + dx, pos[1] + dy, pos[2] + dz]
                        )
                    for dr in rots:
                        ori = sim.getObjectOrientation(target_handle, -1)
                        sim.setObjectOrientation(
                            target_handle, -1,
                            [ori[0], ori[1], ori[2] + dr]
                        )
                finally:
                    sim.releaseLock()

            # ─── render & step
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
