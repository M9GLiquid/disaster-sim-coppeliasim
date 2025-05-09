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
        SimConnection._instance = self
        
        # Get logger instance
        self.logger = get_logger()
        self.logger.info("Connection", "Simulation connection module initialized")

        EM.subscribe('simulation/shutdown', self.shutdown)
        EM.subscribe('simulation/connect', self.connect)
        self.logger.debug_at_level(DEBUG_L1, "Connection", "Registered event handlers for shutdown and connect")

    
    def connect(self, timeout_sec=2.5):
        """
        Connect to CoppeliaSim's remote API server.
        
        If the simulation is stopped, start it and wait until running.
        """
        if self._is_connected:
            self.logger.debug_at_level(DEBUG_L1, "Connection", "Already connected to simulation")
            return self.sim
            
        self.logger.info("Connection", "Connecting to CoppeliaSim...")
        self.client = RemoteAPIClient()
        self.sim = self.client.require('sim')
        self.logger.debug_at_level(DEBUG_L1, "Connection", "Remote API client created and sim module loaded")

        sim_state = self.sim.getSimulationState()
        self.logger.debug_at_level(DEBUG_L2, "Connection", f"Current simulation state: {sim_state}")
        
        if sim_state == self.sim.simulation_advancing_running:
            self.logger.info("Connection", "Simulation already running")
        elif sim_state == self.sim.simulation_stopped:
            self.logger.info("Connection", "Simulation stopped. Starting...")
            self.sim.startSimulation()
            self._wait_until_running(timeout_sec)
        else:
            self.logger.warning("Connection", f"Unexpected simulation state: {sim_state}")
        
        self._is_connected = True
        EM.publish('simulation/connected', self.sim)
        self.logger.debug_at_level(DEBUG_L1, "Connection", "Published 'simulation/connected' event")
        return self.sim
    
    def _wait_until_running(self, timeout_sec=2.5):
        """
        Wait until simulation state is 'running' or until timeout.
        """
        start_time = time.time()
        self.logger.debug_at_level(DEBUG_L2, "Connection", f"Waiting for simulation to start (timeout: {timeout_sec}s)")
        while True:
            state = self.sim.getSimulationState()
            self.logger.debug_at_level(DEBUG_L3, "Connection", f"Current state while waiting: {state}")
            if state == self.sim.simulation_advancing_running:
                self.logger.info("Connection", "Simulation is running")
                return
            if time.time() - start_time > timeout_sec:
                self.logger.warning("Connection", "Timeout while waiting for simulation to start")
                return
            time.sleep(0.05)
    
    def shutdown(self, data=None, depth_collector=None, floating_view_rgb=None, camera_manager=None):
        """
        Cleanly shutdown keyboard control, camera viewer, disconnect from simulation.
        
        When called via event system, data will be the event data and depth_collector/floating_view_rgb will be None.
        When called directly from main.py, use named parameters for clarity.
        
        Args:
            data: Event data when called via event system
            depth_collector: DepthDatasetCollector instance to shutdown
            floating_view_rgb: Floating view handle to remove
            camera_manager: CameraManager instance to shutdown
        """
        self.logger.info("Connection", "Shutting down KeyboardManager...")
        try:
            KM.stop()
            self.logger.debug_at_level(DEBUG_L1, "Connection", "KeyboardManager stopped successfully")
        except Exception as e:
            self.logger.error("Connection", f"Error stopping KeyboardManager: {e}")

        # Shutdown camera manager if provided
        if camera_manager is not None:
            self.logger.info("Connection", "Shutting down CameraManager...")
            try:
                camera_manager.shutdown()
                self.logger.debug_at_level(DEBUG_L1, "Connection", "CameraManager shutdown successfully")
            except Exception as e:
                self.logger.error("Connection", f"Error shutting down CameraManager: {e}")

        # Remove camera floating view if provided
        if floating_view_rgb is not None:
            self.logger.info("Connection", "Removing Camera View...")
            try:
                self.sim.floatingViewRemove(floating_view_rgb)
                self.logger.debug_at_level(DEBUG_L1, "Connection", "Camera view removed successfully")
            except Exception as e:
                self.logger.error("Connection", f"Error removing Camera View: {e}")
        else:
            self.logger.debug_at_level(DEBUG_L1, "Connection", "No camera view to remove (not provided)")

        # Shutdown depth dataset collector if provided
        if depth_collector is not None:
            self.logger.info("Connection", "Shutting down DepthDatasetCollector...")
            try:
                depth_collector.shutdown()
                self.logger.debug_at_level(DEBUG_L1, "Connection", "DepthDatasetCollector shutdown successfully")
            except Exception as e:
                self.logger.error("Connection", f"Error shutting down DepthDatasetCollector: {e}")
        else:
            self.logger.debug_at_level(DEBUG_L1, "Connection", "No depth collector to shutdown (not provided)")

        self.logger.info("Connection", "Disconnecting Remote API client...")
        try:
            self.sim.stopSimulation()
            self.logger.info("Connection", "Simulation stopped")
            self._is_connected = False
            self.logger.debug_at_level(DEBUG_L1, "Connection", "Connection flag set to disconnected")
        except Exception as e:
            self.logger.error("Connection", f"Error during simulation stop: {e}")