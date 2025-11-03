import cv2
import os
import time
from ultralytics import YOLO
import tkinter as tk
from tkinter import filedialog

# --- CONFIG ---
MODEL_PATH = os.path.join("modelos", "monitoreo.pt")
DISPLAY_WIDTH = 900
CONF_THRESHOLD = 0.25
TARGET_CLASS = "bonder_tip"

# indicador de máquina (el lento)
MOVE_THRESHOLD_IDLE = 4.0
COOLDOWN_REPOSO = 5.0  # seg

# conteo de golpes (el rápido)
FAST_MOVE_THRESHOLD = 2.0   # píxeles para decir "hubo un golpe"
# -----------------


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
    # prioridad MOSSE porque suele estar en Raspberry
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


def piezas_desde_movimientos(movimientos):
    """
    Regla que tú nos diste:
    - 0..14 mov  -> 7 piezas máx (1ª operación)
      en realidad: cada 2 movimientos = 1 pieza
    - 14..28 mov -> +7 piezas (2ª operación)
    - 28..40 mov -> +6 piezas (3ª operación)
    total 20

    Lo hacemos por tramos.
    """
    if movimientos <= 0:
        return 0

    piezas = 0

    # tramo 1: 0..14 -> máx 7 piezas
    if movimientos <= 14:
        piezas = movimientos // 2
        return piezas

    # ya pasamos los 14 primeros
    piezas = 7  # primeras 7 piezas completas
    # tramo 2: 14..28
    if movimientos <= 28:
        extra_movs = movimientos - 14
        piezas += extra_movs // 2
        return piezas

    # ya pasamos 28
    piezas = 14  # 7 + 7
    # tramo 3: 28..40
    extra_movs = movimientos - 28
    piezas += extra_movs // 2  # aquí solo llegará hasta +6
    if piezas > 20:
        piezas = 20
    return piezas


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

    # --- estado lento (idle/activo) ---
    prev_center_idle = None
    is_moving_idle = False
    still_start_time = None

    # --- estado rápido (conteo) ---
    prev_center_fast = None
    movement_counter = 0      # 0..40
    frame_counter = 0         # cuántos frames completos lleva
    # para no contar muchas veces el mismo golpe:
    fast_moving_now = False   # true mientras está en el pico

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

                            # reset de estados
                            prev_center_idle = None
                            is_moving_idle = False
                            still_start_time = None

                            prev_center_fast = None
                            fast_moving_now = False
                            # ojo: no reseteamos counters globales aquí
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

                # centros para ambas lógicas
                cx = x + w / 2.0
                cy = y + h / 2.0
                now = time.time()

                # 1) LÓGICA LENTA (idle/activo) con enfriamiento
                if prev_center_idle is not None:
                    dx_idle = cx - prev_center_idle[0]
                    dy_idle = cy - prev_center_idle[1]
                    dist_idle = (dx_idle ** 2 + dy_idle ** 2) ** 0.5

                    if dist_idle > MOVE_THRESHOLD_IDLE:
                        is_moving_idle = True
                        still_start_time = None
                    else:
                        if still_start_time is None:
                            still_start_time = now
                        else:
                            if (now - still_start_time) >= COOLDOWN_REPOSO:
                                is_moving_idle = False
                prev_center_idle = (cx, cy)

                # 2) LÓGICA RÁPIDA (conteo de golpes)
                if prev_center_fast is not None:
                    dx_fast = cx - prev_center_fast[0]
                    dy_fast = cy - prev_center_fast[1]
                    dist_fast = (dx_fast ** 2 + dy_fast ** 2) ** 0.5

                    if dist_fast > FAST_MOVE_THRESHOLD:
                        # hay un golpe/mov. rápido
                        if not fast_moving_now:
                            movement_counter += 1
                            fast_moving_now = True
                            # si llegamos a 40 → frame completo
                            if movement_counter >= 40:
                                frame_counter += 1
                                movement_counter = 0
                    else:
                        # ya no está en el pico, liberamos para contar otro
                        fast_moving_now = False

                prev_center_fast = (cx, cy)

            else:
                # tracker perdido → volver a detección
                tracking_activo = False
                tracker = None
                info_objeto = None
                prev_center_idle = None
                still_start_time = None
                prev_center_fast = None
                fast_moving_now = False

        # calcular piezas con la regla de 14+14+12
        piezas_actuales = piezas_desde_movimientos(movement_counter)

        # --- OVERLAYS ---
        # 1) estado máquina
        status_text = "MOVIMIENTO" if is_moving_idle else "REPOSO"
        color = (0, 255, 0) if is_moving_idle else (0, 0, 255)
        cv2.rectangle(frame, (10, 10), (260, 55), (0, 0, 0), -1)
        cv2.putText(frame, status_text, (20, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)

        # 2) contadores
        # movimientos: actual / 40
        cv2.rectangle(frame, (10, 65), (330, 150), (0, 0, 0), -1)
        cv2.putText(frame, f"Movs: {movement_counter}/40", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Piezas: {piezas_actuales}/20", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Frames: {frame_counter}", (20, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        frame_display = redimensionar_para_display(frame, DISPLAY_WIDTH)
        cv2.imshow("Monitoreo bonder_tip", frame_display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

