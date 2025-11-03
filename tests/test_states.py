#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cv2
import numpy as np
from tkinter import Tk, Label, filedialog
from PIL import Image, ImageTk

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
PROC_SIZE = (480, 270)         # procesamos bajito para ir rápido
OUTPUT_W = 1600                # ventana final
OUTPUT_H = 900

# layout inferior (solo para modo MULTI)
ENGINE_TILE_W = 300
ENGINE_TILE_H = 160
CARD_W = 110
CARD_H = ENGINE_TILE_H
GAP_X = 8
GAP_Y = 8
BOTTOM_COLS = 3   # 3 columnas → 6 trackers en 2 filas

# colores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY_LIGHT = (230, 230, 230)
GREEN = (0, 170, 0)
RED = (0, 0, 220)

FONT = cv2.FONT_HERSHEY_SIMPLEX

TRACKER_NAMES = ["KCF", "CSRT", "MOSSE", "MIL", "MedianFlow", "Boosting"]


# =========================================================
# SELECTOR DE VIDEO
# =========================================================
def seleccionar_video():
    root = Tk()
    root.withdraw()
    tipos = [
        ("Todos los archivos", "*.*"),
        ("Videos", (
            "*.[Mm][Pp]4", "*.[Mm][Oo][Vv]", "*.[Aa][Vv][Ii]", "*.[Mm][Kk][Vv]",
            "*.[Mm]4[Vv]", "*.[Ww][Mm][Vv]", "*.[Mm][Pp][Ee][Gg]", "*.[Mm][Pp][Gg]",
            "*.[Mm][Tt][Ss]", "*.[Tt][Ss]", "*.[Hh]264", "*.[Hh]265",
            "*.[Hh][Ee][Vv][Cc]", "*.[3][Gg][Pp]",
        )),
    ]
    path = filedialog.askopenfilename(
        title="Selecciona un video",
        initialdir=os.getcwd(),
        filetypes=tipos
    )
    root.destroy()
    return path


# =========================================================
# UTILIDADES GENERALES
# =========================================================
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


def make_card(title, status_txt, status_ok, cycles):
    card = np.full((CARD_H, CARD_W, 3), WHITE, dtype=np.uint8)
    cv2.rectangle(card, (0, 0), (CARD_W - 1, CARD_H - 1), GRAY_LIGHT, 1, cv2.LINE_AA)
    color = GREEN if status_ok else RED
    cv2.rectangle(card, (8, 8), (CARD_W - 8, 36), color, -1)
    cv2.putText(card, status_txt, (14, 30), FONT, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.line(card, (8, 44), (CARD_W - 8, 44), GRAY_LIGHT, 1, cv2.LINE_AA)
    y = 68
    for ln in wrap_text(title, 10):
        cv2.putText(card, ln, (10, y), FONT, 0.55, BLACK, 1, cv2.LINE_AA)
        y += 20
    cv2.putText(card, "Ciclos:", (10, CARD_H - 40), FONT, 0.5, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.putText(card, str(cycles), (10, CARD_H - 12), FONT, 0.9, (0, 0, 0), 2, cv2.LINE_AA)
    return card


def compose_layout(top_img, tiles, cards):
    canvas = np.full((OUTPUT_H, OUTPUT_W, 3), WHITE, dtype=np.uint8)

    col_w = ENGINE_TILE_W + GAP_X + CARD_W
    grid_w = BOTTOM_COLS * col_w + (BOTTOM_COLS - 1) * GAP_X
    bottom_h = 2 * ENGINE_TILE_H + GAP_Y

    margin_top = 20
    margin_bottom = 20
    top_h = OUTPUT_H - bottom_h - margin_top - margin_bottom - GAP_Y

    top_area_w = min(grid_w, OUTPUT_W - 2 * GAP_X)
    top_resized = resize_keep_aspect(top_img, width=top_area_w)
    if top_resized.shape[0] > top_h:
        top_resized = resize_keep_aspect(top_img, height=top_h)

    top_x = (OUTPUT_W - top_resized.shape[1]) // 2
    top_y = margin_top
    canvas[top_y:top_y + top_resized.shape[0], top_x:top_x + top_resized.shape[1]] = top_resized

    start_y = margin_top + top_h + GAP_Y
    for idx in range(6):
        row = idx // BOTTOM_COLS
        col = idx % BOTTOM_COLS
        x0 = (OUTPUT_W - grid_w) // 2 + col * (col_w + GAP_X)
        y0 = start_y + row * (ENGINE_TILE_H + GAP_Y)
        tile = cv2.resize(tiles[idx], (ENGINE_TILE_W, ENGINE_TILE_H), interpolation=cv2.INTER_AREA)
        card = cv2.resize(cards[idx], (CARD_W, CARD_H), interpolation=cv2.INTER_AREA)
        canvas[y0:y0 + ENGINE_TILE_H, x0:x0 + ENGINE_TILE_W] = tile
        canvas[y0:y0 + CARD_H, x0 + ENGINE_TILE_W + GAP_X:x0 + ENGINE_TILE_W + GAP_X + CARD_W] = card

    return canvas


# =========================================================
# CONTADOR POR EJE DOMINANTE (AJUSTADO)
# =========================================================
class AxisCycleCounter:
    """
    Aprende el eje de movimiento y cuenta un ciclo completo cada 2 cambios de dirección.
    Esto ayuda cuando la cámara está inclinada y el movimiento es horizontal.
    """
    def __init__(self, warmup_points=5, movement_threshold=1.5, min_span=3):
        self.warmup_points = warmup_points
        self.points = []
        self.axis = None
        self.last_proj = None
        self.direction = 0
        self.cycles = 0
        self.movement_threshold = movement_threshold
        self.min_span = min_span
        self.frame_idx = 0
        self.last_dir_change_frame = 0
        self.dir_changes = 0  # cada 2 dir_changes = 1 ciclo

    def add_point(self, x, y):
        self.frame_idx += 1

        # fase de aprendizaje
        if self.axis is None:
            self.points.append((x, y))
            if len(self.points) >= self.warmup_points:
                self._compute_axis()
            return self.cycles

        # proyección
        proj = x * self.axis[0] + y * self.axis[1]
        if self.last_proj is None:
            self.last_proj = proj
            return self.cycles

        delta = proj - self.last_proj
        if abs(delta) > self.movement_threshold:
            new_dir = 1 if delta > 0 else -1
            if self.direction != 0 and new_dir != self.direction:
                # cambio de dirección válido
                if self.frame_idx - self.last_dir_change_frame > self.min_span:
                    self.dir_changes += 1
                    self.last_dir_change_frame = self.frame_idx
                    # cada 2 cambios → 1 ciclo
                    if self.dir_changes % 2 == 0:
                        self.cycles += 1
            self.direction = new_dir

        self.last_proj = proj
        return self.cycles

    def _compute_axis(self):
        x0, y0 = self.points[0]
        x1, y1 = self.points[-1]
        vx = x1 - x0
        vy = y1 - y0
        norm = (vx ** 2 + vy ** 2) ** 0.5
        if norm < 1.0:
            # casi sin movimiento → asumimos horizontal
            self.axis = np.array([1.0, 0.0], dtype=np.float32)
        else:
            self.axis = np.array([vx / norm, vy / norm], dtype=np.float32)


# =========================================================
# TRACKERS
# =========================================================
def create_tracker_by_name(name):
    name = name.lower()
    if not hasattr(cv2, "legacy"):
        return None
    if name == "kcf":
        return cv2.legacy.TrackerKCF_create()
    if name == "csrt":
        return cv2.legacy.TrackerCSRT_create()
    if name == "mosse":
        return cv2.legacy.TrackerMOSSE_create()
    if name == "mil":
        return cv2.legacy.TrackerMIL_create()
    if name == "medianflow":
        return cv2.legacy.TrackerMedianFlow_create()
    if name == "boosting":
        return cv2.legacy.TrackerBoosting_create()
    return None


# =========================================================
# APP MULTI-TRACKER (el que ya teníamos)
# =========================================================
class MultiTrackerBenchTk:
    def __init__(self, root, video_path):
        self.root = root
        self.root.title("Multi Tracker Bench — 1600x900")
        self.root.configure(bg="white")
        self.root.geometry(f"{OUTPUT_W}x{OUTPUT_H}")

        self.lbl = Label(self.root, bg="white", width=OUTPUT_W, height=OUTPUT_H)
        self.lbl.pack(fill="both", expand=True)

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.lbl.config(text=f"No se pudo abrir: {video_path}", fg="red")
            return

        ret, frame = self.cap.read()
        if not ret:
            self.lbl.config(text="Video vacío", fg="red")
            return

        frame = cv2.resize(frame, PROC_SIZE, interpolation=cv2.INTER_AREA)
        self.first_frame = frame.copy()
        self.frame_w = frame.shape[1]
        self.frame_h = frame.shape[0]

        self.offset_x = (OUTPUT_W - self.frame_w) // 2
        self.offset_y = (OUTPUT_H - self.frame_h) // 2

        self.roi_selecting = True
        self.roi = None
        self.start_x = self.start_y = None
        self.end_x = self.end_y = None

        self.show_frame_for_roi(show_hint=True)

        self.lbl.bind("<Button-1>", self.on_mouse_down)
        self.lbl.bind("<B1-Motion>", self.on_mouse_drag)
        self.lbl.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.root.bind("<KeyPress-q>", lambda e: self.on_close())
        self.root.bind("<KeyPress-Q>", lambda e: self.on_close())

        self.trackers = []
        self.counters = []
        self.paused = False

    # ---------- ROI helpers (multi) ----------
    def show_frame_for_roi(self, rect=None, show_hint=False):
        canvas = np.full((OUTPUT_H, OUTPUT_W, 3), WHITE, dtype=np.uint8)
        canvas[self.offset_y:self.offset_y + self.frame_h,
               self.offset_x:self.offset_x + self.frame_w] = self.first_frame
        if show_hint:
            cv2.rectangle(canvas, (10, 10), (380, 40), (255, 255, 255), -1)
            cv2.putText(canvas, "Arrastra sobre el video para seleccionar ROI",
                        (15, 33), FONT, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        if rect is not None:
            x0, y0, x1, y1 = rect
            cv2.rectangle(canvas, (x0, y0), (x1, y1), (0, 255, 0), 3)
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.lbl.configure(image=imgtk)
        self.lbl.image = imgtk

    def screen_to_frame_coords(self, sx, sy):
        if (sx < self.offset_x or sx >= self.offset_x + self.frame_w or
                sy < self.offset_y or sy >= self.offset_y + self.frame_h):
            fx = min(max(sx - self.offset_x, 0), self.frame_w - 1)
            fy = min(max(sy - self.offset_y, 0), self.frame_h - 1)
            return fx, fy, False
        return sx - self.offset_x, sy - self.offset_y, True

    def frame_to_screen_coords(self, fx, fy):
        return fx + self.offset_x, fy + self.offset_y

    def on_mouse_down(self, event):
        if not self.roi_selecting:
            return
        fx, fy, valid = self.screen_to_frame_coords(event.x, event.y)
        if not valid:
            return
        self.start_x = fx
        self.start_y = fy
        self.end_x = fx
        self.end_y = fy
        sx, sy = self.frame_to_screen_coords(fx, fy)
        self.show_frame_for_roi(rect=(sx, sy, sx+1, sy+1))

    def on_mouse_drag(self, event):
        if not self.roi_selecting:
            return
        fx, fy, valid = self.screen_to_frame_coords(event.x, event.y)
        if not valid:
            fx = min(max(fx, 0), self.frame_w - 1)
            fy = min(max(fy, 0), self.frame_h - 1)
        self.end_x = fx
        self.end_y = fy

        x0 = min(self.start_x, self.end_x)
        y0 = min(self.start_y, self.end_y)
        x1 = max(self.start_x, self.end_x)
        y1 = max(self.start_y, self.end_y)
        sx0, sy0 = self.frame_to_screen_coords(x0, y0)
        sx1, sy1 = self.frame_to_screen_coords(x1, y1)
        self.show_frame_for_roi(rect=(sx0, sy0, sx1, sy1))

    def on_mouse_up(self, event):
        if not self.roi_selecting:
            return
        fx, fy, valid = self.screen_to_frame_coords(event.x, event.y)
        if not valid:
            fx = min(max(fx, 0), self.frame_w - 1)
            fy = min(max(fy, 0), self.frame_h - 1)
        self.end_x = fx
        self.end_y = fy

        x0 = min(self.start_x, self.end_x)
        y0 = min(self.start_y, self.end_y)
        x1 = max(self.start_x, self.end_x)
        y1 = max(self.start_y, self.end_y)
        w = x1 - x0
        h = y1 - y0

        if w < 10 or h < 10:
            print("ROI muy pequeño, vuelve a seleccionar")
            self.show_frame_for_roi(show_hint=True)
            return

        self.roi = (x0, y0, w, h)
        self.roi_selecting = False

        self.init_trackers_with_roi()
        self.root.after(1, self.update_loop)

    def init_trackers_with_roi(self):
        self.trackers = []
        self.counters = []
        x, y, w, h = self.roi
        for name in TRACKER_NAMES:
            tr = create_tracker_by_name(name)
            ok = False
            if tr is not None:
                ok = tr.init(self.first_frame, (x, y, w, h))
            self.trackers.append(tr if ok else None)
            self.counters.append(AxisCycleCounter())

    def update_loop(self):
        if self.roi_selecting:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.lbl.config(text="Fin del video.", fg="black")
            self.root.after(1000, self.on_close)
            return

        frame = cv2.resize(frame, PROC_SIZE, interpolation=cv2.INTER_AREA)
        top_img = frame.copy()

        tiles = []
        cards = []

        for i, name in enumerate(TRACKER_NAMES):
            vis = frame.copy()
            tr = self.trackers[i]
            counter = self.counters[i]
            cycles = counter.cycles
            ok = False

            if tr is not None:
                ok, bbox = tr.update(frame)
                if ok:
                    x, y, w, h = [int(v) for v in bbox]
                    cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cx = x + w // 2
                    cy = y + h // 2
                    cycles = counter.add_point(cx, cy)
                    cv2.circle(vis, (cx, cy), 3, (0, 0, 255), -1)

            tiles.append(vis)
            cards.append(make_card(name, "OK" if ok else "LOST", ok, cycles))

        mosaic = compose_layout(top_img, tiles, cards)
        mosaic = cv2.resize(mosaic, (OUTPUT_W, OUTPUT_H), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(mosaic, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.lbl.configure(image=imgtk)
        self.lbl.image = imgtk

        self.root.after(1, self.update_loop)

    def on_close(self):
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        self.root.destroy()


# =========================================================
# APP INDIVIDUAL (1 solo tracker, sin mosaico)
# =========================================================
class SingleTrackerTk:
    def __init__(self, root, video_path, tracker_name):
        self.root = root
        self.root.title(f"Tracker individual — {tracker_name}")
        self.root.configure(bg="white")
        self.root.geometry(f"{OUTPUT_W}x{OUTPUT_H}")

        self.lbl = Label(self.root, bg="white", width=OUTPUT_W, height=OUTPUT_H)
        self.lbl.pack(fill="both", expand=True)

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.lbl.config(text=f"No se pudo abrir: {video_path}", fg="red")
            return

        ret, frame = self.cap.read()
        if not ret:
            self.lbl.config(text="Video vacío", fg="red")
            return

        frame = cv2.resize(frame, PROC_SIZE, interpolation=cv2.INTER_AREA)
        self.first_frame = frame.copy()
        self.frame_w = frame.shape[1]
        self.frame_h = frame.shape[0]

        self.offset_x = (OUTPUT_W - self.frame_w) // 2
        self.offset_y = (OUTPUT_H - self.frame_h) // 2

        self.tracker_name = tracker_name
        self.tracker = None
        self.counter = AxisCycleCounter()

        self.roi_selecting = True
        self.roi = None
        self.start_x = self.start_y = None
        self.end_x = self.end_y = None

        self.show_frame_for_roi(show_hint=True)

        self.lbl.bind("<Button-1>", self.on_mouse_down)
        self.lbl.bind("<B1-Motion>", self.on_mouse_drag)
        self.lbl.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.root.bind("<KeyPress-q>", lambda e: self.on_close())
        self.root.bind("<KeyPress-Q>", lambda e: self.on_close())

    def show_frame_for_roi(self, rect=None, show_hint=False):
        canvas = np.full((OUTPUT_H, OUTPUT_W, 3), WHITE, dtype=np.uint8)
        canvas[self.offset_y:self.offset_y + self.frame_h,
               self.offset_x:self.offset_x + self.frame_w] = self.first_frame
        if show_hint:
            cv2.rectangle(canvas, (10, 10), (380, 40), (255, 255, 255), -1)
            cv2.putText(canvas, "Arrastra sobre el video para seleccionar ROI",
                        (15, 33), FONT, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        if rect is not None:
            x0, y0, x1, y1 = rect
            cv2.rectangle(canvas, (x0, y0), (x1, y1), (0, 255, 0), 3)
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.lbl.configure(image=imgtk)
        self.lbl.image = imgtk

    def screen_to_frame_coords(self, sx, sy):
        if (sx < self.offset_x or sx >= self.offset_x + self.frame_w or
                sy < self.offset_y or sy >= self.offset_y + self.frame_h):
            fx = min(max(sx - self.offset_x, 0), self.frame_w - 1)
            fy = min(max(sy - self.offset_y, 0), self.frame_h - 1)
            return fx, fy, False
        return sx - self.offset_x, sy - self.offset_y, True

    def frame_to_screen_coords(self, fx, fy):
        return fx + self.offset_x, fy + self.offset_y

    def on_mouse_down(self, event):
        if not self.roi_selecting:
            return
        fx, fy, valid = self.screen_to_frame_coords(event.x, event.y)
        if not valid:
            return
        self.start_x = fx
        self.start_y = fy
        self.end_x = fx
        self.end_y = fy
        sx, sy = self.frame_to_screen_coords(fx, fy)
        self.show_frame_for_roi(rect=(sx, sy, sx+1, sy+1))

    def on_mouse_drag(self, event):
        if not self.roi_selecting:
            return
        fx, fy, valid = self.screen_to_frame_coords(event.x, event.y)
        if not valid:
            fx = min(max(fx, 0), self.frame_w - 1)
            fy = min(max(fy, 0), self.frame_h - 1)
        self.end_x = fx
        self.end_y = fy
        x0 = min(self.start_x, self.end_x)
        y0 = min(self.start_y, self.end_y)
        x1 = max(self.start_x, self.end_x)
        y1 = max(self.start_y, self.end_y)
        sx0, sy0 = self.frame_to_screen_coords(x0, y0)
        sx1, sy1 = self.frame_to_screen_coords(x1, y1)
        self.show_frame_for_roi(rect=(sx0, sy0, sx1, sy1))

    def on_mouse_up(self, event):
        if not self.roi_selecting:
            return
        fx, fy, valid = self.screen_to_frame_coords(event.x, event.y)
        if not valid:
            fx = min(max(fx, 0), self.frame_w - 1)
            fy = min(max(fy, 0), self.frame_h - 1)
        self.end_x = fx
        self.end_y = fy
        x0 = min(self.start_x, self.end_x)
        y0 = min(self.start_y, self.end_y)
        x1 = max(self.start_x, self.end_x)
        y1 = max(self.start_y, self.end_y)
        w = x1 - x0
        h = y1 - y0
        if w < 10 or h < 10:
            print("ROI muy pequeño, vuelve a seleccionar")
            self.show_frame_for_roi(show_hint=True)
            return
        self.roi = (x0, y0, w, h)
        self.roi_selecting = False

        # inicializar tracker elegido
        tr = create_tracker_by_name(self.tracker_name)
        if tr is None:
            self.lbl.config(text=f"Tracker {self.tracker_name} no disponible en este OpenCV", fg="red")
            return
        ok = tr.init(self.first_frame, self.roi)
        if not ok:
            self.lbl.config(text=f"No se pudo inicializar tracker {self.tracker_name}", fg="red")
            return
        self.tracker = tr

        # arrancar loop individual
        self.root.after(1, self.update_loop)

    def update_loop(self):
        if self.roi_selecting:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.lbl.config(text="Fin del video.", fg="black")
            self.root.after(1000, self.on_close)
            return

        frame = cv2.resize(frame, PROC_SIZE, interpolation=cv2.INTER_AREA)

        canvas = np.full((OUTPUT_H, OUTPUT_W, 3), WHITE, dtype=np.uint8)
        canvas[self.offset_y:self.offset_y + self.frame_h,
               self.offset_x:self.offset_x + self.frame_w] = frame

        ok = False
        cycles = self.counter.cycles
        if self.tracker is not None:
            ok, bbox = self.tracker.update(frame)
            if ok:
                x, y, w, h = [int(v) for v in bbox]
                # dibujar sobre frame (pero en canvas necesitamos offset)
                cv2.rectangle(canvas,
                              (self.offset_x + x, self.offset_y + y),
                              (self.offset_x + x + w, self.offset_y + y + h),
                              (0, 255, 0), 2)
                cx = x + w // 2
                cy = y + h // 2
                cycles = self.counter.add_point(cx, cy)
                cv2.circle(canvas,
                           (self.offset_x + cx, self.offset_y + cy),
                           3, (0, 0, 255), -1)

        # dibujar card arriba a la derecha
        info_x = OUTPUT_W - 240
        info_y = 20
        cv2.rectangle(canvas, (info_x, info_y), (info_x + 220, info_y + 120), (230, 230, 230), -1)
        cv2.putText(canvas, f"Tracker: {self.tracker_name}", (info_x + 10, info_y + 25),
                    FONT, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        cv2.putText(canvas, f"Estado: {'OK' if ok else 'LOST'}", (info_x + 10, info_y + 50),
                    FONT, 0.55, (0, 170, 0) if ok else (0, 0, 220), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Ciclos: {cycles}", (info_x + 10, info_y + 80),
                    FONT, 0.7, (0, 0, 0), 2, cv2.LINE_AA)

        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        self.lbl.configure(image=imgtk)
        self.lbl.image = imgtk

        self.root.after(1, self.update_loop)

    def on_close(self):
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        self.root.destroy()


# =========================================================
# MAIN
# =========================================================
def main():
    video_path = seleccionar_video()
    if not video_path:
        print("No seleccionaste video.")
        return

    print("Selecciona modo:")
    print("1) Multimotor (6 trackers, layout 1600x900)")
    print("2) Individual (un solo tracker)")
    modo = input("Ingresa 1 o 2: ").strip()

    root = Tk()

    if modo == "2":
        print("Trackers disponibles:", ", ".join(TRACKER_NAMES))
        tracker_name = input("Escribe el nombre EXACTO del tracker (ej. CSRT): ").strip()
        if tracker_name not in TRACKER_NAMES:
            print("Nombre no válido, uso CSRT por defecto")
            tracker_name = "CSRT"
        app = SingleTrackerTk(root, video_path, tracker_name)
    else:
        app = MultiTrackerBenchTk(root, video_path)

    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

