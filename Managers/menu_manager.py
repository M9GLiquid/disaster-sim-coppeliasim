# Managers/menu_manager.py

from Interfaces.menu_interface import MenuInterface

class MenuManager:
    def __init__(self):
        self.menus = {}

    def register(self, name: str, menu: MenuInterface):
        self.menus[name] = menu

    def get(self, name: str) -> MenuInterface:
        return self.menus.get(name)

    def show_menu(self, name: str):
        menu = self.get(name)
        if menu:
            menu.on_open()
        else:
            print(f"[MenuManager] No menu found for '{name}'.")
