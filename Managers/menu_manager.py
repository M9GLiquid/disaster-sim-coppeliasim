# Managers/menu_manager.py

from Interfaces.menu_interface import MenuInterface
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

class MenuManager:
    def __init__(self):
        self.menus = {}
        self.logger = get_logger()

    def register(self, name: str, menu: MenuInterface):
        self.menus[name] = menu

    def get(self, name: str) -> MenuInterface:
        return self.menus.get(name)

    def show_menu(self, name: str):
        menu = self.get(name)
        if menu:
            menu.on_open()
        else:
            self.logger.warning("MenuManager", f"No menu found for '{name}'.")
