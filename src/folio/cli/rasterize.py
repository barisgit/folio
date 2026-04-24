"""`folio rasterize` command — thin IO adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from folio.core.cache import CacheError, cached_pages, last_build_svg
from folio.core.dsl.loader import resolve_spec_path
from folio.core.preview import PreviewError, render_preview_file, render_raster

console = Console()


def _parse_viewport(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", maxsplit=1)
        width = int(width_text)
        height = int(height_text)
    except ValueError as exc:
        raise typer.BadParameter("Viewport must be WIDTHxHEIGHT, e.g. 1920x1080") from exc
    if width <= 0 or height <= 0:
        raise typer.BadParameter("Viewport dimensions must be positive")
    return width, height


def rasterize_command(
    svg_path: Annotated[Path | None, typer.Argument(help="SVG file to rasterize")] = None,
    spec_path: Annotated[
        Path | None, typer.Option("--spec", help="Spec file used for cache location")
    ] = None,
    output_path: Annotated[
        Path | None,
        typer.Option("--output", help="PNG output path when rasterizing a specific SVG"),
    ] = None,
    viewport: Annotated[
        str | None,
        typer.Option("--viewport", help="Viewport as WIDTHxHEIGHT, e.g. 1920x1080"),
    ] = None,
) -> None:
    resolved_viewport = _parse_viewport(viewport) if viewport is not None else None

    if svg_path is None and output_path is not None:
        raise typer.BadParameter("--output requires an SVG path argument")

    try:
        outputs = []
        if svg_path is not None:
            outputs.append(
                render_preview_file(
                    svg_path,
                    output_path=output_path,
                    viewport=resolved_viewport,
                )
            )
        else:
            resolved_spec = resolve_spec_path(spec_path)
            for page in cached_pages(resolved_spec):
                cached_svg = last_build_svg(resolved_spec, page.page_number)
                outputs.append(
                    render_raster(
                        cached_svg,
                        spec_path=resolved_spec,
                        page_number=page.page_number,
                        viewport=resolved_viewport,
                    )
                )
    except (CacheError, FileNotFoundError, PreviewError) as exc:
        console.print(f"[red]Rasterize error:[/red] {exc}")
        raise typer.Exit(2) from exc

    for output in outputs:
        console.print(f"wrote [green]{output}[/green]")
