# Monitoreo Industrial – Detector de Movimiento

> Aplicación de escritorio en Tkinter para auditar actividad en video y registrar estados en una base de datos MySQL.

Monitoreo Industrial automatiza la revisión de grabaciones industriales, detectando actividad o inactividad en líneas de producción y registrando cada tramo en una base de datos relacional para su trazabilidad. Está pensada para desplegarse en estaciones de control (por ejemplo, Raspberry Pi u operarios de planta) que necesitan una interfaz gráfica sencilla y una integración directa con el backend corporativo.

## 📦 Características principales

- **Interfaz gráfica en Tkinter** con previsualización de video y estado actual de la máquina.
- **Detección de movimiento por visión por computador** usando OpenCV y un fondo adaptativo sencillo.
- **Máquina de estados con tolerancia configurable** para evitar falsos positivos cuando se entra o sale de estado IDLE.
- **Registro automático en MySQL** de los periodos ACTIVO/IDLE mediante un `DBManager` transaccional.
- **Herramientas y scripts auxiliares** para pruebas con distintos trackers y prototipos almacenados en `legacy/` y `tools/`.

## 🧱 Arquitectura

La aplicación principal se inicia desde [`main.py`](main.py) y crea una instancia de `DetectorApp`, definida en [`ui/main_window.py`](ui/main_window.py). Esta clase orquesta los siguientes componentes:

- [`video/capture.py`](video/capture.py): abstrae `cv2.VideoCapture` y sincroniza cada frame con una línea de tiempo auditada.
- [`video/motion.py`](video/motion.py): inicializa y actualiza el fondo adaptativo y devuelve contornos relevantes.
- [`services/state_machine.py`](services/state_machine.py): máquina de estados que aplica la tolerancia a IDLE y dispara callbacks al cerrar un tramo.
- [`services/event_recorder.py`](services/event_recorder.py): traduce los segmentos a estatus binarios y llama a [`db/manager.py`](db/manager.py) para persistirlos en MySQL.
- [`config/settings.py`](config/settings.py): parámetros globales (por ejemplo, tolerancia, dimensiones y variables de entorno de la base de datos).

Además, `utils/file_dialog.py` gestiona la selección de archivos de video con soporte para mayúsculas/minúsculas en sistemas Linux.

```
main.py → DetectorApp
           ├─ VideoSource (video/capture.py)
           ├─ Motion detection utils (video/motion.py)
           ├─ StateMachine (services/state_machine.py)
           ├─ EventRecorder (services/event_recorder.py)
           └─ DBManager (db/manager.py)
```

## 🛠 Requisitos

- Python 3.10 o superior
- Dependencias de sistema:
  - Bibliotecas nativas necesarias para compilar/ejecutar OpenCV (`libgl1`, `ffmpeg`, etc.).
  - Cliente de MySQL accesible desde la máquina donde corre la aplicación.
  - Servidor MySQL con las tablas `operacion_maquina` y `estado_maquina` (ver sección de base de datos).

Las dependencias de Python están listadas en [`requirements.txt`](requirements.txt). Para funcionalidades experimentales ubicadas en `legacy/` o scripts bajo `tests/` que dependen de YOLOv8, instale también `ultralytics` usando [`requirements-dev.txt`](requirements-dev.txt).

## 🚀 Puesta en marcha rápida

```bash
# 1) Crear y activar un entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# 2) Instalar dependencias
pip install -r requirements.txt  # Añada -r requirements-dev.txt para scripts experimentales

# 3) Configurar credenciales de base de datos
cp .venv.example .env  # archivo ignorado por git con las variables necesarias
# edite .env y expórtelo en su shell (ejemplo para Bash)
set -a; source .env; set +a

# 4) Ejecutar la aplicación
python main.py
```

> 💡 Si ejecuta la aplicación en un dispositivo sin pantalla (por ejemplo, un servidor), recuerde que Tkinter requiere un entorno gráfico.

## 🗃 Configuración de base de datos

Las credenciales y parámetros sensibles se obtienen desde variables de entorno. Consulte `.venv.example` para ver todos los nombres esperados:

| Variable | Descripción |
| --- | --- |
| `VISION_BONDER_DB_HOST` | Host o IP del servidor MySQL. |
| `VISION_BONDER_DB_PORT` | Puerto TCP (opcional, por defecto 3306). |
| `VISION_BONDER_DB_USER` | Usuario con permisos de inserción en las tablas objetivo. |
| `VISION_BONDER_DB_PASSWORD` | Contraseña del usuario anterior. |
| `VISION_BONDER_DB_NAME` | Base de datos donde residen `operacion_maquina` y `estado_maquina`. |
| `VISION_BONDER_MACHINE_ID` | Identificador numérico de la máquina monitoreada. |

> ℹ️ El repositorio no incluye contraseñas ni datos reales; cada despliegue debe definir sus propios valores antes de ejecutar la aplicación.

El proyecto asume la existencia de las siguientes tablas en el esquema definido por `DB_CONFIG`:

- `operacion_maquina`: guarda una fila por operación detectada. Se inserta con datos mínimos (`id_maquina`, `id_operador`, etc.) y se usa su `lastrowid` para relacionar estados.
- `estado_maquina`: almacena cada tramo con campos `id_operacion`, `id_maquina`, `estatus` (1=ACTIVO, 0=IDLE), `fecha_inicio`, `fecha_fin` y `duracion_seg`.

Si la tabla `estado_maquina` no utiliza `AUTO_INCREMENT`, el `DBManager` calculará el siguiente identificador disponible (`_siguiente_id`). Ajuste los nombres de columnas o la lógica según su esquema real.

Configure `ID_MAQUINA_MONITOREADA` para asociar los registros a la máquina correcta. En entornos multi-planta, considere parametrizarlo mediante variables de entorno.

## 🧪 Pruebas y scripts auxiliares

El directorio `tests/` contiene notebooks y scripts interactivos utilizados durante el desarrollo (por ejemplo, comparativas de trackers). Muchos requieren interfaz gráfica, OpenCV y –en algunos casos– YOLOv8 (`ultralytics`). Ejecútelos manualmente según sus necesidades.

Para validar la lógica de máquina de estados sin UI, puede escribir pruebas unitarias adicionales que instancien `StateMachine` y simulen transiciones. Se recomiendan frameworks como `pytest` para automatizar esta cobertura.

## 🗂 Estructura del repositorio

```
monitoreo/
├── config/            # Parámetros globales de la aplicación
├── db/                # Conectores y utilidades de base de datos
├── services/          # Lógica de dominio (máquina de estados, grabador de eventos)
├── ui/                # Componentes de interfaz de usuario en Tkinter
├── utils/             # Utilidades compartidas (selección de archivos, etc.)
├── video/             # Captura y procesamiento de video con OpenCV
├── tools/             # Scripts de laboratorio y benchmarks
├── legacy/            # Prototipos heredados (no soportados)
├── tests/             # Scripts de experimentación manual
└── main.py            # Punto de entrada principal
```

## 🤝 Contribuir

Revise las pautas en [`CONTRIBUTING.md`](CONTRIBUTING.md) antes de proponer cambios. Se fomenta el uso de _pull requests_ bien documentados, pruebas reproducibles y linters como `flake8` o `black` para mantener la calidad del código.

## 📄 Licencia

Este proyecto se distribuye bajo los términos de la [licencia MIT](LICENSE).

## 📬 Soporte

Abra un _issue_ en GitHub con información detallada sobre su entorno (SO, versión de Python, versión de MySQL, etc.) y pasos para reproducir el problema. Para consultas privadas, contacte al responsable del proyecto en su organización.

