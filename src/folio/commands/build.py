from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.cache import cache_build
from folio.dsl.loader import DslError, default_spec_path, load_dsl_module
from folio.dsl.renderer import BuildResult, RenderError, build_pages, write_pages

console = Console()


def build_command(
    spec_path: Annotated[Path | None, typer.Argument(help="Path to Python DSL module")] = None,
    out_dir: Annotated[Path, typer.Option("--out-dir", help="Directory for rendered SVGs")] = Path(
        "out"
    ),
    page_number: Annotated[
        int | None,
        typer.Option("--page", min=1, help="Only write a single page number"),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Skip updating the last-build cache"),
    ] = False,
) -> None:
    resolved_spec = (spec_path or default_spec_path()).expanduser().resolve()
    try:
        dsl_module = load_dsl_module(resolved_spec)
        result = build_pages(dsl_module, config_dir=resolved_spec.parent)
        output_result = result
        if page_number is not None:
            selected_pages = [page for page in result.pages if page.page_number == page_number]
            if not selected_pages:
                raise RenderError(f"Page {page_number} not found in spec")
            output_result = BuildResult(pages=selected_pages, config_hash=result.config_hash)
        written = write_pages(output_result, out_dir)
        cached = None if no_cache else cache_build(result, spec_path=resolved_spec)
    except DslError as exc:
        console.print(f"[red]Build error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except RenderError as exc:
        console.print(f"[red]Render error:[/red] {exc}")
        raise typer.Exit(2) from exc

    for path in written:
        console.print(f"wrote [green]{path}[/green]")
    if cached is not None:
        console.print(f"cached build in [cyan]{cached.manifest.parent}[/cyan]")
