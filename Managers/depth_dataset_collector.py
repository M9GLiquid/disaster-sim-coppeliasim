# Managers/depth_dataset_collector.py

import os
import threading
import queue
import numpy as np

from Utils.capture_utils import capture_depth, capture_pose, capture_dummy_distance
from Utils.save_utils import save_batch_npz

class DepthDatasetCollector:
    def __init__(self, sim, sensor_handle, event_manager,
                 base_folder="Data/Depth_Dataset",
                 batch_size=500,
                 save_every_n_frames=10,
                 split_ratio=(0.98, 0.01, 0.01)):
        """
        Main depth dataset collector.
        """
        self.sim = sim
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

        # Setup folders
        self.train_folder = os.path.join(base_folder, "train")
        self.val_folder = os.path.join(base_folder, "val")
        self.test_folder = os.path.join(base_folder, "test")
        for folder in [self.train_folder, self.val_folder, self.test_folder]:
            os.makedirs(folder, exist_ok=True)

        # Counters
        self.global_frame_counter = 0
        self.train_counter = 0
        self.val_counter = 0
        self.test_counter = 0

        # Control flags
        self.shutdown_requested = False

        # Action tracking
        self.last_action_label = 8  # Default: hover

        # Background saving
        self.save_queue = queue.Queue()
        self.saving_thread = threading.Thread(target=self._background_saver, daemon=True)
        self.saving_thread.start()

        # Event subscriptions
        event_manager.subscribe('keyboard/move', self._on_move)
        event_manager.subscribe('keyboard/rotate', self._on_rotate)

    def capture(self):
        if self.global_frame_counter % self.save_every_n_frames == 0:
            depth_img = capture_depth(self.sim, self.sensor_handle)
            pose = capture_pose(self.sim)
            distance = capture_dummy_distance()

            self.depths.append(depth_img)
            self.poses.append(pose)
            self.frames.append(self.global_frame_counter)
            self.distances.append(distance)
            self.actions.append(self.last_action_label)

            if len(self.depths) >= self.batch_size:
                self._flush_buffer()

        self.global_frame_counter += 1

    def shutdown(self):
        if self.depths:
            self._flush_buffer()
        self.shutdown_requested = True
        self.saving_thread.join()
        print("[DepthCollector] Shutdown complete, all data saved.")

    # ─────────────────────────────────────────────────────────────────────

    def _flush_buffer(self):
        batch = {
            'depths': np.stack(self.depths),
            'poses': np.stack(self.poses),
            'frames': np.array(self.frames, dtype=np.int32),
            'distances': np.array(self.distances, dtype=np.float32),
            'actions': np.array(self.actions, dtype=np.int32)
        }
        self.save_queue.put(batch)
        print(f"[DepthCollector] Queued batch with {len(self.depths)} frames for saving.")

        self.depths.clear()
        self.poses.clear()
        self.frames.clear()
        self.distances.clear()
        self.actions.clear()

    def _background_saver(self):
        while not self.shutdown_requested or not self.save_queue.empty():
            try:
                batch = self.save_queue.get(timeout=0.1)
                self._save_batch(batch)
            except queue.Empty:
                continue

    def _save_batch(self, batch):
        folder, counter = self._select_split()
        save_batch_npz(folder, counter, batch)
        if folder == self.train_folder:
            self.train_counter += 1
        elif folder == self.val_folder:
            self.val_counter += 1
        else:
            self.test_counter += 1

    def _select_split(self):
        rnd = np.random.rand()
        if rnd < self.train_ratio:
            return self.train_folder, self.train_counter
        elif rnd < self.train_ratio + self.val_ratio:
            return self.val_folder, self.val_counter
        else:
            return self.test_folder, self.test_counter

    def _on_move(self, delta):
        dx, dy, dz = delta
        if dy > 0:
            self.last_action_label = 0  # forward
        elif dy < 0:
            self.last_action_label = 1  # backward
        elif dx < 0:
            self.last_action_label = 2  # left
        elif dx > 0:
            self.last_action_label = 3  # right
        elif dz > 0:
            self.last_action_label = 4  # up
        elif dz < 0:
            self.last_action_label = 5  # down

    def _on_rotate(self, delta):
        if delta > 0:
            self.last_action_label = 6  # rotate left
        elif delta < 0:
            self.last_action_label = 7  # rotate right
