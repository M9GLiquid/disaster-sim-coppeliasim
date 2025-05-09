import threading
import time
import sys
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

EM = EventManager.get_instance()
logger = get_logger()

class KeyboardManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Get or create the singleton KeyboardManager instance.
        """
        if cls._instance is None:
            cls._instance = KeyboardManager()
        return cls._instance
    
    def __init__(self):
        # Ensure only one instance is created
        if KeyboardManager._instance is not None:
            raise Exception("KeyboardManager already exists! Use KeyboardManager.get_instance() to get the singleton instance.")
            
        self.running = True
        self.typing_mode = False      # only used as a flag
        self.key_pressed = None
        self.last_command = None

        logger.info("KeyboardManager", "Initializing keyboard manager")
        self.thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        self.thread.start()
        logger.debug_at_level(DEBUG_L1, "KeyboardManager", "Keyboard monitoring thread started")
        
        KeyboardManager._instance = self

    def _keyboard_loop(self):
        try:
            import msvcrt  # Windows
            logger.debug_at_level(DEBUG_L1, "KeyboardManager", "Using Windows keyboard input method")
            while self.running:
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8')
                    self.key_pressed = key
                    logger.debug_at_level(DEBUG_L3, "KeyboardManager", f"Key pressed: {repr(key)}")
                    EM.publish('keyboard/key_pressed', key)
                time.sleep(0.01)
        except ImportError:
            # Unix-like system
            import tty
            import termios
            import select
            logger.debug_at_level(DEBUG_L1, "KeyboardManager", "Using Unix keyboard input method")
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while self.running:
                    dr, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if dr:
                        key = sys.stdin.read(1)
                        self.key_pressed = key
                        logger.debug_at_level(DEBUG_L3, "KeyboardManager", f"Key pressed: {repr(key)}")
                        EM.publish('keyboard/key_pressed', key)
                    time.sleep(0.01)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                logger.debug_at_level(DEBUG_L1, "KeyboardManager", "Restored terminal settings")

    def in_typing_mode(self):
        return self.typing_mode

    def finish_typing(self, command):
        self.last_command = command
        self.typing_mode = False
        logger.debug_at_level(DEBUG_L2, "KeyboardManager", f"Typing mode finished, command: {command}")

    def get_command(self):
        cmd = self.last_command
        self.last_command = None
        return cmd

    def stop(self):
        logger.info("KeyboardManager", "Stopping keyboard manager")
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
            logger.debug_at_level(DEBUG_L1, "KeyboardManager", "Keyboard thread joined successfully")
