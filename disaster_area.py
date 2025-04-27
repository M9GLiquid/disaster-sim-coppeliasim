# disaster_area.py (Final Version: SOC + Tilt System)

import random
import math

FLOOR_THICKNESS = 0.5  # Thicker floor for realism

def create_floor(sim, area_size):
    size = [area_size, area_size, FLOOR_THICKNESS]
    floor = sim.createPrimitiveShape(sim.primitiveshape_cuboid, size, 0)

    sim.setBoolProperty(floor, "collidable", True)
    sim.setBoolProperty(floor, "respondable", True)
    sim.setBoolProperty(floor, "dynamic", False)

    sim.setObjectPosition(floor, -1, [0, 0, FLOOR_THICKNESS/2])
    sim.setObjectAlias(floor, "DisasterFloor")
    return floor

def create_log_shape(sim, trunk_len=None, trunk_rad=None):
    if trunk_len is None:
        trunk_len = random.uniform(2.5, 4.5)
    if trunk_rad is None:
        trunk_rad = random.uniform(0.09, 0.13)

    trunk = sim.createPrimitiveShape(
        sim.primitiveshape_cylinder,
        [trunk_rad * 2, trunk_rad * 2, trunk_len],
        0
    )

    sim.setShapeColor(trunk, None, sim.colorcomponent_ambient_diffuse, [0.4, 0.27, 0.14])
    sim.setBoolProperty(trunk, "collidable", True)
    sim.setBoolProperty(trunk, "respondable", False)

    return trunk, trunk_len

def place_fallen_tree(sim, trunk, position):
    x, y = position
    z = FLOOR_THICKNESS + random.uniform(0.05, 0.5)

    choice = random.random()
    if choice < 0.3:
        # Small tilt (10–20 degrees)
        roll = random.uniform(-math.radians(20), math.radians(20))
        pitch = random.uniform(-math.radians(20), math.radians(20))
    elif choice < 0.7:
        # High tilt (30–45 degrees)
        roll = random.uniform(-math.radians(45), math.radians(45))
        pitch = random.uniform(-math.radians(45), math.radians(45))
    else:
        # Fully lying down (70–90 degrees)
        roll = random.uniform(-math.radians(80), math.radians(80))
        pitch = random.uniform(-math.radians(80), math.radians(80))

    yaw = random.uniform(-math.pi, math.pi)

    sim.setObjectPosition(trunk, -1, [x, y, z])
    sim.setObjectOrientation(trunk, -1, [roll, pitch, yaw])

def place_standing_tree(sim, trunk, position, trunk_len):
    x, y = position
    z = FLOOR_THICKNESS + trunk_len / 2

    sim.setObjectPosition(trunk, -1, [x, y, z])
    sim.setObjectOrientation(trunk, -1, [0, 0, random.uniform(-math.pi, math.pi)])

def create_fallen_tree(sim, position):
    trunk, trunk_len = create_log_shape(sim)
    place_fallen_tree(sim, trunk, position)
    sim.setObjectAlias(trunk, f"FallenTree_{trunk}")
    return trunk

def create_standing_tree(sim, position):
    trunk, trunk_len = create_log_shape(sim)
    place_standing_tree(sim, trunk, position, trunk_len)
    sim.setObjectAlias(trunk, f"StandingTree_{trunk}")
    return trunk

def create_rock(sim, position, size):
    dims = [
        size * random.uniform(0.7, 1.2),
        size * random.uniform(0.7, 1.2),
        size * random.uniform(0.5, 1.0)
    ]
    rock = sim.createPrimitiveShape(sim.primitiveshape_spheroid, dims, 0)

    sim.setBoolProperty(rock, "collidable", True)
    sim.setBoolProperty(rock, "respondable", True)
    sim.setBoolProperty(rock, "dynamic", False)

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

def create_disaster_area(sim, config):
    handles = []
    group = sim.createDummy(0.01)
    sim.setObjectAlias(group, "DisasterGroup")
    handles.append(group)

    area_size = config['area_size']
    num_trees = config['num_trees']
    num_rocks = config['num_rocks']
    fraction_standing = config['fraction_standing']

    num_standing = int(num_trees * fraction_standing)
    num_fallen = num_trees - num_standing

    handles.append(create_floor(sim, area_size))

    # Create rocks
    for _ in range(num_rocks):
        pos = (
            random.uniform(-area_size/2, area_size/2),
            random.uniform(-area_size/2, area_size/2)
        )
        rock = create_rock(sim, pos, random.uniform(0.3, 0.7))
        handles.append(rock)

    # Create standing trees
    for _ in range(num_standing):
        pos = (
            random.uniform(-area_size/2, area_size/2),
            random.uniform(-area_size/2, area_size/2)
        )
        trunk = create_standing_tree(sim, pos)
        handles.append(trunk)

    # Create fallen trees
    for _ in range(num_fallen):
        pos = (
            random.uniform(-area_size/2, area_size/2),
            random.uniform(-area_size/2, area_size/2)
        )
        trunk = create_fallen_tree(sim, pos)
        handles.append(trunk)

    # Parent everything
    for h in handles[1:]:
        if isinstance(h, (list, tuple)):
            for sub_h in h:
                if sim.isHandleValid(sub_h):
                    sim.setObjectParent(sub_h, group, True)
        else:
            if sim.isHandleValid(h):
                sim.setObjectParent(h, group, True)

    print(f"[DisasterArea] Created {len(handles)-1} objects (floor, rocks, trees).")
    return handles
