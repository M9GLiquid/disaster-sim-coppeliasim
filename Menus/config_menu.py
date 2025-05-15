# Managers/config_menu.py

from Interfaces.menu_interface import MenuInterface
from Utils.config_utils import FIELDS
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

EM = EventManager.get_instance()
logger = get_logger()

class ConfigMenu(MenuInterface):
    def __init__(self, config: dict):
        self.config = config
        self.fields = FIELDS
        self.logger = get_logger()

    def on_open(self):
        self.logger.info("ConfigMenu", "Current configuration:")
        for idx, field in enumerate(self.fields, start=1):
            value = self.config.get(field["key"], "N/A")
            self.logger.info("ConfigMenu", f"  {idx}. {field['desc']}: {value}")
        self.logger.info("ConfigMenu", f"  {len(self.fields) + 1}. Return to main menu")

    def on_command(self, cmd: str):
        try:
            idx = int(cmd) - 1
            if idx == len(self.fields):
                self.on_exit()
                return 'main'
            elif 0 <= idx < len(self.fields):
                self._modify_field(idx)
            else:
                self.logger.warning("ConfigMenu", "Invalid selection.")
        except ValueError:
            self.logger.warning("ConfigMenu", "Please enter a number.")
        return None

    def _modify_field(self, index: int):
        field = self.fields[index]
        key = field["key"]
        field_type = field["type"]

        if field_type is bool:
            self.config[key] = not self.config[key]
            self.logger.info("ConfigMenu", f"{field['desc']} toggled to {self.config[key]}")
        else:
            val = input(f"Enter new value for {field['desc']}: ").strip()
            try:
                self.config[key] = field_type(val)
                self.logger.info("ConfigMenu", f"{field['desc']} updated to {self.config[key]}")
                EM.publish("config/updated", key)
            except ValueError:
                self.logger.error("ConfigMenu", "Invalid input. Please enter correct type.")

    def on_exit(self):
        self.logger.info("ConfigMenu", "Returning to main menu.")
