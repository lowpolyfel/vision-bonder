using System.Collections.Concurrent;
using VisionBonder.Web.DocumentosModule.Models;

namespace VisionBonder.Web.DocumentosModule.Services;

public sealed class DocumentoStorageService(IWebHostEnvironment env) : IDocumentoStorageService
{
    private readonly string _carpeta = Path.Combine(env.WebRootPath, "uploads", "documentos");
    private readonly ConcurrentDictionary<Guid, DocumentoAsignado> _documentos = new();

    public async Task<DocumentoAsignado> GuardarAsync(IFormFile archivo, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(_carpeta);

        var extension = Path.GetExtension(archivo.FileName);
        var nombreAlmacenado = $"{Guid.NewGuid():N}{extension}";
        var rutaCompleta = Path.Combine(_carpeta, nombreAlmacenado);

        await using var stream = File.Create(rutaCompleta);
        await archivo.CopyToAsync(stream, cancellationToken);

        var documento = new DocumentoAsignado
        {
            NombreOriginal = archivo.FileName,
            NombreAlmacenado = nombreAlmacenado,
            TipoContenido = string.IsNullOrWhiteSpace(archivo.ContentType)
                ? "application/octet-stream"
                : archivo.ContentType
        };

        _documentos[documento.Id] = documento;
        return documento;
    }

    public Task<IReadOnlyCollection<DocumentoAsignado>> ListarAsync(CancellationToken cancellationToken = default)
    {
        IReadOnlyCollection<DocumentoAsignado> resultado = _documentos.Values
            .OrderByDescending(d => d.FechaCargaUtc)
            .ToArray();

        return Task.FromResult(resultado);
    }

    public Task<bool> AsignarNumeroAsync(Guid documentoId, int numero, CancellationToken cancellationToken = default)
    {
        if (!_documentos.TryGetValue(documentoId, out var documento))
        {
            return Task.FromResult(false);
        }

        documento.NumeroAsignado = numero;
        return Task.FromResult(true);
    }
}
