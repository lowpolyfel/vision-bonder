from datetime import datetime, timedelta
import cv2

class VideoSource:
    """
    Entrega (ret, frame, ts_actual) y mantiene un base_datetime
    para auditoría en tiempo real: t0 del video = momento de arranque.
    """
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        self.frame_idx = 0
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
        if not self.fps or self.fps <= 0:
            self.fps = 30.0  # fallback razonable

        # Ancla de tiempo: ahora corresponde al inicio del video (t=0)
        # En la primera lectura, ajustamos base_datetime para que
        # base_datetime + delta == now.
        self.base_datetime = None
        self.ultimo_ts = None

    def is_opened(self):
        return self.cap.isOpened()

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return ret, None, None

        self.frame_idx += 1

        pos_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        if pos_ms and pos_ms > 0:
            delta = timedelta(milliseconds=float(pos_ms))
        else:
            delta = timedelta(seconds=self.frame_idx / self.fps)

        if self.base_datetime is None:
            # Anclar t=0 al instante actual de análisis (auditoría en tiempo real)
            self.base_datetime = datetime.now() - delta

        ts_actual = self.base_datetime + delta
        self.ultimo_ts = ts_actual
        return ret, frame, ts_actual

    def last_ts(self):
        return self.ultimo_ts

    def release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()

