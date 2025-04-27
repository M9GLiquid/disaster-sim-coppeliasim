# Managers/menu_system.py

from Core.event_manager               import EventManager
from Managers.menu_manager            import MenuManager
from Managers.typing_mode_manager     import TypingModeManager
from Managers.keyboard_manager        import KeyboardManager
from Utils.config_utils               import modify_config

class MenuSystem:
    def __init__(self,
                 event_manager: EventManager,
                 keyboard_manager: KeyboardManager,
                 config: dict):
        self.event_manager    = event_manager
        self.keyboard_manager = keyboard_manager
        self.config           = config

        self.menu_manager   = MenuManager()
        self.typing_manager = TypingModeManager(event_manager, keyboard_manager)
        self.menu_active    = False

        # raw keys → decide to pop up menu
        self.event_manager.subscribe('keyboard/key_pressed', self._on_key)
        # complete line → dispatch or config‐edit
        self.event_manager.subscribe('typing/command_ready', self._on_cmd)

    def _on_key(self, key: str):
        # ENTER toggles us into typing/menu mode (once)
        if not self.keyboard_manager.in_typing_mode() and key in ('\r','\n'):
            self.keyboard_manager.typing_mode = True
            self.menu_manager.show_menu()
            self.typing_manager.start_typing()
            self.menu_active = True

    def _on_cmd(self, cmd: str):
        # 9 → open the config‐utils interactive menu
        if cmd == '9':
            modify_config(self.config)
            # finish chat‐mode
            self.keyboard_manager.finish_typing(cmd)
            self.menu_active = False
            return

        # otherwise hand back to main
        self.event_manager.publish('menu/selected', cmd)
        self.keyboard_manager.finish_typing(cmd)
        self.menu_active = False
