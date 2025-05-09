# target_mover.py
from Managers.Connections.sim_connection import SimConnection
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

SC = SimConnection.get_instance()
logger = get_logger()

class TargetMover:
    def __init__(self):
        self.target = SC.sim.getObject('/target')
        logger.info("TargetMover", "Initializing target movement controller")

        self.current_velocity = [0.0, 0.0, 0.0]  # dx, dy, dz
        self.current_yaw_rate = 0.0  # radians/sec

        self.response_speed = 10.0  # Higher = more aggressive response
        logger.debug_at_level(DEBUG_L1, "TargetMover", f"Response speed set to {self.response_speed}")

    def update(self, desired_velocity, desired_yaw_rate, dt):
        # Assuming caller holds the simulation lock
        pos = SC.sim.getObjectPosition(self.target, -1)
        ori = SC.sim.getObjectOrientation(self.target, -1)
        
        logger.debug_at_level(DEBUG_L3, "TargetMover", f"Current position: {pos}, orientation: {ori}")
        logger.debug_at_level(DEBUG_L3, "TargetMover", f"Desired velocity: {desired_velocity}, yaw rate: {desired_yaw_rate}")

        # Simple inertia model: move current velocity toward desired velocity
        for i in range(3):
            delta = desired_velocity[i] - self.current_velocity[i]
            self.current_velocity[i] += delta * min(self.response_speed * dt, 1.0)

        delta_yaw = desired_yaw_rate - self.current_yaw_rate
        self.current_yaw_rate += delta_yaw * min(self.response_speed * dt, 1.0)
        
        logger.debug_at_level(DEBUG_L3, "TargetMover", f"Updated velocity: {self.current_velocity}, yaw rate: {self.current_yaw_rate}")

        new_pos = [
            pos[0] + self.current_velocity[0] * dt,
            pos[1] + self.current_velocity[1] * dt,
            pos[2] + self.current_velocity[2] * dt
        ]
        new_ori = [
            ori[0],
            ori[1],
            ori[2] + self.current_yaw_rate * dt
        ]
        
        logger.debug_at_level(DEBUG_L3, "TargetMover", f"New position: {new_pos}, new orientation: {new_ori}")

        SC.sim.setObjectPosition(self.target, -1, new_pos)
        SC.sim.setObjectOrientation(self.target, -1, new_ori)
