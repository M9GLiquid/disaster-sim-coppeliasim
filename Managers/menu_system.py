# Managers/menu_system.py

from Core.event_manager             import EventManager
from Managers.menu_manager          import MenuManager
from Menus.main_menu                import MainMenu
from Menus.config_menu              import ConfigMenu
from Managers.typing_mode_manager   import TypingModeManager

class MenuSystem:
    def __init__(self, event_manager: EventManager, keyboard_manager, config: dict):
        self.event_manager    = event_manager
        self.keyboard_manager = keyboard_manager
        self.config           = config

        self.menu_manager   = MenuManager()
        self.active_menu    = 'main'
        self.typing_manager = TypingModeManager(event_manager, keyboard_manager)
        self._suppress_open = False

        # Register menus
        self.menu_manager.register('main',   MainMenu(self.event_manager))
        self.menu_manager.register('config', ConfigMenu(self.config, self.event_manager))

        # Subscribe to key events
        self.event_manager.subscribe('keyboard/key_pressed', self._on_raw_key)
        self.event_manager.subscribe('typing/command_ready', self._on_command)
        self.event_manager.subscribe('typing/exit',          self._on_exit)

    def _on_raw_key(self, key: str):
        # If in typing mode, don’t auto-open
        if self.keyboard_manager.in_typing_mode():
            return

        # ENTER outside typing ⇒ open chat, unless suppressed
        if key in ('\r', '\n'):
            if self._suppress_open:
                self._suppress_open = False
            else:
                self.open_chat()

    def _on_command(self, cmd: str):
        # finish typing and handle the command
        self.keyboard_manager.finish_typing(cmd)
        menu = self.menu_manager.get(self.active_menu)
        next_menu = menu.on_command(cmd)
        if next_menu:
            self.active_menu = next_menu
            self.menu_manager.show_menu(self.active_menu)

    def _on_exit(self, _):
        # empty ENTER or ESC: exit chat & suppress the next ENTER
        self.keyboard_manager.finish_typing('')
        print("\n[MenuSystem] Exited chat mode.")
        self._suppress_open = True

    def open_chat(self):
        """Show the active menu and enter typing mode."""
        self.keyboard_manager.typing_mode = True
        print("[MenuSystem] Entered chat mode. Type your command and press ENTER.")
        self.menu_manager.show_menu(self.active_menu)
        self.typing_manager.start_typing()