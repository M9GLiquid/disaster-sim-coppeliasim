# Controls/keyboard_manager.py
import threading
import time
import sys
import math

class KeyboardManager:
    def __init__(self, sim, target_handle):
        self.sim = sim
        self.target_handle = target_handle
        self.running = True
        self.typing_mode = False
        self.key_pressed = None
        self.last_command = None

        self.thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        self.thread.start()

    def _keyboard_loop(self):
        try:
            import msvcrt  # Windows
            while self.running:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b'\r':  # ENTER pressed
                        if not self.typing_mode:
                            print("\n[KeyboardManager] Entering typing mode...")
                            self.typing_mode = True
                        else:
                            pass
                    elif self.typing_mode:
                        pass
                    else:
                        key = key.decode('utf-8').lower()
                        self.key_pressed = key
                time.sleep(0.01)
        except ImportError:
            import tty
            import termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while self.running:
                    key = sys.stdin.read(1)
                    if key == '\r' or key == '\n':
                        if not self.typing_mode:
                            print("\n[KeyboardManager] Entering typing mode...")
                            self.typing_mode = True
                        else:
                            pass
                    elif self.typing_mode:
                        pass
                    else:
                        self.key_pressed = key.lower()
                    time.sleep(0.01)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def process_keys(self):
        MOVE_STEP = 0.1
        ROTATE_STEP = math.radians(10)  # Nice clean 10 degrees

        if self.key_pressed and not self.typing_mode:
            key = self.key_pressed
            self.key_pressed = None

            try:
                self.sim.acquireLock()
                pos = self.sim.getObjectPosition(self.target_handle, -1)
                orient = self.sim.getObjectOrientation(self.target_handle, -1)

                new_pos = list(pos)
                new_orient = list(orient)

                if key == 'w':      # Forward movement
                    new_pos[1] += MOVE_STEP
                elif key == 's':    # Backward movement
                    new_pos[1] -= MOVE_STEP
                elif key == 'a':    # Leftward movement  
                    new_pos[0] -= MOVE_STEP
                elif key == 'd':    # Rightward movement
                    new_pos[0] += MOVE_STEP
                elif key == ' ':    # Jump (upward movement)
                    new_pos[2] += MOVE_STEP
                elif key == 'z':    # Downward movement
                    new_pos[2] -= MOVE_STEP
                elif key == 'q':    # Rotate left (yaw)
                    new_orient[2] += ROTATE_STEP
                elif key == 'e':    # Rotate right (yaw)
                    new_orient[2] -= ROTATE_STEP

                self.sim.setObjectPosition(self.target_handle, -1, new_pos)
                self.sim.setObjectOrientation(self.target_handle, -1, new_orient)

            finally:
                self.sim.releaseLock()

    def in_typing_mode(self):
        return self.typing_mode

    def finish_typing(self, command):
        self.last_command = command
        self.typing_mode = False
        print("[KeyboardManager] Exited typing mode.")

    def get_command(self):
        cmd = self.last_command
        self.last_command = None
        return cmd

    def stop(self):
        self.running = False
