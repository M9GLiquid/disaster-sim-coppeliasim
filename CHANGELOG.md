## [V.1.4.2]

### Added
- Automatic scene restart after episode end: When an episode finishes, the simulation now automatically restarts the scene using the same configuration, following the publisher-subscriber pattern and project architecture.
- Logging for automatic scene restarts and configuration reuse in EpisodeManager.

### Changed
- EpisodeManager now publishes the scene creation event (`scene/start_creation`) with the config directly as event data after episode end, ensuring correct scene re-initialization.
- Refactored EpisodeManager to store and reuse the scene configuration for subsequent restarts.

### Removed
- Removed dead and redundant config/restart logic from EpisodeManager and related modules.

### Changed
- (Placeholder for V1.4.0: details should be filled in based on the actual commit.)

## [V.1.4.1] - 2025-05-26

### Fixed
- Prevented unintended dataset saving on application shutdown by suppressing EPISODE_END event during shutdown. Dataset saving now only occurs on explicit episode completion.
- Fixed frame-logging callback not being unsubscribed on scene creation cancel, preventing errors when simulation objects are missing.

## [V1.4.0] - 2024-05-26

### Changed
- (Details for this release should be filled in based on the actual commit, as the message only contains the version bump.)

## [V.1.3.0] - 2025-05-26

### Added
- Asynchronous, episode-based dataset collection: Each episode is saved as a single .npz file in a unique session folder (e.g., data/20250526_025014/train or val).
- 90/10 train/val split: Each episode is randomly assigned to train (90%) or val (10%) and saved in the corresponding subfolder.
- Unique dataset folder per run: All data for a session is stored in a timestamped folder (e.g., data/20250526_025014), with no 'depth_dataset' in the name.
- Robust logging for episode saving, split assignment, and async file operations.

### Changed
- Removed all batch-based dataset logic in favor of episode-based saving.
- Refactored DepthDatasetCollector to support async episode saving and session-based folder structure.
- Updated directory structure for datasets to improve organization and reproducibility.

### Fixed
- Ensured all episode save threads are joined on shutdown for data integrity.
- Improved error handling and logging for episode data saving.

## [V.1.2.1] - 2023-09-20

### Added
- Added detailed comments to the notebook code for better documentation
- Added comprehensive function and class docstrings for improved code readability

### Changed
- Moved the notebook from root directory to Notebooks/ folder for better project organization 
- Updated .gitignore to ignore all notebook files

## [V.1.2.0] - 2023-05-17

### Added
- Added command-line argument support for verbose mode (`--verbose`)
- Added semi-transparent popup notification system for configuration changes
- Added temporary visual feedback when settings are changed
- Added automatic window resizing when switching to Status tab
- Added comprehensive verbose logging for important system events
- Added centralized logging system with file output support
- Added command-line options for log level control and file logging
- Added log directory configuration option
- Added detailed debug level guidelines in log_utils.py to standardize logging across modules

### Improved
- Improved configuration UI with instant-apply settings that update immediately
- Improved Status tab with larger radar display for better victim visualization
- Improved verbose output to focus on important system events while reducing noise
- Improved scene manager error reporting and status updates
- Improved error handling with centralized logging facility
- Improved debugging capability with optional file-based logging
- Improved shutdown sequence with proper logger cleanup
- Improved lock acquisition/release logging in lock_utils.py

### Changed
- Changed default verbose setting to false for cleaner standard output
- Changed console output to use structured logging format
- Changed print statements to use centralized logger throughout codebase
- Changed debug levels in terrain_elements.py for consistency with logging guidelines

### Fixed
- Fixed verbose flag behavior to properly enable/disable based on command-line argument
- Fixed configuration UI showing notifications when field loses focus but value hasn't changed
- Fixed "invalid command name" error during shutdown when UI callbacks are triggered after window closure
- Fixed incomplete event unsubscription that could cause memory leaks and errors
- Fixed inconsistent debug logging levels in Utils folder for better log clarity

### Removed
- Removed redundant "Apply All Changes" button from configuration UI
- Removed unnecessary print statements replaced with appropriate logger calls

## [V.1.1.2] - 2023-07-25

### Added
- Added enhanced configuration UI with grouped settings
- Added tooltips for all configuration options
- Added "Reset to Defaults" button in config UI
- Added missing configurations:
  - `dataset_capture_frequency` - Controls data capture frequency
  - `victim_detection_threshold` - Sets threshold for victim detection alarms
  - `clear_zone_center` - Center point for clear zone
  - `drone_height` - Initial drone height

### Changed
- Reorganized configuration system to use categorical groups
- Improved validation and error handling for configuration inputs
- Enhanced visual feedback for configuration changes using status bar
- Improved command-line config menu with grouped categories

### Fixed
- Fixed coordinate tuple parsing for clear_zone_center
- Fixed type validation for configuration values
- Improved error messages for invalid configuration inputs
- Fixed teleportation error related to getObjectPropertiesInfo method
- Fixed batch_size not being updated when changed through configuration UI
- Fixed object inclusion settings not being respected (include_rocks, include_standing_trees, etc.)

## [V.1.1.1] - 2023-07-24

### Added
- Added new CameraManager singleton class to handle vision sensors through the event system
- Added capture_rgb function in Utils/capture_utils.py to properly capture and flip RGB images
- Added automatic sensor removal for invalid vision sensors

### Changed
- Refactored vision sensor handling to use event-driven approach
- Enhanced SimConnection.shutdown method to accept camera_manager parameter
- Modified shutdown sequence to properly clean up all manager instances
- Improved parameter handling using named parameters for clarity

### Fixed
- Fixed 'int' object has no attribute 'shutdown' error in SimConnection.shutdown
- Fixed incorrect parameter order in SimConnection.shutdown method
- Fixed "object does not exist" error in vision sensor handling
- Fixed image orientation by applying np.flipud() to image data instead of camera handle

## [V.1.1.0] - 2023-07-24

### Added
- Added View_Depth_Image.py tool for viewing and manipulating depth image datasets
- Added validator.py tool for validating image orientation with preview capability
- Added flip.py batch processing tool for flipping entire datasets of images

## [V.1.0.0] - 2025-05-05

### Added
- Added Status tab with comprehensive victim detection visualization:
  - Direction indicator with radar-like display showing victim's position accurately relative to drone's heading
  - Elevation indicator displaying victim's height difference in meters with color coding
  - Distance display with color coding (green=near, orange=medium, red=far)
  - Signal strength indicator that increases as drone gets closer to victim
- Enhanced error handling for object existence checking with new `does_object_exist_by_alias()` function
- Added event subscription system for real-time victim position tracking
- Added complete scene_manager.py implementation with fully event-driven scene creation
- Added visual feedback when configuration settings are modified
- Added safety distance check to ensure victim spawns at least 2m away from drone's starting position
- Added category-based scene organization with proper parent-child relationships

### Changed
- Completely refactored scene creation system:
  - Removed progressive/threaded creation in favor of event-based architecture
  - Implemented batch processing to maintain UI responsiveness
- Enhanced configuration system:
  - Improved config saving/loading with proper UI synchronization
  - Added `_on_config_updated_gui` method to handle external config changes
  - Implemented visual highlights to show when settings are modified
- Modified floor creation to ensure it updates size when area_size configuration changes
- Improved UI responsiveness using Tkinter's `after()` method for safer UI updates
- Enhanced SimConnection shutdown process to safely handle event-triggered shutdowns
- Updated depth_dataset_collector to properly emit victim vector data for position tracking
- Extended event system with more topics and improved handling
- Implemented proper coordinate transformation to align victim indicator with drone's orientation

### Fixed
- Fixed configuration not saving/loading properly with direct UI synchronization
- Fixed floor not resizing when area_size is changed in configuration
- Fixed potential UI freezing during updates by properly scheduling UI operations
- Improved error handling in victim direction calculation
- Corrected coordinate transformation in get_victim_direction() to show accurate victim positions
- Fixed circular reference issues in scene hierarchy with improved category naming

### Removed
- Removed multiple redundant scene creation files:
  - scene_core.py
  - scene_creator_base.py
  - scene_progressive.py
  - scene_pos_sampler.py
  - scene_object_creators.py
- Eliminated progressive scene creation in favor of more efficient event-based approach

## [V.0.10.0] - 2025-05-03

### Added
- Event-driven depth dataset collection via `simulation/frame` events
- New config `victim_detection_threshold` to fire `victim/detected` alarms
- Immediate one-off capture when victim detected (bypasses frame skip)
- Thread-safe event publishes from background threads (save and capture events)
- Automatic unsubscribe from all dataset events on `shutdown()` to avoid leaks
- Created TODO.md file to track planned features and improvements
- Implemented singleton pattern for core managers (EventManager, KeyboardManager, SimConnection)
- Added SceneCreatorBase abstract class to standardize scene creation approaches
- Created new scene_helpers.py module with helper functions for scene creation
- Added setup_scene_event_handlers() for event-based scene management
- Added create_terrain_object() helper function to standardize terrain object creation

### Changed
- Replaced dummy distances with real Euclidean distance calculations
- Configurable sampling rate via `dataset_capture_frequency`
- Introduced capture and batch events: `dataset/capture/complete`, `dataset/batch/saved`, `dataset/batch/error`
- Refactored Controls subsystem to use singleton pattern
- Converted all direct sim references to use SimConnection singleton
- Created scene_helpers.py with utility functions to reduce code duplication
- Moved from threaded simulation architecture to single-thread event-driven approach
- Reimplemented core scene creation functionality using the new SceneCreatorBase structure
- Enhanced victim direction vector error handling in depth_dataset_collector.py
- Refactored all menu classes to use the EventManager singleton
- Improved main.py to explicitly calculate delta_time between simulation frames
- Simplified object creation workflow with normalized property setting

### Fixed
- Proper cleanup of event subscriptions on shutdown
- Fixed Cancel Creating Environment button being disabled during scene creation
- Improved error handling in victim direction vectors in depth_dataset_collector.py
- Consolidated terrain element creation in create_terrain_object helper function
- Fixed simulation termination and shutdown sequence
- Fixed scene creation cancellation issues

### Removed
- Eliminated physics_utils.py in favor of direct property setting via SimConnection
- Removed sim_utils.py as it's no longer needed with the new architecture
- Removed global creator reference in scene_progressive.py in favor of module attribute
- Eliminated the need to pass sim and event_manager instances throughout the codebase

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