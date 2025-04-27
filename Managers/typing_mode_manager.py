class TypingModeManager:
    def __init__(self, event_manager, keyboard_manager):
        self.event_manager     = event_manager
        self.keyboard_manager  = keyboard_manager
        self.current_buffer    = ""

        # Capture *every* key press
        self.event_manager.subscribe('keyboard/key_pressed', self._on_key_pressed)

    def _on_key_pressed(self, key):
        # ─────────── START TYPING ───────────
        if not self.keyboard_manager.in_typing_mode():
            # only ENTER kicks us into typing mode
            if key in ('\r', '\n'):
                self.keyboard_manager.typing_mode = True
            return

        # ─────────── COLLECT OR SUBMIT ───────────
        if key in ('\r', '\n'):
            # ENTER again => submit
            cmd = self.current_buffer.strip().lower()
            self.event_manager.publish('typing/command_ready', cmd)
            self.current_buffer = ""
            print("\n[TypingModeManager] Command submitted.")
        else:
            # buffer & echo
            self.current_buffer += key
            print(key, end='', flush=True)

    def start_typing(self):
        # called from main once typing_mode flips on
        self.current_buffer = ""
        print(">> ", end='', flush=True)
