# Managers/menu_system.py

import sys
from Core.event_manager import EventManager
from Managers.menu_manager import MenuManager
from Menus.main_menu import MainMenu
from Menus.config_menu import ConfigMenu
from Managers.typing_mode_manager import TypingModeManager

class MenuSystem:
    def __init__(self, event_manager: EventManager, keyboard_manager, sim, config: dict, sim_command_queue):
        self.event_manager = event_manager
        self.keyboard_manager = keyboard_manager
        self.config = config
        self.sim = sim
        self.sim_queue = sim_command_queue

        self.menu_manager = MenuManager()
        self.active_menu = 'menu/main'
        self.typing_manager = TypingModeManager(event_manager, keyboard_manager)
        self._suppress_open = False

        # Register menus
        self.menu_manager.register('menu/main', MainMenu(self.event_manager, self.sim, self.config, self.sim_queue))
        self.menu_manager.register('menu/config', ConfigMenu(self.config, self.event_manager))

        # Subscribe to key & typing events
        self.event_manager.subscribe('keyboard/key_pressed', self._on_raw_key)
        self.event_manager.subscribe('typing/command_ready', self._on_command)
        self.event_manager.subscribe('typing/exit', self._on_exit)

        # Allow menu transitions from handlers
        self.event_manager.subscribe('menu/change', self._on_menu_change)

    def _on_raw_key(self, key: str):
        if self.keyboard_manager.in_typing_mode():
            return
        if key in ('\r', '\n'):
            if self._suppress_open:
                self._suppress_open = False
            else:
                self.open_chat()

    def _on_command(self, cmd: str):
        self.keyboard_manager.finish_typing(cmd)
        menu = self.menu_manager.get(self.active_menu)
        next_menu = menu.on_command(cmd)
        if next_menu:
            self.active_menu = next_menu
            self.menu_manager.show_menu(self.active_menu)

    def _on_exit(self, _):
        self.keyboard_manager.finish_typing('')
        print("\n[MenuSystem] Exited chat mode.")
        self._suppress_open = True

    def _on_menu_change(self, next_menu: str):
        self.active_menu = next_menu
        self.menu_manager.show_menu(next_menu)

    def open_chat(self):
        self.keyboard_manager.typing_mode = True
        print("[MenuSystem] Entered chat mode. Type your command and press ENTER.")
        self.menu_manager.show_menu(self.active_menu)
        self.typing_manager.start_typing()
