# Utils/config_utils.py

def get_default_config():
    """
    Returns the default disaster scene configuration.
    """
    return {
        'area_size': 10.0,
        'num_trees': 25,
        'fraction_standing': 0.4,
        'num_rocks': 20,
        'clear_zone_center': (0, 0),
        'clear_zone_radius': 2.0
    }

def modify_config(config):
    """
    Menu-based config modification.
    Shows current values and lets user update one at a time.
    """
    while True:
        print("\n[Config Menu] Current configuration:")
        print(f"  1. Area size           : {config['area_size']} m")
        print(f"  2. Number of trees     : {config['num_trees']}")
        print(f"  3. Fraction standing   : {config['fraction_standing']}")
        print(f"  4. Number of rocks     : {config['num_rocks']}")
        print(f"  5. Clear zone radius   : {config['clear_zone_radius']} [m]")
        print( "  r. Return to main menu\n")

        choice = input("Select a setting to modify (0 to return): ").strip()

        if choice == '1':
            value = input("Enter new area size (float): ").strip()
            try:
                config['area_size'] = float(value)
            except ValueError:
                print("Invalid value.")
        elif choice == '2':
            value = input("Enter new number of trees (int): ").strip()
            try:
                config['num_trees'] = int(value)
            except ValueError:
                print("Invalid value.")
        elif choice == '3':
            value = input("Enter new fraction of standing trees (0.0–1.0): ").strip()
            try:
                config['fraction_standing'] = float(value)
            except ValueError:
                print("Invalid value.")
        elif choice == '4':
            value = input("Enter new number of rocks (int): ").strip()
            try:
                config['num_rocks'] = int(value)
            except ValueError:
                print("Invalid value.")
        elif choice == '5':
            value = input("Enter new clear zone radius (float): ").strip()
            try:
                config['clear_zone_radius'] = float(value)
            except ValueError:
                print("Invalid value.")
        elif choice == 'r':
            print("[Config Menu] Returning to main menu...")
            break
        else:
            print("Invalid choice. Please select 0–5.")