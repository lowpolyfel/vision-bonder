using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using RpeEppWeb.Data;
using RpeEppWeb.Models;

namespace RpeEppWeb.Pages;

public class IndexModel(AppDbContext db) : PageModel
{
    [BindProperty(SupportsGet = true)]
    public string? Rpe { get; set; }

    public Worker? Worker { get; set; }

    public IReadOnlyList<DocumentType> RequiredTypes { get; } = Enum.GetValues<DocumentType>();
    public HashSet<DocumentType> UploadedTypes { get; set; } = [];

    public async Task OnGetAsync()
    {
        if (string.IsNullOrWhiteSpace(Rpe)) return;

        Worker = await db.Workers
            .Include(w => w.Documents)
            .FirstOrDefaultAsync(w => w.Rpe == Rpe.ToUpper());

        if (Worker is not null)
        {
            UploadedTypes = Worker.Documents.Select(d => d.Tipo).ToHashSet();
        }
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
