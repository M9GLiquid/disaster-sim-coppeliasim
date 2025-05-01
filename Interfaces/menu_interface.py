# Interfaces/menu_interface.py

class MenuInterface:
    """
    Base class for all menus.
    Subclasses must implement:
      - on_open():    display the menu options
      - on_command(): handle a user‐entered command, return next menu key or None
    Optionally override:
      - on_exit():    cleanup or state when leaving the menu
    """

    def on_open(self):
        raise NotImplementedError("MenuInterface.on_open must be overridden")

    def on_command(self, cmd: str):
        raise NotImplementedError("MenuInterface.on_command must be overridden")

    def on_exit(self):
        pass
