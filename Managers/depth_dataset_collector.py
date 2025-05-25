import os
import numpy as np
import math
import threading
import copy
import random
import datetime

from Utils.capture_utils import capture_depth, capture_pose, capture_distance_to_victim
from Utils.config_utils import get_default_config
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3
from Utils.episode_utils import save_episode_data, EPISODE_START, EPISODE_END, EPISODE_SAVE_COMPLETED, EPISODE_SAVE_ERROR

from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager

EM = EventManager.get_instance()
SC = SimConnection.get_instance()
logger = get_logger()

# Dataset collection events
DATASET_CAPTURE_REQUEST = 'dataset/capture/request'    # Request a data capture
DATASET_CAPTURE_COMPLETE = 'dataset/capture/complete'  # Data point captured successfully
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
                 base_folder=None,
                 batch_size=500,
                 save_every_n_frames=10,
                 split_ratio=(0.98, 0.01, 0.01)):
        """
        Main depth dataset collector - now episode-based.
        """
        # Verbose logging flag from configuration
        self.verbose = get_default_config().get('verbose', False)
        
        logger.info("DepthCollector", "Initializing episode-based depth dataset collector")
        logger.debug_at_level(DEBUG_L1, "DepthCollector", 
                         f"Parameters: base_folder={base_folder}, batch_size={batch_size}, "
                         f"save_every_n_frames={save_every_n_frames}")
        
        # Listen for config updates
        EM.subscribe('config/updated', self._on_config_updated)
        self.sensor_handle = sensor_handle

        # Generate a unique dataset folder for this run (no 'depth_dataset' in name)
        now = datetime.datetime.now()
        dataset_folder = now.strftime('%Y%m%d_%H%M%S')
        self.base_folder = os.path.join("data", dataset_folder)
        logger.info("DepthCollector", f"Dataset base folder for this run: {self.base_folder}")

        self.batch_size = batch_size
        self.save_every_n_frames = save_every_n_frames
        self.train_ratio, self.val_ratio, self.test_ratio = split_ratio        # Episode data buffers
        self.episode_depths = []
        self.episode_poses = []
        self.episode_frames = []
        self.episode_distances = []
        self.episode_actions = []
        self.episode_victim_dirs = []
        self.current_episode_number = 0

        # Setup folders
        self.train_folder = os.path.join(self.base_folder, "train")
        self.val_folder   = os.path.join(self.base_folder, "val")
        for folder in [self.train_folder, self.val_folder]:
            os.makedirs(folder, exist_ok=True)
            logger.debug_at_level(DEBUG_L1, "DepthCollector", f"Created directory: {folder}")

        # Counters
        self.global_frame_counter = 0
        self.train_counter = 0
        self.val_counter   = 0
        self.test_counter  = 0

        # Control flags
        self.shutdown_requested = False        # Action tracking
        self.last_action_label = 8  # Default: hover

        # Episode collection activation flag
        self.collecting_episode = False
        
        # Subscribe to episode events instead of scene events
        EM.subscribe(EPISODE_START, self._on_episode_start)
        EM.subscribe(EPISODE_END, self._on_episode_end)

        # Event subscriptions
        EM.subscribe('keyboard/move',   self._on_move)
        EM.subscribe('keyboard/rotate', self._on_rotate)

        logger.debug_at_level(DEBUG_L1, "DepthCollector", "Event subscriptions registered")

        # Track async save threads
        self._save_threads = []

    def _on_episode_start(self, data):
        """
        Start collecting data when a new episode begins.
        """
        self.current_episode_number = data.get('episode_number', 0)
        self.collecting_episode = True
        
        # Clear episode buffers
        self.episode_depths = []
        self.episode_poses = []
        self.episode_frames = []
        self.episode_distances = []
        self.episode_actions = []
        self.episode_victim_dirs = []
        
        logger.info("DepthCollector", f"Started collecting data for episode {self.current_episode_number}")

        # Subscribe to simulation frame events for data capture only after scene is ready
        EM.subscribe('simulation/frame', self._on_simulation_frame)
        logger.debug_at_level(DEBUG_L1, "DepthCollector", "Subscribed to simulation/frame after scene creation")

    def _on_episode_end(self, data):
        """
        Save episode data when episode ends.
        """
        if not self.collecting_episode:
            logger.warning("DepthCollector", "Episode end event received but not collecting episode data")
            return
            
        episode_number = data.get('episode_number', self.current_episode_number)
        logger.info("DepthCollector", f"Episode {episode_number} ended, saving {len(self.episode_depths)} data points")
        
        if self.episode_depths:
            # Prepare episode data
            episode_data = {
                'depths': self._safe_stack('episode_depths', self.episode_depths, np.float32),
                'poses': self._safe_stack('episode_poses', self.episode_poses, np.float32),
                'frames': self._safe_stack('episode_frames', self.episode_frames, np.int32),
                'distances': self._safe_stack('episode_distances', self.episode_distances, np.float32),
                'actions': self._safe_stack('episode_actions', self.episode_actions, np.int32),
                'victim_dirs': self._safe_stack('episode_victim_dirs', self.episode_victim_dirs, np.float32)
            }
            # Check if all data was successfully stacked
            if all(v is not None for v in episode_data.values()):
                # Deep copy data for thread safety
                episode_data_copy = copy.deepcopy(episode_data)
                # Randomly assign split (90% train, 10% val)
                split = "train" if random.random() < 0.9 else "val"
                split_dir = self.train_folder if split == "train" else self.val_folder
                os.makedirs(split_dir, exist_ok=True)
                filename = f"episode_{episode_number:05d}.npz"
                save_path = os.path.join(split_dir, filename)
                def save_worker():
                    logger.info("DepthCollector", f"[Async] Saving episode {episode_number} to {save_path} [{split}]")
                    try:
                        np.savez_compressed(
                            save_path,
                            depths      = episode_data_copy['depths'],
                            poses       = episode_data_copy['poses'],
                            frames      = episode_data_copy['frames'],
                            distances   = episode_data_copy['distances'],
                            actions     = episode_data_copy['actions'],
                            victim_dirs = episode_data_copy['victim_dirs'],
                        )
                        logger.info("DepthCollector", f"[Async] Successfully saved episode {episode_number} to {save_path}")
                        EM.publish(EPISODE_SAVE_COMPLETED, {'episode_number': episode_number})
                    except Exception as e:
                        logger.error("DepthCollector", f"[Async] Failed to save episode {episode_number} to {save_path}: {e}")
                        EM.publish(EPISODE_SAVE_ERROR, {'episode_number': episode_number})
                t = threading.Thread(target=save_worker, name=f"EpisodeSave-{episode_number}")
                t.start()
                self._save_threads.append(t)
            else:
                logger.error("DepthCollector", f"Failed to prepare data for episode {episode_number}")
                EM.publish(EPISODE_SAVE_ERROR, {'episode_number': episode_number})
        else:
            logger.warning("DepthCollector", f"No data collected for episode {episode_number}")
        
        # Reset for next episode
        self.collecting_episode = False
        self.episode_depths = []
        self.episode_poses = []
        self.episode_frames = []
        self.episode_distances = []
        self.episode_actions = []
        self.episode_victim_dirs = []

        # Unsubscribe from simulation frame events to avoid errors if scene is reset
        EM.unsubscribe('simulation/frame', self._on_simulation_frame)
        logger.debug_at_level(DEBUG_L1, "DepthCollector", "Unsubscribed from simulation/frame after episode end")

    def capture(self):
        """Deprecated: use event 'simulation/frame' instead"""
        pass

    def _on_simulation_frame(self, _):
        """
        Handle simulation frame event: capture data every save_every_n_frames for episodes
        """
        # increment frame counter
        self.global_frame_counter += 1
        
        # Always print action and distance to victim for user
        distance = capture_distance_to_victim()

        # Only collect data if we're in an active episode
        if not self.collecting_episode:
            return
            
        if self.global_frame_counter % self.save_every_n_frames != 0:
            return
            
        logger.debug_at_level(DEBUG_L2, "DepthCollector", f"Capturing episode data for frame {self.global_frame_counter}")
        
        # perform capture
        depth_img = capture_depth(self.sensor_handle)
        pose     = capture_pose()
        
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
            victim_vec = (0.0, 0.0, 0.0, 0.0)  # Default: no direction, zero distance        # Store in episode buffers
        self.episode_depths.append(depth_img)
        self.episode_poses.append(pose)
        self.episode_frames.append(self.global_frame_counter)
        self.episode_distances.append(distance)
        self.episode_actions.append(self.last_action_label)
        self.episode_victim_dirs.append(victim_vec)

        # Print action and distance to victim for user
        logger.info("DepthCollector", f"Action: {self.last_action_label}, Distance to victim: {distance:.2f}m")

        logger.debug_at_level(DEBUG_L2, "DepthCollector",
                         f"Episode {self.current_episode_number} - captured data - distance: {distance:.2f}, action: {self.last_action_label}")

        # publish capture complete event
        EM.publish(DATASET_CAPTURE_COMPLETE, {
            'frame': self.global_frame_counter,
            'distance': distance,
            'action': self.last_action_label,
            'victim_vec': victim_vec
        })

    def shutdown(self):
        """Shutdown the data collector."""
        logger.info("DepthCollector", "Shutting down episode-based depth dataset collector")
        self.shutdown_requested = True
        
        # End any active episode
        if self.collecting_episode:
            logger.info("DepthCollector", "Ending active episode during shutdown")
            self.collecting_episode = False
        # Wait for all save threads to finish
        for t in self._save_threads:
            logger.info("DepthCollector", f"Waiting for save thread {t.name} to finish...")
            t.join()
        logger.info("DepthCollector", "All episode save threads have completed.")

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