# Controls/drone_movement_transformer.py

import math
from Controls.target_mover import TargetMover

class DroneMovementTransformer:
    def __init__(self, sim):
        self.sim = sim
        target_handle = sim.getObject('/target')
        self.drone_base = sim.getObject('/Quadcopter/base')

        self.target_mover = TargetMover(sim)

    def update(self, forward, sideward, upward, yaw_rate, dt):
        yaw = self.sim.getObjectOrientation(self.drone_base, -1)[2]

        dx = -forward * math.cos(yaw) - sideward * math.sin(yaw)
        dy = -forward * math.sin(yaw) + sideward * math.cos(yaw)
        dz = upward

        world_velocity = (dx, dy, dz)
        self.target_mover.update(world_velocity, yaw_rate, dt)
