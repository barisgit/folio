"""``folio search stock`` sub-command — stock-image search via Openverse / Pexels / Pixabay."""

from __future__ import annotations

import json as _json

import typer
from rich.console import Console
from rich.table import Table

from folio.search.providers import Provider, SearchResult, fetch_stock

console = Console(width=120)

COMMAND_NAME = "stock"
COMMAND_HELP = "Search stock images from Openverse, Pexels, or Pixabay."


def _render_table(results: list[SearchResult]) -> None:
    table = Table(title="Search Results", show_lines=True)
    table.add_column("#", style="dim", justify="right")
    table.add_column("ID", style="cyan", max_width=24)
    table.add_column("Provider", style="green")
    table.add_column("Description", max_width=60)
    table.add_column("URL", style="blue", max_width=50)
    table.add_column("Size", justify="right")

    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r.id[:24],
            r.provider,
            r.description[:60],
            r.url[:50],
            f"{r.width}×{r.height}",
        )
    console.print(table)


def _render_json(results: list[SearchResult]) -> None:
    payload = [
        {
            "id": r.id,
            "provider": r.provider,
            "description": r.description,
            "url": r.url,
            "thumbnail": r.thumbnail,
            "width": r.width,
            "height": r.height,
        }
        for r in results
    ]
    console.print_json(_json.dumps(payload))


def stock_command(
    query: str = typer.Argument(..., help="Search query string."),
    provider: Provider = typer.Option(
        "openverse", "--provider", "-p", help="Image provider."
    ),
    per_page: int = typer.Option(10, "--per-page", "-n", help="Max results to return."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Search stock images from Openverse, Pexels, or Pixabay."""
    try:
        results = fetch_stock(query, provider=provider, per_page=per_page)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Request failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        raise typer.Exit()

    if json_output:
        _render_json(results)
    else:
        _render_table(results)


command = stock_command
