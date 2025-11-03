import cv2
import tkinter as tk
from tkinter import messagebox
import time
from PIL import Image, ImageTk
import mysql.connector
from datetime import datetime

# ===================== Configuración =====================
TOLERANCIA_IDLE_SEGUNDOS = 30
AREA_MINIMA_CONTORNO = 500
VIDEO_FUENTE = "proto1.MOV"
VIDEO_ANCHO_DISPLAY = 640

# --- Base de datos ---
DB_CONFIG = {
    'host': "127.0.0.1",
    'user': "fel",
    'password': "feli123",
    'database': "wb_db"
}
ID_MAQUINA_MONITOREADA = 1

# =========================================================
class DBManager:
    def __init__(self, config):
        self.config = config
        self.cnx = None
        self.cursor = None
        self.conectar()

    def conectar(self):
        try:
            self.cnx = mysql.connector.connect(**self.config)
            self.cursor = self.cnx.cursor()
            print("✅ Conexión a la base de datos establecida.")
        except mysql.connector.Error as err:
            print(f"❌ Error de conexión a BD: {err}")
            messagebox.showerror("Error de BD", f"No se pudo conectar:\n{err}")
            self.cnx = None

    def registrar_evento_completo(self, id_maquina, fecha_inicio, fecha_fin):
        """
        Inserta en operacion_maquina y luego en estado_maquina,
        respetando el AUTO_INCREMENT y las claves foráneas.
        """
        if not self.cnx or not self.cnx.is_connected():
            print("❌ Sin conexión activa. Abortando registro.")
            return

        duracion_seg = int((fecha_fin - fecha_inicio).total_seconds())

        try:
            # --- 1️⃣ Crear operación base (dummy mínima) ---
            sql_operacion = """
                INSERT INTO operacion_maquina (id_maquina, id_operador, id_reel, id_tecnico, id_work_order,
                                               fecha_inicio, fecha_fin)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            valores_op = (id_maquina, 1, 1, 1, 1, fecha_inicio, fecha_fin)
            self.cursor.execute(sql_operacion, valores_op)
            self.cnx.commit()
            id_operacion_generada = self.cursor.lastrowid
            print(f"🧩 Nueva operación creada ID: {id_operacion_generada}")

            # --- 2️⃣ Crear evento en estado_maquina ---
            sql_estado = """
                INSERT INTO estado_maquina (id_operacion, id_maquina, estatus, fecha_inicio, fecha_fin, duracion_seg)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            valores_em = (id_operacion_generada, id_maquina, 0, fecha_inicio, fecha_fin, duracion_seg)
            self.cursor.execute(sql_estado, valores_em)
            self.cnx.commit()
            id_estado = self.cursor.lastrowid
            print(f"✅ Evento completo registrado en estado_maquina (ID: {id_estado})")

        except mysql.connector.Error as err:
            print(f"❌ Error SQL: {err}")
            self.cnx.rollback()

    def cerrar(self):
        if self.cnx and self.cnx.is_connected():
            self.cursor.close()
            self.cnx.close()
            print("🔒 Conexión a BD cerrada.")


# =========================================================
class DetectorApp:
    def __init__(self, root, video_source):
        self.root = root
        self.root.title("Detector de Movimiento v2 - Conectado a BD")
        self.root.configure(bg="#f0f0f0")

        self.db_manager = DBManager(DB_CONFIG)
        self.inicio_activo_timestamp = None
        self.estado_actual = "IDLE"
        self.tiempo_inicio_idle_pendiente = None
        self.fondo = None

        # --- OpenCV ---
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            tk.Label(root, text=f"Error al abrir el video {video_source}",
                     font=("Helvetica", 12, "bold"), fg="red", bg="#f0f0f0").pack(padx=20, pady=20)
            return

        print("🎥 Video cargado, iniciando detección...")

        # --- GUI ---
        self.panel_video = tk.Label(root, bg="black")
        self.panel_video.pack(padx=10, pady=10, fill="both", expand=True)

        status_frame = tk.Frame(root, bg="#d9d9d9", bd=2, relief="sunken")
        status_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.label_estado_visual = tk.Label(status_frame, text=" IDLE ", font=("Helvetica", 16, "bold"),
                                            bg="red", fg="white", width=15, relief="raised", bd=2)
        self.label_estado_visual.pack(side="right", padx=10, pady=10, fill="x", expand=True)

        self.label_timer_visual = tk.Label(root, text=" -- ", font=("Helvetica", 16, "bold"),
                                           bg="#b0bec5", fg="black", width=15, relief="raised", bd=2)
        self.label_timer_visual.pack(pady=10)

        self.btn_quit = tk.Button(root, text="Salir", command=self.on_close,
                                  font=("Helvetica", 10, "bold"), bg="#ff6b6b", fg="white")
        self.btn_quit.pack(pady=(0, 10))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_frame()

    # -----------------------------------------------------
    def procesar_logica_estado(self, movimiento_detectado_en_frame):
        tiempo_actual = time.time()
        deteccion_actual_raw = "ACTIVO" if movimiento_detectado_en_frame else "IDLE"

        if self.estado_actual == "IDLE" and deteccion_actual_raw == "ACTIVO":
            self.estado_actual = "ACTIVO"
            self.inicio_activo_timestamp = datetime.now()
            self.tiempo_inicio_idle_pendiente = None
            print(f"▶️ Cambio a ACTIVO ({self.inicio_activo_timestamp})")

        elif self.estado_actual == "ACTIVO":
            if deteccion_actual_raw == "IDLE":
                if self.tiempo_inicio_idle_pendiente is None:
                    self.tiempo_inicio_idle_pendiente = tiempo_actual
                    print(f"⌛ Esperando {TOLERANCIA_IDLE_SEGUNDOS}s para confirmar IDLE...")
                else:
                    if tiempo_actual - self.tiempo_inicio_idle_pendiente >= TOLERANCIA_IDLE_SEGUNDOS:
                        self.estado_actual = "IDLE"
                        print("🛑 Confirmado cambio a IDLE.")
                        if self.inicio_activo_timestamp:
                            self.db_manager.registrar_evento_completo(
                                ID_MAQUINA_MONITOREADA,
                                self.inicio_activo_timestamp,
                                datetime.now()
                            )
                            self.inicio_activo_timestamp = None
                        self.tiempo_inicio_idle_pendiente = None
            else:
                if self.tiempo_inicio_idle_pendiente:
                    print("🔄 Movimiento retomado, cancelando conteo IDLE.")
                self.tiempo_inicio_idle_pendiente = None

    # -----------------------------------------------------
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            print("📁 Fin del video.")
            self.on_close()
            return

        h, w, _ = frame.shape
        ratio = VIDEO_ANCHO_DISPLAY / w
        nuevo_h = int(h * ratio)
        frame_display = cv2.resize(frame, (VIDEO_ANCHO_DISPLAY, nuevo_h))
        gris = cv2.cvtColor(frame_display, cv2.COLOR_BGR2GRAY)
        gris = cv2.GaussianBlur(gris, (21, 21), 0)

        if self.fondo is None:
            self.fondo = gris.copy().astype("float")
            self.root.after(30, self.update_frame)
            return

        cv2.accumulateWeighted(gris, self.fondo, 0.5)
        frame_delta = cv2.absdiff(gris, cv2.convertScaleAbs(self.fondo))
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contornos, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        movimiento_detectado = any(cv2.contourArea(c) >= AREA_MINIMA_CONTORNO for c in contornos)
        for c in contornos:
            if cv2.contourArea(c) >= AREA_MINIMA_CONTORNO:
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame_display, (x, y), (x + w, y + h), (0, 255, 0), 2)

        self.procesar_logica_estado(movimiento_detectado)

        self.label_estado_visual.config(
            text=" ACTIVO " if self.estado_actual == "ACTIVO" else " IDLE ",
            bg="#4CAF50" if self.estado_actual == "ACTIVO" else "#F44336"
        )

        if self.tiempo_inicio_idle_pendiente:
            restante = int(TOLERANCIA_IDLE_SEGUNDOS - (time.time() - self.tiempo_inicio_idle_pendiente))
            self.label_timer_visual.config(text=f" {max(0, restante)}s ", bg="#FF9800")
        else:
            self.label_timer_visual.config(text=" -- ", bg="#b0bec5")

        img_tk = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame_display, cv2.COLOR_BGR2RGB)))
        self.panel_video.config(image=img_tk)
        self.panel_video.image = img_tk

        self.root.after(30, self.update_frame)

    def on_close(self):
        if self.inicio_activo_timestamp:
            self.db_manager.registrar_evento_completo(
                ID_MAQUINA_MONITOREADA,
                self.inicio_activo_timestamp,
                datetime.now()
            )
        self.db_manager.cerrar()
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = DetectorApp(root, VIDEO_FUENTE)
    root.mainloop()

