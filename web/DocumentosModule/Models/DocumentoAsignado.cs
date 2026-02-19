namespace VisionBonder.Web.DocumentosModule.Models;

public sealed class DocumentoAsignado
{
    public Guid Id { get; init; } = Guid.NewGuid();
    public required string NombreOriginal { get; init; }
    public required string NombreAlmacenado { get; init; }
    public required string TipoContenido { get; init; }
    public string RutaRelativa => $"/uploads/documentos/{NombreAlmacenado}";
    public DateTime FechaCargaUtc { get; init; } = DateTime.UtcNow;
    public int? NumeroAsignado { get; set; }
}
