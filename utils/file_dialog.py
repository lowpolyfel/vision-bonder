from tkinter import filedialog
import os

def seleccionar_video_por_dialogo(root, initialdir=None):
    """
    Diálogo para seleccionar archivo de video.
    Compatible con Linux (case-sensitive) y Tkinter en Raspberry Pi.
    
    Características:
    - Acepta extensiones en mayúsculas y minúsculas (ej: .mov, .MOV, .MoV, etc.).
    - Usa tuplas de patrones en lugar de strings (mayor compatibilidad en Linux).
    - Si el filtro de video no muestra nada, reintenta con 'Todos los archivos'.
    - Puede recordar un directorio inicial.
    """
    if initialdir is None:
        initialdir = os.getcwd()  # carpeta actual por defecto

    # Filtros de archivo: el primero se selecciona por defecto
    tipos = [
        # Se muestra primero para evitar que el diálogo quede vacío
        ("Todos los archivos", "*.*"),

        # Filtro de videos con patrones case-insensitive
        ("Archivos de video", (
            "*.[Mm][Pp]4",        # .mp4 / .MP4
            "*.[Mm][Oo][Vv]",     # .mov / .MOV / .MoV
            "*.[Aa][Vv][Ii]",     # .avi / .AVI
            "*.[Mm][Kk][Vv]",     # .mkv / .MKV
            "*.[Mm]4[Vv]",        # .m4v / .M4V
            "*.[Ww][Mm][Vv]",     # .wmv / .WMV
            "*.[Mm][Pp][Ee][Gg]", # .mpeg / .MPEG
            "*.[Mm][Pp][Gg]",     # .mpg / .MPG
            "*.[Mm][Tt][Ss]",     # .mts / .MTS
            "*.[Tt][Ss]",         # .ts / .TS
            "*.[Hh]264",          # .h264
            "*.[Hh]265",          # .h265
            "*.[Hh][Ee][Vv][Cc]", # .hevc
            "*.[3][Gg][Pp]",      # .3gp / .3GP
        )),
    ]

    # Primer intento con filtro de videos
    path = filedialog.askopenfilename(
        title="Selecciona un archivo de video",
        initialdir=initialdir,
        filetypes=tipos
    )

    # Fallback: si el filtro no muestra nada o se cancela, reintenta mostrando todos los archivos
    if not path:
        path = filedialog.askopenfilename(
            title="Selecciona un archivo de video (mostrar todo)",
            initialdir=initialdir,
            filetypes=[("Todos los archivos", "*.*")]
        )

    return path

