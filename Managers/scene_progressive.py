import random
from Managers.Connections.sim_connection import SimConnection
from Managers.scene_creator_base import SceneCreatorBase, SCENE_CREATION_PROGRESS
from Utils.terrain_elements import create_floor
from Utils.scene_helpers import normalize_position, create_terrain_object

SC = SimConnection.get_instance()

class ProgressiveSceneCreator(SceneCreatorBase):
    """
    Incrementally builds the scene through repeated `update()` calls,
    reporting progress via events.
    """
    def __init__(self, config):
        super().__init__(config)
        
        # Initialize tracking variables for progressive creation
        self.creator_idx = 0
        self.batch_size = config.get('batch_size', 10)
        self.prepared_positions = {}
        self.type_progress = {k:0 for k in self.keys}
        self.current_step = 0
        self.completed_objects = 0
        
    def start(self):
        """Start the progressive scene creation process."""
        # Teleport Quadcopter before scene creation begins to avoid physics issues
        self.teleport_quadcopter_to_edge()
        
        # Publish event that scene creation has started
        self.publish_started()
        self.publish_progress(0.0)
        return True

    def update(self):
        """
        Perform one step of progressive scene creation.
        Returns True if more steps remain, False if completed or cancelled.
        """
        # Don't do anything if we've already completed or cancelled
        if self.is_completed:
            return False
            
        if self.is_cancelled:
            self.publish_canceled()
            return False
            
        # Step 0: init group and sampler, and prepare positions
        if self.current_step == 0:
            self.initialize_scene()
            # Precompute all positions for batch processing
            self._precompute_positions()
            self.current_step = 1
            return True
            
        # Step 1: micro-batch creation for each object type
        if self.current_step == 1:
            if self.creator_idx < len(self.keys):
                key = self.keys[self.creator_idx]
                total = self.totals[key]
                
                # Handle floor and victim instantly
                if key == 'floor':
                    if self.verbose:
                        print(f"[ProgressiveScene] Creating floor (1/1)")
                    h = create_floor(self.config["area_size"])
                elif key == 'victim':
                    if self.verbose:
                        print(f"[ProgressiveScene] Creating victim (1/1)")
                    h = create_terrain_object('victim', self.victim_pos)
                else:
                    h = None
                if h is not None:
                    self.handles.append(h)
                    self.type_progress[key] = 1
                    self.completed_objects += 1
                    self.creator_idx += 1
                    self.publish_progress(self.completed_objects / self.total_objects)
                    return True
                    
                # Process batch creation for other types
                positions = self.prepared_positions.get(key, [])
                if positions:
                    # Take unified batch size
                    bs = self.batch_size
                    batch = positions[:bs]
                    self.prepared_positions[key] = positions[bs:]
                    
                    # Create batch of objects
                    self._create_batch(key, batch)
                    
                    if self.verbose:
                        msg = f"{key.replace('_',' ').title()}: {self.type_progress[key]}/{total}"
                        print(f"[ProgressiveScene] Creating {msg}")
                    
                    self.publish_progress(self.completed_objects / self.total_objects)
                    return True
                
                # Done with this key
                self.creator_idx += 1
                return True
                
            # All keys done
            self.current_step = 2
            return True
            
        # Step 2: finalize
        if self.current_step == 2:
            self.finalize_scene()
            self.publish_progress(1.0)
            
            # Mark as completed so we don't process this again
            self.is_completed = True
            self.publish_completed()
            
            return False
            
        return True
        
    def _precompute_positions(self):
        """Precompute all positions for batch processing."""
        # Use normalize_position from scene_helpers
        self.prepared_positions['rocks'] = [normalize_position(pos) 
                                           for pos in self.pos_sampler(batch_size=self.totals['rocks'])]
        
        self.prepared_positions['standing_trees'] = self.pos_sampler(batch_size=self.totals['standing_trees'])
        
        self.prepared_positions['fallen_trees'] = [normalize_position(pos) 
                                                 for pos in self.pos_sampler(batch_size=self.totals['fallen_trees'])]
        
        self.prepared_positions['bushes'] = [normalize_position(pos) 
                                           for pos in self.pos_sampler(batch_size=self.totals['bushes'])]
        
        self.prepared_positions['ground_foliage'] = [normalize_position(pos) 
                                                   for pos in self.pos_sampler(batch_size=self.totals['ground_foliage'])]
    
    def _create_batch(self, key, positions):
        """Create a batch of objects of the specified type."""
        # Use create_terrain_object from scene_helpers instead of duplicating creation logic
        creators = {
            'rocks': lambda pos: create_terrain_object('rock', pos, random.uniform(0.3, 0.7)),
            'standing_trees': lambda pos: create_terrain_object('standing_tree', pos),
            'fallen_trees': lambda pos: create_terrain_object('fallen_tree', pos, trunk_len=random.uniform(0.5, 1.0)),
            'bushes': lambda pos: create_terrain_object('bush', pos),
            'ground_foliage': lambda pos: create_terrain_object('ground_foliage', pos),
        }
        
        creator = creators.get(key)
        if not creator:
            return
            
        for pos in positions:
            obj = creator(pos)
            self.handles.append(obj)
            self.type_progress[key] += 1
            self.completed_objects += 1
            
    def create(self):
        """
        Implementation of the abstract create method from SceneCreatorBase.
        For progressive creation, this starts the process but doesn't
        complete it (update() calls are needed).
        """
        self.start()
        return self.handles


# Update function for progressive scene creation - should be called periodically
def update_progressive_scene_creation():
    """
    Update the current progressive scene creation process if one is active.
    This should be called periodically from your main loop.
    
    Returns:
        bool: True if there's an active creation process, False otherwise
    """
    import sys
    this_module = sys.modules[__name__]
    creator = getattr(this_module, '_current_creator', None)
    
    if creator and not creator.is_completed and not creator.is_cancelled:
        return creator.update()
        
    return False


# Create a new progressive scene creator and register it
def create_scene_progressive(config):
    """
    Create a new progressive scene creator and register it for updates.
    You must call update_progressive_scene_creation() periodically to advance creation.
    
    Returns:
        ProgressiveSceneCreator: The scene creator object
    """
    creator = ProgressiveSceneCreator(config)
    
    # Register for the update routine
    import sys
    this_module = sys.modules[__name__]
    setattr(this_module, '_current_creator', creator)
    
    return creator