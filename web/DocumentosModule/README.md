# Módulo de documentos para ASP.NET Core / Blazor

Este apartado agrega una sección reutilizable para una web existente donde se puede:

1. Subir documentos (PDF, imágenes o archivos Office).
2. Visualizar el archivo subido mediante URL pública.
3. Asignar un número de referencia a cada documento.

## Integración rápida en una web existente

1. Copia la carpeta `DocumentosModule` dentro de tu solución .NET.
2. En `Program.cs`, registra controladores y el servicio:

```csharp
builder.Services.AddControllers();
builder.Services.AddRazorPages();
builder.Services.AddServerSideBlazor();
builder.Services.AddDocumentosModule();

var app = builder.Build();

app.UseStaticFiles();
app.MapControllers();
app.MapBlazorHub();
app.MapFallbackToPage("/_Host");
```

3. Agrega navegación al componente de Blazor (`/documentos`) en tu layout.

## Endpoints disponibles

- `GET /api/documentos`: lista documentos.
- `POST /api/documentos/subir`: recibe `IFormFile archivo`.
- `PUT /api/documentos/{id}/asignar-numero`: body JSON `{ "numero": 123 }`.

## Notas

- El almacenamiento actual es local en `wwwroot/uploads/documentos` y metadatos en memoria.
- Para producción, sustituye `DocumentoStorageService` por implementación con SQL Server/PostgreSQL y blob storage (Azure, S3 o MinIO).
