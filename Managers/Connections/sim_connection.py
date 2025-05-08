# sim_connection.py

from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from Managers.keyboard_manager import KeyboardManager
from Core.event_manager import EventManager
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

        EM.subscribe('simulation/shutdown', self.shutdown)
        EM.subscribe('simulation/connect', self.connect)

    
    def connect(self, timeout_sec=2.5):
        """
        Connect to CoppeliaSim's remote API server.
        
        If the simulation is stopped, start it and wait until running.
        """
        if self._is_connected:
            return self.sim
            
        print("[Connection] Connecting to CoppeliaSim...")
        self.client = RemoteAPIClient()
        self.sim = self.client.require('sim')

        sim_state = self.sim.getSimulationState()
        if sim_state == self.sim.simulation_advancing_running:
            print("[Connection] Simulation already running.")
        elif sim_state == self.sim.simulation_stopped:
            print("[Connection] Simulation stopped. Starting...")
            self.sim.startSimulation()
            self._wait_until_running(timeout_sec)
        else:
            print(f"[Connection] Unexpected simulation state: {sim_state}")
        
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
                print("[Connection] Simulation is running.")
                return
            if time.time() - start_time > timeout_sec:
                print("[Connection] Timeout while waiting for simulation to start.")
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
        print("[Connection] Shutting down KeyboardManager...")
        try:
            KM.stop()
        except Exception as e:
            print(f"[Connection] Error stopping KeyboardManager: {e}")

        # Shutdown camera manager if provided
        if camera_manager is not None:
            print("[Connection] Shutting down CameraManager...")
            try:
                camera_manager.shutdown()
            except Exception as e:
                print(f"[Connection] Error shutting down CameraManager: {e}")

        # Remove camera floating view if provided
        if floating_view_rgb is not None:
            print("[Connection] Removing Camera View...")
            try:
                self.sim.floatingViewRemove(floating_view_rgb)
            except Exception as e:
                print(f"[Connection] Error removing Camera View: {e}")
        else:
            print("[Connection] No camera view to remove (not provided)")

        # Shutdown depth dataset collector if provided
        if depth_collector is not None:
            print("[Connection] Shutting down DepthDatasetCollector...")
            try:
                depth_collector.shutdown()
            except Exception as e:
                print(f"[Connection] Error shutting down DepthDatasetCollector: {e}")
        else:
            print("[Connection] No depth collector to shutdown (not provided)")

        print("[Connection] Disconnecting Remote API client...")
        try:
            self.sim.stopSimulation()
            print("[Connection] Simulation stopped.")
            self._is_connected = False
        except Exception as e:
            print(f"[Connection] Error during simulation stop: {e}")