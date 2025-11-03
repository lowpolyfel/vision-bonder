import cv2
import os
from ultralytics import YOLO
import tkinter as tk
from tkinter import filedialog

MODEL_PATH = os.path.join("modelos", "monitoreo.pt")
DISPLAY_WIDTH = 900
CONF_THRESHOLD = 0.25
TARGET_CLASS = "bonder_tip"


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
    """
    En Raspberry muchas veces el que sí jala es el MOSSE legacy.
    Lo ponemos primero.
    """
    # MOSSE legacy
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerMOSSE_create"):
        return cv2.legacy.TrackerMOSSE_create()
    # CSRT normal
    if hasattr(cv2, "TrackerCSRT_create"):
        return cv2.TrackerCSRT_create()
    # CSRT legacy
    if hasattr(cv2, "legacy") and hasattr(cv2.legacy, "TrackerCSRT_create"):
        return cv2.legacy.TrackerCSRT_create()
    # KCF
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

    # recorte a los límites
    if x < 0: x = 0
    if y < 0: y = 0
    if x + w > W: w = W - x
    if y + h > H: h = H - y

    # tamaño mínimo
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

        # aquí ignoramos TODO lo que no sea bonder_tip
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

    print("Presiona 'q' para salir.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if not tracking_activo:
            results = model(frame, conf=CONF_THRESHOLD)[0]

            # dibujar todo lo detectado para debug
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
                # debug: ver qué bbox estamos intentando
                print(f"bbox detectada para tracker: {bbox}")
                bbox_int = sanitizar_bbox(bbox, frame.shape)
                print(f"bbox saneada: {bbox_int}")

                if bbox_int is None:
                    print("BBox demasiado pequeña o fuera de cuadro. Esperando otra detección...")
                else:
                    try:
                        tracker = crear_tracker()
                        ok = tracker.init(frame, bbox_int)
                        print(f"tipo de tracker: {type(tracker)}; init={ok}")
                        if ok:
                            tracking_activo = True
                            info_objeto = info
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
            else:
                print("Tracker perdido, regresando a YOLO...")
                tracking_activo = False
                tracker = None
                info_objeto = None

        frame_display = redimensionar_para_display(frame, DISPLAY_WIDTH)
        cv2.imshow("YOLO + Tracker (solo bonder_tip)", frame_display)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

