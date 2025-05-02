# Utils/capture_utils.py

import numpy as np

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

def capture_dummy_distance():
    """
    Placeholder for distance to goal. Currently returns dummy value.
    """
    return -1.0  # Replace with real victim distance later
