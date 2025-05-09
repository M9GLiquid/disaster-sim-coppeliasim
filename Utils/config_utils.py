# Utils/config_utils.py

import re
from Utils.log_utils import get_logger

logger = get_logger()

# Group config fields by category
CONFIG_GROUPS = [
    {
        "name": "Environment",
        "fields": [
            {"key": "area_size", "desc": "Area size [m]", "type": float, "tooltip": "Size of the disaster area in meters"},
            {"key": "clear_zone_radius", "desc": "Clear zone radius [m]", "type": float, "tooltip": "Radius of area kept clear of objects"},
            {"key": "clear_zone_center", "desc": "Clear zone center (x,y)", "type": str, "tooltip": "Center coordinates of the clear zone"},
            {"key": "drone_height", "desc": "Initial drone height [m]", "type": float, "tooltip": "Starting height of the drone"},
            {"key": "drone_spawn_margin", "desc": "Drone spawn margin [m]", "type": float, "tooltip": "Margin from area edge for drone spawning"},
        ]
    },
    {
        "name": "Number of elements",
        "fields": [
            {"key": "num_rocks", "desc": "Rocks", "type": int, "tooltip": "Number of rock objects in the scene"},
            {"key": "num_trees", "desc": "Trees", "type": int, "tooltip": "Total number of trees in the scene"},
            {"key": "num_bushes", "desc": "Bushes", "type": int, "tooltip": "Number of bush objects in the scene"},
            {"key": "num_foliage", "desc": "Foliage clusters", "type": int, "tooltip": "Number of foliage clusters on the ground"},
            {"key": "fraction_standing", "desc": "Fraction standing trees", "type": float, "tooltip": "Fraction of trees that are standing (0-1)"},
        ]
    },
    {
        "name": "Object Inclusion",
        "fields": [
            {"key": "include_rocks", "desc": "Rocks", "type": bool, "tooltip": "Whether to include rocks in the scene"},
            {"key": "include_standing_trees", "desc": "Standing trees", "type": bool, "tooltip": "Whether to include standing trees"},
            {"key": "include_fallen_trees", "desc": "Fallen trees and logs", "type": bool, "tooltip": "Whether to include fallen trees and logs"},
            {"key": "include_bushes", "desc": "Bushes", "type": bool, "tooltip": "Whether to include bushes"},
            {"key": "include_foliage", "desc": "Ground foliage", "type": bool, "tooltip": "Whether to include ground foliage"},
        ]
    },
    {
        "name": "Drone Controls",
        "fields": [
            {"key": "move_step", "desc": "Move step [m]", "type": float, "tooltip": "Distance the drone moves in a single step"},
            {"key": "rotate_step_deg", "desc": "Rotate step [deg]", "type": float, "tooltip": "Degrees the drone rotates in a single step"},
        ]
    },
    {
        "name": "Data Collection",
        "fields": [
            {"key": "dataset_capture_frequency", "desc": "Capture frequency", "type": int, "tooltip": "Frequency of dataset captures (in frames)"},
            {"key": "victim_detection_threshold", "desc": "Victim detection [m]", "type": float, "tooltip": "Distance threshold for victim detection"},
            {"key": "batch_size", "desc": "Batch size", "type": int, "tooltip": "Batch size for scene creation and data collection"},
        ]
    },
    {
        "name": "System",
        "fields": [
            {"key": "verbose", "desc": "Verbose mode", "type": bool, "tooltip": "Enable detailed logging"},
            {"key": "optimized_creation", "desc": "Use optimized creation", "type": bool, "tooltip": "Use optimized scene creation process"},
            {"key": "colored_output", "desc": "Colored console output", "type": bool, "tooltip": "Enable colored logging in console"},
        ]
    },
]

# Get Default Config
def get_default_config():
    config = {
        "area_size": 10.0,
        "num_trees": 5,
        "fraction_standing": 0.85,
        "num_rocks": 5,
        "num_bushes": 5,
        "num_foliage": 5,
        "clear_zone_center": "(0, 0)",
        "clear_zone_radius": 0.5,
        "verbose": False,
        "move_step": 0.2,
        "rotate_step_deg": 10.0,
        "drone_spawn_margin": 1.0,
        "drone_height": 1.5,
        "optimized_creation": True,
        "include_rocks": True,
        "include_standing_trees": True,
        "include_fallen_trees": True,
        "include_bushes": True,
        "include_foliage": True,
        "batch_size": 10,
        "dataset_capture_frequency": 5,
        "victim_detection_threshold": 2.0,
        "colored_output": True,
    }
    logger.debug_at_level(2, "ConfigUtils", "Created default configuration")
    return config

# Parse tuple format from string like "(0, 0)" to actual tuple
def parse_coordinate_tuple(value):
    if isinstance(value, tuple):
        return value
    if isinstance(value, str):
        match = re.search(r'\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)', value)
        if match:
            parsed_value = (float(match.group(1)), float(match.group(2)))
            logger.debug_at_level(3, "ConfigUtils", f"Parsed coordinates: {value} -> {parsed_value}")
            return parsed_value
    logger.error("ConfigUtils", f"Invalid format for coordinates: {value}")
    raise ValueError("Invalid format for coordinates. Use (x, y)")