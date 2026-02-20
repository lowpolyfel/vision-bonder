using System.ComponentModel.DataAnnotations;

namespace RpeEppWeb.Models;

public class Worker
{
    public int Id { get; set; }

    [Required]
    [StringLength(120)]
    public string Nombre { get; set; } = string.Empty;

    [Required]
    [RegularExpression("^[A-Za-z]{1,5}$", ErrorMessage = "RPE debe tener solo letras (máximo 5).")]
    [StringLength(5)]
    public string Rpe { get; set; } = string.Empty;

    public string? FotoPath { get; set; }

    public ICollection<WorkerDocument> Documents { get; set; } = new List<WorkerDocument>();
}
