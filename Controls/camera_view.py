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
        self.fig, self.ax = plt.subplots()
        self.image_plot = None

    def update(self):
        if not self.active:
            return

        try:
            self.sim.acquireLock()

            # ✨ Handle the vision sensor first!
            self.sim.handleVisionSensor(self.camera_handle)

            # Then fetch the image
            rgb_buffer_packed, resolution = self.sim.getVisionSensorImg(self.camera_handle)
            resX, resY = resolution[0], resolution[1]
            rgb_buffer = self.sim.unpackUInt8Table(rgb_buffer_packed)
            rgb_image = np.array(rgb_buffer, dtype=np.uint8).reshape((resY, resX, 3))
            rgb_image = np.flipud(rgb_image)

            self.sim.releaseLock()

            if self.image_plot is None:
                self.image_plot = self.ax.imshow(rgb_image)
                plt.ion()
                plt.show()
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
