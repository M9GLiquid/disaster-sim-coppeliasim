# Controls/camera_setup.py
import math

import numpy as np

def setup_drone_camera(sim, config):
    """
    Creates and attaches a Vision Sensor (RGB + Depth) to the drone,
    and sets visibility of the target based on config.
    """
    print("[CameraSetup] Creating Vision Sensor attached to drone...")

    parent_handle = sim.getObject('/Quadcopter/base')
    target_handle = sim.getObject('/target')

    options = 1 | 2  # explicitly handled + perspective mode

    intParams = [
        256, 256, 0, 0  # resolution X, Y and reserved
    ]

    near_plane = 0.1
    far_plane = 10.0
    fov_deg = 80.0
    view_angle = fov_deg * math.pi / 180.0

    floatParams = [
        near_plane, far_plane, view_angle, 0.0, 0.0, 0.0,
        0.5, 0.5, 0.5, 0.0, 0.0
    ]

    cam_handle = sim.createVisionSensor(
        options, intParams, floatParams
    )

    sim.setObjectAlias(cam_handle, "DroneCamera")
    sim.setObjectParent(cam_handle, parent_handle, False)

    sim.setObjectPosition(cam_handle, parent_handle, [0.0, 0.08, 0.1])
    sim.setObjectOrientation(cam_handle, parent_handle, [math.radians(-90), 0, 0])


    # 🔥 Hide target if config says so
    if not config.get('verbose', False):
        # Read the layer
        layer = sim.getProperty(target_handle, "layer")

        print(f"Target is currently in layer: {layer}")

        print("[CameraSetup] Target set to HIDDEN (verbose=False).")
    else:
        print("[CameraSetup] Target remains VISIBLE (verbose=True).")

    print("[CameraSetup] Vision Sensor created and attached.")
    return cam_handle, target_handle
