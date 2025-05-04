# Managers/menu_system.py

import tkinter as tk
from tkinter import ttk
from Utils.config_utils import FIELDS
from Utils.scene_utils import restart_disaster_area
from Managers.scene_manager import (
    create_scene, clear_scene, cancel_scene_creation,
    SCENE_START_CREATION, SCENE_CREATION_PROGRESS, 
    SCENE_CREATION_COMPLETED, SCENE_CREATION_CANCELED
)

from Managers.Connections.sim_connection import SimConnection
SC = SimConnection.get_instance()

from Core.event_manager import EventManager
EM = EventManager.get_instance()


class MenuSystem:
    def __init__(self, config: dict, sim_command_queue):
        self.sim_queue = sim_command_queue
        self.sim = SC.sim
        self.config = config
        # Map to hold config UI variables and widgets
        self._config_vars = {}
        self._config_widgets = {}

        # Subscribe to config updates to sync UI
        EM.subscribe('config/updated', self._on_config_updated_gui)

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
        
        # Subscribe to UI update trigger
        EM.subscribe('trigger_ui_update', self._force_ui_update)
        
        # Subscribe to dataset capture complete for victim distance updates
        EM.subscribe('dataset/capture/complete', self._update_victim_indicator)
        
    def _force_ui_update(self, _):
        """Force the UI to update immediately"""
        try:
            self.root.update()
        except Exception as e:
            if hasattr(self, 'verbose') and self.verbose:
                print(f"Error updating UI: {e}")

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
        config_tab = ttk.Frame(notebook, padding=5)  # Reduced padding to maximize space
        notebook.add(config_tab, text="Config")
        self._build_config_tab(config_tab)
        
        # Status tab with victim indicator
        status_tab = ttk.Frame(notebook, padding=10)
        notebook.add(status_tab, text="Status")
        self._build_status_tab(status_tab)
        
        # Make window resizable
        self.root.resizable(True, True)
        # Set minimum size to prevent UI elements from becoming too cramped
        self.root.minsize(320, 400)

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
        
        # Create scene with event-driven approach
        def create_scene_with_event():
            # Apply all config changes first to ensure latest values are used
            self._apply_all_config_changes()
            
            # Disable all buttons during scene creation
            for btn in self.scene_buttons:
                if "Cancel" not in btn["text"]:
                    btn.configure(state="disabled")
                else:
                    # Enable the cancel button during scene creation
                    btn.configure(state="normal")
            
            # Show progress bar
            self.progress_bar.pack(fill="x", pady=5)
            self.progress_var.set(0.0)
            self.status_label.configure(text="Creating scene...")
            
            # Start scene creation via event system
            create_scene(self.config)
        
        # Restart scene using event-based approach
        def restart_scene():
            self.status_label.configure(text="Restarting scene...")
            restart_disaster_area(self.config)
            
        # Clear scene using event-based approach
        def clear_scene_action():
            self.status_label.configure(text="Clearing scene...")
            clear_scene()
            
        # Cancel ongoing scene creation 
        def cancel_creation():
            cancel_scene_creation()
            self.status_label.configure(text="Canceling scene creation...")
        
        # Scene control buttons
        self.scene_buttons = []
        for text, command in [
            ("Create Environment", create_scene_with_event),
            ("Clear Environment", clear_scene_action),
            ("Cancel Creating Environment", cancel_creation),
        ]:
            btn = ttk.Button(parent, text=text, command=command)
            
            # Initially disable the Cancel button since creation is not in progress
            if "Cancel" in text:
                btn.configure(state="disabled")
            btn.pack(fill="x", pady=5)
            self.scene_buttons.append(btn)
            
        # Quit button
        ttk.Button(parent, text="Quit", command=self._quit).pack(fill="x", pady=(15,0))

    def _build_config_tab(self, parent):
        # Create a canvas with scrollbar for the config options
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure the canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create a window in the canvas to hold the scrollable frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Title
        ttk.Label(scrollable_frame, text="Configuration", font=("Helvetica", 14, "bold")).pack(pady=(0,10))
        
        # Add fields to the scrollable frame
        for field in FIELDS:
            key, desc, typ = field['key'], field['desc'], field['type']
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill="x", pady=2)
            ttk.Label(frame, text=desc+":", width=20).pack(side="left")
            if typ is bool:
                var = tk.BooleanVar(value=self.config.get(key, False))
                chk = ttk.Checkbutton(frame, variable=var)
                chk.pack(side="left")
                var.trace_add('write', lambda *_, k=key, v=var: self._update_config(k, v.get()))
                widget = chk
            else:
                var = tk.StringVar(value=str(self.config.get(key, '')))
                ent = ttk.Entry(frame, textvariable=var)
                ent.pack(side="left", fill="x", expand=True)
                # Update config on Enter key press
                ent.bind('<Return>', lambda e, k=key, v=var: self._update_config(k, v.get()))
                # Also update config when field loses focus
                ent.bind('<FocusOut>', lambda e, k=key, v=var: self._update_config(k, v.get()))
                widget = ent
            # store for synchronization and feedback
            self._config_vars[key] = var
            self._config_widgets[key] = widget
            
        # Add a "Apply All Changes" button to ensure all values are synchronized
        apply_btn = ttk.Button(scrollable_frame, text="Apply All Changes", 
                              command=self._apply_all_config_changes)
        apply_btn.pack(fill="x", pady=(15, 5))
        
        # Add mouse wheel scrolling support
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        # For Linux/macOS (different event)
        canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))

    def _build_status_tab(self, parent):
        """Build the status tab with victim distance indicator"""
        # Title
        ttk.Label(parent, text="Simulation Status", font=("Helvetica", 16, "bold")).pack(pady=(0,10))
        
        # Victim indicator section
        victim_frame = ttk.LabelFrame(parent, text="Victim Detection")
        victim_frame.pack(fill="x", pady=10, padx=5)
        
        # Distance indicator
        ttk.Label(victim_frame, text="Distance to victim:").pack(pady=5)
        self.distance_var = tk.StringVar(value="Not detected")
        self.distance_label = ttk.Label(victim_frame, textvariable=self.distance_var, font=("Helvetica", 14))
        self.distance_label.pack(pady=5)
        
        # Elevation indicator - simplified to just show numerical value
        ttk.Label(victim_frame, text="Elevation difference:").pack(pady=5)
        self.elevation_var = tk.StringVar(value="Not detected")
        self.elevation_label = ttk.Label(victim_frame, textvariable=self.elevation_var, font=("Helvetica", 14))
        self.elevation_label.pack(pady=5)
        
        # Direction indicator (graphical)
        ttk.Label(victim_frame, text="Direction:").pack(pady=5)
        canvas_size = 150
        self.direction_canvas = tk.Canvas(victim_frame, width=canvas_size, height=canvas_size*2, 
                                         bg="black", highlightthickness=1, highlightbackground="gray")
        self.direction_canvas.pack(pady=10)
        
        # Draw the initial state (no detection)
        self._draw_direction_indicator(None, None, None)
        
        # Signal strength (distance-based)
        ttk.Label(victim_frame, text="Signal strength:").pack(pady=5)
        self.signal_var = tk.DoubleVar(value=0.0)
        self.signal_bar = ttk.Progressbar(victim_frame, variable=self.signal_var, maximum=1.0)
        self.signal_bar.pack(fill="x", pady=5, padx=10)

    def _apply_all_config_changes(self):
        """Apply all changes to the configuration."""
        for key, var in self._config_vars.items():
            self._update_config(key, var.get())
            
        # Provide feedback to the user
        self.status_label.configure(text="Configuration updated!")
        self.root.after(1000, lambda: self.status_label.configure(text=""))

    def _update_config(self, key, value):
        # convert value to proper type and update
        for field in FIELDS:
            if field['key'] == key:
                typ = field['type']
                try:
                    self.config[key] = typ(value)
                    EM.publish('config/updated', key)
                except Exception:
                    pass
                break

    def _on_config_updated_gui(self, key):
        """
        Handle external or internal config updates and sync GUI elements.
        key: the configuration key that was updated.
        """
        # Update the corresponding variable
        if key in self._config_vars:
            var = self._config_vars[key]
            new_val = self.config.get(key)
            # Set variable (convert to string for non-bool)
            if isinstance(var, tk.StringVar):
                var.set(str(new_val))
            else:
                var.set(bool(new_val))
            # Visual feedback: highlight updated widget
            widget = self._config_widgets.get(key)
            if widget:
                try:
                    widget.configure(background='lightyellow')
                    # revert after short delay
                    widget.after(800, lambda w=widget: w.configure(background='white'))
                except Exception:
                    pass
        else:
            # If key is None or unknown, refresh all
            for k, var in self._config_vars.items():
                val = self.config.get(k)
                if isinstance(var, tk.StringVar):
                    var.set(str(val))
                else:
                    var.set(bool(val))

    def _quit(self):
        # Signal application to quit and close GUI
        EM.publish('simulation/shutdown', None)
        self.root.destroy()
        
    def _on_scene_progress(self, data):
        """Update the progress bar and status label when scene creation progresses."""
        def update_ui():
            progress = data.get('progress', 0.0)
            current_category = data.get('current_category', '')
            completed_objects = data.get('completed_objects', 0)
            total_objects = data.get('total_objects', 0)
            
            # Set progress bar value
            self.progress_var.set(progress)
            
            # Format appropriate message based on creation state
            if current_category == 'complete':
                message = f"Scene created - {total_objects}/{total_objects} elements"
            else:
                # Format the category name nicely (capitalize)
                category_display = current_category.capitalize()
                message = f"Creating scene - {category_display}: {completed_objects}/{total_objects} elements"
            
            # Update status label
            self.status_label.configure(text=message)
            
            # Force the UI to update
            self.root.update_idletasks()
            
        # Schedule UI update in the main thread
        self.root.after(0, update_ui)
        
    def _on_scene_completed(self, _):
        """Handle scene creation completion."""
        def update_ui():
            self.status_label.configure(text="Scene creation completed!")
            # Re-enable normal buttons and specifically disable the Cancel button
            for btn in self.scene_buttons:
                if "Cancel" in btn["text"]:
                    btn.configure(state="disabled")  # Disable the cancel button
                else:
                    btn.configure(state="normal")  # Enable other buttons
            self.progress_bar.pack_forget()
        
        # Schedule the update on the main thread
        self.root.after(0, update_ui)
        
    def _on_scene_canceled(self, _):
        """Handle scene creation cancellation."""
        def update_ui():
            self.status_label.configure(text="Scene creation canceled")
            # Re-enable normal buttons and specifically disable the Cancel button
            for btn in self.scene_buttons:
                if "Cancel" in btn["text"]:
                    btn.configure(state="disabled")  # Disable the cancel button
                else:
                    btn.configure(state="normal")  # Enable other buttons
            self.progress_bar.pack_forget()
        
        # Schedule the update on the main thread
        self.root.after(0, update_ui)

    def _on_scene_creation_request(self, config=None):
        """
        Handle a scene creation request from the menu system.
        This gets triggered when the user selects 'Create disaster area' from the main menu.
        """
        # Apply all configuration changes first
        self._apply_all_config_changes()
        
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
        
        # Start scene creation via event
        create_scene(config)

    def _update_victim_indicator(self, data):
        """Update the victim distance and direction indicator based on capture data"""
        # Extract victim vector data (dx, dy, dz, distance)
        if 'victim_vec' not in data:
            return
            
        victim_vec = data.get('victim_vec', (0, 0, 0, 0))
        if len(victim_vec) < 4:
            return
            
        dx, dy, dz, distance = victim_vec
        
        # Update UI safely
        def update_ui():
            # Update distance text
            if distance <= 0:
                self.distance_var.set("Not detected")
                self.elevation_var.set("Not detected")
            else:
                self.distance_var.set(f"{distance:.2f} meters")
                
                # Update elevation text with simple numerical format
                if abs(dz) < 0.1:  # If very close to level
                    self.elevation_var.set("Same level (±0.1m)")
                    self.elevation_label.configure(foreground="green")
                elif dz > 0:
                    self.elevation_var.set(f"{dz:.2f}m above drone")
                    # Color based on how much higher (harder to reach)
                    if dz > 3:
                        self.elevation_label.configure(foreground="red")
                    else:
                        self.elevation_label.configure(foreground="orange")
                else:  # dz < 0
                    self.elevation_var.set(f"{abs(dz):.2f}m below drone")
                    # Color based on how much lower (easier to spot)
                    if abs(dz) > 3:
                        self.elevation_label.configure(foreground="orange")
                    else:
                        self.elevation_label.configure(foreground="green")
                
            # Update direction indicator
            self._draw_direction_indicator(dx, dy, dz)
            
            # Update signal strength (inverse of distance)
            if distance <= 0:
                self.signal_var.set(0.0)
            else:
                # Normalize signal strength: stronger when closer
                # Maximum strength at 1m, diminishes with distance
                strength = min(1.0, 1.0 / max(1.0, distance))
                self.signal_var.set(strength)
                
            # Color-code the distance label based on proximity
            if distance <= 0:
                self.distance_label.configure(foreground="gray")
            elif distance < 5.0:
                self.distance_label.configure(foreground="green")
            elif distance < 15.0:
                self.distance_label.configure(foreground="orange")
            else:
                self.distance_label.configure(foreground="red")
                
        # Schedule UI update on the main thread
        self.root.after(0, update_ui)
        
    def _draw_direction_indicator(self, dx, dy, dz):
        """Draw a direction indicator on the canvas showing victim direction"""
        # Clear canvas
        self.direction_canvas.delete("all")
        canvas_width = self.direction_canvas.winfo_width()
        canvas_height = self.direction_canvas.winfo_height()
        
        # Ensure we have minimum dimensions
        if canvas_width < 20 or canvas_height < 20:
            canvas_width = canvas_height = 150
            
        # Calculate center
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        radius = min(center_x, center_y) - 10
        
        # Draw outer circle (radar)
        self.direction_canvas.create_oval(
            center_x - radius, center_y - radius, 
            center_x + radius, center_y + radius, 
            outline="green", width=2
        )
        
        # Draw crosshairs
        self.direction_canvas.create_line(
            center_x, center_y - radius, center_x, center_y + radius, 
            fill="green", dash=(4, 4)
        )
        self.direction_canvas.create_line(
            center_x - radius, center_y, center_x + radius, center_y, 
            fill="green", dash=(4, 4)
        )
        
        # If direction is valid, draw victim indicator
        if dx is not None and dy is not None and (dx != 0 or dy != 0):
            # Calculate endpoint of direction vector
            # Note: Invert y because canvas coordinates increase downward
            end_x = center_x + dx * radius
            end_y = center_y - dy * radius  # Inverted y-axis
            
            # Draw direction vector
            self.direction_canvas.create_line(
                center_x, center_y, end_x, end_y,
                fill="red", width=3, arrow=tk.LAST
            )
            
            # Draw victim point
            self.direction_canvas.create_oval(
                end_x - 5, end_y - 5, end_x + 5, end_y + 5,
                fill="red", outline="white"
            )
        else:
            # If no vector, draw "not detected" text
            self.direction_canvas.create_text(
                center_x, center_y,
                text="No victim detected",
                fill="gray", font=("Helvetica", 10)
            )
            
        # Label the directions
        self.direction_canvas.create_text(center_x, center_y - radius - 10, text="Forward", fill="white")
        self.direction_canvas.create_text(center_x, center_y + radius + 10, text="Back", fill="white")
        self.direction_canvas.create_text(center_x - radius - 10, center_y, text="Left", fill="white", angle=90)
        self.direction_canvas.create_text(center_x + radius + 10, center_y, text="Right", fill="white", angle=270)

    def run(self):
        self.root.mainloop()
        
    def cleanup(self, data=None):
        """Unsubscribe from events when the menu system is closed"""
        EM.unsubscribe(SCENE_CREATION_PROGRESS, self._on_scene_progress)
        EM.unsubscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        EM.unsubscribe(SCENE_CREATION_CANCELED, self._on_scene_canceled)
        EM.unsubscribe('dataset/capture/complete', self._update_victim_indicator)
