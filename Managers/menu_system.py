# Managers/menu_system.py

import tkinter as tk
from tkinter import ttk
from Core.event_manager import EventManager
from Utils.scene_utils import clear_disaster_area, restart_disaster_area
from Managers.scene_manager import create_scene
from Utils.config_utils import FIELDS

class MenuSystem:
    def __init__(self, event_manager, sim, config: dict, sim_command_queue):
        self.event_manager = event_manager
        self.sim_queue = sim_command_queue
        self.config = config

        # Build and style main window
        self.root = tk.Tk()
        self.root.title("Disaster Simulation Control")
        self.root.geometry("320x360")
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
        # Enqueue helper
        def enqueue(fn, args=None):
            if args is None:
                args = []
            self.sim_queue.put((fn, args, {}))
            self.event_manager.publish("scene/created", None)
        # Buttons
        for text, fn, args in [
            ("Create Disaster", create_scene, [self.config]),
            ("Restart Disaster", restart_disaster_area, [self.config]),
            ("Clear Disaster", clear_disaster_area, []),
        ]:
            btn = ttk.Button(parent, text=text, command=lambda f=fn, a=args: enqueue(f, a))
            btn.pack(fill="x", pady=5)
        # Quit
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

    def run(self):
        self.root.mainloop()
