# Controls/camera_setup.py
import math

def setup_drone_camera(sim):
    """
    Creates and attaches a Vision Sensor (RGB + Depth) to the drone.
    """
    print("[CameraSetup] Creating Vision Sensor attached to drone...")

    parent_handle = sim.getObject('/Quadcopter/base')
    options = 1 | 2  # explicitly handled + perspective mode

    intParams = [
        256,  # resolution X
        256,  # resolution Y
        0,    # reserved
        0     # reserved
    ]

    near_plane = 0.1
    far_plane = 10.0
    fov_deg = 80.0  # field of view
    view_angle = fov_deg * math.pi / 180.0

    floatParams = [
        near_plane,
        far_plane,
        view_angle,
        0.0,    # sensor size x (for ortho mode, 0.0 if perspective)
        0.0,    # reserved
        0.0,    # reserved
        0.5,    # null pixel R (background color)
        0.5,    # null pixel G
        0.5,    # null pixel B
        0.0,    # reserved
        0.0     # reserved
    ]

    cam_handle = sim.createVisionSensor(
        options,
        intParams,
        floatParams
    )

    sim.setObjectAlias(cam_handle, "DroneCamera")
    sim.setObjectParent(cam_handle, parent_handle, False)

    # After setting parent
    sim.setObjectPosition(cam_handle, parent_handle, [0.1, 0.1, 0.05])

    # Important: Rotate camera to face forward
    sim.setObjectOrientation(cam_handle, parent_handle, [math.radians(-90), 0, 0])

    print("[CameraSetup] Vision Sensor created and attached!")
    return cam_handle
