# Controls/drone_keyboard_mapper.py

import math

def register_drone_keyboard_mapper(event_manager):
    MOVE_STEP = 0.1
    ROTATE_STEP = math.radians(10)

    def on_key_pressed(key):
        if key == 'w':
            event_manager.publish('keyboard/move', (0, MOVE_STEP, 0))
        elif key == 's':
            event_manager.publish('keyboard/move', (0, -MOVE_STEP, 0))
        elif key == 'a':
            event_manager.publish('keyboard/move', (-MOVE_STEP, 0, 0))
        elif key == 'd':
            event_manager.publish('keyboard/move', (MOVE_STEP, 0, 0))
        elif key == ' ':
            event_manager.publish('keyboard/move', (0, 0, MOVE_STEP))
        elif key == 'z':
            event_manager.publish('keyboard/move', (0, 0, -MOVE_STEP))
        elif key == 'q':
            event_manager.publish('keyboard/rotate', ROTATE_STEP)
        elif key == 'e':
            event_manager.publish('keyboard/rotate', -ROTATE_STEP)

    event_manager.subscribe('keyboard/key_pressed', on_key_pressed)
