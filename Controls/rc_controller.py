# Controls/rc_controller.py

import pygame
import time
import multiprocessing
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

EM = EventManager.get_instance()
logger = get_logger()

def rc_loop(config, conn):
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        logger.warning("RC", "No joystick detected.")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    logger.info("RC", f"Using: {joystick.get_name()}")

    move_step = config.get('move_step', 0.2)
    rotate_step = config.get('rotate_step_deg', 15.0)
    sensitivity = config.get('rc_sensitivity', 10.0)
    deadzone_threshold = config.get('rc_deadzone', 0.1)
    yaw_sensitivity = config.get('rc_yaw_sensitivity', 0.15)  # Default 15%
    
    # Default mappings (can be overridden by config)
    mappings = {
        "pitch": {"axis": 1, "invert": False},
        "roll": {"axis": 0, "invert": False},
        "throttle": {"axis": 2, "invert": False},
        "yaw": {"axis": 3, "invert": False}
    }
    
    # Load custom mappings if available
    if "rc_mappings" in config and config["rc_mappings"]:
        logger.info("RC", f"Using custom mappings: {config['rc_mappings']}")
        mappings.update(config["rc_mappings"])
    else:
        logger.info("RC", "Using default controller mappings")

    # Optimized deadzone function - more efficient by avoiding redundant calculations
    def deadzone(val, threshold=deadzone_threshold):
        if abs(val) <= threshold:
            return 0.0
        # Scale the value to maintain smooth range after deadzone
        scaled_val = (val - (threshold if val > 0 else -threshold)) / (1.0 - threshold)
        return scaled_val

    # Log the initial controller configuration
    logger.info("RC", f"Controller started with sensitivity: {sensitivity}, deadzone: {deadzone_threshold}, yaw sensitivity: {yaw_sensitivity}")
    logger.info("RC", f"Mappings: pitch={mappings['pitch']}, roll={mappings['roll']}, throttle={mappings['throttle']}, yaw={mappings['yaw']}")

    # Variables to track last sent values to minimize unnecessary updates
    last_sideward = last_forward = last_upward = last_yaw_rate = 0.0
    
    # Throttle update rate - controls how many position updates to skip
    update_counter = 0
    update_every = 1 # Only send every nth update
    
    # Timestamp tracking for adaptive timing
    last_time = time.time()
    frame_time_avg = 0.01 # Initialize with a reasonable value

    while True:
        try:
            # Check for config updates from the pipe
            if conn.poll():
                data = conn.recv()
                if isinstance(data, dict):
                    if 'rc_sensitivity' in data:
                        sensitivity = data['rc_sensitivity']
                        logger.info("RC", f"Sensitivity updated to: {sensitivity}")
                    if 'rc_deadzone' in data:
                        deadzone_threshold = data['rc_deadzone']
                        logger.info("RC", f"Deadzone updated to: {deadzone_threshold}")
                    if 'rc_yaw_sensitivity' in data:
                        yaw_sensitivity = data['rc_yaw_sensitivity']
                        logger.info("RC", f"Yaw sensitivity updated to: {yaw_sensitivity}")
                    if 'rc_mappings' in data and data['rc_mappings']:
                        mappings.update(data['rc_mappings'])
                        logger.info("RC", f"Mappings updated: {mappings}")
                    continue

            # Start timing this frame's processing
            frame_start = time.time()
            pygame.event.pump()
            
            # Get axis values based on mappings
            pitch_map = mappings.get('pitch', {"axis": 1, "invert": True})
            roll_map = mappings.get('roll', {"axis": 0, "invert": False})
            throttle_map = mappings.get('throttle', {"axis": 2, "invert": False})
            yaw_map = mappings.get('yaw', {"axis": 3, "invert": False})
            
            # Make sure axis values are valid
            num_axes = joystick.get_numaxes()
            
            # Read pitch
            if pitch_map["axis"] < num_axes:
                pitch = joystick.get_axis(pitch_map["axis"])
                if pitch_map.get("invert", False):
                    pitch = -pitch
            else:
                pitch = 0.0
                
            # Read roll
            if roll_map["axis"] < num_axes:
                roll = joystick.get_axis(roll_map["axis"])
                if roll_map.get("invert", False):
                    roll = -roll
            else:
                roll = 0.0
                
            # Read throttle
            if throttle_map["axis"] < num_axes:
                throttle = joystick.get_axis(throttle_map["axis"])
                if throttle_map.get("invert", False):
                    throttle = -throttle
            else:
                throttle = 0.0
                
            # Read yaw
            if yaw_map["axis"] < num_axes:
                yaw = joystick.get_axis(yaw_map["axis"])
                if yaw_map.get("invert", False):
                    yaw = -yaw
            else:
                yaw = 0.0

            # Apply deadzone and sensitivity
            forward = deadzone(-pitch) * move_step * sensitivity
            sideward = deadzone(roll) * move_step * sensitivity
            upward = deadzone(throttle) * move_step * sensitivity
            yaw_rate = deadzone(-yaw) * rotate_step * yaw_sensitivity

            # Only send updates when values change or on regular intervals
            update_counter += 1
            should_update = (
                update_counter >= update_every or
                abs(forward - last_forward) > 0.01 or
                abs(sideward - last_sideward) > 0.01 or
                abs(upward - last_upward) > 0.01 or
                abs(yaw_rate - last_yaw_rate) > 0.01
            )
            
            if should_update:
                conn.send((sideward, forward, upward, yaw_rate))
                last_sideward, last_forward, last_upward, last_yaw_rate = sideward, forward, upward, yaw_rate
                update_counter = 0

            # Debug output at high verbosity level
            logger.debug_at_level(DEBUG_L3, "RC", f"pitch={pitch:.2f}, roll={roll:.2f}, throttle={throttle:.2f}, yaw={yaw:.2f}")

            # Calculate frame processing time
            frame_end = time.time()
            frame_time = frame_end - frame_start
            
            # Use a moving average for frame time to make sleep times more stable
            frame_time_avg = 0.9 * frame_time_avg + 0.1 * frame_time
            
            # Dynamic sleep time: shorter when frame time is longer
            # This makes controller more responsive under system load
            sleep_time = max(0.01, 0.03 - frame_time_avg)  # Minimum 10ms, target 30ms total cycle time
            time.sleep(sleep_time)

        except Exception as e:
            logger.error("RC", f"Error reading axes: {e}")
            time.sleep(0.1)  # Add a small delay before retrying
            continue
