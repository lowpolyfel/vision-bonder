using VisionBonder.Web.DocumentosModule.Models;

namespace VisionBonder.Web.DocumentosModule.Services;

public interface IDocumentoStorageService
{
    Task<DocumentoAsignado> GuardarAsync(IFormFile archivo, CancellationToken cancellationToken = default);
    Task<IReadOnlyCollection<DocumentoAsignado>> ListarAsync(CancellationToken cancellationToken = default);
    Task<bool> AsignarNumeroAsync(Guid documentoId, int numero, CancellationToken cancellationToken = default);
}
