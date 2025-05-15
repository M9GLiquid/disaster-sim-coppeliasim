# Controls/drone_movement_transformer.py

import math
from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

SC = SimConnection.get_instance()
logger = get_logger()

class DroneMovementTransformer:
    def __init__(self):
        self.target_handle = SC.sim.getObject('/target')
        self.drone_base = SC.sim.getObject('/Quadcopter/base')
        self.logger = get_logger()

    def update(self, forward, sideward, upward, yaw_rate, dt):
        # Get current rotation around Z axis (yaw)
        yaw = SC.sim.getObjectOrientation(self.drone_base, -1)[2]

        # Convert to world coordinates
        dx = -forward * math.cos(yaw) - sideward * math.sin(yaw)
        dy = -forward * math.sin(yaw) + sideward * math.cos(yaw)
        dz = upward

        # Calculate new position
        current_pos = SC.sim.getObjectPosition(self.target_handle, -1)
        new_pos = [
            current_pos[0] + dx * dt,
            current_pos[1] + dy * dt,
            current_pos[2] + dz * dt
        ]

        SC.sim.setObjectPosition(self.target_handle, -1, new_pos)

        # Calculate new rotation
        current_ori = SC.sim.getObjectOrientation(self.target_handle, -1)
        new_yaw = current_ori[2] + yaw_rate * dt
        SC.sim.setObjectOrientation(self.target_handle, -1, [current_ori[0], current_ori[1], new_yaw])

        # Debug output (optional)
        self.logger.debug_at_level(DEBUG_L3, "Movement", f"dx={dx:.3f}, dy={dy:.3f}, dz={dz:.3f}, yaw_rate={yaw_rate:.3f}")
