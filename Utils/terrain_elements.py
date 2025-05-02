import math
import random
from Utils.physics_utils import set_collision_properties

FLOOR_THICKNESS = 0.5

def create_floor(sim, area_size):
    size = [area_size, area_size, FLOOR_THICKNESS]
    floor = sim.createPrimitiveShape(sim.primitiveshape_cuboid, size, 0)
    # Floor is the only element that needs collision enabled
    set_collision_properties(sim, floor, enable_collision=True)
    sim.setShapeColor(floor, None, sim.colorcomponent_ambient_diffuse, [0.2, 0.5, 0.2])  # green
    sim.setObjectPosition(floor, -1, [0, 0, FLOOR_THICKNESS/2])
    sim.setObjectAlias(floor, "DisasterFloor")
    return floor

import math
import random

FLOOR_THICKNESS = 0.5

def create_tree(sim, position, fallen=True, trunk_len=None, tilt_angle=0.0):
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
    trunk = sim.createPrimitiveShape(
        sim.primitiveshape_cylinder,
        [trunk_rad*2, trunk_rad*2, trunk_len],
        0
    )
    sim.setShapeColor(trunk, None, sim.colorcomponent_ambient_diffuse, [0.4, 0.27, 0.14])  # brown
    # Disable collisions for trunk
    set_collision_properties(sim, trunk, enable_collision=False)
    
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

    sim.setObjectPosition(trunk, -1, [x, y, z])
    sim.setObjectOrientation(trunk, -1, [roll, pitch, yaw])
    sim.setObjectAlias(trunk, f"{'Fallen' if fallen else 'Standing'}Tree_{trunk}")
    
    # 5) Add realistic tree crown to standing trees (if not a stump)
    if not fallen and trunk_len > 0.6:  # Only add crown to taller trees
        # Create a crown dummy as a container for all foliage elements
        crown_dummy = sim.createDummy(0.05)
        sim.setObjectAlias(crown_dummy, f"TreeCrownGroup_{trunk}")
        sim.setObjectParent(crown_dummy, trunk, True)
        
        # Position the crown dummy at the top quarter of the trunk
        crown_base_height = trunk_len * 0.75
        sim.setObjectPosition(crown_dummy, trunk, [0, 0, crown_base_height])
        
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
            foliage = sim.createPrimitiveShape(
                sim.primitiveshape_spheroid,
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
            sim.setShapeColor(foliage, None, sim.colorcomponent_ambient_diffuse, cluster_color)
            transparency = 0.2 + random.uniform(0, 0.2)  # 0.2-0.4 transparency
            sim.setShapeColor(foliage, None, sim.colorcomponent_transparency, [transparency])
            
            # Make the foliage non-collidable
            set_collision_properties(sim, foliage, enable_collision=False)
            
            # Position the foliage cluster relative to the crown dummy
            sim.setObjectPosition(foliage, crown_dummy, [pos_x, pos_y, pos_z])
            sim.setObjectAlias(foliage, f"LeafCluster_{i}_{foliage}")
            
            # Attach the foliage to the crown dummy
            sim.setObjectParent(foliage, crown_dummy, True)
            
        # Add a small branch connection between trunk and crown
        if trunk_len > 1.5:  # Only for taller trees
            branch_connector = sim.createPrimitiveShape(
                sim.primitiveshape_cone,
                [trunk_rad * 3, trunk_rad * 3, crown_width * 0.6],
                0
            )
            sim.setShapeColor(branch_connector, None, sim.colorcomponent_ambient_diffuse, [0.3, 0.2, 0.1])  # darker brown
            
            # Position at the top of trunk, as a visual connection to the crown
            sim.setObjectPosition(branch_connector, trunk, [0, 0, crown_base_height - (crown_width * 0.3)])
            sim.setObjectParent(branch_connector, trunk, True)
        
        tree_objects.append(crown_dummy)
    
    return tree_objects[0]  # Return trunk for backward compatibility

def create_rock(sim, position, size):
    dims = [size, size, size * 0.8]
    rock = sim.createPrimitiveShape(sim.primitiveshape_spheroid, dims, 0)
    # Disable collisions for rock
    set_collision_properties(sim, rock, enable_collision=False)
    sim.setShapeColor(rock, None, sim.colorcomponent_ambient_diffuse, [0.5, 0.5, 0.5])  # gray
    sim.setObjectPosition(rock, -1, [
        position[0],
        position[1],
        FLOOR_THICKNESS + dims[2]/2
    ])
    sim.setObjectOrientation(rock, -1, [
        random.uniform(0, math.pi/6),
        random.uniform(0, math.pi/6),
        random.uniform(-math.pi, math.pi)
    ])
    sim.setObjectAlias(rock, f"Rock_{rock}")
    return rock

def create_victim(sim, position=(0, 0), size=(0.3, 0.1, 1.2)):
    """
    Create a thin red disc representing the victim.
    Just a flat circular marker on the ground.
    """
    # create a flat disc of 0.5m diameter and 0.1m thickness
    dims = [0.5, 0.5, 0.1]
    victim = sim.createPrimitiveShape(sim.primitiveshape_cylinder, dims, 0)
    sim.setObjectAlias(victim, "Victim")
    # Disable collisions for victim
    set_collision_properties(sim, victim, enable_collision=False)
    sim.setShapeColor(victim, None, sim.colorcomponent_ambient_diffuse, [1.0, 0.2, 0.2])  # red

    x, y = position
    # Place the disc just slightly above the floor to avoid z-fighting
    z = FLOOR_THICKNESS + 0.01  
    sim.setObjectPosition(victim, -1, [x, y, z])
    sim.setObjectOrientation(victim, -1, [0, 0, 0])  # flat on ground

    return victim

def create_ground_foliage(sim, position, size_range=(0.05, 0.15)):
    """
    Create a small cluster of ground foliage (grass, small plants, etc.)
    """
    # Randomize size within the provided range
    size = random.uniform(size_range[0], size_range[1])
    
    # Create a cone shape for the foliage
    height = size * random.uniform(1.0, 2.0)  # Taller than wide
    foliage = sim.createPrimitiveShape(
        sim.primitiveshape_cone if random.random() < 0.6 else sim.primitiveshape_spheroid, 
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
    sim.setShapeColor(foliage, None, sim.colorcomponent_ambient_diffuse, color)
    
    # Add some transparency
    transparency = random.uniform(0.0, 0.3)
    sim.setShapeColor(foliage, None, sim.colorcomponent_transparency, [transparency])
    
    # Position at the provided location, just above ground level
    x, y = position
    sim.setObjectPosition(foliage, -1, [x, y, FLOOR_THICKNESS + (height/3)])
    
    # Random orientation for variation, but keep mostly upright
    tilt = random.uniform(0, math.pi/8)  # Small tilt angle (0-22.5 degrees)
    tilt_direction = random.uniform(0, math.pi*2)
    
    sim.setObjectOrientation(foliage, -1, [
        tilt * math.cos(tilt_direction),
        tilt * math.sin(tilt_direction),
        random.uniform(0, math.pi*2)  # Random rotation around vertical axis
    ])
    
    # Non-collidable
    set_collision_properties(sim, foliage, enable_collision=False)
    sim.setObjectAlias(foliage, f"GroundFoliage_{foliage}")
    
    return foliage

def create_bush(sim, position, size_range=(0.3, 0.8)):
    """
    Create a larger bush or shrub with more complex structure.
    
    Args:
        sim: Simulation handle
        position: (x, y) tuple for base position
        size_range: (min, max) range for bush size
    
    Returns:
        bush_group: The main bush handle
    """
    # Create a group to contain the bush elements
    bush_group = sim.createDummy(0.01)
    sim.setObjectAlias(bush_group, f"BushGroup_{bush_group}")
    
    # Determine bush size
    bush_size = random.uniform(size_range[0], size_range[1])
    
    # Position the bush group
    x, y = position
    sim.setObjectPosition(bush_group, -1, [x, y, FLOOR_THICKNESS])
    
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
        trunk = sim.createPrimitiveShape(
            sim.primitiveshape_cylinder,
            [trunk_radius*2, trunk_radius*2, trunk_height],
            0
        )
        sim.setShapeColor(trunk, None, sim.colorcomponent_ambient_diffuse, [0.35, 0.25, 0.12])
        # Disable collisions for trunk
        set_collision_properties(sim, trunk, enable_collision=False)
        sim.setObjectPosition(trunk, bush_group, [0, 0, trunk_height/2])
        sim.setObjectParent(trunk, bush_group, True)
        
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
        foliage = sim.createPrimitiveShape(
            sim.primitiveshape_spheroid,
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
        sim.setShapeColor(foliage, None, sim.colorcomponent_ambient_diffuse, cluster_color)
        transparency = 0.1 + random.uniform(0, 0.2)  # 0.1-0.3 transparency
        sim.setShapeColor(foliage, None, sim.colorcomponent_transparency, [transparency])
        
        # Position the foliage cluster relative to the bush group
        sim.setObjectPosition(foliage, bush_group, [pos_x, pos_y, pos_z])
        sim.setObjectAlias(foliage, f"BushCluster_{i}_{foliage}")
        
        # Make the foliage partially collidable
        set_collision_properties(sim, foliage, enable_collision=False)
        
        # Attach the foliage to the bush group
        sim.setObjectParent(foliage, bush_group, True)
    
    return bush_group
