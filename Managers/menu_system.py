# Managers/menu_system.py

from Core.event_manager           import EventManager
from Managers.menu_manager        import MenuManager
from Managers.typing_mode_manager import TypingModeManager
from Managers.keyboard_manager    import KeyboardManager
from Utils.config_utils           import modify_config

class MenuSystem:
    def __init__(self,
                 event_manager: EventManager,
                 keyboard_manager: KeyboardManager,
                 config: dict):
        self.event_manager     = event_manager
        self.keyboard_manager  = keyboard_manager
        self.config            = config

        self.menu_manager      = MenuManager()
        self.typing_manager    = TypingModeManager(event_manager, keyboard_manager)
        self._suppress_open    = False    # NEW: flag to swallow next ENTER

        # ENTER to open; commands & empty-exit handled below
        self.event_manager.subscribe('keyboard/key_pressed',   self._on_raw_key)
        self.event_manager.subscribe('typing/command_ready',   self._on_command)
        self.event_manager.subscribe('typing/exit',            self._on_exit)

    def _on_raw_key(self, key: str):
        # only if not already in typing_mode, ENTER tries to open chat
        if not self.keyboard_manager.in_typing_mode() and key in ('\r', '\n'):
            if self._suppress_open:
                # swallow exactly one ENTER
                self._suppress_open = False
                return
            self.open_chat()

    def _on_command(self, cmd: str):
        # always finish typing first (clears typing_mode)
        self.keyboard_manager.finish_typing(cmd)

        if cmd == '9':
            # config submenu: run it, then re-open
            modify_config(self.config)
            self.open_chat()
            return

        if cmd == 'q':
            # quit chat & notify main, but do not re-open
            print("[MenuSystem] Exited chat mode.")
            self.event_manager.publish('menu/selected', cmd)
            return

        # any other command: hand off to main, do not re-open here
        self.event_manager.publish('menu/selected', cmd)

    def _on_exit(self, _):
        # empty ENTER: exit chat and suppress the very next ENTER
        self.keyboard_manager.finish_typing('')
        print("[MenuSystem] Exited chat mode.")
        self._suppress_open = True

    def open_chat(self):
        """Show the menu and prompt, and enter typing mode."""
        self.keyboard_manager.typing_mode = True
        self.menu_manager.show_menu()
        self.typing_manager.start_typing()
