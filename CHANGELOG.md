# Changelog

All notable changes to the AI for Robotics project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html):
- MAJOR version (X) when making incompatible API changes
- MINOR version (Y) when adding functionality in a backward compatible manner
- PATCH version (Z) when making backward compatible bug fixes

## [V.0.9.0] - 2025-05-02

### Added
- New `teleport_quadcopter_to_edge()` function in scene_progressive.py that doesn't trigger physics optimization
- Created CHANGELOG.md to track project changes
- Added proper completion state tracking to ProgressiveSceneCreator
- Implemented event-driven scene creation architecture with dedicated event topics

### Fixed
- Fixed "property is unknown" error in physics_utils.py by using correct property names
- Fixed issue with physics optimization being triggered multiple times when teleporting the quadcopter
- Fixed ModuleNotFoundError after removing scene_manager.py by updating imports in dependent files
- Fixed bug causing repeated teleportation and physics optimization messages by adding proper completion state tracking
- Fixed code duplication in quadcopter teleportation by centralizing the functionality in a single function
- Fixed misleading function name by renaming `create_scene_threaded` to `create_scene_queued` to better reflect its actual behavior

### Changed
- Moved quadcopter teleportation to the beginning of scene creation process to prevent physics issues
- Improved property checking in physics_utils.py to verify support before attempting to set properties
- Removed unnecessary scene_manager.py facade to simplify the codebase
- Updated direct imports in main.py, depth_dataset_collector.py, and main_menu.py to reference source modules
- Updated copilot-agent-instructions.md with guidance for maintaining the changelog
- Modified scene creation update mechanism to respect completion state
- Refactored scene creation to use event system instead of global variables
- Enhanced create_scene and create_scene_threaded to publish events when event_manager is provided
- Refactored quadcopter teleportation code to eliminate duplication between scene_core.py and scene_progressive.py
- Renamed `create_scene_threaded` to `create_scene_queued` to better reflect its actual functionality

### Removed
- Deleted scene_manager.py facade module as it was redundant
- Removed global _active_creator variable in scene_progressive.py in favor of event-based communication