import math

from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

SC = SimConnection.get_instance()
logger = get_logger()

def setup_rgbd_camera(config):
    logger.info("Camera", "Creating combined RGB/depth sensors...")

    parent_handle = SC.sim.getObject('/Quadcopter')
    target_handle = SC.sim.getObject('/target')

    SC.sim.setBoolProperty(target_handle, "collidable", True)
    SC.sim.setBoolProperty(target_handle, "respondable", False)

    # (Optional) Also hide from depth buffer:
    SC.sim.setBoolProperty(target_handle, "depthInvisible", True)

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
    cam_rgb = SC.sim.createVisionSensor(options, intParams, floatParams)
    SC.sim.setObjectAlias(cam_rgb, "DroneSensorRGB")
    SC.sim.setObjectParent(cam_rgb, parent_handle, False)
    SC.sim.setObjectPosition(cam_rgb, parent_handle, [-0.1, 0.0, 0.0])
    SC.sim.setObjectOrientation(cam_rgb, parent_handle, [
        math.radians(0),
        math.radians(-90),
        math.radians(-90)
    ])

    # ─── Create Floating Views ───
    floating_view_rgb = SC.sim.floatingViewAdd(0.75, 0.2, 1.0, 1.0, 0)
    SC.sim.adjustView(floating_view_rgb, cam_rgb, 0)

    # ─── Hide the target if needed ───
    if not config.get('verbose', False):
        layer = SC.sim.getProperty(target_handle, "layer")
        logger.debug_at_level(DEBUG_L1, "RGBCameraSetup", f"Hiding target (layer {layer}).")
    else:
        logger.debug_at_level(DEBUG_L1, "RGBCameraSetup", "Target remains visible.")

    logger.info("RGBCameraSetup", "Sensors created and linked to floating views.")

    return cam_rgb, floating_view_rgb
