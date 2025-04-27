import math

def setup_rgbd_camera(sim, config):
    """
    Creates and attaches a single Vision Sensor (RGB+Depth) to the drone.
    Returns the sensor handle.
    """
    print("[RGBCameraSetup] Creating combined RGB/depth sensor...")

    parent_handle = sim.getObject('/Quadcopter/base')
    target_handle = sim.getObject('/target')

    # bit 0=explicitHandling, bit 1=perspective
    options = 1 | 2
    intParams = [512, 512, 0, 0]

    view_angle = math.radians(80.0)
    floatParams = [
        0.1, 10.0, view_angle,   # near, far, FOV
        0.0, 0.0, 0.0,           # sensorSizeX, reserved, reserved
        0.5, 0.5, 0.5,           # null-pixel RGB
        0.0, 0.0                 # reserved, reserved
    ]

    cam = sim.createVisionSensor(options, intParams, floatParams)
    sim.setObjectAlias(cam, "DroneSensor")
    sim.setObjectParent(cam, parent_handle, False)
    sim.setObjectPosition(cam, parent_handle, [0.0, 0.08, 0.1])
    sim.setObjectOrientation(cam, parent_handle, [math.radians(-90), 0.0, 0.0])

    if not config.get('verbose', False):
        layer = sim.getProperty(target_handle, "layer")
        print(f"[RGBCameraSetup] Hiding target (layer {layer}).")
    else:
        print("[RGBCameraSetup] Target remains visible.")

    print("[RGBCameraSetup] Sensor created and attached.")
    return cam
