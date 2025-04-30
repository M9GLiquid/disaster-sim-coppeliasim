# Managers/scene_manager.py

import random
import math
from Utils.terrain_elements import create_floor, create_tree, create_rock

def create_scene(sim, config):
    handles = []
    group = sim.createDummy(0.01)
    sim.setObjectAlias(group, "DisasterGroup")
    handles.append(group)

    area_size      = config["area_size"]
    total_trees    = config["num_trees"]
    total_rocks    = config["num_rocks"]
    frac_standing  = config["fraction_standing"]
    clear_center   = config.get("clear_zone_center", (0, 0))
    clear_radius   = config.get("clear_zone_radius", 0)

    n_stand = int(total_trees * frac_standing)
    n_fall  = total_trees - n_stand

    # ─── Floor ───
    handles.append(create_floor(sim, area_size))

    # helper to sample a position outside the clear zone
    def _random_pos():
        while True:
            x = random.uniform(-area_size/2, area_size/2)
            y = random.uniform(-area_size/2, area_size/2)
            dx, dy = x - clear_center[0], y - clear_center[1]
            if dx*dx + dy*dy >= clear_radius*clear_radius:
                return (x, y)

    # ─── Rocks ───
    for _ in range(total_rocks):
        pos  = _random_pos()
        size = random.uniform(0.3, 0.7)
        handles.append(create_rock(sim, pos, size))

    # ─── Standing Trees ───
    for _ in range(n_stand):
        pos = _random_pos()
        if random.random() < 0.1:
            length = random.uniform(0.2, 0.5)
        else:
            length = random.uniform(2.5, 4.5)

        r = random.random()
        if r < 0.5:
            tilt_deg = 0.0
        elif r < 0.8:
            tilt_deg = random.uniform(5.0, 15.0)
        else:
            tilt_deg = random.uniform(15.0, 30.0)

        handles.append(create_tree(
            sim,
            pos,
            fallen=False,
            trunk_len=length,
            tilt_angle=tilt_deg
        ))

    # ─── Fallen Logs ───
    for _ in range(n_fall):
        pos    = _random_pos()
        length = random.uniform(0.5, 1.0)
        handles.append(create_tree(sim, pos, fallen=True, trunk_len=length))

    # ─── Parent under group ───
    for h in handles[1:]:
        if sim.isHandleValid(h):
            sim.setObjectParent(h, group, True)

    print(f"[SceneManager] Created {len(handles)-1} objects (floor, rocks, trees).")

    # ─── Teleport entire quadcopter + target ───
    try:
        margin   = 1.0
        z_height = 1.2
        start_x  = (area_size / 2) + margin
        start_y  = 0.0
        new_pos  = [start_x, start_y, z_height]

        # Compute yaw so the drone's FRONT (-X axis) points toward (0,0):
        # vector from drone → center = (-start_x, -start_y)
        # but since local front is -X, yaw = atan2(start_y, start_x)
        yaw     = math.atan2(start_y, start_x)
        new_ori = [0.0, 0.0, yaw]

        sim.acquireLock()
        try:
            quad_root = sim.getObject('/Quadcopter')
            sim.setObjectPosition   (quad_root, -1, new_pos)
            sim.setObjectOrientation(quad_root, -1, new_ori)

            tgt = sim.getObject('/target')
            sim.setObjectPosition   (tgt, -1, new_pos)
            sim.setObjectOrientation(tgt, -1, new_ori)
        finally:
            sim.releaseLock()

        print(f"[SceneManager] Teleported QuadCopter & target to {new_pos}, yaw={yaw:.2f} rad.")
    except Exception as e:
        print(f"[SceneManager] Warning: teleport failed → {e}")

    return handles
