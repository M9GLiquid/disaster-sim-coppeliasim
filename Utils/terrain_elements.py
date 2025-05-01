import math
import random

FLOOR_THICKNESS = 0.5

def create_floor(sim, area_size):
    size = [area_size, area_size, FLOOR_THICKNESS]
    floor = sim.createPrimitiveShape(sim.primitiveshape_cuboid, size, 0)
    sim.setBoolProperty(floor, "collidable", True)
    sim.setBoolProperty(floor, "respondable", True)
    sim.setBoolProperty(floor, "dynamic", False)
    sim.setShapeColor(floor, None, sim.colorcomponent_ambient_diffuse, [0.2, 0.5, 0.2])  # green
    sim.setObjectPosition(floor, -1, [0, 0, FLOOR_THICKNESS/2])
    sim.setObjectAlias(floor, "DisasterFloor")
    return floor

import math
import random

FLOOR_THICKNESS = 0.5

def create_tree(sim, position, fallen=True, trunk_len=None, tilt_angle=0.0):
    """
    - fallen=True  → small broken log (0.5–1.0m) with 60/30/10° tilt distribution
    - fallen=False → stump (0.2–0.5m) or full tree (2.5–4.5m)
                     with 50% vertical, 30% lean 5–15°, 20% lean 15–30°
    """
    # 1) choose trunk length if not given
    if trunk_len is None:
        if fallen:
            trunk_len = random.uniform(0.5, 1.0)
        else:
            trunk_len = (random.uniform(0.2, 0.5)
                         if random.random() < 0.1
                         else random.uniform(2.5, 4.5))

    # 2) create cylinder
    trunk_rad = random.uniform(0.08, 0.12)
    trunk = sim.createPrimitiveShape(
        sim.primitiveshape_cylinder,
        [trunk_rad*2, trunk_rad*2, trunk_len],
        0
    )
    sim.setShapeColor( trunk, None, sim.colorcomponent_ambient_diffuse, [0.4,0.27,0.14] )
    sim.setBoolProperty(trunk, "collidable", True)
    sim.setBoolProperty(trunk, "respondable", False)

    # 3) position
    x, y = position
    z = FLOOR_THICKNESS + (trunk_rad if fallen else trunk_len/2)

    # 4) compute tilt
    r = random.random()
    if fallen:
        if r < 0.45:
            deg = 90
        elif r < 0.75:
            deg = 80
        else:
            deg = 45
    else:
        if r < 0.4:
            deg = 0
        elif r < 0.75:
            deg = random.uniform(5.0, 15.0)
        else:
            deg = random.uniform(15.0, 30.0)

    tilt_rad = math.radians(deg)
    if fallen or deg > 0:
        # randomize direction of tilt in roll/pitch
        roll  = tilt_rad if random.random() < 0.5 else -tilt_rad
        pitch = tilt_rad if random.random() < 0.5 else -tilt_rad
    else:
        roll = pitch = 0.0

    yaw = random.uniform(-math.pi, math.pi)

    sim.setObjectPosition(trunk, -1, [x, y, z])
    sim.setObjectOrientation(trunk, -1, [roll, pitch, yaw])
    sim.setObjectAlias(trunk, f"{'Fallen' if fallen else 'Standing'}Tree_{trunk}")
    return trunk


def create_rock(sim, position, size):
    dims = [size, size, size * 0.8]
    rock = sim.createPrimitiveShape(sim.primitiveshape_spheroid, dims, 0)
    sim.setBoolProperty(rock, "collidable", True)
    sim.setBoolProperty(rock, "respondable", True)
    sim.setBoolProperty(rock, "dynamic", False)
    sim.setShapeColor(rock, None, sim.colorcomponent_ambient_diffuse, [0.5, 0.5, 0.5])  # gray
    sim.setObjectPosition(rock, -1, [
        position[0],
        position[1],
        FLOOR_THICKNESS + dims[2]/2
    ])
    sim.setObjectOrientation(rock, -1, [
        random.uniform(0, math.pi/6),
        random.uniform(0, math.pi/6),
        random.uniform(-math.pi, math.pi)
    ])
    sim.setObjectAlias(rock, f"Rock_{rock}")
    return rock

def create_victim(sim, position=(0, 0), size=(0.3, 0.1, 1.2)):
    """
    Create a thin red rectangular box representing the victim.
    Default height: 1.2 m standing figure.
    """
    # create a disc of 0.5m diameter and 0.5m thickness instead of cuboid
    dims = [0.5, 0.5, 0.5]
    victim = sim.createPrimitiveShape(sim.primitiveshape_cylinder, dims, 0)
    sim.setObjectAlias(victim, "Victim")
    sim.setBoolProperty(victim, "collidable", False)
    sim.setBoolProperty(victim, "respondable", False)
    sim.setBoolProperty(victim, "dynamic", False)
    sim.setShapeColor(victim, None, sim.colorcomponent_ambient_diffuse, [1.0, 0.2, 0.2])  # red

    x, y = position
    z = FLOOR_THICKNESS + dims[2] / 2  # Center the disc vertically above ground
    sim.setObjectPosition(victim, -1, [x, y, z])
    sim.setObjectOrientation(victim, -1, [0, 0, 0])  # upright

    return victim
