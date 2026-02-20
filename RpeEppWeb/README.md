# Módulo Razor Pages - Control de Documentos EPP por RPE

Este módulo en **.NET 8 / Razor Pages** permite:

- Registrar trabajador con **Nombre, RPE (solo letras, máx. 5)** y foto.
- Subir PDFs obligatorios por trabajador:
  - Arnés
  - Bandolas
  - Casco
  - Líneas de vida
  - Certificado de aptitud
- Visualizar y eliminar documentos.
- Consultar por RPE y ver checklist de qué documentos están cargados.

## 1) Crear y abrir en Visual Studio Code

1. Instala SDK de .NET 8.
2. En terminal:
   ```bash
   cd RpeEppWeb
   dotnet restore
   dotnet run
   ```
3. Abre `http://localhost:5000` o la URL que muestre la consola.

## 2) Flujo recomendado de uso

1. Ir a **Registrar trabajador**.
2. Capturar nombre, RPE y foto.
3. Guardar.
4. En la vista del trabajador, subir cada PDF por tipo.
5. En **Buscar trabajador**, escribir RPE para ver checklist de documentos.

## 3) Estructura para mantener orden en VS Code

- `Models/`: entidades (`Worker`, `WorkerDocument`, `DocumentType`).
- `Data/`: `AppDbContext` (SQLite).
- `Services/`: almacenamiento de archivos.
- `Pages/`: UI Razor + lógica de página.
- `uploads/`: archivos físicos subidos.

## 4) Base de datos

- Motor: **SQLite** (`rpe-epp.db`).
- La base se crea automáticamente con `EnsureCreated()` al arrancar.

## 5) Cómo unir esta página con otra web

Tienes varias opciones:

### Opción A: Enlace directo (rápida)
- Desde tu otra web agrega botón o menú a `https://tudominio-epp/`.

### Opción B: Embebida en iframe
- Publica este módulo como subdominio y embébelo en tu portal principal.

### Opción C: Integración por API (recomendada a futuro)
- Crear endpoints (`Minimal API` o `Controller`) para consultar trabajador/documentos por RPE.
- Consumir desde tu otro sistema para mostrar estado de EPP dentro de un dashboard central.

## 6) Publicar (ejemplo)

```bash
dotnet publish -c Release -o ./publish
```

Luego despliegas la carpeta `publish/` en IIS, Linux + systemd, Docker, etc.

## 7) Notas importantes

- `uploads/.gitkeep` está vacío **a propósito**. Git no guarda carpetas vacías; este archivo permite que la carpeta `uploads/` exista en el repo desde el inicio.
- Para cambiar colores de la página, modifica `wwwroot/css/site.css` (variables en `:root`, por ejemplo `--brand-bg`).
