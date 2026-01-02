import threading
import time

import dxcam


class DXCamCapture:
    def __init__(self, monitor_index: int = 0, target_fps: int = 60) -> None:
        self._camera = dxcam.create(output_idx=monitor_index)
        self._target_fps = target_fps
        self._lock = threading.Lock()
        self._latest_frame = None
        self._running = False
        self._thread = None
        self._region = None

    def start(self, region) -> None:
        self._region = region
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        interval = 1.0 / max(self._target_fps, 1)
        while self._running:
            frame = self._camera.grab(region=self._region)
            if frame is not None:
                with self._lock:
                    self._latest_frame = frame
            time.sleep(interval)

    def get_latest_frame(self):
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self._thread = None
