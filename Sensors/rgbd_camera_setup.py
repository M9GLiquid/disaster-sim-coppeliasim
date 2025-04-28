import math

def setup_rgbd_camera(sim, config):
    """
    Creates and attaches two Vision Sensors (RGB + Depth) to the drone,
    and links them to floating views.
    Returns both camera handles and floating view handles.
    """
    print("[RGBCameraSetup] Creating combined RGB/depth sensors...")

    parent_handle = sim.getObject('/Quadcopter/base')
    target_handle = sim.getObject('/target')
    target_handle = sim.getObject('/target')

    # Fully disable physics interaction:
    sim.setBoolProperty(target_handle, "collidable", False)
    sim.setBoolProperty(target_handle, "respondable", False)

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

    # ─── Clone to create Depth Sensor ───
    cam_depth = sim.copyPasteObjects([cam_rgb], 0)[0]
    sim.setObjectAlias(cam_depth, "DroneSensorDepth")
    sim.setObjectParent(cam_depth, parent_handle, False)
    sim.setObjectPosition(cam_depth, parent_handle, [-0.1, 0.0, 0.0])
    sim.setObjectOrientation(cam_depth, parent_handle, [
        math.radians(0),
        math.radians(-90),
        math.radians(-90)
    ])

    # ─── Switch Depth Sensor to Depth Visualization ───
    sim.setIntProperty(cam_depth, "renderMode", 1)  # 0 = RGB, 1 = Depth Buffer

    # ─── Create Floating Views ───
    floating_view_rgb = sim.floatingViewAdd(0.75, 0.2, 0.2, 0.2, 0)
    sim.adjustView(floating_view_rgb, cam_rgb, 0)

    floating_view_depth = sim.floatingViewAdd(0.95, 0.2, 0.2, 0.2, 0)
    sim.adjustView(floating_view_depth, cam_depth, 0)

    # ─── Hide the target if needed ───
    if not config.get('verbose', False):
        layer = sim.getProperty(target_handle, "layer")
        print(f"[RGBCameraSetup] Hiding target (layer {layer}).")
    else:
        print("[RGBCameraSetup] Target remains visible.")

    print("[RGBCameraSetup] Sensors created and linked to floating views.")

    return cam_rgb, cam_depth, floating_view_rgb, floating_view_depth
