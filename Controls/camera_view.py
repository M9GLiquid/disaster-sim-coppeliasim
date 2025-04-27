# Controls/camera_view.py
import numpy as np
import matplotlib.pyplot as plt

class CameraView:
    def __init__(self, sim, camera_handle):
        self.sim = sim
        self.camera_handle = camera_handle
        self.active = False
        self.fig, self.ax = None, None
        self.image_plot = None

    def start(self):
        print("[CameraView] Starting RGB camera viewer (matplotlib)...")
        self.active = True

        # Create figure and axis
        self.fig, self.ax = plt.subplots()

        # Remove margins and axis ticks
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.axis('off')

        # Hide toolbar
        self.fig.canvas.toolbar_visible = False
        self.fig.canvas.manager.toolbar_visible = False
        # Remove the toolbar and status bar
        try:
            self.fig.canvas.manager.toolbar.pack_forget()
        except Exception:
            pass  # On some systems, toolbar manager doesn't exist

        
        self.image_plot = None

        # Enable interactive mode and show
        plt.ion()
        plt.show()

        # Remove window borders
        # self.fig.canvas.manager.window.overrideredirect(True)

        # Resize to 256x256 pixels
        self.fig.set_size_inches(256/100, 256/100)  # Assuming 100 DPI
        self.fig.canvas.manager.window.geometry(f"{256}x{256}")

        print("[CameraView] Viewer initialized.")

    def update(self):
        if not self.active:
            return

        try:
            self.sim.acquireLock()

            # Handle the vision sensor first
            self.sim.handleVisionSensor(self.camera_handle)

            # Fetch the image
            rgb_buffer_packed, resolution = self.sim.getVisionSensorImg(self.camera_handle)
            resX, resY = resolution[0], resolution[1]
            rgb_buffer = self.sim.unpackUInt8Table(rgb_buffer_packed)

            rgb_image = np.array(rgb_buffer, dtype=np.uint8).reshape((resY, resX, 3))
            rgb_image = np.fliplr(rgb_image)

            self.sim.releaseLock()

            if self.image_plot is None:
                self.image_plot = self.ax.imshow(rgb_image)
                plt.draw()
                plt.pause(0.001)
            else:
                self.image_plot.set_data(rgb_image)
                plt.draw()
                plt.pause(0.001)

        except Exception as e:
            print(f"[CameraView] Error: {e}")

    def close(self):
        print("[CameraView] Closing camera viewer.")
        self.active = False
        plt.close(self.fig)
