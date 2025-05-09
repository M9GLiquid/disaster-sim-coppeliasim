# Controls/drone_keyboard_mapper.py

from Core.event_manager import EventManager
from Managers.keyboard_manager import KeyboardManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3
import math

EM = EventManager.get_instance()
KM = KeyboardManager.get_instance()
logger = get_logger()

def register_drone_keyboard_mapper(config):
    move_step = config.get('move_step', 0.2)
    rotate_step = math.radians(config.get('rotate_step_deg', 10.0))
    
    logger.info("DroneKeyboardMapper", "Registering drone keyboard controls")
    logger.debug_at_level(DEBUG_L1, "DroneKeyboardMapper", f"Move step: {move_step}, Rotate step: {rotate_step} rad")

    def on_key_pressed(key):
        if KM.in_typing_mode():
            logger.debug_at_level(DEBUG_L2, "DroneKeyboardMapper", f"Ignoring key {key} - typing mode active")
            return 

        if key == 'w':
            EM.publish('keyboard/move', (0, move_step, 0))
            logger.debug_at_level(DEBUG_L3, "DroneKeyboardMapper", "Forward movement")
        elif key == 's':
            EM.publish('keyboard/move', (0, -move_step, 0))
            logger.debug_at_level(DEBUG_L3, "DroneKeyboardMapper", "Backward movement")
        elif key == 'a':
            EM.publish('keyboard/move', (-move_step, 0, 0))
            logger.debug_at_level(DEBUG_L3, "DroneKeyboardMapper", "Left movement")
        elif key == 'd':
            EM.publish('keyboard/move', (move_step, 0, 0))
            logger.debug_at_level(DEBUG_L3, "DroneKeyboardMapper", "Right movement")
        elif key == ' ':
            EM.publish('keyboard/move', (0, 0, move_step))
            logger.debug_at_level(DEBUG_L3, "DroneKeyboardMapper", "Up movement")
        elif key == 'z':
            EM.publish('keyboard/move', (0, 0, -move_step))
            logger.debug_at_level(DEBUG_L3, "DroneKeyboardMapper", "Down movement")
        elif key == 'q':
            EM.publish('keyboard/rotate', rotate_step)
            logger.debug_at_level(DEBUG_L3, "DroneKeyboardMapper", "Rotate left")
        elif key == 'e':
            EM.publish('keyboard/rotate', -rotate_step)
            logger.debug_at_level(DEBUG_L3, "DroneKeyboardMapper", "Rotate right")

    EM.subscribe('keyboard/key_pressed', on_key_pressed)
    logger.debug_at_level(DEBUG_L1, "DroneKeyboardMapper", "Keyboard event subscriptions registered")
