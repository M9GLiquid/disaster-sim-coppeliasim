import threading
import time
import sys

class KeyboardManager:
    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.running = True
        self.typing_mode = False      # only used as a flag
        self.key_pressed = None
        self.last_command = None

        self.thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        self.thread.start()

    def _keyboard_loop(self):
        try:
            import msvcrt  # Windows
            while self.running:
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8')
                    self.key_pressed = key
                    self.event_manager.publish('keyboard/key_pressed', key)
                time.sleep(0.01)
        except ImportError:
            import tty
            import termios
            import select
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while self.running:
                    dr, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if dr:
                        key = sys.stdin.read(1)
                        self.key_pressed = key
                        self.event_manager.publish('keyboard/key_pressed', key)
                    time.sleep(0.01)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def in_typing_mode(self):
        return self.typing_mode

    def finish_typing(self, command):
        self.last_command = command
        self.typing_mode = False

    def get_command(self):
        cmd = self.last_command
        self.last_command = None
        return cmd

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
