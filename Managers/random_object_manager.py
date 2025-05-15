# Managers/random_object_manager.py
import math
import random
import time
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

FLOOR_THICKNESS = 0.5

class RandomObjectManager:
    def __init__(self, sim, area_size):
        self.sim = sim
        self.birds = []
        self.trees = []
        self.num_birds = 10  
        self.num_falling_trees = 5 
        self.tree_spawn_interval = 30.0  # seconds between new batches of trees
        self.last_tree_spawn = time.time()  # track when we last spawned trees
        self.directions = []
        self.vertical_speeds = []
        self.falling_trees = []
        self.created_objects = []
        self.logger = get_logger()  # Initialize logger

        self.last_update = time.time()
        self.change_interval = 3.0
        self.base_speed = 0.03  # Base speed for birds
        self.bird_speed = 1.0   # Speed multiplier for birds

        self.area_min = -area_size / 2
        self.area_max = area_size / 2
        self.z_min = 1.0
        self.z_max = 2.5

    def _create_bird(self):
        """Create a single bird with all its components"""
        try:
            size = random.uniform(0.3, 0.5)
            x = random.uniform(self.area_min, self.area_max)
            y = random.uniform(self.area_min, self.area_max)
            z = random.uniform(self.z_min, self.z_max)

            # Create bird body
            body = self.sim.createPrimitiveShape(self.sim.primitiveshape_capsule, [size*0.3, size*0.3, size*0.3], 0)
            self.created_objects.append(body)
            self.sim.setObjectPosition(body, -1, [x, y, z])
            self.sim.setObjectOrientation(body, -1, [0, 0, 0])
            self.sim.setShapeColor(body, None, self.sim.colorcomponent_ambient_diffuse, [1.0, 0.6, 0.2])
            self.sim.setObjectAlias(body, f"Bird_{len(self.birds)}")
            self.sim.setBoolProperty(body, "collidable", True)
            self.sim.setBoolProperty(body, "respondable", True)
            self.sim.setBoolProperty(body, "dynamic", False)

            # Create beak
            beak = self.sim.createPrimitiveShape(self.sim.primitiveshape_cone, [size*0.1, size*0.1, size*0.2], 0)
            self.created_objects.append(beak)
            self.sim.setShapeColor(beak, None, self.sim.colorcomponent_ambient_diffuse, [1.0, 0.4, 0.0])
            self.sim.setObjectParent(beak, body, False)
            self.sim.setObjectPosition(beak, body, [0, size*0.2, 0])
            self.sim.setObjectOrientation(beak, body, [math.radians(270), 0, 0])

            # Create wings
            # left wing
            wing_l = self.sim.createPrimitiveShape(self.sim.primitiveshape_cuboid, [size*0.4, 0.05, 0.01], 0)
            self.created_objects.append(wing_l)
            self.sim.setShapeColor(wing_l, None, self.sim.colorcomponent_ambient_diffuse, [0.2, 0.2, 0.2])
            self.sim.setObjectParent(wing_l, body, False)
            self.sim.setObjectPosition(wing_l, body, [size*0.3, -0.03, 0])
            self.sim.setObjectOrientation(wing_l, body, [0, 0, math.radians(340)])
            self.sim.setBoolProperty(wing_l, "collidable", False)

            # right wing
            wing_r = self.sim.createPrimitiveShape(self.sim.primitiveshape_cuboid, [size*0.4, 0.05, 0.01], 0)
            self.created_objects.append(wing_r)
            self.sim.setShapeColor(wing_r, None, self.sim.colorcomponent_ambient_diffuse, [0.2, 0.2, 0.2])
            self.sim.setObjectParent(wing_r, body, False)
            self.sim.setObjectPosition(wing_r, body, [-size*0.3, -0.03, 0])
            self.sim.setObjectOrientation(wing_r, body, [0, 0, -math.radians(340)])
            self.sim.setBoolProperty(wing_r, "collidable", False)

            # Add to birds list and set direction
            self.birds.append(body)
            angle = random.uniform(0, 2 * math.pi)
            self.directions.append([math.cos(angle), math.sin(angle)])
            self.vertical_speeds.append(random.uniform(-0.01, 0.01))

            return body
        except Exception as e:
            self.logger.error("RandomObjectManager", f"Error creating bird: {e}")
            return None

    def create_object(self):
        """Create all dynamic objects"""
        # Create birds
        for _ in range(self.num_birds):
            self._create_bird()

        # Create falling trees
        self.logger.info("RandomObjectManager", f"Creating {self.num_falling_trees} falling trees")
        for _ in range(self.num_falling_trees):
            self._create_single_tree()

    def _create_single_tree(self):
        trunk_height = random.uniform(2.5, 4.5)
        radius = 0.2
        x = random.uniform(self.area_min + 1, self.area_max - 1)
        y = random.uniform(self.area_min + 1, self.area_max - 1)

        pivot = self.sim.createDummy(0.01)
        self.created_objects.append(pivot)
        self.sim.setObjectPosition(pivot, -1, [x, y, FLOOR_THICKNESS])

        tree = self.sim.createPrimitiveShape(self.sim.primitiveshape_cylinder, [radius, radius, trunk_height], 0)
        self.created_objects.append(tree)
        self.sim.setObjectPosition(tree, pivot, [0, 0, trunk_height / 2])
        self.sim.setObjectOrientation(tree, pivot, [0, 0, 0])
        self.sim.setShapeColor(tree, None, self.sim.colorcomponent_ambient_diffuse, [0.4, 0.25, 0.1])
        self.sim.setBoolProperty(tree, "collidable", True)
        self.sim.setBoolProperty(tree, "respondable", True)
        self.sim.setBoolProperty(tree, "dynamic", False)
        self.sim.setObjectParent(tree, pivot, True)

        fall_dir = random.uniform(0, 2 * math.pi)
        self.falling_trees.append({
            "handle": pivot,
            "angle": 0.0,
            "dir": fall_dir,
            "removed": False
        })

    def update(self):
        current_time = time.time()
        if current_time - self.last_update > self.change_interval:
            for i in range(len(self.vertical_speeds)):
                self.vertical_speeds[i] += random.uniform(-0.005, 0.005)
                self.vertical_speeds[i] = max(min(self.vertical_speeds[i], 0.02), -0.02)
            self.last_update = current_time

        # Check if it's time to spawn a new batch of trees
        if current_time - self.last_tree_spawn > self.tree_spawn_interval:
            self.logger.info("RandomObjectManager", f"Spawning new batch of {self.num_falling_trees} trees")
            self.clear_objects()  # Clear existing objects
            self.create_object()  # Create new objects
            self.last_tree_spawn = current_time

        for i, bird in enumerate(self.birds):
            try:
                pos = self.sim.getObjectPosition(bird, -1)
                dx = self.directions[i][0] * self.base_speed * self.bird_speed
                dy = self.directions[i][1] * self.base_speed * self.bird_speed
                dz = self.vertical_speeds[i]

                new_x = pos[0] + dx
                new_y = pos[1] + dy
                new_z = pos[2] + dz

                if not (self.area_min < new_x < self.area_max):
                    self.directions[i][0] *= -1
                    dx *= -1
                    new_x = pos[0] + dx

                if not (self.area_min < new_y < self.area_max):
                    self.directions[i][1] *= -1
                    dy *= -1
                    new_y = pos[1] + dy

                if not (self.z_min < new_z < self.z_max):
                    self.vertical_speeds[i] *= -1
                    dz *= -1
                    new_z = pos[2] + dz

                self.sim.setObjectPosition(bird, -1, [new_x, new_y, new_z])
                angle_rad = math.atan2(dy, dx) + math.radians(270)
                self.sim.setObjectOrientation(bird, -1, [0, 0, angle_rad])

            except Exception as e:
                self.logger.error("RandomObjectManager", f"Error in bird movement {i}: {e}")

        fall_speed = 0.01
        max_angle = math.radians(90)

        for tree in self.falling_trees:
            if tree["removed"]:
                continue
            try:
                if tree["angle"] < max_angle:
                    tree["angle"] += fall_speed
                    tree["angle"] = min(tree["angle"], max_angle)
                    dx = math.cos(tree["dir"])
                    dy = math.sin(tree["dir"])
                    self.sim.setObjectOrientation(tree["handle"], -1, [
                        tree["angle"] * dx,
                        tree["angle"] * dy,
                        0
                    ])
            except Exception as e:
                self.logger.error("RandomObjectManager", f"Error animating tree: {e}")

        # Check and maintain tree count - fixed by moving outside the time interval check
        active_trees = len([t for t in self.falling_trees if not t["removed"]])
        while active_trees < self.num_falling_trees:
            self._create_single_tree()
            active_trees += 1

    def clear_objects(self):
        """Clear all dynamic objects"""
        self.logger.info("RandomObjectManager", f"Clearing {len(self.birds)} birds and {len(self.falling_trees)} trees")
        
        # Clear birds
        for obj in self.created_objects:
            try:
                self.sim.removeObject(obj)
            except Exception as e:
                self.logger.error("RandomObjectManager", f"Error removing object: {e}")
        
        # Reset all tracking lists
        self.birds = []
        self.directions = []
        self.vertical_speeds = []
        self.falling_trees = []
        self.created_objects = []
        
        self.logger.info("RandomObjectManager", "All objects cleared.")
            
    def set_object_counts(self, num_birds=None, num_falling_trees=None, tree_spawn_interval=None, bird_speed=None):
        """Update the counts of dynamic objects"""
        if num_birds is not None:
            self.num_birds = max(0, int(num_birds))
        if num_falling_trees is not None:
            self.num_falling_trees = max(0, int(num_falling_trees))
        if tree_spawn_interval is not None:
            self.tree_spawn_interval = max(5.0, float(tree_spawn_interval))
        if bird_speed is not None:
            self.bird_speed = max(0.1, min(5.0, float(bird_speed)))
            
        self._update_objects()
            
    def _update_objects(self):
        """Update objects after counts change"""
        # For simplicity, just clear and recreate all objects
        self.clear_objects()
        self.create_object()