import random
from Utils.terrain_elements import create_floor, create_tree, create_rock, create_victim, create_bush


def create_scene_floor(sim, config, random_pos, victim_pos):
    return [create_floor(sim, config["area_size"])]


def create_scene_rocks(sim, config, random_pos, victim_pos):
    rocks = []
    num_rocks = config.get("num_rocks", 0)
    positions = random_pos(batch_size=num_rocks) if hasattr(random_pos, '__call__') and random_pos.__code__.co_argcount > 0 else [random_pos() for _ in range(num_rocks)]
    for pos in positions:
        if len(pos) > 2:
            pos = pos[:2]
        rocks.append(create_rock(sim, pos, random.uniform(0.3, 0.7)))
    return rocks


def create_scene_standing_trees(sim, config, random_pos, victim_pos):
    num_standing = int(config.get("num_trees", 0) * config.get("fraction_standing", 0))
    trees = []
    positions = random_pos(batch_size=num_standing) if hasattr(random_pos, '__call__') and random_pos.__code__.co_argcount > 0 else [random_pos() for _ in range(num_standing)]
    for pos in positions:
        if len(pos) > 2:
            x, y, z = pos
            trees.append(create_tree(sim, (x, y), fallen=False, trunk_len=random.uniform(0.2, 0.5)))
        else:
            trees.append(create_tree(sim, pos, fallen=False))
    return trees


def create_scene_fallen_trees(sim, config, random_pos, victim_pos):
    num_fallen = config.get("num_trees", 0) - int(config.get("num_trees", 0) * config.get("fraction_standing", 0))
    trees = []
    positions = random_pos(batch_size=num_fallen) if hasattr(random_pos, '__call__') and random_pos.__code__.co_argcount > 0 else [random_pos() for _ in range(num_fallen)]
    for pos in positions:
        if len(pos) > 2:
            pos = pos[:2]
        trees.append(create_tree(sim, pos, fallen=True, trunk_len=random.uniform(0.5, 1.0)))
    return trees


def create_scene_bushes(sim, config, random_pos, victim_pos):
    bushes = []
    num_bushes = config.get("num_bushes", 0)
    positions = random_pos(batch_size=num_bushes) if hasattr(random_pos, '__call__') and random_pos.__code__.co_argcount > 0 else [random_pos() for _ in range(num_bushes)]
    for pos in positions:
        if len(pos) > 2:
            pos = pos[:2]
        bushes.append(create_bush(sim, pos, (0.3, 0.8)))
    return bushes


def create_scene_ground_foliage(sim, config, random_pos, victim_pos):
    from Utils.terrain_elements import create_ground_foliage
    foliage = []
    num_foliage = config.get("num_foliage", 0)
    positions = random_pos(batch_size=num_foliage) if hasattr(random_pos, '__call__') and random_pos.__code__.co_argcount > 0 else [random_pos() for _ in range(num_foliage)]
    for pos in positions:
        if len(pos) > 2:
            pos = pos[:2]
        foliage.append(create_ground_foliage(sim, pos))
    return foliage


def create_scene_victim(sim, config, random_pos, victim_pos):
    return [create_victim(sim, victim_pos)]