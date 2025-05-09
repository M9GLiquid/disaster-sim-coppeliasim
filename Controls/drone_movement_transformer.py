# Controls/drone_movement_transformer.py

import math
from Controls.target_mover import TargetMover
from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

SC = SimConnection.get_instance()
logger = get_logger()

class DroneMovementTransformer:
    def __init__(self):
        target_handle = SC.sim.getObject('/target')
        self.drone_base = SC.sim.getObject('/Quadcopter/base')
        logger.info("DroneMovementTransformer", "Initializing movement transformer")
        logger.debug_at_level(DEBUG_L1, "DroneMovementTransformer", f"Target handle: {target_handle}, Drone base: {self.drone_base}")

        self.target_mover = TargetMover()

    def update(self, forward, sideward, upward, yaw_rate, dt):
        yaw = SC.sim.getObjectOrientation(self.drone_base, -1)[2]
        logger.debug_at_level(DEBUG_L3, "DroneMovementTransformer", f"Current yaw: {yaw}")

        dx = -forward * math.cos(yaw) - sideward * math.sin(yaw)
        dy = -forward * math.sin(yaw) + sideward * math.cos(yaw)
        dz = upward

        world_velocity = (dx, dy, dz)
        logger.debug_at_level(DEBUG_L3, "DroneMovementTransformer", f"Calculated world velocity: ({dx}, {dy}, {dz})")
        self.target_mover.update(world_velocity, yaw_rate, dt)
