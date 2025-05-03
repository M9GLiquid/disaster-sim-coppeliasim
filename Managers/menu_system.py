# Managers/menu_system.py

import tkinter as tk
from tkinter import ttk
from Utils.scene_utils import clear_disaster_area, restart_disaster_area
from Managers.scene_creator_base import (
    SCENE_CREATION_STARTED,
    SCENE_CREATION_PROGRESS, 
    SCENE_CREATION_COMPLETED, 
    SCENE_CREATION_CANCELED
)
from Managers.scene_progressive import create_scene_progressive
from Utils.config_utils import FIELDS
from Managers.Connections.sim_connection import SimConnection
from Core.event_manager import EventManager

EM = EventManager.get_instance()
SC = SimConnection.get_instance()

class MenuSystem:
    def __init__(self, config: dict, sim_command_queue):
        self.sim_queue = sim_command_queue
        self.sim = SC.sim
        self.config = config
        self.scene_creator = None
        self.progress_var = None  # For progress bar

        # Build and style main window
        self.root = tk.Tk()
        self.root.title("Disaster Simulation Control")
        self.root.geometry("320x400")
        self.root.configure(bg="#e5e5e5")
        self._build_ui()
        
        # Register for scene-related events
        self._register_event_handlers()

    def _register_event_handlers(self):
        """Set up event handlers for scene-related events"""
        # Scene creation events
        EM.subscribe(SCENE_CREATION_PROGRESS, self._on_scene_progress)
        EM.subscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        EM.subscribe(SCENE_CREATION_CANCELED, self._on_scene_canceled)
        
        # Handle scene creation requests from menus
        EM.subscribe('scene/creation/request', self._on_scene_creation_request)
        EM.subscribe('simulation/frame', self._on_simulation_frame)
        EM.subscribe('simulation/shutdown', self.cleanup)

    def _on_simulation_frame(self, _):
        """Wrapper method to handle simulation frame events and update the UI safely"""
        try:
            self.root.update()
        except Exception as e:
            print(f"Error updating UI: {e}")

    def _build_ui(self):
        # Themed notebook for Scene and Config tabs
        style = ttk.Style(self.root)
        style.theme_use('clam')
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill="both")
        
        # Scene tab
        scene_tab = ttk.Frame(notebook, padding=20)
        notebook.add(scene_tab, text="Scene")
        self._build_scene_tab(scene_tab)
        
        # Config tab
        config_tab = ttk.Frame(notebook, padding=20)
        notebook.add(config_tab, text="Config")
        self._build_config_tab(config_tab)

    def _build_scene_tab(self, parent):
        # Title
        ttk.Label(parent, text="Disaster Simulation Control", font=("Helvetica", 16, "bold")).pack(pady=(0,10))
        
        # Progress bar for scene creation
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(parent, variable=self.progress_var, maximum=1.0)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.pack_forget()  # Hide initially
        
        # Status label
        self.status_label = ttk.Label(parent, text="")
        self.status_label.pack(pady=2)
        
        # Create scene with progressive approach
        def create_scene_with_progress():
            # Disable all buttons during scene creation
            for btn in self.scene_buttons:
                btn.configure(state="disabled")
            
            # Show progress bar
            self.progress_bar.pack(fill="x", pady=5)
            self.progress_var.set(0.0)
            self.status_label.configure(text="Creating scene...")
            
            # Start progressive scene creation
            self.scene_creator = create_scene_progressive(
                self.config
            )
        
        # Restart scene using event-based approach
        def restart_scene():
            self.status_label.configure(text="Restarting scene...")
            # Use an event to trigger the restart instead of a direct function call
            EM.publish('scene/restart', self.config)
            
        # Clear scene using event-based approach
        def clear_scene():
            self.status_label.configure(text="Clearing scene...")
            # Use an event to trigger the clearing instead of a direct function call
            EM.publish('scene/clear', None)
            
        # Cancel ongoing scene creation if any
        def cancel_scene_creation():
            if self.scene_creator:
                self.scene_creator.cancel()
                # The scene_creator will fire the SCENE_CREATION_CANCELED event
                # which we're already listening for, so no need to manually update UI
        
        # Scene control buttons
        self.scene_buttons = []
        for text, command in [
            ("Create Environment", create_scene_with_progress),
            ("Clear Environment", clear_scene),
            ("Cancel Creating Environment", cancel_scene_creation),
        ]:
            btn = ttk.Button(parent, text=text, command=command)
            btn.pack(fill="x", pady=5)
            self.scene_buttons.append(btn)
            
        # Quit button
        ttk.Button(parent, text="Quit", command=self._quit).pack(fill="x", pady=(15,0))

    def _build_config_tab(self, parent):
        ttk.Label(parent, text="Configuration", font=("Helvetica", 14, "bold")).pack(pady=(0,10))
        # Fields grid
        for field in FIELDS:
            key, desc, typ = field['key'], field['desc'], field['type']
            frame = ttk.Frame(parent)
            frame.pack(fill="x", pady=2)
            ttk.Label(frame, text=desc+":", width=20).pack(side="left")
            if typ is bool:
                var = tk.BooleanVar(value=self.config.get(key, False))
                chk = ttk.Checkbutton(frame, variable=var)
                chk.pack(side="left")
                var.trace_add('write', lambda *_, k=key, v=var: self._update_config(k, v.get()))
            else:
                var = tk.StringVar(value=str(self.config.get(key, '')))
                ent = ttk.Entry(frame, textvariable=var)
                ent.pack(side="left", fill="x", expand=True)
                ent.bind('<Return>', lambda e, k=key, v=var: self._update_config(k, v.get()))

    def _update_config(self, key, value):
        # convert value to proper type and update
        for field in FIELDS:
            if field['key'] == key:
                typ = field['type']
                try:
                    self.config[key] = typ(value)
                    EM.publish('config/updated', None)
                except Exception:
                    pass
                break

    def _quit(self):
        # Signal application to quit and close GUI
        EM.publish('simulation/shutdown', None)
        self.root.destroy()
        
    def _on_scene_progress(self, progress):
        """Update the progress bar when scene creation progresses."""
        self.progress_var.set(progress)
        self.status_label.configure(text=f"Creating scene... {int(progress * 100)}%")
        
    def _on_scene_completed(self, _):
        """Handle scene creation completion."""
        self.status_label.configure(text="Scene creation completed!")
        # Re-enable all buttons
        for btn in self.scene_buttons:
            btn.configure(state="normal")
        self.root.after(1000, lambda: self.progress_bar.pack_forget())
        self.scene_creator = None
        
    def _on_scene_canceled(self, _):
        """Handle scene creation cancellation."""
        self.status_label.configure(text="Scene creation canceled")
        # Re-enable all buttons
        for btn in self.scene_buttons:
            btn.configure(state="normal")
        self.root.after(500, lambda: self.progress_bar.pack_forget())
        self.scene_creator = None

    def _on_scene_creation_request(self, config=None):
        """
        Handle a scene creation request from the menu system.
        This gets triggered when the user selects 'Create disaster area' from the main menu.
        """
        # Use provided config or fall back to the current config
        if config is None:
            config = self.config
            
        # Disable buttons except for the Cancel button during scene creation
        for i, btn in enumerate(self.scene_buttons):
            if "Cancel" not in btn["text"]:  # Keep the Cancel button enabled
                btn.configure(state="disabled")
            else:
                btn.configure(state="normal")  # Ensure the Cancel button is enabled
        
        # Show progress bar
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_var.set(0.0)
        self.status_label.configure(text="Creating scene...")
        
        # Start progressive scene creation
        self.scene_creator = create_scene_progressive(
            self.config
        )

    def run(self):
        self.root.mainloop()
        
    def cleanup(self):
        """Unsubscribe from events when the menu system is closed"""
        EM.unsubscribe(SCENE_CREATION_PROGRESS, self._on_scene_progress)
        EM.unsubscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        EM.unsubscribe(SCENE_CREATION_CANCELED, self._on_scene_canceled)
