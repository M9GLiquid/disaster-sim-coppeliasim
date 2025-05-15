import math
import random
from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

SC = SimConnection.get_instance()
logger = get_logger()

FLOOR_THICKNESS = 0.5

def does_object_exist_by_alias(alias):
    """
    Check if an object with the given alias exists in the scene.
    Simple implementation that returns None if the object doesn't exist.
    
    Args:
        alias: The alias to search for
    
    Returns:
        The object handle if found, None otherwise
    """
    # Direct approach - if this fails, it will propagate the error
    # which is preferable to silently failing
    handles = SC.sim.getObjectsInTree(SC.sim.handle_scene, SC.sim.handle_all, 0)
    
    for h in handles:
        # For each handle, check if it has the requested alias
        if SC.sim.getObjectAlias(h) == alias:
            return h
    
    # If we reach here, the object doesn't exist
    return None

def create_floor(area_size):
    # Check for an existing floor
    existing = does_object_exist_by_alias('DisasterFloor')
    if existing is not None:
        # Remove the existing floor so we can create a new one with the updated size
        SC.sim.removeObject(existing)
        
    # Create a new floor with the specified size
    size = [area_size, area_size, FLOOR_THICKNESS]
    floor = SC.sim.createPrimitiveShape(SC.sim.primitiveshape_cuboid, size, 0)
    # Floor is the only element that needs collision enabled
    SC.sim.setBoolProperty(floor, "collidable", True)
    SC.sim.setBoolProperty(floor, "respondable", False)
    SC.sim.setShapeColor(floor, None, SC.sim.colorcomponent_ambient_diffuse, [0.2, 0.5, 0.2])  # green
    SC.sim.setObjectPosition(floor, -1, [0, 0, FLOOR_THICKNESS/2])
    SC.sim.setObjectAlias(floor, "DisasterFloor")
    return floor

def create_tree(position, fallen=True, trunk_len=None, tilt_angle=0.0):
    """
    - fallen=True  → small broken log (0.5–1.0m) with 60/30/10° tilt distribution
    - fallen=False → stump (0.2–0.5m) or full tree (2.5–4.5m)
                     with 50% vertical, 30% lean 5–15°, 20% lean 15–30°
    """
    # 1) choose trunk length if not given
    if trunk_len is None:
        if fallen:
            trunk_len = random.uniform(0.5, 1.0)
        else:
            trunk_len = (random.uniform(0.2, 0.5)
                         if random.random() < 0.1
                         else random.uniform(2.5, 4.5))

    # 2) create cylinder
    trunk_rad = random.uniform(0.08, 0.12)
    trunk = SC.sim.createPrimitiveShape(
        SC.sim.primitiveshape_cylinder,
        [trunk_rad*2, trunk_rad*2, trunk_len],
        0
    )
    SC.sim.setShapeColor(trunk, None, SC.sim.colorcomponent_ambient_diffuse, [0.4, 0.27, 0.14])  # brown
    # Disable collisions for trunk
    SC.sim.setBoolProperty(trunk, "collidable", False)
    SC.sim.setBoolProperty(trunk, "respondable", False)
    
    # Tree objects to return
    tree_objects = [trunk]

    # 3) position
    x, y = position
    z = FLOOR_THICKNESS + (trunk_rad if fallen else trunk_len/2)

    # 4) compute tilt
    r = random.random()
    if fallen:
        if r < 0.45:
            deg = 90
        elif r < 0.75:
            deg = 80
        else:
            deg = 45
    else:
        if r < 0.4:
            deg = 0
        elif r < 0.75:
            deg = random.uniform(5.0, 15.0)
        else:
            deg = random.uniform(15.0, 30.0)

    tilt_rad = math.radians(deg)
    if fallen or deg > 0:
        # randomize direction of tilt in roll/pitch
        roll  = tilt_rad if random.random() < 0.5 else -tilt_rad
        pitch = tilt_rad if random.random() < 0.5 else -tilt_rad
    else:
        roll = pitch = 0.0

    yaw = random.uniform(-math.pi, math.pi)

    SC.sim.setObjectPosition(trunk, -1, [x, y, z])
    SC.sim.setObjectOrientation(trunk, -1, [roll, pitch, yaw])
    SC.sim.setObjectAlias(trunk, f"{'Fallen' if fallen else 'Standing'}Tree_{trunk}")
    
    # 5) Add realistic tree crown to standing trees (if not a stump)
    if not fallen and trunk_len > 0.6:  # Only add crown to taller trees
        # Create a crown dummy as a container for all foliage elements
        crown_dummy = SC.sim.createDummy(0.05)
        SC.sim.setObjectAlias(crown_dummy, f"TreeCrownGroup_{trunk}")
        SC.sim.setObjectParent(crown_dummy, trunk, True)
        
        # Position the crown dummy at the top quarter of the trunk
        crown_base_height = trunk_len * 0.75
        SC.sim.setObjectPosition(crown_dummy, trunk, [0, 0, crown_base_height])
        
        # Create multiple foliage clusters to form the crown
        crown_width = trunk_len * 0.6  # Adjust crown width based on trunk length
        cluster_count = random.randint(5, 9)  # Number of foliage clusters
        
        # Generate base color with some randomness
        base_r = 0.05 + random.uniform(0, 0.05)
        base_g = 0.25 + random.uniform(0, 0.15)
        base_b = 0.05 + random.uniform(0, 0.05)
        
        for i in range(cluster_count):
            # Vary the cluster sizes to create natural look
            cluster_size = random.uniform(0.3, 0.6) * crown_width
            
            # Create the foliage cluster with random position offset within the crown area
            angle = random.uniform(0, math.pi * 2)
            radius = random.uniform(0, crown_width * 0.7)
            height_offset = random.uniform(-0.3, 0.3) * crown_width
            
            # Calculate position offset from crown center
            pos_x = radius * math.cos(angle)
            pos_y = radius * math.sin(angle)
            pos_z = height_offset
            
            # Create slightly non-spherical foliage cluster
            stretch = random.uniform(0.8, 1.2)
            foliage = SC.sim.createPrimitiveShape(
                SC.sim.primitiveshape_spheroid,
                [cluster_size, cluster_size, cluster_size * stretch],
                0
            )
            
            # Vary the color slightly for each cluster
            color_variation = random.uniform(-0.05, 0.05)
            cluster_color = [
                base_r + color_variation,
                base_g + color_variation,
                base_b + color_variation
            ]
            
            # Set color and transparency
            SC.sim.setShapeColor(foliage, None, SC.sim.colorcomponent_ambient_diffuse, cluster_color)
            transparency = 0.2 + random.uniform(0, 0.2)  # 0.2-0.4 transparency
            SC.sim.setShapeColor(foliage, None, SC.sim.colorcomponent_transparency, [transparency])
            
            # Make the foliage non-collidable
            SC.sim.setBoolProperty(foliage, "collidable", False)
            SC.sim.setBoolProperty(foliage, "respondable", False)
            
            # Position the foliage cluster relative to the crown dummy
            SC.sim.setObjectPosition(foliage, crown_dummy, [pos_x, pos_y, pos_z])
            SC.sim.setObjectAlias(foliage, f"LeafCluster_{i}_{foliage}")
            
            # Attach the foliage to the crown dummy
            SC.sim.setObjectParent(foliage, crown_dummy, True)
            
        # Add a small branch connection between trunk and crown
        if trunk_len > 1.5:  # Only for taller trees
            branch_connector = SC.sim.createPrimitiveShape(
                SC.sim.primitiveshape_cone,
                [trunk_rad * 3, trunk_rad * 3, crown_width * 0.6],
                0
            )
            SC.sim.setShapeColor(branch_connector, None, SC.sim.colorcomponent_ambient_diffuse, [0.3, 0.2, 0.1])  # darker brown
            
            # Position at the top of trunk, as a visual connection to the crown
            SC.sim.setObjectPosition(branch_connector, trunk, [0, 0, crown_base_height - (crown_width * 0.3)])
            SC.sim.setObjectParent(branch_connector, trunk, True)
        
        tree_objects.append(crown_dummy)
    
    return tree_objects[0]  # Return trunk for backward compatibility

def create_rock(position, size):
    dims = [size, size, size * 0.8]
    rock = SC.sim.createPrimitiveShape(SC.sim.primitiveshape_spheroid, dims, 0)
    # Disable collisions for rock
    SC.sim.setBoolProperty(rock, "collidable", False)
    SC.sim.setBoolProperty(rock, "respondable", False)
    SC.sim.setShapeColor(rock, None, SC.sim.colorcomponent_ambient_diffuse, [0.5, 0.5, 0.5])  # gray
    SC.sim.setObjectPosition(rock, -1, [
        position[0],
        position[1],
        FLOOR_THICKNESS + dims[2]/2
    ])
    SC.sim.setObjectOrientation(rock, -1, [
        random.uniform(0, math.pi/6),
        random.uniform(0, math.pi/6),
        random.uniform(-math.pi, math.pi)
    ])
    SC.sim.setObjectAlias(rock, f"Rock_{rock}")
    return rock

def create_victim(position=(0, 0), size=(0.3, 0.1, 1.2)):
    logger.debug_at_level(DEBUG_L3, "TerrainElements", f"create_victim called with position={position}")
    # Prevent duplicate victim creation: search scene tree for object alias
    existing = does_object_exist_by_alias('Victim')
    if existing is not None:
        logger.debug_at_level(DEBUG_L2, "TerrainElements", f"Found existing victim object with handle {existing}")
        existing_pos = SC.sim.getObjectPosition(existing, -1)
        logger.debug_at_level(DEBUG_L2, "TerrainElements", f"Existing victim position: {existing_pos}")
        
        # MODIFIED: Instead of just returning, update the existing victim's position
        # Check if the existing victim is already positioned correctly
        x, y = position
        z = FLOOR_THICKNESS + 0.05  # 5cm above ground to avoid z-fighting
        
        # Force update the position
        try:
            SC.sim.setObjectPosition(existing, -1, [x, y, z])
            new_pos = SC.sim.getObjectPosition(existing, -1)
            logger.debug_at_level(DEBUG_L2, "TerrainElements", f"Updated existing victim position to {new_pos}")
            
            # Try to reset the parent to -1 (scene root) to avoid hierarchy issues
            try:
                # Only change parent if it's not already at the scene root
                current_parent = SC.sim.getObjectParent(existing)
                if current_parent != -1:
                    logger.debug_at_level(DEBUG_L2, "TerrainElements", f"Removing existing victim from its current parent ({current_parent})")
                    SC.sim.setObjectParent(existing, -1, True)
            except Exception as e:
                logger.error("TerrainElements", f"Failed to reset victim parent: {e}")
                
            # Make sure it's visible with proper color
            try:
                SC.sim.setShapeColor(existing, None, SC.sim.colorcomponent_ambient_diffuse, [1.0, 1.0, 1.0])  # white
                SC.sim.setShapeColor(existing, None, SC.sim.colorcomponent_emission, [0.5, 0.5, 0.5])  # stronger glow
            except Exception as e:
                logger.error("TerrainElements", f"Failed to update victim colors: {e}")
                
        except Exception as e:
            logger.error("TerrainElements", f"Failed to update victim position: {e}")
        
        return existing
        
    # Create a disc with 1.0m diameter (0.5m radius)
    radius = 0.5  # radius (0.5m)
    height = 0.05  # Height/thickness of the disc - reduced for better visibility
    victim = SC.sim.createPrimitiveShape(SC.sim.primitiveshape_disc, [radius, radius, height], 0)
    logger.debug_at_level(DEBUG_L2, "TerrainElements", f"Created new victim object with handle {victim}")
    SC.sim.setObjectAlias(victim, "Victim")
    # Disable collisions for victim
    SC.sim.setBoolProperty(victim, "collidable", False)
    SC.sim.setBoolProperty(victim, "respondable", False)
    # Set color to white for better visibility
    SC.sim.setShapeColor(victim, None, SC.sim.colorcomponent_ambient_diffuse, [1.0, 1.0, 1.0])  # white
    
    # Set emission to make it glow slightly for better visibility in dark areas
    SC.sim.setShapeColor(victim, None, SC.sim.colorcomponent_emission, [0.5, 0.5, 0.5])  # stronger glow
    
    x, y = position
    # Place the disc slightly higher above the floor for better visibility
    z = FLOOR_THICKNESS + 0.05  # 5cm above ground to avoid z-fighting
    SC.sim.setObjectPosition(victim, -1, [x, y, z])
    actual_pos = SC.sim.getObjectPosition(victim, -1)
    logger.debug_at_level(DEBUG_L2, "TerrainElements", f"Set victim position to ({x}, {y}, {z}), actual position: {actual_pos}")
    SC.sim.setObjectOrientation(victim, -1, [0, 0, 0])  # flat on ground

    return victim

def create_ground_foliage(position, size_range=(0.05, 0.15)):
    """
    Create a small cluster of ground foliage (grass, small plants, etc.)
    """
    # Randomize size within the provided range
    size = random.uniform(size_range[0], size_range[1])
    
    # Create a cone shape for the foliage
    height = size * random.uniform(1.0, 2.0)  # Taller than wide
    foliage = SC.sim.createPrimitiveShape(
        SC.sim.primitiveshape_cone if random.random() < 0.6 else SC.sim.primitiveshape_spheroid, 
        [size, size, height],
        0
    )
    
    # Choose a shade of green with some variation
    if random.random() < 0.15:  # Some plants are flowers
        # Create some colorful flowers occasionally
        colors = [
            [0.8, 0.2, 0.2],  # Red
            [0.9, 0.8, 0.2],  # Yellow
            [0.6, 0.3, 0.8],  # Purple
            [1.0, 0.5, 0.0],  # Orange
        ]
        color = random.choice(colors)
    else:
        # Normal green vegetation with variation
        green_shade = random.uniform(0.25, 0.55)
        color = [0.05, green_shade, 0.05]
    
    # Set the color
    SC.sim.setShapeColor(foliage, None, SC.sim.colorcomponent_ambient_diffuse, color)
    
    # Add some transparency
    transparency = random.uniform(0.0, 0.3)
    SC.sim.setShapeColor(foliage, None, SC.sim.colorcomponent_transparency, [transparency])
    
    # Position at the provided location, just above ground level
    x, y = position
    SC.sim.setObjectPosition(foliage, -1, [x, y, FLOOR_THICKNESS + (height/3)])
    
    # Random orientation for variation, but keep mostly upright
    tilt = random.uniform(0, math.pi/8)  # Small tilt angle (0-22.5 degrees)
    tilt_direction = random.uniform(0, math.pi*2)
    
    SC.sim.setObjectOrientation(foliage, -1, [
        tilt * math.cos(tilt_direction),
        tilt * math.sin(tilt_direction),
        random.uniform(0, math.pi*2)  # Random rotation around vertical axis
    ])
    
    # Non-collidable
    SC.sim.setBoolProperty(foliage, "collidable", False)
    SC.sim.setBoolProperty(foliage, "respondable", False)
    SC.sim.setObjectAlias(foliage, f"GroundFoliage_{foliage}")
    
    return foliage

def create_bush(position, size_range=(0.3, 0.8)):
    """
    Create a larger bush or shrub with more complex structure.
    
    Args:
        position: (x, y) tuple for base position
        size_range: (min, max) range for bush size
    
    Returns:
        bush_group: The main bush handle
    """
    # Create a group to contain the bush elements
    bush_group = SC.sim.createDummy(0.01)
    SC.sim.setObjectAlias(bush_group, f"BushGroup_{bush_group}")
    
    # Determine bush size
    bush_size = random.uniform(size_range[0], size_range[1])
    
    # Position the bush group
    x, y = position
    SC.sim.setObjectPosition(bush_group, -1, [x, y, FLOOR_THICKNESS])
    
    # Determine how many foliage clusters to create
    cluster_count = random.randint(3, 7)
    
    # Generate base color with some randomness
    base_r = 0.05 + random.uniform(0, 0.1)
    base_g = 0.3 + random.uniform(0, 0.2)
    base_b = 0.05 + random.uniform(0, 0.1)
    
    # Create a small trunk/stem base sometimes
    if random.random() < 0.7:
        trunk_height = bush_size * 0.3
        trunk_radius = bush_size * 0.08
        trunk = SC.sim.createPrimitiveShape(
            SC.sim.primitiveshape_cylinder,
            [trunk_radius*2, trunk_radius*2, trunk_height],
            0
        )
        SC.sim.setShapeColor(trunk, None, SC.sim.colorcomponent_ambient_diffuse, [0.35, 0.25, 0.12])
        # Disable collisions for trunk
        SC.sim.setBoolProperty(trunk, "collidable", False)
        SC.sim.setBoolProperty(trunk, "respondable", False)
        SC.sim.setObjectPosition(trunk, bush_group, [0, 0, trunk_height/2])
        SC.sim.setObjectParent(trunk, bush_group, True)
        
    # Create multiple foliage clusters to form the bush
    for i in range(cluster_count):
        # Vary the cluster sizes to create natural look
        cluster_size = random.uniform(0.3, 0.6) * bush_size
        
        # Create position offset from bush center
        angle = random.uniform(0, math.pi * 2)
        radius = random.uniform(0, bush_size * 0.4)
        height = bush_size * 0.4 + random.uniform(0, bush_size * 0.6)
        
        # Calculate position
        pos_x = radius * math.cos(angle)
        pos_y = radius * math.sin(angle)
        pos_z = height
        
        # Create slightly non-spherical foliage cluster
        stretch_v = random.uniform(0.8, 1.2)
        stretch_h = random.uniform(0.8, 1.2)
        foliage = SC.sim.createPrimitiveShape(
            SC.sim.primitiveshape_spheroid,
            [cluster_size * stretch_h, cluster_size * stretch_h, cluster_size * stretch_v],
            0
        )
        
        # Vary the color slightly for each cluster
        color_variation = random.uniform(-0.05, 0.05)
        
        # Occasional flowering bush
        if random.random() < 0.15:
            # Create some colorful flower bushes
            flower_colors = [
                [0.8, 0.2, 0.2],  # Red
                [0.9, 0.8, 0.2],  # Yellow
                [0.6, 0.3, 0.8],  # Purple
                [1.0, 0.5, 0.0],  # Orange
                [1.0, 0.7, 0.8],  # Pink
            ]
            cluster_color = random.choice(flower_colors)
        else:
            # Normal green bush with variation
            cluster_color = [
                base_r + color_variation,
                base_g + color_variation,
                base_b + color_variation
            ]
        
        # Set color and transparency
        SC.sim.setShapeColor(foliage, None, SC.sim.colorcomponent_ambient_diffuse, cluster_color)
        transparency = 0.1 + random.uniform(0, 0.2)  # 0.1-0.3 transparency
        SC.sim.setShapeColor(foliage, None, SC.sim.colorcomponent_transparency, [transparency])
        
        # Position the foliage cluster relative to the bush group
        SC.sim.setObjectPosition(foliage, bush_group, [pos_x, pos_y, pos_z])
        SC.sim.setObjectAlias(foliage, f"BushCluster_{i}_{foliage}")
        
        # Make the foliage partially collidable
        SC.sim.setBoolProperty(foliage, "collidable", False)
        SC.sim.setBoolProperty(foliage, "respondable", False)
        
        # Attach the foliage to the bush group
        SC.sim.setObjectParent(foliage, bush_group, True)
    
    return bush_group
