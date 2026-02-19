using Microsoft.AspNetCore.Mvc;
using VisionBonder.Web.DocumentosModule.Services;

namespace VisionBonder.Web.DocumentosModule.Controllers;

[ApiController]
[Route("api/documentos")]
public sealed class DocumentosController(IDocumentoStorageService storageService) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> Listar(CancellationToken cancellationToken)
    {
        var documentos = await storageService.ListarAsync(cancellationToken);
        return Ok(documentos);
    }

    [HttpPost("subir")]
    [RequestSizeLimit(20 * 1024 * 1024)]
    public async Task<IActionResult> Subir([FromForm] IFormFile archivo, CancellationToken cancellationToken)
    {
        if (archivo.Length == 0)
        {
            return BadRequest("El archivo está vacío.");
        }

        var documento = await storageService.GuardarAsync(archivo, cancellationToken);
        return CreatedAtAction(nameof(Listar), new { id = documento.Id }, documento);
    }

    [HttpPut("{id:guid}/asignar-numero")]
    public async Task<IActionResult> AsignarNumero(Guid id, [FromBody] AsignarNumeroRequest request, CancellationToken cancellationToken)
    {
        if (request.Numero <= 0)
        {
            return BadRequest("El número asignado debe ser mayor a cero.");
        }

        var actualizado = await storageService.AsignarNumeroAsync(id, request.Numero, cancellationToken);
        return actualizado ? NoContent() : NotFound();
    }

    public sealed class AsignarNumeroRequest
    {
        public int Numero { get; init; }
    }
}
