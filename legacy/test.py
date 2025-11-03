import cv2
import tkinter as tk
from tkinter import messagebox, filedialog
import time
from PIL import Image, ImageTk
import mysql.connector
from datetime import datetime, timedelta

# ===================== Configuración =====================
TOLERANCIA_IDLE_SEGUNDOS = 30
AREA_MINIMA_CONTORNO = 500
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

    def _siguiente_id(self, tabla, pk_col):
        """Obtiene MAX(pk_col)+1 (fallback si no hay AUTO_INCREMENT)."""
        self.cursor.execute(f"SELECT COALESCE(MAX({pk_col}), 0) + 1 FROM {tabla}")
        (next_id,) = self.cursor.fetchone()
        return int(next_id)

    def registrar_evento_completo(self, id_maquina, fecha_inicio, fecha_fin, estatus):
        """
        Inserta una operación y su estado asociado con el estatus indicado:
        estatus: 1=ACTIVO, 0=IDLE
        """
        if not self.cnx or not self.cnx.is_connected():
            print("❌ Sin conexión activa. Abortando registro.")
            return

        try:
            self.cnx.start_transaction()

            # 1) Insert en operacion_maquina (dummy mínima para satisfacer FK)
            sql_operacion = """
                INSERT INTO operacion_maquina (
                    id_maquina, id_operador, id_reel, id_tecnico, id_work_order,
                    fecha_inicio, fecha_fin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            valores_op = (id_maquina, 1, 1, 1, 1, fecha_inicio, fecha_fin)
            self.cursor.execute(sql_operacion, valores_op)
            id_operacion_generada = self.cursor.lastrowid
            # 2) Insert en estado_maquina con o sin PK (según esquema)
            duracion_seg = int((fecha_fin - fecha_inicio).total_seconds())
            sql_estado_sin_pk = """
                INSERT INTO estado_maquina (
                    id_operacion, id_maquina, estatus, fecha_inicio, fecha_fin, duracion_seg
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            valores_estado = (id_operacion_generada, id_maquina, estatus, fecha_inicio, fecha_fin, duracion_seg)

            try:
                self.cursor.execute(sql_estado_sin_pk, valores_estado)
            except mysql.connector.Error as e:
                # Fallback: generar PK manual
                next_id = self._siguiente_id("estado_maquina", "id_estado_maquina")
                sql_estado_con_pk = """
                    INSERT INTO estado_maquina (
                        id_estado_maquina, id_operacion, id_maquina, estatus, fecha_inicio, fecha_fin, duracion_seg
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                valores_estado_con_pk = (next_id,) + valores_estado
                self.cursor.execute(sql_estado_con_pk, valores_estado_con_pk)

            self.cnx.commit()

        except mysql.connector.Error as err:
            print(f"❌ Error SQL (rollback): {err}")
            try:
                self.cnx.rollback()
            except Exception:
                pass

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

        # Estado y tiempos (alineados al TIEMPO DE VIDEO)
        self.estado_actual = None                     # "IDLE" o "ACTIVO" (se determinará al primer análisis)
        self.inicio_estado_timestamp = None           # datetime anclado al inicio del video
        self.base_datetime = None                     # datetime que representa el t=0 del video
        self.ultimo_timestamp_video = None            # último timestamp de video usado (datetime)
        self.tiempo_inicio_idle_pendiente = None      # para tolerancia (reloj del sistema, no se registra)

        # Fallback si el códec no da POS_MSEC
        self.frame_idx = 0
        self.fps = None

        # Fondo para sustracción
        self.fondo = None

        # --- OpenCV ---
        self.cap = cv2.VideoCapture(video_source)
        if not self.cap.isOpened():
            tk.Label(root, text=f"Error al abrir el video:\n{video_source}",
                     font=("Helvetica", 12, "bold"), fg="red", bg="#f0f0f0", justify="left").pack(padx=20, pady=20)
            tk.Button(root, text="Cerrar", command=self.on_close,
                      font=("Helvetica", 10, "bold"), bg="#ff6b6b", fg="white").pack(pady=(0, 10))
            return

        # Preparar metadatos
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
        if not self.fps or self.fps <= 0:
            self.fps = 30.0  # fallback razonable

        print("🎥 Video cargado. Tiempos alineados al video (no al reloj del sistema).")

        # --- GUI ---
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
        self.update_frame()

    # ---------------------- Utilidades de tiempo ----------------------
    def _timestamp_video_actual(self):
        """
        Convierte la posición actual del video a un datetime = base_datetime + POS_MSEC.
        Si POS_MSEC no está disponible, usa frame_idx / fps.
        """
        pos_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        if pos_ms and pos_ms > 0:
            delta = timedelta(milliseconds=float(pos_ms))
        else:
            # Fallback por frames
            delta = timedelta(seconds=self.frame_idx / self.fps)
        if self.base_datetime is None:
            # Anclar inicio del video al momento de este primer cálculo menos delta, de modo que
            # base_datetime + delta == now (alineado a t=0 del video)
            self.base_datetime = datetime.now() - delta
        current_ts = self.base_datetime + delta
        self.ultimo_timestamp_video = current_ts
        return current_ts

    # ---------------------- Registro de tramos ----------------------
    def _cerrar_y_registrar_tramo_actual(self, nuevo_estado, ts_actual):
        """
        Cierra el tramo del estado actual (desde self.inicio_estado_timestamp hasta ts_actual),
        lo registra en BD con estatus 0/1, y abre un nuevo tramo desde ts_actual con nuevo_estado.
        """
        if self.estado_actual is not None and self.inicio_estado_timestamp is not None:
            estatus_actual = 1 if self.estado_actual == "ACTIVO" else 0
            # No registramos tolerancia: ts_actual es el momento confirmado del cambio
            self.db_manager.registrar_evento_completo(
                ID_MAQUINA_MONITOREADA,
                self.inicio_estado_timestamp,
                ts_actual,
                estatus_actual
            )

        # Abrir nuevo tramo
        self.estado_actual = nuevo_estado
        self.inicio_estado_timestamp = ts_actual
        estado_txt = " ACTIVO " if nuevo_estado == "ACTIVO" else " IDLE "
        self.label_estado_visual.config(
            text=estado_txt,
            bg="#4CAF50" if nuevo_estado == "ACTIVO" else "#F44336"
        )

    # ---------------------- Lógica de estados ----------------------
    def procesar_logica_estado(self, movimiento_detectado_en_frame, ts_actual):
        """
        Reglas:
        1/2: Al cambiar, cerrar tramo anterior y abrir nuevo (con tolerancia al volver a IDLE).
        3/4: El primer estado (IDLE/ACTIVO) se decide al primer análisis y se ancla al inicio del video.
        5: La tolerancia no se registra; solo decide cuándo confirmar el cambio.
        """
        # Estado detectado en este frame
        estado_detectado = "ACTIVO" if movimiento_detectado_en_frame else "IDLE"

        # Inicialización del estado (primer análisis válido): anclar al t0 del video
        if self.estado_actual is None:
            ts_inicio_video = self.base_datetime if self.base_datetime else ts_actual
            # Asegurar que el primer tramo inicie exactamente en el inicio del video (t=0)
            self.inicio_estado_timestamp = ts_inicio_video
            self.estado_actual = estado_detectado
            self.label_estado_visual.config(
                text=" ACTIVO " if self.estado_actual == "ACTIVO" else " IDLE ",
                bg="#4CAF50" if self.estado_actual == "ACTIVO" else "#F44336"
            )
            return

        # Transiciones
        if self.estado_actual == "IDLE":
            if estado_detectado == "ACTIVO":
                # Cambio inmediato a ACTIVO: cerrar IDLE [t0..ts_actual] y abrir ACTIVO desde ts_actual
                self._cerrar_y_registrar_tramo_actual("ACTIVO", ts_actual)
                self.tiempo_inicio_idle_pendiente = None

        elif self.estado_actual == "ACTIVO":
            if estado_detectado == "IDLE":
                # Aplicar tolerancia para confirmar vuelta a IDLE
                if self.tiempo_inicio_idle_pendiente is None:
                    self.tiempo_inicio_idle_pendiente = time.time()
                else:
                    if time.time() - self.tiempo_inicio_idle_pendiente >= TOLERANCIA_IDLE_SEGUNDOS:
                        # Confirmado: cerrar ACTIVO [..ts_actual] y abrir IDLE desde ts_actual
                        self._cerrar_y_registrar_tramo_actual("IDLE", ts_actual)
                        self.tiempo_inicio_idle_pendiente = None
            else:
                # Sigue ACTIVO: cancelar conteo si había
                self.tiempo_inicio_idle_pendiente = None

        # UI de contador de tolerancia (solo visual)
        if self.tiempo_inicio_idle_pendiente:
            restante = int(TOLERANCIA_IDLE_SEGUNDOS - (time.time() - self.tiempo_inicio_idle_pendiente))
            self.label_timer_visual.config(text=f" {max(0, restante)}s ", bg="#FF9800")
        else:
            self.label_timer_visual.config(text=" -- ", bg="#b0bec5")

    # ---------------------- Bucle de frames ----------------------
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            print("📁 Fin del video.")
            # Cerrar y registrar tramo final hasta el último timestamp conocido del video
            ts_fin = self.ultimo_timestamp_video or datetime.now()
            self._cerrar_y_registrar_tramo_final(ts_fin)
            self.on_close()
            return

        self.frame_idx += 1
        ts_actual = self._timestamp_video_actual()

        # Pre-procesado
        h, w, _ = frame.shape
        ratio = VIDEO_ANCHO_DISPLAY / w
        nuevo_h = int(h * ratio)
        frame_display = cv2.resize(frame, (VIDEO_ANCHO_DISPLAY, nuevo_h))
        gris = cv2.cvtColor(frame_display, cv2.COLOR_BGR2GRAY)
        gris = cv2.GaussianBlur(gris, (21, 21), 0)

        # Inicializar fondo y esperar al siguiente frame
        if self.fondo is None:
            self.fondo = gris.copy().astype("float")
            self._dibujar_frame(frame_display)
            self.root.after(1, self.update_frame)
            return

        # Detección de movimiento
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

        # Lógica de estados con tiempo de video
        self.procesar_logica_estado(movimiento_detectado, ts_actual)

        # Render
        self._dibujar_frame(frame_display)
        self.root.after(1, self.update_frame)

    def _dibujar_frame(self, frame_bgr):
        img_tk = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)))
        self.panel_video.config(image=img_tk)
        self.panel_video.image = img_tk

    def _cerrar_y_registrar_tramo_final(self, ts_fin):
        """Al terminar el video, registra el tramo vigente [inicio_estado_timestamp .. ts_fin]."""
        if self.estado_actual is not None and self.inicio_estado_timestamp is not None:
            estatus_actual = 1 if self.estado_actual == "ACTIVO" else 0
            self.db_manager.registrar_evento_completo(
                ID_MAQUINA_MONITOREADA,
                self.inicio_estado_timestamp,
                ts_fin,
                estatus_actual
            )

    def on_close(self):
        try:
            # Si aún hay tramo abierto y no se registró (por cierre manual)
            if self.estado_actual is not None and self.inicio_estado_timestamp is not None:
                ts_fin = self.ultimo_timestamp_video or datetime.now()
                self._cerrar_y_registrar_tramo_final(ts_fin)
            self.db_manager.cerrar()
        finally:
            if hasattr(self, "cap") and self.cap and self.cap.isOpened():
                self.cap.release()
            cv2.destroyAllWindows()
            try:
                self.root.destroy()
            except Exception:
                pass


# =========================================================
def seleccionar_video_por_dialogo(root):
    """
    Abre un diálogo para seleccionar el archivo de video (soporta extensiones en mayúsculas y minúsculas).
    """
    tipos = [
        ("Archivos de video", "*.mp4 *.MP4 *.mov *.MOV *.avi *.AVI *.mkv *.MKV *.m4v *.M4V *.wmv *.WMV"),
        ("Todos los archivos", "*.*"),
    ]
    return filedialog.askopenfilename(
        title="Selecciona un archivo de video",
        filetypes=tipos
    )


# =========================================================
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    video_path = seleccionar_video_por_dialogo(root)

    if not video_path:
        messagebox.showinfo("Sin archivo", "No seleccionaste un video. Saliendo.")
        try:
            root.destroy()
        except Exception:
            pass
    else:
        root.deiconify()
        app = DetectorApp(root, video_path)
        root.mainloop()

