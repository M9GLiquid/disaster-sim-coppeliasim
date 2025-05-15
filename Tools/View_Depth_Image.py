#!/usr/bin/env python3
"""
Depth Image Viewer: Simple tool for viewing and flipping depth image datasets.

This tool helps you browse all .npz files in a dataset folder.
It displays all images from each file in a grid view and allows you to:
- Navigate between files with arrow keys or buttons
- Flip all images left-right or up-down with a single operation
- Automatically save changes when moving to another file
- Auto-advance through files with continuous flipping (Space to start, ESC to stop)
- Select a custom dataset directory

Usage:
    python View_Depth_Image.py

Keyboard shortcuts:
    Left/Right arrow: Navigate between files
    Space: Flip all images up-down (hold to auto-advance)
    Enter: Flip all images left-right
    ESC: Stop auto-advance

Requires: numpy, pillow, tkinter
"""
import os
import sys
import glob
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog  # For advanced widgets like Combobox and file dialogs
from PIL import Image, ImageTk
import math  # For grid layout calculations
import threading  # For running batch operations without freezing the UI
import time  # For progress updates
import tempfile  # Added import for tempfile module

# Import matplotlib for 3D visualization
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for embedding in Tkinter
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D

# Add the parent directory to the path so we can import from the Utils package
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import from Utils package
from Utils.log_utils import get_logger, DEBUG_L1, DEBUG_L2, DEBUG_L3, LOG_LEVEL_DEBUG, LOG_LEVEL_INFO, LOG_LEVEL_WARNING, LOG_LEVEL_ERROR, LOG_LEVEL_CRITICAL

# Initialize logger
logger = get_logger()

# Default path to the dataset
DATASET_DIR = "data/depth_dataset"

# Path to the assets directory
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

class ImageViewer:
    """
    Main application for viewing and manipulating depth images from .npz files.
    """
    def __init__(self, root):
        """
        Initialize the image viewer application.
        
        Args:
            root: The tkinter root window
        """
        logger.info("ImageViewer", "Initializing depth image viewer application")
        self.root = root
        self.root.title("Depth Image Viewer v.0.2.0")
        
        # Set app icon for Windows and macOS
        self.set_app_icon()
        
        # Initialize logger
        self.logger = get_logger()
        
        # Set app color scheme to match main app
        self.configure_app_style()
        
        # Custom dataset directory
        self.dataset_dir = os.path.join(os.getcwd(), DATASET_DIR)
        
        # Temporary and backup directories are created inside the dataset directory
        # They will be initialized when the dataset directory is set
        self.temp_dir = None
        self.backup_dir = None
        
        # Initialize state
        self.initialize_state()
        
        # Initialize resize debounce
        self.last_resize_time = time.time()
        self.resize_timer = None
        
        # Set up the UI
        self.setup_ui()
        
        # Set up keyboard shortcuts
        self.setup_keyboard_bindings()
        
        # Initialize the temp and backup directories
        self.initialize_temp_backup_dirs()
        
        # Start viewing
        self.load_initial_file()
        
        # Set minimum window size after a short delay to ensure window is rendered
        # self.root.after(500, self.set_current_size_as_minimum)
    
    def set_app_icon(self):
        """Set the application icon for Windows taskbar and macOS dock."""
        try:
            # Icon paths
            icon_path = os.path.join(ASSETS_DIR, "tool_icon.png")
            icon_path_ico = os.path.join(ASSETS_DIR, "tool_icon.ico")
            
            # Check if icon files exist
            if not os.path.exists(ASSETS_DIR):
                os.makedirs(ASSETS_DIR, exist_ok=True)
                logger.warning("ImageViewer", f"Assets directory created: {ASSETS_DIR}")
            
            # Check if icon files exist and log availability
            icon_png_exists = os.path.exists(icon_path)
            icon_ico_exists = os.path.exists(icon_path_ico)
            
            logger.debug_at_level(DEBUG_L1, "ImageViewer", f"PNG icon exists: {icon_png_exists}, ICO icon exists: {icon_ico_exists}")
            
            # For Windows (uses .ico file)
            if sys.platform.startswith('win') and icon_ico_exists:
                self.root.iconbitmap(icon_path_ico)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Set Windows icon: {icon_path_ico}")
            
            # For macOS (uses .png or .icns file)
            elif sys.platform == 'darwin' and icon_png_exists:
                # Use PIL to open and convert the image for Tkinter
                icon_image = Image.open(icon_path)
                icon_tk = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(True, icon_tk)
                # Keep a reference to prevent garbage collection
                self.icon_image = icon_tk
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Set macOS icon: {icon_path}")
            
            # For Linux (uses .png file)
            elif sys.platform.startswith('linux') and icon_png_exists:
                icon_image = Image.open(icon_path)
                icon_tk = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(True, icon_tk)
                # Keep a reference to prevent garbage collection
                self.icon_image = icon_tk
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Set Linux icon: {icon_path}")
            
            else:
                logger.warning("ImageViewer", f"No suitable icon found for platform {sys.platform}")
                if not icon_png_exists and not icon_ico_exists:
                    logger.warning("ImageViewer", f"Icon files not found in {ASSETS_DIR}")
        
        except Exception as e:
            logger.error("ImageViewer", f"Error setting application icon: {str(e)}")
            # Continue without icon - this is not a critical error
        
    def configure_app_style(self):
        """Configure the application style to match the main app."""
        # Light theme with black text
        self.bg_color = "#ffffff"  # Pure white background
        self.fg_color = "#000000"  # Black text
        self.accent_color = "#0078d7"  # Modern blue accent
        self.success_color = "#2ecc71"  # Modern green
        self.warning_color = "#f39c12"  # Modern orange
        self.error_color = "#e74c3c"  # Modern red
        self.hover_color = "#f5f5f5"  # Light gray for hover states
        self.border_color = "#d0d0d0"  # Light gray for borders
        
        # Configure the root window
        self.root.configure(bg=self.bg_color)
        
        # Configure ttk styles
        style = ttk.Style()
        
        # Configure frame styles
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color)
        style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.accent_color, font=("Helvetica", 10, "bold"))
        
        # Configure label styles
        style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        style.configure("Title.TLabel", font=("Helvetica", 14, "bold"), foreground=self.accent_color, background=self.bg_color)
        style.configure("Subtitle.TLabel", font=("Helvetica", 12), foreground=self.fg_color, background=self.bg_color)
        
        # Configure button styles
        style.configure("TButton", 
                      background=self.hover_color, 
                      foreground=self.fg_color, 
                      font=("Helvetica", 10))
        
        style.map("TButton",
                background=[("active", self.hover_color)],
                foreground=[("active", self.accent_color)])
        
        # Configure entry styles
        style.configure("TEntry",
                      fieldbackground=self.bg_color,
                      foreground=self.fg_color,
                      insertcolor=self.fg_color)
        
        # Configure combobox styles
        style.configure("TCombobox", 
                      fieldbackground=self.bg_color,
                      foreground=self.fg_color,
                      background=self.bg_color)
        
        style.map("TCombobox",
                  fieldbackground=[("readonly", self.bg_color)],
                  background=[("readonly", self.bg_color)],
                  foreground=[("readonly", self.fg_color)])
        
        # Configure the notebook style (used for tabs)
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab",
                      background=self.bg_color,
                      foreground=self.fg_color,
                      padding=[10, 5],
                      font=("Helvetica", 10))
        
        style.map("TNotebook.Tab",
                background=[("selected", self.hover_color)],
                foreground=[("selected", self.accent_color)])
        
        # Configure scrollbar style
        style.configure("TScrollbar", 
                      background=self.bg_color, 
                      troughcolor=self.hover_color,
                      arrowcolor=self.fg_color)
    
    #--- Initialization Methods ---#
    
    def initialize_state(self):
        """Initialize application state variables."""
        logger.debug_at_level(DEBUG_L1, "ImageViewer", "Initializing application state")
        # Dataset navigation
        self.npz_files = self.find_npz_files()
        self.current_file_idx = 0
        self.current_batch = None
        
        # File display names (basename without extension)
        self.file_display_names = []
        for file_path in self.npz_files:
            basename = os.path.basename(file_path)
            display_name = os.path.splitext(basename)[0]  # Remove extension
            self.file_display_names.append(display_name)
        
        logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Found {len(self.npz_files)} .npz files")
        
        # Image manipulation
        self.flip_actions = []  # List of flip actions for current file
        self.flipped_images = None  # Store flipped images for saving
        
        # For batch view
        self.thumbnail_labels = []
        self.thumbnail_photos = []
        
        # Auto-advance state
        self.auto_advance = False
        self.auto_advance_id = None
        self.last_auto_action = None
        
        # Debugging flag
        self.debug_mode = False  # Set to True to enable debug messages
    
    def setup_ui(self):
        """Set up the user interface components."""
        # Main content frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a notebook (tabbed container)
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Viewer
        viewer_tab = ttk.Frame(notebook)
        notebook.add(viewer_tab, text="Viewer")
        
        # Tab 2: Batch Operations
        batch_tab = ttk.Frame(notebook)
        notebook.add(batch_tab, text="Batch Operations")
        
        # Tab 3: Help
        help_tab = ttk.Frame(notebook)
        notebook.add(help_tab, text="Help")
        
        # Setup viewer tab content
        self.setup_viewer_tab(viewer_tab)
        
        # Setup batch operations tab content
        self.setup_batch_operations_tab(batch_tab)
        
        # Setup help tab content
        self.setup_help_tab(help_tab)
    
    def setup_viewer_tab(self, parent_frame):
        """Set up the viewer tab content."""
        # Header with title
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="Depth Image Viewer", style="Title.TLabel")
        title_label.pack(side=tk.LEFT, padx=5)
        
        # Window size control - REMOVING THIS BUTTON
        size_frame = ttk.Frame(header_frame)
        size_frame.pack(side=tk.RIGHT, padx=5)
        
        
        # Logging controls
        log_frame = ttk.Frame(header_frame)
        log_frame.pack(side=tk.RIGHT, padx=5)
        
        # Create a dropdown for log levels
        ttk.Label(log_frame, text="Log Level:").pack(side=tk.LEFT, padx=(0, 5))
        self.log_level_var = tk.StringVar(value="INFO")
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level_dropdown = ttk.Combobox(log_frame, textvariable=self.log_level_var, values=log_levels, state="readonly", width=8)
        level_dropdown.pack(side=tk.LEFT, padx=(0, 5))
        
        # Button to apply the log level change
        apply_level_btn = ttk.Button(log_frame, text="Apply", command=self._change_log_level)
        apply_level_btn.pack(side=tk.LEFT)
        
        # Verbose mode toggle
        verbose_frame = ttk.Frame(header_frame)
        verbose_frame.pack(side=tk.RIGHT, padx=5)
        
        self.verbose_var = tk.BooleanVar(value=False)
        verbose_chk = ttk.Checkbutton(verbose_frame, text="Verbose Mode", 
                                    variable=self.verbose_var,
                                    command=self._toggle_verbose_mode)
        verbose_chk.pack(side=tk.RIGHT)
        
        # Directory selection frame
        dir_frame = ttk.LabelFrame(parent_frame, text="Dataset Directory")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        dir_content = ttk.Frame(dir_frame)
        dir_content.pack(fill=tk.X, padx=10, pady=10)
        
        self.dir_entry = ttk.Entry(dir_content, width=50, style="TEntry")
        self.dir_entry.insert(0, self.dataset_dir)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(dir_content, text="Browse... 💾", 
                             command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        reload_btn = ttk.Button(dir_content, text="Reload 🔄", 
                             command=self.reload_directory)
        reload_btn.pack(side=tk.LEFT, padx=5)
        
        # File navigation frame
        nav_frame = ttk.LabelFrame(parent_frame, text="Navigation")
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        nav_content = ttk.Frame(nav_frame)
        nav_content.pack(fill=tk.X, padx=10, pady=10)
        
        self.prev_file_btn = ttk.Button(nav_content, text="◀ Previous", 
                                     command=self.prev_file)
        self.prev_file_btn.pack(side=tk.LEFT, padx=5)
        
        # File selector dropdown
        selector_frame = ttk.Frame(nav_content)
        selector_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Create the dropdown with file names
        self.file_selector = ttk.Combobox(selector_frame, width=25, state="readonly")
        if self.file_display_names:
            self.file_selector['values'] = self.file_display_names
            self.file_selector.current(self.current_file_idx)
        self.file_selector.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Jump button
        self.jump_btn = ttk.Button(selector_frame, text="Show 🔎", 
                                command=self.jump_to_selected_file)
        self.jump_btn.pack(side=tk.LEFT)
        
        self.next_file_btn = ttk.Button(nav_content, text="Next ▶", 
                                     command=self.next_file)
        self.next_file_btn.pack(side=tk.RIGHT, padx=5)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(parent_frame, text="Actions")
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        actions_content = ttk.Frame(actions_frame)
        actions_content.pack(fill=tk.X, padx=10, pady=10)
        
        # Flip controls
        flip_frame = ttk.Frame(actions_content)
        flip_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        flip_label = ttk.Label(flip_frame, text="Flip:")
        flip_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.fliplr_btn = ttk.Button(flip_frame, text="Left-Right ↔️", 
                                  command=self.batch_flip_lr)
        self.fliplr_btn.pack(side=tk.LEFT, padx=5)
        
        self.flipud_btn = ttk.Button(flip_frame, text="Up-Down ↕️", 
                                  command=self.batch_flip_ud)
        self.flipud_btn.pack(side=tk.LEFT, padx=5)
        
        # Auto-advance controls
        auto_frame = ttk.Frame(actions_content)
        auto_frame.pack(side=tk.RIGHT)
        
        auto_label = ttk.Label(auto_frame, text="Auto-Advance:")
        auto_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.auto_ud_btn = ttk.Button(auto_frame, text="Up-Down ↕️", 
                                   command=lambda: self.toggle_auto_advance("flipud"))
        self.auto_ud_btn.pack(side=tk.LEFT, padx=5)
        
        self.auto_lr_btn = ttk.Button(auto_frame, text="Left-Right ↔️", 
                                   command=lambda: self.toggle_auto_advance("fliplr"))
        self.auto_lr_btn.pack(side=tk.LEFT, padx=5)
        
        self.auto_stop_btn = ttk.Button(auto_frame, text="Stop",
                                     command=self.stop_auto_advance,
                                     state=tk.DISABLED)
        self.auto_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Legend for color indicators in a frame
        legend_frame = ttk.LabelFrame(parent_frame, text="Legend")
        legend_frame.pack(fill=tk.X, pady=(0, 10))
        
        legend_content = ttk.Frame(legend_frame)
        legend_content.pack(padx=10, pady=10)
        
        # Original image example
        orig_frame = ttk.Frame(legend_content)
        orig_frame.pack(side=tk.LEFT, padx=20)
        
        # Use a Canvas for the colored sample
        self.orig_sample = tk.Canvas(orig_frame, width=20, height=20, bg=self.border_color, 
                                highlightthickness=1, highlightbackground=self.fg_color)
        self.orig_sample.pack(side=tk.LEFT, padx=5)
        
        orig_label = ttk.Label(orig_frame, text="Original")
        orig_label.pack(side=tk.LEFT)
        
        # Flipped image example
        flipped_frame = ttk.Frame(legend_content)
        flipped_frame.pack(side=tk.LEFT, padx=20)
        
        # Use a Canvas for the colored sample
        self.flipped_sample = tk.Canvas(flipped_frame, width=20, height=20, bg=self.accent_color, 
                                   highlightthickness=1, highlightbackground=self.fg_color)
        self.flipped_sample.pack(side=tk.LEFT, padx=5)
        
        flipped_label = ttk.Label(flipped_frame, text="Flipped")
        flipped_label.pack(side=tk.LEFT)
        
        # Current flip type indicator
        self.flip_status = ttk.Label(legend_content, text="", font=("Helvetica", 9, "italic"))
        self.flip_status.pack(side=tk.RIGHT, padx=20)
        
        # Info and status bar
        info_frame = ttk.Frame(parent_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Info display - file and batch info
        self.info_text = ttk.Label(info_frame, style="Subtitle.TLabel")
        self.info_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Auto-advance indicator
        self.auto_label = ttk.Label(info_frame, foreground=self.accent_color)
        self.auto_label.pack(side=tk.RIGHT)
        
        # Status message for operations feedback
        self.status_label = ttk.Label(parent_frame, font=("Helvetica", 9, "italic"))
        self.status_label.pack(fill=tk.X, pady=(0, 10))
        
        # Main grid frame (for batch view) with scrollable content
        grid_container = ttk.Frame(parent_frame)
        grid_container.pack(fill=tk.BOTH, expand=True)
        
        # Store reference to grid frame for later updates
        self.grid_frame = grid_container
        
        # Create a canvas for the grid to support scrolling for large batches
        canvas_frame = ttk.Frame(grid_container, style="Canvas.TFrame")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Style for canvas frame with border
        style = ttk.Style()
        style.configure("Canvas.TFrame", borderwidth=1, relief="solid")
        
        # Define grid dimensions
        grid_height = getattr(self, 'grid_height_value', 300)  # Default height
        grid_width = getattr(self, 'grid_width_value', 800)    # Default width
        rows = 2  # Fixed number of rows
        cols = 5  # Fixed number of columns
        batch_size = 10  # Default batch size if no data is loaded yet
        
        # Create a canvas with scrollbars for both vertical and horizontal scrolling
        self.canvas = tk.Canvas(canvas_frame, bg=self.bg_color, bd=0, highlightthickness=0, 
                         height=grid_height)  # Set explicit height
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _on_shift_mousewheel(event):
            if event.state & 0x0001:  # Check if shift is pressed
                self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")
            else:
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel events
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)
        
        # Frame inside canvas for the grid
        inner_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=inner_frame, anchor="nw", width=grid_width)
        
        # Fixed display of 2 rows x 5 columns = 10 images
        max_images = min(batch_size, rows * cols)
        
        # Create a container frame for the 2x5 grid
        grid_container = ttk.Frame(inner_frame)
        grid_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Configure grid container for even spacing across full width
        for c in range(cols):
            grid_container.columnconfigure(c, weight=1)  # Equal width columns
        
        # Configure rows with consistent height
        for r in range(rows):
            grid_container.rowconfigure(r, weight=1)  # Equal height rows
        
        # Calculate thumbnail size based on grid width
        available_width = grid_width - 100  # Account for padding, borders, and scrollbar
        thumb_width = max(100, min(180, (available_width // cols) - 20))  # Ensure reasonable size range
        self.thumb_size = (thumb_width, thumb_width)
        
        # Create placeholder depths if not available
        depths = []
        if hasattr(self, 'current_batch') and self.current_batch is not None and 'depths' in self.current_batch:
            depths = self.current_batch['depths']
        
        # Initialize flip_actions if not already done
        if not hasattr(self, 'flip_actions') or len(self.flip_actions) < max_images:
            self.flip_actions = [None] * max(batch_size, 10)  # Ensure we have enough slots
        
        for i in range(max_images):
            # Calculate row and column
            r = i // cols
            c = i % cols
            
            # Create frame for this thumbnail
            frame = tk.Frame(grid_container, bg=self.bg_color)
            frame.grid(row=r, column=c, padx=5, pady=5)
            
            try:
                # Process the image if available
                if i < len(depths):
                    img_array = depths[i]
                    
                    # Apply flip if needed
                    if self.flip_actions[i]:
                        if self.flip_actions[i] == "fliplr":
                            img_array = np.fliplr(img_array)
                        elif self.flip_actions[i] == "flipud":
                            img_array = np.flipud(img_array)
                        elif self.flip_actions[i] == "both":
                            img_array = np.flipud(np.fliplr(img_array))
                    
                    pil_img = self.prepare_image(img_array)
                    pil_thumb = pil_img.resize(self.thumb_size, Image.NEAREST)
                    photo = ImageTk.PhotoImage(pil_thumb)
                    
                    # Create background color based on flip state
                    # Use light blue background if the image has been flipped
                    bg_color = "#d4e6f1" if self.flip_actions[i] else "white"  # Light blue for flipped
                    
                    # Create card-like frame for the image with fixed size
                    card_frame = tk.Frame(frame, bd=1, relief=tk.SOLID, 
                                       bg=bg_color, padx=2, pady=2,
                                       width=thumb_width+10, height=thumb_width+30)
                    card_frame.pack(padx=5, pady=5)
                    card_frame.pack_propagate(False)  # Prevent the frame from resizing to fit content
                    
                    # Create and add image label with appropriate background
                    img_label = tk.Label(card_frame, image=photo, bg=bg_color)
                    img_label.pack(pady=(5, 2))
                    
                    # Bind click event to show full-size image
                    img_label.bind("<Button-1>", lambda event, idx=i: self.show_full_size_image(idx))
                    
                    # Store references to prevent garbage collection
                    self.thumbnail_photos.append(photo)
                    self.thumbnail_labels.append(img_label)
                    
                    # Add image number and flip indicator
                    flip_text = f"Image #{i+1}" + (" (flipped)" if self.flip_actions[i] else "")
                    num_label = tk.Label(card_frame, text=flip_text, bg=bg_color,
                                      font=("Helvetica", 8))
                    num_label.pack(pady=(2, 4))
                else:
                    # Create a placeholder for missing images
                    placeholder_frame = tk.Frame(frame, bd=1, relief=tk.SOLID,
                                            bg="#f0f0f0", padx=2, pady=2,
                                            width=thumb_width+10, height=thumb_width+30)
                    placeholder_frame.pack(padx=5, pady=5)
                    placeholder_frame.pack_propagate(False)
                    
                    placeholder_label = tk.Label(placeholder_frame, text="No Image",
                                             bg="#f0f0f0", font=("Helvetica", 10))
                    placeholder_label.pack(expand=True, fill=tk.BOTH)
                    
                    # Bind click event to show message for placeholder
                    placeholder_label.bind("<Button-1>", lambda event: self.show_status_message("No image available", self.warning_color))
                
                # Update every 20 images to keep UI responsive
                if i % 20 == 0:
                    self.root.update_idletasks()
                    
            except Exception as e:
                logger.error("ImageViewer", f"Error processing image {i}: {str(e)}")
                # Create a text label as fallback
                error_label = tk.Label(frame, text=f"Image {i+1}\nError", 
                                     width=thumb_width//10, height=thumb_width//12, 
                                     bg="#f0f0f0")
                error_label.pack(pady=5)
        
        # If there are more images than displayed, add a message
        if batch_size > max_images:
            more_frame = ttk.Frame(grid_container)
            more_frame.pack(fill=tk.X, pady=5)
            
            more_label = ttk.Label(more_frame, text=f"+ {batch_size - max_images} more images not shown",
                                font=("Helvetica", 9, "italic"), foreground="#7f8c8d")
            more_label.pack(pady=5)
        
        # Update the canvas scrollregion
        inner_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def setup_batch_operations_tab(self, parent_frame):
        """Set up the batch operations tab content."""
        # Header with title
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="Batch Operations", style="Title.TLabel")
        title_label.pack(side=tk.LEFT, padx=5)
        
        # Source directory frame
        source_frame = ttk.LabelFrame(parent_frame, text="Source Directory")
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        source_content = ttk.Frame(source_frame)
        source_content.pack(fill=tk.X, padx=10, pady=10)
        
        self.source_entry = ttk.Entry(source_content, width=50, style="TEntry")
        self.source_entry.insert(0, self.dataset_dir)
        self.source_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        source_browse_btn = ttk.Button(source_content, text="Browse... 💾", 
                                    command=self.browse_source_directory)
        source_browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Output directory frame
        output_frame = ttk.LabelFrame(parent_frame, text="Output Directory")
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        output_content = ttk.Frame(output_frame)
        output_content.pack(fill=tk.X, padx=10, pady=10)
        
        self.output_entry = ttk.Entry(output_content, width=50, style="TEntry")
        default_output = os.path.join(os.path.dirname(self.dataset_dir), "flipped_dataset")
        self.output_entry.insert(0, default_output)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        output_browse_btn = ttk.Button(output_content, text="Browse... 💾", 
                                    command=self.browse_output_directory)
        output_browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Flip options frame
        options_frame = ttk.LabelFrame(parent_frame, text="Flip Options")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        options_content = ttk.Frame(options_frame)
        options_content.pack(fill=tk.X, padx=10, pady=10)
        
        # Flip type selection
        flip_type_label = ttk.Label(options_content, text="Flip Type:")
        flip_type_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.flip_type_var = tk.StringVar(value="fliplr")
        
        # Add trace to update preview when flip type changes, but with auto-preview off by default
        # The trace_add is now only added when preview is enabled
        
        flip_lr_radio = ttk.Radiobutton(options_content, text="Left-Right ↔️", 
                                     variable=self.flip_type_var, value="fliplr")
        flip_lr_radio.pack(side=tk.LEFT, padx=10)
        
        flip_ud_radio = ttk.Radiobutton(options_content, text="Up-Down ↕️", 
                                     variable=self.flip_type_var, value="flipud")
        flip_ud_radio.pack(side=tk.LEFT, padx=10)
        
        flip_none_radio = ttk.Radiobutton(options_content, text="No Flip (Copy Only) 📄", 
                                      variable=self.flip_type_var, value="none")
        flip_none_radio.pack(side=tk.LEFT, padx=10)
        
        # Preview options
        preview_frame = ttk.Frame(options_content)
        preview_frame.pack(side=tk.RIGHT, padx=10)
        
        # Changed default to False to prevent auto-flipping at startup
        self.preview_var = tk.BooleanVar(value=False)
        preview_check = ttk.Checkbutton(preview_frame, text="Show Preview in Viewer", 
                                      variable=self.preview_var,
                                      command=self.toggle_preview)
        preview_check.pack(side=tk.RIGHT, padx=10)
        
        # Quick Flip Buttons
        quick_flip_frame = ttk.Frame(options_frame)
        quick_flip_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        quick_flip_label = ttk.Label(quick_flip_frame, text="Quick Flip Preview:")
        quick_flip_label.pack(side=tk.LEFT, padx=(0, 10))
        
        quick_fliplr_btn = ttk.Button(quick_flip_frame, text="Left-Right ↔️", 
                                   command=lambda: self.quick_flip_preview("fliplr"))
        quick_fliplr_btn.pack(side=tk.LEFT, padx=5)
        
        quick_flipud_btn = ttk.Button(quick_flip_frame, text="Up-Down ↕️", 
                                   command=lambda: self.quick_flip_preview("flipud"))
        quick_flipud_btn.pack(side=tk.LEFT, padx=5)
        
        quick_reset_btn = ttk.Button(quick_flip_frame, text="Reset Preview 🧹", 
                                  command=lambda: self.quick_flip_preview("none"))
        quick_reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Execute button
        execute_frame = ttk.Frame(parent_frame)
        execute_frame.pack(fill=tk.X, pady=(10, 10))
        
        self.execute_btn = ttk.Button(execute_frame, text="Execute Batch Operation", 
                                  command=self.execute_batch_operation)
        self.execute_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(parent_frame, text="Progress")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        progress_content = ttk.Frame(progress_frame)
        progress_content.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress_bar = ttk.Progressbar(progress_content, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, side=tk.TOP, pady=(0, 5))
        
        progress_info_frame = ttk.Frame(progress_content)
        progress_info_frame.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(progress_info_frame, text="Ready")
        self.progress_label.pack(side=tk.LEFT)
        
        self.progress_count = ttk.Label(progress_info_frame, text="")
        self.progress_count.pack(side=tk.RIGHT)
        
        # Log frame
        log_frame = ttk.LabelFrame(parent_frame, text="Operation Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        log_content = ttk.Frame(log_frame)
        log_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrolled text widget for logs
        self.log_text = tk.Text(log_content, height=10, width=50, wrap=tk.WORD,
                         bg=self.bg_color, fg=self.fg_color)
        log_scrollbar = ttk.Scrollbar(log_content, orient="vertical", 
                                  command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Disable editing of log
        self.log_text.config(state=tk.DISABLED)
    
    def setup_help_tab(self, parent_frame):
        """Set up the help tab content with usage instructions."""
        # Create a scrollable text area
        frame = ttk.Frame(parent_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a scrolled text widget
        text_widget = tk.Text(frame, wrap=tk.WORD, bg=self.bg_color, fg=self.fg_color,
                         font=("Helvetica", 11), padx=15, pady=15)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Make the text widget read-only
        text_widget.config(state=tk.NORMAL)
        
        # Add help content
        help_content = """Depth Image Viewer - Help

Overview
This application allows you to view and manipulate depth image datasets stored in .npz files. You can browse through files, view images in a grid, flip images, and visualize them in 3D.

Main Viewer Tab

Navigation
- Previous/Next buttons: Navigate between .npz files in the dataset
- File selector dropdown: Jump directly to a specific file
- Keyboard shortcuts: 
  - Left/Right arrows: Navigate between files
  - Space: Flip all images up-down
  - Enter: Flip all images left-right
  - ESC: Stop auto-advance

Actions
- Flip Left-Right: Horizontally flip all images in the current file
- Flip Up-Down: Vertically flip all images in the current file
- Auto-Advance: Automatically move through files while applying flips

Image Grid
- Click on any thumbnail: Open a full-size view of the image
- Full-size view features:
  - Scrollable view for large images
  - "View 3D" button to see a 3D visualization of the depth data
  - Information about image dimensions and flip status

3D Visualization
- Interactive 3D surface: Click and drag to rotate the view
- View angle buttons: Quickly switch between different perspectives
  - Top: View from above
  - Side: View from the side
  - Front: View from the front side
  - Isometric: View from the side, but with a 45 degree angle
- Colormap: Depth values are represented by colors

Batch Operations Tab

Directory Selection
- Source Directory: Select the directory containing .npz files to process
- Output Directory: Choose where to save the processed files

Operation Options
- Flip Type: Choose between Left-Right flip, Up-Down flip, or Copy only
- Show Preview: Enable to see a preview of the operation in the Viewer tab
- Quick Flip Preview: Quickly apply different flip types to see the results

Execution
- Execute Batch Operation: Process all files in the source directory
- Progress indicators: Track the progress of the batch operation
- Operation Log: View details about the processing

Tips
- Changes are automatically saved when navigating between files
- Click on thumbnails to see full-size images and 3D visualizations
- The 3D view can be rotated with your mouse for better depth perception
"""
        
        # Insert the help content
        text_widget.insert(tk.END, help_content)
        
        # Add tags for formatting
        text_widget.tag_configure("heading1", font=("Helvetica", 18, "bold"), foreground=self.accent_color, spacing1=10, spacing3=10)
        text_widget.tag_configure("heading2", font=("Helvetica", 16, "bold"), foreground=self.accent_color, spacing1=10, spacing3=5)
        text_widget.tag_configure("heading3", font=("Helvetica", 14, "bold"), foreground=self.accent_color, spacing1=5, spacing3=2)
        text_widget.tag_configure("bold", font=("Helvetica", 11, "bold"))
        text_widget.tag_configure("bullet", lmargin1=20, lmargin2=30)
        text_widget.tag_configure("subbullet", lmargin1=40, lmargin2=50)
        
        # Apply formatting based on content structure
        lines = help_content.split('\n')
        line_count = 1
        
        # Map of headings to apply formatting
        heading1_lines = ["Depth Image Viewer - Help"]
        heading2_lines = ["Overview", "Main Viewer Tab", "Batch Operations Tab", "Tips"]
        heading3_lines = ["Navigation", "Actions", "Image Grid", "3D Visualization", 
                       "Directory Selection", "Operation Options", "Execution"]
        
        # Bold text in bullet points - feature names
        bold_phrases = [
            "Previous/Next buttons", "File selector dropdown", 
            "Flip Left-Right", "Flip Up-Down", "Auto-Advance",
            "Click on any thumbnail", "Full-size view features",
            "Interactive 3D surface", "View angle buttons", "Colormap",
            "Source Directory", "Output Directory",
            "Flip Type", "Show Preview", "Quick Flip Preview",
            "Execute Batch Operation", "Progress indicators", "Operation Log"
        ]
        
        for i, line in enumerate(lines):
            # Apply heading styles
            if line in heading1_lines:
                text_widget.tag_add("heading1", f"{i+1}.0", f"{i+1}.end")
            elif line in heading2_lines:
                text_widget.tag_add("heading2", f"{i+1}.0", f"{i+1}.end")
            elif line in heading3_lines:
                text_widget.tag_add("heading3", f"{i+1}.0", f"{i+1}.end")
            
            # Apply bullet formatting
            elif line.startswith("- "):
                text_widget.tag_add("bullet", f"{i+1}.0", f"{i+1}.end")
                
                # Bold the feature name (text before the colon)
                if ": " in line:
                    colon_idx = line.find(": ")
                    if colon_idx > 2:  # Skip the "- " prefix
                        text_widget.tag_add("bold", f"{i+1}.2", f"{i+1}.{colon_idx}")
                
                # Check for bold phrases
                for phrase in bold_phrases:
                    if phrase in line:
                        start_idx = line.find(phrase)
                        if start_idx >= 0:
                            text_widget.tag_add("bold", f"{i+1}.{start_idx}", f"{i+1}.{start_idx + len(phrase)}")
            
            # Apply sub-bullet formatting
            elif line.startswith("  - "):
                text_widget.tag_add("subbullet", f"{i+1}.0", f"{i+1}.end")
                
                # Bold the feature name (text before the colon)
                if ": " in line:
                    colon_idx = line.find(": ")
                    if colon_idx > 4:  # Skip the "  - " prefix
                        text_widget.tag_add("bold", f"{i+1}.4", f"{i+1}.{colon_idx}")
                
                # Check for bold phrases
                for phrase in bold_phrases:
                    if phrase in line:
                        start_idx = line.find(phrase)
                        if start_idx >= 0:
                            text_widget.tag_add("bold", f"{i+1}.{start_idx}", f"{i+1}.{start_idx + len(phrase)}")
        
        # Make the text widget read-only
        text_widget.config(state=tk.DISABLED)
    
    def _change_log_level(self):
        """Change the logging level at runtime."""
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
            logger.set_level(level)
            self.show_status_message(f"Log level changed to {level_str}")
        else:
            self.show_status_message(f"Invalid log level: {level_str}", self.error_color)
    
    def browse_source_directory(self):
        """Open a file dialog to select a source dataset directory."""
        directory = filedialog.askdirectory(
            initialdir=self.source_entry.get(),
            title="Select Source Dataset Directory"
        )
        
        if directory:  # If a directory was selected
            self.source_entry.delete(0, tk.END)
            self.source_entry.insert(0, directory)
            
            # Also update the output directory to be alongside the input directory
            output_dir = os.path.join(os.path.dirname(directory), "flipped_dataset")
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, output_dir)
            
            # If we changed the source directory, update the viewer too
            if self.preview_var.get():
                # Switch to the same directory in the viewer
                self.dataset_dir = directory
                self.dir_entry.delete(0, tk.END)
                self.dir_entry.insert(0, self.dataset_dir)
                
                # Update temp and backup directories
                self.initialize_temp_backup_dirs()
                
                self.reload_directory()
                
                # Ensure preview is shown
                self.update_batch_preview()
    
    def browse_output_directory(self):
        """Open a file dialog to select an output directory."""
        directory = filedialog.askdirectory(
            initialdir=self.output_entry.get(),
            title="Select Output Directory"
        )
        
        if directory:  # If a directory was selected
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)
    
    def execute_batch_operation(self):
        """Execute the batch flip operation with selected parameters."""
        # Get parameters from UI
        source_dir = self.source_entry.get().strip()
        output_dir = self.output_entry.get().strip()
        flip_type = self.flip_type_var.get()
        
        if not source_dir or not os.path.isdir(source_dir):
            self.show_batch_status("Source directory does not exist", self.error_color)
            return
        
        # Check if output directory exists, create it if not
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                self.show_batch_status(f"Failed to create output directory: {str(e)}", self.error_color)
                return
        
        # Disable execute button during operation
        self.execute_btn.config(state=tk.DISABLED)
        
        # Reset progress
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Starting batch operation...")
        self.progress_count.config(text="")
        
        # Clear log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Add start message to log
        self.add_to_log(f"Starting batch operation: {flip_type}\n")
        self.add_to_log(f"Source directory: {source_dir}\n")
        self.add_to_log(f"Output directory: {output_dir}\n")
        self.add_to_log("-" * 50 + "\n")
        
        # Start operation in a separate thread
        threading.Thread(
            target=self.run_batch_operation,
            args=(source_dir, output_dir, flip_type),
            daemon=True
        ).start()
    
    def run_batch_operation(self, npz_dir, out_dir, flip_type):
        """Run the batch flip operation in a background thread."""
        logger.info("BatchOp", f"Starting batch flip operation: {flip_type}")
        self.update_progress_label(f"Starting batch {flip_type} operation...")
        
        if flip_type == 'none':
            self.add_to_log("Copy-only operation (no flip) selected.\n")
        
        # Find all .npz files
        files = []
        for root, _, names in os.walk(npz_dir):
            for name in names:
                if name.lower().endswith('.npz'):
                    files.append(os.path.join(root, name))
        
        total = len(files)
        logger.info("BatchOp", f"Found {total} .npz files. Applying {flip_type}...")
        self.add_to_log(f"Found {total} .npz files. Applying {flip_type}...\n")
        
        if total == 0:
            self.update_progress_label("No .npz files found!")
            self.execute_btn.config(state=tk.NORMAL)
            return
        
        # Determine flip axis based on operation type
        # IMPORTANT: For numpy depth arrays in our code, axis 2 is horizontal (left-right) and axis 1 is vertical (up-down)
        # This custom convention is used in our specific data format
        if flip_type == 'fliplr':
            axis = 2  # Flip horizontally (left-right)
            description = "horizontally (left-right)"
        elif flip_type == 'flipud':
            axis = 1  # Flip vertically (up-down)
            description = "vertically (up-down)"
        else:
            axis = None  # No flip
            description = "without flipping"
            
        logger.debug_at_level(DEBUG_L1, "BatchOp", f"Flipping {description} (axis={axis})")
        self.add_to_log(f"Flipping images {description}\n")
        
        # Update progress bar maximum
        self.progress_bar["maximum"] = total
        
        successful = 0
        errors = 0
        
        for idx, fpath in enumerate(files, 1):
            rel = os.path.relpath(fpath, npz_dir)
            out_path = os.path.join(out_dir, rel)
            
            # Update progress
            self.update_progress(idx, total, rel)
            
            logger.debug_at_level(DEBUG_L2, "BatchOp", f"Processing file {idx}/{total}: {rel}")
            
            # Create output directory if needed
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            
            try:
                data = np.load(fpath, allow_pickle=True)
                
                # Create a copy of the data for the output
                flipped = {}
                
                # Process each array in the file
                for k, v in data.items():
                    # Only flip arrays with at least 2 dimensions and if a flip type is selected
                    if isinstance(v, np.ndarray) and v.ndim >= 2 and flip_type != 'none':
                        # Log the array being flipped for debugging
                        logger.debug_at_level(DEBUG_L3, "BatchOp", f"Flipping array '{k}' with shape {v.shape}")
                        
                        # Make a copy to avoid modifying the original
                        flipped_array = np.copy(v)
                        
                        # Check dimensions and use appropriate axis
                        ndim = flipped_array.ndim
                        if flip_type == 'fliplr':
                            # For left-right flip, use last dimension (width)
                            flip_axis = min(2, ndim - 1)  # Use axis 2 for 3D+ arrays, axis 1 for 2D arrays
                        else:  # flipud
                            # For up-down flip, use second-to-last dimension (height)
                            flip_axis = min(1, ndim - 2)  # Use axis 1 for 3D+ arrays, axis 0 for 2D arrays
                            if ndim < 2:
                                flip_axis = 0  # Fallback for 1D arrays
                        
                        logger.debug_at_level(DEBUG_L3, "BatchOp", f"Using flip_axis={flip_axis} for {ndim}D array")
                        
                        # Apply the flip operation with the appropriate axis
                        flipped_array = np.flip(flipped_array, axis=flip_axis)
                        
                        # Store the flipped array
                        flipped[k] = flipped_array
                        
                        # Verify the flip by checking if any elements changed
                        if np.array_equal(v, flipped_array):
                            logger.warning("BatchOp", f"Warning: Flipping '{k}' had no effect")
                            self.add_to_log(f"  Warning: Flipping '{k}' had no effect - check data content\n")
                    else:
                        # For non-array types or arrays with fewer dimensions, just copy
                        flipped[k] = v
                
                # Save the modified file
                np.savez_compressed(out_path, **flipped)
                logger.debug_at_level(DEBUG_L1, "BatchOp", f"[{idx}/{total}] Processed: {rel}")
                
                # Add a success message with the flip type
                if flip_type == 'none':
                    self.add_to_log(f"[{idx}/{total}] Copied: {rel}\n")
                else:
                    self.add_to_log(f"[{idx}/{total}] Flipped {description}: {rel}\n")
                
                successful += 1
                
            except Exception as e:
                errors += 1
                logger.error("BatchOp", f"Error processing file {fpath}: {e}")
                self.add_to_log(f"Error processing {rel}: {str(e)}\n")
        
        # Operation complete
        logger.info("BatchOp", f"Batch operation complete. Successful: {successful}, Errors: {errors}")
        self.update_progress_label(f"Batch operation complete! Processed {successful} files ({errors} errors)")
        
        summary = (
            f"\nBatch operation completed!\n"
            f"- Total files: {total}\n"
            f"- Successfully processed: {successful}\n"
            f"- Errors: {errors}\n"
            f"- Operation type: {flip_type} ({description})\n"
            f"- Output directory: {out_dir}\n"
        )
        self.add_to_log(summary)
        
        # Re-enable execute button
        self.execute_btn.config(state=tk.NORMAL)
    
    def update_progress(self, current, total, filename):
        """Update the progress indicators."""
        def _update():
            self.progress_bar["value"] = current
            self.progress_count.config(text=f"{current}/{total}")
            self.update_progress_label(f"Processing: {filename}")
            self.add_to_log(f"[{current}/{total}] Processing: {filename}\n")
        
        # Schedule UI update in the main thread
        self.root.after(0, _update)
    
    def update_progress_label(self, text):
        """Update the progress label."""
        def _update():
            self.progress_label.config(text=text)
        
        # Schedule UI update in the main thread
        self.root.after(0, _update)
    
    def add_to_log(self, text):
        """Add text to the log widget."""
        def _update():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, text)
            self.log_text.see(tk.END)  # Scroll to the end
            self.log_text.config(state=tk.DISABLED)
        
        # Schedule UI update in the main thread
        self.root.after(0, _update)
    
    def show_batch_status(self, message, color=None):
        """Show a status message in the batch operations tab."""
        if color is None:
            color = self.success_color
        
        # Update the progress label with the message
        self.progress_label.config(text=message, foreground=color)
        
        # Add to log as well
        self.add_to_log(f"{message}\n")
        
        # Reset color after a delay
        def _reset_color():
            self.progress_label.config(foreground=self.fg_color)
        
        self.root.after(3000, _reset_color)
    
    def find_npz_files(self):
        """Find all .npz files in the dataset directory."""
        try:
            if not os.path.exists(self.dataset_dir):
                logger.warning("ImageViewer", f"Dataset directory does not exist: {self.dataset_dir}")
                # Create the directory structure if it doesn't exist
                os.makedirs(self.dataset_dir, exist_ok=True)
                
                # Create subdirectories if we're using the default path
                if self.dataset_dir == os.path.join(os.getcwd(), DATASET_DIR):
                    os.makedirs(os.path.join(self.dataset_dir, "train"), exist_ok=True)
                    os.makedirs(os.path.join(self.dataset_dir, "val"), exist_ok=True)
                    os.makedirs(os.path.join(self.dataset_dir, "test"), exist_ok=True)
                
            # Use glob to find all .npz files recursively
            all_files = glob.glob(os.path.join(self.dataset_dir, "**", "*.npz"), recursive=True)
            all_files.sort()  # Sort files alphabetically
            return all_files
        except Exception as e:
            logger.error("ImageViewer", f"Error finding .npz files: {str(e)}")
            return []
    
    def load_initial_file(self):
        """Load the first file in the dataset."""
        if not self.npz_files:
            msg = "No depth image files found in dataset directory."
            logger.warning("ImageViewer", msg)
            self.info_text.configure(text=msg)
            self.show_status_message("No depth image files found.", self.error_color)
            return
        
        self.load_file()
    
    def load_file(self):
        """Load the current file and display its images."""
        if not self.npz_files or self.current_file_idx >= len(self.npz_files):
            self.show_status_message("No valid file to load", self.error_color)
            return
        
        current_file = self.npz_files[self.current_file_idx]
        logger.info("ImageViewer", f"Loading file: {os.path.basename(current_file)}")
        
        try:
            # Load the npz file
            self.current_batch = np.load(current_file)
            
            # Reset flip actions for the new file
            self.flip_actions = [None] * len(self.current_batch['depths'])
            self.flipped_images = None
            
            # Ensure canvas has the correct background color
            self.canvas.configure(bg=self.bg_color)
            
            # Update the UI
            self.info_text.configure(
                text=f"File {self.current_file_idx + 1}/{len(self.npz_files)}: "
                     f"{os.path.basename(current_file)} "
                     f"({len(self.current_batch['depths'])} images)"
            )
            
            # Update the file selector
            self.update_file_selector()
            
            # Display the images
            self.setup_batch_grid()
            
            # Update legend
            self.update_legend_status()
            
            # Apply batch preview if applicable and explicitly enabled
            if hasattr(self, 'preview_var') and self.preview_var.get():
                try:
                    self.update_batch_preview()
                except Exception as e:
                    logger.warning("ImageViewer", f"Could not apply batch preview: {str(e)}")
            
            self.show_status_message(f"Loaded {os.path.basename(current_file)}")
        except Exception as e:
            logger.error("ImageViewer", f"Error loading file: {str(e)}")
            self.show_status_message(f"Error loading file: {str(e)}", self.error_color)
            
            # If we failed to load, try to load the next file
            self.current_batch = None
            self.current_file_idx = (self.current_file_idx + 1) % len(self.npz_files)
            try:
                # Recursive call to try the next file
                # Add a guard to prevent infinite recursion
                if not hasattr(self, '_load_retry_count'):
                    self._load_retry_count = 0
                
                self._load_retry_count += 1
                if self._load_retry_count <= 3:  # Only retry 3 times max
                    self.load_file()
                else:
                    self.show_status_message("Failed to load any valid files after multiple attempts", self.error_color)
                    self._load_retry_count = 0
            except Exception:
                self._load_retry_count = 0  # Reset the counter
    
    def save_current_file(self):
        """
        Save changes to the current file.
        
        The saving process follows these steps for safety:
        1. Create a backup of the original file with .backup extension
        2. Save changes to a temporary file with .temp extension
        3. Verify the temporary file can be loaded without errors
        4. Replace the original file with the temporary file
        5. Clean up temporary files and backups when successful
        
        This approach prevents data loss if the save operation fails.
        """
        if not self.current_batch or not any(self.flip_actions):
            # Nothing to save
            return
        
        current_file = self.npz_files[self.current_file_idx]
        current_filename = os.path.basename(current_file)
        logger.info("ImageViewer", f"Saving changes to: {current_filename}")
        
        try:
            # Get absolute paths for temp and backup directories
            temp_dir_abs = os.path.abspath(self.temp_dir)
            backup_dir_abs = os.path.abspath(self.backup_dir)
            
            logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Temp directory path: {temp_dir_abs}")
            logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Backup directory path: {backup_dir_abs}")
            
            # Make sure directories are writable
            if not os.access(temp_dir_abs, os.W_OK):
                logger.error("ImageViewer", f"Temp directory not writable: {temp_dir_abs}")
                raise Exception(f"Temp directory not writable: {temp_dir_abs}")
                
            if not os.access(backup_dir_abs, os.W_OK):
                logger.error("ImageViewer", f"Backup directory not writable: {backup_dir_abs}")
                # This is not fatal - we can proceed without backups
                logger.warning("ImageViewer", "Will proceed without creating backups")
            
            # Make sure temp and backup directories exist
            try:
                os.makedirs(temp_dir_abs, exist_ok=True)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Created/confirmed temp directory: {temp_dir_abs}")
                if not os.path.exists(temp_dir_abs):
                    logger.error("ImageViewer", f"Failed to create temp directory: {temp_dir_abs}")
                
                os.makedirs(backup_dir_abs, exist_ok=True)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Created/confirmed backup directory: {backup_dir_abs}")
            except Exception as dir_err:
                logger.error("ImageViewer", f"Error creating directories: {str(dir_err)}")
                raise Exception(f"Failed to create necessary directories: {str(dir_err)}")
            
            # Create a backup of the original file in the backup directory
            backup_filename = f"{current_filename}.backup.{int(time.time())}"
            backup_file = os.path.join(backup_dir_abs, backup_filename)
            
            try:
                if os.access(backup_dir_abs, os.W_OK):
                    import shutil
                    shutil.copy2(current_file, backup_file)
                    logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Created backup at {backup_file}")
                else:
                    logger.warning("ImageViewer", f"Skipping backup - directory not writable")
            except Exception as e:
                logger.warning("ImageViewer", f"Failed to create backup: {str(e)}")
            
            # We need to create a copy with the flipped images
            depths = self.current_batch['depths']
            
            # If we haven't calculated flipped images yet, do it now
            if self.flipped_images is None:
                modified_depths = np.copy(depths)
                
                # Apply all flip operations
                for i, action in enumerate(self.flip_actions):
                    if action == "fliplr":
                        modified_depths[i] = np.fliplr(depths[i])
                    elif action == "flipud":
                        modified_depths[i] = np.flipud(depths[i])
                    elif action == "both":
                        modified_depths[i] = np.flipud(np.fliplr(depths[i]))
                
                self.flipped_images = modified_depths
            
            # Create a new npz file with the same data but flipped depths
            save_data = {key: self.current_batch[key] for key in self.current_batch.files}
            save_data['depths'] = self.flipped_images
            
            # Create a unique temporary file name using Python's tempfile module
            import tempfile
            
            # First approach: use the system temp directory with a unique filename
            _, temp_file = tempfile.mkstemp(suffix=f'.{current_filename}.temp.npz')
            
            # Log the full paths being used
            logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Current file: {current_file}")
            logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Using temp file path: {temp_file}")
            
            # Verify the temp directory exists and is writable
            temp_dir = os.path.dirname(temp_file)
            if not os.path.exists(temp_dir):
                logger.error("ImageViewer", f"Temp directory missing: {temp_dir}")
                raise Exception(f"Temp directory doesn't exist: {temp_dir}")
            
            if not os.access(temp_dir, os.W_OK):
                logger.error("ImageViewer", f"Temp directory not writable: {temp_dir}")
                raise Exception(f"Temp directory not writable: {temp_dir}")
            
            logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Saving to temporary file: {temp_file}")
            
            # Save to the temporary file
            try:
                np.savez_compressed(temp_file, **save_data)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Saved temp file successfully: {temp_file}")
                
                # Immediately check if the file exists after saving
                if os.path.exists(temp_file):
                    logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Temp file exists after saving: {temp_file}")
                    file_size = os.path.getsize(temp_file)
                    logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Temp file size: {file_size} bytes")
                else:
                    logger.error("ImageViewer", f"Temp file does not exist immediately after saving: {temp_file}")
                    raise Exception(f"Temp file disappeared immediately after saving")
                
            except Exception as save_err:
                logger.error("ImageViewer", f"Error saving temp file: {str(save_err)}")
                # Check if directory exists after error
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Temp dir exists: {os.path.exists(temp_dir)}")
                raise Exception(f"Failed to save temporary file: {str(save_err)}")
            
            # Verify the temporary file
            try:
                # Check if file exists before loading
                if not os.path.exists(temp_file):
                    logger.error("ImageViewer", f"Temp file not found after saving: {temp_file}")
                    raise FileNotFoundError(f"Temp file not found after saving: {temp_file}")
                
                test_load = np.load(temp_file)
                # If we can load it without error, it's good
                logger.debug_at_level(DEBUG_L1, "ImageViewer", "Verified temporary file")
            except Exception as e:
                # If we can't load it, something went wrong
                logger.error("ImageViewer", f"Temporary file verification failed: {str(e)}")
                # Check file existence and permissions
                if os.path.exists(temp_file):
                    logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Temp file exists but failed to load")
                    # Check file permissions
                    is_readable = os.access(temp_file, os.R_OK)
                    logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Temp file readable: {is_readable}")
                else:
                    logger.error("ImageViewer", f"Temp file doesn't exist after saving")
                    
                # Clean up the temp file if it exists
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Cleaned up bad temp file: {temp_file}")
                    except Exception:
                        pass  # Ignore cleanup errors
                raise Exception(f"Failed to create valid output file: {str(e)}")
                
            # If verification passed, move the temp file to the target location
            import shutil
            try:
                # Check if the current file location is writable
                current_file_dir = os.path.dirname(current_file)
                is_dir_writable = os.access(current_file_dir, os.W_OK)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Target directory writable: {is_dir_writable}")
                
                if not is_dir_writable:
                    logger.error("ImageViewer", f"Target directory not writable: {current_file_dir}")
                    raise Exception(f"Cannot write to target directory: {current_file_dir}")
                
                # On some platforms (especially Windows), we might need to remove the target first
                if os.path.exists(current_file):
                    os.remove(current_file)
                shutil.copy2(temp_file, current_file)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Copied temp file to target: {current_file}")
                # Remove the temp file after successful copy
                os.remove(temp_file)
            except Exception as e:
                logger.error("ImageViewer", f"Error replacing original file: {str(e)}")
                # Try to restore from backup if copying failed
                if os.path.exists(backup_file):
                    shutil.copy2(backup_file, current_file)
                    logger.warning("ImageViewer", f"Restored from backup after move failure")
                raise Exception(f"Failed to replace original file: {str(e)}")
            
            # Keep only the 5 most recent backups for this file to avoid clutter
            self.cleanup_old_backups(current_filename)
            
            # Clean up any old temp files
            self.cleanup_old_temp_files()
            
            self.show_status_message(f"Saved changes to {current_filename}")
            logger.info("ImageViewer", f"Successfully saved changes to {current_filename}")
        except Exception as e:
            logger.error("ImageViewer", f"Error saving file: {str(e)}")
            self.show_status_message(f"Error saving file: {str(e)}", self.error_color)

    def cleanup_old_backups(self, base_filename):
        """
        Keep only the 5 most recent backups for a specific file.
        
        Args:
            base_filename: The base filename to clean up backups for
        """
        try:
            # Get all backup files for this filename
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith(base_filename + ".backup."):
                    full_path = os.path.join(self.backup_dir, filename)
                    backup_files.append((full_path, os.path.getmtime(full_path)))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Keep only the 5 most recent backups
            for file_path, _ in backup_files[5:]:
                os.remove(file_path)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Removed old backup: {os.path.basename(file_path)}")
        except Exception as e:
            logger.debug_at_level(DEBUG_L2, "ImageViewer", f"Error cleaning up old backups: {str(e)}")

    def cleanup_old_temp_files(self):
        """Clean up temporary files older than 1 hour."""
        try:
            current_time = time.time()
            for filename in os.listdir(self.temp_dir):
                if ".temp." in filename:
                    file_path = os.path.join(self.temp_dir, filename)
                    # Check file age
                    file_age = current_time - os.path.getmtime(file_path)
                    # Remove files older than 1 hour
                    if file_age > 3600:
                        os.remove(file_path)
                        logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Removed old temp file: {filename}")
        except Exception as e:
            logger.debug_at_level(DEBUG_L2, "ImageViewer", f"Error cleaning up temp files: {str(e)}")

    def cleanup_temp_files(self, directory):
        """
        DEPRECATED: Use cleanup_old_temp_files() instead.
        This method is kept for compatibility with existing code.
        """
        self.cleanup_old_temp_files()

    def prepare_image(self, arr):
        """Convert a depth array to a displayable PIL image."""
        # Normalize to 0-255 range for display
        depth_min = np.min(arr)
        depth_max = np.max(arr)
        
        if depth_max > depth_min:
            normalized = ((arr - depth_min) / (depth_max - depth_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros_like(arr, dtype=np.uint8)
        
        # Create PIL image
        img = Image.fromarray(normalized)
        return img
    
    def next_file(self):
        """Load the next file in the dataset."""
        if not self.npz_files:
            return
        
        # Save any changes to the current file
        self.save_current_file_if_modified()
        
        # Move to the next file
        self.current_file_idx = (self.current_file_idx + 1) % len(self.npz_files)
        
        # Load the new file
        self.load_file()
    
    def prev_file(self):
        """Load the previous file in the dataset."""
        if not self.npz_files:
            return
        
        # Save any changes to the current file
        self.save_current_file_if_modified()
        
        # Move to the previous file
        self.current_file_idx = (self.current_file_idx - 1) % len(self.npz_files)
        
        # Load the new file
        self.load_file()
    
    def save_current_file_if_modified(self):
        """Check if the current file has been modified and save it if needed."""
        if not self.current_batch:
            return
        
        # Check if any flip actions have been applied
        try:
            # Check if any flip actions have been applied
            if any(self.flip_actions):
                logger.info("ImageViewer", "Saving changes before switching files")
                self.save_current_file()
                
                # Reset flip actions after saving
                self.flip_actions = [None] * len(self.current_batch['depths'])
                self.flipped_images = None
        except Exception as e:
            logger.error("ImageViewer", f"Error checking for modifications: {str(e)}")
            # Reset to prevent further errors
            self.flip_actions = []
            self.flipped_images = None
    
    def update_file_selector(self):
        """Update the file selector with the current file names."""
        if self.file_display_names:
            self.file_selector['values'] = self.file_display_names
            self.file_selector.current(self.current_file_idx)
            
    
    def setup_batch_grid(self):
        """Set up the grid for batch view."""
        try:
            # Clear existing grid contents
            for widget in self.grid_frame.winfo_children():
                widget.destroy()
            
            self.thumbnail_labels = []
            self.thumbnail_photos = []
            
            if self.current_batch is None or not hasattr(self.current_batch, 'files') or 'depths' not in self.current_batch.files:
                self.debug_print("No batch or missing depth data")
                return
            
            depths = self.current_batch['depths']
            batch_size = len(depths)
            
            # Fixed grid dimensions: 2 rows, 5 columns
            rows = 2
            cols = 5
            
            # Create main container for all grid-related widgets
            main_container = ttk.Frame(self.grid_frame)
            main_container.pack(fill=tk.BOTH, expand=True)
            
            # Add width adjustment slider at the top
            slider_frame = ttk.Frame(main_container)
            # We're not adding any controls to the slider_frame, so don't pack it
            # slider_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
            
            # Fixed grid width at 88%
            self.grid_width_value = 88
            
            # Get window width and calculate grid width based on fixed percentage
            win_width = self.root.winfo_width() or 900  # Default if not yet rendered
            grid_width_percent = self.grid_width_value / 100
            grid_width = int(win_width * grid_width_percent)
            
            # Use stored height value or default
            grid_height = getattr(self, 'grid_height_value', 300)
            
            # Create a canvas for the grid to support scrolling for large batches
            canvas_frame = ttk.Frame(main_container, style="Canvas.TFrame")
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Style for canvas frame with border
            style = ttk.Style()
            style.configure("Canvas.TFrame", borderwidth=1, relief="solid")
            
            # Create a canvas with scrollbars for both vertical and horizontal scrolling
            self.canvas = tk.Canvas(canvas_frame, bg=self.bg_color, bd=0, highlightthickness=0, 
                             height=grid_height)  # Set explicit height
            v_scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
            h_scrollbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
            self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Enable mouse wheel scrolling
            def _on_mousewheel(event):
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            def _on_shift_mousewheel(event):
                if event.state & 0x0001:  # Check if shift is pressed
                    self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")
                else:
                    self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            # Bind mouse wheel events
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
            self.canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)
            
            # Frame inside canvas for the grid
            inner_frame = ttk.Frame(self.canvas)
            self.canvas.create_window((0, 0), window=inner_frame, anchor="nw", width=grid_width)
            
            # Fixed display of 2 rows x 5 columns = 10 images
            max_images = min(batch_size, rows * cols)
            
            # Create a container frame for the 2x5 grid
            grid_container = ttk.Frame(inner_frame)
            grid_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Configure grid container for even spacing across full width
            for c in range(cols):
                grid_container.columnconfigure(c, weight=1)  # Equal width columns
            
            # Configure rows with consistent height
            for r in range(rows):
                grid_container.rowconfigure(r, weight=1)  # Equal height rows
            
            # Calculate thumbnail size based on grid width
            available_width = grid_width - 100  # Account for padding, borders, and scrollbar
            thumb_width = max(100, min(180, (available_width // cols) - 20))  # Ensure reasonable size range
            self.thumb_size = (thumb_width, thumb_width)
            
            for i in range(max_images):
                # Calculate row and column
                r = i // cols
                c = i % cols
                
                # Create frame for this thumbnail
                frame = tk.Frame(grid_container, bg=self.bg_color)
                frame.grid(row=r, column=c, padx=5, pady=5)
                
                try:
                    # Process the image
                    img_array = depths[i]
                    
                    # Apply flip if needed
                    if self.flip_actions[i]:
                        if self.flip_actions[i] == "fliplr":
                            img_array = np.fliplr(img_array)
                        elif self.flip_actions[i] == "flipud":
                            img_array = np.flipud(img_array)
                        elif self.flip_actions[i] == "both":
                            img_array = np.flipud(np.fliplr(img_array))
                    
                    pil_img = self.prepare_image(img_array)
                    pil_thumb = pil_img.resize(self.thumb_size, Image.NEAREST)
                    photo = ImageTk.PhotoImage(pil_thumb)
                    
                    # Create background color based on flip state
                    # Use light blue background if the image has been flipped
                    bg_color = "#d4e6f1" if self.flip_actions[i] else "white"  # Light blue for flipped
                    
                    # Create card-like frame for the image with fixed size
                    card_frame = tk.Frame(frame, bd=1, relief=tk.SOLID, 
                                       bg=bg_color, padx=2, pady=2,
                                       width=thumb_width+10, height=thumb_width+30)
                    card_frame.pack(padx=5, pady=5)
                    card_frame.pack_propagate(False)  # Prevent the frame from resizing to fit content
                    
                    # Create and add image label with appropriate background
                    img_label = tk.Label(card_frame, image=photo, bg=bg_color)
                    img_label.pack(pady=(5, 2))
                    
                    # Bind click event to show full-size image
                    img_label.bind("<Button-1>", lambda event, idx=i: self.show_full_size_image(idx))
                    
                    # Store references to prevent garbage collection
                    self.thumbnail_photos.append(photo)
                    self.thumbnail_labels.append(img_label)
                    
                    # Add image number and flip indicator
                    flip_text = f"Image #{i+1}" + (" (flipped)" if self.flip_actions[i] else "")
                    num_label = tk.Label(card_frame, text=flip_text, bg=bg_color,
                                      font=("Helvetica", 8))
                    num_label.pack(pady=(2, 4))
                    
                    # Update every 20 images to keep UI responsive
                    if i % 20 == 0:
                        self.root.update_idletasks()
                        
                except Exception as e:
                    logger.error("ImageViewer", f"Error processing image {i}: {str(e)}")
                    # Create a text label as fallback
                    error_label = tk.Label(frame, text=f"Image {i+1}\nError", 
                                         width=thumb_width//10, height=thumb_width//12, 
                                         bg="#f0f0f0")
                    error_label.pack(pady=5)
            
            # If there are more images than displayed, add a message
            if batch_size > max_images:
                more_frame = ttk.Frame(grid_container)
                more_frame.pack(fill=tk.X, pady=5)
                
                more_label = ttk.Label(more_frame, text=f"+ {batch_size - max_images} more images not shown",
                                    font=("Helvetica", 9, "italic"), foreground="#7f8c8d")
                more_label.pack(pady=5)
            
            # Update the canvas scrollregion
            inner_frame.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        except Exception as e:
            logger.error("ImageViewer", f"Error in setup_batch_grid: {str(e)}")
            self.show_status_message(f"Error displaying images: {str(e)}", self.error_color)

    def batch_flip_lr(self):
        """Flip all images in the current batch left-to-right."""
        if not self.npz_files or 'depths' not in self.current_batch:
            return
            
        logger.debug_at_level(DEBUG_L1, "ImageViewer", "Performing batch left-right flip")
        depths = self.current_batch['depths']
        
        # Create a flipped copy
        if self.flipped_images is None:
            self.flipped_images = depths.copy()
        
        # Check dimensions and use appropriate axis
        ndim = self.flipped_images.ndim
        flip_axis = min(2, ndim - 1)  # Use axis 2 for 3D+ arrays, axis 1 for 2D arrays
        logger.debug_at_level(DEBUG_L2, "ImageViewer", f"Left-right flip using axis {flip_axis} for {ndim}D array")
        
        # Flip left-right with appropriate axis
        self.flipped_images = np.flip(self.flipped_images, axis=flip_axis)
        
        # Update flip actions for tracking
        for i in range(len(depths)):
            if self.flip_actions[i] is None:
                self.flip_actions[i] = "fliplr"
            elif self.flip_actions[i] == "fliplr":
                self.flip_actions[i] = None
            elif self.flip_actions[i] == "flipud":
                self.flip_actions[i] = "both"
            elif self.flip_actions[i] == "both":
                self.flip_actions[i] = "flipud"
        
        # Update the display
        self.show_status_message("Flipped all images left-right")
        self.update_batch_grid()
        
        # Update legend status
        self.update_legend_status()
        
        # Apply auto-advance if activated
        if self.auto_advance and self.last_auto_action == "fliplr":
            self.root.after(1000, self.auto_advance_step)
        
        logger.debug_at_level(DEBUG_L2, "ImageViewer", "Batch flip LR completed")
    
    def batch_flip_ud(self):
        """Flip all images in the current batch up-down."""
        if not self.npz_files or 'depths' not in self.current_batch:
            return
            
        logger.debug_at_level(DEBUG_L1, "ImageViewer", "Performing batch up-down flip")
        depths = self.current_batch['depths']
        
        # Create a flipped copy
        if self.flipped_images is None:
            self.flipped_images = depths.copy()
        
        # Check dimensions and use appropriate axis
        ndim = self.flipped_images.ndim
        if ndim >= 3:
            flip_axis = 1  # For 3D+ arrays, use axis 1 (height)
        else:
            flip_axis = 0  # For 2D arrays, use axis 0
        logger.debug_at_level(DEBUG_L2, "ImageViewer", f"Up-down flip using axis {flip_axis} for {ndim}D array")
        
        # Flip up-down with appropriate axis
        self.flipped_images = np.flip(self.flipped_images, axis=flip_axis)
        
        # Update flip actions for tracking
        for i in range(len(depths)):
            if self.flip_actions[i] is None:
                self.flip_actions[i] = "flipud"
            elif self.flip_actions[i] == "flipud":
                self.flip_actions[i] = None
            elif self.flip_actions[i] == "fliplr":
                self.flip_actions[i] = "both"
            elif self.flip_actions[i] == "both":
                self.flip_actions[i] = "fliplr"
        
        # Update the display
        self.show_status_message("Flipped all images up-down")
        self.update_batch_grid()
        
        # Update legend status
        self.update_legend_status()
        
        # Apply auto-advance if activated
        if self.auto_advance and self.last_auto_action == "flipud":
            self.root.after(1000, self.auto_advance_step)
        
        logger.debug_at_level(DEBUG_L2, "ImageViewer", "Batch flip UD completed")
    
    def toggle_flip_action(self, idx, action):
        """
        Toggle a flip action for a specific image.
        
        Args:
            idx: Index of the image
            action: Type of flip action ("fliplr" or "flipud")
        """
        current = self.flip_actions[idx]
        
        if current is None:
            # No action, set to the new action
            self.flip_actions[idx] = action
        elif current == action:
            # Same action, remove it
            self.flip_actions[idx] = None
        elif current == "both":
            # Both actions, remove the specified action
            self.flip_actions[idx] = "flipud" if action == "fliplr" else "fliplr"
        else:
            # Different action, set to both
            self.flip_actions[idx] = "both"
        
        logger.debug_at_level(DEBUG_L2, "ImageViewer", f"Image {idx}: flipped to {self.flip_actions[idx]}")
    
    def show_batch_grid(self):
        """Display all images in the current batch as a grid."""
        if not self.current_batch:
            return
        
        self.setup_batch_grid()
    
    def update_batch_grid(self):
        """Update the existing batch grid with current flip states."""
        if not self.current_batch or not self.thumbnail_labels:
            return
        
        # The current implementation only updates the background color, not the actual images
        # We need to completely rebuild the grid to show the flipped images
        self.setup_batch_grid()
        
        # The old implementation only updated the background colors:
        # for i, container in enumerate(self.thumbnail_labels):
        #     if self.flip_actions[i]:
        #         container.configure(background=self.accent_color)
        #     else:
        #         container.configure(background=self.border_color)
    
    def toggle_auto_advance(self, action_type):
        """
        Toggle auto-advance mode for a specific action type.
        
        Args:
            action_type: The type of flip action to apply ("fliplr" or "flipud")
        """
        # If already running, stop
        if self.auto_advance and self.last_auto_action == action_type:
            self.stop_auto_advance()
        else:
            self.start_auto_advance(action_type)
    
    def start_auto_advance(self, action_type):
        """
        Start auto-advance with a specific flip action.
        
        Args:
            action_type: The type of flip action to apply ("fliplr" or "flipud")
        """
        logger.info("ImageViewer", f"Starting auto-advance with {action_type}")
        
        # Update button states
        self.auto_ud_btn.config(state=tk.DISABLED if action_type == "flipud" else tk.NORMAL)
        self.auto_lr_btn.config(state=tk.DISABLED if action_type == "fliplr" else tk.NORMAL)
        self.auto_stop_btn.config(state=tk.NORMAL)
        
        # Save current file if modified
        self.save_current_file_if_modified()
        
        # Update auto-advance state
        self.auto_advance = True
        self.last_auto_action = action_type
        
        # Schedule first auto-advance step
        if self.auto_advance_id is not None:
            self.root.after_cancel(self.auto_advance_id)
        
        # Apply the action to the current file first, then proceed
        if action_type == "fliplr":
            self.batch_flip_lr()
        else:
            self.batch_flip_ud()
        
        # Update status
        self.update_auto_status()
    
    def auto_advance_step(self):
        """Process one step of auto-advance."""
        if not self.auto_advance:
            return
        
        logger.debug_at_level(DEBUG_L2, "ImageViewer", "Auto-advance step")
        
        # Save current file if modified
        self.save_current_file_if_modified()
        
        # Move to the next file
        self.current_file_idx = (self.current_file_idx + 1) % len(self.npz_files)
        
        # Load the new file
        self.load_file()
        
        # Apply the flip action to the new file
        self.apply_auto_action()
        
        # Update status
        self.update_auto_status()
    
    def apply_auto_action(self):
        """Apply the current auto-advance action to the current file."""
        if not self.auto_advance or not self.last_auto_action:
            return
        
        # Apply the appropriate action
        if self.last_auto_action == "fliplr":
            self.batch_flip_lr()
        else:
            self.batch_flip_ud()
    
    def stop_auto_advance(self):
        """Stop auto-advance mode."""
        if not self.auto_advance:
            return
        
        logger.info("ImageViewer", "Stopping auto-advance")
        
        # Update button states
        self.auto_ud_btn.configure(state=tk.NORMAL)
        self.auto_lr_btn.configure(state=tk.NORMAL)
        self.auto_stop_btn.configure(state=tk.DISABLED)
        
        # Update auto-advance state
        self.auto_advance = False
        self.last_auto_action = None
        
        # Cancel any pending auto-advance
        if self.auto_advance_id is not None:
            self.root.after_cancel(self.auto_advance_id)
            self.auto_advance_id = None
        
        # Update status
        self.auto_label.configure(text="")
    
    def update_auto_status(self):
        """Update the auto-advance status indicator."""
        if not self.auto_advance:
            self.auto_label.configure(text="")
            return
        
        # Show current status
        action_name = "Left-Right" if self.last_auto_action == "fliplr" else "Up-Down"
        current_pos = f"{self.current_file_idx + 1}/{len(self.npz_files)}"
        self.auto_label.configure(text=f"Auto-Advance: {action_name} ({current_pos})")
    
    def jump_to_selected_file(self):
        """
        Jump to the selected file in the dropdown.
        If the current file is already selected, act as a "Next" button.
        """
        # Get selected file index
        selected_idx = self.file_selector.current()
        
        # If already on this file, just go to next (treat as "Next" button)
        if selected_idx == self.current_file_idx:
            self.debug_print(f"Already on selected file, moving to next")
            self.next_file()
            return
        
        # Save current file if modified
        self.save_current_file_if_modified()
        
        # Change displayed batch
        self.current_file_idx = selected_idx
        self.debug_print(f"Jumping to file: {self.npz_files[self.current_file_idx]}")
        self.load_file()
        
        # Update UI
        self.file_selector.current(self.current_file_idx)
        self.show_status_message(f"Loaded file: {self.file_display_names[self.current_file_idx]}")
        
        # Apply batch preview if applicable
        if hasattr(self, 'preview_var') and self.preview_var.get():
            self.update_batch_preview()
    
    def debug_print(self, message):
        """Print a debug message if debug mode is enabled."""
        if self.debug_mode:
            self.logger.debug_at_level(DEBUG_L2, "DepthViewer", message)
    
    def show_status_message(self, message, color=None, duration=3000):
        """
        Show a status message for a specified duration.
        
        Args:
            message: The message to display
            color: Text color (default: None - uses success_color)
            duration: Duration in milliseconds (default: 3000ms)
        """
        if color is None:
            color = self.success_color
        
        self.status_label.configure(text=message, foreground=color)
        
        # Clear the message after the duration
        def _clear_status():
            # Only clear if this message is still showing
            if self.status_label.cget("text") == message:
                self.status_label.configure(text="")
        
        # Cancel any existing timers and set a new one
        if hasattr(self, "_status_timer_id") and self._status_timer_id:
            self.root.after_cancel(self._status_timer_id)
        
        self._status_timer_id = self.root.after(duration, _clear_status)

    def browse_directory(self):
        """Open a file dialog to select a dataset directory."""
        directory = filedialog.askdirectory(
            initialdir=self.dataset_dir,
            title="Select Dataset Directory"
        )
        
        if directory:  # If a directory was selected
            self.dataset_dir = directory
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, self.dataset_dir)
            
            # Update temp and backup directories
            self.initialize_temp_backup_dirs()
            
            self.reload_directory()
    
    def reload_directory(self):
        """Reload files from the current dataset directory."""
        # Get directory from entry field
        entered_dir = self.dir_entry.get().strip()
        if entered_dir and entered_dir != self.dataset_dir:
            self.dataset_dir = entered_dir
        
        # Save current file if modified
        self.save_current_file_if_modified()
        
        # Reset state
        self.current_file_idx = 0
        self.current_batch = None
        
        # Update temp and backup directories to be in the new dataset directory
        self.initialize_temp_backup_dirs()
        
        # Find files in the new directory
        self.npz_files = self.find_npz_files()
        
        # Update file display names
        self.file_display_names = []
        for file_path in self.npz_files:
            basename = os.path.basename(file_path)
            display_name = os.path.splitext(basename)[0]
            self.file_display_names.append(display_name)
        
        # Update UI
        self.update_file_selector()
        
        # Load first file if available
        self.load_initial_file()
        
        # Show status message
        file_count = len(self.npz_files)
        if file_count > 0:
            self.show_status_message(f"Loaded {file_count} files from {self.dataset_dir}")
            
            # Apply batch preview if applicable
            if hasattr(self, 'preview_var') and self.preview_var.get():
                self.update_batch_preview()
        else:
            self.show_status_message("No .npz files found in the selected directory", self.warning_color)
            # Clear the grid frame
            for widget in self.grid_frame.winfo_children():
                widget.destroy()
            self.info_text.configure(text="No files found")

    def update_batch_preview(self, *args):
        """Update the viewer to show a preview of the selected flip operation."""
        # Only show preview if checkbox is selected
        if not hasattr(self, 'preview_var') or not self.preview_var.get():
            return
            
        # Only proceed if we have a current batch
        if not self.current_batch or 'depths' not in self.current_batch:
            return
        
        try:    
            # Get flip type
            flip_type = self.flip_type_var.get()
            logger.debug_at_level(DEBUG_L1, "BatchPreview", f"Updating preview for flip type: {flip_type}")
            
            # Reset all flip actions
            self.flip_actions = [None] * len(self.current_batch['depths'])
            
            # Don't apply any flips if none is selected
            if flip_type == "none":
                # Clear all flips
                self.flipped_images = None
                self.setup_batch_grid()  # Complete refresh of the grid
                # Update legend
                self.update_legend_status()
                return
                
            # Set appropriate flip action for all images
            for i in range(len(self.current_batch['depths'])):
                self.flip_actions[i] = flip_type
                
            # Reset flipped images cache
            self.flipped_images = None
            
            # Update the grid display with complete refresh to show flipped images
            self.setup_batch_grid()
            
            # Update the legend
            self.update_legend_status()
            
            self.show_status_message(f"Preview: {flip_type} flip")
        except Exception as e:
            logger.error("BatchPreview", f"Error updating preview: {str(e)}")
            self.show_status_message(f"Error updating preview: {str(e)}", self.error_color)

    def quick_flip_preview(self, flip_type):
        """Apply a quick flip preview with the specified type."""
        # Update the flip type variable to trigger the preview
        self.flip_type_var.set(flip_type)
        
        # Force update in case the value didn't change
        self.update_batch_preview()
        
        # Update legend
        self.update_legend_status()
        
        # Show a status message
        if flip_type == "none":
            self.show_status_message("Reset preview to original images")
        else:
            self.show_status_message(f"Applied {flip_type} preview to all images")

    def update_legend_status(self):
        """Update the legend to reflect the current flip status."""
        if not hasattr(self, 'flipped_sample') or not hasattr(self, 'orig_sample'):
            return
        
        if not self.current_batch or not hasattr(self, 'flip_actions') or not self.flip_actions:
            return
        
        # Count the number of flipped images
        flipped_count = sum(1 for a in self.flip_actions if a is not None)
        total_count = len(self.flip_actions)
        
        # If all images have the same flip status
        if flipped_count == 0:
            # No flip - highlight original color
            self.orig_sample.configure(bg="white")
            self.flipped_sample.configure(bg="#d4e6f1")  # Light blue for flipped
            
            if hasattr(self, 'flip_status'):
                self.flip_status.configure(text="No flip applied")
        
        elif flipped_count == total_count:
            # All flipped - check if same type
            flip_types = set(a for a in self.flip_actions if a is not None)
            
            # Highlight flipped color
            self.orig_sample.configure(bg="white")
            self.flipped_sample.configure(bg="#d4e6f1")  # Light blue for flipped
            
            if hasattr(self, 'flip_status'):
                if len(flip_types) == 1:
                    flip_type = list(flip_types)[0]
                    if flip_type == "fliplr":
                        self.flip_status.configure(text="All flipped left-right")
                    elif flip_type == "flipud":
                        self.flip_status.configure(text="All flipped up-down")
                    elif flip_type == "both":
                        self.flip_status.configure(text="All flipped both ways")
                else:
                    self.flip_status.configure(text="Mixed flips applied")
        
        else:
            # Some flipped, some not
            self.orig_sample.configure(bg="white")
            self.flipped_sample.configure(bg="#d4e6f1")  # Light blue for flipped
            
            if hasattr(self, 'flip_status'):
                self.flip_status.configure(text=f"Mixed flips ({flipped_count}/{total_count} flipped)")

    def on_window_resize(self, event):
        """Handle window resize events to reflow the grid."""
        # Only handle resizes on the root window
        if event.widget != self.root:
            return
            
        # Only update if we have a batch loaded
        if not self.current_batch or not hasattr(self, 'last_resize_time'):
            # Store the current time for debouncing
            self.last_resize_time = time.time()
            return
            
        # Debounce the resize event to avoid excessive updates
        current_time = time.time()
        if current_time - self.last_resize_time < 0.5:  # 500ms debounce
            # Cancel any pending update
            if hasattr(self, 'resize_timer') and self.resize_timer:
                self.root.after_cancel(self.resize_timer)
                
            # Schedule a new update
            self.resize_timer = self.root.after(500, self.update_grid_on_resize)
        else:
            # It's been more than the debounce time, update immediately
            self.update_grid_on_resize()
            
        # Update the last resize time
        self.last_resize_time = current_time
        
    def update_grid_on_resize(self):
        """Update the grid layout after a window resize."""
        # Ensure the grid width value is set to 88%
        self.grid_width_value = 88
        
        # Completely rebuild the grid to use the new window size
        self.setup_batch_grid()

    def toggle_preview(self):
        """Toggle the preview functionality on/off."""
        if hasattr(self, 'preview_var') and self.preview_var.get():
            # Preview enabled - add trace for automatic updates and update now
            try:
                # First remove any existing trace to avoid duplicates
                for trace_id in self.flip_type_var.trace_info():
                    if trace_id[0] == "write":
                        self.flip_type_var.trace_remove("write", trace_id[1])
                
                # Add new trace
                self.flip_type_var.trace_add("write", self.update_batch_preview)
                
                # Update the preview now
                self.update_batch_preview()
                self.show_status_message("Preview enabled - flip changes will be shown immediately")
            except Exception as e:
                logger.error("ImageViewer", f"Error enabling preview: {e}")
                self.show_status_message(f"Error enabling preview: {e}", self.error_color)
        else:
            # Preview disabled - remove trace and clear preview
            try:
                if hasattr(self, 'flip_type_var'):
                    for trace_id in self.flip_type_var.trace_info():
                        if trace_id[0] == "write":
                            self.flip_type_var.trace_remove("write", trace_id[1])
                
                # Reset the flip actions to clear preview
                if self.current_batch and hasattr(self, 'flip_actions'):
                    self.flip_actions = [None] * len(self.current_batch['depths'])
                    self.flipped_images = None
                    self.setup_batch_grid()
                    self.update_legend_status()
                
                self.show_status_message("Preview disabled - showing original images")
            except Exception as e:
                logger.error("ImageViewer", f"Error disabling preview: {e}")
                self.show_status_message(f"Error disabling preview: {e}", self.error_color)

    def initialize_temp_backup_dirs(self):
        """Initialize temporary and backup directories in the current dataset directory."""
        # Make sure the dataset directory exists
        os.makedirs(self.dataset_dir, exist_ok=True)
        
        # Use system temp directory instead of custom directory for temporary files
        import tempfile
        self.temp_dir = tempfile.gettempdir()
        
        # Backup directory still in dataset directory
        self.backup_dir = os.path.join(self.dataset_dir, ".backup")
        
        # Create directories if they don't exist
        try:
            # Temp dir should already exist since it's the system temp dir
            if not os.path.exists(self.temp_dir):
                logger.error("ImageViewer", f"System temp directory doesn't exist: {self.temp_dir}")
            else:
                # Check if the temp directory is writable
                test_writable = os.access(self.temp_dir, os.W_OK)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Temp directory writable: {test_writable}")
                if not test_writable:
                    logger.error("ImageViewer", f"Temp directory not writable: {self.temp_dir}")
            
            # Create backup directory
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Verify that the directories were created
            if not os.path.exists(self.backup_dir):
                logger.error("ImageViewer", f"Failed to create backup directory: {self.backup_dir}")
            else:
                # Check if the backup directory is writable
                test_writable = os.access(self.backup_dir, os.W_OK)
                logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Backup directory writable: {test_writable}")
                if not test_writable:
                    logger.error("ImageViewer", f"Backup directory not writable: {self.backup_dir}")
                
            logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Using system temp directory: {self.temp_dir}")
            logger.debug_at_level(DEBUG_L1, "ImageViewer", f"Initialized backup directory: {self.backup_dir}")
        except Exception as e:
            logger.error("ImageViewer", f"Error initializing temp/backup directories: {str(e)}")

    def _toggle_verbose_mode(self):
        """Toggle verbose logging mode on or off."""
        verbose = self.verbose_var.get()
        try:
            # Configure logger with new verbose setting
            # This preserves the current console level and debug level
            console_level = LOG_LEVEL_DEBUG if verbose else LOG_LEVEL_INFO
            debug_level = getattr(self, 'debug_level_var', tk.IntVar(value=DEBUG_L1)).get()
            
            logger.configure(
                verbose=verbose,
                console_level=console_level,
                debug_level=debug_level,
                colored_output=True
            )
            
            # Store the verbose setting in the instance
            self.debug_mode = verbose
            
            # Show appropriate message
            if verbose:
                self.show_status_message("Verbose mode enabled")
            else:
                self.show_status_message("Verbose mode disabled")
        except Exception as e:
            self.show_status_message(f"Error setting verbose mode: {str(e)}", self.error_color)

    def show_full_size_image(self, image_idx):
        """Show a full-size version of the selected image in a new window."""
        try:
            if not self.current_batch or 'depths' not in self.current_batch:
                return
            
            depths = self.current_batch['depths']
            if image_idx >= len(depths):
                return
            
            # Get the image data
            img_array = depths[image_idx]
            
            # Apply flip if needed
            if self.flip_actions[image_idx]:
                if self.flip_actions[image_idx] == "fliplr":
                    img_array = np.fliplr(img_array)
                elif self.flip_actions[image_idx] == "flipud":
                    img_array = np.flipud(img_array)
                elif self.flip_actions[image_idx] == "both":
                    img_array = np.flipud(np.fliplr(img_array))
            
            # Create a new top-level window
            popup = tk.Toplevel(self.root)
            popup.title(f"Full Size Image #{image_idx + 1}")
            
            # Create a frame to hold the image with scrollbars
            frame = ttk.Frame(popup)
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Create canvas with scrollbars
            canvas = tk.Canvas(frame, bg=self.bg_color)
            v_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            h_scrollbar = ttk.Scrollbar(frame, orient="horizontal", command=canvas.xview)
            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Prepare the image at full resolution
            pil_img = self.prepare_image(img_array)
            
            # Get image dimensions
            img_width, img_height = pil_img.size
            
            # Create a PhotoImage object
            photo = ImageTk.PhotoImage(pil_img)
            
            # Create a label to display the image
            img_label = tk.Label(canvas, image=photo, bg=self.bg_color)
            img_label.image = photo  # Keep a reference to prevent garbage collection
            
            # Add the label to the canvas
            canvas.create_window((0, 0), window=img_label, anchor="nw")
            
            # Configure the scrollregion
            canvas.configure(scrollregion=canvas.bbox("all"))
            
            # Use a fixed window size instead of calculating based on image dimensions
            # You can adjust these values to your preferred window size
            fixed_width = 538   # Fixed width in pixels
            fixed_height = 570   # Fixed height in pixels
            
            # Update window size with fixed dimensions
            popup.geometry(f"{fixed_width}x{fixed_height}")
            
            # Add image info at the bottom
            info_frame = ttk.Frame(popup)
            info_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Show image dimensions and flip status
            flip_status = "Original"
            if self.flip_actions[image_idx] == "fliplr":
                flip_status = "Flipped Left-Right"
            elif self.flip_actions[image_idx] == "flipud":
                flip_status = "Flipped Up-Down"
            elif self.flip_actions[image_idx] == "both":
                flip_status = "Flipped Both Ways"
            
            info_text = f"Image #{image_idx + 1} • Size: {img_width}x{img_height} • Status: {flip_status}"
            info_label = ttk.Label(info_frame, text=info_text)
            info_label.pack(side=tk.LEFT)
            
            # Add a close button
            close_btn = ttk.Button(info_frame, text="Close", command=popup.destroy)
            close_btn.pack(side=tk.RIGHT, padx=5)
            
            # Add a button to show 3D visualization
            view_3d_btn = ttk.Button(info_frame, text="View 3D", 
                                  command=lambda: self.show_3d_visualization(image_idx))
            view_3d_btn.pack(side=tk.RIGHT, padx=5)
            
            # Enable mouse wheel scrolling on the canvas
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            def _on_shift_mousewheel(event):
                if event.state & 0x0001:  # Check if shift is pressed
                    canvas.xview_scroll(int(-1*(event.delta/120)), "units")
                else:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            # Bind mouse wheel events
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)
            
            # Focus the popup window
            popup.focus_set()
            
            # Center the popup on the screen
            screen_width = popup.winfo_screenwidth()
            screen_height = popup.winfo_screenheight()
            x = (screen_width - fixed_width) // 2
            y = (screen_height - fixed_height) // 2
            popup.geometry(f"+{x}+{y}")
            
        except Exception as e:
            logger.error("ImageViewer", f"Error showing full-size image: {str(e)}")
            self.show_status_message(f"Error showing full-size image: {str(e)}", self.error_color)
    
    def show_3d_visualization(self, image_idx):
        """Create and display a 3D visualization of the depth image."""
        try:
            if not self.current_batch or 'depths' not in self.current_batch:
                self.show_status_message("No depth data available", self.error_color)
                return
            
            depths = self.current_batch['depths']
            if image_idx >= len(depths):
                self.show_status_message("Invalid image index", self.error_color)
                return
            
            # Get the image data
            img_array = depths[image_idx]
            
            # Apply flip if needed
            if self.flip_actions[image_idx]:
                if self.flip_actions[image_idx] == "fliplr":
                    img_array = np.fliplr(img_array)
                elif self.flip_actions[image_idx] == "flipud":
                    img_array = np.flipud(img_array)
                elif self.flip_actions[image_idx] == "both":
                    img_array = np.flipud(np.fliplr(img_array))
            
            # Create a new top-level window
            popup = tk.Toplevel(self.root)
            popup.title(f"3D Visualization - Image #{image_idx + 1}")
            
            # Set a reasonable size for the 3D visualization window
            # For 3D visualization, we want a bit more space than the image dimensions
            # to accommodate the 3D plot, colorbar, and controls
            screen_width = popup.winfo_screenwidth()
            screen_height = popup.winfo_screenheight()
            
            # Get image dimensions
            height, width = img_array.shape
            
            # Calculate window size with appropriate aspect ratio
            # Use a minimum size for small images
            min_width = 800
            min_height = 600
            
            # Calculate a good size based on image dimensions
            # We use a larger multiplier for 3D visualization to give room for the plot
            window_width = max(min_width, min(int(width * 1.5), int(screen_width * 0.9)))
            window_height = max(min_height, min(int(height * 1.5), int(screen_height * 0.9)))
            
            # Set the window size
            popup.geometry(f"{window_width}x{window_height}")
            
            # Create a style for the view buttons - larger and more visible
            style = ttk.Style()
            style.configure("ViewBtn.TButton", font=("Helvetica", 11, "bold"), padding=6)
            
            # Create a separate frame for view angle controls at the top of the window
            view_controls_frame = ttk.Frame(popup)
            view_controls_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Add view angle controls in a more prominent position
            view_frame = ttk.LabelFrame(view_controls_frame, text="View Angle Controls")
            view_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Create a frame for the buttons with even spacing
            buttons_frame = ttk.Frame(view_frame)
            buttons_frame.pack(pady=5, fill=tk.X)
            
            # Make the buttons evenly spaced
            for i in range(4):  # Changed from 5 to 4 columns since we're removing one button
                buttons_frame.columnconfigure(i, weight=1)
            
            # Create main frame for the plot
            main_frame = ttk.Frame(popup)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Create a matplotlib figure
            fig = Figure(figsize=(10, 8), dpi=100)
            ax = fig.add_subplot(111, projection='3d')
            
            # Create coordinate grids
            x = np.arange(0, width, 1)
            y = np.arange(0, height, 1)
            X, Y = np.meshgrid(x, y)
            
            # Create the 3D surface plot
            # Normalize depth values for better visualization
            Z = img_array.copy()
            
            # Handle NaN or inf values
            Z = np.nan_to_num(Z, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Plot the surface
            surf = ax.plot_surface(X, Y, Z, cmap='viridis', 
                                 linewidth=0, antialiased=True, alpha=0.8)
            
            # Add a color bar
            fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
            
            # Set labels
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            ax.set_zlabel('Depth')
            ax.set_title(f'3D Visualization of Depth Image #{image_idx + 1}')
            
            # Create a canvas to display the matplotlib figure
            canvas = FigureCanvasTkAgg(fig, master=main_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Top view button
            top_view_btn = ttk.Button(buttons_frame, text="Top View", style="ViewBtn.TButton",
                                   command=lambda: self.set_3d_view(ax, 90, -90, canvas))
            top_view_btn.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
            
            # Side view button
            side_view_btn = ttk.Button(buttons_frame, text="Side View", style="ViewBtn.TButton",
                                    command=lambda: self.set_3d_view(ax, 0, 0, canvas))
            side_view_btn.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
            
            # Front view button
            front_view_btn = ttk.Button(buttons_frame, text="Front View", style="ViewBtn.TButton",
                                     command=lambda: self.set_3d_view(ax, 0, -90, canvas))
            front_view_btn.grid(row=0, column=2, padx=10, pady=5, sticky="ew")
            
            # Isometric view button
            iso_view_btn = ttk.Button(buttons_frame, text="Isometric View", style="ViewBtn.TButton",
                                   command=lambda: self.set_3d_view(ax, 30, -45, canvas))
            iso_view_btn.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
            
            # Add a brief instruction
            instruction_label = ttk.Label(view_controls_frame, 
                                       text="Click and drag on the 3D plot to rotate manually, or use the view buttons above for preset angles",
                                       font=("Helvetica", 10, "italic"))
            instruction_label.pack(pady=(0, 5))
            
            # Add controls frame at the bottom
            controls_frame = ttk.Frame(popup)
            controls_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Set initial view angle
            self.set_3d_view(ax, 30, -45, canvas)
            
        except Exception as e:
            logger.error("ImageViewer", f"Error showing 3D visualization: {str(e)}")
            self.show_status_message(f"Error showing 3D visualization: {str(e)}", self.error_color)
    
    def set_3d_view(self, ax, elev, azim, canvas):
        """Set the view angle for the 3D plot."""
        ax.view_init(elev=elev, azim=azim)
        canvas.draw()

    def setup_keyboard_bindings(self):
        """Set up keyboard shortcuts."""
        self.root.bind('<Left>', lambda event: self.prev_file())
        self.root.bind('<Right>', lambda event: self.next_file())
        self.root.bind('<space>', lambda event: self.batch_flip_ud())
        self.root.bind('<Return>', lambda event: self.batch_flip_lr())
        self.root.bind('<Escape>', lambda event: self.stop_auto_advance()) 

def main():
    """Main function to run the application."""
    # Default configuration for logger
    logger.configure(
        verbose=False,
        console_level=LOG_LEVEL_INFO,
        debug_level=DEBUG_L1,
        colored_output=True
    )
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Depth Image Viewer Tool v.0.2.0")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--debug", type=int, choices=[1, 2, 3], default=1, 
                      help="Debug level (1=Basic, 2=Medium, 3=Verbose)")
    parser.add_argument("--log", action="store_true", help="Enable file logging")
    args = parser.parse_args()
    
    # Configure logger based on command line arguments
    if args.verbose or args.debug > 1 or args.log:
        console_level = LOG_LEVEL_DEBUG if args.verbose else LOG_LEVEL_INFO
        debug_level = args.debug
        
        logger.configure(
            verbose=args.verbose,
            console_level=console_level,
            debug_level=debug_level,
            colored_output=True
        )
        
        if args.log:
            # Enable file logging if requested
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"depth_viewer_{timestamp}.log"
            logger.configure_file_logging(enabled=True, level=LOG_LEVEL_DEBUG, filename=filename)
            logger.info("Main", f"File logging enabled: logs/{filename}")
    
    logger.info("Main", "Starting Depth Image Viewer application")
    
    # Create and run the application
    root = tk.Tk()
    root.geometry("900x850")  # Larger size to match main app style
    root.minsize(900, 850)    # Set minimum window size to match initial size
    root.title("Depth Image Viewer - Disaster Simulation")
    
    # Set default background color for all tk widgets
    root.configure(bg="#ffffff")
    root.option_add("*Background", "#ffffff")
    root.option_add("*Foreground", "#000000")
    
    # Create the app
    app = ImageViewer(root)
    
    # Start the main loop
    root.mainloop()
    
    # Shutdown logger properly before exit
    logger.info("Main", "Application shutting down")
    if hasattr(logger, 'shutdown'):
        logger.shutdown()

if __name__ == "__main__":
    main() 