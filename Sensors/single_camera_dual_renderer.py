import numpy as np
import matplotlib.pyplot as plt
from contextlib import contextmanager
from typing import Tuple

class SingleCameraDualViewRenderer:
    """
    Renders both the RGB image and the depth image from one vision sensor.
    """
    def __init__(self, sim, sensor_handle: int):
        self.sim    = sim
        self.handle = sensor_handle

        # Create a figure with 2 subplots side-by-side
        self.fig, (self.ax_rgb, self.ax_depth) = plt.subplots(1, 2, figsize=(8, 4))
        self.plot_rgb   = None
        self.plot_depth = None

        for ax in (self.ax_rgb, self.ax_depth):
            ax.axis('off')
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        plt.ion()

    def start(self) -> None:
        print("[SingleCameraDualViewRenderer] Starting viewer.")
        plt.show()

    def update(self) -> None:
        with self._locked():
            # explicitHandling requires this
            self.sim.handleVisionSensor(self.handle)

            # ─── RGB ──────────────────────────
            packed_img, (w, h) = self.sim.getVisionSensorImg(self.handle)
            raw = self.sim.unpackUInt8Table(packed_img)
            rgb = np.array(raw, dtype=np.uint8).reshape((h, w, 3))
            rgb = np.fliplr(rgb)

            # ─── Depth ────────────────────────
            packed_depth, (dw, dh) = self.sim.getVisionSensorDepth(self.handle)
            depth_flat = self.sim.unpackFloatTable(packed_depth)
            depth = np.array(depth_flat, dtype=np.float32).reshape((dh, dw))
            depth = np.fliplr(depth)

        # draw or update RGB
        if self.plot_rgb is None:
            self.plot_rgb = self.ax_rgb.imshow(rgb)
        else:
            self.plot_rgb.set_data(rgb)

        # draw or update Depth
        if self.plot_depth is None:
            self.plot_depth = self.ax_depth.imshow(depth, cmap='gray')
        else:
            self.plot_depth.set_data(depth)

        plt.draw()
        plt.pause(0.001)

    def close(self) -> None:
        print("[SingleCameraDualViewRenderer] Closing viewer.")
        plt.close(self.fig)

    @contextmanager
    def _locked(self):
        self.sim.acquireLock()
        try:
            yield
        finally:
            self.sim.releaseLock()
