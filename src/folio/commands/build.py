from __future__ import annotations

from dataclasses import replace
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.cache import cache_build
from folio.dsl.loader import DslError, load_dsl_module, resolve_spec_path
from folio.dsl.renderer import (
    BuildResult,
    RenderError,
    document_from_module,
    render_document,
    write_pages,
)
from folio.export import write_idml

console = Console()


class BuildFormat(StrEnum):
    SVG = "svg"
    IDML = "idml"


def build_command(
    spec_path: Annotated[Path | None, typer.Argument(help="Path to Python DSL module")] = None,
    out_dir: Annotated[
        Path | None, typer.Option("--out-dir", help="Directory for rendered output")
    ] = None,
    output_format: Annotated[
        BuildFormat,
        typer.Option("--format", help="Output format: svg or idml"),
    ] = BuildFormat.SVG,
    page_number: Annotated[
        int | None,
        typer.Option("--page", min=1, help="Only write a single page number"),
    ] = None,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Skip updating the last-build cache"),
    ] = False,
) -> None:
    resolved_spec = resolve_spec_path(spec_path)
    resolved_out_dir = (out_dir or (resolved_spec.parent / "out")).expanduser().resolve()
    try:
        dsl_module = load_dsl_module(resolved_spec)
        document = document_from_module(dsl_module)
        result = render_document(
            document,
            config_dir=resolved_spec.parent,
            source_path=resolved_spec,
        )
        output_result = result
        output_document = document
        if page_number is not None:
            selected_pages = [page for page in result.pages if page.page_number == page_number]
            selected_document_pages = [
                page for page in document.pages if page.page_number == page_number
            ]
            if not selected_pages or not selected_document_pages:
                raise RenderError(f"Page {page_number} not found in spec")
            output_result = BuildResult(pages=selected_pages, config_hash=result.config_hash)
            output_document = replace(document, pages=tuple(selected_document_pages))
        written = write_pages(output_result, resolved_out_dir)
        if output_format is BuildFormat.IDML:
            written.append(write_idml(output_document, resolved_out_dir))
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
