# Managers/main_menu.py

from Interfaces.menu_interface import MenuInterface
from Utils.scene_utils import clear_disaster_area, restart_disaster_area
from Managers.scene_manager import create_scene
import sys

class MainMenu(MenuInterface):
    def __init__(self, event_manager, sim, config, sim_queue):
        self.event_manager = event_manager
        self.sim = sim
        self.config = config
        self.sim_queue = sim_queue

        # Register self to listen to events
        self.event_manager.subscribe('menu/selected', self._on_menu_selected)

        self.entries = [
            ('1', 'Create disaster area', self._handle_create),
            ('2', 'Add dynamic flying objects', self._handle_dynamic),
            ('3', 'Restart disaster area', self._handle_restart),
            ('4', 'Clear disaster area', self._handle_clear),
            ('9', 'Modify configuration', lambda: 'menu/config'),
            ('q', 'Quit', self._handle_quit),
        ]

    def on_open(self):
        print("\n[Main Menu]")
        for key, desc, _ in self.entries:
            print(f"  {key} - {desc}")

    def on_command(self, cmd: str):
        for key, _, handler in self.entries:
            if cmd == key:
                return handler()
        print("[MainMenu] Unknown command.")
        return None

    def _handle_create(self):
        self.sim_queue.put((create_scene, [self.config], {}))
        return None

    def _handle_restart(self):
        self.sim_queue.put((restart_disaster_area, [self.config], {}))
        return None

    def _handle_clear(self):
        self.sim_queue.put((clear_disaster_area, [], {}))
        return None

    def _handle_dynamic(self):
        print("[MainMenu] Dynamic objects feature not yet implemented.")
        return None

    def _handle_quit(self):
        print("[MainMenu] Quit requested.")
        # signal application to quit via event
        self.event_manager.publish('app/quit', None)
        return None

    def _on_menu_selected(self, cmd: str):
        """
        Handles events like `event_manager.publish("menu/selected", "1")`.
        """
        for key, _, handler in self.entries:
            if cmd == key:
                result = handler()
                if isinstance(result, str):
                    self.event_manager.publish("menu/change", result)
                return
        print("[MainMenu] Unknown command via event.")
