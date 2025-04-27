# Controls/typing_mode_handler.py

def register_typing_mode_handler(event_manager, keyboard_manager):
    def on_key_pressed(key):
        if key == '\r' or key == '\n':  # ENTER pressed
            if not keyboard_manager.in_typing_mode():
                print("[TypingModeHandler] Entering typing mode...")
                keyboard_manager.typing_mode = True
            else:
                print("[TypingModeHandler] Exiting typing mode...")
                keyboard_manager.typing_mode = False

    event_manager.subscribe('keyboard/key_pressed', on_key_pressed)
