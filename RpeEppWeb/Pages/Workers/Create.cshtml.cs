using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using Microsoft.EntityFrameworkCore;
using RpeEppWeb.Data;
using RpeEppWeb.Models;
using RpeEppWeb.Services;

namespace RpeEppWeb.Pages.Workers;

public class CreateModel(AppDbContext db, FileStorageService storage) : PageModel
{
    [BindProperty]
    public InputModel Input { get; set; } = new();

    public class InputModel
    {
        [Required, StringLength(120)]
        public string Nombre { get; set; } = string.Empty;

        [Required]
        [Display(Name = "RPE")]
        [RegularExpression("^[A-Za-z]{1,5}$", ErrorMessage = "RPE debe tener solo letras (máximo 5).")]
        public string Rpe { get; set; } = string.Empty;

        [Display(Name = "Foto del trabajador")]
        public IFormFile? Foto { get; set; }
    }

    public async Task<IActionResult> OnPostAsync()
    {
        if (!ModelState.IsValid) return Page();

        var normalizedRpe = Input.Rpe.ToUpperInvariant();

        var exists = await db.Workers.AnyAsync(w => w.Rpe == normalizedRpe);
        if (exists)
        {
            ModelState.AddModelError(string.Empty, "Ya existe un trabajador con ese RPE.");
            return Page();
        }

        string? fotoPath = null;
        if (Input.Foto is not null)
        {
            try
            {
                fotoPath = await storage.SaveImageAsync(Input.Foto, "photos");
            }
            catch (InvalidOperationException ex)
            {
                ModelState.AddModelError(nameof(Input.Foto), ex.Message);
                return Page();
            }
        }

        var worker = new Worker
        {
            Nombre = Input.Nombre,
            Rpe = normalizedRpe,
            FotoPath = fotoPath
        };

        db.Workers.Add(worker);
        await db.SaveChangesAsync();

        return RedirectToPage("/Workers/Details", new { id = worker.Id });
    }
}
