# Managers/menu_system.py

import tkinter as tk
from tkinter import ttk
from Core.event_manager import EventManager
from Utils.scene_utils import clear_disaster_area, restart_disaster_area
from Managers.scene_core import create_scene
from Managers.scene_progressive import (
    create_scene_progressive, 
    SCENE_CREATION_PROGRESS, 
    SCENE_CREATION_COMPLETED, 
    SCENE_CREATION_CANCELED
)
from Utils.config_utils import FIELDS

class MenuSystem:
    def __init__(self, event_manager, sim, config: dict, sim_command_queue):
        self.event_manager = event_manager
        self.sim_queue = sim_command_queue
        self.sim = sim
        self.config = config
        self.scene_creator = None
        self.progress_var = None  # For progress bar

        # Build and style main window
        self.root = tk.Tk()
        self.root.title("Disaster Simulation Control")
        self.root.geometry("320x400")
        self.root.configure(bg="#e5e5e5")
        self._build_ui()

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
        
        # Enqueue helper - for backward compatibility
        def enqueue(fn, args=None):
            if args is None:
                args = []
            self.sim_queue.put((fn, args, {}))
            self.event_manager.publish("scene/created", None)
        
        # Create scene with progressive approach
        def create_scene_with_progress():
            # Disable all buttons during scene creation
            for btn in self.scene_buttons:
                btn.configure(state="disabled")
            
            # Show progress bar
            self.progress_bar.pack(fill="x", pady=5)
            self.progress_var.set(0.0)
            self.status_label.configure(text="Creating scene...")
            
            # Subscribe to scene creation events
            self.event_manager.subscribe(SCENE_CREATION_PROGRESS, self._on_scene_progress)
            self.event_manager.subscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
            self.event_manager.subscribe(SCENE_CREATION_CANCELED, self._on_scene_canceled)
            
            # Start progressive scene creation
            self.scene_creator = create_scene_progressive(
                self.sim,
                self.config,
                self.event_manager
            )
        
        # Restart scene with progressive approach
        def restart_scene_with_progress():
            # For now, use the original restart function
            self.status_label.configure(text="Restarting scene...")
            self.sim_queue.put((restart_disaster_area, [self.config, self.event_manager], {}))
            self.root.after(200, lambda: self.status_label.configure(text="Scene restarted"))
            # No need for manual event publishing, handled within restart_disaster_area now
            
        # Clear scene - no threading needed as it's fast
        def clear_scene():
            self.status_label.configure(text="Clearing scene...")
            self.sim_queue.put((clear_disaster_area, [], {}))
            self.root.after(200, lambda: self.status_label.configure(text="Scene cleared"))
            self.event_manager.publish("scene/created", None)
        
        # Cancel ongoing scene creation if any
        def cancel_scene_creation():
            if self.scene_creator:
                self.scene_creator.cancel()
                self.status_label.configure(text="Scene creation cancelled")
                for btn in self.scene_buttons:
                    btn.configure(state="normal")
                self.root.after(500, lambda: self.progress_bar.pack_forget())
                self.scene_creator = None
        
        # Scene control buttons
        self.scene_buttons = []
        for text, command in [
            ("Create Disaster", create_scene_with_progress),
            ("Restart Disaster", restart_scene_with_progress),
            ("Clear Disaster", clear_scene),
            ("Cancel Creation", cancel_scene_creation),
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
                    self.event_manager.publish('config/updated', None)
                except Exception:
                    pass
                break

    def _quit(self):
        # Signal application to quit and close GUI
        self.event_manager.publish('app/quit', None)
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
        # Unsubscribe from events
        self.event_manager.unsubscribe(SCENE_CREATION_PROGRESS, self._on_scene_progress)
        self.event_manager.unsubscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        self.event_manager.unsubscribe(SCENE_CREATION_CANCELED, self._on_scene_canceled)
        
    def _on_scene_canceled(self, _):
        """Handle scene creation cancellation."""
        self.status_label.configure(text="Scene creation canceled")
        # Re-enable all buttons
        for btn in self.scene_buttons:
            btn.configure(state="normal")
        self.root.after(500, lambda: self.progress_bar.pack_forget())
        self.scene_creator = None
        # Unsubscribe from events
        self.event_manager.unsubscribe(SCENE_CREATION_PROGRESS, self._on_scene_progress)
        self.event_manager.unsubscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        self.event_manager.unsubscribe(SCENE_CREATION_CANCELED, self._on_scene_canceled)

    def run(self):
        self.root.mainloop()
