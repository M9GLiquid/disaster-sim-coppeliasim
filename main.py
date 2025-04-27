# main.py

import time

from disaster_area import create_disaster_area

from Utils.scene_utils      import clear_disaster_area, restart_disaster_area
from Utils.config_utils     import get_default_config, modify_config

from Controls.camera_setup       import setup_drone_camera
from Controls.camera_view        import CameraView

from Core.event_manager      import EventManager

from Controls.drone_keyboard_mapper import register_drone_keyboard_mapper

from Managers.typing_mode_manager    import TypingModeManager
from Managers.menu_manager           import MenuManager
from Managers.keyboard_manager       import KeyboardManager
from Managers.movement_manager   import MovementManager

from Managers.Connections.sim_connection import connect_to_simulation, shutdown_simulation


def main():
    event_manager    = EventManager()
    sim              = connect_to_simulation()
    print("[Main] Simulation connected.")

    # step-by-step mode
    sim.setStepping(True)

    # load default parameters
    config = get_default_config()

    # setup camera on the drone
    cam_handle, target_handle = setup_drone_camera(sim, config)
    camera_view               = CameraView(sim, cam_handle)
    camera_view.start()

    # input & event systems
    keyboard_manager = KeyboardManager(event_manager)
    typing_manager   = TypingModeManager(event_manager, keyboard_manager)
    menu_manager     = MenuManager()
    movement_manager = MovementManager(event_manager)

    # map WASD/QE → move/rotate events
    register_drone_keyboard_mapper(event_manager, keyboard_manager)

    # chat-mode state
    menu_active     = False
    current_command = None
    def on_command_ready(cmd):
        nonlocal current_command
        current_command = cmd
    event_manager.subscribe('typing/command_ready', on_command_ready)


    try:
        while True:
            # ─── Entering chat? show menu only once ───
            if keyboard_manager.in_typing_mode() and not menu_active:
                menu_manager.show_menu()
                typing_manager.start_typing()
                menu_active = True

            # ─── Command entered? dispatch ───
            if current_command:
                sim.acquireLock()
                try:
                    if current_command == '1':
                        create_disaster_area(sim, config)
                    elif current_command == '3':
                        restart_disaster_area(sim, config)
                    elif current_command == '4':
                        clear_disaster_area(sim)
                    elif current_command == '9':
                        modify_config(config)
                    elif current_command == 'q':
                        print("[Main] Quit requested.")
                        break
                    else:
                        print("[Main] Unknown command.")
                finally:
                    sim.releaseLock()

                keyboard_manager.finish_typing(current_command)
                current_command = None
                menu_active     = False   # allow next menu show

            # ─── Drone movement events ───
            moves = movement_manager.get_moves()
            rots  = movement_manager.get_rotates()
            if moves or rots:
                sim.acquireLock()
                try:
                    # apply translations
                    for dx, dy, dz in moves:
                        pos = sim.getObjectPosition(target_handle, -1)
                        sim.setObjectPosition(
                            target_handle, -1,
                            [pos[0] + dx, pos[1] + dy, pos[2] + dz]
                        )
                    # apply yaw rotations
                    for dr in rots:
                        ori = sim.getObjectOrientation(target_handle, -1)
                        sim.setObjectOrientation(
                            target_handle, -1,
                            [ori[0], ori[1], ori[2] + dr]
                        )
                finally:
                    sim.releaseLock()

            # ─── Update camera & step ───
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
