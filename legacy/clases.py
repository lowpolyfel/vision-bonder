# ver_clases_yolo.py
from ultralytics import YOLO

# Ruta a tu modelo entrenado
MODEL_PATH = "modelos/monitoreo.pt"

def main():
    print(f"Cargando modelo: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)

    print("\n📦 Clases encontradas en el modelo:\n")
    for class_id, class_name in model.names.items():
        print(f"  ID {class_id:<3} → {class_name}")

    print("\n✅ Listo. Usa el ID correspondiente en tu configuración (yolo_class_id).")

if __name__ == "__main__":
    main()

