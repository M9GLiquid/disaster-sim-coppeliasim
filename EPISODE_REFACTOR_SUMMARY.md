# Episode Save Refactor - Implementation Summary

## Overview
Successfully implemented episode-based data collection to replace the previous batch-based system. The system now collects data during discrete episodes that start when scenes are created and end when the drone reaches the victim or is manually stopped.

## ✅ Completed Phases

### Phase 1: Hook Episode Start to Scene Creation
- **EpisodeManager** subscribes to `SCENE_CREATION_COMPLETED` events
- Automatically starts new episodes when scenes are created
- Publishes `EPISODE_START` events to notify data collectors

### Phase 2: Collect Data Each Frame  
- **DepthDatasetCollector** now subscribes to `EPISODE_START` and `EPISODE_END` events
- Collects data into episode-specific buffers during active episodes
- Data collection only occurs when `collecting_episode = True`

### Phase 3: Detect Episode End (Threshold)
- **EpisodeManager** monitors simulation frames for distance to victim
- Automatically ends episodes when drone is within 0.5m of victim
- Uses `capture_distance_to_victim()` for accurate distance calculation

### Phase 4: Manual Episode End Trigger
- Added "End Episode" button to menu system UI
- Button calls `EpisodeManager.trigger_manual_end()`
- Provides manual control for testing and edge cases

### Phase 5: Save Episode Data
- **DepthDatasetCollector** saves complete episodes as individual `.npz` files
- Uses `save_episode_data()` from `episode_utils.py`
- Files saved as `data/episodes/episode_00001.npz`, etc.
- Includes all data: depths, poses, frames, distances, actions, victim_dirs

### Phase 6: Reset for Next Episode
- Episode buffers automatically cleared after successful save
- `collecting_episode` flag reset to `False`
- Ready for next episode immediately

### Phase 7: Remove Old Batch Save Logic
- Removed unused batch saving methods (`_flush_buffer`, `_save_batch`, etc.)
- Removed batch-related events (`DATASET_BATCH_SAVED`, `DATASET_BATCH_ERROR`)
- Removed background saving thread and queue (episodes save immediately)
- Cleaned up unused imports (`threading`, `queue`, `save_batch_npz`)

## Key Components Modified

### 1. EpisodeManager (NEW)
- `Managers/episode_manager.py` - New singleton class
- Manages episode lifecycle and publishes events
- Integrated into main.py startup and shutdown

### 2. DepthDatasetCollector (REFACTORED)
- `Managers/depth_dataset_collector.py` - Major refactor
- Episode-based data collection instead of batch collection
- Immediate saving on episode end

### 3. MenuSystem (ENHANCED)
- `Managers/menu_system.py` - Added "End Episode" button
- Manual episode control for testing

### 4. Main Application (UPDATED)
- `main.py` - Added EpisodeManager initialization and shutdown

## Event Flow

```
Scene Creation → SCENE_CREATION_COMPLETED → EpisodeManager starts episode
                                         ↓
                                   EPISODE_START → DepthDatasetCollector begins collecting
                                         ↓
Simulation Frames → Distance check OR Manual trigger → Episode end detected
                                         ↓
                                   EPISODE_END → DepthDatasetCollector saves data
                                         ↓
                                   Episode reset → Ready for next episode
```

## Data Format

Episodes are saved as `episode_XXXXX.npz` files containing:
- `depths`: Depth images from drone camera
- `poses`: Drone position and orientation data  
- `frames`: Frame numbers for temporal alignment
- `distances`: Distance to victim at each frame
- `actions`: Drone action labels (movement/rotation)
- `victim_dirs`: Direction vectors from drone to victim

## Benefits

1. **Discrete Episodes**: Clear boundaries between data collection sessions
2. **Automatic Management**: Episodes start/end automatically based on simulation state
3. **Complete Data**: Each episode contains a full sequence from start to goal
4. **Manual Control**: Testing and debugging support via UI button
5. **Immediate Saving**: No data loss if simulation crashes
6. **Clean Architecture**: Removed complex batch management code

## Next Steps

The episode-based system is now ready for:
- Training reinforcement learning models on complete episodes
- Analyzing drone behavior patterns per episode
- Collecting datasets with clear start/end boundaries
- Manual episode control during development and testing

All phases of the action plan have been successfully implemented and tested.
