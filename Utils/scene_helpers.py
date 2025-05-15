"""
Scene helper functions to remove duplication across scene creation modules.
Contains shared utilities for position handling, object creation, and property setting.
"""
import random
import math
from Utils.terrain_elements import FLOOR_THICKNESS

from Managers.Connections.sim_connection import SimConnection
SC = SimConnection.get_instance()

from Core.event_manager import EventManager
EM = EventManager.get_instance()

def normalize_position(pos):
    """Normalize position to 2D if it has more dimensions."""
    return pos[:2] if len(pos) > 2 else pos

def generate_positions(random_pos, count):
    """Generate positions using either a batch function or individual calls."""
    if hasattr(random_pos, '__call__') and random_pos.__code__.co_argcount > 0:
        return random_pos(batch_size=count)
    return [random_pos() for _ in range(count)]

def set_standard_object_properties(handle, collidable=False, respondable=False, dynamic =False):
    """Set standard collision properties on an object."""
    if SC.sim.getObjectType(handle) == SC.sim.sceneobject_shape:
        SC.sim.setBoolProperty(handle, "respondable", respondable)
        SC.sim.setBoolProperty(handle, "dynamic", dynamic)

    if SC.sim.getObjectType(handle) == SC.sim.objecttype_sceneobject:
        SC.sim.setBoolProperty(handle, "collidable", False)

def create_terrain_object(object_type, pos, size=None, **kwargs):
    # Normalize position
    pos = normalize_position(pos)
    
    # Import terrain element functions
    from Utils.terrain_elements import (
        create_rock, create_tree, create_bush, 
        create_ground_foliage, create_victim
    )
    
    # Create appropriate object based on type
    if object_type == 'rock':
        size = size if size is not None else random.uniform(0.3, 0.7)
        obj = create_rock(pos, size)
    elif object_type == 'standing_tree':
        obj = create_tree(pos, fallen=False, **kwargs)
    elif object_type == 'fallen_tree':
        obj = create_tree(pos, fallen=True, **kwargs)
    elif object_type == 'bush':
        obj = create_bush(pos, **kwargs)
    elif object_type == 'ground_foliage':
        obj = create_ground_foliage(pos, **kwargs)
    elif object_type == 'victim':
        obj = create_victim(pos, **kwargs)
    else:
        raise ValueError(f"Unknown terrain object type: {object_type}")
    
    # Set standard properties
    set_standard_object_properties(obj)
    
    return obj

def sample_victim_pos(config):
    area = config["area_size"]
    margin = 1.0
    return (
        random.uniform(-area / 2 + margin, area / 2 - margin),
        random.uniform(-area / 2 + margin, area / 2 - margin)
    )

def make_pos_sampler(config, avoid_zone, avoid_radius, avoid_height):
    area = config["area_size"]
    clear_center = config.get("clear_zone_center", (0, 0))
    clear_radius = config.get("clear_zone_radius", 0)
    floor_height = FLOOR_THICKNESS

    if config.get("optimized_creation", True):
        def random_pos_optimized(batch_size=1):
            positions = []
            max_attempts = batch_size * 3
            attempts = 0
            while len(positions) < batch_size and attempts < max_attempts:
                xs = [random.uniform(-area/2, area/2) for _ in range(batch_size)]
                ys = [random.uniform(-area/2, area/2) for _ in range(batch_size)]
                for x, y in zip(xs, ys):
                    dx1, dy1 = x - clear_center[0], y - clear_center[1]
                    dx2, dy2 = x - avoid_zone[0], y - avoid_zone[1]
                    dist_to_clear = dx1*dx1 + dy1*dy1
                    dist_to_victim = dx2*dx2 + dy2*dy2
                    if dist_to_clear >= clear_radius*clear_radius and dist_to_victim >= avoid_radius*avoid_radius:
                        positions.append((x, y))
                    elif dist_to_victim < avoid_radius*avoid_radius and random.random() < 0.05:
                        z = floor_height + avoid_height + random.uniform(0.1, 1.0)
                        positions.append((x, y, z))
                    if len(positions) >= batch_size:
                        break
                attempts += batch_size
            if batch_size == 1:
                return positions[0] if positions else (0, 0)
            return positions
        return random_pos_optimized

    else:
        def random_pos():
            while True:
                x = random.uniform(-area/2, area/2)
                y = random.uniform(-area/2, area/2)
                dx1, dy1 = x - clear_center[0], y - clear_center[1]
                dx2, dy2 = x - avoid_zone[0], y - avoid_zone[1]
                horiz_dist_to_victim = math.sqrt(dx2*dx2 + dy2*dy2)
                if dx1*dx1 + dy1*dy1 >= clear_radius*clear_radius and horiz_dist_to_victim >= avoid_radius:
                    return (x, y)
                elif horiz_dist_to_victim < avoid_radius and random.random() < 0.05:
                    z = floor_height + avoid_height + random.uniform(0.1, 1.0)
                    return (x, y, z)
        return random_pos
