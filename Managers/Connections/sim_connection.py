# sim_connection.py

from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Managers.keyboard_manager import KeyboardManager
from Core.event_manager import EventManager
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3
import time

KM = KeyboardManager.get_instance()
EM = EventManager.get_instance()

class SimConnection:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """
        Get or create the singleton SimConnection instance.
        """
        if cls._instance is None:
            cls._instance = SimConnection()
        return cls._instance
    
    def __init__(self):
        # Ensure only one instance is created
        if SimConnection._instance is not None:
            raise Exception("SimConnection already exists! Use SimConnection.get_instance() to get the singleton instance.")
        
        self.client = None
        self.sim = None
        self._is_connected = False
        self.depth_collector = None  # Store reference to depth_collector
        self.logger = get_logger()  # Initialize logger
        SimConnection._instance = self

        EM.subscribe('simulation/shutdown', self.shutdown)
        EM.subscribe('simulation/connect', self.connect)

    
    def connect(self, timeout_sec=2.5):
        """
        Connect to CoppeliaSim's remote API server.
        
        If the simulation is stopped, start it and wait until running.
        """
        if self._is_connected:
            return self.sim
            
        self.logger.info("Connection", "Connecting to CoppeliaSim...")
        self.client = RemoteAPIClient()
        self.sim = self.client.require('sim')

        sim_state = self.sim.getSimulationState()
        if sim_state == self.sim.simulation_advancing_running:
            self.logger.info("Connection", "Simulation already running.")
        elif sim_state == self.sim.simulation_stopped:
            self.logger.info("Connection", "Simulation stopped. Starting...")
            self.sim.startSimulation()
            self._wait_until_running(timeout_sec)
        else:
            self.logger.warning("Connection", f"Unexpected simulation state: {sim_state}")
        
        self._is_connected = True
        EM.publish('simulation/connected', self.sim)
        return self.sim
    
    def _wait_until_running(self, timeout_sec=2.5):
        """
        Wait until simulation state is 'running' or until timeout.
        """
        start_time = time.time()
        while True:
            state = self.sim.getSimulationState()
            if state == self.sim.simulation_advancing_running:
                self.logger.info("Connection", "Simulation is running.")
                return
            if time.time() - start_time > timeout_sec:
                self.logger.warning("Connection", "Timeout while waiting for simulation to start.")
                return
            time.sleep(0.05)
    
    def shutdown(self, data=None, depth_collector=None, floating_view_rgb=None):
        """
        Cleanly shutdown keyboard control, camera viewer, disconnect from simulation.
        
        When called via event system, data will be the event data and depth_collector/floating_view_rgb will be None.
        When called directly from main.py, data will be None and the other arguments will be provided.
        """
        self.logger.info("Connection", "Shutting down KeyboardManager...")
        try:
            KM.stop()
        except Exception as e:
            self.logger.error("Connection", f"Error stopping KeyboardManager: {e}")

        # Remove camera floating view if provided
        if floating_view_rgb is not None:
            self.logger.info("Connection", "Removing Camera View...")
            try:
                self.sim.floatingViewRemove(floating_view_rgb)
            except Exception as e:
                self.logger.error("Connection", f"Error removing Camera View: {e}")
        else:
            self.logger.debug_at_level(DEBUG_L1, "Connection", "No camera view to remove (not provided)")

        # Shutdown depth dataset collector if provided
        collector_to_shutdown = depth_collector if depth_collector is not None else self.depth_collector
        if collector_to_shutdown is not None:
            self.logger.info("Connection", "Shutting down DepthDatasetCollector...")
            try:
                # We already have EM instance at the top level, reusing it here
                
                # Safely unsubscribe from events before shutdown - check if methods exist
                if hasattr(collector_to_shutdown, '_on_simulation_frame') and callable(collector_to_shutdown._on_simulation_frame):
                    EM.unsubscribe('simulation/frame', collector_to_shutdown._on_simulation_frame)
                
                if hasattr(collector_to_shutdown, '_on_move') and callable(collector_to_shutdown._on_move):
                    EM.unsubscribe('keyboard/move', collector_to_shutdown._on_move)
                
                if hasattr(collector_to_shutdown, '_on_rotate') and callable(collector_to_shutdown._on_rotate):
                    EM.unsubscribe('keyboard/rotate', collector_to_shutdown._on_rotate)
                
                # Then shut down gracefully if shutdown method exists
                if hasattr(collector_to_shutdown, 'shutdown') and callable(collector_to_shutdown.shutdown):
                    collector_to_shutdown.shutdown()
                else:
                    self.logger.warning("Connection", "Depth collector has no shutdown method")
            except Exception as e:
                self.logger.error("Connection", f"Error shutting down DepthDatasetCollector: {e}")
        else:
            self.logger.debug_at_level(DEBUG_L1, "Connection", "No depth collector to shutdown (not provided)")

        # Clear reference
        self.depth_collector = None

        self.logger.info("Connection", "Disconnecting Remote API client...")
        try:
            self.sim.stopSimulation()
            self.logger.info("Connection", "Simulation stopped.")
            self._is_connected = False
        except Exception as e:
            self.logger.error("Connection", f"Error during simulation stop: {e}")

    def set_depth_collector(self, depth_collector):
        """Store a reference to the depth dataset collector for access from UI"""
        self.depth_collector = depth_collector
        self.logger.debug_at_level(DEBUG_L1, "Connection", "Depth collector reference stored")
        
    def get_depth_collector(self):
        """Retrieve the stored depth dataset collector instance"""
        if self.depth_collector is None:
            self.logger.warning("Connection", "No depth collector has been set")
        return self.depth_collector