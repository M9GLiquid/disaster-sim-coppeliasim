# Managers/main_menu.py

from Managers.menu_interface import MenuInterface

class MainMenu(MenuInterface):
    def __init__(self, event_manager):
        self.event_manager = event_manager

    def on_open(self):
        print("\n[Main Menu]")
        print("  1 - Create disaster area")
        print("  2 - Add dynamic flying objects (birds & junk)")
        print("  3 - Restart disaster area")
        print("  4 - Clear disaster area")
        print("  9 - Modify configuration")
        print("  q - Quit")

    def on_command(self, cmd: str):
        if cmd == '9':
            return 'config'
        elif cmd in ('1', '2', '3', '4', 'q'):
            self.event_manager.publish('menu/selected', cmd)
        else:
            print("[MainMenu] Unknown command.")
        return None

    def on_exit(self):
        pass
