# main.py

import time

from disaster_area                     import create_disaster_area
from Utils.scene_utils                 import clear_disaster_area, restart_disaster_area
from Utils.config_utils                import get_default_config

from Sensors.rgbd_camera_setup             import setup_rgbd_camera
from Sensors.single_camera_dual_renderer    import SingleCameraDualViewRenderer

from Core.event_manager                import EventManager
from Controls.drone_keyboard_mapper    import register_drone_keyboard_mapper
from Managers.movement_manager         import MovementManager

from Managers.keyboard_manager         import KeyboardManager
from Managers.menu_system              import MenuSystem
from Managers.Connections.sim_connection import connect_to_simulation, shutdown_simulation

def main():
    # ─── Initialization ───
    event_manager    = EventManager()
    sim              = connect_to_simulation()
    print("[Main] Simulation connected.")

    sim.setStepping(True)
    config = get_default_config()

    # ─── Single RGB-D Sensor Setup ───
    sensor_handle = setup_rgbd_camera(sim, config)
    renderer      = SingleCameraDualViewRenderer(sim, sensor_handle)
    renderer.start()

    # ─── Movement target for drone control ───
    target_handle = sim.getObject('/target')

    # ─── Input & Control Systems ───
    keyboard_manager = KeyboardManager(event_manager)
    menu_system      = MenuSystem(event_manager, keyboard_manager, config)
    movement_manager = MovementManager(event_manager)
    register_drone_keyboard_mapper(event_manager, keyboard_manager)

    # ─── Menu selection handler ───
    current_command = None
    def on_menu_selected(cmd):
        nonlocal current_command
        current_command = cmd
    event_manager.subscribe('menu/selected', on_menu_selected)

    try:
        while True:
            # ─── Dispatch menu commands ───
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

                # re-open chat for next command (unless quitting)
                if current_command != 'q':
                    menu_system.open_chat()
                current_command = None

            # ─── Drone movement (W/A/S/D/Q/E) ───
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

            # ─── Update the combined RGB-D view & step ───
            renderer.update()
            for _ in range(3):
                sim.step()
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt received. Exiting...")

    finally:
        # ensure renderer closes its window
        shutdown_simulation(keyboard_manager, renderer, sim)
        print("[Main] Shutdown complete.")

if __name__ == '__main__':
    main()
