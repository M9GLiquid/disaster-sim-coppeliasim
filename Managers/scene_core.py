from Utils.terrain_elements import create_floor
from Utils.scene_helpers import generate_positions, create_terrain_object
import random
import math
from Managers.scene_creator_base import SceneCreatorBase
from Managers.Connections.sim_connection import SimConnection
from Utils.scene_helpers import set_standard_object_properties

SC = SimConnection.get_instance()

class create_scene(SceneCreatorBase):
    """
    Builds the full scene synchronously in a single call.
    Provides the same interface as ProgressiveSceneCreator but completes immediately.
    """
    def __init__(self, config):
        super().__init__(config)
        
    def create(self):
        """
        Implementation of the abstract create method from SceneCreatorBase.
        Builds the entire scene synchronously at once.
        
        Returns:
            List of created object handles
        """
        # Start by publishing event and teleporting quadcopter
        self.publish_started()
        self.teleport_quadcopter_to_edge()
        
        # Initialize scene group and samplers
        self.initialize_scene()
        
        # Create all objects
        creator_map = {
            'floor': lambda cfg, sap, vic: [create_floor(cfg['area_size'])],
            'rocks': lambda cfg, sap, vic: [create_terrain_object('rock', pos) for pos in generate_positions(sap, cfg.get('num_rocks', 0))],
            'standing_trees': lambda cfg, sap, vic: [create_terrain_object('standing_tree', pos) for pos in generate_positions(sap, int(cfg.get('num_trees', 0) * cfg.get('fraction_standing', 0)))],
            'fallen_trees': lambda cfg, sap, vic: [create_terrain_object('fallen_tree', pos, trunk_len=random.uniform(0.5, 1.0)) for pos in generate_positions(sap, cfg.get('num_trees', 0) - int(cfg.get('num_trees', 0) * cfg.get('fraction_standing', 0)))],
            'bushes': lambda cfg, sap, vic: [create_terrain_object('bush', pos) for pos in generate_positions(sap, cfg.get('num_bushes', 0))],
            'ground_foliage': lambda cfg, sap, vic: [create_terrain_object('ground_foliage', pos) for pos in generate_positions(sap, cfg.get('num_foliage', 0))],
            'victim': lambda cfg, sap, vic: [create_terrain_object('victim', vic)]
        }

        # Calculate total steps for progress tracking
        total_steps = len(self.keys)
        current_step = 0
        
        # Create objects type by type
        for key in self.keys:
            if self.verbose:
                print(f"[Scene] Creating {key}")
                
            creator = creator_map.get(key)
            if creator:
                objs = creator(self.config, self.pos_sampler, self.victim_pos)
                self.handles.extend(objs)
                
                # Set standard properties on created objects using helper
                for obj in objs:
                    set_standard_object_properties(obj)
                    
                if self.verbose:
                    print(f"[Scene] {key}: Created {len(objs)} objects")
            
            # Update progress
            current_step += 1
            progress = current_step / total_steps
            self.publish_progress(progress)
            
        # Finalize scene
        self.finalize_scene()
        
        # Mark as completed
        self.is_completed = True
        self.publish_completed()
        
        if self.verbose:
            print(f"[Scene] Created {len(self.handles) - 1} objects.")
        
        return self.handles


def get_victim_direction():
    """
    Returns a unit direction vector and distance from quadcopter to victim.
    
    Returns:
        tuple: ((dx, dy, dz), distance) - normalized direction vector and Euclidean distance
    """
    try:
        # Get object handles
        quad = SC.sim.getObject('/Quadcopter')
        vic = SC.sim.getObject('/Victim')

        # Get positions
        qx, qy, qz = SC.sim.getObjectPosition(quad, -1)
        vx, vy, vz = SC.sim.getObjectPosition(vic, -1)

        # Calculate vector components and distance
        dx, dy, dz = vx - qx, vy - qy, vz - qz
        distance = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Calculate normalized direction vector (unit vector)
        if distance < 0.0001:  # Avoid division by near-zero
            unit_vector = (0.0, 0.0, 0.0)
        else:
            unit_vector = (dx / distance, dy / distance, dz / distance)

        return unit_vector, distance
        
    except Exception as e:
        print(f"[SceneCore] Error calculating victim direction: {e}")
        return (0.0, 0.0, 0.0), -1.0  # Return zero vector and invalid distance on error