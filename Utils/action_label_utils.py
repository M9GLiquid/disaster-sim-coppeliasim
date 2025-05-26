"""
Utility for computing action labels based on actual drone movement and target state.
"""
import math
import logging
from Managers.Connections.sim_connection import SimConnection
from enum import IntEnum

# Thresholds for hover condition (tunable)
DISTANCE_THRESHOLD = 0.2            # meters
ORIENTATION_THRESHOLD = math.radians(5)  # radians
SPEED_THRESHOLD = 0.1               # m/s
YAW_CHANGE_THRESHOLD = math.radians(2)  # 5 degrees in radians

SC = SimConnection.get_instance()


class ActionLabel(IntEnum):
    Forward = 0
    Backward = 1
    Left = 2
    Right = 3
    Up = 4
    Down = 5
    Yaw_Left = 6
    Yaw_Right = 7
    Hover = 8


def compute_forward_unit_vector(yaw):
    """
    Returns the (x,y) unit vector for the drone's forward axis given yaw.
    """
    return math.cos(yaw), math.sin(yaw)


def project_velocity_to_axes(vx, vy, yaw):
    """
    Projects world-frame velocity (vx,vy) into drone-local
    forward and side components.
    """
    ux, uy = compute_forward_unit_vector(yaw)
    forward = vx * ux + vy * uy
    side    = -vx * uy + vy * ux
    return forward, side


# Debounce hover by simulation time
HOVER_TIME_THRESHOLD = 0.5  # seconds
_hover_time_accum = 0.0
_last_non_hover = ActionLabel.Hover

# Track previous yaw for yaw action detection
_prev_yaw = None


def get_action_label():
    """
    Determine the drone's action label, with time-based hover debounce and yaw detection.
    Returns:
        ActionLabel: Enum value representing the current action.
    """
    global _hover_time_accum, _last_non_hover, _prev_yaw

    quad = SC.sim.getObject('/Quadcopter')
    vic = SC.sim.getObject('/Victim')
    pos = SC.sim.getObjectPosition(quad, -1)
    vic_pos = SC.sim.getObjectPosition(vic, -1)
    ori = SC.sim.getObjectOrientation(quad, -1)
    yaw = ori[2]
    lin_vel, _ = SC.sim.getObjectVelocity(quad)
    vx, vy, vz = lin_vel
    forward, side = project_velocity_to_axes(vx, vy, yaw)
    dx, dy, dz = vic_pos[0] - pos[0], vic_pos[1] - pos[1], vic_pos[2] - pos[2]
    distance = math.sqrt(dx*dx + dy*dy + dz*dz)
    desired_yaw = math.atan2(dy, dx)
    yaw_diff = abs((desired_yaw - yaw + math.pi) % (2*math.pi) - math.pi)
    speed = math.sqrt(vx*vx + vy*vy + vz*vz)

    # Minimal yaw detection logic
    if _prev_yaw is not None:
        delta_yaw = (yaw - _prev_yaw + math.pi) % (2 * math.pi) - math.pi
        if abs(delta_yaw) > YAW_CHANGE_THRESHOLD:
            _hover_time_accum = 0.0
            _last_non_hover = ActionLabel.Yaw_Left if delta_yaw > 0 else ActionLabel.Yaw_Right
            _prev_yaw = yaw  # Only update here!
            return _last_non_hover
    # Do not update _prev_yaw here; only update after a yaw action is detected

    if (distance < DISTANCE_THRESHOLD and
        yaw_diff < ORIENTATION_THRESHOLD and
        speed < SPEED_THRESHOLD):
        raw = ActionLabel.Hover
    elif abs(forward) > abs(side) and abs(forward) > SPEED_THRESHOLD:
        raw = ActionLabel.Forward if forward < 0 else ActionLabel.Backward
    elif abs(side) > SPEED_THRESHOLD:
        raw = ActionLabel.Right if side > 0 else ActionLabel.Left
    elif abs(vz) > SPEED_THRESHOLD:
        raw = ActionLabel.Up if vz > 0 else ActionLabel.Down
    else:
        raw = ActionLabel.Hover

    dt = SC.get_simulation_time_step()
    if raw != ActionLabel.Hover:
        _hover_time_accum = 0.0
        _last_non_hover = raw
        _prev_yaw = yaw  # Update here for non-hover actions
        return raw
    _hover_time_accum += dt
    if _hover_time_accum >= HOVER_TIME_THRESHOLD:
        _prev_yaw = yaw  # Update here when hover is stable
        return ActionLabel.Hover
    return _last_non_hover
