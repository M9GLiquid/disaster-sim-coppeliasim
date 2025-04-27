# Controls/waypoint_navigation.py

import time
import math
import random

def duplicate_target(sim):
    try:
        waypoint_handle = sim.getObject('/waypoint_target')
        print("[Waypoint] Existing waypoint_target found.")
    except Exception:
        print("[Waypoint] Duplicating /target to create waypoint_target...")
        target_handle = sim.getObject('/target')
        waypoint_handle = sim.copyPasteObjects([target_handle])[0]
        sim.setObjectAlias(waypoint_handle, 'waypoint_target')
    return waypoint_handle

def prepare_waypoint(sim, config):
    waypoint_handle = duplicate_target(sim)
    area_size = config['area_size']
    
    x = random.uniform(-area_size/2 * 0.9, area_size/2 * 0.9)
    y = random.uniform(-area_size/2 * 0.9, area_size/2 * 0.9)
    z = 0.8

    sim.acquireLock()
    try:
        sim.setObjectPosition(waypoint_handle, -1, [x, y, z])
    finally:
        sim.releaseLock()

    print(f"[Waypoint] Waypoint_target placed at random position ({x:.2f}, {y:.2f}, {z:.2f})")

def activate_waypoint_follow(sim):
    print("\n[Waypoint] Activating waypoint follow and landing...")
    target_handle = sim.getObject('/target')
    waypoint_handle = sim.getObject('/waypoint_target')

    DELAY = 0.05
    SPEED = 0.5
    DESCENT_SPEED = 0.2

    try:
        while True:
            sim.acquireLock()
            try:
                target_pos = sim.getObjectPosition(target_handle, -1)
                waypoint_pos = sim.getObjectPosition(waypoint_handle, -1)
            finally:
                sim.releaseLock()

            direction = [
                waypoint_pos[0] - target_pos[0],
                waypoint_pos[1] - target_pos[1],
                0
            ]
            distance = math.sqrt(direction[0]**2 + direction[1]**2)

            if distance > 0.05:
                direction = [d / distance for d in direction]
                step = [d * SPEED * DELAY for d in direction]
                new_target_pos = [
                    target_pos[0] + step[0],
                    target_pos[1] + step[1],
                    target_pos[2]
                ]
            else:
                new_target_pos = [
                    target_pos[0],
                    target_pos[1],
                    max(waypoint_pos[2], target_pos[2] - DESCENT_SPEED * DELAY)
                ]

            sim.acquireLock()
            try:
                sim.setObjectPosition(target_handle, -1, new_target_pos)
            finally:
                sim.releaseLock()

            if distance <= 0.05 and abs(new_target_pos[2] - waypoint_pos[2]) <= 0.02:
                print("[Waypoint] Drone has landed on waypoint!")
                break

            time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\n[Waypoint] Waypoint following interrupted.")
