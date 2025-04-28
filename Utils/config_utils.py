# Utils/config_utils.py

# ─── Editable Fields ───
FIELDS = [
    {"key": "area_size",         "desc": "Area size [m]",           "type": float},
    {"key": "num_trees",         "desc": "Number of trees",          "type": int},
    {"key": "fraction_standing", "desc": "Fraction standing trees", "type": float},
    {"key": "num_rocks",         "desc": "Number of rocks",          "type": int},
    {"key": "clear_zone_radius", "desc": "Clear zone radius [m]",    "type": float},
    {"key": "move_step",         "desc": "Drone move step [m]",      "type": float},
    {"key": "rotate_step_deg",   "desc": "Drone rotate step [deg]",  "type": float},
    {"key": "verbose",           "desc": "Verbose mode (toggle)",    "type": bool},
]

# ─── Get Default Config ───
def get_default_config():
    return {
        "area_size": 10.0,
        "num_trees": 125,
        "fraction_standing": 0.85,
        "num_rocks": 55,
        "clear_zone_center": (0, 0),
        "clear_zone_radius": 0.5,
        "verbose": False,
        "move_step": 0.2,
        "rotate_step_deg": 10.0,
    }

# ─── Modify Config ───
def modify_config(config):
    def print_menu():
        print("\n[Config Menu] Current configuration:")
        for idx, field in enumerate(FIELDS, start=1):
            value = config.get(field["key"], "N/A")
            print(f"  {idx}. {field['desc']}: {value}")
        print(f"  {len(FIELDS)+1}. Return to main menu\n")

    def modify_field(index):
        field = FIELDS[index]
        key = field["key"]
        field_type = field["type"]

        if field_type == bool:
            config[key] = not config[key]
            print(f"[Config] {field['desc']} toggled to {config[key]}")
        else:
            prompt = f"Enter new value for {field['desc']}: "
            value = input(prompt).strip()
            try:
                config[key] = field_type(value)
                print(f"[Config] {field['desc']} updated to {config[key]}")
            except ValueError:
                print("[Config] Invalid input. Please enter correct type.")

    while True:
        print_menu()
        choice = input("Select a setting to modify: ").strip().lower()

        try:
            idx = int(choice) - 1
            if idx == len(FIELDS):
                print("[Config Menu] Returning to main menu...")
                break
            elif 0 <= idx < len(FIELDS):
                modify_field(idx)
            else:
                print("[Config Menu] Invalid selection.")
        except ValueError:
            print("[Config Menu] Please enter a number.")
