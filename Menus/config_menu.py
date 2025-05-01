# Managers/config_menu.py

from Interfaces.menu_interface import MenuInterface
from Utils.config_utils import FIELDS

class ConfigMenu(MenuInterface):
    def __init__(self, config: dict, event_manager):
        self.config = config
        self.event_manager = event_manager
        self.fields = FIELDS

    def on_open(self):
        print("\n[Config Menu] Current configuration:")
        for idx, field in enumerate(self.fields, start=1):
            value = self.config.get(field["key"], "N/A")
            print(f"  {idx}. {field['desc']}: {value}")
        print(f"  {len(self.fields) + 1}. Return to main menu")

    def on_command(self, cmd: str):
        try:
            idx = int(cmd) - 1
            if idx == len(self.fields):
                self.on_exit()
                return 'main'
            elif 0 <= idx < len(self.fields):
                self._modify_field(idx)
            else:
                print("[ConfigMenu] Invalid selection.")
        except ValueError:
            print("[ConfigMenu] Please enter a number.")
        return None

    def _modify_field(self, index: int):
        field = self.fields[index]
        key = field["key"]
        field_type = field["type"]

        if field_type is bool:
            self.config[key] = not self.config[key]
            print(f"[ConfigMenu] {field['desc']} toggled to {self.config[key]}")
        else:
            val = input(f"Enter new value for {field['desc']}: ").strip()
            try:
                self.config[key] = field_type(val)
                print(f"[ConfigMenu] {field['desc']} updated to {self.config[key]}")
                self.event_manager.publish("config/updated", None)
            except ValueError:
                print("[ConfigMenu] Invalid input. Please enter correct type.")

    def on_exit(self):
        print("[ConfigMenu] Returning to main menu.")
