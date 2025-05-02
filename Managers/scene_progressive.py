import random
import traceback
import math  # For calculating angle towards center

from Managers.scene_pos_sampler import sample_victim_pos, make_pos_sampler
from Managers.scene_object_creators import (
    create_scene_floor, create_scene_rocks, create_scene_standing_trees,
    create_scene_fallen_trees, create_scene_bushes, create_scene_ground_foliage,
    create_scene_victim
)
from Utils.terrain_elements import create_rock, create_tree, create_bush, create_ground_foliage
from Utils.physics_utils import set_collision_properties, optimize_scene_physics

# Events used by the progressive scene creator
SCENE_CREATION_STARTED = 'scene/creation/started'
SCENE_CREATION_PROGRESS = 'scene/creation/progress'
SCENE_CREATION_COMPLETED = 'scene/creation/completed'
SCENE_CREATION_CANCELED = 'scene/creation/canceled'

class ProgressiveSceneCreator:
    """
    Incrementally builds the scene through repeated `update()` calls,
    reporting progress via events.
    """
    def __init__(self, sim, config, event_manager):
        self.sim = sim
        self.config = config
        self.event_manager = event_manager
        
        self.is_cancelled = False
        self.is_completed = False
        self.handles = []
        self.group = None
        self.victim_pos = None
        self.pos_sampler = None
        self.current_step = 0
        self.total_objects = (
            1 + config.get("num_rocks", 0) + config.get("num_trees", 0)
            + config.get("num_bushes", 0) + config.get("num_foliage", 0) + 1
        )
        self.completed_objects = 0
        # verbose batch progress flag
        self.verbose = config.get('verbose', False)
        # index of next creator to run
        self.creator_idx = 0
        # determine sequence of object types based on config toggles
        base_keys = ['floor','rocks','standing_trees','fallen_trees','bushes','ground_foliage','victim']
        self.keys = ['floor'] + [k for k in base_keys[1:-1] if config.get(f'include_{k}', True)] + ['victim']
        # unified batch size for all types
        self.batch_size = config.get('batch_size', 10)
        # totals per type
        num_trees = config.get('num_trees', 0)
        fs = config.get('fraction_standing', 0)
        standing = int(num_trees * fs)
        fallen = num_trees - standing
        self.totals = {
            'floor':1, 'rocks':config.get('num_rocks',0),
            'standing_trees':standing, 'fallen_trees':fallen,
            'bushes':config.get('num_bushes',0), 'ground_foliage':config.get('num_foliage',0),
            'victim':1
        }
        # counters
        self.type_progress = {k:0 for k in self.keys}
        # placeholder for prepared positions
        self.prepared_positions = {}
        # quadcopter and target handles
        try:
            self.quadcopter = sim.getObject('/Quadcopter')
            self.target = sim.getObject('/target')
        except Exception as e:
            if self.verbose:
                print(f"[ProgressiveScene] Error getting Quadcopter/target: {e}")
            self.quadcopter = -1
            self.target = -1

    def start(self):
        # Teleport Quadcopter before scene creation begins to avoid physics issues
        # This is now the first thing done in the scene creation process
        self._teleport_quadcopter_and_target()
        
        # Publish event that scene creation has started
        self.event_manager.publish(SCENE_CREATION_STARTED, None)
        self._update_progress(0.0)
        return True

    def update(self):
        # Don't do anything if we've already completed or cancelled
        if self.is_completed:
            return False
            
        if self.is_cancelled:
            # Publish event that scene creation was cancelled
            self.event_manager.publish(SCENE_CREATION_CANCELED, None)
            return False
            
        # Step 0: init group and sampler, and prepare positions
        if self.current_step == 0:
            self.group = self.sim.createDummy(0.01)
            self.sim.setObjectAlias(self.group, "DisasterGroup")
            self.handles.append(self.group)
            # sample and sampler
            self.victim_pos = sample_victim_pos(self.config)
            self.pos_sampler = make_pos_sampler(
                self.config, self.victim_pos,
                self.config.get("victim_radius", 0.7),
                self.config.get("victim_height_clearance", 1.5)
            )
            # precompute all positions
            self.prepared_positions['rocks'] = [p[:2] if len((p:=pos))>2 else pos for pos in self.pos_sampler(batch_size=self.totals['rocks'])]
            self.prepared_positions['standing_trees'] = self.pos_sampler(batch_size=self.totals['standing_trees'])
            self.prepared_positions['fallen_trees'] = [p[:2] if len((p:=pos))>2 else pos for pos in self.pos_sampler(batch_size=self.totals['fallen_trees'])]
            self.prepared_positions['bushes'] = [p[:2] if len((p:=pos))>2 else pos for pos in self.pos_sampler(batch_size=self.totals['bushes'])]
            self.prepared_positions['ground_foliage'] = [p[:2] if len((p:=pos))>2 else pos for pos in self.pos_sampler(batch_size=self.totals['ground_foliage'])]
            self.current_step = 1
            return True
        # Step 1: micro-batch creation for each object type
        if self.current_step == 1:
            if self.creator_idx < len(self.keys):
                key = self.keys[self.creator_idx]
                total = self.totals[key]
                # handle floor and victim instantly
                if key in ('floor', 'victim'):
                    if self.verbose:
                        print(f"[ProgressiveScene] Creating {key} ({self.type_progress[key]+1}/{total})")
                    fn = create_scene_floor if key=='floor' else create_scene_victim
                    h = fn(self.sim, self.config, self.pos_sampler, self.victim_pos)[0]
                    self.handles.append(h)
                    self.type_progress[key] = 1
                    self.completed_objects += 1
                    self.creator_idx += 1
                    self._update_progress(self.completed_objects / self.total_objects)
                    return True
                # batch types
                positions = self.prepared_positions.get(key, [])
                if positions:
                    # take unified batch size
                    bs = self.batch_size
                    batch = positions[:bs]
                    self.prepared_positions[key] = positions[bs:]
                    for pos in batch:
                        if key == 'rocks':
                            h = create_rock(self.sim, pos, random.uniform(0.3, 0.7))
                        elif key in ('standing_trees', 'fallen_trees'):
                            fallen = (key=='fallen_trees')
                            h = create_tree(self.sim, pos, fallen=fallen)
                        elif key == 'bushes':
                            h = create_bush(self.sim, pos)
                        else:
                            h = create_ground_foliage(self.sim, pos)
                        
                        # Disable collision on created objects for performance
                        set_collision_properties(self.sim, h, enable_collision=False)
                        
                        self.handles.append(h)
                        self.type_progress[key] += 1
                        self.completed_objects += 1
                    if self.verbose:
                        msg = f"{key.replace('_',' ').title()}: {self.type_progress[key]}/{total}"
                        print(f"[ProgressiveScene] Creating {msg}")
                    self._update_progress(self.completed_objects / self.total_objects)
                    return True
                # done with this key
                self.creator_idx += 1
                return True
            # all keys done
            self.current_step = 2
            return True
        # Step 2: finalize
        if self.current_step == 2:
            # Parent objects to group
            for h in self.handles:
                if h != self.group:  # Don't parent the group to itself
                    try:
                        self.sim.setObjectParent(h, self.group, True)
                    except Exception:
                        pass  # Ignore parenting errors
            
            # Apply final physics optimizations to all created objects ONCE
            optimize_scene_physics(self.sim, self.handles)
            
            self._update_progress(1.0)
            
            # Mark as completed so we don't process this again
            self.is_completed = True
            
            # Publish event that scene creation is complete
            self.event_manager.publish(SCENE_CREATION_COMPLETED, self.handles)
            
            return False
        return True
        
    def _teleport_quadcopter_and_target(self):
        """Teleport the quadcopter and target to the edge of the area, oriented towards center"""
        # Use the existing teleport_quadcopter_to_edge function instead of duplicating the logic
        teleport_quadcopter_to_edge(self.sim, self.config, self.verbose)

    def cancel(self):
        if not self.is_cancelled and not self.is_completed:
            self.is_cancelled = True
            # Publish event that scene creation was cancelled
            self.event_manager.publish(SCENE_CREATION_CANCELED, None)

    def _update_progress(self, progress):
        # Publish progress event
        self.event_manager.publish(SCENE_CREATION_PROGRESS, progress)


def create_scene_progressive(sim, config, event_manager):
    """Start progressive scene creation."""
    # Create a new progressive scene creator
    creator = ProgressiveSceneCreator(sim, config, event_manager)
    creator.start()
    
    # Register as current creator for update_progressive_scene_creation
    set_current_creator(creator)
    
    return creator


# Current creator for update_progressive_scene_creation
current_creator = None

def update_progressive_scene_creation():
    """Advance progressive creation; return True if still running."""
    global current_creator
    if current_creator and not current_creator.is_completed and not current_creator.is_cancelled:
        return current_creator.update()
    return False


def set_current_creator(creator):
    """Set the current creator for the update function."""
    global current_creator
    current_creator = creator


def teleport_quadcopter_to_edge(sim, config, verbose=False):
    """
    Public function to teleport the quadcopter to the edge of the area.
    This function does NOT trigger physics optimization, making it safe to call multiple times.
    
    Args:
        sim: The simulation handle
        config: Configuration dictionary 
        verbose: Whether to print debug messages
    """
    try:
        # Get quadcopter and target handles
        quadcopter = sim.getObject('/Quadcopter')
        target = sim.getObject('/target')
        
        # Get area size from config
        area_size = config.get("area_size", 10.0)
        
        # Calculate position at edge of area
        edge_distance = area_size * 0.45  # Slightly inside the edge
        x_pos = edge_distance
        y_pos = edge_distance
        z_pos = config.get("drone_height", 1.5)
        
        # Calculate angle towards center (0,0)
        # Fix: Adding PI to make the drone face the center properly
        angle_to_center = math.atan2(-y_pos, -x_pos) + math.pi
        
        # Set positions
        sim.setObjectPosition(quadcopter, -1, [x_pos, y_pos, z_pos])
        sim.setObjectPosition(target, -1, [x_pos, y_pos, z_pos])
        
        # Set orientation - yaw towards center
        sim.setObjectOrientation(quadcopter, -1, [0, 0, angle_to_center])
        sim.setObjectOrientation(target, -1, [0, 0, angle_to_center])
        
        # Set additional target properties
        from Utils.physics_utils import set_collision_properties
        set_collision_properties(sim, target, enable_collision=False)
        sim.setBoolProperty(target, "depthInvisible", True)
        # Fix: Using the correct property name "visible" instead of "visibleDuringSimulation"
        sim.setBoolProperty(target, "visible", False)
        
        if verbose:
            print(f"[Teleport] Quadcopter positioned at edge position [{x_pos:.2f}, {y_pos:.2f}, {z_pos:.2f}] facing center")
            
        return True
    except Exception as e:
        if verbose:
            print(f"[Teleport] Error teleporting Quadcopter/target: {e}")
            import traceback
            traceback.print_exc()
        return False