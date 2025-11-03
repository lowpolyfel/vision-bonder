import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2
from datetime import datetime

from config.settings import (
    DB_CONFIG, ID_MAQUINA_MONITOREADA, TOLERANCIA_IDLE_SEGUNDOS,
    AREA_MINIMA_CONTORNO, VIDEO_ANCHO_DISPLAY
)
from db.manager import DBManager
from services.state_machine import StateMachine
from services.event_recorder import EventRecorder
from video.capture import VideoSource
from video.motion import init_background, detect_motion

class DetectorApp:
    def __init__(self, root, video_path):
        self.root = root
        self.root.title("Detector de Movimiento v2 - Conectado a BD")
        self.root.configure(bg="#f0f0f0")

        # --- Flags para evitar duplicados en el cierre ---
        self._segmento_final_cerrado = False
        self._cerrado = False

        # --- Componentes principales ---
        self.db_manager = DBManager(DB_CONFIG)
        self.recorder = EventRecorder(self.db_manager, ID_MAQUINA_MONITOREADA)

        self.source = VideoSource(video_path)
        if not self.source.is_opened():
            tk.Label(root, text=f"Error al abrir el video:\n{video_path}",
                     font=("Helvetica", 12, "bold"), fg="red", bg="#f0f0f0", justify="left").pack(padx=20, pady=20)
            tk.Button(root, text="Cerrar", command=self.on_close,
                      font=("Helvetica", 10, "bold"), bg="#ff6b6b", fg="white").pack(pady=(0, 10))
            return

        self.state_machine = StateMachine(
            base_datetime=None,  # se fija al primer frame válido
            tolerancia_idle_segundos=TOLERANCIA_IDLE_SEGUNDOS,
            on_segment_callback=self._on_segment_closed
        )

        # --- UI ---
        self.panel_video = tk.Label(root, bg="black")
        self.panel_video.pack(padx=10, pady=10, fill="both", expand=True)

        status_frame = tk.Frame(root, bg="#d9d9d9", bd=2, relief="sunken")
        status_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.label_estado_visual = tk.Label(status_frame, text=" -- ", font=("Helvetica", 16, "bold"),
                                            bg="gray", fg="white", width=15, relief="raised", bd=2)
        self.label_estado_visual.pack(side="right", padx=10, pady=10, fill="x", expand=True)

        self.label_timer_visual = tk.Label(root, text=" -- ", font=("Helvetica", 16, "bold"),
                                           bg="#b0bec5", fg="black", width=15, relief="raised", bd=2)
        self.label_timer_visual.pack(pady=10)

        self.btn_quit = tk.Button(root, text="Salir", command=self.on_close,
                                  font=("Helvetica", 10, "bold"), bg="#ff6b6b", fg="white")
        self.btn_quit.pack(pady=(0, 10))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- Detección ---
        self.fondo = None

        # Loop
        self.update_frame()

    # Callback: se dispara cada vez que se cierra un segmento en la máquina de estados
    def _on_segment_closed(self, estado_prev, inicio, fin):
        estatus = 1 if estado_prev == "ACTIVO" else 0
        print(f"📝 Registrando tramo {estado_prev} de {inicio} a {fin} (estatus={estatus})")
        self.recorder.on_segment(estado_prev, inicio, fin)

        # Actualizar UI del estado actual (el nuevo estado ya está aplicado dentro de la StateMachine)
        self.label_estado_visual.config(
            text=" ACTIVO " if (self.state_machine.estado_actual == "ACTIVO") else " IDLE ",
            bg="#4CAF50" if (self.state_machine.estado_actual == "ACTIVO") else "#F44336"
        )

    def update_frame(self):
        ret, frame, ts_actual = self.source.read()
        if not ret:
            print("📁 Fin del video.")
            ts_fin = self.source.last_ts() or datetime.now()

            # Cerrar tramo final SOLO una vez
            if (not self._segmento_final_cerrado) and (self.state_machine.base_datetime is not None):
                self.state_machine.close_final(ts_fin)
                self._segmento_final_cerrado = True

            # Continuar con el cierre de la app (no vuelve a cerrar el tramo)
            self.on_close()
            return

        # Fijar base_datetime en el primer frame válido
        if self.state_machine.base_datetime is None:
            self.state_machine.base_datetime = self.source.base_datetime

        # Pre-procesado de imagen
        h, w, _ = frame.shape
        ratio = VIDEO_ANCHO_DISPLAY / w
        nuevo_h = int(h * ratio)
        frame_display = cv2.resize(frame, (VIDEO_ANCHO_DISPLAY, nuevo_h))
        gris = cv2.cvtColor(frame_display, cv2.COLOR_BGR2GRAY)
        gris = cv2.GaussianBlur(gris, (21, 21), 0)

        # Inicializar fondo
        if self.fondo is None:
            self.fondo = init_background(gris)
            self._render_frame(frame_display)
            self.root.after(1, self.update_frame)
            return

        # Detección de movimiento
        movimiento, contornos, _ = detect_motion(gris, self.fondo, AREA_MINIMA_CONTORNO)
        for c in contornos:
            if cv2.contourArea(c) >= AREA_MINIMA_CONTORNO:
                x, y, cw, ch = cv2.boundingRect(c)
                cv2.rectangle(frame_display, (x, y), (x + cw, y + ch), (0, 255, 0), 2)

        # Máquina de estados
        estado_detectado = "ACTIVO" if movimiento else "IDLE"
        self.state_machine.process(estado_detectado, ts_actual)

        # UI: estado y tolerancia visual
        self.label_estado_visual.config(
            text=" ACTIVO " if (self.state_machine.estado_actual == "ACTIVO") else " IDLE ",
            bg="#4CAF50" if (self.state_machine.estado_actual == "ACTIVO") else "#F44336"
        )
        restante = self.state_machine.get_tolerancia_restante()
        if restante is not None:
            self.label_timer_visual.config(text=f" {restante}s ", bg="#FF9800")
        else:
            self.label_timer_visual.config(text=" -- ", bg="#b0bec5")

        # Render
        self._render_frame(frame_display)
        self.root.after(1, self.update_frame)

    def _render_frame(self, frame_bgr):
        # Conversión segura a PhotoImage
        from PIL import Image
        img_tk = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)))
        self.panel_video.config(image=img_tk)
        self.panel_video.image = img_tk

    def on_close(self):
        if self._cerrado:
            return  # evita re-entradas
        self._cerrado = True

        try:
            # Si aún hay un tramo abierto y NO se cerró ya al final del video, ciérralo aquí
            if (not self._segmento_final_cerrado) and (self.state_machine.base_datetime is not None):
                ts_fin = self.source.last_ts() or datetime.now()
                self.state_machine.close_final(ts_fin)
                self._segmento_final_cerrado = True

            self.db_manager.cerrar()
        finally:
            try:
                self.source.release()
            except Exception:
                pass
            cv2.destroyAllWindows()
            try:
                self.root.destroy()
            except Exception:
                pass

