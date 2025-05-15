import os
import threading
import queue
import numpy as np
import math
import datetime

from Utils.capture_utils import capture_depth, capture_pose, capture_distance_to_victim
from Utils.save_utils import save_batch_npz
from Utils.config_utils import get_default_config
from Managers.scene_manager import SCENE_CREATION_COMPLETED, SCENE_CLEARED
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager

EM = EventManager.get_instance()
SC = SimConnection.get_instance()
logger = get_logger()

# Dataset collection events
DATASET_CAPTURE_REQUEST = 'dataset/capture/request'    # Request a data capture
DATASET_CAPTURE_COMPLETE = 'dataset/capture/complete'  # Data point captured successfully
DATASET_BATCH_SAVED = 'dataset/batch/saved'           # Batch successfully saved
DATASET_BATCH_ERROR = 'dataset/batch/error'           # Error saving batch
VICTIM_DETECTED = 'victim/detected'                   # Victim detected in frame
DATASET_CONFIG_UPDATED = 'dataset/config/updated'     # Dataset configuration updated
DATASET_DIR_CHANGED = 'dataset/dir/changed'           # Dataset directory changed

def get_victim_direction():
    """
    Returns a unit direction vector and distance from quadcopter to victim,
    transformed to be relative to the drone's current orientation.
    
    Returns:
        tuple: ((dx, dy, dz), distance) - normalized direction vector and Euclidean distance
    """
    try:
        # Get quadcopter handle
        quad = SC.sim.getObject('/Quadcopter')
        
        # Check if victim exists
        try:
            vic = SC.sim.getObject('/Victim')
        except Exception:
            # Victim doesn't exist
            logger.debug_at_level(2, "DepthCollector", "No victim in scene, skipping direction calculation")
            return (0.0, 0.0, 0.0), -1.0

        # Get positions
        qx, qy, qz = SC.sim.getObjectPosition(quad, -1)
        vx, vy, vz = SC.sim.getObjectPosition(vic, -1)

        # Calculate vector components and distance in world coordinates
        dx_world, dy_world, dz_world = vx - qx, vy - qy, vz - qz
        distance = math.sqrt(dx_world*dx_world + dy_world*dy_world + dz_world*dz_world)
        
        # Get drone's orientation (Euler angles in radians)
        drone_orientation = SC.sim.getObjectOrientation(quad, -1)
        alpha, beta, gamma = drone_orientation  # Roll, pitch, yaw
        
        # Fix the transformation by first calculating the correct angle
        # CoppeliaSim's coordinate system: X right, Y forward, Z up
        # We need to adjust gamma (yaw) to match our display conventions
        cos_yaw = math.cos(gamma)
        sin_yaw = math.sin(gamma)
        
        # Correct transformation with proper rotation matrix
        # This transformation ensures "forward" on the display corresponds to
        # the drone's forward direction (Y-axis in CoppeliaSim)
        # We need to invert the sign of dy to fix the backwards issue
        dx = -dx_world * sin_yaw + dy_world * cos_yaw  # Left-right axis (X in display)
        dy = -dx_world * cos_yaw - dy_world * sin_yaw   # Forward-back axis (Y in display)
        dz = dz_world  # Keep the original Z difference for elevation

        # Calculate normalized direction vector (unit vector)
        if distance < 0.0001:  # Avoid division by near-zero
            unit_vector = (0.0, 0.0, 0.0)
        else:
            unit_vector = (dx / distance, dy / distance, dz / distance)

        return unit_vector, distance
        
    except Exception as e:
        logger.error("DepthCollector", f"Error calculating victim direction: {e}")
        return (0.0, 0.0, 0.0), -1.0  # Return zero vector and invalid distance on error

class DepthDatasetCollector:
    def __init__(self, sensor_handle,
                 base_folder="depth_dataset",
                 batch_size=500,
                 save_every_n_frames=10,
                 split_ratio=(0.98, 0.01, 0.01),
                 use_timestamp_subfolder=True):
        """
        Main depth dataset collector.
        """
        # Initialize logger
        self.logger = get_logger()
        
        # Verbose logging flag from configuration
        self.verbose = get_default_config().get('verbose', False)
        # Listen for config updates
        EM.subscribe('config/updated', self._on_config_updated)
        self.sensor_handle = sensor_handle
        self.base_folder = base_folder
        self.batch_size = batch_size
        self.save_every_n_frames = save_every_n_frames
        self.train_ratio, self.val_ratio, self.test_ratio = split_ratio
        self.use_timestamp_subfolder = use_timestamp_subfolder

        # Create timestamp subfolder if configured
        if self.use_timestamp_subfolder:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.base_folder = os.path.join(self.base_folder, timestamp)
            if self.verbose:
                self.logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Using timestamped folder: {self.base_folder}")

        # Buffers
        self.depths = []
        self.poses = []
        self.frames = []
        self.distances = []
        self.actions = []
        self.victim_dirs = []    # <-- new buffer for direction vectors

        # Setup folders
        self._setup_folders()

        # Counters
        self.global_frame_counter = 0
        self.train_counter = 0
        self.val_counter   = 0
        self.test_counter  = 0

        # Control flags
        self.shutdown_requested = False

        # Action tracking
        self.last_action_label = 8  # Default: hover

        # Background saving
        self.save_queue = queue.Queue()
        self.saving_thread = threading.Thread(target=self._background_saver, daemon=True)
        self.saving_thread.start()

        # data capture activation flag
        self.active = False
        
        # Subscribe to scene creation completed event
        EM.subscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        EM.subscribe(SCENE_CLEARED, self._on_scene_cleared)

        # Event subscriptions
        EM.subscribe('keyboard/move',   self._on_move)
        EM.subscribe('keyboard/rotate', self._on_rotate)
        EM.subscribe(DATASET_DIR_CHANGED, self._on_dir_changed)

        # subscribe to simulation frame events for data capture
        EM.subscribe('simulation/frame', self._on_simulation_frame)

    def _setup_folders(self):
        """Set up the dataset directories"""
        self.train_folder = os.path.join(self.base_folder, "train")
        self.val_folder   = os.path.join(self.base_folder, "val")
        self.test_folder  = os.path.join(self.base_folder, "test")
        for folder in [self.base_folder, self.train_folder, self.val_folder, self.test_folder]:
            os.makedirs(folder, exist_ok=True)
        if self.verbose:
            self.logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Created dataset directories in {self.base_folder}")
    
    def _on_dir_changed(self, data):
        """Handle directory change request"""
        if 'base_dir' in data:
            new_base_dir = data['base_dir']
            if self.verbose:
                self.logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Changing base directory to: {new_base_dir}")
            
            # First, flush any existing data
            if self.depths:
                self._flush_buffer()
            
            # Update the base folder
            self.base_folder = new_base_dir
            
            # Add timestamp subfolder if configured
            if self.use_timestamp_subfolder and 'use_timestamp' in data and data['use_timestamp']:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self.base_folder = os.path.join(self.base_folder, timestamp)
            
            # Re-setup the folder structure
            self._setup_folders()
            
            # Reset counters for new dataset
            self.train_counter = 0
            self.val_counter = 0
            self.test_counter = 0
            
            if self.verbose:
                self.logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Dataset directory changed to {self.base_folder}")
            
            # Notify UI of the change
            EM.publish(DATASET_CONFIG_UPDATED, {
                'base_dir': self.base_folder,
                'verbose': self.verbose
            })
            
    def change_directory(self, new_base_dir, use_timestamp=True):
        """
        Change the dataset directory.
        
        Args:
            new_base_dir (str): New base directory for dataset storage
            use_timestamp (bool): Whether to create a timestamp subfolder
        """
        EM.publish(DATASET_DIR_CHANGED, {
            'base_dir': new_base_dir,
            'use_timestamp': use_timestamp
        })
      
    def set_base_folder(self, folder_path):
        self.change_directory(folder_path)
        self.logger.info("DepthCollector", f"Dataset directory changed to {folder_path}")
        
    def _on_scene_completed(self, _):
        """Handle scene creation completion event"""
        self.active = True
        self.logger.info("DepthCollector", "Scene creation completed. Activating data capture.")
        
    def _on_scene_cleared(self, _):
        """Handle scene cleared event by deactivating data collection"""
        self.active = False
        self.logger.info("DepthCollector", "Scene cleared, deactivating data collection")
        
        # Clear any pending data
        self.depths.clear()
        self.poses.clear()
        self.frames.clear()
        self.distances.clear()
        self.actions.clear()
        self.victim_dirs.clear()
        
    def capture(self):
        """Manually trigger a data capture"""
        EM.publish(DATASET_CAPTURE_REQUEST, self.global_frame_counter)
        
    def _on_simulation_frame(self, _):
        """Callback for each simulation frame to potentially capture data"""
        # Don't capture if not active
        if not self.active:
            return
        
        # Only capture every N frames (skip frames)
        self.global_frame_counter += 1
        if self.global_frame_counter % self.save_every_n_frames != 0:
            return

        # Calculate distance to victim
        distance = capture_distance_to_victim()
        victim_dir = (0.0, 0.0, 0.0)
        
        # Only attempt to calculate victim direction if we have a valid distance
        if distance > 0:
            # Calculate normalized direction to victim
            try:
                victim_dir, victim_dist = get_victim_direction()
                
                # Only override distance if the one from get_victim_direction is valid
                if victim_dist > 0:
                    distance = victim_dist
                    
                    # Publish victim detected event for UI updates
                    # This will update the victim indicator in the UI
                    EM.publish(VICTIM_DETECTED, {
                        'frame': self.global_frame_counter,
                        'distance': victim_dist,
                        'victim_vec': victim_dir,
                        'is_background_thread': False
                    })
            except Exception as e:
                self.logger.error("DepthCollector", f"Error getting victim direction: {e}")
                victim_dir = (0.0, 0.0, 0.0)

        # Capture depth and pose data
        depth_array = capture_depth(self.sensor_handle)
        pose = capture_pose()

        # Add data to buffers
        if depth_array is not None:
            self.depths.append(depth_array)
            self.poses.append(pose)
            self.frames.append(self.global_frame_counter)
            self.distances.append(distance)
            self.actions.append(self.last_action_label)
            self.victim_dirs.append(victim_dir)

        # publish capture complete event with thread safety info
        try:
            EM.publish(DATASET_CAPTURE_COMPLETE, {
                'frame': self.global_frame_counter,
                'distance': distance,
                'action': self.last_action_label,
                'victim_vec': victim_dir,
                'is_background_thread': False  # Main simulation thread
            })
        except Exception as e:
            self.logger.error("DepthCollector", f"Error publishing capture event: {e}")

        # flush if batch full
        if len(self.depths) >= self.batch_size:
            self._flush_buffer()

    def shutdown(self):
        """Shutdown the data collector and flush the buffer"""
        self.logger.debug_at_level(DEBUG_L1, "DepthCollector", "Shutting down depth dataset collector")
        self.shutdown_requested = True
        self.active = False
        
        # Unsubscribe from events to prevent more data capture during shutdown
        try:
            EM.unsubscribe('simulation/frame', self._on_simulation_frame)
            EM.unsubscribe('keyboard/move', self._on_move)
            EM.unsubscribe('keyboard/rotate', self._on_rotate)
            EM.unsubscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
            EM.unsubscribe(SCENE_CLEARED, self._on_scene_cleared)
            EM.unsubscribe(DATASET_DIR_CHANGED, self._on_dir_changed)
            EM.unsubscribe('config/updated', self._on_config_updated)
            self.logger.debug_at_level(DEBUG_L1, "DepthCollector", "Unsubscribed from all events")
        except Exception as e:
            self.logger.error("DepthCollector", f"Error unsubscribing from events: {e}")
        
        # Flush any remaining data
        if self.depths:
            try:
                self._flush_buffer()
                self.logger.debug_at_level(DEBUG_L1, "DepthCollector", "Buffer flushed during shutdown")
            except Exception as e:
                self.logger.error("DepthCollector", f"Error flushing buffer during shutdown: {e}")
                
        # Wait for background thread to finish
        try:
            # Put None in the queue to signal end
            self.save_queue.put(None)
            
            # Wait for a short time for the thread to finish
            if hasattr(self, 'saving_thread') and self.saving_thread.is_alive():
                self.saving_thread.join(timeout=2.0)
                if self.saving_thread.is_alive():
                    self.logger.warning("DepthCollector", "Background saving thread did not finish in time")
        except Exception as e:
            self.logger.error("DepthCollector", f"Error waiting for background thread: {e}")
            
        self.logger.info("DepthCollector", "Depth dataset collector shutdown complete")

    def _safe_stack(self, name, arr_list, dtype=None):
        try:
            return np.stack(arr_list)
        except Exception as e:
            self.logger.warning("DepthCollector", f"Warning: could not stack {name}: {e}")
            # show individual shapes
            try:
                shapes = [np.shape(a) for a in arr_list]
                self.logger.debug_at_level(DEBUG_L2, "DepthCollector", f"{name} element shapes: {shapes}")
            except:
                pass
            return np.array(arr_list, dtype=dtype if dtype else object)

    def _flush_buffer(self):
        """Flush the current batch to disk"""
        if not self.depths:
            return  # Don't attempt to save empty batch
            
        # Determine destination folder based on ratios
        split = self._select_split()

        # Stack arrays safely with fallback
        try:
            batch = {
                'depths': self._safe_stack('depths', self.depths),
                'poses': self._safe_stack('poses', self.poses),
                'frames': self._safe_stack('frames', self.frames),
                'distances': self._safe_stack('distances', self.distances),
                'actions': self._safe_stack('actions', self.actions),
                'victim_dirs': self._safe_stack('victim_dirs', self.victim_dirs),
                'split': split
            }
            
            # Add to save queue
            self.save_queue.put(batch)
            
            self.logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Queued batch with {len(self.depths)} frames for saving.")
            
            # Clear in-memory batch
            self.depths.clear()
            self.poses.clear()
            self.frames.clear()
            self.distances.clear()
            self.actions.clear()
            self.victim_dirs.clear()
            
        except Exception as e:
            self.logger.error("DepthCollector", f"Error preparing batch for saving: {e}")

    def _background_saver(self):
        """Background thread for saving batches"""
        self.logger.info("DepthCollector", "Background saving thread started")
        while not self.shutdown_requested:
            try:
                batch = self.save_queue.get(timeout=1.0)
                
                # Check for shutdown signal
                if batch is None:
                    self.logger.debug_at_level(DEBUG_L1, "DepthCollector", "Received shutdown signal in background saver")
                    break
                
                self._save_batch(batch)
                self.save_queue.task_done()
            except queue.Empty:
                # Timeout is expected, just continue the loop
                continue
            except Exception as e:
                self.logger.error("DepthCollector", f"Error in background saver: {e}")
                
        self.logger.info("DepthCollector", "Background saving thread exiting")

    def _save_batch(self, batch):
        """Save a batch of data as NPZ file"""
        try:
            depths = batch['depths']
            split = batch['split']
            batch_id = np.min(batch['frames']) if len(batch['frames']) > 0 else 0
            
            # Get right folder
            if split == 'train':
                self.train_counter += 1
                folder = self.train_folder
                counter = self.train_counter
            elif split == 'val':
                self.val_counter += 1
                folder = self.val_folder
                counter = self.val_counter
            else:  # test
                self.test_counter += 1
                folder = self.test_folder
                counter = self.test_counter
                
            # Generate filename based on split and batch ID
            filename = f"{split}_batch_{batch_id:06d}.npz"
            filepath = os.path.join(folder, filename)
            
            # Save file
            save_batch_npz(filepath, batch)
            
            total_saved = self.train_counter + self.val_counter + self.test_counter
            
            # Publish event for UI update
            try:
                EM.publish(DATASET_BATCH_SAVED, {
                    'batch_id': batch_id,
                    'split': split,
                    'count': len(depths),
                    'total_saved': total_saved,
                    'is_background_thread': True  # Indicate this is from background thread
                })
            except Exception as e:
                self.logger.error("DepthCollector", f"Error publishing batch event: {e}")
                
        except Exception as e:
            self.logger.error("DepthCollector", f"Error saving batch: {e}")
            EM.publish(DATASET_BATCH_ERROR, {
                'error': str(e)
            })
            
    def _select_split(self):
        """Select train/val/test split probabilistically"""
        p = np.random.random()
        if p < self.train_ratio:
            return 'train'
        elif p < self.train_ratio + self.val_ratio:
            return 'val'
        else:
            return 'test'
            
    def _on_move(self, delta):
        """Handle movement commands to track last action"""
        dx, dy, dz = delta
        
        # Simple mapping of movement to action labels
        if abs(dx) > 0.1 or abs(dy) > 0.1 or abs(dz) > 0.1:
            # determine dominant direction
            max_dir = max(abs(dx), abs(dy), abs(dz))
            if max_dir == abs(dx):
                self.last_action_label = 0 if dx > 0 else 1  # Right/Left
            elif max_dir == abs(dy):
                self.last_action_label = 2 if dy > 0 else 3  # Forward/Back
            else:
                self.last_action_label = 4 if dz > 0 else 5  # Up/Down
                
    def _on_rotate(self, delta):
        """Handle rotation commands to track last action"""
        if abs(delta) > 0.01:
            self.last_action_label = 6 if delta > 0 else 7  # Turn Right/Left
        else:
            self.last_action_label = 8  # Hover / No rotation

    def _on_config_updated(self, _):
        """Handle configuration updates"""
        # Update verbose flag when configuration changes
        config = get_default_config()
        self.verbose = config.get('verbose', False)
