# Utils/capture_utils.py

import numpy as np
import math

def capture_depth(sim, sensor_handle):
    """
    Capture and return depth image from a vision sensor.
    """
    sim.handleVisionSensor(sensor_handle)
    raw_depth, (width, height) = sim.getVisionSensorDepth(sensor_handle)
    depth_buffer = sim.unpackFloatTable(raw_depth)
    depth_img = np.array(depth_buffer, dtype=np.float32).reshape((height, width))
    return depth_img

def capture_pose(sim):
    """
    Capture and return drone pose (position + orientation).
    """
    parent_handle = sim.getObject('/Quadcopter')
    pos = sim.getObjectPosition(parent_handle, -1)
    ori = sim.getObjectOrientation(parent_handle, -1)
    return np.array([pos[0], pos[1], pos[2], ori[0], ori[1], ori[2]], dtype=np.float32)

def capture_distance_to_victim(sim):
    """
    Calculate the actual distance from the drone to the victim.
    """
    try:
        # Get handles to quadcopter and victim
        quad_handle = sim.getObject('/Quadcopter')
        victim_handle = sim.getObject('/Victim')
        
        # Get positions
        quad_pos = sim.getObjectPosition(quad_handle, -1)
        victim_pos = sim.getObjectPosition(victim_handle, -1)
        
        # Calculate Euclidean distance
        dx = quad_pos[0] - victim_pos[0]
        dy = quad_pos[1] - victim_pos[1]
        dz = quad_pos[2] - victim_pos[2]
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        return distance
    except Exception as e:
        print(f"[CaptureUtils] Error calculating distance to victim: {e}")
        return -1.0  # Fallback to -1.0 in case of error
