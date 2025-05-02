import math
from Utils.physics_utils import set_collision_properties

def setup_rgbd_camera(sim, config):
    """
    Creates and attaches two Vision Sensors (RGB + Depth) to the drone,
    and links them to floating views.
    Returns both camera handles and floating view handles.
    """
    print("[Camera] Creating combined RGB/depth sensors...")

    parent_handle = sim.getObject('/Quadcopter')
    target_handle = sim.getObject('/target')

    # Disable collision using our centralized function
    set_collision_properties(sim, target_handle, enable_collision=False)

    # (Optional) Also hide from depth buffer:
    sim.setBoolProperty(target_handle, "depthInvisible", True)

    # Vision Sensor parameters
    options = 1 | 2  # bit 0 = explicitHandling, bit 1 = perspective projection
    intParams = [512, 512, 0, 0]

    view_angle = math.radians(80.0)
    floatParams = [
        0.1, 10.0, view_angle,  # near clip, far clip, view angle
        0.0, 0.0, 0.0,          # sensorSizeX, reserved, reserved
        0.5, 0.5, 0.5,          # null-pixel RGB
        0.0, 0.0                # reserved, reserved
    ]

    # ─── Create Main RGB Sensor ───
    cam_rgb = sim.createVisionSensor(options, intParams, floatParams)
    sim.setObjectAlias(cam_rgb, "DroneSensorRGB")
    sim.setObjectParent(cam_rgb, parent_handle, False)
    sim.setObjectPosition(cam_rgb, parent_handle, [-0.1, 0.0, 0.0])
    sim.setObjectOrientation(cam_rgb, parent_handle, [
        math.radians(0),
        math.radians(-90),
        math.radians(-90)
    ])

    # ─── Create Floating Views ───
    floating_view_rgb = sim.floatingViewAdd(0.75, 0.2, 1.0, 1.0, 0)
    sim.adjustView(floating_view_rgb, cam_rgb, 0)

    # ─── Hide the target if needed ───
    if not config.get('verbose', False):
        layer = sim.getProperty(target_handle, "layer")
        print(f"[RGBCameraSetup] Hiding target (layer {layer}).")
    else:
        print("[RGBCameraSetup] Target remains visible.")

    print("[RGBCameraSetup] Sensors created and linked to floating views.")

    return cam_rgb, floating_view_rgb
