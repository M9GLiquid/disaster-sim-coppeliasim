# Controls/keyboard_manager.py

import threading
import time
import sys

class KeyboardManager:
    def __init__(self, event_manager):
        self.event_manager = event_manager
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
                    if self.typing_mode:
                        pass  # Typing mode handled elsewhere
                    else:
                        key = key.decode('utf-8').lower()
                        self.key_pressed = key
                time.sleep(0.01)
        except ImportError:
            import tty, termios, select
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while self.running:
                    dr, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if dr:
                        key = sys.stdin.read(1)
                        if self.typing_mode:
                            pass
                        else:
                            self.key_pressed = key.lower()
                    time.sleep(0.01)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def process_keys(self):
        if self.key_pressed and not self.typing_mode:
            key = self.key_pressed
            self.key_pressed = None
            self.event_manager.publish('keyboard/key_pressed', key)

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
        if self.thread.is_alive():
            self.thread.join()
