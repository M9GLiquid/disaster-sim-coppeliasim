import tkinter as tk
from tkinter import ttk
import pygame
import json
import os
import time
import threading
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3
from Core.event_manager import EventManager

EM = EventManager.get_instance()

class RCMappingWizard:
    def __init__(self, parent):
        self.parent = parent
        self.joystick = None
        self.mappings = {}
        self.running = False
        self.logger = get_logger()
        
        # Controls to be mapped
        self.controls = [
            {"name": "Throttle", "description": "Controls up/down movement", "axis": None, "invert": False},
            {"name": "Yaw", "description": "Controls rotation", "axis": None, "invert": False},
            {"name": "Pitch", "description": "Controls forward/backward", "axis": None, "invert": False},
            {"name": "Roll", "description": "Controls left/right", "axis": None, "invert": False}
        ]
        self.current_control_index = 0
        
        # Initialize pygame for joystick
        pygame.init()
        pygame.joystick.init()
        
    def start(self):
        """Start the mapping wizard"""
        # Completely reinitialize pygame - this helps with certain joystick issues
        try:
            # Quit pygame if it's already initialized
            pygame.quit()
            
            # Reinitialize pygame and joystick subsystem
            pygame.init()
            pygame.joystick.init()
            
            # Log initialization status
            init_status = pygame.get_init()
            joystick_init_status = pygame.joystick.get_init()
            self.logger.info("RC", f"Pygame initialized: {init_status}, Joystick subsystem: {joystick_init_status}")
            
            if not init_status or not joystick_init_status:
                import tkinter.messagebox as messagebox
                messagebox.showerror("Controller Error", 
                                   "Could not initialize pygame. Please ensure you have pygame installed correctly.")
                return
        except Exception as e:
            self.logger.error("RC", f"Error reinitializing pygame: {str(e)}")
            import tkinter.messagebox as messagebox
            messagebox.showerror("Controller Error", 
                               f"Error initializing controller subsystem: {str(e)}")
            return
            
        # Check for available joysticks
        try:
            joystick_count = pygame.joystick.get_count()
            if joystick_count == 0:
                import tkinter.messagebox as messagebox
                messagebox.showerror("Controller Error", 
                                   "No joystick detected! Please connect your RC controller and try again.")
                self.logger.warning("RC", "No joystick detected for mapping wizard")
                return
                
            self.logger.info("RC", f"Found {joystick_count} joystick(s)")
            
            # Initialize joystick
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            
            # Log joystick details
            joystick_name = self.joystick.get_name()
            joystick_id = self.joystick.get_instance_id()
            self.logger.info("RC", f"Using joystick: {joystick_name} (ID: {joystick_id})")
            
            # Test joystick access by reading first axis
            try:
                # IMPORTANT: Only pump events from the main thread
                pygame.event.pump()
                if self.joystick.get_numaxes() > 0:
                    test_value = self.joystick.get_axis(0)
                    self.logger.debug_at_level(DEBUG_L1, "RC", f"Successfully read from joystick, first axis value: {test_value}")
                else:
                    self.logger.warning("RC", "Joystick has no axes")
                    import tkinter.messagebox as messagebox
                    messagebox.showerror("Controller Error", 
                                       "Your controller doesn't have any axes to map! Please use a different controller.")
                    return
            except Exception as e:
                self.logger.error("RC", f"Error testing joystick access: {str(e)}")
                import tkinter.messagebox as messagebox
                messagebox.showerror("Controller Error", 
                                   f"Could not read data from your controller. Error: {str(e)}\n\nPlease check your controller connection and permissions.")
                return
                
        except Exception as e:
            self.logger.error("RC", f"Error initializing joystick: {str(e)}")
            import tkinter.messagebox as messagebox
            messagebox.showerror("Controller Error", 
                               f"Error initializing controller: {str(e)}")
            return
        
        # Create wizard window
        self.window = tk.Toplevel(self.parent)
        self.window.title("RC Controller Mapping")
        self.window.geometry("650x650")  
        self.window.minsize(650, 650)    # Set minimum size
        self.window.transient(self.parent)
        self.window.grab_set()  # Make modal
        
        # Apply dark theme to the window
        self.window.configure(bg="#2E2E2E")
        
        # Define styles for dark theme
        style = ttk.Style(self.window)
        style.configure("Dark.TFrame", background="#2E2E2E")
        style.configure("Dark.TLabelframe", background="#2E2E2E", foreground="#FFFFFF")
        style.configure("Dark.TLabelframe.Label", background="#2E2E2E", foreground="#FFFFFF")
        style.configure("Dark.TLabel", background="#2E2E2E", foreground="#FFFFFF")
        style.configure("Dark.TButton", background="#3E3E3E", foreground="#FFFFFF")
        style.map("TButton", 
            background=[("active", "#3E3E3E"), ("pressed", "#555555")],
            foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")])
        style.configure("Horizontal.TProgressbar", 
            background="#00AAFF",
            troughcolor="#444444",
            bordercolor="#444444",
            lightcolor="#444444",
            darkcolor="#444444")
            
        # Special green style for the confirm button
        style.configure("Green.TButton", 
            background="#4CAF50",  # Light green
            foreground="#FFFFFF")
        style.map("Green.TButton",
            background=[("active", "#66BB6A"), ("pressed", "#43A047")],  # Lighter on hover, darker on press
            foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")])
        
        # Main instruction label
        self.instruction_label = ttk.Label(
            self.window, 
            text="RC Controller Mapping Wizard",
            font=("Segoe UI", 16, "bold"),
            wraplength=600,
            style="Dark.TLabel"
        )
        self.instruction_label.pack(pady=(20, 10))
        
        # Current step instruction
        self.step_label = ttk.Label(
            self.window, 
            text="Please follow the instructions to map your controller",
            font=("Segoe UI", 12),
            wraplength=600,
            style="Dark.TLabel"
        )
        self.step_label.pack(pady=(0, 20))
        
        # Control info frame
        control_frame = ttk.LabelFrame(self.window, text="Control Details", style="Dark.TLabelframe")
        control_frame.pack(fill="x", padx=20, pady=10)
        
        self.control_name = ttk.Label(
            control_frame, 
            text="Control: -",
            font=("Segoe UI", 12, "bold"),
            style="Dark.TLabel"
        )
        self.control_name.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.control_desc = ttk.Label(
            control_frame, 
            text="Description: -",
            font=("Segoe UI", 10),
            style="Dark.TLabel"
        )
        self.control_desc.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Live values frame
        values_frame = ttk.LabelFrame(self.window, text="Live Input Values", style="Dark.TLabelframe")
        values_frame.pack(fill="x", padx=20, pady=10)
        
        # Grid for axis values
        self.axis_labels = []
        self.axis_values = []
        self.axis_bars = []
        
        for i in range(min(8, self.joystick.get_numaxes())):
            row = i % 4
            col = i // 4 * 2
            
            # Axis label
            axis_label = ttk.Label(
                values_frame,
                text=f"Axis {i}:",
                font=("Courier New", 10, "bold"),
                style="Dark.TLabel",
                foreground="#FFFFFF"  # Explicitly set white text
            )
            axis_label.grid(row=row, column=col, sticky="e", padx=5, pady=5)
            self.axis_labels.append(axis_label)
            
            # Value display
            value_var = tk.StringVar(value="0.00")
            value_label = ttk.Label(
                values_frame,
                textvariable=value_var,
                font=("Courier New", 10, "bold"),
                style="Dark.TLabel",
                foreground="#FFFFFF"  # Explicitly set white text
            )
            value_label.grid(row=row, column=col+1, sticky="w", padx=5, pady=5)
            self.axis_values.append(value_var)
            
            # Progress bar
            bar = ttk.Progressbar(
                values_frame,
                length=100,
                maximum=200,
                value=100  # Center position
            )
            bar.grid(row=row, column=col+2, padx=5, pady=5)
            self.axis_bars.append(bar)
        
        # Detection frame
        detection_frame = ttk.Frame(self.window, style="Dark.TFrame")
        detection_frame.pack(fill="x", padx=20, pady=10)
        
        self.detection_label = ttk.Label(
            detection_frame,
            text="Waiting for stick movement...",
            font=("Segoe UI", 11, "italic"),
            style="Dark.TLabel",
            foreground="#FFFFFF"  # Ensure white text
        )
        self.detection_label.pack(side="left", fill="x", expand=True)
        
        # Add a spacer frame to push buttons to the bottom
        spacer_frame = ttk.Frame(self.window, style="Dark.TFrame")
        spacer_frame.pack(fill="both", expand=True)
        
        # Action buttons at the bottom
        button_frame = ttk.Frame(self.window, style="Dark.TFrame")
        button_frame.pack(fill="x", padx=20, pady=20, side="bottom")
        
        self.skip_btn = ttk.Button(
            button_frame,
            text="Skip This Control",
            command=self._skip_current,
            style="TButton"
        )
        self.skip_btn.pack(side="left", padx=5)
        
        self.invert_btn = ttk.Button(
            button_frame,
            text="Invert Axis",
            command=self._toggle_invert,
            state="disabled",
            style="TButton"
        )
        self.invert_btn.pack(side="left", padx=5)
        
        self.next_btn = ttk.Button(
            button_frame,
            text="Confirm & Next",
            command=self._confirm_and_next,
            state="disabled",
            style="Green.TButton"
        )
        self.next_btn.pack(side="right", padx=5)
        
        self.cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel,
            style="TButton"
        )
        self.cancel_btn.pack(side="right", padx=5)
        
        # Initialize state for main thread handling
        self.running = True
        self.detected_axis = None
        
        # Set up main thread timer for polling
        self._setup_main_thread_polling()
        
        # Start with the first control
        self._show_current_control()
        
    def _setup_main_thread_polling(self):
        """Set up polling for joystick events in the main thread using tkinter's after method"""
        self.axis_values_cache = {}
        self.max_movement = [0.0] * self.joystick.get_numaxes()
        self.base_values = [0.0] * self.joystick.get_numaxes()
        
        # Get initial base values for each axis
        try:
            # Pump events in the main thread
            pygame.event.pump()
            for i in range(self.joystick.get_numaxes()):
                try:
                    self.base_values[i] = self.joystick.get_axis(i)
                except Exception as e:
                    self.logger.error("RC", f"Error getting base value for axis {i}: {str(e)}")
        except Exception as e:
            self.logger.error("RC", f"Error getting base values: {str(e)}")
            # Show error message but continue
            self.detection_label.config(
                text=f"Warning: {str(e)}",
                foreground="orange"
            )
        
        # Schedule the first polling
        self._poll_joystick()
    
    def _poll_joystick(self):
        """Poll joystick data in the main thread"""
        if not self.running:
            return
        
        try:
            # Pump events in the main thread
            pygame.event.pump()
            
            # Read all axis values
            num_axes = self.joystick.get_numaxes()
            for i in range(num_axes):
                try:
                    # Get current value
                    value = self.joystick.get_axis(i)
                    self.axis_values_cache[i] = value
                    
                    # Update UI value display
                    if i < len(self.axis_values):
                        self.axis_values[i].set(f"{value:.2f}")
                    
                    # Update UI progress bar
                    if i < len(self.axis_bars):
                        bar_value = int((value + 1.0) * 100)  # Convert -1..1 to 0..200
                        self.axis_bars[i].config(value=bar_value)
                    
                    # Calculate movement
                    movement = abs(value - self.base_values[i])
                    self.max_movement[i] = max(self.max_movement[i], movement)
                    
                    # Check for significant movement
                    if movement > 0.5 and self.detected_axis is None:
                        self.detected_axis = i
                        self.detection_label.config(
                            text=f"Detected movement on Axis {i}!"
                        )
                        self.next_btn.config(state="normal")
                        self.invert_btn.config(state="normal")
                    
                    # Highlight detected axis
                    if i < len(self.axis_labels):
                        if i == self.detected_axis:
                            self.axis_labels[i].config(foreground="#00FF00")  # Bright green for detected axis
                        else:
                            self.axis_labels[i].config(foreground="#FFFFFF")  # White for other axes
                except Exception as e:
                    self.logger.error("RC", f"Error reading axis {i}: {str(e)}")
                    
        except Exception as e:
            self.logger.error("RC", f"Error polling joystick: {str(e)}")
            # Only show error message if it's a new error
            if not hasattr(self, 'last_error') or self.last_error != str(e):
                self.last_error = str(e)
                self.detection_label.config(
                    text=f"Error: {str(e)}",
                    foreground="red"
                )
        
        # Schedule next polling
        if self.running and hasattr(self, 'window') and self.window.winfo_exists():
            self.window.after(100, self._poll_joystick)
        
    def _show_current_control(self):
        """Update UI for the current control being mapped"""
        if self.current_control_index >= len(self.controls):
            self._finish_mapping()
            return
            
        control = self.controls[self.current_control_index]
        
        # Update labels
        self.control_name.config(text=f"Control: {control['name']}")
        self.control_desc.config(text=f"Description: {control['description']}")
        
        # Update main instruction
        self.step_label.config(
            text=f"Step {self.current_control_index+1}/{len(self.controls)}: Please move the "
                 f"{control['name']} stick or wheel fully in both directions"
        )
        
        # Reset detection
        self.detected_axis = None
        self.detection_label.config(text="Waiting for stick movement...")
        self.next_btn.config(state="disabled")
        self.invert_btn.config(state="disabled")
        self.invert_axis = False
        
    def _confirm_and_next(self):
        """Confirm the current mapping and move to next control"""
        if self.detected_axis is not None:
            # Save mapping
            self.controls[self.current_control_index]["axis"] = self.detected_axis
            invert = getattr(self, "invert_axis", False)
            self.controls[self.current_control_index]["invert"] = invert
            
            # Move to next control
            self.current_control_index += 1
            self._show_current_control()
    
    def _skip_current(self):
        """Skip the current control without mapping"""
        self.current_control_index += 1
        self._show_current_control()
    
    def _toggle_invert(self):
        """Toggle axis inversion for current control"""
        self.invert_axis = not getattr(self, "invert_axis", False)
        if self.invert_axis:
            self.invert_btn.config(text="Invert Axis (ON)")
        else:
            self.invert_btn.config(text="Invert Axis (OFF)")
    
    def _cancel(self):
        """Cancel the mapping process"""
        self.running = False
        
        # Clean up pygame resources
        try:
            if self.joystick:
                self.joystick.quit()
        except Exception as e:
            self.logger.warning("RC", f"Error quitting joystick: {e}")
            
        self.window.destroy()
    
    def _finish_mapping(self):
        """Finish the mapping process and save the configuration"""
        # Create mappings dictionary
        final_mappings = {}
        for control in self.controls:
            if control["axis"] is not None:
                final_mappings[control["name"].lower()] = {
                    "axis": control["axis"],
                    "invert": control["invert"]
                }
        
        # Save to file
        config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Config")
        os.makedirs(config_dir, exist_ok=True)
        
        config_path = os.path.join(config_dir, "rc_mapping.json")
        with open(config_path, "w") as f:
            json.dump(final_mappings, f, indent=4)
        
        self.logger.info("RCMappingWizard", f"RC mappings saved to {config_path}")
        
        # Try to find config in the application and apply mappings
        try:
            # Store mappings in a global attribute to be retrieved by the parent
            self.final_mappings = final_mappings
            
            # Publish an event to notify about new mappings
            # This will be handled by any components listening for configuration updates
            EM.publish('rc/mappings_updated', final_mappings)
            self.logger.info("RCMappingWizard", "Published mappings update event")
        except Exception as e:
            self.logger.error("RCMappingWizard", f"Error publishing mapping event: {e}")
        
        # Update UI - Show success message at top
        self.step_label.config(text="Mapping completed successfully!")
        self.instruction_label.config(text="RC Controller Mapping Complete")
        
        # Clear the live values frame and detection frame
        for widget in self.detection_label.master.winfo_children():
            widget.destroy()
            
        # Display mappings in the detection frame area
        mappings_frame = self.detection_label.master
        
        # Display final mappings in formatted style
        mapping_title = ttk.Label(
            mappings_frame,
            text="Saved Mappings:",
            font=("Segoe UI", 12, "bold"),
            style="Dark.TLabel"
        )
        mapping_title.pack(anchor="w", pady=(0, 5))
        
        # Create a label for each mapped control
        for control in self.controls:
            if control["axis"] is not None:
                invert_text = " (Inverted)" if control["invert"] else ""
                mapping_text = f"• {control['name']}: Axis {control['axis']}{invert_text}"
                
                mapping_label = ttk.Label(
                    mappings_frame,
                    text=mapping_text,
                    font=("Segoe UI", 11),
                    style="Dark.TLabel"
                )
                mapping_label.pack(anchor="w", padx=15, pady=2)
            else:
                mapping_label = ttk.Label(
                    mappings_frame,
                    text=f"• {control['name']}: Not mapped",
                    font=("Segoe UI", 11),
                    style="Dark.TLabel"
                )
                mapping_label.pack(anchor="w", padx=15, pady=2)
        
        # Change buttons (which are already at the bottom)
        self.skip_btn.config(state="disabled")
        self.invert_btn.config(state="disabled")
        self.next_btn.config(text="Close", command=self._close_and_cleanup, style="Green.TButton")
        
        # Stop threads
        self.running = False
        
    def _close_and_cleanup(self):
        """Close the window and clean up resources"""
        # Clean up pygame resources
        try:
            if self.joystick:
                self.joystick.quit()
        except Exception as e:
            self.logger.warning("RC", f"Error quitting joystick: {e}")
            
        self.window.destroy()

    def _show_error_message(self, message):
        """Show an error message to the user"""
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Controller Error", 
                               f"There was an error with your controller:\n\n{message}\n\nPlease ensure your controller is properly connected and try again.")
            self.window.destroy()
        except Exception as e:
            self.logger.error("RC", f"Error showing error message: {e}")
            # As a fallback, try to update the detection label
            try:
                self.detection_label.config(
                    text=f"ERROR: {message}",
                    foreground="red"
                )
                self.skip_btn.config(text="Close", command=self.window.destroy)
                self.next_btn.config(state="disabled")
                self.invert_btn.config(state="disabled")
            except:
                pass 