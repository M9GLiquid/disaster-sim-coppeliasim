import os
import threading
import queue
import numpy as np

from Utils.capture_utils import capture_depth, capture_pose, capture_distance_to_victim
from Utils.save_utils import save_batch_npz
from Managers.scene_core import get_victim_direction
from Utils.config_utils import get_default_config

# Dataset collection events
DATASET_CAPTURE_REQUEST = 'dataset/capture/request'    # Request a data capture
DATASET_CAPTURE_COMPLETE = 'dataset/capture/complete'  # Data point captured successfully
DATASET_BATCH_SAVED = 'dataset/batch/saved'           # Batch successfully saved
DATASET_BATCH_ERROR = 'dataset/batch/error'           # Error saving batch
VICTIM_DETECTED = 'victim/detected'                   # Victim detected in frame
DATASET_CONFIG_UPDATED = 'dataset/config/updated'     # Dataset configuration updated

class DepthDatasetCollector:
    def __init__(self, sim, sensor_handle, event_manager,
                 base_folder="depth_dataset",
                 batch_size=500,
                 save_every_n_frames=10,
                 split_ratio=(0.98, 0.01, 0.01)):
        """
        Main depth dataset collector.
        """
        # Verbose logging flag from configuration
        self.verbose = get_default_config().get('verbose', False)
        # Listen for config updates
        event_manager.subscribe('config/updated', self._on_config_updated)
        self.sim = sim
        self.sensor_handle = sensor_handle
        self.base_folder = base_folder
        self.event_manager = event_manager
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
        # subscribe to scene creation event to start data capture
        self.event_manager.subscribe('scene/created', self._on_scene_created)

        # Event subscriptions
        event_manager.subscribe('keyboard/move',   self._on_move)
        event_manager.subscribe('keyboard/rotate', self._on_rotate)

        # subscribe to simulation frame events for data capture
        event_manager.subscribe('simulation/frame', self._on_simulation_frame)

    def _on_scene_created(self, _):
        """
        Activate data collection once the scene is created.
        """
        # Only activate once
        if not self.active:
            if self.verbose:
                print("[DepthCollector] Scene created event received. Activating data capture.")
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
        # perform capture
        depth_img = capture_depth(self.sim, self.sensor_handle)
        pose     = capture_pose(self.sim)
        distance = capture_distance_to_victim(self.sim)
        unit_vec, dist = get_victim_direction(self.sim)
        victim_vec = (*unit_vec, dist)

        self.depths.append(depth_img)
        self.poses.append(pose)
        self.frames.append(self.global_frame_counter)
        self.distances.append(distance)
        self.actions.append(self.last_action_label)
        self.victim_dirs.append(victim_vec)

        # publish capture complete event
        self.event_manager.publish(DATASET_CAPTURE_COMPLETE, {
            'frame': self.global_frame_counter,
            'distance': distance,
            'action': self.last_action_label,
            'victim_vec': victim_vec
        })

        # flush if batch full
        if len(self.depths) >= self.batch_size:
            self._flush_buffer()

    def shutdown(self):
        if self.depths:
            self._flush_buffer()
        self.shutdown_requested = True
        self.saving_thread.join()
        if self.verbose:
            print("[DepthCollector] Shutdown complete, all data saved.")

    def _safe_stack(self, name, arr_list, dtype=None):
        try:
            return np.stack(arr_list)
        except Exception as e:
            if self.verbose:
                print(f"[DepthCollector] Warning: could not stack {name}: {e}")
            # show individual shapes
            try:
                shapes = [np.shape(a) for a in arr_list]
                if self.verbose:
                    print(f"[DepthCollector] {name} element shapes: {shapes}")
            except:
                pass
            return np.array(arr_list, dtype=dtype if dtype else object)

    def _flush_buffer(self):
        # Stack arrays safely with fallback
        batch = {
            'depths':      self._safe_stack('depths', self.depths),
            'poses':       self._safe_stack('poses', self.poses),
            'frames':      np.array(self.frames, dtype=np.int32),
            'distances':   np.array(self.distances, dtype=np.float32),
            'actions':     np.array(self.actions, dtype=np.int32),
            'victim_dirs': self._safe_stack('victim_dirs', self.victim_dirs, dtype=np.float32)
        }
        self.save_queue.put(batch)
        if self.verbose:
            print(f"[DepthCollector] Queued batch with {len(self.depths)} frames for saving.")

        self.depths.clear()
        self.poses.clear()
        self.frames.clear()
        self.distances.clear()
        self.actions.clear()
        self.victim_dirs.clear()    # <-- clear buffer

    def _background_saver(self):
        while not self.shutdown_requested or not self.save_queue.empty():
            try:
                batch = self.save_queue.get(timeout=0.1)
                self._save_batch(batch)
            except queue.Empty:
                continue

    def _save_batch(self, batch):
        folder, counter = self._select_split()
        success = save_batch_npz(folder, counter, batch)
        if success:
            self.event_manager.publish(DATASET_BATCH_SAVED, {'folder': folder, 'counter': counter})
        else:
            self.event_manager.publish(DATASET_BATCH_ERROR, {'folder': folder, 'counter': counter})
        if folder == self.train_folder:
            self.train_counter += 1
        elif folder == self.val_folder:
            self.val_counter   += 1
        else:
            self.test_counter  += 1

    def _select_split(self):
        rnd = np.random.rand()
        if rnd < self.train_ratio:
            return self.train_folder, self.train_counter
        elif rnd < self.train_ratio + self.val_ratio:
            return self.val_folder,   self.val_counter
        else:
            return self.test_folder,  self.test_counter

    def _on_move(self, delta):
        dx, dy, dz = delta
        if dy > 0:       self.last_action_label = 0  # forward
        elif dy < 0:     self.last_action_label = 1  # backward
        elif dx < 0:     self.last_action_label = 2  # left
        elif dx > 0:     self.last_action_label = 3  # right
        elif dz > 0:     self.last_action_label = 4  # up
        elif dz < 0:     self.last_action_label = 5  # down

    def _on_rotate(self, delta):
        if delta > 0:    self.last_action_label = 6  # rotate left
        elif delta < 0:  self.last_action_label = 7  # rotate right

    def _on_config_updated(self, _):
        # Update verbose flag when configuration changes
        self.verbose = get_default_config().get('verbose', False)
        # publish dataset config updated
        self.event_manager.publish(DATASET_CONFIG_UPDATED, {'verbose': self.verbose})
