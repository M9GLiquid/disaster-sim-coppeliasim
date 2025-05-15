# Managers/main_menu.py

from Interfaces.menu_interface import MenuInterface
from Utils.scene_utils import restart_disaster_area
from Managers.scene_manager import create_scene, clear_scene
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

EM = EventManager.get_instance()
logger = get_logger()

class MainMenu(MenuInterface):
    def __init__(self, config, sim_queue):
        self.config = config
        self.sim_queue = sim_queue
        self.logger = get_logger()

        # Register self to listen to events
        EM.subscribe('menu/selected', self._on_menu_selected)

        self.entries = [
            ('1', 'Create disaster area', self._handle_create),
            ('2', 'Add dynamic flying objects', self._handle_dynamic),
            ('3', 'Restart disaster area', self._handle_restart),
            ('4', 'Clear area', self._handle_clear),
            ('9', 'Modify configuration', lambda: 'menu/config'),
            ('q', 'Quit', self._handle_quit),
        ]

    def on_open(self):
        self.logger.info("MainMenu", "Main Menu Options:")
        for key, desc, _ in self.entries:
            self.logger.info("MainMenu", f"  {key} - {desc}")

    def on_command(self, cmd: str):
        for key, _, handler in self.entries:
            if cmd == key:
                return handler()
        self.logger.warning("MainMenu", "Unknown command.")
        return None

    def _handle_create(self):
        # Use event-based scene creation
        create_scene(self.config)
        return None

    def _handle_restart(self):
        # Use event-based restart
        restart_disaster_area(self.config)
        return None

    def _handle_clear(self):
        # Use event-based clear
        clear_scene()
        return None

    def _handle_dynamic(self):
        self.logger.warning("MainMenu", "Dynamic objects feature not yet implemented.")
        return None

    def _handle_quit(self):
        self.logger.info("MainMenu", "Quit requested.")
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
        self.logger.warning("MainMenu", "Unknown command via event.")
