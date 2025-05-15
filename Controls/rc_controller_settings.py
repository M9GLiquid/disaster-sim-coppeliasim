import tkinter as tk
from tkinter import ttk
import pygame
import json
import os
import threading
from Controls.rc_mapping_wizard import RCMappingWizard
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3
from Core.event_manager import EventManager

EM = EventManager.get_instance()

class RCControllerSettings:
    def __init__(self, parent_frame, config):
        """
        Creates a complete RC controller settings panel
        
        Parameters:
        - parent_frame: Parent tkinter frame to add this panel to
        - config: Reference to the application config dictionary
        """
        self.parent = parent_frame
        self.config = config
        self.mappings = {}
        self.settings_frame = None
        self.logger = get_logger()
        
        # Load existing mappings/settings
        self.load_settings()
        
        # Build the UI
        self.build_settings_panel()
        
        # Subscribe to config updates
        EM.subscribe('config/updated', self._on_config_updated)
        
        # Subscribe to RC mapping updates from the mapping wizard
        EM.subscribe('rc/mappings_updated', self._on_mappings_updated)
    
    def load_settings(self):
        """Load RC controller settings from file"""
        try:
            # Load axis mappings
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Config")
            mapping_path = os.path.join(config_dir, "rc_mapping.json")
            if os.path.exists(mapping_path):
                with open(mapping_path, "r") as f:
                    self.mappings = json.load(f)
                self.logger.debug_at_level(DEBUG_L1, "RCSettings", f"Loaded RC mappings from {mapping_path}")
                
                # Apply loaded mappings to config so they take effect immediately
                self.config["rc_mappings"] = self.mappings
                EM.publish('config/updated', 'rc_mappings')
            
            # Load or initialize sensitivity/deadzone settings
            if "rc_sensitivity" not in self.config:
                self.config["rc_sensitivity"] = 1.0
            if "rc_deadzone" not in self.config:
                self.config["rc_deadzone"] = 0.1
            if "rc_yaw_sensitivity" not in self.config:
                self.config["rc_yaw_sensitivity"] = 0.15  # Default to 15%
                
            self.logger.debug_at_level(DEBUG_L1, "RCSettings", f"RC sensitivity: {self.config['rc_sensitivity']}, deadzone: {self.config['rc_deadzone']}, yaw sensitivity: {self.config['rc_yaw_sensitivity']}")
                
        except Exception as e:
            self.logger.error("RCSettings", f"Error loading RC settings: {e}")
    
    def build_settings_panel(self):
        """Build the RC controller settings panel"""
        self.settings_frame = ttk.LabelFrame(
            self.parent, 
            text="RC Controller Settings",
            padding=15,
            labelanchor="n"
        )
        self.settings_frame.pack(fill="x", pady=10, padx=5)
        
        # Main instruction
        ttk.Label(
            self.settings_frame,
            text="Configure your RC controller settings below:",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Sensitivity adjustment
        sens_frame = ttk.Frame(self.settings_frame)
        sens_frame.pack(fill="x", pady=5)
        
        ttk.Label(
            sens_frame,
            text="Sensitivity:",
            width=20
        ).pack(side="left")
        
        # Sensitivity slider
        self.sensitivity_var = tk.DoubleVar(value=self.config.get("rc_sensitivity", 1.0))
        sensitivity_scale = ttk.Scale(
            sens_frame,
            from_=1.0,
            to=50.0,
            orient="horizontal",
            variable=self.sensitivity_var,
            command=self._update_sensitivity_label
        )
        sensitivity_scale.pack(side="left", fill="x", expand=True, padx=5)
        
        self.sensitivity_label = ttk.Label(
            sens_frame,
            text=f"{self.sensitivity_var.get():.1f}",
            width=6
        )
        self.sensitivity_label.pack(side="left", padx=5)
        
        # Add small description of what sensitivity affects
        ttk.Label(
            sens_frame,
            text="(Higher = more responsive)",
            font=("Segoe UI", 8, "italic")
        ).pack(side="left", padx=5)
        
        # Yaw Sensitivity adjustment
        yaw_sens_frame = ttk.Frame(self.settings_frame)
        yaw_sens_frame.pack(fill="x", pady=5)
        
        ttk.Label(
            yaw_sens_frame,
            text="Yaw Sensitivity:",
            width=20
        ).pack(side="left")
        
        # Yaw Sensitivity slider - change from 5% to 50%
        self.yaw_sensitivity_var = tk.DoubleVar(value=self.config.get("rc_yaw_sensitivity", 0.15))
        yaw_sensitivity_scale = ttk.Scale(
            yaw_sens_frame,
            from_=0.05,  # 5%
            to=0.5,      # 50%
            orient="horizontal",
            variable=self.yaw_sensitivity_var,
            command=self._update_yaw_sensitivity_label
        )
        yaw_sensitivity_scale.pack(side="left", fill="x", expand=True, padx=5)
        
        self.yaw_sensitivity_label = ttk.Label(
            yaw_sens_frame,
            text=f"{int(self.yaw_sensitivity_var.get() * 100)}%",
            width=6
        )
        self.yaw_sensitivity_label.pack(side="left", padx=5)
        
        # Add small description of what yaw sensitivity affects
        ttk.Label(
            yaw_sens_frame,
            text="(Higher = faster rotation)",
            font=("Segoe UI", 8, "italic")
        ).pack(side="left", padx=5)
        
        # Deadzone adjustment
        dead_frame = ttk.Frame(self.settings_frame)
        dead_frame.pack(fill="x", pady=5)
        
        ttk.Label(
            dead_frame,
            text="Deadzone:",
            width=20
        ).pack(side="left")
        
        # Deadzone slider
        self.deadzone_var = tk.DoubleVar(value=self.config.get("rc_deadzone", 0.1))
        deadzone_scale = ttk.Scale(
            dead_frame,
            from_=0.1,
            to=2.0,
            orient="horizontal",
            variable=self.deadzone_var,
            command=self._update_deadzone_label
        )
        deadzone_scale.pack(side="left", fill="x", expand=True, padx=5)
        
        self.deadzone_label = ttk.Label(
            dead_frame,
            text=f"{self.deadzone_var.get():.2f}",
            width=5
        )
        self.deadzone_label.pack(side="left", padx=5)
        
        # Add small description of what deadzone affects
        ttk.Label(
            dead_frame,
            text="(Higher = ignores larger movements)",
            font=("Segoe UI", 8, "italic")
        ).pack(side="left", padx=5)
        
        # Current mappings display
        mappings_frame = ttk.LabelFrame(
            self.settings_frame,
            text="Current Axis Mappings",
            labelanchor="n"
        )
        mappings_frame.pack(fill="x", pady=10)
        
        # Create mapping labels
        self.mapping_labels = {}
        control_names = ["Throttle", "Yaw", "Pitch", "Roll"]
        
        for i, name in enumerate(control_names):
            name_lower = name.lower()
            mapping = self.mappings.get(name_lower, {})
            axis = mapping.get("axis", "Not mapped")
            inverted = " (Inverted)" if mapping.get("invert", False) else ""
            
            control_frame = ttk.Frame(mappings_frame)
            control_frame.pack(fill="x", pady=2)
            
            ttk.Label(
                control_frame,
                text=f"{name}:",
                width=15
            ).pack(side="left")
            
            mapping_text = f"Axis {axis}{inverted}" if axis != "Not mapped" else "Not mapped"
            label = ttk.Label(
                control_frame,
                text=mapping_text
            )
            label.pack(side="left", fill="x", expand=True)
            self.mapping_labels[name_lower] = label
        
        # Action buttons
        button_frame = ttk.Frame(self.settings_frame)
        button_frame.pack(fill="x", pady=10)
        
        # Map Controller button
        map_btn = ttk.Button(
            button_frame,
            text="Configure Axis Mapping",
            command=self.open_mapping_wizard
        )
        map_btn.pack(side="left", padx=5)
        
        # Test Controller button
        test_btn = ttk.Button(
            button_frame,
            text="Test Controller",
            command=self.open_test_window
        )
        test_btn.pack(side="left", padx=5)
        
        # Apply Settings button
        apply_btn = ttk.Button(
            button_frame,
            text="Apply Settings",
            command=self._apply_settings,
            style="Apply.TButton"
        )
        apply_btn.pack(side="right", padx=5)
    
    def _update_sensitivity_label(self, value):
        """Update the sensitivity value label"""
        try:
            val = float(value)
            # Use integer format for values over 10, round to one decimal for smaller values
            if val >= 10:
                self.sensitivity_label.config(text=f"{round(val)}")
            else:
                self.sensitivity_label.config(text=f"{round(val, 1)}")
        except:
            pass
    
    def _update_yaw_sensitivity_label(self, value):
        """Update the yaw sensitivity value label"""
        try:
            val = float(value)
            # Display as percentage
            self.yaw_sensitivity_label.config(text=f"{int(val * 100)}%")
        except:
            pass
    
    def _update_deadzone_label(self, value):
        """Update the deadzone value label"""
        try:
            val = float(value)
            self.deadzone_label.config(text=f"{round(val, 2):.2f}")
        except:
            pass
    
    def _apply_settings(self):
        """Save the current settings to config"""
        # Update config with current UI values - round sensitivity to 1 decimal place
        self.config["rc_sensitivity"] = round(self.sensitivity_var.get(), 1)
        self.config["rc_deadzone"] = round(self.deadzone_var.get(), 2)
        self.config["rc_yaw_sensitivity"] = round(self.yaw_sensitivity_var.get(), 2)
        # Also apply current mappings
        self.config["rc_mappings"] = self.mappings
        
        # Save to config file
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Config")
            os.makedirs(config_dir, exist_ok=True)
            
            # Save sensitivity and deadzone to main config
            with open(os.path.join(config_dir, "rc_settings.json"), "w") as f:
                json.dump({
                    "sensitivity": self.config["rc_sensitivity"],
                    "deadzone": self.config["rc_deadzone"],
                    "yaw_sensitivity": self.config["rc_yaw_sensitivity"]
                }, f, indent=4)
            
            # Publish config update event for all relevant settings
            EM.publish('config/updated', 'rc_sensitivity')
            EM.publish('config/updated', 'rc_deadzone')
            EM.publish('config/updated', 'rc_yaw_sensitivity')
            EM.publish('config/updated', 'rc_mappings')
                
            # Show confirmation message
            sensitivity_val = round(self.config["rc_sensitivity"], 1)
            deadzone_val = round(self.config["rc_deadzone"], 2)
            yaw_sensitivity_val = int(round(self.config["rc_yaw_sensitivity"], 2) * 100)
            self._show_message(f"Settings applied - Sensitivity: {sensitivity_val}, Yaw: {yaw_sensitivity_val}%, Deadzone: {deadzone_val}")
            self.logger.info("RCSettings", f"Saved and applied RC settings: sensitivity={self.config['rc_sensitivity']}, yaw_sensitivity={self.config['rc_yaw_sensitivity']}, deadzone={self.config['rc_deadzone']}, mappings={self.mappings}")
        except Exception as e:
            self._show_message(f"Error saving settings: {e}", error=True)
            self.logger.error("RCSettings", f"Error saving RC settings: {e}")
    
    def _on_config_updated(self, key):
        """Handle config update events"""
        if key == 'rc_sensitivity':
            self.sensitivity_var.set(self.config.get('rc_sensitivity', 1.0))
            self._update_sensitivity_label(self.config.get('rc_sensitivity', 1.0))
        elif key == 'rc_deadzone':
            self.deadzone_var.set(self.config.get('rc_deadzone', 0.1))
            self._update_deadzone_label(self.config.get('rc_deadzone', 0.1))
        elif key == 'rc_yaw_sensitivity':
            self.yaw_sensitivity_var.set(self.config.get('rc_yaw_sensitivity', 0.15))
            self._update_yaw_sensitivity_label(self.config.get('rc_yaw_sensitivity', 0.15))
    
    def _show_message(self, message, error=False):
        """Show a temporary message"""
        # Create the message label if it doesn't exist
        if not hasattr(self, "message_label"):
            self.message_label = ttk.Label(
                self.settings_frame,
                text="",
                foreground="green",
                font=("Segoe UI", 10, "bold"),
                padding=(5, 3),
                relief="groove"
            )
        
        # Configure with message and show it
        color = "red" if error else "green"
        self.message_label.config(text=message, foreground=color)
        self.message_label.pack(pady=5)
        
        # Schedule hiding after 5 seconds
        self.parent.after(5000, self._hide_message)
    
    def _hide_message(self):
        """Hide the message label completely"""
        if hasattr(self, "message_label"):
            self.message_label.pack_forget()  # Remove from layout instead of just clearing text
    
    def open_mapping_wizard(self):
        """Open the axis mapping wizard"""
        try:
            # Initialize pygame for joystick
            if not pygame.get_init():
                pygame.init()
                
            if not pygame.joystick.get_init():
                pygame.joystick.init()
                
            # Check if any joysticks are available
            joystick_count = pygame.joystick.get_count()
            if joystick_count == 0:
                self._show_message("No joystick detected! Please connect your RC controller.", error=True)
                self.logger.warning("RCSettings", "No joystick detected for mapping wizard")
                return
            
            # Basic test to see if joystick is accessible
            try:
                joystick = pygame.joystick.Joystick(0)
                joystick.init()
                
                # Test reading an axis
                pygame.event.pump()
                _ = joystick.get_axis(0)  # Just to test if we can read it
                
                # Clean up test joystick
                joystick.quit()
            except Exception as e:
                self._show_message(f"Could not access joystick: {e}", error=True)
                self.logger.error("RCSettings", f"Error accessing joystick: {e}")
                return
            
            # Create wizard window
            wizard = RCMappingWizard(self.parent.winfo_toplevel())
            wizard.start()
            
            # Set callback to update UI when wizard is done
            def check_mapping_done():
                if not hasattr(wizard, 'window') or not wizard.window.winfo_exists():
                    # Window closed, reload mappings
                    self.load_settings()
                    self._update_mapping_display()
                    
                    # Also check if the wizard has stored final mappings
                    if hasattr(wizard, 'final_mappings') and wizard.final_mappings:
                        self.logger.debug_at_level(DEBUG_L1, "RCSettings", "Found mappings directly from wizard object")
                        # Apply the mappings directly
                        self.mappings = wizard.final_mappings
                        self.config["rc_mappings"] = dict(wizard.final_mappings)
                        self._update_mapping_display()
                        EM.publish('config/updated', 'rc_mappings')
                    return
                # Check again after a short delay
                self.parent.after(500, check_mapping_done)
            
            # Start checking
            self.parent.after(1000, check_mapping_done)
        except Exception as e:
            self._show_message(f"Error starting mapping wizard: {e}", error=True)
            self.logger.error("RCSettings", f"Error starting mapping wizard: {e}")
            
            # Try to clean up pygame
            try:
                pygame.joystick.quit()
                pygame.quit()
            except:
                pass
    
    def _update_mapping_display(self):
        """Update the mapping labels with current mappings"""
        control_names = ["throttle", "yaw", "pitch", "roll"]
        
        for name in control_names:
            if name in self.mapping_labels:
                mapping = self.mappings.get(name, {})
                axis = mapping.get("axis", "Not mapped")
                inverted = " (Inverted)" if mapping.get("invert", False) else ""
                
                mapping_text = f"Axis {axis}{inverted}" if axis != "Not mapped" else "Not mapped"
                self.mapping_labels[name].config(text=mapping_text)
        
        # Apply the new mapping to the current configuration
        self._apply_mapping_to_config()
        self.logger.debug_at_level(DEBUG_L1, "RCSettings", "Updated mapping display and applied to current controls")
    
    def _apply_mapping_to_config(self):
        """Apply the current mapping to the active configuration so it takes effect immediately"""
        try:
            # Save the mappings to the configuration
            self.config["rc_mappings"] = self.mappings
            
            # Make sure we create a new object reference to trigger updates properly
            # This ensures the controller process gets the update
            self.config["rc_mappings"] = dict(self.mappings)
            
            # Publish an event to notify other components
            EM.publish('config/updated', 'rc_mappings')
            
            # Show a brief success message
            self._show_message("Mappings applied to controller!")
            
            # Log the applied mappings
            self.logger.info("RCSettings", f"Applied RC mappings: {self.mappings}")
        except Exception as e:
            self.logger.error("RCSettings", f"Error applying mappings: {str(e)}")
            self._show_message(f"Error applying mappings: {str(e)}", error=True)
    
    def open_test_window(self):
        """Open a window to test RC controller inputs"""
        try:
            # Initialize pygame for joystick
            if not pygame.get_init():
                pygame.init()
                
            if not pygame.joystick.get_init():
                pygame.joystick.init()
                
            # Check for joysticks
            joystick_count = pygame.joystick.get_count()
            if joystick_count == 0:
                self._show_message("No joystick detected! Please connect your RC controller.", error=True)
                self.logger.warning("RCSettings", "No joystick detected for test window")
                return
            
            # Basic test to see if joystick is accessible
            try:
                # Initialize joystick
                joystick = pygame.joystick.Joystick(0)
                joystick.init()
                
                # Test reading an axis
                pygame.event.pump()
                _ = joystick.get_axis(0)  # Just to test if we can read it
                
                # Get some info
                joystick_name = joystick.get_name()
                num_axes = joystick.get_numaxes()
                num_buttons = joystick.get_numbuttons()
            except Exception as e:
                self._show_message(f"Could not access joystick: {e}", error=True)
                self.logger.error("RCSettings", f"Error accessing joystick: {e}")
                return
            
            # Create test window
            test_window = tk.Toplevel(self.parent)
            test_window.title("RC Controller Test")
            test_window.geometry("500x530")  # Increased height
            test_window.minsize(500, 530)    # Set minimum size
            test_window.transient(self.parent.winfo_toplevel())
            
            # Apply dark theme to the window
            test_window.configure(bg="#2E2E2E")
            
            # Define styles for dark theme
            style = ttk.Style(test_window)
            style.configure("Dark.TFrame", background="#2E2E2E")
            style.configure("Dark.TLabelframe", background="#2E2E2E", foreground="#FFFFFF")
            style.configure("Dark.TLabelframe.Label", background="#2E2E2E", foreground="#FFFFFF")
            style.configure("Dark.TLabel", background="#2E2E2E", foreground="#FFFFFF")
            style.configure("Dark.TButton", background="#3E3E3E", foreground="#FFFFFF")
            
            # Add joystick info
            info_frame = ttk.Frame(test_window, padding=10, style="Dark.TFrame")
            info_frame.pack(fill="x")
            
            ttk.Label(
                info_frame,
                text=f"Controller: {joystick_name}",
                font=("Segoe UI", 12, "bold"),
                style="Dark.TLabel"
            ).pack(anchor="w")
            
            ttk.Label(
                info_frame,
                text=f"Axes: {num_axes}, Buttons: {num_buttons}",
                font=("Segoe UI", 10),
                style="Dark.TLabel"
            ).pack(anchor="w")
            
            # Load mappings for display
            ctrl_frame = ttk.LabelFrame(test_window, text="Mapped Controls", padding=10, style="Dark.TLabelframe")
            ctrl_frame.pack(fill="x", pady=10, padx=10)
            
            # Control value displays with progress bars
            controls = {
                "throttle": {"name": "Throttle", "value": 0.0},
                "yaw": {"name": "Yaw", "value": 0.0},
                "pitch": {"name": "Pitch", "value": 0.0},
                "roll": {"name": "Roll", "value": 0.0}
            }
            
            # Create UI elements for each control
            for ctrl_id, ctrl in controls.items():
                frame = ttk.Frame(ctrl_frame, style="Dark.TFrame")
                frame.pack(fill="x", pady=5)
                
                # Label
                ttk.Label(
                    frame,
                    text=f"{ctrl['name']}:",
                    width=15,
                    style="Dark.TLabel"
                ).pack(side="left")
                
                # Value label
                ctrl["value_var"] = tk.StringVar(value="0.00")
                value_label = ttk.Label(
                    frame,
                    textvariable=ctrl["value_var"],
                    width=8,
                    style="Dark.TLabel"
                )
                value_label.pack(side="left", padx=5)
                
                # Progress bar
                ctrl["bar"] = ttk.Progressbar(
                    frame,
                    length=200,
                    maximum=200,
                    value=100  # Center position
                )
                ctrl["bar"].pack(side="left", fill="x", expand=True, padx=5)
            
            # Raw axis values display
            raw_frame = ttk.LabelFrame(test_window, text="Raw Axis Values", padding=10, style="Dark.TLabelframe")
            raw_frame.pack(fill="x", pady=10, padx=10)
            
            # Create displays for raw axis values
            axis_values = []
            for i in range(min(6, joystick.get_numaxes())):  # Show up to 6 axes
                frame = ttk.Frame(raw_frame, style="Dark.TFrame")
                frame.pack(fill="x", pady=2)
                
                ttk.Label(
                    frame,
                    text=f"Axis {i}:",
                    width=15,
                    style="Dark.TLabel"
                ).pack(side="left")
                
                # Value display
                value_var = tk.StringVar(value="0.00")
                ttk.Label(
                    frame,
                    textvariable=value_var,
                    width=8,
                    style="Dark.TLabel"
                ).pack(side="left", padx=5)
                
                # Progress bar
                bar = ttk.Progressbar(
                    frame,
                    length=200,
                    maximum=200,
                    value=100  # Center position
                )
                bar.pack(side="left", fill="x", expand=True, padx=5)
                
                axis_values.append({"var": value_var, "bar": bar})
            
            # Close button
            close_btn = ttk.Button(
                test_window,
                text="Close",
                command=test_window.destroy,
                padding=10
            )
            close_btn.pack(pady=20)
            
            # Configure button style
            style.map("TButton", 
                background=[("active", "#3E3E3E"), ("pressed", "#555555")],
                foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")])
            
            # Try to make progressbars fit the theme
            style.configure("Horizontal.TProgressbar", 
                background="#00AAFF",
                troughcolor="#444444",
                bordercolor="#444444",
                lightcolor="#444444",
                darkcolor="#444444")
            
            # Running flag for update thread
            running = True
            
            # Function to update values
            def update_values():
                # Check if window still exists
                if not test_window.winfo_exists():
                    nonlocal running
                    running = False
                    return  # Window closed
                    
                try:
                    # Process joystick events in the main thread
                    pygame.event.pump()
                    
                    # Get sensitivity and deadzone
                    sensitivity = self.config.get("rc_sensitivity", 1.0)
                    deadzone = self.config.get("rc_deadzone", 0.1)
                    
                    # Update raw axis values
                    for i, axis_info in enumerate(axis_values):
                        if i < num_axes:
                            try:
                                value = joystick.get_axis(i)
                                axis_info["var"].set(f"{value:.2f}")
                                bar_value = int((value + 1.0) * 100)  # Convert -1..1 to 0..200
                                axis_info["bar"].config(value=bar_value)
                            except Exception as e:
                                self.logger.error("RCSettings", f"Error reading axis {i}: {str(e)}")
                                axis_info["var"].set("ERROR")
                    
                    # Update mapped controls
                    for ctrl_id, ctrl in controls.items():
                        mapping = self.mappings.get(ctrl_id, {})
                        axis = mapping.get("axis")
                        
                        if axis is not None and axis < num_axes:
                            try:
                                raw_value = joystick.get_axis(axis)
                                
                                # Apply inversion if needed
                                if mapping.get("invert", False):
                                    raw_value = -raw_value
                                    
                                # Apply deadzone
                                if abs(raw_value) < deadzone:
                                    value = 0.0
                                else:
                                    # Scale the value to account for deadzone
                                    sign = 1.0 if raw_value > 0 else -1.0
                                    value = sign * (abs(raw_value) - deadzone) / (1.0 - deadzone)
                                    
                                # Apply sensitivity
                                value = value * sensitivity
                                
                                # Clamp to -1 to 1
                                value = max(-1.0, min(1.0, value))
                                
                                # Update UI
                                ctrl["value_var"].set(f"{value:.2f}")
                                bar_value = int((value + 1.0) * 100)  # Convert -1..1 to 0..200
                                ctrl["bar"].config(value=bar_value)
                            except Exception as e:
                                self.logger.error("RCSettings", f"Error processing mapped control {ctrl_id}: {str(e)}")
                                ctrl["value_var"].set("ERROR")
                        else:
                            ctrl["value_var"].set("N/A")
                except Exception as e:
                    self.logger.error("RCSettings", f"Error updating RC test display: {str(e)}")
                
                # Schedule next update if still running
                if running and test_window.winfo_exists():
                    test_window.after(50, update_values)
            
            # Start updating with tkinter's after method (main thread)
            test_window.after(50, update_values)
            
            # Handle window close
            def on_closing():
                nonlocal running
                running = False
                
                # Clean up pygame resources
                try:
                    joystick.quit()
                    pygame.quit()
                except Exception as e:
                    self.logger.warning("RCSettings", f"Error quitting joystick: {e}")
                    
                test_window.destroy()
                
            test_window.protocol("WM_DELETE_WINDOW", on_closing)
            
            self.logger.info("RCSettings", "Opened RC controller test window")
        except Exception as e:
            self._show_message(f"Error starting test window: {e}", error=True)
            self.logger.error("RCSettings", f"Error starting test window: {e}")
    
    def _on_mappings_updated(self, new_mappings):
        """Handle mapping updates from the mapping wizard"""
        self.logger.info("RCSettings", f"Received new mappings from wizard: {new_mappings}")
        
        # Update our local mappings
        self.mappings = new_mappings
        
        # Apply to the configuration
        self.config["rc_mappings"] = dict(new_mappings)
        
        # Update the UI display
        self._update_mapping_display()
        
        # Publish config update to notify the main process
        EM.publish('config/updated', 'rc_mappings')
    
    def destroy(self):
        """Clean up resources when the panel is destroyed"""
        # Unsubscribe from events
        EM.unsubscribe('config/updated', self._on_config_updated)
        EM.unsubscribe('rc/mappings_updated', self._on_mappings_updated)
        
        # Remove UI elements
        if self.settings_frame:
            self.settings_frame.destroy()
            self.settings_frame = None 