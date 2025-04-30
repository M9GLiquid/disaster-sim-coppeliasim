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