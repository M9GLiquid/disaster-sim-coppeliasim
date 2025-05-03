# Core/event_manager.py

from collections import defaultdict
import threading

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

    def subscribe(self, topic, callback):
        """
        Subscribe a callback to a specific topic.
        """
        with self.lock:
            self.listeners[topic].append(callback)
        print(f"[EventManager] Subscribed to topic '{topic}'.")

    def unsubscribe(self, topic, callback):
        """
        Unsubscribe a specific callback from a topic.
        """
        with self.lock:
            if topic in self.listeners and callback in self.listeners[topic]:
                self.listeners[topic].remove(callback)
                print(f"[EventManager] Unsubscribed from topic '{topic}'.")
            else:
                print(f"[EventManager] Warning: Could not unsubscribe from topic '{topic}' - callback not found.")

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
                print(f"[EventManager] Error calling subscriber for topic '{topic}': {e}")

    def unsubscribe_all(self):
        """
        Remove all subscriptions (e.g., for shutdown).
        """
        with self.lock:
            self.listeners.clear()
        print("[EventManager] Cleared all subscriptions.")
