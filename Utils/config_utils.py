# Utils/config_utils.py

# ─── Editable Fields ───
FIELDS = [
    {"key": "area_size",         "desc": "Area size [m]",           "type": float},
    {"key": "num_trees",         "desc": "Number of trees",          "type": int},
    {"key": "fraction_standing", "desc": "Fraction standing trees", "type": float},
    {"key": "num_rocks",         "desc": "Number of rocks",          "type": int},
    {"key": "num_bushes",        "desc": "Number of bushes",         "type": int},
    {"key": "num_foliage",       "desc": "Ground foliage clusters",  "type": int},
    {"key": "clear_zone_radius", "desc": "Clear zone radius [m]",    "type": float},
    {"key": "move_step",         "desc": "Drone move step [m]",      "type": float},
    {"key": "rotate_step_deg",   "desc": "Drone rotate step [deg]",  "type": float},
    {"key": "verbose",           "desc": "Verbose mode (toggle)",    "type": bool},
    {"key": "drone_spawn_margin", "desc": "Drone spawn margin [m]",    "type": float},
    {"key": "optimized_creation", "desc": "Use optimized creation", "type": bool},
    {"key": "include_rocks",           "desc": "Include rocks", "type": bool},
    {"key": "include_standing_trees", "desc": "Include standing trees", "type": bool},
    {"key": "include_fallen_trees",   "desc": "Include fallen trees",  "type": bool},
    {"key": "include_bushes",          "desc": "Include bushes", "type": bool},
    {"key": "include_foliage",         "desc": "Include ground foliage", "type": bool},
    {"key": "batch_size",              "desc": "Batch size for scene creation", "type": int},
]

# ─── Get Default Config ───
def get_default_config():
    return {
        "area_size": 10.0,
        "num_trees": 5,
        "fraction_standing": 0.85,
        "num_rocks": 5,
        "num_bushes": 5,
        "num_foliage": 5,
        "clear_zone_center": (0, 0),
        "clear_zone_radius": 0.5,
        "verbose": True,
        "move_step": 0.2,
        "rotate_step_deg": 10.0,
        "drone_spawn_margin": 1.0,
        "optimized_creation": True,
        "include_rocks": True,
        "include_standing_trees": True,
        "include_fallen_trees": True,
        "include_bushes": True,
        "include_foliage": True,
        "batch_size": 10,
    }