using VisionBonder.Web.DocumentosModule.Services;

namespace VisionBonder.Web.DocumentosModule;

public static class DocumentosModuleExtensions
{
    public static IServiceCollection AddDocumentosModule(this IServiceCollection services)
    {
        services.AddScoped<IDocumentoStorageService, DocumentoStorageService>();
        return services;
    }
}
