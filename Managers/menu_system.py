# Managers/menu_system.py

import tkinter as tk
from tkinter import ttk, filedialog
from Utils.config_utils import FIELDS
from Utils.scene_utils import restart_disaster_area
from Managers.scene_manager import (
    create_scene, clear_scene, cancel_scene_creation,
    SCENE_START_CREATION, SCENE_CREATION_PROGRESS, 
    SCENE_CREATION_COMPLETED, SCENE_CREATION_CANCELED,
    SCENE_CLEARED
)
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3, LOG_LEVEL_DEBUG, LOG_LEVEL_INFO, LOG_LEVEL_WARNING, LOG_LEVEL_ERROR, LOG_LEVEL_CRITICAL
from Controls.rc_controller_settings import RCControllerSettings

from Managers.Connections.sim_connection import SimConnection
SC = SimConnection.get_instance()

from Core.event_manager import EventManager
EM = EventManager.get_instance()

import math
import json
import time
import psutil
import platform
import threading
from datetime import datetime
import os


class MenuSystem:
    def __init__(self, config: dict, sim_command_queue):
        self.sim_queue = sim_command_queue
        self.sim = SC.sim
        self.config = config
        # Map to hold config UI variables and widgets
        self._config_vars = {}
        self._config_widgets = {}

        # Flag to track UI state
        self._ui_active = True
        
        # Get logger instance
        self.logger = get_logger()
        
        # Track current selected tab
        self._current_tab = "Scene"  # Default tab

        # Subscribe to config updates to sync UI
        EM.subscribe('config/updated', self._on_config_updated_gui)

        self.progress_var = None  # For progress bar

        # Performance tracking
        self._last_ui_update = 0
        self._last_fps_update = 0
        self._frame_times = []
        self._sim_frame_times = []
        self._start_time = time.time()
        self._monitoring_active = False
        self._monitoring_after_id = None
        
        # Set default monitoring state to disabled
        self.config["enable_performance_monitoring"] = False
        
        # Ensure default values for tree spawn interval and bird speed
        if "tree_spawn_interval" not in self.config:
            self.config["tree_spawn_interval"] = 30.0
        if "bird_speed" not in self.config:
            self.config["bird_speed"] = 1.0
            
        # Set of currently pressed keys for UI control
        self._ui_pressed_keys = set()

        # Build and style main window
        self.root = tk.Tk()
        self.root.title("Disaster Simulation with Drone Navigation v1.3.1")
        self.root.geometry("700x900")  # Increased width to ensure all tabs are visible
        self.root.configure(bg="#1a1a1a")  # Dark background
        
        # Initialize Tkinter variables after root window is created
        self.control_status_var = tk.StringVar(value="UI Control: Initializing (5x Speed)...")
        
        # Set window icon
        try:
            # Get the absolute path to the assets directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            assets_dir = os.path.join(os.path.dirname(current_dir), 'assets')
            
            # Try to load the icon file
            icon_path = os.path.join(assets_dir, 'icon.ico')
            png_path = os.path.join(assets_dir, 'icon.png')
            
            self.logger.debug_at_level(DEBUG_L2, "MenuSystem", f"Looking for icons in: {assets_dir}")
            self.logger.debug_at_level(DEBUG_L2, "MenuSystem", f"ICO path: {icon_path}")
            self.logger.debug_at_level(DEBUG_L2, "MenuSystem", f"PNG path: {png_path}")
            
            if platform.system() == 'Darwin':  # macOS
                if os.path.exists(png_path):
                    self.logger.debug_at_level(DEBUG_L1, "MenuSystem", "Found PNG file, setting icon for macOS")
                    # For macOS, we need to use iconphoto with a PhotoImage
                    icon_image = tk.PhotoImage(file=png_path)
                    self.root.iconphoto(True, icon_image)  # True means apply to all windows
                else:
                    self.logger.warning("MenuSystem", "No PNG file found for macOS")
            else:  # Windows/Linux
                if os.path.exists(icon_path):
                    self.logger.debug_at_level(DEBUG_L1, "MenuSystem", "Found ICO file, setting icon")
                    self.root.iconbitmap(icon_path)
                elif os.path.exists(png_path):
                    self.logger.debug_at_level(DEBUG_L1, "MenuSystem", "Found PNG file, setting icon")
                    icon_image = tk.PhotoImage(file=png_path)
                    self.root.iconphoto(True, icon_image)
                else:
                    self.logger.warning("MenuSystem", "No icon files found")
        except Exception as e:
            self.logger.error("MenuSystem", f"Error loading icon: {str(e)}")
            
        # Make window resizable with minimum size
        self.root.resizable(True, True)
        self.root.minsize(700, 900)  # Increased minimum width to ensure all tabs are visible
        
        # Add window shadow effect
        self.root.attributes('-alpha', 0.98)  # Slight transparency for modern look
        
        # Configure styles
        self._configure_styles()
        self._build_ui()
        
        # Register for scene-related events
        self._register_event_handlers()
        
        # Center window on screen
        self._center_window()

        # Set up keyboard control from UI
        self._setup_keyboard_control()
        
    # Add keyboard control setup method
    def _setup_keyboard_control(self):
        """Set up keyboard event handling for drone control from UI window"""
        # Map keys to movement directions
        self.key_direction_map = {
            'w': ('forward', 1),
            's': ('forward', -1),
            'a': ('sideward', -1),
            'd': ('sideward', 1),
            'space': ('upward', 1),  # Use 'space' instead of ' ' for Tkinter
            'z': ('upward', -1),
            'q': ('yaw', 1),
            'e': ('yaw', -1),
        }
        
        # Track specific key names
        self.known_keysyms = {
            'space': 'space',
            'w': 'w', 'a': 'a', 's': 's', 'd': 'd',
            'z': 'z', 'q': 'q', 'e': 'e',
            'W': 'w', 'A': 'a', 'S': 's', 'D': 'd',
            'Z': 'z', 'Q': 'q', 'E': 'e'
        }
        
        # Bind key press and release events
        self.root.bind("<KeyPress>", self._on_ui_key_press)
        self.root.bind("<KeyRelease>", self._on_ui_key_release)
        
        # Add specific space key binding
        self.root.bind("<space>", lambda e: self._on_ui_key_press_special('space'))
        self.root.bind("<KeyRelease-space>", lambda e: self._on_ui_key_release_special('space'))
        
        # Bind focus events
        self.root.bind("<FocusIn>", self._on_focus_in)
        self.root.bind("<FocusOut>", self._on_focus_out)
        
        # Schedule regular movement updates based on pressed keys
        self._schedule_movement_updates()
        
        # Make sure we grab focus for keyboard events
        self.root.after(100, self._ensure_focus)
    
    def _on_focus_in(self, event):
        """Handle window gaining focus"""
        self.control_status_var.set("UI Control Active")
        self.control_status_label.configure(foreground="#00FF00")  # Green
        
        # Ensure we don't have any stuck keys from previous state
        self._ui_pressed_keys.clear()
        
        # Stop any existing movement to ensure clean state
        EM.publish('keyboard/move', (0.0, 0.0, 0.0))
        EM.publish('keyboard/rotate', 0.0)
        
        self.logger.info("MenuSystem", "UI control active - window regained focus")
    
    def _on_focus_out(self, event):
        """Handle window losing focus"""
        self.control_status_var.set("UI Control Inactive - Click window to activate")
        self.control_status_label.configure(foreground="#FF3333")  # Red
        
        # Clear pressed keys to stop movement
        self._ui_pressed_keys.clear()
        
        # Stop any existing movement
        EM.publish('keyboard/move', (0.0, 0.0, 0.0))
        EM.publish('keyboard/rotate', 0.0)
        
        self.logger.warning("MenuSystem", "UI control inactive - window lost focus")
    
    def _ensure_focus(self):
        """Ensure the window has focus for keyboard events"""
        self.root.focus_force()
        
        # Update status message
        if self.root.focus_get():
            self.control_status_var.set("UI Control Active")
            self.control_status_label.configure(foreground="#00FF00")  # Green
            self.logger.info("MenuSystem", "UI control active - window has focus")
        else:
            self.control_status_var.set("UI Control Inactive - Click window to activate")
            self.control_status_label.configure(foreground="#FF3333")  # Red
            self.logger.warning("MenuSystem", "UI control inactive - window lacks focus")
    
    def _on_ui_key_press(self, event):
        """Handle key press events from UI"""
        # Get the key symbol or character
        key = event.keysym.lower() if hasattr(event, 'keysym') else event.char.lower()
        
        # Map to known key if possible
        if key in self.known_keysyms:
            key = self.known_keysyms[key]
        
        # Ignore if the key is not in our mapping
        if key not in self.key_direction_map:
            self.logger.debug_at_level(DEBUG_L3, "MenuSystem", f"Ignoring unknown key: {key}")
            return
        
        # Add to pressed keys set
        self._ui_pressed_keys.add(key)
        
        # Log key press for debugging
        self.logger.debug_at_level(DEBUG_L3, "MenuSystem", f"UI key press: {key}")
    
    def _on_ui_key_press_special(self, key):
        """Handle special key press events that need specific handling"""
        self._ui_pressed_keys.add(key)
        self.logger.debug_at_level(DEBUG_L3, "MenuSystem", f"UI special key press: {key}")
        return "break"  # Prevent default handling
    
    def _on_ui_key_release(self, event):
        """Handle key release events from UI"""
        # Get the key symbol or character
        key = event.keysym.lower() if hasattr(event, 'keysym') else event.char.lower()
        
        # Map to known key if possible
        if key in self.known_keysyms:
            key = self.known_keysyms[key]
        
        # Remove from pressed keys set if present
        if key in self._ui_pressed_keys:
            self._ui_pressed_keys.discard(key)
            
        # Log key release for debugging
        self.logger.debug_at_level(DEBUG_L3, "MenuSystem", f"UI key release: {key}")
    
    def _on_ui_key_release_special(self, key):
        """Handle special key release events that need specific handling"""
        if key in self._ui_pressed_keys:
            self._ui_pressed_keys.discard(key)
        self.logger.debug_at_level(DEBUG_L3, "MenuSystem", f"UI special key release: {key}")
        return "break"  # Prevent default handling
    
    def _schedule_movement_updates(self):
        """Schedule regular movement updates based on pressed keys"""
        # Process current key state
        self._process_movement()
        
        # Schedule next update (every 20ms for smooth control)
        self.root.after(20, self._schedule_movement_updates)
    
    def _process_movement(self):
        """Process movement based on currently pressed keys"""
        # Calculate movement values
        forward = sideward = upward = yaw = 0
        
        for key in self._ui_pressed_keys:
            if key not in self.key_direction_map:
                continue
            
            direction, sign = self.key_direction_map[key]
            if direction == 'forward':
                forward += sign
            elif direction == 'sideward':
                sideward += sign
            elif direction == 'upward':
                upward += sign
            elif direction == 'yaw':
                yaw += sign
        
        # Get movement parameters from config
        move_step = self.config.get('move_step', 0.2)
        rotate_step = self.config.get('rotate_step_deg', 15.0)
        
        # Increase the movement speed for UI control by 6x
        # We'll also apply a small adjustment factor since we're updating more frequently
        ui_speed_multiplier = 6.0  # 5 times faster for UI control
        smooth_move_step = move_step * ui_speed_multiplier * 0.5
        smooth_rotate_step = math.radians(rotate_step) * 0.5
        
        # Send movement events if there are active keys
        if self._ui_pressed_keys:
            if forward or sideward or upward:
                EM.publish('keyboard/move', (sideward * smooth_move_step, forward * smooth_move_step, upward * smooth_move_step))
            
            if yaw:
                EM.publish('keyboard/rotate', yaw * smooth_rotate_step)
        
        # Always process movement, which helps ensure smooth control
        # This gets called regularly via _schedule_movement_updates

    def _center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _configure_styles(self):
        """Configure modern styles for the application"""
        style = ttk.Style(self.root)
        style.theme_use('clam')
        
        # Configure colors - Modern dark theme with accent colors
        bg_color = "#1a1a1a"  # Dark background
        fg_color = "#ffffff"  # White text
        accent_color = "#00b4d8"  # Modern blue accent
        success_color = "#2ecc71"  # Modern green
        warning_color = "#f1c40f"  # Modern yellow
        error_color = "#e74c3c"  # Modern red
        hover_color = "#2d2d2d"  # Slightly lighter for hover states
        
        # Configure notebook style
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", 
                       background=bg_color,
                       foreground=fg_color,
                       padding=[18, 8],  # Increased horizontal padding for wider tabs
                       font=("Segoe UI", 10, "bold"),
                       justify="center")  # Center text in tabs
        style.map("TNotebook.Tab",
                 background=[("selected", hover_color)],
                 foreground=[("selected", accent_color)])
        
        # Make tabs expand to fill entire width
        style.layout("TNotebook", [("TNotebook.client", {"sticky": "nswe"})])
        style.layout("TNotebook.Tab", [
            ("TNotebook.tab", {
                "sticky": "nswe",  # Make tabs expand in all directions
                "children": [
                    ("TNotebook.padding", {
                        "side": "top",
                        "sticky": "nswe",
                        "children": [
                            ("TNotebook.label", {"side": "top", "sticky": "n", "expand": 1})  # Center-align text with expand=1 and sticky="n"
                        ]
                    })
                ]
            })
        ])
        
        # Configure frame styles
        style.configure("TFrame", background=bg_color)
        style.configure("TLabelframe", 
                       background=bg_color, 
                       foreground=fg_color,
                       borderwidth=1,
                       relief="solid")
        style.configure("TLabelframe.Label", 
                       background=bg_color,
                       foreground=accent_color,
                       font=("Segoe UI", 11, "bold"),
                       padding=[0, 5])
        
        # Configure label styles
        style.configure("TLabel", 
                       background=bg_color,
                       foreground=fg_color,
                       font=("Segoe UI", 10),
                       padding=[5, 2])
        style.configure("Title.TLabel",
                       font=("Segoe UI", 18, "bold"),
                       foreground=accent_color,
                       padding=[0, 10])
        style.configure("Subtitle.TLabel",
                       font=("Segoe UI", 12, "bold"),
                       foreground=fg_color,
                       padding=[0, 5])
        
        # Configure button styles
        style.configure("TButton",
                       background=bg_color,
                       foreground=fg_color,
                       padding=[20, 15],  # Increased padding for larger buttons
                       font=("Segoe UI", 12, "bold"),  # Larger font
                       borderwidth=1,
                       relief="solid",
                       anchor="center",
                       justify="center")
        style.map("TButton",
                 background=[("active", hover_color)],
                 foreground=[("active", accent_color)],
                 relief=[("pressed", "sunken")])
        
        # Configure Apply button style with light green color
        style.configure("Apply.TButton",
                       background="#4CAF50",  # Light green
                       foreground="#ffffff",
                       padding=[20, 15],
                       font=("Segoe UI", 12, "bold"),
                       borderwidth=1,
                       relief="solid")
        style.map("Apply.TButton",
                 background=[("active", "#3E8E41")],  # Darker green on hover
                 foreground=[("active", "#ffffff")],
                 relief=[("pressed", "sunken")])
        
        # Configure scene control button styles with colors
        # Create button - Green
        style.configure("Create.TButton",
                       background=success_color,
                       foreground="#ffffff",
                       padding=[20, 15],  # Increased padding for larger buttons
                       font=("Segoe UI", 12, "bold"),  # Larger font
                       borderwidth=1,
                       width=30,  # Increased width
                       relief="solid")
        style.map("Create.TButton",
                 background=[("active", "#27ae60")],  # Darker green on hover
                 foreground=[("active", "#ffffff")],
                 relief=[("pressed", "sunken")])
                 
        # Clear button - Orange
        style.configure("Clear.TButton",
                       background="#e67e22",  # Orange
                       foreground="#ffffff",
                       padding=[20, 15],  # Increased padding for larger buttons
                       font=("Segoe UI", 12, "bold"),  # Larger font
                       borderwidth=1,
                       width=30,  # Increased width
                       relief="solid")
        style.map("Clear.TButton",
                 background=[("active", "#d35400")],  # Darker orange on hover
                 foreground=[("active", "#ffffff")],
                 relief=[("pressed", "sunken")])
                 
        # Cancel button - Red
        style.configure("Cancel.TButton",
                       background=error_color,
                       foreground="#ffffff",
                       padding=[20, 15],  # Increased padding for larger buttons
                       font=("Segoe UI", 12, "bold"),  # Larger font
                       borderwidth=1,
                       width=30,  # Increased width
                       relief="solid")
        style.map("Cancel.TButton",
                 background=[("active", "#c0392b")],  # Darker red on hover
                 foreground=[("active", "#ffffff")],
                 relief=[("pressed", "sunken")])
        
        # Configure quit button style
        style.configure("Quit.TButton",
                       background=bg_color,
                       foreground=error_color,
                       padding=[15, 10],
                       font=("Segoe UI", 12, "bold"),
                       borderwidth=1,
                       relief="solid")
        style.map("Quit.TButton",
                 background=[("active", hover_color)],
                 foreground=[("active", error_color)],
                 relief=[("pressed", "sunken")])
        
        # Configure entry styles
        style.configure("TEntry",
                       fieldbackground=hover_color,
                       foreground=fg_color,
                       borderwidth=1,
                       relief="solid",
                       font=("Segoe UI", 10),
                       padding=[5, 2])
        
        # Configure checkbutton styles
        style.configure("TCheckbutton",
                       background=bg_color,
                       foreground=fg_color,
                       font=("Segoe UI", 10),
                       padding=[5, 2])
        style.map("TCheckbutton",
                 background=[("active", bg_color)],
                 foreground=[("active", accent_color)],
                 indicatorcolor=[("selected", accent_color), ("!selected", hover_color)],
                 indicatorbackground=[("selected", hover_color), ("!selected", hover_color)],
                 indicatorrelief=[("selected", "flat"), ("!selected", "flat")],
                 indicatorborderwidth=[("selected", 0), ("!selected", 0)],
                 indicatorforeground=[("selected", accent_color), ("!selected", hover_color)])
        
        # Configure progress bar styles with gradients
        style.configure("Red.Horizontal.TProgressbar", 
                       troughcolor=bg_color,
                       background=error_color,
                       bordercolor=accent_color,
                       thickness=10)
        style.configure("Orange.Horizontal.TProgressbar", 
                       troughcolor=bg_color,
                       background=warning_color,
                       bordercolor=accent_color,
                       thickness=10)
        style.configure("Yellow.Horizontal.TProgressbar", 
                       troughcolor=bg_color,
                       background=warning_color,
                       bordercolor=accent_color,
                       thickness=10)
        style.configure("Green.Horizontal.TProgressbar", 
                       troughcolor=bg_color,
                       background=success_color,
                       bordercolor=accent_color,
                       thickness=10)

    def _register_event_handlers(self):
        """Set up event handlers for scene-related events"""
        # Scene creation events
        EM.subscribe(SCENE_CREATION_PROGRESS, self._on_scene_progress)
        EM.subscribe(SCENE_CREATION_COMPLETED, self._on_scene_completed)
        EM.subscribe(SCENE_CREATION_CANCELED, self._on_scene_canceled)
        EM.subscribe(SCENE_CLEARED, self._on_scene_cleared)
        
        # Handle scene creation requests from menus
        EM.subscribe('scene/creation/request', self._on_scene_creation_request)
        EM.subscribe('simulation/frame', self._on_simulation_frame)
        EM.subscribe('simulation/shutdown', self.cleanup)
        
        # Subscribe to UI update trigger
        EM.subscribe('trigger_ui_update', self._force_ui_update)
        
        # Subscribe to dataset capture complete for victim distance updates
        EM.subscribe('dataset/capture/complete', self._update_victim_indicator)
        
        # Subscribe to victim detection events
        EM.subscribe('victim/detected', self._update_victim_indicator)
        
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

    def _update_tab_widths(self, event=None):
        """Update tab widths to fill the notebook width evenly when the window is resized."""
        try:
            tab_count = self.notebook.index('end')
            if tab_count > 0:
                # Get the current width of the notebook
                notebook_width = self.notebook.winfo_width()
                if notebook_width > 0:
                    # Calculate new tab width (with a small margin)
                    tab_width = max(1, (notebook_width // tab_count) - 2)
                    # Update the style while maintaining centered text
                    style = ttk.Style()
                    style.configure('TNotebook.Tab', width=tab_width, justify="center", anchor="center")
        except Exception as e:
            # Ignore errors during resize
            pass
            
    def _build_ui(self):
        """Build the main UI with tabs for different functionality."""
        # Main container frame with adjusted padding
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create the Notebook (tabbed interface)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Scene tab
        scene_tab = ttk.Frame(self.notebook)
        self.notebook.add(scene_tab, text="Scene")
        self._build_scene_tab(scene_tab)
        
        # Controls tab
        controls_tab = ttk.Frame(self.notebook)
        self.notebook.add(controls_tab, text="Controls")
        self._build_controls_tab(controls_tab)
        
        # Config tab
        config_tab = ttk.Frame(self.notebook)
        self.notebook.add(config_tab, text="Config")
        self._build_config_tab(config_tab)
        
        # Status tab
        status_tab = ttk.Frame(self.notebook)
        self.notebook.add(status_tab, text="Status")
        self._build_status_tab(status_tab)
        
        # Help tab
        help_tab = ttk.Frame(self.notebook)
        self.notebook.add(help_tab, text="Help")
        self._build_help_tab(help_tab)
        
        # Performance tab
        perf_tab = ttk.Frame(self.notebook)
        self.notebook.add(perf_tab, text="Monitor")
        self._build_performance_tab(perf_tab)
        
        # Dataset tab
        dataset_tab = ttk.Frame(self.notebook)
        self.notebook.add(dataset_tab, text="Dataset")
        self._build_dataset_tab(dataset_tab)
        
        # Logging tab
        logging_tab = ttk.Frame(self.notebook)
        self.notebook.add(logging_tab, text="Logging")
        self._build_logging_tab(logging_tab)
        
        # Configure tab stretching - ensure tabs take full width
        self.root.update_idletasks()  # Force geometry update
        tab_count = self.notebook.index('end')
        if tab_count > 0:
            # Set tab width to distribute evenly
            tab_width = self.notebook.winfo_width() // tab_count
            style = ttk.Style()
            style.configure('TNotebook.Tab', width=tab_width, justify="center", anchor="center")
        
        # Bind window resize to update tab widths
        self.root.bind("<Configure>", self._update_tab_widths)
            
        # Connect tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # Add quit button at the bottom
        quit_frame = ttk.Frame(self.root)
        quit_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        quit_btn = ttk.Button(quit_frame, text="Quit Application", 
                           style="Quit.TButton", command=self._quit)
        quit_btn.pack(fill=tk.X)

    def _on_tab_changed(self, event):
        """Handle tab selection change"""
        self._pause_monitoring()  # Always pause first
        
        # Get the current tab index and name
        tab_idx = event.widget.index('current')
        tab_name = event.widget.tab(tab_idx, 'text')
        
        # Update the current tab attribute
        self._current_tab = tab_name
        
        self.logger.debug_at_level(DEBUG_L2, "MenuSystem", f"Tab changed to: {tab_name}")
        
        if tab_name == "Performance" or tab_name == "Monitor":
            # Resume monitoring only if needed
            if self.config.get("enable_performance_monitoring", False):
                self._resume_monitoring()
        elif tab_name == "Logging":
            # Update logging status when tab is selected
            self._update_logging_status()
        elif tab_name == "Status":
            # Update status indicators
            self._update_victim_indicator({'victim_vec': (0, 0, 0, 0)})
        elif tab_name == "Config":
            # Update config values
            self._on_config_updated_gui(None)
            
        # Force a single update
        self.root.update_idletasks()

    def _pause_monitoring(self):
        """Pause performance monitoring"""
        if self._monitoring_after_id:
            self.root.after_cancel(self._monitoring_after_id)
            self._monitoring_after_id = None
        self._monitoring_active = False

    def _resume_monitoring(self):
        """Resume performance monitoring"""
        if not self._monitoring_active and self.config.get("enable_performance_monitoring", False):
            self._monitoring_active = True
            self._schedule_ui_update()

    def _schedule_ui_update(self):
        """Schedule the next UI update with optimized timing"""
        # Cancel any existing scheduled update
        if self._monitoring_after_id:
            self.root.after_cancel(self._monitoring_after_id)
            self._monitoring_after_id = None
        
        # Only schedule new update if monitoring is enabled
        if self.config.get("enable_performance_monitoring", False):
            current_time = time.time()
            self._frame_times.append(current_time)
            
            # Only update the UI if we're on the Performance tab
            if self._current_tab == "Performance" or self._current_tab == "Monitor":
                if current_time - self._last_ui_update >= 0.1:  # 100ms update interval
                    self._last_ui_update = current_time
                    self._update_performance_metrics()
            
            # Schedule next update regardless of current tab
            self._monitoring_after_id = self.root.after(100, self._schedule_ui_update)
            self._monitoring_active = True
        else:
            # Only clear metrics if monitoring is disabled
            self._monitoring_active = False
            self._clear_performance_metrics()

    def _build_scene_tab(self, parent):
        # Title with modern styling
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill="x", pady=(0, 20))
        ttk.Label(title_frame, text="Drone Search & Rescue Simulator", style="Title.TLabel").pack()
        
        # Progress bar container with modern styling
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill="x", pady=10)
        
        # Progress bar for scene creation with enhanced styling
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, 
                                          variable=self.progress_var, 
                                          maximum=1.0,
                                          style="Green.Horizontal.TProgressbar",
                                          mode='determinate')
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.pack_forget()  # Hide initially
        
        # Status label with enhanced styling
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", pady=10)
        self.status_label = ttk.Label(status_frame, 
                                    text="", 
                                    style="Subtitle.TLabel",
                                    wraplength=400)  # Allow text wrapping
        self.status_label.pack(pady=5)
        
        # Create scene with event-driven approach
        def create_scene_with_event():
            # Apply all config changes first to ensure latest values are used
            self._apply_all_changes()  # Use apply_all_changes instead of apply_all_config_changes
            
            # Disable all buttons during scene creation
            for btn in self.scene_buttons:
                if "Cancel" not in btn["text"]:
                    btn.configure(state="disabled")
                else:
                    # Enable the cancel button during scene creation
                    btn.configure(state="normal")
            
            # Show progress bar with animation
            self.progress_bar.pack(fill="x", pady=5)
            self.progress_var.set(0.0)
            self.status_label.configure(text="Creating scene...", foreground="#00b4d8")
            
            # Start scene creation via event system
            create_scene(self.config)
        
        # Restart scene using event-based approach
        def restart_scene():
            # Apply all changes including dynamic objects before restarting
            self._apply_all_changes()
            self.status_label.configure(text="Restarting scene...", foreground="#f1c40f")
            restart_disaster_area(self.config)
            
        # Clear scene using event-based approach with confirmation
        def clear_scene_action():
            # Create confirmation dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Confirm Clear")
            dialog.geometry("300x150")
            dialog.configure(bg="#1a1a1a")
            dialog.transient(self.root)  # Make dialog modal
            dialog.grab_set()  # Make dialog modal
            
            # Center dialog on parent window
            dialog.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
            dialog.geometry(f"+{x}+{y}")
            
            # Add padding frame
            frame = ttk.Frame(dialog, padding=20)
            frame.pack(expand=True, fill="both")
            
            # Warning message
            ttk.Label(frame, 
                     text="Are you sure you want to clear the environment?",
                     style="Subtitle.TLabel",
                     wraplength=250).pack(pady=(0, 20))
            
            # Buttons frame
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill="x", pady=(0, 10))
            
            # Create a style specifically for these confirmation buttons
            style = ttk.Style()
            btn_style = "Confirmation.TButton"
            style.configure(btn_style, 
                           padding=[10, 10], 
                           font=("Segoe UI", 11, "bold"),
                           anchor="center",
                           justify="center")
            
            # Yes button
            yes_btn = ttk.Button(btn_frame, 
                              text="Yes, Clear",
                              command=lambda: self._confirm_clear(dialog),
                              style=btn_style,
                              compound="center")
            yes_btn.pack(side="left", expand=True, padx=(0, 5), fill="both", ipady=5)
            
            # No button
            no_btn = ttk.Button(btn_frame,
                             text="No, Cancel",
                             command=dialog.destroy,
                             style=btn_style,
                             compound="center")
            no_btn.pack(side="left", expand=True, padx=(5, 0), fill="both", ipady=5)
        
        # Cancel ongoing scene creation 
        def cancel_creation():
            cancel_scene_creation()
            self.status_label.configure(text="Canceling scene creation...", foreground="#e74c3c")
        
        # Scene control buttons with enhanced styling
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=10)
        
        # Center frame for buttons
        center_frame = ttk.Frame(button_frame)
        center_frame.pack(anchor="center")
        
        # Create a container for the vertically arranged buttons
        buttons_container = ttk.Frame(center_frame)
        buttons_container.pack(pady=15)
        
        self.scene_buttons = []
        
        # Create Environment button (Green)
        create_btn = ttk.Button(
            buttons_container, 
            text="Create Environment", 
            command=create_scene_with_event,
            style="Create.TButton"
        )
        create_btn.grid(row=0, column=0, padx=10, pady=8)
        self.scene_buttons.append(create_btn)
        
        # Clear Environment button (Orange)
        clear_btn = ttk.Button(
            buttons_container, 
            text="Clear Environment", 
            command=clear_scene_action,
            style="Clear.TButton"
        )
        clear_btn.grid(row=1, column=0, padx=10, pady=8)
        self.scene_buttons.append(clear_btn)
        
        # Cancel Creating Environment button (Red)
        cancel_btn = ttk.Button(
            buttons_container, 
            text="Cancel Creating", 
            command=cancel_creation,
            style="Cancel.TButton"
        )
        cancel_btn.grid(row=2, column=0, padx=10, pady=8)
        
        # Initially disable the Cancel button since creation is not in progress
        cancel_btn.configure(state="disabled")
        self.scene_buttons.append(cancel_btn)
            
        # Add visual separator
        separator = ttk.Separator(parent, orient='horizontal')
        separator.pack(fill='x', pady=20)

    def _confirm_clear(self, dialog):
        """Handle confirmed clear environment action"""
        dialog.destroy()
        self.status_label.configure(text="Clearing scene...", foreground="#e74c3c")
        clear_scene()

    def _build_config_tab(self, parent):
        # Create a canvas with scrollbar for the config options
        canvas = tk.Canvas(parent, bg="#0a0a0a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Configure the canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create a window in the canvas to hold the scrollable frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the scrollbar and canvas with padding
        scrollbar.pack(side="right", fill="y", padx=(5, 0))  # Add padding on the left of scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))  # Add padding on the right of canvas
        
        # Title
        ttk.Label(scrollable_frame, text="Configuration", style="Title.TLabel").pack(pady=(0,20))
        
        # Dynamic Objects Section with centered title
        dynamic_frame = ttk.LabelFrame(scrollable_frame, text="Dynamic Objects", padding=15, labelanchor="n")
        dynamic_frame.pack(fill="x", pady=10, padx=5)
        
        # Falling Trees control
        trees_frame = ttk.Frame(dynamic_frame)
        trees_frame.pack(fill="x", pady=2)
        ttk.Label(trees_frame, text="Number of Falling Trees:", width=25, style="TLabel", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        trees_var = tk.StringVar(value=str(self.config.get("num_falling_trees", 5)))
        trees_entry = ttk.Entry(trees_frame, textvariable=trees_var, width=20)
        trees_entry.pack(side="left", fill="x", expand=True)
        trees_entry.bind('<Return>', lambda e: self._update_config("num_falling_trees", trees_var.get()))
        trees_entry.bind('<FocusOut>', lambda e: self._update_config("num_falling_trees", trees_var.get()))
        self._config_vars["num_falling_trees"] = trees_var
        self._config_widgets["num_falling_trees"] = trees_entry
        
        # Tree Spawn Interval control
        spawn_frame = ttk.Frame(dynamic_frame)
        spawn_frame.pack(fill="x", pady=2)
        ttk.Label(spawn_frame, text="Tree Spawn Interval (s):", width=25, style="TLabel").pack(side="left", padx=(0, 10))
        spawn_var = tk.StringVar(value=str(self.config.get("tree_spawn_interval", 30.0)))
        spawn_entry = ttk.Entry(spawn_frame, textvariable=spawn_var, width=20)
        spawn_entry.pack(side="left", fill="x", expand=True)
        spawn_entry.bind('<Return>', lambda e: self._update_config("tree_spawn_interval", spawn_var.get()))
        spawn_entry.bind('<FocusOut>', lambda e: self._update_config("tree_spawn_interval", spawn_var.get()))
        self._config_vars["tree_spawn_interval"] = spawn_var
        self._config_widgets["tree_spawn_interval"] = spawn_entry

        # Birds control
        birds_frame = ttk.Frame(dynamic_frame)
        birds_frame.pack(fill="x", pady=2)
        ttk.Label(birds_frame, text="Number of Birds:", width=25, style="TLabel", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        birds_var = tk.StringVar(value=str(self.config.get("num_birds", 10)))
        birds_entry = ttk.Entry(birds_frame, textvariable=birds_var, width=20)
        birds_entry.pack(side="left", fill="x", expand=True)
        birds_entry.bind('<Return>', lambda e: self._update_config("num_birds", birds_var.get()))
        birds_entry.bind('<FocusOut>', lambda e: self._update_config("num_birds", birds_var.get()))
        self._config_vars["num_birds"] = birds_var
        self._config_widgets["num_birds"] = birds_entry

        # Bird Speed control
        bird_speed_frame = ttk.Frame(dynamic_frame)
        bird_speed_frame.pack(fill="x", pady=2)
        ttk.Label(bird_speed_frame, text="Bird Movement Speed:", width=25, style="TLabel", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        bird_speed_var = tk.StringVar(value=str(self.config.get("bird_speed", 1.0)))
        bird_speed_entry = ttk.Entry(bird_speed_frame, textvariable=bird_speed_var, width=20)
        bird_speed_entry.pack(side="left", fill="x", expand=True)
        bird_speed_entry.bind('<Return>', lambda e: self._update_config("bird_speed", bird_speed_var.get()))
        bird_speed_entry.bind('<FocusOut>', lambda e: self._update_config("bird_speed", bird_speed_var.get()))
        self._config_vars["bird_speed"] = bird_speed_var
        self._config_widgets["bird_speed"] = bird_speed_entry

        # Environment Settings Section with centered title
        env_frame = ttk.LabelFrame(scrollable_frame, text="Environment Settings", padding=15, labelanchor="n")
        env_frame.pack(fill="x", pady=10, padx=5)
        
        # Add static tree settings first in Environment Settings
        static_trees_frame = ttk.Frame(env_frame)
        static_trees_frame.pack(fill="x", pady=2)
        ttk.Label(static_trees_frame, text="Number of Static Trees:", width=25, style="TLabel", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        static_trees_var = tk.StringVar(value=str(self.config.get("num_trees", 0)))
        static_trees_entry = ttk.Entry(static_trees_frame, textvariable=static_trees_var, width=20)
        static_trees_entry.pack(side="left", fill="x", expand=True)
        static_trees_entry.bind('<Return>', lambda e: self._update_config("num_trees", static_trees_var.get()))
        static_trees_entry.bind('<FocusOut>', lambda e: self._update_config("num_trees", static_trees_var.get()))
        self._config_vars["num_trees"] = static_trees_var
        self._config_widgets["num_trees"] = static_trees_entry
        
        # Add other environment-related fields
        env_fields = [f for f in FIELDS if f['key'] in ['num_rocks', 'num_bushes', 'num_foliage']]
        for field in env_fields:
            key, desc, typ = field['key'], field['desc'], field['type']
            frame = ttk.Frame(env_frame)
            frame.pack(fill="x", pady=2)
            
            # Make specific labels bold
            if key in ['num_rocks', 'num_bushes', 'num_foliage']:
                label = ttk.Label(frame, text=desc+":", width=25, style="TLabel", font=("Segoe UI", 10, "bold"))
            else:
                label = ttk.Label(frame, text=desc+":", width=25, style="TLabel")
            label.pack(side="left", padx=(0, 10))
            
            if typ is bool:
                var = tk.BooleanVar(value=self.config.get(key, False))
                chk = ttk.Checkbutton(frame, variable=var)
                chk.pack(side="left", fill="x", expand=True)
                var.trace_add('write', lambda *_, k=key, v=var: self._update_config(k, v.get()))
                widget = chk
            else:
                var = tk.StringVar(value=str(self.config.get(key, '')))
                ent = ttk.Entry(frame, textvariable=var, width=20)
                ent.pack(side="left", fill="x", expand=True)
                ent.bind('<Return>', lambda e, k=key, v=var: self._update_config(k, v.get()))
                ent.bind('<FocusOut>', lambda e, k=key, v=var: self._update_config(k, v.get()))
                widget = ent
            self._config_vars[key] = var
            self._config_widgets[key] = widget
            
        # Simulation Settings Section with centered title
        sim_frame = ttk.LabelFrame(scrollable_frame, text="Simulation Settings", padding=15, labelanchor="n")
        sim_frame.pack(fill="x", pady=10, padx=5)
        
        # Add simulation-related fields
        sim_fields = [f for f in FIELDS if f['key'] not in [
            'num_rocks', 'num_bushes', 'num_foliage', 
            'num_birds', 'num_falling_trees', 'tree_spawn_interval', 
            'num_trees', 'rc_sensitivity'
        ]]
        for field in sim_fields:
            key, desc, typ = field['key'], field['desc'], field['type']
            frame = ttk.Frame(sim_frame)
            frame.pack(fill="x", pady=2)
            
            # Make area size label bold
            if key == 'area_size':
                label = ttk.Label(frame, text=desc+":", width=25, style="TLabel", font=("Segoe UI", 10, "bold"))
            else:
                label = ttk.Label(frame, text=desc+":", width=25, style="TLabel")
            label.pack(side="left", padx=(0, 10))
            
            if typ is bool:
                var = tk.BooleanVar(value=self.config.get(key, False))
                chk = ttk.Checkbutton(frame, variable=var)
                chk.pack(side="left", fill="x", expand=True)
                var.trace_add('write', lambda *_, k=key, v=var: self._update_config(k, v.get()))
                widget = chk
            else:
                var = tk.StringVar(value=str(self.config.get(key, '')))
                ent = ttk.Entry(frame, textvariable=var, width=20)
                ent.pack(side="left", fill="x", expand=True)
                ent.bind('<Return>', lambda e, k=key, v=var: self._update_config(k, v.get()))
                ent.bind('<FocusOut>', lambda e, k=key, v=var: self._update_config(k, v.get()))
                widget = ent
            self._config_vars[key] = var
            self._config_widgets[key] = widget
            
        # Add a single "Apply Changes" button to handle all changes
        apply_btn = ttk.Button(scrollable_frame, text="Apply Changes", 
                              command=self._apply_all_changes,
                              style="Apply.TButton")
        apply_btn.pack(fill="x", pady=(15, 5), padx=5)

        # Add Save/Load buttons
        save_load_frame = ttk.Frame(scrollable_frame)
        save_load_frame.pack(fill="x", pady=(5, 15), padx=5)
        
        save_btn = ttk.Button(save_load_frame, text="Save Settings", 
                             command=self._save_config)
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        load_btn = ttk.Button(save_load_frame, text="Load Settings", 
                             command=self._load_config)
        load_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Add mouse wheel scrolling support
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        # For Linux/macOS (different event)
        canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))
        
        # Update canvas width when window is resized
        def on_resize(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind('<Configure>', on_resize)

    def _apply_all_changes(self):
        """Apply all changes including dynamic objects"""
        try:
            # Apply regular config changes
            self._apply_all_config_changes()
            
            # Get and validate dynamic object values
            num_birds = max(0, int(self._config_vars["num_birds"].get()))
            num_trees = max(0, int(self._config_vars["num_falling_trees"].get()))
            tree_spawn = max(5.0, float(self._config_vars["tree_spawn_interval"].get()))
            bird_speed = max(0.1, min(5.0, float(self._config_vars["bird_speed"].get())))  # Limit speed between 0.1 and 5.0
            
            # Update the config
            self.config["num_birds"] = num_birds
            self.config["num_falling_trees"] = num_trees
            self.config["tree_spawn_interval"] = tree_spawn
            self.config["bird_speed"] = bird_speed
            
            # Update RandomObjectManager if it exists
            from Managers.scene_manager import get_scene_manager
            SM = get_scene_manager()
            if hasattr(SM, 'random_object_manager') and SM.random_object_manager:
                self.logger.info("MenuSystem", f"Setting counts: {num_birds} birds (speed: {bird_speed}), {num_trees} trees, spawn: {tree_spawn}s")
                SM.random_object_manager.set_object_counts(
                    num_birds=num_birds, 
                    num_falling_trees=num_trees,
                    tree_spawn_interval=tree_spawn,
                    bird_speed=bird_speed
                )
                self.status_label.configure(text=f"Updated: {num_birds} birds (speed: {bird_speed}), {num_trees} trees, spawn: {tree_spawn}s")
                self.root.after(1000, lambda: self.status_label.configure(text=""))
                # Update simulation stats
                self._update_simulation_stats()
            else:
                self.status_label.configure(text="No active scene - create scene first")
                self.root.after(2000, lambda: self.status_label.configure(text=""))
        except ValueError as e:
            self.status_label.configure(text="Please enter valid numbers")
            self.root.after(2000, lambda: self.status_label.configure(text=""))

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
                    # Special handling for move_step to round to one decimal place
                    if key == "move_step" and typ is float:
                        self.config[key] = round(float(value), 1)
                    else:
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
            
            # Update monitoring status if the key is enable_performance_monitoring
            if key == "enable_performance_monitoring":
                # Restart or stop monitoring based on new value
                if new_val and not self._monitoring_active:
                    self._schedule_ui_update()
                elif not new_val and self._monitoring_active:
                    self._clear_performance_metrics()
        else:
            # If key is None or unknown, refresh all
            for k, var in self._config_vars.items():
                val = self.config.get(k)
                if isinstance(var, tk.StringVar):
                    var.set(str(val))
                else:
                    var.set(bool(val))

    def _quit(self):
        """Quit the application with confirmation dialog"""
        if not hasattr(self, 'root') or not self.root:
            # Already quitting or destroyed
            return
        
        self.logger.info("MenuSystem", "Shutting down application...")
        
        # Create dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Confirm Exit")
        dialog.geometry("360x180")
        dialog.transient(self.root)  # Set to be on top of the main window
        dialog.grab_set()  # Modal
        
        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Content
        content_frame = ttk.Frame(dialog, padding=20)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        message = ttk.Label(
            content_frame, 
            text="Are you sure you want to exit?\nThis will close the simulator.",
            font=("Segoe UI", 11),
            wraplength=300,
            justify=tk.CENTER
        )
        message.pack(pady=(0, 20))
        
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill=tk.X)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        confirm_btn = ttk.Button(
            button_frame, 
            text="Exit", 
            style="Quit.TButton",
            command=lambda: self._confirm_quit(dialog)
        )
        confirm_btn.pack(side=tk.RIGHT, padx=5, expand=True, fill=tk.X)

    def _confirm_quit(self, dialog):
        """Handle confirmed quit action"""
        dialog.destroy()
        self.cleanup()
        EM.publish('simulation/shutdown', None)
        
        # Force application to quit in case there are hanging threads
        if hasattr(self, 'root') and self.root:
            # Set a force-quit timer in case normal exit fails
            # Note: after() schedules task, but we need to immediately start quitting process
            self.root.after(500, lambda: os._exit(0))
            
            # Try normal exit first
            try:
                self.root.quit()
                self.root.destroy()
            except Exception as e:
                self.logger.error("MenuSystem", f"Error during application shutdown: {e}")
                # If we reach here, the force-quit will still happen via the scheduled after() call

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
            for i, btn in enumerate(self.scene_buttons):
                if i == 2:  # Cancel button is index 2
                    btn.configure(state="disabled")  # Disable the cancel button
                else:
                    btn.configure(state="normal")  # Enable other buttons
            self.progress_bar.pack_forget()
            # Update simulation stats
            self._update_simulation_stats()
        
        # Schedule the update on the main thread
        self.root.after(0, update_ui)
        
    def _on_scene_canceled(self, _):
        """Handle scene creation cancellation with error handling"""
        def update_ui():
            try:
                self.status_label.configure(text="Scene creation canceled", foreground="white")
                self.progress_var.set(0.0)
                self.progress_bar.pack_forget()
                
                # Re-enable all buttons except Cancel
                for btn in self.scene_buttons:
                    if "Cancel" in btn["text"]:
                        btn.configure(state="disabled")
                    else:
                        btn.configure(state="normal")
            except Exception as e:
                self.logger.error("MenuSystem", f"Error updating UI after scene canceled: {e}")
        
        # Schedule UI update on the main thread
        self.root.after(0, update_ui)
        
    def _on_scene_cleared(self, _):
        """Handle scene cleared event by updating UI state"""
        def update_ui():
            try:
                # Reset status label
                if hasattr(self, 'status_label'):
                    self.status_label.configure(text="Scene cleared", foreground="white")
                
                # Reset victim indicators
                if hasattr(self, 'distance_var'):
                    self.distance_var.set("Not detected")
                
                if hasattr(self, 'elevation_var'):
                    self.elevation_var.set("Not detected")
                
                if hasattr(self, 'direction_canvas'):
                    self.direction_canvas.delete("all")  # Clear the direction indicator
                
                # Re-enable scene control buttons
                if hasattr(self, 'scene_buttons'):
                    for btn in self.scene_buttons:
                        btn.configure(state="normal")
                
            except Exception as e:
                self.logger.error("MenuSystem", f"Error updating UI after scene clear: {e}")
        
        # Schedule UI update on the main thread
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
            if i == 2:  # Cancel button is index 2
                btn.configure(state="normal")  # Enable the cancel button
            else:
                btn.configure(state="disabled")  # Disable other buttons
        
        # Show progress bar
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_var.set(0.0)
        self.status_label.configure(text="Creating scene...")
        
        # Start scene creation via event
        create_scene(config)

    def _update_victim_indicator(self, data):
        """Update the victim distance and direction indicator based on capture data"""
        # Add debug logging to see what data is coming in
        self.logger.debug_at_level(DEBUG_L1, "MenuSystem", f"Received victim data: {data}")
        
        # Extract victim vector data (dx, dy, dz) and distance
        if 'victim_vec' not in data:
            self.logger.warning("MenuSystem", "Missing victim_vec in update data")
            return
            
        victim_vec = data.get('victim_vec', (0, 0, 0))
        distance = data.get('distance', 0)
        
        # Validate the vector format
        if not isinstance(victim_vec, tuple) or len(victim_vec) != 3:
            self.logger.debug_at_level(DEBUG_L1, "MenuSystem", f"Invalid victim vector format: {type(victim_vec)}, len: {len(victim_vec) if hasattr(victim_vec, '__len__') else 'N/A'}")
            return
            
        # Unpack victim vector data
        try:
            dx, dy, dz = victim_vec
            self.logger.debug_at_level(DEBUG_L1, "MenuSystem", f"Processing victim data: dx={dx}, dy={dy}, dz={dz}, distance={distance}")
        except Exception as e:
            self.logger.error("MenuSystem", f"Error unpacking victim vector: {e}")
            return
        
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
                self.signal_bar.configure(style='Red.Horizontal.TProgressbar')
            else:
                # Normalize signal strength: stronger when closer
                # Maximum strength at 1m, diminishes with distance
                strength = min(1.0, 1.0 / max(1.0, distance))
                self.signal_var.set(strength)
                
                # Update signal bar color based on strength
                if strength > 0.85:
                    self.signal_bar.configure(style='Green.Horizontal.TProgressbar')
                elif strength > 0.5:
                    self.signal_bar.configure(style='Yellow.Horizontal.TProgressbar')
                elif strength > 0.25:
                    self.signal_bar.configure(style='Orange.Horizontal.TProgressbar')
                else:
                    self.signal_bar.configure(style='Red.Horizontal.TProgressbar')
                
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
        """Draw a futuristic aeronautical direction indicator on the canvas showing victim direction"""
        # Clear canvas
        self.direction_canvas.delete("all")
        canvas_width = self.direction_canvas.winfo_width()
        canvas_height = self.direction_canvas.winfo_height()
        
        # Ensure we have minimum dimensions
        if canvas_width < 20 or canvas_height < 20:
            canvas_width = canvas_height = 250  # Increased from 150 to 250
            
        # Calculate center and radius
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        radius = min(center_x, center_y) - 15  # Slightly larger margin (10 to 15)
        radius_int = int(radius)
        
        # Draw outer circle with gradient
        for i in range(3):
            opacity = 0.1 + i * 0.1
            color = f'#{int(0x00 * opacity):02x}{int(0xFF * opacity):02x}{int(0x00 * opacity):02x}'
        self.direction_canvas.create_oval(
            center_x - radius, center_y - radius, 
            center_x + radius, center_y + radius, 
                outline=color,
                width=3  # Thicker line (2 to 3)
        )
        
        # Draw inner circle
        inner_radius = radius * 0.8
        self.direction_canvas.create_oval(
            center_x - inner_radius, center_y - inner_radius,
            center_x + inner_radius, center_y + inner_radius,
            outline="#00FF00",
            width=2  # Thicker line (1 to 2)
        )
        
        # Add a simple crosshair in the center
        crosshair_size = radius * 0.2  # Size of the crosshair lines
        # Horizontal line
        self.direction_canvas.create_line(
            center_x - crosshair_size, center_y,
            center_x + crosshair_size, center_y,
            fill="#00FF00",
            width=2
        )
        # Vertical line
        self.direction_canvas.create_line(
            center_x, center_y - crosshair_size,
            center_x, center_y + crosshair_size,
            fill="#00FF00",
            width=2
        )
        
        # Draw distance rings with gradient
        for r in range(radius_int, 0, -radius_int//4):
            opacity = 0.2 + (1 - r/radius) * 0.3
            color = f'#{int(0x00 * opacity):02x}{int(0xFF * opacity):02x}{int(0x00 * opacity):02x}'
            self.direction_canvas.create_oval(
                center_x - r, center_y - r,
                center_x + r, center_y + r,
                outline=color,
                width=2  # Thicker line (1 to 2)
        )
        
        # If direction is valid, draw victim indicator
        if dx is not None and dy is not None and (dx != 0 or dy != 0):
            # Calculate endpoint of direction vector
            end_x = center_x + dx * radius
            end_y = center_y - dy * radius  # Inverted y-axis
            
            # Draw direction vector with HUD-style arrow
            # Main line
            self.direction_canvas.create_line(
                center_x, center_y,
                end_x, end_y,
                fill="#00FF00",
                width=3  # Thicker line (2 to 3)
            )
            
            # Draw arrow head
            arrow_size = 15  # Increased from 10 to 15
            angle = math.atan2(end_y - center_y, end_x - center_x)
            arrow_angle1 = angle + math.radians(150)
            arrow_angle2 = angle - math.radians(150)
            
            arrow_x1 = end_x + arrow_size * math.cos(arrow_angle1)
            arrow_y1 = end_y + arrow_size * math.sin(arrow_angle1)
            arrow_x2 = end_x + arrow_size * math.cos(arrow_angle2)
            arrow_y2 = end_y + arrow_size * math.sin(arrow_angle2)
            
            self.direction_canvas.create_polygon(
                end_x, end_y,
                arrow_x1, arrow_y1,
                arrow_x2, arrow_y2,
                fill="#00FF00",
                outline=""
            )
            
            # Draw victim point with HUD-style targeting reticle
            reticle_size = 22  # Increased from 15 to 22
            # Outer circle
            self.direction_canvas.create_oval(
                end_x - reticle_size, end_y - reticle_size,
                end_x + reticle_size, end_y + reticle_size,
                outline="#00FF00",
                width=2  # Thicker line (1 to 2)
            )
            # Inner circle
            self.direction_canvas.create_oval(
                end_x - reticle_size/2, end_y - reticle_size/2,
                end_x + reticle_size/2, end_y + reticle_size/2,
                outline="#00FF00",
                width=2  # Thicker line (1 to 2)
            )
            
            # Draw crosshair lines
            self.direction_canvas.create_line(
                end_x - reticle_size, end_y,
                end_x + reticle_size, end_y,
                fill="#00FF00",
                width=2  # Thicker line (1 to 2)
            )
            self.direction_canvas.create_line(
                end_x, end_y - reticle_size,
                end_x, end_y + reticle_size,
                fill="#00FF00",
                width=2  # Thicker line (1 to 2)
            )
        else:
            # If no vector, draw "not detected" text with HUD style
            self.direction_canvas.create_text(
                center_x, center_y,
                text="NO SIGNAL",
                fill="#00FF00",
                font=("Courier", 16, "bold")  # Larger font (12 to 16)
            )

    def _build_status_tab(self, parent):
        """Build the status tab with victim distance indicator"""
        # Title
        ttk.Label(parent, text="Simulation Status", style="Title.TLabel").pack(pady=(0,20))
        
        # UI Control status indicator (simplified)
        self.control_status_label = ttk.Label(
            parent,
            textvariable=self.control_status_var,
            foreground="#00FF00",  # Green text for visibility
            font=("Segoe UI", 10, "bold"),
            wraplength=400
        )
        self.control_status_label.pack(pady=5)
        
        # Victim indicator section
        victim_frame = ttk.LabelFrame(parent, text="Victim Detection", padding=15, labelanchor="n")
        victim_frame.pack(fill="x", pady=10)
        
        # Distance indicator
        ttk.Label(victim_frame, text="Distance to victim:", style="Subtitle.TLabel").pack(pady=5)
        self.distance_var = tk.StringVar(value="Not detected")
        self.distance_label = ttk.Label(victim_frame, textvariable=self.distance_var, 
                                      font=("Segoe UI", 14))
        self.distance_label.pack(pady=5)
        
        # Elevation indicator
        ttk.Label(victim_frame, text="Elevation difference:", style="Subtitle.TLabel").pack(pady=5)
        self.elevation_var = tk.StringVar(value="Not detected")
        self.elevation_label = ttk.Label(victim_frame, textvariable=self.elevation_var, 
                                       font=("Segoe UI", 14))
        self.elevation_label.pack(pady=5)
            
        # Direction indicator (graphical)
        ttk.Label(victim_frame, text="Direction:", style="Subtitle.TLabel").pack(pady=5)
        canvas_size = 250  # Increased from 150 to 250
        self.direction_canvas = tk.Canvas(victim_frame, width=canvas_size, height=canvas_size, 
                                         bg="black", highlightthickness=1, highlightbackground="#666666")
        self.direction_canvas.pack(pady=10)
        
        # Draw the initial state (no detection)
        self._draw_direction_indicator(None, None, None)
        
        # Signal strength (distance-based)
        ttk.Label(victim_frame, text="Signal strength:", style="Subtitle.TLabel").pack(pady=5)
        self.signal_var = tk.DoubleVar(value=0.0)
        self.signal_bar = ttk.Progressbar(victim_frame, variable=self.signal_var, maximum=1.0)
        self.signal_bar.pack(fill="x", pady=5, padx=10)

    def _build_help_tab(self, parent):
        """Build the help tab with application information and controls"""
        # Create a canvas with scrollbar for the help content
        canvas = tk.Canvas(parent, bg="#0a0a0a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Configure the canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create a window in the canvas to hold the scrollable frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the scrollbar and canvas with padding
        scrollbar.pack(side="right", fill="y", padx=(5, 0))  # Add padding on the left of scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))  # Add padding on the right of canvas
        
        # Define enhanced styles for the help tab
        help_title_font = ("Segoe UI", 22, "bold")  # Larger title font
        section_title_font = ("Segoe UI", 14, "bold")  # Enhanced section title font
        help_content_font = ("Segoe UI", 12)  # Larger content font
        
        # Title with enhanced styling
        title_frame = ttk.Frame(scrollable_frame, padding=(0, 0, 0, 10))
        title_frame.pack(fill="x", pady=(0, 25))
        title_label = ttk.Label(
            title_frame, 
            text="Help & Information", 
            font=help_title_font,
            foreground="#00b4d8"  # Accent color for title
        )
        title_label.pack(pady=(5, 0))
        
        # Version Information Section with enhanced styling
        version_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Version Information", 
            padding=20,
            labelanchor="n"  # Center the label
        )
        version_frame.pack(fill="x", pady=10, padx=15)  # Increased padding
        
        version_info = """
• Version: HyperDrive Sync v1.3.1
• Build: 10.05.2025
        """
        version_label = ttk.Label(
            version_frame, 
            text=version_info, 
            justify="left",
            font=help_content_font
        )
        version_label.pack(fill="x")
        
        # Keyboard Controls Section with enhanced styling
        keyboard_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Keyboard Controls", 
            padding=20,
            labelanchor="n"
        )
        keyboard_frame.pack(fill="x", pady=10, padx=15)  # Increased padding
        
        keyboard_info = """
• There are two ways to control the drone via keyboard:
  - Terminal Control: Use the terminal to send commands directly to the drone.
  - UI Control: Use the application interface for keyboard control.
  
• Movement Controls (UI Control):
  - W: Move forward
  - S: Move backward
  - A: Move left
  - D: Move right
  - Space: Move up
  - Z: Move down
  - Q: Rotate counterclockwise
  - E: Rotate clockwise
        """
        keyboard_label = ttk.Label(
            keyboard_frame, 
            text=keyboard_info, 
            justify="left",
            font=help_content_font
        )
        keyboard_label.pack(fill="x")
        
        # RC Joystick Controls section
        joystick_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="RC Joystick Controls", 
            padding=20,
            labelanchor="n"
        )
        joystick_frame.pack(fill="x", pady=10, padx=15)
        
        joystick_info = """
• The application also supports control via an RC joystick. This allows for more intuitive and precise control of the drone's movements.
• To use the joystick:
  - Connect your joystick to the computer.
  - Ensure that the joystick is recognized by the application.
  - Use the joystick's controls to maneuver the drone in all directions, similar to the keyboard controls.
• The joystick provides a more tactile experience, making it easier to perform complex maneuvers.
        """
        joystick_label = ttk.Label(
            joystick_frame, 
            text=joystick_info, 
            justify="left",
            font=help_content_font
        )
        joystick_label.pack(fill="x")
        
        # Scene Tab Section with enhanced styling
        scene_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Scene Controls", 
            padding=20,
            labelanchor="n"
        )
        scene_frame.pack(fill="x", pady=10, padx=15)  # Increased padding
        
        scene_info = """
• Create Environment: Generates a new disaster simulation environment
• Clear Environment: Removes all objects from the current scene
• Cancel Creating Environment: Stops the environment creation process
• Progress bar shows creation status with category and element counts
        """
        scene_label = ttk.Label(
            scene_frame, 
            text=scene_info, 
            justify="left",
            font=help_content_font
        )
        scene_label.pack(fill="x")
        
        # Config Tab Section with enhanced styling
        config_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Configuration", 
            padding=20,
            labelanchor="n"
        )
        config_frame.pack(fill="x", pady=10, padx=15)  # Increased padding
        
        config_info = """
• Dynamic Objects:
  - Number of Birds: Controls how many birds appear in the scene
  - Bird Movement Speed: Sets how fast birds fly (0.1-5.0)
  - Number of Falling Trees: Sets how many trees will randomly fall
  - Tree Spawn Interval: Time between tree spawns (in seconds)

• Environment Settings:
  - Number of Static Trees: Sets the number of non-falling trees
  - Number of Rocks: Controls how many rock formations appear
  - Number of Bushes: Sets the amount of bush clusters
  - Number of Foliage: Controls ground vegetation density
  - Area Size: Sets the overall simulation area dimensions

• Simulation Settings:
  - Adjust various parameters to customize the simulation behavior
  - Changes are applied when you click "Apply Changes"

• Save/Load Settings:
  - Save your current configuration to a file
  - Load previously saved configurations
        """
        config_label = ttk.Label(
            config_frame, 
            text=config_info, 
            justify="left",
            font=help_content_font
        )
        config_label.pack(fill="x")
        
        # Status Tab Section with enhanced styling
        status_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Status & Victim Detection", 
            padding=20,
            labelanchor="n"
        )
        status_frame.pack(fill="x", pady=10, padx=15)  # Increased padding
        
        status_info = """
• Control Status: Shows whether keyboard controls are active
  - Green: UI control active and ready for keyboard input
  - Red: UI control inactive (click window to activate)

• Victim Detection:
  - Distance: Shows how far the victim is from the drone
  - Elevation: Indicates height difference between drone and victim
  - Direction: Visual indicator showing victim's location
  - Signal Strength: Bar showing signal quality:
    > Green: Strong signal (close proximity)
    > Yellow: Moderate signal
    > Orange: Weak signal
    > Red: Very weak signal (far distance)

• HUD-style radar display shows victim location relative to drone
        """
        status_label = ttk.Label(
            status_frame, 
            text=status_info, 
            justify="left",
            font=help_content_font
        )
        status_label.pack(fill="x")
        
        # Performance Monitor Tab with enhanced styling
        monitor_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Performance Monitoring", 
            padding=20,
            labelanchor="n"
        )
        monitor_frame.pack(fill="x", pady=10, padx=15)  # Increased padding
        
        monitor_info = """
• System Information:
  - Shows OS version, Python version, and CPU core count

• Performance Metrics:
  - FPS: Frames per second of the application
  - Memory Usage: Application memory consumption
  - CPU Usage: Processor utilization
  - Active Threads: Number of running threads

• Simulation Statistics:
  - Total Objects: Count of all objects in the scene
  - Individual counts for birds, trees, rocks, bushes, and foliage

• Runtime Statistics:
  - Uptime: Duration the application has been running
        """
        monitor_label = ttk.Label(
            monitor_frame, 
            text=monitor_info, 
            justify="left",
            font=help_content_font
        )
        monitor_label.pack(fill="x")

        # Dataset Tab with enhanced styling
        dataset_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Dataset Collection", 
            padding=20,
            labelanchor="n"
        )
        dataset_frame.pack(fill="x", pady=10, padx=15)  # Increased padding
        
        dataset_info = """
• Dataset Directory:
  - View current dataset storage location
  - Change the directory where captures are saved

• Dataset Status:
  - View capture statistics and progress
  - Monitor batch saves and total image count
        """
        dataset_label = ttk.Label(
            dataset_frame, 
            text=dataset_info, 
            justify="left",
            font=help_content_font
        )
        dataset_label.pack(fill="x")

        # Logging Tab with enhanced styling
        logging_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Logging Configuration", 
            padding=20,
            labelanchor="n"
        )
        logging_frame.pack(fill="x", pady=(10, 20), padx=15)  # Increased padding
        
        logging_info = """
• Log Level:
  - DEBUG: Shows all messages including detailed debugging
  - INFO: Shows information, warnings, and errors
  - WARNING: Shows only warnings and errors
  - ERROR: Shows only errors
  - CRITICAL: Shows only critical errors

• Debug Verbosity:
  - L1 (Basic): High-level information and important events
  - L2 (Medium): Detailed operations and parameters
  - L3 (Verbose): All events including frequent updates

• File Logging:
  - Enable/disable logging to file
  - Open logs directory to view saved logs

• Verbose Mode:
  - Enable for maximum detail in debugging
        """
        logging_label = ttk.Label(
            logging_frame, 
            text=logging_info, 
            justify="left",
            font=help_content_font
        )
        logging_label.pack(fill="x")
        
        # Keyboard Shortcuts with enhanced styling
        shortcuts_frame = ttk.LabelFrame(
            scrollable_frame, 
            text="Keyboard Shortcuts", 
            padding=20,
            labelanchor="n"
        )
        shortcuts_frame.pack(fill="x", pady=(10, 20), padx=15)  # Increased padding
        
        shortcuts_info = """
• Enter: Apply changes in configuration fields
• Ctrl+S: Save current configuration
• Ctrl+O: Load saved configuration
• Esc: Cancel ongoing operations

• Tab Navigation:
  - Click tabs to switch between different sections
  - Some tabs provide real-time monitoring when selected
        """
        shortcuts_label = ttk.Label(
            shortcuts_frame, 
            text=shortcuts_info, 
            justify="left",
            font=help_content_font
        )
        shortcuts_label.pack(fill="x")
        
        # Add mouse wheel scrolling support
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        # For Linux/macOS (different event)
        canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))
        
        # Update canvas width when window is resized
        def on_resize(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind('<Configure>', on_resize)

    def _save_config(self):
        """Save current configuration to a JSON file"""
        try:
            # Get the current configuration values
            config_to_save = {}
            for key, var in self._config_vars.items():
                if isinstance(var, tk.BooleanVar):
                    config_to_save[key] = var.get()
                else:
                    try:
                        # Try to convert to float if possible
                        config_to_save[key] = float(var.get())
                    except ValueError:
                        # If not a number, save as string
                        config_to_save[key] = var.get()

            # Open file dialog to choose save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Save Configuration"
            )
            
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(config_to_save, f, indent=4)
                self.status_label.configure(text="Configuration saved successfully!")
                self.root.after(2000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.status_label.configure(text=f"Error saving configuration: {str(e)}")
            self.root.after(2000, lambda: self.status_label.configure(text=""))

    def _load_config(self):
        """Load configuration from a JSON file"""
        try:
            # Open file dialog to choose file to load
            file_path = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Load Configuration"
            )
            
            if file_path:
                with open(file_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Update all configuration variables
                for key, value in loaded_config.items():
                    if key in self._config_vars:
                        var = self._config_vars[key]
                        if isinstance(var, tk.BooleanVar):
                            var.set(bool(value))
                        else:
                            var.set(str(value))
                        self._update_config(key, value)
                
                # Apply the changes
                self._apply_all_changes()
                self.status_label.configure(text="Configuration loaded successfully!")
                self.root.after(2000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.status_label.configure(text=f"Error loading configuration: {str(e)}")
            self.root.after(2000, lambda: self.status_label.configure(text=""))

    def _update_performance_metrics(self):
        """Update performance metrics in the UI"""
        try:
            if not hasattr(self, 'root') or not self.root:
                return

            # Calculate current FPS
            current_time = time.time()
            if self._frame_times:
                # Calculate FPS from the most recent frame times
                frame_count = min(len(self._frame_times), 60)  # Use up to 60 frames for calculation
                time_span = current_time - self._frame_times[-min(frame_count, len(self._frame_times))]
                if time_span > 0:
                    fps = frame_count / time_span
                    if hasattr(self, 'fps_var'):
                        self.fps_var.set(f"{fps:.1f} FPS")

            # Update uptime
            uptime = current_time - self._start_time
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            seconds = int(uptime % 60)
            if hasattr(self, 'uptime_var'):
                self.uptime_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

            # Update memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            if hasattr(self, 'mem_var'):
                self.mem_var.set(f"{memory_mb:.1f} MB")
                
            # Update memory percentage
            mem_percent = psutil.virtual_memory().percent
            if hasattr(self, 'mem_percent_var'):
                self.mem_percent_var.set(f"{mem_percent:.1f}%")

            # Get CPU usage (this is percentage of a single core)
            cpu_percent = psutil.cpu_percent(interval=None)
            if hasattr(self, 'cpu_usage_var'):
                self.cpu_usage_var.set(f"{cpu_percent:.1f}%")
                
            # Get CPU frequency
            try:
                cpu_freq = psutil.cpu_freq().current
                if hasattr(self, 'cpu_freq_var'):
                    self.cpu_freq_var.set(f"{cpu_freq:.0f} MHz")
            except Exception:
                if hasattr(self, 'cpu_freq_var'):
                    self.cpu_freq_var.set("N/A")
                    
            # Get thread count
            thread_count = threading.active_count()
            if hasattr(self, 'thread_var'):
                self.thread_var.set(str(thread_count))

            # Update simulation statistics
            self._update_simulation_stats()

            # Don't schedule here - scheduling is handled by _schedule_ui_update
        except Exception as e:
            self.logger.error("MenuSystem", f"Error updating performance metrics: {e}")

    def _update_simulation_stats(self):
        """Update simulation statistics based on current config"""
        try:
            # Get values from config
            num_birds = self.config.get("num_birds", 0)
            num_trees = self.config.get("num_trees", 0)
            num_rocks = self.config.get("num_rocks", 0)
            num_bushes = self.config.get("num_bushes", 0)
            num_foliage = self.config.get("num_foliage", 0)
            
            # Update individual counts
            self.birds_var.set(str(num_birds))
            self.trees_var.set(str(num_trees))
            self.rocks_var.set(str(num_rocks))
            self.bushes_var.set(str(num_bushes))
            self.foliage_var.set(str(num_foliage))
            
            # Update total count
            total_objects = num_birds + num_trees + num_rocks + num_bushes + num_foliage
            self.obj_var.set(str(total_objects))
        except Exception:
            self.obj_var.set("N/A")
            self.birds_var.set("N/A")
            self.trees_var.set("N/A")
            self.rocks_var.set("N/A")
            self.bushes_var.set("N/A")
            self.foliage_var.set("N/A")

    def _build_performance_tab(self, parent):
        """Build the performance monitoring tab"""
        # Title
        ttk.Label(parent, text="Performance Monitoring", style="Title.TLabel").pack(pady=(0,20))
        
        # Monitoring Toggle
        toggle_frame = ttk.Frame(parent)
        toggle_frame.pack(fill="x", pady=(0, 10))
        
        # Create the toggle button
        self.monitoring_var = tk.BooleanVar(value=self.config.get("enable_performance_monitoring", False))
        toggle_btn = ttk.Checkbutton(toggle_frame, 
                                   text="Enable Performance Monitoring",
                                   variable=self.monitoring_var,
                                   command=self._toggle_monitoring)
        toggle_btn.pack(side="left", padx=5)
        
        # Create a simple frame instead of scrollable canvas
        scrollable_frame = ttk.Frame(parent)
        scrollable_frame.pack(fill="both", expand=True, padx=5)
        
        # System Information Section
        sys_frame = ttk.LabelFrame(scrollable_frame, text="System Information", padding=15, labelanchor="n")
        sys_frame.pack(fill="x", pady=10, padx=5)
        
        # OS Info
        os_frame = ttk.Frame(sys_frame)
        os_frame.pack(fill="x", pady=2)
        ttk.Label(os_frame, text="Operating System:", width=25, style="TLabel").pack(side="left")
        self.os_var = tk.StringVar(value=platform.system() + " " + platform.release())
        ttk.Label(os_frame, textvariable=self.os_var, style="TLabel").pack(side="left")
        
        # Python Version
        py_frame = ttk.Frame(sys_frame)
        py_frame.pack(fill="x", pady=2)
        ttk.Label(py_frame, text="Python Version:", width=25, style="TLabel").pack(side="left")
        self.py_var = tk.StringVar(value=platform.python_version())
        ttk.Label(py_frame, textvariable=self.py_var, style="TLabel").pack(side="left")
        
        # CPU Info
        cpu_info_frame = ttk.Frame(sys_frame)
        cpu_info_frame.pack(fill="x", pady=2)
        ttk.Label(cpu_info_frame, text="CPU Cores:", width=25, style="TLabel").pack(side="left")
        self.cpu_cores_var = tk.StringVar(value=str(psutil.cpu_count()))
        ttk.Label(cpu_info_frame, textvariable=self.cpu_cores_var, style="TLabel").pack(side="left")
        
        # Performance Metrics Section
        perf_frame = ttk.LabelFrame(scrollable_frame, text="Performance Metrics", padding=15, labelanchor="n")
        perf_frame.pack(fill="x", pady=10, padx=5)
        
        # FPS counter
        fps_frame = ttk.Frame(perf_frame)
        fps_frame.pack(fill="x", pady=2)
        ttk.Label(fps_frame, text="FPS:", width=25, style="TLabel").pack(side="left")
        self.fps_var = tk.StringVar(value="0.0")
        ttk.Label(fps_frame, textvariable=self.fps_var, style="TLabel").pack(side="left")
        
        # Memory usage
        mem_frame = ttk.Frame(perf_frame)
        mem_frame.pack(fill="x", pady=2)
        ttk.Label(mem_frame, text="Memory Usage:", width=25, style="TLabel").pack(side="left")
        self.mem_var = tk.StringVar(value="0 MB")
        ttk.Label(mem_frame, textvariable=self.mem_var, style="TLabel").pack(side="left")
        
        # Memory percentage
        mem_percent_frame = ttk.Frame(perf_frame)
        mem_percent_frame.pack(fill="x", pady=2)
        ttk.Label(mem_percent_frame, text="Memory %:", width=25, style="TLabel").pack(side="left")
        self.mem_percent_var = tk.StringVar(value="0%")
        ttk.Label(mem_percent_frame, textvariable=self.mem_percent_var, style="TLabel").pack(side="left")
        
        # CPU usage
        cpu_frame = ttk.Frame(perf_frame)
        cpu_frame.pack(fill="x", pady=2)
        ttk.Label(cpu_frame, text="CPU Usage:", width=25, style="TLabel").pack(side="left")
        self.cpu_usage_var = tk.StringVar(value="0%")
        ttk.Label(cpu_frame, textvariable=self.cpu_usage_var, style="TLabel").pack(side="left")
        
        # CPU frequency
        cpu_freq_frame = ttk.Frame(perf_frame)
        cpu_freq_frame.pack(fill="x", pady=2)
        ttk.Label(cpu_freq_frame, text="CPU Frequency:", width=25, style="TLabel").pack(side="left")
        self.cpu_freq_var = tk.StringVar(value="N/A")
        ttk.Label(cpu_freq_frame, textvariable=self.cpu_freq_var, style="TLabel").pack(side="left")
        
        # Thread count
        thread_frame = ttk.Frame(perf_frame)
        thread_frame.pack(fill="x", pady=2)
        ttk.Label(thread_frame, text="Active Threads:", width=25, style="TLabel").pack(side="left")
        self.thread_var = tk.StringVar(value="0")
        ttk.Label(thread_frame, textvariable=self.thread_var, style="TLabel").pack(side="left")
        
        # Simulation Statistics Section
        sim_frame = ttk.LabelFrame(scrollable_frame, text="Simulation Statistics", padding=15, labelanchor="n")
        sim_frame.pack(fill="x", pady=10, padx=5)
        
        # Scene objects
        obj_frame = ttk.Frame(sim_frame)
        obj_frame.pack(fill="x", pady=2)
        ttk.Label(obj_frame, text="Total Objects:", width=25, style="TLabel").pack(side="left")
        self.obj_var = tk.StringVar(value="0")
        ttk.Label(obj_frame, textvariable=self.obj_var, style="TLabel").pack(side="left")
        
        # Birds count
        birds_frame = ttk.Frame(sim_frame)
        birds_frame.pack(fill="x", pady=2)
        ttk.Label(birds_frame, text="Birds:", width=25, style="TLabel").pack(side="left")
        self.birds_var = tk.StringVar(value="0")
        ttk.Label(birds_frame, textvariable=self.birds_var, style="TLabel").pack(side="left")
        
        # Trees count
        trees_frame = ttk.Frame(sim_frame)
        trees_frame.pack(fill="x", pady=2)
        ttk.Label(trees_frame, text="Trees:", width=25, style="TLabel").pack(side="left")
        self.trees_var = tk.StringVar(value="0")
        ttk.Label(trees_frame, textvariable=self.trees_var, style="TLabel").pack(side="left")
        
        # Rocks count
        rocks_frame = ttk.Frame(sim_frame)
        rocks_frame.pack(fill="x", pady=2)
        ttk.Label(rocks_frame, text="Rocks:", width=25, style="TLabel").pack(side="left")
        self.rocks_var = tk.StringVar(value="0")
        ttk.Label(rocks_frame, textvariable=self.rocks_var, style="TLabel").pack(side="left")
        
        # Bushes count
        bushes_frame = ttk.Frame(sim_frame)
        bushes_frame.pack(fill="x", pady=2)
        ttk.Label(bushes_frame, text="Bushes:", width=25, style="TLabel").pack(side="left")
        self.bushes_var = tk.StringVar(value="0")
        ttk.Label(bushes_frame, textvariable=self.bushes_var, style="TLabel").pack(side="left")
        
        # Foliage count
        foliage_frame = ttk.Frame(sim_frame)
        foliage_frame.pack(fill="x", pady=2)
        ttk.Label(foliage_frame, text="Foliage:", width=25, style="TLabel").pack(side="left")
        self.foliage_var = tk.StringVar(value="0")
        ttk.Label(foliage_frame, textvariable=self.foliage_var, style="TLabel").pack(side="left")
        
        # Runtime Statistics Section
        runtime_frame = ttk.LabelFrame(scrollable_frame, text="Runtime Statistics", padding=15, labelanchor="n")
        runtime_frame.pack(fill="x", pady=10, padx=5)
        
        # Uptime
        uptime_frame = ttk.Frame(runtime_frame)
        uptime_frame.pack(fill="x", pady=2)
        ttk.Label(uptime_frame, text="Uptime:", width=25, style="TLabel").pack(side="left")
        self.uptime_var = tk.StringVar(value="00:00:00")
        ttk.Label(uptime_frame, textvariable=self.uptime_var, style="TLabel").pack(side="left")
        
        # Start performance monitoring
        self._schedule_ui_update()

    def _clear_performance_metrics(self):
        """Clear all performance metrics when monitoring is disabled"""
        self.fps_var.set("N/A")
        self.mem_var.set("N/A")
        self.mem_percent_var.set("N/A")
        self.cpu_usage_var.set("N/A")
        self.cpu_freq_var.set("N/A")
        self.thread_var.set("N/A")
        self._frame_times = []

    def _toggle_monitoring(self):
        """Handle monitoring toggle button click"""
        is_enabled = self.monitoring_var.get()
        self.config["enable_performance_monitoring"] = is_enabled
        
        if is_enabled:
            self._schedule_ui_update()
        else:
            if self._monitoring_after_id:
                self.root.after_cancel(self._monitoring_after_id)
                self._monitoring_after_id = None
            self._monitoring_active = False
            self._clear_performance_metrics()
            self._last_ui_update = 0
            self._last_fps_update = 0

    def run(self):
        """Run the UI main loop"""
        self.logger.info("MenuSystem", "Starting UI main loop")
        self.root.mainloop()
        
    def cleanup(self, data=None):
        """Perform cleanup before application exit"""
        # Perform cleanup tasks
        self.logger.info("MenuSystem", "Performing cleanup tasks...")
        
        # Cancel any pending scheduled tasks
        if hasattr(self, '_monitoring_after_id') and self._monitoring_after_id:
            try:
                self.root.after_cancel(self._monitoring_after_id)
                self._monitoring_after_id = None
            except Exception as e:
                self.logger.error("MenuSystem", f"Error cleaning up monitoring after task: {e}")
        
        # Cancel movement update schedule
        try:
            # Get all "after" ids and cancel them
            for after_id in self.root.tk.call('after', 'info'):
                try:
                    self.root.after_cancel(after_id)
                except Exception as e:
                    self.logger.debug("MenuSystem", f"Error canceling after task {after_id}: {e}")
        except Exception as e:
            self.logger.error("MenuSystem", f"Error cleaning up after tasks: {e}")
        
        # Clear any pressed keys and stop movement
        self._ui_pressed_keys.clear()
        try:
            # Explicitly stop all movement by publishing zero values
            EM.publish('keyboard/move', (0.0, 0.0, 0.0))
            EM.publish('keyboard/rotate', 0.0)
        except Exception as e:
            self.logger.error("MenuSystem", f"Error stopping movement: {e}")
        
        # Clean up RC settings if they exist
        if hasattr(self, 'rc_settings') and self.rc_settings:
            try:
                self.rc_settings.destroy()
            except Exception as e:
                self.logger.error("MenuSystem", f"Error cleaning up RC settings: {e}")
        
        # Unsubscribe from events
        EM.unsubscribe('scene/progress', self._on_scene_progress)
        EM.unsubscribe('scene/completed', self._on_scene_completed)
        EM.unsubscribe('scene/canceled', self._on_scene_canceled)
        EM.unsubscribe('scene/request_creation', self._on_scene_creation_request)
        EM.unsubscribe('victim/detected', self._update_victim_indicator)
        EM.unsubscribe('simulation/frame', self._on_simulation_frame)
        EM.unsubscribe('config/updated', self._on_config_updated_gui)
        EM.unsubscribe('dataset/batch_saved', self._on_batch_saved)
        EM.unsubscribe('dataset/config_updated', self._on_dataset_config_updated)
        EM.unsubscribe('dataset/status_update', self._force_ui_update)
        
        self.logger.info("MenuSystem", "Cleanup complete - all events unsubscribed")

    def _build_dataset_tab(self, parent):
        """Build the dataset tab for configuring dataset collection"""
        # Title with modern styling
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill="x", pady=(0, 20))
        ttk.Label(title_frame, text="Dataset Configuration", style="Title.TLabel").pack()
        
        # Directory Selection Section
        dir_frame = ttk.LabelFrame(parent, text="Dataset Directory", padding=15, labelanchor="n")
        dir_frame.pack(fill="x", pady=10, padx=5)
        
        # Current Directory Display
        current_dir_frame = ttk.Frame(dir_frame)
        current_dir_frame.pack(fill="x", pady=5)
        ttk.Label(current_dir_frame, text="Current Directory:", width=20).pack(side="left", padx=(0, 10))
        
        # Dataset directory variable
        self.dataset_dir_var = tk.StringVar(value="data/depth_dataset")
        dir_label = ttk.Label(current_dir_frame, textvariable=self.dataset_dir_var, 
                            font=("Segoe UI", 10, "italic"))
        dir_label.pack(side="left", fill="x", expand=True)
        
        # Directory Selection Button
        select_dir_frame = ttk.Frame(dir_frame)
        select_dir_frame.pack(fill="x", pady=5)
        
        # Directory Selection Button
        select_dir_btn = ttk.Button(select_dir_frame, 
                                 text="Select Directory", 
                                 command=self._select_dataset_directory)
        select_dir_btn.pack(fill="x")
        
        # Subscribe to dataset events - keep only those we still need
        EM.subscribe('dataset/batch/saved', self._on_batch_saved)
        EM.subscribe('dataset/config/updated', self._on_dataset_config_updated)
    
    def _select_dataset_directory(self):
        """Select a directory for dataset storage"""
        try:
            directory = filedialog.askdirectory(
                title="Select Dataset Directory",
                initialdir="data/depth_dataset"
            )
            
            if directory:
                self.logger.debug_at_level(DEBUG_L1, "MenuSystem", f"Selected dataset directory: {directory}")
                
                # Get depth collector
                depth_collector = SC.get_depth_collector()
                if not depth_collector:
                    self.logger.warning("MenuSystem", "No depth collector available. Please create a scene first.")
                    self.status_label.configure(text="No depth collector available. Please create a scene first.")
                    self.root.after(3000, lambda: self.status_label.configure(text=""))
                    return
                    
                # Set new base folder
                depth_collector.set_base_folder(directory)
                
                # Update the UI
                self.dataset_dir_var.set(directory)
                self.status_label.configure(text=f"Dataset directory set to: {directory}")
                self.root.after(3000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.logger.error("MenuSystem", f"Error setting dataset directory: {e}")
            self.status_label.configure(text=f"Error: {str(e)}")
            self.root.after(3000, lambda: self.status_label.configure(text=""))
    
    def _safe_ui_update(self, function):
        """Safely update the UI from any thread"""
        if not hasattr(self, 'root') or not self.root:
            self.logger.warning("MenuSystem", "Cannot update UI - window no longer exists")
            return
            
        # If we're in the main thread, just execute the function
        if threading.current_thread() is threading.main_thread():
            try:
                function()
            except tk.TclError as e:
                if "main thread is not in main loop" in str(e):
                    self.logger.warning("MenuSystem", "Cannot update UI - main thread is not in main loop")
                else:
                    self.logger.error("MenuSystem", f"Tkinter error in UI update: {e}")
            except Exception as e:
                self.logger.error("MenuSystem", f"Error in UI update: {e}")
        else:
            # We're in a background thread, schedule the update on the main thread
            try:
                # Only schedule if the root window exists and is in mainloop
                if hasattr(self, 'root') and self.root.winfo_exists():
                    # Use after(0) instead of after_idle for more reliable execution
                    self.root.after(0, function)
                else:
                    self.logger.warning("MenuSystem", "Cannot schedule UI update - window no longer exists or mainloop not running")
            except tk.TclError as e:
                # If we get an error about main thread not in main loop, 
                # we'll ignore it as it's expected from background threads
                if "main thread is not in main loop" not in str(e):
                    self.logger.error("MenuSystem", f"Error scheduling UI update: {e}")
            except Exception as e:
                self.logger.error("MenuSystem", f"Error scheduling UI update: {e}")

    def _on_batch_saved(self, data):
        """Handle batch saved event"""
        # Check if UI is still active before attempting update
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        
        # Extract relevant data safely
        batch_id = data.get('batch_id', 0)
        count = data.get('count', 0)
        total_saved = data.get('total_saved', 0)
        is_bg_thread = data.get('is_background_thread', False)
        
        def update_ui():
            try:
                if hasattr(self, 'dataset_status_label'):
                    self.dataset_status_label.config(
                        text=f"Saved batch {batch_id} ({count} images)"
                    )
                
                if hasattr(self, 'dataset_stats_label'):
                    self.dataset_stats_label.config(
                        text=f"Total: {total_saved} images"
                    )
            except Exception as e:
                # Don't log TclError about main thread, as these are expected
                if not isinstance(e, tk.TclError) or "main thread is not in main loop" not in str(e):
                    self.logger.error("MenuSystem", f"Error updating batch save status: {e}")
        
        # Handle differently based on thread
        if is_bg_thread:
            try:
                # For background threads, only attempt if root exists and use idletasks
                if hasattr(self, 'root') and self.root.winfo_exists():
                    # Schedule with a longer delay to avoid threading issues
                    self.root.after(500, update_ui)
            except Exception as e:
                # Completely ignore main thread errors - these are expected from background threads
                pass
        else:
            # Use normal update for main thread
            try:
                self._safe_ui_update(update_ui)
            except Exception as e:
                # Silently ignore errors from UI updates
                pass

    def _on_dataset_config_updated(self, data):
        """Handle dataset config updated event"""
        # Check if UI is still active before attempting update
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
            
        def update_ui():
            try:
                if hasattr(self, 'dataset_dir_label'):
                    self.dataset_dir_label.config(
                        text=f"Directory: {data['base_folder']}"
                    )
            except Exception as e:
                self.logger.error("MenuSystem", f"Error updating dataset directory display: {e}")
        
        self._safe_ui_update(update_ui)

    def _build_logging_tab(self, parent):
        """Build the logging configuration tab."""
        # Create a canvas with scrollbar for better organization
        canvas = tk.Canvas(parent, bg="#1a1a1a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure the canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create a window in the canvas to hold the scrollable frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the scrollbar and canvas with padding
        scrollbar.pack(side="right", fill="y", padx=(5, 0))
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Title
        title_label = ttk.Label(
            scrollable_frame, 
            text="Logging Configuration", 
            style="Title.TLabel"
        )
        title_label.pack(pady=(0, 20))
        
        # Log Level selection section
        log_level_frame = ttk.LabelFrame(scrollable_frame, text="Log Level", labelanchor="n", padding=15)
        log_level_frame.pack(fill="x", padx=5, pady=10)
        
        log_level_content = ttk.Frame(log_level_frame)
        log_level_content.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(log_level_content, text="Select log level:").pack(side="left", padx=(0, 10))
        
        # Create the dropdown for log levels
        self.log_level_var = tk.StringVar(value="INFO")
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_dropdown = ttk.Combobox(
            log_level_content, 
            textvariable=self.log_level_var, 
            values=log_levels, 
            state="readonly",
            width=10
        )
        level_dropdown.pack(side="left", padx=5)
        
        # Button to apply the log level change
        apply_level_btn = ttk.Button(
            log_level_content, 
            text="Apply", 
            command=self._change_log_level,
            style="Apply.TButton"
        )
        apply_level_btn.pack(side="left", padx=10)
        
        # Current log level display
        self.current_level_label = ttk.Label(log_level_content, text="Current: INFO")
        self.current_level_label.pack(side="right", padx=10)
        
        # Debug Level selection section
        debug_level_frame = ttk.LabelFrame(scrollable_frame, text="Debug Verbosity", labelanchor="n", padding=15)
        debug_level_frame.pack(fill="x", padx=5, pady=10)
        
        debug_level_content = ttk.Frame(debug_level_frame)
        debug_level_content.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(debug_level_content, text="Select debug verbosity:").pack(anchor="w", pady=(0, 5))
        
        # Description of debug levels
        debug_desc_frame = ttk.Frame(debug_level_content)
        debug_desc_frame.pack(fill="x", pady=5)
        
        ttk.Label(debug_desc_frame, text="L1 - Basic: High-level info and important events").pack(anchor="w")
        ttk.Label(debug_desc_frame, text="L2 - Medium: Detailed operations and parameters").pack(anchor="w")
        ttk.Label(debug_desc_frame, text="L3 - Verbose: All events including frequent updates").pack(anchor="w")
        
        # Debug level radio buttons
        debug_selection_frame = ttk.Frame(debug_level_content)
        debug_selection_frame.pack(fill="x", pady=10)
        
        self.debug_level_var = tk.IntVar(value=1)
        debug_levels = [(1, "L1 (Basic)"), (2, "L2 (Medium)"), (3, "L3 (Verbose)")]
        
        for level, text in debug_levels:
            rb = ttk.Radiobutton(
                debug_selection_frame, 
                text=text, 
                variable=self.debug_level_var, 
                value=level
            )
            rb.pack(side="left", padx=10)
        
        # Apply debug level button
        apply_debug_btn = ttk.Button(
            debug_level_content, 
            text="Apply Debug Level", 
            command=self._change_debug_level,
            style="Apply.TButton"
        )
        apply_debug_btn.pack(pady=10)
        
        # Current debug level display
        self.current_debug_label = ttk.Label(debug_level_content, text="Current: L1 (Basic)")
        self.current_debug_label.pack(pady=5)
        
        # File Logging section
        file_logging_frame = ttk.LabelFrame(scrollable_frame, text="File Logging", labelanchor="n", padding=15)
        file_logging_frame.pack(fill="x", padx=5, pady=10)
        
        file_logging_content = ttk.Frame(file_logging_frame)
        file_logging_content.pack(fill="x", padx=10, pady=10)
        
        # File logging toggle
        self.file_logging_var = tk.BooleanVar(value=False)
        file_logging_chk = ttk.Checkbutton(
            file_logging_content, 
            text="Enable File Logging", 
            variable=self.file_logging_var
        )
        file_logging_chk.pack(anchor="w", pady=5)
        
        # Logs directory display
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
        logs_dir_frame = ttk.Frame(file_logging_content)
        logs_dir_frame.pack(fill="x", pady=5)
        
        ttk.Label(logs_dir_frame, text="Logs directory:").pack(side="left", padx=(0, 5))
        self.logs_dir_label = ttk.Label(logs_dir_frame, text=logs_dir)
        self.logs_dir_label.pack(side="left", padx=5)
        
        # Apply file logging button
        apply_file_logging_btn = ttk.Button(
            file_logging_content, 
            text="Apply File Logging Setting", 
            command=self._toggle_file_logging,
            style="Apply.TButton"
        )
        apply_file_logging_btn.pack(pady=10)
        
        # Logging status display
        self.file_logging_status = ttk.Label(
            file_logging_content, 
            text="File logging is currently disabled"
        )
        self.file_logging_status.pack(pady=5)
        
        # Open logs directory button
        open_logs_btn = ttk.Button(
            file_logging_content, 
            text="Open Logs Directory", 
            command=self._open_logs_directory
        )
        open_logs_btn.pack(pady=10)
        
        # Verbose mode section
        verbose_frame = ttk.LabelFrame(scrollable_frame, text="Verbose Mode", labelanchor="n", padding=15)
        verbose_frame.pack(fill="x", padx=5, pady=10)
        
        verbose_content = ttk.Frame(verbose_frame)
        verbose_content.pack(fill="x", padx=10, pady=10)
        
        # Verbose mode toggle
        self.verbose_var = tk.BooleanVar(value=False)
        verbose_chk = ttk.Checkbutton(
            verbose_content, 
            text="Enable Verbose Logging", 
            variable=self.verbose_var
        )
        verbose_chk.pack(anchor="w", pady=5)
        
        # Description of verbose mode
        ttk.Label(
            verbose_content, 
            text="Verbose mode enables detailed logging at DEBUG level with all debug messages",
            wraplength=500
        ).pack(pady=5)
        
        # Apply verbose mode button
        apply_verbose_btn = ttk.Button(
            verbose_content, 
            text="Apply Verbose Setting", 
            command=self._toggle_verbose_mode,
            style="Apply.TButton"
        )
        apply_verbose_btn.pack(pady=10)
        
        # Update canvas width when window is resized
        def on_resize(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind('<Configure>', on_resize)
        
        # Add mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        # For Linux/macOS (different event)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        
        # Update the current settings
        self._update_logging_status()
    
    def _update_logging_status(self):
        """Update the logging status labels based on current settings."""
        # This function is called from the main thread UI handlers
        try:
            # Get instance from the actual Logger class
            from Utils.log_utils import get_logger
            logger_instance = get_logger()
            
            # Debug logging for diagnostics
            self.logger.info("MenuSystem", f"Logger type: {type(logger_instance).__name__}")
            
            # Get console handler level - the fork uses console_handler property
            if hasattr(logger_instance, 'console_handler') and hasattr(logger_instance.console_handler, 'level'):
                level = logger_instance.console_handler.level
                self.logger.info("MenuSystem", f"Console handler level: {level}")
                
                # Use the logger's own _level_to_name method if available
                if hasattr(logger_instance, '_level_to_name') and callable(logger_instance._level_to_name):
                    level_name = logger_instance._level_to_name(level)
                else:
                    level_name = self._level_to_name(level)
                    
                self.logger.info("MenuSystem", f"Level name: {level_name}")
                self.current_level_label.config(text=f"Current: {level_name}")
                self.log_level_var.set(level_name)
            else:
                self.logger.warning("MenuSystem", "Could not access console_handler.level")
                self.current_level_label.config(text="Current: Unknown")
                self.log_level_var.set("INFO")  # Default fallback
            
            # Update debug level label
            if hasattr(logger_instance, 'current_debug_level'):
                debug_level = logger_instance.current_debug_level
                self.logger.info("MenuSystem", f"Debug level: {debug_level}")
                debug_names = {1: "L1 (Basic)", 2: "L2 (Medium)", 3: "L3 (Verbose)"}
                self.current_debug_label.config(text=f"Current: {debug_names.get(debug_level, 'Unknown')}")
                self.debug_level_var.set(debug_level)
            else:
                self.logger.warning("MenuSystem", "Could not access current_debug_level")
                self.current_debug_label.config(text="Current: L1 (Basic)")
                self.debug_level_var.set(1)  # Default fallback
            
            # Update file logging status
            has_file_logging = hasattr(logger_instance, 'file_handler') and logger_instance.file_handler is not None
            self.file_logging_var.set(has_file_logging)
            
            if has_file_logging and hasattr(logger_instance.file_handler, 'baseFilename'):
                log_file = logger_instance.file_handler.baseFilename
                self.file_logging_status.config(text=f"File logging enabled: {os.path.basename(log_file)}")
            else:
                self.file_logging_status.config(text="File logging is currently disabled")
            
            # Update verbose mode status
            if hasattr(logger_instance, 'verbose'):
                self.verbose_var.set(logger_instance.verbose)
            else:
                self.verbose_var.set(False)  # Default fallback
                
        except Exception as e:
            self.logger.error("MenuSystem", f"Error updating logging status: {e}")
            self.status_label.configure(text=f"Error updating logging status: {str(e)}")
            self.root.after(2000, lambda: self.status_label.configure(text=""))
    
    def _change_debug_level(self):
        """Change the debug verbosity level from the UI."""
        try:
            level = self.debug_level_var.get()
            self.logger.info("MenuSystem", f"Changing debug level to: {level}")
            
            if level in [DEBUG_L1, DEBUG_L2, DEBUG_L3]:
                # Get instance from the actual Logger class
                from Utils.log_utils import get_logger
                logger_instance = get_logger()
                
                # Use the set_debug_level method
                logger_instance.set_debug_level(level)
                
                level_names = {DEBUG_L1: "Basic", DEBUG_L2: "Medium", DEBUG_L3: "Verbose"}
                self.logger.info("MenuSystem", f"Debug level changed to L{level} ({level_names[level]})")
                
                # Update UI immediately since we're in the main thread
                self._update_logging_status()
                self.status_label.configure(text=f"Debug level changed to L{level} ({level_names[level]})")
                self.root.after(2000, lambda: self.status_label.configure(text=""))
            else:
                self.logger.error("MenuSystem", f"Invalid debug level: {level}")
                self.status_label.configure(text=f"Error: Invalid debug level")
                self.root.after(2000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.logger.error("MenuSystem", f"Error changing debug level: {e}")
            self.status_label.configure(text=f"Error changing debug level: {str(e)}")
            self.root.after(2000, lambda: self.status_label.configure(text=""))
    
    def _toggle_file_logging(self):
        """Toggle file logging on or off from the UI."""
        # This already runs in the main thread, so no need for _safe_ui_update
        try:
            enabled = self.file_logging_var.get()
            self.logger.info("MenuSystem", f"Setting file logging to: {enabled}")
            
            # Get instance from the actual Logger class
            from Utils.log_utils import get_logger
            logger_instance = get_logger()
            
            if enabled:
                # Create logs directory if it doesn't exist
                logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
                os.makedirs(logs_dir, exist_ok=True)
                
                # Generate filename with timestamp
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"disaster_sim_{timestamp}.log"
                
                # Configure file logging
                logger_instance.configure_file_logging(enabled=True, level=LOG_LEVEL_DEBUG, filename=filename)
                self.logger.info("MenuSystem", f"File logging enabled: {filename}")
                self.status_label.configure(text=f"File logging enabled: {filename}")
            else:
                logger_instance.configure_file_logging(enabled=False)
                self.logger.info("MenuSystem", "File logging disabled")
                self.status_label.configure(text="File logging disabled")
                
            # Update UI immediately since we're in the main thread
            self._update_logging_status()
            self.root.after(3000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.logger.error("MenuSystem", f"Error configuring file logging: {e}")
            self.status_label.configure(text=f"Error: {str(e)}")
            self.root.after(3000, lambda: self.status_label.configure(text=""))
            
    def _toggle_verbose_mode(self):
        """Toggle verbose mode on or off from the UI."""
        try:
            verbose = self.verbose_var.get()
            self.logger.info("MenuSystem", f"Setting verbose mode to: {verbose}")
            
            # Get instance from the actual Logger class
            from Utils.log_utils import get_logger
            logger_instance = get_logger()
            
            # Configure logger with new verbose setting
            console_level = LOG_LEVEL_DEBUG if verbose else LOG_LEVEL_INFO
            debug_level = self.debug_level_var.get()
            
            logger_instance.configure(
                verbose=verbose,
                console_level=console_level,
                debug_level=debug_level,
                colored_output=True
            )
            
            # Show appropriate message
            message = "Verbose mode enabled" if verbose else "Verbose mode disabled"
            self.logger.info("MenuSystem", message)
            self.status_label.configure(text=message)
            
            # Update UI immediately since we're in the main thread
            self._update_logging_status()
            self.root.after(2000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.logger.error("MenuSystem", f"Error setting verbose mode: {e}")
            self.status_label.configure(text=f"Error: {str(e)}")
            self.root.after(2000, lambda: self.status_label.configure(text=""))
    
    def _open_logs_directory(self):
        """Open the logs directory in the file explorer."""
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        try:
            if platform.system() == "Windows":
                os.startfile(logs_dir)
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                subprocess.call(["open", logs_dir])
            else:  # Linux
                import subprocess
                subprocess.call(["xdg-open", logs_dir])
        except Exception as e:
            self.logger.error("MenuSystem", f"Error opening logs directory: {e}")

    def _change_log_level(self):
        """Change the logging level from the UI."""
        # This runs in the main thread, so no need for _safe_ui_update
        try:
            level_str = self.log_level_var.get()
            self.logger.info("MenuSystem", f"Trying to change log level to: {level_str}")
            
            # Map level names to standard Python logging levels
            level_map = {
                "DEBUG": LOG_LEVEL_DEBUG,
                "INFO": LOG_LEVEL_INFO,
                "WARNING": LOG_LEVEL_WARNING,
                "ERROR": LOG_LEVEL_ERROR,
                "CRITICAL": LOG_LEVEL_CRITICAL
            }
            
            if level_str in level_map:
                level = level_map[level_str]
                self.logger.info("MenuSystem", f"Mapped level name {level_str} to value {level}")
                
                # Get the logger instance directly to ensure we're using the right object
                from Utils.log_utils import get_logger
                logger_instance = get_logger()
                
                try:
                    # Use the proper set_level method
                    logger_instance.set_level(level)
                    self.logger.info("MenuSystem", f"Log level changed to {level_str}")
                    
                    # Generate a test message at the selected level to verify the change
                    if level_str == "DEBUG":
                        logger_instance.debug("MenuSystem", f"TEST: This is a DEBUG message")
                    elif level_str == "INFO":
                        logger_instance.info("MenuSystem", f"TEST: This is an INFO message")
                    elif level_str == "WARNING":
                        logger_instance.warning("MenuSystem", f"TEST: This is a WARNING message")
                    elif level_str == "ERROR":
                        logger_instance.error("MenuSystem", f"TEST: This is an ERROR message")
                    elif level_str == "CRITICAL":
                        logger_instance.critical("MenuSystem", f"TEST: This is a CRITICAL message")
                    
                    # Update UI immediately since we're in the main thread
                    self._update_logging_status()
                    self.status_label.configure(text=f"Log level changed to {level_str} (test message sent)")
                    self.root.after(2000, lambda: self.status_label.configure(text=""))
                except Exception as e:
                    self.logger.error("MenuSystem", f"Error setting log level: {e}")
                    self.status_label.configure(text=f"Error: {str(e)}")
                    self.root.after(2000, lambda: self.status_label.configure(text=""))
            else:
                self.logger.error("MenuSystem", f"Invalid log level: {level_str}")
                self.status_label.configure(text=f"Error: Invalid log level")
                self.root.after(2000, lambda: self.status_label.configure(text=""))
        except Exception as e:
            self.logger.error("MenuSystem", f"Error changing log level: {e}")
            self.status_label.configure(text=f"Error changing log level: {str(e)}")
            self.root.after(2000, lambda: self.status_label.configure(text=""))

    def _level_to_name(self, level):
        """Convert logging level integer to name."""
        try:
            # Log the level we're trying to convert for debugging
            self.logger.info("MenuSystem", f"Converting level value: {level} (type: {type(level).__name__})")
            
            # Handle the case when level is 0
            if level == 0:
                self.logger.warning("MenuSystem", "Received level 0, defaulting to INFO")
                return "INFO"
                
            # Standard logging levels
            if level == LOG_LEVEL_DEBUG:
                return "DEBUG"
            elif level == LOG_LEVEL_INFO:
                return "INFO"
            elif level == LOG_LEVEL_WARNING:
                return "WARNING"
            elif level == LOG_LEVEL_ERROR:
                return "ERROR"
            elif level == LOG_LEVEL_CRITICAL:
                return "CRITICAL"
            
            # Handle other common level values that might be used
            elif level == 10:  # Common value for DEBUG
                return "DEBUG"
            elif level == 20:  # Common value for INFO
                return "INFO"
            elif level == 30:  # Common value for WARNING
                return "WARNING"
            elif level == 40:  # Common value for ERROR
                return "ERROR"
            elif level == 50:  # Common value for CRITICAL
                return "CRITICAL"
            else:
                self.logger.warning("MenuSystem", f"Unknown log level value: {level}")
                return f"UNKNOWN ({level})"
        except Exception as e:
            self.logger.error("MenuSystem", f"Error converting log level to name: {e}")
            return "UNKNOWN"

    def _build_controls_tab(self, parent):
        """Build the controls tab with controller settings"""
        # Title with modern styling
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill="x", pady=(0, 20))
        ttk.Label(title_frame, text="Controller Settings", style="Title.TLabel").pack()
        
        # Create a canvas with scrollbar for the controls options - set proper background color
        canvas = tk.Canvas(parent, bg="#1a1a1a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="TFrame")  # Use themed frame

        # Configure the canvas
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create a window in the canvas to hold the scrollable frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the scrollbar and canvas with padding
        scrollbar.pack(side="right", fill="y", padx=(5, 0))  # Add padding on the left of scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))  # Add padding on the right of canvas
        
        # Keyboard Controls Section
        keyboard_frame = ttk.LabelFrame(scrollable_frame, text="Keyboard Controls", padding=15, labelanchor="n")
        keyboard_frame.pack(fill="x", pady=10, padx=5)
        
        # Create a keyboard controls info display
        key_info = """Movement Controls:"""
        
        ttk.Label(
            keyboard_frame,
            text=key_info,
            justify="left",
            wraplength=500
        ).pack(padx=10, pady=5, anchor="w")
        
        # Keyboard sensitivity settings
        key_settings_frame = ttk.Frame(keyboard_frame)
        key_settings_frame.pack(fill="x", pady=10)
        
        # Move step (keyboard sensitivity)
        move_frame = ttk.Frame(key_settings_frame)
        move_frame.pack(fill="x", pady=5)
        
        ttk.Label(
            move_frame,
            text="Movement Speed:",
            width=20
        ).pack(side="left")
        
        # Move step slider
        self.move_step_var = tk.DoubleVar(value=self.config.get("move_step", 0.2))
        move_scale = ttk.Scale(
            move_frame,
            from_=0.1,
            to=1.0,
            orient="horizontal",
            variable=self.move_step_var,
            command=self._update_move_step_label
        )
        move_scale.pack(side="left", fill="x", expand=True, padx=5)
        
        self.move_step_label = ttk.Label(
            move_frame,
            text=f"{self.move_step_var.get():.1f}",
            width=5
        )
        self.move_step_label.pack(side="left", padx=5)
        
        # Rotate step (rotation speed)
        rotate_frame = ttk.Frame(key_settings_frame)
        rotate_frame.pack(fill="x", pady=5)
        
        ttk.Label(
            rotate_frame,
            text="Rotation Speed:",
            width=20
        ).pack(side="left")
        
        # Rotate step slider
        self.rotate_step_var = tk.DoubleVar(value=self.config.get("rotate_step_deg", 15.0))
        rotate_scale = ttk.Scale(
            rotate_frame,
            from_=5.0,
            to=40.0,
            orient="horizontal",
            variable=self.rotate_step_var,
            command=self._update_rotate_step_label
        )
        rotate_scale.pack(side="left", fill="x", expand=True, padx=5)
        
        self.rotate_step_label = ttk.Label(
            rotate_frame,
            text=f"{self.rotate_step_var.get():.1f}°",
            width=5
        )
        self.rotate_step_label.pack(side="left", padx=5)
        
        # Apply keyboard settings button
        apply_keyboard_btn = ttk.Button(
            keyboard_frame,
            text="Apply Keyboard Settings",
            command=self._apply_keyboard_settings,
            style="Apply.TButton"
        )
        apply_keyboard_btn.pack(pady=10)
        
        # RC Controller Section
        # Create an instance of RCControllerSettings
        self.rc_settings = RCControllerSettings(scrollable_frame, self.config)
        
        # Add mouse wheel scrolling support
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        # For Linux/macOS (different event)
        canvas.bind_all("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))
        
        # Update canvas width when window is resized
        def on_resize(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind('<Configure>', on_resize)
    
    def _update_move_step_label(self, value):
        """Update the movement speed value label"""
        try:
            val = float(value)
            self.move_step_label.config(text=f"{val:.1f}")
        except:
            pass
    
    def _update_rotate_step_label(self, value):
        """Update the rotation speed value label"""
        try:
            val = float(value)
            self.rotate_step_label.config(text=f"{val:.1f}°")
        except:
            pass
    
    def _apply_keyboard_settings(self):
        """Apply keyboard control settings"""
        try:
            # Update config with current UI values, rounding move_step to one decimal
            self.config["move_step"] = round(self.move_step_var.get(), 1)
            self.config["rotate_step_deg"] = self.rotate_step_var.get()
            
            # Publish config update events
            EM.publish('config/updated', 'move_step')
            EM.publish('config/updated', 'rotate_step_deg')
            
            # Show confirmation via status label
            self.status_label.configure(text="Keyboard settings updated")
            self.root.after(2000, lambda: self.status_label.configure(text=""))
            
            self.logger.info("MenuSystem", f"Updated keyboard settings: move_step={self.config['move_step']}, rotate_step_deg={self.config['rotate_step_deg']}")
        except Exception as e:
            self.status_label.configure(text=f"Error updating keyboard settings: {e}")
            self.root.after(2000, lambda: self.status_label.configure(text=""))
            self.logger.error("MenuSystem", f"Error updating keyboard settings: {e}")

