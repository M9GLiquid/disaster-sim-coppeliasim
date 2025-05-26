# Managers/episode_manager.py

import os
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2
from Utils.episode_utils import check_episode_end_condition, save_episode_data, EPISODE_START, EPISODE_END, EPISODE_SAVE_COMPLETED, EPISODE_SAVE_ERROR
from Core.event_manager import EventManager
from Managers.scene_manager import SCENE_CREATION_COMPLETED

EM = EventManager.get_instance()
logger = get_logger()

# Episode manager specific events
EPISODE_MANUAL_END = 'episode/manual_end'
SCENE_START_CREATION = 'scene/start_creation'

class EpisodeManager:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls, threshold=0.5):
        if cls._instance is None:
            cls._instance = cls(threshold)
        return cls._instance

    def __init__(self, threshold=0.5):
        if self.__class__._initialized:
            return
        self.__class__._initialized = True
        
        self.threshold = threshold
        self.episode_active = False
        self.episode_number = 0
        self.episode_data = {
            'depths': [],
            'poses': [],
            'frames': [],
            'distances': [],
            'actions': [],
            'victim_dirs': []
        }
        self._scene_config = None  # Store config for scene restarts
        
        logger.info("EpisodeManager", f"Initialized with threshold: {threshold}m")
        
        # Subscribe to events
        EM.subscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        EM.subscribe('simulation/frame', self._on_simulation_frame)
        EM.subscribe('dataset/capture/complete', self._on_data_captured)
        EM.subscribe(EPISODE_MANUAL_END, self._on_manual_end)
        
        logger.debug_at_level(DEBUG_L1, "EpisodeManager", "Event subscriptions registered")
    
    def set_scene_config(self, config):
        """
        Store the scene configuration for future restarts.
        """
        self._scene_config = config
        logger.debug_at_level(DEBUG_L1, "EpisodeManager", "Scene config stored for episode restarts")
    
    def _on_scene_completed(self, data):
        """
        Start a new episode when scene creation is completed.
        Store the config if provided.
        """
        config = None
        if isinstance(data, dict) and 'config' in data:
            config = data['config']
            self.set_scene_config(config)
        self._start_episode()
    
    def _start_episode(self):
        """
        Initialize a new episode.
        """
        if self.episode_active:
            logger.warning("EpisodeManager", "Starting new episode while previous episode is still active")
            self._end_episode()
        
        self.episode_number += 1
        self.episode_active = True
        
        # Reset episode data
        self.episode_data = {
            'depths': [],
            'poses': [],
            'frames': [],
            'distances': [],
            'actions': [],
            'victim_dirs': []
        }
        
        logger.info("EpisodeManager", f"Episode {self.episode_number} started")
        
        # Publish episode start event
        EM.publish(EPISODE_START, {
            'episode_number': self.episode_number
        })
    
    def _on_simulation_frame(self, _):
        """
        Check for episode end condition each frame.
        """
        if not self.episode_active:
            return
        
        # Check if episode should end based on threshold
        if check_episode_end_condition(self.threshold):
            logger.info("EpisodeManager", f"Episode {self.episode_number} ending - drone reached victim")
            self._end_episode()
    
    def _on_data_captured(self, data):
        """
        Collect data from each frame capture.
        """
        if not self.episode_active:
            return
        
        # Extract data from capture event
        frame = data.get('frame', 0)
        distance = data.get('distance', -1.0)
        action = data.get('action', 8)  # Default: hover
        victim_vec = data.get('victim_vec', (0.0, 0.0, 0.0, 0.0))
        
        # Note: We don't have direct access to depth and pose data here
        # The depth dataset collector will handle the actual data collection
        # This is just for episode management
        
        logger.debug_at_level(DEBUG_L2, "EpisodeManager", 
                            f"Episode {self.episode_number} frame {frame}: distance={distance:.2f}m, action={action}")
    
    def _on_manual_end(self, _):
        """
        Handle manual episode end trigger.
        """
        if self.episode_active:
            logger.info("EpisodeManager", f"Episode {self.episode_number} manually ended")
            self._end_episode()
        else:
            logger.warning("EpisodeManager", "Manual episode end triggered but no episode is active")
    
    def _end_episode(self):
        """
        End the current episode and trigger data saving.
        """
        if not self.episode_active:
            logger.warning("EpisodeManager", "Attempted to end episode but no episode is active")
            return
        
        self.episode_active = False

        # Calculate and print distance to victim at episode end
        from Utils.capture_utils import capture_distance_to_victim
        distance = capture_distance_to_victim()
        logger.info(
            "EpisodeManager",
            f"EPISODE FINISHED: {self.episode_number} | Distance to victim: {distance:.2f}m (threshold: {self.threshold:.2f}m)"
        )
        if distance <= self.threshold:
            logger.info("EpisodeManager", f"Threshold reached! (distance {distance:.2f}m ≤ threshold {self.threshold:.2f}m)")
        else:
            logger.info("EpisodeManager", f"Episode ended, but distance above threshold (distance {distance:.2f}m > threshold {self.threshold:.2f}m)")

        logger.info("EpisodeManager", f"Episode {self.episode_number} ended")
        
        # Publish episode end event - this will trigger data collection systems to save their data
        EM.publish(EPISODE_END, {
            'episode_number': self.episode_number
        })

        # Publish scene restart event with stored config (publish config directly)
        if self._scene_config is not None:
            logger.info("EpisodeManager", "Triggering automatic scene restart after episode end")
            EM.publish(SCENE_START_CREATION, self._scene_config)
        else:
            logger.warning("EpisodeManager", "No scene config stored, cannot restart scene automatically")
    
    def trigger_manual_end(self):
        """
        Public method to manually trigger episode end (for UI button).
        """
        EM.publish(EPISODE_MANUAL_END, None)
    
    def get_current_episode_number(self):
        """
        Get the current episode number.
        """
        return self.episode_number
    
    def is_episode_active(self):
        """
        Check if an episode is currently active.
        """
        return self.episode_active
    
    def shutdown(self, save_on_shutdown=True):
        """
        Shutdown the episode manager.
        If save_on_shutdown is False, do not end the episode or publish EPISODE_END.
        """
        if self.episode_active and save_on_shutdown:
            logger.info("EpisodeManager", "Shutting down with active episode - ending episode")
            self._end_episode()
        elif self.episode_active and not save_on_shutdown:
            logger.info("EpisodeManager", "Shutting down with active episode - NOT saving episode data (save_on_shutdown=False)")
            self.episode_active = False
        # Unsubscribe from events
        EM.unsubscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        EM.unsubscribe('simulation/frame', self._on_simulation_frame)
        EM.unsubscribe('dataset/capture/complete', self._on_data_captured)
        EM.unsubscribe(EPISODE_MANUAL_END, self._on_manual_end)
        logger.info("EpisodeManager", "Episode manager shutdown complete")
