# Core/event_manager.py

from collections import defaultdict
import threading
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

class EventManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Get or create the singleton EventManager instance.
        """
        if cls._instance is None:
            cls._instance = EventManager()
        return cls._instance
    
    def __init__(self):
        # Ensure only one instance is created
        if EventManager._instance is not None:
            raise Exception("EventManager already exists! Use EventManager.get_instance() to get the singleton instance.")
        
        self.listeners = defaultdict(list)
        self.lock = threading.Lock()
        self.logger = get_logger()  # Initialize logger
        EventManager._instance = self

    def subscribe(self, topic, callback):
        """
        Subscribe a callback to a specific topic.
        """
        with self.lock:
            self.listeners[topic].append(callback)
        self.logger.debug_at_level(DEBUG_L2, "EventManager", f"Subscribed to topic '{topic}'.")

    def unsubscribe(self, topic, callback):
        """
        Unsubscribe a specific callback from a topic.
        """
        with self.lock:
            if topic in self.listeners and callback in self.listeners[topic]:
                self.listeners[topic].remove(callback)
                self.logger.debug_at_level(DEBUG_L2, "EventManager", f"Unsubscribed from topic '{topic}'.")
            else:
                self.logger.warning("EventManager", f"Could not unsubscribe from topic '{topic}' - callback not found.")

    def publish(self, topic, data=None):
        """
        Publish an event to all subscribers of a topic.
        """
        with self.lock:
            callbacks = list(self.listeners[topic])

        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                # Special handling for background thread UI errors
                error_str = str(e)
                is_thread_error = "main thread is not in main loop" in error_str
                is_dataset_event = topic.startswith('dataset/')
                
                # Only log errors that aren't threading errors from dataset events
                if not (is_thread_error and is_dataset_event):
                    self.logger.error("EventManager", f"Error calling subscriber for topic '{topic}': {e}")

    def unsubscribe_all(self):
        """
        Remove all subscriptions (e.g., for shutdown).
        """
        with self.lock:
            self.listeners.clear()
        self.logger.info("EventManager", "Cleared all subscriptions.")
