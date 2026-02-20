using Microsoft.EntityFrameworkCore;
using RpeEppWeb.Models;

namespace RpeEppWeb.Data;

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Worker> Workers => Set<Worker>();
    public DbSet<WorkerDocument> WorkerDocuments => Set<WorkerDocument>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Worker>()
            .HasIndex(w => w.Rpe)
            .IsUnique();

        modelBuilder.Entity<WorkerDocument>()
            .HasIndex(d => new { d.WorkerId, d.Tipo })
            .IsUnique();
    }
}
