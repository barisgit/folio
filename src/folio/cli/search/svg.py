"""``folio search svg`` sub-command — thin IO adapter."""

from __future__ import annotations

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from folio.services.search.svg import (
    SUPPORTED_SVG_SOURCES,
    SvgSearchError,
    SvgSearchResponse,
    search_svg_assets,
)

console = Console()

COMMAND_NAME = "svg"
COMMAND_HELP = "Search public SVG sources for logos and icons."


def _render_results_table(response: SvgSearchResponse) -> Table:
    table = Table(show_header=True)
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("Source", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Context")
    table.add_column("SVG URL", overflow="fold")

    for index, result in enumerate(response.results, start=1):
        context_parts = [
            part for part in (result.subtitle, result.identifier, result.website) if part
        ]
        table.add_row(
            str(index),
            result.source,
            result.title,
            "\n".join(context_parts) or "-",
            result.svg_url,
        )

    return table


def svg_command(
    query: Annotated[str, typer.Argument(help="Search query, e.g. 'stripe' or 'trash icon'")],
    limit: Annotated[
        int,
        typer.Option("--limit", min=1, max=25, help="Maximum verified matches to return"),
    ] = 8,
    source: Annotated[
        list[str] | None,
        typer.Option(
            "--source",
            help=(
                "Search only specific providers. Repeatable. "
                f"Choices: {', '.join(SUPPORTED_SVG_SOURCES)}"
            ),
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON"),
    ] = False,
) -> None:
    try:
        response = search_svg_assets(query, limit=limit, sources=tuple(source or ()))
    except SvgSearchError as exc:
        console.print(f"[red]SVG search error:[/red] {exc}")
        raise typer.Exit(1) from exc

    if json_output:
        console.print_json(json.dumps(response.to_dict(), indent=2))
        return

    if response.results:
        console.print(_render_results_table(response))
    else:
        console.print(f"[yellow]No SVG matches found[/yellow] for [cyan]{query}[/cyan]")

    for warning in response.warnings:
        console.print(f"[yellow]warning:[/yellow] {warning}")


command = svg_command
