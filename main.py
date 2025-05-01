# main.py

import time
import queue
from Managers.depth_dataset_collector    import DepthDatasetCollector
from Utils.scene_utils                   import clear_disaster_area, restart_disaster_area
from Utils.config_utils                  import get_default_config
from Sensors.rgbd_camera_setup           import setup_rgbd_camera
from Controls.drone_keyboard_mapper      import register_drone_keyboard_mapper
from Core.event_manager                  import EventManager
from Managers.keyboard_manager           import KeyboardManager
from Managers.menu_system                import MenuSystem
from Managers.Connections.sim_connection import connect_to_simulation, shutdown_simulation
from Controls.drone_control_manager      import DroneControlManager
from Utils.lock_utils                    import sim_lock
from Utils.sim_utils                     import safe_step

def main():
    event_manager = EventManager()
    sim = connect_to_simulation()
    print("[Main] Simulation connected.")

    # monitor quit event
    running = {'flag': True}
    def _on_app_quit(_):
        print("[Main] app/quit received, stopping simulation thread.")
        running['flag'] = False
    event_manager.subscribe('app/quit', _on_app_quit)

    sim_command_queue = queue.Queue()

    sim.setStepping(True)
    config = get_default_config()

    # Setup camera & data collection
    cam_rgb, floating_view_rgb = setup_rgbd_camera(sim, config)
    depth_collector = DepthDatasetCollector(
        sim, cam_rgb,
        base_folder="data/depth_dataset",
        batch_size=100,
        save_every_n_frames=10,
        split_ratio=(0.98, 0.01, 0.01),
        event_manager=event_manager
    )

    # Input & control setup
    keyboard_manager = KeyboardManager(event_manager)
    register_drone_keyboard_mapper(event_manager, keyboard_manager, config)
    drone_control_manager = DroneControlManager(event_manager, sim)

    # Start simulation loop in background thread
    import threading
    def sim_loop():
        timestep = 0.05
        while running['flag']:
            with sim_lock(sim) as locked:
                if locked:
                    drone_control_manager.update(timestep)
                    while not sim_command_queue.empty():
                        fn, args, kwargs = sim_command_queue.get()
                        fn(sim, *args, **kwargs)
                        if fn.__name__ in ("create_scene", "restart_disaster_area"):
                            event_manager.publish("scene/created", None)
                    sim.handleVisionSensor(cam_rgb)
                    depth_collector.capture()
            safe_step(sim) 
            time.sleep(timestep)
    threading.Thread(target=sim_loop, daemon=True).start()

    # Launch GUI menu (blocks until quit)
    menu_system = MenuSystem(event_manager, sim, config, sim_command_queue)
    menu_system.run()
    # After GUI closes, perform shutdown
    shutdown_simulation(keyboard_manager, depth_collector, floating_view_rgb, sim)
    print("[Main] Shutdown complete.")

if __name__ == '__main__':
    main()
