# Controls/movement_manager.py

import queue

class MovementManager:
    def __init__(self, event_manager):
        self._move_q   = queue.Queue()
        self._rot_q    = queue.Queue()
        event_manager.subscribe('keyboard/move',   self._on_move)
        event_manager.subscribe('keyboard/rotate', self._on_rotate)

    def _on_move(self, delta):
        self._move_q.put(delta)

    def _on_rotate(self, delta):
        self._rot_q.put(delta)

    def get_moves(self):
        moves = []
        while not self._move_q.empty():
            moves.append(self._move_q.get())
        return moves

    def get_rotates(self):
        rots = []
        while not self._rot_q.empty():
            rots.append(self._rot_q.get())
        return rots
