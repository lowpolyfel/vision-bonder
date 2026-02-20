using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using RpeEppWeb.Data;
using RpeEppWeb.Models;
using RpeEppWeb.Services;

namespace RpeEppWeb.Pages.Workers;

public class DetailsModel(AppDbContext db, FileStorageService storage) : PageModel
{
    public Worker? Worker { get; set; }
    public IReadOnlyList<DocumentType> RequiredTypes { get; } = Enum.GetValues<DocumentType>();

    [TempData]
    public string? StatusMessage { get; set; }

    public async Task<IActionResult> OnGetAsync(int id)
    {
        Worker = await db.Workers
            .Include(w => w.Documents)
            .FirstOrDefaultAsync(w => w.Id == id);

        if (Worker is null)
        {
            return NotFound();
        }

        return Page();
    }

    public async Task<IActionResult> OnPostUploadDocumentAsync(int workerId, DocumentType tipo, IFormFile pdfFile)
    {
        var worker = await db.Workers
            .Include(w => w.Documents)
            .FirstOrDefaultAsync(w => w.Id == workerId);

        if (worker is null)
        {
            return NotFound();
        }

        if (pdfFile is null)
        {
            StatusMessage = "Debes seleccionar un archivo PDF.";
            return RedirectToPage(new { id = workerId });
        }

        try
        {
            var path = await storage.SavePdfAsync(pdfFile, $"worker-{workerId}");
            var existing = worker.Documents.FirstOrDefault(d => d.Tipo == tipo);

            if (existing is not null)
            {
                storage.DeleteByRelativePath(existing.FilePath);
                existing.FilePath = path;
                existing.FileName = pdfFile.FileName;
                existing.UploadedAt = DateTime.UtcNow;
            }
            else
            {
                worker.Documents.Add(new WorkerDocument
                {
                    Tipo = tipo,
                    FilePath = path,
                    FileName = pdfFile.FileName
                });
            }

            await db.SaveChangesAsync();
            StatusMessage = "Documento cargado correctamente.";
        }
        catch (Exception ex)
        {
            StatusMessage = ex.Message;
        }

        return RedirectToPage(new { id = workerId });
    }

    public async Task<IActionResult> OnPostDeleteDocumentAsync(int workerId, DocumentType tipo)
    {
        var document = await db.WorkerDocuments
            .FirstOrDefaultAsync(d => d.WorkerId == workerId && d.Tipo == tipo);

        if (document is not null)
        {
            storage.DeleteByRelativePath(document.FilePath);
            db.WorkerDocuments.Remove(document);
            await db.SaveChangesAsync();
            StatusMessage = "Documento eliminado.";
        }

        return RedirectToPage(new { id = workerId });
    }

    public string GetLabel(DocumentType tipo) => tipo switch
    {
        DocumentType.Arnes => "Arnés",
        DocumentType.Bandolas => "Bandolas",
        DocumentType.Casco => "Casco",
        DocumentType.LineasDeVida => "Líneas de vida",
        DocumentType.CertificadoDeAptitud => "Certificado de aptitud",
        _ => tipo.ToString()
    };
}
