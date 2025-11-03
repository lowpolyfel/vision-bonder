import cv2
import os
import time
from ultralytics import YOLO
import tkinter as tk
from tkinter import filedialog

MODEL_PATH = os.path.join("modelos", "monitoreo.pt")
DISPLAY_WIDTH = 900
CONF_THRESHOLD = 0.25
TARGET_CLASS = "bonder_tip"

# --- parámetros de detección de movimiento ---
MOVE_THRESHOLD = 4.0        # píxeles para considerar que sí se movió
COOLDOWN_REPOSO = 10.0       # segundos quieto para decir "REPOSO"
# ------------------------------------------------


def elegir_video():
    root = tk.Tk()
    root.withdraw()
    ruta_video = filedialog.askopenfilename(
        title="Selecciona un video",
        filetypes=[("Videos", "*.mp4 *.avi *.mov *.MOV *"), ("Todos", "*.*")]
    )
    root.destroy()
    return ruta_video


def crear_tracker():
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerMOSSE_create"):
        return cv2.legacy.TrackerMOSSE_create()
    if hasattr(cv2, "TrackerCSRT_create"):
        return cv2.TrackerCSRT_create()
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
        return cv2.legacy.TrackerCSRT_create()
    if hasattr(cv2, "TrackerKCF_create"):
        return cv2.TrackerKCF_create()
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerKCF_create"):
        return cv2.legacy.TrackerKCF_create()
    raise RuntimeError("No hay trackers disponibles en esta versión de OpenCV")


def redimensionar_para_display(frame, width=DISPLAY_WIDTH):
    h, w = frame.shape[:2]
    if w <= width:
        return frame
    scale = width / float(w)
    new_h = int(h * scale)
    return cv2.resize(frame, (width, new_h))


def sanitizar_bbox(bbox, frame_shape):
    x, y, w, h = bbox
    H, W = frame_shape[:2]

    if x < 0: x = 0
    if y < 0: y = 0
    if x + w > W: w = W - x
    if y + h > H: h = H - y

    if w < 5 or h < 5:
        return None

    return (int(x), int(y), int(w), int(h))


def escoger_bonder_tip(results, conf_threshold):
    if results is None or results.boxes is None or len(results.boxes) == 0:
        return None, None

    candidatos = []
    for box in results.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        label = results.names.get(cls_id, f"id_{cls_id}")

        if label != TARGET_CLASS:
            continue
        if conf < conf_threshold:
            continue

        w = x2 - x1
        h = y2 - y1
        candidatos.append({
            "bbox": (x1, y1, w, h),
            "label": label,
            "conf": conf
        })

    if not candidatos:
        return None, None

    candidatos = sorted(candidatos, key=lambda c: c["conf"], reverse=True)
    return candidatos[0]["bbox"], candidatos[0]


def main():
    video_path = elegir_video()
    if not video_path:
        print("No se seleccionó video. Saliendo.")
        return

    if not os.path.exists(MODEL_PATH):
        print(f"No encontré el modelo en: {MODEL_PATH}")
        return

    print("Cargando modelo YOLO...")
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("No se pudo abrir el video.")
        return

    tracker = None
    tracking_activo = False
    info_objeto = None

    # --- MOVIMIENTO ---
    prev_center = None
    is_moving = False
    still_start_time = None  # cuándo empezó a estar quieto
    # -------------------

    print("Presiona 'q' para salir.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if not tracking_activo:
            results = model(frame, conf=CONF_THRESHOLD)[0]

            # dibujar detecciones
            if results.boxes is not None:
                for box in results.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    label = results.names.get(cls_id, f"id_{cls_id}")
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.putText(frame, f"{label} {conf:.2f}", (int(x1), int(y1) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)

            bbox, info = escoger_bonder_tip(results, CONF_THRESHOLD)
            if bbox is not None:
                bbox_int = sanitizar_bbox(bbox, frame.shape)
                if bbox_int is not None:
                    try:
                        tracker = crear_tracker()
                        ok = tracker.init(frame, bbox_int)
                        if ok:
                            tracking_activo = True
                            info_objeto = info
                            # reset de movimiento
                            prev_center = None
                            is_moving = False
                            still_start_time = None
                            print(f"Tracker iniciado sobre: {info_objeto['label']} ({info_objeto['conf']:.2f})")
                        else:
                            print("No se pudo iniciar el tracker con esa bbox (init devolvió False).")
                    except Exception as e:
                        print(f"Error iniciando tracker: {e}")
                        tracker = None
                        tracking_activo = False
                        info_objeto = None

        else:
            ok, bbox = tracker.update(frame)
            if ok:
                x, y, w, h = [int(v) for v in bbox]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                txt = f"{info_objeto['label']} (track)" if info_objeto else "tracking"
                cv2.putText(frame, txt, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2, cv2.LINE_AA)

                # --- MOVIMIENTO con enfriamiento ---
                cx = x + w / 2.0
                cy = y + h / 2.0
                now = time.time()

                if prev_center is not None:
                    dx = cx - prev_center[0]
                    dy = cy - prev_center[1]
                    dist = (dx ** 2 + dy ** 2) ** 0.5

                    if dist > MOVE_THRESHOLD:
                        # hubo movimiento → activar inmediatamente
                        is_moving = True
                        still_start_time = None  # reiniciamos el conteo de reposo
                    else:
                        # casi no se movió → empezar/continuar conteo de reposo
                        if still_start_time is None:
                            still_start_time = now
                        else:
                            elapsed = now - still_start_time
                            if elapsed >= COOLDOWN_REPOSO:
                                is_moving = False
                prev_center = (cx, cy)
            else:
                # tracker perdido
                tracking_activo = False
                tracker = None
                info_objeto = None
                prev_center = None
                is_moving = False
                still_start_time = None

        # --- indicador en pantalla ---
        status_text = "MOVIMIENTO" if is_moving else "REPOSO"
        color = (0, 255, 0) if is_moving else (0, 0, 255)
        cv2.rectangle(frame, (10, 10), (245, 55), (0, 0, 0), -1)
        cv2.putText(frame, status_text, (20, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)

        frame_display = redimensionar_para_display(frame, DISPLAY_WIDTH)
        cv2.imshow("YOLO + Tracker (solo bonder_tip)", frame_display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

