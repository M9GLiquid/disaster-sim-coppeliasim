# Controls/drone_keyboard_mapper.py

from Core.event_manager import EventManager
from Managers.keyboard_manager import KeyboardManager
import math

EM = EventManager.get_instance()
KM = KeyboardManager.get_instance()

def register_drone_keyboard_mapper(config):
    move_step = config.get('move_step', 0.2)
    rotate_step = math.radians(config.get('rotate_step_deg', 10.0))

    def on_key_pressed(key):
        if KM.in_typing_mode():
            return 

        if key == 'w':
            EM.publish('keyboard/move', (0, move_step, 0))
        elif key == 's':
            EM.publish('keyboard/move', (0, -move_step, 0))
        elif key == 'a':
            EM.publish('keyboard/move', (-move_step, 0, 0))
        elif key == 'd':
            EM.publish('keyboard/move', (move_step, 0, 0))
        elif key == ' ':
            EM.publish('keyboard/move', (0, 0, move_step))
        elif key == 'z':
            EM.publish('keyboard/move', (0, 0, -move_step))
        elif key == 'q':
            EM.publish('keyboard/rotate', rotate_step)
        elif key == 'e':
            EM.publish('keyboard/rotate', -rotate_step)

    EM.subscribe('keyboard/key_pressed', on_key_pressed)
