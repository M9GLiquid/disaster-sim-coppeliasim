# Utils/physics_utils.py

"""
Centralized physics engine settings and optimizations specifically for Bullet engine.
These functions help optimize performance while maintaining simulation accuracy.
"""

def configure_bullet_engine(sim, config=None):
    """
    Optimizes the Bullet physics engine settings for better performance.
    
    Args:
        sim: The simulation handle
        config: Optional configuration dictionary with physics-specific settings
    """
    if config is None:
        config = {}
    
    try:
        # Check if we're using a physics engine that supports these settings
        using_bullet = False
        if hasattr(sim, 'getEngineInfo'):
            engine_info = sim.getEngineInfo()
            using_bullet = ('bullet' in engine_info.lower())
            print(f"[Physics] Using engine: {engine_info}")
        
        # Bullet-specific optimizations
        if using_bullet:
            # Set global physics settings for performance
            if hasattr(sim, 'setFloatParam'):
                # Increase the physics time step for faster simulation
                # Default is 0.005 (5ms), we use a larger value for performance
                time_step = config.get('physics_timestep', 0.01)  # 10ms
                sim.setFloatParam(sim.floatparam_simulation_time_step, time_step)
                
                # Adjust physics accuracy vs performance trade-off
                accuracy = config.get('physics_accuracy', 0.01)  # Lower values = faster but less accurate
                if hasattr(sim, 'setEngineFloatParameter'):
                    sim.setEngineFloatParameter(sim.enginefloatparam_bullet_constraintsolveriteration, 2)  # Default is 4
                
                # Set gravity (optional)
                gravity = config.get('physics_gravity', -9.81)
                sim.setFloatParam(sim.floatparam_gravity_z, gravity)
            
            if hasattr(sim, 'setBoolParam'):
                # Disable full physics updates for non-visible objects
                sim.setBoolParam(sim.boolparam_full_model_load_in_visuals_thread, False)
                
                # Hierarchical culling for better performance
                sim.setBoolParam(sim.boolparam_viewport_culling, True)
                
            print("[Physics] Bullet physics engine configured for optimized performance")
        else:
            print("[Physics] Not using Bullet physics engine, using default settings")
            
    except Exception as e:
        print(f"[Physics] Error configuring physics engine: {e}")

def optimize_scene_physics(sim, scene_objects=None):
    """
    Optimizes physics for an entire scene or specific objects by:
    - Setting static objects to not participate in dynamics
    - Simplifying collision geometries
    - Grouping objects into entities where possible
    
    Args:
        sim: The simulation handle
        scene_objects: Optional list of object handles to optimize
    """
    try:
        # Handle all objects if none specified
        if scene_objects is None:
            scene_objects = []
            try:
                # Try to get all objects in the scene
                if hasattr(sim, 'getObjects'):
                    scene_objects = sim.getObjects()
            except Exception:
                pass
        
        # Apply physics optimizations to each object
        for obj in scene_objects:
            try:
                # Get object type to apply appropriate optimizations
                obj_type = sim.getObjectType(obj)
                obj_name = sim.getObjectAlias(obj)
                
                # Skip camera, light and target objects
                if ("camera" in obj_name.lower() or 
                    "light" in obj_name.lower() or 
                    "target" in obj_name.lower()):
                    continue
                
                # For static environmental elements, completely disable dynamics
                if ("floor" in obj_name.lower() or 
                    "rock" in obj_name.lower() or
                    "tree" in obj_name.lower() or
                    "bush" in obj_name.lower() or
                    "foliage" in obj_name.lower()):
                    disable_physics_for_object(sim, obj)
            except Exception:
                continue
                
        print(f"[Physics] Optimized physics for {len(scene_objects)} scene objects")
    except Exception as e:
        print(f"[Physics] Error during scene physics optimization: {e}")

def disable_physics_for_object(sim, object_handle):
    """
    Completely disables physics processing for an object to improve performance.
    More aggressive than just disabling collisions.
    
    Args:
        sim: The simulation handle
        object_handle: The object to disable physics for
    """
    try:
        # Get object info silently
        obj_name = "Unknown"
        obj_type = "Unknown"
        try:
            obj_name = sim.getObjectAlias(object_handle)
            obj_type = sim.getObjectType(object_handle)
            # Debug output removed
        except Exception:
            pass
            
        # Modern API (CoppeliaSim 4.9+)
        if hasattr(sim, 'setEngineBoolProperty'):
            # Disable dynamics/physics for the object
            sim.setEngineBoolProperty(sim.engineproperty_dynamics, object_handle, False)
            sim.setEngineBoolProperty(sim.engineproperty_respondable, object_handle, False)
            
            # Disable additional physics properties for the object if available
            try:
                if hasattr(sim, 'setEngineFloatProperty'):
                    # Set mass to 0
                    sim.setEngineFloatProperty(sim.enginefloatproperty_mass, object_handle, 0)
            except Exception:
                pass
        # Legacy API
        else:
            # Check which properties are supported
            for prop in ["collidable", "respondable", "dynamic"]:
                if _is_property_supported(sim, object_handle, prop):
                    sim.setBoolProperty(object_handle, prop, False)
    except Exception as e:
        print(f"[Physics] Error disabling physics for object {object_handle} ({obj_name}): {e}")

def set_collision_properties(sim, object_handle, enable_collision=False):
    """
    Centralized function to set collision properties on objects.
    
    Args:
        sim: Simulation handle
        object_handle: Handle to the object
        enable_collision: Whether to enable collision (default: False)
    """
    # Modern API (CoppeliaSim 4.9+)
    if hasattr(sim, 'setEngineBoolProperty'):
        # Only enable dynamics and collisions if specifically requested
        try:
            sim.setEngineBoolProperty(sim.engineproperty_dynamics, object_handle, enable_collision)
            sim.setEngineBoolProperty(sim.engineproperty_respondable, object_handle, enable_collision)
            
            # Set additional Bullet-specific collision parameters
            if hasattr(sim, 'setEngineFloatProperty') and not enable_collision:
                # For objects with disabled collision, explicitly set to 0
                sim.setEngineFloatProperty(sim.enginefloatproperty_friction, object_handle, 0)
                sim.setEngineFloatProperty(sim.enginefloatproperty_restitution, object_handle, 0)
                
            return  # Exit if using the modern API path successfully
        except Exception:
            # If modern API fails, fall back to legacy API
            pass
            
    # Legacy API with property checking approach
    try:
        obj_type = sim.getObjectType(object_handle)
    except Exception:
        obj_type = -1
        
    # Define properties to check based on object type
    properties_to_set = ["respondable", "collidable"]
    
    # Only add dynamic property for shape objects
    if obj_type == sim.object_shape_type:
        properties_to_set.append("dynamic")
    
    # Apply supported properties only
    for prop_name in properties_to_set:
        # Use a function to check property existence without storing unused values
        if _is_property_supported(sim, object_handle, prop_name):
            sim.setBoolProperty(object_handle, prop_name, enable_collision)

def _is_property_supported(sim, object_handle, property_name):
    """
    Helper function to check if a property is supported for an object.
    
    Args:
        sim: Simulation handle
        object_handle: Handle to the object
        property_name: Name of the property to check
        
    Returns:
        bool: True if property is supported, False otherwise
    """
    try:
        # Simply try to get the property, don't store the result
        sim.getBoolProperty(object_handle, property_name)
        return True
    except Exception as e:
        # print(f"[Physics Debug] Property check '{property_name}' failed: {e}")
        return False