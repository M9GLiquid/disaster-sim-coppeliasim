# Managers/typing_mode_manager.py

class TypingModeManager:
    def __init__(self, event_manager, keyboard_manager):
        self.event_manager    = event_manager
        self.keyboard_manager = keyboard_manager
        self.current_buffer   = ""

        # listen to every raw key
        self.event_manager.subscribe('keyboard/key_pressed', self._on_key)

    def _on_key(self, key: str):
        # only handle keys when in typing mode
        if not self.keyboard_manager.in_typing_mode():
            return

        # ESC ⇒ exit immediately
        if key == '\x1b':  
            self.event_manager.publish('typing/exit', None)
            return

        # ENTER ⇒ either submit or exit
        if key in ('\r', '\n'):
            if self.current_buffer:
                cmd = self.current_buffer.strip().lower()
                self.event_manager.publish('typing/command_ready', cmd)
                self.current_buffer = ""
                print("\n[Chat] Command submitted.")
            else:
                # empty buffer: exit chat
                self.event_manager.publish('typing/exit', None)
            return

        # any other key: accumulate & echo
        self.current_buffer += key
        print(key, end='', flush=True)

    def start_typing(self):
        self.current_buffer = ""
        print(">> ", end='', flush=True)
