# Controls/keyboard_handlers.py

def register_keyboard_handlers(event_manager, sim, target_handle):
    def handle_move(delta):
        dx, dy, dz = delta
        sim.acquireLock()
        try:
            pos = sim.getObjectPosition(target_handle, -1)
            new_pos = [pos[0] + dx, pos[1] + dy, pos[2] + dz]
            sim.setObjectPosition(target_handle, -1, new_pos)
        finally:
            sim.releaseLock()

    def handle_rotate(delta_yaw):
        sim.acquireLock()
        try:
            orient = sim.getObjectOrientation(target_handle, -1)
            new_orient = list(orient)
            new_orient[2] += delta_yaw
            sim.setObjectOrientation(target_handle, -1, new_orient)
        finally:
            sim.releaseLock()

    event_manager.subscribe('keyboard/move', handle_move)
    event_manager.subscribe('keyboard/rotate', handle_rotate)
