# Managers/menu_manager.py

from Interfaces.menu_interface import MenuInterface
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

logger = get_logger()

class MenuManager:
    def __init__(self):
        self.menus = {}
        logger.info("MenuManager", "Initializing menu manager")

    def register(self, name: str, menu: MenuInterface):
        self.menus[name] = menu
        logger.debug_at_level(DEBUG_L1, "MenuManager", f"Registered menu: '{name}'")

    def get(self, name: str) -> MenuInterface:
        menu = self.menus.get(name)
        if menu is None:
            logger.warning("MenuManager", f"Menu '{name}' not found")
        else:
            logger.debug_at_level(DEBUG_L2, "MenuManager", f"Retrieved menu: '{name}'")
        return menu

    def show_menu(self, name: str):
        menu = self.get(name)
        if menu:
            logger.info("MenuManager", f"Opening menu: '{name}'")
            menu.on_open()
        else:
            logger.error("MenuManager", f"Failed to open menu '{name}' - not registered")
