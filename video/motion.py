import cv2

def init_background(frame_gray):
    return frame_gray.copy().astype("float")

def detect_motion(frame_gray, fondo_float, area_minima):
    """
    Aplica acumulación ponderada para actualizar el fondo y
    retorna (movimiento_bool, contornos, fondo_actualizado).
    """
    cv2.accumulateWeighted(frame_gray, fondo_float, 0.5)
    frame_delta = cv2.absdiff(frame_gray, cv2.convertScaleAbs(fondo_float))
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    contornos, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    movimiento = any(cv2.contourArea(c) >= area_minima for c in contornos)
    return movimiento, contornos, fondo_float

