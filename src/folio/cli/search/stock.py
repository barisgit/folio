"""``folio search stock`` sub-command — thin IO adapter."""
from __future__ import annotations

import json as _json
from typing import TypeGuard

import typer
from rich.console import Console
from rich.table import Table

from folio.services.search.providers import (
    PROVIDERS,
    Provider,
    SearchResult,
    fetch_stock,
    fetch_stock_multi,
)


def _is_provider(value: str) -> TypeGuard[Provider]:
    return value in PROVIDERS

console = Console(width=200)

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
    table.add_column("License", max_width=16)
    table.add_column("Creator", max_width=20)
    table.add_column("Source", max_width=20)

    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r.id[:24],
            r.provider,
            r.description[:60],
            r.url[:50],
            f"{r.width}×{r.height}",
            r.license or "\u2013",
            r.creator or "\u2013",
            r.source or "\u2013",
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
            "license": r.license or None,
            "creator": r.creator or None,
            "source": r.source or None,
        }
        for r in results
    ]
    console.print_json(_json.dumps(payload))


def _resolve_providers(raw_providers: list[str] | None) -> list[Provider]:
    if not raw_providers:
        return ["openverse"]

    if "all" in raw_providers:
        invalid = sorted(
            {
                provider
                for provider in raw_providers
                if provider != "all" and provider not in PROVIDERS
            }
        )
        if invalid:
            valid = ", ".join(PROVIDERS) + ", all"
            raise RuntimeError(
                f"Unknown provider(s): {', '.join(invalid)}. Valid: {valid}"
            )
        return list(PROVIDERS)

    invalid = sorted({provider for provider in raw_providers if provider not in PROVIDERS})
    if invalid:
        valid = ", ".join(PROVIDERS) + ", all"
        raise RuntimeError(
            f"Unknown provider(s): {', '.join(invalid)}. Valid: {valid}"
        )

    resolved: list[Provider] = []
    for provider_name in raw_providers:
        if _is_provider(provider_name) and provider_name not in resolved:
            resolved.append(provider_name)
    return resolved


def stock_command(
    query: str = typer.Argument(..., help="Search query string."),
    provider: list[str] | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Repeat to search multiple providers. Choices: openverse, pexels, pixabay, all.",
    ),
    per_page: int = typer.Option(10, "--per-page", "-n", help="Max results to return."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Search stock images from Openverse, Pexels, or Pixabay."""
    try:
        providers_list = _resolve_providers(provider)
        if len(providers_list) == 1:
            results = fetch_stock(query, provider=providers_list[0], per_page=per_page)
        else:
            results = fetch_stock_multi(query, providers=providers_list, per_page=per_page)
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
