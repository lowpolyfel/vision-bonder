#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --- Asegura que las importaciones locales funcionen al ejecutar "python3 main.py"
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tkinter import Tk, messagebox
from utils.file_dialog import seleccionar_video_por_dialogo
from ui.main_window import DetectorApp


def main():
    root = Tk()
    root.withdraw()
    video_path = seleccionar_video_por_dialogo(root)
    if not video_path:
        messagebox.showinfo("Sin archivo", "No seleccionaste un video. Saliendo.")
        root.destroy()
        return

    root.deiconify()
    app = DetectorApp(root, video_path)
    root.mainloop()


if __name__ == "__main__":
    main()

