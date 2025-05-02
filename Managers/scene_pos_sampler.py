import random
import math
from Utils.terrain_elements import FLOOR_THICKNESS


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