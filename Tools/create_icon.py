from PIL import Image, ImageDraw, ImageTk
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys

# Add the current directory to the path to ensure we can import from Utils
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Suppress NSOpenPanel warnings on macOS
if sys.platform == 'darwin':
    os.environ['TK_SILENCE_DEPRECATION'] = '1'
    # This is a more comprehensive solution that disables all Cocoa warnings
    os.environ['NSApplicationCrashOnExceptions'] = '1'
    # Additional environment variable to suppress AppKit warnings
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

# Path to assets directory
ASSETS_DIR = os.path.join(current_dir, "assets")

def create_app_icon(custom_image_path=None, output_dir=None):
    """
    Create application icons from a custom image.
    
    Args:
        custom_image_path (str): Path to your custom image file. 
                               This image will be used as the base for the icons.
                                         Supported formats: PNG, JPG, ICO
        output_dir (str, optional): Custom output directory path. If not provided, 
                                   uses an "assets" subfolder in the image's directory.
    """
    # Determine the output directory
    if custom_image_path and os.path.exists(custom_image_path):
        # Use the provided output directory or create one in the input image directory
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(custom_image_path), "assets")
        print(f"Using custom image: {custom_image_path}")
        print(f"Output directory: {output_dir}")
        try:
            # Load and resize the custom image
            image = Image.open(custom_image_path)
            # Convert to RGBA if not already
            image = image.convert('RGBA')
            # Resize to 256x256
            image = image.resize((256, 256), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return False, str(e)
    else:
        # No image provided or file not found
        error_msg = "No valid image provided. Please select a valid image file."
        print(error_msg)
        return False, error_msg
    
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        
        # Define the output file paths
        ico_path = os.path.join(output_dir, 'icon.ico')
        png_path = os.path.join(output_dir, 'icon.png')
        app_ico_path = os.path.join(output_dir, 'tool_icon.ico')
        app_png_path = os.path.join(output_dir, 'tool_icon.png')
        creator_ico_path = os.path.join(output_dir, 'creator_icon.ico')
        creator_png_path = os.path.join(output_dir, 'creator_icon.png')
        small_png_path = os.path.join(output_dir, 'icon_small.png')
        
        # Save as ICO file with multiple sizes
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        image.save(ico_path, format='ICO', sizes=icon_sizes)
        
        # Save as PNG with specific settings for macOS
        png_image = image.copy()
        png_image.save(png_path, format='PNG', optimize=True)
        
        # Create additional copies with tool_icon prefix for the viewer app
        image.save(app_ico_path, format='ICO', sizes=icon_sizes)
        png_image.save(app_png_path, format='PNG', optimize=True)
        
        # Create additional copies with creator_icon prefix
        image.save(creator_ico_path, format='ICO', sizes=icon_sizes)
        png_image.save(creator_png_path, format='PNG', optimize=True)
        
        # Create a smaller version for macOS dock
        small_size = 128
        small_image = image.resize((small_size, small_size), Image.Resampling.LANCZOS)
        small_image.save(small_png_path, format='PNG', optimize=True)
        
        result_message = (
            f"Icon files created successfully in:\n{output_dir}\n\n"
            f"Created files:\n"
            f"- icon.ico and icon.png (standard icons)\n"
            f"- tool_icon.ico and tool_icon.png (for tools)\n"
            f"- creator_icon.ico and creator_icon.png (for creators)\n"
            f"- icon_small.png (small version for dock)"
        )
        
        print("Icon files created successfully!")
        print(f"ICO file: {os.path.abspath(ico_path)}")
        print(f"PNG file: {os.path.abspath(png_path)}")
        print(f"Tool ICO file: {os.path.abspath(app_ico_path)}")
        print(f"Tool PNG file: {os.path.abspath(app_png_path)}")
        print(f"Creator ICO file: {os.path.abspath(creator_ico_path)}")
        print(f"Creator PNG file: {os.path.abspath(creator_png_path)}")
        print(f"Small PNG file: {os.path.abspath(small_png_path)}")
        return True, result_message
    except Exception as e:
        print(f"Error saving icon files: {str(e)}")
        return False, str(e)

class IconCreatorApp:
    """Icon Creator Application"""
    
    def __init__(self, master):
        self.master = master
        master.title("Icon Creator Tool v.0.2.0")
        
        # Set initial window size and minimum size
        master.geometry("600x600")
        master.minsize(600, 600)  # Smaller minimum size to allow flexibility
        
        # Set app icon using the existing creator_icon files
        self.set_app_icon()
        
        # Define colors used in the app
        self.bg_color = "#ffffff"     # White background
        self.fg_color = "#000000"     # Black text
        self.accent_color = "#0078d7" # Modern blue
        self.green_color = "#4CAF50"  # Light green for Create button
        self.green_hover = "#66BB6A"  # Lighter green for hover
        self.green_pressed = "#388E3C" # Darker green for pressed
        
        # Configure the style for a light theme
        self.configure_style()
        
        # Create the main frame with padding
        self.main_frame = ttk.Frame(master, padding="20 20 20 20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create header with title
        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.title_label = ttk.Label(
            self.header_frame, 
            text="Icon Creator Tool", 
            font=("Helvetica", 16, "bold"),
            foreground="#0078d7"
        )
        self.title_label.pack(side=tk.LEFT)
        
        # Create image selection section
        self.img_frame = ttk.LabelFrame(self.main_frame, text="Source Image", padding="10 10 10 10")
        self.img_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.path_var = tk.StringVar()
        self.img_content = ttk.Frame(self.img_frame)
        self.img_content.pack(fill=tk.X, expand=True)
        
        self.path_entry = ttk.Entry(self.img_content, textvariable=self.path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.browse_btn = ttk.Button(
            self.img_content, 
            text="Browse...", 
            command=self.browse_image
        )
        self.browse_btn.pack(side=tk.RIGHT)
        
        # Create output directory section
        self.out_frame = ttk.LabelFrame(self.main_frame, text="Output Directory", padding="10 10 10 10")
        self.out_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.out_var = tk.StringVar()
        # Default to assets subfolder
        self.out_var.set(os.path.abspath("assets"))
        
        self.out_content = ttk.Frame(self.out_frame)
        self.out_content.pack(fill=tk.X, expand=True)
        
        self.out_entry = ttk.Entry(self.out_content, textvariable=self.out_var)
        self.out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.out_browse_btn = ttk.Button(
            self.out_content, 
            text="Browse...", 
            command=self.browse_output_dir
        )
        self.out_browse_btn.pack(side=tk.RIGHT)
        
        # Create options section
        self.options_frame = ttk.LabelFrame(self.main_frame, text="Options", padding="10 10 10 10")
        self.options_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Option to open output folder after creation
        self.open_folder_var = tk.BooleanVar(value=True)
        self.open_folder_check = ttk.Checkbutton(
            self.options_frame,
            text="Open output folder after creation",
            variable=self.open_folder_var
        )
        self.open_folder_check.pack(anchor=tk.W, pady=5)
        
        # Preview section
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="Preview", padding="10 10 10 10")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create a container for the preview image to allow centering
        self.preview_container = ttk.Frame(self.preview_frame)
        self.preview_container.pack(fill=tk.BOTH, expand=True)
        
        # Configure the container for centering
        self.preview_container.columnconfigure(0, weight=1)
        self.preview_container.rowconfigure(0, weight=1)
        
        # Placeholder for image preview
        self.preview_label = ttk.Label(self.preview_container, text="No image selected")
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        
        # Default preview
        self.update_preview()
        
        # Create buttons section
        self.btn_frame = ttk.Frame(self.main_frame)
        self.btn_frame.pack(fill=tk.X)
        
        # Create the button with ttk style (like Exit button) but with Green style
        self.create_btn = ttk.Button(
            self.btn_frame, 
            text="Create Icons", 
            command=self.create_icons,
            style="Green.TButton"
        )
        self.create_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # For platforms where ttk styling doesn't work well with colors,
        # we'll color the button after it's created using a platform-specific approach
        self.apply_green_button_color()
        
        self.exit_btn = ttk.Button(
            self.btn_frame, 
            text="Exit", 
            command=master.destroy
        )
        self.exit_btn.pack(side=tk.RIGHT)
        
        # Create status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            master, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            padding=(10, 5)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind path changes to preview update
        self.path_var.trace_add("write", lambda *args: self.update_preview())
        
        # Bind window resize event to update preview
        master.bind("<Configure>", self.on_window_resize)
        
        # For debouncing resize events
        self.resize_timer = None
        self.last_window_width = master.winfo_width()
        self.last_window_height = master.winfo_height()
    
    def set_app_icon(self):
        """Set the application icon using the existing creator_icon files"""
        try:
            # Look for creator_icon files in the assets directory
            icon_path = os.path.join(ASSETS_DIR, "creator_icon.png")
            icon_path_ico = os.path.join(ASSETS_DIR, "creator_icon.ico")
            
            # Check if icon files exist
            icon_png_exists = os.path.exists(icon_path)
            icon_ico_exists = os.path.exists(icon_path_ico)
            
            # For Windows (uses .ico file)
            if sys.platform.startswith('win') and icon_ico_exists:
                self.master.iconbitmap(icon_path_ico)
            
            # For macOS (uses .png file)
            elif sys.platform == 'darwin' and icon_png_exists:
                # Use PIL to open and convert the image for Tkinter
                icon_image = Image.open(icon_path)
                icon_tk = ImageTk.PhotoImage(icon_image)
                self.master.iconphoto(True, icon_tk)
                # Keep a reference to prevent garbage collection
                self.icon_image = icon_tk
            
            # For Linux (uses .png file)
            elif sys.platform.startswith('linux') and icon_png_exists:
                icon_image = Image.open(icon_path)
                icon_tk = ImageTk.PhotoImage(icon_image)
                self.master.iconphoto(True, icon_tk)
                # Keep a reference to prevent garbage collection
                self.icon_image = icon_tk
            
        except Exception as e:
            print(f"Error setting application icon: {str(e)}")
            # Continue without icon - this is not a critical error
    
    def configure_style(self):
        """Configure the application style for a light theme"""
        style = ttk.Style()
        
        # Configure colors
        bg_color = "#ffffff"  # White background
        fg_color = "#000000"  # Black text
        accent_color = "#0078d7"  # Modern blue
        green_color = "#4CAF50"  # Light green for Create button
        
        # Configure frame styles
        style.configure("TFrame", background=bg_color)
        style.configure("TLabelframe", background=bg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=accent_color, font=("Helvetica", 10, "bold"))
        
        # Configure label styles
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        
        # Configure button styles
        style.configure("TButton", background=bg_color, font=("Helvetica", 10))
        
        # Green button style - matching TButton style but with green color
        style.configure("Green.TButton", 
                      font=("Helvetica", 10, "bold"))
                      
        # Set green button colors - this works on some platforms
        # For platforms where this doesn't work, we'll add a workaround in the class
        if sys.platform.startswith('win'):  # Windows
            style.configure("Green.TButton", foreground='white', background=green_color)
            style.map("Green.TButton",
                    background=[("active", "#66BB6A"), ("pressed", "#388E3C")],
                    foreground=[("active", "white"), ("pressed", "white")])
                    
        # Configure entry styles
        style.configure("TEntry", fieldbackground=bg_color)
        
        # Configure checkbutton styles
        style.configure("TCheckbutton", background=bg_color)
    
    def browse_image(self):
        """Open a file dialog to select an image file"""
    file_path = filedialog.askopenfilename(
        title="Select Icon Image",
        filetypes=[
            ("Image files", "*.png *.jpg *.jpeg *.ico"),
            ("All files", "*.*")
        ]
    )
    
    if file_path:
            self.path_var.set(file_path)
            
            # Update output directory to be in the same location as the image
            out_dir = os.path.join(os.path.dirname(file_path), "assets")
            self.out_var.set(out_dir)
            
            # Update preview
            self.update_preview()
            
            self.status_var.set(f"Selected image: {os.path.basename(file_path)}")
    
    def browse_output_dir(self):
        """Open a file dialog to select an output directory"""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.out_var.get()
        )
        
        if directory:
            self.out_var.set(directory)
            self.status_var.set(f"Selected output directory: {directory}")
    
    def update_preview(self):
        """Update the image preview"""
        # Try to load and display the selected image
        image_path = self.path_var.get()
        
        if image_path and os.path.exists(image_path):
            try:
                # Load image and resize for preview
                image = Image.open(image_path)
                image = image.convert('RGBA')
                image.thumbnail((128, 128), Image.Resampling.LANCZOS)
                
                # Display the image
                photo = ImageTk.PhotoImage(image)
                self.preview_label.configure(image=photo, text="")
                self.preview_label.image = photo  # Keep a reference
            except Exception as e:
                # Show error message if image can't be loaded
                self.preview_label.configure(text=f"Error loading image: {str(e)}", image="")
        else:
            # No image selected or invalid path
            self.preview_label.configure(text="No image selected", image="")
    
    def create_icons(self):
        """Create the icon files"""
        # Get selected options
        img_path = self.path_var.get()
        out_dir = self.out_var.get()
        
        # Validate input
        if not img_path or not os.path.exists(img_path):
            messagebox.showerror("Error", "Please select a valid image file.")
            return
        
        # Update status
        self.status_var.set("Creating icons...")
        self.master.update_idletasks()
        
        # Create icons
        success, message = create_app_icon(img_path, out_dir)
        
        if success:
            # Show success message
            messagebox.showinfo("Success", message)
            
            # Open output folder if option is selected
            if self.open_folder_var.get():
                self.open_folder(out_dir)
            
            self.status_var.set("Icons created successfully!")
        else:
            # Show error message
            messagebox.showerror("Error", f"Failed to create icons: {message}")
            self.status_var.set("Error creating icons")
    
    def open_folder(self, path):
        """Open a folder in the file explorer"""
        try:
            if sys.platform == 'darwin':  # macOS
                os.system(f'open "{path}"')
            elif sys.platform == 'win32':  # Windows
                os.system(f'explorer "{path}"')
            else:  # Linux
                os.system(f'xdg-open "{path}"')
        except Exception as e:
            print(f"Error opening folder: {str(e)}")
    
    def on_window_resize(self, event):
        """Handle window resize events to avoid excessive preview updates"""
        # Only respond to root window resizes
        if event.widget != self.master:
            return
            
        # Get current window dimensions
        current_width = self.master.winfo_width()
        current_height = self.master.winfo_height()
        
        # Check if size actually changed significantly (more than 5 pixels difference)
        size_changed = (abs(current_width - self.last_window_width) > 5 or 
                       abs(current_height - self.last_window_height) > 5)
        
        if size_changed:
            # Store new dimensions
            self.last_window_width = current_width
            self.last_window_height = current_height
            
            # Cancel any previous scheduled updates
            if self.resize_timer:
                self.master.after_cancel(self.resize_timer)
                
            # Schedule a new update after a delay
            self.resize_timer = self.master.after(200, self.update_preview)

    def apply_green_button_color(self):
        """Apply green color to the button using platform-specific methods"""
        try:
            if sys.platform == 'darwin':  # macOS
                # On macOS, we can use the TButton.label to set the background
                # The actual widget is created after a short delay
                self.master.after(10, self._mac_color_button)
            elif not sys.platform.startswith('win'):  # Linux and others
                # For Linux and other platforms, try a different approach if needed
                self._try_alt_color_method()
        except Exception as e:
            print(f"Warning: Could not apply green color to button: {str(e)}")
    
    def _mac_color_button(self):
        """Apply color to button on macOS"""
        try:
            # Get the actual button widget on macOS
            btn_label = self.create_btn.winfo_children()[0]
            btn_label.configure(background=self.green_color, foreground='white')
        except:
            pass
            
    def _try_alt_color_method(self):
        """Try alternative method to color the button"""
        try:
            # Some Linux themes support this approach
            self.create_btn.configure(default='active')
        except:
            pass

def main():
    # Create the main window
    root = tk.Tk()
    app = IconCreatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 