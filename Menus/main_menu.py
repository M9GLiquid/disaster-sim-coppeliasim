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

        logger.info("MainMenu", "Initializing main menu")
        
        # Register self to listen to events
        EM.subscribe('menu/selected', self._on_menu_selected)
        logger.debug_at_level(DEBUG_L1, "MainMenu", "Subscribed to menu selection events")

        self.entries = [
            ('1', 'Create disaster area', self._handle_create),
            ('2', 'Add dynamic flying objects', self._handle_dynamic),
            ('3', 'Restart disaster area', self._handle_restart),
            ('4', 'Clear area', self._handle_clear),
            ('9', 'Modify configuration', lambda: 'menu/config'),
            ('q', 'Quit', self._handle_quit),
        ]
        logger.debug_at_level(DEBUG_L2, "MainMenu", f"Menu initialized with {len(self.entries)} options")

    def on_open(self):
        logger.debug_at_level(DEBUG_L1, "MainMenu", "Opening main menu")
        print("\n[Main Menu]")
        for key, desc, _ in self.entries:
            print(f"  {key} - {desc}")

    def on_command(self, cmd: str):
        logger.debug_at_level(DEBUG_L2, "MainMenu", f"Processing command: '{cmd}'")
        for key, _, handler in self.entries:
            if cmd == key:
                logger.debug_at_level(DEBUG_L1, "MainMenu", f"Executing command: '{cmd}'")
                return handler()
        logger.debug_at_level(DEBUG_L1, "MainMenu", f"Unknown command: '{cmd}'")
        print("[Main Menu] Unknown command.")
        return None

    def _handle_create(self):
        # Use event-based scene creation
        logger.debug_at_level(DEBUG_L1, "MainMenu", "Creating disaster area scene")
        create_scene(self.config)
        return None

    def _handle_restart(self):
        # Use event-based restart
        logger.debug_at_level(DEBUG_L1, "MainMenu", "Restarting disaster area")
        restart_disaster_area(self.config)
        return None

    def _handle_clear(self):
        # Use event-based clear
        logger.debug_at_level(DEBUG_L1, "MainMenu", "Clearing scene")
        clear_scene()
        return None

    def _handle_dynamic(self):
        logger.debug_at_level(DEBUG_L1, "MainMenu", "Dynamic objects feature requested (not implemented)")
        print("[Main Menu] Dynamic objects feature not yet implemented.")
        return None

    def _handle_quit(self):
        logger.info("MainMenu", "Quit requested, initiating shutdown")
        print("[Main Menu] Quit requested.")
        # signal application to quit via event
        EM.publish('simulation/shutdown', None)
        return None

    def _on_menu_selected(self, cmd: str):
        """
        Handles events like `event_manager.publish("menu/selected", "1")`.
        """
        logger.debug_at_level(DEBUG_L2, "MainMenu", f"Menu selection event received: '{cmd}'")
        for key, _, handler in self.entries:
            if cmd == key:
                logger.debug_at_level(DEBUG_L1, "MainMenu", f"Handling menu selection: '{cmd}'")
                result = handler()
                if isinstance(result, str):
                    logger.debug_at_level(DEBUG_L1, "MainMenu", f"Changing menu to: '{result}'")
                    EM.publish("menu/change", result)
                return
        logger.debug_at_level(DEBUG_L1, "MainMenu", f"Unknown menu selection via event: '{cmd}'")
        print("[Main Menu] Unknown command via event.")
