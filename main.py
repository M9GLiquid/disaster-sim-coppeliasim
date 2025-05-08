# main.py

import time
import queue
from Managers.depth_dataset_collector    import DepthDatasetCollector
from Utils.scene_utils                   import setup_scene_event_handlers
from Utils.config_utils                  import get_default_config
from Sensors.rgbd_camera_setup           import setup_rgbd_camera
from Controls.drone_keyboard_mapper      import register_drone_keyboard_mapper
from Core.event_manager                  import EventManager
from Managers.keyboard_manager           import KeyboardManager
from Managers.menu_system                import MenuSystem
from Managers.Connections.sim_connection import SimConnection
from Controls.drone_control_manager      import DroneControlManager
from Utils.lock_utils                    import sim_lock
from Managers.scene_manager              import get_scene_manager
from Managers.camera_manager             import CameraManager


EM = EventManager.get_instance()
KeyboardManager.get_instance()
SC = SimConnection.get_instance()
# Initialize SceneManager early to ensure its event handlers are registered
SM = get_scene_manager()
# Initialize CameraManager to handle vision sensors
CM = CameraManager.get_instance()

def main():
    # Get singleton instances
    SC.connect()
    sim = SC.sim
    print("[Main] Simulation connected.")

    # Monitor quit event
    running = True
    def _on_app_quit(_):
        nonlocal running
        print("[Main] shutdown received, stopping simulation.")
        running = False
    EM.subscribe('simulation/shutdown', _on_app_quit)

    sim_command_queue = queue.Queue()

    sim.setStepping(True)
    config = get_default_config()
    
    # Register scene event handlers
    setup_scene_event_handlers()

    # Setup camera & data collection
    cam_rgb, floating_view_rgb = setup_rgbd_camera(config)
    # Register the vision sensor with the camera manager
    CM.register_sensor(cam_rgb)
    
    depth_collector = DepthDatasetCollector(
        cam_rgb,
        base_folder="data/depth_dataset",
        batch_size=config.get("batch_size", 100),
        save_every_n_frames=config.get("dataset_capture_frequency", 5),
        split_ratio=(0.8, 0.1, 0.1),
    )

    # Input & control setup
    register_drone_keyboard_mapper(config)
    DroneControlManager()
    
    # Create GUI menu
    MenuSystem(config, sim_command_queue)
    
    # Initialize time tracking for delta time calculation
    last_time = time.time()
    
    # Run the main loop - everything happens in this single thread
    while running:
        # Calculate delta time
        current_time = time.time()
        delta_time = current_time - last_time
        last_time = current_time
        
        # Process simulation step
        with sim_lock() as locked:
            if locked:
                
                # Process commands from queue
                while not sim_command_queue.empty():
                    fn, args, kwargs = sim_command_queue.get()
                    fn(*args, **kwargs)
                
                # No need to call update_progressive_scene_creation - the event system handles this
                # Vision sensors are now handled by CameraManager via events
                
                # Publish frame event with delta time
                EM.publish('simulation/frame', delta_time)
        
        # Step the simulation
        sim.step()
    
    # After GUI closes, perform shutdown
    # Let SimConnection handle all the shutdown steps
    SC.shutdown(
        depth_collector=depth_collector,
        floating_view_rgb=floating_view_rgb,
        camera_manager=CM
    )
    print("[Main] Shutdown complete.")

if __name__ == '__main__':
    main()
