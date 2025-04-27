# Controls/drone_control.py

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

    def move_target(dx=0, dy=0, dz=0):
        sim.acquireLock()
        try:
            pos = sim.getObjectPosition(target_handle, -1)
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
                    move_target(dy=MOVE_STEP)
                elif key == 's':
                    move_target(dy=-MOVE_STEP)
                elif key == 'a':
                    move_target(dx=-MOVE_STEP)
                elif key == 'd':
                    move_target(dx=+MOVE_STEP)
                elif key == 'q':
                    move_target(dz=+MOVE_STEP)
                elif key == 'e':
                    move_target(dz=-MOVE_STEP)
                elif key == 'x':
                    print("[Drone Manual Control] Exiting manual control...")
                    break

            time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\n[Drone Manual Control] Exiting on Ctrl-C.")
