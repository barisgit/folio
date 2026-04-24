"""`folio docs` command group — thin IO adapter."""
from __future__ import annotations

import json
import sys
from difflib import get_close_matches
from enum import StrEnum
from typing import Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from folio.services.docs import VALID_KINDS
from folio.services.docs.generate import index_path
from folio.services.docs.generate import main as _generate_main

_EXIT_OK = 0
_EXIT_USER_ERROR = 1
_EXIT_NOT_FOUND = 2
_EXIT_SCHEMA_MISMATCH = 3


class _Format(StrEnum):
    TEXT = "text"
    JSON = "json"
    MD = "md"


docs_app = typer.Typer(
    name="docs",
    help="Look up the Folio DSL reference from the packaged JSON index.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

_console = Console()
_error_console = Console(stderr=True)


@docs_app.command("show")
def show_command(
    symbol: str = typer.Argument(
        ..., help="Symbol id or bare name, e.g. `page` or `folio.dsl.page`."
    ),
    format: _Format = typer.Option(  # noqa: A002
        _Format.TEXT, "--format", case_sensitive=False, help="Output format."
    ),
    json_flag: bool = typer.Option(
        False, "--json", help="Shortcut for --format=json."
    ),
) -> None:
    """Show the signature, summary, params, examples, and source for a symbol."""
    fmt = _resolve_format(format=format, json_flag=json_flag)
    index = _load_index()
    match = _find_symbol(index, symbol)
    if match is None:
        hint = _nearest_symbol(index, symbol)
        if fmt is _Format.JSON:
            _print_json({"error": "unknown_symbol", "query": symbol, "suggestion": hint})
        else:
            _error_console.print(
                f"[red]unknown symbol:[/red] {symbol}"
                + (f"\n[dim]did you mean:[/dim] {hint}" if hint else "")
            )
        raise typer.Exit(code=_EXIT_NOT_FOUND)
    if fmt is _Format.JSON:
        _print_json(match)
    elif fmt is _Format.MD:
        _console.print(_symbol_to_markdown(match))
    else:
        _render_symbol_text(match)


@docs_app.command("search")
def search_command(
    query: str = typer.Argument(..., help="Search term (case-insensitive)."),
    format: _Format = typer.Option(  # noqa: A002
        _Format.TEXT, "--format", case_sensitive=False, help="Output format."
    ),
    json_flag: bool = typer.Option(
        False, "--json", help="Shortcut for --format=json."
    ),
) -> None:
    """Search symbols by name, summary, parameter names, or tags."""
    fmt = _resolve_format(format=format, json_flag=json_flag)
    index = _load_index()
    matches = _search_symbols(index, query)
    if fmt is _Format.JSON:
        _print_json({"query": query, "matches": matches})
    elif fmt is _Format.MD:
        _console.print(_search_to_markdown(query, matches))
    else:
        _render_search_text(query, matches)


@docs_app.command("list")
def list_command(
    kind: str | None = typer.Option(
        None, "--kind", help=f"Filter by kind: one of {', '.join(VALID_KINDS)}."
    ),
    format: _Format = typer.Option(  # noqa: A002
        _Format.TEXT, "--format", case_sensitive=False, help="Output format."
    ),
    json_flag: bool = typer.Option(
        False, "--json", help="Shortcut for --format=json."
    ),
) -> None:
    """List every symbol in the index, optionally filtered by `--kind`."""
    fmt = _resolve_format(format=format, json_flag=json_flag)
    if kind is not None and kind not in VALID_KINDS:
        _error_console.print(
            f"[red]invalid kind:[/red] {kind}\n"
            f"[dim]expected one of:[/dim] {', '.join(VALID_KINDS)}"
        )
        raise typer.Exit(code=_EXIT_USER_ERROR)
    index = _load_index()
    symbols = index["symbols"]
    if kind is not None:
        symbols = [symbol for symbol in symbols if symbol["kind"] == kind]
    if fmt is _Format.JSON:
        _print_json({"version": index["version"], "count": len(symbols), "symbols": symbols})
    elif fmt is _Format.MD:
        _console.print(_list_to_markdown(symbols))
    else:
        _render_list_text(symbols, kind=kind)


@docs_app.command("generate")
def generate_command() -> None:
    """Regenerate `src/folio/docs/index.json` from the current DSL source."""
    code = _generate_main([])
    raise typer.Exit(code=code)


def _resolve_format(*, format: _Format, json_flag: bool) -> _Format:
    if not json_flag:
        return format
    if format is _Format.JSON or format is _Format.TEXT:
        return _Format.JSON
    _error_console.print(
        f"[red]conflicting flags:[/red] --json cannot be combined with --format={format.value}"
    )
    raise typer.Exit(code=_EXIT_USER_ERROR)


def _load_index() -> dict[str, Any]:
    path = index_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _error_console.print(
            f"[red]doc index missing:[/red] {path}\n"
            "[dim]run `python -m folio.docs.generate` or reinstall Folio.[/dim]"
        )
        raise typer.Exit(code=_EXIT_SCHEMA_MISMATCH) from None
    except (json.JSONDecodeError, OSError) as exc:
        _error_console.print(f"[red]doc index unreadable:[/red] {path}\n[dim]{exc}[/dim]")
        raise typer.Exit(code=_EXIT_SCHEMA_MISMATCH) from None
    version = payload.get("version")
    if version != 1:
        _error_console.print(
            f"[red]doc index schema mismatch:[/red] expected 1, got {version!r}"
        )
        raise typer.Exit(code=_EXIT_SCHEMA_MISMATCH)
    return payload


def _find_symbol(index: dict[str, Any], query: str) -> dict[str, Any] | None:
    for symbol in index["symbols"]:
        if symbol["id"] == query:
            return symbol
    bare = query.rsplit(".", 1)[-1]
    for symbol in index["symbols"]:
        if symbol["name"] == bare:
            return symbol
    return None


def _nearest_symbol(index: dict[str, Any], query: str) -> str | None:
    candidates = [symbol["id"] for symbol in index["symbols"]] + [
        symbol["name"] for symbol in index["symbols"]
    ]
    matches = get_close_matches(query, candidates, n=1, cutoff=0.55)
    return matches[0] if matches else None


def _search_symbols(index: dict[str, Any], query: str) -> list[dict[str, Any]]:
    needle = query.casefold()
    matches: list[dict[str, Any]] = []
    for symbol in index["symbols"]:
        haystacks = [
            symbol["name"],
            symbol["summary"],
            " ".join(symbol.get("tags", [])),
        ]
        haystacks.extend(param["name"] for param in symbol.get("params", []))
        if any(needle in field.casefold() for field in haystacks):
            matches.append(symbol)
    return matches


def _print_json(payload: Any) -> None:
    _console.print_json(data=payload)


def _render_symbol_text(symbol: dict[str, Any]) -> None:
    title = f"[bold]{symbol['id']}[/bold]  [dim]({symbol['kind']})[/dim]"
    _console.print(Panel.fit(title, border_style="cyan"))
    _console.print(f"[cyan]{symbol['signature']}[/cyan]")
    _console.print()
    _console.print(symbol["summary"])
    if symbol.get("description"):
        _console.print()
        _console.print(symbol["description"])
    if symbol.get("params"):
        _console.print()
        table = Table(title="Parameters", show_lines=False, box=None)
        table.add_column("name", style="magenta")
        table.add_column("type", style="cyan")
        table.add_column("doc")
        for param in symbol["params"]:
            table.add_row(param["name"], param["type"] or "\u2014", param["doc"] or "")
        _console.print(table)
    returns = symbol.get("returns")
    if returns:
        _console.print()
        _console.print(
            f"[bold]Returns:[/bold] [cyan]{returns['type']}[/cyan]"
            + (f" \u2014 {returns['doc']}" if returns.get("doc") else "")
        )
    for index_, example in enumerate(symbol.get("examples", []), start=1):
        _console.print()
        caption = example.get("caption") or f"Example {index_}"
        _console.print(Panel(example["code"], title=caption, border_style="green"))
    if symbol.get("tags"):
        _console.print()
        _console.print(f"[dim]tags:[/dim] {', '.join(symbol['tags'])}")
    _console.print()
    _console.print(f"[dim]source: {symbol['source']} \u2014 import from {symbol['module']}[/dim]")


def _symbol_to_markdown(symbol: dict[str, Any]) -> Markdown:
    lines = [f"# `{symbol['id']}` ({symbol['kind']})", ""]
    lines.append(f"```python\n{symbol['signature']}\n```")
    lines.append("")
    lines.append(symbol["summary"])
    if symbol.get("description"):
        lines.extend(["", symbol["description"]])
    if symbol.get("params"):
        lines.extend(["", "## Parameters", ""])
        for param in symbol["params"]:
            lines.append(f"- `{param['name']}` ({param['type']}): {param['doc']}")
    returns = symbol.get("returns")
    if returns:
        lines.extend(
            ["", f"## Returns\n\n`{returns['type']}` \u2014 {returns.get('doc', '')}"]
        )
    for index_, example in enumerate(symbol.get("examples", []), start=1):
        caption = example.get("caption") or f"Example {index_}"
        lines.extend(["", f"### {caption}", "", f"```python\n{example['code']}\n```"])
    if symbol.get("tags"):
        lines.extend(["", f"_tags: {', '.join(symbol['tags'])}_"])
    lines.extend(["", f"_source: `{symbol['source']}` \u00b7 import from `{symbol['module']}`_"])
    return Markdown("\n".join(lines))


def _search_to_markdown(query: str, matches: list[dict[str, Any]]) -> Markdown:
    if not matches:
        return Markdown(f"# search `{query}`\n\nNo results.")
    lines = [f"# search `{query}` ({len(matches)} match{'es' if len(matches) != 1 else ''})", ""]
    for symbol in matches:
        lines.append(f"- `{symbol['id']}` ({symbol['kind']}) \u2014 {symbol['summary']}")
    return Markdown("\n".join(lines))


def _list_to_markdown(symbols: list[dict[str, Any]]) -> Markdown:
    lines = [f"# Folio DSL ({len(symbols)} symbol{'s' if len(symbols) != 1 else ''})", ""]
    for symbol in symbols:
        lines.append(f"- `{symbol['id']}` ({symbol['kind']}) \u2014 {symbol['summary']}")
    return Markdown("\n".join(lines))


def _render_search_text(query: str, matches: list[dict[str, Any]]) -> None:
    if not matches:
        _console.print(f"no results for: [bold]{query}[/bold]")
        return
    table = Table(title=f"search: {query}", box=None, show_lines=False)
    table.add_column("id", style="cyan")
    table.add_column("kind", style="magenta")
    table.add_column("summary")
    for symbol in matches:
        table.add_row(symbol["id"], symbol["kind"], symbol["summary"])
    _console.print(table)


def _render_list_text(symbols: list[dict[str, Any]], *, kind: str | None) -> None:
    title = "folio docs list"
    if kind:
        title += f"  (kind={kind})"
    table = Table(title=title, box=None, show_lines=False)
    table.add_column("id", style="cyan")
    table.add_column("kind", style="magenta")
    table.add_column("summary")
    for symbol in symbols:
        table.add_row(symbol["id"], symbol["kind"], symbol["summary"])
    _console.print(table)


__all__ = ["docs_app"]


def _entrypoint() -> None:
    _ = sys.argv
    docs_app()
