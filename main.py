# main.py

import time
import queue
import argparse
import os
import logging
from Managers.depth_dataset_collector    import DepthDatasetCollector
from Utils.scene_utils                   import setup_scene_event_handlers
from Utils.config_utils                  import get_default_config
from Utils.log_utils                     import get_logger, LOG_LEVEL_DEBUG, LOG_LEVEL_INFO, DEBUG_L1, DEBUG_L2, DEBUG_L3
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


# Get the logger first
logger = get_logger()

# Then initialize all the other singleton instances
EM = EventManager.get_instance()
KeyboardManager.get_instance()
SC = SimConnection.get_instance()
# Initialize SceneManager early to ensure its event handlers are registered
SM = get_scene_manager()
# Initialize CameraManager to handle vision sensors
CM = CameraManager.get_instance()

def parse_arguments():
    parser = argparse.ArgumentParser(description='AI for Robotics - Drone Search and Rescue Simulation')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--log-file', action='store_true', help='Enable logging to file')
    parser.add_argument('--log-dir', type=str, default='logs', help='Directory to store log files')
    parser.add_argument('--log-level', type=str, choices=['debug', 'info', 'warning', 'error', 'critical'],
                        default='info', help='Minimum log level to display')
    parser.add_argument('--debug-level', type=int, choices=[1, 2, 3], default=1,
                       help='Debug verbosity level (1=basic, 2=medium, 3=detailed)')
    parser.add_argument('--no-color', action='store_true', help='Disable colored console output')
    return parser.parse_args()

def main():
    # Parse command-line arguments
    args = parse_arguments()
    
    # Configure logger based on arguments
    log_level_map = {
        'debug': LOG_LEVEL_DEBUG,
        'info': LOG_LEVEL_INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    
    # Map debug level argument to constants
    debug_level_map = {
        1: DEBUG_L1,
        2: DEBUG_L2,
        3: DEBUG_L3
    }
    
    # Configure the main logger
    logger.configure(
        verbose=args.verbose,
        console_level=log_level_map[args.log_level],
        log_directory=args.log_dir,
        debug_level=debug_level_map[args.debug_level],
        colored_output=not args.no_color
    )
    
    # Configure file logging if requested
    if args.log_file:
        logger.configure_file_logging(enabled=True, level=LOG_LEVEL_DEBUG)
    
    # Log startup information
    logger.info("Main", "Starting Drone Search and Rescue Simulation")
    
    # Get singleton instances
    SC.connect()
    sim = SC.sim
    logger.info("Main", "Simulation connected")

    # Monitor quit event
    running = True
    def _on_app_quit(_):
        nonlocal running
        logger.info("Main", "Shutdown received, stopping simulation")
        running = False
    EM.subscribe('simulation/shutdown', _on_app_quit)

    sim_command_queue = queue.Queue()

    sim.setStepping(True)
    
    # Get default config and apply command-line arguments
    config = get_default_config()
    
    # Update config based on command-line arguments
    # Explicitly set verbose based on command-line argument, overriding the default setting
    config['verbose'] = args.verbose
    config['debug_level'] = args.debug_level
    config['colored_output'] = not args.no_color
    if args.verbose:
        logger.info("Main", f"Verbose mode enabled with debug level {args.debug_level}")
    
    # Register scene event handlers
    setup_scene_event_handlers()

    # Setup camera & data collection
    try:
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
    except Exception as e:
        logger.error("Main", f"Error setting up camera and data collection: {str(e)}")
        return

    # Input & control setup
    register_drone_keyboard_mapper(config)
    DroneControlManager()
    
    # Create GUI menu
    MenuSystem(config, sim_command_queue)
    
    # Initialize time tracking for delta time calculation
    last_time = time.time()
    logger.info("Main", "Initialization complete, entering main loop")
    
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
    logger.info("Main", "Main loop exited, beginning shutdown sequence")
    
    # Shut down the logger
    logger.verbose_log("Main", "Shutting down logger", "info")
    
    # Let SimConnection handle all the shutdown steps
    logger.info("Main", "Shutting down simulation")
    SC.shutdown(
        depth_collector=depth_collector,
        floating_view_rgb=floating_view_rgb,
        camera_manager=CM
    )
    
    # Final logger shutdown
    logger.info("Main", "Shutdown complete")
    logger.shutdown()

if __name__ == '__main__':
    main()
