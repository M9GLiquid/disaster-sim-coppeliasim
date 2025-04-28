# Controls/drone_control_manager.py

from Controls.drone_movement_transformer import DroneMovementTransformer

class DroneControlManager:
    def __init__(self, event_manager, sim):
        self._forward = 0.0
        self._sideward = 0.0
        self._upward = 0.0
        self._yaw_rate = 0.0

        self.camera_movement_controller = DroneMovementTransformer(sim)

        event_manager.subscribe('keyboard/move', self._on_move)
        event_manager.subscribe('keyboard/rotate', self._on_rotate)

    def _on_move(self, delta):
        dx, dy, dz = delta
        self._sideward += dx
        self._forward  += dy
        self._upward   += dz

    def _on_rotate(self, delta):
        self._yaw_rate += delta

    def update(self, dt):
        self.camera_movement_controller.update(self._forward, self._sideward, self._upward, self._yaw_rate, dt)
        self._forward = self._sideward = self._upward = self._yaw_rate = 0.0
