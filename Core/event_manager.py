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
        EventManager._instance = self
        
        # Get logger instance
        self.logger = get_logger()
        self.logger.info("EventManager", "Event manager initialized")

    def subscribe(self, topic, callback):
        """
        Subscribe a callback to a specific topic.
        """
        with self.lock:
            self.listeners[topic].append(callback)
        self.logger.debug_at_level(DEBUG_L1, "EventManager", f"Subscribed to topic '{topic}'")

    def unsubscribe(self, topic, callback):
        """
        Unsubscribe a specific callback from a topic.
        """
        with self.lock:
            if topic in self.listeners and callback in self.listeners[topic]:
                self.listeners[topic].remove(callback)
                self.logger.debug_at_level(DEBUG_L1, "EventManager", f"Unsubscribed from topic '{topic}'")
            else:
                self.logger.warning("EventManager", f"Could not unsubscribe from topic '{topic}' - callback not found")

    def publish(self, topic, data=None):
        """
        Publish an event to all subscribers of a topic.
        """
        with self.lock:
            callbacks = list(self.listeners[topic])
        
        # Log event publication at different detail levels based on event type
        if topic.startswith('keyboard/'):
            # Keyboard events are very frequent, so use highest debug level
            self.logger.debug_at_level(DEBUG_L3, "EventManager", f"Publishing '{topic}' event with data: {data}")
        elif topic == 'simulation/frame':
            # Frame updates are very frequent, so use highest debug level
            self.logger.debug_at_level(DEBUG_L3, "EventManager", f"Publishing frame event with dt: {data}")
        else:
            # Other events are less frequent, use medium debug level
            self.logger.debug_at_level(DEBUG_L2, "EventManager", f"Publishing '{topic}' event with data: {data}")

        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                self.logger.error("EventManager", f"Error calling subscriber for topic '{topic}': {e}")

    def unsubscribe_all(self):
        """
        Remove all subscriptions (e.g., for shutdown).
        """
        with self.lock:
            self.listeners.clear()
        self.logger.info("EventManager", "Cleared all subscriptions")
