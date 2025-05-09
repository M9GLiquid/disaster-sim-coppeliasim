import os
import threading
import queue
import numpy as np
import math

from Utils.capture_utils import capture_depth, capture_pose, capture_distance_to_victim
from Utils.save_utils import save_batch_npz
from Utils.config_utils import get_default_config
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3
from Managers.scene_manager import SCENE_CREATION_COMPLETED

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

def get_victim_direction():
    """
    Returns a unit direction vector and distance from quadcopter to victim,
    transformed to be relative to the drone's current orientation.
    
    Returns:
        tuple: ((dx, dy, dz), distance) - normalized direction vector and Euclidean distance
    """
    try:
        # Get object handles
        quad = SC.sim.getObject('/Quadcopter')
        vic = SC.sim.getObject('/Victim')

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

        logger.debug_at_level(DEBUG_L3, "DepthCollector", f"Victim direction: {unit_vector}, distance: {distance}")
        return unit_vector, distance
        
    except Exception as e:
        logger.error("DepthCollector", f"Error calculating victim direction: {e}")
        return (0.0, 0.0, 0.0), -1.0  # Return zero vector and invalid distance on error

class DepthDatasetCollector:
    def __init__(self, sensor_handle,
                 base_folder="depth_dataset",
                 batch_size=500,
                 save_every_n_frames=10,
                 split_ratio=(0.98, 0.01, 0.01)):
        """
        Main depth dataset collector.
        """
        # Verbose logging flag from configuration
        self.verbose = get_default_config().get('verbose', False)
        
        logger.info("DepthCollector", "Initializing depth dataset collector")
        logger.debug_at_level(DEBUG_L1, "DepthCollector", 
                         f"Parameters: base_folder={base_folder}, batch_size={batch_size}, "
                         f"save_every_n_frames={save_every_n_frames}")
        
        # Listen for config updates
        EM.subscribe('config/updated', self._on_config_updated)
        self.sensor_handle = sensor_handle
        self.base_folder = base_folder
        self.batch_size = batch_size
        self.save_every_n_frames = save_every_n_frames
        self.train_ratio, self.val_ratio, self.test_ratio = split_ratio

        # Buffers
        self.depths = []
        self.poses = []
        self.frames = []
        self.distances = []
        self.actions = []
        self.victim_dirs = []    # <-- new buffer for direction vectors

        # Setup folders
        self.train_folder = os.path.join(base_folder, "train")
        self.val_folder   = os.path.join(base_folder, "val")
        self.test_folder  = os.path.join(base_folder, "test")
        for folder in [self.train_folder, self.val_folder, self.test_folder]:
            os.makedirs(folder, exist_ok=True)
            logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Created directory: {folder}")

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
        logger.debug_at_level(DEBUG_L1, "DepthCollector", "Background saving thread started")

        # data capture activation flag
        self.active = False
        
        # Subscribe to scene creation completed event
        EM.subscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)

        # Event subscriptions
        EM.subscribe('keyboard/move',   self._on_move)
        EM.subscribe('keyboard/rotate', self._on_rotate)

        # subscribe to simulation frame events for data capture
        EM.subscribe('simulation/frame', self._on_simulation_frame)
        logger.debug_at_level(DEBUG_L1, "DepthCollector", "Event subscriptions registered")

    def _on_scene_completed(self, _):
        """
        Activate data collection once the scene is created.
        """
        # Only activate once
        if not self.active:
            logger.info("DepthCollector", "Scene creation completed. Activating data capture.")
            self.active = True

    def capture(self):
        """Deprecated: use event 'simulation/frame' instead"""
        pass

    def _on_simulation_frame(self, _):
        """
        Handle simulation frame event: capture data every save_every_n_frames
        """
        # increment frame counter
        self.global_frame_counter += 1
        if not self.active:
            return
        if self.global_frame_counter % self.save_every_n_frames != 0:
            return
            
        logger.debug_at_level(DEBUG_L2, "DepthCollector", f"Capturing data for frame {self.global_frame_counter}")
        
        # perform capture
        depth_img = capture_depth(self.sensor_handle)
        pose     = capture_pose()
        distance = capture_distance_to_victim()
        
        # Add error handling for victim direction
        try:
            unit_vec, dist = get_victim_direction()
            # Check if any values are None before unpacking
            if unit_vec is None or dist is None:
                # Default values if victim direction isn't available
                victim_vec = (0.0, 0.0, 0.0, 0.0)  # Default: no direction, zero distance
                logger.warning("DepthCollector", "Invalid victim direction values")
            else:
                victim_vec = (*unit_vec, dist)
        except Exception as e:
            logger.error("DepthCollector", f"Error getting victim direction: {e}")
            victim_vec = (0.0, 0.0, 0.0, 0.0)  # Default: no direction, zero distance

        self.depths.append(depth_img)
        self.poses.append(pose)
        self.frames.append(self.global_frame_counter)
        self.distances.append(distance)
        self.actions.append(self.last_action_label)
        self.victim_dirs.append(victim_vec)

        logger.debug_at_level(DEBUG_L2, "DepthCollector", 
                         f"Captured data - distance: {distance:.2f}, action: {self.last_action_label}")

        # publish capture complete event
        EM.publish(DATASET_CAPTURE_COMPLETE, {
            'frame': self.global_frame_counter,
            'distance': distance,
            'action': self.last_action_label,
            'victim_vec': victim_vec
        })

        # flush if batch full
        if len(self.depths) >= self.batch_size:
            logger.info("DepthCollector", f"Batch size reached ({self.batch_size}), flushing buffer")
            self._flush_buffer()

    def shutdown(self):
        """Shutdown the data collector."""
        logger.info("DepthCollector", "Shutting down depth dataset collector")
        self.shutdown_requested = True
        if self.depths:
            logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Flushing remaining {len(self.depths)} samples")
            self._flush_buffer()
        if self.saving_thread.is_alive():
            self.saving_thread.join(timeout=2.0)
            logger.debug_at_level(DEBUG_L1, "DepthCollector", "Saving thread joined")

    def _safe_stack(self, name, arr_list, dtype=None):
        """Safely stack arrays with error handling."""
        try:
            if not arr_list:
                logger.warning("DepthCollector", f"Empty list for {name}, skipping")
                return None
            return np.stack(arr_list) if dtype is None else np.stack(arr_list).astype(dtype)
        except Exception as e:
            logger.error("DepthCollector", f"Error stacking {name}: {e}")
            return None

    def _flush_buffer(self):
        """Flush data to disk."""
        if not self.depths:
            logger.debug_at_level(DEBUG_L1, "DepthCollector", "No data to flush")
            return

        # Stack arrays safely with fallback
        logger.debug_at_level(DEBUG_L2, "DepthCollector", f"Stacking arrays for {len(self.depths)} samples")
        batch = {
            'depths': self._safe_stack('depths', self.depths, np.float32),
            'poses': self._safe_stack('poses', self.poses, np.float32),
            'frames': self._safe_stack('frames', self.frames, np.int32),
            'distances': self._safe_stack('distances', self.distances, np.float32),
            'actions': self._safe_stack('actions', self.actions, np.int32),
            'victim_dirs': self._safe_stack('victim_dirs', self.victim_dirs, np.float32)
        }

        # Put in save queue and clear buffers
        if all(v is not None for v in batch.values()):
            self.save_queue.put(batch)
            logger.debug_at_level(DEBUG_L1, "DepthCollector", "Batch queued for saving")
            self.depths, self.poses, self.frames = [], [], []
            self.distances, self.actions, self.victim_dirs = [], [], []
        else:
            logger.error("DepthCollector", "Failed to create batch, some arrays could not be stacked")

    def _background_saver(self):
        """Background thread that saves batches from the queue."""
        logger.debug_at_level(DEBUG_L1, "DepthCollector", "Background saver thread started")
        while not self.shutdown_requested or not self.save_queue.empty():
            try:
                batch = self.save_queue.get(block=True, timeout=0.5)
                self._save_batch(batch)
                self.save_queue.task_done()
            except queue.Empty:
                pass
        logger.debug_at_level(DEBUG_L1, "DepthCollector", "Background saver thread finished")

    def _save_batch(self, batch):
        """Save a batch of data to the appropriate split directory."""
        split = self._select_split()
        folder = getattr(self, f"{split}_folder")
        counter = getattr(self, f"{split}_counter")
        
        try:
            # Fix the call to save_batch_npz with the correct parameters
            save_batch_npz(folder, counter, batch)
            setattr(self, f"{split}_counter", counter + 1)
            logger.info("DepthCollector", f"Saved {split} batch #{counter} with {len(batch['frames'])} samples")
            
            # Publish success event
            EM.publish(DATASET_BATCH_SAVED, {'split': split, 'batch': counter, 'samples': len(batch['frames'])})
        except Exception as e:
            logger.error("DepthCollector", f"Error saving batch: {e}")
            EM.publish(DATASET_BATCH_ERROR, {'error': str(e)})

    def _select_split(self):
        """Randomly select a split based on the specified ratios."""
        r = np.random.random()
        if r < self.train_ratio:
            return "train"
        elif r < self.train_ratio + self.val_ratio:
            return "val"
        else:
            return "test"

    def _on_move(self, delta):
        """Handle move events to track the current action."""
        dx, dy, dz = delta
        # Update action label based on movement
        if dx > 0: self.last_action_label = 0  # Right
        elif dx < 0: self.last_action_label = 1  # Left
        elif dy > 0: self.last_action_label = 2  # Forward
        elif dy < 0: self.last_action_label = 3  # Backward
        elif dz > 0: self.last_action_label = 4  # Up
        elif dz < 0: self.last_action_label = 5  # Down
        logger.debug_at_level(DEBUG_L3, "DepthCollector", f"Move action updated: {self.last_action_label}")

    def _on_rotate(self, delta):
        """Handle rotation events to track the current action."""
        self.last_action_label = 6 if delta > 0 else 7  # 6=turn left, 7=turn right
        logger.debug_at_level(DEBUG_L3, "DepthCollector", f"Rotate action updated: {self.last_action_label}")

    def _on_config_updated(self, _):
        """Update configuration settings."""
        config = get_default_config()
        self.verbose = config.get('verbose', False)
        logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Configuration updated, verbose: {self.verbose}")
