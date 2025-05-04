"""
Fully event-driven scene manager that simplifies scene creation while maintaining UI responsiveness.
"""
import math
import random
from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager
from Utils.terrain_elements import (
    FLOOR_THICKNESS, create_floor, create_rock, create_tree, 
    create_victim, create_bush, create_ground_foliage, 
    does_object_exist_by_alias
)

# Get singleton instances
SC = SimConnection.get_instance()
EM = EventManager.get_instance()

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
        
        # Register event handlers for both internal and external events
        EM.subscribe(SCENE_START_CREATION, self._handle_start_creation)
        EM.subscribe(SCENE_PROCESS_BATCH, self._handle_process_batch)
        EM.subscribe(SCENE_CREATION_CANCELED, self._handle_creation_canceled)
        EM.subscribe(SCENE_CLEAR, self._handle_clear)
        EM.subscribe(SCENE_RESTART, self._handle_restart)
        
        if self.verbose:
            print("[SceneManager] Initialized and registered event handlers")
    
    def _create_scene_structure(self):
        """Create the main dummy and category dummies for organization"""
        # Create main scene dummy
        self.scene_dummy = SC.sim.createDummy(0.01)
        SC.sim.setObjectAlias(self.scene_dummy, "SceneElements")
        self.objects.append(self.scene_dummy)
        
        # Create category dummies
        # Changed 'victim' to 'victims' to avoid name conflict with the Victim object
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
        
        print(f"[SceneManager] Looking for victim position at least {min_distance}m from drone at ({drone_x:.2f}, {drone_y:.2f})")
        
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
                print(f"[SceneManager] Found valid victim position at ({victim_x:.2f}, {victim_y:.2f}), " 
                      f"{distance_to_drone:.2f}m from drone starting position (attempt {attempt+1})")
                break
            
            if (attempt + 1) % 10 == 0:
                print(f"[SceneManager] Still searching for valid victim position... (attempt {attempt+1})")
        
        if not found_valid_position:
            print(f"[SceneManager] WARNING: Could not find valid victim position after {max_attempts} attempts. "
                  f"Using position ({victim_x:.2f}, {victim_y:.2f})")
        
        # Add the victim task with the validated position
        print(f"[SceneManager] Adding victim creation task with position ({victim_x:.2f}, {victim_y:.2f})")
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
            
            # Try to set properties only if supported
            try:
                # Check if properties exist before setting them
                properties = SC.sim.getObjectPropertiesInfo(target)
                if "depthInvisible" in properties:
                    SC.sim.setBoolProperty(target, "depthInvisible", True)
                elif self.verbose:
                    print("[Teleport] Note: 'depthInvisible' property not available for target object")
                    
                if "visible" in properties:
                    SC.sim.setBoolProperty(target, "visible", False)
                elif self.verbose:
                    print("[Teleport] Note: 'visible' property not available for target object")
            except Exception as prop_error:
                # Only log if verbose since these properties are not critical
                if self.verbose:
                    print(f"[Teleport] Warning: Could not set target object properties: {prop_error}")
                    print("[Teleport] This is not critical and teleportation succeeded.")
            
            if self.verbose:
                print(f"[Teleport] Quadcopter positioned at edge position [{x_pos:.2f}, {y_pos:.2f}, {z_pos:.2f}] facing center")
                
            return True
        except Exception as e:
            # Enhanced error message with more information
            error_msg = str(e)
            additional_info = ""
            
            if "object does not exist" in error_msg:
                additional_info = " - Quadcopter or target object not found in scene"
            elif "property could not be written" in error_msg:
                additional_info = " - The property is not supported for this object type"
            
            print(f"[Teleport] Error teleporting Quadcopter/target: {error_msg}{additional_info}")
            if self.verbose:
                print("[Teleport] Make sure both '/Quadcopter' and '/target' objects exist in your scene")
            return False
        
    def _handle_start_creation(self, config):
        """Handle the scene creation start event"""
        if self.is_creating:
            if self.verbose:
                print("[SceneManager] Scene creation already in progress, ignoring start request")
            return
            
        # Store the configuration
        self.config = config
        self.batch_size = config.get('batch_size', 10)
        self.verbose = config.get('verbose', False)
        
        # First, clear any existing scene
        self._clear_scene()
        
        # Reset state
        self.is_creating = True
        self.creation_tasks = []
        self.completed_objects = 0
        self.objects = []
        
        # Try to teleport quadcopter if it exists
        self._teleport_quadcopter_to_edge()
        
        # Create scene structure
        self._create_scene_structure()
        
        # Generate creation tasks
        self._generate_creation_tasks()
        
        if self.verbose:
            print(f"[SceneManager] Starting scene creation with {self.total_objects} objects")
        
        # Trigger the first batch
        EM.publish(SCENE_PROCESS_BATCH, None)
    
    def _handle_process_batch(self, _):
        """Handle the process batch event"""
        if not self.is_creating or not self.creation_tasks:
            return
        
        # Process a small batch (3-5 objects at a time)
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
        
            # Update progress with raw data (following Separation of Concerns)
            progress = self.completed_objects / max(1, self.total_objects)
            EM.publish(SCENE_CREATION_PROGRESS, {
                'progress': progress,
                'current_category': obj_type,
                'completed_objects': self.completed_objects,
                'total_objects': self.total_objects
            })
            
            if self.verbose:
                print(f"[SceneManager] Created {self.completed_objects}/{self.total_objects} objects ({obj_type})")
        
        # Check if we're done
        if not self.creation_tasks:
            self.is_creating = False
            if self.verbose:
                print(f"[SceneManager] Scene creation completed with {self.completed_objects} objects")
                
            EM.publish(SCENE_CREATION_PROGRESS, {
                'progress': 1.0,
                'current_category': 'complete',
                'completed_objects': self.total_objects,
                'total_objects': self.total_objects
            })
            EM.publish(SCENE_CREATION_COMPLETED, self.objects)
        else:
            # Schedule next batch processing with after() to allow UI updates
            # This is the key improvement - we let the main event loop finish this cycle
            EM.publish('trigger_ui_update', None)  # Special event to trigger UI update
            EM.publish(SCENE_PROCESS_BATCH, None)
    
    def _handle_creation_canceled(self, _):
        """Handle the scene creation cancel event"""
        if self.is_creating:
            self.is_creating = False
            self.creation_tasks = []
            if self.verbose:
                print("[SceneManager] Scene creation canceled")
    
    def _handle_clear(self, _):
        """Handle the scene clear event"""
        self._clear_scene()
        EM.publish(SCENE_CLEARED, None)
    
    def _handle_restart(self, config):
        """Handle the scene restart event"""
        # First clear the scene
        self._clear_scene()
        
        # Use default config if none provided
        if config is None:
            from Utils.config_utils import get_default_config
            config = get_default_config()
        
        # Then start a new scene creation
        EM.publish(SCENE_START_CREATION, config)
    
    def _clear_scene(self):
        """Clear the scene - internal implementation"""
        # Cancel any ongoing creation
        if self.is_creating:
            self.is_creating = False
            self.creation_tasks = []
        
        # Remove existing scene objects
        try:
            existing_scene = does_object_exist_by_alias("SceneElements")
            if existing_scene is not None:
                SC.sim.removeObject(existing_scene)
                if self.verbose:
                    print("[SceneManager] Removed scene elements dummy")
            else:
                # Check if there are any objects with scene-related names
                try:
                    for category in ["Floor", "Rocks", "Trees", "Bushes", "Foliage", "Victim"]:
                        obj = does_object_exist_by_alias(category)
                        if obj is not None:
                            SC.sim.removeObject(obj)
                            if self.verbose:
                                print(f"[SceneManager] Removed {category} dummy")
                except Exception as e:
                    if self.verbose:
                        print(f"[SceneManager] Error during extended clearing: {e}")
        except Exception as e:
            print(f"[SceneManager] Error while clearing scene: {e}")
        
        # Reset all state
        self.scene_dummy = None
        self.category_dummies = {}
        self.objects = []
        
        if self.verbose:
            print("[SceneManager] Scene cleared")
            
        return True
    
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
                    print(f"[SceneManager] Skipping parenting for victim - would create circular reference")
                    
                    # Just make sure the victim is visible
                    try:
                        SC.sim.setShapeColor(handle, None, SC.sim.colorcomponent_ambient_diffuse, [1.0, 1.0, 1.0])
                        SC.sim.setShapeColor(handle, None, SC.sim.colorcomponent_emission, [0.5, 0.5, 0.5])
                    except Exception as color_error:
                        print(f"[SceneManager] Note: Could not update victim colors: {color_error}")
                        
                    # Get and log position to verify
                    try:
                        position = SC.sim.getObjectPosition(handle, -1)
                        print(f"[SceneManager] Final victim position: {position}")
                    except:
                        pass
                        
                    return
                    
                # Otherwise, we can safely parent it
                print(f"[SceneManager] Parenting victim to category dummy")
                SC.sim.setObjectParent(handle, self.category_dummies[category], True)
                
                # Verify position after parenting
                try:
                    new_position = SC.sim.getObjectPosition(handle, -1)
                    print(f"[SceneManager] Victim position after final parenting: {new_position}")
                except:
                    pass
                
                return
            except Exception as e:
                print(f"[SceneManager] Error in special victim handling: {e}")
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
                    print(f"[SceneManager] {alias} already correctly parented to {category} category")
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
                    print(f"[SceneManager] Cannot parent {alias} to {category} category - would create circular reference")
                    print(f"[SceneManager] Ancestry chain: {chain_str}")
                return
            
            # Safe to parent
            SC.sim.setObjectParent(handle, self.category_dummies[category], True)
                
        except Exception as e:
            # This shouldn't stop the scene creation, just log it
            if self.verbose:
                print(f"[SceneManager] Error parenting {alias} ({handle}) to {category} category: {e}")
                print(f"[SceneManager] Continuing with scene creation...")

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