# Managers/menu_interface.py

class MenuInterface:
    def on_open(self):
        """Called when the menu is displayed."""
        raise NotImplementedError

    def on_command(self, cmd: str):
        """
        Handle a user command.

        Returns:
          - str: name of the next menu to switch to, or
          - None: stay on the current menu.
        """
        raise NotImplementedError

    def on_exit(self):
        """Called when exiting this menu."""
        pass
