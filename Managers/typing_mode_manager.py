# Managers/typing_mode_manager.py

class TypingModeManager:
    def __init__(self, event_manager, keyboard_manager):
        self.event_manager    = event_manager
        self.keyboard_manager = keyboard_manager
        self.current_buffer   = ""

        # listen to every raw key
        self.event_manager.subscribe('keyboard/key_pressed', self._on_key)

    def _on_key(self, key: str):
        # ignore everything unless we’re in typing mode
        if not self.keyboard_manager.in_typing_mode():
            return

        if key in ('\r', '\n'):
            # ENTER pressed
            if self.current_buffer:
                # non‐empty: submit as command
                cmd = self.current_buffer.strip().lower()
                self.event_manager.publish('typing/command_ready', cmd)
                self.current_buffer = ""
                print("\n[TypingModeManager] Command submitted.")
            else:
                # empty buffer: exit chat
                self.event_manager.publish('typing/exit', None)
        else:
            # buffer & echo
            self.current_buffer += key
            print(key, end='', flush=True)

    def start_typing(self):
        # called when we first enter chat
        self.current_buffer = ""
        print(">> ", end='', flush=True)
