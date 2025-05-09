# Managers/config_menu.py

from Interfaces.menu_interface import MenuInterface
from Utils.config_utils import CONFIG_GROUPS
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

EM = EventManager.get_instance()
logger = get_logger()

class ConfigMenu(MenuInterface):
    def __init__(self, config: dict):
        self.config = config
        logger.info("ConfigMenu", "Initializing configuration menu")
        
        # Create a flattened list for the console interface
        self.fields = []
        for group in CONFIG_GROUPS:
            self.fields.extend(group['fields'])
        
        logger.debug_at_level(DEBUG_L2, "ConfigMenu", f"Initialized with {len(self.fields)} configuration fields")

    def on_open(self):
        logger.debug_at_level(DEBUG_L1, "ConfigMenu", "Opening configuration menu")
        print("\n[Config Menu] Current configuration:")
        
        # Display configurations by group
        for group_idx, group in enumerate(CONFIG_GROUPS, start=1):
            print(f"\n  --- {group['name']} ---")
            logger.debug_at_level(DEBUG_L2, "ConfigMenu", f"Displaying group {group_idx}: {group['name']}")
            
            # Display fields in this group
            field_start_idx = len(self.fields) if group_idx == 1 else sum(len(g['fields']) for g in CONFIG_GROUPS[:group_idx-1])
            for field_idx, field in enumerate(group['fields'], start=1):
                overall_idx = field_start_idx + field_idx
                key = field["key"]
                value = self.config.get(key, "N/A")
                print(f"  {overall_idx}. {field['desc']}: {value}")
                logger.debug_at_level(DEBUG_L3, "ConfigMenu", f"Field {overall_idx}: {key}={value}")
        
        print(f"\n  {len(self.fields) + 1}. Return to main menu")

    def on_command(self, cmd: str):
        logger.debug_at_level(DEBUG_L2, "ConfigMenu", f"Processing command: '{cmd}'")
        try:
            idx = int(cmd) - 1
            if idx == len(self.fields):
                logger.debug_at_level(DEBUG_L1, "ConfigMenu", "Exiting to main menu")
                self.on_exit()
                return 'main'
            elif 0 <= idx < len(self.fields):
                logger.debug_at_level(DEBUG_L1, "ConfigMenu", f"Modifying field at index {idx}")
                self._modify_field(idx)
            else:
                logger.debug_at_level(DEBUG_L1, "ConfigMenu", f"Invalid selection: {cmd}")
                print("[Config Menu] Invalid selection.")
        except ValueError:
            logger.debug_at_level(DEBUG_L1, "ConfigMenu", f"Non-numeric input: '{cmd}'")
            print("[Config Menu] Please enter a number.")
        return None

    def _modify_field(self, index: int):
        field = self.fields[index]
        key = field["key"]
        field_type = field["type"]
        tooltip = field.get("tooltip", "")
        
        logger.debug_at_level(DEBUG_L2, "ConfigMenu", f"Modifying field: {key}, current value: {self.config.get(key, 'N/A')}")

        if tooltip:
            print(f"[Config Menu] Info: {tooltip}")

        if field_type is bool:
            self.config[key] = not self.config[key]
            logger.debug_at_level(DEBUG_L1, "ConfigMenu", f"Toggled {key} to {self.config[key]}")
            print(f"[Config Menu] {field['desc']} toggled to {self.config[key]}")
            EM.publish("config/updated", key)
        else:
            val = input(f"Enter new value for {field['desc']}: ").strip()
            try:
                # Special handling for coordinate tuples
                if key == "clear_zone_center":
                    import re
                    match = re.search(r'\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)', val)
                    if match:
                        x, y = float(match.group(1)), float(match.group(2))
                        self.config[key] = (x, y)
                        logger.debug_at_level(DEBUG_L1, "ConfigMenu", f"Updated {key} to {self.config[key]}")
                        print(f"[Config Menu] {field['desc']} updated to {self.config[key]}")
                        EM.publish("config/updated", key)
                    else:
                        logger.debug_at_level(DEBUG_L1, "ConfigMenu", f"Invalid coordinate format: {val}")
                        print("[Config Menu] Invalid format for coordinates. Use (x, y)")
                else:
                    # Regular type conversion
                    self.config[key] = field_type(val)
                    logger.debug_at_level(DEBUG_L1, "ConfigMenu", f"Updated {key} to {self.config[key]}")
                    print(f"[Config Menu] {field['desc']} updated to {self.config[key]}")
                    EM.publish("config/updated", key)
            except ValueError:
                logger.debug_at_level(DEBUG_L1, "ConfigMenu", f"Invalid input for {key}: {val}")
                print("[Config Menu] Invalid input. Please enter correct type.")

    def on_exit(self):
        logger.debug_at_level(DEBUG_L1, "ConfigMenu", "Exiting configuration menu")
        print("[Config Menu] Returning to main menu.")
