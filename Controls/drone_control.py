# Controls/drone_control.py

import math
import time
import threading
import sys

def manual_drone_control(sim):
    """
    Manual WASD/QE control of the /target directly.
    """
    print("\n[Drone Manual Control] Starting manual control...")
    target_handle = sim.getObject('/target')
    
    MOVE_STEP = 0.1
    DELAY = 0.05
    key_pressed = None

    # Keyboard listening thread
    try:
        import msvcrt
        def get_key():
            nonlocal key_pressed
            while True:
                if msvcrt.kbhit():
                    key_pressed = msvcrt.getch().decode('utf-8').lower()
                time.sleep(0.01)
    except ImportError:
        import tty
        import termios
        def get_key():
            nonlocal key_pressed
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while True:
                    key_pressed = sys.stdin.read(1).lower()
                    time.sleep(0.01)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    keyboard_thread = threading.Thread(target=get_key)
    keyboard_thread.daemon = True
    keyboard_thread.start()

    def move_target(forward=0.0, sideward=0.0, upward=0.0):
        sim.acquireLock()
        try:
            pos = sim.getObjectPosition(target_handle, -1)
            ori = sim.getObjectOrientation(target_handle, -1)

            yaw = ori[2]  # Only yaw matters

            # Adjust for drone facing -X
            dx = -forward * math.cos(yaw) - sideward * math.sin(yaw)
            dy = -forward * math.sin(yaw) + sideward * math.cos(yaw)
            dz = upward

            new_pos = [pos[0] + dx, pos[1] + dy, pos[2] + dz]
            sim.setObjectPosition(target_handle, -1, new_pos)
        finally:
            sim.releaseLock()


    print("[Drone Manual Control] Use W/A/S/D/Q/E to move, X to exit.")

    try:
        while True:
            if key_pressed:
                key = key_pressed
                key_pressed = None

                if key == 'w':
                    move_target(forward=MOVE_STEP)
                elif key == 's':
                    move_target(forward=-MOVE_STEP)
                elif key == 'a':
                    move_target(sideward=-MOVE_STEP)
                elif key == 'd':
                    move_target(sideward=+MOVE_STEP)
                elif key == 'q':
                    move_target(upward=+MOVE_STEP)
                elif key == 'e':
                    move_target(upward=-MOVE_STEP)


            time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\n[Drone Manual Control] Exiting on Ctrl-C.")
