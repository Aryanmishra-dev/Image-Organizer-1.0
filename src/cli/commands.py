"""Click CLI with rich progress output and full duplicate finding workflow."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel

from core.scanner import FileScanner, ScanConfig, format_size
from core.hasher import ParallelHasher
from core.comparator import DuplicateComparator, ComparisonResult, format_duplicate_report
from core.cleaner import Cleaner
from core.database import CacheDB
from utils.logger import init_logging

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output")
@click.pass_context
def app(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """DupClean - High-performance duplicate file finder for macOS."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    if verbose:
        init_logging()


@app.command()
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--type", "-t", "file_type", 
              type=click.Choice(["all", "images", "videos", "audio", "documents"]),
              default="all", help="File type to scan")
@click.option("--similarity", "-s", default=10, type=int,
              help="Similarity threshold for perceptual matching (0-64, lower=stricter)")
@click.option("--min-size", default=1, type=int, help="Minimum file size in bytes")
@click.option("--max-size", default=0, type=int, help="Maximum file size in bytes (0=unlimited)")
@click.option("--workers", "-w", default=0, type=int, help="Number of worker processes (0=auto)")
@click.option("--no-perceptual", is_flag=True, help="Skip perceptual hash comparison")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Save results to JSON file")
@click.option("--use-cache/--no-cache", default=True, help="Use SQLite cache for incremental scans")
@click.pass_context
def scan(
    ctx: click.Context,
    paths: tuple[Path, ...],
    file_type: str,
    similarity: int,
    min_size: int,
    max_size: int,
    workers: int,
    no_perceptual: bool,
    output: Optional[Path],
    use_cache: bool,
) -> None:
    """Scan directories for duplicate files."""
    quiet = ctx.obj.get("quiet", False)
    start_time = time.time()
    
    # Configure scanner
    config = ScanConfig(
        min_size=min_size,
        max_size=max_size if max_size > 0 else 0,
    )
    
    if file_type != "all":
        config.file_extensions = FileScanner.get_extensions_for_type(file_type)
    
    scanner = FileScanner(config)
    hasher = ParallelHasher(
        max_workers=workers if workers > 0 else None,
        compute_perceptual=not no_perceptual and file_type in ("all", "images"),
    )
    comparator = DuplicateComparator(similarity_threshold=similarity)
    
    # Initialize cache if enabled
    cache: Optional[CacheDB] = None
    if use_cache:
        cache = CacheDB(Path.home() / ".dupclean" / "cache.db")
    
    all_files = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        disable=quiet,
    ) as progress:
        
        # Stage 1: Scan filesystem
        scan_task = progress.add_task("[cyan]Scanning files...", total=None)
        
        for batch in scanner.scan(list(paths)):
            all_files.extend(batch)
            progress.update(scan_task, description=f"[cyan]Scanned {len(all_files):,} files...")
        
        progress.update(scan_task, completed=100, total=100)
        
        if not all_files:
            console.print("[yellow]No files found matching criteria.[/yellow]")
            return
        
        # Stage 2: Size-based pre-grouping (optimization)
        progress.update(scan_task, description="[cyan]Grouping by size...")
        size_groups = {}
        for f in all_files:
            if f.size not in size_groups:
                size_groups[f.size] = []
            size_groups[f.size].append(f)
        
        # Only hash files that have size duplicates
        candidates = []
        for size, group in size_groups.items():
            if len(group) > 1:
                candidates.extend(group)
        
        if not candidates:
            console.print("[green]No potential duplicates found (all files have unique sizes).[/green]")
            return
        
        # Stage 3: Hash candidates
        hash_task = progress.add_task(
            f"[green]Hashing {len(candidates):,} candidates...", 
            total=len(candidates)
        )
        
        def hash_progress(done: int, total: int) -> None:
            progress.update(hash_task, completed=done)
        
        hasher.hash_files(candidates, progress_callback=hash_progress)
        
        # Stage 4: Find duplicates
        progress.update(hash_task, description="[magenta]Analyzing duplicates...")
        result = comparator.find_all_duplicates(
            candidates,
            include_perceptual=not no_perceptual,
        )
    
    elapsed = time.time() - start_time
    
    # Display results
    if not quiet:
        console.print()
        display_results(result, scanner.stats, hasher.stats, elapsed)
    
    # Save to JSON if requested
    if output:
        save_results_json(result, output)
        console.print(f"\n[green]Results saved to {output}[/green]")
    
    # Cache results
    if cache:
        for f in candidates:
            cache.upsert_file(f.path, f.size, f.mtime, f.sha256, f.phash)
        cache.close()


def display_results(
    result: ComparisonResult,
    scan_stats: dict,
    hash_stats: dict,
    elapsed: float,
) -> None:
    """Display scan results in a rich formatted output."""
    
    # Summary panel
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="cyan", justify="right")
    summary.add_column(style="white")
    
    summary.add_row("Files scanned:", f"{scan_stats.get('files_scanned', 0):,}")
    summary.add_row("Total size:", format_size(scan_stats.get('total_size', 0)))
    summary.add_row("Files hashed:", f"{hash_stats.get('processed', 0):,}")
    summary.add_row("Scan time:", f"{elapsed:.1f}s")
    summary.add_row("", "")
    summary.add_row("Exact duplicate groups:", f"{len(result.exact_groups)}")
    summary.add_row("Similar image groups:", f"{len(result.perceptual_groups)}")
    summary.add_row("Total duplicates:", f"{result.total_duplicates:,}")
    summary.add_row("Space recoverable:", f"[bold green]{format_size(result.total_wasted_bytes)}[/bold green]")
    
    console.print(Panel(summary, title="[bold]Scan Summary[/bold]", border_style="blue"))
    
    # Top duplicate groups
    if result.exact_groups:
        console.print("\n[bold cyan]Top Exact Duplicate Groups:[/bold cyan]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Group", style="dim", width=6)
        table.add_column("Files", justify="right", width=6)
        table.add_column("Wasted", justify="right", width=12)
        table.add_column("Sample Path", style="green", no_wrap=False)
        
        for group in result.exact_groups[:10]:
            table.add_row(
                str(group.group_id),
                str(group.count),
                format_size(group.wasted_size),
                str(group.members[0].path)[:80],
            )
        
        console.print(table)
        
        if len(result.exact_groups) > 10:
            console.print(f"[dim]... and {len(result.exact_groups) - 10} more groups[/dim]")
    
    if result.perceptual_groups:
        console.print("\n[bold magenta]Similar Image Groups:[/bold magenta]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Group", style="dim", width=6)
        table.add_column("Files", justify="right", width=6)
        table.add_column("Sample Path", style="magenta", no_wrap=False)
        
        for group in result.perceptual_groups[:5]:
            table.add_row(
                str(group.group_id),
                str(group.count),
                str(group.members[0].path)[:80],
            )
        
        console.print(table)


def save_results_json(result: ComparisonResult, path: Path) -> None:
    """Save results to JSON file."""
    data = {
        "summary": {
            "exact_groups": len(result.exact_groups),
            "perceptual_groups": len(result.perceptual_groups),
            "total_duplicates": result.total_duplicates,
            "wasted_bytes": result.total_wasted_bytes,
        },
        "exact_duplicates": [
            {
                "group_id": g.group_id,
                "hash": g.key,
                "count": g.count,
                "wasted_bytes": g.wasted_size,
                "files": [
                    {"path": str(m.path), "size": m.size, "mtime": m.mtime}
                    for m in g.members
                ],
            }
            for g in result.exact_groups
        ],
        "similar_images": [
            {
                "group_id": g.group_id,
                "count": g.count,
                "files": [
                    {"path": str(m.path), "size": m.size, "phash": m.phash}
                    for m in g.members
                ],
            }
            for g in result.perceptual_groups
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


@app.command()
@click.argument("targets", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--group-id", "-g", type=int, help="Remove duplicates from specific group ID")
@click.option("--keep", type=click.Choice(["oldest", "newest", "largest", "smallest"]),
              default="oldest", help="Strategy for choosing which file to keep")
@click.option("--backup/--no-backup", default=True, help="Move to backup instead of delete")
@click.option("--backup-dir", type=click.Path(path_type=Path), 
              default=Path.home() / ".dupclean_backup",
              help="Backup directory location")
@click.option("--dry-run", is_flag=True, help="Show what would be deleted without doing it")
@click.pass_context
def remove(
    ctx: click.Context,
    targets: tuple[Path, ...],
    group_id: Optional[int],
    keep: str,
    backup: bool,
    backup_dir: Path,
    dry_run: bool,
) -> None:
    """Remove duplicate files safely."""
    if not targets and group_id is None:
        console.print("[red]Specify files to remove or use --group-id[/red]")
        return
    
    cleaner = Cleaner(backup_dir=backup_dir if backup else None)
    
    if dry_run:
        console.print("[yellow]DRY RUN - No files will be deleted[/yellow]\n")
        for path in targets:
            console.print(f"  Would remove: {path}")
        console.print(f"\n[dim]Total: {len(targets)} files[/dim]")
        return
    
    if backup:
        records = cleaner.delete_with_backup(targets)
        console.print(f"[green]Moved {len(records)} files to {backup_dir}[/green]")
    else:
        # Permanent deletion requires confirmation
        if not click.confirm(f"Permanently delete {len(targets)} files?"):
            return
        for path in targets:
            if path.exists():
                path.unlink()
        console.print(f"[green]Deleted {len(targets)} files[/green]")


@app.command()
@click.option("--format", "-f", "fmt", 
              type=click.Choice(["json", "csv", "text"]),
              default="text", help="Output format")
@click.option("--input", "-i", "input_file", type=click.Path(exists=True, path_type=Path),
              help="Load results from previous scan JSON")
@click.option("--output", "-o", type=click.Path(path_type=Path), required=True,
              help="Output file path")
def report(fmt: str, input_file: Optional[Path], output: Path) -> None:
    """Generate a report from scan results."""
    if not input_file:
        console.print("[red]Please specify --input with a JSON results file[/red]")
        return
    
    data = json.loads(input_file.read_text())
    
    if fmt == "json":
        output.write_text(json.dumps(data, indent=2))
    elif fmt == "csv":
        import csv
        with output.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["group_id", "type", "path", "size", "hash"])
            for group in data.get("exact_duplicates", []):
                for file in group["files"]:
                    writer.writerow([
                        group["group_id"], "exact",
                        file["path"], file["size"], group["hash"][:16]
                    ])
    else:
        # Text format
        lines = [
            "DUPLICATE FILE REPORT",
            "=" * 60,
            f"Exact duplicate groups: {data['summary']['exact_groups']}",
            f"Similar image groups: {data['summary']['perceptual_groups']}",
            f"Total duplicates: {data['summary']['total_duplicates']}",
            f"Space recoverable: {format_size(data['summary']['wasted_bytes'])}",
            "",
        ]
        output.write_text("\n".join(lines))
    
    console.print(f"[green]Report saved to {output}[/green]")


@app.command()
def gui() -> None:
    """Launch the graphical interface."""
    try:
        from gui.main_window import run_gui
        run_gui()
    except ImportError as e:
        console.print(f"[red]GUI dependencies not available: {e}[/red]")
        console.print("Install with: pip install PyQt6")


@app.command()
def info() -> None:
    """Show system info and library versions."""
    import platform
    import os
    
    table = Table(title="System Information", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    
    table.add_row("Python", platform.python_version())
    table.add_row("Platform", platform.platform())
    table.add_row("CPU Cores", str(os.cpu_count()))
    table.add_row("Architecture", platform.machine())
    
    # Check optional dependencies
    try:
        import xxhash
        table.add_row("xxhash", xxhash.VERSION)
    except ImportError:
        table.add_row("xxhash", "[red]Not installed[/red]")
    
    try:
        import imagehash
        table.add_row("imagehash", "[green]Available[/green]")
    except ImportError:
        table.add_row("imagehash", "[red]Not installed[/red]")
    
    try:
        from PIL import Image
        table.add_row("Pillow", Image.__version__)
    except ImportError:
        table.add_row("Pillow", "[red]Not installed[/red]")
    
    console.print(table)


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()
