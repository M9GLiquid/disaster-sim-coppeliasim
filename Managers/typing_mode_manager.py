# Managers/typing_mode_manager.py
from Core.event_manager import EventManager
from Managers.keyboard_manager import KeyboardManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

EM = EventManager.get_instance()
KM = KeyboardManager.get_instance()
logger = get_logger()

class TypingModeManager:
    def __init__(self):
        self.current_buffer = ""
        logger.info("TypingModeManager", "Initializing typing mode manager")

        # listen to every raw key
        EM.subscribe('keyboard/key_pressed', self._on_key)
        logger.debug_at_level(DEBUG_L1, "TypingModeManager", "Subscribed to keyboard events")

    def _on_key(self, key: str):
        # only handle keys when in typing mode
        if not KM.in_typing_mode():
            return

        # ESC ⇒ exit immediately
        if key == '\x1b':  
            logger.debug_at_level(DEBUG_L1, "TypingModeManager", "ESC pressed, exiting typing mode")
            EM.publish('typing/exit', None)
            return

        # ENTER ⇒ either submit or exit
        if key in ('\r', '\n'):
            if self.current_buffer:
                cmd = self.current_buffer.strip().lower()
                logger.debug_at_level(DEBUG_L1, "TypingModeManager", f"Command submitted: '{cmd}'")
                EM.publish('typing/command_ready', cmd)
                self.current_buffer = ""
                print("\n[Chat] Command submitted.")
            else:
                # empty buffer: exit chat
                logger.debug_at_level(DEBUG_L1, "TypingModeManager", "Empty command, exiting typing mode")
                EM.publish('typing/exit', None)
            return

        # any other key: accumulate & echo
        self.current_buffer += key
        logger.debug_at_level(DEBUG_L3, "TypingModeManager", f"Key added to buffer: '{key}', buffer now: '{self.current_buffer}'")
        print(key, end='', flush=True)

    def start_typing(self):
        self.current_buffer = ""
        logger.debug_at_level(DEBUG_L1, "TypingModeManager", "Starting typing mode")
        print(">> ", end='', flush=True)
