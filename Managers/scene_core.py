from Managers.scene_pos_sampler import sample_victim_pos, make_pos_sampler
from Managers.scene_object_creators import (
    create_scene_floor, create_scene_rocks, create_scene_standing_trees,
    create_scene_fallen_trees, create_scene_bushes, create_scene_ground_foliage,
    create_scene_victim
)
import random, math
from Utils.physics_utils import set_collision_properties, optimize_scene_physics

# Registry of creator functions
OBJECT_CREATORS = [
    create_scene_floor,
    create_scene_rocks,
    create_scene_standing_trees,
    create_scene_fallen_trees,
    create_scene_bushes,
    create_scene_ground_foliage,
    create_scene_victim,
]

def create_scene(sim, config, event_manager=None):
    """
    Build the full scene synchronously, grouping and positioning objects.
    
    Args:
        sim: The simulation handle
        config: Configuration dictionary
        event_manager: Optional event manager to publish scene events
    """
    # Publish event that scene creation has started (if event_manager is provided)
    if event_manager:
        event_manager.publish('scene/creation/started', None)
    
    # Teleport quadcopter & target to edge of area, facing center
    # Import the teleport function to avoid code duplication
    from Managers.scene_progressive import teleport_quadcopter_to_edge
    teleport_quadcopter_to_edge(sim, config, config.get('verbose', False))
    
    # Additional target properties (not handled by teleport function)
    try:
        target = sim.getObject('/target')
        # Hide target from rendering and depth using centralized function
        set_collision_properties(sim, target, enable_collision=False)
        sim.setBoolProperty(target, 'depthInvisible', True)
        sim.setBoolProperty(target, 'visibleDuringSimulation', False)
    except Exception as e:
        print(f"[Scene] Target setup failed: {e}")
    
    # Create group for all objects
    handles = []
    group = sim.createDummy(0.01)
    sim.setObjectAlias(group, "DisasterGroup")
    handles.append(group)
    
    # Sample victim and get position sampler
    victim_pos = sample_victim_pos(config)
    pos_sampler = make_pos_sampler(config, victim_pos, config.get("victim_radius", 0.7), config.get("victim_height_clearance", 1.5))
    
    # Determine which creators to run based on config toggles
    creators = []
    from Managers.scene_object_creators import (
        create_scene_rocks, create_scene_standing_trees,
        create_scene_fallen_trees, create_scene_bushes, create_scene_ground_foliage,
        create_scene_floor, create_scene_victim
    )
    
    # always include floor
    creators.append(create_scene_floor)
    if config.get('include_rocks', True):
        creators.append(create_scene_rocks)
    if config.get('include_standing_trees', True):
        creators.append(create_scene_standing_trees)
    if config.get('include_fallen_trees', True):
        creators.append(create_scene_fallen_trees)
    if config.get('include_bushes', True):
        creators.append(create_scene_bushes)
    if config.get('include_foliage', True):
        creators.append(create_scene_ground_foliage)
    # victim last
    creators.append(create_scene_victim)
    
    # Calculate total steps for progress tracking
    total_steps = len(creators)
    current_step = 0
    
    # Run selected creators
    for creator in creators:
        if config.get('verbose', False):
            print(f"[Scene] Running {creator.__name__}")
        objs = creator(sim, config, pos_sampler, victim_pos)
        
        # Disable collision for all created objects using centralized function
        for obj in objs:
            set_collision_properties(sim, obj, enable_collision=False)
            
        if config.get('verbose', False):
            print(f"[Scene] {creator.__name__} created {len(objs)} objects")
        handles.extend(objs)
        
        # Update progress
        current_step += 1
        if event_manager:
            progress = current_step / total_steps
            event_manager.publish('scene/creation/progress', progress)
    
    # Parent created objects under group
    for h in handles[1:]:
        if sim.isHandleValid(h):
            sim.setObjectParent(h, group, True)
    
    # Use the optimize_scene_physics utility for overall physics optimization
    optimize_scene_physics(sim, handles)
    
    print(f"[Scene] Created {len(handles) - 1} objects.")
    
    # Publish event that scene creation is complete
    if event_manager:
        event_manager.publish('scene/creation/completed', handles)
        # Also publish the standard scene/created event for backward compatibility
        event_manager.publish('scene/created', None)
        
    return handles


def create_scene_queued(sim, config, callback=None, progress_callback=None, event_manager=None):
    """
    Synchronous wrapper for backward compatibility with logging and event publishing.
    This function is designed to be called from the simulation queue system.
    
    Args:
        sim: The simulation handle
        config: Configuration dictionary
        callback: Callback function to call when scene creation is complete
        progress_callback: Callback function to call with progress updates
        event_manager: Optional event manager to publish scene events
    """
    print("[Scene] Creating scene, please wait...")
    
    # Create a progress callback that will update both through the original callback
    # and through the event system if available
    def combined_progress_callback(progress):
        if progress_callback:
            progress_callback(progress)
        if event_manager:
            event_manager.publish('scene/creation/progress', progress)
    
    # Create a completion callback that will update both through the original callback
    # and through the event system if available
    def combined_completion_callback(handles):
        if callback:
            callback(handles)
        if event_manager:
            event_manager.publish('scene/creation/completed', handles)
            # Also publish the standard scene/created event for backward compatibility
            event_manager.publish('scene/created', None)
    
    # If we have an event manager, publish the start event
    if event_manager:
        event_manager.publish('scene/creation/started', None)
        
    handles = create_scene(sim, config, event_manager)
    
    print(f"[Scene] Created {len(handles)} objects.")
    
    # Call the combined completion callback
    if callback:
        combined_completion_callback(handles)
        
    return handles


def get_victim_direction(sim):
    """
    Returns a unit direction vector and distance from quadcopter to victim.
    
    Returns:
        tuple: ((dx, dy, dz), distance) - normalized direction vector and Euclidean distance
    """
    try:
        # Get object handles
        quad = sim.getObject('/Quadcopter')
        vic = sim.getObject('/Victim')

        # Get positions
        qx, qy, qz = sim.getObjectPosition(quad, -1)
        vx, vy, vz = sim.getObjectPosition(vic, -1)

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