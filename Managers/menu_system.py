# Managers/menu_system.py

import tkinter as tk
from tkinter import ttk
import logging
from Utils.config_utils import CONFIG_GROUPS, parse_coordinate_tuple
from Utils.scene_utils import restart_disaster_area
from Utils.log_utils import get_logger, LOG_LEVEL_DEBUG, LOG_LEVEL_INFO, LOG_LEVEL_WARNING, LOG_LEVEL_ERROR, LOG_LEVEL_CRITICAL
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
        # Store verbose setting for easy access
        self.verbose = config.get('verbose', False)
        # Get logger instance
        self.logger = get_logger()

        # Subscribe to config updates to sync UI
        EM.subscribe('config/updated', self._on_config_updated_gui)

        self.progress_var = None  # For progress bar

        # Build and style main window
        self.root = tk.Tk()
        self.root.title("Disaster Simulation Control")
        self.root.geometry("320x400")
        self.root.configure(bg="#e5e5e5")
        
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Initializing UI components")
            
        self._build_ui()
        
        # Register for scene-related events
        self._register_event_handlers()
        
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Initialization complete")

    def _register_event_handlers(self):
        """Set up event handlers for scene-related events"""
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Registering event handlers")
            
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
        
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Event handlers registered")

    def _force_ui_update(self, _):
        """Force the UI to update immediately"""
        try:
            self.root.update()
        except Exception as e:
            if hasattr(self, 'verbose') and self.verbose:
                self.logger.error("MenuSystem", f"Error updating UI: {e}")

    def _on_simulation_frame(self, _):
        """Wrapper method to handle simulation frame events and update the UI safely"""
        try:
            self.root.update()
        except Exception as e:
            self.logger.error("MenuSystem", f"Error updating UI: {e}")

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
        
        # Handle tab changes to resize window when switching to Status tab
        def on_tab_changed(event):
            tab_id = notebook.index(notebook.select())
            if tab_id == 2:  # Status tab (0-based index)
                # Make window larger for Status tab
                self.root.geometry("400x600")
            else:
                # Default size for other tabs
                self.root.geometry("320x400")
        
        # Bind the tab change event
        notebook.bind("<<NotebookTabChanged>>", on_tab_changed)

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
        
        # Create notification popup for config changes
        self.notification = tk.Label(self.root, text="", background="#4CAF50", foreground="white",
                              relief="solid", borderwidth=1, font=("Helvetica", 10), padx=10, pady=5)
        self.notification.place_forget()  # Hide initially
        
        # Create UI for each group
        self._group_frames = {}
        
        for group in CONFIG_GROUPS:
            # Create group frame
            group_frame = ttk.LabelFrame(scrollable_frame, text=group["name"])
            group_frame.pack(fill="x", pady=5, padx=5)
            
            # Add fields to the group
            for field in group['fields']:
                key, desc, typ = field['key'], field['desc'], field['type']
                tooltip = field.get('tooltip', '')
                
                frame = ttk.Frame(group_frame)
                frame.pack(fill="x", pady=2)
                
                # Create label with tooltip
                label = ttk.Label(frame, text=desc+":", width=20)
                label.pack(side="left")
                
                # Add tooltip functionality
                self._create_tooltip(label, tooltip)
                
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
                
                # Store for synchronization and feedback
                self._config_vars[key] = var
                self._config_widgets[key] = widget
        
        # Add logging options group
        log_frame = ttk.LabelFrame(scrollable_frame, text="Logging Options")
        log_frame.pack(fill="x", pady=5, padx=5)
        
        # Log level dropdown
        level_frame = ttk.Frame(log_frame)
        level_frame.pack(fill="x", pady=2)
        
        ttk.Label(level_frame, text="Log Level:", width=20).pack(side="left")
        
        # Create a dropdown for log levels
        self.log_level_var = tk.StringVar(value="INFO")
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_dropdown = ttk.Combobox(level_frame, textvariable=self.log_level_var, values=log_levels, state="readonly")
        level_dropdown.pack(side="left", fill="x", expand=True)
        
        # Create a button to apply the log level change
        apply_button = ttk.Button(log_frame, text="Apply Log Level", 
                                 command=self._change_log_level)
        apply_button.pack(fill="x", pady=5)
        
        # Add file logging toggle
        file_log_frame = ttk.Frame(log_frame)
        file_log_frame.pack(fill="x", pady=2)
        
        ttk.Label(file_log_frame, text="Enable File Logging:", width=20).pack(side="left")
        
        # Create checkbox for file logging
        self.file_logging_var = tk.BooleanVar(value=False)
        file_logging_chk = ttk.Checkbutton(file_log_frame, variable=self.file_logging_var)
        file_logging_chk.pack(side="left")
        
        # Button to apply file logging setting
        apply_file_log_button = ttk.Button(log_frame, text="Apply File Logging", 
                                         command=self._toggle_file_logging)
        apply_file_log_button.pack(fill="x", pady=5)
        
        # Add "Reset to Defaults" button
        reset_btn = ttk.Button(scrollable_frame, text="Reset to Defaults", 
                             command=self._reset_to_defaults)
        reset_btn.pack(fill="x", pady=5)
        
        # Add mouse wheel scrolling support
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        # For Linux/macOS (different event)
        canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))
    
    def _show_notification(self, message, duration=800, success=True):
        """Show a temporary popup notification"""
        # Configure the notification based on success/error
        if success:
            self.notification.configure(
                text=message, 
                background="#4CAF50",  # Green for success
                foreground="white"
            )
        else:
            self.notification.configure(
                text=message, 
                background="#F44336",  # Red for error
                foreground="white"
            )
        
        # Apply semi-transparency (using alpha channel)
        # This is done by making the background color have some transparency
        self.notification.winfo_toplevel().attributes('-alpha', 0.85)
        
        # Calculate position (centered at the top of the window)
        width = self.notification.winfo_reqwidth()
        if width == 0:  # If not yet rendered, estimate based on text length
            width = len(message) * 7 + 20
        
        x = (self.root.winfo_width() - width) // 2
        y = 10  # 10 pixels from the top
        
        # Show the notification
        self.notification.place(x=max(x, 0), y=y)
        
        # Schedule hiding the notification
        self.root.after(duration, self._hide_notification)
    
    def _hide_notification(self):
        """Hide the notification and restore window transparency"""
        self.notification.place_forget()
        self.notification.winfo_toplevel().attributes('-alpha', 1.0)  # Restore full opacity

    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        if not text:  # Skip if no tooltip
            return
            
        # Create the tooltip as a regular tkinter Label (not ttk)
        tooltip = tk.Label(self.root, text=text, background="#ffffe0", 
                           relief="solid", borderwidth=1, padx=4, pady=2)
        tooltip.pack_forget()
        
        def on_enter(event):
            # Position the tooltip near the mouse pointer
            tooltip.place(x=event.x_root + 15, y=event.y_root + 10)
            
        def on_leave(event):
            tooltip.place_forget()
            
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _reset_to_defaults(self):
        """Reset all configurations to default values"""
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Resetting configuration to defaults")
            
        from Utils.config_utils import get_default_config
        default_config = get_default_config()
        
        # Update all values
        for key, var in self._config_vars.items():
            if key in default_config:
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(default_config[key]))
                else:
                    var.set(str(default_config[key]))
        
        # Apply all changes
        self._apply_all_config_changes()
        
        # Show confirmation using the popup notification instead of status label
        self._show_notification("Reset to defaults", duration=1000)
        
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Configuration reset complete")

    def _apply_all_config_changes(self):
        """Apply all changes to the configuration."""
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Applying all configuration changes")
            
        for key, var in self._config_vars.items():
            self._update_config(key, var.get(), show_notification=False)
            
        # Update verbose setting for this instance
        self.verbose = self.config.get('verbose', False)
            
        # Show a single notification for all changes
        self._show_notification("All settings applied", duration=1000)
        
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "All configuration changes applied")

    def _update_config(self, key, value, show_notification=True):
        """Update a configuration value with proper type conversion"""
        # Find the field definition to get its type
        field_type = None
        
        # Search through all groups to find the field
        for group in CONFIG_GROUPS:
            for field in group['fields']:
                if field['key'] == key:
                    field_type = field['type']
                    break
            if field_type:
                break
                
        if not field_type:
            return  # Field not found
            
        try:
            # Handle special cases
            if key == "clear_zone_center":
                # Parse the coordinate tuple
                try:
                    new_value = parse_coordinate_tuple(value)
                    # Only update and show notification if the value has changed
                    if str(new_value) != str(self.config.get(key, "")):
                        self.config[key] = new_value
                        # Visual feedback on success using popup
                        if show_notification:
                            self._show_notification(f"Updated: {key}", duration=800)
                        # Publish the update event
                        EM.publish('config/updated', key)
                        
                        if self.verbose and key == 'verbose':
                            self.logger.info("MenuSystem", f"Verbose mode {'enabled' if new_value else 'disabled'}")
                        elif self.verbose:
                            self.logger.verbose_log("MenuSystem", f"Updated config {key} = {new_value}")
                except ValueError as e:
                    # Show error as popup notification
                    if show_notification:
                        self._show_notification(f"Error: {str(e)}", duration=1500, success=False)
                    if self.verbose:
                        self.logger.error("MenuSystem", f"Error updating {key}: {e}")
                    return
            else:
                # Regular type conversion
                try:
                    # Convert to the correct type
                    new_value = field_type(value)
                    
                    # Only update and show notification if the value has changed
                    if new_value != self.config.get(key, None):
                        old_value = self.config.get(key, None)
                        self.config[key] = new_value
                        
                        # Update verbose setting if that's what changed
                        if key == 'verbose':
                            self.verbose = new_value
                            self.logger.info("MenuSystem", f"Verbose mode {'enabled' if new_value else 'disabled'}")
                        elif self.verbose:
                            self.logger.verbose_log("MenuSystem", f"Updated config {key} = {new_value} (was {old_value})")
                            
                        # Visual feedback on success using popup
                        if show_notification:
                            self._show_notification(f"Updated: {key}", duration=800)
                        # Publish the update event
                        EM.publish('config/updated', key)
                except Exception as e:
                    # Show error message as popup
                    if show_notification:
                        self._show_notification(f"Error: {str(e)}", duration=1500, success=False)
                    if self.verbose:
                        self.logger.error("MenuSystem", f"Error updating {key}: {e}")
        except Exception as e:
            # Show error message as popup
            if show_notification:
                self._show_notification(f"Error: {str(e)}", duration=1500, success=False)
            if self.verbose:
                self.logger.error("MenuSystem", f"Error updating {key}: {e}")

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
            # Don't show notification here as it would duplicate
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
        if self.verbose:
            print("[MenuSystem] Shutting down application...")
            
        EM.publish('simulation/shutdown', None)
        self.root.destroy()
        
    def _on_scene_progress(self, data):
        """Update the progress bar and status label when scene creation progresses."""
        progress = data.get('progress', 0.0)
        current_category = data.get('current_category', '')
        completed_objects = data.get('completed_objects', 0)
        total_objects = data.get('total_objects', 0)
        
        # Only log important progress milestones if verbose
        if self.verbose and (progress == 0.0 or progress == 1.0 or current_category == 'complete' or 
                             (completed_objects > 0 and completed_objects % 5 == 0)):
            self.logger.verbose_log("MenuSystem", f"Scene creation progress: {progress:.0%} - {completed_objects}/{total_objects} objects created")
        
        def update_ui():
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
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Scene creation completed successfully")
            
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
        if self.verbose:
            self.logger.verbose_log("MenuSystem", "Scene creation canceled by user")
            
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
        
        # Only schedule UI update if root still exists
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        
        # Update UI safely
        def update_ui():
            # Verify that UI elements still exist before updating
            if not hasattr(self, 'distance_var') or not hasattr(self, 'elevation_var'):
                return
                
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
                
            # Update direction indicator if canvas still exists
            if hasattr(self, 'direction_canvas') and self.direction_canvas.winfo_exists():
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
        
        # Use a try-except block when scheduling the update
        try:
            # Schedule UI update on the main thread
            self.root.after(0, update_ui)
        except Exception as e:
            print(f"[MenuSystem] Error scheduling UI update: {e}")
            
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
        canvas_size = 250  # Increased from 150 to 250 for better visualization
        self.direction_canvas = tk.Canvas(victim_frame, width=canvas_size, height=canvas_size, 
                                         bg="black", highlightthickness=1, highlightbackground="gray")
        self.direction_canvas.pack(pady=10)
        
        # Draw the initial state (no detection)
        self._draw_direction_indicator(None, None, None)
        
        # Signal strength (distance-based)
        ttk.Label(victim_frame, text="Signal strength:").pack(pady=5)
        self.signal_var = tk.DoubleVar(value=0.0)
        self.signal_bar = ttk.Progressbar(victim_frame, variable=self.signal_var, maximum=1.0)
        self.signal_bar.pack(fill="x", pady=5, padx=10)

    def _change_log_level(self):
        """Change the logging level at runtime"""
        level_str = self.log_level_var.get()
        level_map = {
            "DEBUG": LOG_LEVEL_DEBUG,
            "INFO": LOG_LEVEL_INFO,
            "WARNING": LOG_LEVEL_WARNING,
            "ERROR": LOG_LEVEL_ERROR,
            "CRITICAL": LOG_LEVEL_CRITICAL
        }
        
        if level_str in level_map:
            level = level_map[level_str]
            self.logger.set_level(level)
            self._show_notification(f"Log level changed to {level_str}", duration=1000)
        else:
            self._show_notification(f"Invalid log level: {level_str}", duration=1000, success=False)
    
    def _toggle_file_logging(self):
        """Toggle file logging on or off"""
        enabled = self.file_logging_var.get()
        
        try:
            if enabled:
                self.logger.configure_file_logging(enabled=True, level=LOG_LEVEL_DEBUG)
                self._show_notification("File logging enabled", duration=1000)
            else:
                self.logger.configure_file_logging(enabled=False)
                self._show_notification("File logging disabled", duration=1000)
        except Exception as e:
            self._show_notification(f"Error: {str(e)}", duration=1500, success=False)

    def run(self):
        if self.verbose:
            print("[MenuSystem] Starting UI main loop")
        self.root.mainloop()
        
    def cleanup(self, data=None):
        """Unsubscribe from events when the menu system is closed"""
        if self.verbose:
            print("[MenuSystem] Performing cleanup tasks...")
            
        # Unsubscribe from all events
        EM.unsubscribe(SCENE_CREATION_PROGRESS, self._on_scene_progress)
        EM.unsubscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        EM.unsubscribe(SCENE_CREATION_CANCELED, self._on_scene_canceled)
        EM.unsubscribe('dataset/capture/complete', self._update_victim_indicator)
        EM.unsubscribe('config/updated', self._on_config_updated_gui)
        EM.unsubscribe('simulation/frame', self._on_simulation_frame)
        EM.unsubscribe('trigger_ui_update', self._force_ui_update)
        
        # Cancel any pending "after" tasks
        try:
            if hasattr(self, 'root') and self.root.winfo_exists():
                for task_id in self.root.tk.call('after', 'info'):
                    self.root.after_cancel(task_id)
        except Exception as e:
            print(f"[MenuSystem] Error cleaning up 'after' tasks: {e}")
            
        if self.verbose:
            print("[MenuSystem] Cleanup complete")
