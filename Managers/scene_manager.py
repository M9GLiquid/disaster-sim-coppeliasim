"""
Fully event-driven scene manager that simplifies scene creation while maintaining UI responsiveness.
"""
import math
import random
from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3
from Utils.terrain_elements import (
    FLOOR_THICKNESS, create_floor, create_rock, create_tree, 
    create_victim, create_bush, create_ground_foliage, 
    does_object_exist_by_alias
)
from Managers.random_object_manager import RandomObjectManager

# Get singleton instances
SC = SimConnection.get_instance()
EM = EventManager.get_instance()
logger = get_logger()

# Event names - centralizing all scene events
SCENE_START_CREATION = 'scene/start_creation'
SCENE_CREATION_PROGRESS = 'scene/creation/progress'
SCENE_CREATION_COMPLETED = 'scene/creation/completed'
SCENE_CREATION_CANCELED = 'scene/creation/canceled'
SCENE_CLEAR = 'scene/clear'
SCENE_CLEARED = 'scene/cleared'
SCENE_RESTART = 'scene/restart'
SCENE_PROCESS_BATCH = 'scene/process_batch'

class SceneManager:
    """Fully event-driven scene manager."""
    
    def __init__(self):
        # Scene state
        self.scene_dummy = None
        self.category_dummies = {}
        self.config = None
        self.objects = []
        
        # Progress tracking
        self.is_creating = False
        self.batch_size = 10
        self.creation_tasks = []
        self.completed_objects = 0
        self.total_objects = 0
        self.verbose = False
        
        # Random object manager
        self.random_object_manager = None
        
        # Initialize logger
        self.logger = get_logger()
        
        # Register event handlers for both internal and external events
        EM.subscribe(SCENE_START_CREATION, self._handle_start_creation)
        EM.subscribe(SCENE_PROCESS_BATCH, self._handle_process_batch)
        EM.subscribe(SCENE_CREATION_CANCELED, self._handle_creation_canceled)
        EM.subscribe(SCENE_CLEAR, self._handle_clear)
        EM.subscribe(SCENE_RESTART, self._handle_restart)
        
        if self.verbose:
            self.logger.debug_at_level(DEBUG_L1, "SceneManager", "Initialized and registered event handlers")
    
    def _create_scene_structure(self):
        """Create the main dummy and category dummies for organization"""
        # Create main scene dummy
        self.scene_dummy = SC.sim.createDummy(0.01)
        SC.sim.setObjectAlias(self.scene_dummy, "SceneElements")
        self.objects.append(self.scene_dummy)
        
        # Create category dummies
        categories = ['floor', 'rocks', 'trees', 'bushes', 'foliage', 'victims']
        self.category_dummies = {}
        
        for category in categories:
            dummy = SC.sim.createDummy(0.01)
            SC.sim.setObjectAlias(dummy, f"{category.capitalize()}")
            SC.sim.setObjectParent(dummy, self.scene_dummy, True)
            self.category_dummies[category] = dummy
            self.objects.append(dummy)
    
    def _generate_creation_tasks(self):
        """Generate all the object creation tasks based on config"""
        area_size = self.config.get("area_size", 10.0)
        
        # Add floor task
        self.creation_tasks.append(('floor', {
            'area_size': area_size
        }))
        
        # Add rocks
        num_rocks = self.config.get("num_rocks", 0)
        for _ in range(num_rocks):
            x = random.uniform(-area_size/2, area_size/2)
            y = random.uniform(-area_size/2, area_size/2)
            size = random.uniform(0.3, 0.7)
            self.creation_tasks.append(('rock', {
                'position': (x, y),
                'size': size
            }))
        
        # Add trees
        num_trees = self.config.get("num_trees", 0)
        fraction_standing = self.config.get("fraction_standing", 0.7)
        num_standing = int(num_trees * fraction_standing)
        
        for i in range(num_trees):
            x = random.uniform(-area_size/2, area_size/2)
            y = random.uniform(-area_size/2, area_size/2)
            fallen = (i >= num_standing)
            trunk_len = None  # Let the create_tree function determine based on fallen status
            self.creation_tasks.append(('tree', {
                'position': (x, y),
                'fallen': fallen,
                'trunk_len': trunk_len
            }))
        
        # Add bushes
        num_bushes = self.config.get("num_bushes", 0)
        for _ in range(num_bushes):
            x = random.uniform(-area_size/2, area_size/2)
            y = random.uniform(-area_size/2, area_size/2)
            self.creation_tasks.append(('bush', {
                'position': (x, y)
            }))
        
        # Add ground foliage
        num_foliage = self.config.get("num_foliage", 0)
        for _ in range(num_foliage):
            x = random.uniform(-area_size/2, area_size/2)
            y = random.uniform(-area_size/2, area_size/2)
            self.creation_tasks.append(('ground_foliage', {
                'position': (x, y)
            }))
        
        # Add victim (always last)
        # Calculate the drone's position at the edge of the area
        drone_x = area_size * 0.45
        drone_y = area_size * 0.45
        
        # Initialize default victim position (will be overwritten if valid position found)
        # Default to opposite side of the area from the drone
        victim_x = -drone_x
        victim_y = -drone_y
        
        # Find a valid position for the victim that's at least 2m away from the drone
        min_distance = 2.0  # Minimum distance from drone (in meters)
        max_attempts = 100  # Prevent infinite loops
        found_valid_position = False
        
        self.logger.info("SceneManager", f"Looking for victim position at least {min_distance}m from drone at ({drone_x:.2f}, {drone_y:.2f})")
        
        for attempt in range(max_attempts):
            # Generate a random position with margin from area edge
            margin = 1.0
            x = random.uniform(-area_size/2 + margin, area_size/2 - margin)
            y = random.uniform(-area_size/2 + margin, area_size/2 - margin)
            
            # Calculate distance between victim and drone
            distance_to_drone = math.sqrt((x - drone_x)**2 + (y - drone_y)**2)
            
            # If distance is sufficient, break the loop
            if distance_to_drone >= min_distance:
                victim_x = x
                victim_y = y
                found_valid_position = True
                self.logger.info("SceneManager", f"Found valid victim position at ({victim_x:.2f}, {victim_y:.2f}), " 
                      f"{distance_to_drone:.2f}m from drone starting position (attempt {attempt+1})")
                break
            
            if (attempt + 1) % 10 == 0:
                self.logger.debug_at_level(DEBUG_L1, "SceneManager", f"Still searching for valid victim position... (attempt {attempt+1})")
        
        if not found_valid_position:
            self.logger.warning("SceneManager", f"Could not find valid victim position after {max_attempts} attempts. "
                  f"Using position ({victim_x:.2f}, {victim_y:.2f})")
        
        # Add the victim task with the validated position
        self.logger.debug_at_level(DEBUG_L1, "SceneManager", f"Adding victim creation task with position ({victim_x:.2f}, {victim_y:.2f})")
        self.creation_tasks.append(('victim', {
            'position': (victim_x, victim_y)
        }))
        
        self.total_objects = len(self.creation_tasks)
        
    def _teleport_quadcopter_to_edge(self):
        """Teleport the quadcopter to the edge of the area (if it exists)"""
        try:
            # Get quadcopter and target handles
            quadcopter = SC.sim.getObject('/Quadcopter')
            target = SC.sim.getObject('/target')
            
            # Get area size from config
            area_size = self.config.get("area_size", 10.0)
            
            # Calculate position at edge of area
            import math
            edge_distance = area_size * 0.45  # Slightly inside the edge
            x_pos = edge_distance
            y_pos = edge_distance
            z_pos = self.config.get("drone_height", 1.5)
            
            # Calculate angle towards center (0,0)
            angle_to_center = math.atan2(-y_pos, -x_pos) + math.pi
            
            # Set positions
            SC.sim.setObjectPosition(quadcopter, -1, [x_pos, y_pos, z_pos])
            SC.sim.setObjectPosition(target, -1, [x_pos, y_pos, z_pos])
            
            # Set orientation - yaw towards center
            SC.sim.setObjectOrientation(quadcopter, -1, [0, 0, angle_to_center])
            SC.sim.setObjectOrientation(target, -1, [0, 0, angle_to_center])
            
            # Try to set the target to be invisible to depth sensor
            try:
                SC.sim.setBoolProperty(target, "depthInvisible", True)
            except Exception:
                self.logger.debug_at_level(DEBUG_L2, "Teleport", "Note: 'depthInvisible' property not available for target object")
            
            # Try to set the target to be invisible visually
            try:
                SC.sim.setBoolProperty(target, "visible", False)
            except Exception:
                self.logger.debug_at_level(DEBUG_L2, "Teleport", "Note: 'visible' property not available for target object")
            
            # Log the new position for debugging
            self.logger.info("Teleport", f"Quadcopter positioned at edge position [{x_pos:.2f}, {y_pos:.2f}, {z_pos:.2f}] facing center")
                
            return True
        except Exception as error_msg:
            # Get Python exception arguments/message as additional info
            import traceback
            additional_info = f"\n{traceback.format_exc()}" if self.verbose else ""
            self.logger.error("Teleport", f"Error teleporting Quadcopter/target: {error_msg}{additional_info}")
            self.logger.error("Teleport", "Make sure both '/Quadcopter' and '/target' objects exist in your scene")
        
        return False
    
    def _handle_start_creation(self, config):
        """Handle the scene creation start event"""
        if self.is_creating:
            self.logger.warning("SceneManager", "Scene creation already in progress, ignoring start request")
            return
            
        # Store the configuration
        self.config = config
        self.batch_size = config.get('batch_size', 10)
        self.verbose = config.get('verbose', False)
        area_size = config.get("area_size", 10.0)
        
        # First, clear any existing scene
        self._clear_scene()
        
        # Reset state
        self.is_creating = True
        self.creation_tasks = []
        self.completed_objects = 0
        self.objects = []
        
        # Initialize RandomObjectManager with explicitly set parameters from config
        self.random_object_manager = RandomObjectManager(SC.sim, area_size)
        
        # Explicitly set the dynamic object counts from config
        num_birds = config.get("num_birds", 10)
        num_falling_trees = config.get("num_falling_trees", 5)
        tree_spawn_interval = config.get("tree_spawn_interval", 30.0)
        bird_speed = config.get("bird_speed", 1.0)
        
        self.logger.info("SceneManager", f"Setting dynamic objects from config: {num_birds} birds (speed: {bird_speed}), {num_falling_trees} trees, spawn: {tree_spawn_interval}s")
        
        # Update the RandomObjectManager with these values
        # Note: This internally calls _update_objects() which clears and creates objects,
        # so we don't need to call create_object() again
        self.random_object_manager.set_object_counts(
            num_birds=num_birds,
            num_falling_trees=num_falling_trees,
            tree_spawn_interval=tree_spawn_interval,
            bird_speed=bird_speed
        )
        
        # Try to teleport quadcopter if it exists
        self._teleport_quadcopter_to_edge()
        
        # Create scene structure
        self._create_scene_structure()
        
        # Generate creation tasks
        self._generate_creation_tasks()
        
        # Log the start of creation
        self.logger.info("SceneManager", f"Starting scene creation with {self.total_objects} objects")
        
        # Trigger the first batch
        EM.publish(SCENE_PROCESS_BATCH, None)
    
    def _handle_process_batch(self, _):
        """Handle the process batch event"""
        if not self.is_creating or not self.creation_tasks:
            return
        
        # Update random objects
        if self.random_object_manager:
            self.random_object_manager.update()
            
        if not self.is_creating or not self.creation_tasks:
            return
        
        # Process batch
        batch_size = min(3, len(self.creation_tasks))
        for _ in range(batch_size):
            if not self.creation_tasks:
                break
                
            obj_type, params = self.creation_tasks.pop(0)
            obj = self._create_object(obj_type, params)
            
            if obj:
                self.objects.append(obj)
                self._add_to_category(obj_type, obj)
                
            self.completed_objects += 1
            
            progress = self.completed_objects / max(1, self.total_objects)
            EM.publish(SCENE_CREATION_PROGRESS, {
                'progress': progress,
                'current_category': obj_type,
                'completed_objects': self.completed_objects,
                'total_objects': self.total_objects
            })
            
            # Log progress
            self.logger.debug_at_level(DEBUG_L1, "SceneManager", f"Created {self.completed_objects}/{self.total_objects} objects ({obj_type})")
        
        if not self.creation_tasks:
            self.is_creating = False
            self.logger.info("SceneManager", f"Scene creation completed with {self.completed_objects} objects")
            
            EM.publish(SCENE_CREATION_PROGRESS, {
                'progress': 1.0,
                'current_category': 'complete',
                'completed_objects': self.total_objects,
                'total_objects': self.total_objects
            })
            EM.publish(SCENE_CREATION_COMPLETED, self.objects)
        else:
            EM.publish('trigger_ui_update', None)
            EM.publish(SCENE_PROCESS_BATCH, None)
    
    def _clear_scene(self):
        """Clear the scene - internal implementation"""
        if self.is_creating:
            self.is_creating = False
            self.creation_tasks = []
        
        # Clear random objects
        if self.random_object_manager:
            self.random_object_manager.clear_objects()
            self.random_object_manager = None
        
        try:
            # List of objects to preserve (essential objects)
            preserve_objects = []
            try:
                # Try to get quadcopter and target if they exist
                quadcopter = SC.sim.getObject('/Quadcopter')
                target = SC.sim.getObject('/target')
                preserve_objects.extend([quadcopter, target])
            except:
                pass  # If objects don't exist, that's fine

            # Try to remove objects by their categories first
            categories = ['Floor', 'Rocks', 'Trees', 'Bushes', 'Foliage', 'Victims']
            for category in categories:
                try:
                    category_dummy = SC.sim.getObject(f'./{category}')
                    # Get all objects under this category
                    objects = SC.sim.getObjectsInTree(category_dummy, SC.sim.handle_all)
                    # Remove all objects in this category
                    for obj in objects:
                        if obj not in preserve_objects:
                            try:
                                SC.sim.removeObject(obj)
                                self.logger.debug_at_level(DEBUG_L2, "SceneManager", f"Removed {category} object: {obj}")
                            except Exception as e:
                                self.logger.debug_at_level(DEBUG_L2, "SceneManager", f"Error removing {category} object {obj}: {e}")
                    # Remove the category dummy itself
                    SC.sim.removeObject(category_dummy)
                    self.logger.debug_at_level(DEBUG_L2, "SceneManager", f"Removed {category} category dummy")
                except:
                    pass  # If category doesn't exist, that's fine

            # Try to remove the main scene dummy
            try:
                scene_dummy = SC.sim.getObject('./SceneElements')
                SC.sim.removeObject(scene_dummy)
                self.logger.debug_at_level(DEBUG_L1, "SceneManager", "Removed scene elements dummy")
            except:
                pass  # If scene dummy doesn't exist, that's fine
            
            # Instead of trying to get all objects using getObjects (which seems problematic),
            # we'll just make sure we've removed all the tracked objects
            self.logger.info("SceneManager", "Cleanup complete - removed all tracked scene objects")
            
            # If we need to clean up anything else in the future, we can implement a more specific
            # approach rather than trying to get all objects in the scene
        except Exception as e:
            self.logger.error("SceneManager", f"Error while clearing scene: {e}")
        
        self.scene_dummy = None
        self.category_dummies = {}
        self.objects = []
        
        self.logger.info("SceneManager", "Scene cleared")
        EM.publish(SCENE_CLEARED, None)
        
        return True
    
    def _handle_creation_canceled(self, _):
        """Handle the scene creation cancel event"""
        if self.is_creating:
            self.is_creating = False
            self.creation_tasks = []
            self.logger.info("SceneManager", "Scene creation canceled")
    
    def _handle_clear(self, _):
        """Handle the scene clear event"""
        self._clear_scene()
        EM.publish(SCENE_CLEARED, None)
    
    def _handle_restart(self, config):
        """Handle the scene restart event"""
        self._clear_scene()
        
        if config is None:
            from Utils.config_utils import get_default_config
            config = get_default_config()
        
        EM.publish(SCENE_START_CREATION, config)
        
    def _create_object(self, obj_type, params):
        """Create a single object based on type and parameters"""
        if obj_type == 'floor':
            return create_floor(params['area_size'])
        elif obj_type == 'rock':
            return create_rock(params['position'], params['size'])
        elif obj_type == 'tree':
            return create_tree(params['position'], params['fallen'], params['trunk_len'])
        elif obj_type == 'bush':
            return create_bush(params['position'])
        elif obj_type == 'ground_foliage':
            return create_ground_foliage(params['position'])
        elif obj_type == 'victim':
            return create_victim(params['position'])
        return None
    
    def _add_to_category(self, obj_type, handle):
        """Add object to the appropriate category dummy"""
        category_map = {
            'floor': 'floor',
            'rock': 'rocks',
            'tree': 'trees',
            'bush': 'bushes',
            'ground_foliage': 'foliage',
            'victim': 'victims'  # Updated to use 'victims' category instead of 'victim'
        }
        
        category = category_map.get(obj_type)
        if not category or category not in self.category_dummies:
            return
            
        # Special handling for victim - check if it's already in the hierarchy
        if obj_type == 'victim':
            try:
                # Get object alias for more informative messages
                try:
                    alias = SC.sim.getObjectAlias(handle)
                except:
                    alias = f"Object_{handle}"
                    
                # Before attempting to parent, check if it's already in the hierarchy
                parent_chain = []
                current = handle
                
                # Traverse up the parent chain to detect cycles
                while current != -1:
                    parent_chain.append(current)
                    current = SC.sim.getObjectParent(current)
                
                # If the category dummy is already in the parent chain, we have a cycle
                if self.category_dummies[category] in parent_chain:
                    self.logger.debug_at_level(DEBUG_L2, "SceneManager", "Skipping parenting for victim - would create circular reference")
                    
                    # Just make sure the victim is visible
                    try:
                        SC.sim.setShapeColor(handle, None, SC.sim.colorcomponent_ambient_diffuse, [1.0, 1.0, 1.0])
                        SC.sim.setShapeColor(handle, None, SC.sim.colorcomponent_emission, [0.5, 0.5, 0.5])
                    except Exception as color_error:
                        self.logger.debug_at_level(DEBUG_L2, "SceneManager", f"Note: Could not update victim colors: {color_error}")
                        
                    # Get and log position to verify
                    try:
                        position = SC.sim.getObjectPosition(handle, -1)
                        self.logger.debug_at_level(DEBUG_L2, "SceneManager", f"Final victim position: {position}")
                    except:
                        pass
                        
                    return
                    
                # Otherwise, we can safely parent it
                self.logger.debug_at_level(DEBUG_L2, "SceneManager", "Parenting victim to category dummy")
                SC.sim.setObjectParent(handle, self.category_dummies[category], True)
                
                # Verify position after parenting
                try:
                    new_position = SC.sim.getObjectPosition(handle, -1)
                    self.logger.debug_at_level(DEBUG_L3, "SceneManager", f"Victim position after final parenting: {new_position}")
                except:
                    pass
                
                return
            except Exception as e:
                self.logger.error("SceneManager", f"Error in special victim handling: {e}")
                # Continue with normal handling
        
        # Normal handling for other objects
        try:
            # Try to get object alias for better debugging
            try:
                alias = SC.sim.getObjectAlias(handle)
            except:
                alias = f"Object_{handle}"
                
            # Check if the object is already properly parented
            current_parent = SC.sim.getObjectParent(handle)
            if current_parent == self.category_dummies[category]:
                if self.verbose:
                    self.logger.debug_at_level(DEBUG_L3, "SceneManager", f"{alias} already correctly parented to {category} category")
                return
                
            # Check if the object is an ancestor of the category dummy (would create circular reference)
            is_ancestor = False
            parent_to_check = SC.sim.getObjectParent(self.category_dummies[category])
            ancestor_chain = []
            
            while parent_to_check != -1:
                try:
                    ancestor_alias = SC.sim.getObjectAlias(parent_to_check)
                    ancestor_chain.append(f"{parent_to_check}({ancestor_alias})")
                except:
                    ancestor_chain.append(f"{parent_to_check}")
                    
                if parent_to_check == handle:
                    is_ancestor = True
                    break
                parent_to_check = SC.sim.getObjectParent(parent_to_check)
            
            if is_ancestor:
                if self.verbose:
                    chain_str = " -> ".join(ancestor_chain)
                    self.logger.warning("SceneManager", f"Cannot parent {alias} to {category} category - would create circular reference")
                    self.logger.debug_at_level(DEBUG_L2, "SceneManager", f"Ancestry chain: {chain_str}")
                return
            
            # Safe to parent
            SC.sim.setObjectParent(handle, self.category_dummies[category], True)
                
        except Exception as e:
            # This shouldn't stop the scene creation, just log it
            alias = SC.sim.getObjectAlias(handle) if SC.sim is not None else "unknown"
            self.logger.error("SceneManager", f"Error parenting {alias} ({handle}) to {category} category: {e}")
            self.logger.info("SceneManager", "Continuing with scene creation...")

# Singleton instance
_scene_manager = None

def get_scene_manager():
    """Get the singleton SceneManager instance"""
    global _scene_manager
    if _scene_manager is None:
        _scene_manager = SceneManager()
    return _scene_manager

# Convenience functions - all using events for consistency
def create_scene(config):
    """Start scene creation via event"""
    EM.publish(SCENE_START_CREATION, config)

def clear_scene():
    """Clear the current scene via event"""
    EM.publish(SCENE_CLEAR, None)

def cancel_scene_creation():
    """Cancel ongoing scene creation via event"""
    EM.publish(SCENE_CREATION_CANCELED, None)

def restart_scene(config=None):
    """Restart the scene via event"""
    EM.publish(SCENE_RESTART, config)