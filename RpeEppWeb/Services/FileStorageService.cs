namespace RpeEppWeb.Services;

public class FileStorageService(IWebHostEnvironment env)
{
    private readonly string _uploadsRoot = Path.Combine(env.ContentRootPath, "uploads");

    public async Task<string> SavePdfAsync(IFormFile file, string subfolder)
    {
        ValidatePdf(file);
        var folder = Path.Combine(_uploadsRoot, subfolder);
        Directory.CreateDirectory(folder);

        var extension = Path.GetExtension(file.FileName);
        var uniqueName = $"{Guid.NewGuid():N}{extension}";
        var physicalPath = Path.Combine(folder, uniqueName);

        await using var stream = File.Create(physicalPath);
        await file.CopyToAsync(stream);

        return $"/uploads/{subfolder}/{uniqueName}";
    }

    public async Task<string> SaveImageAsync(IFormFile file, string subfolder)
    {
        var allowed = new[] { ".jpg", ".jpeg", ".png", ".webp" };
        var extension = Path.GetExtension(file.FileName).ToLowerInvariant();

        if (!allowed.Contains(extension))
        {
            throw new InvalidOperationException("La foto debe ser JPG, PNG o WEBP.");
        }

        var folder = Path.Combine(_uploadsRoot, subfolder);
        Directory.CreateDirectory(folder);

        var uniqueName = $"{Guid.NewGuid():N}{extension}";
        var physicalPath = Path.Combine(folder, uniqueName);

        await using var stream = File.Create(physicalPath);
        await file.CopyToAsync(stream);

        return $"/uploads/{subfolder}/{uniqueName}";
    }

    public void DeleteByRelativePath(string? relativePath)
    {
        if (string.IsNullOrWhiteSpace(relativePath)) return;

        var cleaned = relativePath.TrimStart('/').Replace('/', Path.DirectorySeparatorChar);
        var physicalPath = Path.Combine(env.ContentRootPath, cleaned);

        if (File.Exists(physicalPath))
        {
            File.Delete(physicalPath);
        }
    }

    private static void ValidatePdf(IFormFile file)
    {
        if (Path.GetExtension(file.FileName).ToLowerInvariant() != ".pdf")
        {
            throw new InvalidOperationException("Solo se aceptan archivos PDF.");
        }
    }
}
