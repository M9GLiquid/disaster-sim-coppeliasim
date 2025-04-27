# dynamic_objects.py

import random
import math

def create_flying_bird(sim, idx, area_size):
    body_radius = random.uniform(0.13,0.18)
    x = random.uniform(-area_size/2*0.7, area_size/2*0.7)
    y = random.uniform(-area_size/2*0.7, area_size/2*0.7)
    z = random.uniform(2,4)
    bird_handle = sim.createPrimitiveShape(sim.primitiveshape_spheroid, [body_radius*1.2, body_radius, body_radius*0.8], 0)
    sim.setObjectPosition(bird_handle, -1, [x,y,z])
    sim.setObjectAlias(bird_handle, f"FlyingBird{idx:02d}")
    bird_color = random.choice([
        [0.2,0.2,0.4],      # dark bluish
        [0.25,0.20,0.09],   # brownish
        [0.12,0.10,0.09],   # blackish (crow/raven)
    ])
    sim.setShapeColor(bird_handle, None, sim.colorcomponent_ambient_diffuse, bird_color)
    sim.setObjectInt32Param(bird_handle, sim.shapeintparam_static, 0)
    speed = random.uniform(0.6,1.1)
    heading = random.uniform(0, 2*math.pi)
    vx = speed * math.cos(heading)
    vy = speed * math.sin(heading)
    vz = random.uniform(-0.1,0.2)
    sim.setObjectVelocity(bird_handle, [vx, vy, vz], [0,0,0])
    return bird_handle

def create_flying_junk(sim, idx, area_size):
    typ = random.choice(['box','can','bottle'])
    x = random.uniform(-area_size/2*0.7, area_size/2*0.7)
    y = random.uniform(-area_size/2*0.7, area_size/2*0.7)
    z = random.uniform(2, 4)
    if typ == 'box':
        size = random.uniform(0.13,0.21)
        handle = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [size,size*0.7,size*0.5], 0)
        sim.setShapeColor(handle, None, sim.colorcomponent_ambient_diffuse, [0.9,0.85,0.05])
    elif typ == 'can':
        r = random.uniform(0.05,0.08)
        length = random.uniform(0.15,0.25)
        handle = sim.createPrimitiveShape(sim.primitiveshape_cylinder, [r*2, r*2, length], 0)
        sim.setShapeColor(handle, None, sim.colorcomponent_ambient_diffuse, [0.8,0.1,0.1])
    else:
        r = random.uniform(0.04,0.07)
        length = random.uniform(0.18,0.25)
        handle = sim.createPrimitiveShape(sim.primitiveshape_cylinder, [r*2, r*2, length], 0)
        sim.setShapeColor(handle, None, sim.colorcomponent_ambient_diffuse, [0.1,0.6,0.9])
    sim.setObjectPosition(handle, -1, [x, y, z])
    sim.setObjectAlias(handle, f"FlyingJunk{idx:02d}")
    sim.setObjectInt32Param(handle, sim.shapeintparam_static, 0)
    speed = random.uniform(0.6,1.0)
    heading = random.uniform(0, 2*math.pi)
    vx = speed * math.cos(heading)
    vy = speed * math.sin(heading)
    vz = random.uniform(-0.1,0.3)
    sim.setObjectVelocity(handle, [vx, vy, vz], [0,0,0])
    return handle

def create_all_dynamic(sim, area_size, num_birds=1, num_junk=3):
    handles = []
    for i in range(num_birds):
        handles.append(create_flying_bird(sim, i, area_size))
    for i in range(num_junk):
        handles.append(create_flying_junk(sim, i, area_size))
    print(f"[DynamicObjects] {num_birds} birds, {num_junk} flying junk created (Area size {area_size}m).")
    return handles