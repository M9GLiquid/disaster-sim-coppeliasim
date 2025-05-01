import random
import math
import traceback
from Utils.terrain_elements import create_floor, create_tree, create_rock, create_victim

# ─────────────────────────────────────────────────────────────────────
# Object Registry: Add new elements here to include in scene creation
# Each entry specifies the function name as a string
# ─────────────────────────────────────────────────────────────────────
OBJECT_CREATORS = [
    {"name": "Victim",        "description": "Victim in danger zone", "func": "create_scene_victim"},
    {"name": "Floor",         "description": "Base ground",           "func": "create_scene_floor"},
    {"name": "Rocks",         "description": "Scattered rocks",       "func": "create_scene_rocks"},
    {"name": "StandingTrees", "description": "Vertical trees",        "func": "create_scene_standing_trees"},
    {"name": "FallenTrees",   "description": "Broken logs",           "func": "create_scene_fallen_trees"},
]
# ─────────────────────────────────────────────────────────────────────
# Victim position: Random within bounds, padded from edges
# ─────────────────────────────────────────────────────────────────────
def _sample_victim_pos(config):
    area = config["area_size"]
    margin = 1.0  # leave 1m margin from all borders
    return (
        random.uniform(-area / 2 + margin, area / 2 - margin),
        random.uniform(-area / 2 + margin, area / 2 - margin)
    )

# ─────────────────────────────────────────────────────────────────────
# Random position generator that avoids victim zone + clear zone
# ─────────────────────────────────────────────────────────────────────
def _make_pos_sampler(config, avoid_zone, avoid_radius):
    area = config["area_size"]
    clear_center = config.get("clear_zone_center", (0, 0))
    clear_radius = config.get("clear_zone_radius", 0)

    def random_pos():
        while True:
            x = random.uniform(-area / 2, area / 2)
            y = random.uniform(-area / 2, area / 2)

            dx1, dy1 = x - clear_center[0], y - clear_center[1]
            dx2, dy2 = x - avoid_zone[0], y - avoid_zone[1]

            if (dx1 * dx1 + dy1 * dy1 >= clear_radius * clear_radius and
                dx2 * dx2 + dy2 * dy2 >= avoid_radius * avoid_radius):
                return (x, y)
    return random_pos

# ─────────────────────────────────────────────────────────────────────
# Scene Creator: builds terrain based on config
# ─────────────────────────────────────────────────────────────────────
def create_scene(sim, config):
    handles = []
    group = sim.createDummy(0.01)
    sim.setObjectAlias(group, "DisasterGroup")
    handles.append(group)

    # Victim placed first
    victim_pos = _sample_victim_pos(config)
    victim_radius = 1.0  # 1m safe zone
    pos_sampler = _make_pos_sampler(config, victim_pos, victim_radius)

    # Create all registered objects
    for entry in OBJECT_CREATORS:
        func_name = entry["func"]
        if func_name in globals():
            creator_func = globals()[func_name]
            objects = creator_func(sim, config, pos_sampler, victim_pos)
            handles.extend(objects)
        else:
            print(f"[SceneManager] Function '{func_name}' not found.")

    # Parent everything under group
    for h in handles[1:]:
        if sim.isHandleValid(h):
            sim.setObjectParent(h, group, True)
            
        # ─── Move Quadcopter Out of Clear Zone ───
    try:
        quad_handle = sim.getObject('/Quadcopter')
        safe_z = 1.0  # Hover height
        sim.setObjectPosition(quad_handle, -1, [0, -config["area_size"]/2 + 1.0, safe_z])
        print("[SceneManager] Quadcopter repositioned outside obstacle area.")
    except Exception as e:
        print(f"[SceneManager] Warning: Could not reposition Quadcopter: {e}")

    # ─── Hide Target from Rendering and Depth ───
    try:
        target_handle = sim.getObject('/target')
        sim.setBoolProperty(target_handle, "collidable", False)
        sim.setBoolProperty(target_handle, "respondable", False)
        sim.setBoolProperty(target_handle, "depthInvisible", True)
        sim.setObjectInt32Param(target_handle, sim.objintparam_visibility_layer, 0)
        print("[SceneManager] Target object hidden.")
    except Exception as e:
        print(f"[SceneManager] Warning: Could not hide target: {e}")


    print(f"[SceneManager] Created {len(handles) - 1} objects.")
    return handles

# ─────────────────────────────────────────────────────────────────────
# Object Creation Functions
# Each function returns a list of created object handles
# ─────────────────────────────────────────────────────────────────────
def create_scene_floor(sim, config, random_pos, victim_pos):
    floor_handle = create_floor(sim, config["area_size"])
    return [floor_handle]

def create_scene_rocks(sim, config, random_pos, victim_pos):
    rocks = [
        create_rock(sim, random_pos(), random.uniform(0.3, 0.7))
        for _ in range(config["num_rocks"])
    ]
    return rocks

def create_scene_standing_trees(sim, config, random_pos, victim_pos):
    num_standing = int(config["num_trees"] * config["fraction_standing"])
    trees = [
        create_tree(
            sim,
            random_pos(),
            fallen=False,
            trunk_len=(
                random.uniform(0.2, 0.5) if random.random() < 0.1
                else random.uniform(2.5, 4.5)
            ),
            tilt_angle=(
                0.0 if (r := random.random()) < 0.5
                else (random.uniform(5.0, 15.0) if r < 0.8
                      else random.uniform(15.0, 30.0))
            )
        )
        for _ in range(num_standing)
    ]
    return trees

def create_scene_fallen_trees(sim, config, random_pos, victim_pos):
    num_fallen = config["num_trees"] - int(config["num_trees"] * config["fraction_standing"])
    trees = [
        create_tree(sim, random_pos(), fallen=True, trunk_len=random.uniform(0.5, 1.0))
        for _ in range(num_fallen)
    ]
    return trees

def create_scene_victim(sim, config, random_pos, victim_pos):
    victim_handle = create_victim(sim, victim_pos)
    return [victim_handle]

import math

def get_victim_direction(sim):
    """
    Returns:
        - unit_direction: (dx, dy, dz), normalized vector from drone to victim
        - distance: float, straight-line distance to victim
    """
    quad = sim.getObject('/Quadcopter')
    vic  = sim.getObject('/Victim')

    qx, qy, qz = sim.getObjectPosition(quad, -1)
    vx, vy, vz = sim.getObjectPosition(vic, -1)

    dx, dy, dz = vx - qx, vy - qy, vz - qz
    distance = math.sqrt(dx*dx + dy*dy + dz*dz)

    if distance == 0.0:
        unit_vector = (0.0, 0.0, 0.0)
    else:
        unit_vector = (dx / distance, dy / distance, dz / distance)

    return unit_vector, distance
