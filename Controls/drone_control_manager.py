# Controls/drone_control_manager.py

from Controls.drone_movement_transformer import DroneMovementTransformer
from Core.event_manager import EventManager



EM = EventManager.get_instance()

class DroneControlManager:
    def __init__(self):
        self._forward = 0.0
        self._sideward = 0.0
        self._upward = 0.0
        self._yaw_rate = 0.0

        self.camera_movement_controller = DroneMovementTransformer()

        EM.subscribe('keyboard/move', self._on_move)
        EM.subscribe('keyboard/rotate', self._on_rotate)
        EM.subscribe('simulation/frame', self._update)

    def _on_move(self, delta):
        dx, dy, dz = delta
        self._sideward = dx
        self._forward = dy
        self._upward = dz


    def _on_rotate(self, delta):
        self._yaw_rate += delta

    def _update(self, dt):
        self.camera_movement_controller.update(
            self._forward,
            self._sideward,
            self._upward,
            self._yaw_rate,
            dt
        )

        # And then reset to zero
        self._forward = self._sideward = self._upward = self._yaw_rate = 0.0


        
    def reset_controls(self):
        self._forward = 0.0
        self._sideward = 0.0
        self._upward = 0.0
        self._yaw_rate = 0.0
