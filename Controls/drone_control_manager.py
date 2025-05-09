# Controls/drone_control_manager.py

from Controls.drone_movement_transformer import DroneMovementTransformer
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3


EM = EventManager.get_instance()
logger = get_logger()

class DroneControlManager:
    def __init__(self):
        self._forward = 0.0
        self._sideward = 0.0
        self._upward = 0.0
        self._yaw_rate = 0.0

        logger.info("DroneControlManager", "Initializing drone control systems")
        self.camera_movement_controller = DroneMovementTransformer()

        EM.subscribe('keyboard/move', self._on_move)
        EM.subscribe('keyboard/rotate', self._on_rotate)
        EM.subscribe('simulation/frame', self._update)
        logger.debug_at_level(DEBUG_L1, "DroneControlManager", "Event subscriptions registered")

    def _on_move(self, delta):
        dx, dy, dz = delta
        self._sideward += dx
        self._forward  += dy
        self._upward   += dz
        logger.debug_at_level(DEBUG_L3, "DroneControlManager", f"Movement command received: dx={dx}, dy={dy}, dz={dz}")

    def _on_rotate(self, delta):
        self._yaw_rate += delta
        logger.debug_at_level(DEBUG_L3, "DroneControlManager", f"Rotation command received: delta={delta}")

    def _update(self, dt):
        logger.debug_at_level(DEBUG_L3, "DroneControlManager", f"Updating movement with dt={dt}")
        self.camera_movement_controller.update(
            self._forward, 
            self._sideward, 
            self._upward, 
            self._yaw_rate, 
            dt
        )
        self._forward = self._sideward = self._upward = self._yaw_rate = 0.0
