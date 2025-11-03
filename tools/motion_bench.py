

































#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cv2
import numpy as np
from tkinter import Tk, Toplevel, Label, filedialog
from PIL import Image, ImageTk

# ===================== Configuración =====================
# Resolución de procesamiento (ligero)
PROC_SIZE = (640, 360)

# Tamaño final de la ventana (16:9)
OUTPUT_W = 1280
OUTPUT_H = 720

# Layout de la rejilla inferior
ENGINE_TILE_W = 300    # ancho del render de cada motor (izquierda)
ENGINE_TILE_H = 180    # alto del render de cada motor
CARD_W = 100           # ancho de la card (derecha)
CARD_H = ENGINE_TILE_H
GAP_X = 10             # espacios horizontales
GAP_Y = 10             # espacios verticales
BOTTOM_COLS = 3        # 3 columnas (dos filas) = 6 motores

AREA_MINIMA_CONTORNO = 500
FG_BIN_THRESH = 25
FLOW_MAG_THRESH = 2.0
FONT = cv2.FONT_HERSHEY_SIMPLEX

# Colores (BGR)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY_LIGHT = (230, 230, 230)
GREEN = (0, 170, 0)
RED = (0, 0, 220)

# ===================== Selector de video =====================
def seleccionar_video():
    root = Tk()
    root.withdraw()
    tipos = [
        ("Todos los archivos", "*.*"),
        ("Archivos de video", (
            "*.[Mm][Pp]4", "*.[Mm][Oo][Vv]", "*.[Aa][Vv][Ii]", "*.[Mm][Kk][Vv]",
            "*.[Mm]4[Vv]", "*.[Ww][Mm][Vv]", "*.[Mm][Pp][Ee][Gg]", "*.[Mm][Pp][Gg]",
            "*.[Mm][Tt][Ss]", "*.[Tt][Ss]", "*.[Hh]264", "*.[Hh]265",
            "*.[Hh][Ee][Vv][Cc]", "*.[3][Gg][Pp]",
        )),
    ]
    path = filedialog.askopenfilename(
        title="Selecciona un video para el benchmark",
        initialdir=os.getcwd(),
        filetypes=tipos
    )
    root.destroy()
    return path

# ===================== Utilidades =====================
def resize_keep_aspect(img, width=None, height=None):
    h, w = img.shape[:2]
    if width is not None:
        scale = width / float(w)
        new_w, new_h = width, int(h * scale)
    elif height is not None:
        scale = height / float(h)
        new_h, new_w = height, int(w * scale)
    else:
        return img
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

def decision_from_mask(mask, area_min=AREA_MINIMA_CONTORNO):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        if cv2.contourArea(c) >= area_min:
            return True, cnts
    return False, cnts

def draw_status_pill(img, text, color, org=(10, 28)):
    cv2.rectangle(img, (org[0]-6, org[1]-20), (org[0]+110, org[1]+8), color, -1)
    cv2.putText(img, text, org, FONT, 0.6, WHITE, 2, cv2.LINE_AA)

def blue_card_like(engine_name, active):
    """
    Card limpia sobre fondo blanco con borde gris claro.
    Estado en color (verde/rojo) + nombre del motor en negro.
    """
    card = np.full((CARD_H, CARD_W, 3), WHITE, dtype=np.uint8)
    # Borde
    cv2.rectangle(card, (0, 0), (CARD_W-1, CARD_H-1), GRAY_LIGHT, 1, cv2.LINE_AA)

    # Estado
    status_txt = "ACTIVO" if active else "IDLE"
    status_col = GREEN if active else RED
    draw_status_pill(card, status_txt, status_col, org=(10, 30))

    # Separador
    cv2.line(card, (10, 45), (CARD_W-10, 45), GRAY_LIGHT, 1, cv2.LINE_AA)

    # Título (motor)
    y = 70
    for line in wrap_text(engine_name, width_chars=10):
        cv2.putText(card, line, (10, y), FONT, 0.55, BLACK, 1, cv2.LINE_AA)
        y += 22
        if y > CARD_H - 8:
            break
    return card

def wrap_text(text, width_chars=10):
    lines, line = [], ""
    for ch in text:
        if len(line) >= width_chars:
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines

def compose_layout_white(top_img, engine_tiles, cards):
    """
    Lienzo blanco 16:9:
    - Arriba: original centrado
    - Abajo: 2 filas × 3 columnas; en cada columna [tile, GAP, card]
    """
    assert len(engine_tiles) == len(cards) == 6

    # Dimensiones de la rejilla inferior
    col_w = ENGINE_TILE_W + GAP_X + CARD_W
    grid_w = BOTTOM_COLS * col_w + (BOTTOM_COLS - 1) * GAP_X
    bottom_h = 2 * ENGINE_TILE_H + GAP_Y

    # Espacio superior disponible (OUTPUT_H total menos lo de abajo y márgenes)
    margin_top = 20
    margin_bottom = 20
    top_h = OUTPUT_H - bottom_h - margin_top - margin_bottom - GAP_Y

    # Lienzo blanco 16:9
    canvas = np.full((OUTPUT_H, OUTPUT_W, 3), WHITE, dtype=np.uint8)

    # Top: centrado
    top_area_w = min(grid_w, OUTPUT_W - 2 * GAP_X)
    top_area_h = top_h
    top_resized = resize_keep_aspect(top_img, width=top_area_w)
    if top_resized.shape[0] > top_area_h:
        top_resized = resize_keep_aspect(top_img, height=top_area_h)

    top_x = (OUTPUT_W - top_resized.shape[1]) // 2
    top_y = margin_top
    canvas[top_y:top_y+top_resized.shape[0], top_x:top_x+top_resized.shape[1]] = top_resized

    # Abajo: colocar 6 pares (tile + card)
    start_y = margin_top + top_h + GAP_Y
    for idx in range(6):
        row = idx // BOTTOM_COLS
        col = idx % BOTTOM_COLS
        x0 = (OUTPUT_W - grid_w) // 2 + col * (col_w + GAP_X)
        y0 = start_y + row * (ENGINE_TILE_H + GAP_Y)

        tile = cv2.resize(engine_tiles[idx], (ENGINE_TILE_W, ENGINE_TILE_H), interpolation=cv2.INTER_AREA)
        card = cv2.resize(cards[idx], (CARD_W, CARD_H), interpolation=cv2.INTER_AREA)

        canvas[y0:y0+ENGINE_TILE_H, x0:x0+ENGINE_TILE_W] = tile
        canvas[y0:y0+CARD_H, x0+ENGINE_TILE_W+GAP_X:x0+ENGINE_TILE_W+GAP_X+CARD_W] = card

    return canvas

# ===================== Motores =====================
class EngineRunningAverage:
    def __init__(self): self.bg = None
    def process(self, gray):
        if self.bg is None:
            self.bg = gray.copy().astype("float")
            return np.zeros_like(gray)
        cv2.accumulateWeighted(gray, self.bg, 0.5)
        delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.bg))
        _, th = cv2.threshold(delta, FG_BIN_THRESH, 255, cv2.THRESH_BINARY)
        th = cv2.dilate(th, None, iterations=2)
        return th

class EngineFirstFrameDiff:
    def __init__(self): self.first = None
    def process(self, gray):
        if self.first is None:
            self.first = gray.copy()
            return np.zeros_like(gray)
        delta = cv2.absdiff(gray, self.first)
        _, th = cv2.threshold(delta, FG_BIN_THRESH, 255, cv2.THRESH_BINARY)
        th = cv2.dilate(th, None, iterations=2)
        return th

class EngineThreeFrameDiff:
    def __init__(self):
        self.prev2 = None
        self.prev1 = None
    def process(self, gray):
        if self.prev1 is None:
            self.prev1 = gray.copy()
            return np.zeros_like(gray)
        if self.prev2 is None:
            self.prev2 = self.prev1.copy()
            self.prev1 = gray.copy()
            return np.zeros_like(gray)
        diff1 = cv2.absdiff(gray, self.prev1)
        diff2 = cv2.absdiff(self.prev1, self.prev2)
        th1 = cv2.threshold(diff1, FG_BIN_THRESH, 255, cv2.THRESH_BINARY)[1]
        th2 = cv2.threshold(diff2, FG_BIN_THRESH, 255, cv2.THRESH_BINARY)[1]
        th = cv2.bitwise_and(th1, th2)
        th = cv2.dilate(th, None, iterations=2)
        self.prev2 = self.prev1
        self.prev1 = gray.copy()
        return th

class EngineMOG2:
    def __init__(self):
        self.sub = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=16, detectShadows=True)
    def process(self, gray):
        fg = self.sub.apply(gray)
        fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)[1]  # filtra sombras
        fg = cv2.dilate(fg, None, iterations=2)
        return fg

class EngineKNN:
    def __init__(self):
        self.sub = cv2.createBackgroundSubtractorKNN(history=400, dist2Threshold=400.0, detectShadows=True)
    def process(self, gray):
        fg = self.sub.apply(gray)
        fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)[1]
        fg = cv2.dilate(fg, None, iterations=2)
        return fg

class EngineOpticalFlow:
    def __init__(self):
        self.prev = None
    def process(self, gray):
        if self.prev is None:
            self.prev = gray.copy()
            return np.zeros_like(gray)
        flow = cv2.calcOpticalFlowFarneback(self.prev, gray, None,
                                            pyr_scale=0.5, levels=3, winsize=15,
                                            iterations=3, poly_n=5, poly_sigma=1.2, flags=0)
        mag, _ = cv2.cartToPolar(flow[...,0], flow[...,1])
        mask = (mag > FLOW_MAG_THRESH).astype(np.uint8) * 255
        mask = cv2.dilate(mask, None, iterations=1)
        self.prev = gray.copy()
        return mask

# ===================== App Tkinter =====================
class MotionBenchTk:
    def __init__(self, master, video_path):
        self.master = master
        self.master.title("Motion Bench 640x360 — 16:9 — Tkinter (Q: salir, P: pausa)")
        self.master.configure(bg="#FFFFFF")
        try:
            # Intenta ajustar tamaño de la ventana
            self.master.geometry(f"{OUTPUT_W}x{OUTPUT_H}")
        except Exception:
            pass

        self.label = Label(self.master, bg="#FFFFFF")
        self.label.pack(fill="both", expand=True)

        # Estado
        self.paused = False
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.label.config(text=f"No se pudo abrir: {video_path}", fg="red", bg="white")
            return

        # Motores
        self.engines = [
            ("RunningAvg", EngineRunningAverage()),
            ("FirstFrame", EngineFirstFrameDiff()),
            ("3-FrameDiff", EngineThreeFrameDiff()),
            ("MOG2",       EngineMOG2()),
            ("KNN",        EngineKNN()),
            ("OptFlow",    EngineOpticalFlow()),
        ]

        # Bind de teclas
        self.master.bind("<KeyPress-q>", lambda e: self.on_close())
        self.master.bind("<KeyPress-Q>", lambda e: self.on_close())
        self.master.bind("<KeyPress-p>", lambda e: self.toggle_pause())
        self.master.bind("<KeyPress-P>", lambda e: self.toggle_pause())

        # Loop
        self.update_frame()

    def toggle_pause(self):
        self.paused = not self.paused

    def update_frame(self):
        if not self.paused:
            ret, frame = self.cap.read()
            if not ret:
                self.label.config(text="Fin del video.", fg="black", bg="white")
                self.master.after(1200, self.on_close)
                return

            # Procesamiento ligero
            frame = cv2.resize(frame, PROC_SIZE, interpolation=cv2.INTER_AREA)
            disp_top = frame.copy()

            gray_base = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_base = cv2.GaussianBlur(gray_base, (21, 21), 0)

            engine_tiles, cards = [], []
            for label, engine in self.engines:
                fgmask = engine.process(gray_base)
                activo, cnts = decision_from_mask(fgmask, AREA_MINIMA_CONTORNO)

                vis = cv2.cvtColor(fgmask, cv2.COLOR_GRAY2BGR)
                for c in cnts:
                    if cv2.contourArea(c) >= AREA_MINIMA_CONTORNO:
                        x, y, w, h = cv2.boundingRect(c)
                        cv2.rectangle(vis, (x, y), (x+w, y+h), (0,255,0), 2)

                # Subtítulo/estado sobre el tile
                status_txt = "ACTIVO" if activo else "IDLE"
                status_col = GREEN if activo else RED
                cv2.putText(vis, status_txt, (10, 24), FONT, 0.7, status_col, 2, cv2.LINE_AA)
                cv2.putText(vis, label, (10, 48), FONT, 0.6, (60,60,60), 2, cv2.LINE_AA)

                engine_tiles.append(vis)
                cards.append(blue_card_like(label, activo))

            # Componer mosaico blanco 16:9 y mostrar en Tkinter
            mosaic = compose_layout_white(disp_top, engine_tiles, cards)
            mosaic = cv2.resize(mosaic, (OUTPUT_W, OUTPUT_H), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(mosaic, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=im)
            self.label.configure(image=imgtk)
            self.label.image = imgtk

        # Programa el siguiente frame
        self.master.after(1, self.update_frame)

    def on_close(self):
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        self.master.destroy()

# ===================== MAIN =====================
def main():
    path = seleccionar_video()
    if not path:
        print("No seleccionaste video. Saliendo.")
        return

    root = Tk()
    app = MotionBenchTk(root, path)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()

















































































































































































































































































































