# Managers/scene_creator_base.py

"""
Base scene creator class to handle the common logic between
synchronous and progressive scene creation approaches.
"""

import random
import math
from abc import ABC, abstractmethod

from Utils.scene_helpers import sample_victim_pos, make_pos_sampler
from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager

EM = EventManager.get_instance()
SC = SimConnection.get_instance()

# Shared event names for scene creation
SCENE_CREATION_STARTED = 'scene/creation/started'
SCENE_CREATION_PROGRESS = 'scene/creation/progress'
SCENE_CREATION_COMPLETED = 'scene/creation/completed'
SCENE_CREATION_CANCELED = 'scene/creation/canceled'


class SceneCreatorBase(ABC):
    """
    Base class for scene creation with common functionality.
    Both synchronous and progressive implementations inherit from this.
    """
    def __init__(self, config):
        """
        Initialize the scene creator.
        
        Args:
            sim: Simulation handle
            config: Configuration dictionary
            event_manager: Optional event manager for publishing events
        """
        self.config = config
        self.handles = []
        self.group = None
        self.victim_pos = None
        self.pos_sampler = None
        self.verbose = config.get('verbose', False)
        self.is_completed = False
        self.is_cancelled = False
        
        # Calculate total objects based on config
        self.total_objects = (
            1 + config.get("num_rocks", 0) + config.get("num_trees", 0)
            + config.get("num_bushes", 0) + config.get("num_foliage", 0) + 1
        )
        
        # Base creator configuration
        base_keys = ['floor','rocks','standing_trees','fallen_trees','bushes','ground_foliage','victim']
        self.keys = ['floor'] + [k for k in base_keys[1:-1] if config.get(f'include_{k}', True)] + ['victim']
        
        # Object counts by type
        num_trees = config.get('num_trees', 0)
        fs = config.get('fraction_standing', 0)
        standing = int(num_trees * fs)
        fallen = num_trees - standing
        self.totals = {
            'floor':1, 'rocks':config.get('num_rocks',0),
            'standing_trees':standing, 'fallen_trees':fallen,
            'bushes':config.get('num_bushes',0), 'ground_foliage':config.get('num_foliage',0),
            'victim':1
        }

    def teleport_quadcopter_to_edge(self):
        """
        Teleport the quadcopter to the edge of the area, facing center.
        """
        try:
            # Get quadcopter and target handles
            quadcopter = SC.sim.getObject('/Quadcopter')
            target = SC.sim.getObject('/target')
            
            # Get area size from config
            area_size = self.config.get("area_size", 10.0)
            
            # Calculate position at edge of area
            edge_distance = area_size * 0.45  # Slightly inside the edge
            x_pos = edge_distance
            y_pos = edge_distance
            z_pos = self.config.get("drone_height", 1.5)
            
            # Calculate angle towards center (0,0)
            angle_to_center = math.atan2(-y_pos, -x_pos) + math.pi
            
            # Set positions
            SC.sim.setObjectPosition(quadcopter, -1, [x_pos, y_pos, z_pos])
            SC.sim.setObjectPosition(target, -1, [x_pos, y_pos, z_pos])
            
            # Set orientation - yaw towards center
            SC.sim.setObjectOrientation(quadcopter, -1, [0, 0, angle_to_center])
            SC.sim.setObjectOrientation(target, -1, [0, 0, angle_to_center])
            
            SC.sim.setBoolProperty(target, "depthInvisible", True)
            SC.sim.setBoolProperty(target, "visible", False)
            
            if self.verbose:
                print(f"[Teleport] Quadcopter positioned at edge position [{x_pos:.2f}, {y_pos:.2f}, {z_pos:.2f}] facing center")
                
            return True
        except Exception as e:
            if self.verbose:
                print(f"[Teleport] Error teleporting Quadcopter/target: {e}")
                import traceback
                traceback.print_exc()
            return False
            
    def initialize_scene(self):
        """
        Initialize scene by creating a group and setting up samplers.
        This is common to both synchronous and progressive approaches.
        """
        # Create group for all objects
        self.group = SC.sim.createDummy(0.01)
        SC.sim.setObjectAlias(self.group, "DisasterGroup")
        self.handles.append(self.group)
        
        # Sample victim and create position sampler
        self.victim_pos = sample_victim_pos(self.config)
        self.pos_sampler = make_pos_sampler(
            self.config, self.victim_pos,
            self.config.get("victim_radius", 0.7),
            self.config.get("victim_height_clearance", 1.5)
        )
        
    def publish_progress(self, progress):
        """
        Publish scene creation progress event if an event manager is available.
        
        Args:
            progress: Progress value between 0.0 and 1.0
        """
        EM.publish(SCENE_CREATION_PROGRESS, progress)
            
    def publish_started(self):
        """Publish scene creation started event"""
        EM.publish(SCENE_CREATION_STARTED, None)
            
    def publish_completed(self):
        """Publish scene creation completed event"""
        EM.publish(SCENE_CREATION_COMPLETED, self.handles)
        # Also publish the standard scene/created event for backward compatibility
        EM.publish('scene/created', None)
            
    def publish_canceled(self):
        """Publish scene creation canceled event"""
        EM.publish(SCENE_CREATION_CANCELED, None)
            
    def finalize_scene(self):
        """
        Finalize the scene by parenting objects and optimizing physics.
        """
        # Parent objects to group
        for h in self.handles:
            if h != self.group:  # Don't parent the group to itself
                try:
                    SC.sim.setObjectParent(h, self.group, True)
                except Exception:
                    pass  # Ignore parenting errors
        
    def cancel(self):
        """
        Cancel scene creation if not already completed.
        """
        if not self.is_cancelled and not self.is_completed:
            self.is_cancelled = True
            self.publish_canceled()
            
    @abstractmethod
    def create(self):
        """
        Abstract method to be implemented by subclasses.
        This is where the actual scene creation happens.
        
        Returns:
            List of created object handles
        """
        pass