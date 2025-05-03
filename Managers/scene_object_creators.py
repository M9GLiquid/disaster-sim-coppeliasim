import random
from Utils.terrain_elements import create_floor, create_victim
from Utils.scene_helpers import normalize_position, generate_positions, create_terrain_object

def create_scene_floor(config, random_pos, victim_pos):
    return [create_floor(config["area_size"])]

def create_scene_rocks(config, random_pos, victim_pos):
    num_rocks = config.get("num_rocks", 0)
    positions = generate_positions(random_pos, num_rocks)
    return [create_terrain_object('rock', pos) for pos in positions]

def create_scene_standing_trees(config, random_pos, victim_pos):
    num_standing = int(config.get("num_trees", 0) * config.get("fraction_standing", 0))
    positions = generate_positions(random_pos, num_standing)
    
    trees = []
    for pos in positions:
        if len(pos) > 2:
            kwargs = {'trunk_len': random.uniform(0.2, 0.5)}
            trees.append(create_terrain_object('standing_tree', pos, **kwargs))
        else:
            trees.append(create_terrain_object('standing_tree', pos))
    return trees

def create_scene_fallen_trees(config, random_pos, victim_pos):
    num_fallen = config.get("num_trees", 0) - int(config.get("num_trees", 0) * config.get("fraction_standing", 0))
    positions = generate_positions(random_pos, num_fallen)
    
    return [create_terrain_object('fallen_tree', pos, trunk_len=random.uniform(0.5, 1.0)) for pos in positions]

def create_scene_bushes(config, random_pos, victim_pos):
    num_bushes = config.get("num_bushes", 0)
    positions = generate_positions(random_pos, num_bushes)
    
    return [create_terrain_object('bush', pos, size_range=(0.3, 0.8)) for pos in positions]

def create_scene_ground_foliage(config, random_pos, victim_pos):
    num_foliage = config.get("num_foliage", 0)
    positions = generate_positions(random_pos, num_foliage)
    
    return [create_terrain_object('ground_foliage', pos) for pos in positions]

def create_scene_victim(config, random_pos, victim_pos):
    return [create_victim(victim_pos)]