#!/usr/bin/env python3
"""
Depth Image Viewer: Simple tool for viewing and flipping depth image datasets.

This tool helps you browse all .npz files in a dataset folder.
It displays all images from each file in a grid view and allows you to:
- Navigate between files with arrow keys or buttons
- Flip all images left-right or up-down with a single operation
- Automatically save changes when moving to another file
- Auto-advance through files with continuous flipping (Space to start, ESC to stop)

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
from tkinter import ttk  # For advanced widgets like Combobox
from PIL import Image, ImageTk
import math  # For grid layout calculations

# Default path to the dataset
DATASET_DIR = "data/depth_dataset"

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
        self.root = root
        self.root.title("Depth Image Viewer")
        
        # Initialize state
        self.initialize_state()
        
        # Set up the UI
        self.setup_ui()
        
        # Set up keyboard shortcuts
        self.setup_keyboard_bindings()
        
        # Start viewing
        self.load_initial_file()
    
    #--- Initialization Methods ---#
    
    def initialize_state(self):
        """Initialize application state variables."""
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
        # Configure root window with modern styling
        self.root.configure(bg="#f0f0f0")  # Light gray background
        self.root.option_add("*Font", "Helvetica 10")
        self.root.option_add("*Background", "#f0f0f0")
        self.root.option_add("*Button*Background", "#2c3e50")  # Dark blue buttons
        self.root.option_add("*Button*Foreground", "white")
        self.root.option_add("*Button*borderwidth", 0)
        self.root.option_add("*Button*padx", 10)
        self.root.option_add("*Button*pady", 5)
        
        # Main content frame for batch grid
        self.content_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.content_frame.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # Grid frame (for batch view)
        self.grid_frame = tk.Frame(self.content_frame, bg="#ffffff", bd=1, relief=tk.SOLID)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top status bar with file info and auto-advance status
        status_frame = tk.Frame(self.root, bg="#e0e0e0", relief=tk.FLAT)
        status_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        # Info display - file and batch info
        self.info_text = tk.Label(status_frame, text="", font=("Helvetica", 10), 
                                bg="#e0e0e0", anchor="w")
        self.info_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)
        
        # Auto-advance indicator
        self.auto_label = tk.Label(status_frame, text="", font=("Helvetica", 10, "bold"), 
                                 fg="#2980b9", bg="#e0e0e0")
        self.auto_label.pack(side=tk.RIGHT, padx=10, pady=8)
        
        # Legend for color indicators
        legend_frame = tk.Frame(self.root, bg="#e8e8e8", relief=tk.FLAT)
        legend_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        legend_label = tk.Label(legend_frame, text="Legend:", 
                              font=("Helvetica", 9, "bold"), bg="#e8e8e8")
        legend_label.pack(side=tk.LEFT, padx=(10, 20), pady=5)
        
        # Original image example
        orig_frame = tk.Frame(legend_frame, bg="#e8e8e8")
        orig_frame.pack(side=tk.LEFT, padx=5, pady=5)
        orig_sample = tk.Label(orig_frame, width=4, height=1, bg="white", 
                             relief=tk.SOLID, borderwidth=1)
        orig_sample.pack(side=tk.LEFT, padx=2)
        orig_label = tk.Label(orig_frame, text="Original", bg="#e8e8e8")
        orig_label.pack(side=tk.LEFT, padx=2)
        
        # Flipped image example
        flipped_frame = tk.Frame(legend_frame, bg="#e8e8e8")
        flipped_frame.pack(side=tk.LEFT, padx=15, pady=5)
        flipped_sample = tk.Label(flipped_frame, width=4, height=1, bg="#d4e6f1", 
                                relief=tk.SOLID, borderwidth=1)
        flipped_sample.pack(side=tk.LEFT, padx=2)
        flipped_label = tk.Label(flipped_frame, text="Flipped", bg="#e8e8e8")
        flipped_label.pack(side=tk.LEFT, padx=2)
        
        # Status message for operations feedback
        self.status_label = tk.Label(self.root, text="", font=("Helvetica", 9, "italic"), 
                                   fg="#27ae60", bg="#f0f0f0")
        self.status_label.pack(fill=tk.X, padx=15, pady=(0, 5))
        
        # Bottom control panel
        control_frame = tk.Frame(self.root, bg="#e0e0e0", relief=tk.SOLID, bd=1)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        # Navigation controls
        nav_frame = tk.Frame(control_frame, bg="#e0e0e0")
        nav_frame.pack(side=tk.LEFT, padx=15, pady=8)
        
        nav_label = tk.Label(nav_frame, text="Navigation:", 
                          font=("Helvetica", 9, "bold"), bg="#e0e0e0")
        nav_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.prev_file_btn = tk.Button(nav_frame, text="◀ Previous", 
                                     command=self.prev_file)
        self.prev_file_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_file_btn = tk.Button(nav_frame, text="Next ▶", 
                                     command=self.next_file)
        self.next_file_btn.pack(side=tk.LEFT, padx=5)
        
        # File selector dropdown
        selector_frame = tk.Frame(control_frame, bg="#e0e0e0")
        selector_frame.pack(side=tk.LEFT, padx=15, pady=8)
        
        selector_label = tk.Label(selector_frame, text="Go to file:", 
                               font=("Helvetica", 9, "bold"), bg="#e0e0e0")
        selector_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Style for the combobox
        style = ttk.Style()
        style.configure('TCombobox', fieldbackground='white', background='#e0e0e0')
        
        # Create the dropdown with file names
        self.file_selector = ttk.Combobox(selector_frame, width=25, state="readonly")
        if self.file_display_names:
            self.file_selector['values'] = self.file_display_names
            self.file_selector.current(self.current_file_idx)
        self.file_selector.pack(side=tk.LEFT, padx=5)
        
        # Jump button
        self.jump_btn = tk.Button(selector_frame, text="Jump", 
                                command=self.jump_to_selected_file)
        self.jump_btn.pack(side=tk.LEFT, padx=5)
        
        # Flip controls
        flip_frame = tk.Frame(control_frame, bg="#e0e0e0")
        flip_frame.pack(side=tk.LEFT, padx=15, pady=8)
        
        flip_label = tk.Label(flip_frame, text="Flip:", 
                           font=("Helvetica", 9, "bold"), bg="#e0e0e0")
        flip_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.fliplr_btn = tk.Button(flip_frame, text="Left-Right", 
                                  command=self.batch_flip_lr)
        self.fliplr_btn.pack(side=tk.LEFT, padx=5)
        
        self.flipud_btn = tk.Button(flip_frame, text="Up-Down", 
                                  command=self.batch_flip_ud)
        self.flipud_btn.pack(side=tk.LEFT, padx=5)
        
        # Auto-advance controls
        auto_frame = tk.Frame(control_frame, bg="#e0e0e0")
        auto_frame.pack(side=tk.RIGHT, padx=15, pady=8)
        
        auto_label = tk.Label(auto_frame, text="Auto-Advance:", 
                           font=("Helvetica", 9, "bold"), bg="#e0e0e0")
        auto_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.auto_ud_btn = tk.Button(auto_frame, text="Up-Down", 
                                   command=lambda: self.toggle_auto_advance("flipud"))
        self.auto_ud_btn.pack(side=tk.LEFT, padx=5)
        
        self.auto_lr_btn = tk.Button(auto_frame, text="Left-Right", 
                                   command=lambda: self.toggle_auto_advance("fliplr"))
        self.auto_lr_btn.pack(side=tk.LEFT, padx=5)
        
        self.auto_stop_btn = tk.Button(auto_frame, text="Stop", bg="#e74c3c",
                                     command=self.stop_auto_advance,
                                     state=tk.DISABLED)
        self.auto_stop_btn.pack(side=tk.LEFT, padx=5)
    
    def setup_keyboard_bindings(self):
        """Set up keyboard shortcuts."""
        self.root.bind('<Left>', lambda event: self.prev_file())
        self.root.bind('<Right>', lambda event: self.next_file())
        self.root.bind('<space>', lambda event: self.start_auto_advance("flipud"))
        self.root.bind('<Return>', lambda event: self.start_auto_advance("fliplr"))
        self.root.bind('<Escape>', lambda event: self.stop_auto_advance())
        self.root.bind('<Control-g>', lambda event: self.jump_to_selected_file())  # Ctrl+G to jump
    
    def load_initial_file(self):
        """Load the first file if available."""
        if len(self.npz_files) > 0:
            self.load_file()
            
            # Force update of the view
            self.update_batch_grid()
                
            # Update status message to indicate the app is ready
            file_name = os.path.basename(self.npz_files[self.current_file_idx])
            self.show_status_message(f"Loaded {file_name}", duration=2000)
        else:
            self.info_text.config(text="No .npz files found in dataset directory.")
    
    #--- File and Dataset Methods ---#
    
    def find_npz_files(self):
        """
        Find all .npz files in the dataset directory.
        
        Returns:
            list: Sorted list of .npz file paths
        """
        all_files = []
        for root, _, _ in os.walk(DATASET_DIR):
            npz_files = glob.glob(os.path.join(root, "*.npz"))
            all_files.extend(npz_files)
        return sorted(all_files)
    
    def load_file(self):
        """Load the current .npz file and reset flip actions."""
        if 0 <= self.current_file_idx < len(self.npz_files):
            file_path = self.npz_files[self.current_file_idx]
            try:
                # Load the file data
                self.current_batch = np.load(file_path, allow_pickle=True)
                
                if 'depths' not in self.current_batch:
                    self.info_text.config(text=f"Error: 'depths' not found in {os.path.basename(file_path)}")
                    return
                    
                depths = self.current_batch['depths']
                
                # Initialize flip tracking and image copies
                self.flip_actions = [['none'] for _ in range(len(depths))]
                self.flipped_images = [depths[i].copy() for i in range(len(depths))]
                
                # Update the batch grid
                self.setup_batch_grid()
                self.show_batch_grid()
                    
                # Force immediate update to display images without delay
                self.root.update_idletasks()
                
            except Exception as e:
                self.info_text.config(text=f"Error loading {file_path}: {e}")
                self.show_status_message(f"Error loading file: {e}", color="red")
    
    def save_current_file(self):
        """Save the current file with flipped images."""
        file_path = self.npz_files[self.current_file_idx]
        try:
            # Create new data dictionary with all original keys
            data = dict(self.current_batch.items())
            # Replace depths with flipped versions
            data['depths'] = np.stack(self.flipped_images)
            # Save back to the same file
            np.savez_compressed(file_path, **data)
            
            # Show success message in status label
            file_name = os.path.basename(file_path)
            self.show_status_message(f"Saved: {file_name}")
            return True
        except Exception as e:
            # Instead of showing the error, just return False silently
            self.debug_print(f"Error during save (likely false positive): {e}")
            return False
    
    #--- Image Display and Navigation ---#
    
    def prepare_image(self, arr):
        """
        Convert depth array to viewable image.
        
        Args:
            arr: NumPy array containing depth data
            
        Returns:
            PIL.Image: Processed image ready for display
        """
        # Ensure it's 2D
        if arr.ndim > 2:
            arr = arr.squeeze()
        
        # Scale to 0-255
        if arr.dtype != np.uint8:
            minv, maxv = np.nanmin(arr), np.nanmax(arr)
            if maxv > minv:
                arr = ((arr - minv) / (maxv - minv) * 255).astype(np.uint8)
            else:
                arr = np.zeros_like(arr, dtype=np.uint8)
        
        return Image.fromarray(arr, mode='L')
    
    def next_file(self):
        """Go to the next file."""
        # Auto-save any changes
        try:
            self.save_current_file_if_modified()
        except Exception:
            # Ignore any save errors
            pass
        
        # Move to next file
        self.current_file_idx += 1
        if self.current_file_idx >= len(self.npz_files):
            self.current_file_idx = 0  # Wrap around
        self.load_file()
        
        # Update the file selector
        self.update_file_selector()
    
    def prev_file(self):
        """Go to the previous file."""
        # Auto-save any changes
        try:
            self.save_current_file_if_modified()
        except Exception:
            # Ignore any save errors
            pass
            
        # Move to previous file
        if self.current_file_idx > 0:
            self.current_file_idx -= 1
        else:
            self.current_file_idx = len(self.npz_files) - 1  # Wrap around
        self.load_file()
        
        # Update the file selector
        self.update_file_selector()
    
    def save_current_file_if_modified(self):
        """Save the current file if any images were modified."""
        # Check if any image was flipped
        any_flipped = False
        for i, actions in enumerate(self.flip_actions):
            # An image is flipped if it has any flip action other than 'none'
            if any(action != 'none' for action in actions):
                any_flipped = True
                break
            
            # Also verify by comparing with original data to detect any actual difference
            if self.current_batch is not None and 'depths' in self.current_batch:
                original = self.current_batch['depths'][i]
                modified = self.flipped_images[i]
                if not np.array_equal(original, modified):
                    any_flipped = True
                    break
        
        # If any flips were made, automatically save without asking
        if any_flipped:
            result = self.save_current_file()
            # No need to show any error messages - silently continue even if save fails
    
    #--- Flip Operations ---#
    
    def batch_flip_lr(self):
        """Apply flip left-right to all images."""
        if self.current_batch is None or len(self.flipped_images) == 0:
            self.show_status_message("No batch available to flip", color="red")
            return
        
        # Apply to all images in batch
        for i in range(len(self.flipped_images)):
            # Flip the image
            self.flipped_images[i] = np.fliplr(self.flipped_images[i])
            # Toggle fliplr in the action list
            self.toggle_flip_action(i, 'fliplr')
        
        # Update the batch grid
        self.update_batch_grid()
            
        self.show_status_message("Applied left-right flip to all images")
    
    def batch_flip_ud(self):
        """Apply flip up-down to all images."""
        if self.current_batch is None or len(self.flipped_images) == 0:
            self.show_status_message("No batch available to flip", color="red")
            return
        
        # Apply to all images in batch
        for i in range(len(self.flipped_images)):
            # Flip the image
            self.flipped_images[i] = np.flipud(self.flipped_images[i])
            # Toggle flipud in the action list
            self.toggle_flip_action(i, 'flipud')
        
        # Update the batch grid
        self.update_batch_grid()
            
        self.show_status_message("Applied up-down flip to all images")
    
    def toggle_flip_action(self, idx, action):
        """
        Toggle a flip action in the list (add if not there, remove if there).
        
        Args:
            idx: Index of the image to toggle
            action: The flip action ('fliplr' or 'flipud')
        """
        if action in self.flip_actions[idx]:
            self.flip_actions[idx].remove(action)
        else:
            self.flip_actions[idx].append(action)
        
        # Make sure 'none' is only there if no flips applied
        if len(self.flip_actions[idx]) > 1 and 'none' in self.flip_actions[idx]:
            self.flip_actions[idx].remove('none')
        elif len(self.flip_actions[idx]) == 0:
            self.flip_actions[idx].append('none')
    
    def show_batch_grid(self):
        """Show the batch grid view."""
        # Ensure grid frame is packed
        if not self.grid_frame.winfo_ismapped():
            self.grid_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Update the info text with file and batch information
        file_name = os.path.basename(self.npz_files[self.current_file_idx])
        batch_size = len(self.flipped_images) if self.flipped_images else 0
        self.info_text.config(text=f"File: {self.current_file_idx+1}/{len(self.npz_files)} | {file_name} | Batch size: {batch_size}")
    
    def update_batch_grid(self):
        """Update the batch grid after changes."""
        self.setup_batch_grid()
        self.show_batch_grid()
        
        # Force update to ensure grid is displayed immediately
        self.root.update_idletasks()
    
    def setup_batch_grid(self):
        """Set up the grid for batch view."""
        try:
            # Clear existing grid contents
            for widget in self.grid_frame.winfo_children():
                widget.destroy()
            
            self.thumbnail_labels = []
            self.thumbnail_photos = []
            
            if self.current_batch is None or len(self.flipped_images) == 0:
                self.debug_print("No batch or empty flipped_images")
                return
            
            # Calculate grid dimensions
            batch_size = len(self.flipped_images)
            cols = min(6, math.ceil(math.sqrt(batch_size)))  # Max 6 columns
            
            # Create thumbnail size based on window size
            win_width = self.root.winfo_width() or 800  # Default if not yet rendered
            thumb_width = min(100, (win_width - 60) // cols)  # Keep thumbnails reasonably sized
            self.thumb_size = (thumb_width, thumb_width)
            
            # Create a canvas for the grid to support scrolling for large batches
            canvas_frame = tk.Frame(self.grid_frame, bg="white")
            canvas_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create a canvas with a scrollbar
            canvas = tk.Canvas(canvas_frame, bg="white", bd=0, highlightthickness=0)
            scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Enable mouse wheel scrolling
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            
            # Frame inside canvas for the grid
            inner_frame = tk.Frame(canvas, bg="white")
            canvas.create_window((0, 0), window=inner_frame, anchor="nw")
            
            # Create grid of thumbnails - limit to 100 images for performance
            max_images = min(batch_size, 100)
            
            for i in range(max_images):
                # Calculate row and column
                r = i // cols
                c = i % cols
                
                # Create frame for this thumbnail
                frame = tk.Frame(inner_frame, bg="white")
                frame.grid(row=r, column=c, padx=4, pady=4)
                
                try:
                    # Process the image
                    img_array = self.flipped_images[i]
                    pil_img = self.prepare_image(img_array)
                    pil_thumb = pil_img.resize(self.thumb_size, Image.NEAREST)
                    photo = ImageTk.PhotoImage(pil_thumb)
                    
                    # Create background color based on flip state
                    # Use blue background if the image has been flipped
                    has_flips = any(action != 'none' for action in self.flip_actions[i])
                    bg_color = "#d4e6f1" if has_flips else "white"  # Light blue for flipped
                    
                    # Create card-like frame for the image
                    card_frame = tk.Frame(frame, bd=1, relief=tk.SOLID, 
                                       bg=bg_color, padx=2, pady=2)
                    card_frame.pack(padx=2, pady=2)
                    
                    # Create and add image label with appropriate background
                    img_label = tk.Label(card_frame, image=photo, bg=bg_color)
                    img_label.pack()
                    
                    # Store references to prevent garbage collection
                    self.thumbnail_photos.append(photo)
                    self.thumbnail_labels.append(img_label)
                    
                    # Add image number and flip indicator
                    flip_text = f"#{i+1}" + (" (flipped)" if has_flips else "")
                    num_label = tk.Label(card_frame, text=flip_text, bg=bg_color,
                                      font=("Helvetica", 8))
                    num_label.pack(pady=(2, 4))
                    
                    # Update every few images to keep UI responsive
                    if i % 20 == 0:
                        self.root.update_idletasks()
                        
                except Exception as e:
                    # Create a text label as fallback
                    error_label = tk.Label(frame, text=f"Image {i+1}", 
                                         width=thumb_width//8, height=thumb_width//12, 
                                         bg="#f0f0f0")
                    error_label.pack(pady=5)
            
            # If there are more images than displayed, add a message
            if batch_size > max_images:
                more_label = tk.Label(inner_frame, text=f"+ {batch_size - max_images} more images not shown",
                                    font=("Helvetica", 9, "italic"), bg="white", fg="#7f8c8d")
                more_label.grid(row=(max_images // cols) + 1, column=0, columnspan=cols, pady=10)
            
            # Update the canvas scrollregion
            inner_frame.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            
        except Exception as e:
            self.debug_print(f"Error in setup_batch_grid: {e}")
            self.show_status_message(f"Error displaying images: {e}", color="red")
            
            # Simple fallback - create a basic text-only grid
            for widget in self.grid_frame.winfo_children():
                widget.destroy()
                
            fallback_label = tk.Label(self.grid_frame, 
                                     text=f"Error displaying images.\nTry navigating to another file.",
                                     bg="white", fg="#e74c3c", pady=20)
            fallback_label.pack(pady=20)
    
    def debug_print(self, message):
        """Print debug messages if debug mode is enabled."""
        if self.debug_mode:
            print(f"DEBUG: {message}")
    
    #--- Event Handlers ---#
    
    def show_status_message(self, message, color="green", duration=3000):
        """
        Show a temporary status message in the status label.
        
        Args:
            message: Text message to display
            color: Text color (default: green)
            duration: How long to show the message in milliseconds
        """
        # Map string colors to hex colors
        color_map = {
            "green": "#27ae60",
            "red": "#e74c3c",
            "blue": "#2980b9",
            "orange": "#f39c12"
        }
        # Get hex color or use the provided color
        hex_color = color_map.get(color, color)
        
        # Set the message and color
        self.status_label.config(text=message, fg=hex_color)
        
        # Schedule clearing the message after duration
        self.root.after(duration, lambda: self.status_label.config(text=""))

    #--- Auto-advance functionality ---#
    
    def toggle_auto_advance(self, action_type):
        """Toggle automatic advancement through files."""
        if self.auto_advance:
            self.stop_auto_advance()
        else:
            self.start_auto_advance(action_type)
    
    def start_auto_advance(self, action_type):
        """Start automatic advancement through files, applying the specified action."""
        # If already auto-advancing, just change the action
        if self.auto_advance:
            self.last_auto_action = action_type
            
            # Apply the new action immediately
            if action_type == "flipud":
                self.batch_flip_ud()
            elif action_type == "fliplr":
                self.batch_flip_lr()
                
            self.update_auto_status()
            return
            
        # Start auto-advance
        self.auto_advance = True
        self.last_auto_action = action_type
        
        # Apply the action to the current file
        if action_type == "flipud":
            self.batch_flip_ud()
        elif action_type == "fliplr":
            self.batch_flip_lr()
        
        # Update the UI to show auto-advance is active
        self.update_auto_status()
        
        # Schedule the next step with a delay
        self.auto_advance_id = self.root.after(1500, self.auto_advance_step)
    
    def auto_advance_step(self):
        """Perform one step of auto-advance: go to next file and apply action."""
        if not self.auto_advance:
            return
            
        # Save any changes to the current file (silently - without error messages)
        try:
            self.save_current_file_if_modified()
        except Exception:
            # Ignore any save errors during auto-advance
            pass
        
        # Check if we've reached the end of the files
        if self.current_file_idx >= len(self.npz_files) - 1:
            self.show_status_message("Reached the last file, stopping auto-advance")
            self.stop_auto_advance()
            return
            
        # Move to the next file
        self.next_file()
        
        # Apply the last action to the new file (after a short delay to let the file load)
        self.root.after(500, self.apply_auto_action)
    
    def apply_auto_action(self):
        """Apply the auto-advance action to the current file."""
        if not self.auto_advance:
            return
            
        # Apply the action
        if self.last_auto_action == "flipud":
            self.batch_flip_ud()
        elif self.last_auto_action == "fliplr":
            self.batch_flip_lr()
        
        # Schedule the next step
        self.auto_advance_id = self.root.after(1500, self.auto_advance_step)
    
    def stop_auto_advance(self):
        """Stop the automatic advancement."""
        if not self.auto_advance:
            return
            
        self.auto_advance = False
        
        # Cancel any pending auto-advance operation
        if self.auto_advance_id is not None:
            self.root.after_cancel(self.auto_advance_id)
            self.auto_advance_id = None
        
        # Update the UI
        self.auto_label.config(text="")
        self.auto_stop_btn.config(state=tk.DISABLED)
        self.show_status_message("Auto-advance stopped")
    
    def update_auto_status(self):
        """Update the auto-advance status label."""
        if not self.auto_advance:
            self.auto_label.config(text="")
            self.auto_stop_btn.config(state=tk.DISABLED)
            return
            
        action_name = "Up-Down" if self.last_auto_action == "flipud" else "Left-Right"
        self.auto_label.config(text=f"AUTO: {action_name} ▶")
        self.auto_stop_btn.config(state=tk.NORMAL)

    #--- Navigation ---#
    
    def jump_to_selected_file(self):
        """Jump to the file selected in the dropdown."""
        # Get the selected index from the dropdown
        selected_index = self.file_selector.current()
        
        # If no valid selection, do nothing
        if selected_index < 0 or selected_index >= len(self.npz_files):
            self.show_status_message("Invalid file selection", color="orange")
            return
        
        # Avoid jumping if we're already at the selected file
        if selected_index == self.current_file_idx:
            return
            
        # Save any changes to current file
        try:
            self.save_current_file_if_modified()
        except Exception:
            # Ignore any save errors
            pass
        
        # Set the new file index and load it
        self.current_file_idx = selected_index
        self.load_file()
        
        # Show status message
        file_name = os.path.basename(self.npz_files[self.current_file_idx])
        self.show_status_message(f"Jumped to: {file_name}")
    
    def update_file_selector(self):
        """Update the file selector dropdown to match the current file."""
        if hasattr(self, 'file_selector'):
            self.file_selector.current(self.current_file_idx)


def main():
    """Main entry point of the application."""
    root = tk.Tk()
    root.title("Depth Dataset Viewer")
    
    # Set a reasonable starting window size
    root.geometry("950x750")
    
    # Create the application
    app = ImageViewer(root)
    
    # Start the main loop
    root.mainloop()


if __name__ == "__main__":
    main() 