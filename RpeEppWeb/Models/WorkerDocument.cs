using System.ComponentModel.DataAnnotations;

namespace RpeEppWeb.Models;

public class WorkerDocument
{
    public int Id { get; set; }

    [Required]
    public DocumentType Tipo { get; set; }

    [Required]
    public string FileName { get; set; } = string.Empty;

    [Required]
    public string FilePath { get; set; } = string.Empty;

    public DateTime UploadedAt { get; set; } = DateTime.UtcNow;

    public int WorkerId { get; set; }
    public Worker Worker { get; set; } = default!;
}
