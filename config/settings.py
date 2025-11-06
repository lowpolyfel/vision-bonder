# ===================== Configuración =====================
import os

TOLERANCIA_IDLE_SEGUNDOS = 30
AREA_MINIMA_CONTORNO = 500
VIDEO_ANCHO_DISPLAY = 640


def _env_int(nombre, predeterminado):
    valor = os.getenv(nombre)
    if valor is None:
        return predeterminado
    try:
        return int(valor)
    except ValueError:
        return predeterminado


# --- Base de datos ---
DB_CONFIG = {
    "host": os.getenv("VISION_BONDER_DB_HOST", "127.0.0.1"),
    "user": os.getenv("VISION_BONDER_DB_USER", ""),
    "password": os.getenv("VISION_BONDER_DB_PASSWORD", ""),
    "database": os.getenv("VISION_BONDER_DB_NAME", "vision_bonder"),
}

_db_port = os.getenv("VISION_BONDER_DB_PORT")
if _db_port:
    try:
        DB_CONFIG["port"] = int(_db_port)
    except ValueError:
        pass

ID_MAQUINA_MONITOREADA = _env_int("VISION_BONDER_MACHINE_ID", 1)

