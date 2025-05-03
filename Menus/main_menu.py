# Managers/main_menu.py

from Interfaces.menu_interface import MenuInterface
from Utils.scene_utils import clear_disaster_area, restart_disaster_area
from Managers.scene_progressive import create_scene_progressive
from Core.event_manager import EventManager

EM = EventManager.get_instance()

class MainMenu(MenuInterface):
    def __init__(self, config, sim_queue):
        self.config = config
        self.sim_queue = sim_queue

        # Register self to listen to events
        EM.subscribe('menu/selected', self._on_menu_selected)

        self.entries = [
            ('1', 'Create disaster area', self._handle_create),
            ('2', 'Add dynamic flying objects', self._handle_dynamic),
            ('3', 'Restart disaster area', self._handle_restart),
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
        print("[Main Menu] Unknown command.")
        return None

    def _handle_create(self):
        # Use event-based progressive scene creation instead of queued function
        EM.publish('scene/creation/request', self.config)
        return None

    def _handle_restart(self):
        self.sim_queue.put((restart_disaster_area, [self.config], {}))
        return None

    def _handle_clear(self):
        self.sim_queue.put((clear_disaster_area, [], {}))
        return None

    def _handle_dynamic(self):
        print("[Main Menu] Dynamic objects feature not yet implemented.")
        return None

    def _handle_quit(self):
        print("[Main Menu] Quit requested.")
        # signal application to quit via event
        EM.publish('simulation/shutdown', None)
        return None

    def _on_menu_selected(self, cmd: str):
        """
        Handles events like `event_manager.publish("menu/selected", "1")`.
        """
        for key, _, handler in self.entries:
            if cmd == key:
                result = handler()
                if isinstance(result, str):
                    EM.publish("menu/change", result)
                return
        print("[Main Menu] Unknown command via event.")
