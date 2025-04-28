# Controls/drone_keyboard_mapper.py
import math

def register_drone_keyboard_mapper(event_manager, keyboard_manager, config):
    move_step = config.get('move_step', 0.2)
    rotate_step = math.radians(config.get('rotate_step_deg', 10.0))

    def on_key_pressed(key):
        if keyboard_manager.in_typing_mode():
            return 

        if key == 'w':
            event_manager.publish('keyboard/move', (0, move_step, 0))
        elif key == 's':
            event_manager.publish('keyboard/move', (0, -move_step, 0))
        elif key == 'a':
            event_manager.publish('keyboard/move', (-move_step, 0, 0))
        elif key == 'd':
            event_manager.publish('keyboard/move', (move_step, 0, 0))
        elif key == ' ':
            event_manager.publish('keyboard/move', (0, 0, move_step))
        elif key == 'z':
            event_manager.publish('keyboard/move', (0, 0, -move_step))
        elif key == 'q':
            event_manager.publish('keyboard/rotate', rotate_step)
        elif key == 'e':
            event_manager.publish('keyboard/rotate', -rotate_step)

    event_manager.subscribe('keyboard/key_pressed', on_key_pressed)
