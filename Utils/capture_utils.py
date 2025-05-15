# Utils/capture_utils.py

import numpy as np
import math
from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger

SC = SimConnection.get_instance()
logger = get_logger()

def capture_depth(sensor_handle):
    """
    Capture and return depth image from a vision sensor.
    """
    try:
        SC.sim.handleVisionSensor(sensor_handle)
        raw_depth, (width, height) = SC.sim.getVisionSensorDepth(sensor_handle)
        depth_buffer = SC.sim.unpackFloatTable(raw_depth)
        depth_img = np.array(depth_buffer, dtype=np.float32).reshape((height, width))
        # Flip the image upside down
        depth_img = np.flipud(depth_img)
        logger.debug_at_level(3, "CaptureUtils", f"Captured depth image {width}x{height}")
        return depth_img
    except Exception as e:
        logger.error("CaptureUtils", f"Error capturing depth: {e}")
        return np.zeros((1, 1), dtype=np.float32)  # Return empty array on error

def capture_rgb(sensor_handle):
    """
    Capture and return RGB image from a vision sensor, flipped upside down.
    """
    try:
        SC.sim.handleVisionSensor(sensor_handle)
        raw_rgb, (width, height) = SC.sim.getVisionSensorImage(sensor_handle)
        rgb_buffer = SC.sim.unpackFloatTable(raw_rgb)
        rgb_img = np.array(rgb_buffer, dtype=np.float32).reshape((height, width, 3))
        # Flip the image upside down
        rgb_img = np.flipud(rgb_img)
        logger.debug_at_level(3, "CaptureUtils", f"Captured RGB image {width}x{height}")
        return rgb_img
    except Exception as e:
        logger.error("CaptureUtils", f"Error capturing RGB: {e}")
        return np.zeros((1, 1, 3), dtype=np.float32)  # Return empty array on error

def capture_pose():
    """
    Capture and return drone pose (position + orientation).
    """
    try:
        parent_handle = SC.sim.getObject('/Quadcopter')
        pos = SC.sim.getObjectPosition(parent_handle, -1)
        ori = SC.sim.getObjectOrientation(parent_handle, -1)
        pose = np.array([pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]], dtype=np.float32)
        logger.debug_at_level(3, "CaptureUtils", f"Captured pose: {pose}")
        return pose
    except Exception as e:
        logger.error("CaptureUtils", f"Error capturing pose: {e}")
        return np.zeros(6, dtype=np.float32)  # Return zeros on error

def capture_distance_to_victim():
    """
    Calculate the actual distance from the drone to the victim.
    """
    try:
        # Get handle to quadcopter
        quad_handle = SC.sim.getObject('/Quadcopter')
        
        # Check if victim exists
        try:
            victim_handle = SC.sim.getObject('/Victim')
        except Exception:
            # Victim doesn't exist, return -1 as invalid distance
            logger.debug_at_level(2, "CaptureUtils", "No victim in scene, skipping distance calculation")
            return -1.0
        
        # Get positions
        quad_pos = SC.sim.getObjectPosition(quad_handle, -1)
        victim_pos = SC.sim.getObjectPosition(victim_handle, -1)
        
        # Calculate Euclidean distance
        dx = quad_pos[0] - victim_pos[0]
        dy = quad_pos[1] - victim_pos[1]
        dz = quad_pos[2] - victim_pos[2]
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        logger.debug_at_level(2, "CaptureUtils", f"Distance to victim: {distance:.2f}m")
        return distance
    except Exception as e:
        logger.error("CaptureUtils", f"Error calculating distance to victim: {e}")
        return -1.0  # Fallback to -1.0 in case of error
