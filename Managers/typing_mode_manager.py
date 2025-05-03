# Managers/typing_mode_manager.py
from Core.event_manager import EventManager
from Managers.keyboard_manager import KeyboardManager

EM = EventManager.get_instance()
KM = KeyboardManager.get_instance()

class TypingModeManager:
    def __init__(self):
        self.current_buffer   = ""

        # listen to every raw key
        EM.subscribe('keyboard/key_pressed', self._on_key)

    def _on_key(self, key: str):
        # only handle keys when in typing mode
        if not KM.in_typing_mode():
            return

        # ESC ⇒ exit immediately
        if key == '\x1b':  
            EM.publish('typing/exit', None)
            return

        # ENTER ⇒ either submit or exit
        if key in ('\r', '\n'):
            if self.current_buffer:
                cmd = self.current_buffer.strip().lower()
                EM.publish('typing/command_ready', cmd)
                self.current_buffer = ""
                print("\n[Chat] Command submitted.")
            else:
                # empty buffer: exit chat
                EM.publish('typing/exit', None)
            return

        # any other key: accumulate & echo
        self.current_buffer += key
        print(key, end='', flush=True)

    def start_typing(self):
        self.current_buffer = ""
        print(">> ", end='', flush=True)
