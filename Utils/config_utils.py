# Utils/config_utils.py

# ─── Editable Fields ───
FIELDS = [
    {"key": "area_size",         "desc": "Area size [m]",           "type": float},
    {"key": "num_trees",         "desc": "Number of trees",          "type": int},
    {"key": "fraction_standing", "desc": "Fraction standing trees", "type": float},
    {"key": "num_rocks",         "desc": "Number of rocks",          "type": int},
    {"key": "num_bushes",        "desc": "Number of bushes",         "type": int},
    {"key": "num_foliage",       "desc": "Ground foliage clusters",  "type": int},
    {"key": "num_birds",         "desc": "Number of birds",          "type": int},
    {"key": "num_falling_trees", "desc": "Number of falling trees",  "type": int},
    {"key": "tree_spawn_interval", "desc": "Tree spawn interval [s]", "type": float},
    {"key": "bird_speed",        "desc": "Bird movement speed",      "type": float},
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
    {"key": "rc_sensitivity",          "desc": "RC controller sensitivity", "type": float},
]

import os
import json
from Utils.log_utils import get_logger

# ─── Get Default Config ───
def get_default_config():
    config = {
        "area_size": 10.0,
        "num_trees": 5,
        "fraction_standing": 0.85,
        "num_rocks": 5,
        "num_bushes": 5,
        "num_foliage": 5,
        "num_birds": 10,           
        "num_falling_trees": 5,   
        "tree_spawn_interval": 30.0,
        "bird_speed": 1.0,
        "clear_zone_center": (0, 0),
        "clear_zone_radius": 0.5,
        "verbose": True,
        "move_step": 0.2,
        "rotate_step_deg": 15.0,
        "drone_spawn_margin": 1.0,
        "optimized_creation": True,
        "include_rocks": True,
        "include_standing_trees": True,
        "include_fallen_trees": True,
        "include_bushes": True,
        "include_foliage": True,
        "batch_size": 10,
        "rc_sensitivity": 10.0,
    }
    
    # Load saved RC controller settings and mappings if available
    config = load_rc_settings(config)
    
    return config

def load_rc_settings(config):
    """
    Load saved RC controller settings and mappings from Config directory and update the config
    
    Args:
        config: The config dictionary to update
        
    Returns:
        Updated config dictionary with loaded RC settings
    """
    logger = get_logger()
    
    try:
        # Get the Config directory path
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Config")
        
        # Load RC sensitivity and deadzone settings
        rc_settings_path = os.path.join(config_dir, "rc_settings.json")
        if os.path.exists(rc_settings_path):
            with open(rc_settings_path, "r") as f:
                rc_settings = json.load(f)
            
            # Update config with loaded settings
            if "sensitivity" in rc_settings:
                config["rc_sensitivity"] = rc_settings["sensitivity"]
            if "deadzone" in rc_settings:
                config["rc_deadzone"] = rc_settings["deadzone"]
            if "yaw_sensitivity" in rc_settings:
                config["rc_yaw_sensitivity"] = rc_settings["yaw_sensitivity"]
                
            logger.info("Config", f"Loaded RC settings: sensitivity={config.get('rc_sensitivity', 'N/A')}, "
                      f"deadzone={config.get('rc_deadzone', 'N/A')}, "
                      f"yaw_sensitivity={config.get('rc_yaw_sensitivity', 'N/A')}")
        
        # Load RC mappings
        rc_mapping_path = os.path.join(config_dir, "rc_mapping.json")
        if os.path.exists(rc_mapping_path):
            with open(rc_mapping_path, "r") as f:
                rc_mappings = json.load(f)
            
            # Update config with loaded mappings
            config["rc_mappings"] = rc_mappings
            logger.info("Config", f"Loaded RC mappings: {rc_mappings}")
    
    except Exception as e:
        logger.error("Config", f"Error loading RC settings: {e}")
    
    return config