from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3

SC = SimConnection.get_instance()
EM = EventManager.get_instance()
logger = get_logger()

class CameraManager:
    """
    Manages vision sensors by handling them on each simulation frame.
    
    This class ensures that vision sensors are properly handled on every frame,
    which is necessary for them to work correctly and generate images.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get or create the singleton CameraManager instance."""
        if cls._instance is None:
            cls._instance = CameraManager()
        return cls._instance
    
    def __init__(self):
        """Initialize the CameraManager."""
        # Ensure only one instance is created
        if CameraManager._instance is not None:
            raise Exception("CameraManager already exists! Use CameraManager.get_instance() to get the singleton instance.")
        
        CameraManager._instance = self
        self.vision_sensors = []
        self.verbose = False
        
        logger.info("CameraManager", "Initializing camera manager")
        
        # Subscribe to frame events to handle vision sensors
        EM.subscribe('simulation/frame', self._on_simulation_frame)
        # Subscribe to config updates
        EM.subscribe('config/updated', self._on_config_updated)
        logger.debug_at_level(DEBUG_L1, "CameraManager", "Event subscriptions registered")
    
    def _on_config_updated(self, _):
        """Update configuration settings."""
        from Utils.config_utils import get_default_config
        config = get_default_config()
        self.verbose = config.get('verbose', False)
    
    def register_sensor(self, sensor_handle):
        """
        Register a vision sensor to be handled on each frame.
        
        Args:
            sensor_handle: The handle for the vision sensor.
        """
        if sensor_handle not in self.vision_sensors:
            self.vision_sensors.append(sensor_handle)
            logger.info("CameraManager", f"Registered vision sensor: {sensor_handle}")
            logger.debug_at_level(DEBUG_L1, "CameraManager", f"Total vision sensors: {len(self.vision_sensors)}")
    
    def unregister_sensor(self, sensor_handle):
        """
        Unregister a vision sensor.
        
        Args:
            sensor_handle: The handle for the vision sensor to unregister.
        """
        if sensor_handle in self.vision_sensors:
            self.vision_sensors.remove(sensor_handle)
            logger.info("CameraManager", f"Unregistered vision sensor: {sensor_handle}")
            logger.debug_at_level(DEBUG_L1, "CameraManager", f"Remaining vision sensors: {len(self.vision_sensors)}")
    
    def _on_simulation_frame(self, _):
        """
        Handle all registered vision sensors on each simulation frame.
        
        This is called automatically for each frame via the event system.
        """
        logger.debug_at_level(DEBUG_L3, "CameraManager", "Processing vision sensors")
        for sensor in self.vision_sensors:
            try:
                SC.sim.handleVisionSensor(sensor)
                logger.debug_at_level(DEBUG_L3, "CameraManager", f"Handled vision sensor: {sensor}")
            except Exception as e:
                logger.error("CameraManager", f"Error handling vision sensor {sensor}: {e}")
                # Remove invalid sensors
                if "object does not exist" in str(e).lower():
                    logger.warning("CameraManager", f"Vision sensor {sensor} no longer exists, removing")
                    self.unregister_sensor(sensor)
    
    def shutdown(self):
        """Clean shutdown of the camera manager."""
        logger.info("CameraManager", f"Shutting down camera manager, cleaning up {len(self.vision_sensors)} sensors")
        self.vision_sensors.clear()
        logger.debug_at_level(DEBUG_L1, "CameraManager", "All vision sensors unregistered") 